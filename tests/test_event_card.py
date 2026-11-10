"""Scénarios de la fiche d'un événement (https://github.com/dascritch/machincast/issues/32).

Les étapes de la fenêtre, des listes, des fiches et des fenêtres de dialogue sont dans tests/interface_steps.py ;
celles-ci manipulent la fiche de l'événement, et lisent la base de test.
"""

import re
from collections.abc import Callable
from datetime import datetime

import pytest
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import QAbstractButton, QComboBox, QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.event_card import EventCard
from machincast.player.broadcast import GRID_FINGERPRINT
from tests.interface_steps import NAME, Connection, Context, identifier, open_in, slide, window

scenarios("event_card.feature")

DATE = "dd/MM/yyyy HH:mm"
IN_DATABASE = re.compile(r"(le sonore|la banque|la séquence|le fichier) « ([^»]+) »")


def card(interface: Context) -> EventCard:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, EventCard), opened
	return opened


def lines(interface: Context) -> list[QTreeWidgetItem]:
	return card(interface).items.lines()


def choose(interface: Context, name: str) -> None:
	"""Rend courante la seule ligne de l'élément."""
	found_list = []
	for line in lines(interface):
		if line.text(1) == name:
			found_list.append(line)
	assert len(found_list) == 1, f"« {name} » : {len(found_list)} lignes"
	card(interface).ui.items.setCurrentItem(found_list[0])


def choose_text(choice: QComboBox, text: str) -> None:
	index = choice.findText(text, Qt.MatchFlag.MatchFixedString)
	assert index >= 0, f"« {text} » absent : {[choice.itemText(i) for i in range(choice.count())]}"
	choice.setCurrentIndex(index)


def if_ticked(box: QAbstractButton, read: Callable[[], str]) -> Callable[[], str]:
	"""Ce que montre un champ qui ne compte que si sa case est cochée : rien sinon."""

	def playback() -> str:
		if not box.isChecked():
			return ""
		return read()

	return playback


def _combo(combo: QComboBox) -> Callable[[], str]:
	"""Le choix d'une liste déroulante, et « (grisé) » quand elle ne se choisit pas."""

	def shown() -> str:
		text = combo.currentText().casefold()
		if not combo.isEnabled():
			text += " (grisé)"
		return text

	return shown


def shows(event: EventCard) -> dict[str, Callable[[], str]]:
	"""Ce que la fiche montre, par nom de champ à l'écran."""
	ui = event.ui
	return {
		"Nom interne": ui.internal_name.text,
		"Nom public": ui.public_name.text,
		"Priorité": lambda: ui.priority.currentText().casefold(),
		"Artiste et titre": lambda: ui.hiding.currentText().casefold(),
		"Début": if_ticked(ui.has_start, ui.start.text),
		"Fin": if_ticked(ui.has_end, ui.end.text),
		"Jours": lambda: ", ".join(day.text() for day in event.days if day.isChecked()),
		# https://github.com/dascritch/machincast/issues/350
		"Fin de la liste": _combo(ui.end_of_list),
		"Secours de fin de liste": _combo(ui.end_fallback),
		"Secours d'un stream tombé": _combo(ui.stream_fallback),
	}


def boxes(event: EventCard) -> dict[str, QAbstractButton]:
	ui = event.ui
	day_dict = {}
	for day in event.days:
		day_dict[day.text()] = day
	return {"Début": ui.has_start, "Fin": ui.has_end} | day_dict


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("« {name} » qui vient de passer dans l'événement « {event} »"))
def play(empty_database: Connection, name: str, event: str) -> None:
	"""Le début d'un passage dans l'historique de diffusion, joué par la ligne de la banque ou du sonore dans la liste
	de l'événement."""
	empty_database.execute(
		"INSERT INTO airplay (play_id, line_type, event_id, event_item_id, bank_id)"
		" SELECT gen_random_uuid(), 'start', ev.id, e.id, e.bank_id FROM event_items e"
		" JOIN events ev ON ev.id = e.event_id LEFT JOIN banks b ON b.id = e.bank_id"
		" LEFT JOIN sounds s ON s.id = e.sound_id WHERE ev.internal_name = %s AND %s IN (b.internal_name, s.title)",
		(event, name),
	)


# ─── Quand ─────────────────────────────────────────────────


@when("je saisis dans la fiche de l'événement :")
def enter(interface: Context, datatable: list[list[str]]) -> None:
	"""Une date vide décoche sa case ; les jours se donnent tous, ceux qui manquent sont décochés."""
	event = card(interface)
	ui = event.ui
	_headers, *rows = datatable
	field_list = []
	for field, raw in rows:
		field_list.append((field.strip(), raw.strip()))
	for field, raw in field_list:
		combos = {
			"Priorité": ui.priority,
			"Artiste et titre": ui.hiding,
			"Fin de la liste": ui.end_of_list,
			"Secours de fin de liste": ui.end_fallback,
			"Secours d'un stream tombé": ui.stream_fallback,
		}
		if field in combos:
			choose_text(combos[field], raw)
		else:
			if field in ("Début", "Fin"):
				box, date = {"Début": (ui.has_start, ui.start), "Fin": (ui.has_end, ui.end)}[field]
				if raw != "":
					date.setDateTime(QDateTime.fromString(raw, DATE))
				box.setChecked(raw != "")
			else:
				assert field == "Jours", field
				ticked_list = set()
				for day in raw.split(","):
					if day.strip():
						ticked_list.add(day.strip())
				for day in event.days:
					day.setChecked(day.text() in ticked_list)


