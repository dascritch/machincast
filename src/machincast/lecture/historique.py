"""Historique de diffusion, en base ou en mémoire (https://github.com/dascritch/machincast/issues/21).

Tout ce que le binaire lecture lit dans l'airplay pour décider (compteurs de lectures, cycles des banques, position
dans les listes), et tout ce qu'il y écrit (passages, log, expirations), passe par un Historique :

- HistoriqueEnBase (EN_BASE), pour la diffusion : il lit et écrit la base, par machincast.lecture.enregistrement et
  machincast.lecture.expiration ;
- HistoriqueSimule (machincast.lecture.simulation), pour la simulation : il lit la base sans jamais y écrire, et tient
  en mémoire les passages, le log et les expirations simulés, dont ses lectures tiennent compte.

Les deux donnent les mêmes réponses pour un même historique : la logique de lecture est la même en diffusion et en
simulation.
"""

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import entier_ou_rien
from machincast.lecture import enregistrement
from machincast.lecture.enregistrement import Passage
from machincast.lecture.expiration import Expiration, expirer

Connexion = psycopg.Connection[TupleRow]


@dataclass(frozen=True)
class DernierPassage:
	"""Le passage le plus récent de tout l'historique, et la banque qui l'a fourni."""

	id: uuid.UUID
	banque: int | None
	"""None pour un sonore placé directement dans un événement."""
	debut: datetime | None = None
	evenement: int | None = None
	element: int | None = None
	"""Élément de la liste de l'événement qui l'a fait jouer."""
	sequence_element: int | None = None
	"""Élément de la séquence qui l'a fait jouer (https://github.com/dascritch/machincast/issues/99)."""


class Historique(Protocol):
	def lectures(self, connexion: Connexion, sonores: Collection[int]) -> dict[int, int]:
		"""Passages de chaque sonore (lignes de début), sur tout l'historique, quelle que soit la banque."""
		...

	def joues_via_banque(self, connexion: Connexion, banque: int) -> list[int]:
		"""Sonores joués via la banque, du passage le plus récent au plus ancien."""
		...

	def dernier_element(self, connexion: Connexion, evenement: int, depuis: datetime | None) -> int | None:
		"""Élément de l'événement joué en dernier, depuis cet instant s'il est donné."""
		...

	def dernier_passage(self, connexion: Connexion) -> DernierPassage | None:
		"""Passage le plus récent, tous événements confondus ; None si l'historique est vide."""
		...

	def commencer_passage(
		self,
		connexion: Connexion,
		sonore: int,
		banque: int | None,
		evenement: int | None,
		element: int | None,
		instant: datetime,
		sequence: int | None = None,
		sequence_element: int | None = None,
	) -> Passage: ...

	def terminer_passage(
		self,
		connexion: Connexion,
		passage: Passage,
		instant: datetime,
		coupe: bool = False,
		erreur: str | None = None,
		nature: str = "lecture interrompue",
	) -> None: ...

	def consigner(
		self,
		connexion: Connexion,
		niveau: str,
		nature: str,
		message: str,
		instant: datetime | None = None,
		sonore: int | None = None,
		banque: int | None = None,
		evenement: int | None = None,
	) -> None: ...

	def expirer(self, connexion: Connexion, instant: datetime, sonore: int | None = None) -> list[Expiration]: ...


@dataclass(frozen=True)
class HistoriqueEnLecture:
	"""Un historique qui lit celui qu'il enveloppe, sans jamais rien écrire : pour anticiper une décision sans en
	laisser de trace (https://github.com/dascritch/machincast/issues/169)."""

	source: Historique

	def lectures(self, connexion: Connexion, sonores: Collection[int]) -> dict[int, int]:
		return self.source.lectures(connexion, sonores)

	def joues_via_banque(self, connexion: Connexion, banque: int) -> list[int]:
		return self.source.joues_via_banque(connexion, banque)

	def dernier_element(self, connexion: Connexion, evenement: int, depuis: datetime | None) -> int | None:
		return self.source.dernier_element(connexion, evenement, depuis)

	def dernier_passage(self, connexion: Connexion) -> DernierPassage | None:
		return self.source.dernier_passage(connexion)

	def commencer_passage(
		self,
		connexion: Connexion,
		sonore: int,
		banque: int | None,
		evenement: int | None,
		element: int | None,
		instant: datetime,
		sequence: int | None = None,
		sequence_element: int | None = None,
	) -> Passage:
		raise AssertionError("une anticipation ne commence aucun passage")

	def terminer_passage(
		self,
		connexion: Connexion,
		passage: Passage,
		instant: datetime,
		coupe: bool = False,
		erreur: str | None = None,
		nature: str = "lecture interrompue",
	) -> None:
		raise AssertionError("une anticipation ne termine aucun passage")

	def consigner(
		self,
		connexion: Connexion,
		niveau: str,
		nature: str,
		message: str,
		instant: datetime | None = None,
		sonore: int | None = None,
		banque: int | None = None,
		evenement: int | None = None,
	) -> None:
		"""Rien n'est consigné : ce sera fait quand la décision sera prise pour de bon."""

	def expirer(self, connexion: Connexion, instant: datetime, sonore: int | None = None) -> list[Expiration]:
		return []


