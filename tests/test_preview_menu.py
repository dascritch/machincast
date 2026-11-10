"""Scénarios de la pré-écoute depuis le menu contextuel d'une ligne (https://github.com/dascritch/machincast/issues/226).

Les étapes de la fenêtre, des fiches et des listes sont dans tests/interface_steps.py, celles de la pré-écoute dans
tests/preview_steps.py. Le menu d'une ligne se demande à l'écran qui le construit, comme le ferait le clic droit,
sans l'afficher : un menu ouvert attendrait qu'on le ferme.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

import psycopg
import pytest
from PySide6.QtCore import QItemSelectionModel, QModelIndex, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QAbstractButton, QMenu, QTreeWidget, QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import display, icons
from machincast.interface.bank_card import BankCard
from machincast.interface.event_card import EventCard
from machincast.interface.lists import List
from machincast.interface.sequence_card import SequenceCard
from machincast.interface.sound_card import SoundCard
from tests.interface_steps import Context, actions, identifier, list_, same_icon, slide, window

scenarios("preview_menu.feature")

Connection = psycopg.Connection[tuple[object, ...]]
PREVIEW = "Pré-écoute…"


@dataclass
class Menu:
	opened: QMenu | None = None
	asks: bool = False
	"""Un menu a été demandé, même s'il n'y en a pas eu."""
	entries: list[str] = field(default_factory=list)


@pytest.fixture
def menu() -> Menu:
	return Menu()


def _retain(menu: Menu, opened: QMenu | None) -> None:
	menu.asks = True
	menu.opened = opened
	menu.entries = []
	if opened is not None:
		action_list = []
		for action in opened.actions():
			action_list.append((action.text()) or ("—"))
		menu.entries = action_list


# ─── Étant donné ───────────────────────────────────────────


def _play(database: Connection, interface: Context, sound: int | None, title: str, hour: str) -> None:
	assert interface.clock is not None
	day = interface.clock.now().date()
	start = datetime.fromisoformat(f"{day.isoformat()}T{hour}:00").astimezone()
	database.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, title) VALUES (%s, 'start', %s, %s, %s)",
		(uuid.uuid4(), start, sound, title),
	)


@given(parsers.re(r"« (?P<title>[^»]+) » passé à l'antenne à (?P<hour>\d\d:\d\d)$"))
def passes(interface: Context, empty_database: Connection, title: str, hour: str) -> None:
	_play(empty_database, interface, identifier(empty_database, "sounds", "title", title), title, hour)


@given(parsers.parse("« {title} » passé à l'antenne à {hour}, son sonore supprimé depuis"))
def passes_then_deleted(interface: Context, empty_database: Connection, title: str, hour: str) -> None:
	"""L'airplay garde l'artiste et le titre du passage ; son sonore n'est plus désigné."""
	_play(empty_database, interface, None, title, hour)


# ─── Quand ─────────────────────────────────────────────────


def _list_line(opened: List, title: str) -> QModelIndex:
	model = opened.table.model()
	for row in range(model.rowCount()):
		for column in range(model.columnCount()):
			if model.index(row, column).data() == title:
				return model.index(row, 0)
	raise AssertionError(f"aucune ligne « {title} » dans la liste")


def _tree_line(tree: QTreeWidget, title: str) -> QTreeWidgetItem:
	for row in range(tree.topLevelItemCount()):
		line = tree.topLevelItem(row)
		found = False
		for column in range(tree.columnCount()):
			if title in line.text(column):
				found = True
				break
		if found:
			return line
	raise AssertionError(f"aucune ligne « {title} »")


@when(parsers.parse("je sélectionne les lignes « {first} » et « {second} » de la liste"))
def select(interface: Context, first: str, second: str) -> None:
	opened = list_(interface)
	selection = opened.table.selectionModel()
	selection.clearSelection()
	for title in (first, second):
		selection.select(
			_list_line(opened, title),
			QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
		)


@when(parsers.parse("j'ouvre le menu contextuel de la ligne « {title} » de la liste"))
def list_menu(interface: Context, menu: Menu, title: str) -> None:
	opened = list_(interface)
	_retain(menu, opened.line_menu(_list_line(opened, title)))


@when(parsers.parse("j'ouvre le menu contextuel de la ligne « {title} » de l'airplay"))
def airplay_menu(interface: Context, menu: Menu, title: str) -> None:
	home = window(interface).home
	model = home.airplay_model
	(row,) = [
		row
		for row in range(model.rowCount())
		if any(model.index(row, column).data() == title for column in range(model.columnCount()))
	]
	_retain(menu, home.airplay_menu(model.index(row, 0)))


