"""Scénarios de l'événement qui joue une occurrence, choisi par un plugin
(https://github.com/dascritch/machincast/issues/608).

Les événements sont en base de test ; le plugin est imité par un abonné au point « grid.substitutions » des plugins
du binaire (machincast.plugins.active), que tests/conftest.py remet à vide après chaque scénario.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import plugins
from machincast.plugins.points import CORE
from machincast.shared import grid
from machincast.shared.grid import Event, Substitution
from tests.interface_steps import Connection, date_or_none
from tests.test_plugins import journal_says

scenarios("grid_substitution.feature")

then(parsers.parse("le journal dit « {message} »"))(journal_says)

POINT = "grid.substitutions"


@dataclass
class Context:
	names: dict[str, int] = field(default_factory=dict)
	choosing: bool = True
	read: list[Event] = field(default_factory=list)


@pytest.fixture
def context() -> Context:
	return Context()


@given("les événements de la grille :")
def grid_events(empty_database: Connection, context: Context, datatable: list[list[str]]) -> None:
	for name, priority, start, end, days in datatable[1:]:
		day_list = "{" + days.strip() + "}"
		found = empty_database.execute(
			"INSERT INTO events (internal_name, priority, starts_at, ends_at, recurrence_days)"
			" VALUES (%s, %s, %s, %s, %s::weekday[]) RETURNING id",
			(name.strip(), priority.strip(), date_or_none(start.strip()), date_or_none(end.strip()), day_list),
		).fetchone()
		assert found is not None
		context.names[name.strip()] = int(str(found[0]))


@given(
	parsers.re(
		r"le plugin « alternance » qui fait jouer « (?P<meta>[^»]+) » par « (?P<first>[^»]+) » le premier mercredi"
		r" du mois, par « (?P<other>[^»]+) » sinon"
	)
)
def alternation(context: Context, meta: str, first: str, other: str) -> None:
	def hidden(event: Event) -> frozenset[int]:
		if (not context.choosing) or (event.id != context.names[meta]):
			return frozenset()
		return frozenset({context.names[first], context.names[other]})

	def playing(event: Event, day: date) -> int | None:
		if (not context.choosing) or (event.id != context.names[meta]):
			return None
		if day.day <= 7:
			return context.names[first]
		return context.names[other]

	plugins.active().points.subscribe("alternance", POINT, lambda _data: Substitution(hidden, playing))


@given("le plugin « alternance » qui ne choisit rien")
def nothing_chosen(context: Context) -> None:
	"""Ni choix, ni événement hors grille : il ne fait jouer personne."""
	context.choosing = False


@given(parsers.parse("le plugin « {name} » qui répond « {value} » au point « {point} »"))
def chatty(name: str, value: str, point: str) -> None:
	plugins.active().points.subscribe(name, point, lambda _data: value)


@when("la grille est lue")
def read(empty_database: Connection, context: Context, caplog: pytest.LogCaptureFixture) -> None:
	caplog.set_level(logging.WARNING, logger="machincast.shared.grid")
	context.read = grid.read_grid(empty_database)


def _moment(text: str) -> datetime:
	return datetime.fromisoformat(text)


@then(
	parsers.re(
		r"à « (?P<instant>[^»]+) », l'événement actif est « (?P<name>[^»]+) », de « (?P<start>[^»]+) » à"
		r" « (?P<end>[^»]+) », de priorité « (?P<priority>[^»]+) »"
	)
)
def active(context: Context, instant: str, name: str, start: str, end: str, priority: str) -> None:
	found = grid.active_event(context.read, _moment(instant).astimezone())
	assert found is not None
	assert (found.event.name, found.start, found.end, found.event.priority) == (
		name,
		_moment(start),
		_moment(end),
		grid.Priority(priority),
	)
	assert found.key == (context.names[name], _moment(start))


@then(parsers.parse("à « {instant} », aucun événement n'est actif"))
def none_active(context: Context, instant: str) -> None:
	assert grid.active_event(context.read, _moment(instant).astimezone()) is None


@then(parsers.re(r"la grille lue n'a que (?P<names>«.+»)"))
def only(context: Context, names: str) -> None:
	found = []
	for event in context.read:
		found.append(event.name)
	assert found == re.findall(r"« ([^»]+) »", names)


@then(parsers.re(r"le calendrier du « (?P<first>[^»]+) » au « (?P<last>[^»]+) » montre (?P<shown>.+)"))
def calendar(context: Context, first: str, last: str, shown: str) -> None:
	found = []
	for planned in grid.plan(context.read, _moment(first), _moment(last)):
		assert planned.start is not None
		found.append((planned.occurrence.event.name, planned.start))
	expected = []
	for name, start in re.findall(r"« ([^»]+) » le « ([^»]+) »", shown):
		expected.append((name, _moment(start)))
	assert found == expected


@then(parsers.parse("le point « {point} » est un point du cœur"))
def core_point(point: str) -> None:
	assert point in CORE
	assert "machincast.shared.grid.Substitution" in CORE[point]
