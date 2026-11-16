"""Étapes partagées des scénarios de l'interface : les listes (tables des sonores, banques, séquences, événements)

Chargé comme greffon pytest par tests/conftest.py (https://github.com/dascritch/machincast/issues/444 : découpé de
tests/interface_steps.py, par domaine).
"""

from PySide6.QtCore import QPoint, Qt
from pytest_bdd import given, parsers, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.lists import List
from tests.interface_steps import NAME, Connection, Context, lines, list_, marked_list, tab_title, type_, window
from tests.waiting import settle


@when(parsers.parse("je tape « {text} » dans le filtre de la liste"))
def apply_filter(interface: Context, qtbot: QtBot, text: str) -> None:
	type_(qtbot, list_(interface).filter_, text)


@given(parsers.parse("{count:d} sonores sans artiste ni titre, de /srv/grande/1.flac à /srv/grande/{last:d}.flac"))
def many_sounds(empty_database: Connection, count: int, last: int) -> None:
	"""https://github.com/dascritch/machincast/issues/383"""
	assert count == last
	empty_database.execute(
		"INSERT INTO sounds (type, location, state, duration)"
		" SELECT 'file', '/srv/grande/' || n || '.flac', 'active', '3 min' FROM generate_series(1, %s) n",
		(count,),
	)


@then(parsers.parse("la table de la liste a {count:d} lignes"))
def table_lines(interface: Context, count: int) -> None:
	assert list_(interface).table.model().rowCount() == count


@when("je descends au bas de la table de la liste")
def list_to_bottom(interface: Context, qtbot: QtBot) -> None:
	"""La vue demande la page suivante (fetchMore) en arrivant au bas de la table, une fois ses lignes disposées."""
	settle(qtbot)
	bar = list_(interface).table.verticalScrollBar()
	bar.setValue(bar.maximum())
	settle(qtbot)


@then(parsers.parse("la première ligne de la liste a pour titre « {title} »"))
def first_title(interface: Context, title: str) -> None:
	assert lines(interface)[0]["Titre"] == title, lines(interface)[:3]


@when(parsers.parse("je clique sur le titre de la colonne « {title} »"))
def sort(interface: Context, qtbot: QtBot, title: str) -> None:
	table = list_(interface).table
	header = table.horizontalHeader()
	model = table.model()
	titles = []
	for column_rank in range(model.columnCount()):
		titles.append(str(model.headerData(column_rank, Qt.Orientation.Horizontal)))
	column = titles.index(title)
	position = QPoint(header.sectionViewportPosition(column) + header.sectionSize(column) // 2, header.height() // 2)
	qtbot.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=position)


@when("j'efface le filtre de la liste")
def erase_filter(interface: Context) -> None:
	list_(interface).filter_.clear()


@then(parsers.re(r"les listes qui proposent de créer un élément sont (?P<buttons>.+)"))
def new_buttons(interface: Context, buttons: str) -> None:
	tabs = window(interface).ui.tabs
	with_ = []
	for index in range(tabs.count()):
		opened = tabs.widget(index)
		if (isinstance(opened, List)) and (not opened.ui.new.isHidden()):
			with_.append(f"{tab_title(tabs, index)} : {opened.ui.new.text()}")
	assert with_ == NAME.findall(buttons)


@then("la liste montre :")
def expected_entries(interface: Context, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	expected_list = []
	for values in rows:
		cells = []
		for v in values:
			cells.append(interface.path(v.strip()))
		expected_list.append(dict(zip(headers, cells, strict=True)))
	assert lines(interface) == expected_list, lines(interface)


@then(parsers.re(r"la colonne « (?P<column>[^»]+) » de la liste montre (?P<values>«.+)"))
def displayed_column(interface: Context, column: str, values: str) -> None:
	line_list = []
	for line in lines(interface):
		line_list.append(line[column])
	assert line_list == NAME.findall(values), lines(interface)


@then(parsers.re(r"la liste montre les titres (?P<titles>.+)"))
def shown_titles(interface: Context, titles: str) -> None:
	line_list = []
	for line in lines(interface):
		line_list.append(line["Titre"])
	assert line_list == NAME.findall(titles), lines(interface)


@then(parsers.re(r"la liste marque en anomalie les lignes (?P<names>.+), avec l'infobulle « (?P<tooltip>[^»]+) »"))
def anomalies(interface: Context, names: str, tooltip: str) -> None:
	name_list = []
	for name in NAME.findall(names):
		name_list.append([name, tooltip])
	assert marked_list(interface) == name_list


@then("la liste marque en anomalie les lignes et infobulles :")
def anomalies_and_tooltips(interface: Context, datatable: list[list[str]]) -> None:
	"""Chaque ligne en anomalie a son infobulle, propre à la ligne (https://github.com/dascritch/machincast/issues/140)."""
	_headers, *rows = datatable
	line_list = []
	for line, tooltip in rows:
		line_list.append([line.strip(), tooltip.strip()])
	assert marked_list(interface) == line_list


@then(parsers.parse("la première colonne de la liste est « {title} », avec l'infobulle « {tooltip} »"))
def anomaly_column(interface: Context, title: str, tooltip: str) -> None:
	model = list_(interface).table.model()
	header = (
		model.headerData(0, Qt.Orientation.Horizontal),
		model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole),
	)
	assert header == (title, tooltip)
	assert list_(interface).table.horizontalHeader().visualIndex(0) == 0


@then(parsers.parse("la liste n'a pas de colonne « {title} »"))
def without_column(interface: Context, title: str) -> None:
	model = list_(interface).table.model()
	titles = []
	for column in range(model.columnCount()):
		titles.append(model.headerData(column, Qt.Orientation.Horizontal))
	assert title not in titles


@then(parsers.parse("le compte de la liste est « {text} »"))
def count(interface: Context, text: str) -> None:
	assert list_(interface).count.text() == text
