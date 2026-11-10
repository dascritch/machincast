"""Scénarios de la fiche d'une banque (https://github.com/dascritch/machincast/issues/31).

Les étapes de la fenêtre, des listes et des fenêtres de dialogue sont dans tests/interface_steps.py ; celles-ci
manipulent la fiche, le choix des sonores, et lisent la base de test.
"""

import time
from collections.abc import Iterator
from datetime import timedelta

import pytest
from PySide6.QtCore import QItemSelectionModel, Qt, QTime
from PySide6.QtWidgets import (
	QAbstractItemView,
	QCheckBox,
	QComboBox,
	QDialog,
	QDoubleSpinBox,
	QTimeEdit,
	QTreeWidgetItem,
	QWidget,
)
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.database import Role, open_connection
from machincast.interface.bank_card import SOUND, BankCard
from machincast.interface.choice import Choice
from machincast.interface.lists import IDENTIFIER, SOUNDS
from tests.database_fixtures import sample_database_parameters
from tests.interface_steps import (
	NAME,
	Connection,
	Context,
	identifier,
	open_in,
	slide,
	type_,
	window,
)

scenarios("bank_card.feature")

HIDINGS = {"hérité du sonore": None, "masqués": True, "affichés": False}
MODES = {"séquentielle": "sequential", "aléatoire": "random"}


@pytest.fixture
def choice() -> Iterator[list[Choice]]:
	"""Le choix des sonores ouvert par le scénario, hors de la fenêtre."""
	opened_list: list[Choice] = []
	yield opened_list
	for opened in opened_list:
		opened.list_.connection.close()


def card(interface: Context) -> BankCard:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, BankCard), opened
	return opened


def sound(interface: Context, database: Connection, title: str) -> QTreeWidgetItem:
	"""La ligne du sonore dans la liste de la fiche, sélectionnée."""
	number = identifier(database, "sounds", "title", title)
	list_ = card(interface).ui.sounds
	for row in range(list_.topLevelItemCount()):
		line = list_.topLevelItem(row)
		if line.data(0, SOUND) == number:
			list_.setCurrentItem(line)
			return line
	raise AssertionError(f"« {title} » absent de la fiche")


def click(qtbot: QtBot, button: QWidget) -> None:
	qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.re(r"les sonores sans titre (?P<locations>.+) sont dans la banque « (?P<name>[^»]+) »"))
def without_title(empty_database: Connection, locations: str, name: str) -> None:
	"""Rangés en fin de liste, par leur emplacement : chemin du fichier ou adresse du stream."""
	bank = identifier(empty_database, "banks", "internal_name", name)
	for location in NAME.findall(locations):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position)"
			" SELECT %s, s.id, (SELECT COALESCE(MAX(position), 0) + 1 FROM bank_sounds WHERE bank_id = %s)"
			" FROM sounds s WHERE %s IN (s.location, s.stream_url)",
			(bank, bank, location),
		)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je (?P<action>coche|décoche) « ne pas répéter »"))
def tick(interface: Context, action: str) -> None:
	card(interface).ui.no_repeat.setChecked(action == "coche")


@when(parsers.parse("j'ajoute le répertoire « {directory} »"))
def add_directory(interface: Context, qtbot: QtBot, directory: str) -> None:
	interface.chosen_directories.append(directory)
	click(qtbot, card(interface).ui.add_directory)


@when("je renonce à choisir un répertoire")
def give_up(interface: Context, qtbot: QtBot) -> None:
	interface.chosen_directories.append(None)
	click(qtbot, card(interface).ui.add_directory)


@when(parsers.parse("je retire le répertoire « {directory} »"))
def remove_directory(interface: Context, qtbot: QtBot, directory: str) -> None:
	ui = card(interface).ui
	found_list = ui.directories.findItems(directory, Qt.MatchFlag.MatchExactly)
	assert len(found_list) == 1, found_list
	ui.directories.setCurrentItem(found_list[0])
	click(qtbot, ui.remove_directory)


