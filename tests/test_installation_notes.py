"""Scénarios de « Votre installation » et du lien de l'équipe (https://github.com/dascritch/machincast/issues/451).

Le document se crée par python -m machincast.notes create, comme install.sh le lance, dans un processus à part, avec
la langue demandée ; xdg-user-dir, xdg-mime, gio et les éditeurs du poste sont des scripts du répertoire du scénario,
en tête du PATH, qui notent leurs arguments (https://github.com/dascritch/machincast/issues/491). Les éditeurs ne se
cherchent que là (installation_notes.EDITOR_PATH) : ceux installés sur le poste des tests n'y sont pour rien. Les applications du
bureau sont celles de XDG_DATA_HOME et XDG_DATA_DIRS, dans le répertoire du scénario. Les étapes de la fenêtre et de
ses menus sont dans tests/interface_steps.py.
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import tomlkit
from PySide6.QtWidgets import QWidget
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.configuration import PROJECT_DIRECTORY, Crossfades
from machincast.interface import installation_notes
from machincast.interface.installation_notes import EDITORS
from machincast.interface.preferences import INTERFACE, PreferencesWindow, Settings
from tests.database_fixtures import configuration_test
from tests.interface_steps import Context, configuration_file
from tests.test_preferences import TEST_PREVIEW

scenarios("installation_notes.feature")


@dataclass
class Station:
	"""Le poste du scénario : ses commandes imitées, son répertoire personnel, et la configuration à donner."""

	directory: Path
	commands: Path
	home: Path
	configuration: Path | None = None
	result: subprocess.CompletedProcess[str] | None = None
	window: PreferencesWindow | None = None
	parent: QWidget | None = None
	given: Settings | None = None
	editors: list[str] = field(default_factory=list)

	def path(self, text: str) -> Path:
		return Path(text.replace("…/", f"{self.directory}/").replace("<personnel>", str(self.home)))

	def text(self, text: str) -> str:
		return text.replace("…/", f"{self.directory}/").replace("<personnel>", str(self.home))


@pytest.fixture
def station(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Station:
	commands = tmp_path / "commandes"
	home = tmp_path / "personnel"
	commands.mkdir()
	home.mkdir()
	monkeypatch.setenv("PATH", f"{commands}:{os.environ['PATH']}")
	monkeypatch.setenv("HOME", str(home))
	monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "applications-du-compte"))
	monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "applications-du-systeme"))
	# Les éditeurs ne se cherchent que parmi les commandes du scénario : ceux du poste des tests, kate sous KDE par
	# exemple, n'y sont jamais (https://github.com/dascritch/machincast/issues/508).
	monkeypatch.setattr(installation_notes, "EDITOR_PATH", str(commands))
	station = Station(tmp_path, commands, home)
	# Jamais les associations ni les applications du poste des tests : sans étape, le bureau n'en a aucune.
	imitate(station, "xdg-mime", "exit 4")
	imitate(station, "gio", f'echo "$*" >"{tmp_path}/gio.ouvert"')
	return station


def imitate(station: Station, name: str, script: str) -> None:
	program = station.commands / name
	program.write_text(f"#!/bin/bash\n{script}\n", encoding="utf-8")
	program.chmod(0o755)


@given(parsers.parse("le Bureau « {directory} » du compte"))
def desktop(station: Station, directory: str) -> None:
	path = station.path(directory)
	path.mkdir(parents=True, exist_ok=True)
	imitate(station, "xdg-user-dir", f'[[ "$1" == DESKTOP ]] && echo "{path}"')


@given("un poste sans xdg-user-dir")
def without_xdg(station: Station) -> None:
	"""Les commandes du poste restent dans le PATH : seul xdg-user-dir est remplacé par un échec, comme absent."""
	imitate(station, "xdg-user-dir", "exit 127")


@given(parsers.parse("le document « {path} » qui contient « {text} »"))
def existing_document(station: Station, path: str, text: str) -> None:
	document = station.path(path)
	document.parent.mkdir(parents=True, exist_ok=True)
	document.write_text(f"{text}\n", encoding="utf-8")


def _configuration(station: Station) -> Path:
	if station.configuration is None:
		station.configuration = station.directory / "machincast.toml"
		station.configuration.write_bytes(configuration_test().path.read_bytes())
	return station.configuration


def _set_interface_key(path: Path, key: str, value: str) -> None:
	document = tomlkit.parse(path.read_text(encoding="utf-8"))
	if "interface" not in document:
		document.add("interface", tomlkit.table())
	section = document["interface"]
	assert isinstance(section, tomlkit.items.Table)
	section[key] = value
	path.write_text(tomlkit.dumps(document), encoding="utf-8")


@given(parsers.parse("la configuration avec interface.notes « {path} »"))
def configured_notes(station: Station, path: str) -> None:
	_set_interface_key(_configuration(station), "notes", str(station.path(path)))


@given(parsers.parse("la configuration de l'interface avec interface.team_link « {address} »"))
def configured_link(interface: Context, address: str) -> None:
	_set_interface_key(configuration_file(interface), "team_link", address)


@given(parsers.re(r"les éditeurs (?P<names>«.+») sur le poste"))
def editors(station: Station, names: str) -> None:
	for name in re.findall(r"« ([^»]+) »", names):
		imitate(station, name, f'echo "$*" >"{station.directory}/{name}.ouvert"')


@given(parsers.parse("le bureau associe les fichiers texte à « {application} », et les .md à Okular"))
def associations(station: Station, application: str) -> None:
	applications = station.directory / "applications-du-compte" / "applications"
	applications.mkdir(parents=True)
	(applications / application).write_text("[Desktop Entry]\nType=Application\nName=Bloc-notes\n", encoding="utf-8")
	imitate(
		station,
		"xdg-mime",
		f'[[ "$1 $2" == "query default" ]] || exit 1\ncase "$3" in\n\ttext/plain) echo "{application}" ;;\n'
		"\ttext/markdown) echo org.kde.okular.desktop ;;\n\t*) exit 4 ;;\nesac",
	)


@then(parsers.parse("gio a lancé « {application} » sur « {path} »"))
def launched_by_gio(station: Station, qtbot: object, application: str, path: str) -> None:
	opened = station.directory / "gio.ouvert"
	qtbot.waitUntil(opened.exists, timeout=5000)  # type: ignore[attr-defined]
	desktop = station.directory / "applications-du-compte" / "applications" / application
	assert opened.read_text(encoding="utf-8").strip() == f"launch {desktop} {station.path(path)}"


@then("le navigateur web n'a rien ouvert")
def nothing_opened(interface: Context) -> None:
	assert interface.opened_pages == []


@when("le poste n'a plus d'éditeur de texte")
def without_editor(station: Station) -> None:
	for name in EDITORS:
		(station.commands / name).unlink(missing_ok=True)


@when(parsers.re(r"je crée le document de l'installation, en (?P<language>français|anglais)"))
def create(station: Station, language: str) -> None:
	command = [sys.executable, "-m", "machincast.notes", "create", "--config", str(_configuration(station))]
	environment = dict(os.environ)
	environment["LANGUAGE"] = {"français": "fr", "anglais": "en"}[language]
	station.result = subprocess.run(
		command, capture_output=True, text=True, timeout=60, env=environment, cwd=PROJECT_DIRECTORY, check=False
	)
	assert station.result.returncode == 0, station.result.stderr


@then(parsers.parse("le document « {path} » commence par « {text} »"))
def document_starts(station: Station, qtbot: object, path: str, text: str) -> None:
	assert station.path(path).read_text(encoding="utf-8").startswith(text)


@then(parsers.re(r"il contient les titres (?P<titles>«.+»)"))
def titles(station: Station, titles: str) -> None:
	assert station.result is not None
	(document,) = station.path("…/Bureau").iterdir()
	headings = re.findall(r"^# (.+)$", document.read_text(encoding="utf-8"), re.MULTILINE)
	assert headings == re.findall(r"« ([^»]+) »", titles)


@then(parsers.parse("la création a dit « {text} »"))
def creation_said(station: Station, text: str) -> None:
	assert station.result is not None
	assert station.text(text) in station.result.stderr + station.result.stdout


@then(parsers.parse("« {editor} » a ouvert « {path} »"))
def opened_by(station: Station, qtbot: object, editor: str, path: str) -> None:
	opened = station.directory / f"{editor}.ouvert"
	qtbot.waitUntil(opened.exists, timeout=5000)  # type: ignore[attr-defined]
	assert opened.read_text(encoding="utf-8").strip() == str(station.path(path))


@then(parsers.parse("la barre d'état annonce « {text} »"))
def status_bar(interface: Context, station: Station, text: str) -> None:
	assert interface.window is not None
	assert interface.window.statusBar().currentMessage() == station.text(text)


@then(parsers.parse("le navigateur web a ouvert « {address} »"))
def opened_page(interface: Context, station: Station, address: str) -> None:
	assert interface.opened_pages == [station.text(address)]


# ─── Préférences de l'interface ────────────────────────────


@when(
	parsers.parse(
		"la fenêtre des préférences de l'interface s'ouvre sur le document « {path} » et le lien « {address} »"
	)
)
def open_preferences(station: Station, qtbot: object, path: str, address: str) -> None:
	parent = QWidget()
	qtbot.addWidget(parent)  # type: ignore[attr-defined]
	station.parent = parent
	all_ = Settings(Crossfades(), None, TEST_PREVIEW, notes=Path(path), team_link=address)
	station.window = PreferencesWindow(all_, "dummy", parent, kind=INTERFACE, timers=True)


@then(parsers.parse("elle montre le document « {path} » et le lien « {address} »"))
def shown(station: Station, path: str, address: str) -> None:
	assert station.window is not None
	ui = station.window.ui
	assert (ui.notes.text(), ui.team_link.text()) == (path, address)


@when(parsers.re(r"j'y saisis le document « (?P<path>[^»]*) » et le lien « (?P<address>[^»]*) »"))
def enter(station: Station, path: str, address: str) -> None:
	assert station.window is not None
	station.window.ui.notes.setText(path.strip())
	station.window.ui.team_link.setText(address.strip())


@when("j'y clique sur « OK »")
def ok(station: Station) -> None:
	assert station.window is not None
	station.window.accept()
	station.given = station.window.settings()


@then(parsers.parse("elle a donné le document « {path} » et le lien « {address} »"))
def given_values(station: Station, path: str, address: str) -> None:
	assert station.given is not None
	assert (station.given.notes, station.given.team_link) == (Path(path), address)


@then("elle n'a donné ni document ni lien")
def nothing_given(station: Station) -> None:
	assert station.given is not None
	assert (station.given.notes, station.given.team_link) == (None, None)


@given(parsers.parse("les préférences seront réglées avec le document « {path} » et le lien « {address} »"))
def adjusted(interface: Context, path: str, address: str) -> None:
	interface.adjusted_notes = (Path(path), address)


# ─── install.sh ────────────────────────────────────────────


@then(
	parsers.parse(
		"install.sh crée le document de l'installation par « python -m machincast.notes create », avec sa configuration"
	)
)
def install_creates() -> None:
	install = (PROJECT_DIRECTORY / "install.sh").read_text(encoding="utf-8")
	assert '"${VENV}/bin/python" -m machincast.notes create --config "${CONFIGURATION}"' in install
