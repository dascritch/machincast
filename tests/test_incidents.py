"""Scénarios de l'écran des incidents (https://github.com/dascritch/machincast/issues/35).

Les étapes de la fenêtre, des listes et des fiches sont dans tests/interface_steps.py ; celles-ci écrivent le log de
la base de test, comme Machin player, et lisent l'écran.
"""

from datetime import datetime, timedelta

from PySide6.QtCore import QModelIndex, Qt
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.incidents import IncidentScreen
from tests.interface_steps import NAME, Connection, Context, identifier, type_, window

scenarios("incidents.feature")


def screen(interface: Context) -> IncidentScreen:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, IncidentScreen), opened
	return opened


def lines(interface: Context) -> list[dict[str, str]]:
	model = screen(interface).table.model()
	titles = [str(model.headerData(column, Qt.Orientation.Horizontal)) for column in range(model.columnCount())]
	return [
		{title: str((model.index(row, column).data()) or ("")) for column, title in enumerate(titles)}
		for row in range(model.rowCount())
	]


def note(database: Connection, timestamp: str, level: str, kind: str, message: str, references: dict[str, str]) -> None:
	"""Une entrée du log, comme l'écrit Machin player ; chaque référence par le nom de l'élément."""
	ids = {
		"sound": ("sounds", "title"),
		"bank": ("banks", "internal_name"),
		"event": ("events", "internal_name"),
	}
	values = {key: None for key in ids}
	for key, (table, column) in ids.items():
		if references.get(key, "") != "":
			values[key] = identifier(database, table, column, references[key])
	database.execute(
		"INSERT INTO log (logged_at, level, kind, message, sound_id, bank_id, event_id)"
		" VALUES (%s, %s, %s, %s, %s, %s, %s)",
		(
			datetime.fromisoformat(timestamp).astimezone(),
			level,
			kind,
			message,
			values["sound"],
			values["bank"],
			values["event"],
		),
	)


# ─── Étant donné ───────────────────────────────────────────


@given("le log :")
def log(empty_database: Connection, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	for values in rows:
		line = dict(zip((header.strip() for header in headers), (v.strip() for v in values), strict=True))
		note(empty_database, line["logged_at"], line["level"], line["kind"], line["message"], line)


@given("le log est vide")
def empty_log(empty_database: Connection) -> None:
	empty_database.execute("DELETE FROM log")


@given(parsers.parse("{count:d} alertes « {kind} » dans le log, une par minute depuis « {start} »"))
def warnings(empty_database: Connection, count: int, kind: str, start: str) -> None:
	departure = datetime.fromisoformat(start)
	for rank in range(count):
		note(empty_database, (departure + timedelta(minutes=rank)).isoformat(), "warning", kind, f"n° {rank}", {})


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("Machin player note l'incident « {kind} » à « {timestamp} »"))
def incident(empty_database: Connection, kind: str, timestamp: str) -> None:
	note(empty_database, timestamp, "incident", kind, "", {})


@when(parsers.re(r"je (?P<gesture>coche|décoche) « Montrer aussi les informations »"))
def information(interface: Context, gesture: str) -> None:
	box = screen(interface).ui.information
	assert box.isChecked() == (gesture == "décoche")
	box.click()


@when(parsers.parse("je tape « {text} » dans le filtre des incidents"))
def apply_filter(interface: Context, qtbot: QtBot, text: str) -> None:
	type_(qtbot, screen(interface).ui.filter_, text)


@when(parsers.parse("j'ouvre la cellule « {cell} » de l'entrée « {kind} »"))
def open_cell(interface: Context, qtbot: QtBot, cell: str, kind: str) -> None:
	table = screen(interface).table
	model = table.model()
	found_list = [
		model.index(row, column)
		for row in range(model.rowCount())
		for column in range(model.columnCount())
		if (model.index(row, 2).data() == kind) and (model.index(row, column).data() == cell)
	]
	assert len(found_list) == 1, found_list
	index: QModelIndex = found_list[0]
	table.scrollTo(index)
	centre = table.visualRect(index).center()
	qtbot.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)
	qtbot.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)


# ─── Alors ─────────────────────────────────────────────────


@then("la liste des incidents montre :")
def shows(interface: Context, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	expected_list = [
		dict(zip((e.strip() for e in headers), (v.strip() for v in values), strict=True)) for values in rows
	]
	assert lines(interface) == expected_list


@then(parsers.re(r"la liste des incidents montre les natures (?P<kinds>.+)"))
def kinds(interface: Context, kinds: str) -> None:
	assert [line["Nature"] for line in lines(interface)] == NAME.findall(kinds)


@then(parsers.parse("la liste des incidents commence par la nature « {kind} »"))
def first(interface: Context, kind: str) -> None:
	assert lines(interface)[0]["Nature"] == kind


@then(parsers.parse("le compte des incidents est « {text} »"))
def count(interface: Context, text: str) -> None:
	assert screen(interface).ui.count.text() == text
