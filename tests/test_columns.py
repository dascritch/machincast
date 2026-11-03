"""Scénarios des colonnes des tableaux de l'interface (https://github.com/dascritch/machincast/issues/207).

Chaque test a son propre fichier de réglages des vues (tests/conftest.py, view_settings) : jamais celui du compte.
Les étapes de la fenêtre, des onglets et des éléments en base sont dans tests/interface_steps.py.
"""

import codecs
from pathlib import Path

import psycopg
from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QAction, QMouseEvent, QStandardItemModel
from PySide6.QtWidgets import (
	QAbstractItemView,
	QApplication,
	QCalendarWidget,
	QGroupBox,
	QMenu,
	QTableView,
	QTreeView,
	QWidget,
)
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import columns as column_module
from machincast.interface.columns import EXPORT, REINSTATE, Columns
from machincast.interface.search import SearchScreen
from tests.interface_steps import NAME, Context, choose_in_menu, tab, window

scenarios("columns.feature")

Connection = psycopg.Connection[tuple[object, ...]]
WAITING = 3000
"""Millisecondes qu'un ajustement a pour se faire : il attend la fin de la lecture du tableau."""
VIEWS = {
	"liste-evenements",
	"liste-sequences",
	"liste-banques",
	"liste-sonores",
	"liste-feeds",
	"recherche",
	"incidents",
	"accueil-airplay",
	"accueil-a-venir",
	"onglet-airplay",
	"simulation",
	"fiche-banque-sonores",
	"fiche-sequence-elements",
	"fiche-evenement-elements",
	"fiche-sonore-relations",
	"fiche-sonore-passages",
}
"""Les vues de l'interface, une par tableau."""


def all_(screen: QWidget) -> list[Columns]:
	return [columns for view in screen.findChildren(QAbstractItemView) for columns in view.findChildren(Columns)]


def of_the_tab(interface: Context, title: str) -> Columns:
	tabs = window(interface).ui.tabs
	screen = tabs.widget(tab(interface, title))
	(found_list,) = all_(screen)
	return found_list


def of_the_card(interface: Context, group: str) -> Columns:
	"""Les colonnes du tableau de la fiche ouverte qui est dans l'encart de ce titre."""
	card = window(interface).ui.tabs.currentWidget()
	assert card is not None

	def in_(columns: Columns) -> bool:
		parent = columns.view.parentWidget()
		while parent is not None:
			if (isinstance(parent, QGroupBox)) and (group in parent.title()):
				return True
			parent = parent.parentWidget()
		return False

	(found_list,) = [columns for columns in all_(card) if in_(columns)]
	return found_list


def columns_of(interface: Context, place: str) -> Columns:
	"""« l'onglet « Sonores » » ou « du tableau « Sonores » de la fiche »."""
	name = NAME.findall(place)[0]
	if place.startswith("du tableau"):
		return of_the_card(interface, name)
	return of_the_tab(interface, name)


def index(columns: Columns, title: str) -> int:
	return columns.titles().index(title)


def width(columns: Columns, title: str) -> int:
	return columns.header.sectionSize(index(columns, title))


def entry(columns: Columns, text: str) -> QAction:
	(action,) = [action for action in columns.menu().actions() if action.text() == text]
	return action


PLACE = r"(?P<place>de l'onglet « [^»]+ »|du tableau « [^»]+ » de la fiche)"


# ─── Étant donné ───────────────────────────────────────────


