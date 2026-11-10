"""Scénarios de l'onglet Airplay (https://github.com/dascritch/machincast/issues/244).

Les passages sont écrits dans l'airplay de la base de test (tests/interface_steps.py). Le sélecteur de fichier de
l'export est remplacé par le choix du scénario ; les exports s'écrivent dans le répertoire temporaire du scénario.
"""

import csv
import re
from pathlib import Path

import psycopg
import pytest
from PySide6.QtWidgets import QWidget
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import dialogs
from machincast.interface.airplay_tab import AirplayScreen
from tests.categories import AIRPLAY_KEYS
from tests.interface_steps import NAME, Context, open_in, window

scenarios("airplay_tab.feature")

Connection = psycopg.Connection[tuple[object, ...]]


@pytest.fixture
def tracking() -> dict[str, str]:
	"""Ce que le scénario note en chemin : le nom proposé pour l'export."""
	return {}


def screen(interface: Context) -> AirplayScreen:
	tabs = window(interface).ui.tabs
	screens = []
	for index in range(tabs.count()):
		screens.append(tabs.widget(index))
	(found,) = [screen for screen in screens if isinstance(screen, AirplayScreen)]
	return found


def exports(interface: Context) -> Path:
	directory = interface.directory / "exports"
	directory.mkdir(exist_ok=True)
	return directory


def location(database: Connection, title: str) -> str:
	line = database.execute("SELECT location FROM sounds WHERE title = %s", (title,)).fetchone()
	assert line is not None
	return str(line[0])


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je règle l'onglet Airplay sur (?P<hours>\d+) heures?"))
def set_(interface: Context, hours: str) -> None:
	screen(interface).hours.setValue(int(hours))


@when(parsers.parse("j'ouvre dans l'onglet Airplay la cellule « {text} »"))
def open_cell(interface: Context, qtbot: QtBot, text: str) -> None:
	open_in(qtbot, screen(interface).table, text)


@when(parsers.parse("j'exporte l'onglet Airplay sous « {name} », avec le filtre « {filter_} »"))
def export(interface: Context, tracking: dict[str, str], name: str, filter_: str) -> None:
	def choose(_parent: QWidget, offers: str, filters: list[str], _title: str = "") -> tuple[Path, str]:
		assert filter_ in filters, filters
		tracking["propose"] = offers
		return exports(interface) / name, filter_

	interface.monkeypatch.setattr(dialogs, "choose_export", choose)
	screen(interface).export.click()


@when("j'abandonne l'export de l'onglet Airplay")
def abandon(interface: Context) -> None:
	def choose(_parent: QWidget, _offered: str, _filters: list[str], _title: str = "") -> None:
		return None

	interface.monkeypatch.setattr(dialogs, "choose_export", choose)
	screen(interface).export.click()


@when("l'onglet Antenne relit son airplay, pour un nouveau sonore")
def reread_home(interface: Context) -> None:
	window(interface).home.refresh_airplay()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("l'onglet Airplay montre les {hours:d} dernières heures"))
def shown_hours(interface: Context, hours: int) -> None:
	assert screen(interface).hours.value() == hours


def table(interface: Context) -> list[dict[str, str]]:
	opened = screen(interface)
	model = opened.model
	table = []
	for row in range(model.rowCount()):
		item_dict = {}
		for column, (key, _) in enumerate(opened.COLUMNS):
			item_dict[AIRPLAY_KEYS.get(key, key)] = model.item(row, column).text()
		table.append(item_dict)
	return table


@then("la table de l'onglet Airplay montre :")
def expected_table(interface: Context, datatable: list[list[str]]) -> None:
	headers, *lines = datatable
	expected_list = []
	for values in lines:
		v_list = []
		for v in values:
			v_list.append(v.strip())
		expected_list.append(dict(zip(headers, v_list, strict=True)))
	assert table(interface) == expected_list, table(interface)


@then(parsers.re(r"la table de l'onglet Airplay a (?P<count>\d+) lignes?"))
def lines(interface: Context, count: str) -> None:
	assert screen(interface).model.rowCount() == int(count), table(interface)


