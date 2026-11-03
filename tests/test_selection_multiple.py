"""Scénarios de la sélection multiple dans les listes des sonores et des banques
(https://github.com/dascritch/machincast/issues/114).

Les étapes de la fenêtre, des listes et des éléments en base sont dans tests/interface_steps.py ; les fenêtres de
dialogue y sont remplacées par les réponses du scénario.
"""

import re

import psycopg
from PySide6.QtCore import QItemSelection, QItemSelectionModel, QModelIndex, Qt
from PySide6.QtWidgets import QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.interface.bank_card import STATE_COLUMN, BankCard
from machincast.interface.lists import List
from tests.interface_steps import NAME, Context, identifier, list_, tab_title, window

scenarios("selection_multiple.feature")

Connection = psycopg.Connection[tuple[object, ...]]
HIDINGS = {"masqués": True, "affichés": False, "hérité": None}
"""Valeurs de banks.hide_metadata, par leur nom dans les scénarios."""


def index_of(opened: List, name: str) -> QModelIndex:
	"""La première cellule de la ligne dont une cellule porte ce nom."""
	model = opened.table.model()
	found_list = [
		model.index(row, 0)
		for row in range(model.rowCount())
		if any(model.index(row, column).data() == name for column in range(model.columnCount()))
	]
	assert len(found_list) == 1, name
	return found_list[0]


def menu(opened: List, index: QModelIndex) -> list[str]:
	choice = opened.line_menu(index)
	assert choice is not None
	# Les séparateurs ne sont pas des entrées.
	return [action.text() for action in choice.actions() if not action.isSeparator()]


def trigger(opened: List, index: QModelIndex, text: str) -> None:
	choice = opened.line_menu(index)
	assert choice is not None
	(action,) = [action for action in choice.actions() if action.text() == text]
	action.trigger()


def sounds_by_title(database: Connection, titles: str) -> list[int]:
	return [identifier(database, "sounds", "title", title) for title in NAME.findall(titles)]


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.re(r"les banques choisies (?P<names>aucune|«.+)"))
def chosen_banks(interface: Context, empty_database: Connection, names: str) -> None:
	interface.chosen_banks = [
		identifier(empty_database, "banks", "internal_name", name) for name in NAME.findall(names)
	]


@given("les confirmations d'action refusées")
def refused_confirmations(interface: Context) -> None:
	interface.action = False


@given(
	parsers.re(
		r"le masquage « (?P<first>[^»]+) » de la banque « (?P<bank>[^»]+) » et « (?P<second>[^»]+) »"
		r" de la banque « (?P<other>[^»]+) »"
	)
)
def hidings(empty_database: Connection, first: str, bank: str, second: str, other: str) -> None:
	for value, name in ((first, bank), (second, other)):
		empty_database.execute("UPDATE banks SET hide_metadata = %s WHERE internal_name = %s", (HIDINGS[value], name))


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je sélectionne les lignes (?P<names>«.+) de la liste"))
def select(interface: Context, names: str) -> None:
	opened = list_(interface)
	selection = QItemSelection()
	for name in NAME.findall(names):
		index = index_of(opened, name)
		selection.select(index, index)
	opened.table.selectionModel().select(
		selection, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows
	)


@when(parsers.parse("je choisis « {text} » au clic droit sur la sélection"))
def act_on_selection(interface: Context, text: str) -> None:
	opened = list_(interface)
	(first, *_others) = sorted(opened.table.selectionModel().selectedRows(), key=lambda index: index.row())
	trigger(opened, first, text)


@when(parsers.parse("je choisis « {text} » au clic droit sur la ligne « {name} »"))
def act_on_line(interface: Context, text: str, name: str) -> None:
	opened = list_(interface)
	trigger(opened, index_of(opened, name), text)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"le clic droit sur la sélection propose (?P<texts>«.+)"))
def selection_menu(interface: Context, texts: str) -> None:
	opened = list_(interface)
	(first, *_others) = sorted(opened.table.selectionModel().selectedRows(), key=lambda index: index.row())
	assert menu(opened, first) == NAME.findall(texts)


@then(parsers.parse("la dernière question, intitulée « {title} », a dit « {text} »"))
def last_question(interface: Context, title: str, text: str) -> None:
	assert interface.questions[-1] == f"action : {title}\n{text}", interface.questions


@then(parsers.parse("son bouton était « {button} »"))
def question_button(interface: Context, button: str) -> None:
	"""https://github.com/dascritch/machincast/issues/294"""
	assert interface.action_buttons[-1] == button, interface.action_buttons


@then(parsers.re(r"les sonores (?P<titles>«.+) sont à l'état « (?P<state>[^»]+) » en base"))
@then(parsers.re(r"le sonore (?P<titles>« [^»]+ ») est à l'état « (?P<state>[^»]+) » en base"))
def states_in_database(empty_database: Connection, titles: str, state: str) -> None:
	for sound in sounds_by_title(empty_database, titles):
		assert empty_database.execute("SELECT state::text FROM sounds WHERE id = %s", (sound,)).fetchone() == (state,)


@then(parsers.re(r"la liste montre l'état « (?P<state>[^»]+) » pour (?P<titles>«.+)"))
def shown_states(interface: Context, state: str, titles: str) -> None:
	opened = list_(interface)
	model = opened.table.model()
	column_titles = [model.headerData(rank, Qt.Orientation.Horizontal) for rank in range(model.columnCount())]
	column = column_titles.index("État")
	for title in NAME.findall(titles):
		assert model.index(index_of(opened, title).row(), column).data() == state, title


