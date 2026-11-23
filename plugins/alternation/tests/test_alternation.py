"""Scénarios des émissions en alternance (https://github.com/dascritch/machincast/issues/609).

Les événements sont en base de test ; le plugin s'abonne au point « grid.substitutions » des plugins du binaire
(machincast.plugins.active), que tests/conftest.py remet à vide après chaque scénario. La section de la fiche est
ouverte seule, au rôle machincast_interface, à une heure fixe.
"""

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import machincast_alternation
import psycopg
import pytest
from machincast_alternation import rotation
from machincast_alternation.section import AlternationSection
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot
from tests.database_fixtures import sample_database_parameters
from tests.interface_steps import date_or_none

from conftest import PLUGIN
from machincast import plugins
from machincast.clock import FixedClock
from machincast.database import Role, open_connection
from machincast.interface.card import Refusal
from machincast.shared import grid

scenarios(str(PLUGIN / "tests" / "features" / "alternation.feature"))

Connection = psycopg.Connection[tuple[object, ...]]
EMPTY = "—"


@dataclass
class Context:
	read: list[grid.Event] = field(default_factory=list)
	section: AlternationSection | None = None
	connection: Connection | None = None
	changes: list[None] = field(default_factory=list)
	replaced: list[bool] = field(default_factory=list)


@pytest.fixture
def context(qtbot: QtBot) -> Iterator[Context]:
	found = Context()
	yield found
	if found.connection is not None:
		found.connection.close()


