"""Scénarios des plugins dans l'interface : l'onglet « Plugins » des paramètres du service et le menu « Plugins »
(https://github.com/dascritch/machincast/issues/587).

Les plugins sont créés dans un répertoire temporaire par les étapes de tests/test_plugins.py, réenregistrées ici.
"""

import dataclasses
import re
import shutil
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractItemView, QLabel, QMenu, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import plugins
from machincast.configuration import Configuration, Crossfades, Plugins
from machincast.database import url_yoyo
from machincast.interface import preferences
from machincast.interface.plugins_page import (
	Installer,
	Offered,
	PluginEntry,
	PluginsPage,
	PluginWindow,
	fill_menu,
	newly_enabled,
	offered,
)
from machincast.interface.preferences import INTERFACE, SERVICE, Kind, PreferencesWindow, Settings, service_changed
from machincast.plugins import schema
from tests.database_fixtures import configuration_test, sample_configuration_path, sample_database_parameters
from tests.test_plugins import (
	NAME,
	_names,
	_package,
	enabled,
	faulty_plugin,
	forgotten_plugins,
	plugin,
	plugin_directory,
	requires_plugin,
	settings,
)

scenarios("plugins_interface.feature")

__all__ = ["forgotten_plugins", "plugin_directory", "settings"]

TEST_PREVIEW = "preecoute-factice"

given(
	parsers.parse(
		"le plugin « {name} » {version}, pour « {binary} », décrit « {description} » et en français « {french} »"
	)
)(plugin)
given(parsers.parse("le plugin « {name} » dont le manifest a {defect}"))(faulty_plugin)
given(parsers.parse("le plugin « {name} » demande le plugin « {other} » {versions}"))(requires_plugin)
given(parsers.re(rf"les plugins activés (?P<names>{NAME}(?:, {NAME})*)$"))(enabled)


@pytest.fixture
def production() -> dict[str, bool]:
	return {"test": False}


@pytest.fixture
def configuration(plugin_directory: Path, settings: dict[str, Any], production: dict[str, bool]) -> Configuration:
	"""La configuration des tests, et ses plugins ; sa « base de production » est la base de test quand le scénario
	installe un plugin : jamais la vraie."""
	loaded = configuration_test()
	if production["test"]:
		_socket, name = sample_database_parameters()
		loaded = dataclasses.replace(
			loaded, database=dataclasses.replace(loaded.database, production=name, test=f"{name}-jamais")
		)
	return dataclasses.replace(
		loaded,
		plugins=Plugins(
			enabled=tuple(settings["enabled"]), directory=plugin_directory, settings=dict(settings["settings"])
		),
	)


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


def _box(entry: PluginEntry) -> str:
	assert entry.isEnabled(), "un plugin n'est jamais grisé : ses raisons doivent se lire"
	if entry.box is None:
		return "sans case"
	if entry.box.isChecked():
		return "cochée"
	return "décochée"


def _plugin_entries(opened: Opened) -> list[PluginEntry]:
	page = _page(opened)
	# Des éléments dépliables, pas un tableau.
	assert page.findChildren(QAbstractItemView) == []
	return page.entries


def _heading(entry: PluginEntry) -> list[str]:
	"""« nom version · état » : le nom, la version, l'état."""
	title, state = entry.heading.text().split(" · ")
	name, _space, version = title.partition(" ")
	return [name, version, state]


def _entry(opened: Opened, name: str) -> PluginEntry:
	found = []
	for entry in _plugin_entries(opened):
		if _heading(entry)[0] == name:
			found.append(entry)
	assert len(found) == 1, name
	return found[0]


@then("l'onglet « Plugins » montre, un élément dépliable par plugin :")
def shows(opened: Opened, datatable: list[list[str]]) -> None:
	rows = []
	for entry in _plugin_entries(opened):
		unfolded = {True: "oui", False: "non"}[entry.unfolded()]
		assert entry.details.isHidden() != entry.unfolded()
		rows.append([_box(entry), *_heading(entry), unfolded])
	expected = []
	for line in datatable[1:]:
		cells = []
		for cell in line:
			cells.append(cell.strip())
		expected.append(cells)
	assert rows == expected


@then(parsers.parse("le plugin « {name} », déplié, dit :"))
def unfolded(opened: Opened, name: str, datatable: list[list[str]]) -> None:
	entry = _entry(opened, name)
	if not entry.unfolded():
		entry.fold.click()
	assert not entry.details.isHidden()
	lines = []
	for label in entry.lines:
		lines.append(label.text())
	expected = []
	for line in datatable:
		expected.append(line[0].strip())
	assert len(lines) == len(expected), lines
	# Une raison longue, comme l'erreur du JSON illisible, se reconnaît à son début.
	for line, start in zip(lines, expected, strict=True):
		assert line.startswith(start), lines


@then(parsers.parse("le plugin « {name} » se replie et se déplie"))
def folds(opened: Opened, name: str) -> None:
	entry = _entry(opened, name)
	entry.fold.click()
	assert (entry.unfolded(), entry.details.isHidden(), entry.fold.arrowType()) == (
		False,
		True,
		Qt.ArrowType.RightArrow,
	)
	# Sa ligne le déplie aussi, comme sa flèche.
	QTest.mouseClick(entry.heading, Qt.MouseButton.LeftButton)
	assert (entry.unfolded(), entry.details.isHidden(), entry.fold.arrowType()) == (
		True,
		False,
		Qt.ArrowType.DownArrow,
	)


