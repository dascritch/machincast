"""Scénarios de l'API REST v1 de l'intranet, en lecture (https://github.com/dascritch/machincast/issues/540), et de
son accueil en direct (https://github.com/dascritch/machincast/issues/541), et de son calendrier
(https://github.com/dascritch/machincast/issues/542).

Les requêtes passent directement à l'application ASGI (tests.asgi_client), sur la base de test, au rôle
machincast_webserver. Machin player est imité par une vraie socket d'état (machincast.player.state.StateSocket).
"""

import html
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.rows import TupleRow
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import __version__
from machincast.clock import FixedClock
from machincast.configuration import PROJECT_DIRECTORY
from machincast.configuration import Intranet as Settings
from machincast.database import Role, open_connection
from machincast.player.state import StateSocket
from machincast.shortcut import ICON
from machincast.webserver import agenda, home, sessions
from machincast.webserver.api import ApiV1
from machincast.webserver.app import Intranet
from machincast.webserver.pages import Pages
from machincast.webserver.portal import Portal
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
	pages = Pages(portal, connect, socket_path, "Radio Thune", clock)
	routes = {
		**portal.routes(),
		**ApiV1(portal, connect, socket_path, clock).routes(),
		**pages.routes(),
	}
	built = Api(Intranet(routes), socket_path, clock.now(), extra={"pages": pages})
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


# ─── Le schéma OpenAPI (https://github.com/dascritch/machincast/issues/602) ───


@then(parsers.parse("l'API répond 200, un schéma OpenAPI 3.1 « {title} », de la version installée"))
def openapi_schema(api: Api, title: str) -> None:
	assert _answer(api).status == 200, _answer(api).text()
	schema = _json(api)
	assert schema["openapi"].startswith("3.1."), schema["openapi"]
	assert (schema["info"]["title"], schema["info"]["version"]) == (title, __version__)


@then("le schéma décrit les chemins :")
def openapi_paths(api: Api, datatable: list[list[str]]) -> None:
	found = []
	for path, operations in sorted(_json(api)["paths"].items()):
		for method in sorted(operations):
			found.append([path, method])
	expected = []
	for path, method in datatable[1:]:
		expected.append([path.strip(), method.strip()])
	assert found == expected


@then(parsers.parse("le schéma accepte le jeton en « Authorization: Bearer » ou dans le cookie « {name} »"))
def openapi_security(api: Api, name: str) -> None:
	schema = _json(api)
	schemes = schema["components"]["securitySchemes"]
	assert schemes["bearer"] == {"type": "http", "scheme": "bearer"}
	assert schemes["cookie"] == {"type": "apiKey", "in": "cookie", "name": name}
	assert schema["security"] == [{"bearer": []}, {"cookie": []}]


@then(parsers.re(r"le schéma donne à « (?P<method>[A-Z]+) (?P<path>[^»]+) » les paramètres (?P<names>.+)"))
def openapi_parameters(api: Api, method: str, path: str, names: str) -> None:
	operation = _json(api)["paths"][path][method.lower()]
	found = []
	for parameter in operation["parameters"]:
		assert parameter["in"] == "query"
		found.append(parameter["name"])
	assert found == re.findall(r"« ([^»]+) »", names)


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
	# L'accueil a son propre titre, « MachinCast - » et la radio (https://github.com/dascritch/machincast/issues/598).
	full = f"{title} — Machin webserver"
	if title.startswith("MachinCast - "):
		full = title
	assert f"<title>{full}</title>" in text, text
	assert f'<span class="radio">{radio}</span>' in text
	assert '<span class="machin">Machin webserver</span>' in text
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


@then(
	parsers.re(
		r"l'accueil met côte à côte « (?P<a>[^»]+) » et « (?P<b>[^»]+) », puis « (?P<c>[^»]+) » et « (?P<d>[^»]+) »"
	)
)
def side_by_side(api: Api, a: str, b: str, c: str, d: str) -> None:
	pairs = []
	for pair in re.findall(r'<div class="paire">(.*?)</div>', _page(api), re.DOTALL):
		pairs.append(re.findall(r'<section class="([^"]+)">', pair))
	assert pairs == [[a, b], [c, d]]


