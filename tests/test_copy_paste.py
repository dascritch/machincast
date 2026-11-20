"""Scénarios du copier-coller des éléments d'un événement ou d'une séquence
(https://github.com/dascritch/machincast/issues/129).

La liste de la fiche est celle de ses éléments, ou celle des sonores d'une banque. Le presse-papiers est celui de
l'application, vidé avant et après chaque scénario : sous la plateforme offscreen de
Qt, des données laissées au presse-papiers font planter Python à sa sortie, après les tests. Les fiches s'ouvrent par les étapes de
tests/interface_steps.py ; celle du scénario est l'onglet ouvert.
"""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QItemSelection, QItemSelectionModel, QMimeData, QPoint, Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.bank_card import BankCard
from machincast.interface.card import Card
from machincast.interface.columns import Columns
from machincast.interface.items import ItemList
from tests.interface_steps import NAME, Context, window
from tests.test_bank_card import sounds_in_database
from tests.test_event_card import items_in_database
from tests.test_search import result_names, screen, type_

scenarios("copy_paste.feature")

then(parsers.re(r"les éléments de l'événement « (?P<name>[^»]+) » sont, dans l'ordre, (?P<items>.+)"))(
	items_in_database
)
when(parsers.parse("je tape « {text} » dans le champ de recherche"))(type_)
then(parsers.re(r"les résultats nommés sont (?P<names>aucun|«.+)"))(result_names)
then(parsers.re(r"les sonores de la banque « (?P<name>[^»]+) » sont, dans l'ordre, (?P<titles>.+)"))(sounds_in_database)


@pytest.fixture(autouse=True)
def clipboard_emptied() -> Iterator[None]:
	"""Le presse-papiers vidé avant et après chaque scénario."""
	QGuiApplication.clipboard().clear()
	yield
	QGuiApplication.clipboard().clear()


def card(interface: Context) -> Card:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, Card), opened
	return opened


def items(interface: Context) -> ItemList:
	found = card(interface).items  # type: ignore[attr-defined]
	assert isinstance(found, ItemList)
	return found


def list_(interface: Context) -> QTreeWidget:
	opened = card(interface)
	if isinstance(opened, BankCard):
		return opened.ui.sounds
	return items(interface).list_


def lines(interface: Context) -> list[QTreeWidgetItem]:
	view = list_(interface)
	found = []
	for row in range(view.topLevelItemCount()):
		line = view.topLevelItem(row)
		assert line is not None
		found.append(line)
	return found


def name(interface: Context, line: QTreeWidgetItem) -> str:
	"""Le nom d'un sonore d'une banque est dans sa première colonne ; celui d'un élément, après son genre."""
	if isinstance(card(interface), BankCard):
		return line.text(0)
	return line.text(1)


def columns(interface: Context) -> Columns:
	opened = card(interface)
	if isinstance(opened, BankCard):
		return opened.columns
	return items(interface).columns


@given("un presse-papiers vide")
def empty_clipboard() -> None:
	QGuiApplication.clipboard().setMimeData(QMimeData())


@when(parsers.parse("je choisis les éléments n° {first:d} à {last:d} de la liste"))
def choose(interface: Context, first: int, last: int) -> None:
	view = list_(interface)
	view.clearSelection()
	found = lines(interface)
	view.setCurrentItem(found[last - 1])
	for line in found[first - 1 : last]:
		line.setSelected(True)


@when("je copie les éléments choisis")
def copy(interface: Context) -> None:
	opened = card(interface)
	if isinstance(opened, BankCard):
		opened.copy_sounds()
		return
	items(interface).copy()


@when("je colle les éléments")
def paste(interface: Context) -> None:
	opened = card(interface)
	if isinstance(opened, BankCard):
		opened.paste_sounds()
		return
	items(interface).paste()


