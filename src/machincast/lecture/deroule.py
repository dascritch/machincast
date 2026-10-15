"""Déroulé de la liste de lecture et transitions entre événements (https://github.com/dascritch/machincast/issues/14).

Spec § 4.2 et § 4.3. L'ordonnanceur décide, à chaque instant, ce que la sortie audio doit faire : continuer le
sonore en cours, le couper net, jouer un nouveau sonore, ou se taire. Il ne joue rien lui-même (moteur audio :
https://github.com/dascritch/machincast/issues/15) et n'écrit pas l'airplay
(https://github.com/dascritch/machincast/issues/17) : il lit l'airplay pour savoir où en est chaque liste.

Liste de lecture d'un événement (§ 4.3) :

- les éléments se jouent dans l'ordre de leur position ; un même élément peut revenir plusieurs fois ;
- un élément banque fait jouer un seul sonore de la banque (machincast.lecture.banques) ;
- une banque sans sonore jouable, ou un sonore qui n'est pas jouable, est sauté : on passe à l'élément suivant ;
- arrivée au bout, la liste reprend au début, sauf pour une émission ou un spécial sans fin, qui se termine alors
  pour cette occurrence : l'événement de priorité inférieure reprend la main ;
- une émission ou un spécial dont plus rien n'est jouable se termine de même ;
- l'élément suivant se lit dans l'airplay : celui qui suit le dernier élément joué. Pour une émission ou un
  spécial, seuls comptent les passages de l'occurrence en cours, qui commence donc au début de sa liste ; un fil
  musical reprend toujours à l'élément qui suit son dernier joué, d'une occurrence à l'autre (§ 4.2).

Transitions (§ 4.2) :

- le début d'un événement coupe net le sonore en cours, quel qu'il soit ;
- à la fin d'un événement, si aucun autre ne commence, le dernier sonore est joué jusqu'au bout, puis l'événement
  actif (le fil musical) reprend ;
- rien à diffuser : silence, et une alerte dans le log, une seule fois par silence.

Un sonore dont le fichier est introuvable au moment de le jouer est écarté (exclure) pendant
REESSAI_FICHIER_INTROUVABLE : il est traité comme non jouable, pour ne pas le réessayer à chaque tour de liste
(https://github.com/dascritch/machincast/issues/88).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow

from machincast.hasard import Hasard
from machincast.lecture.banques import choisir_sonore, sonore_jouable
from machincast.lecture.enregistrement import consigner
from machincast.lecture.grille import Occurrence, Priorite, evenement_actif, heure_murale, lire_grille

REESSAI_FICHIER_INTROUVABLE = timedelta(hours=1)
"""Durée pendant laquelle un sonore au fichier introuvable n'est plus proposé."""


@dataclass(frozen=True)
class Element:
	"""Un élément de la liste d'un événement : un sonore ou une banque."""

	id: int
	position: int
	sonore: int | None
	banque: int | None


@dataclass(frozen=True)
class Choix:
	"""Sonore à jouer, avec ce que le passage doit noter dans l'airplay."""

	sonore: int
	element: Element
	banque: int | None
	"""Banque qui a fourni le sonore ; None pour un sonore placé directement dans l'événement."""
	occurrence: Occurrence


@dataclass(frozen=True)
class EnCours:
	"""Passage en cours sur la sortie audio."""

	occurrence: Occurrence
	debut: datetime
	fin_prevue: datetime


@dataclass(frozen=True)
class Decision:
	couper: bool = False
	"""Couper net le sonore en cours."""
	jouer: Choix | None = None
	silence: bool = False
	"""Rien à diffuser : se taire."""
	occurrence: Occurrence | None = None
	"""Événement actif pendant un silence, pour le signaler."""

	@property
	def continuer(self) -> bool:
		return not (self.couper or self.jouer or self.silence)


def elements_a_essayer(elements: list[Element], dernier: int | None, boucle: bool) -> list[Element]:
	"""Éléments à essayer dans l'ordre, à partir de celui qui suit le dernier joué.

	Avec boucle, la liste fait un tour complet ; sans boucle, elle s'arrête à son dernier élément. Un dernier
	élément inconnu (jamais joué, ou supprimé depuis) fait repartir du début.
	"""
	ids = [e.id for e in elements]
	depart = ids.index(dernier) + 1 if dernier in ids else 0
	if not boucle:
		return elements[depart:]
	return elements[depart:] + elements[:depart]


def lire_elements(connexion: psycopg.Connection[TupleRow], evenement: int) -> list[Element]:
	lignes = connexion.execute(
		"SELECT id, position, sonore_id, banque_id FROM evenements_elements WHERE evenement_id = %s ORDER BY position",
		(evenement,),
	).fetchall()
	return [
		Element(
			id=int(str(identifiant)),
			position=int(str(position)),
			sonore=None if sonore is None else int(str(sonore)),
			banque=None if banque is None else int(str(banque)),
		)
		for identifiant, position, sonore, banque in lignes
	]


