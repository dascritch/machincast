"""Scénarios du cartouchier dans Machin intranet (https://github.com/dascritch/machincast/issues/512).

Les requêtes passent directement à l'application ASGI de l'intranet (tests.asgi_client), avec le cartouchier ajouté
par son Extension, sur la base de test, au rôle machincast_intranet. Machin player est imité par FakePlayer.
"""

import json
import re
import socket
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import machincast_cartwall
import pytest
from machincast_cartwall import intranet
from pytest_bdd import given, parsers, scenarios, then, when
from tests.asgi_client import call
from tests.test_intranet_api import (
	Api,
	_answer,
	_json,
	_page,
	ask_with,
	connect,
	failed,
	navigation,
	status,
	templated,
	valid_session,
)
from tests.test_plugin_intranet import assets

from conftest import PLUGIN, Connection, identifier
from machincast.clock import FixedClock
from machincast.configuration import Intranet as Settings
from machincast.intranet.app import Intranet
from machincast.intranet.extensions import POINT, Extensions
from machincast.intranet.pages import Pages
from machincast.intranet.portal import Portal
from machincast.plugins.points import Points

scenarios(str(PLUGIN / "tests" / "features" / "cartwall.feature"))

NOW = datetime.fromisoformat("2026-11-20 10:00:00").astimezone()

given(parsers.parse("une session valide de « {name} », de jeton « {value} »"), target_fixture="token")(valid_session)
when(parsers.parse("je demande à l'API « {request} », avec le jeton « {value} »"))(ask_with)
then(parsers.re(r"l'API répond (?P<status>\d+)$"))(status)
then(parsers.parse("l'API répond {status:d}, avec l'erreur « {message} »"))(failed)
then(parsers.parse("l'API répond 200, une page « {title} » du gabarit de « {radio} », « {state} », pour « {user} »"))(
	templated
)
then(parsers.parse("le bandeau mène à « {address} » « {label} », la page en cours, et permet de se déconnecter"))(
	navigation
)
then(parsers.parse("la page charge la feuille de style « {sheet} » et le script « {script} »"))(assets)


# ─── Machin player imité ───────────────────────────────────


@dataclass
class FakePlayer:
	"""Une socket de l'intranet qui publie un état, retient les demandes, et y répond : faites, ou refusées."""

	path: Path
	state: dict[str, Any]
	refusal: str | None = None
	received: list[dict[str, Any]] = field(default_factory=list)
	server: socket.socket | None = None

	def start(self) -> None:
		self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.server.bind(str(self.path))
		self.server.listen()
		threading.Thread(target=self._serve, daemon=True).start()

	def _serve(self) -> None:
		assert self.server is not None
		while True:
			try:
				client, _address = self.server.accept()
			except OSError:
				return
			with client:
				self._talk(client)

	def _talk(self, client: socket.socket) -> None:
		client.sendall((json.dumps(self.state) + "\n").encode())
		client.settimeout(0.3)
		received = b""
		try:
			while b"\n" not in received:
				chunk = client.recv(65536)
				if chunk == b"":
					return
				received += chunk
		except OSError:
			return
		asked = json.loads(received.split(b"\n", 1)[0])
		self.received.append(asked)
		reply: dict[str, Any] = {"version": 3, "reply": asked["id"], "done": True}
		if self.refusal is not None:
			reply = {"version": 3, "reply": asked["id"], "done": False, "reason": self.refusal}
		client.sendall((json.dumps(reply) + "\n").encode())

	def stop(self) -> None:
		if self.server is not None:
			self.server.close()


def _state(*, following: bool) -> dict[str, Any]:
	sound = {"sound_id": 1, "type": "file", "artist": "Les Gaufres", "title": "Café à minuit", "duration": 180.0}
	state: dict[str, Any] = {
		"version": 3,
		"state": "playing",
		"current": {
			**sound,
			"public_text": "Radio Thune",
			"position": 12.5,
			"estimated_end": "2026-11-20T10:02:47+01:00",
		},
		"next": {**sound, "title": "Spot", "estimated_start": "2026-11-20T10:02:47+01:00"},
		"upcoming": [],
		"next_event": None,
	}
	if following:
		state["next_event"] = {
			"id": 12,
			"name": "Journal",
			"priority": "show",
			"start": "2026-11-20 12:00",
			"end": None,
		}
	return state


@pytest.fixture
def socket_path(tmp_path: Path) -> Path:
	directory = tmp_path / "lecture"
	directory.mkdir(mode=0o700)
	return directory / "intranet.sock"