@when(parsers.parse("l'accueil écrit la durée {value}"), target_fixture="written")
def write_duration(value: str) -> str:
	given: object = None
	if value != "inconnue":
		given = float(value)
	return home.duration(given)


@then(parsers.parse("il écrit « {text} »"))
def written_as(written: str, text: str) -> None:
	assert written == text


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


DAY_NAME = re.compile(r'<text class="nom-du-jour(?P<today>[^"]*)"[^>]*>(?P<name>[^<]*)</text>')
BLOCK = re.compile(
	r'<svg class="bloc (?P<priority>[^"]+)" x="(?P<x>[\d.]+)%" y="(?P<y>[^"]+)" width="(?P<width>[\d.]+)%"'
	r' height="(?P<height>[^"]+)">(?P<inside>.*?)</svg>',
	re.DOTALL,
)
SUMMARY = re.compile(r'<span class="summary p-name">([^<]*)</span>')
PERCENT = r'="(?P<value>[\d.]+)%"'
MINUTES = 24 * 60


def _days(api: Api) -> list[str]:
	names = []
	for found in DAY_NAME.finditer(_page(api)):
		names.append(html.unescape(found["name"]))
	return names


def _group(api: Api, kind: str, day: str) -> str:
	"""Les blocs d'un jour : ceux de ses heures (« jour »), ou de sa bande de la journée entière (« bande »)."""
	found = re.search(
		rf'<g class="{kind}[^"]*" aria-label="{re.escape(day)}">(?P<inside>.*?)</g>', _page(api), re.DOTALL
	)
	assert found is not None, (kind, day)
	return found["inside"]


def _clock(minutes: float) -> str:
	whole = round(minutes)
	return f"{whole // 60:02d}:{whole % 60:02d}"


def _share(inside: str, name: str, axis: str, length: str) -> list[tuple[float, float]]:
	"""Les moments pleins d'un bloc, en parts de lui-même : de haut en bas (y), ou de gauche à droite (x)."""
	shares = []
	for rectangle in re.findall(r'<rect class="antenne"[^>]*/>', inside):
		start = re.search(f"{axis}{PERCENT}", rectangle)
		size = re.search(f"{length}{PERCENT}", rectangle)
		assert (start is not None) and (size is not None), (name, rectangle)
		shares.append((float(start["value"]) / 100, (float(start["value"]) + float(size["value"])) / 100))
	return shares


def _blocks(inside: str) -> list[tuple[str, re.Match[str]]]:
	"""Les blocs, dans l'ordre, avec leur nom : un événement coupé par un autre en a plusieurs
	(https://github.com/dascritch/machincast/issues/599)."""
	found = []
	for block in BLOCK.finditer(inside):
		names = SUMMARY.findall(block["inside"])
		assert len(names) == 1, block["inside"]
		found.append((html.unescape(names[0]), block))
	return found


def _names(found: list[tuple[str, re.Match[str]]]) -> list[str]:
	names = []
	for name, _block in found:
		names.append(name)
	return names


def _named(found: list[tuple[str, re.Match[str]]], wanted: str) -> re.Match[str]:
	for name, block in found:
		if name == wanted:
			return block
	raise AssertionError(wanted)


@then(parsers.re(r"la grille a pour jours (?P<names>.+)"))
def grid_days(api: Api, names: str) -> None:
	assert _days(api) == NAME.findall(names)


@then(parsers.parse("la grille a pour heures « {first} » à « {last} », et s'ouvre à {opening}"))
def grid_hours(api: Api, first: str, last: str, opening: str) -> None:
	text = _page(api)
	hours = re.findall(r'<text class="heure"[^>]*>(\d\d:\d\d)</text>', text)
	assert (hours[0], hours[-1], len(hours)) == (first, last, 24)
	assert f'id="grille" data-premiere-heure="{int(opening[:2])}"' in text