class HistoriqueEnBase:
	"""L'airplay et le log de la base, avec les droits de la lecture."""

	def lectures(self, connexion: Connexion, sonores: Collection[int]) -> dict[int, int]:
		lignes = connexion.execute(
			"SELECT sonore_id, count(*) FROM airplay WHERE type_ligne = 'debut' AND sonore_id = ANY(%s)"
			" GROUP BY sonore_id",
			(list(sonores),),
		).fetchall()
		comptes = {int(str(sonore)): int(str(nombre)) for sonore, nombre in lignes}
		return {sonore: comptes.get(sonore, 0) for sonore in sonores}

	def joues_via_banque(self, connexion: Connexion, banque: int) -> list[int]:
		lignes = connexion.execute(
			"SELECT sonore_id FROM airplay WHERE banque_id = %s AND type_ligne = 'debut' AND sonore_id IS NOT NULL"
			" ORDER BY horodatage DESC, id DESC",
			(banque,),
		).fetchall()
		return [int(str(ligne[0])) for ligne in lignes]

	def dernier_element(self, connexion: Connexion, evenement: int, depuis: datetime | None) -> int | None:
		ligne = connexion.execute(
			"SELECT element_id FROM airplay WHERE evenement_id = %s AND type_ligne = 'debut'"
			" AND (%s::timestamptz IS NULL OR horodatage >= %s::timestamptz)"
			" ORDER BY horodatage DESC, id DESC LIMIT 1",
			(evenement, depuis, depuis),
		).fetchone()
		return None if (ligne is None) or (ligne[0] is None) else int(str(ligne[0]))

	def dernier_passage(self, connexion: Connexion) -> DernierPassage | None:
		ligne = connexion.execute(
			"SELECT passage_id, banque_id, horodatage, evenement_id, element_id, sequence_element_id FROM airplay"
			" WHERE type_ligne = 'debut' ORDER BY horodatage DESC, id DESC LIMIT 1"
		).fetchone()
		if ligne is None:
			return None
		passage, banque, debut, evenement, element, sequence_element = ligne
		return DernierPassage(
			uuid.UUID(str(passage)),
			entier_ou_rien(banque),
			debut if isinstance(debut, datetime) else None,
			entier_ou_rien(evenement),
			entier_ou_rien(element),
			entier_ou_rien(sequence_element),
		)

	def commencer_passage(
		self,
		connexion: Connexion,
		sonore: int,
		banque: int | None,
		evenement: int | None,
		element: int | None,
		instant: datetime,
		sequence: int | None = None,
		sequence_element: int | None = None,
	) -> Passage:
		return enregistrement.commencer_passage(
			connexion, sonore, banque, evenement, element, instant, sequence, sequence_element
		)

	def terminer_passage(
		self,
		connexion: Connexion,
		passage: Passage,
		instant: datetime,
		coupe: bool = False,
		erreur: str | None = None,
		nature: str = "lecture interrompue",
	) -> None:
		enregistrement.terminer_passage(connexion, passage, instant, coupe=coupe, erreur=erreur, nature=nature)

	def consigner(
		self,
		connexion: Connexion,
		niveau: str,
		nature: str,
		message: str,
		instant: datetime | None = None,
		sonore: int | None = None,
		banque: int | None = None,
		evenement: int | None = None,
	) -> None:
		enregistrement.consigner(connexion, niveau, nature, message, instant, sonore, banque, evenement)

	def expirer(self, connexion: Connexion, instant: datetime, sonore: int | None = None) -> list[Expiration]:
		return expirer(connexion, instant, sonore)


EN_BASE: Historique = HistoriqueEnBase()
"""Historique de la diffusion : la base."""
