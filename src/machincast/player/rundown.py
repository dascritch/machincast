"""Déroulé de la liste de lecture et transitions entre événements (https://github.com/dascritch/machincast/issues/14).

Spec § 4.2 et § 4.3. L'ordonnanceur décide, à chaque instant, ce que la sortie audio doit faire : continuer le
sonore en cours, le couper net, jouer un nouveau sonore, ou se taire. Il ne joue rien lui-même (moteur audio :
https://github.com/dascritch/machincast/issues/15) et n'écrit pas l'airplay
(https://github.com/dascritch/machincast/issues/17) : il lit l'airplay pour savoir où en est chaque liste.

Liste de lecture d'un événement (§ 4.3) :

- les éléments se jouent dans l'ordre de leur position ; un même élément peut revenir plusieurs fois ;
- un élément banque fait jouer un seul sonore de la banque (machincast.player.banks) ;
- une banque sans sonore jouable, ou un sonore qui n'est pas jouable, est sauté : on passe à l'élément suivant ;
- arrivée au bout, la liste reprend au début, sauf pour une émission ou un spécial sans fin, qui se termine alors
  pour cette occurrence : l'événement de priorité inférieure reprend la main ;
- une émission ou un spécial dont plus rien n'est jouable se termine de même ;
- une banque marquée « ne pas répéter » ne passe jamais deux fois de suite
  (https://github.com/dascritch/machincast/issues/63) : si le dernier passage de l'airplay, tous événements
  confondus, a été fourni par elle, l'élément qui la rappelle est sauté, comme une banque vide, et noté dans le log
  (info « élément sauté », une fois par élément et par passage). Si l'occurrence n'a alors plus rien de jouable,
  elle se termine (alerte « événement terminé plus tôt ») ; un fil musical se tait. À l'édition, ignored_calls
  donne les lignes qui seront toujours sautées ;
- une séquence (https://github.com/dascritch/machincast/issues/99) joue ses éléments dans l'ordre, chaque banque
  un seul sonore ; un élément non jouable est sauté, et une séquence dont rien n'est jouable est sautée comme une
  banque vide. Pour les transitions, elle se comporte comme un seul sonore : à la fin de son événement, elle va
  jusqu'au bout (suite de la séquence du dernier passage, _suite), sauf si un événement commence, qui la coupe net
  avec son sonore en cours. Sa position se lit dans l'airplay (sequence_item_id) ; elle ne reprend que si le
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
https://github.com/dascritch/machincast/issues/228) : sauter après une séquence l'abandonne (abandon_sequence),
et la liste reprend à l'élément qui la suit ; couper l'événement par le fil musical l'abandonne aussi, et termine
chaque occurrence active au-dessus du fil musical (return_to_background_programming), comme une liste épuisée, jusqu'à
sa fin
prévue.

Coupure par le secours ou par un feed (https://github.com/dascritch/machincast/issues/323, cut_by) : comme pour le
fil musical, chaque occurrence active au-dessus du fil musical est terminée ; puis un remplacement (Remplacement) tient
l'antenne, au-dessus de la grille, jusqu'à la fin prévue de l'événement coupé, ou, sans fin connue ou sous le fil
musical, jusqu'au début de l'événement suivant. Le secours y joue sa liste ; un feed, le stream qui le suit, au nom de
l'événement coupé (ELEMENT_HORS_LISTE : le passage ne vient d'aucun élément de liste). Un secours qui n'a plus rien de
jouable, un feed dont le stream ne l'est plus ou qui tombe (suspendre), rendent l'antenne à la grille : sous elle, le
fil musical. Une coupure par le fil musical, ou une avance, met fin au remplacement.

Playlist immédiate (https://github.com/dascritch/machincast/issues/228) : les sonores à venir se prévoient dans une
prévision (prevision), où les décisions voient les passages prévus comme joués et ne laissent aucune trace, sauf leurs
tirages au hasard, qui sont engagés : ces sonores seront joués. Quand l'un d'eux devient le prochain sonore, les
occurrences que sa décision a terminées le sont pour de bon (engager).

Prêter son nom (https://github.com/dascritch/machincast/issues/399, END_LEND_NAME) : une émission ou un spécial dont la
liste est épuisée, ou vide dès son début, se termine comme les autres, mais reste au-dessus de la grille jusqu'à sa fin
prévue : l'événement en dessous, le plus souvent le fil musical, y joue sa liste sous son nom (Choice.lender,
Decision.lender). Ce prêt se déduit de la grille et des occurrences terminées (_lender) : il survit à une prévision et
se retrouve après un redémarrage. Une coupure par le fil musical, par le secours ou par un feed y met fin.

Un sonore dont le fichier est introuvable au moment de le jouer est écarté (exclure) pendant
NOT_FOUND_FILE_RETRY : il est traité comme non jouable, pour ne pas le réessayer à chaque tour de liste
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

from machincast.conversion import integer_or_none
from machincast.i18n import N_, _
from machincast.player.banks import choose_sound, has_no_repeat, playable_sound
from machincast.player.grid import (
	Event,
	Occurrence,
	Priority,
	active_event,
	following_event,
	next_change,
	read_event,
	read_grid,
	wall_hour,
)
from machincast.player.history import IN_DATABASE, History, HistoryInPlayback, LastPlay, PlannedHistory
from machincast.player.saving import Play
from machincast.player.sequences import SequenceItem, items_after, read_sequence
from machincast.randomness import Randomness

NOT_FOUND_FILE_RETRY = timedelta(hours=1)
"""Durée pendant laquelle un sonore au fichier introuvable n'est plus proposé."""
OUTSIDE_LIST = 0
"""Identifiant de l'élément d'un passage qui ne vient d'aucune liste : le stream d'un feed qui coupe l'antenne."""
END_REPLAY = "replay"
END_TO_BACKGROUND = "background_programming"
END_TO_FALLBACK = "fallback"
END_LEND_NAME = "lend_name"
"""Les valeurs de events.end_of_list (https://github.com/dascritch/machincast/issues/350,
https://github.com/dascritch/machincast/issues/399)."""


