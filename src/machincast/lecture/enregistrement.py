"""Enregistrement de l'airplay et du log (https://github.com/dascritch/machincast/issues/17, spec § 3.1 et § 5.2).

Le binaire lecture n'écrit que par ce module, et seulement des insertions : ses droits PostgreSQL ne lui
permettent ni de modifier ni de supprimer une ligne d'airplay ou de log, ni de lire le log (pas de RETURNING).

- Airplay : deux lignes par passage, reliées par passage_id. Chacune recopie l'emplacement (pour un stream, son
  adresse directe ou celle de son marque-page), l'artiste et le titre du sonore au moment du passage, et référence
  le sonore, la banque qui l'a fourni (aucune pour un sonore placé directement dans l'événement), l'événement et
  l'élément de sa liste. La ligne de fin donne la durée effectivement diffusée et l'indicateur sans_incident.
- Log : chaque opération, normale (info) ou non (alerte, incident), avec sa nature, un message et ses références.
  Une coupure nette est une opération normale ; une lecture interrompue par une erreur est un incident, que
  l'appelant peut nommer plus précisément (flux tombé d'un stream).

Les heures viennent de l'horloge du binaire (machincast.horloge), pour que la simulation et les tests soient
reproductibles.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import psycopg
from psycopg.rows import TupleRow

Niveau = Literal["info", "alerte", "incident"]


@dataclass(frozen=True)
class Passage:
	id: uuid.UUID
	sonore: int
	banque: int | None
	evenement: int | None
	element: int | None
	debut: datetime


def consigner(
	connexion: psycopg.Connection[TupleRow],
	niveau: str,
	nature: str,
	message: str,
	instant: datetime | None = None,
	sonore: int | None = None,
	banque: int | None = None,
	evenement: int | None = None,
) -> None:
	"""Ajoute une ligne au log ; sans instant, l'heure du serveur PostgreSQL. Jamais de RETURNING : la lecture
	n'a pas le droit de lire le log."""
	with connexion.transaction():
		connexion.execute(
			"INSERT INTO log (horodatage, niveau, nature, message, sonore_id, banque_id, evenement_id)"
			" VALUES (COALESCE(%s, clock_timestamp()), %s, %s, %s, %s, %s, %s)",
			(instant, niveau, nature, message, sonore, banque, evenement),
		)


def _debut(connexion: psycopg.Connection[TupleRow], passage: Passage) -> None:
	connexion.execute(
		"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, banque_id, evenement_id, element_id,"
		" emplacement, artiste, titre)"
		" SELECT %s, 'debut', %s, s.id, %s, %s, %s, COALESCE(s.emplacement, s.url_stream, m.url), s.artiste, s.titre"
		" FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id WHERE s.id = %s",
		(passage.id, passage.debut, passage.banque, passage.evenement, passage.element, passage.sonore),
	)


def _fin(connexion: psycopg.Connection[TupleRow], passage: Passage, instant: datetime, sans_incident: bool) -> None:
	# La ligne de fin recopie la ligne de début : l'artiste et le titre restent ceux du moment du passage.
	connexion.execute(
		"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, banque_id, evenement_id, element_id,"
		" emplacement, artiste, titre, duree_diffusee, sans_incident)"
		" SELECT passage_id, 'fin', %s, sonore_id, banque_id, evenement_id, element_id, emplacement, artiste,"
		" titre, %s, %s FROM airplay WHERE passage_id = %s AND type_ligne = 'debut'",
		(instant, instant - passage.debut, sans_incident, passage.id),
	)


def commencer_passage(
	connexion: psycopg.Connection[TupleRow],
	sonore: int,
	banque: int | None,
	evenement: int | None,
	element: int | None,
	instant: datetime,
) -> Passage:
	"""Ligne de début d'un passage ; l'artiste et le titre sont recopiés tels qu'ils sont à cet instant."""
	passage = Passage(uuid.uuid4(), sonore, banque, evenement, element, instant)
	with connexion.transaction():
		_debut(connexion, passage)
	return passage


def terminer_passage(
	connexion: psycopg.Connection[TupleRow],
	passage: Passage,
	instant: datetime,
	coupe: bool = False,
	erreur: str | None = None,
	nature: str = "lecture interrompue",
) -> None:
	"""Ligne de fin d'un passage, avec la durée diffusée ; une coupure ou une erreur est aussi consignée au log,
	l'erreur en incident de la nature donnée."""
	with connexion.transaction():
		_fin(connexion, passage, instant, erreur is None)
		references = {"sonore": passage.sonore, "banque": passage.banque, "evenement": passage.evenement}
		if erreur is not None:
			consigner(connexion, "incident", nature, erreur, instant, **references)
		elif coupe:
			consigner(connexion, "info", "coupure nette", "début d'un événement", instant, **references)
