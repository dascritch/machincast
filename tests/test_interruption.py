"""Scénarios de l'interruption manuelle de l'antenne (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228).

La diffusion tourne sur le moteur simulé de la simulation (machincast.player.simulation.SimulatedEngine), qui suit
l'horloge du binaire : un sonore d'une minute s'interrompt à la seconde voulue, sans attendre. Les étapes partagées de
la diffusion sont dans tests/broadcast_steps.py.
"""

import json
import logging
import socket
import threading
import time
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from pytest_bdd import parsers, scenarios, then, when

from machincast.player.interruptions import ADVANCED_EVENT, MANUAL_INSERTION, MANUAL_INTERRUPTION
from machincast.player.state import (
	IGNORED_REQUEST,
	advance_request,
	cutoff_request_by_fallback,
	from_user,
)
from machincast.webserver import live
from tests.broadcast_steps import Bench, broadcast, clock
from tests.log_texts import shown

scenarios("interruption.feature")

Connection = psycopg.Connection[tuple[object, ...]]
WAITING = 5.0
"""Secondes qu'une demande a pour arriver par la socket d'état."""


def interruption_log(database: Connection) -> list[str]:
	interruption_log = []
	for (message,) in database.execute(
		"SELECT message FROM log WHERE level = 'info' AND kind = %s ORDER BY id", (MANUAL_INTERRUPTION,)
	).fetchall():
		interruption_log.append(shown(message))
	return interruption_log


def advances_log(database: Connection) -> list[str]:
	advances_log = []
	for (message,) in database.execute(
		"SELECT message FROM log WHERE level = 'info' AND kind = %s ORDER BY id", (ADVANCED_EVENT,)
	).fetchall():
		advances_log.append(shown(message))
	return advances_log


def identifier(database: Connection, name: str) -> int:
	"""L'identifiant de l'événement ; 0, qu'aucun n'a, pour un événement absent."""
	line = database.execute("SELECT id FROM events WHERE internal_name = %s", (name,)).fetchone()
	if line is None:
		return 0
	return int(str(line[0]))


# ─── Étant donné ───────────────────────────────────────────


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("j'avance l'événement suivant « {name} »"))
def advance_event(bench: Bench, empty_database: Connection, name: str) -> None:
	"""https://github.com/dascritch/machincast/issues/257 : la demande nomme l'événement suivant attendu."""
	broadcast(bench).interruptions.advance(identifier(empty_database, name))


@when(parsers.parse("un client de la socket d'état demande d'avancer l'événement « {name} »"))
def ask_advance(bench: Bench, empty_database: Connection, caplog: pytest.LogCaptureFixture, name: str) -> None:
	ask(bench, caplog, advance_request(identifier(empty_database, name)).strip())


@when(parsers.parse("un client de la socket d'état demande de couper l'antenne par le secours « {name} »"))
def ask_fallback(bench: Bench, empty_database: Connection, caplog: pytest.LogCaptureFixture, name: str) -> None:
	"""https://github.com/dascritch/machincast/issues/323"""
	ask(bench, caplog, cutoff_request_by_fallback(identifier(empty_database, name)).strip())


@when(
	parsers.parse(
		"le serveur intranet demande, pour le compte « {user} », de couper l'antenne par le secours « {name} »"
	)
)
def intranet_asks_fallback(
	bench: Bench, empty_database: Connection, caplog: pytest.LogCaptureFixture, user: str, name: str
) -> None:
	line = from_user(cutoff_request_by_fallback(identifier(empty_database, name)), user)
	_send(bench, caplog, line.strip(), intranet=True)


@when(parsers.re(r"un client de la socket (?P<which>de l'intranet|d'état) demande « (?P<asks>.+) »$"))
def ask_on(bench: Bench, caplog: pytest.LogCaptureFixture, which: str, asks: str) -> None:
	_send(bench, caplog, asks, intranet=which == "de l'intranet")


