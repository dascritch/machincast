"""Étapes du chevauchement de deux événements de même priorité (https://github.com/dascritch/machincast/issues/32)."""

from datetime import datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then

from machincast.player.grid import DAYS, NEVER, Event, Priority, overlap

scenarios("overlaps.feature")


def hour_or_none(text: str) -> datetime | None:
	"""« 2026-10-14 21:30 » en heure du poste, avec fuseau ; aucune heure pour une cellule vide."""
	if text == "":
		return None
	return datetime.fromisoformat(text).astimezone()


@pytest.fixture
def events() -> list[Event]:
	return []


@given("les événements à comparer :")
def to_compare(events: list[Event], datatable: list[list[str]]) -> None:
	headers, *lines = datatable
	for number, values in enumerate(lines, start=1):
		line = dict(zip((header.strip() for header in headers), (value.strip() for value in values), strict=True))
		events.append(
			Event(
				id=number,
				name=line["nom"],
				priority=Priority(line["priorité"]),
				start=hour_or_none(line["début"]),
				end=hour_or_none(line["fin"]),
				days=frozenset(DAYS.index(day.strip()) for day in line["jours"].split(",") if day.strip()),
				modified_at=NEVER,
			)
		)


@then(
	parsers.re(
		r"(?:à partir du « (?P<since>[^»]+) », )?« (?P<name>[^»]+) » chevauche"
		r" (?:rien|« (?P<other>[^»]+) » le « (?P<instant>[^»]+) »)"
	)
)
def overlaps(events: list[Event], since: str | None, name: str, other: str | None, instant: str | None) -> None:
	(place,) = [event for event in events if event.name == name]
	others = [event for event in events if event is not place]
	found = overlap(place, others, since=hour_or_none((since) or ("")))
	obtained = None
	if found is not None:
		obtained = (found[0].name, f"{found[1]:%Y-%m-%d %H:%M}")
	expected = None
	if other is not None:
		expected = (other, instant)
	assert obtained == expected