@dataclass(frozen=True)
class Item:
	"""Un élément de la liste d'un événement : un sonore, une banque ou une séquence."""

	id: int
	position: int
	sound: int | None
	bank: int | None
	sequence: int | None = None


@dataclass(frozen=True)
class Choice:
	"""Sonore à jouer, avec ce que le passage doit noter dans l'airplay."""

	sound: int
	item: Item
	bank: int | None
	"""Banque qui a fourni le sonore ; None pour un sonore placé directement dans l'événement ou la séquence."""
	occurrence: Occurrence
	line: SequenceItem | None = None
	"""Élément de la séquence qui a fait jouer le sonore, quand l'élément de l'événement est une séquence."""
	lender: Occurrence | None = None
	"""L'occurrence au nom de qui le sonore passe, quand elle prête son nom à son événement
	(https://github.com/dascritch/machincast/issues/399)."""


@dataclass(frozen=True)
class Ongoing:
	"""Passage en cours sur la sortie audio."""

	occurrence: Occurrence
	start: datetime
	planned_end: datetime
	stream: bool = False
	"""Un stream n'a pas de fin connue : il s'éteint à la fin de son événement."""


@dataclass(frozen=True)
class Cutoff:
	"""L'événement qui commencera pendant le sonore en cours, et le coupera net
	(https://github.com/dascritch/machincast/issues/169)."""

	instant: datetime
	occurrence: Occurrence


@dataclass(frozen=True)
class Suspension:
	"""Occurrence d'un stream tombé, remplacée le temps de le reconnecter."""

	occurrence: Occurrence
	fallback: Event | None
	"""Événement de secours du stream ; None : l'événement de priorité inférieure."""


@dataclass(frozen=True)
class Replacement:
	"""Ce qui tient l'antenne à la place de la grille après une coupure par le secours ou par un feed
	(https://github.com/dascritch/machincast/issues/323)."""

	occurrence: Occurrence
	"""Pour le secours, son occurrence ; pour un feed, l'occurrence coupée, au nom de qui le stream passe."""
	until: datetime | None
	"""En heure murale ; None, sans événement suivant : jusqu'à une autre coupure."""
	stream: int | None = None
	"""Pour un feed : le stream qui le suit."""


@dataclass(frozen=True)
class Repetition:
	"""Banque « ne pas répéter » qui a fourni le dernier passage : elle ne peut pas fournir le suivant."""

	play: uuid.UUID
	bank: int
	name: str


@dataclass(frozen=True)
class Skip:
	"""Élément sauté parce qu'il rappelle la banque « ne pas répéter » qui vient de passer."""

	key: tuple[str, int]
	"""Table et identifiant de l'élément : un élément d'événement ou de séquence."""
	description: str
	event: int


@dataclass(frozen=True)
class Decision:
	cut: bool = False
	"""Couper net le sonore en cours."""
	switch_off: bool = False
	"""Éteindre le stream en cours pendant son crossfade de fin : son événement est fini."""
	play: Choice | None = None
	dead_air: bool = False
	"""Rien à diffuser : se taire."""
	occurrence: Occurrence | None = None
	"""Événement actif pendant un blanc, pour le signaler."""
	lender: Occurrence | None = None
	"""L'occurrence qui prête son nom à l'antenne à cet instant, sonore en cours compris
	(https://github.com/dascritch/machincast/issues/399)."""

	@property
	def continue_(self) -> bool:
		return not ((self.cut) or (self.switch_off) or (self.play) or (self.dead_air))


def items_to_try(items: list[Item], last: int | None, loop: bool) -> list[Item]:
	"""Éléments à essayer dans l'ordre, à partir de celui qui suit le dernier joué.

	Avec boucle, la liste fait un tour complet ; sans boucle, elle s'arrête à son dernier élément. Un dernier
	élément inconnu (jamais joué, ou supprimé depuis) fait repartir du début.
	"""
	ids = [e.id for e in items]
	departure = 0
	if last in ids:
		departure = ids.index(last) + 1
	if not loop:
		return items[departure:]
	return items[departure:] + items[:departure]


def _items(lines: list[TupleRow]) -> list[Item]:
	return [
		Item(
			id=int(str(identifier)),
			position=int(str(position)),
			sound=integer_or_none(sound),
			bank=integer_or_none(bank),
			sequence=integer_or_none(sequence),
		)
		for identifier, position, sound, bank, sequence in lines
	]


