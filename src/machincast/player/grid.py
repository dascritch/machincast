"""Grille des événements et choix de l'événement actif (https://github.com/dascritch/machincast/issues/12, spec § 4.1).

À tout instant, l'événement actif est celui de plus haute priorité (spécial > émission > fil musical) dont une
occurrence couvre l'instant, sauf si cette occurrence s'est terminée plus tôt (liste épuisée d'un événement sans
fin). À priorité égale, une occurrence sans fin, ou un fil musical permanent, laisse la place à toute occurrence qui
a commencé après elle, et reprend après (https://github.com/dascritch/machincast/issues/32) : un fil permanent sert
de fond. Sinon, deux événements de même priorité qui se chevauchent sont départagés par leur date de modification :
le dernier modifié en base l'emporte. L'interface refuse ces chevauchements à la saisie (chevauchement).

Dates d'un événement (spec § 3.1) : debut et fin sont ceux de sa première occurrence.

- Un fil musical sans debut ni fin est permanent.
- Sans jours de récurrence, l'événement a une seule occurrence, [debut, fin[, ou [debut, ∞[ sans fin.
- Avec des jours de récurrence, il revient chacun de ces jours à partir de sa première occurrence, à la même
  heure que debut, et dure jusqu'à l'heure de fin, autant de jours plus tard que la première occurrence : un
  événement peut passer minuit, et c'est le jour de son début qui compte.
- Sans fin, une occurrence couvre l'instant à partir de son début, jusqu'à ce que sa liste soit épuisée : le
  binaire la déclare alors terminée (Occurrence.cle).

Une session sautée (https://github.com/dascritch/machincast/issues/273), désignée par le jour où elle commence
(Evenement.sautees), n'existe pas pour la grille : elle ne joue pas, ne coupe rien, ne chevauche rien. Seul le
calendrier la montre (prevoir, Prevue.sautee).

Un événement de secours (https://github.com/dascritch/machincast/issues/16) n'est jamais actif par la grille :
sans date ni jour, sa liste ne joue qu'à la place d'un stream tombé (machincast.player.rundown).

Le poste travaille en heure locale, celle de Paris : la grille calcule en heure murale, sans fuseau à manier.
Au changement d'heure, un événement garde donc son heure (spec § 4.1 : aucune règle particulière).
"""

from collections.abc import Iterable, Set
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

import psycopg
from psycopg.rows import TupleRow

from machincast.i18n import _


class Priority(StrEnum):
	"""Valeurs du type event_priority, de la plus basse à la plus haute."""

	FALLBACK = "fallback"
	"""Hors grille : remplace un stream tombé, jamais actif à une heure donnée."""
	BACKGROUND_PROGRAMMING = "background_programming"
	SHOW = "show"
	SPECIAL = "special"


RANKS = {priority: rank for rank, priority in enumerate(Priority)}

