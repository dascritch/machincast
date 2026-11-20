"""Scénarios de l'API REST v1 de l'intranet, en lecture (https://github.com/dascritch/machincast/issues/540), et de
son accueil en direct (https://github.com/dascritch/machincast/issues/541), et de son calendrier
(https://github.com/dascritch/machincast/issues/542).

Les requêtes passent directement à l'application ASGI (tests.asgi_client), sur la base de test, au rôle
machincast_intranet. Machin player est imité par une vraie socket d'état (machincast.player.state.StateSocket).
"""

import html
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
from machincast.intranet.pages import Pages
from machincast.intranet.portal import Portal
from machincast.player.state import StateSocket
from tests.asgi_client import Answer, call
from tests.database_fixtures import sample_database_parameters
from tests.interface_steps import NAME, Connection, identifier

scenarios("intranet_api.feature", "intranet_home.feature", "intranet_calendar.feature")


@dataclass
class Api:
	application: Intranet
	socket_path: Path
	now: datetime
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
	routes = {
		**portal.routes(),
		**ApiV1(portal, connect, socket_path, clock).routes(),
		**Pages(portal, connect, socket_path, "Radio Thune", clock).routes(),
	}
	built = Api(Intranet(routes), socket_path, clock.now())
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
	ends = api.now + timedelta(seconds=167.5)
	published = dict(
		_sound(current), public_text=f"Radio Thune — {current}", position=12.5, estimated_end=ends.isoformat()
	)
	following_sound = dict(_sound(titles[0]), estimated_start=ends.isoformat())
	upcoming = []
	for title in titles[1:]:
		upcoming.append(_sound(title))
	api.player = StateSocket(api.socket_path)
	api.player.open_()
	api.player.publish(
		{"version": 3, "state": "playing", "current": published, "next": following_sound, "upcoming": upcoming}
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
	assert found["name"] == name
	assert datetime.fromisoformat(found["start"]) == datetime.fromisoformat(start).astimezone()
	assert datetime.fromisoformat(found["end"]) == datetime.fromisoformat(end).astimezone()


@then("l'API répond 200, en direct « stopped », sans sonore en cours ni à venir")
def stopped(api: Api) -> None:
	found = _json(api)
	assert (found["state"], found["current"], found["next"]) == ("stopped", None, [])


def _page(api: Api) -> str:
	answer = _answer(api)
	assert answer.header("content-type") == "text/html; charset=utf-8", answer.headers
	return answer.text()


def _element(api: Api, identifier: str) -> str:
	"""Le texte de l'élément d'identifiant donné, sans balise."""
	found = re.search(rf'id="{identifier}"[^>]*>(?P<text>[^<]*)<', _page(api))
	assert found is not None, identifier
	return html.unescape(found["text"])


@then(parsers.parse("l'API répond {status:d}, vers « {address} »"))
def redirected(api: Api, status: int, address: str) -> None:
	assert (_answer(api).status, _answer(api).header("location")) == (status, address)


@then(parsers.parse("l'API répond {status:d}, de type « {kind} »"))
def typed(api: Api, status: int, kind: str) -> None:
	assert (_answer(api).status, _answer(api).header("content-type")) == (status, kind)


@then(parsers.parse("l'API répond 200, une page « {title} » du gabarit de « {radio} », « {state} », pour « {user} »"))
def templated(api: Api, title: str, radio: str, state: str, user: str) -> None:
	assert _answer(api).status == 200, _answer(api).text()
	text = _page(api)
	assert f"<title>{title} — Machin intranet</title>" in text
	assert f'<span class="radio">{radio}</span>' in text
	assert '<span class="machin">Machin intranet</span>' in text
	assert _element(api, "etat") == state
	assert f'<span class="discret">{user}</span>' in text


@then(parsers.parse("le bandeau mène à « {address} » « {label} », la page en cours, et permet de se déconnecter"))
def navigation(api: Api, address: str, label: str) -> None:
	text = _page(api)
	assert f'<a href="{address}" aria-current="page">{label}</a>' in text
	assert '<form method="post" action="/logout"><button type="submit">Se déconnecter</button></form>' in text


@then("la page charge /static/intranet.css et /static/intranet.js, sans script dans la page")
def resources(api: Api) -> None:
	text = _page(api)
	assert '<link rel="stylesheet" href="/static/intranet.css">' in text
	assert re.findall(r"<script[^>]*>", text) == ['<script src="/static/intranet.js" defer>']
	assert "default-src 'self'" in str(_answer(api).header("content-security-policy"))


@then(parsers.re(r"les sections de l'accueil sont, dans l'ordre, (?P<names>.+)"))
def sections(api: Api, names: str) -> None:
	text = _page(api)
	positions = []
	for name in NAME.findall(names):
		found = re.search(rf'(?:class|id)="{name}"', text)
		assert found is not None, name
		positions.append(found.start())
	assert positions == sorted(positions)


@then("l'accueil montre :")
def shown(api: Api, datatable: list[list[str]]) -> None:
	for element, text in datatable[1:]:
		assert _element(api, element.strip()) == text.strip(), element


@then(parsers.re(r"les décomptes (?P<names>.+) ont leur limite, pour le script"))
def limits(api: Api, names: str) -> None:
	for element in NAME.findall(names):
		found = re.search(rf'id="{element}" class="decompte" data-limite="(?P<limit>[^"]+)"', _page(api))
		assert found is not None, element
		assert datetime.fromisoformat(found["limit"]) > api.now


@then(parsers.re(r"l'airplay de l'accueil est (?P<lines>.+)"))
def recent(api: Api, lines: str) -> None:
	found = re.search(r'<ol id="airplay">(?P<items>.*?)</ol>', _page(api))
	assert found is not None
	items = []
	for item in re.findall(r"<li>([^<]*)</li>", found["items"]):
		items.append(html.unescape(item))
	assert items == NAME.findall(lines)


def _local(moment: str) -> datetime:
	return datetime.fromisoformat(moment).astimezone()


def _calendar_entry(api: Api, name: str) -> dict[str, Any]:
	for entry in _json(api)["events"]:
		if entry["name"] == name:
			return dict(entry)
	raise AssertionError(name)


@then(
	parsers.re(r"l'API répond 200, avec le calendrier du « (?P<first>[^»]+) » au « (?P<last>[^»]+) » : (?P<names>.+)")
)
def calendar(api: Api, first: str, last: str, names: str) -> None:
	assert _answer(api).status == 200, _answer(api).text()
	found = _json(api)
	assert (found["from"], found["to"]) == (first, last)
	listed = []
	for entry in found["events"]:
		listed.append(entry["name"])
	assert listed == NAME.findall(names)


@then(parsers.re(r"« (?P<name>[^»]+) » est à l'antenne (?P<moments>de « .+)"))
def on_air_moments(api: Api, name: str, moments: str) -> None:
	given = NAME.findall(moments)
	expected = []
	for start, end in zip(given[::2], given[1::2], strict=True):
		expected.append((_local(start), _local(end)))
	found = []
	for moment in _calendar_entry(api, name)["on_air"]:
		found.append((datetime.fromisoformat(moment["start"]), datetime.fromisoformat(moment["end"])))
	assert found == expected


@then(parsers.parse("« {name} », de « {start} » à « {end} », est couverte, sans moment à l'antenne"))
def covered(api: Api, name: str, start: str, end: str) -> None:
	entry = _calendar_entry(api, name)
	assert (datetime.fromisoformat(entry["start"]), datetime.fromisoformat(entry["end"])) == (
		_local(start),
		_local(end),
	)
	assert (entry["covered"], entry["on_air"], entry["skipped"]) == (True, [], False)


def _vevents(api: Api) -> list[str]:
	return re.findall(r'<li class="vevent h-event[^"]*">.*?</li>', _page(api))


@then(parsers.parse("l'API répond 200, une page hCalendar de {count:d} occurrences"))
def hcalendar(api: Api, count: int) -> None:
	assert _answer(api).status == 200
	assert '<ol class="vcalendar">' in _page(api)
	assert len(_vevents(api)) == count


@then(parsers.parse("l'occurrence hCalendar « {name} » est de « {start} » à « {end} », « {category} », couverte"))
def vevent(api: Api, name: str, start: str, end: str, category: str) -> None:
	for found in _vevents(api):
		if f'<span class="summary p-name">{name}</span>' in found:
			assert "couvert" in found.split(">", 1)[0]
			assert f'class="dtstart dt-start" datetime="{_local(start).isoformat()}"' in found
			assert f'class="dtend dt-end" datetime="{_local(end).isoformat()}"' in found
			assert f'<span class="category p-category">{category}</span>' in found
			return
	raise AssertionError(name)


@then(parsers.parse("la page est titrée « {title} »"))
def titled(api: Api, title: str) -> None:
	assert f"<h1>{title}</h1>" in _page(api)


@then(parsers.parse("la page mène à la semaine précédente « {before} » et à la suivante « {after} »"))
def weeks(api: Api, before: str, after: str) -> None:
	text = _page(api)
	assert f'rel="prev" href="{before}"' in text
	assert f'rel="next" href="{after}"' in text


@then(parsers.re(r"le « (?P<day>[^»]+) » montre (?P<names>.+)"))
def day_shows(api: Api, day: str, names: str) -> None:
	found = re.search(rf"<h2>{day}</h2>\n<ol class=\"vcalendar\">(?P<items>.*?)</ol>", _page(api), re.DOTALL)
	assert found is not None, day
	assert re.findall(r'<span class="summary p-name">([^<]*)</span>', found["items"]) == NAME.findall(names)


@then("la page mène au guide de l'antenne et à la spécification de l'intranet, à la version installée")
def documentation(api: Api) -> None:
	text = _page(api)
	guide = re.search(r'<a id="guide" href="(?P<address>[^"]+)"', text)
	specification = re.search(r'<a id="specification" href="(?P<address>[^"]+)"', text)
	assert (guide is not None) and (specification is not None)
	assert re.fullmatch(
		r"https://github.com/dascritch/machincast/blob/(main|v[\d.]+)/doc/fr/utilisateur/README.md", guide["address"]
	)
	assert specification["address"] == guide["address"].replace(
		"doc/fr/utilisateur/README.md", "doc/fr/spec.md#13-intranet-et-api"
	)
