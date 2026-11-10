"""Scénarios de la recherche globale (https://github.com/dascritch/machincast/issues/27,
https://github.com/dascritch/machincast/issues/105).

Les étapes de la fenêtre, des onglets et des éléments en base sont dans tests/interface_steps.py.
"""

import psycopg
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCompleter
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.interface import search
from machincast.interface.search import SearchScreen
from tests.interface_steps import NAME, Context, window

scenarios("search.feature")

Connection = psycopg.Connection[tuple[object, ...]]


def screen(interface: Context) -> SearchScreen:
	tabs = window(interface).ui.tabs
	index_list = []
	for index in range(tabs.count()):
		if isinstance(widget := tabs.widget(index), SearchScreen):
			index_list.append(widget)
	(found,) = index_list
	return found


def lines(interface: Context) -> list[list[str]]:
	model = screen(interface).model
	lines = []
	for row in range(model.rowCount()):
		column_list = []
		for column in range(model.columnCount()):
			column_list.append(str((model.index(row, column).data()) or ("")))
		lines.append(column_list)
	return lines


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("{count:d} sonores titrés « {first} » à « {last} »"))
def numbered_sounds(empty_database: Connection, count: int, first: str, last: str) -> None:
	prefix = first.rsplit(" ", 1)[0]
	assert last == f"{prefix} {count:02d}"
	for number in range(1, count + 1):
		empty_database.execute(
			"INSERT INTO sounds (type, location, title, state) VALUES ('file', %s, %s, 'active')",
			(f"/srv/spots/{number:02d}.flac", f"{prefix} {number:02d}"),
		)


@given(parsers.parse("une table de résultats limitée à {limit:d} lignes"))
def limit(monkeypatch: pytest.MonkeyPatch, limit: int) -> None:
	monkeypatch.setattr(search, "LIMIT", limit)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je tape « {text} » dans le champ de recherche"))
def type_(interface: Context, text: str) -> None:
	screen(interface).field.setText(text)


@when(parsers.parse("j'ouvre le résultat « {name} »"))
def open_result(interface: Context, name: str) -> None:
	opened = screen(interface)
	line_list = []
	for rank, line in enumerate(lines(interface)):
		if line[1] == name:
			line_list.append(rank)
	(row,) = line_list
	opened.table.activated.emit(opened.model.index(row, 0))


@when(parsers.parse("la banque « {name} » est ajoutée en base"))
def added_bank(empty_database: Connection, name: str) -> None:
	empty_database.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, 'random')", (name,))


# ─── Alors ─────────────────────────────────────────────────


@then("le champ de recherche a le focus")
def has_focus(interface: Context) -> None:
	assert window(interface).focusWidget() is screen(interface).field


@then(parsers.parse("le champ de recherche a le focus, avec « {text} » sélectionné"))
def has_focus_and_selected(interface: Context, text: str) -> None:
	assert window(interface).focusWidget() is screen(interface).field
	assert screen(interface).field.selectedText() == text


@then(parsers.parse("le champ de recherche contient « {text} »"))
def contains(interface: Context, text: str) -> None:
	assert screen(interface).field.text() == text


@then("le champ de recherche ne propose pas de suggestions")
def without_suggestions(interface: Context) -> None:
	opened = screen(interface)
	assert opened.field.completer() is None
	assert opened.findChildren(QCompleter) == []


@then(parsers.re(r"les résultats nommés sont (?P<names>aucun|«.+)"))
def result_names(interface: Context, names: str) -> None:
	line_list = []
	for line in lines(interface):
		line_list.append(line[1])
	assert line_list == NAME.findall(names)


@then("les résultats sont :")
def results(interface: Context, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	model = screen(interface).model
	titles = []
	for column in range(model.columnCount()):
		titles.append(str(model.headerData(column, Qt.Orientation.Horizontal)))
	header_list = []
	for header in headers:
		header_list.append(header.strip())
	assert titles == header_list
	values_list = []
	for values in rows:
		value_list = []
		for value in values:
			value_list.append(value.strip())
		values_list.append(value_list)
	assert lines(interface) == values_list


@then(parsers.parse("le compte des résultats est « {text} »"))
def count(interface: Context, text: str) -> None:
	assert screen(interface).count.text() == text