@when(parsers.re(r"je (?P<gesture>coche|décoche) « (?P<box>[^»]+) » dans la fiche de l'événement"))
def tick(interface: Context, gesture: str, box: str) -> None:
	button = boxes(card(interface))[box]
	assert button.isChecked() == (gesture == "décoche"), f"« {box} » est déjà dans cet état"
	# Un clic au centre d'une case élargie par sa colonne tombe à côté de son texte : click() la coche comme un clic.
	button.click()


@when(parsers.parse("je saisis la fin « {text} » dans la fiche de l'événement"))
def enter_end(interface: Context, text: str) -> None:
	ui = card(interface).ui
	ui.end.setDateTime(QDateTime.fromString(text, DATE))
	ui.has_end.setChecked(True)


@when(parsers.parse("je choisis l'élément « {name} » de l'événement"))
def choose_item(interface: Context, name: str) -> None:
	choose(interface, name)


@then(parsers.re(r"les boutons de ligne actifs de l'événement sont (?P<buttons>.+)"))
def line_buttons(interface: Context, buttons: str) -> None:
	ui = card(interface).ui
	active_list = []
	for button in (ui.remove_item, ui.raise_, ui.go_down):
		if button.isEnabled():
			active_list.append(button.text())
	assert active_list == NAME.findall(buttons)


@when(
	parsers.re(
		r"j'ajoute les feeds (?P<names>« [^»]+ »(?:, « [^»]+ »)*),"
		r" en effaçant « (?P<erased>[^»]+) » de la base pendant le choix"
	)
)
def add_in_erasing(interface: Context, qtbot: QtBot, empty_database: Connection, names: str, erased: str) -> None:
	name_list = []
	for name in NAME.findall(names):
		name_list.append(identifier(empty_database, "feeds", "name", name))
	interface.chosen_feeds = name_list
	empty_database.execute("DELETE FROM feeds WHERE name = %s", (erased,))
	qtbot.mouseClick(card(interface).ui.add_feeds, Qt.MouseButton.LeftButton)


@when(parsers.parse("je choisis l'élément n° {number:d} de l'événement"))
def choose_number(interface: Context, number: int) -> None:
	card(interface).ui.items.setCurrentItem(lines(interface)[number - 1])


@when(parsers.re(r"je retire les éléments (?P<names>.+)"))
def remove(interface: Context, qtbot: QtBot, names: str) -> None:
	for name in NAME.findall(names):
		choose(interface, name)
		qtbot.mouseClick(card(interface).ui.remove_item, Qt.MouseButton.LeftButton)


@when(parsers.re(r"je dépose sur les éléments de l'événement (?P<what>.+)"))
def drop_in(interface: Context, what: str) -> None:
	slide(interface, card(interface).ui.items, what, True, False)


@when(parsers.parse("j'ouvre l'élément « {name} » de l'événement"))
def open_item(interface: Context, qtbot: QtBot, name: str) -> None:
	open_in(qtbot, card(interface).ui.items, name)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"la priorité se choisit parmi (?P<priorities>.+)"))
def priorities(interface: Context, priorities: str) -> None:
	choice = card(interface).ui.priority
	index_list = []
	for index in range(choice.count()):
		index_list.append(choice.itemText(index).casefold())
	assert index_list == NAME.findall(priorities)


