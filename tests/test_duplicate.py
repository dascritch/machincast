"""Scénarios de la duplication d'un événement, d'une séquence ou d'une banque
(https://github.com/dascritch/machincast/issues/130).

Les étapes de la fenêtre, des fiches et des éléments en base sont dans tests/interface_steps.py.
"""

from datetime import datetime

import psycopg
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import QTreeWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.bank_card import BankCard
from machincast.interface.card import Card
from machincast.interface.event_card import EventCard
from machincast.interface.lists import IDENTIFIER, List
from tests.interface_steps import ITEM, NAME, Context, identifier, tab_title, window

scenarios("duplicate.feature")

Connection = psycopg.Connection[tuple[object, ...]]
TABLES = {"séquence": "sequences", "événement": "events", "banque": "banks"}
ITEMS = {
	"séquence": ("sequence_items", "sequence_id"),
	"événement": ("event_items", "event_id"),
}
"""La liste d'éléments de chaque genre : sa table et sa colonne du parent."""


def opened_card(interface: Context) -> Card:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, Card), opened
	return opened


def item_list(interface: Context) -> QTreeWidget:
	list_ = opened_card(interface).findChild(QTreeWidget, "items")
	assert list_ is not None
	return list_


def lines(list_: QTreeWidget) -> list[str]:
	"""Le nom de l'élément de chaque ligne, deuxième colonne."""
	return [item.text(1) for row in range(list_.topLevelItemCount()) if (item := list_.topLevelItem(row))]


def instant(text: str) -> datetime:
	return datetime.fromisoformat(text).astimezone()


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'événement « {name} » masque les métadonnées"))
def hides(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE events SET hide_metadata = true WHERE internal_name = %s", (name,))


@given(parsers.parse("la séquence au nom interne de {length:d} caractères « {letter} »"))
def sequence_to_long_name(empty_database: Connection, length: int, letter: str) -> None:
	empty_database.execute("INSERT INTO sequences (internal_name) VALUES (%s)", (letter * length,))


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je retire les éléments (?P<names>.+)"))
def remove(interface: Context, qtbot: QtBot, names: str) -> None:
	list_ = item_list(interface)
	remove_item = opened_card(interface).ui.remove_item  # type: ignore[attr-defined]
	for name in NAME.findall(names):
		(row,) = [row for row, text in enumerate(lines(list_)) if text == name]
		list_.setCurrentItem(list_.topLevelItem(row))
		qtbot.mouseClick(remove_item, Qt.MouseButton.LeftButton)


@when(parsers.parse("je donne à l'événement copié le début « {text} »"))
def give_start(interface: Context, text: str) -> None:
	opened = opened_card(interface)
	assert isinstance(opened, EventCard)
	opened.ui.has_start.setChecked(True)
	opened.ui.start.setDateTime(QDateTime.fromSecsSinceEpoch(int(instant(text).timestamp())))


@when(parsers.parse("je choisis « Dupliquer » au clic droit sur la ligne de {length:d} caractères « {letter} »"))
def duplicate_long_name(interface: Context, length: int, letter: str) -> None:
	duplicate_to_right_click(interface, letter * length)


@when(parsers.parse("je choisis « Dupliquer » au clic droit sur la ligne « {name} »"))
def duplicate_to_right_click(interface: Context, name: str) -> None:
	list_ = window(interface).ui.tabs.currentWidget()
	assert isinstance(list_, List)
	found_list = list_.proxy.match(list_.proxy.index(0, 0), IDENTIFIER + 1, name, -1, Qt.MatchFlag.MatchExactly)
	assert len(found_list) == 1, name
	menu = list_.line_menu(found_list[0])
	assert menu is not None
	(action,) = [action for action in menu.actions() if action.text() == "Dupliquer"]
	action.trigger()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"le bouton « Dupliquer » de la fiche est (?P<state>actif|inactif)"))
def button_duplicate(interface: Context, state: str) -> None:
	button = opened_card(interface).button_duplicate
	assert button is not None
	assert button.isEnabled() == (state == "actif")


