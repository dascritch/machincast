"""Scénarios des pages, des routes d'API et des fichiers statiques des plugins dans Machin webserver
(https://github.com/dascritch/machincast/issues/588).

Le plugin « horloge » est imité par un abonné au point « intranet.extensions » d'un registre de points
(machincast.plugins.points.Points) ; les requêtes passent directement à l'application ASGI (tests.asgi_client), sur la
base de test, au rôle machincast_webserver, comme celles de tests/test_intranet_api.py, dont les étapes servent ici.
"""

import json
import logging
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.clock import FixedClock
from machincast.configuration import Intranet as Settings
from machincast.plugins.points import Points
from machincast.webserver.api import ApiV1
from machincast.webserver.app import Intranet, Request
from machincast.webserver.extensions import POINT, Endpoint, Extension, Extensions, HomeSection, Page, Tools
from machincast.webserver.pages import Pages
from machincast.webserver.portal import Portal
from tests.asgi_client import call
from tests.test_intranet_api import (
	Api,
	_answer,
	_json,
	_page,
	ask_with,
	ask_without,
	connect,
	failed,
	navigation,
	openapi_schema,
	redirected,
	status,
	templated,
	typed,
	valid_session,
)
from tests.test_plugins import journal_says

scenarios("plugin_intranet.feature")

given(parsers.parse("une session valide de « {name} », de jeton « {value} »"), target_fixture="token")(valid_session)
when(parsers.parse("je demande à l'API « {request} », sans jeton"))(ask_without)
when(parsers.parse("je demande à l'API « {request} », avec le jeton « {value} »"))(ask_with)
then(parsers.re(r"l'API répond (?P<status>\d+)$"))(status)
then(parsers.parse("l'API répond {status:d}, avec l'erreur « {message} »"))(failed)
then(parsers.parse("l'API répond {status:d}, vers « {address} »"))(redirected)
then(parsers.parse("l'API répond {status:d}, de type « {kind} »"))(typed)
then(parsers.parse("l'API répond 200, une page « {title} » du gabarit de « {radio} », « {state} », pour « {user} »"))(
	templated
)
then(parsers.parse("le bandeau mène à « {address} » « {label} », la page en cours, et permet de se déconnecter"))(
	navigation
)
then(parsers.parse("le journal dit « {message} »"))(journal_says)
then(parsers.parse("l'API répond 200, un schéma OpenAPI 3.1 « {title} », de la version installée"))(openapi_schema)

TOKENS = {"regie": "jeton-de-regie", "invite": "jeton-d-invite"}


async def _clock(tools: Tools, request: Request) -> str:
	return f'<p id="horloge">pour {tools.session.user}</p>'


async def _settings(tools: Tools, request: Request) -> str:
	return "<p>Réglages de l'horloge</p>"


async def _ring(tools: Tools, request: Request) -> tuple[int, Any]:
	return 202, {"sonne": tools.session.user}


def _horloge(static: Path) -> Extension:
	return Extension(
		pages=(
			Page("", "Horloge", _clock, navigation="Horloge", assets=("horloge.css", "horloge.js")),
			Page("reglages", "Réglages", _settings, role="actions"),
		),
		endpoints=(Endpoint("post", "sonner", _ring, role="actions", summary="Fait sonner l'horloge"),),
		static=static,
		home=(
			HomeSection(_dial, assets=("cadran.css",)),
			HomeSection(_alarms, role="actions"),
		),
	)


async def _dial(tools: Tools, request: Request) -> str:
	return f'<section id="cadran"><h2>Cadran</h2><p>pour {tools.session.user}</p></section>'


async def _alarms(tools: Tools, request: Request) -> str:
	return '<section id="alarmes"><h2>Alarmes</h2></section>'


async def _broken(tools: Tools, request: Request) -> str:
	raise RuntimeError("cadran cassé")


@pytest.fixture
def socket_path(tmp_path: Path) -> Path:
	directory = tmp_path / "lecture"
	directory.mkdir(mode=0o700)
	return directory / "lecture.sock"


@pytest.fixture
def static(tmp_path: Path) -> Path:
	directory = tmp_path / "horloge" / "static"
	directory.mkdir(parents=True)
	(directory / "horloge.css").write_text(".horloge { color: red; }\n", encoding="utf-8")
	(directory / "horloge.js").write_text("// horloge\n", encoding="utf-8")
	(directory / "cadran.svg").write_text("<svg/>\n", encoding="utf-8")
	(directory / "notes.txt").write_text("rien\n", encoding="utf-8")
	(directory / ".cache.css").write_text("\n", encoding="utf-8")
	(tmp_path / "horloge" / "secret.css").write_text("\n", encoding="utf-8")
	(directory / "sous").mkdir()
	(directory / "sous" / "horloge.css").write_text("\n", encoding="utf-8")
	return directory


@pytest.fixture
def points(static: Path) -> Points:
	registry = Points()
	registry.subscribe("horloge", POINT, lambda data: _horloge(static))
	return registry


