"""Scénarios des raccourcis des onglets (https://github.com/dascritch/machincast/issues/192,
https://github.com/dascritch/machincast/issues/318, https://github.com/dascritch/machincast/issues/428,
https://github.com/dascritch/machincast/issues/529).

Les étapes de la fenêtre et des fiches sont dans tests/interface_steps.py.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton, QMenu
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import key_hints
from machincast.interface.lists import List
from tests.interface_steps import NAME, Context, actions, named_menu, tab_title, window

scenarios("tab_shortcuts.feature")


def tooltips(interface: Context) -> dict[str, str]:
	tabs = window(interface).ui.tabs
	tooltips = {}
	for index in range(tabs.count()):
		tooltips[tab_title(tabs, index)] = tabs.tabToolTip(index)
	return tooltips


@then(parsers.re(r"les onglets ont pour infobulles (?P<texts>«.+)"))
def tooltip_all(interface: Context, texts: str) -> None:
	assert list(tooltips(interface).values()) == NAME.findall(texts)


@then(parsers.parse("l'onglet « {title} » a pour infobulle « {text} »"))
def tooltip(interface: Context, title: str, text: str) -> None:
	assert tooltips(interface)[title] == text


@then(parsers.parse("l'onglet « {title} » n'a pas d'infobulle"))
def without_tooltip(interface: Context, title: str) -> None:
	assert tooltips(interface)[title] == ""


# ─── Onglet précédent, suivant, premier et dernier (https://github.com/dascritch/machincast/issues/318) ───


def screen(interface: Context, title: str) -> List:
	tabs = window(interface).ui.tabs
	indices = range(tabs.count())
	index_list = []
	for index in indices:
		if tab_title(tabs, index) == title:
			index_list.append(tabs.widget(index))
	(found,) = index_list
	assert isinstance(found, List), found
	return found


@when(parsers.parse("je donne le focus au tableau de l'onglet « {title} »"))
def focus_to_table(interface: Context, qtbot: QtBot, title: str) -> None:
	table = screen(interface, title).ui.table
	table.setFocus()
	qtbot.waitUntil(table.hasFocus)


@when("je clique sur l'horloge de l'onglet Antenne")
def click_clock(interface: Context, qtbot: QtBot) -> None:
	qtbot.mouseClick(window(interface).home.ui.hour, Qt.MouseButton.LeftButton)


@when(parsers.parse("je saisis « {text} » dans le filtre de l'onglet « {title} », le curseur à la fin"))
def enter_filter(interface: Context, qtbot: QtBot, text: str, title: str) -> None:
	filter_ = screen(interface, title).ui.filter_
	filter_.setFocus()
	qtbot.waitUntil(filter_.hasFocus)
	filter_.clear()
	qtbot.keyClicks(filter_, text)
	assert filter_.cursorPosition() == len(text)


# ─── Fermer, enregistrer et rouvrir un onglet (https://github.com/dascritch/machincast/issues/428) ───


def submenu(interface: Context, title: str, menu: str) -> QMenu:
	"""Le sous-menu, ouvert comme sous la souris : son menu le relit, puis lui-même (aboutToShow)."""
	named_menu(interface, menu).aboutToShow.emit()
	found_list = []
	for action in actions(interface, menu):
		under_menu = action.menu()
		if (isinstance(under_menu, QMenu)) and (action.text() == title):
			found_list.append(under_menu)
	(found,) = found_list
	found.aboutToShow.emit()
	return found


@then(parsers.parse("le sous-menu « {title} » du menu « {menu} » est inactif"))
def inactive_submenu(interface: Context, title: str, menu: str) -> None:
	assert not submenu(interface, title, menu).menuAction().isEnabled()


@then(parsers.re(r"le sous-menu « (?P<title>[^»]+) » du menu « (?P<menu>[^»]+) » propose (?P<titles>«.+»)$"))
def offered_submenu(interface: Context, title: str, menu: str, titles: str) -> None:
	under_menu = submenu(interface, title, menu)
	assert under_menu.menuAction().isEnabled()
	text_list = []
	for action in under_menu.actions():
		text_list.append(action.text().split("\t")[0])
	assert text_list == NAME.findall(titles)


@when(parsers.parse("je choisis « {entry} » dans le sous-menu « {title} » du menu « {menu} »"))
def choose_in_submenu(interface: Context, entry: str, title: str, menu: str) -> None:
	found_list = []
	for action in submenu(interface, title, menu).actions():
		if action.text().split("\t")[0] == entry:
			found_list.append(action)
	(found,) = found_list
	found.trigger()


# ─── Raccourcis en surimpression (https://github.com/dascritch/machincast/issues/529) ───

HELD_KEYS = {"Ctrl": Qt.Key.Key_Control, "Alt": Qt.Key.Key_Alt}


@pytest.fixture(autouse=True)
def short_hold(monkeypatch: pytest.MonkeyPatch) -> None:
	"""L'attente de la touche tenue, raccourcie : 50 ms au lieu d'une seconde."""
	monkeypatch.setattr(key_hints, "HOLD_DELAY", 50)


def _hints(interface: Context) -> list[key_hints.Hint]:
	return window(interface).key_hints.shown


def _press(interface: Context, qtbot: QtBot, key: Qt.Key) -> None:
	with qtbot.waitActive(window(interface)):
		window(interface).activateWindow()
	qtbot.keyPress(window(interface), key)


@when(parsers.re(r"je tiens la touche (?P<key>Ctrl|Alt)"))
def hold(interface: Context, qtbot: QtBot, key: str) -> None:
	_press(interface, qtbot, HELD_KEYS[key])
	qtbot.waitUntil(lambda: _hints(interface) != [], timeout=5000)


@when(parsers.re(r"je relâche la touche (?P<key>Ctrl|Alt)"))
def release(interface: Context, qtbot: QtBot, key: str) -> None:
	qtbot.keyRelease(window(interface), HELD_KEYS[key])


@when("je presse Ctrl puis F avant la fin de l'attente")
def interrupted(interface: Context, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(key_hints, "HOLD_DELAY", 200)
	_press(interface, qtbot, Qt.Key.Key_Control)
	qtbot.keyPress(window(interface), Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
	qtbot.waitUntil(lambda: not window(interface).key_hints.waiting(), timeout=5000)


def _on_button(hint: key_hints.Hint) -> str:
	if isinstance(hint.target, QAbstractButton):
		return hint.target.text()
	return ""


@then(parsers.parse("les raccourcis en surimpression comptent « {text} » sur « {button} »"))
def on_button(interface: Context, text: str, button: str) -> None:
	found = []
	for hint in _hints(interface):
		if _on_button(hint) == button:
			found.append(hint.text)
	assert text in found, _hints(interface)


@then(parsers.parse("les raccourcis en surimpression comptent « {text} » pour « {entry} »"))
def for_entry(interface: Context, text: str, entry: str) -> None:
	found = []
	for hint in _hints(interface):
		if hint.entry == entry:
			found.append(hint.text)
	assert text in found, _hints(interface)


@then(parsers.re(r"les raccourcis en surimpression ne comptent aucun raccourci (?:de |d')(?P<key>Ctrl|Alt)"))
def without(interface: Context, key: str) -> None:
	for hint in _hints(interface):
		assert f"{key}+" not in hint.text, hint


@then("aucun raccourci n'est en surimpression")
def nothing_shown(interface: Context) -> None:
	assert _hints(interface) == []
	assert window(interface).key_hints.labels == []
