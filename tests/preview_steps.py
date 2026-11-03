"""Étapes partagées de la fenêtre de pré-écoute (https://github.com/dascritch/machincast/issues/116).

Chargé comme greffon pytest par tests/conftest.py : la pré-écoute d'un sonore (test_preview.py), l'écoute de
l'antenne depuis le VU-mètre (test_vu_meter.py, https://github.com/dascritch/machincast/issues/24) et les périphériques
audio qui ne répondent plus (test_blocked_devices.py, https://github.com/dascritch/machincast/issues/259) s'en
servent.
"""

import shutil
from datetime import timedelta

import psycopg
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from pytest_bdd import given, parsers, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import monitor
from machincast.interface.default_screen import DefaultScreen
from machincast.interface.preview import PreviewWindow
from tests.interface_steps import Context, identifier, window
from tests.sounds import SOUND_FILES

Connection = psycopg.Connection[tuple[object, ...]]

DELAY = 5000
"""Millisecondes laissées à GStreamer pour ce qui arrive « bientôt »."""
SIGNALS = {
	"sinusoïde à -10 dB": "audiotestsrc is-live=true wave=sine volume=0.316",
	"blanc": "audiotestsrc is-live=true wave=silence",
	"carré à 0 dB": "audiotestsrc is-live=true wave=square volume=1.0",
	"introuvable": "elementintrouvable",
	"bref": "audiotestsrc is-live=true num-buffers=10 wave=sine",
	"coupable": "audiotestsrc is-live=true wave=sine volume=0.316 ! valve name=robinet",
}
"""Les signaux de test du port de monitoring de la sortie factice."""


def preview_window(interface: Context) -> PreviewWindow:
	opened = window(interface).preview
	assert opened is not None, "aucune fenêtre de pré-écoute"
	return opened


def home(interface: Context) -> DefaultScreen:
	return window(interface).home


def insert(database: Connection, interface: Context, title: str, artist: str | None, file: str) -> None:
	copies = interface.directory / file
	shutil.copyfile(SOUND_FILES / file, copies)
	database.execute(
		"INSERT INTO sounds (type, location, artist, title, state, duration) VALUES ('file', %s, %s, %s, 'active', %s)",
		(str(copies), artist, title, timedelta(seconds=1)),
	)


@given(parsers.parse("le sonore « {title} » de « {artist} », pour une copie du fichier de test « {file} »"))
def sound_with_artist(interface: Context, empty_database: Connection, title: str, artist: str, file: str) -> None:
	insert(empty_database, interface, title, artist, file)


@given(parsers.re(r"le sonore « (?P<title>[^»]+) », pour une copie du fichier de test « (?P<file>[^»]+) »"))
def sound(interface: Context, empty_database: Connection, title: str, file: str) -> None:
	insert(empty_database, interface, title, None, file)


# ─── Port de monitoring de l'antenne (https://github.com/dascritch/machincast/issues/24) ───


@given(parsers.parse("le signal de test « {signal} » sur l'antenne factice"))
def sample_signal(monkeypatch: pytest.MonkeyPatch, signal: str) -> None:
	monkeypatch.setattr(monitor, "DUMMY_SIGNAL", SIGNALS[signal])