@pytest.fixture
def player(socket_path: Path) -> Iterator[FakePlayer]:
	fake = FakePlayer(socket_path, _state(following=True))
	fake.start()
	yield fake
	fake.stop()


@given(parsers.parse("Machin player, qui publie l'événement suivant « {event} » et fait les demandes"))
def publishing(player: FakePlayer, event: str) -> None:
	assert player.state["next_event"]["id"] == int(event)


@given(parsers.parse("Machin player, qui refuse les demandes parce que « {reason} »"))
def refusing(player: FakePlayer, reason: str) -> None:
	player.refusal = reason


@given("Machin player, qui ne publie pas d'événement suivant")
def without_following(player: FakePlayer) -> None:
	player.state = _state(following=False)


@given("l'intranet avec le cartouchier", target_fixture="api")
def application(socket_path: Path, player: FakePlayer, monkeypatch: pytest.MonkeyPatch) -> Api:
	clock = FixedClock(NOW)
	points = Points()
	points.subscribe("cartwall", POINT, lambda data: intranet.extension())
	portal = Portal(Settings(enabled=True), connect)
	pages = Pages(portal, connect, socket_path, "Radio Thune", clock)
	extensions = Extensions(portal, connect, socket_path, "Radio Thune", points.collect(POINT))
	pages.navigation = extensions.navigation
	pages.home_sections = extensions.home
	return Api(Intranet({**portal.routes(), **pages.routes(), **extensions.routes()}), socket_path, NOW)


# ─── La base ───────────────────────────────────────────────


@given(parsers.parse("les boutons de « {user} » retirés"))
def removed(base: Connection, user: str) -> None:
	base.execute("DELETE FROM cartwall__buttons WHERE api_user_id = %s", (identifier(base, "api_users", "name", user),))


@given(parsers.parse("le sonore à l'antenne vient de la banque « {name} »"))
def on_air_from(base: Connection, name: str) -> None:
	base.execute(
		"INSERT INTO airplay (play_id, line_type, bank_id, title) VALUES (gen_random_uuid(), 'start', %s, 'Jingle')",
		(identifier(base, "banks", "internal_name", name),),
	)


@given(parsers.parse("le bouton « {label} » de « {user} » insère la banque « {name} »"))
def inserts(base: Connection, label: str, user: str, name: str) -> None:
	base.execute(
		"UPDATE cartwall__buttons SET bank_id = %s WHERE label = %s AND api_user_id = %s",
		(identifier(base, "banks", "internal_name", name), label, identifier(base, "api_users", "name", user)),
	)


@given(parsers.parse("la séquence « {name} » supprimée"))
def deleted(base: Connection, name: str) -> None:
	base.execute("UPDATE sequences SET deleted_at = clock_timestamp() WHERE internal_name = %s", (name,))


# ─── La page ───────────────────────────────────────────────


@then(parsers.parse("la page a l'antenne en direct, puis la section « {title} »"))
def live_then_section(api: Api, title: str) -> None:
	text = _page(api)
	assert 'id="direct"' in text
	assert text.index('id="direct"') < text.index('<section id="cartouchier"'), text
	assert f"<h2>{title}</h2>" in text


@then(parsers.parse("le bandeau n'a pas d'entrée « {label} »"))
def no_entry(api: Api, label: str) -> None:
	assert f">{label}</a>" not in _page(api)


@then(parsers.parse("la page n'a pas de section « {title} », ni ses fichiers"))
def no_section(api: Api, title: str) -> None:
	text = _page(api)
	assert ('id="cartouchier"' not in text) and (f"<h2>{title}</h2>" not in text)
	assert "/plugins/cartwall/static/" not in text


def _buttons(api: Api) -> list[tuple[str, str, bool]]:
	found = []
	for match in re.finditer(
		r'<button type="button" class="carte" data-bouton="\d+" data-couleur="(?P<colour>[^"]+)"[^>]*?'
		r"(?P<disabled> disabled)?>(?P<label>[^<]+)</button>",
		_page(api),
	):
		found.append((match["label"], match["colour"], match["disabled"] is not None))
	return found


@then(parsers.re(r"la page a les boutons (?P<listed>« .+)$"))
def coloured(api: Api, listed: str) -> None:
	expected = []
	for label, colour in re.findall(r"« ([^»]+) » (#[0-9a-f]{6})", listed):
		expected.append((label, colour, False))
	assert _buttons(api) == expected


@then(parsers.re(r"la page a les boutons grisés (?P<listed>« .+)$"))
def greyed(api: Api, listed: str) -> None:
	labels = []
	for label, _colour, disabled in _buttons(api):
		assert disabled
		labels.append(label)
	assert labels == re.findall(r"« ([^»]+) »", listed)