@then(parsers.parse("le « {day} » est aujourd'hui, l'heure actuelle à {moment}"))
def today(api: Api, day: str, moment: str) -> None:
	text = _page(api)
	marked = []
	for found in DAY_NAME.finditer(text):
		if found["today"] == " aujourdhui":
			marked.append(found["name"])
	assert marked == [day]
	assert f'<g class="jour aujourdhui" aria-label="{day}">' in text
	line = re.search(r'<line class="maintenant" x1="(?P<x>[\d.]+)%"[^>]* y1="(?P<y>[\d.]+)%"', text)
	assert line is not None
	assert round(float(line["x"]) * 7 / 100) == _days(api).index(day)
	assert _clock(float(line["y"]) / 100 * MINUTES) == moment


@then(parsers.re(r"la bande de la journée entière du « (?P<day>[^»]+) » montre (?P<names>.+)"))
def band_shows(api: Api, day: str, names: str) -> None:
	assert _names(_blocks(_group(api, "bande", day))) == NAME.findall(names)


@then(parsers.re(r"les heures du « (?P<day>[^»]+) » montrent (?P<names>.+)"))
def hours_show(api: Api, day: str, names: str) -> None:
	assert _names(_blocks(_group(api, "jour", day))) == NAME.findall(names)


@then(parsers.parse("les heures du « {day} » ne montrent rien"))
def hours_empty(api: Api, day: str) -> None:
	assert _blocks(_group(api, "jour", day)) == []


@then("la page n'a aucun attribut style")
def without_style(api: Api) -> None:
	assert re.search(r"\sstyle=", _page(api)) is None


def _fading(inside: str) -> str:
	if 'class="hachures"' in inside:
		return "hachuré"
	if re.search(r'<div class="vevent[^"]* couvert', inside):
		return "oui"
	return "non"


@then(parsers.parse("les heures du « {day} » ont pour blocs :"))
def day_blocks(api: Api, day: str, datatable: list[list[str]]) -> None:
	index = _days(api).index(day)
	found = _blocks(_group(api, "jour", day))
	headers, *rows = datatable
	names = []
	for row in rows:
		names.append(row[0].strip())
	assert _names(found) == names
	for row, (_name, block) in zip(rows, found, strict=True):
		cells = []
		for cell in row:
			cells.append(cell.strip())
		expected = dict(zip(headers, cells, strict=True))
		name = expected.pop("nom")
		width = float(block["width"])
		count = round(100 / 7 / width)
		column = round((float(block["x"]) - index * 100 / 7) / width) + 1
		start = float(block["y"].rstrip("%")) / 100 * MINUTES
		end = start + float(block["height"].rstrip("%")) / 100 * MINUTES
		moments = []
		for top, bottom in _share(block["inside"], name, "y", "height"):
			moments.append(f"{_clock(start + top * (end - start))} – {_clock(start + bottom * (end - start))}")
		assert {
			"priorité": block["priority"],
			"heures": f"{_clock(start)} – {_clock(end)}",
			"colonne": f"{column} sur {count}",
			"à l'antenne": (", ".join(moments)) or ("—"),
			"estompé": _fading(block["inside"]),
		} == expected, name


@then(parsers.parse("le bloc « {name} » du « {day} » dit :"))
def block_says(api: Api, name: str, day: str, docstring: str) -> None:
	inside = _named(_blocks(_group(api, "jour", day)), name)["inside"]
	title = re.search(r'<div class="vevent[^"]*" title="(?P<title>[^"]*)"', inside)
	assert title is not None
	assert html.unescape(title["title"]) == docstring


