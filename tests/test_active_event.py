"""Étapes de la détermination de l'événement actif (https://github.com/dascritch/machincast/issues/12)."""

import dataclasses
from dataclasses import dataclass, field
from datetime import date, datetime

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.clock import FixedClock
from machincast.database import Role, open_connection
from machincast.player.grid import (
	Event,
	Occurrence,
	Priority,
	active_event,
	following_event,
	next_change,
	occurrence,
	read_grid,
	wall_hour,
)
from tests.database_fixtures import sample_database_parameters

scenarios("active_event.feature")

Connection = psycopg.Connection[tuple[object, ...]]
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass
class Context:
	events: list[Event] = field(default_factory=list)
	finished_list: set[tuple[int, datetime | None]] = field(default_factory=set)
	clock: FixedClock | None = None
	advanced: Occurrence | None = None
	"""L'occurrence avancée (https://github.com/dascritch/machincast/issues/257)."""


@pytest.fixture
def context() -> Context:
	return Context()


def hour(context: Context, text: str) -> datetime:
	"""« 2026-10-14 21:30 » en heure du poste, ou « 2026-10-25 02:30+01:00 » avec son décalage ; avec fuseau."""
	return datetime.fromisoformat(text.strip()).astimezone()


def hour_or_none(context: Context, text: str) -> datetime | None:
	"""Comme heure, et aucune heure pour une cellule vide."""
	if text == "":
		return None
	return hour(context, text)


def table(datatable: list[list[str]]) -> list[dict[str, str]]:
	headers, *lines = datatable
	return [dict(zip(headers, (cell.strip() for cell in line), strict=True)) for line in lines]


def named(context: Context, name: str) -> Event:
	return next(e for e in context.events if e.name == name)


def active(context: Context, instant: datetime) -> str | None:
	result = active_event(context.events, instant, frozenset(context.finished_list), context.advanced)
	return None if result is None else result.event.name


@given("aucun événement")
def no(context: Context) -> None:
	context.events = []


@given(parsers.parse("l'heure « {text} »"))
def clock(context: Context, text: str) -> None:
	context.clock = FixedClock(hour(context, text))


@given("les événements :")
def events(context: Context, datatable: list[list[str]]) -> None:
	context.events = [
		Event(
			id=number,
			name=line["nom"],
			priority=Priority(line["priorité"]),
			start=hour_or_none(context, line["début"]),
			end=hour_or_none(context, line["fin"]),
			days=frozenset(DAYS.index(day.strip()) for day in line["jours"].split(",") if day.strip()),
			modified_at=hour(context, line["modifié"]),
		)
		for number, line in enumerate(table(datatable), start=1)
	]


@given("ces événements enregistrés en base")
def in_database(context: Context, empty_database: Connection) -> None:
	for e in context.events:
		empty_database.execute(
			"INSERT INTO events (internal_name, priority, starts_at, ends_at, recurrence_days, modified_at)"
			" VALUES (%s, %s, %s, %s, %s::weekday[], %s)",
			(e.name, e.priority.value, e.start, e.end, [DAYS[j] for j in sorted(e.days)], e.modified_at),
		)


@when("le binaire lecture lit la grille en base")
def read(context: Context, empty_database: Connection) -> None:
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		context.events = read_grid(connection)


@when(parsers.parse("l'occurrence de « {name} » commencée le « {start} » se termine, sa liste épuisée"))
def finish(context: Context, name: str, start: str) -> None:
	instant = hour(context, start)
	ongoing = occurrence(named(context, name), instant)
	assert (ongoing is not None) and (ongoing.start == wall_hour(instant)), ongoing
	context.finished_list.add(ongoing.key)


@given(parsers.parse("la session du « {day} » de « {name} » est sautée"))
def skip(context: Context, day: str, name: str) -> None:
	skipped = date.fromisoformat(day)
	events = []
	for event in context.events:
		if event.name == name:
			event = dataclasses.replace(event, skipped_list=event.skipped_list | {skipped})
		events.append(event)
	context.events = events


@given(parsers.parse("l'occurrence de « {name} » du « {start} » avancée"))
def advance(context: Context, name: str, start: str) -> None:
	instant = hour(context, start)
	planned = occurrence(named(context, name), instant)
	assert (planned is not None) and (planned.start == wall_hour(instant)), planned
	context.advanced = planned


@then(
	parsers.re(
		r"après le « (?P<instant>[^»]+) », (?:il n'y a pas d'événement suivant"
		r"|l'événement suivant est « (?P<name>[^»]+) » du « (?P<start>[^»]+) »)"
	)
)
def following(context: Context, instant: str, name: str | None, start: str | None) -> None:
	found = following_event(context.events, hour(context, instant), frozenset(context.finished_list))
	obtained = None
	if found is not None:
		obtained = (found.event.name, found.start)
	expected = None
	if (name is not None) and (start is not None):
		expected = (name, wall_hour(hour(context, start)))
	assert obtained == expected


@then(parsers.parse("le prochain changement de la grille après le « {instant} » est le « {expected} »"))
def change(context: Context, instant: str, expected: str) -> None:
	found = next_change(context.events, hour(context, instant))
	assert found is not None
	assert found == hour(context, expected), found


@then("aucun événement n'est actif")
def no_active(context: Context) -> None:
	assert context.clock is not None
	assert active(context, context.clock.now()) is None


@then(parsers.parse("l'événement actif est « {name} » à chacune de ces heures :"))
def active_everywhere(context: Context, name: str, datatable: list[list[str]]) -> None:
	for line in table(datatable):
		assert active(context, hour(context, line["heure"])) == name, line["heure"]


@then("l'événement actif est :")
def active_according_to_hour(context: Context, datatable: list[list[str]]) -> None:
	gaps = []
	for line in table(datatable):
		# La grille ne lit l'heure que par une horloge : une horloge fixe, réglée sur chaque heure du tableau.
		obtained = active(context, FixedClock(hour(context, line["heure"])).now())
		if obtained != line["actif"]:
			gaps.append(f"{line['heure']} : {obtained} au lieu de {line['actif']}")
	assert not gaps, "\n".join(gaps)
