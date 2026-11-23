"""Scénarios des boutons du cartouchier, réglés dans Machin interface (https://github.com/dascritch/machincast/issues/512).

La fenêtre du plugin se connecte à la base de test, au rôle machincast_interface.
"""

import re
from collections.abc import Iterator

import psycopg
import pytest
from machincast_cartwall.settings import ButtonsSettings
from PySide6.QtWidgets import QComboBox, QPushButton
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot
from tests.database_fixtures import configuration_test, sample_database_parameters

from conftest import PLUGIN, Connection, stored
from machincast.database import Role, open_connection

scenarios(str(PLUGIN / "tests" / "features" / "settings.feature"))


def _connect() -> psycopg.Connection[tuple[object, ...]]:
	socket, database = sample_database_parameters()
	return open_connection(socket, database, Role.INTERFACE)


def _unreachable() -> psycopg.Connection[tuple[object, ...]]:
	raise psycopg.OperationalError("connexion refusée")


class Opened:
	window: ButtonsSettings | None = None


@pytest.fixture
def opened(qtbot: QtBot) -> Iterator[Opened]:
	found = Opened()
	yield found
	if found.window is not None:
		found.window.close()


def _window(opened: Opened) -> ButtonsSettings:
	assert opened.window is not None
	return opened.window


@when(parsers.re(r"j'ouvre les réglages du cartouchier(?P<without>, sans base)?$"))
def open_settings(opened: Opened, qtbot: QtBot, base: Connection, without: str | None) -> None:
	connect = _connect
	if without is not None:
		connect = _unreachable
	opened.window = ButtonsSettings(configuration_test(), None, connect)
	qtbot.addWidget(opened.window)


def _items(combo: QComboBox) -> list[str]:
	found = []
	for index in range(combo.count()):
		found.append(combo.itemText(index))
	return found


def _choose(combo: QComboBox, text: str) -> None:
	index = combo.findText(text)
	assert index >= 0, (text, _items(combo))
	combo.setCurrentIndex(index)


def _names(text: str) -> list[str]:
	return re.findall(r"«\s?([^»]*?)\s?»", text)


@then(parsers.re(r"les comptes proposés sont (?P<names>.+)$"))
def accounts(opened: Opened, names: str) -> None:
	assert _items(_window(opened).account) == _names(names)


@when(parsers.parse("je choisis le compte « {name} »"))
def account(opened: Opened, name: str) -> None:
	_choose(_window(opened).account, name)


@then("la liste des boutons est :")
def listed(opened: Opened, datatable: list[list[str]]) -> None:
	window = _window(opened)
	found = []
	for row in range(window.list.count()):
		item = window.list.item(row)
		found.append(item.text())
	expected = []
	for line in datatable:
		expected.append(line[0].strip())
	assert found == expected


@when(parsers.parse("je choisis l'action « {action} »"))
def action(opened: Opened, action: str) -> None:
	_choose(_window(opened).action, action)


@then(
	parsers.re(
		r"les cibles proposées sont (?P<names>« [^»]+ »(?:, « [^»]+ »)*), et le blanc (?P<blank>est grisé|se choisit)$"
	)
)
def proposed(opened: Opened, names: str, blank: str) -> None:
	window = _window(opened)
	assert window.target.isEnabled()
	assert _items(window.target) == _names(names)
	assert window.blank.isEnabled() == (blank == "se choisit")


@then("aucune cible n'est proposée, et le blanc est grisé")
def no_target(opened: Opened) -> None:
	window = _window(opened)
	assert (window.target.isEnabled(), window.target.count(), window.blank.isEnabled()) == (False, 0, False)


@when(parsers.re(r"je remplis le bouton (?P<fields>«.*»)$"))
def fill(opened: Opened, fields: str) -> None:
	window = _window(opened)
	label, colour, action_, target, blank = _names(fields)
	_choose(window.action, action_)
	if target != "":
		_choose(window.target, target)
	if blank != "":
		_choose(window.blank, blank)
	# L'intitulé, écrit après le choix de l'action, remplace celui qu'elle propose.
	window.label.setText(label)
	window.colour.setText(colour)


@when(parsers.parse("je choisis le bouton « {label} »"))
def choose_button(opened: Opened, label: str) -> None:
	window = _window(opened)
	for row, button in enumerate(window.buttons):
		if button.label == label:
			window.list.setCurrentRow(row)
			return
	raise AssertionError(label)


@when(parsers.parse("j'appuie sur « {text} »"))
def click(opened: Opened, text: str) -> None:
	found = []
	for button in _window(opened).findChildren(QPushButton):
		if button.text() == text:
			found.append(button)
	assert len(found) == 1, text
	assert found[0].isEnabled(), text
	found[0].click()


@then(parsers.parse("les boutons de « {user} » sont :"))
def saved(base: Connection, user: str, datatable: list[list[str]]) -> None:
	expected = []
	for row in datatable[1:]:
		cells = []
		for cell in row:
			cells.append(cell.strip())
		expected.append(cells)
	assert stored(base, user) == expected


@then(parsers.parse("la fenêtre dit « {text} »"))
def says(opened: Opened, text: str) -> None:
	assert _window(opened).message.text() == text


@then("la fenêtre dit que les boutons ne se lisent ni ne s'enregistrent")
def unreachable(opened: Opened) -> None:
	assert _window(opened).message.text() == "Les boutons ne se lisent ni ne s'enregistrent : connexion refusée"


@when(parsers.parse("je choisis la cible « {name} »"))
def target(opened: Opened, name: str) -> None:
	_choose(_window(opened).target, name)


@when(parsers.parse("j'écris l'intitulé « {text} »"))
def write_label(opened: Opened, text: str) -> None:
	_window(opened).label.setText(text)


@then(parsers.parse("l'intitulé est « {text} »"))
def label_is(opened: Opened, text: str) -> None:
	assert _window(opened).label.text() == text