def read_items(connection: psycopg.Connection[TupleRow], event: int) -> list[Item]:
	return _items(
		connection.execute(
			"SELECT id, position, sound_id, bank_id, sequence_id FROM event_items WHERE event_id = %s"
			" ORDER BY position",
			(event,),
		).fetchall()
	)


def read_item(connection: psycopg.Connection[TupleRow], item: int) -> Item | None:
	items = _items(
		connection.execute(
			"SELECT id, position, sound_id, bank_id, sequence_id FROM event_items WHERE id = %s", (item,)
		).fetchall()
	)
	if items:
		return items[0]
	return None


def last_item(
	connection: psycopg.Connection[TupleRow], occurrence: Occurrence, history: History = IN_DATABASE
) -> int | None:
	"""Dernier élément joué de l'événement : dans l'occurrence en cours, ou depuis toujours pour un fil musical."""
	event = occurrence.event
	since = None
	# Une occurrence avancée a commencé avant son début prévu (https://github.com/dascritch/machincast/issues/257).
	started = (occurrence.started) or (occurrence.start)
	if (event.priority not in (Priority.BACKGROUND_PROGRAMMING, Priority.FALLBACK)) and (started is not None):
		since = started.astimezone()
	return history.last_item(connection, event.id, since)


def loop(occurrence: Occurrence) -> bool:
	"""Une émission ou un spécial sans fin ne boucle pas : il se termine à la fin de sa liste. Un fil musical et un
	événement de secours bouclent toujours. Une occurrence qui a une fin rejoue sa liste, sauf si son événement passe
	alors au fil musical ou à un secours (https://github.com/dascritch/machincast/issues/350) : elle se termine, comme
	sans fin."""
	permanent_list = (Priority.BACKGROUND_PROGRAMMING, Priority.FALLBACK)
	if occurrence.event.priority in permanent_list:
		return True
	return (occurrence.end is not None) and (occurrence.event.end_of_list == END_REPLAY)


def next_(
	connection: psycopg.Connection[TupleRow],
	occurrence: Occurrence,
	instant: datetime,
	randomness: Randomness,
	excluded_list: frozenset[int] = frozenset(),
	history: History = IN_DATABASE,
	forbidden: int | None = None,
	skipped_list: list[Skip] | None = None,
) -> Choice | None:
	"""Prochain sonore de la liste de l'occurrence ; None si rien n'est jouable jusqu'à la fin de la liste.

	exclus : sonores écartés, traités comme non jouables. interdite : banque « ne pas répéter » qui vient de passer ;
	les éléments qui la rappellent sont sautés, et ajoutés à sautes. Une séquence se joue depuis son premier élément
	jouable ; sans élément jouable, elle est sautée.
	"""
	items = read_items(connection, occurrence.event.id)
	last = last_item(connection, occurrence, history)
	for item in items_to_try(items, last, loop(occurrence)):
		if item.sequence is not None:
			choice = in_sequence(
				connection, occurrence, item, None, instant, randomness, excluded_list, history, forbidden, skipped_list
			)
			if choice is not None:
				return choice
		else:
			if (item.bank is not None) and (item.bank == forbidden):
				if skipped_list is not None:
					description = N_("element {position} of “{name}”").format(
						position=item.position, name=occurrence.event.name
					)
					skipped_list.append(Skip(("event_items", item.id), description, occurrence.event.id))
			else:
				sound = _provide(connection, item.sound, item.bank, instant, randomness, excluded_list, history)
				if sound is not None:
					return Choice(sound, item, item.bank, occurrence)
	return None


def in_sequence(
	connection: psycopg.Connection[TupleRow],
	occurrence: Occurrence,
	item: Item,
	last: int | None,
	instant: datetime,
	randomness: Randomness,
	excluded_list: frozenset[int] = frozenset(),
	history: History = IN_DATABASE,
	forbidden: int | None = None,
	skipped_list: list[Skip] | None = None,
) -> Choice | None:
	"""Premier sonore jouable de la séquence de l'élément, après son élément dernier (None : depuis le début) ;
	None quand il ne reste rien de jouable dans la séquence. Mêmes règles que prochain."""
	sequence = None
	if item.sequence is not None:
		sequence = read_sequence(connection, item.sequence)
	if sequence is None:
		return None
	for line in items_after(sequence, last):
		if (line.bank is not None) and (line.bank == forbidden):
			if skipped_list is not None:
				description = N_("element {position} of the sequence “{name}”, in “{name2}”").format(
					position=line.position, name=sequence.name, name2=occurrence.event.name
				)
				skipped_list.append(Skip(("sequence_items", line.id), description, occurrence.event.id))
			continue
		sound = _provide(connection, line.sound, line.bank, instant, randomness, excluded_list, history)
		if sound is not None:
			return Choice(sound, item, line.bank, occurrence, line)
	return None


def _provide(
	connection: psycopg.Connection[TupleRow],
	sound: int | None,
	bank: int | None,
	instant: datetime,
	randomness: Randomness,
	excluded_list: frozenset[int],
	history: History,
) -> int | None:
	"""Le sonore, s'il est jouable, ou celui que la banque fournit ; None si rien n'est jouable."""
	if sound is not None:
		playable = (sound not in excluded_list) and (playable_sound(connection, sound, instant, history))
		if playable:
			return sound
		return None
	if bank is not None:
		return choose_sound(connection, bank, instant, randomness, excluded_list, history)
	return None