@given(
	parsers.re(
		r"une disposition de la vue « (?P<view>[^»]+) », sa dernière colonne en premier,"
		r" gardée pour les colonnes (?P<titles>«.+)"
	)
)
def old_layout(view: str, titles: str) -> None:
	"""Une disposition valable, mais gardée pour d'autres titres de colonnes que ceux de la vue."""
	old_list = NAME.findall(titles)
	model = QStandardItemModel(0, len(old_list))
	model.setHorizontalHeaderLabels(old_list)
	table = QTableView()
	table.setModel(model)
	table.horizontalHeader().moveSection(len(old_list) - 1, 0)
	settings = QSettings(str(column_module.file()), QSettings.Format.IniFormat)
	settings.beginGroup(view)
	settings.setValue("colonnes", old_list)
	settings.setValue("disposition", table.horizontalHeader().saveState())
	settings.endGroup()
	settings.sync()
	table.deleteLater()


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(rf"j'élargis la colonne « (?P<title>[^»]+) » {PLACE} à (?P<pixels>\d+) pixels"))
def widen(interface: Context, qtbot: QtBot, title: str, place: str, pixels: str) -> None:
	"""À la souris, comme l'utilisateur : la bordure droite du titre glisse jusqu'à la largeur voulue."""
	columns = columns_of(interface, place)
	qtbot.wait(50)
	header = columns.header
	column = index(columns, title)
	edge = header.sectionViewportPosition(column) + header.sectionSize(column) - 1
	height = header.height() // 2
	target = edge + int(pixels) - header.sectionSize(column)
	screen = header.viewport()
	for category, x, buttons in (
		(QEvent.Type.MouseButtonPress, edge, Qt.MouseButton.LeftButton),
		(QEvent.Type.MouseMove, target, Qt.MouseButton.LeftButton),
		(QEvent.Type.MouseButtonRelease, target, Qt.MouseButton.NoButton),
	):
		position = QPointF(x, height)
		event = QMouseEvent(
			category,
			position,
			screen.mapToGlobal(position),
			Qt.MouseButton.LeftButton,
			buttons,
			Qt.KeyboardModifier.NoModifier,
		)
		QApplication.sendEvent(screen, event)
	assert header.sectionSize(column) == int(pixels), header.sectionSize(column)


@when(parsers.re(rf"je glisse la colonne « (?P<title>[^»]+) » {PLACE} en première place"))
def slide(interface: Context, title: str, place: str) -> None:
	columns = columns_of(interface, place)
	header = columns.header
	header.moveSection(header.visualIndex(index(columns, title)), 0)


@when(parsers.re(rf"je (?P<gesture>coche|décoche) « (?P<title>[^»]+) » dans le menu des colonnes {PLACE}"))
def tick(interface: Context, gesture: str, title: str, place: str) -> None:
	action = entry(columns_of(interface, place), title)
	assert action.isEnabled()
	assert action.isChecked() == (gesture == "décoche")
	action.trigger()


@when(parsers.re(rf"je choisis « {REINSTATE} » dans le menu des colonnes {PLACE}"))
def reinstate(interface: Context, place: str) -> None:
	entry(columns_of(interface, place), REINSTATE).trigger()


@when(parsers.parse("je tape « {text} » dans le champ de recherche"))
def type_(interface: Context, text: str) -> None:
	(search,) = window(interface).findChildren(SearchScreen)
	search.field.setText(text)


@when(parsers.parse("le sonore « {title} » est ajouté à la banque « {bank} » en base"))
def add_to_bank(empty_database: Connection, title: str, bank: str) -> None:
	line = empty_database.execute(
		"INSERT INTO sounds (type, location, title) VALUES ('file', %s, %s) RETURNING id",
		(f"/srv/{title}.flac", title),
	).fetchone()
	assert line is not None
	empty_database.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position) SELECT id, %s, 99 FROM banks WHERE internal_name = %s",
		(line[0], bank),
	)


@when("j'ouvre chaque onglet et la fiche de chaque genre")
def all_open(interface: Context, qtbot: QtBot) -> None:
	opened = window(interface)
	for menu_entry in (
		"Ouvrir l'onglet Sonores",
		"Ouvrir l'onglet Feeds",
		"Ouvrir l'onglet Simulation",
		"Ouvrir l'onglet Airplay",
		"Rechercher…",
	):
		choose_in_menu(interface, menu_entry, "Affichage")
	for category in ("banque", "séquence", "événement", "sonore"):
		opened._open_card(category, None)
	qtbot.wait(50)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(rf"la colonne « (?P<title>[^»]+) » {PLACE} montre « (?P<text>[^»]+) » en entier"))
def in_integer(interface: Context, qtbot: QtBot, title: str, place: str, text: str) -> None:
	columns = columns_of(interface, place)
	required = columns.view.fontMetrics().horizontalAdvance(text)
	qtbot.waitUntil(lambda: width(columns, title) >= required, timeout=WAITING)


