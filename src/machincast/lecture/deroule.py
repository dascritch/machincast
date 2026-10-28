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
- une banque marquée « ne pas répéter » ne passe jamais deux fois de suite
  (https://github.com/dascritch/machincast/issues/63) : si le dernier passage de l'airplay, tous événements
  confondus, a été fourni par elle, l'élément qui la rappelle est sauté, comme une banque vide, et noté dans le log
  (info « élément sauté », une fois par élément et par passage). Si l'occurrence n'a alors plus rien de jouable,
  elle se termine (alerte « événement terminé plus tôt ») ; un fil musical se tait. À l'édition, appels_ignores
  donne les lignes qui seront toujours sautées ;
- une séquence (https://github.com/dascritch/machincast/issues/99) joue ses éléments dans l'ordre, chaque banque
  un seul sonore ; un élément non jouable est sauté, et une séquence dont rien n'est jouable est sautée comme une
  banque vide. Pour les transitions, elle se comporte comme un seul sonore : à la fin de son événement, elle va
  jusqu'au bout (suite de la séquence du dernier passage, _suite), sauf si un événement commence, qui la coupe net
  avec son sonore en cours. Sa position se lit dans l'airplay (sequence_element_id) ; elle ne reprend que si le
  dernier passage de tout l'airplay vient d'elle. Ensuite, la liste reprend à l'élément qui suit la séquence ;
- l'élément suivant se lit dans l'airplay : celui qui suit le dernier élément joué. Pour une émission ou un
  spécial, seuls comptent les passages de l'occurrence en cours, qui commence donc au début de sa liste ; un fil
  musical reprend toujours à l'élément qui suit son dernier joué, d'une occurrence à l'autre (§ 4.2).

Transitions (§ 4.2) :

- le début d'un événement coupe net le sonore en cours, quel qu'il soit ;
- à la fin d'un événement, si aucun autre ne commence, le dernier sonore est joué jusqu'au bout, puis l'événement
  actif (le fil musical) reprend ;
- rien à diffuser : un blanc, et une alerte dans le log, une seule fois par blanc.

Streams (§ 4.7, https://github.com/dascritch/machincast/issues/16) :

- un stream s'arrête au début d'un événement de priorité égale ou supérieure (coupure nette, comme un fichier), ou à
  la fin de son événement : il s'éteint alors pendant son crossfade de fin (eteindre) ;
- un flux tombé suspend son occurrence (suspendre) : tant qu'elle reste active, la liste de l'événement de secours
  du stream la remplace, ou, sans secours, l'événement de priorité inférieure ; la diffusion retente la connexion
  et reprend le stream dès qu'il revient (reprendre). Une autre occurrence active met fin à la suspension.

Interruption manuelle (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228) : sauter après une séquence l'abandonne (abandonner_la_sequence),
et la liste reprend à l'élément qui la suit ; couper l'événement par le fil musical l'abandonne aussi, et termine
chaque occurrence active au-dessus du fil musical (rendre_au_fil_musical), comme une liste épuisée, jusqu'à sa fin
prévue.

Playlist immédiate (https://github.com/dascritch/machincast/issues/228) : les sonores à venir se prévoient dans une
prévision (prevision), où les décisions voient les passages prévus comme joués et ne laissent aucune trace, sauf leurs
tirages au hasard, qui sont engagés : ces sonores seront joués. Quand l'un d'eux devient le prochain sonore, les
occurrences que sa décision a terminées le sont pour de bon (engager).

Un sonore dont le fichier est introuvable au moment de le jouer est écarté (exclure) pendant
REESSAI_FICHIER_INTROUVABLE : il est traité comme non jouable, pour ne pas le réessayer à chaque tour de liste
(https://github.com/dascritch/machincast/issues/88).
"""

import dataclasses
import uuid
from collections.abc import Collection, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import entier_ou_rien
from machincast.hasard import Hasard
from machincast.lecture.banques import a_ne_pas_repeter, choisir_sonore, sonore_jouable
from machincast.lecture.enregistrement import Passage
from machincast.lecture.grille import (
	Evenement,
	Occurrence,
	Priorite,
	evenement_actif,
	evenement_suivant,
	heure_murale,
	lire_evenement,
	lire_grille,
	prochain_changement,
)
from machincast.lecture.historique import EN_BASE, DernierPassage, Historique, HistoriqueEnLecture, HistoriquePrevu
from machincast.lecture.sequences import ElementDeSequence, elements_apres, lire_sequence

REESSAI_FICHIER_INTROUVABLE = timedelta(hours=1)
"""Durée pendant laquelle un sonore au fichier introuvable n'est plus proposé."""


@dataclass(frozen=True)
class Element:
	"""Un élément de la liste d'un événement : un sonore, une banque ou une séquence."""

	id: int
	position: int
	sonore: int | None
	banque: int | None
	sequence: int | None = None


@dataclass(frozen=True)
class Choix:
	"""Sonore à jouer, avec ce que le passage doit noter dans l'airplay."""

	sonore: int
	element: Element
	banque: int | None
	"""Banque qui a fourni le sonore ; None pour un sonore placé directement dans l'événement ou la séquence."""
	occurrence: Occurrence
	ligne: ElementDeSequence | None = None
	"""Élément de la séquence qui a fait jouer le sonore, quand l'élément de l'événement est une séquence."""


@dataclass(frozen=True)
class EnCours:
	"""Passage en cours sur la sortie audio."""

	occurrence: Occurrence
	debut: datetime
	fin_prevue: datetime
	stream: bool = False
	"""Un stream n'a pas de fin connue : il s'éteint à la fin de son événement."""


@dataclass(frozen=True)
class Coupure:
	"""L'événement qui commencera pendant le sonore en cours, et le coupera net
	(https://github.com/dascritch/machincast/issues/169)."""

	instant: datetime
	occurrence: Occurrence


@dataclass(frozen=True)
class Suspension:
	"""Occurrence d'un stream tombé, remplacée le temps de le reconnecter."""

	occurrence: Occurrence
	secours: Evenement | None
	"""Événement de secours du stream ; None : l'événement de priorité inférieure."""


@dataclass(frozen=True)
class Repetition:
	"""Banque « ne pas répéter » qui a fourni le dernier passage : elle ne peut pas fournir le suivant."""

	passage: uuid.UUID
	banque: int
	nom: str


@dataclass(frozen=True)
class Saut:
	"""Élément sauté parce qu'il rappelle la banque « ne pas répéter » qui vient de passer."""

	cle: tuple[str, int]
	"""Table et identifiant de l'élément : un élément d'événement ou de séquence."""
	description: str
	evenement: int


@dataclass(frozen=True)
class Decision:
	couper: bool = False
	"""Couper net le sonore en cours."""
	eteindre: bool = False
	"""Éteindre le stream en cours pendant son crossfade de fin : son événement est fini."""
	jouer: Choix | None = None
	blanc: bool = False
	"""Rien à diffuser : se taire."""
	occurrence: Occurrence | None = None
	"""Événement actif pendant un blanc, pour le signaler."""

	@property
	def continuer(self) -> bool:
		return not ((self.couper) or (self.eteindre) or (self.jouer) or (self.blanc))


def elements_a_essayer(elements: list[Element], dernier: int | None, boucle: bool) -> list[Element]:
	"""Éléments à essayer dans l'ordre, à partir de celui qui suit le dernier joué.

	Avec boucle, la liste fait un tour complet ; sans boucle, elle s'arrête à son dernier élément. Un dernier
	élément inconnu (jamais joué, ou supprimé depuis) fait repartir du début.
	"""
	ids = [e.id for e in elements]
	depart = 0
	if dernier in ids:
		depart = ids.index(dernier) + 1
	if not boucle:
		return elements[depart:]
	return elements[depart:] + elements[:depart]


def _elements(lignes: list[TupleRow]) -> list[Element]:
	return [
		Element(
			id=int(str(identifiant)),
			position=int(str(position)),
			sonore=entier_ou_rien(sonore),
			banque=entier_ou_rien(banque),
			sequence=entier_ou_rien(sequence),
		)
		for identifiant, position, sonore, banque, sequence in lignes
	]


def lire_elements(connexion: psycopg.Connection[TupleRow], evenement: int) -> list[Element]:
	return _elements(
		connexion.execute(
			"SELECT id, position, sonore_id, banque_id, sequence_id FROM evenements_elements WHERE evenement_id = %s"
			" ORDER BY position",
			(evenement,),
		).fetchall()
	)


def lire_element(connexion: psycopg.Connection[TupleRow], element: int) -> Element | None:
	elements = _elements(
		connexion.execute(
			"SELECT id, position, sonore_id, banque_id, sequence_id FROM evenements_elements WHERE id = %s", (element,)
		).fetchall()
	)
	return elements[0] if elements else None


def dernier_element(
	connexion: psycopg.Connection[TupleRow], occurrence: Occurrence, historique: Historique = EN_BASE
) -> int | None:
	"""Dernier élément joué de l'événement : dans l'occurrence en cours, ou depuis toujours pour un fil musical."""
	evenement = occurrence.evenement
	depuis = None
	# Une occurrence avancée a commencé avant son début prévu (https://github.com/dascritch/machincast/issues/257).
	commencee = (occurrence.commencee) or (occurrence.debut)
	if (evenement.priorite not in (Priorite.FIL_MUSICAL, Priorite.SECOURS)) and (commencee is not None):
		depuis = commencee.astimezone()
	return historique.dernier_element(connexion, evenement.id, depuis)


def boucle(occurrence: Occurrence) -> bool:
	"""Une émission ou un spécial sans fin ne boucle pas : il se termine à la fin de sa liste. Un fil musical et un
	événement de secours bouclent toujours."""
	permanents = (Priorite.FIL_MUSICAL, Priorite.SECOURS)
	return (occurrence.evenement.priorite in permanents) or (occurrence.fin is not None)


def prochain(
	connexion: psycopg.Connection[TupleRow],
	occurrence: Occurrence,
	instant: datetime,
	hasard: Hasard,
	exclus: frozenset[int] = frozenset(),
	historique: Historique = EN_BASE,
	interdite: int | None = None,
	sautes: list[Saut] | None = None,
) -> Choix | None:
	"""Prochain sonore de la liste de l'occurrence ; None si rien n'est jouable jusqu'à la fin de la liste.

	exclus : sonores écartés, traités comme non jouables. interdite : banque « ne pas répéter » qui vient de passer ;
	les éléments qui la rappellent sont sautés, et ajoutés à sautes. Une séquence se joue depuis son premier élément
	jouable ; sans élément jouable, elle est sautée.
	"""
	elements = lire_elements(connexion, occurrence.evenement.id)
	dernier = dernier_element(connexion, occurrence, historique)
	for element in elements_a_essayer(elements, dernier, boucle(occurrence)):
		if element.sequence is not None:
			choix = dans_la_sequence(
				connexion, occurrence, element, None, instant, hasard, exclus, historique, interdite, sautes
			)
			if choix is not None:
				return choix
		elif (element.banque is not None) and (element.banque == interdite):
			if sautes is not None:
				description = f"l'élément {element.position} de « {occurrence.evenement.nom} »"
				sautes.append(Saut(("evenements_elements", element.id), description, occurrence.evenement.id))
		else:
			sonore = _fournir(connexion, element.sonore, element.banque, instant, hasard, exclus, historique)
			if sonore is not None:
				return Choix(sonore, element, element.banque, occurrence)
	return None


def dans_la_sequence(
	connexion: psycopg.Connection[TupleRow],
	occurrence: Occurrence,
	element: Element,
	dernier: int | None,
	instant: datetime,
	hasard: Hasard,
	exclus: frozenset[int] = frozenset(),
	historique: Historique = EN_BASE,
	interdite: int | None = None,
	sautes: list[Saut] | None = None,
) -> Choix | None:
	"""Premier sonore jouable de la séquence de l'élément, après son élément dernier (None : depuis le début) ;
	None quand il ne reste rien de jouable dans la séquence. Mêmes règles que prochain."""
	sequence = None
	if element.sequence is not None:
		sequence = lire_sequence(connexion, element.sequence)
	if sequence is None:
		return None
	for ligne in elements_apres(sequence, dernier):
		if (ligne.banque is not None) and (ligne.banque == interdite):
			if sautes is not None:
				description = (
					f"l'élément {ligne.position} de la séquence « {sequence.nom} », dans « {occurrence.evenement.nom} »"
				)
				sautes.append(Saut(("sequences_elements", ligne.id), description, occurrence.evenement.id))
			continue
		sonore = _fournir(connexion, ligne.sonore, ligne.banque, instant, hasard, exclus, historique)
		if sonore is not None:
			return Choix(sonore, element, ligne.banque, occurrence, ligne)
	return None


def _fournir(
	connexion: psycopg.Connection[TupleRow],
	sonore: int | None,
	banque: int | None,
	instant: datetime,
	hasard: Hasard,
	exclus: frozenset[int],
	historique: Historique,
) -> int | None:
	"""Le sonore, s'il est jouable, ou celui que la banque fournit ; None si rien n'est jouable."""
	if sonore is not None:
		jouable = (sonore not in exclus) and (sonore_jouable(connexion, sonore, instant, historique))
		return sonore if jouable else None
	if banque is not None:
		return choisir_sonore(connexion, banque, instant, hasard, exclus, historique)
	return None


class Ordonnanceur:
	"""Décide, à chaque instant, ce que la sortie audio doit faire.

	La connexion a endossé le rôle de la lecture (machincast.base.connecter) : la grille, les listes et l'airplay
	sont lus ; seule une alerte de blanc est écrite, dans le log.
	"""

	def __init__(
		self, connexion: psycopg.Connection[TupleRow], hasard: Hasard, historique: Historique = EN_BASE
	) -> None:
		self.connexion = connexion
		self.hasard = hasard
		self.historique = historique
		self.terminees: set[tuple[int, datetime | None]] = set()
		"""Occurrences terminées plus tôt : liste épuisée, ou plus rien de jouable."""
		self.en_blanc = False
		self.exclus: dict[int, datetime] = {}
		"""Sonores écartés, avec l'instant où ils l'ont été."""
		self.suspension: Suspension | None = None
		"""Stream tombé en attente de reconnexion."""
		self._reservation = False
		"""Décision prise pour réserver le prochain sonore : un blanc n'y est pas encore signalé."""
		self._sauts_notes: tuple[uuid.UUID | None, set[tuple[str, int]]] = (None, set())
		"""Éléments sautés déjà notés dans le log, pour le dernier passage : une seule ligne par élément."""
		self.sequence_abandonnee: uuid.UUID | None = None
		"""Passage dont la séquence a été interrompue : elle ne continue pas après lui."""
		self.avancee: Occurrence | None = None
		"""L'occurrence avancée à la demande (https://github.com/dascritch/machincast/issues/257) : active dès la
		demande, jusqu'à son début prévu, où la grille la retrouve. Retenue en mémoire seulement, comme une occurrence
		terminée plus tôt."""

	def _actif(
		self,
		evenements: list[Evenement],
		instant: datetime,
		terminees: Collection[tuple[int, datetime | None]] | None = None,
	) -> Occurrence | None:
		"""L'occurrence active, l'occurrence avancée comprise ; terminees, sinon celles de l'ordonnanceur."""
		if terminees is None:
			terminees = self.terminees
		actif = evenement_actif(evenements, instant, frozenset(terminees), self.avancee)
		# Après son début prévu, la grille la retrouve, sans l'heure où elle a commencé : celle de l'avance.
		if (actif is not None) and (self.avancee is not None) and (actif.cle == self.avancee.cle):
			return self.avancee
		return actif

	def evenement_suivant(self, instant: datetime) -> Occurrence | None:
		"""L'événement suivant, après l'occurrence en cours, avancée comprise (grille.evenement_suivant)."""
		with self.connexion.transaction():
			evenements = lire_grille(self.connexion)
		return evenement_suivant(evenements, instant, frozenset(self.terminees), self.avancee)

	def avancer(self, instant: datetime) -> Occurrence | None:
		"""L'événement suivant commence aussitôt (https://github.com/dascritch/machincast/issues/257) ; None sans lui.
		Une séquence en cours ne continue pas : l'occurrence avancée a commencé après son dernier passage (_suite)."""
		suivant = self.evenement_suivant(instant)
		if suivant is None:
			return None
		self.avancee = dataclasses.replace(suivant, commencee=heure_murale(instant))
		return self.avancee

	def reserver(self, instant: datetime) -> Choix | None:
		"""Prochain sonore, choisi dès le début du sonore en cours (https://github.com/dascritch/machincast/issues/20).

		Comme une décision sans sonore en cours, mais sans alerte de blanc : le blanc ne viendra qu'à la fin du
		sonore en cours, et sera signalé alors.
		"""
		self._reservation = True
		try:
			return self.decider(instant, None).jouer
		finally:
			self._reservation = False

	def coupure(self, en_cours: EnCours, instant: datetime, horizon: datetime) -> Coupure | None:
		"""Le premier événement qui commencera après l'instant et avant l'horizon, et coupera net le sonore en cours,
		comme le décidera decider ; None si le sonore va jusqu'à l'horizon. Rien n'est changé.

		Un événement qui commence n'est une coupure que si la décision prise à son début coupe : un événement sans
		rien de jouable laisse l'antenne à celui de priorité inférieure, qui peut être celui du sonore en cours
		(https://github.com/dascritch/machincast/issues/253). La coupure nomme l'occurrence qui jouera alors."""
		with self.connexion.transaction():
			evenements = lire_grille(self.connexion)
		terminees = frozenset(self.terminees)
		moment = prochain_changement(evenements, instant)
		while (moment is not None) and (moment < horizon):
			actif = self._actif(evenements, moment, terminees)
			if (
				(actif is not None)
				and (actif.cle != en_cours.occurrence.cle)
				and (self._commence_apres(actif, en_cours))
			):
				with self._sans_trace():
					self._reservation = True
					decision = self.decider(moment, en_cours)
				if decision.couper:
					return Coupure(moment, self._occurrence_de(decision, actif))
			moment = prochain_changement(evenements, moment)
		return None

	@staticmethod
	def _occurrence_de(decision: Decision, actif: Occurrence) -> Occurrence:
		"""L'occurrence qui prend l'antenne à la coupure : celle du sonore qu'elle joue, ou celle qui s'y tait."""
		if decision.jouer is not None:
			return decision.jouer.occurrence
		return (decision.occurrence) or (actif)

	def anticiper(self, instant: datetime) -> Choix | None:
		"""Le sonore que réserverait la décision à un instant à venir, sans en garder de trace : rien n'est consigné,
		aucune occurrence n'est terminée, aucune suspension levée, aucun saut noté, aucun sonore écarté n'est oublié,
		et le hasard n'avance pas : la décision prise à cet instant tirera le même sonore, si rien n'a changé
		(https://github.com/dascritch/machincast/issues/169)."""
		with self._sans_trace():
			return self.reserver(instant)

	@contextmanager
	def _sans_trace(self) -> Iterator[None]:
		"""Le temps d'une décision anticipée : rien n'est consigné, et à la sortie, l'état de l'ordonnanceur et le
		hasard sont rétablis."""
		# Une décision note les sauts d'un autre passage dans un nouvel ensemble : garder l'ancien suffit.
		sauts = self._sauts_notes
		etat = (
			set(self.terminees),
			self.en_blanc,
			self.suspension,
			dict(self.exclus),
			self.historique,
			self._reservation,
		)
		tirages = self.hasard.getstate()
		self.historique = HistoriqueEnLecture(self.historique)
		try:
			yield
		finally:
			self.terminees, self.en_blanc, self.suspension, self.exclus, self.historique, self._reservation = etat
			self.hasard.setstate(tirages)
			self._sauts_notes = sauts

	@contextmanager
	def prevision(
		self, prevus: list[Passage], terminees: Collection[tuple[int, datetime | None]] = ()
	) -> Iterator[HistoriquePrevu]:
		"""Le temps de prévoir les sonores à venir (https://github.com/dascritch/machincast/issues/228) : les décisions
		voient les passages prévus, du plus ancien au plus récent, comme joués, et les occurrences terminées données
		comme terminées. Rien n'est consigné ; à la sortie, l'état de l'ordonnanceur est rétabli, sauf le hasard : les
		tirages des sonores prévus sont engagés. La liste des passages prévus peut s'allonger dans la prévision. Le
		contexte donne l'historique de la prévision, qui garde ce que les décisions consigneraient."""
		sauts = self._sauts_notes
		etat = (set(self.terminees), self.en_blanc, self.suspension, dict(self.exclus), self.historique)
		self.terminees |= set(terminees)
		historique = HistoriquePrevu(self.historique, prevus)
		self.historique = historique
		try:
			yield historique
		finally:
			self.terminees, self.en_blanc, self.suspension, self.exclus, self.historique = etat
			self._sauts_notes = sauts

	def engager(self, terminees: Collection[tuple[int, datetime | None]]) -> None:
		"""Un sonore prévu devient le prochain : les occurrences que sa décision a terminées le sont pour de bon."""
		self.terminees |= set(terminees)

	def valider(self, choix: Choix, instant: datetime) -> bool:
		"""Le sonore réservé peut-il encore être joué : son occurrence est toujours active et il est jouable."""
		with self.connexion.transaction():
			evenements = lire_grille(self.connexion)
			actif = self._remplacer(evenements, instant, self._actif(evenements, instant))
			if (actif is None) or (actif.cle != choix.occurrence.cle) or (choix.sonore in self._exclus(instant)):
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
		if (self.suspension is not None) and (self.suspension.secours is not None):
			self.terminees.discard(_occurrence_de_secours(self.suspension.secours).cle)
		self.suspension = None

	def abandonner_la_sequence(self, passage: uuid.UUID) -> None:
		"""La séquence du passage est interrompue : la liste de son événement reprend à l'élément qui la suit."""
		self.sequence_abandonnee = passage

	def rendre_au_fil_musical(self, instant: datetime) -> list[Occurrence]:
		"""L'événement est coupé par le fil musical (https://github.com/dascritch/machincast/issues/228) : chaque
		occurrence active au-dessus du fil musical est terminée, comme une liste épuisée, jusqu'à sa fin prévue, et
		un stream tombé n'est plus reconnecté. Renvoie les occurrences terminées, de la plus prioritaire à la moins
		prioritaire."""
		with self.connexion.transaction():
			evenements = lire_grille(self.connexion)
		terminees = []
		suspension = self.suspension
		if (suspension is not None) and (suspension.occurrence.evenement.priorite is not Priorite.FIL_MUSICAL):
			self.terminees.add(suspension.occurrence.cle)
			terminees.append(suspension.occurrence)
			self._lever_suspension()
		while True:
			actif = self._remplacer(evenements, instant, self._actif(evenements, instant))
			if (actif is None) or (actif.evenement.priorite in (Priorite.FIL_MUSICAL, Priorite.SECOURS)):
				return terminees
			self.terminees.add(actif.cle)
			terminees.append(actif)

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

	def _repetition(self, dernier: DernierPassage | None) -> Repetition | None:
		"""La banque « ne pas répéter » qui a fourni le dernier passage, s'il y en a une."""
		if (dernier is None) or (dernier.banque is None):
			return None
		nom = a_ne_pas_repeter(self.connexion, dernier.banque)
		if nom is None:
			return None
		return Repetition(dernier.id, dernier.banque, nom)

	def _noter_les_sauts(self, repetition: Repetition, sautes: list[Saut], instant: datetime) -> None:
		passage, notes = self._sauts_notes
		if passage != repetition.passage:
			notes = set()
			self._sauts_notes = (repetition.passage, notes)
		for saut in sautes:
			if saut.cle in notes:
				continue
			notes.add(saut.cle)
			self.historique.consigner(
				self.connexion,
				"info",
				"élément sauté",
				f"banque « {repetition.nom} » à ne pas répéter : elle vient de passer, {saut.description} est sauté",
				instant,
				banque=repetition.banque,
				evenement=saut.evenement,
			)

	def _decider(self, instant: datetime, en_cours: EnCours | None) -> Decision:
		evenements = lire_grille(self.connexion)
		couper = eteindre = False
		while True:
			actif = self._remplacer(evenements, instant, self._actif(evenements, instant))
			if (en_cours is not None) and (not ((couper) or (eteindre))):
				if (actif is not None) and (actif.cle == en_cours.occurrence.cle):
					return Decision()
				if (actif is not None) and (self._commence_apres(actif, en_cours)):
					# Un événement a commencé pendant le sonore en cours : il le coupe net.
					couper = True
				elif en_cours.stream:
					# Fin de l'événement du stream : il s'éteint, l'événement actif reprend.
					eteindre = True
				else:
					# Fin d'événement sans successeur : le sonore va jusqu'au bout.
					return Decision()
			# Lu seulement quand il faut choisir : pas à chaque pas d'un sonore qui continue.
			dernier = self.historique.dernier_passage(self.connexion)
			repetition = self._repetition(dernier)
			interdite = None if repetition is None else repetition.banque
			sautes: list[Saut] = []
			# D'abord la suite de la séquence en cours, s'il en reste ; sinon, l'élément suivant de l'événement actif.
			choix = self._suite(instant, actif, dernier, interdite, sautes)
			if (choix is None) and (actif is not None):
				exclus = self._exclus(instant)
				choix = prochain(
					self.connexion, actif, instant, self.hasard, exclus, self.historique, interdite, sautes
				)
			if repetition is not None:
				self._noter_les_sauts(repetition, sautes, instant)
			if choix is not None:
				self.en_blanc = False
				return Decision(couper=couper, eteindre=eteindre, jouer=choix)
			if actif is None:
				return self._blanc(instant, couper, eteindre, None, "aucun événement actif")
			if actif.evenement.priorite is Priorite.FIL_MUSICAL:
				return self._blanc(instant, couper, eteindre, actif, "rien à diffuser dans le fil musical")
			# Liste épuisée, ou plus rien de jouable : l'occurrence se termine, l'événement inférieur reprend. Le sonore
			# en cours est jugé de nouveau face à lui : il continue si c'est son événement
			# (https://github.com/dascritch/machincast/issues/253).
			self.terminees.add(actif.cle)
			couper = eteindre = False
			if (repetition is not None) and (any(saut.evenement == actif.evenement.id for saut in sautes)):
				self.historique.consigner(
					self.connexion,
					"alerte",
					"événement terminé plus tôt",
					f"« {actif.evenement.nom} » : plus rien de jouable une fois la banque « {repetition.nom} » sautée",
					instant,
					banque=repetition.banque,
					evenement=actif.evenement.id,
				)

	def _suite(
		self,
		instant: datetime,
		actif: Occurrence | None,
		dernier: DernierPassage | None,
		interdite: int | None,
		sautes: list[Saut],
	) -> Choix | None:
		"""Suite de la séquence du dernier passage, tant qu'il lui reste un élément jouable.

		Une séquence se comporte comme un seul sonore : elle va jusqu'au bout, même son événement terminé, sauf si un
		événement a commencé depuis le dernier passage, qui l'a coupée. Pendant la suspension d'un stream, elle cède la
		place au secours.
		"""
		if (
			(dernier is None)
			or (dernier.sequence_element is None)
			or (dernier.element is None)
			or (self.suspension is not None)
			or (dernier.id == self.sequence_abandonnee)
		):
			return None
		if (actif is not None) and (dernier.debut is not None) and (self._a_commence(actif, dernier.debut)):
			return None
		element = lire_element(self.connexion, dernier.element)
		if element is None:
			return None
		occurrence = None
		if (actif is not None) and (actif.evenement.id == dernier.evenement):
			occurrence = actif
		elif dernier.evenement is not None:
			# Son événement est fini : la séquence va jusqu'au bout en son nom.
			evenement = lire_evenement(self.connexion, dernier.evenement)
			if evenement is not None:
				occurrence = Occurrence(evenement, None, None)
		if occurrence is None:
			return None
		return dans_la_sequence(
			self.connexion,
			occurrence,
			element,
			dernier.sequence_element,
			instant,
			self.hasard,
			self._exclus(instant),
			self.historique,
			interdite,
			sautes,
		)

	def _remplacer(self, evenements: list[Evenement], instant: datetime, actif: Occurrence | None) -> Occurrence | None:
		"""Pendant la suspension d'un stream, son occurrence cède la place à son secours ; ailleurs, la suspension
		prend fin."""
		suspension = self.suspension
		if suspension is None:
			return actif
		if (actif is None) or (actif.cle != suspension.occurrence.cle):
			self._lever_suspension()
			return actif
		if suspension.secours is not None:
			secours = _occurrence_de_secours(suspension.secours)
			if secours.cle not in self.terminees:
				return secours
		# Sans secours, ou secours sans rien de jouable : l'événement de priorité inférieure.
		return self._actif(evenements, instant, self.terminees | {suspension.occurrence.cle})

	@staticmethod
	def _commence_apres(actif: Occurrence, en_cours: EnCours) -> bool:
		return Ordonnanceur._a_commence(actif, en_cours.debut)

	@staticmethod
	def _a_commence(actif: Occurrence, depuis: datetime) -> bool:
		"""L'occurrence a-t-elle commencé après cet instant ?"""
		return (actif.debut is not None) and (actif.debut > heure_murale(depuis))

	def _blanc(
		self, instant: datetime, couper: bool, eteindre: bool, actif: Occurrence | None, message: str
	) -> Decision:
		if self._reservation:
			return Decision(couper=couper, eteindre=eteindre, blanc=True, occurrence=actif)
		if not self.en_blanc:
			self.en_blanc = True
			evenement = None if actif is None else actif.evenement.id
			self.historique.consigner(self.connexion, "alerte", "blanc", message, instant, evenement=evenement)
		return Decision(couper=couper, eteindre=eteindre, blanc=True, occurrence=actif)


def _occurrence_de_secours(evenement: Evenement) -> Occurrence:
	"""Un événement de secours n'a pas de dates : une seule occurrence, sans début ni fin."""
	return Occurrence(evenement, None, None)


def appels_ignores(banques: Sequence[int | None], ne_pas_repeter: Collection[int], boucle: bool) -> list[int]:
	"""Lignes de la liste d'un événement, numérotées dès 1, qui rappellent la banque « ne pas répéter » de la ligne
	précédente : elles seront toujours sautées à la diffusion. Pour un événement qui boucle, la première ligne suit la
	dernière.

	banques : la banque de chaque ligne, None pour un sonore. Pour l'avertissement de l'interface à l'édition d'une
	séquence (https://github.com/dascritch/machincast/issues/112), qui n'empêche pas d'enregistrer.
	"""
	return appels_ignores_aux_bords([(banque, banque) for banque in banques], ne_pas_repeter, boucle)


def appels_ignores_aux_bords(
	bords: Sequence[tuple[int | None, int | None]], ne_pas_repeter: Collection[int], boucle: bool
) -> list[int]:
	"""Comme appels_ignores, quand une ligne commence et finit par des banques différentes : une séquence
	(https://github.com/dascritch/machincast/issues/32). Chaque ligne donne sa première banque, celle que la ligne
	précédente peut avoir déjà fait passer, et sa dernière, que la ligne suivante peut rappeler ; None pour un
	sonore.
	"""
	signalees = []
	for indice, (premiere, _derniere) in enumerate(bords):
		if (premiere not in ne_pas_repeter) or ((indice == 0) and (not boucle)):
			continue
		if bords[indice - 1][1] == premiere:
			signalees.append(indice + 1)
	return signalees
