"""Ce que la fiche d'une émission dit du créneau qu'elle partage (https://github.com/dascritch/machincast/issues/609) :
à la place de l'encadré de sa grille, dont les dates ne comptent plus, l'événement méta qui la fait jouer, son jour,
ses heures, la règle et le prochain passage de l'émission, puis, en tableau, les autres émissions de son alternance,
chacune avec sa règle et son prochain passage.

« Cette émission partage le créneau « Mercredi soir », le mercredi de 20h à 21h. Elle passe le 2e et 4e mercredi du
mois, prochainement le mercredi 09/12/2026 à 20:00. »
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from machincast.clock import Clock
from machincast.i18n import date_and_hour, short_date
from machincast.shared import grid
from machincast_alternation import queries, rotation
from machincast_alternation.labels import listed, rule
from machincast_alternation.queries import Connection
from machincast_alternation.texts import t

HORIZON = timedelta(days=7 * 26)
"""Jusqu'où chercher le prochain passage d'une émission : une émission mensuelle en a six en six mois."""
NONE = "—"


@dataclass(frozen=True)
class Member:
	"""Une émission de l'alternance : ce qui la fait jouer, son prochain passage, son nom."""

	identifier: int
	rule: str
	start: datetime | None
	name: str

	def following(self) -> str:
		"""« mercredi 09/12/2026 à 20:00 » ; « — » sans passage dans les six mois."""
		return shown(self.start)


@dataclass(frozen=True)
class Slot:
	"""Le créneau partagé d'un événement méta, vu d'une de ses émissions."""

	meta: str
	text: str
	others: list[Member] = field(default_factory=list)


def hour(instant: datetime) -> str:
	"""« 20h », ou « 20h30 »."""
	wall = grid.wall_hour(instant)
	if wall.minute == 0:
		return f"{wall.hour}h"
	return f"{wall.hour}h{wall.minute:02d}"


def when(event: grid.Event) -> str:
	"""« le mercredi de 20h à 21h », « le lundi et le mercredi de 20h à 21h », « le 02/12/2026 à partir de 20h »."""
	days = []
	for day in sorted(event.days):
		days.append(t("on {day}").format(day=grid.DAY_NAMES[day].lower()))
	if (not days) and (event.start is not None):
		days.append(t("on {day}").format(day=short_date(grid.wall_hour(event.start).date())))
	hours = ""
	if (event.start is not None) and (event.end is not None):
		hours = t("from {start} to {end}").format(start=hour(event.start), end=hour(event.end))
	if (event.start is not None) and (event.end is None):
		hours = t("from {start} on").format(start=hour(event.start))
	return " ".join([listed(days), hours]).strip()


def _day(event: grid.Event) -> int | None:
	"""Le jour de l'événement méta, s'il n'en a qu'un, pour nommer les rangs du mois."""
	if len(event.days) == 1:
		(day,) = tuple(event.days)
		return day
	return None


def following(event: grid.Event, alternation: rotation.Alternation, show: int, now: datetime) -> datetime | None:
	"""Le début du prochain passage de cette émission, en heure murale, d'ici six mois ; None sans passage."""
	today = grid.wall_hour(now).date()
	first = rotation.first_day(event)
	for start, _end in grid.sessions(event, today, today + HORIZON):
		if (start >= grid.wall_hour(now)) and (alternation.playing(start.date(), first) == show):
			return start
	return None


def shown(start: datetime | None) -> str:
	"""« mercredi 09/12/2026 à 20:00 » ; « — » sans passage."""
	if start is None:
		return NONE
	return f"{grid.DAY_NAMES[start.weekday()].lower()} {date_and_hour(start)}"


def slots(connection: Connection, show: int, clock: Clock) -> list[Slot]:
	"""Les créneaux que cette émission partage : un par événement méta dont l'alternance la fait jouer."""
	found = []
	now = clock.now()
	for meta, name, shared in queries.sharing(connection, show):
		event = grid.read_event(connection, meta)
		alternation = rotation.read(queries.properties(connection, meta))
		if (event is not None) and (alternation is not None):
			found.append(_slot(connection, show, name, event, alternation, shared, now))
	return found


def _slot(
	connection: Connection,
	show: int,
	name: str,
	event: grid.Event,
	alternation: rotation.Alternation,
	shared: list[int],
	now: datetime,
) -> Slot:
	day = _day(event)
	text = t("This show shares the slot “{name}”, {when}.").format(name=name, when=when(event))
	own = t("For it: {rule}; next broadcast: {following}.").format(
		rule=rule(alternation, show, day), following=shown(following(event, alternation, show, now))
	)
	known = queries.names(connection, shared)
	others = []
	for candidate in shared:
		if (candidate != show) and (candidate in known):
			others.append(
				Member(
					candidate,
					rule(alternation, candidate, day),
					following(event, alternation, candidate, now),
					known[candidate],
				)
			)
	others.sort(key=_order)
	return Slot(name, f"{text} {own}", others)


def _order(member: Member) -> tuple[bool, datetime, str]:
	"""Par prochain passage, puis par nom ; celles sans passage à la fin."""
	if member.start is None:
		return (True, datetime.min, member.name)
	return (False, member.start, member.name)
