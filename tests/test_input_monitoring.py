"""Scénarios du VU-mètre et de la pré-écoute de chaque entrée audio, dans les Paramètres du service
(https://github.com/dascritch/machincast/issues/624).

Les Paramètres du service s'affichent sur une sortie choisie ; sur la sortie factice, une entrée donne le signal de
test du moniteur de l'antenne, et la pré-écoute joue sur la sortie factice.
"""

import socket
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot
from shiboken6 import isValid

from machincast import audio, service
from machincast.audio import Device
from machincast.configuration import DUMMY, Audio, AudioInput, AudioOutput, Crossfades
from machincast.interface.audio_inputs import NAME, AudioInputs, InputLevel
from machincast.interface.monitor import input_source
from machincast.interface.preferences import SERVICE, PreferencesWindow, Settings

scenarios("input_monitoring.feature")

PREVIEW = "preecoute-factice"
WAIT = 5000
"""Millisecondes laissées à un VU-mètre pour montrer sa modulation."""


@dataclass
class Shown:
	window: PreferencesWindow | None = None
	parent: QWidget | None = None
	sockets: list[socket.socket] = field(default_factory=list)


@pytest.fixture
def shown(qtbot: QtBot) -> Iterator[Shown]:
	found = Shown()
	yield found
	if (found.window is not None) and (isValid(found.window)):
		block = found.window.inputs
		if block is not None:
			block.halt()
		found.window.close()
	for connection in found.sockets:
		connection.close()


def _block(shown: Shown) -> AudioInputs:
	assert shown.window is not None
	assert shown.window.inputs is not None
	return shown.window.inputs


def _level(shown: Shown, name: str) -> InputLevel:
	block = _block(shown)
	for row in range(block.table.rowCount()):
		cell = block.table.item(row, NAME)
		if (cell is not None) and (cell.text() == name):
			level = block.levels()[row]
			return level
	raise AssertionError(name)


def _button(shown: Shown, text: str) -> QPushButton:
	block = _block(shown)
	assert block.pre_listen.text() == text, block.pre_listen.text()
	return block.pre_listen


# ─── Étant donné ───────────────────────────────────────────


@given("les entrées de carte son du poste :")
def station_inputs(monkeypatch: pytest.MonkeyPatch, datatable: list[list[str]]) -> None:
	found = []
	for identifier, name in datatable[1:]:
		found.append(Device(identifier.strip(), name.strip()))

	def listed(_output: AudioOutput) -> list[Device]:
		return found

	monkeypatch.setattr(audio, "input_devices", listed)


@given("le PipeWire du service qui répond")
def service_pipewire(monkeypatch: pytest.MonkeyPatch, shown: Shown) -> None:
	def connected() -> socket.socket:
		ours, _theirs = socket.socketpair()
		shown.sockets += [ours, _theirs]
		return ours

	monkeypatch.setattr(service, "connect_pipewire", connected)


# ─── Quand ─────────────────────────────────────────────────


@when(
	parsers.re(
		r"les Paramètres du service s'affichent, sur la sortie « (?P<output>[^»]+) », avec l'entrée « (?P<name>[^»]+) »"
		r" sur « (?P<device>[^»]+) »(?P<dummy>, et la pré-écoute sur la sortie factice)?$"
	)
)
def show_settings(qtbot: QtBot, shown: Shown, output: str, name: str, device: str, dummy: str | None) -> None:
	preview = PREVIEW
	if dummy is not None:
		preview = DUMMY
	settings = Settings(Crossfades(), "alsa_output.usb-antenne", preview, inputs=(AudioInput(device, name),))
	shown.parent = QWidget()
	qtbot.addWidget(shown.parent)
	shown.window = PreferencesWindow(settings, output, shown.parent, kind=SERVICE)  # type: ignore[arg-type]
	shown.window.ui.pages.setCurrentWidget(shown.window.ui.page_audio)
	shown.window.show()
	qtbot.waitExposed(shown.window)


