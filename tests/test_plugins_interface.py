"""Scénarios des plugins dans l'interface : l'onglet « Plugins » des paramètres du service et le menu « Plugins »
(https://github.com/dascritch/machincast/issues/587).

Les plugins sont créés dans un répertoire temporaire par les étapes de tests/test_plugins.py, réenregistrées ici.
"""

import re
import shutil
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMenu, QTableWidget, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import plugins
from machincast.configuration import Configuration, Crossfades
from machincast.interface import preferences
from machincast.interface.plugins_page import Offered, PluginsPage, PluginWindow, fill_menu, offered
from machincast.interface.preferences import INTERFACE, SERVICE, Kind, PreferencesWindow, Settings, service_changed
from tests.database_fixtures import sample_configuration_path
from tests.test_plugins import (
	NAME,
	_names,
	_package,
	configuration,
	enabled,
	faulty_plugin,
	forgotten_plugins,
	plugin,
	plugin_directory,
	requires_plugin,
	settings,
)

scenarios("plugins_interface.feature")

__all__ = ["configuration", "forgotten_plugins", "plugin_directory", "settings"]

TEST_PREVIEW = "preecoute-factice"

given(
	parsers.parse(
		"le plugin « {name} » {version}, pour « {binary} », décrit « {description} » et en français « {french} »"
	)
)(plugin)
given(parsers.parse("le plugin « {name} » dont le manifest a {defect}"))(faulty_plugin)
given(parsers.parse("le plugin « {name} » demande le plugin « {other} » {versions}"))(requires_plugin)
given(parsers.re(rf"les plugins activés (?P<names>{NAME}(?:, {NAME})*)$"))(enabled)


class Opened:
	window: PreferencesWindow | None = None
	plugin_window: PluginWindow | None = None
	menu: QMenu | None = None
	path: Path | None = None


@pytest.fixture
def opened() -> Opened:
	return Opened()


@pytest.fixture
def parent(qtbot: QtBot) -> Iterator[QWidget]:
	widget = QWidget()
	qtbot.addWidget(widget)
	yield widget


def _window(opened: Opened) -> PreferencesWindow:
	assert opened.window is not None
	return opened.window


def _page(opened: Opened) -> PluginsPage:
	page = _window(opened).plugins_page
	assert page is not None
	return page


def _open(opened: Opened, parent: QWidget, configuration: Configuration, kind: Kind) -> None:
	shown = Settings(Crossfades(), None, TEST_PREVIEW, plugins=configuration.plugins.enabled)
	opened.window = PreferencesWindow(shown, "dummy", parent, kind=kind, offered=offered(configuration))


@when("j'ouvre les paramètres du service")
def open_service(opened: Opened, parent: QWidget, configuration: Configuration) -> None:
	_open(opened, parent, configuration, SERVICE)


@when("j'ouvre les préférences de l'interface")
def open_interface(opened: Opened, parent: QWidget, configuration: Configuration) -> None:
	_open(opened, parent, configuration, INTERFACE)


def _tabs(opened: Opened) -> list[str]:
	ui = _window(opened).ui
	tabs = []
	for rank in range(ui.pages.count()):
		tabs.append(ui.pages.tabText(rank))
	return tabs


@then("ils ont l'onglet « Plugins »")
def has_tab(opened: Opened) -> None:
	assert _tabs(opened)[-1] == "Plugins", _tabs(opened)


@then("elles n'ont pas l'onglet « Plugins »")
def has_no_tab(opened: Opened) -> None:
	assert "Plugins" not in _tabs(opened)
	assert _window(opened).plugins_page is None


def _box(item: Any) -> str:
	state = "décochée"
	if item.checkState() == Qt.CheckState.Checked:
		state = "cochée"
	if not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
		state += " grisée"
	return state


def _rows(opened: Opened) -> list[list[str]]:
	table = _page(opened).findChild(QTableWidget, "plugins")
	assert table is not None
	rows = []
	for row in range(table.rowCount()):
		line = [_box(table.item(row, 0))]
		for column in range(1, table.columnCount()):
			item = table.item(row, column)
			assert item is not None
			line.append(item.text())
		rows.append(line)
	return rows


