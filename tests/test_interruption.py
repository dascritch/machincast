"""Scénarios de l'interruption manuelle de l'antenne (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228).

La diffusion tourne sur le moteur simulé de la simulation (machincast.player.simulation.SimulatedEngine), qui suit
l'horloge du binaire : un sonore d'une minute s'interrompt à la seconde voulue, sans attendre. Les étapes partagées de
la diffusion sont dans tests/broadcast_steps.py.
"""

import logging
import socket
import time

import psycopg
import pytest
from pytest_bdd import parsers, scenarios, then, when

from machincast.player.broadcast import ADVANCED_EVENT, MANUAL_INTERRUPTION
from machincast.player.state import IGNORED_REQUEST, advance_request, cutoff_request_by_fallback
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
	broadcast(bench).advance(identifier(empty_database, name))


@when(parsers.parse("un client de la socket d'état demande d'avancer l'événement « {name} »"))
def ask_advance(bench: Bench, empty_database: Connection, caplog: pytest.LogCaptureFixture, name: str) -> None:
	ask(bench, caplog, advance_request(identifier(empty_database, name)).strip())


@when(parsers.parse("un client de la socket d'état demande de couper l'antenne par le secours « {name} »"))
def ask_fallback(bench: Bench, empty_database: Connection, caplog: pytest.LogCaptureFixture, name: str) -> None:
	"""https://github.com/dascritch/machincast/issues/323"""
	ask(bench, caplog, cutoff_request_by_fallback(identifier(empty_database, name)).strip())


@when(parsers.parse("un client de la socket d'état demande « {asks} »"))
def ask(bench: Bench, caplog: pytest.LogCaptureFixture, asks: str) -> None:
	"""La demande est envoyée, puis le scénario attend qu'elle arrive, ou que le journal du binaire dise qu'elle est
	ignorée : jamais la fin d'un délai (https://github.com/dascritch/machincast/issues/280)."""
	state = bench.state
	assert state is not None

	def ignored() -> bool:
		for r in caplog.records:
			if IGNORED_REQUEST in r.getMessage():
				return True
		return False

	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
		client.connect(str(state.path))
		client.sendall(f"{asks}\n".encode())
		# Le message d'état qu'envoie la socket à la connexion montre qu'elle sert ce client.
		client.settimeout(WAITING)
		client.recv(1)
		limit = time.monotonic() + WAITING
		while (state._requests.empty()) and (not ignored()) and (time.monotonic() < limit):
			time.sleep(0.01)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le log note l'interruption manuelle « {message} »"))
def noted_interruption(empty_database: Connection, message: str) -> None:
	assert interruption_log(empty_database) == [message]


@then(parsers.parse("le log note l'avance « {message} »"))
def advances_noted(empty_database: Connection, message: str) -> None:
	assert advances_log(empty_database) == [message]


@then("le log ne note aucune avance")
def no_advanced(empty_database: Connection) -> None:
	assert advances_log(empty_database) == []


@then(parsers.parse("Machin player annonce l'événement suivant « {name} », du « {start} » au « {end} »"))
def following_announcement(bench: Bench, empty_database: Connection, name: str, start: str, end: str) -> None:
	announces = broadcast(bench)._state(clock(bench).now(), False)["next_event"]
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
