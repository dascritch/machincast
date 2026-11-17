"""Scénarios des raccourcis des onglets (https://github.com/dascritch/machincast/issues/192,
https://github.com/dascritch/machincast/issues/318, https://github.com/dascritch/machincast/issues/428).

Les étapes de la fenêtre et des fiches sont dans tests/interface_steps.py.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

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


@then(parsers.parse("l'entrée « {entry} » du menu « {menu} » est {state}"))
def menu_entry_state(interface: Context, entry: str, menu: str, state: str) -> None:
	found_list = []
	for action in actions(interface, menu):
		if action.text() == entry:
			found_list.append(action)
	(found,) = found_list
	assert found.isEnabled() == (state == "active"), state


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
