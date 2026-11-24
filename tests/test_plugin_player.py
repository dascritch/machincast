"""Scénarios des points d'extension de Machin player (https://github.com/dascritch/machincast/issues/589).

Les étapes de la diffusion viennent de tests/broadcast_steps.py ; le plugin est un abonné aux points d'un registre
(machincast.plugins.points.Points), que la diffusion reçoit comme dans Machin player. La simulation, elle, ne reçoit
jamais de points : le plugin y est abonné aux points des plugins chargés (machincast.plugins.active), que
tests/conftest.py remet à vide après chaque scénario.
"""

import threading
from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import plugins
from machincast.database import Role, open_connection
from machincast.player.simulation import simulate
from machincast.plugins.points import Points
from tests.broadcast_steps import Bench, Connection, hour
from tests.database_fixtures import sample_database_parameters
from tests.plugin_steps import Recorder, core_points, subscribe_failing

scenarios("plugin_player.feature")

POINTS = core_points("player.")
"""Les points notifiés de Machin player (https://github.com/dascritch/machincast/issues/589) ; « player.before_choice »,
demandé à chaque choix, l'est aussi en simulation (tests/features/rundown.feature,
https://github.com/dascritch/machincast/issues/640)."""
POINTS.remove("player.before_choice")
# « player.sound_gain » est demandé avant chaque fichier joué (tests/features/sound_gain.feature,
# https://github.com/dascritch/machincast/issues/643).
POINTS.remove("player.sound_gain")


@pytest.fixture
def released() -> Iterator[threading.Event]:
	"""Ce qui relâche le plugin lent ; relâché à la fin du scénario, quoi qu'il arrive."""
	event = threading.Event()
	yield event
	event.set()


def _points(bench: Bench) -> Points:
	if bench.points is None:
		bench.points = Points()
	return bench.points


def _named(data: Mapping[str, Any]) -> str:
	"""Le nom de ce dont parle le point : l'événement ou la séquence, le titre du sonore ; rien pour le service."""
	if "title" in data:
		return str(data["title"])
	if "name" in data:
		return str(data["name"])
	return ""


def _found(recorder: Recorder, point: str, name: str) -> dict[str, Any]:
	for data in recorder.of(point):
		if _named(data) == name:
			return data
	raise AssertionError(f"{point} de {name} : {recorder.received}")


def _instant(text: str) -> str:
	return datetime.fromisoformat(text).astimezone().isoformat()


@given("un plugin abonné à chaque point de Machin player")
def subscribed(bench: Bench, recorder: Recorder) -> None:
	recorder.subscribe(_points(bench), "témoin", POINTS)


@given(parsers.parse("un plugin « {name} », bloqué à chaque point de Machin player jusqu'à la fin du scénario"))
def slow(bench: Bench, recorder: Recorder, released: threading.Event, name: str) -> None:
	def blocked(point: str) -> Any:
		def receive(data: Mapping[str, Any]) -> None:
			released.wait()
			recorder.received.append((point, dict(data)))

		return receive

	for point in POINTS:
		_points(bench).subscribe(name, point, blocked(point))


@given(parsers.parse("un plugin « {name} », qui échoue à chaque point de Machin player"))
def failing(bench: Bench, name: str) -> None:
	subscribe_failing(_points(bench), name, POINTS)


@given("un plugin chargé, abonné à chaque point de Machin player")
def loaded(recorder: Recorder) -> None:
	recorder.subscribe(plugins.active().points, "témoin", POINTS)


@when(parsers.parse("la diffusion de {start} à {end} est simulée"))
def simulated(empty_database: Connection, tmp_path: Path, start: str, end: str) -> None:
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		simulate(connection, tmp_path / "simulation", hour(f"2026-10-14 {start}"), hour(f"2026-10-14 {end}"))
	plugins.active().points.close()


@when("les plugins ont fini")
def finished(bench: Bench, released: threading.Event) -> None:
	released.set()
	_points(bench).close()


@then("le plugin a été prévenu, dans l'ordre :")
def in_order(bench: Bench, recorder: Recorder, datatable: list[list[str]]) -> None:
	_points(bench).close()
	expected = []
	for point, name in datatable[1:]:
		expected.append((point.strip(), name.strip()))
	received = []
	for point, data in recorder.received:
		received.append((point, _named(data)))
	assert received == expected


@then(
	parsers.re(
		r"« player.event_start » de « (?P<name>[^»]+) » dit : (?:nom public « (?P<public>[^»]+) »|sans nom public),"
		r" priorité « (?P<priority>[^»]+) », (?:de « (?P<start>[^»]+) » à « (?P<end>[^»]+) »|sans début ni fin)"
	)
)
def event_said(
	recorder: Recorder, name: str, public: str | None, priority: str, start: str | None, end: str | None
) -> None:
	data = _found(recorder, "player.event_start", name)
	expected_start = None
	expected_end = None
	if start is not None:
		expected_start = _instant(start)
	if end is not None:
		expected_end = _instant(end)
	assert (data["public_name"], data["priority"], data["start"], data["end"]) == (
		public,
		priority,
		expected_start,
		expected_end,
	)
	stopped = _found(recorder, "player.event_stop", name)
	assert stopped["event"] == data["event"]


@then(parsers.parse("« player.sequence_start » de « {name} » dit l'événement « {event} »"))
def sequence_said(recorder: Recorder, name: str, event: str) -> None:
	assert _found(recorder, "player.sequence_start", name)["event_name"] == event


@then(
	parsers.re(
		r"« player.sound_stop » de « (?P<name>[^»]+) » dit : (?P<how>coupé|terminé), (?P<played>\d+) secondes jouées,"
		r" de la position (?P<start>\d+) à la position (?P<end>\d+), sans erreur"
	)
)
def sound_stop_said(recorder: Recorder, name: str, how: str, played: str, start: str, end: str) -> None:
	data = _found(recorder, "player.sound_stop", name)
	assert (data["cut"], data["played"], data["start_position"], data["end_position"], data["error"]) == (
		how == "coupé",
		float(played),
		float(start),
		float(end),
		None,
	)


@then(
	parsers.parse(
		"« player.sound_start » de « {name} » dit : {duration:d} secondes, de la position {start:d},"
		" dans l'événement « {event} »"
	)
)
def sound_start_said(
	empty_database: Connection, recorder: Recorder, name: str, duration: int, start: int, event: str
) -> None:
	data = _found(recorder, "player.sound_start", name)
	found = empty_database.execute("SELECT id FROM events WHERE internal_name = %s", (event,)).fetchone()
	assert found is not None
	assert (data["duration"], data["start_position"], data["event"], data["stream"]) == (
		float(duration),
		float(start),
		found[0],
		False,
	)


@then("« player.service_stop » dit : sans erreur")
def service_stop_said(recorder: Recorder) -> None:
	assert recorder.of("player.service_stop")[0]["error"] is None


@then("la diffusion a avancé sans attendre les plugins")
def without_waiting(recorder: Recorder) -> None:
	assert recorder.received == []


@then(parsers.parse("le plugin « {name} » a été prévenu de « {point} » {count:d} fois"))
def received_count(recorder: Recorder, name: str, point: str, count: int) -> None:
	assert len(recorder.of(point)) == count


@then("le plugin chargé n'a été prévenu de rien")
def nothing(recorder: Recorder) -> None:
	assert recorder.received == []