def _identifier(connection: Connection, name: str) -> int:
	found = connection.execute("SELECT id FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert found is not None, name
	return int(str(found[0]))


def _names(text: str) -> list[str]:
	return re.findall(r"« ([^»]+) »", text)


@given("les événements :")
def events(empty_database: Connection, datatable: list[list[str]]) -> None:
	for name, priority, start, end, days in datatable[1:]:
		day_list = []
		if days.strip():
			day_list.append(days.strip())
		empty_database.execute(
			"INSERT INTO events (internal_name, priority, starts_at, ends_at, recurrence_days)"
			" VALUES (%s, %s, %s, %s, %s::weekday[])",
			(name.strip(), priority.strip(), date_or_none(start.strip()), date_or_none(end.strip()), day_list),
		)


@given("le plugin des émissions en alternance, chargé")
def loaded() -> None:
	plugins.active().points.subscribe("alternation", "grid.substitutions", lambda _data: rotation.substitution())


def _update(connection: Connection, name: str, path: list[str], value: object) -> None:
	connection.execute(
		"UPDATE events SET properties = jsonb_set(properties, %s, %s::jsonb, true) WHERE internal_name = %s",
		(path, json.dumps(value), name),
	)


@given(parsers.re(r"l'alternance de « (?P<meta>[^»]+) » : (?P<ranks>.+)"))
def alternation(empty_database: Connection, meta: str, ranks: str) -> None:
	ranked: dict[str, int | None] = {}
	candidates: list[int] = []
	for rank, cell in enumerate(ranks.split(", "), start=1):
		chosen = None
		if cell.strip() != EMPTY:
			chosen = _identifier(empty_database, _names(cell)[0])
			if chosen not in candidates:
				candidates.append(chosen)
		ranked[str(rank)] = chosen
	_update(
		empty_database,
		meta,
		["alternation"],
		{"candidates": sorted(candidates), "rotation": ranked, "choices": {}},
	)


@given(parsers.parse("le passage du « {day} » de « {meta} » choisi : « {name} »"))
def choice(empty_database: Connection, day: str, meta: str, name: str) -> None:
	_update(empty_database, meta, ["alternation", "choices", day], _identifier(empty_database, name))


@given(parsers.parse("la propriété « {key} » de « {meta} » : « {value} »"))
def other_property(empty_database: Connection, key: str, meta: str, value: str) -> None:
	_update(empty_database, meta, [key], value)


@when("la grille est lue")
def read(empty_database: Connection, context: Context) -> None:
	context.read = grid.read_grid(empty_database)


@then(parsers.re(r"le calendrier de décembre 2026 montre (?P<shown>.+)"))
def december(context: Context, shown: str) -> None:
	found = []
	for planned in grid.plan(context.read, datetime(2026, 12, 1), datetime(2027, 1, 1)):
		if (planned.start.weekday() == 2) and (planned.start.hour == 20):
			found.append((planned.occurrence.event.name, planned.start.day))
	expected = []
	for name, day in re.findall(r"« ([^»]+) » le (\d+)", shown):
		expected.append((name, int(day)))
	assert found == expected


@then(parsers.re(r"la grille lue a (?P<names>«.+»)"))
def read_names(context: Context, names: str) -> None:
	found = []
	for event in context.read:
		found.append(event.name)
	assert found == _names(names)


@then(parsers.parse("le « {day} » est le {rank:d} de son mois"))
def week(day: str, rank: int) -> None:
	assert rotation.week(date.fromisoformat(day)) == rank


# ─── La section de la fiche ────────────────────────────────


def _open(context: Context, qtbot: QtBot, identifier: int | None, moment: str) -> None:
	socket, database = sample_database_parameters()
	context.connection = open_connection(socket, database, Role.INTERFACE)
	clock = FixedClock(datetime.fromisoformat(moment).astimezone())
	section = AlternationSection(context.connection, clock)
	qtbot.addWidget(section)
	section.changed.connect(lambda: context.changes.append(None))
	section.replaces_items.connect(context.replaced.append)
	with context.connection.transaction():
		section.read(identifier)
	section.show()
	context.section = section
	context.changes.clear()


@when(parsers.parse("j'ouvre la section des émissions en alternance de « {meta} », le « {moment} »"))
def open_section(empty_database: Connection, context: Context, qtbot: QtBot, meta: str, moment: str) -> None:
	_open(context, qtbot, _identifier(empty_database, meta), moment)


@when(parsers.parse("j'ouvre la section des émissions en alternance d'un nouvel événement, le « {moment} »"))
def open_new(empty_database: Connection, context: Context, qtbot: QtBot, moment: str) -> None:
	_open(context, qtbot, None, moment)


def _section(context: Context) -> AlternationSection:
	assert context.section is not None
	return context.section


@then("la section est cochée, et remplace la liste de lecture")
def ticked(context: Context) -> None:
	assert _section(context).enabled.isChecked()
	assert context.replaced[-1] is True
	assert not _section(context).content.isHidden()


@then("la section n'est pas cochée")
def unticked(context: Context) -> None:
	assert not _section(context).enabled.isChecked()
	assert _section(context).content.isHidden()


@then("la section remplace la liste de lecture")
def replaces(context: Context) -> None:
	assert context.replaced[-1] is True


@then("la section ne remplace plus la liste de lecture")
def gives_back(context: Context) -> None:
	assert context.replaced[-1] is False
	assert _section(context).content.isHidden()


@then(parsers.re(r"elle propose les émissions (?P<offered>.+), dont (?P<chosen>.+) sont cochées"))
def offered(context: Context, offered: str, chosen: str) -> None:
	candidates = _section(context).candidates
	found = []
	ticked_list = []
	for index in range(candidates.count()):
		item = candidates.item(index)
		assert item is not None
		found.append(item.text())
		if item.checkState() == Qt.CheckState.Checked:
			ticked_list.append(item.text())
	assert (found, ticked_list) == (_names(offered), _names(chosen))


def _caption(section: AlternationSection, box: QComboBox, form: Any) -> str:
	label = form.labelForField(box)
	assert isinstance(label, QLabel)
	return label.text()


@then("sa rotation est :")
def ranks(context: Context, datatable: list[list[str]]) -> None:
	section = _section(context)
	found = []
	for box in section.rotation_boxes:
		found.append([_caption(section, box, section.rotation_form), box.currentText()])
	expected = []
	for rank, name in datatable[1:]:
		expected.append([rank.strip(), name.strip()])
	assert found == expected


@then(parsers.re(r"sa rotation est par (?P<captions>.+)"))
def rank_captions(context: Context, captions: str) -> None:
	section = _section(context)
	found = []
	for box in section.rotation_boxes:
		found.append(_caption(section, box, section.rotation_form))
	assert found == _names(captions)


@then(parsers.re(r"la rotation est (?P<names>.+)"))
def rotation_names(context: Context, names: str) -> None:
	found = []
	for box in _section(context).rotation_boxes:
		found.append(box.currentText())
	assert found == _names(names)


@then(parsers.parse("ses {count:d} prochains passages commencent par :"))
def coming(context: Context, count: int, datatable: list[list[str]]) -> None:
	section = _section(context)
	assert len(section.coming_boxes) == count
	found = []
	for box in section.coming_boxes[: len(datatable) - 1]:
		found.append([_caption(section, box, section.coming_form), box.currentText()])
	expected = []
	for day, name in datatable[1:]:
		expected.append([day.strip(), name.strip()])
	assert found == expected


@then("la section ne signale aucun changement")
def no_change(context: Context) -> None:
	assert context.changes == []


@then("la section signale un changement")
def change(context: Context) -> None:
	assert context.changes != []


@then(parsers.parse("elle dit « {text} »"))
def says(context: Context, text: str) -> None:
	assert _section(context).coming_note.text() == text


@when(parsers.parse("je choisis « {name} » pour le passage du « {day} »"))
def choose(context: Context, name: str, day: str) -> None:
	section = _section(context)
	box = section.coming_boxes[section.days.index(date.fromisoformat(day))]
	box.setCurrentIndex(box.findText(name))


@when(parsers.parse("je décoche l'émission « {name} »"))
def untick_show(context: Context, name: str) -> None:
	(item,) = _section(context).candidates.findItems(name, Qt.MatchFlag.MatchExactly)
	item.setCheckState(Qt.CheckState.Unchecked)


@when(parsers.re(r"je (?P<gesture>coche|décoche) « Émissions en alternance »"))
def tick_section(context: Context, gesture: str) -> None:
	box = _section(context).enabled
	assert box.text() == "Émissions en alternance"
	box.setChecked(gesture == "coche")


@when("la section s'enregistre")
def save(empty_database: Connection, context: Context) -> None:
	assert context.connection is not None
	with context.connection.transaction():
		_section(context).write(_identifier(empty_database, "Mercredi soir"))


@then(parsers.parse("la section refuse l'enregistrement : « {message} »"))
def refused(empty_database: Connection, context: Context, message: str) -> None:
	assert context.connection is not None
	with pytest.raises(Refusal) as refusal, context.connection.transaction():
		_section(context).write(_identifier(empty_database, "Mercredi soir"))
	assert str(refusal.value) == message


@then(parsers.parse("« {name} » a pour propriétés :"))
def stored(empty_database: Connection, name: str, docstring: str) -> None:
	found = empty_database.execute("SELECT properties FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert found is not None
	assert found[0] == json.loads(docstring)


# ─── Le plugin ─────────────────────────────────────────────


@dataclass
class Registered:
	points: list[str] = field(default_factory=list)


@dataclass
class _Context:
	executable: str
	configuration: Any = None


@dataclass
class _Plugin:
	context: _Context
	registered: Registered

	def on(self, point: str, function: Any) -> None:
		self.registered.points.append(point)


@pytest.fixture
def registered() -> Registered:
	return Registered()


@when(parsers.parse("le plugin des émissions en alternance s'enregistre dans « {executable} »"))
def register(registered: Registered, executable: str) -> None:
	machincast_alternation.register(_Plugin(_Context(executable), registered))  # type: ignore[arg-type]


@then(parsers.re(r"il s'abonne seulement à (?P<points>.+)"))
def subscribed(registered: Registered, points: str) -> None:
	assert registered.points == _names(points)