@then(parsers.re(r"le bloc « (?P<name>[^»]+) » de la bande du « (?P<day>[^»]+) » est à l'antenne (?P<moments>de .+)"))
def band_on_air(api: Api, name: str, day: str, moments: str) -> None:
	inside = _named(_blocks(_group(api, "bande", day)), name)["inside"]
	found = []
	for left, right in _share(inside, name, "x", "width"):
		found.append((_clock(left * MINUTES), _clock(right * MINUTES)))
	assert found == re.findall(r"de (\d\d:\d\d) à (\d\d:\d\d)", moments)


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


# ─── Lisible de loin (https://github.com/dascritch/machincast/issues/598) ───

LOGO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect width="1" height="1"/></svg>\n'


@given(parsers.re(r"l'icône de l'application « (?P<name>[^»]+) »(?P<missing>, qui n'existe pas)?$"))
def application_icon(api: Api, tmp_path: Path, name: str, missing: str | None) -> None:
	path = tmp_path / name
	if missing is None:
		path.write_text(LOGO, encoding="utf-8")
	api.extra["pages"].icon = path


@then("l'horloge et le titre public sont sur la même ligne, le titre à droite")
def clock_line(api: Api) -> None:
	text = _page(api)
	line = re.search(
		r'<div class="ligne-heure">\s*<p class="heure">.*?</p>\s*<p class="texte-public">', text, re.DOTALL
	)
	assert line is not None, text


@then("la feuille de style écrit le temps restant des sonores aussi grand que l'horloge")
def large_countdowns() -> None:
	sheet = (PROJECT_DIRECTORY / "src" / "machincast" / "webserver" / "static" / "intranet.css").read_text(
		encoding="utf-8"
	)
	clock = re.search(r"^\.heure \{[^}]*font-size: ([0-9.]+rem)", sheet, re.MULTILINE)
	countdowns = re.search(
		r"^\.sonore \.decompte, \.prochain \.decompte \{[^}]*font-size: ([0-9.]+rem)", sheet, re.MULTILINE
	)
	assert (clock is not None) and (countdowns is not None)
	assert clock.group(1) == countdowns.group(1)
	assert re.search(r"\.ligne-heure \{[^}]*display: flex", sheet)


@then(parsers.parse("la page déclare l'icône « {address} »"))
def declares_icon(api: Api, address: str) -> None:
	assert f'<link rel="icon" href="{address}">' in _page(api)


@then(parsers.parse("l'icône servie est « {name} »"))
def served_icon(api: Api, name: str) -> None:
	assert _answer(api).body == LOGO.encode()


@then("l'icône servie est celle de MachinCast")
def default_icon(api: Api) -> None:
	assert _answer(api).body == ICON.read_bytes()


# ─── L'agenda (https://github.com/dascritch/machincast/issues/599) ───


@then(parsers.parse("la bande de la journée entière du « {day} » ne montre rien"))
def band_empty(api: Api, day: str) -> None:
	assert _blocks(_group(api, "bande", day)) == []


@given(parsers.parse("l'événement de secours « {name} »"))
def fallback_event(empty_database: Connection, name: str) -> None:
	empty_database.execute("INSERT INTO events (internal_name, priority) VALUES (%s, 'fallback')", (name,))


@then(
	parsers.parse("l'agenda de la semaine du « {first} », pour un plugin, est « {name} » de « {start} » à « {end} »"),
	target_fixture="layer",
)
def plugin_agenda(api: Api, first: str, name: str, start: str, end: str) -> list[dict[str, Any]]:
	with connect() as connection:
		layer = agenda.week(connection, date.fromisoformat(first), api.now)
	found = []
	for item in layer:
		found.append((item["name"], item["start"].isoformat(sep=" ")[:16], item["end"].isoformat(sep=" ")[:16]))
	assert found == [(name, start, end)]
	return layer


@then(parsers.parse("son HTML est une section « {name} », en grille horaire"))
def agenda_html(api: Api, layer: list[dict[str, Any]], name: str) -> None:
	text = agenda.render(layer, date(2026, 11, 23), api.now)
	assert text.startswith(f'<section class="{name}">'), text
	assert '<div class="calendrier">' in text
