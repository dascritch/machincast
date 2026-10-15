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

Streams (§ 4.7, https://github.com/dascritch/machincast/issues/16) :

- un stream s'arrête au début d'un événement de priorité égale ou supérieure (coupure nette, comme un fichier), ou à
  la fin de son événement : il s'éteint alors pendant son crossfade de fin (eteindre) ;
- un flux tombé suspend son occurrence (suspendre) : tant qu'elle reste active, la liste de l'événement de secours
  du stream la remplace, ou, sans secours, l'événement de priorité inférieure ; la diffusion retente la connexion
  et reprend le stream dès qu'il revient (reprendre). Une autre occurrence active met fin à la suspension.

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
from machincast.lecture.grille import (
	Evenement,
	Occurrence,
	Priorite,
	evenement_actif,
	heure_murale,
	lire_evenement,
	lire_grille,
)
from machincast.lecture.historique import EN_BASE, Historique

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
	stream: bool = False
	"""Un stream n'a pas de fin connue : il s'éteint à la fin de son événement."""


@dataclass(frozen=True)
class Suspension:
	"""Occurrence d'un stream tombé, remplacée le temps de le reconnecter."""

	occurrence: Occurrence
	secours: Evenement | None
	"""Événement de secours du stream ; None : l'événement de priorité inférieure."""


@dataclass(frozen=True)
class Decision:
	couper: bool = False
	"""Couper net le sonore en cours."""
	eteindre: bool = False
	"""Éteindre le stream en cours pendant son crossfade de fin : son événement est fini."""
	jouer: Choix | None = None
	silence: bool = False
	"""Rien à diffuser : se taire."""
	occurrence: Occurrence | None = None
	"""Événement actif pendant un silence, pour le signaler."""

	@property
	def continuer(self) -> bool:
		return not (self.couper or self.eteindre or self.jouer or self.silence)


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


def dernier_element(
	connexion: psycopg.Connection[TupleRow], occurrence: Occurrence, historique: Historique = EN_BASE
) -> int | None:
	"""Dernier élément joué de l'événement : dans l'occurrence en cours, ou depuis toujours pour un fil musical."""
	evenement = occurrence.evenement
	depuis = None
	if evenement.priorite not in (Priorite.FIL_MUSICAL, Priorite.SECOURS) and occurrence.debut is not None:
		depuis = occurrence.debut.astimezone()
	return historique.dernier_element(connexion, evenement.id, depuis)


def boucle(occurrence: Occurrence) -> bool:
	"""Une émission ou un spécial sans fin ne boucle pas : il se termine à la fin de sa liste. Un fil musical et un
	événement de secours bouclent toujours."""
	permanents = (Priorite.FIL_MUSICAL, Priorite.SECOURS)
	return occurrence.evenement.priorite in permanents or occurrence.fin is not None


def prochain(
	connexion: psycopg.Connection[TupleRow],
	occurrence: Occurrence,
	instant: datetime,
	hasard: Hasard,
	exclus: frozenset[int] = frozenset(),
	historique: Historique = EN_BASE,
) -> Choix | None:
	"""Prochain sonore de la liste de l'occurrence ; None si rien n'est jouable jusqu'à la fin de la liste.

	exclus : sonores écartés, traités comme non jouables.
	"""
	elements = lire_elements(connexion, occurrence.evenement.id)
	dernier = dernier_element(connexion, occurrence, historique)
	for element in elements_a_essayer(elements, dernier, boucle(occurrence)):
		if element.sonore is not None:
			if element.sonore not in exclus and sonore_jouable(connexion, element.sonore, instant, historique):
				return Choix(element.sonore, element, None, occurrence)
		elif element.banque is not None:
			sonore = choisir_sonore(connexion, element.banque, instant, hasard, exclus, historique)
			if sonore is not None:
				return Choix(sonore, element, element.banque, occurrence)
	return None


class Ordonnanceur:
	"""Décide, à chaque instant, ce que la sortie audio doit faire.

	La connexion a endossé le rôle de la lecture (machincast.base.connecter) : la grille, les listes et l'airplay
	sont lus ; seule une alerte de silence est écrite, dans le log.
	"""

	def __init__(
		self, connexion: psycopg.Connection[TupleRow], hasard: Hasard, historique: Historique = EN_BASE
	) -> None:
		self.connexion = connexion
		self.hasard = hasard
		self.historique = historique
		self.terminees: set[tuple[int, datetime | None]] = set()
		"""Occurrences terminées plus tôt : liste épuisée, ou plus rien de jouable."""
		self.en_silence = False
		self.exclus: dict[int, datetime] = {}
		"""Sonores écartés, avec l'instant où ils l'ont été."""
		self.suspension: Suspension | None = None
		"""Stream tombé en attente de reconnexion."""
		self._reservation = False
		"""Décision prise pour réserver le prochain sonore : un silence n'y est pas encore signalé."""

	def reserver(self, instant: datetime) -> Choix | None:
		"""Prochain sonore, choisi dès le début du sonore en cours (https://github.com/dascritch/machincast/issues/20).

		Comme une décision sans sonore en cours, mais sans alerte de silence : le silence ne viendra qu'à la fin du
		sonore en cours, et sera signalé alors.
		"""
		self._reservation = True
		try:
			return self.decider(instant, None).jouer
		finally:
			self._reservation = False

	def valider(self, choix: Choix, instant: datetime) -> bool:
		"""Le sonore réservé peut-il encore être joué : son occurrence est toujours active et il est jouable."""
		with self.connexion.transaction():
			evenements = lire_grille(self.connexion)
			actif = evenement_actif(evenements, instant, frozenset(self.terminees))
			actif = self._remplacer(evenements, instant, actif)
			if actif is None or actif.cle != choix.occurrence.cle or choix.sonore in self._exclus(instant):
				return False
			return sonore_jouable(self.connexion, choix.sonore, instant, self.historique)

	def suspendre(self, occurrence: Occurrence, secours: int | None) -> None:
		"""Le stream de l'occurrence est tombé : la remplacer, tant qu'elle reste active, par l'événement de secours,
		ou sans secours par l'événement de priorité inférieure."""
		evenement = None
		if secours is not None:
			with self.connexion.transaction():
				evenement = lire_evenement(self.connexion, secours)
		self.suspension = Suspension(occurrence, evenement)

	def reprendre(self) -> None:
		"""Le stream est revenu : son occurrence reprend l'antenne."""
		self._lever_suspension()

	def _lever_suspension(self) -> None:
		if self.suspension is not None and self.suspension.secours is not None:
			self.terminees.discard(_occurrence_de_secours(self.suspension.secours).cle)
		self.suspension = None

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
		couper = eteindre = False
		while True:
			actif = self._remplacer(
				evenements, instant, evenement_actif(evenements, instant, frozenset(self.terminees))
			)
			if en_cours is not None and not (couper or eteindre):
				if actif is not None and actif.cle == en_cours.occurrence.cle:
					return Decision()
				if actif is not None and self._commence_apres(actif, en_cours):
					# Un événement a commencé pendant le sonore en cours : il le coupe net.
					couper = True
				elif en_cours.stream:
					# Fin de l'événement du stream : il s'éteint, l'événement actif reprend.
					eteindre = True
				else:
					# Fin d'événement sans successeur : le sonore va jusqu'au bout.
					return Decision()
			if actif is None:
				return self._silence(instant, couper, eteindre, None, "aucun événement actif")
			choix = prochain(self.connexion, actif, instant, self.hasard, self._exclus(instant), self.historique)
			if choix is not None:
				self.en_silence = False
				return Decision(couper=couper, eteindre=eteindre, jouer=choix)
			if actif.evenement.priorite is Priorite.FIL_MUSICAL:
				return self._silence(instant, couper, eteindre, actif, "rien à diffuser dans le fil musical")
			# Liste épuisée, ou plus rien de jouable : l'occurrence se termine, l'événement inférieur reprend.
			self.terminees.add(actif.cle)

	def _remplacer(self, evenements: list[Evenement], instant: datetime, actif: Occurrence | None) -> Occurrence | None:
		"""Pendant la suspension d'un stream, son occurrence cède la place à son secours ; ailleurs, la suspension
		prend fin."""
		suspension = self.suspension
		if suspension is None:
			return actif
		if actif is None or actif.cle != suspension.occurrence.cle:
			self._lever_suspension()
			return actif
		if suspension.secours is not None:
			secours = _occurrence_de_secours(suspension.secours)
			if secours.cle not in self.terminees:
				return secours
		# Sans secours, ou secours sans rien de jouable : l'événement de priorité inférieure.
		return evenement_actif(evenements, instant, frozenset(self.terminees | {suspension.occurrence.cle}))

	@staticmethod
	def _commence_apres(actif: Occurrence, en_cours: EnCours) -> bool:
		return actif.debut is not None and actif.debut > heure_murale(en_cours.debut)

	def _silence(
		self, instant: datetime, couper: bool, eteindre: bool, actif: Occurrence | None, message: str
	) -> Decision:
		if self._reservation:
			return Decision(couper=couper, eteindre=eteindre, silence=True, occurrence=actif)
		if not self.en_silence:
			self.en_silence = True
			evenement = None if actif is None else actif.evenement.id
			self.historique.consigner(self.connexion, "alerte", "silence", message, instant, evenement=evenement)
		return Decision(couper=couper, eteindre=eteindre, silence=True, occurrence=actif)


def _occurrence_de_secours(evenement: Evenement) -> Occurrence:
	"""Un événement de secours n'a pas de dates : une seule occurrence, sans début ni fin."""
	return Occurrence(evenement, None, None)
