"""Scénarios de la fiche d'une séquence (https://github.com/dascritch/machincast/issues/112).

Les étapes de la fenêtre, des listes, des fiches et des fenêtres de dialogue sont dans tests/interface_steps.py ;
celles-ci manipulent la fiche de la séquence, et lisent la base de test.
"""

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.sequence_card import SequenceCard
from tests.interface_steps import NAME, Connection, Context, open_in, slide, window

scenarios("sequence_card.feature")

HIDINGS = {"selon la banque ou le sonore": None, "masqués": True, "affichés": False}
IN_DATABASE = re.compile(r"(le sonore|la banque|le fichier) « ([^»]+) »")


def card(interface: Context) -> SequenceCard:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, SequenceCard), opened
	return opened


def lines(interface: Context) -> list[QTreeWidgetItem]:
	list_ = card(interface).ui.items
	found_list = []
	for row in range(list_.topLevelItemCount()):
		found_list.append(list_.topLevelItem(row))
	lines = []
	for line in found_list:
		if line is not None:
			lines.append(line)
	return lines


def choose(interface: Context, name: str) -> None:
	"""Rend courante la seule ligne de l'élément."""
	found_list = []
	for line in lines(interface):
		if line.text(1) == name:
			found_list.append(line)
	assert len(found_list) == 1, f"« {name} » : {len(found_list)} lignes"
	card(interface).ui.items.setCurrentItem(found_list[0])


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("« {title} » qui vient de passer dans la séquence « {name} »"))
def play(empty_database: Connection, title: str, name: str) -> None:
	"""Le début d'un passage dans l'historique de diffusion, joué par la ligne du sonore dans la séquence."""
	empty_database.execute(
		"INSERT INTO airplay (play_id, line_type, sound_id, sequence_id, sequence_item_id, location, title)"
		" SELECT gen_random_uuid(), 'start', s.id, q.id, e.id, s.location, s.title FROM sequence_items e"
		" JOIN sequences q ON q.id = e.sequence_id JOIN sounds s ON s.id = e.sound_id"
		" WHERE q.internal_name = %s AND s.title = %s",
		(name, title),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je choisis l'élément « {name} »"))
def choose_item(interface: Context, name: str) -> None:
	choose(interface, name)


@when(parsers.parse("je choisis l'élément n° {number:d}"))
def choose_number(interface: Context, number: int) -> None:
	card(interface).ui.items.setCurrentItem(lines(interface)[number - 1])


@when(parsers.parse("je choisis l'élément « {name} », puis je descends"))
def go_down(interface: Context, qtbot: QtBot, name: str) -> None:
	choose(interface, name)
	qtbot.mouseClick(card(interface).ui.go_down, Qt.MouseButton.LeftButton)


@when(parsers.re(r"je retire les éléments (?P<names>.+)"))
def remove(interface: Context, qtbot: QtBot, names: str) -> None:
	for name in NAME.findall(names):
		choose(interface, name)
		qtbot.mouseClick(card(interface).ui.remove_item, Qt.MouseButton.LeftButton)


@when(
	parsers.re(
		r"je dépose sur les éléments de la séquence (?P<what>.+?)"
		r"(?P<relocation>, en ne proposant que le déplacement)?"
	)
)
def drop_in(interface: Context, what: str, relocation: str | None) -> None:
	slide(interface, card(interface).ui.items, what, True, relocation is not None)


@when(parsers.parse("j'ouvre l'élément « {name} » de la séquence"))
def open_item(interface: Context, qtbot: QtBot, name: str) -> None:
	open_in(qtbot, card(interface).ui.items, name)


@when(parsers.parse("j'ouvre l'événement « {name} » de la séquence"))
def open_event(interface: Context, qtbot: QtBot, name: str) -> None:
	open_in(qtbot, card(interface).ui.events, name)


# ─── Alors ─────────────────────────────────────────────────


@then(
	parsers.re(
		r"la fiche de la séquence montre le nom interne « (?P<name>[^»]*) », le nom public « (?P<public_name>[^»]*) »"
		r" et le masquage « (?P<hiding>[^»]+) »"
	)
)
def fields(interface: Context, name: str, public_name: str, hiding: str) -> None:
	ui = card(interface).ui
	shown_list = (ui.internal_name.text(), ui.public_name.text(), ui.hiding.currentText().casefold())
	assert shown_list == (name.strip(), public_name.strip(), hiding)


@then("la fiche de la séquence montre les éléments :")
def items_in_table(interface: Context, datatable: list[list[str]]) -> None:
	list_ = card(interface).ui.items
	headers, *rows = datatable
	titles = []
	for column in range(list_.columnCount()):
		titles.append(list_.headerItem().text(column))
	header_list = []
	for header in headers:
		header_list.append(header.strip())
	assert titles == header_list
	shown_list = []
	for line in lines(interface):
		column_list = []
		for column in range(list_.columnCount()):
			column_list.append(line.text(column))
		shown_list.append(column_list)
	values_list = []
	for values in rows:
		value_list = []
		for value in values:
			value_list.append(value.strip())
		values_list.append(value_list)
	assert shown_list == values_list


@then(parsers.re(r"la fiche de la séquence montre les éléments (?P<names>«.+)"))
def shown_items(interface: Context, names: str) -> None:
	line_list = []
	for line in lines(interface):
		line_list.append(line.text(1))
	assert line_list == NAME.findall(names)


@then(parsers.re(r"la fiche de la séquence montre les événements (?P<names>aucun|«.+)"))
def shown_events(interface: Context, names: str) -> None:
	list_ = card(interface).ui.events
	row_list = []
	for row in range(list_.count()):
		row_list.append(list_.item(row).text())
	assert row_list == NAME.findall(names)


@then(parsers.re(r"la fiche de la séquence (?:n')?avertit (?:de rien|« (?P<text>.+) »)"))
def warns(interface: Context, text: str | None) -> None:
	"""Sous la liste : ce que la diffusion sautera. « De rien » : ni là, ni en haut de la fiche."""
	assert card(interface).ui.warning.text() == ((text) or (""))
	if text is None:
		assert not card(interface).warning.isVisibleTo(card(interface))


@then(parsers.re(r"les boutons de ligne actifs de la séquence sont (?P<buttons>.+)"))
def line_buttons(interface: Context, buttons: str) -> None:
	ui = card(interface).ui
	active_list = []
	for button in (ui.remove_item, ui.raise_, ui.go_down):
		if button.isEnabled():
			active_list.append(button.text())
	assert active_list == NAME.findall(buttons)


@then("les éléments de la séquence se réordonnent par glisser-déposer, sans se déposer les uns dans les autres")
def reorderable(interface: Context) -> None:
	list_ = card(interface).ui.items
	assert list_.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
	assert lines(interface) != []
	every_one = True
	for line in lines(interface):
		if line.flags() & Qt.ItemFlag.ItemIsDropEnabled:
			every_one = False
			break
	assert every_one
	all_draggable = True
	for line in lines(interface):
		if not (line.flags() & Qt.ItemFlag.ItemIsDragEnabled):
			all_draggable = False
			break
	assert all_draggable


@then(
	parsers.re(
		r"la séquence « (?P<name>[^»]+) » est en base : (?:nom public « (?P<public_name>[^»]+) »|sans nom public),"
		r" masquage « (?P<hiding>[^»]+) »"
	)
)
def sequence_in_database(empty_database: Connection, name: str, public_name: str | None, hiding: str) -> None:
	lines = empty_database.execute(
		"SELECT public_name, hide_metadata FROM sequences WHERE internal_name = %s", (name,)
	).fetchall()
	assert lines == [(public_name, HIDINGS[hiding])]


@then(
	parsers.re(
		r"l'historique de diffusion désigne, dans la séquence « (?P<name>[^»]+) », la ligne n° (?P<number>\d+)"
		r" et aucune ligne"
	)
)
def history(empty_database: Connection, name: str, number: str) -> None:
	"""Les passages, dans leur ordre : la position de la ligne qui les a joués, aucune pour une ligne retirée."""
	positions = empty_database.execute(
		"SELECT e.position FROM airplay a JOIN sequences q ON q.id = a.sequence_id"
		" LEFT JOIN sequence_items e ON e.id = a.sequence_item_id WHERE q.internal_name = %s ORDER BY a.id",
		(name,),
	).fetchall()
	assert positions == [(int(number),), (None,)]


@then(parsers.re(r"les éléments de la séquence « (?P<name>[^»]+) » sont, dans l'ordre, (?P<items>.+)"))
def items_in_database(interface: Context, empty_database: Connection, name: str, items: str) -> None:
	"""Un sonore par son titre, une banque par son nom, un sonore sans titre par son fichier."""
	lines = empty_database.execute(
		"SELECT e.position, CASE WHEN e.bank_id IS NOT NULL THEN 'la banque' WHEN s.title IS NOT NULL"
		" THEN 'le sonore' ELSE 'le fichier' END, COALESCE(b.internal_name, s.title, s.location)"
		" FROM sequence_items e JOIN sequences q ON q.id = e.sequence_id"
		" LEFT JOIN banks b ON b.id = e.bank_id LEFT JOIN sounds s ON s.id = e.sound_id"
		" WHERE q.internal_name = %s ORDER BY e.position",
		(name,),
	).fetchall()
	expected_list = []
	for category, item in IN_DATABASE.findall(items):
		expected_list.append((category, interface.path(item)))
	positioned = []
	for position, expected in enumerate(expected_list, start=1):
		positioned.append((position, *expected))
	assert lines == positioned