@when("la fenêtre se ferme")
def close(shown: Shown) -> None:
	assert shown.window is not None
	shown.window.reject()


@when(parsers.parse("je choisis la ligne « {name} »"))
def choose(shown: Shown, name: str) -> None:
	block = _block(shown)
	for row in range(block.table.rowCount()):
		cell = block.table.item(row, NAME)
		if (cell is not None) and (cell.text() == name):
			block.table.setCurrentCell(row, NAME)


@when(parsers.parse("je clique sur « {text} »"))
def click(qtbot: QtBot, shown: Shown, text: str) -> None:
	qtbot.mouseClick(_button(shown, text), Qt.MouseButton.LeftButton)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le VU-mètre de « {name} » montre bientôt sa modulation"))
def modulation(qtbot: QtBot, shown: Shown, name: str) -> None:
	level = _level(shown, name)
	qtbot.waitUntil(lambda: level.meter.levels != [], timeout=WAIT)
	assert level.meter.isVisible()
	assert not level.unavailable.isVisible()


@then(parsers.parse("le VU-mètre de « {name} » n'écoute plus son entrée"))
def not_listening(shown: Shown, name: str) -> None:
	assert not _level(shown, name).monitor.active()


@then(parsers.parse("à la place du VU-mètre de « {name} », le bloc dit « {text} »"))
def unavailable(qtbot: QtBot, shown: Shown, name: str, text: str) -> None:
	level = _level(shown, name)
	qtbot.waitUntil(lambda: level.unavailable.isVisible(), timeout=WAIT)
	assert level.unavailable.text() == text
	assert not level.meter.isVisible()


@then(parsers.re(r"« Pré-écoute » est inactif(?:, avec l'infobulle « (?P<tip>[^»]+) »)?$"))
def pre_listen_inactive(shown: Shown, tip: str | None) -> None:
	button = _block(shown).pre_listen
	assert not button.isEnabled()
	if tip is not None:
		assert button.toolTip() == tip


@then(parsers.parse("l'entrée « {device} » s'écoute sur la sortie de pré-écoute « {preview} », jamais à l'antenne"))
def heard(shown: Shown, device: str, preview: str) -> None:
	player = _block(shown).preview_player
	assert player.active()
	assert player.device == device
	pipeline = player._pipeline
	assert pipeline is not None
	sinks: list[Any] = []
	pipeline.iterate_sinks().foreach(sinks.append)
	assert len(sinks) == 1
	factory = sinks[0].get_factory()
	assert factory is not None
	# Sur la sortie factice, la pré-écoute joue sur la sortie factice : celle de la pré-écoute, pas l'antenne.
	assert factory.get_name() == audio.PLUGINS["dummy"].factory
	assert player.listening.preview == preview
	assert player.listening.device is None


@then(parsers.parse("le bouton s'appelle « {text} »"))
def button_text(shown: Shown, text: str) -> None:
	assert _block(shown).pre_listen.text() == text


@then("aucune entrée ne s'écoute")
def nothing_heard(shown: Shown) -> None:
	assert not _block(shown).preview_player.active()


@then(
	parsers.parse(
		"la source de l'entrée « {device} » sur la sortie « {output} » est pipewiresrc, sur ce périphérique, par le"
		" PipeWire du service"
	)
)
def service_source(shown: Shown, device: str, output: str) -> None:
	block = input_source(Audio(output=output, device=None, preview=PREVIEW), device)  # type: ignore[arg-type]
	elements: list[Any] = []
	block.iterate_elements().foreach(elements.append)
	found = []
	for element in elements:
		if element.get_factory().get_name() == "pipewiresrc":
			found.append(element)
	(source,) = found
	assert source.get_property("target-object") == device
	assert source.get_property("fd") == shown.sockets[0].fileno()
	properties = source.get_property("stream-properties")
	for key in audio.LOCK:
		assert properties.get_value(key) is True, key