@then(parsers.parse("la fiche montre le nom interne « {name} » et le nom public « {public_name} »"))
def shown_names(interface: Context, name: str, public_name: str) -> None:
	ui = opened_card(interface).ui  # type: ignore[attr-defined]
	assert (ui.internal_name.text(), ui.public_name.text()) == (name, public_name)


@then(parsers.re(r"la fiche montre les éléments (?P<names>«.+)"))
def shown_items(interface: Context, names: str) -> None:
	assert lines(item_list(interface)) == NAME.findall(names)


@then(
	parsers.parse(
		"la fiche de l'événement copié montre la priorité « {priority} », le masquage « {hiding} », ni début,"
		" ni fin, ni jours"
	)
)
def copied_event(interface: Context, priority: str, hiding: str) -> None:
	opened = opened_card(interface)
	assert isinstance(opened, EventCard)
	ui = opened.ui
	assert (ui.priority.currentText(), ui.hiding.currentText()) == (priority, hiding)
	assert not ui.has_start.isChecked()
	assert not ui.has_end.isChecked()
	assert not any(day.isChecked() for day in opened.days)


@then(
	parsers.re(
		r"la fiche de la banque copiée montre le mode « (?P<mode>[^»]+) », « ne pas répéter » coché,"
		r" les répertoires (?P<directories>.+), et aucun sonore"
	)
)
def copied_bank(interface: Context, mode: str, directories: str) -> None:
	opened = opened_card(interface)
	assert isinstance(opened, BankCard)
	ui = opened.ui
	assert (ui.mode.currentText(), ui.no_repeat.isChecked()) == (mode, True)
	shown_list = [ui.directories.item(row).text() for row in range(ui.directories.count())]
	assert shown_list == [interface.path(directory) for directory in NAME.findall(directories)]
	assert ui.sounds.topLevelItemCount() == 0


@then(parsers.re(r"(?:la |l')(?P<category>séquence|événement|banque) « (?P<name>[^»]+) » n'est pas en base"))
def absent(empty_database: Connection, category: str, name: str) -> None:
	table = TABLES[category]
	assert empty_database.execute(f"SELECT 1 FROM {table} WHERE internal_name = %s", (name,)).fetchone() is None  # noqa: S608


def items_in_database(database: Connection, category: str, name: str) -> list[tuple[str, str]]:
	"""Chaque élément de la liste, dans l'ordre : « le sonore » et son titre, « la banque » ou « la séquence » et son
	nom. Dans une séquence, sequence_id désigne la séquence elle-même : ses éléments n'en sont jamais une."""
	table, parent = ITEMS[category]
	number = identifier(database, TABLES[category], "internal_name", name)
	cited_sequence = "e.sequence_id"
	if category == "séquence":
		cited_sequence = "NULL"
	rows = database.execute(
		"SELECT CASE WHEN e.sound_id IS NOT NULL THEN 'le sonore' WHEN e.bank_id IS NOT NULL THEN 'la banque'"
		" ELSE 'la séquence' END, COALESCE(s.title, b.internal_name, q.internal_name)"
		f" FROM {table} e LEFT JOIN sounds s ON s.id = e.sound_id"  # noqa: S608
		" LEFT JOIN banks b ON b.id = e.bank_id"
		f" LEFT JOIN sequences q ON q.id = {cited_sequence}"
		f" WHERE e.{parent} = %s ORDER BY e.position",
		(number,),
	).fetchall()
	return [(str(what), str(who)) for what, who in rows]


@then(
	parsers.re(
		r"la séquence « (?P<name>[^»]+) » a en base le nom public « (?P<public_name>[^»]+) » et les éléments"
		r" (?P<items>.+)"
	)
)
def sequence_in_database(empty_database: Connection, name: str, public_name: str, items: str) -> None:
	line = empty_database.execute("SELECT public_name FROM sequences WHERE internal_name = %s", (name,)).fetchone()
	assert line == (public_name,)
	assert items_in_database(empty_database, "séquence", name) == ITEM.findall(items)


