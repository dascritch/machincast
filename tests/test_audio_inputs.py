"""Scénarios des entrées audio, choisies et nommées dans les Paramètres du service, réservées au service
(https://github.com/dascritch/machincast/issues/622).

python -m machincast.input_reservation travaille dans une racine à part (--root). pkexec et systemctl sont des scripts,
en tête du PATH, qui notent leurs arguments ; pkexec lance ensuite la commande, sans autre droit, ou refuse
l'authentification. Les entrées de carte son du poste sont celles du scénario (machincast.audio.input_devices).
"""

import dataclasses
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import tomlkit
from PySide6.QtWidgets import QDialogButtonBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import audio, service
from machincast.audio import Device
from machincast.configuration import PROJECT_DIRECTORY, AudioInput, AudioOutput, Crossfades, load
from machincast.interface import dialogs
from machincast.interface.audio_inputs import DEVICE, NAME, AudioInputs, InputReservation
from machincast.interface.preferences import INTERFACE, SERVICE, PreferencesWindow, Settings, write
from tests.database_fixtures import configuration_test
from tests.interface_steps import Context, configuration_file, window

scenarios("audio_inputs.feature")

FRAGMENT = "/etc/wireplumber/wireplumber.conf.d/50-machincast.conf"
PREVIEW = "preecoute-factice"
INPUTS = re.compile(r"« ([^»]+) » sur « ([^»]+) »")


@dataclass
class System:
	"""La racine du scénario, ses commandes imitées, la configuration, et la dernière commande lancée."""

	root: Path
	commands: Path
	log: Path
	configuration: Path | None = None
	result: subprocess.CompletedProcess[str] | None = None
	window: PreferencesWindow | None = None
	said: list[str] = field(default_factory=list)
	reserved: list[Path] = field(default_factory=list)

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
	found = System(root, commands, log)
	imitate(found, "systemctl", "exit 0")
	return found


def _inputs(text: str) -> tuple[AudioInput, ...]:
	found = []
	for name, device in INPUTS.findall(text):
		found.append(AudioInput(device=device, name=name))
	return tuple(found)


def _configuration(system: System, inputs: tuple[AudioInput, ...], *, output: str = "pipewire") -> None:
	document = tomlkit.parse(configuration_test().path.read_text(encoding="utf-8"))
	audio_section = document["audio"]
	assert isinstance(audio_section, tomlkit.items.Table)
	audio_section["output"] = output
	audio_section["device"] = "alsa_output.usb-antenne"
	entries = tomlkit.array()
	for audio_input in inputs:
		entry = tomlkit.inline_table()
		entry.update({"device": audio_input.device, "name": audio_input.name})
		entries.append(entry)
	if inputs:
		audio_section["inputs"] = entries
	path = system.root.parent / "service.toml"
	path.write_text(tomlkit.dumps(document), encoding="utf-8")
	system.configuration = path


# ─── Étant donné ───────────────────────────────────────────


@given("les entrées de carte son du poste :")
def station_inputs(monkeypatch: pytest.MonkeyPatch, datatable: list[list[str]]) -> None:
	found = []
	for identifier, name in datatable[1:]:
		found.append(Device(identifier.strip(), name.strip()))

	def listed(_output: AudioOutput) -> list[Device]:
		return found

	monkeypatch.setattr(audio, "input_devices", listed)


@given(
	parsers.re(
		r"une configuration du service sur la sortie « (?P<output>[^»]+) », (?:avec les entrées (?P<inputs>.+)|sans entrée)$"
	)
)
def service_configuration(system: System, output: str, inputs: str | None) -> None:
	_configuration(system, _inputs((inputs) or ("")), output=output)


@given(parsers.parse("une configuration du service dont deux entrées s'appellent « {name} »"))
def invalid_configuration(system: System, name: str) -> None:
	_configuration(system, (AudioInput("alsa_input.a", name), AudioInput("alsa_input.b", name)))


@given("systemctl qui échoue")
def failing_systemctl(system: System) -> None:
	imitate(system, "systemctl", "echo 'Unit machincast-wireplumber.service not found.' >&2\nexit 5")


@given("pkexec et systemctl imités")
def imitated(system: System) -> None:
	imitate(system, "pkexec", 'exec "$@"')
	_configuration(system, (AudioInput("alsa_input.usb-studio", "Studio A"),))


@given("pkexec qui refuse l'authentification")
def refused(system: System) -> None:
	imitate(system, "pkexec", "exit 126")


@given(parsers.re(r"le service de diffusion (?P<state>installé|non installé)"))
def service_installed(monkeypatch: pytest.MonkeyPatch, system: System, state: str) -> None:
	installed = service.ServiceState(installed=state == "installé", active="inactive")
	monkeypatch.setattr(service, "read_state", lambda: installed)
	monkeypatch.setattr(InputReservation, "start", lambda _self, path: system.reserved.append(path))


