"""Scénarios de l'écran de simulation (https://github.com/dascritch/machincast/issues/37).

Machin player simule ici sur la base de test, par tests/sample_simulation.py : la base de production de la
configuration des tests est volontairement inexistante. Les étapes de la fenêtre, des onglets et des éléments en base
sont dans tests/interface_steps.py.
"""

import os
import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import psycopg
import pytest
from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import dialogs, simulation
from machincast.interface.simulation import COLUMNS, SimulationScreen
from tests.interface_steps import NAME, Context, window

scenarios("simulation_interface.feature")

Connection = psycopg.Connection[tuple[object, ...]]
SIMULATOR = Path(__file__).parent / "simulation_fixtures.py"
SIMULATION_COMMAND = simulation.simulation_command
MAXIMAL_DURATION = 60_000
"""Millisecondes qu'une simulation a pour finir."""


@pytest.fixture
def tracking() -> dict[str, object]:
	"""Ce que les étapes notent en passant : le répertoire temporaire de l'onglet, ce que le sélecteur a proposé."""
	return {}


def screen(interface: Context) -> SimulationScreen:
	tabs = window(interface).ui.tabs
	index_list = []
	for index in range(tabs.count()):
		if isinstance(widget := tabs.widget(index), SimulationScreen):
			index_list.append(widget)
	(found,) = index_list
	return found


def exports(interface: Context) -> Path:
	return interface.directory / "exports"


def rule(text: str) -> QDateTime:
	moment = datetime.fromisoformat(text)
	return QDateTime(QDate(moment.year, moment.month, moment.day), QTime(moment.hour, moment.minute))


def shows(editing: QDateTime) -> str:
	return str(editing.toString("yyyy-MM-dd HH:mm"))


def simulator(interface: Context, *options: str) -> None:
	def command(configuration: Path | None) -> list[str]:
		assert configuration is not None
		return [sys.executable, str(SIMULATOR), *options, "--config", str(configuration)]

	interface.monkeypatch.setattr(simulation, "simulation_command", command)


# ─── Étant donné ───────────────────────────────────────────


@given("un Machin player qui simule sur la base de test")
def on_test_database(interface: Context) -> None:
	simulator(interface)


@given("un Machin player qui simule sans base joignable")
def without_database(interface: Context) -> None:
	simulator(interface, "--sans-base")


@given("un Machin player qui échoue après avoir simulé")
def who_failed(interface: Context) -> None:
	simulator(interface, "--echoue")


@given(parsers.parse("le sonore « {title} » est à l'état « {state} » en base"))
@when(parsers.parse("le sonore « {title} » est à l'état « {state} » en base"))
def sound_state(empty_database: Connection, title: str, state: str) -> None:
	empty_database.execute("UPDATE sounds SET state = %s WHERE title = %s", (state, title))


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je règle la simulation du « {start} » au « {end} »"))
def set_(interface: Context, start: str, end: str) -> None:
	opened = screen(interface)
	opened.start.setDateTime(rule(start))
	opened.end.setDateTime(rule(end))


@when("Machin player attend avant de simuler")
def waits(interface: Context, waiting_end: Path) -> None:
	simulator(interface, "--attend", str(waiting_end))


@pytest.fixture
def waiting_end(interface: Context) -> Iterator[Path]:
	"""Le fichier qui termine l'attente du Machin player factice ; il est créé en fin de scénario."""
	end = interface.directory / "fin-de-l-attente"
	yield end
	end.touch()


@when("je lance la simulation")
def launch(interface: Context, qtbot: QtBot, tracking: dict[str, object]) -> None:
	opened = screen(interface)
	tracking["temporaire"] = opened.temporary
	opened.simulate.click()
	qtbot.waitUntil(lambda: not opened.ongoing(), timeout=MAXIMAL_DURATION)


@when("je lance la simulation, sans attendre sa fin")
def launch_without_wait(interface: Context, qtbot: QtBot, tracking: dict[str, object]) -> None:
	opened = screen(interface)
	tracking["temporaire"] = opened.temporary
	opened.simulate.click()
	process = opened.process
	assert process is not None
	qtbot.waitUntil(lambda: process.processId() > 0, timeout=MAXIMAL_DURATION)
	tracking["pid"] = process.processId()


@when(parsers.parse("j'exporte la simulation sous « {name} », avec le filtre « {filter_} »"))
def export(interface: Context, tracking: dict[str, object], name: str, filter_: str) -> None:
	exports(interface).mkdir(exist_ok=True)

	def choose(_parent: QWidget, offers: str, filters: list[str]) -> tuple[Path, str]:
		assert filter_ in filters
		tracking["propose"] = offers
		return exports(interface) / name, filter_

	interface.monkeypatch.setattr(dialogs, "choose_export", choose)
	screen(interface).export.click()