def ask(bench: Bench, caplog: pytest.LogCaptureFixture, asks: str) -> None:
	_send(bench, caplog, asks, intranet=False)


def _send(bench: Bench, caplog: pytest.LogCaptureFixture, asks: str, *, intranet: bool) -> None:
	"""La demande est envoyée, puis le scénario attend qu'elle arrive, ou que le journal du binaire dise qu'elle est
	ignorée : jamais la fin d'un délai (https://github.com/dascritch/machincast/issues/280)."""
	state = bench.state
	assert state is not None
	path = state.path
	if intranet:
		assert state.intranet is not None
		path = state.intranet

	def ignored() -> bool:
		for r in caplog.records:
			if IGNORED_REQUEST in r.getMessage():
				return True
		return False

	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
		client.connect(str(path))
		client.sendall(f"{asks}\n".encode())
		# Le message d'état qu'envoie la socket à la connexion montre qu'elle sert ce client.
		client.settimeout(WAITING)
		client.recv(1)
		limit = time.monotonic() + WAITING
		while (state._requests.empty()) and (not ignored()) and (time.monotonic() < limit):
			time.sleep(0.01)


@pytest.fixture
def intranet_client() -> Iterator[dict[str, Any]]:
	"""La connexion du serveur intranet à sa socket, gardée ouverte pour recevoir les réponses
	(https://github.com/dascritch/machincast/issues/593)."""
	kept: dict[str, Any] = {}
	yield kept
	client = kept.get("client")
	if client is not None:
		client.close()


def _keep(bench: Bench, intranet_client: dict[str, Any], line: str) -> None:
	"""Envoie la demande sur une connexion gardée, puis attend qu'elle arrive, ou qu'elle soit refusée."""
	state = bench.state
	assert (state is not None) and (state.intranet is not None)
	client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	client.connect(str(state.intranet))
	client.settimeout(WAITING)
	intranet_client["client"] = client
	client.sendall(f"{line}\n".encode())
	# Le premier état reçu montre que la socket sert ce client ; il est gardé pour la lecture des réponses.
	intranet_client["buffer"] = client.recv(65536)
	limit = time.monotonic() + WAITING
	while (state._requests.empty()) and (time.monotonic() < limit) and (b"reply" not in _received(intranet_client)):
		time.sleep(0.01)


def _received(intranet_client: dict[str, Any]) -> bytes:
	return bytes(intranet_client.get("buffer", b""))


@when(
	parsers.parse(
		"le serveur intranet demande avec l'identifiant « {reply} », pour le compte « {user} », de couper l'antenne "
		"par le secours « {name} »"
	)
)
def intranet_asks_with_identifier(
	bench: Bench,
	empty_database: Connection,
	intranet_client: dict[str, Any],
	user: str,
	reply: str,
	name: str,
) -> None:
	message = json.loads(from_user(cutoff_request_by_fallback(identifier(empty_database, name)), user))
	_keep(bench, intranet_client, json.dumps({**message, "id": reply}))


@when(parsers.parse("le serveur intranet envoie « {line} »"))
def intranet_sends(bench: Bench, intranet_client: dict[str, Any], line: str) -> None:
	_keep(bench, intranet_client, line)


def _lines(intranet_client: dict[str, Any]) -> list[dict[str, Any]]:
	"""Les lignes reçues par le serveur intranet, jusqu'à ce que plus rien n'arrive."""
	client = intranet_client["client"]
	received = _received(intranet_client)
	client.settimeout(0.5)
	while True:
		try:
			chunk = client.recv(65536)
		except TimeoutError:
			break
		if chunk == b"":
			break
		received += chunk
	intranet_client["buffer"] = received
	lines = []
	for line in received.split(b"\n"):
		if line.strip() != b"":
			lines.append(json.loads(line))
	return lines