@given("le fichier de configuration de l'interface")
def interface_configuration(system: System) -> None:
	_configuration(system, ())


# ─── Quand ─────────────────────────────────────────────────


@when("je lance « python -m machincast.input_reservation » avec cette configuration, dans la racine du scénario")
def launch(system: System) -> None:
	assert system.configuration is not None
	system.result = subprocess.run(
		[
			sys.executable,
			"-m",
			"machincast.input_reservation",
			"--config",
			str(system.configuration),
			"--root",
			str(system.root),
		],
		capture_output=True,
		text=True,
		timeout=60,
		cwd=PROJECT_DIRECTORY,
		check=False,
	)


@pytest.fixture
def parent(qtbot: QtBot) -> QWidget:
	widget = QWidget()
	qtbot.addWidget(widget)
	return widget


@when(
	parsers.re(
		r"la fenêtre des paramètres du service s'ouvre, (?:avec l'entrée « (?P<name>[^»]+) » sur « (?P<device>[^»]+) »"
		r"|sans entrée)"
	)
)
def open_service(system: System, parent: QWidget, name: str | None, device: str | None) -> None:
	inputs: tuple[AudioInput, ...] = ()
	if (name is not None) and (device is not None):
		inputs = (AudioInput(device, name),)
	settings = Settings(Crossfades(), "alsa_output.usb-antenne", PREVIEW, inputs=inputs)
	system.window = PreferencesWindow(settings, "pipewire", parent, kind=SERVICE)


@when("la fenêtre des préférences de l'interface s'ouvre")
def open_interface(system: System, parent: QWidget) -> None:
	settings = Settings(Crossfades(), "alsa_output.usb-antenne", PREVIEW)
	system.window = PreferencesWindow(settings, "pipewire", parent, kind=INTERFACE)


def _block(system: System) -> AudioInputs:
	assert system.window is not None
	assert system.window.inputs is not None
	return system.window.inputs


def _row(block: AudioInputs, text: str) -> int:
	found = set()
	for row in range(block.table.rowCount()):
		for column in range(block.table.columnCount()):
			cell = block.table.item(row, column)
			if (cell is not None) and (cell.text() == text):
				found.add(row)
	(row,) = found
	return row


@when(parsers.parse("j'y ajoute l'entrée « {name} »"))
def add(system: System, name: str) -> None:
	block = _block(system)
	block.choice.setCurrentIndex(block.choice.findText(name))
	block.add.click()


@when(parsers.re(r"je nomme « (?P<name>[^»]*) » la ligne « (?P<line>[^»]+) »"))
def rename(system: System, name: str, line: str) -> None:
	block = _block(system)
	cell = block.table.item(_row(block, line), NAME)
	assert cell is not None
	cell.setText(name)


@when(parsers.parse("j'y retire la ligne « {line} »"))
def remove(system: System, line: str) -> None:
	block = _block(system)
	block.table.setCurrentCell(_row(block, line), NAME)
	block.remove.click()


@when(parsers.re(r"les préférences écrivent (?:les entrées (?P<inputs>.+)|aucune entrée)$"))
def write_inputs(system: System, inputs: str | None) -> None:
	assert system.configuration is not None
	settings = Settings(Crossfades(), "alsa_output.usb-antenne", PREVIEW, inputs=_inputs((inputs) or ("")))
	write(system.configuration, settings)


@when("l'interface réserve les entrées de sa configuration")
def reserve(system: System, qtbot: QtBot) -> None:
	assert system.configuration is not None
	reservation = InputReservation()
	# Jamais le /etc du poste : la racine du scénario.
	reservation.root = system.root
	reservation.announced.connect(system.said.append)
	reservation.start(system.configuration)
	qtbot.waitUntil(lambda: system.said != [], timeout=20000)


@when(parsers.parse("j'enregistre dans les Paramètres du service l'entrée « {name} » sur « {device} »"))
def save_in_window(interface: Context, monkeypatch: pytest.MonkeyPatch, name: str, device: str) -> None:
	def answered(_parent: QWidget, shown: Settings, *_arguments: Any, **_keywords: Any) -> Settings:
		return dataclasses.replace(shown, inputs=(AudioInput(device, name),))

	monkeypatch.setattr(dialogs, "set_preferences", answered)
	window(interface)._preferences(SERVICE)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def exit_code(system: System, code: int) -> None:
	assert system.result is not None
	assert system.result.returncode == code, system.result.stderr


@then(parsers.re(r"le fragment « (?P<path>[^»]+) » désactive les nœuds (?P<nodes>«.+»)$"))
def fragment_nodes(system: System, path: str, nodes: str) -> None:
	text = (system.root / path.lstrip("/")).read_text(encoding="utf-8")
	expected = ["alsa_output.usb-antenne", *re.findall(r"« ([^»]+) »", nodes)]
	assert re.findall(r'node\.name = "([^"]*)"', text) == expected, text