NEVER = datetime.min.replace(tzinfo=UTC)
"""Date de modification d'un événement qui n'en a pas."""
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
"""Valeurs du type weekday, dans l'ordre de datetime.weekday()."""
DAY_NAMES = (_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"), _("Sunday"))
"""Leurs noms à l'écran, dans le même ordre : ceux aussi des cases de la fiche d'un événement."""


@dataclass(frozen=True)
class Event:
	id: int
	name: str
	priority: Priority
	start: datetime | None
	"""Début de la première occurrence ; None pour un fil musical permanent."""
	end: datetime | None
	days: frozenset[int]
	"""Jours de récurrence, 0 pour lundi ; vide si l'événement n'a qu'une occurrence."""
	modified_at: datetime
	skipped_list: frozenset[date] = frozenset()
	"""Les jours où commencent ses sessions sautées (https://github.com/dascritch/machincast/issues/273)."""
	deleted_at: datetime | None = None
	"""Supprimé depuis l'interface (https://github.com/dascritch/machincast/issues/267) : il ne joue plus après ;
	seul le calendrier lit un événement supprimé, pour ses occurrences d'avant
	(https://github.com/dascritch/machincast/issues/269)."""


@dataclass(frozen=True)
class Occurrence:
	event: Event
	start: datetime | None
	"""Début de l'occurrence, en heure murale du poste ; None pour un fil musical permanent."""
	end: datetime | None
	"""None pour une occurrence sans fin, qui dure jusqu'à l'épuisement de sa liste."""
	started: datetime | None = field(default=None, compare=False)
	"""Pour une occurrence avancée (https://github.com/dascritch/machincast/issues/257) : l'heure murale où elle a
	commencé, avant son début prévu. Sa liste se compte depuis là. Elle ne change ni la clé, ni l'égalité."""

	@property
	def key(self) -> tuple[int, datetime | None]:
		"""Identifie l'occurrence, pour la déclarer terminée plus tôt."""
		return self.event.id, self.start


def wall_hour(moment: datetime) -> datetime:
	"""Heure du poste, sans fuseau : la machine travaille en heure locale, celle de Paris."""
	if moment.tzinfo is None:
		return moment
	return moment.astimezone().replace(tzinfo=None)


def _wall_hour_or_none(moment: datetime | None) -> datetime | None:
	if moment is None:
		return None
	return wall_hour(moment)


def _covers(start: datetime, end: datetime | None, moment: datetime) -> bool:
	return (start <= moment) and ((end is None) or (moment < end))


def occurrence(event: Event, instant: datetime) -> Occurrence | None:
	"""Occurrence de l'événement qui couvre l'instant, ou None. Ses dates sont en heure murale du poste."""
	if event.start is None:
		return Occurrence(event, None, None)
	start = wall_hour(event.start)
	end = _wall_hour_or_none(event.end)
	moment = wall_hour(instant)
	if not event.days:
		if (not _covers(start, end, moment)) or (start.date() in event.skipped_list):
			return None
		return Occurrence(event, start, end)

	first_day = start.date()
	duration_in_days: int | None = None
	if end is not None:
		duration_in_days = (end.date() - first_day).days
	# Une occurrence avec fin a commencé au plus tôt autant de jours avant que dure la première ; une occurrence
	# sans fin, dans la semaine qui précède.
	recoil = 7 if duration_in_days is None else duration_in_days
	for gap in range(recoil + 1):
		day = moment.date() - timedelta(days=gap)
		if (day < first_day) or ((day != first_day) and (day.weekday() not in event.days)):
			continue
		if day in event.skipped_list:
			continue
		departure = datetime.combine(day, start.time())
		arrival = None
		if (end is not None) and (duration_in_days is not None):
			arrival = datetime.combine(day + timedelta(days=duration_in_days), end.time())
		if _covers(departure, arrival, moment):
			return Occurrence(event, departure, arrival)
	return None


def active_event(
	events: Iterable[Event],
	instant: datetime,
	finished_list: Set[tuple[int, datetime | None]] = frozenset(),
	advanced: Occurrence | None = None,
) -> Occurrence | None:
	"""Occurrence de l'événement actif à l'instant, ou None si aucun ne le couvre.

	terminees contient les clés (Occurrence.cle) des occurrences terminées plus tôt, liste épuisée. Une occurrence
	avancée (https://github.com/dascritch/machincast/issues/257), tant qu'elle n'est pas terminée, est active avant son
	début prévu, au-dessus de tout ; à son début, la grille la retrouve, avec la même clé.
	"""
	if (
		(advanced is not None)
		and (advanced.start is not None)
		and (advanced.key not in finished_list)
		and (wall_hour(instant) < advanced.start)
	):
		return advanced
	candidates = [
		o
		for e in events
		if (e.priority is not Priority.FALLBACK)
		and ((o := occurrence(e, instant)) is not None)
		and (o.key not in finished_list)
	]
	return _winning(candidates)


def _yields(opened: Occurrence, others: Iterable[Occurrence]) -> bool:
	"""Une occurrence sans fin, ou permanente, laisse la place à une occurrence qui a commencé après elle."""
	if opened.end is not None:
		return False
	return any(
		(other.start is not None) and ((opened.start is None) or (other.start > opened.start)) for other in others
	)


def sessions(event: Event, de: date, a: date) -> list[tuple[datetime, datetime | None]]:
	"""Début et fin, en heure murale, des sessions d'un événement qui commencent du premier jour, inclus, au second,
	exclu, sautées comprises : celles que l'interface peut sauter ou rétablir
	(https://github.com/dascritch/machincast/issues/273)."""
	return _occurrences(event, de, a, with_skipped=True)


def _occurrences(event: Event, de: date, a: date, with_skipped: bool = False) -> list[tuple[datetime, datetime | None]]:
	"""Début et fin, en heure murale, des occurrences qui commencent du premier jour, inclus, au second, exclu ; sans
	les sessions sautées, sauf demande. Rien pour un événement sans début."""
	if event.start is None:
		return []
	start = wall_hour(event.start)
	end = _wall_hour_or_none(event.end)
	duration_in_days: int | None = None
	if end is not None:
		duration_in_days = (end.date() - start.date()).days
	found_list: list[tuple[datetime, datetime | None]] = []
	for gap in range((a - de).days):
		day = de + timedelta(days=gap)
		if (day < start.date()) or ((day != start.date()) and (day.weekday() not in event.days)):
			continue
		if (day in event.skipped_list) and (not with_skipped):
			continue
		arrival = None
		if (end is not None) and (duration_in_days is not None):
			arrival = datetime.combine(day + timedelta(days=duration_in_days), end.time())
		found_list.append((datetime.combine(day, start.time()), arrival))
	return found_list


def _common_instant(
	first: tuple[datetime, datetime | None], second: tuple[datetime, datetime | None]
) -> datetime | None:
	"""Le premier instant commun à deux occurrences ; une occurrence sans fin ne compte que par son début."""
	(start, end), (other_start, other_end) = first, second
	if (end is None) and (other_end is None):
		if start == other_start:
			return start
		return None
	if end is None:
		if _covers(other_start, other_end, start):
			return start
		return None
	if other_end is None:
		if _covers(start, end, other_start):
			return other_start
		return None
	if (start < other_end) and (other_start < end):
		return max(start, other_start)
	return None


def _to_leave_of(
	occurrences: list[tuple[datetime, datetime | None]], since: datetime | None
) -> list[tuple[datetime, datetime | None]]:
	"""Les occurrences ramenées à ce qui en reste à partir de l'instant, en heure murale : une occurrence finie avant
	disparaît, une occurrence en cours commence à l'instant, une occurrence sans fin commencée avant disparaît."""
	if since is None:
		return occurrences
	remaining_list: list[tuple[datetime, datetime | None]] = []
	for start, end in occurrences:
		if end is None:
			if start >= since:
				remaining_list.append((max(start, since), end))
		elif end > since:
			remaining_list.append((max(start, since), end))
	return remaining_list


def overlap(event: Event, others: Iterable[Event], since: datetime | None = None) -> tuple[Event, datetime] | None:
	"""Le premier événement de même priorité que l'événement chevauche, avec le premier instant commun, en heure
	murale ; None s'il n'en chevauche aucun (spec § 4.1, https://github.com/dascritch/machincast/issues/32).

	Un événement sans début ne chevauche rien : un fil musical permanent sert de fond, un événement de secours est
	hors grille. Une occurrence sans fin ne compte que par son début. Les occurrences se répètent chaque semaine : il
	suffit de les comparer de part et d'autre du début le plus tardif des deux, sur une semaine et leurs durées.

	Avec un instant, seul compte ce qui chevauche à partir de lui : la grille déjà diffusée ne bloque rien, un
	chevauchement en cours compte à partir de l'instant (https://github.com/dascritch/machincast/issues/271).
	"""
	wall = _wall_hour_or_none(since)
	found_list: list[tuple[datetime, int, Event]] = []
	if event.start is None:
		return None
	for other in others:
		if (other.priority is not event.priority) or (other.start is None):
			continue
		duration = _covered_days(event) + _covered_days(other)
		pivot = max(wall_hour(event.start), wall_hour(other.start), (wall) or (datetime.min)).date()
		de, a = pivot - timedelta(days=duration + 1), pivot + timedelta(days=duration + 8)
		common_list = [
			instant
			for first in _to_leave_of(_occurrences(event, de, a), wall)
			for second in _to_leave_of(_occurrences(other, de, a), wall)
			if (instant := _common_instant(first, second)) is not None
		]
		if common_list:
			found_list.append((min(common_list), other.id, other))
	if not found_list:
		return None
	instant, _identifier, other = min(found_list, key=lambda found: (found[0], found[1]))
	return other, instant


def _covered_days(event: Event) -> int:
	"""Jours que touche une occurrence, au-delà de celui de son début ; aucun pour une occurrence sans fin."""
	if (event.start is None) or (event.end is None):
		return 0
	return (wall_hour(event.end).date() - wall_hour(event.start).date()).days


def next_change(events: Iterable[Event], instant: datetime) -> datetime | None:
	"""Prochain début ou fin d'une occurrence après l'instant, ou None : la grille ne change plus.

	Sert à la simulation (https://github.com/dascritch/machincast/issues/21), qui avance d'échéance en échéance.
	"""
	moment = wall_hour(instant)
	candidates: list[datetime] = []
	for event in events:
		if (event.priority is Priority.FALLBACK) or (event.start is None):
			continue
		start = wall_hour(event.start)
		end = _wall_hour_or_none(event.end)
		if not event.days:
			if start.date() not in event.skipped_list:
				candidates += [c for c in (start, end) if c is not None]
			continue
		duration_in_days: int | None = None
		if end is not None:
			duration_in_days = (end.date() - start.date()).days
		# Les occurrences commencées dans la semaine passée peuvent encore finir ; celles de la semaine à venir,
		# commencer.
		for gap in range(-8 - ((duration_in_days) or (0)), 8):
			day = moment.date() + timedelta(days=gap)
			if (day < start.date()) or ((day != start.date()) and (day.weekday() not in event.days)):
				continue
			if day in event.skipped_list:
				continue
			candidates.append(datetime.combine(day, start.time()))
			if (end is not None) and (duration_in_days is not None):
				candidates.append(datetime.combine(day + timedelta(days=duration_in_days), end.time()))
	after = [candidate for candidate in candidates if candidate > moment]
	if not after:
		return None
	return min(after).astimezone()


FOLLOWING_EVENT_HORIZON = timedelta(days=7)
"""Jusqu'où chercher l'événement suivant (https://github.com/dascritch/machincast/issues/257)."""


def following_event(
	events: Iterable[Event],
	instant: datetime,
	finished_list: Set[tuple[int, datetime | None]] = frozenset(),
	advanced: Occurrence | None = None,
	horizon: timedelta = FOLLOWING_EVENT_HORIZON,
) -> Occurrence | None:
	"""La première occurrence qui commencera après l'instant et prendra l'antenne, jusqu'à l'horizon compris ; None
	sans elle (https://github.com/dascritch/machincast/issues/257). Un fil musical qui reprend, ou une occurrence
	commencée avant l'instant qui retrouve l'antenne, n'en est pas une : c'est ce que fait couper l'événement. Une
	occurrence avancée est l'occurrence en cours : le suivant est celui qui viendra après elle."""
	events = list(events)
	current = active_event(events, instant, finished_list, advanced)
	# En heure murale : sept jours d'horloge, même au changement d'heure.
	departure = wall_hour(instant)
	limit = departure + horizon
	moment = next_change(events, instant)
	while (moment is not None) and (wall_hour(moment) <= limit):
		active = active_event(events, moment, finished_list, advanced)
		if (
			(active is not None)
			and (active.start is not None)
			and (active.start > departure)
			and ((current is None) or (active.key != current.key))
		):
			return active
		moment = next_change(events, moment)
	return None


@dataclass(frozen=True)
class Planned:
	"""Une occurrence prévue, telle que la montre le calendrier (https://github.com/dascritch/machincast/issues/36)."""

	occurrence: Occurrence
	start: datetime
	"""Début dessiné : celui de l'occurrence, ou celui de la période pour un fil musical permanent."""
	end: datetime
	"""Fin dessinée : celle de l'occurrence ; pour une occurrence sans fin, le début suivant d'une priorité égale ou
	plus haute, au plus tard minuit ; pour un fil musical permanent, la fin de la période."""
	plays: tuple[tuple[datetime, datetime], ...]
	"""Les moments de la période où l'occurrence serait à l'antenne, dans l'ordre."""
	skipped: bool = False
	"""Une session sautée (https://github.com/dascritch/machincast/issues/273) : elle ne joue rien, ne cache rien."""


def plan(events: Iterable[Event], de: datetime, a: datetime) -> list[Planned]:
	"""Les occurrences qui touchent la période [de, a[, en heure murale, et ce que chacune en joue.

	Ce qui joue suit active_event, avec la fin dessinée d'une occurrence sans fin : la durée réelle de sa liste
	n'est connue qu'à la diffusion. Les événements de secours, hors grille, n'y sont pas. Un événement supprimé
	n'a que ses occurrences commencées avant sa suppression, arrêtées à elle
	(https://github.com/dascritch/machincast/issues/269). Une session sautée est montrée à part (Prevue.sautee) : elle
	ne joue rien, et ne compte ni pour ce qui joue, ni pour la fin dessinée d'une autre
	(https://github.com/dascritch/machincast/issues/273).
	"""
	de, a = wall_hour(de), wall_hour(a)
	grid = [event for event in events if event.priority is not Priority.FALLBACK]
	occurrences: list[Occurrence] = []
	skipped_list: list[Occurrence] = []
	for event in grid:
		deleted = _wall_hour_or_none(event.deleted_at)
		if event.start is None:
			if (deleted is None) or (deleted > de):
				occurrences.append(Occurrence(event, None, None))
			continue
		# Une occurrence commencée avant la période peut encore la toucher : autant de jours qu'elle en couvre.
		since = de.date() - timedelta(days=_covered_days(event) + 1)
		for start, end in _occurrences(event, since, a.date() + timedelta(days=1), with_skipped=True):
			if (deleted is not None) and (start >= deleted):
				continue
			if start.date() in event.skipped_list:
				skipped_list.append(Occurrence(event, start, end))
			else:
				occurrences.append(Occurrence(event, start, end))
	ends = {o.key: _drawn_end(o, occurrences, a) for o in occurrences}
	for o in occurrences:
		deleted = _wall_hour_or_none(o.event.deleted_at)
		if deleted is not None:
			ends[o.key] = min(ends[o.key], deleted)
	# Une occurrence hors de la période n'y couvre aucun moment : elle n'y joue pas, et n'y est pas dessinée.
	kept_list = occurrences
	bounds = sorted(
		{de, a}
		| {o.start for o in kept_list if (o.start is not None) and (de < o.start < a)}
		| {ends[o.key] for o in kept_list if de < ends[o.key] < a}
	)
	plays: dict[tuple[int, datetime | None], list[tuple[datetime, datetime]]] = {o.key: [] for o in kept_list}
	for departure, arrival in zip(bounds, bounds[1:], strict=False):
		covering = [o for o in kept_list if ((o.start is None) or (o.start <= departure)) and (ends[o.key] > departure)]
		winning = _winning(covering)
		if winning is None:
			continue
		moments = plays[winning.key]
		if (moments) and (moments[-1][1] == departure):
			moments[-1] = (moments[-1][0], arrival)
			continue
		moments.append((departure, arrival))
	planned_list = [Planned(o, (o.start) or (de), ends[o.key], tuple(plays[o.key])) for o in kept_list]
	planned_list += [
		Planned(o, (o.start) or (de), _drawn_end(o, occurrences, a), (), skipped=True) for o in skipped_list
	]
	return sorted(planned_list, key=lambda p: (p.start, RANKS[p.occurrence.event.priority], p.occurrence.event.id))


def _drawn_end(occurrence: Occurrence, all_: list[Occurrence], a: datetime) -> datetime:
	if occurrence.start is None:
		return a
	if occurrence.end is not None:
		return occurrence.end
	midnight = datetime.combine(occurrence.start.date() + timedelta(days=1), datetime.min.time())
	rank = RANKS[occurrence.event.priority]
	following_list = [
		other.start
		for other in all_
		if (other.start is not None) and (other.start > occurrence.start) and (RANKS[other.event.priority] >= rank)
	]
	return min([midnight, *following_list])


def _winning(covering: list[Occurrence]) -> Occurrence | None:
	"""Comme active_event : la plus haute priorité, puis ce qui ne cède pas, puis la dernière modifiée."""
	if not covering:
		return None
	rank = max(RANKS[o.event.priority] for o in covering)
	equal = [o for o in covering if RANKS[o.event.priority] == rank]
	kept_list = [o for o in equal if not _yields(o, equal)]
	return max(kept_list, key=lambda o: (o.event.modified_at, o.event.id))


COLUMNS = (
	"id, internal_name, priority::text, starts_at, ends_at, recurrence_days::text[], modified_at, deleted_at,"
	" ARRAY(SELECT s.day FROM event_skips s WHERE s.event_id = events.id)"
)


def read_grid(connection: psycopg.Connection[TupleRow], deleted_list: bool = False) -> list[Event]:
	"""Événements de la grille, sans les événements de secours ; la connexion a endossé le rôle de la lecture
	(machincast.database.open_connection). Un événement supprimé ne joue plus
	(https://github.com/dascritch/machincast/issues/267) : seul le calendrier les demande (supprimes), pour leurs
	occurrences d'avant leur suppression."""
	condition = "deleted_at IS NULL"
	if deleted_list:
		condition = "TRUE"
	lines = connection.execute(
		f"SELECT {COLUMNS} FROM events WHERE priority <> 'fallback' AND {condition} ORDER BY id"  # noqa: S608
	).fetchall()
	return _events(lines)


def read_event(connection: psycopg.Connection[TupleRow], identifier: int) -> Event | None:
	"""Un événement, quelle que soit sa priorité : par exemple l'événement de secours d'un stream."""
	lines = connection.execute(
		f"SELECT {COLUMNS} FROM events WHERE id = %s",
		(identifier,),
	).fetchall()
	return next(iter(_events(lines)), None)


def _events(lines: list[TupleRow]) -> list[Event]:
	return [
		Event(
			id=int(str(identifier)),
			name=str(name),
			priority=Priority(str(priority)),
			start=start if isinstance(start, datetime) else None,
			end=end if isinstance(end, datetime) else None,
			days=frozenset(DAYS.index(str(day)) for day in (days if isinstance(days, list) else [])),
			modified_at=modified_at if isinstance(modified_at, datetime) else NEVER,
			skipped_list=frozenset(
				day for day in (skipped_list if isinstance(skipped_list, list) else []) if isinstance(day, date)
			),
			deleted_at=deleted_at if isinstance(deleted_at, datetime) else None,
		)
		for identifier, name, priority, start, end, days, modified_at, deleted_at, skipped_list in lines
	]
