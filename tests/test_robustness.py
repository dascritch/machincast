"""Scénarios de robustesse relevés au tour du code (https://github.com/dascritch/machincast/issues/187).

Les étapes de la diffusion sont dans tests/broadcast_steps.py.
"""

import logging
import os
import socket
import subprocess
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import sound_card, version
from machincast.interface.state import PlaybackState, StateClient
from machincast.player.broadcast import air
from machincast.player.state import StateSocket
from tests.broadcast_steps import Bench, broadcast

scenarios("robustness.feature")


@dataclass
class Robustness:
	state_socket: StateSocket | None = None
	descriptors: set[str] = field(default_factory=set)
	error: BaseException | None = None
	server: socket.socket | None = None
	connection: socket.socket | None = None
	client: StateClient | None = None
	received_list: list[PlaybackState] = field(default_factory=list)
	date: datetime | None = None


@pytest.fixture
def robustness() -> Iterator[Robustness]:
	context = Robustness()
	yield context
	for opened in (context.connection, context.server):
		if opened is not None:
			opened.close()
	if context.client is not None:
		context.client.shut_down()


def _descriptors() -> set[str]:
	return set(os.listdir("/proc/self/fd"))


# ─── Socket d'état de Machin player ──────────────────────


@given("une socket d'état dont le chemin est trop long pour le système")
def socket_too_long(robustness: Robustness, tmp_path: Path) -> None:
	# Une socket Unix a un chemin de 108 octets au plus.
	robustness.state_socket = StateSocket(tmp_path / ("s" * 120) / "lecture.sock")


@when("Machin player tente de l'ouvrir")
def open_(robustness: Robustness) -> None:
	assert robustness.state_socket is not None
	robustness.descriptors = _descriptors()
	try:
		robustness.state_socket.open_()
	except OSError as error:
		robustness.error = error


@then("l'ouverture échoue")
def failed_opening(robustness: Robustness) -> None:
	assert isinstance(robustness.error, OSError), robustness.error


@then("aucun descripteur de fichier n'est resté ouvert")
def no_descriptor(robustness: Robustness) -> None:
	assert _descriptors() == robustness.descriptors


@given("la socket d'état de la diffusion dans un répertoire temporaire")
def broadcast_socket(bench: Bench, tmp_path: Path) -> None:
	bench.state = StateSocket(tmp_path / "run" / "lecture.sock")


@when("une erreur interrompt la boucle de diffusion")
def error_in_loop(bench: Bench, robustness: Robustness) -> None:
	"""La diffusion a déjà démarré : la boucle de Machin player reprend au premier pas, qui échoue."""
	launched = broadcast(bench)

	def fail() -> None:
		raise RuntimeError("base de données perdue")

	launched.start = lambda: None  # type: ignore[method-assign]
	launched.step = fail  # type: ignore[method-assign]
	try:
		air(launched, threading.Event(), pause=0)
	except RuntimeError as error:
		robustness.error = error


@then("l'erreur remonte jusqu'à Machin player")
def rise_error(robustness: Robustness) -> None:
	assert isinstance(robustness.error, RuntimeError), robustness.error


@then("la socket d'état est effacée, et plus rien n'y répond")
def closed_socket(bench: Bench) -> None:
	assert bench.state is not None
	path = bench.state.path
	assert not path.exists()
	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as trial, pytest.raises(OSError):
		trial.connect(str(path))


# ─── Client de la socket d'état, dans l'interface ─────────


@given("un serveur de socket d'état de test")
def sample_server(robustness: Robustness, tmp_path: Path) -> None:
	server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	server.bind(str(tmp_path / "etat.sock"))
	server.listen()
	robustness.server = server


@when("l'interface s'y connecte")
def connected_client(robustness: Robustness, qtbot: QtBot, tmp_path: Path) -> None:
	assert robustness.server is not None
	client = StateClient(tmp_path / "etat.sock")
	client.received_state.connect(robustness.received_list.append)
	client.open_connection()
	robustness.client = client
	robustness.server.settimeout(5)
	robustness.connection, _ = robustness.server.accept()


@when(parsers.parse("le serveur envoie {count:d} octets sans fin de ligne, puis un message complet"))
def send_too(robustness: Robustness, qtbot: QtBot, caplog: pytest.LogCaptureFixture, count: int) -> None:
	assert robustness.connection is not None
	caplog.set_level(logging.WARNING, logger="machincast")
	robustness.connection.sendall(b"x" * count)

	# L'interface lit d'abord les octets sans fin de ligne, puis la suite.
	def too_long_logged() -> bool:
		for saving in caplog.records:
			if "trop long" in saving.getMessage():
				return True
		return False

	qtbot.waitUntil(too_long_logged)
	robustness.connection.sendall(b'\n{"state": "dead_air", "current": null, "next": null}\n')

	def dead_air_received() -> bool:
		for state in robustness.received_list:
			if state.state == "dead_air":
				return True
		return False

	qtbot.waitUntil(dead_air_received, timeout=5000)


@then("l'interface a ignoré les octets en trop, en le signalant")
def bytes_ignored(robustness: Robustness, caplog: pytest.LogCaptureFixture) -> None:
	assert robustness.client is not None
	assert len(robustness.client.buffer_in_waiting()) == 0
	found = False
	for saving in caplog.records:
		if "trop long" in saving.getMessage():
			found = True
			break
	assert found, caplog.records


@then("elle a reçu le message complet")
def received_message(robustness: Robustness) -> None:
	state_list = []
	for state in robustness.received_list:
		if state.state == "dead_air":
			state_list.append(state.state)
	assert state_list == ["dead_air"]


# ─── Commandes système de l'interface ─────────────────────


def _replace_command(monkeypatch: pytest.MonkeyPatch, case: str, output: str) -> None:
	def run(command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
		assert options.get("timeout") is not None, "commande sans délai"
		if case == "ne répond pas":
			raise subprocess.TimeoutExpired(command, float(str(options["timeout"])))
		if case == "n'existe pas sur le poste":
			raise FileNotFoundError(command[0])
		return subprocess.CompletedProcess(command, 0, output, "")

	monkeypatch.setattr(subprocess, "run", run)


@when(parsers.parse("la fiche d'un sonore demande la date de création de son fichier, et que stat {case}"))
def birth(robustness: Robustness, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, case: str) -> None:
	_replace_command(monkeypatch, case, "?\n")
	robustness.date = sound_card._birth(tmp_path)


@then("la date de création est inconnue")
def unknown_creation(robustness: Robustness) -> None:
	assert robustness.date is None


@when(parsers.parse("Aide → Version demande la date du dernier commit, et que git {case}"))
def last_commit(robustness: Robustness, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, case: str) -> None:
	(tmp_path / ".git").mkdir()
	_replace_command(monkeypatch, case, "\n")
	robustness.date = version.last_change(tmp_path)


@then("la date du dernier commit est inconnue")
def unknown_commit(robustness: Robustness) -> None:
	assert robustness.date is None