@then(parsers.parse("le fragment « {path} » désactive seulement la carte de l'antenne"))
def fragment_on_air(system: System, path: str) -> None:
	text = (system.root / path.lstrip("/")).read_text(encoding="utf-8")
	assert re.findall(r'node\.name = "([^"]*)"', text) == ["alsa_output.usb-antenne"], text


@then(parsers.parse("le fragment « {path} » n'existe pas"))
def no_fragment(system: System, path: str) -> None:
	assert not (system.root / path.lstrip("/")).exists()


@then(parsers.re(r"systemctl a été lancé avec (?P<calls>«.+»)$"))
def systemctl_called(system: System, calls: str) -> None:
	assert system.calls("systemctl") == re.findall(r"« ([^»]+) »", calls)


@then("systemctl n'a pas été lancé")
def systemctl_not_called(system: System) -> None:
	assert system.calls("systemctl") == []


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
	assert found != [], system.result.stdout + system.result.stderr


@then(parsers.parse("sa page « Audio » a le bloc « {title} », avec :"))
def block_rows(system: System, title: str, datatable: list[list[str]]) -> None:
	block = _block(system)
	assert block.title() == title
	assert system.window is not None
	assert block.parentWidget() is system.window.ui.page_audio
	rows = []
	for row in range(block.table.rowCount()):
		cells = []
		# La troisième colonne, le VU-mètre de l'entrée (https://github.com/dascritch/machincast/issues/624), n'a pas de
		# texte.
		for column in (NAME, DEVICE):
			cell = block.table.item(row, column)
			assert cell is not None
			cells.append(cell.text())
		rows.append(cells)
	expected = []
	for line in datatable[1:]:
		expected.append([line[0].strip(), line[1].strip()])
	assert rows == expected


@then(parsers.parse("sa page « Audio » n'a pas de bloc « {title} »"))
def no_block(system: System, title: str) -> None:
	assert system.window is not None
	assert system.window.inputs is None
	assert system.window.findChild(AudioInputs) is None


@then(parsers.re(r"il propose d'ajouter (?P<names>«.+»)"))
def offered(system: System, names: str) -> None:
	block = _block(system)
	shown = []
	for index in range(block.choice.count()):
		shown.append(block.choice.itemText(index))
	assert shown == re.findall(r"« ([^»]+) »", names)
	assert block.add.isEnabled()


@then("il ne propose plus rien à ajouter")
def nothing_offered(system: System) -> None:
	block = _block(system)
	assert not block.add.isEnabled()
	assert not block.choice.isEnabled()


@then(parsers.re(r"les paramètres (?:donnent les entrées (?P<inputs>.+)|ne donnent aucune entrée)$"))
def given_inputs(system: System, inputs: str | None) -> None:
	assert system.window is not None
	assert system.window.settings().inputs == _inputs((inputs) or (""))


@then(parsers.re(r"« OK » est (?P<state>actif|inactif)"))
def ok_state(system: System, state: str) -> None:
	assert system.window is not None
	ok = system.window.ui.buttons.button(QDialogButtonBox.StandardButton.Ok)
	assert ok.isEnabled() == (state == "actif")


@then(parsers.parse("le bloc des entrées dit « {text} »"))
def block_says(system: System, text: str) -> None:
	block = _block(system)
	assert block.error.text() == text
	assert not block.error.isHidden()


@then(parsers.parse("la configuration relue a les entrées {inputs}"))
def reread(system: System, inputs: str) -> None:
	assert system.configuration is not None
	assert load(system.configuration).audio.inputs == _inputs(inputs)


@then(parsers.parse("le fichier de configuration n'a plus de clé « {key} »"))
def without_key(system: System, key: str) -> None:
	assert system.configuration is not None
	document = tomlkit.parse(system.configuration.read_text(encoding="utf-8"))
	assert key not in document["audio"]  # type: ignore[operator]


@then(
	parsers.parse(
		"pkexec a lancé « python -m machincast.input_reservation --config » avec la configuration, dans la racine du"
		" scénario"
	)
)
def pkexec_called(system: System) -> None:
	assert system.configuration is not None
	assert system.calls("pkexec") == [
		f"{sys.executable} -m machincast.input_reservation --config {system.configuration.absolute()}"
		f" --root {system.root}"
	]


@then(parsers.parse("la réservation a dit « {text} »"))
def reservation_said(system: System, text: str) -> None:
	assert system.said == [text]


@then(parsers.parse("la configuration de l'interface a les entrées {inputs}"))
def interface_inputs(interface: Context, inputs: str) -> None:
	assert load(configuration_file(interface)).audio.inputs == _inputs(inputs)
	assert window(interface).audio.inputs == _inputs(inputs)


@then(parsers.re(r"la réservation des entrées a été demandée (?P<count>\d+) fois"))
def reservation_asked(interface: Context, system: System, count: str) -> None:
	assert system.reserved == [configuration_file(interface)] * int(count)
