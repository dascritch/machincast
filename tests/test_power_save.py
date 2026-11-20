"""Scénarios des cartes son toujours éveillées (https://github.com/dascritch/machincast/issues/499).

python -m machincast.power_save travaille dans une racine à part (--root) : /etc et /sys y sont des répertoires du
scénario. udevadm et pkexec sont des scripts, en tête du PATH, qui notent leurs arguments ; pkexec lance ensuite la
commande, sans autre droit, ou refuse l'authentification. Les étapes de la fenêtre et de ses menus sont dans
tests/interface_steps.py.
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from PySide6.QtWidgets import QCheckBox, QLabel
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import power_save, service
from machincast.configuration import PROJECT_DIRECTORY, Crossfades
from machincast.interface.preferences import INTERFACE, SERVICE, PreferencesWindow, Settings
from tests.database_fixtures import configuration_test

scenarios("power_save.feature")


HDA = Path("sys/module/snd_hda_intel/parameters/power_save")


@dataclass
class System:
	"""La racine du scénario, ses commandes imitées, et la dernière commande lancée."""

	root: Path
	commands: Path
	log: Path
	result: subprocess.CompletedProcess[str] | None = None

	def path(self, text: str) -> Path:
		return self.root / text.lstrip("/")

	def calls(self, name: str) -> list[str]:
		file = self.log / f"{name}.appels"
		if not file.exists():
			return []
		return file.read_text(encoding="utf-8").splitlines()


def imitate(system: System, name: str, script: str) -> None:
	program = system.commands / name
	program.write_text(f'#!/bin/bash\necho "$*" >>"{system.log}/{name}.appels"\n{script}\n', encoding="utf-8")
	program.chmod(0o755)


@pytest.fixture
def system(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> System:
	root, commands, log = tmp_path / "racine", tmp_path / "commandes", tmp_path / "appels"
	for directory in (root, commands, log):
		directory.mkdir()
	monkeypatch.setenv("PATH", f"{commands}:{os.environ['PATH']}")
	monkeypatch.delenv(service.ACCOUNT_ENVIRONMENT, raising=False)
	found = System(root, commands, log)
	imitate(found, "udevadm", "exit 0")
	imitate(found, "pkexec", 'exec "$@"')
	return found


@given(parsers.parse("snd_hda_intel chargé, en économie d'énergie après {seconds:d} seconde"))
def hda_loaded(system: System, seconds: int) -> None:
	parameter = system.root / HDA
	parameter.parent.mkdir(parents=True)
	parameter.write_text(f"{seconds}\n", encoding="utf-8")


@given("les cartes son tenues éveillées dans la racine du scénario")
def kept_awake(system: System) -> None:
	for path, text in power_save.SETTINGS:
		file = system.path(str(path))
		file.parent.mkdir(parents=True, exist_ok=True)
		file.write_text(text(), encoding="utf-8")


@given(parsers.parse("« {path} », un fichier et non un répertoire, dans la racine du scénario"))
def not_a_directory(system: System, path: str) -> None:
	file = system.path(path)
	file.parent.mkdir(parents=True, exist_ok=True)
	file.write_text("", encoding="utf-8")


@given("la racine du scénario pour les réglages des cartes son")
def interface_root(system: System, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(power_save, "ROOT", system.root)


@given("pkexec qui refuse l'authentification")
def refused(system: System) -> None:
	imitate(system, "pkexec", "exit 126")


@given(parsers.parse("le compte du service « {name} »"))
def service_account(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
	monkeypatch.setenv(service.ACCOUNT_ENVIRONMENT, name)


@when(parsers.parse("je lance « python -m machincast.power_save {action} » dans la racine du scénario"))
def launch(system: System, action: str) -> None:
	system.result = subprocess.run(
		[sys.executable, "-m", "machincast.power_save", action, "--root", str(system.root)],
		capture_output=True,
		text=True,
		timeout=60,
		cwd=PROJECT_DIRECTORY,
		check=False,
	)


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def exit_code(system: System, code: int) -> None:
	assert system.result is not None
	assert system.result.returncode == code, system.result.stderr


@then(parsers.parse("« {path} » contient la ligne « {line} »"))
def contains(system: System, path: str, line: str) -> None:
	assert line in system.path(path).read_text(encoding="utf-8").splitlines()


@then(parsers.parse("« {path} » n'existe plus"))
def removed(system: System, path: str) -> None:
	assert not system.path(path).exists()


@then(parsers.parse("l'économie d'énergie de snd_hda_intel est à « {value} »"))
def hda_value(system: System, value: str) -> None:
	assert (system.root / HDA).read_text(encoding="utf-8").strip() == value


@then("udevadm a été lancé avec, dans l'ordre :")
def udevadm(system: System, datatable: list[list[str]]) -> None:
	_header, *rows = datatable
	expected = []
	for row in rows:
		expected.append(row[0].strip())
	assert system.calls("udevadm") == expected


@then(parsers.parse("la commande a dit « {text} »"))
def said(system: System, text: str) -> None:
	assert system.result is not None
	assert text in system.result.stdout + system.result.stderr, system.result.stdout + system.result.stderr


@then(parsers.parse("la commande a dit un message qui commence par « {start} »"))
def said_start(system: System, start: str) -> None:
	assert system.result is not None
	found = []
	for line in (system.result.stdout + system.result.stderr).splitlines():
		# Chaque ligne s'ouvre sur son horodatage (https://github.com/dascritch/machincast/issues/253).
		if line.partition(" ")[2].startswith(start):
			found.append(line)
	assert found, system.result.stdout + system.result.stderr


@then(parsers.parse("« python -m machincast.installation {action} » écrit la ligne « {line} »"))
def drafted(action: str, line: str) -> None:
	result = subprocess.run(
		[sys.executable, "-m", "machincast.installation", action, "--config", str(configuration_test().path)],
		capture_output=True,
		text=True,
		timeout=60,
		cwd=PROJECT_DIRECTORY,
		check=False,
	)
	assert result.returncode == 0, result.stderr
	assert line in result.stdout.splitlines()


def _function(text: str, name: str) -> str:
	start = text.index(f"\n{name}() {{")
	return text[start : text.index("\n}\n", start)]


@then("install.sh, en installant le service, lance « machincast.power_save wake » après les deux réglages")
def sh_installs() -> None:
	body = _function((PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8"), "garder_les_cartes_eveillees")
	modprobe = body.index('installer_fichier power-save "${FICHIER_MODPROBE}"')
	usb = body.index('installer_fichier usb-power "${FICHIER_USB}"')
	wake = body.index("-m machincast.power_save wake --root /")
	assert modprobe < usb < wake, body
	assert "garder_les_cartes_eveillees" in _function(
		(PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8"), "installer_service"
	)


@then("install.sh, en retirant le service, recharge les règles de udev")
def sh_removes() -> None:
	body = _function((PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8"), "retirer_service")
	assert "executer sudo udevadm control --reload" in body, body


@pytest.fixture
def settings_window(qtbot: QtBot) -> dict[str, PreferencesWindow]:
	return {}


def _open(qtbot: QtBot, opened: dict[str, PreferencesWindow], kind: str) -> PreferencesWindow:
	window = PreferencesWindow(Settings(Crossfades(), None, None), "dummy", None, kind=kind)
	qtbot.addWidget(window)
	opened["window"] = window
	return window


@when("j'ouvre les paramètres du service")
def open_service_settings(qtbot: QtBot, settings_window: dict[str, PreferencesWindow]) -> None:
	"""https://github.com/dascritch/machincast/issues/532"""
	_open(qtbot, settings_window, SERVICE)


