"""Scénarios d'un périphérique audio qui ne répond plus (https://github.com/dascritch/machincast/issues/259).

Le serveur audio simulé remplace Gst.Element.set_state : tant qu'il ne répond plus, chaque changement d'état d'un
pipeline attend qu'il réponde de nouveau, et note qui l'a demandé. Une demande faite dans le fil de l'interface est une
faute : elle la figerait. Le serveur répond toujours de nouveau à la fin du scénario, pour libérer les fils qui
l'attendent.
"""

import re
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import gi
import pytest
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402

from tests.interface_steps import Context  # noqa: E402
from tests.preview_steps import DELAY, home, preview_window  # noqa: E402

scenarios("blocked_devices.feature")

WAITING_AT_MOST = 3.0
"""Secondes au plus qu'une demande attend le serveur, pour qu'un scénario qui échoue ne reste pas bloqué."""
INTERFACE = Path(__file__).parent.parent / "src" / "machincast" / "interface"
SET_STATE = re.compile(r"\.set_state\(")


@dataclass
class AudioServer:
	answers: threading.Event = field(default_factory=threading.Event)
	tracking: bool = False
	"""Le serveur a cessé de répondre au moins une fois : ses demandes sont notées."""
	requests: list[tuple[Gst.Element, Gst.State]] = field(default_factory=list)
	"""Les changements d'état demandés depuis que le serveur a cessé de répondre, dans l'ordre."""
	interface_waits: list[Gst.State] = field(default_factory=list)
	"""Ceux que le fil de l'interface a demandés : il les a attendus."""
	pipeline: Gst.Element | None = None
	"""Le pipeline de la pré-écoute, quand le serveur a cessé de répondre."""


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> Iterator[AudioServer]:
	server = AudioServer()
	server.answers.set()
	original: Callable[[Gst.Element, Gst.State], Gst.StateChangeReturn] = Gst.Element.set_state

	def set_state(item: Gst.Element, state: Gst.State) -> Gst.StateChangeReturn:
		if server.tracking:
			server.requests.append((item, state))
		if not server.answers.is_set():
			if threading.current_thread() is threading.main_thread():
				server.interface_waits.append(state)
			server.answers.wait(WAITING_AT_MOST)
		return original(item, state)

	monkeypatch.setattr(Gst.Element, "set_state", set_state)
	yield server
	server.answers.set()


# ─── Quand ─────────────────────────────────────────────────


@when("le serveur audio ne répond plus")
def answers_more(interface: Context, server: AudioServer) -> None:
	if (interface.window is not None) and (interface.window.preview is not None):
		server.pipeline = interface.window.preview.player._pipeline
	server.tracking = True
	server.answers.clear()


@when("le serveur audio répond de nouveau")
def answers(server: AudioServer) -> None:
	server.answers.set()


@when(parsers.parse("la sortie de la pré-écoute signale l'erreur « {message} »"))
def output_error(interface: Context, message: str) -> None:
	pipeline = preview_window(interface).player._pipeline
	assert pipeline is not None
	error = GLib.Error.new_literal(Gst.ResourceError.quark(), message, Gst.ResourceError.WRITE)
	pipeline.post_message(Gst.Message.new_error(pipeline, error, "serveur audio simulé"))


# ─── Alors ─────────────────────────────────────────────────


@then("l'interface n'a jamais attendu le serveur audio")
def never_expected(server: AudioServer) -> None:
	assert server.interface_waits == []


@then("le pipeline de la pré-écoute est bientôt arrêté")
def stops(qtbot: QtBot, server: AudioServer) -> None:
	pipeline = server.pipeline
	assert pipeline is not None

	def has_stop() -> bool:
		asks = any((item is pipeline) and (state == Gst.State.NULL) for item, state in server.requests)
		_return, state, _expected = pipeline.get_state(0)
		return (asks) and (state == Gst.State.NULL)

	qtbot.waitUntil(has_stop, timeout=DELAY)


@then("le pipeline de la pré-écoute est passé, dans l'ordre, en pause, en lecture, puis à l'arrêt")
def in_order(server: AudioServer) -> None:
	states = [state for item, state in server.requests if item is server.pipeline]
	assert states == [Gst.State.PAUSED, Gst.State.PLAYING, Gst.State.NULL], states


@then("le port de monitoring de l'antenne est bientôt réessayé")
def retries(interface: Context, qtbot: QtBot, server: AudioServer) -> None:
	qtbot.waitUntil(lambda: Gst.State.PLAYING in [state for _e, state in server.requests], timeout=DELAY)
	assert home(interface).monitor.active()


@then("aucun autre module de l'interface n'appelle set_state")
def only_states() -> None:
	faults = [
		str(path.relative_to(INTERFACE))
		for path in sorted(INTERFACE.rglob("*.py"))
		if (path.name != "states.py") and (SET_STATE.search(path.read_text(encoding="utf-8")))
	]
	assert faults == [], faults
