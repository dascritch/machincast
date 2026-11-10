"""Scénarios du calendrier de la grille (https://github.com/dascritch/machincast/issues/36,
https://github.com/dascritch/machincast/issues/118).

Les étapes de la fenêtre, de ses menus et de ses onglets sont dans tests/interface_steps.py. Le calendrier se montre
dans une fenêtre visible, hors écran, à une taille fixe : ses blocs y ont une place, où les étapes cliquent et
survolent.
"""

import re
import uuid
from datetime import date, datetime, time, timedelta

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QHelpEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QMenu, QPushButton, QToolTip, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.i18n import _
from machincast.interface.calendar import Block, Calendar, Strip, day_label
from machincast.interface.event_card import EventCard
from tests.interface_steps import NAME, Connection, Context, identifier, window

scenarios("calendar.feature")

SIZE = (1400, 900)
"""Taille de la fenêtre pendant les scénarios du calendrier."""
DELETED = "(supprimé)"
"""Un passage dont l'événement a été supprimé : son event_id est vide."""


def calendar(interface: Context) -> Calendar:
	"""Le calendrier ouvert, dans une fenêtre montrée à sa taille, ses blocs placés."""
	main = window(interface)
	if not main.isVisible():
		main.resize(*SIZE)
		main.show()
	QApplication.processEvents()
	opened = main.ui.tabs.currentWidget()
	assert isinstance(opened, Calendar), opened
	return opened


def named_day(view: Calendar, label: str) -> date:
	days = {}
	for day in view.days():
		days[day_label(day)] = day
	assert label in days, list(days)
	return days[label]


def schedule(day: date, moment: datetime) -> str:
	"""« 07:00 », ou « 24:00 » pour la fin du jour."""
	if moment == datetime.combine(day + timedelta(days=1), datetime.min.time()):
		return "24:00"
	return f"{moment:%H:%M}"


def table(datatable: list[list[str]]) -> list[list[str]]:
	table = []
	for row in datatable[1:]:
		value_list = []
		for value in row:
			value_list.append(value.strip())
		table.append(value_list)
	return table


def named_block(view: Calendar, name: str, label: str, whole_day: bool = False) -> Block:
	day = named_day(view, label)
	blocks = view.blocks()
	if whole_day:
		blocks = view.whole_day()
	found_list = []
	for block in blocks:
		if (block.day == day) and (block.event.name == name):
			found_list.append(block)
	assert len(found_list) == 1, found_list
	return found_list[0]


def named_strip(view: Calendar, name: str, start: str, label: str) -> Strip:
	day = named_day(view, label)
	found_list = []
	for b in view.strips():
		if (b.day == day) and (b.name == name) and (schedule(day, b.start) == start):
			found_list.append(b)
	assert len(found_list) == 1, view.strips()
	return found_list[0]


def tooltip(widget: QWidget, point: QPointF) -> str:
	"""Ce que montre le survol du point : l'infobulle que le widget affiche à l'événement ToolTip de Qt."""
	QToolTip.hideText()
	position = point.toPoint()
	hover = QHelpEvent(QEvent.Type.ToolTip, position, widget.mapToGlobal(position))
	QApplication.sendEvent(widget, hover)
	text = QToolTip.text()
	QToolTip.hideText()
	return text


def button(view: Calendar, text: str) -> QPushButton:
	buttons = []
	for b in view.findChildren(QPushButton):
		if b.text() == text:
			buttons.append(b)
	b_list = []
	for b in view.findChildren(QPushButton):
		b_list.append(b.text())
	assert len(buttons) == 1, b_list
	return buttons[0]


def box(view: Calendar, text: str) -> QCheckBox:
	boxes = []
	for c in view.findChildren(QCheckBox):
		if c.text() == text:
			boxes.append(c)
	assert len(boxes) == 1, text
	return boxes[0]


# ─── Étant donné ───────────────────────────────────────────