@when("j'ouvre les préférences de l'interface")
def open_interface_preferences(qtbot: QtBot, settings_window: dict[str, PreferencesWindow]) -> None:
	_open(qtbot, settings_window, INTERFACE)


def _box(settings_window: dict[str, PreferencesWindow]) -> QCheckBox:
	box = settings_window["window"].findChild(QCheckBox, "power_save")
	assert isinstance(box, QCheckBox)
	return box


@when("je clique sur la case « Cartes son toujours éveillées »")
def click_box(settings_window: dict[str, PreferencesWindow]) -> None:
	_box(settings_window).click()


@then(
	parsers.re(
		r"la case « Cartes son toujours éveillées » de la page « Audio » est (?P<state>active|inactive), "
		r"(?P<checked>cochée|décochée)(?:, avec l'infobulle « (?P<tooltip>[^»]+) »)?$"
	)
)
def box_state(
	settings_window: dict[str, PreferencesWindow], qtbot: QtBot, state: str, checked: str, tooltip: str | None
) -> None:
	box = _box(settings_window)
	assert box.text() == "Cartes son toujours éveillées"
	ui = settings_window["window"].ui
	assert ui.device_group.isAncestorOf(box)
	assert ui.pages.tabText(ui.pages.indexOf(ui.page_audio)) == "Audio"
	qtbot.waitUntil(lambda: box.isChecked() == (checked == "cochée"), timeout=5000)
	assert box.isEnabled() == (state == "active")
	if tooltip is not None:
		assert box.toolTip() == tooltip


@then(parsers.parse("les paramètres du service disent bientôt « {text} »"))
def said_in_settings(settings_window: dict[str, PreferencesWindow], qtbot: QtBot, text: str) -> None:
	said = settings_window["window"].findChild(QLabel, "power_save_result")
	assert isinstance(said, QLabel)
	qtbot.waitUntil(lambda: said.text() == text, timeout=5000)
	assert not said.isHidden()


@then("la page « Audio » n'a pas de case « Cartes son toujours éveillées »")
def without_box(settings_window: dict[str, PreferencesWindow]) -> None:
	assert settings_window["window"].findChild(QCheckBox, "power_save") is None


@then(parsers.parse("pkexec a lancé « python -m machincast.power_save {action} »"))
def pkexec_launched(system: System, action: str) -> None:
	assert f"{sys.executable} -m machincast.power_save {action} --root {system.root}" in system.calls("pkexec")