class Scheduler:
	"""Décide, à chaque instant, ce que la sortie audio doit faire.

	La connexion a endossé le rôle de la lecture (machincast.database.open_connection) : la grille, les listes et
	l'airplay
	sont lus ; seule une alerte de blanc est écrite, dans le log.
	"""

	def __init__(
		self, connection: psycopg.Connection[TupleRow], randomness: Randomness, history: History = IN_DATABASE
	) -> None:
		self.connection = connection
		self.randomness = randomness
		self.history = history
		self.finished_list: set[tuple[int, datetime | None]] = set()
		"""Occurrences terminées plus tôt : liste épuisée, ou plus rien de jouable."""
		self.in_dead_air = False
		self.excluded_list: dict[int, datetime] = {}
		"""Sonores écartés, avec l'instant où ils l'ont été."""
		self.suspension: Suspension | None = None
		"""Stream tombé en attente de reconnexion."""
		self._reservation = False
		"""Décision prise pour réserver le prochain sonore : un blanc n'y est pas encore signalé."""
		self._notes_skips: tuple[uuid.UUID | None, set[tuple[str, int]]] = (None, set())
		"""Éléments sautés déjà notés dans le log, pour le dernier passage : une seule ligne par élément."""
		self.abandoned_sequence: uuid.UUID | None = None
		"""Passage dont la séquence a été interrompue : elle ne continue pas après lui."""
		self.replacement: Replacement | None = None
		"""La coupure par le secours ou par un feed en cours (https://github.com/dascritch/machincast/issues/323) ;
		retenue en mémoire seulement, comme une occurrence terminée plus tôt."""
		self.cut_list: set[tuple[int, datetime | None]] = set()
		"""Occurrences terminées à la main, coupées par le fil musical, par le secours ou par un feed : leur secours de
		fin de liste ne les remplace pas (https://github.com/dascritch/machincast/issues/350)."""
		self.advanced: Occurrence | None = None
		"""L'occurrence avancée à la demande (https://github.com/dascritch/machincast/issues/257) : active dès la
		demande, jusqu'à son début prévu, où la grille la retrouve. Retenue en mémoire seulement, comme une occurrence
		terminée plus tôt."""

	def _active(
		self,
		events: list[Event],
		instant: datetime,
		finished_list: Collection[tuple[int, datetime | None]] | None = None,
	) -> Occurrence | None:
		"""L'occurrence active, l'occurrence avancée comprise ; terminees, sinon celles de l'ordonnanceur."""
		if finished_list is None:
			finished_list = self.finished_list
		active = active_event(events, instant, frozenset(finished_list), self.advanced)
		# Après son début prévu, la grille la retrouve, sans l'heure où elle a commencé : celle de l'avance.
		if (active is not None) and (self.advanced is not None) and (active.key == self.advanced.key):
			return self.advanced
		return active

	def _on_grid(self, events: list[Event], instant: datetime) -> Occurrence | None:
		"""L'occurrence active, ou, au-dessus d'elle, le secours de fin de liste d'une occurrence dont la liste s'est
		épuisée (https://github.com/dascritch/machincast/issues/350) : il tient l'antenne jusqu'à la fin prévue de
		l'occurrence, tant qu'il a de quoi jouer."""
		active = self._active(events, instant)
		above: set[tuple[int, datetime | None]] = set()
		while True:
			top = self._active(events, instant, above)
			if (top is None) or ((active is not None) and (top.key == active.key)):
				return active
			event = top.event
			if (
				(top.key not in self.cut_list)
				and (event.end_of_list == END_TO_FALLBACK)
				and (event.end_fallback is not None)
				and (top.end is not None)
			):
				fallback = read_event(self.connection, event.end_fallback)
				if (fallback is not None) and (fallback.deleted_at is None):
					occurrence = _fallback_occurrence(fallback)
					if occurrence.key not in self.finished_list:
						return occurrence
			above.add(top.key)

	def following_event(self, instant: datetime) -> Occurrence | None:
		"""L'événement suivant, après l'occurrence en cours, avancée comprise (grid.following_event)."""
		with self.connection.transaction():
			events = read_grid(self.connection)
		return following_event(events, instant, frozenset(self.finished_list), self.advanced)

	def advance(self, instant: datetime) -> Occurrence | None:
		"""L'événement suivant commence aussitôt (https://github.com/dascritch/machincast/issues/257) ; None sans lui.
		Une séquence en cours ne continue pas : l'occurrence avancée a commencé après son dernier passage (_suite)."""
		following = self.following_event(instant)
		if following is None:
			return None
		self.replacement = None
		self.advanced = dataclasses.replace(following, started=wall_hour(instant))
		return self.advanced

	def reserve(self, instant: datetime) -> Choice | None:
		"""Prochain sonore, choisi dès le début du sonore en cours (https://github.com/dascritch/machincast/issues/20).

		Comme une décision sans sonore en cours, mais sans alerte de blanc : le blanc ne viendra qu'à la fin du
		sonore en cours, et sera signalé alors.
		"""
		self._reservation = True
		try:
			return self.decide(instant, None).play
		finally:
			self._reservation = False

	def cutoff(self, ongoing: Ongoing, instant: datetime, horizon: datetime) -> Cutoff | None:
		"""Le premier événement qui commencera après l'instant et avant l'horizon, et coupera net le sonore en cours,
		comme le décidera decider ; None si le sonore va jusqu'à l'horizon. Rien n'est changé.

		Un événement qui commence n'est une coupure que si la décision prise à son début coupe : un événement sans
		rien de jouable laisse l'antenne à celui de priorité inférieure, qui peut être celui du sonore en cours
		(https://github.com/dascritch/machincast/issues/253). La coupure nomme l'occurrence qui jouera alors."""
		with self.connection.transaction():
			events = read_grid(self.connection)
		finished_list = frozenset(self.finished_list)
		moment = next_change(events, instant)
		while (moment is not None) and (moment < horizon):
			active = self._active(events, moment, finished_list)
			if (
				(active is not None)
				and (active.key != ongoing.occurrence.key)
				and (self._begins_after(active, ongoing))
			):
				with self._without_trace():
					self._reservation = True
					decision = self.decide(moment, ongoing)
				if decision.cut:
					return Cutoff(moment, self._occurrence_of(decision, active))
			moment = next_change(events, moment)
		return None

	@staticmethod
	def _occurrence_of(decision: Decision, active: Occurrence) -> Occurrence:
		"""L'occurrence qui prend l'antenne à la coupure : celle du sonore qu'elle joue, ou celle qui s'y tait."""
		if decision.play is not None:
			return decision.play.occurrence
		return (decision.occurrence) or (active)

	def anticipate(self, instant: datetime) -> Choice | None:
		"""Le sonore que réserverait la décision à un instant à venir, sans en garder de trace : rien n'est consigné,
		aucune occurrence n'est terminée, aucune suspension levée, aucun saut noté, aucun sonore écarté n'est oublié,
		et le hasard n'avance pas : la décision prise à cet instant tirera le même sonore, si rien n'a changé
		(https://github.com/dascritch/machincast/issues/169)."""
		with self._without_trace():
			return self.reserve(instant)

	@contextmanager
	def _without_trace(self) -> Iterator[None]:
		"""Le temps d'une décision anticipée : rien n'est consigné, et à la sortie, l'état de l'ordonnanceur et le
		hasard sont rétablis."""
		# Une décision note les sauts d'un autre passage dans un nouvel ensemble : garder l'ancien suffit.
		skips = self._notes_skips
		state = (
			set(self.finished_list),
			self.in_dead_air,
			self.suspension,
			dict(self.excluded_list),
			self.history,
			self._reservation,
		)
		draws = self.randomness.getstate()
		self.history = HistoryInPlayback(self.history)
		try:
			yield
		finally:
			(
				self.finished_list,
				self.in_dead_air,
				self.suspension,
				self.excluded_list,
				self.history,
				self._reservation,
			) = state
			self.randomness.setstate(draws)
			self._notes_skips = skips

	@contextmanager
	def forecast(
		self, planned_list: list[Play], finished_list: Collection[tuple[int, datetime | None]] = ()
	) -> Iterator[PlannedHistory]:
		"""Le temps de prévoir les sonores à venir (https://github.com/dascritch/machincast/issues/228) : les décisions
		voient les passages prévus, du plus ancien au plus récent, comme joués, et les occurrences terminées données
		comme terminées. Rien n'est consigné ; à la sortie, l'état de l'ordonnanceur est rétabli, sauf le hasard : les
		tirages des sonores prévus sont engagés. La liste des passages prévus peut s'allonger dans la prévision. Le
		contexte donne l'historique de la prévision, qui garde ce que les décisions consigneraient."""
		skips = self._notes_skips
		state = (set(self.finished_list), self.in_dead_air, self.suspension, dict(self.excluded_list), self.history)
		self.finished_list |= set(finished_list)
		history = PlannedHistory(self.history, planned_list)
		self.history = history
		try:
			yield history
		finally:
			self.finished_list, self.in_dead_air, self.suspension, self.excluded_list, self.history = state
			self._notes_skips = skips

	def engage(self, finished_list: Collection[tuple[int, datetime | None]]) -> None:
		"""Un sonore prévu devient le prochain : les occurrences que sa décision a terminées le sont pour de bon."""
		self.finished_list |= set(finished_list)

	def validate(self, choice: Choice, instant: datetime) -> bool:
		"""Le sonore réservé peut-il encore être joué : son occurrence est toujours active et il est jouable."""
		with self.connection.transaction():
			events = read_grid(self.connection)
			active = self._cover(instant, self._replace(events, instant, self._on_grid(events, instant)))
			if (
				(active is None)
				or (active.key != choice.occurrence.key)
				or (choice.sound in self._excluded_list(instant))
			):
				return False
			if (choice.item.id == OUTSIDE_LIST) and (self._by_feed(instant, active) is None):
				# Le stream d'un feed ne passe que tant que le feed coupe l'antenne.
				return False
			return playable_sound(self.connection, choice.sound, instant, self.history)

	def suspend(self, occurrence: Occurrence, fallback: int | None) -> None:
		"""Le stream de l'occurrence est tombé : la remplacer, tant qu'elle reste active, par l'événement de secours,
		ou sans secours par l'événement de priorité inférieure."""
		event = None
		# Le secours d'un stream tombé, choisi dans l'événement, l'emporte sur celui du stream
		# (https://github.com/dascritch/machincast/issues/350).
		if occurrence.event.stream_fallback is not None:
			fallback = occurrence.event.stream_fallback
		if fallback is not None:
			with self.connection.transaction():
				event = read_event(self.connection, fallback)
		replacement = self.replacement
		if (replacement is not None) and (replacement.stream is not None) and (replacement.occurrence == occurrence):
			# Le feed qui coupait l'antenne est tombé : la grille reprend, sans secours ; sans suspension, la diffusion
			# abandonne la reconnexion.
			self.replacement = None
			self.suspension = None
			return
		self.suspension = Suspension(occurrence, event)

	def resume(self) -> None:
		"""Le stream est revenu : son occurrence reprend l'antenne."""
		self._raise_suspension()

	def _raise_suspension(self) -> None:
		if (self.suspension is not None) and (self.suspension.fallback is not None):
			self.finished_list.discard(_fallback_occurrence(self.suspension.fallback).key)
		self.suspension = None

	def abandon_sequence(self, play: uuid.UUID) -> None:
		"""La séquence du passage est interrompue : la liste de son événement reprend à l'élément qui la suit."""
		self.abandoned_sequence = play

	def return_to_background_programming(self, instant: datetime) -> list[Occurrence]:
		"""L'événement est coupé par le fil musical (https://github.com/dascritch/machincast/issues/228) : chaque
		occurrence active au-dessus du fil musical est terminée, comme une liste épuisée, jusqu'à sa fin prévue, et
		un stream tombé n'est plus reconnecté. Renvoie les occurrences terminées, de la plus prioritaire à la moins
		prioritaire."""
		self.replacement = None
		# Une occurrence déjà terminée ne passe plus à son secours de fin de liste.
		self.cut_list |= self.finished_list
		with self.connection.transaction():
			events = read_grid(self.connection)
		finished_list = []
		suspension = self.suspension
		if (suspension is not None) and (suspension.occurrence.event.priority is not Priority.BACKGROUND_PROGRAMMING):
			self.finished_list.add(suspension.occurrence.key)
			self.cut_list.add(suspension.occurrence.key)
			finished_list.append(suspension.occurrence)
			self._raise_suspension()
		while True:
			active = self._replace(events, instant, self._on_grid(events, instant))
			if (active is None) or (active.event.priority in (Priority.BACKGROUND_PROGRAMMING, Priority.FALLBACK)):
				return finished_list
			self.finished_list.add(active.key)
			self.cut_list.add(active.key)
			finished_list.append(active)

	def cut_by(self, instant: datetime, fallback: Event | None, stream: int | None) -> Replacement:
		"""Coupe l'antenne par le secours, ou par le stream d'un feed (https://github.com/dascritch/machincast/issues/323)
		: chaque occurrence active au-dessus du fil musical est terminée, et le remplacement tient l'antenne jusqu'à la
		fin prévue des occurrences coupées, ou, sans fin connue ou sous le fil musical, jusqu'au début de l'événement
		suivant."""
		with self.connection.transaction():
			events = read_grid(self.connection)
			under = self._replace(events, instant, self._on_grid(events, instant))
		cut_list = self.return_to_background_programming(instant)
		ends = [occurrence.end for occurrence in cut_list]
		until: datetime | None = None
		if (ends != []) and (None not in ends):
			until = max(end for end in ends if end is not None)
		else:
			following = self.following_event(instant)
			if following is not None:
				until = following.start
		occurrence = (next(iter(cut_list), None)) or (under)
		if fallback is not None:
			occurrence = _fallback_occurrence(fallback)
			# Un secours épuisé par une coupure précédente retrouve toute sa liste.
			self.finished_list.discard(occurrence.key)
		assert occurrence is not None, _("nothing to cut: the broadcast checks that a sound is on air")
		self.replacement = Replacement(occurrence, until, stream)
		return self.replacement

	def _cover(self, instant: datetime, active: Occurrence | None) -> Occurrence | None:
		"""Le remplacement en cours, au-dessus de la grille, jusqu'à sa fin ; le secours, tant qu'il lui reste de quoi
		jouer ; un feed, tant que son stream est jouable. Ailleurs, l'occurrence active de la grille."""
		replacement = self.replacement
		if replacement is None:
			return active
		if (replacement.until is not None) and (wall_hour(instant) >= replacement.until):
			return active
		if replacement.stream is None:
			if replacement.occurrence.key in self.finished_list:
				return active
			return replacement.occurrence
		if (replacement.stream in self._excluded_list(instant)) or (
			not playable_sound(self.connection, replacement.stream, instant, self.history)
		):
			return active
		return replacement.occurrence

	def _by_feed(self, instant: datetime, active: Occurrence | None) -> Choice | None:
		"""Le stream du feed qui coupe l'antenne, s'il la tient : au nom de l'occurrence coupée, hors de toute liste."""
		replacement = self.replacement
		if (
			(replacement is None)
			or (replacement.stream is None)
			or (active is None)
			or (active != replacement.occurrence)
			or (self._cover(instant, None) is None)
		):
			return None
		item = Item(OUTSIDE_LIST, 0, replacement.stream, None)
		return Choice(replacement.stream, item, None, active)

	def exclude(self, sound: int, instant: datetime) -> None:
		"""Écarte un sonore pendant NOT_FOUND_FILE_RETRY, par exemple quand son fichier est introuvable."""
		self.excluded_list[sound] = instant

	def _excluded_list(self, instant: datetime) -> frozenset[int]:
		self.excluded_list = {
			s: since for s, since in self.excluded_list.items() if instant < since + NOT_FOUND_FILE_RETRY
		}
		return frozenset(self.excluded_list)

	def decide(self, instant: datetime, ongoing: Ongoing | None) -> Decision:
		"""Ce que la sortie audio doit faire à l'instant ; ongoing est le passage qu'elle diffuse, s'il y en a un. Le
		sonore à jouer, et la décision, portent l'occurrence qui prête alors son nom."""
		with self.connection.transaction():
			events = read_grid(self.connection)
			decision = self._decide(instant, ongoing, events)
			lender = self._lender(events, instant)
		play = decision.play
		if (play is not None) and (lender is not None) and (lender.event.id != play.occurrence.event.id):
			play = dataclasses.replace(play, lender=lender)
		return dataclasses.replace(decision, play=play, lender=lender)

	def lender(self, instant: datetime) -> Occurrence | None:
		"""L'occurrence qui prête son nom à cet instant : pour un sonore réservé, qui commence sans nouvelle décision."""
		with self.connection.transaction():
			return self._lender(read_grid(self.connection), instant)

	def _lender(self, events: list[Event], instant: datetime) -> Occurrence | None:
		"""L'occurrence qui prête son nom (https://github.com/dascritch/machincast/issues/399) : la plus haute de la
		grille, si son événement prête son nom à la fin de sa liste, que sa liste est épuisée (terminée plus tôt), et
		qu'aucune coupure ne l'a terminée. Une occurrence terminée d'un autre événement n'en est pas une."""
		lending = {event.id for event in events if event.end_of_list == END_LEND_NAME}
		if not lending:
			return None
		others = frozenset(key for key in self.finished_list if (key[0] not in lending) or (key in self.cut_list))
		top = self._active(events, instant, others)
		if (top is None) or (top.event.id not in lending) or (top.key not in self.finished_list) or (top.end is None):
			return None
		return top

	def _repetition(self, last: LastPlay | None) -> Repetition | None:
		"""La banque « ne pas répéter » qui a fourni le dernier passage, s'il y en a une."""
		if (last is None) or (last.bank is None):
			return None
		name = has_no_repeat(self.connection, last.bank)
		if name is None:
			return None
		return Repetition(last.id, last.bank, name)

	def _note_skips(self, repetition: Repetition, skipped_list: list[Skip], instant: datetime) -> None:
		play, notes = self._notes_skips
		if play != repetition.play:
			notes = set()
			self._notes_skips = (repetition.play, notes)
		for skip in skipped_list:
			if skip.key in notes:
				continue
			notes.add(skip.key)
			self.history.record(
				self.connection,
				"info",
				N_("skipped element"),
				N_("bank “{name}” not to repeat: it has just played, {description} is skipped").format(
					name=repetition.name, description=skip.description
				),
				instant,
				bank=repetition.bank,
				event=skip.event,
			)

	def _decide(self, instant: datetime, ongoing: Ongoing | None, events: list[Event]) -> Decision:
		cut = switch_off = False
		while True:
			active = self._cover(instant, self._replace(events, instant, self._on_grid(events, instant)))
			if (ongoing is not None) and (not ((cut) or (switch_off))):
				if (active is not None) and (active.key == ongoing.occurrence.key):
					return Decision()
				if (active is not None) and (self._begins_after(active, ongoing)):
					# Un événement a commencé pendant le sonore en cours : il le coupe net.
					cut = True
				else:
					if ongoing.stream:
						# Fin de l'événement du stream : il s'éteint, l'événement actif reprend.
						switch_off = True
					else:
						# Fin d'événement sans successeur : le sonore va jusqu'au bout.
						return Decision()
			# Lu seulement quand il faut choisir : pas à chaque pas d'un sonore qui continue.
			last = self.history.last_play(self.connection)
			repetition = self._repetition(last)
			if repetition is None:
				forbidden = None
			else:
				forbidden = repetition.bank
			skipped_list: list[Skip] = []
			# Le stream d'un feed qui coupe l'antenne (https://github.com/dascritch/machincast/issues/323) ; sinon,
			# d'abord la suite de la séquence en cours, s'il en reste ; sinon, l'élément suivant de l'événement actif.
			choice = self._by_feed(instant, active)
			if choice is None:
				choice = self._remainder(instant, active, last, forbidden, skipped_list)
			if (choice is None) and (active is not None):
				excluded_list = self._excluded_list(instant)
				choice = next_(
					self.connection,
					active,
					instant,
					self.randomness,
					excluded_list,
					self.history,
					forbidden,
					skipped_list,
				)
			if repetition is not None:
				self._note_skips(repetition, skipped_list, instant)
			if choice is not None:
				self.in_dead_air = False
				return Decision(cut=cut, switch_off=switch_off, play=choice)
			if active is None:
				return self._dead_air(instant, cut, switch_off, None, N_("no active event"))
			if active.event.priority is Priority.BACKGROUND_PROGRAMMING:
				return self._dead_air(
					instant, cut, switch_off, active, N_("nothing to broadcast in the background programming")
				)
			# Liste épuisée, ou plus rien de jouable : l'occurrence se termine, l'événement inférieur reprend. Le sonore
			# en cours est jugé de nouveau face à lui : il continue si c'est son événement
			# (https://github.com/dascritch/machincast/issues/253).
			self.finished_list.add(active.key)
			cut = switch_off = False
			if (repetition is not None) and (any(skip.event == active.event.id for skip in skipped_list)):
				self.history.record(
					self.connection,
					"warning",
					N_("event ended earlier"),
					N_("“{name}”: nothing playable any more once the bank “{name2}” is skipped").format(
						name=active.event.name, name2=repetition.name
					),
					instant,
					bank=repetition.bank,
					event=active.event.id,
				)

	def _remainder(
		self,
		instant: datetime,
		active: Occurrence | None,
		last: LastPlay | None,
		forbidden: int | None,
		skipped_list: list[Skip],
	) -> Choice | None:
		"""Suite de la séquence du dernier passage, tant qu'il lui reste un élément jouable.

		Une séquence se comporte comme un seul sonore : elle va jusqu'au bout, même son événement terminé, sauf si un
		événement a commencé depuis le dernier passage, qui l'a coupée. Pendant la suspension d'un stream, elle cède la
		place au secours.
		"""
		if (
			(last is None)
			or (last.item_sequence is None)
			or (last.item is None)
			or (self.suspension is not None)
			or (last.id == self.abandoned_sequence)
		):
			return None
		if (active is not None) and (last.start is not None) and (self._has_started(active, last.start)):
			return None
		item = read_item(self.connection, last.item)
		if item is None:
			return None
		occurrence = None
		if (active is not None) and (active.event.id == last.event):
			occurrence = active
		else:
			if last.event is not None:
				# Son événement est fini : la séquence va jusqu'au bout en son nom.
				event = read_event(self.connection, last.event)
				if event is not None:
					occurrence = Occurrence(event, None, None)
		if occurrence is None:
			return None
		return in_sequence(
			self.connection,
			occurrence,
			item,
			last.item_sequence,
			instant,
			self.randomness,
			self._excluded_list(instant),
			self.history,
			forbidden,
			skipped_list,
		)

	def _replace(self, events: list[Event], instant: datetime, active: Occurrence | None) -> Occurrence | None:
		"""Pendant la suspension d'un stream, son occurrence cède la place à son secours ; ailleurs, la suspension
		prend fin."""
		suspension = self.suspension
		if suspension is None:
			return active
		if (active is None) or (active.key != suspension.occurrence.key):
			self._raise_suspension()
			return active
		if suspension.fallback is not None:
			fallback = _fallback_occurrence(suspension.fallback)
			if fallback.key not in self.finished_list:
				return fallback
		# Sans secours, ou secours sans rien de jouable : l'événement de priorité inférieure.
		return self._active(events, instant, self.finished_list | {suspension.occurrence.key})

	@staticmethod
	def _begins_after(active: Occurrence, ongoing: Ongoing) -> bool:
		return Scheduler._has_started(active, ongoing.start)

	@staticmethod
	def _has_started(active: Occurrence, since: datetime) -> bool:
		"""L'occurrence a-t-elle commencé après cet instant ?"""
		return (active.start is not None) and (active.start > wall_hour(since))

	def _dead_air(
		self, instant: datetime, cut: bool, switch_off: bool, active: Occurrence | None, message: str
	) -> Decision:
		if self._reservation:
			return Decision(cut=cut, switch_off=switch_off, dead_air=True, occurrence=active)
		if not self.in_dead_air:
			self.in_dead_air = True
			if active is None:
				event = None
			else:
				event = active.event.id
			self.history.record(self.connection, "warning", N_("dead air"), message, instant, event=event)
		return Decision(cut=cut, switch_off=switch_off, dead_air=True, occurrence=active)