def _routes(socket_path: Path, points: Points) -> tuple[Extensions, dict[Any, Any]]:
	clock = FixedClock(datetime.fromisoformat("2026-11-20 10:00:00").astimezone())
	portal = Portal(Settings(enabled=True), connect)
	pages = Pages(portal, connect, socket_path, "Radio Thune", clock)
	extensions = Extensions(portal, connect, socket_path, "Radio Thune", points.collect(POINT))
	pages.navigation = extensions.navigation
	pages.home_sections = extensions.home
	api = ApiV1(portal, connect, socket_path, clock)
	api.plugin_operations = extensions.operations
	routes = {
		**portal.routes(),
		**api.routes(),
		**pages.routes(),
		**extensions.routes(),
	}
	return extensions, routes


@given(parsers.parse("l'intranet sur la base de test, avec le plugin « {name} »"), target_fixture="api")
def application(socket_path: Path, points: Points, name: str) -> Api:
	extensions, routes = _routes(socket_path, points)
	built = Api(Intranet(routes), socket_path, datetime.fromisoformat("2026-11-20 10:00:00").astimezone())
	built.extra["extensions"] = extensions
	return built


@given(parsers.parse("le plugin « {name} » qui répond « {value} » au point « {point} »"))
def chatty(points: Points, name: str, value: str, point: str) -> None:
	points.subscribe(name, point, lambda data: value)


@given(parsers.parse("le plugin « {name} » qui ajoute une page « {path} »"))
def lopsided(points: Points, name: str, path: str) -> None:
	extension = Extension(pages=(Page(path, "Évasion", _settings),))
	points.subscribe(name, POINT, lambda data: extension)


@when("Machin webserver rassemble les extensions des plugins", target_fixture="gathered")
def gather(api: Api, points: Points, caplog: pytest.LogCaptureFixture) -> dict[Any, Any]:
	caplog.set_level(logging.ERROR, logger="machincast.webserver.extensions")
	return _routes(api.socket_path, points)[0].routes()


@when(parsers.parse("le compte « {name} » envoie « {request} » depuis « {origin} »"))
def from_elsewhere(api: Api, name: str, request: str, origin: str) -> None:
	method, path = request.split(" ", 1)
	headers = {"authorization": f"Bearer {TOKENS[name]}", "origin": origin}
	api.answer = call(api.application, method, path, headers=headers)


@then(
	parsers.re(
		r"le schéma donne « (?P<method>[A-Z]+) (?P<path>[^»]+) », « (?P<summary>[^»]+) », du plugin « (?P<name>[^»]+) »,"
		r" pour les comptes « (?P<role>[^»]+) »"
	)
)
def plugin_operation(api: Api, method: str, path: str, summary: str, name: str, role: str) -> None:
	operation = _json(api)["paths"][path][method.lower()]
	assert operation["summary"] == summary
	assert operation["tags"] == [name]
	assert role in operation["description"], operation["description"]
	assert operation["x-machincast-role"] == "actions"


@then(parsers.parse("la page contient « {text} »"))
def contains(api: Api, text: str) -> None:
	assert text in _page(api), _page(api)


@then(parsers.parse("la page ne contient pas « {text} »"))
def lacks(api: Api, text: str) -> None:
	assert text not in _page(api)


@then(parsers.parse("la page charge la feuille de style « {sheet} » et le script « {script} »"))
def assets(api: Api, sheet: str, script: str) -> None:
	text = _page(api)
	assert f'<link rel="stylesheet" href="{sheet}">' in text
	assert f'<script src="{script}" defer></script>' in text
	assert "default-src 'self'" in str(_answer(api).header("content-security-policy"))


@then(parsers.parse("l'API répond {code:d}, avec le JSON « {value} »"))
def answered(api: Api, code: int, value: str) -> None:
	assert _answer(api).status == code, _answer(api).text()
	assert _json(api) == json.loads(value)


@then(parsers.parse("seules les routes du plugin « {name} » sont ajoutées"))
def only(gathered: Mapping[tuple[str, str], object], name: str) -> None:
	assert gathered != {}
	for _method, path in gathered:
		assert f"/plugins/{name}" in path, path


@given(parsers.parse("le plugin « {name} » qui ajoute à l'accueil une section en échec"))
def broken_section(points: Points, name: str) -> None:
	extension = Extension(home=(HomeSection(_broken),))
	points.subscribe(name, POINT, lambda data: extension)


@given("l'intranet, de nouveau, avec ses plugins", target_fixture="api")
def again(socket_path: Path, points: Points) -> Api:
	return application(socket_path, points, "horloge")


@then(parsers.re(r"l'accueil a, sous l'antenne en direct, les sections (?P<sections>« .+)$"))
def home_sections(api: Api, sections: str) -> None:
	text = _page(api)
	found = re.findall(r'<section id="([a-z]+)"><h2>', text)
	assert found == re.findall(r"« ([^»]+) »", sections), found
	for each in found:
		assert text.index('id="direct"') < text.index(f'<section id="{each}">')