@when("j'abandonne l'export de la simulation")
def abandon(interface: Context) -> None:
	def choose(_parent: QWidget, _offered: str, _filters: list[str]) -> None:
		return None

	interface.monkeypatch.setattr(dialogs, "choose_export", choose)
	screen(interface).export.click()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("la simulation est réglée du « {start} » au « {end} »"))
def adjusted(interface: Context, start: str, end: str) -> None:
	opened = screen(interface)
	assert (shows(opened.start.dateTime()), shows(opened.end.dateTime())) == (start, end)


@then(parsers.parse("le compte de la simulation est « {text} »"))
def count(interface: Context, text: str) -> None:
	assert screen(interface).count.text() == text


@then(parsers.parse("le compte de la simulation commence par « {start} »"))
def started_count(interface: Context, start: str) -> None:
	text = screen(interface).count.text()
	assert text.startswith(start), text


@then(parsers.re(r"le bouton « (?P<button>Simuler|Exporter…) » de la simulation est (?P<state>actif|inactif)"))
def button(interface: Context, button: str, state: str) -> None:
	opened = screen(interface)
	buttons = {"Simuler": opened.simulate, "Exporter…": opened.export}
	assert buttons[button].isEnabled() == (state == "actif")


@then("la simulation montre les passages :")
def plays(interface: Context, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	model = screen(interface).model
	column_list = []
	for column in range(model.columnCount()):
		column_list.append(str(model.horizontalHeaderItem(column).text()))
	header_list = []
	for header in headers:
		header_list.append(header.strip())
	assert column_list == header_list
	expected_list = [[value.strip() for value in row] for row in rows]
	location = COLUMNS.index("Emplacement")
	for row in expected_list:
		row[location] = interface.path(row[location])
	assert screen(interface).lines() == expected_list


@then("la simulation montre aucun passage")
def no_play(interface: Context) -> None:
	assert screen(interface).lines() == []


@then(parsers.parse("la simulation montre les titres {titles}"))
def titles(interface: Context, titles: str) -> None:
	line_list = []
	for line in screen(interface).lines():
		line_list.append(line[3])
	assert line_list == NAME.findall(titles)


@then("la simulation ne signale rien")
def reported_nothing(interface: Context) -> None:
	anomalies = screen(interface).anomalies
	assert (anomalies.count() == 0) and (anomalies.isHidden())


@then(parsers.parse("la simulation signale « {text} »"))
def reports(interface: Context, text: str) -> None:
	anomalies = screen(interface).anomalies
	assert not anomalies.isHidden()
	row_list = []
	for row in range(anomalies.count()):
		row_list.append(anomalies.item(row).text())
	assert row_list == [text]


@then("l'airplay de la base est vide")
def empty_airplay(empty_database: Connection) -> None:
	line = empty_database.execute("SELECT count(*) FROM airplay").fetchone()
	assert line == (0,)


@then("aucune simulation n'a été lancée")
def no_launched(interface: Context) -> None:
	assert screen(interface).launched_list == 0


@then(parsers.parse("{count:d} simulations ont été lancées"))
def launched_list(interface: Context, count: int) -> None:
	assert screen(interface).launched_list == count


@then("le Machin player de la simulation est arrêté")
def stops(tracking: dict[str, object]) -> None:
	pid = tracking["pid"]
	assert isinstance(pid, int)
	with pytest.raises(ProcessLookupError):
		os.kill(pid, 0)


@then(parsers.parse("la commande de simulation pour « {path} » est Machin player --config « {expected} »"))
def command(path: str, expected: str) -> None:
	assert SIMULATION_COMMAND(Path(path)) == [sys.executable, "-m", "machincast.player", "--config", expected]
	assert SIMULATION_COMMAND(None) == [sys.executable, "-m", "machincast.player"]


@then(parsers.parse("le sélecteur d'export a proposé « {name} »"))
def offers(tracking: dict[str, object], name: str) -> None:
	assert tracking["propose"] == name


@then(parsers.parse("le fichier « {file} » exporté est la sortie {extension} de la simulation"))
def exported(interface: Context, file: str, extension: str) -> None:
	(only,) = list(exports(interface).iterdir())
	assert only.name == file
	assert only.read_bytes() == (screen(interface).temporary / f"simulation{extension}").read_bytes()


@then(parsers.parse("la barre d'état a annoncé l'export de la simulation dans « {file} »"))
def announces_export(interface: Context, file: str) -> None:
	assert f"Simulation exportée dans {exports(interface) / file}." in interface.announcements


@then("aucun fichier n'a été exporté")
def exported_nothing(interface: Context) -> None:
	assert (not exports(interface).exists()) or (not list(exports(interface).iterdir()))


@then("le répertoire temporaire de la simulation n'existe plus")
def temporary_erased(tracking: dict[str, object]) -> None:
	temporary = tracking["temporaire"]
	assert isinstance(temporary, Path)
	assert not temporary.exists()