def _fallback_occurrence(event: Event) -> Occurrence:
	"""Un événement de secours n'a pas de dates : une seule occurrence, sans début ni fin."""
	return Occurrence(event, None, None)


def ignored_calls(banks: Sequence[int | None], no_repeat: Collection[int], loop: bool) -> list[int]:
	"""Lignes de la liste d'un événement, numérotées dès 1, qui rappellent la banque « ne pas répéter » de la ligne
	précédente : elles seront toujours sautées à la diffusion. Pour un événement qui boucle, la première ligne suit la
	dernière.

	banques : la banque de chaque ligne, None pour un sonore. Pour l'avertissement de l'interface à l'édition d'une
	séquence (https://github.com/dascritch/machincast/issues/112), qui n'empêche pas d'enregistrer.
	"""
	return ignored_calls_to_edges([(bank, bank) for bank in banks], no_repeat, loop)


def ignored_calls_to_edges(
	edges: Sequence[tuple[int | None, int | None]], no_repeat: Collection[int], loop: bool
) -> list[int]:
	"""Comme ignored_calls, quand une ligne commence et finit par des banques différentes : une séquence
	(https://github.com/dascritch/machincast/issues/32). Chaque ligne donne sa première banque, celle que la ligne
	précédente peut avoir déjà fait passer, et sa dernière, que la ligne suivante peut rappeler ; None pour un
	sonore.
	"""
	reported_list = []
	for index, (first, _last) in enumerate(edges):
		if (first not in no_repeat) or ((index == 0) and (not loop)):
			continue
		if edges[index - 1][1] == first:
			reported_list.append(index + 1)
	return reported_list