@given("les passages de l'airplay :")
def plays(empty_database: Connection, datatable: list[list[str]]) -> None:
	"""Une ligne de début, et une de fin quand le passage est terminé ; « (supprimé) » : sans événement."""
	for name, start, end in table(datatable):
		event = None
		if name != DELETED:
			event = identifier(empty_database, "events", "internal_name", name)
		play = uuid.uuid4()
		departure = datetime.fromisoformat(start).astimezone()
		empty_database.execute(
			"INSERT INTO airplay (play_id, line_type, logged_at, event_id) VALUES (%s, 'start', %s, %s)",
			(play, departure, event),
		)
		if end == "":
			continue
		arrival = datetime.fromisoformat(end).astimezone()
		empty_database.execute(
			"INSERT INTO airplay (play_id, line_type, logged_at, event_id, played_duration, without_incident)"
			" VALUES (%s, 'end', %s, %s, %s, true)",
			(play, arrival, event, arrival - departure),
		)


@given(parsers.parse("l'événement « {name} » supprimé le « {moment} »"))
def deleted_event(empty_database: Connection, name: str, moment: str) -> None:
	empty_database.execute(
		"UPDATE events SET deleted_at = %s WHERE internal_name = %s",
		(datetime.fromisoformat(moment).astimezone(), name),
	)


@given(parsers.parse("je choisirai le jour « {day} » jusqu'où sauter"))
def chosen_day(interface: Context, day: str) -> None:
	interface.chosen_days.append(date.fromisoformat(day))


@given("j'annulerai le choix du jour jusqu'où sauter")
def abandoned_day(interface: Context) -> None:
	interface.chosen_days.append(None)