@then(parsers.parse("la page dit « {text} »"))
def says(api: Api, text: str) -> None:
	assert f'<p class="discret">{text.replace("'", "&#x27;")}</p>' in _page(api), _page(api)


# ─── L'API ─────────────────────────────────────────────────


@then("l'API donne les boutons :")
def listed(api: Api, datatable: list[list[str]]) -> None:
	assert _answer(api).status == 200
	found = []
	for button in _json(api)["buttons"]:
		found.append(
			[
				button["label"],
				button["action"],
				(button["target"]) or (""),
				(button["blank"]) or (""),
				{True: "oui", False: "non"}[button["usable"]],
			]
		)
	expected = []
	for row in datatable[1:]:
		cells = []
		for cell in row:
			cells.append(cell.strip())
		expected.append(cells)
	assert found == expected


def _listed(api: Api, label: str) -> dict[str, Any]:
	for button in _json(api)["buttons"]:
		if button["label"] == label:
			return dict(button)
	raise AssertionError(label)


@then(parsers.parse("le bouton « {label} » n'est pas utilisable, parce que « {reason} »"))
def unusable(api: Api, label: str, reason: str) -> None:
	button = _listed(api, label)
	assert (button["usable"], button["reason"]) == (False, reason)


@then(parsers.parse("le bouton « {label} » est utilisable"))
def usable(api: Api, label: str) -> None:
	button = _listed(api, label)
	assert (button["usable"], button["reason"]) == (True, None)


def _press(api: Api, body: str, token: str) -> None:
	api.answer = call(
		api.application,
		"POST",
		"/api/v1/plugins/cartwall/press",
		headers={"authorization": f"Bearer {token}", "content-type": "application/json"},
		body=body.encode(),
	)


@when(
	parsers.re(
		r"j'appuie sur le bouton « (?P<label>[^»]+) »(?: de « (?P<user>[^»]+) »)?, avec le jeton « (?P<token>[^»]+) »"
	)
)
def press(api: Api, base: Connection, label: str, user: str | None, token: str) -> None:
	owner = (user) or ("regie")
	line = base.execute(
		"SELECT b.id FROM cartwall__buttons b JOIN api_users u ON u.id = b.api_user_id WHERE b.label = %s AND u.name = %s",
		(label, owner),
	).fetchone()
	assert line is not None
	_press(api, json.dumps({"button": line[0]}), token)


@when(parsers.parse("j'envoie « {body} » à « {path} », avec le jeton « {token} »"))
def send(api: Api, body: str, path: str, token: str) -> None:
	assert path == "/api/v1/plugins/cartwall/press"
	_press(api, body, token)


@then("l'API répond 200, faite")
def done(api: Api) -> None:
	assert (_answer(api).status, _json(api)) == (200, {"done": True}), _answer(api).text()


@then(parsers.parse("l'API répond 409, refusée parce que « {reason} »"))
def refused(api: Api, reason: str) -> None:
	assert (_answer(api).status, _json(api)) == (409, {"done": False, "reason": reason}), _answer(api).text()


@then(parsers.parse("Machin player a reçu, de « {user} », la demande « {request} »"))
def received(player: FakePlayer, user: str, request: str) -> None:
	assert len(player.received) == 1, player.received
	asked = dict(player.received[0])
	assert asked.pop("user") == user
	asked.pop("id")
	assert asked == json.loads(request)


@then("Machin player n'a reçu aucune demande")
def nothing_received(player: FakePlayer) -> None:
	assert player.received == []


# ─── Le plugin ─────────────────────────────────────────────


@dataclass
class Registered:
	points: list[str] = field(default_factory=list)


@dataclass
class _Context:
	executable: str
	configuration: Any = None


@dataclass
class _Plugin:
	context: _Context
	registered: Registered

	def on(self, point: str, function: Any) -> None:
		self.registered.points.append(point)


@pytest.fixture
def registered() -> Registered:
	return Registered()


@when(parsers.parse("le cartouchier s'enregistre dans « {executable} »"))
def register(registered: Registered, executable: str) -> None:
	registered.points.clear()
	machincast_cartwall.register(_Plugin(_Context(executable), registered))  # type: ignore[arg-type]


@then(parsers.parse("il s'abonne seulement à « {point} »"))
def subscribed(registered: Registered, point: str) -> None:
	assert registered.points == [point]


@then("les migrations du cartouchier n'ont aucun problème")
def no_problem() -> None:
	from machincast.plugins import schema
	from machincast.plugins.manifest import read

	assert schema.problems(PLUGIN, read(PLUGIN)) == []