@given("un nouvel essai du port de monitoring après une demi-seconde")
def short_retry(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(monitor, "RETRY", 500)


@then(parsers.parse("le VU-mètre de l'antenne est bientôt indisponible, avec une erreur qui commence par « {start} »"))
def unavailable_soon(interface: Context, qtbot: QtBot, start: str) -> None:
	caption = home(interface).ui.monitor_state
	qtbot.waitUntil(lambda: caption.text().startswith(start), timeout=DELAY)


@when("je lance la pré-écoute")
def launch(interface: Context, qtbot: QtBot) -> None:
	button = preview_window(interface).ui.playback
	assert (button.text(), button.toolTip()) == ("⏵", "Lecture")
	qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


@when("je mets la pré-écoute en pause")
def pause(interface: Context, qtbot: QtBot) -> None:
	button = preview_window(interface).ui.playback
	qtbot.waitUntil(lambda: (button.text(), button.toolTip()) == ("⏸", "Pause"), timeout=DELAY)
	qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


@when("j'arrête la pré-écoute")
def halt(interface: Context, qtbot: QtBot) -> None:
	qtbot.mouseClick(preview_window(interface).ui.stop, Qt.MouseButton.LeftButton)


@when("je ferme la fenêtre de pré-écoute")
def shut_down(interface: Context) -> None:
	preview_window(interface).close()


@then(parsers.parse("la pré-écoute lit par l'élément GStreamer « {factory} »"))
def preview_player(interface: Context, factory: str) -> None:
	"""https://github.com/dascritch/machincast/issues/284 : playbin3, qui ne se bloque pas au démarrage d'un AIFF."""
	pipeline = preview_window(interface).player._pipeline
	assert pipeline is not None
	builder = pipeline.get_factory()
	assert (builder is not None) and (builder.get_name() == factory)


@then(parsers.parse("la fenêtre de pré-écoute est ouverte, titrée « {title} »"))
def opened(interface: Context, title: str) -> None:
	opened = preview_window(interface)
	assert opened.isVisible()
	assert opened.windowTitle() == title
	assert opened.isWindow()


@then(parsers.parse("la pré-écoute montre la source « {source} »"))
def source(interface: Context, source: str) -> None:
	assert preview_window(interface).ui.source.text() == interface.path(source)


@when(parsers.re(r"la pré-écoute est (?P<soon>bientôt )?« (?P<state>[^»]+) »(?:, à « (?P<time>[^»]+) »)?"))
@then(parsers.re(r"la pré-écoute est (?P<soon>bientôt )?« (?P<state>[^»]+) »(?:, à « (?P<time>[^»]+) »)?"))
def state(interface: Context, qtbot: QtBot, soon: str | None, state: str, time: str | None) -> None:
	ui = preview_window(interface).ui

	def reached() -> bool:
		return (ui.state.text() == state) and ((time is None) or (ui.time.text() == time))

	if soon is not None:
		qtbot.waitUntil(reached, timeout=DELAY)
	assert reached(), (ui.state.text(), ui.time.text(), ui.message.text())


@then(parsers.re(r"les commandes de la pré-écoute sont : (?P<commands>.+)"))
def commands(interface: Context, commands: str) -> None:
	ui = preview_window(interface).ui
	opened = preview_window(interface)
	fetched_list = []
	assert (ui.stop.text(), ui.stop.toolTip()) == ("⏹", "Arrêt")
	for name, active in (
		(ui.playback.toolTip().lower(), ui.playback.isEnabled()),
		("arrêt", ui.stop.isEnabled()),
		# La position se règle sur la frise, que seul un fichier a (https://github.com/dascritch/machincast/issues/224).
		("position", (ui.timeline_area.isVisibleTo(opened)) and (opened.timeline.isEnabled())),
	):
		button_state = "inactif"
		if active:
			button_state = "actif"
		fetched_list.append(f"{name} {button_state}")
	expected_list = [c.replace("active", "actif").replace("inactive", "inactif") for c in commands.split(", ")]
	assert fetched_list == expected_list


@when("le VU-mètre de la pré-écoute montre bientôt du son")
@then("le VU-mètre de la pré-écoute montre bientôt du son")
def of_sound(interface: Context, qtbot: QtBot) -> None:
	vu_meter = preview_window(interface).vu_meter
	qtbot.waitUntil(lambda: any(level > vu_meter.FLOOR for level in vu_meter.levels), timeout=DELAY)


@then(parsers.parse("la pré-écoute signale bientôt « {start} »"))
def reports_soon(interface: Context, qtbot: QtBot, start: str) -> None:
	message = preview_window(interface).ui.message
	qtbot.waitUntil(lambda: message.text().startswith(start), timeout=DELAY)


@then(parsers.parse("la pré-écoute signale « {text} »"))
def reports(interface: Context, text: str) -> None:
	expected = text.replace("…/", f"{interface.directory}/")
	assert preview_window(interface).ui.message.text() == expected


@then(parsers.parse("la fenêtre de pré-écoute est bientôt titrée « {title} »"))
def soon_titled(interface: Context, qtbot: QtBot, title: str) -> None:
	qtbot.waitUntil(lambda: preview_window(interface).windowTitle() == title, timeout=DELAY)


@then(parsers.parse("la fenêtre de pré-écoute reste titrée « {title} »"))
def remains_titled(interface: Context, qtbot: QtBot, title: str) -> None:
	"""Le temps qu'un état publié arrive à l'interface."""
	qtbot.wait(500)
	assert preview_window(interface).windowTitle() == title


@when(parsers.parse("je demande la pré-écoute du sonore « {title} »"))
def ask(interface: Context, empty_database: Connection, title: str) -> None:
	window(interface)._preview(identifier(empty_database, "sounds", "title", title))


@then("la fenêtre n'a pas de bouton « Pré-écoute » sous ses onglets")
def without_button(interface: Context) -> None:
	"""https://github.com/dascritch/machincast/issues/245 : l'entrée du menu « Diffusion » remplace le bouton."""
	opened = window(interface)
	outside_tabs = [button for button in opened.findChildren(QPushButton) if not opened.ui.tabs.isAncestorOf(button)]
	assert [button.text() for button in outside_tabs if "Pré-écoute" in button.text()] == []
