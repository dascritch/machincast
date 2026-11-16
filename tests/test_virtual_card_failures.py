"""Les pannes de la carte virtuelle de l'antenne factice, sans PipeWire (https://github.com/dascritch/machincast/issues/444).

pw-cli est imité : un faux processus et un faux module subprocess, pour que chaque échec de machincast.player.virtual_card
se joue sur tout poste. Les scénarios de test_virtual_on_air.py, eux, lancent un vrai PipeWire.
"""

import ctypes
import logging
import signal
import subprocess
from types import SimpleNamespace
from typing import Any

import pytest
from pytest_bdd import parsers, scenarios, then, when

from machincast.configuration import DUMMY, Audio
from machincast.player import virtual_card

scenarios("virtual_card_failures.feature")

PR_GET_PDEATHSIG = 2


class FakeProcess:
	"""Un pw-cli imité : il note s'il a été arrêté, et se comporte selon la panne."""

	def __init__(self, fault: str) -> None:
		self.fault = fault
		self.stopped = False
		self.terminations = 0
		self.stdin = SimpleNamespace(write=self._write, flush=lambda: None)

	def _write(self, _text: str) -> None:
		if self.fault == "refuse la commande":
			raise OSError("pipe cassé")

	def poll(self) -> int | None:
		if self.fault == "s'arrête tout de suite":
			return 1
		return None

	def terminate(self) -> None:
		self.terminations += 1

	def wait(self, timeout: float | None = None) -> int:
		if (self.fault == "ne s'arrête pas à terminate") and (not self.stopped):
			self.stopped = True
			raise subprocess.TimeoutExpired("pw-cli", (timeout) or (0))
		self.stopped = True
		return 0

	def kill(self) -> None:
		self.stopped = True


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(played=None)


@pytest.fixture
def started() -> list[FakeProcess]:
	"""Les pw-cli imités lancés pendant le scénario."""
	return []


@when(parsers.parse("Machin player prépare l'antenne factice avec un pw-cli qui « {fault} »"))
def prepared_with_fault(
	monkeypatch: pytest.MonkeyPatch,
	caplog: pytest.LogCaptureFixture,
	started: list[FakeProcess],
	context: SimpleNamespace,
	fault: str,
) -> None:
	def popen(*_arguments: Any, **_keywords: Any) -> FakeProcess:
		if fault == "ne peut pas se lancer":
			raise OSError("pw-cli refuse de se lancer")
		process = FakeProcess(fault)
		started.append(process)
		return process

	def run(*_arguments: Any, **_keywords: Any) -> SimpleNamespace:
		if fault == "ne répond pas à sa requête":
			raise subprocess.TimeoutExpired("pw-cli", 5)
		return SimpleNamespace(stdout="")

	program = None
	if fault != "est absent":
		program = "/usr/bin/pw-cli"
	monkeypatch.setattr(virtual_card, "shutil", SimpleNamespace(which=lambda _name: program))
	monkeypatch.setattr(virtual_card, "time", SimpleNamespace(sleep=lambda _seconds: None))
	monkeypatch.setattr(
		virtual_card,
		"subprocess",
		SimpleNamespace(
			Popen=popen,
			run=run,
			PIPE=subprocess.PIPE,
			DEVNULL=subprocess.DEVNULL,
			TimeoutExpired=subprocess.TimeoutExpired,
			SubprocessError=subprocess.SubprocessError,
		),
	)
	caplog.set_level(logging.INFO, logger="machincast")
	on_air = Audio(output="pipewire", device=DUMMY, preview="casque")  # type: ignore[arg-type]
	with virtual_card.on_air(on_air) as played:
		context.played = played


@then("aucun pw-cli ne reste lancé")
def none_left(started: list[FakeProcess]) -> None:
	for process in started:
		assert (process.stopped) or (process.fault == "s'arrête tout de suite"), process.fault


@when("le pw-cli de la carte est préparé avant son lancement")
def prepared_before_launch(context: SimpleNamespace) -> None:
	virtual_card._die_with_parent()


@then("il reçoit SIGTERM à la mort de son parent")
def receives_sigterm() -> None:
	libc = ctypes.CDLL(None, use_errno=True)
	signal_number = ctypes.c_int(0)
	libc.prctl(PR_GET_PDEATHSIG, ctypes.byref(signal_number))
	libc.prctl(virtual_card.PR_SET_PDEATHSIG, 0)
	assert signal_number.value == signal.SIGTERM


@then("l'antenne est jouée sur la sortie factice")
def played_on_dummy(context: SimpleNamespace) -> None:
	assert context.played.on_air() == ("dummy", None)


@then(parsers.parse("le log dit « {text} »"))
def log_says(caplog: pytest.LogCaptureFixture, text: str) -> None:
	messages = []
	for record in caplog.records:
		messages.append(record.getMessage())
	assert any_contains(messages, text), messages


def any_contains(messages: list[str], text: str) -> bool:
	found = False
	for message in messages:
		if text in message:
			found = True
	return found