@then("l'onglet « Plugins » montre :")
def shows(opened: Opened, datatable: list[list[str]]) -> None:
	rows = _rows(opened)
	expected = datatable[1:]
	assert len(rows) == len(expected), rows
	for row, line in zip(rows, expected, strict=True):
		cells = []
		for cell in line:
			cells.append(cell.strip())
		box, name, version, description, state = cells
		assert row[:4] == [box, name, version, description], rows
		assert state in row[4], rows


@then(parsers.parse("l'onglet « Plugins » a la ligne « {name} », {box}, « {state} »"))
def has_row(opened: Opened, name: str, box: str, state: str) -> None:
	found = []
	for row in _rows(opened):
		if row[1] == name:
			found.append((row[0], row[4]))
	assert found == [(box, state)], _rows(opened)


def _check(opened: Opened, name: str, state: Qt.CheckState) -> None:
	page = _page(opened)
	for row, each in enumerate(page.offered_list):
		if each.name == name:
			item = page.table.item(row, 0)
			assert item is not None
			item.setCheckState(state)
			return
	raise AssertionError(name)


@when(parsers.parse("je coche le plugin « {name} »"))
def tick(opened: Opened, name: str) -> None:
	_check(opened, name, Qt.CheckState.Checked)


@when(parsers.parse("je décoche le plugin « {name} »"))
def untick(opened: Opened, name: str) -> None:
	_check(opened, name, Qt.CheckState.Unchecked)


@then(parsers.re(rf"les paramètres activent les plugins (?P<names>{NAME}(?:, {NAME})*)$"))
def enabled_in_settings(opened: Opened, names: str) -> None:
	assert _window(opened).settings().plugins == tuple(_names(names))


@then("l'onglet « Plugins » ne demande pas de relancer")
def no_restart(opened: Opened) -> None:
	assert _page(opened).restart.isHidden()


@then("l'onglet « Plugins » demande de relancer la diffusion, l'indexation et l'interface")
def restart(opened: Opened) -> None:
	label = _page(opened).restart
	assert not label.isHidden()
	assert label.text() == (
		"Les plugins changent au prochain démarrage de la diffusion, de l'indexation et de l'interface : relancez-les."
	)


@then("ce changement redémarre le service de diffusion")
def restarts(opened: Opened) -> None:
	before = Settings(Crossfades(), None, TEST_PREVIEW)
	after = Settings(Crossfades(), None, TEST_PREVIEW, plugins=_window(opened).settings().plugins)
	assert service_changed(before, after)
	assert not service_changed(after, after)


# ─── Le fichier de configuration ───────────────────────────


@given(
	parsers.parse("un fichier de configuration avec « {section} » et « {line} »"),
)
def file_with(opened: Opened, tmp_path: Path, section: str, line: str) -> None:
	opened.path = tmp_path / "machincast.toml"
	shutil.copy(sample_configuration_path(), opened.path)
	with opened.path.open("a", encoding="utf-8") as file:
		file.write(f"\n{section}\n{line}\n")


@given("un fichier de configuration sans section [plugins]")
def file_without(opened: Opened, tmp_path: Path) -> None:
	opened.path = tmp_path / "machincast.toml"
	shutil.copy(sample_configuration_path(), opened.path)
	assert "plugins" not in tomllib.loads(opened.path.read_text(encoding="utf-8"))


@when(parsers.re(rf"j'enregistre les plugins activés (?P<names>aucun|{NAME}(?:, {NAME})*)$"))
def save(opened: Opened, names: str) -> None:
	assert opened.path is not None
	preferences.write(opened.path, Settings(Crossfades(), None, TEST_PREVIEW, plugins=tuple(_names(names))))


def _read(opened: Opened) -> dict[str, Any]:
	assert opened.path is not None
	return tomllib.loads(opened.path.read_text(encoding="utf-8"))