@then("la fiche de l'événement montre :")
def shown_list(interface: Context, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	players = shows(card(interface))
	expected_list = []
	for field, value in rows:
		expected_list.append((field.strip(), value.strip()))
	value_list = []
	for field, _value in expected_list:
		value_list.append((field, players[field]()))
	assert value_list == expected_list


@then("la fiche de l'événement montre les éléments :")
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


@then(parsers.re(r"la fiche de l'événement montre les éléments (?P<names>aucun|«.+)"))
def shown_items(interface: Context, names: str) -> None:
	line_list = []
	for line in lines(interface):
		line_list.append(line.text(1))
	assert line_list == NAME.findall(names)


@then(parsers.re(r"la fiche de l'événement (?:n')?avertit (?:de rien|« (?P<text>.+) »)"))
def warns(interface: Context, text: str | None) -> None:
	"""Sous la liste : ce que la diffusion sautera. « De rien » : ni là, ni en haut de la fiche."""
	assert card(interface).ui.warning.text() == ((text) or (""))
	if text is None:
		assert not card(interface).warning.isVisibleTo(card(interface))


@then(parsers.re(r"la grille de la fiche de l'événement se saisit par (?P<what>.+)"))
def grid(interface: Context, what: str) -> None:
	"""Les cases de dates actives, et « les jours » quand tous les jours se cochent ; « rien » sinon."""
	event = card(interface)
	ui = event.ui
	active_list = []
	for box in (ui.has_start, ui.has_end):
		if box.isEnabled():
			active_list.append(box.text().replace("&", ""))
	every_one = True
	for day in event.days:
		if not (day.isEnabled()):
			every_one = False
			break
	if every_one:
		active_list.append("les jours")
	else:
		found = False
		for day in event.days:
			if day.isEnabled():
				found = True
				break
		assert not found
	expected_list = NAME.findall(what)
	if what.endswith("les jours"):
		expected_list.append("les jours")
	assert active_list == expected_list
	assert (ui.start.isEnabled(), ui.end.isEnabled()) == (ui.has_start.isChecked(), ui.has_end.isChecked())


@then(parsers.parse("l'événement « {name} » a en base :"))
def event_in_database(empty_database: Connection, name: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	expected_list = [(field.strip(), value.strip()) for field, value in rows]
	fetched_list = []
	for field, _value in expected_list:
		column = {
			"priorite": "priority::text",
			"recurrence_days": "recurrence_days::text[]",
			"end_of_list": "end_of_list::text",
			"end_fallback": "(SELECT f.internal_name FROM events f WHERE f.id = events.end_fallback_event_id)",
			"stream_fallback": "(SELECT f.internal_name FROM events f WHERE f.id = events.stream_fallback_event_id)",
		}.get(field, field)
		line = empty_database.execute(
			f"SELECT {column} FROM events WHERE internal_name = %s",  # noqa: S608
			(name,),
		).fetchone()
		assert line is not None, f"« {name} » absent de la base"
		value = line[0]
		if isinstance(value, datetime):
			value = value.astimezone()
		fetched_list.append((field, str(value)))
	assert fetched_list == expected_list


@then(parsers.re(r"les éléments de l'événement « (?P<name>[^»]+) » sont, dans l'ordre, (?P<items>.+)"))
def items_in_database(interface: Context, empty_database: Connection, name: str, items: str) -> None:
	"""Un sonore par son titre, une banque ou une séquence par son nom, un sonore sans titre par son fichier."""
	lines_in_database = empty_database.execute(
		"SELECT e.position, CASE WHEN e.bank_id IS NOT NULL THEN 'la banque'"
		" WHEN e.sequence_id IS NOT NULL THEN 'la séquence' WHEN s.title IS NOT NULL THEN 'le sonore'"
		" ELSE 'le fichier' END, COALESCE(b.internal_name, q.internal_name, s.title, s.location)"
		" FROM event_items e JOIN events ev ON ev.id = e.event_id"
		" LEFT JOIN banks b ON b.id = e.bank_id LEFT JOIN sequences q ON q.id = e.sequence_id"
		" LEFT JOIN sounds s ON s.id = e.sound_id WHERE ev.internal_name = %s ORDER BY e.position",
		(name,),
	).fetchall()
	expected_list = []
	for category, item in IN_DATABASE.findall(items):
		expected_list.append((category, interface.path(item)))
	expected_list_2 = []
	for position, expected in enumerate(expected_list, start=1):
		expected_list_2.append((position, *expected))
	assert lines_in_database == expected_list_2


@then(
	parsers.re(
		r"l'historique de diffusion désigne, dans l'événement « (?P<name>[^»]+) », la ligne n° (?P<number>\d+)"
		r" et aucune ligne"
	)
)
def history(empty_database: Connection, name: str, number: str) -> None:
	"""Les passages, dans leur ordre : la position de la ligne qui les a joués, aucune pour une ligne retirée."""
	positions = empty_database.execute(
		"SELECT e.position FROM airplay a JOIN events ev ON ev.id = a.event_id"
		" LEFT JOIN event_items e ON e.id = a.event_item_id WHERE ev.internal_name = %s ORDER BY a.id",
		(name,),
	).fetchall()
	assert positions == [(int(number),), (None,)]


# ─── Empreinte de la grille (https://github.com/dascritch/machincast/issues/266) ───


def fingerprint(database: Connection) -> str:
	line = database.execute(GRID_FINGERPRINT).fetchone()
	assert line is not None
	return str(line[0])


@pytest.fixture
def fingerprints() -> list[str]:
	return []


@when("je note l'empreinte de la grille")
def note_fingerprint(empty_database: Connection, fingerprints: list[str]) -> None:
	fingerprints.append(fingerprint(empty_database))


@then(parsers.re(r"l'empreinte de la grille (?P<verdict>n'a pas changé|a changé)"))
def compared_fingerprint(empty_database: Connection, fingerprints: list[str], verdict: str) -> None:
	assert (fingerprint(empty_database) == fingerprints[0]) == (verdict == "n'a pas changé")