@when(parsers.re(r"j'ajoute les sonores (?P<titles>.+), en effaçant « (?P<erased>[^»]+) » de la base pendant le choix"))
def add_erased_sounds(interface: Context, qtbot: QtBot, empty_database: Connection, titles: str, erased: str) -> None:
	title_list = []
	for title in NAME.findall(titles):
		title_list.append(identifier(empty_database, "sounds", "title", title))
	interface.chosen_sounds = title_list
	empty_database.execute("DELETE FROM sounds WHERE title = %s", (erased,))
	click(qtbot, card(interface).ui.add_sounds)


@when(parsers.parse("je choisis le sonore « {title} »"))
def choose_sound(interface: Context, empty_database: Connection, title: str) -> None:
	sound(interface, empty_database, title)


@when(parsers.parse("je choisis le répertoire « {directory} »"))
def choose_directory(interface: Context, directory: str) -> None:
	list_ = card(interface).ui.directories
	found_list = list_.findItems(directory, Qt.MatchFlag.MatchExactly)
	assert len(found_list) == 1, found_list
	list_.setCurrentItem(found_list[0])


@when(parsers.re(r"je (?P<direction>monte|descends) le sonore « (?P<title>[^»]+) »"))
def move(interface: Context, qtbot: QtBot, empty_database: Connection, direction: str, title: str) -> None:
	sound(interface, empty_database, title)
	ui = card(interface).ui
	click(qtbot, {"monte": ui.raise_, "descends": ui.go_down}[direction])


@when(parsers.parse("je retire le sonore « {title} »"))
def remove_sound(interface: Context, qtbot: QtBot, empty_database: Connection, title: str) -> None:
	sound(interface, empty_database, title)
	click(qtbot, card(interface).ui.remove_sound)


@when(parsers.parse("l'indexation rattache le sonore « {title} » à la banque « {name} »"))
def attach(empty_database: Connection, title: str, name: str) -> None:
	# La requête de machincast.indexer.directories : en fin de liste.
	bank = identifier(empty_database, "banks", "internal_name", name)
	empty_database.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position)"
		" SELECT %s, %s, COALESCE(MAX(position), 0) + 1 FROM bank_sounds WHERE bank_id = %s",
		(bank, identifier(empty_database, "sounds", "title", title), bank),
	)


@when(
	parsers.re(
		r"je (?P<gesture>dépose|glisse sans les déposer) sur les (?P<list_>répertoires|sonores) de la fiche"
		r" (?P<what>.+?)(?P<relocation>, en ne proposant que le déplacement)?"
	)
)
def drop_in(interface: Context, gesture: str, list_: str, what: str, relocation: str | None) -> None:
	ui = card(interface).ui
	target = {"répertoires": ui.directories, "sonores": ui.sounds}[list_]
	slide(interface, target, what, gesture == "dépose", relocation is not None)


@when(parsers.parse("j'ouvre le sonore « {name} » de la banque"))
def open_sound(interface: Context, qtbot: QtBot, name: str) -> None:
	open_in(qtbot, card(interface).ui.sounds, name)


@when(parsers.parse("je choisis le sonore « {name} » de la banque, puis j'appuie sur Entrée"))
def open_sound_to_keyboard(interface: Context, qtbot: QtBot, name: str) -> None:
	sounds = card(interface).ui.sounds
	(line,) = sounds.findItems(name, Qt.MatchFlag.MatchExactly, 0)
	sounds.setCurrentItem(line)
	sounds.setFocus()
	qtbot.keyClick(sounds, Qt.Key.Key_Return)


@when(parsers.parse("l'indexation enregistre le fichier « {path} »"))
def index_file(interface: Context, empty_database: Connection, path: str) -> None:
	empty_database.execute(
		"INSERT INTO sounds (type, location, state, indexed_at) VALUES ('file', %s, 'preview', clock_timestamp())",
		(interface.path(path),),
	)


@when("j'ouvre le choix des sonores")
def open_choice(choice: list[Choice], empty_database: Connection, qtbot: QtBot) -> None:
	opened = Choice(SOUNDS, open_connection(*sample_database_parameters(), Role.INTERFACE))
	choice.append(opened)
	qtbot.addWidget(opened)
	opened.show()
	qtbot.waitExposed(opened)


@when(parsers.parse("je tape « {text} » dans le filtre du choix des sonores"))
def apply_filter_choice(choice: list[Choice], qtbot: QtBot, text: str) -> None:
	type_(qtbot, choice[0].list_.filter_, text)


