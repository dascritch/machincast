"""Étapes partagées des scénarios de l'interface : les onglets de la fenêtre

Chargé comme greffon pytest par tests/conftest.py (https://github.com/dascritch/machincast/issues/444 : découpé de
tests/interface_steps.py, par domaine).
"""

from PySide6.QtCore import Qt
from pytest_bdd import parsers, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.card import Card
from machincast.interface.dialogs import Closing
from tests.interface_steps import NAME, Context, closable_list, closing_button, tab, tab_title, window


@then(parsers.parse("l'onglet « {title} » est fermé"))
def closed_tab(interface: Context, title: str) -> None:
	tabs = window(interface).ui.tabs
	titles = []
	for index in range(tabs.count()):
		titles.append(tab_title(tabs, index))
	assert title not in titles, titles


@when(parsers.parse("je ferme l'onglet « {title} »"))
def close_tab(interface: Context, qtbot: QtBot, title: str) -> None:
	tabs = window(interface).ui.tabs
	index = tab(interface, title)
	button = closing_button(tabs.tabBar(), index)
	assert button is not None, f"l'onglet « {title} » n'a pas de bouton de fermeture"
	interface.closed_list.append(tabs.widget(index))
	qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


@when("je ferme la fenêtre de l'interface")
def close_window(interface: Context) -> None:
	window(interface).close()


@when(parsers.re(r"je réponds « (?P<response>[^»]+) » à la question de (?:fermeture|rafraîchissement)"))
def answer_closing(interface: Context, response: str) -> None:
	interface.closing = Closing(response)


@then(parsers.re(r"la fenêtre a les onglets (?P<titles>.+)"))
def tabs(interface: Context, titles: str) -> None:
	tabs = window(interface).ui.tabs
	index_list = []
	for index in range(tabs.count()):
		index_list.append(tab_title(tabs, index))
	assert index_list == NAME.findall(titles)


@then(parsers.parse("l'onglet ouvert est « {title} »"))
def opened_tab(interface: Context, title: str) -> None:
	tabs = window(interface).ui.tabs
	assert tab_title(tabs, tabs.currentIndex()) == title


@then("aucun onglet n'a de bouton de fermeture")
def no_closable(interface: Context) -> None:
	assert closable_list(interface) == []


@then(parsers.re(r"seuls les onglets (?P<titles>«.+) ont un bouton de fermeture"))
def only_closable_ones(interface: Context, titles: str) -> None:
	assert closable_list(interface) == NAME.findall(titles)


@then(parsers.parse("seul l'onglet « {title} » a un bouton de fermeture"))
def only_closable(interface: Context, title: str) -> None:
	tabs = window(interface).ui.tabs
	closable_list = []
	for index in range(tabs.count()):
		if closing_button(tabs.tabBar(), index) is not None:
			closable_list.append(tab_title(tabs, index))
	assert closable_list == [title]


@then(parsers.re(r"la fenêtre de l'interface est (?P<state>fermée|ouverte)"))
def opened_window(interface: Context, state: str) -> None:
	assert window(interface).isVisible() == (state == "ouverte")


@then(parsers.re(r"la fenêtre (?P<verdict>n'a plus|a encore) d'onglet de fiche"))
def card_tab(interface: Context, verdict: str) -> None:
	tabs = window(interface).ui.tabs
	cards = []
	for index in range(tabs.count()):
		cards.append(tabs.widget(index))
	found = False
	for opened in cards:
		if isinstance(opened, Card):
			found = True
			break
	assert found == (verdict == "a encore")


@then("l'onglet « Antenne » montre l'écran par défaut")
def home(interface: Context) -> None:
	assert window(interface).ui.tabs.widget(0) is window(interface).home
