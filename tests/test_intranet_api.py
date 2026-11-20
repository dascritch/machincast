"""Scénarios de l'API REST v1 de l'intranet, en lecture (https://github.com/dascritch/machincast/issues/540).

Les requêtes passent directement à l'application ASGI (tests.asgi_client), sur la base de test, au rôle
machincast_intranet. Machin player est imité par une vraie socket d'état (machincast.player.state.StateSocket).
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.rows import TupleRow
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.clock import FixedClock
from machincast.configuration import Intranet as Settings
from machincast.database import Role, open_connection
from machincast.intranet import sessions
from machincast.intranet.api import ApiV1
from machincast.intranet.app import Intranet
from machincast.intranet.portal import Portal
from machincast.player.state import StateSocket
from tests.asgi_client import Answer, call
from tests.database_fixtures import sample_database_parameters
from tests.interface_steps import NAME, Connection, identifier

scenarios("intranet_api.feature")


@dataclass
class Api:
	application: Intranet
	socket_path: Path
	answer: Answer | None = None
	player: StateSocket | None = None
	extra: dict[str, Any] = field(default_factory=dict)


def connect() -> psycopg.Connection[TupleRow]:
	socket, database = sample_database_parameters()
	return open_connection(socket, database, Role.INTRANET)


@pytest.fixture
def socket_path(tmp_path: Path) -> Path:
	directory = tmp_path / "lecture"
	directory.mkdir(mode=0o700)
	return directory / "lecture.sock"


@given(parsers.parse("l'API de l'intranet sur la base de test, à « {moment} »"), target_fixture="api")
def application(socket_path: Path, moment: str) -> Iterator[Api]:
	clock = FixedClock(datetime.fromisoformat(moment).astimezone())
	portal = Portal(Settings(enabled=True), connect)
	built = Api(Intranet({**portal.routes(), **ApiV1(portal, connect, socket_path, clock).routes()}), socket_path)
	yield built
	if built.player is not None:
		built.player.shut_down()


def _session(empty_database: Connection, name: str, value: str, state: str) -> None:
	if state == "valid":
		empty_database.execute(
			"INSERT INTO api_sessions (user_id, token_hash, state, validated_at, expires_at)"
			" SELECT id, %s, 'valid', clock_timestamp(), clock_timestamp() + interval '1 hour' FROM api_users"
			" WHERE name = %s",
			(sessions.fingerprint(value), name),
		)
		return
	empty_database.execute(
		"INSERT INTO api_sessions (user_id, token_hash, code, validate_before)"
		" SELECT id, %s, '123456', clock_timestamp() + interval '10 minutes' FROM api_users WHERE name = %s",
		(sessions.fingerprint(value), name),
	)


@given(parsers.parse("une session valide de « {name} », de jeton « {value} »"), target_fixture="token")
def valid_session(empty_database: Connection, name: str, value: str) -> str:
	_session(empty_database, name, value, "valid")
	return value


@given(parsers.parse("une session à valider de « {name} », de jeton « {value} »"))
def pending_session(empty_database: Connection, name: str, value: str) -> None:
	_session(empty_database, name, value, "pending")


@given(parsers.parse("le sonore « {title} » est supprimé"))
def deleted_sound(empty_database: Connection, title: str) -> None:
	empty_database.execute("UPDATE sounds SET deleted_at = clock_timestamp() WHERE title = %s", (title,))


@given(parsers.parse("l'événement « {event} » joue la séquence « {sequence} »"))
def plays_sequence(empty_database: Connection, event: str, sequence: str) -> None:
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, sequence_id) VALUES (%s, 1, %s)",
		(
			identifier(empty_database, "events", "internal_name", event),
			identifier(empty_database, "sequences", "internal_name", sequence),
		),
	)


@given("les entrées du log :")
def log_entries(empty_database: Connection, datatable: list[list[str]]) -> None:
	for level, kind, message in datatable[1:]:
		empty_database.execute(
			"INSERT INTO log (level, kind, message) VALUES (%s, %s, %s)", (level.strip(), kind.strip(), message.strip())
		)


def _sound(title: str) -> dict[str, Any]:
	return {"sound_id": 1, "type": "file", "artist": None, "title": title, "duration": 180.0, "event": "Journal"}


@given(parsers.re(r"Machin player qui publie « (?P<current>[^»]+) » en cours, puis (?P<following>.+)"))
def player(api: Api, current: str, following: str) -> None:
	titles = NAME.findall(following)
	published = dict(_sound(current), public_text=f"Radio Thune — {current}", position=12.5)
	upcoming = []
	for title in titles[1:]:
		upcoming.append(_sound(title))
	api.player = StateSocket(api.socket_path)
	api.player.open_()
	api.player.publish(
		{"version": 3, "state": "playing", "current": published, "next": _sound(titles[0]), "upcoming": upcoming}
	)


def _ask(api: Api, request: str, token: str | None) -> None:
	method, path = request.split(" ", 1)
	headers = {}
	if token is not None:
		headers["authorization"] = f"Bearer {token}"
	api.answer = call(api.application, method, path, headers=headers)


@when(parsers.parse("je demande à l'API « {request} », sans jeton"))
def ask_without(api: Api, request: str) -> None:
	_ask(api, request, None)


@when(parsers.parse("je demande à l'API « {request} », avec le jeton « {value} »"))
def ask_with(api: Api, request: str, value: str) -> None:
	_ask(api, request, value)


@when(parsers.re(r"je demande à l'API « (?P<request>[^»]+) »$"))
def ask(api: Api, token: str, request: str) -> None:
	_ask(api, request, token)


@when(parsers.parse("je demande à l'API la page suivante des « {kind} »"))
def ask_next(api: Api, token: str, kind: str) -> None:
	following = _json(api)["next"]
	_ask(api, f"GET /api/v1/{kind}?limit=1&after={following}", token)


CARDS = {
	"la banque": ("banks", "internal_name"),
	"l'événement": ("events", "internal_name"),
	"la séquence": ("sequences", "internal_name"),
}


@when(parsers.re(r"je demande à l'API la fiche de (?P<kind>la banque|l'événement|la séquence) « (?P<name>[^»]+) »"))
def ask_card(api: Api, token: str, empty_database: Connection, kind: str, name: str) -> None:
	table, column = CARDS[kind]
	_ask(api, f"GET /api/v1/{table}/{identifier(empty_database, table, column, name)}", token)


def _answer(api: Api) -> Answer:
	assert api.answer is not None
	return api.answer


def _json(api: Api) -> Any:
	answer = _answer(api)
	assert answer.header("content-type") == "application/json", answer.headers
	return json.loads(answer.body)


@then(parsers.re(r"l'API répond (?P<status>\d+)$"))
def status(api: Api, status: str) -> None:
	assert _answer(api).status == int(status), _answer(api).text()


@then(parsers.parse("l'API répond {status:d}, avec l'erreur « {message} »"))
def failed(api: Api, status: int, message: str) -> None:
	assert _answer(api).status == status
	assert _json(api) == {"error": message}


@then(parsers.parse("la réponse demande un jeton « {scheme} »"))
def challenge(api: Api, scheme: str) -> None:
	assert str(_answer(api).header("www-authenticate")).startswith(scheme)


@then(parsers.re(r"l'API répond 200, avec les « (?P<kind>\w+) » de titres (?P<titles>.+)"))
def listed(api: Api, kind: str, titles: str) -> None:
	assert _answer(api).status == 200
	found = []
	for row in _json(api)[kind]:
		found.append(row["title"])
	assert found == NAME.findall(titles)


@then(parsers.parse("la page suivante commence après le sonore « {title} »"))
def next_page(api: Api, empty_database: Connection, title: str) -> None:
	assert _json(api)["next"] == identifier(empty_database, "sounds", "title", title)


@then("la réponse n'a pas de page suivante")
def last_page(api: Api) -> None:
	assert _json(api)["next"] is None


@then(parsers.re(r"l'API répond 200, avec la fiche (?P<pairs>.+)"))
def card(api: Api, pairs: str) -> None:
	assert _answer(api).status == 200, _answer(api).text()
	values = NAME.findall(pairs)
	found = _json(api)
	for key, value in zip(values[::2], values[1::2], strict=True):
		assert found[key] == value, (key, found[key])


@then(parsers.re(r"ses éléments sont (?P<names>.+)"))
def items(api: Api, names: str) -> None:
	found = []
	for item in _json(api)["items"]:
		found.append(item["name"])
	assert found == NAME.findall(names)


@then(parsers.re(r"l'API répond 200, avec les incidents (?P<kinds>.+)"))
def incidents(api: Api, kinds: str) -> None:
	assert _answer(api).status == 200
	found = []
	for entry in _json(api)["incidents"]:
		found.append(entry["kind"])
	assert found == NAME.findall(kinds)


@then(parsers.parse("l'API répond 200, en direct « {state} », texte public « {text} »"))
def on_air(api: Api, state: str, text: str) -> None:
	found = _json(api)
	assert (_answer(api).status, found["state"], found["public_text"]) == (200, state, text)
	assert found["time"].startswith("2026-11-20T10:00:00")


@then(parsers.parse("le sonore en cours est « {title} »"))
def current(api: Api, title: str) -> None:
	found = _json(api)["current"]
	assert (found["title"], found["position"], found["duration"]) == (title, 12.5, 180.0)


@then(parsers.re(r"les sonores suivants sont (?P<titles>.+)"))
def following(api: Api, titles: str) -> None:
	found = []
	for sound in _json(api)["next"]:
		found.append(sound["title"])
	assert found == NAME.findall(titles)


@then(parsers.re(r"les derniers sonores sont (?P<titles>.+)"))
def previous(api: Api, titles: str) -> None:
	found = []
	for play in _json(api)["previous"]:
		found.append(play["title"])
	assert found == NAME.findall(titles)


@then(
	parsers.re(
		r"l'événement (?P<which>précédent|en cours|suivant) est « (?P<name>[^»]+) », de « (?P<start>[^»]+) » à « (?P<end>[^»]+) »"
	)
)
def event(api: Api, which: str, name: str, start: str, end: str) -> None:
	key = {"précédent": "previous", "en cours": "current", "suivant": "next"}[which]
	found = _json(api)["events"][key]
	assert (found["name"], found["start"], found["end"]) == (name, start, end)


@then("l'API répond 200, en direct « stopped », sans sonore en cours ni à venir")
def stopped(api: Api) -> None:
	found = _json(api)
	assert (found["state"], found["current"], found["next"]) == ("stopped", None, [])