@when("je sélectionne toutes les lignes du choix des sonores")
def all_select(choice: list[Choice]) -> None:
	choice[0].list_.table.selectAll()


@when(parsers.re(r"je sélectionne les lignes (?P<titles>.+) du choix des sonores"))
def select(choice: list[Choice], titles: str) -> None:
	table = choice[0].list_.table
	model = table.model()
	for title in NAME.findall(titles):
		rows = []
		for row in range(model.rowCount()):
			if model.index(row, 0).data(IDENTIFIER + 1) == title:
				rows.append(row)
		assert len(rows) == 1, title
		table.selectionModel().select(
			model.index(rows[0], 0),
			QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
		)


@when(parsers.parse("j'ouvre la ligne « {name} » du choix des sonores"))
def open_choice_line(choice: list[Choice], qtbot: QtBot, name: str) -> None:
	open_in(qtbot, choice[0].list_.table, name)


# ─── Alors ─────────────────────────────────────────────────


@then(
	parsers.re(
		r"la fiche montre le nom interne « (?P<name>[^»]*) », le nom public « (?P<public_name>[^»]*) »,"
		r" le mode « (?P<mode>[^»]+) », le masquage « (?P<hiding>[^»]+) »"
		r" et « ne pas répéter » (?P<box>coché|décoché)"
	)
)
def fields(interface: Context, name: str, public_name: str, mode: str, hiding: str, box: str) -> None:
	ui = card(interface).ui
	shown_list = (ui.internal_name.text(), ui.public_name.text(), ui.mode.currentText().casefold())
	shown_list += (ui.hiding.currentText().casefold(), ui.no_repeat.isChecked())
	assert shown_list == (name.strip(), public_name.strip(), mode, hiding, box == "coché")


@then(parsers.re(r"la fiche montre les répertoires (?P<directories>.+)"))
def shown_directories(interface: Context, directories: str) -> None:
	list_ = card(interface).ui.directories
	expected_list = []
	for directory in NAME.findall(directories):
		expected_list.append(interface.path(directory))
	row_list = []
	for row in range(list_.count()):
		row_list.append(list_.item(row).text())
	assert row_list == expected_list


@then("la fiche montre les sonores :")
def sounds_in_table(interface: Context, datatable: list[list[str]]) -> None:
	list_ = card(interface).ui.sounds
	headers, *rows = datatable
	titles = []
	for column in range(list_.columnCount()):
		titles.append(list_.headerItem().text(column))
	header_list = []
	for header in headers:
		header_list.append(header.strip())
	assert titles == header_list
	shown_list = []
	for row in range(list_.topLevelItemCount()):
		line = list_.topLevelItem(row)
		assert line is not None
		column_list = []
		for column in range(list_.columnCount()):
			column_list.append(line.text(column))
		shown_list.append(column_list)
	values_list = []
	for values in rows:
		value_list = []
		for value in values:
			value_list.append(interface.path(value.strip()))
		values_list.append(value_list)
	assert shown_list == values_list


@then(parsers.re(r"les boutons de ligne actifs de la fiche sont (?P<buttons>.+)"))
def line_buttons(interface: Context, buttons: str) -> None:
	ui = card(interface).ui
	active_list = []
	for button in (ui.remove_directory, ui.remove_sound, ui.raise_, ui.go_down):
		if button.isEnabled():
			active_list.append(button.text())
	assert active_list == NAME.findall(buttons)


@then(parsers.re(r"la fiche montre les sonores (?P<sounds>«.+)"))
def shown_sounds(interface: Context, sounds: str) -> None:
	list_ = card(interface).ui.sounds
	shown_list = []
	for row in range(list_.topLevelItemCount()):
		shown_list.append(list_.topLevelItem(row).text(0))
	assert shown_list == NAME.findall(sounds)


@then("aucune ligne de sonore de la fiche n'accepte qu'on y dépose une autre")
def no_drop(interface: Context) -> None:
	list_ = card(interface).ui.sounds
	lines = []
	for row in range(list_.topLevelItemCount()):
		lines.append(list_.topLevelItem(row))
	assert lines != []
	every_one = True
	for line in lines:
		if line.flags() & Qt.ItemFlag.ItemIsDropEnabled:
			every_one = False
			break
	assert every_one
	every_one_2 = True
	for line in lines:
		if not (line.flags() & Qt.ItemFlag.ItemIsDragEnabled):
			every_one_2 = False
			break
	assert every_one_2