def _reply(intranet_client: dict[str, Any], reply: str) -> dict[str, Any]:
	found = []
	for line in _lines(intranet_client):
		if line.get("reply") == reply:
			found.append(line)
	assert len(found) == 1, found
	return found[0]


@then(parsers.parse("le serveur intranet reçoit la réponse « {reply} », faite"))
def replied_done(intranet_client: dict[str, Any], reply: str) -> None:
	answer = _reply(intranet_client, reply)
	assert (answer["done"], "reason" in answer) == (True, False)


@then(parsers.parse("le serveur intranet reçoit la réponse « {reply} », refusée parce que « {reason} »"))
def replied_refused(intranet_client: dict[str, Any], reply: str, reason: str) -> None:
	answer = _reply(intranet_client, reply)
	assert (answer["done"], answer["reason"]) == (False, reason)


@pytest.fixture
def waiting() -> dict[str, Any]:
	return {}


@when(parsers.parse("le serveur intranet demande « {line} » pour le compte « {user} », et attend"))
def intranet_waits(bench: Bench, waiting: dict[str, Any], line: str, user: str) -> None:
	"""La demande attend sa réponse dans son fil : la diffusion, elle, avance dans celui du scénario."""
	state = bench.state
	assert (state is not None) and (state.intranet is not None)
	path = state.intranet

	def asking() -> None:
		waiting["answer"] = live.ask(path, json.loads(line), user, timeout=WAITING)

	thread = threading.Thread(target=asking)
	thread.start()
	waiting["thread"] = thread
	limit = time.monotonic() + WAITING
	# La demande est arrivée, ou Machin player ne diffuse plus : le fil a sa réponse.
	while (state._requests.empty()) and (thread.is_alive()) and (time.monotonic() < limit):
		time.sleep(0.01)


def _answered(waiting: dict[str, Any]) -> live.Answer:
	waiting["thread"].join(WAITING)
	answer: live.Answer = waiting["answer"]
	return answer


@then(parsers.parse("le serveur intranet apprend que sa demande est refusée : « {reason} »"))
def learns_refusal(waiting: dict[str, Any], reason: str) -> None:
	assert _answered(waiting) == live.Answer(False, reason)


@then("le serveur intranet apprend que sa demande est faite")
def learns_done(waiting: dict[str, Any]) -> None:
	assert _answered(waiting) == live.Answer(True)


@then("le serveur intranet n'a reçu que des états")
def only_states(intranet_client: dict[str, Any]) -> None:
	lines = _lines(intranet_client)
	assert lines != []
	for line in lines:
		assert "reply" not in line


@then(parsers.parse("le log note, depuis « {origin} », par « {user} », l'alerte « {kind} » : « {message} »"))
def noted_refusal(empty_database: Connection, origin: str, user: str, kind: str, message: str) -> None:
	found = []
	for logged_kind, logged_message, logged_origin, api_user in empty_database.execute(
		"SELECT kind, message, origin::text, api_user FROM log WHERE level = 'warning' ORDER BY id"
	).fetchall():
		found.append((shown(logged_kind), shown(logged_message), logged_origin, api_user))
	assert (kind, message, origin, user) in found, found


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le log note l'interruption manuelle « {message} »"))
def noted_interruption(empty_database: Connection, message: str) -> None:
	assert interruption_log(empty_database) == [message]


@then(
	parsers.re(
		r"le log note, depuis « (?P<origin>\w+) », (?:par « (?P<user>[^»]+) »|sans compte), "
		r"l'interruption manuelle « (?P<message>.+) »$"
	)
)
def noted_with_origin(empty_database: Connection, message: str, origin: str, user: str | None) -> None:
	found = []
	for logged_message, logged_origin, api_user in empty_database.execute(
		"SELECT message, origin::text, api_user FROM log WHERE level = 'info' AND kind = %s ORDER BY id",
		(MANUAL_INTERRUPTION,),
	).fetchall():
		found.append((shown(logged_message), logged_origin, api_user))
	assert found == [(message, origin, user)]