@when(parsers.parse("j'ouvre le menu contextuel de la ligne « {title} » des éléments"))
def item_menu(interface: Context, menu: Menu, title: str) -> None:
	card = window(interface).ui.tabs.currentWidget()
	assert isinstance(card, (SequenceCard, EventCard)), card
	items = card.items
	_retain(menu, items.line_menu(_tree_line(items.list_, title)))


@when(parsers.parse("je dépose « {file} » sur les sonores de la banque"))
def drop_in(interface: Context, file: str) -> None:
	card = window(interface).ui.tabs.currentWidget()
	assert isinstance(card, BankCard), card
	slide(interface, card.ui.sounds, f"« {file} »", True, False)


@when(parsers.parse("j'ouvre le menu contextuel de la ligne « {title} » des sonores de la banque"))
def bank_menu(interface: Context, menu: Menu, title: str) -> None:
	card = window(interface).ui.tabs.currentWidget()
	assert isinstance(card, BankCard), card
	_retain(menu, card.sound_menu(_tree_line(card.ui.sounds, title)))


@when(parsers.parse("je choisis « {entry} » dans le menu contextuel"))
def choose(menu: Menu, entry: str) -> None:
	assert menu.opened is not None, "aucun menu contextuel"
	(action,) = [action for action in menu.opened.actions() if action.text() == entry]
	assert isinstance(action, QAction)
	action.trigger()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"le menu contextuel commence par « (?P<entry>[^»]+) »(?P<separator>, puis un séparateur)?"))
def begins_by(menu: Menu, entry: str, separator: str | None) -> None:
	assert menu.entries[:1] == [entry], menu.entries
	if entry == display.PREVIEW:
		# Toute entrée « Pré-écoute… » porte le casque (https://github.com/dascritch/machincast/issues/223).
		assert menu.opened is not None
		assert same_icon(menu.opened.actions()[0].icon(), icons.icon("preview"))
	if separator is not None:
		assert menu.opened is not None
		assert menu.opened.actions()[1].isSeparator(), menu.entries


@then(parsers.parse("le menu contextuel propose toujours « {entry} »"))
def offers_always(menu: Menu, entry: str) -> None:
	assert entry in menu.entries, menu.entries


@then(parsers.parse("le menu contextuel ne propose pas « {entry} »"))
def offered_not(menu: Menu, entry: str) -> None:
	assert menu.asks
	assert entry not in menu.entries, menu.entries


@then("il n'y a pas de menu contextuel")
def without_menu(menu: Menu) -> None:
	assert menu.asks
	assert menu.opened is None, menu.entries


# ─── Pré-écoute désactivée (https://github.com/dascritch/machincast/issues/339) ───


def _inactive(item: QAction | QAbstractButton, tooltip: str) -> None:
	assert (item.isEnabled(), item.toolTip()) == (False, tooltip)


@then(parsers.parse("l'entrée « {entry} » du menu contextuel est inactive, avec l'infobulle « {tooltip} »"))
def contextual_inactive_entry(menu: Menu, entry: str, tooltip: str) -> None:
	assert menu.opened is not None, "aucun menu contextuel"
	(action,) = [action for action in menu.opened.actions() if action.text() == entry]
	_inactive(action, tooltip)
	assert menu.opened.toolTipsVisible()


@then(parsers.parse("l'entrée « {entry} » du menu « {title} » est inactive, avec l'infobulle « {tooltip} »"))
def inactive_entry(interface: Context, entry: str, title: str, tooltip: str) -> None:
	(action,) = [action for action in actions(interface, title) if action.text() == entry]
	_inactive(action, tooltip)


@then(parsers.parse("le bouton « Pré-écoute » du prochain sonore est inactif, avec l'infobulle « {tooltip} »"))
def next_button(interface: Context, tooltip: str) -> None:
	_inactive(window(interface).home.ui.preview_next, tooltip)


@then(parsers.parse("le bouton « Pré-écoute… » de la fiche est inactif, avec l'infobulle « {tooltip} »"))
def card_button(interface: Context, tooltip: str) -> None:
	card = window(interface).ui.tabs.currentWidget()
	assert isinstance(card, SoundCard), card
	_inactive(card.ui.preview, tooltip)


@when("je clique sur le VU-mètre de l'antenne")
def click_on_vu_meter(interface: Context, qtbot: QtBot) -> None:
	qtbot.mouseClick(window(interface).home.vu_meter, Qt.MouseButton.LeftButton)


@when(parsers.parse("l'onglet Antenne demande la pré-écoute de « {title} »"))
def ask_preview(interface: Context, empty_database: Connection, title: str) -> None:
	"""Comme un clic sur la frise du prochain sonore : la fenêtre refuse elle-même une pré-écoute désactivée."""
	window(interface).home.requested_preview.emit(identifier(empty_database, "sounds", "title", title))


@then("il n'y a pas de fenêtre de pré-écoute")
def without_preview(interface: Context) -> None:
	assert window(interface).preview is None