@then(parsers.re(r"les sonores de la fiche (?P<verdict>peuvent|ne peuvent pas) se réordonner"))
def reorderable(interface: Context, verdict: str) -> None:
	ui = card(interface).ui
	can = verdict == "peuvent"
	internal = ui.sounds.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
	assert (internal, ui.sounds.dragEnabled(), ui.raise_.isEnabled(), ui.go_down.isEnabled()) == (can,) * 4


@then(
	parsers.re(
		r"la banque « (?P<name>[^»]+) » est en base : (?:nom public « (?P<public_name>[^»]+) »|sans nom public),"
		r" (?P<mode>séquentielle|aléatoire), masquage « (?P<hiding>[^»]+) »,"
		r" (?P<repeat>avec|sans) « ne pas répéter »"
	)
)
def bank_in_database(
	empty_database: Connection, name: str, public_name: str | None, mode: str, hiding: str, repeat: str
) -> None:
	lines = empty_database.execute(
		"SELECT public_name, mode::text, hide_metadata, no_repeat FROM banks WHERE internal_name = %s",
		(name,),
	).fetchall()
	assert lines == [(public_name, MODES[mode], HIDINGS[hiding], repeat == "avec")]


@then(parsers.re(r"les répertoires de la banque « (?P<name>[^»]+) » sont (?P<directories>.+) en base"))
def directories_in_database(interface: Context, empty_database: Connection, name: str, directories: str) -> None:
	lines = empty_database.execute(
		"SELECT r.directory FROM bank_directories r JOIN banks b ON b.id = r.bank_id"
		" WHERE b.internal_name = %s ORDER BY r.directory",
		(name,),
	).fetchall()
	line_list = []
	for line in lines:
		line_list.append(str(line[0]))
	directory_list = []
	for directory in NAME.findall(directories):
		directory_list.append(interface.path(directory))
	assert line_list == directory_list


@then(parsers.re(r"les sonores de la banque « (?P<name>[^»]+) » sont, dans l'ordre, (?P<titles>.+)"))
def sounds_in_database(interface: Context, empty_database: Connection, name: str, titles: str) -> None:
	"""Chaque sonore par son titre, ou « le fichier « …/chemin » » pour un sonore sans titre."""
	lines = empty_database.execute(
		"SELECT bs.position, COALESCE(s.title, s.location) FROM bank_sounds bs"
		" JOIN banks b ON b.id = bs.bank_id JOIN sounds s ON s.id = bs.sound_id"
		" WHERE b.internal_name = %s ORDER BY bs.position",
		(name,),
	).fetchall()
	expected_list = []
	for title in NAME.findall(titles):
		expected_list.append(interface.path(title))
	assert lines == list(enumerate(expected_list, start=1))


@then(parsers.parse("le sonore « {title} » est toujours en base"))
def always_in_database(empty_database: Connection, title: str) -> None:
	identifier(empty_database, "sounds", "title", title)


@then(parsers.re(r"le choix des sonores donne (?P<titles>.+)"))
def chosen_list(choice: list[Choice], empty_database: Connection, titles: str) -> None:
	expected_list = []
	for title in NAME.findall(titles):
		expected_list.append(identifier(empty_database, "sounds", "title", title))
	assert choice[0].selection() == expected_list


@then("les répertoires et les sonores de la fiche acceptent les dépôts")
def accept(interface: Context) -> None:
	ui = card(interface).ui
	lists = (ui.directories, ui.directories.viewport(), ui.sounds, ui.sounds.viewport())
	list__list = []
	for list_ in lists:
		list__list.append(list_.acceptDrops())
	assert list__list == [True] * 4


@then(parsers.parse("le fichier « {path} » n'est pas en base"))
def absent_file(interface: Context, empty_database: Connection, path: str) -> None:
	lines = empty_database.execute("SELECT id FROM sounds WHERE location = %s", (interface.path(path),)).fetchall()
	assert lines == []


@then("le choix des sonores est validé")
def valid(choice: list[Choice]) -> None:
	assert choice[0].result() == QDialog.DialogCode.Accepted


# ─── Crossfades (https://github.com/dascritch/machincast/issues/143) ─────


