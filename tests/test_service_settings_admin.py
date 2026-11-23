"""Scénarios des paramètres du service réglés avec le mot de passe d'un administrateur
(https://github.com/dascritch/machincast/issues/603).

pkcheck est imité par un script, dans le répertoire du scénario, qui note ses arguments et répond oui ou non ; la
fenêtre des paramètres est remplacée par une doublure qui note ce qui s'ouvre, et si c'est en consultation.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialogButtonBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Crossfades
from machincast.interface import dialogs
from machincast.interface.preferences import PreferencesWindow, Settings
from machincast.service import SERVICE_SETTINGS_ACTION
from tests.interface_steps import Connection, Context, open_window, window
from tests.test_status import service_installed, service_missing

scenarios("service_settings_admin.feature")

given("le service de diffusion est installé")(service_installed)
given("le service de diffusion n'est pas installé")(service_missing)


class Noted:
	"""Ce que le scénario note : les fenêtres de paramètres ouvertes, et pkcheck."""

	def __init__(self, directory: Path) -> None:
		self.opened: list[tuple[str, bool]] = []
		self.arguments = directory / "pkcheck-arguments"
		self.program: Path | None = None
		self.window: PreferencesWindow | None = None


@pytest.fixture
def noted(tmp_path: Path) -> Noted:
	return Noted(tmp_path)


@pytest.fixture
def parent(qtbot: QtBot) -> Iterator[QWidget]:
	widget = QWidget()
	qtbot.addWidget(widget)
	yield widget


@given("les préférences du scénario notées, avec leur consultation")
def noted_preferences() -> None:
	"""La doublure se pose à l'ouverture de la fenêtre de l'interface, qui pose d'abord les siennes."""


POLKIT = {"qui autorise l'action": 0, "qui refuse l'action": 1}


@given(parsers.re(r"polkit, (?P<answer>qui autorise l'action|qui refuse l'action|absent du poste)"))
def polkit(noted: Noted, tmp_path: Path, answer: str) -> None:
	if answer == "absent du poste":
		noted.program = tmp_path / "pkcheck-absent"
		return
	script = tmp_path / "pkcheck"
	script.write_text(
		f'#!/bin/sh\nfor given in "$@"; do echo "$given"; done > "{noted.arguments}"\nexit {POLKIT[answer]}\n',
		encoding="utf-8",
	)
	script.chmod(0o755)
	noted.program = script


@when("la fenêtre de l'interface s'ouvre")
def open_(interface: Context, empty_database: Connection, qtbot: QtBot, noted: Noted) -> None:
	open_window(interface, qtbot)

	def set_preferences(
		_parent: QWidget,
		_settings: object,
		_output: object,
		_service: object = None,
		kind: str = "service",
		**keywords: object,
	) -> None:
		noted.opened.append((kind, bool(keywords.get("read_only", False))))

	interface.monkeypatch.setattr(dialogs, "set_preferences", set_preferences)
	if noted.program is not None:
		window(interface).administrator.program = str(noted.program)


@then(parsers.re(r"polkit a vérifié l'action « (?P<action>[^»]+) » pour l'interface, en demandant l'authentification"))
def checked(noted: Noted, qtbot: QtBot, action: str) -> None:
	assert action == SERVICE_SETTINGS_ACTION
	qtbot.waitUntil(noted.arguments.exists, timeout=5000)
	given = noted.arguments.read_text(encoding="utf-8").split()
	assert given == ["--action-id", action, "--process", str(os.getpid()), "--allow-user-interaction"]


@then("polkit n'a rien vérifié")
def unchecked(noted: Noted) -> None:
	assert not noted.arguments.exists()


@then(
	parsers.re(
		r"la fenêtre des (?P<kind>paramètres du service|préférences de l'interface) s'est ouverte,"
		r" (?P<mode>modifiable|en consultation)"
	)
)
def opened(noted: Noted, qtbot: QtBot, kind: str, mode: str) -> None:
	qtbot.waitUntil(lambda: noted.opened != [], timeout=5000)
	expected = "service"
	if kind == "préférences de l'interface":
		expected = "interface"
	assert noted.opened == [(expected, mode == "en consultation")]


@when("la fenêtre des paramètres du service s'ouvre en consultation")
def read_only_window(noted: Noted, parent: QWidget) -> None:
	noted.window = PreferencesWindow(Settings(Crossfades(), None, "preecoute-factice"), "dummy", parent, read_only=True)


def _window(noted: Noted) -> PreferencesWindow:
	assert noted.window is not None
	return noted.window


@then(parsers.parse("elle est titrée « {title} »"))
def titled(noted: Noted, title: str) -> None:
	assert _window(noted).windowTitle() == title


@then(parsers.parse("elle dit « {text} »"))
def says(noted: Noted, text: str) -> None:
	banner = _window(noted).read_only_banner
	assert banner is not None
	assert (banner.text(), banner.isHidden()) == (text, False)


@then("chacune de ses pages est en lecture seule, ses onglets toujours au choix")
def read_only_pages(noted: Noted) -> None:
	pages = _window(noted).ui.pages
	assert pages.isEnabled()
	for index in range(pages.count()):
		page = pages.widget(index)
		assert not page.isEnabled(), pages.tabText(index)
		assert pages.isTabEnabled(index)


@then(parsers.parse("elle n'a que le bouton « {label} »"))
def only_button(noted: Noted, label: str) -> None:
	buttons = _window(noted).ui.buttons
	shown = []
	for button in buttons.buttons():
		if not button.isHidden():
			shown.append(button.text())
	assert shown == [label]
	assert buttons.standardButtons() == QDialogButtonBox.StandardButton.Close
