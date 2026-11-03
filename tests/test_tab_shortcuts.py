"""Scénarios des raccourcis des onglets (https://github.com/dascritch/machincast/issues/192,
https://github.com/dascritch/machincast/issues/318).

Les étapes de la fenêtre et des fiches sont dans tests/interface_steps.py.
"""

from PySide6.QtCore import Qt
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.lists import List
from tests.interface_steps import NAME, Context, tab_title, window

scenarios("tab_shortcuts.feature")


def tooltips(interface: Context) -> dict[str, str]:
	tabs = window(interface).ui.tabs
	return {tab_title(tabs, index): tabs.tabToolTip(index) for index in range(tabs.count())}


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
	(found,) = [tabs.widget(index) for index in indices if tab_title(tabs, index) == title]
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