def _check(opened: Opened, name: str, state: Qt.CheckState) -> None:
	for entry in _page(opened).entries:
		if entry.plugin.name == name:
			assert entry.box is not None
			entry.box.setChecked(state == Qt.CheckState.Checked)
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


# ─── L'installation à la validation (https://github.com/dascritch/machincast/issues/587) ───


@given("la base de production des scénarios est la base de test")
def production_is_test(production: dict[str, bool], empty_database: Any) -> None:
	production["test"] = True


@given(parsers.parse("le plugin « {name} » a la migration « {identifier} » qui crée la table « {table} »"))
def migration(plugin_directory: Path, name: str, identifier: str, table: str) -> Iterator[None]:
	directory = plugin_directory / name / "migrations"
	directory.mkdir()
	(directory / f"{identifier}.sql").write_text(f"CREATE TABLE {table} (id integer);\n", encoding="utf-8")
	(directory / f"{identifier}.rollback.sql").write_text(f"DROP TABLE {table};\n", encoding="utf-8")
	yield
	# Les tables du plugin, créées par le scénario, ne restent pas pour le suivant.
	_socket, base = sample_database_parameters()
	schema.cancel(url_yoyo(_socket, base), plugin_directory / name)


@given(parsers.parse("le plugin « {name} » a un install.sh qui note ses arguments"))
def noting_script(plugin_directory: Path, name: str) -> None:
	_script(
		plugin_directory / name,
		'for argument in "$@"; do echo "$argument"; done > "$(dirname "$0")/arguments"\necho "fait"\n',
	)


@given(parsers.parse("le plugin « {name} » a un install.sh qui échoue en disant « {text} »"))
def failing_script(plugin_directory: Path, name: str, text: str) -> None:
	_script(plugin_directory / name, f'echo "début"\necho "{text}"\nexit 3\n')


def _script(directory: Path, body: str) -> None:
	script = directory / "install.sh"
	script.write_text(f"#!/usr/bin/env bash\n{body}", encoding="utf-8")
	script.chmod(0o755)


class Installation:
	message: str | None = None
	installed: list[Offered] | None = None
	configuration_file: Path | None = None
	backups: Path | None = None
	installer: Installer | None = None


@pytest.fixture
def installation() -> Installation:
	return Installation()


def _configuration_file(tmp_path: Path, configuration: Configuration) -> Path:
	"""Le fichier que l'installation lit : celui des tests, sur la base de production du scénario."""
	path = tmp_path / "machincast-installation.toml"
	text = sample_configuration_path().read_text(encoding="utf-8")
	text = text.replace(
		'production = "machincast_aucune_production"', f'production = "{configuration.database.production}"'
	)
	text = text.replace('test = "machincast_test"', f'test = "{configuration.database.test}"')
	path.write_text(text, encoding="utf-8")
	return path


@when(parsers.parse("je valide les paramètres en activant « {name} »"))
def validate(
	opened: Opened,
	parent: QWidget,
	qtbot: QtBot,
	tmp_path: Path,
	configuration: Configuration,
	installation: Installation,
	name: str,
) -> None:
	_open(opened, parent, configuration, SERVICE)
	_check(opened, name, Qt.CheckState.Checked)
	_install(opened, qtbot, tmp_path, configuration, installation)


def _install(
	opened: Opened, qtbot: QtBot, tmp_path: Path, configuration: Configuration, installation: Installation
) -> None:
	page = _page(opened)
	installation.installed = newly_enabled(page.offered_list, page.initial, _window(opened).settings().plugins)
	if installation.installed == []:
		return
	installation.configuration_file = _configuration_file(tmp_path, configuration)
	installation.backups = tmp_path / "sauvegardes"
	installer = Installer()
	installation.installer = installer
	with qtbot.waitSignal(installer.finished, timeout=60000) as signal:
		installer.start(installation.installed, installation.configuration_file, installation.backups)
	installation.message = signal.args[0]


@when("je valide les paramètres")
def validate_as_is(
	opened: Opened, qtbot: QtBot, tmp_path: Path, configuration: Configuration, installation: Installation
) -> None:
	_install(opened, qtbot, tmp_path, configuration, installation)


@then(parsers.parse("l'install.sh de « {name} » a reçu la sauvegarde et la configuration"))
def received(plugin_directory: Path, installation: Installation, name: str) -> None:
	arguments = (plugin_directory / name / "arguments").read_text(encoding="utf-8").splitlines()
	assert arguments == ["--backups", str(installation.backups), "--config", str(installation.configuration_file)]


@then(parsers.parse("l'installation dit « {text} »"))
def installation_says(installation: Installation, text: str) -> None:
	assert installation.message == text


@then(parsers.parse("la table « {table} » existe, après une sauvegarde de la base"))
def table_created(empty_database: Any, installation: Installation, table: str) -> None:
	assert empty_database.execute("SELECT to_regclass(%s)", (table,)).fetchone() == (table,)
	assert installation.backups is not None
	assert list(installation.backups.iterdir()) != []


@then("la validation n'installe aucun plugin")
def nothing_installed(installation: Installation) -> None:
	assert installation.installed == []


@then(parsers.parse("l'onglet « Plugins » a « {name} » activable"))
def can_be_enabled(opened: Opened, name: str) -> None:
	entry = _entry(opened, name)
	assert (_box(entry), _heading(entry)[2]) == ("décochée", "activable")
