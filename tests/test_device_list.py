"""Scénarios de la liste des périphériques audio (https://github.com/dascritch/machincast/issues/289).

Le moniteur de périphériques est imité par FakeMonitor, à la place de GStreamer dans machincast.audio ; le dernier
scénario liste, avec GStreamer, les périphériques du poste dans des processus à part : un processus tué par un signal,
ou qui ne rend pas la main, compte comme une chute.
"""

import logging
import subprocess
import sys
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import audio

scenarios("device_list.feature")

STARTED = 1
"""Le type de message DEVICE_MONITOR_STARTED de l'imitation."""
PROCESS_DELAY = 120.0
"""Secondes laissées à un processus pour toutes ses listes."""


class FakeBus:
	def __init__(self, monitor: "FakeMonitor") -> None:
		self.monitor = monitor

	def timed_pop_filtered(self, delay: int, types: int) -> object | None:
		assert types == STARTED
		assert delay == int(audio.MONITOR_STARTUP * FakeGst.SECOND)
		self.monitor.calls.append("attendre le démarrage")
		if not self.monitor.announces:
			return None
		return object()


class FakeMonitor:
	def __init__(self, started: bool, announces: bool) -> None:
		self.started = started
		self.announces = announces
		self.calls: list[str] = []
		self.appliances = [object(), object()]

	def add_filter(self, classes: str, caps: object) -> None:
		assert classes == audio.OUTPUT_CLASS

	def start(self) -> bool:
		self.calls.append("start")
		return self.started

	def get_bus(self) -> FakeBus:
		return FakeBus(self)

	def get_devices(self) -> list[object]:
		self.calls.append("get_devices")
		return self.appliances

	def stop(self) -> None:
		self.calls.append("stop")


class FakeGst:
	SECOND = 1_000_000_000

	def __init__(self, monitor: FakeMonitor, with_message: bool) -> None:
		self.created_list = 0
		"""Les moniteurs créés : chacun est le même moniteur imité, qui note tous les appels."""

		def new() -> FakeMonitor:
			self.created_list += 1
			return monitor

		self.DeviceMonitor = SimpleNamespace(new=new)
		self.MessageType = SimpleNamespace()
		if with_message:
			self.MessageType = SimpleNamespace(DEVICE_MONITOR_STARTED=STARTED)

	def init(self, arguments: object) -> None:
		pass


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(monitor=None, gst=None, appliances=None, chutes=[])


@given(
	parsers.re(
		r"un moniteur de périphériques imité, (?P<case>qui annonce son démarrage|qui n'annonce pas son démarrage"
		r"|d'un GStreamer sans message de démarrage|qui ne démarre pas)"
	)
)
def fake_monitor(context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
	monitor = FakeMonitor(started=case != "qui ne démarre pas", announces=case == "qui annonce son démarrage")
	context.monitor = monitor
	context.gst = FakeGst(monitor, with_message=case != "d'un GStreamer sans message de démarrage")
	monkeypatch.setattr(audio, "Gst", context.gst)
	# Le moniteur du processus, s'il y en a déjà un, n'est pas celui du scénario.
	monkeypatch.setattr(audio, "_monitor", None)


@when("je liste les appareils du poste")
def list_items(context: SimpleNamespace) -> None:
	context.appliances = audio.appliances()


@when(parsers.parse("{process:d} processus listent chacun {lists:d} fois les périphériques du poste"))
def list_items_in_loop(context: SimpleNamespace, process: int, lists: int) -> None:
	code = f"from machincast import audio\nfor _ in range({lists}):\n\taudio.appliances()\n"

	def list_item(_) -> None:
		try:
			finished = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=PROCESS_DELAY)
		except subprocess.TimeoutExpired:
			context.chutes.append("sans réponse")
			return
		if finished.returncode != 0:
			context.chutes.append(f"code {finished.returncode} : {finished.stderr.decode(errors='replace')[-300:]}")

	for _ in range(process):
		list_item(_)


@then(parsers.re(r"le moniteur imité a reçu (?P<calls>«.+»)"))
def received_calls(context: SimpleNamespace, calls: str) -> None:
	assert context.monitor.calls == calls.strip("« »").split(" », « ")


@then("la liste des appareils est celle du moniteur imité")
def monitor_list(context: SimpleNamespace) -> None:
	assert context.appliances == context.monitor.appliances


@then(parsers.re(r"(?:un seul moniteur imité a été créé|(?P<count>\d+) moniteurs imités ont été créés)"))
def created_monitors(context: SimpleNamespace, count: str | None) -> None:
	assert context.gst.created_list == int((count) or ("1"))


@then("la liste des appareils est vide")
def empty_list(context: SimpleNamespace) -> None:
	assert context.appliances == []


@then("le journal avertit que le moniteur de périphériques n'a pas fini de démarrer")
def warning(caplog: pytest.LogCaptureFixture) -> None:
	messages = []
	for r in caplog.records:
		if r.levelno == logging.WARNING:
			messages.append(r.getMessage())
	found = False
	for m in messages:
		if ("moniteur de périphériques" in m) and ("pas fini de démarrer" in m):
			found = True
			break
	assert found, messages


@then("chaque processus a rendu la main normalement")
def without_drop(context: SimpleNamespace) -> None:
	assert context.chutes == []
