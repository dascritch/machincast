"""Scénarios de log_incident, l'avertissement d'un incident grave (https://github.com/dascritch/machincast/issues/592).

Le plugin est abonné aux points des plugins chargés (machincast.plugins.active) d'un binaire, que tests/conftest.py
remet à vide après chaque scénario ; le gestionnaire du journal est celui que machincast.plugins.load installe. Les
notifications sont attendues (Points.close) avant d'être lues.
"""

import logging
from collections.abc import Iterator, Mapping
from typing import Any

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import plugins
from machincast.database import Role, open_connection
from machincast.player.saving import record
from machincast.plugins import incidents
from tests.database_fixtures import sample_database_parameters
from tests.plugin_steps import Recorder, subscribe_failing

scenarios("plugin_incidents.feature")

Connection = psycopg.Connection[tuple[object, ...]]
LEVELS = {"l'incident": "incident", "l'alerte": "warning", "l'information": "info"}


@pytest.fixture
def playback(empty_database: Connection) -> Iterator[Connection]:
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		yield connection


def _identifier(database: Connection, table: str, name: str) -> int:
	if table == "events":
		found = database.execute("SELECT id FROM events WHERE internal_name = %s", (name,)).fetchone()
	else:
		found = database.execute("SELECT id FROM sounds WHERE title = %s", (name,)).fetchone()
	assert found is not None
	return int(str(found[0]))


def _received(recorder: Recorder) -> list[dict[str, Any]]:
	plugins.active().points.close()
	return recorder.of(incidents.POINT)


@given(parsers.parse("un plugin « {name} » chargé dans « {executable} », abonné à « log_incident »"))
def loaded(recorder: Recorder, name: str, executable: str) -> None:
	plugins._active = plugins.Loaded(executable=executable)
	incidents.install()
	recorder.subscribe(plugins.active().points, name, [incidents.POINT])


@given(parsers.parse("un plugin « {name} », qui échoue à « log_incident »"))
def failing(name: str) -> None:
	subscribe_failing(plugins.active().points, name, [incidents.POINT])


@given(parsers.parse("un plugin « {name} », qui consigne une erreur au journal à « log_incident »"))
def talkative(name: str) -> None:
	def complain(data: Mapping[str, Any]) -> None:
		logging.getLogger("machincast_bavard").error("la messagerie ne répond pas")

	plugins.active().points.subscribe(name, incidents.POINT, complain)


@given(parsers.parse("le sonore « {sound} » de l'événement « {event} »"))
def sound_and_event(empty_database: Connection, sound: str, event: str) -> None:
	empty_database.execute(
		"INSERT INTO sounds (type, stream_url, title) VALUES ('stream', 'https://flux.exemple', %s)", (sound,)
	)
	empty_database.execute(
		"INSERT INTO events (internal_name, priority) VALUES (%s, 'background_programming')", (event,)
	)


@when(
	parsers.re(
		r"Machin player consigne (?P<level>l'incident|l'alerte|l'information) « (?P<kind>[^»]+) » :"
		r" « (?P<message>[^»]+) »(?:, pour le sonore « (?P<sound>[^»]+) » et l'événement « (?P<event>[^»]+) »)?"
	)
)
def consigned(
	empty_database: Connection,
	playback: Connection,
	level: str,
	kind: str,
	message: str,
	sound: str | None,
	event: str | None,
) -> None:
	sound_id = None
	event_id = None
	if sound is not None:
		sound_id = _identifier(empty_database, "sounds", sound)
	if event is not None:
		event_id = _identifier(empty_database, "events", event)
	record(playback, LEVELS[level], kind, message, sound=sound_id, event=event_id)


@when(
	parsers.re(
		r"le journal de « (?P<executable>[^»]+) » consigne (?P<level>l'erreur|l'avertissement) « (?P<message>[^»]+) »"
		r" du module « (?P<module>[^»]+) »"
	)
)
def logged(executable: str, level: str, message: str, module: str) -> None:
	assert plugins.active().executable == executable
	logger = logging.getLogger(module)
	if level == "l'erreur":
		logger.error(message)
	else:
		logger.warning(message)


@then(parsers.parse("le plugin « {name} » a été prévenu {count:d} fois"))
def received_count(recorder: Recorder, name: str, count: int) -> None:
	assert len(_received(recorder)) == count, recorder.received


@then(
	parsers.parse(
		"il a reçu de « {executable} » l'incident de niveau « {level} », de nature « {kind} », au message « {message} »"
	)
)
def received(recorder: Recorder, executable: str, level: str, kind: str, message: str) -> None:
	data = _received(recorder)[0]
	assert (data["executable"], data["level"], data["kind"], data["message"]) == (executable, level, kind, message)
	assert data["instant"] is not None


@then(parsers.parse("l'incident concerne le sonore « {sound} » et l'événement « {event} », sans banque"))
def references(empty_database: Connection, recorder: Recorder, sound: str, event: str) -> None:
	assert _received(recorder)[0]["references"] == {
		"sound": _identifier(empty_database, "sounds", sound),
		"bank": None,
		"event": _identifier(empty_database, "events", event),
	}