@then(parsers.re(r"l'événement « (?P<name>[^»]+) » a en base les éléments (?P<items>.+)"))
def event_items(empty_database: Connection, name: str, items: str) -> None:
	assert items_in_database(empty_database, "événement", name) == ITEM.findall(items)


@then(
	parsers.re(
		r"l'événement « (?P<name>[^»]+) » a en base la priorité « (?P<priority>[^»]+) »,"
		r" le nom public « (?P<public_name>[^»]+) », masqué, le début « (?P<start>[^»]+) »,"
		r" (?:sans fin ni jours|la fin « (?P<end>[^»]+) », les jours « (?P<days>[^»]+) »)"
	)
)
def event_in_database(
	empty_database: Connection,
	name: str,
	priority: str,
	public_name: str,
	start: str,
	end: str | None,
	days: str | None,
) -> None:
	line = empty_database.execute(
		"SELECT priority::text, public_name, hide_metadata, starts_at, ends_at, recurrence_days::text[]"
		" FROM events WHERE internal_name = %s",
		(name,),
	).fetchone()
	expected_end = None
	if end is not None:
		expected_end = instant(end)
	expected_days: list[str] = []
	if days is not None:
		expected_days = days.split(", ")
	assert line == (priority, public_name, True, instant(start), expected_end, expected_days)


@then(
	parsers.re(
		r"la banque « (?P<name>[^»]+) » a en base le nom public « (?P<public_name>[^»]+) »,"
		r" le mode « (?P<mode>[^»]+) », « ne pas répéter », les répertoires (?P<directories>.+)"
		r" et les sonores (?P<sounds>aucun|«.+)"
	)
)
def bank_in_database(
	interface: Context,
	empty_database: Connection,
	name: str,
	public_name: str,
	mode: str,
	directories: str,
	sounds: str,
) -> None:
	line = empty_database.execute(
		"SELECT id, public_name, mode::text, no_repeat FROM banks WHERE internal_name = %s", (name,)
	).fetchone()
	assert line is not None
	number, *settings = line
	assert settings == [public_name, mode, True]
	fetched_list = empty_database.execute(
		'SELECT directory FROM bank_directories WHERE bank_id = %s ORDER BY directory COLLATE "C"', (number,)
	).fetchall()
	assert [str(directory) for (directory,) in fetched_list] == [interface.path(r) for r in NAME.findall(directories)]
	titles = empty_database.execute(
		"SELECT s.title FROM bank_sounds bs JOIN sounds s ON s.id = bs.sound_id"
		" WHERE bs.bank_id = %s ORDER BY bs.position",
		(number,),
	).fetchall()
	assert [str(title) for (title,) in titles] == NAME.findall(sounds)


@then(parsers.re(r"les listes qui proposent de dupliquer au clic droit sont (?P<tabs>.+)"))
def lists_who_duplicate(interface: Context, tabs: str) -> None:
	"""Le menu de la première ligne de chaque liste ; toutes en ont une."""
	ui = window(interface).ui
	found_list = []
	for row in range(ui.tabs.count()):
		list_ = ui.tabs.widget(row)
		if not isinstance(list_, List):
			continue
		list_.refresh()
		assert list_.proxy.rowCount() > 0, tab_title(ui.tabs, row)
		menu = list_.line_menu(list_.proxy.index(0, 0))
		if (menu is not None) and (any(action.text() == "Dupliquer" for action in menu.actions())):
			found_list.append(tab_title(ui.tabs, row))
	assert found_list == NAME.findall(tabs)


@then("la fiche ne montre aucun événement où figure la séquence")
def without_event(interface: Context) -> None:
	assert opened_card(interface).ui.events.count() == 0  # type: ignore[attr-defined]


@then(parsers.parse("le nom interne de la copie est de {length:d} caractères « {letter} », suivis de « {suffix} »"))
def shortcut_name(interface: Context, length: int, letter: str, suffix: str) -> None:
	name = opened_card(interface).ui.internal_name.text()  # type: ignore[attr-defined]
	assert name == f"{letter * length} {suffix}"
	assert len(name) == 255