def dernier_element(connexion: psycopg.Connection[TupleRow], occurrence: Occurrence) -> int | None:
	"""Dernier élément joué de l'événement : dans l'occurrence en cours, ou depuis toujours pour un fil musical."""
	evenement = occurrence.evenement
	depuis = None
	if evenement.priorite is not Priorite.FIL_MUSICAL and occurrence.debut is not None:
		depuis = occurrence.debut.astimezone()
	ligne = connexion.execute(
		"SELECT element_id FROM airplay WHERE evenement_id = %s AND type_ligne = 'debut'"
		" AND (%s::timestamptz IS NULL OR horodatage >= %s::timestamptz)"
		" ORDER BY horodatage DESC, id DESC LIMIT 1",
		(evenement.id, depuis, depuis),
	).fetchone()
	return None if ligne is None or ligne[0] is None else int(str(ligne[0]))


def boucle(occurrence: Occurrence) -> bool:
	"""Une émission ou un spécial sans fin ne boucle pas : il se termine à la fin de sa liste."""
	return occurrence.evenement.priorite is Priorite.FIL_MUSICAL or occurrence.fin is not None


def prochain(
	connexion: psycopg.Connection[TupleRow],
	occurrence: Occurrence,
	instant: datetime,
	hasard: Hasard,
	exclus: frozenset[int] = frozenset(),
) -> Choix | None:
	"""Prochain sonore de la liste de l'occurrence ; None si rien n'est jouable jusqu'à la fin de la liste.

	exclus : sonores écartés, traités comme non jouables.
	"""
	elements = lire_elements(connexion, occurrence.evenement.id)
	for element in elements_a_essayer(elements, dernier_element(connexion, occurrence), boucle(occurrence)):
		if element.sonore is not None:
			if element.sonore not in exclus and sonore_jouable(connexion, element.sonore, instant):
				return Choix(element.sonore, element, None, occurrence)
		elif element.banque is not None:
			sonore = choisir_sonore(connexion, element.banque, instant, hasard, exclus)
			if sonore is not None:
				return Choix(sonore, element, element.banque, occurrence)
	return None


class Ordonnanceur:
	"""Décide, à chaque instant, ce que la sortie audio doit faire.

	La connexion a endossé le rôle de la lecture (machincast.base.connecter) : la grille, les listes et l'airplay
	sont lus ; seule une alerte de silence est écrite, dans le log.
	"""

	def __init__(self, connexion: psycopg.Connection[TupleRow], hasard: Hasard) -> None:
		self.connexion = connexion
		self.hasard = hasard
		self.terminees: set[tuple[int, datetime | None]] = set()
		"""Occurrences terminées plus tôt : liste épuisée, ou plus rien de jouable."""
		self.en_silence = False
		self.exclus: dict[int, datetime] = {}
		"""Sonores écartés, avec l'instant où ils l'ont été."""

	def exclure(self, sonore: int, instant: datetime) -> None:
		"""Écarte un sonore pendant REESSAI_FICHIER_INTROUVABLE, par exemple quand son fichier est introuvable."""
		self.exclus[sonore] = instant

	def _exclus(self, instant: datetime) -> frozenset[int]:
		self.exclus = {s: depuis for s, depuis in self.exclus.items() if instant < depuis + REESSAI_FICHIER_INTROUVABLE}
		return frozenset(self.exclus)

	def decider(self, instant: datetime, en_cours: EnCours | None) -> Decision:
		"""Ce que la sortie audio doit faire à l'instant ; en_cours est le passage qu'elle diffuse, s'il y en a un."""
		with self.connexion.transaction():
			return self._decider(instant, en_cours)

	def _decider(self, instant: datetime, en_cours: EnCours | None) -> Decision:
		evenements = lire_grille(self.connexion)
		couper = False
		while True:
			actif = evenement_actif(evenements, instant, frozenset(self.terminees))
			if en_cours is not None and not couper:
				if actif is None or actif.cle == en_cours.occurrence.cle or not self._commence_apres(actif, en_cours):
					# Même événement, ou fin d'événement sans successeur : le sonore va jusqu'au bout.
					return Decision()
				# Un événement a commencé pendant le sonore en cours : il le coupe net.
				couper = True
			if actif is None:
				return self._silence(couper, None, "aucun événement actif")
			choix = prochain(self.connexion, actif, instant, self.hasard, self._exclus(instant))
			if choix is not None:
				self.en_silence = False
				return Decision(couper=couper, jouer=choix)
			if actif.evenement.priorite is Priorite.FIL_MUSICAL:
				return self._silence(couper, actif, "rien à diffuser dans le fil musical")
			# Liste épuisée, ou plus rien de jouable : l'occurrence se termine, l'événement inférieur reprend.
			self.terminees.add(actif.cle)

	@staticmethod
	def _commence_apres(actif: Occurrence, en_cours: EnCours) -> bool:
		return actif.debut is not None and actif.debut > heure_murale(en_cours.debut)

	def _silence(self, couper: bool, actif: Occurrence | None, message: str) -> Decision:
		if not self.en_silence:
			self.en_silence = True
			consigner(
				self.connexion, "alerte", "silence", message, evenement=None if actif is None else actif.evenement.id
			)
		return Decision(couper=couper, silence=True, occurrence=actif)