@then(parsers.parse("le log note l'avance « {message} »"))
def advances_noted(empty_database: Connection, message: str) -> None:
	assert advances_log(empty_database) == [message]


@then("le log ne note aucune avance")
def no_advanced(empty_database: Connection) -> None:
	assert advances_log(empty_database) == []


@then(parsers.parse("Machin player annonce l'événement suivant « {name} », du « {start} » au « {end} »"))
def following_announcement(bench: Bench, empty_database: Connection, name: str, start: str, end: str) -> None:
	announces = broadcast(bench)._state(clock(bench).now(), stop=False)["next_event"]
	expected = {"id": identifier(empty_database, name), "name": name, "priority": "show", "start": start, "end": end}
	assert announces == expected


@then("le log ne note aucune interruption manuelle")
def no_interruption(empty_database: Connection) -> None:
	assert interruption_log(empty_database) == []


@then(parsers.parse("le journal du binaire a signalé « {text} »"))
def reported_log(caplog: pytest.LogCaptureFixture, text: str) -> None:
	found = False
	for r in caplog.records:
		if (r.levelno == logging.WARNING) and (text in r.getMessage()):
			found = True
			break
	assert found, caplog.text


@then("le log ne note aucune insertion manuelle")
def no_insertion(empty_database: Connection) -> None:
	"""https://github.com/dascritch/machincast/issues/530"""
	line = empty_database.execute("SELECT count(*) FROM log WHERE kind = %s", (MANUAL_INSERTION,)).fetchone()
	assert line == (0,)


# ─── Un blanc avant ou après une insertion (https://github.com/dascritch/machincast/issues/594) ───


def insertion_log(database: Connection) -> list[str]:
	insertion_log = []
	for (message,) in database.execute(
		"SELECT message FROM log WHERE level = 'info' AND kind = %s ORDER BY id", (MANUAL_INSERTION,)
	).fetchall():
		insertion_log.append(shown(message))
	return insertion_log


@then(parsers.parse("le log note l'insertion manuelle « {message} »"))
def noted_insertion(empty_database: Connection, message: str) -> None:
	assert insertion_log(empty_database) == [message]


@when(parsers.parse("le serveur intranet envoie, pour la séquence « {name} », « {line} »"))
def intranet_sends_sequence(
	bench: Bench, empty_database: Connection, intranet_client: dict[str, Any], name: str, line: str
) -> None:
	found = empty_database.execute("SELECT id FROM sequences WHERE internal_name = %s", (name,)).fetchone()
	assert found is not None
	_keep(bench, intranet_client, line.replace("SEQUENCE", str(found[0])))


def _published(bench: Bench) -> dict[str, Any]:
	return broadcast(bench)._state(clock(bench).now(), stop=False)


@then(parsers.parse("Machin player annonce « {title} » après un blanc de 5 secondes, à « {start} »"))
def announced_after_blank(bench: Bench, title: str, start: str) -> None:
	published = _published(bench)
	found = []
	for announced in [published["next"], *published["upcoming"]]:
		if announced["title"] == title:
			found.append((announced.get("blank_before"), announced["estimated_start"][11:19]))
	# Le premier passage annoncé de ce sonore ; la liste du fil musical peut le ramener plus loin.
	assert found[0] == (5.0, start), published


@then(parsers.parse("Machin player annonce un blanc jusqu'à « {end} », en diffusion, sans sonore en cours"))
def announced_blank(bench: Bench, end: str) -> None:
	published = _published(bench)
	assert (published["state"], published["current"]) == ("playing", None), published
	assert published["blank"]["end"][11:19] == end, published


@then("Machin player n'annonce aucun blanc")
def no_blank(bench: Bench) -> None:
	published = _published(bench)
	assert published["blank"] is None
	assert published["current"] is not None