@then(parsers.re(rf"la colonne « (?P<title>[^»]+) » {PLACE} (?P<verdict>fait|ne fait pas) (?P<pixels>\d+) pixels"))
def done(interface: Context, qtbot: QtBot, title: str, place: str, verdict: str, pixels: str) -> None:
	qtbot.wait(100)
	columns = columns_of(interface, place)
	assert (width(columns, title) == int(pixels)) == (verdict == "fait"), width(columns, title)


@then(parsers.re(rf"la dernière colonne {PLACE} s'étire jusqu'au bord du tableau"))
def stretched(interface: Context, qtbot: QtBot, place: str) -> None:
	columns = columns_of(interface, place)
	header = columns.header
	last = header.logicalIndex(header.count() - 1)

	def until_edge() -> bool:
		return header.sectionViewportPosition(last) + header.sectionSize(last) == header.viewport().width()

	qtbot.waitUntil(until_edge, timeout=WAITING)


@then(parsers.re(rf"les colonnes {PLACE} sont (?P<titles>«.+)"))
def shown_list(interface: Context, place: str, titles: str) -> None:
	assert columns_of(interface, place).shown_list() == NAME.findall(titles)


@then(parsers.re(rf"le menu des colonnes {PLACE} propose :"))
def menu(interface: Context, place: str, datatable: list[list[str]]) -> None:
	_, *lines = datatable

	def line(action: QAction) -> list[str]:
		if action.isSeparator():
			return ["—", ""]
		if not action.isCheckable():
			return [action.text(), ""]
		if action.isChecked():
			return [action.text(), "coché"]
		return [action.text(), "décoché"]

	obtained_list = [line(action) for action in columns_of(interface, place).menu().actions()]
	assert obtained_list == [[value.strip() for value in line] for line in lines]


@then(parsers.re(rf"l'entrée « (?P<title>[^»]+) » du menu des colonnes {PLACE} est inactive"))
def inactive(interface: Context, title: str, place: str) -> None:
	assert not entry(columns_of(interface, place), title).isEnabled()


@then(parsers.parse("les réglages du compte gardent la vue « {view} »"))
def kept(view: str) -> None:
	settings = QSettings(str(column_module.file()), QSettings.Format.IniFormat)
	assert view in settings.childGroups(), settings.childGroups()


@then("le fichier de configuration n'a pas changé")
def intact_configuration(interface: Context) -> None:
	path = window(interface).configuration
	assert path is not None
	assert path.read_bytes() == interface.initial_configuration


@then("chaque tableau de l'interface a des colonnes déplaçables, de largeur libre, avec le menu des colonnes de sa vue")
def table_all(interface: Context) -> None:
	opened = window(interface)
	views = [
		view
		for view in opened.findChildren(QAbstractItemView)
		if (isinstance(view, (QTableView, QTreeView))) and (not _in_calendar(view))
	]
	names = set()
	for view in views:
		(columns,) = view.findChildren(Columns)
		header = columns.header
		assert header.sectionsMovable(), columns.name
		# La dernière colonne affichée peut s'étirer jusqu'au bord du tableau ; les autres sont de largeur libre.
		last = header.logicalIndex(header.count() - 1)
		free_list = [column for column in range(header.count()) if column != last]
		assert all(header.sectionResizeMode(column) == header.ResizeMode.Interactive for column in free_list), (
			columns.name
		)
		assert header.property(column_module.PROPERTY) == columns.name
		names.add(columns.name)
	assert names == VIEWS, sorted(names ^ VIEWS)


def _in_calendar(view: QWidget) -> bool:
	"""Le tableau des jours d'un sélecteur de date n'est pas un tableau de l'interface."""
	parent = view.parentWidget()
	while parent is not None:
		if isinstance(parent, QCalendarWidget):
			return True
		parent = parent.parentWidget()
	return False


# ─── Exporter un tableau (https://github.com/dascritch/machincast/issues/329) ───


def _texts(menu: QMenu) -> list[str]:
	"""Les entrées du menu, dans l'ordre ; un séparateur s'écrit « — »."""
	texts = []
	for action in menu.actions():
		text = action.text()
		if action.isSeparator():
			text = "—"
		texts.append(text)
	return texts