@given(parsers.parse("je répondrai « {response} » à la question de création"))
def creation_response(interface: Context, response: str) -> None:
	interface.creation = response == "Créer"


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je (?P<action>coche|décoche) la case « (?P<text>[^»]+) » du calendrier"))
def tick(interface: Context, qtbot: QtBot, action: str, text: str) -> None:
	ticked = box(calendar(interface), text)
	assert ticked.isChecked() == (action == "décoche")
	qtbot.mouseClick(ticked, Qt.MouseButton.LeftButton, pos=QPoint(2, ticked.height() // 2))
	assert ticked.isChecked() == (action == "coche")


@when(parsers.re(r"je clique (?:(?P<times>\d+) fois )?sur « (?P<text>[^»]+) » du calendrier"))
def click_on(interface: Context, qtbot: QtBot, times: str | None, text: str) -> None:
	for _click in range(int((times) or ("1"))):
		qtbot.mouseClick(button(calendar(interface), text), Qt.MouseButton.LeftButton)


@when(parsers.parse("je double-clique sur le bloc « {name} » du {day}"))
def block_click_double(interface: Context, qtbot: QtBot, name: str, day: str) -> None:
	view = calendar(interface)
	centre = view.grid.rectangle(named_block(view, name, day)).center().toPoint()
	qtbot.mouseDClick(view.grid, Qt.MouseButton.LeftButton, pos=centre)


@when(parsers.parse("je double-clique sur la bande d'airplay « {name} » de {start} du {day}"))
def strip_click_double(interface: Context, qtbot: QtBot, name: str, start: str, day: str) -> None:
	view = calendar(interface)
	centre = view.grid.rectangle(named_strip(view, name, start, day)).center().toPoint()
	qtbot.mouseDClick(view.grid, Qt.MouseButton.LeftButton, pos=centre)


@when(parsers.re(r"je clique dans le calendrier le (?P<day>\w+ \d+(?:er)?) à (?P<hour>\d\d:\d\d)"))
def click_to(interface: Context, qtbot: QtBot, day: str, hour: str) -> None:
	view = calendar(interface)
	moment = datetime.combine(named_day(view, day), time.fromisoformat(hour))
	qtbot.mouseClick(view.grid, Qt.MouseButton.LeftButton, pos=view.grid.point(moment).toPoint())


@when(parsers.parse("l'événement « {name} » est effacé de la base"))
def erase_event(empty_database: Connection, name: str) -> None:
	empty_database.execute("DELETE FROM events WHERE internal_name = %s", (name,))


def block_menu(view: Calendar, name: str, label: str, whole_day: bool) -> QMenu | None:
	"""Le menu du clic droit au milieu du bloc."""
	block = named_block(view, name, label, whole_day)
	if whole_day:
		return view.header.menu_in(view.header.rectangle(block).center())
	return view.grid.menu_in(view.grid.rectangle(block).center())


@when(
	parsers.re(
		r"je choisis « (?P<entry>[^»]+) » au clic droit sur le bloc « (?P<name>[^»]+) »"
		r" (?:du|de la (?P<whole_day>journée) du) (?P<day>\w+ \d+(?:er)?)"
	)
)
def choose_to_right_click(interface: Context, entry: str, name: str, whole_day: str | None, day: str) -> None:
	menu = block_menu(calendar(interface), name, day, whole_day is not None)
	assert menu is not None
	(action,) = [action for action in menu.actions() if action.text() == entry]
	action.trigger()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le calendrier montre « {title} »"))
def title(interface: Context, title: str) -> None:
	assert calendar(interface).title.text() == title


@then(parsers.re(r"le calendrier a les jours (?P<days>«.+)"))
def days(interface: Context, days: str) -> None:
	view = calendar(interface)
	day_list = []
	for day in view.days():
		day_list.append(day_label(day))
	assert day_list == NAME.findall(days)
	assert view.header.labels() == NAME.findall(days)


@then("le calendrier montre les blocs :")
def blocks(interface: Context, datatable: list[list[str]]) -> None:
	view = calendar(interface)
	fetched_list = []
	for b in view.blocks():
		fetched_list.append(
			[day_label(b.day), schedule(b.day, b.start), schedule(b.day, b.end), b.event.name, _(b.state)]
		)
	assert fetched_list == table(datatable)
	for block in view.blocks():
		assert view.grid.rect().contains(view.grid.rectangle(block).toRect()), block


@then("la bande de la journée entière montre :")
def whole_day(interface: Context, datatable: list[list[str]]) -> None:
	view = calendar(interface)
	b_list = []
	for b in view.whole_day():
		b_list.append([day_label(b.day), b.event.name, _(b.state)])
	assert b_list == table(datatable)
	for block in view.whole_day():
		assert view.header.rect().contains(view.header.rectangle(block).toRect()), block


@then("le calendrier montre les bandes d'airplay :")
def strips(interface: Context, datatable: list[list[str]]) -> None:
	view = calendar(interface)
	fetched_list = []
	for b in view.strips():
		fetched_list.append([day_label(b.day), schedule(b.day, b.start), schedule(b.day, b.end), b.name, str(b.plays)])
	assert fetched_list == table(datatable)


@then("le calendrier ne montre aucun bloc")
def no_block(interface: Context) -> None:
	view = calendar(interface)
	assert (view.blocks(), view.whole_day()) == ([], [])


@then(parsers.parse("le calendrier montre {count:d} blocs"))
def block_count(interface: Context, count: int) -> None:
	assert len(calendar(interface).blocks()) == count


@then(parsers.parse("les blocs « {first} » et « {second} » du {day} sont côte à côte"))
def side_to_side(interface: Context, first: str, second: str, day: str) -> None:
	view = calendar(interface)
	left = view.grid.rectangle(named_block(view, first, day))
	right = view.grid.rectangle(named_block(view, second, day))
	assert left.right() <= right.left(), (left, right)
	assert (left.width() > 0) and (right.width() > 0)


@then(parsers.parse("le bloc « {name} » du {day} a toute la largeur des blocs prévus"))
def full_width(interface: Context, name: str, day: str) -> None:
	view = calendar(interface)
	block = named_block(view, name, day)
	only = view.grid.rectangle(block)
	neighbours = []
	for b in view.blocks():
		if (b.day == block.day) and (b != block):
			neighbours.append(view.grid.rectangle(b))
	every_one = True
	for other in neighbours:
		if not (only.width() >= other.width()):
			every_one = False
			break
	assert every_one, (only, neighbours)
	found = False
	for other in neighbours:
		if only.width() > other.width():
			found = True
			break
	assert found, (only, neighbours)


@then(parsers.parse("le bloc « {name} » du {day} est à la place du bloc « {other} »"))
def same_place(interface: Context, name: str, day: str, other: str) -> None:
	view = calendar(interface)
	first = view.grid.rectangle(named_block(view, name, day))
	second = view.grid.rectangle(named_block(view, other, day))
	assert (first.left(), first.width()) == (second.left(), second.width())


@then(parsers.parse("le bloc « {name} » du {day} a l'infobulle :"))
def block_tooltip(interface: Context, name: str, day: str, docstring: str) -> None:
	view = calendar(interface)
	assert tooltip(view.grid, view.grid.rectangle(named_block(view, name, day)).center()) == docstring


@then(parsers.parse("le bloc « {name} » de la journée du {day} a l'infobulle :"))
def whole_day_tooltip(interface: Context, name: str, day: str, docstring: str) -> None:
	view = calendar(interface)
	centre = view.header.rectangle(named_block(view, name, day, whole_day=True)).center()
	assert tooltip(view.header, centre) == docstring


@then(parsers.parse("la bande d'airplay « {name} » de {start} du {day} a l'infobulle :"))
def strip_tooltip(interface: Context, name: str, start: str, day: str, docstring: str) -> None:
	view = calendar(interface)
	assert tooltip(view.grid, view.grid.rectangle(named_strip(view, name, start, day)).center()) == docstring


@then(parsers.re(r"le calendrier a les cases cochées (?P<texts>«.+)"))
def ticked_boxes(interface: Context, texts: str) -> None:
	view = calendar(interface)
	c_list = []
	for c in view.findChildren(QCheckBox):
		if c.isChecked():
			c_list.append(c.text())
	assert c_list == NAME.findall(texts)


@then(parsers.parse("la case « {box} » du calendrier porte un carré de la couleur du bloc « {name} » du {day}"))
def coloured_box(interface: Context, box: str, name: str, day: str) -> None:
	"""https://github.com/dascritch/machincast/issues/293 : la couleur de l'icône de la case, au milieu, est celle du
	bloc dessiné, au milieu, là où il joue."""
	view = calendar(interface)
	c_list = []
	for c in view.findChildren(QCheckBox):
		if c.text() == box:
			c_list.append(c)
	(ticked,) = c_list
	icon = ticked.icon().pixmap(16, 16).toImage()
	assert not icon.isNull()
	middle = view.grid.rectangle(named_block(view, name, day)).center().toPoint()
	drawing = view.grid.grab().toImage()
	assert icon.pixelColor(8, 8).name() == drawing.pixelColor(middle).name()


@then(parsers.parse("la bande d'airplay « {name} » de {start} du {day} est dessinée en « {colour} » assombri"))
def strip_colour(interface: Context, name: str, start: str, day: str, colour: str) -> None:
	"""Le milieu de la bande, dans le dessin de la grille, a la couleur de sa priorité assombrie, comme toute bande
	d'airplay ; le dessin ne lève rien, ce que pytest-qt vérifie."""
	view = calendar(interface)
	s_list = []
	for s in view.strips():
		if (s.name == name) and (day_label(s.day) == day):
			s_list.append(s)
	(strip,) = s_list
	assert schedule(strip.day, strip.start) == start
	drawing = view.grid.grab().toImage()
	assert drawing.pixelColor(view.grid.rectangle(strip).center().toPoint()).name() == QColor(colour).darker(130).name()


@then(parsers.parse("la case « {box} » du calendrier a l'infobulle « {tooltip} »"))
def box_tooltip(interface: Context, box: str, tooltip: str) -> None:
	c_list = []
	for c in calendar(interface).findChildren(QCheckBox):
		if c.text() == box:
			c_list.append(c)
	(ticked,) = c_list
	assert ticked.toolTip() == tooltip


@then(parsers.re(r"le calendrier grise les jours (?P<days>«.+)"))
def greyed_days(interface: Context, days: str) -> None:
	view = calendar(interface)
	day_list = []
	for day in view.outdated_days():
		day_list.append(day_label(day))
	assert day_list == re.findall(r"« ([^»]+) »", days)


@then(
	parsers.re(
		r"le clic droit sur le bloc « (?P<name>[^»]+) » (?:du|de la (?P<whole_day>journée) du) (?P<day>\w+ \d+(?:er)?)"
		r" (?:propose (?P<entries>«.+)|ne propose rien)"
	)
)
def right_click_entries(interface: Context, name: str, whole_day: str | None, day: str, entries: str | None) -> None:
	menu = block_menu(calendar(interface), name, day, whole_day is not None)
	offered_list = []
	if menu is not None:
		offered_list = []
		for action in menu.actions():
			offered_list.append(action.text())
	assert offered_list == re.findall(r"« ([^»]+) »", (entries) or (""))


@then(parsers.parse("le choix du jour a proposé « {text} », à partir du « {day} »"))
def day_choice(interface: Context, text: str, day: str) -> None:
	assert interface.day_choice == [(text, date.fromisoformat(day))]


def skipped_sessions(database: Connection, name: str) -> list[str]:
	lines = database.execute(
		"SELECT s.day FROM event_skips s JOIN events e ON e.id = s.event_id WHERE e.internal_name = %s ORDER BY s.day",
		(name,),
	).fetchall()
	skipped_sessions = []
	for (day,) in lines:
		skipped_sessions.append(str(day))
	return skipped_sessions


@then(parsers.re(r"les sessions sautées de « (?P<name>[^»]+) » sont (?P<days>«.+)"))
def skipped_list(empty_database: Connection, name: str, days: str) -> None:
	assert skipped_sessions(empty_database, name) == re.findall(r"« ([^»]+) »", days)


@then(parsers.parse("aucune session de « {name} » n'est sautée"))
def no_skipped(empty_database: Connection, name: str) -> None:
	assert skipped_sessions(empty_database, name) == []


@then(parsers.parse("le bloc « {name} » du {day} est « {state} »"))
def block_state(interface: Context, name: str, day: str, state: str) -> None:
	assert _(named_block(calendar(interface), name, day).state) == state


@then(parsers.parse("le bouton « {text} » du calendrier est inactif"))
def inactive_button(interface: Context, text: str) -> None:
	assert not button(calendar(interface), text).isEnabled()


@then(parsers.parse("la question de création a dit « {text} »"))
def creation_question(interface: Context, text: str) -> None:
	assert interface.questions == [f"création : {text}"]


@then(parsers.parse("la fiche de l'événement a pour début « {start} » et pour fin « {end} »"))
def card_dates(interface: Context, start: str, end: str) -> None:
	card = window(interface).ui.tabs.currentWidget()
	assert isinstance(card, EventCard)
	ui = card.ui
	assert (ui.has_start.isChecked(), ui.has_end.isChecked()) == (True, True)
	fetched_list = [ui.start.dateTime().toString("yyyy-MM-dd HH:mm"), ui.end.dateTime().toString("yyyy-MM-dd HH:mm")]
	assert fetched_list == [start, end]


@then(parsers.parse("la base a toujours {count:d} événements"))
def events_in_database(empty_database: Connection, count: int) -> None:
	line = empty_database.execute("SELECT count(*) FROM events").fetchone()
	assert line is not None
	assert line[0] == count


# ─── Navigation et zoom (https://github.com/dascritch/machincast/issues/326) ───


def _texts_of(list_: QComboBox) -> list[str]:
	texts_of = []
	for rank in range(list_.count()):
		texts_of.append(list_.itemText(rank))
	return texts_of


@when(parsers.parse("je choisis la vue « {text} » du calendrier"))
def choose_view(interface: Context, text: str) -> None:
	view = calendar(interface)
	rank = _texts_of(view.view).index(text)
	view.view.setCurrentIndex(rank)
	view.view.activated.emit(rank)


@when(parsers.parse("je choisis le zoom « {text} » du calendrier"))
def choose_zoom(interface: Context, text: str) -> None:
	view = calendar(interface)
	rank = _texts_of(view.zoom).index(text)
	view.zoom.setCurrentIndex(rank)
	view.zoom.activated.emit(rank)


@when(
	parsers.re(
		r"je tourne (?:(?P<times>\d+) fois )?la molette vers le (?P<direction>haut|bas), avec Maj,"
		r" dans la grille du calendrier"
	)
)
def wheel(interface: Context, times: str | None, direction: str) -> None:
	grid = calendar(interface).grid
	notch = -120
	if direction == "haut":
		notch = 120
	for _click in range(int((times) or ("1"))):
		centre = QPointF(grid.width() / 2, grid.height() / 2)
		event = QWheelEvent(
			centre,
			grid.mapToGlobal(centre),
			QPoint(0, 0),
			QPoint(0, notch),
			Qt.MouseButton.NoButton,
			Qt.KeyboardModifier.ShiftModifier,
			Qt.ScrollPhase.NoScrollPhase,
			False,
		)
		QApplication.sendEvent(grid, event)


@then(parsers.re(r"la première ligne du calendrier commence par (?P<buttons>«.+)"))
def first_buttons(interface: Context, buttons: str) -> None:
	view = calendar(interface)
	bar = view.layout().itemAt(0).layout()
	widgets = []
	for rank in range(bar.count()):
		widgets.append(bar.itemAt(rank).widget())
	texts = []
	for widget in widgets[:3]:
		if isinstance(widget, QPushButton):
			texts.append(widget.text())
	assert texts == NAME.findall(buttons)


@then(
	parsers.re(
		r"elle finit par la liste (?P<views>«.+), sur « (?P<view>[^»]+) », puis « (?P<magnifier>[^»]+) » et la liste"
		r" (?P<zooms>«.+), sur « (?P<zoom>[^»]+) »"
	)
)
def line_end(interface: Context, views: str, view: str, magnifier: str, zooms: str, zoom: str) -> None:
	screen = calendar(interface)
	bar = screen.layout().itemAt(0).layout()
	last_list = []
	for rank in range(bar.count() - 3, bar.count()):
		last_list.append(bar.itemAt(rank).widget())
	assert last_list == [screen.view, screen.magnifier, screen.zoom]
	assert (_texts_of(screen.view), screen.view.currentText()) == (NAME.findall(views), view)
	assert screen.magnifier.text() == magnifier
	assert (_texts_of(screen.zoom), screen.zoom.currentText()) == (NAME.findall(zooms), zoom)


@then(parsers.parse("le bouton « {text} » du calendrier a l'infobulle « {tooltip} »"))
def button_tooltip(interface: Context, text: str, tooltip: str) -> None:
	assert button(calendar(interface), text).toolTip() == tooltip


@then(parsers.parse("la grille du calendrier montre {hours:d} heures, à partir de {top}"))
def shown_hours(interface: Context, hours: int, top: str) -> None:
	"""Les heures montrées dans la hauteur visible de la grille, et l'heure de son bord haut, à la minute."""
	view = calendar(interface)
	visible = view.scrolling.viewport().height()
	assert abs(view.hour_height() * hours - visible) <= 1, (view.hour_height(), visible)
	assert view.grid.height() == int(24 * view.hour_height()) + 1
	minutes = round(view.scrolling.verticalScrollBar().value() / view.hour_height() * 60)
	assert f"{minutes // 60:02d}:{minutes % 60:02d}" == top


@then(parsers.parse("le zoom du calendrier est sur « {text} »"))
def chosen_zoom(interface: Context, text: str) -> None:
	assert calendar(interface).zoom.currentText() == text
