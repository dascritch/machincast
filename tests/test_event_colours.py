"""Scénarios du point de la couleur d'un événement (https://github.com/dascritch/machincast/issues/635).

Le plugin des scénarios, « palette », s'abonne au point « grid.event_colour » des plugins du binaire
(machincast.plugins.active), que tests/conftest.py remet à vide après chaque scénario.
"""

import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from PySide6.QtGui import QStandardItem, QStandardItemModel
from pytest_bdd import given, parsers, scenarios, then

from machincast import plugins
from machincast.clock import FixedClock
from machincast.database import Role, open_connection
from machincast.interface import calendar
from machincast.interface.default_screen import EVENT_COLUMN, ITEM, stripe_colour
from machincast.intranet import calendar as intranet_calendar
from machincast.intranet import hour_grid
from machincast.shared import colours
from machincast.shared.grid import Priority, read_grid
from tests.database_fixtures import sample_database_parameters
from tests.interface_steps import Connection

scenarios("event_colours.feature")

PARIS = ZoneInfo("Europe/Paris")


def _event(connection: Connection, name: str) -> int:
	found = connection.execute("SELECT id FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert found is not None, name
	return int(str(found[0]))


@given("le plugin « palette » qui colore :")
def palette(empty_database: Connection, datatable: list[list[str]]) -> None:
	by_event: dict[int, str] = {}
	by_priority: dict[str, str] = {}
	names = set()
	for priority in Priority:
		names.add(str(priority))
	for what, colour in datatable[1:]:
		if what.strip() in names:
			by_priority[what.strip()] = colour.strip()
		else:
			by_event[_event(empty_database, what.strip())] = colour.strip()

	def answer(data: Any) -> str | None:
		if data["event"] in by_event:
			return by_event[data["event"]]
		return by_priority.get(data["priority"])

	plugins.active().points.subscribe("palette", colours.EVENT_COLOUR, answer)


def _grid_event(connection: Connection, name: str) -> Any:
	for event in read_grid(connection):
		if event.name == name:
			return event
	raise AssertionError(name)


@then(parsers.parse("la couleur de « {name} » est celle de la priorité « {priority} » du cœur"))
def core_colour(empty_database: Connection, name: str, priority: str) -> None:
	event = _grid_event(empty_database, name)
	assert calendar.block_colour(event).name() == calendar.COLOURS[Priority(priority)].name()


@then(parsers.parse("la couleur de « {name} » est « {colour} »"))
def plugin_colour(empty_database: Connection, name: str, colour: str) -> None:
	assert calendar.block_colour(_grid_event(empty_database, name)).name() == colour


@then(parsers.parse("la case « Émissions » du calendrier montre « {colour} », sans nom de couleur dans son infobulle"))
def legend(empty_database: Connection, colour: str) -> None:
	assert calendar.priority_colour(Priority.SHOW).name() == colour
	shown = calendar.Calendar(empty_database, _clock())
	box = shown.boxes[Priority.SHOW]
	assert box.toolTip() == "Montrer ou cacher les émissions", box.toolTip()
	shown.deleteLater()


def _clock() -> FixedClock:
	return FixedClock(datetime(2026, 11, 23, 12, tzinfo=PARIS))


def _airplay_cell(connection: Connection, name: str) -> Any:
	model = QStandardItemModel(1, EVENT_COLUMN + 1)
	cell = QStandardItem(name)
	cell.setData(("event", _event(connection, name), name), ITEM)
	model.setItem(0, EVENT_COLUMN, cell)
	return model, model.index(0, EVENT_COLUMN)


@then(parsers.parse("la cellule de l'événement « {name} » d'un tableau d'airplay a un trait « {colour} »"))
def stripe(empty_database: Connection, name: str, colour: str) -> None:
	_model, index = _airplay_cell(empty_database, name)
	found = stripe_colour(index)
	assert (found is not None) and (found.name() == colour), found


@then(parsers.parse("la cellule de l'événement « {name} » d'un tableau d'airplay n'a pas de trait"))
def no_stripe(empty_database: Connection, name: str) -> None:
	_model, index = _airplay_cell(empty_database, name)
	assert stripe_colour(index) is None


@then(parsers.parse("sur « {background} », le texte est « {text} »"))
def readable(background: str, text: str) -> None:
	assert colours.readable_text(background) == text


@then(
	parsers.re(r"le nom du bloc « (?P<name>[^»]+) », (?P<state>à l'antenne|estompé), s'écrit en « (?P<colour>[^»]+) »")
)
def block_name(empty_database: Connection, name: str, state: str, colour: str) -> None:
	shown = calendar.block_colour(_grid_event(empty_database, name))
	assert calendar.name_colour(shown, on_air=state == "à l'antenne").name() == colour


def _intranet(day: str) -> tuple[list[dict[str, Any]], date]:
	day_text, month, year = day.split("/")
	first = date(int(year), int(month), int(day_text))
	with open_connection(*sample_database_parameters(), Role.INTRANET) as connection:
		found = intranet_calendar.entries(connection, first, first)
	return found, first


@then(
	parsers.parse(
		"le calendrier de l'intranet du {day} donne à « {name} » la couleur « {colour} », et à « {other} » aucune"
	)
)
def intranet_json(day: str, name: str, colour: str, other: str) -> None:
	found, _first = _intranet(day)
	by_name = {}
	for entry in found:
		by_name[entry["name"]] = entry["colour"]
	assert (by_name[name], by_name[other]) == (colour, None), by_name


def _svg(day: str, name: str) -> str:
	found, first = _intranet(day)
	page = hour_grid.week(found, first, datetime(2026, 11, 23, 12, tzinfo=PARIS))
	for block in re.finditer(r"<svg class=\"bloc [^\"]*\"[^>]*>.*?</svg>", page, re.DOTALL):
		if f'<span class="summary p-name">{name}</span>' in block.group(0):
			return block.group(0)
	raise AssertionError(name)


@then(
	parsers.parse(
		"la grille de l'intranet du {day} dessine « {name} » en « {colour} », sur un fond « {background} », cadré de"
		" « {frame} »"
	)
)
def intranet_grid(day: str, name: str, colour: str, background: str, frame: str) -> None:
	block = _svg(day, name)
	assert 'class="bloc show colore' in block, block
	assert f'<rect class="fond" width="100%" height="100%" fill="{background}"/>' in block, block
	assert f'<rect class="cadre" width="100%" height="100%" stroke="{frame}"/>' in block, block
	for played in re.findall(r'<rect class="antenne"[^>]*/>', block):
		assert f'fill="{colour}"' in played, played


@then(
	parsers.parse(
		"la grille de l'intranet du {day} dessine « {name} » aux couleurs de sa priorité, par la feuille de style"
	)
)
def intranet_default(day: str, name: str) -> None:
	block = _svg(day, name)
	assert 'class="bloc show"' in block, block
	assert 'fill="#' not in block, block
	assert "stroke=" not in block, block