def _export(interface: Context, tab_: str, file: str | None) -> None:
	"""Le sélecteur de fichier est remplacé : il note le nom proposé, puis rend un fichier du test, ou rien."""

	def choose(_parent: QWidget, offers: str) -> Path | None:
		interface.offered_list.append(offers)
		if file is None:
			return None
		return interface.directory / file

	interface.offered_list = []
	interface.monkeypatch.setattr(column_module, "choose_file", choose)
	columns = of_the_tab(interface, tab_)
	menu = columns.table_menu(QPoint(-1, -1))
	(action,) = [action for action in menu.actions() if action.text() == EXPORT]
	action.trigger()


@when(
	parsers.re(
		r"je choisis « Exporter ce tableau… » au clic droit dans le tableau de l'onglet « (?P<tab_>[^»]+) »,"
		r" vers « (?P<file>[^»]+) »"
	)
)
def export(interface: Context, tab_: str, file: str) -> None:
	_export(interface, tab_, file)


@when(parsers.parse("j'abandonne « Exporter ce tableau… » au clic droit dans le tableau de l'onglet « {tab_} »"))
def abandon(interface: Context, tab_: str) -> None:
	_export(interface, tab_, None)


@then("le clic droit hors des lignes de chaque tableau de l'interface ne propose que « Exporter ce tableau… »")
def export_everywhere(interface: Context) -> None:
	views = [
		view
		for view in window(interface).findChildren(QAbstractItemView)
		if (isinstance(view, (QTableView, QTreeView))) and (not _in_calendar(view))
	]
	for view in views:
		(columns,) = view.findChildren(Columns)
		assert view.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu, columns.name
		assert _texts(columns.table_menu(QPoint(-1, -1))) == [EXPORT], columns.name


@then(parsers.parse("le sélecteur de fichier a proposé « {name} »"))
def offers(interface: Context, name: str) -> None:
	assert interface.offered_list == [name]


@then(parsers.parse("le fichier « {file} » contient, en UTF-8 avec BOM :"))
def content(interface: Context, file: str, docstring: str) -> None:
	bytes_ = (interface.directory / file).read_bytes()
	assert bytes_.startswith(codecs.BOM_UTF8)
	assert bytes_.decode("utf-8-sig") == f"{docstring}\n"


@then(parsers.parse("le fichier « {file} » contient la ligne « {line} »"))
def contains_line(interface: Context, file: str, line: str) -> None:
	assert line in (interface.directory / file).read_text(encoding="utf-8-sig").splitlines()


@then(parsers.parse("le fichier « {file} » n'existe pas"))
def absent(interface: Context, file: str) -> None:
	assert not (interface.directory / file).exists()


@then("aucun fichier n'est exporté")
def nothing(interface: Context) -> None:
	assert interface.offered_list == ["liste-banques.csv"]
	assert list(interface.directory.glob("*.csv")) == []


@then(parsers.parse("la barre d'état annonce que le tableau est exporté dans « {file} »"))
def announces(interface: Context, file: str) -> None:
	expected = f"Tableau exporté dans {interface.directory / file}."
	assert window(interface).statusBar().currentMessage() == expected


@then(parsers.parse("la barre d'état commence par « {start} »"))
def begins(interface: Context, start: str) -> None:
	assert window(interface).statusBar().currentMessage().startswith(start)


@then(
	parsers.re(
		r"le clic droit sur la ligne « (?P<name>[^»]+) » de l'onglet « (?P<tab_>[^»]+) » propose d'abord"
		r" « (?P<first>[^»]+) », et finit par (?P<last_list>«.+)"
	)
)
def line_menu(interface: Context, name: str, tab_: str, first: str, last_list: str) -> None:
	columns = of_the_tab(interface, tab_)
	view = columns.view
	model = view.model()
	(row,) = [row for row in range(model.rowCount()) if name in str(model.index(row, 1).data())]
	position = view.visualRect(model.index(row, 1)).center()
	texts = _texts(columns.table_menu(position))
	end = NAME.findall(last_list)
	assert (texts[0], texts[-len(end) :]) == (first, end), texts