@then(parsers.parse("le clic droit sur la ligne « {title} » de l'onglet Airplay propose « {entry} »"))
def menu(interface: Context, title: str, entry: str) -> None:
	opened = screen(interface)
	model = opened.model
	(row,) = [
		row
		for row in range(model.rowCount())
		if any(model.index(row, column).data() == title for column in range(model.columnCount()))
	]
	line_menu = opened.line_menu(model.index(row, 0))
	assert line_menu is not None
	action_list = []
	for action in line_menu.actions():
		action_list.append(action.text())
	assert entry in action_list
	assert not line_menu.actions()[0].icon().isNull()


@then(parsers.parse("l'export proposait le nom « {name} »"))
def offered_name(tracking: dict[str, str], name: str) -> None:
	assert tracking["propose"] == name


def read(interface: Context, name: str) -> str:
	return (exports(interface) / name).read_text(encoding="utf-8-sig")


@then(parsers.parse("l'export « {name} » a l'en-tête « {header} »"))
def csv_header(interface: Context, name: str, header: str) -> None:
	assert read(interface, name).splitlines()[0] == header


@then(parsers.re(r"l'export « (?P<name>[^»]+) » a (?P<count>\d+) passages(?:, le premier « (?P<first>.+) »)?$"))
def csv_plays(interface: Context, name: str, count: str, first: str | None) -> None:
	_header, *rows = list(csv.reader(read(interface, name).splitlines(), delimiter=";"))
	assert len(rows) == int(count), rows
	if first is None:
		return
	expected = first.split(";")
	assert len(rows[0]) == len(expected), rows[0]
	for obtained, value in zip(rows[0], expected, strict=True):
		# « … » : une valeur quelconque, non vide.
		assert (obtained == value) or ((value == "…") and (obtained != "")), rows[0]


@then(parsers.parse("l'export « {name} » est une page HTML de {count:d} passages"))
def page(interface: Context, name: str, count: int) -> None:
	text = read(interface, name)
	assert text.startswith("<!DOCTYPE html>")
	assert len(re.findall(r"<tr class=\"passage\">", text)) == count, text


@then(parsers.re(r"l'export « (?P<name>[^»]+) » contient (?P<texts>.+) et l'emplacement de « (?P<title>[^»]+) »"))
def page_content(interface: Context, empty_database: Connection, name: str, texts: str, title: str) -> None:
	text = read(interface, name)
	for expected in [*NAME.findall(texts), location(empty_database, title)]:
		assert expected in text, expected


@then(
	parsers.parse(
		"dans l'export « {name} », la ligne de « {title} » a l'incident « {incident} », celle du « {other} » aucun"
	)
)
def page_incidents(interface: Context, name: str, title: str, incident: str, other: str) -> None:
	rows = re.findall(r'<tr class="passage">(.*?)</tr>', read(interface, name))
	cells = {}
	for row in rows:
		cells[re.findall(r"<td>(.*?)</td>", row)[4]] = re.findall(r"<td>(.*?)</td>", row)[-1]
	assert (cells[title], cells[other]) == (incident, ""), cells


@then(parsers.parse("l'export « {name} » commence par « {start} »"))
def m3u_start(interface: Context, name: str, start: str) -> None:
	assert read(interface, name).startswith(f"{start}\n")


@then(parsers.re(r"l'export « (?P<name>[^»]+) » donne, dans l'ordre, les emplacements de (?P<titles>.+)"))
def m3u_locations(interface: Context, empty_database: Connection, name: str, titles: str) -> None:
	fetched_list = []
	for line in read(interface, name).splitlines():
		if (line) and (not line.startswith("#")):
			fetched_list.append(line)
	title_list = []
	for title in NAME.findall(titles):
		title_list.append(location(empty_database, title))
	assert fetched_list == title_list


@then(parsers.re(r"l'export « (?P<name>[^»]+) » contient « (?P<first>[^»]+) » et « (?P<second>[^»]+) »$"))
def m3u_lines(interface: Context, name: str, first: str, second: str) -> None:
	fetched_list = read(interface, name).splitlines()
	assert (first in fetched_list) and (second in fetched_list), fetched_list


@then(parsers.parse("il n'y a pas d'export « {name} »"))
def without_export(interface: Context, name: str) -> None:
	assert not (exports(interface) / name).exists()


@then("aucun fichier n'a été exporté")
def no_export(interface: Context) -> None:
	assert list(exports(interface).iterdir()) == []


@then(parsers.parse("la barre d'état annonce un export, « {start} » suivi de son chemin"))
def announces(interface: Context, start: str) -> None:
	assert window(interface).ui.state_bar.currentMessage().startswith(start)