@then(parsers.re(r"les sonores de la banque « (?P<name>[^»]+) » sont, dans l'ordre, (?P<titles>aucun|«.+)"))
def bank_sounds(empty_database: Connection, name: str, titles: str) -> None:
	fetched_list = empty_database.execute(
		"SELECT s.title, bs.position FROM bank_sounds bs JOIN sounds s ON s.id = bs.sound_id"
		" JOIN banks b ON b.id = bs.bank_id WHERE b.internal_name = %s ORDER BY bs.position",
		(name,),
	).fetchall()
	assert [str(title) for title, _position in fetched_list] == NAME.findall(titles)
	# Les positions se suivent, sans trou.
	assert [int(str(position)) for _title, position in fetched_list] == list(range(1, len(fetched_list) + 1))


@then(parsers.re(r"le choix des banques a proposé (?P<names>«.+)"))
def offered_banks(interface: Context, empty_database: Connection, names: str) -> None:
	(offered_list,) = interface.offered_banks
	assert offered_list is not None
	assert offered_list == [identifier(empty_database, "banks", "internal_name", name) for name in NAME.findall(names)]


@then(parsers.re(r"l'audit complet est demandé pour les sonores (?P<titles>«.+), et pas pour « (?P<other>[^»]+) »"))
def request_audits(empty_database: Connection, titles: str, other: str) -> None:
	marks = [
		str(title)
		for (title,) in empty_database.execute(
			'SELECT title FROM sounds WHERE audit_requested ORDER BY title COLLATE "C"'
		)
	]
	assert marks == sorted(NAME.findall(titles))
	assert other not in marks


@then(
	parsers.re(
		r"le masquage des banques (?P<names>«.+) est « (?P<hiding>[^»]+) » en base,"
		r" et celui de « (?P<other>[^»]+) » « (?P<other_hiding>[^»]+) »"
	)
)
def hidings_in_database(empty_database: Connection, names: str, hiding: str, other: str, other_hiding: str) -> None:
	for name, expected in [(name, hiding) for name in NAME.findall(names)] + [(other, other_hiding)]:
		lu = empty_database.execute("SELECT hide_metadata FROM banks WHERE internal_name = %s", (name,)).fetchone()
		assert lu == (HIDINGS[expected],), name


@then(parsers.re(r"les listes qui sélectionnent plusieurs lignes sont (?P<tabs>«.+)"))
def multiple_lists(interface: Context, tabs: str) -> None:
	ui = window(interface).ui
	multiple_list = sorted(
		tab_title(ui.tabs, row)
		for row in range(ui.tabs.count())
		if (isinstance(screen := ui.tabs.widget(row), List))
		and (screen.table.selectionMode() == screen.table.SelectionMode.ExtendedSelection)
	)
	assert multiple_list == NAME.findall(tabs)


# ─── Fiche d'une banque ────────────────────────────────────

SOUND_STATE = re.compile(r"« ([^»]+) » ([^,]+)")
"""« Les Gaufres – Café à minuit » actif : le sonore de la fiche et son état affiché."""


def bank_card(interface: Context) -> BankCard:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, BankCard), opened
	return opened


def card_lines(interface: Context) -> list[QTreeWidgetItem]:
	sounds = bank_card(interface).ui.sounds
	return [line for row in range(sounds.topLevelItemCount()) if (line := sounds.topLevelItem(row))]


def card_line(interface: Context, name: str) -> QTreeWidgetItem:
	(line,) = [line for line in card_lines(interface) if line.text(0) == name]
	return line


def choose_to_right_click(interface: Context, line: QTreeWidgetItem, text: str) -> None:
	menu = bank_card(interface).sound_menu(line)
	assert menu is not None
	(action,) = [action for action in menu.actions() if action.text() == text]
	action.trigger()


@when(parsers.re(r"je sélectionne les sonores (?P<names>«.+) de la fiche"))
def select_in_card(interface: Context, names: str) -> None:
	sounds = bank_card(interface).ui.sounds
	sounds.clearSelection()
	chosen_list = NAME.findall(names)
	sounds.setCurrentItem(card_line(interface, chosen_list[0]))
	for name in chosen_list:
		card_line(interface, name).setSelected(True)


@when(parsers.parse("je choisis « {text} » au clic droit sur les sonores choisis de la fiche"))
def chosen_sound_state(interface: Context, text: str) -> None:
	first = bank_card(interface).ui.sounds.selectedItems()[0]
	choose_to_right_click(interface, first, text)


@when(parsers.parse("je choisis « {text} » au clic droit sur le sonore « {name} » de la fiche"))
def sound_state(interface: Context, text: str, name: str) -> None:
	choose_to_right_click(interface, card_line(interface, name), text)


@then(parsers.re(r"les sonores de la fiche sont, avec leur état, (?P<sounds>aucun|«.+)"))
def card_states(interface: Context, sounds: str) -> None:
	shown_list = [(line.text(0), line.text(STATE_COLUMN)) for line in card_lines(interface)]
	assert shown_list == SOUND_STATE.findall(sounds)


@then("seul « ➖ Retirer le sonore » sert aux sonores choisis de la fiche")
def only_remove(interface: Context) -> None:
	ui = bank_card(interface).ui
	assert [ui.remove_sound.isEnabled(), ui.raise_.isEnabled(), ui.go_down.isEnabled()] == [True, False, False]


@then(parsers.parse("l'avertissement de réintégration a dit « {text} »"))
def warning(interface: Context, text: str) -> None:
	assert interface.questions == [f"retrait : {text}"]


@when(parsers.parse("le sonore « {title} » repasse en aperçu en base"))
def replays_in_preview(empty_database: Connection, title: str) -> None:
	empty_database.execute("UPDATE sounds SET state = 'preview' WHERE title = %s", (title,))