@then(parsers.re(rf"le fichier active les plugins (?P<names>{NAME}(?:, {NAME})*)$"))
def file_enables(opened: Opened, names: str) -> None:
	assert _read(opened)["plugins"]["enabled"] == _names(names)
	assert opened.path is not None
	assert preferences.plugins_enabled(opened.path) == tuple(_names(names))


@then(parsers.parse("le fichier garde « {line} »"))
def file_keeps(opened: Opened, line: str) -> None:
	assert opened.path is not None
	assert line in opened.path.read_text(encoding="utf-8").splitlines()


@then("le fichier n'a pas de section [plugins]")
def file_has_no_section(opened: Opened) -> None:
	assert "plugins" not in _read(opened)


# ─── Le menu « Plugins » et la fenêtre d'un plugin ─────────


@given(parsers.parse("le plugin « {name} » apporte à sa fenêtre le réglage « {text} »"))
def brings(plugin_directory: Path, name: str, text: str) -> None:
	_package(
		plugin_directory / name,
		"\tfrom PySide6.QtWidgets import QCheckBox\n"
		f"\tplugin.on('interface.plugin_window', lambda data: QCheckBox({text!r}, data['parent']))\n",
	)


@when("l'interface charge ses plugins")
def load(opened: Opened, parent: QWidget, configuration: Configuration) -> None:
	plugins.load(configuration, "Machin_interface")
	opened.menu = QMenu(parent)
	fill_menu(opened.menu, configuration, lambda chosen: None)


def _entries(opened: Opened) -> list[tuple[str, bool]]:
	assert opened.menu is not None
	entries = []
	for action in opened.menu.actions():
		entries.append((action.text(), action.isEnabled()))
	return entries


@then(parsers.parse("le menu « Plugins » propose « {entry} »"))
def proposes(opened: Opened, entry: str) -> None:
	assert _entries(opened) == [(entry, True)]


@then(parsers.parse("le menu « Plugins » propose seulement « {entry} », grisé"))
def proposes_greyed(opened: Opened, entry: str) -> None:
	assert _entries(opened) == [(entry, False)]


@when(parsers.parse("j'ouvre la fenêtre du plugin « {name} »"))
def open_plugin(opened: Opened, parent: QWidget, configuration: Configuration, name: str) -> None:
	chosen: list[Offered] = []
	assert opened.menu is not None
	fill_menu(opened.menu, configuration, chosen.append)
	for action in opened.menu.actions():
		if action.text() == f"{name}…":
			action.trigger()
	assert len(chosen) == 1
	opened.plugin_window = PluginWindow(chosen[0], parent)


def _texts(opened: Opened) -> list[str]:
	window = opened.plugin_window
	assert window is not None
	texts = []
	for name in ("name", "version", "description"):
		label = window.findChild(QLabel, name)
		assert label is not None
		texts.append(label.text())
	return texts


@then(
	parsers.re(
		r"elle montre « (?P<name>[^»]+) », « (?P<version>[^»]+) », « (?P<description>[^»]+) » "
		r"et le réglage « (?P<setting>[^»]+) »$"
	)
)
def shows_window(opened: Opened, name: str, version: str, description: str, setting: str) -> None:
	assert _texts(opened) == [name, version, description]
	window = opened.plugin_window
	assert window is not None
	found = []
	for widget in window.settings:
		found.append(re.sub(r"&", "", str(widget.property("text"))))
	assert found == [setting]


@then(
	parsers.re(
		r"elle montre « (?P<name>[^»]+) », « (?P<version>[^»]+) », « (?P<description>[^»]+) », "
		r"et dit « (?P<text>[^»]+) »$"
	)
)
def shows_without_settings(opened: Opened, name: str, version: str, description: str, text: str) -> None:
	assert _texts(opened) == [name, version, description]
	window = opened.plugin_window
	assert window is not None
	label = window.findChild(QLabel, "no_settings")
	assert (label is not None) and (label.text() == text)