@when(parsers.re(r"j'appuie sur Ctrl\+(?P<key>[CVX]) dans la liste"))
def keys(interface: Context, qtbot: QtBot, key: str) -> None:
	view = list_(interface)
	with qtbot.waitActive(window(interface)):
		window(interface).activateWindow()
	view.setFocus()
	qtbot.waitUntil(view.hasFocus, timeout=5000)
	qtbot.keyClick(view, key.lower(), Qt.KeyboardModifier.ControlModifier)


@when(parsers.parse("je choisis les résultats n° {first:d} à {last:d} de la recherche"))
def choose_results(interface: Context, qtbot: QtBot, first: int, last: int) -> None:
	"""Comme d'un clic, puis Maj+clic : la table a le focus."""
	table = screen(interface).table
	model = table.model()
	table.setCurrentIndex(model.index(first - 1, 0))
	selection = QItemSelection(model.index(first - 1, 0), model.index(last - 1, model.columnCount() - 1))
	table.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
	table.setFocus()
	qtbot.waitUntil(table.hasFocus, timeout=5000)


@when(parsers.parse("je choisis « {entry} » au clic droit dans la recherche"))
def right_click_results(interface: Context, entry: str) -> None:
	found = screen(interface).columns.table_menu(QPoint(-1, -1))
	action_list = []
	for action in found.actions():
		if action.text() == entry:
			action_list.append(action)
	(chosen_action,) = action_list
	chosen_action.trigger()


def _menu_at(interface: Context, position: QPoint) -> dict[str, QAction]:
	menu = columns(interface).table_menu(position)
	found = {}
	for action in menu.actions():
		found[action.text()] = action
	return found


def _position(interface: Context, number: int) -> QPoint:
	line = lines(interface)[number - 1]
	return list_(interface).visualItemRect(line).center()


@when(parsers.parse("je choisis « {entry} » au clic droit sur l'élément n° {number:d} de la liste"))
def right_click(interface: Context, entry: str, number: int) -> None:
	_menu_at(interface, _position(interface, number))[entry].trigger()


@then(parsers.re(r"la liste de la fiche montre les éléments (?P<names>«.+)"))
def shown(interface: Context, names: str) -> None:
	shown_list = []
	for line in lines(interface):
		shown_list.append(name(interface, line))
	assert shown_list == NAME.findall(names)


@then(parsers.re(r"les lignes choisies de la liste sont (?P<names>«.+)"))
def chosen(interface: Context, names: str) -> None:
	chosen_list = []
	for line in lines(interface):
		if line.isSelected():
			chosen_list.append(name(interface, line))
	assert chosen_list == NAME.findall(names)
	current = list_(interface).currentItem()
	assert current is not None
	assert name(interface, current) == chosen_list[-1]


@then(parsers.parse("la fiche dit « {text} »"))
def card_says(interface: Context, text: str) -> None:
	assert card(interface).message.text() == text


@then(
	parsers.re(
		r"le clic droit hors des lignes de la liste propose « Copier » (?P<copy>actif|inactif)"
		r" et « Coller » (?P<paste>actif|inactif)"
	)
)
def offered(interface: Context, copy: str, paste: str) -> None:
	view = list_(interface)
	found = _menu_at(interface, QPoint(5, view.viewport().height() - 2))
	assert (found["Copier"].isEnabled(), found["Coller"].isEnabled()) == (copy == "actif", paste == "actif")


@then("le presse-papiers contient le texte :")
def clipboard_text(docstring: str) -> None:
	assert QGuiApplication.clipboard().text() == docstring + "\n"


@then(parsers.re(r"le clic droit hors des lignes de la liste propose (?P<entries>«.+»)$"))
def offered_entries(interface: Context, entries: str) -> None:
	view = list_(interface)
	menu = columns(interface).table_menu(QPoint(5, view.viewport().height() - 2))
	text_list = []
	for action in menu.actions():
		if action.isSeparator():
			text_list.append("—")
		else:
			text_list.append(action.text())
	assert text_list == NAME.findall(entries)
