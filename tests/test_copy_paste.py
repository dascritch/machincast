"""Scénarios du copier-coller des éléments d'un événement ou d'une séquence
(https://github.com/dascritch/machincast/issues/129).

Le presse-papiers est celui de l'application, vidé avant et après chaque scénario : sous la plateforme offscreen de
Qt, des données laissées au presse-papiers font planter Python à sa sortie, après les tests. Les fiches s'ouvrent par les étapes de
tests/interface_steps.py ; celle du scénario est l'onglet ouvert.
"""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QMimeData, QPoint
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.interface.card import Card
from machincast.interface.items import ItemList
from tests.interface_steps import NAME, Context, window
from tests.test_event_card import items_in_database

scenarios("copy_paste.feature")

then(parsers.re(r"les éléments de l'événement « (?P<name>[^»]+) » sont, dans l'ordre, (?P<items>.+)"))(
	items_in_database
)


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
	return items(interface).list_


@given("un presse-papiers vide")
def empty_clipboard() -> None:
	QGuiApplication.clipboard().setMimeData(QMimeData())


@when(parsers.parse("je choisis les éléments n° {first:d} à {last:d} de la liste"))
def choose(interface: Context, first: int, last: int) -> None:
	view = list_(interface)
	view.clearSelection()
	lines = items(interface).lines()
	view.setCurrentItem(lines[last - 1])
	for line in lines[first - 1 : last]:
		line.setSelected(True)


@when("je copie les éléments choisis")
def copy(interface: Context) -> None:
	items(interface).copy()


@when("je colle les éléments")
def paste(interface: Context) -> None:
	items(interface).paste()


def _menu_at(interface: Context, position: QPoint) -> dict[str, QAction]:
	menu = items(interface).columns.table_menu(position)
	found = {}
	for action in menu.actions():
		found[action.text()] = action
	return found


def _position(interface: Context, number: int) -> QPoint:
	line: QTreeWidgetItem = items(interface).lines()[number - 1]
	return list_(interface).visualItemRect(line).center()


@when(parsers.parse("je choisis « {entry} » au clic droit sur l'élément n° {number:d} de la liste"))
def right_click(interface: Context, entry: str, number: int) -> None:
	_menu_at(interface, _position(interface, number))[entry].trigger()


@then(parsers.re(r"la liste de la fiche montre les éléments (?P<names>«.+)"))
def shown(interface: Context, names: str) -> None:
	shown_list = []
	for line in items(interface).lines():
		shown_list.append(line.text(1))
	assert shown_list == NAME.findall(names)


@then("les éléments collés sont choisis")
def pasted_chosen(interface: Context) -> None:
	chosen_list = []
	for line in items(interface).chosen():
		chosen_list.append(line.text(1))
	assert chosen_list == ["Passage pub", "Les Gaufres – Spot"]


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