def _crossfade(interface: Context, side: str) -> tuple[QComboBox, QDoubleSpinBox]:
	ui = card(interface).ui
	prefix = {"début": "start", "fin": "end"}[side]
	return getattr(ui, f"{prefix}_crossfade_rule"), getattr(ui, f"{prefix}_crossfade")


@when(parsers.re(r"je choisis pour le crossfade de (?P<side>début|fin) la règle « (?P<rule>[^»]+) »"))
def choose_rule(interface: Context, side: str, rule: str) -> None:
	list_, _duration = _crossfade(interface, side)
	rank = list_.findText(rule)
	assert rank >= 0, rule
	list_.setCurrentIndex(rank)


@when(parsers.re(r"je saisis (?P<duration>[\d,]+) seconde de crossfade de (?P<side>début|fin) dans la fiche"))
def enter_crossfade(interface: Context, duration: str, side: str) -> None:
	_list, field = _crossfade(interface, side)
	assert field.isEnabled(), side
	field.setValue(float(duration.replace(",", ".")))


@then("la fiche montre les crossfades :")
def shown_crossfades(interface: Context, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	shown_list = []
	for side, *_values in rows:
		list_, field = _crossfade(interface, side.strip())
		editable = "non"
		if field.isEnabled():
			editable = "oui"
		shown_list.append([side.strip(), list_.currentText(), field.text(), editable])
	row_list = []
	for row in rows:
		value_list = []
		for value in row:
			value_list.append(value.strip())
		row_list.append(value_list)
	assert shown_list == row_list


@then(parsers.re(r"le crossfade de début se règle parmi (?P<rules>.+)"))
def offered_rules(interface: Context, rules: str) -> None:
	list_, _field = _crossfade(interface, "début")
	rank_list = []
	for rank in range(list_.count()):
		rank_list.append(list_.itemText(rank))
	assert rank_list == NAME.findall(rules)


@then(
	parsers.re(
		r"la banque « (?P<name>[^»]+) » a en base les crossfades « (?P<start_rule>[^»]+) » (?P<start>[\d,]+) secondes?"
		r" au début, et « (?P<end_rule>[^»]+) » (?P<end>[\d,]+) secondes? à la fin"
	)
)
def crossfades_in_database(
	empty_database: Connection, name: str, start_rule: str, start: str, end_rule: str, end: str
) -> None:
	lines = empty_database.execute(
		"SELECT crossfade_start_rule::text, crossfade_start, crossfade_end_rule::text, crossfade_end"
		" FROM banks WHERE internal_name = %s",
		(name,),
	).fetchall()
	seconds = []
	for value in (start, end):
		seconds.append(timedelta(seconds=float(value.replace(",", "."))))
	assert lines == [(start_rule, seconds[0], end_rule, seconds[1])]


# ─── Durées des sonores (https://github.com/dascritch/machincast/issues/147) ─────


def _duration(interface: Context, bound: str) -> tuple[QCheckBox, QTimeEdit]:
	ui = card(interface).ui
	prefix = {"minimale": "min", "maximale": "max"}[bound]
	return getattr(ui, f"has_{prefix}_duration"), getattr(ui, f"{prefix}_duration")


@when(parsers.re(r"je fixe la durée (?P<bound>minimale|maximale) des sonores à « (?P<text>[\d:]+) »"))
def set_duration(interface: Context, qtbot: QtBot, bound: str, text: str) -> None:
	box, field = _duration(interface, bound)
	if not box.isChecked():
		qtbot.mouseClick(box, Qt.MouseButton.LeftButton)
	assert field.isEnabled(), bound
	field.setTime(QTime.fromString(text, "H:mm:ss"))


@when(parsers.re(r"je retire la durée (?P<bound>minimale|maximale) des sonores"))
def remove_duration(interface: Context, qtbot: QtBot, bound: str) -> None:
	box, _field = _duration(interface, bound)
	assert box.isChecked(), bound
	qtbot.mouseClick(box, Qt.MouseButton.LeftButton)


@then(
	parsers.re(
		r"la fiche montre les durées des sonores : minimale (?:aucune|« (?P<minimal>[^»]+) »),"
		r" maximale (?:aucune|« (?P<maximal>[^»]+) »)"
	)
)
def shown_durations(interface: Context, minimal: str | None, maximal: str | None) -> None:
	for bound, expected in (("minimale", minimal), ("maximale", maximal)):
		box, field = _duration(interface, bound)
		assert box.isChecked() is (expected is not None), bound
		assert field.isEnabled() is (expected is not None), bound
		if expected is not None:
			assert field.text() == expected, field.text()


@then(
	parsers.re(
		r"la banque « (?P<name>[^»]+) » a en base les durées des sonores d(?:e (?P<minimum>\d+)|'aucune)"
		r" à (?:(?P<maximum>\d+)|aucune) secondes"
	)
)
def durations_in_database(empty_database: Connection, name: str, minimum: str | None, maximum: str | None) -> None:
	lines = empty_database.execute(
		"SELECT min_duration, max_duration FROM banks WHERE internal_name = %s", (name,)
	).fetchall()
	expected_list: list[timedelta | None] = []
	for value in (minimum, maximum):
		expected = None
		if value is not None:
			expected = timedelta(seconds=int(value))
		expected_list.append(expected)
	assert lines == [tuple(expected_list)], lines


def _marks(interface: Context) -> list[list[str]]:
	marks = []
	row_list = []
	for row in range(card(interface).ui.sounds.topLevelItemCount()):
		row_list.append(card(interface).ui.sounds.topLevelItem(row))
	for line in row_list:
		if (line is not None) and (not line.icon(0).isNull()):
			marks.append([line.text(0), line.toolTip(0)])
	return marks


@then("la fiche ne marque aucun sonore hors des durées")
def no_marked(interface: Context) -> None:
	assert _marks(interface) == []
	lines = card(interface).ui.sounds
	every_one = True
	for row in range(lines.topLevelItemCount()):
		if lines.topLevelItem(row).toolTip(0) != "":
			every_one = False
			break
	assert every_one


@then("la fiche marque hors des durées les sonores :")
def marks(interface: Context, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	assert _marks(interface) == [[sound.strip(), tooltip.strip()] for sound, tooltip in rows]


# ─── Détection de silence (https://github.com/dascritch/machincast/issues/146) ───


@when(parsers.re(r"je (?P<action>coche|décoche) « détection de silence »"))
def tick_detection(interface: Context, action: str) -> None:
	card(interface).ui.detection_silences.setChecked(action == "coche")


@then("la case « détection de silence » de la fiche est décochée")
def unticked_detection(interface: Context) -> None:
	assert not card(interface).ui.detection_silences.isChecked()


@then(parsers.re(r"la banque « (?P<name>[^»]+) » (?P<verdict>active|n'active pas) la détection de silence"))
def detection_in_database(empty_database: Connection, name: str, verdict: str) -> None:
	line = empty_database.execute("SELECT silence_detection FROM banks WHERE internal_name = %s", (name,)).fetchone()
	assert line == (verdict == "active",), line


# ─── Grande banque (https://github.com/dascritch/machincast/issues/194) ───


@given(parsers.parse("{count:d} sonores de 3:00 de plus dans la banque « {name} »"))
def large_bank(empty_database: Connection, count: int, name: str) -> None:
	empty_database.execute(
		"WITH nouveaux AS (INSERT INTO sounds (type, location, state, duration)"
		" SELECT 'file', '/srv/grande/' || n || '.flac', 'active', '3 min' FROM generate_series(1, %s) n"
		" RETURNING id)"
		" INSERT INTO bank_sounds (bank_id, sound_id, position)"
		" SELECT b.id, nouveaux.id, 1000 + nouveaux.id FROM nouveaux, banks b WHERE b.internal_name = %s",
		(count, name),
	)


@when(parsers.re(r"je coche la durée (?P<bound>minimale|maximale) des sonores$"))
def tick_duration(interface: Context, qtbot: QtBot, bound: str) -> None:
	box, _field = _duration(interface, bound)
	start = time.monotonic()
	qtbot.mouseClick(box, Qt.MouseButton.LeftButton)
	interface.response_duration = time.monotonic() - start


@when("je compte les lectures de toutes les lignes de la fiche")
def count_readings(interface: Context, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Chaque appel de BankCard._lines lit toutes les lignes de la liste
	(https://github.com/dascritch/machincast/issues/383)."""
	interface.readings = 0
	original = BankCard._lines

	def counted(self: BankCard) -> list[QTreeWidgetItem]:
		interface.readings += 1
		return original(self)

	monkeypatch.setattr(BankCard, "_lines", counted)


@when(parsers.parse("je choisis les {count:d} derniers sonores de la fiche"))
def choose_last(interface: Context, count: int) -> None:
	lines = card(interface).ui.sounds
	total = lines.topLevelItemCount()
	for row in range(total - count, total):
		lines.topLevelItem(row).setSelected(True)


@when("je retire les sonores choisis")
def remove_chosen(interface: Context, qtbot: QtBot) -> None:
	click(qtbot, card(interface).ui.remove_sound)


@then(parsers.parse("la fiche a lu toutes ses lignes au plus {count:d} fois"))
def readings_at_most(interface: Context, count: int) -> None:
	assert interface.readings <= count, interface.readings


@given(parsers.parse("le dernier sonore de la banque « {name} » est à l'état « erroné »"))
def last_corrupt(empty_database: Connection, name: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET state = 'corrupt' WHERE id = (SELECT bs.sound_id FROM bank_sounds bs"
		" JOIN banks b ON b.id = bs.bank_id WHERE b.internal_name = %s ORDER BY bs.position DESC LIMIT 1)",
		(name,),
	)


@when("je descends au bas de la liste des sonores de la fiche")
def scroll_to_bottom(interface: Context, qtbot: QtBot) -> None:
	bar = card(interface).ui.sounds.verticalScrollBar()
	bar.setValue(bar.maximum())
	qtbot.wait(10)


@when("je compte les réécritures des sonores de la banque")
def count_rewrites(interface: Context, monkeypatch: pytest.MonkeyPatch) -> None:
	interface.readings = 0
	original = BankCard._write_sounds

	def counted(self: BankCard, bank: int) -> None:
		interface.readings += 1
		original(self, bank)

	monkeypatch.setattr(BankCard, "_write_sounds", counted)


@then(parsers.parse("la fiche a réécrit les sonores de la banque {count:d} fois"))
def rewrites(interface: Context, count: int) -> None:
	assert interface.readings == count, interface.readings


@then(parsers.parse("la liste des sonores de la fiche a pour titre « {title} »"))
def sounds_title(interface: Context, title: str) -> None:
	assert card(interface).ui.sound_group.title() == title


@then(
	parsers.re(
		r"en base, la banque « (?P<name>[^»]+) » a (?P<count>\d+) sonores dans l'ordre de la fiche, « (?P<title>[^»]+) » (?P<where>d'abord|en dernier)"
	)
)
def bank_sounds_in_database(empty_database: Connection, name: str, count: str, title: str, where: str) -> None:
	"""Les sonores en base, dans l'ordre de leurs positions : les grands, ajoutés par 1000 + leur identifiant,
	gardent leur ordre."""
	titles = [
		str(found)
		for (found,) in empty_database.execute(
			"SELECT COALESCE(s.title, s.location) FROM bank_sounds bs JOIN banks b ON b.id = bs.bank_id"
			" JOIN sounds s ON s.id = bs.sound_id WHERE b.internal_name = %s ORDER BY bs.position",
			(name,),
		)
	]
	assert len(titles) == int(count), len(titles)
	chosen = -1
	if where == "d'abord":
		chosen = 0
	assert titles[chosen] == title, titles[:3] + titles[-3:]
	big = [found for found in titles if found.startswith("/srv/grande/")]
	assert big == sorted(big, key=lambda found: int(found.removeprefix("/srv/grande/").removesuffix(".flac")))


@then(parsers.parse("la fiche montre {count:d} sonores"))
def shows_sounds(interface: Context, count: int) -> None:
	assert card(interface).ui.sounds.topLevelItemCount() == count


@then(parsers.parse("la fiche a marqué hors des durées {count:d} sonores en moins de {seconds:d} secondes"))
def marked_fast(interface: Context, count: int, seconds: int) -> None:
	lines = card(interface).ui.sounds
	marked_list = []
	for row in range(lines.topLevelItemCount()):
		if lines.topLevelItem(row).toolTip(0) != "":
			marked_list.append(row)
	assert len(marked_list) == count
	assert interface.response_duration < seconds, interface.response_duration
