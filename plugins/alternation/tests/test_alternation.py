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
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QComboBox, QLabel
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot
from tests.database_fixtures import sample_database_parameters
from tests.interface_steps import Context as InterfaceContext
from tests.interface_steps import date_or_none, opened_card

from conftest import PLUGIN
from machincast import plugins
from machincast.clock import FixedClock
from machincast.database import Role, open_connection
from machincast.interface.card import Refusal
from machincast.interface.event_card import EventCard
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
	grid_replaced: list[bool] = field(default_factory=list)


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


@given(parsers.re(r"l'alternance de « (?P<meta>[^»]+) » : (?P<ranks>(?:«|—).+)"))
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


@given(parsers.re(r"l'alternance par quinzaine de « (?P<meta>[^»]+) » : « (?P<first>[^»]+) », « (?P<second>[^»]+) »"))
def fortnightly(empty_database: Connection, meta: str, first: str, second: str) -> None:
	ranked = {"1": _identifier(empty_database, first), "2": _identifier(empty_database, second)}
	_update(
		empty_database,
		meta,
		["alternation"],
		{"mode": "fortnightly", "candidates": sorted(ranked.values()), "rotation": ranked, "choices": {}},
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


MONTHS = {
	"décembre 2026": (datetime(2026, 12, 1), datetime(2027, 1, 1)),
	"janvier 2027": (datetime(2027, 1, 1), datetime(2027, 2, 1)),
}


@then(parsers.re(r"le calendrier de (?P<month>décembre 2026|janvier 2027) montre (?P<shown>.+)"))
def month(context: Context, month: str, shown: str) -> None:
	found = []
	first, last = MONTHS[month]
	for planned in grid.plan(context.read, first, last):
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


@then(parsers.parse("depuis le « {first} », le « {day} » est la {rank:d} semaine de sa quinzaine"))
def fortnight(first: str, day: str, rank: int) -> None:
	assert rotation.fortnight(date.fromisoformat(day), date.fromisoformat(first)) == rank


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
	section.replaces_grid.connect(context.grid_replaced.append)
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


@then(
	parsers.re(r"elle propose les émissions (?P<offered>.+), dont (?:(?P<chosen>«.+) sont cochées|aucune n'est cochée)")
)
def offered(context: Context, offered: str, chosen: str | None) -> None:
	candidates = _section(context).candidates
	found = []
	ticked_list = []
	for index in range(candidates.count()):
		item = candidates.item(index)
		assert item is not None
		found.append(item.text())
		if item.checkState() == Qt.CheckState.Checked:
			ticked_list.append(item.text())
	assert (found, ticked_list) == (_names(offered), _names((chosen) or ("")))


def _caption(section: AlternationSection, box: QComboBox, form: Any) -> str:
	label = form.labelForField(box)
	assert isinstance(label, QLabel)
	return label.text()


@then(parsers.re(r"son rythme est « (?P<mode>[^»]+) »(?:, parmi (?P<modes>.+))?"))
def mode(context: Context, mode: str, modes: str | None) -> None:
	box = _section(context).mode
	assert box.currentText() == mode
	if modes is not None:
		found = []
		for index in range(box.count()):
			found.append(box.itemText(index))
		assert found == _names(modes)


@when(parsers.parse("je choisis le rythme « {mode} »"))
def choose_mode(context: Context, mode: str) -> None:
	box = _section(context).mode
	box.setCurrentIndex(box.findText(mode))


@then(parsers.parse("la rotation montre {count:d} semaines"))
def shown_ranks(context: Context, count: int) -> None:
	assert len(_section(context).rank_boxes()) == count
	hidden = 0
	for box in _section(context).rotation_boxes:
		if box.isHidden():
			hidden += 1
	assert hidden == len(rotation.WEEKS) - count


@then(parsers.parse("le passage du « {day} » est « {text} »"))
def coming_text(context: Context, day: str, text: str) -> None:
	section = _section(context)
	assert section.coming_boxes[section.days.index(date.fromisoformat(day))].currentText() == text


@then("sa rotation est :")
def ranks(context: Context, datatable: list[list[str]]) -> None:
	section = _section(context)
	found = []
	for box in section.rank_boxes():
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
	for box in _section(context).rank_boxes():
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


# ─── Créer une émission sur le créneau partagé ─────────────


@then(parsers.parse("le bouton « {label} » est à côté de « {caption} »"))
def create_button(context: Context, label: str, caption: str) -> None:
	section = _section(context)
	assert section.creation.text() == label
	assert section.candidates_caption.text() == caption
	assert section.creation.parentWidget() is section.candidates_caption.parentWidget()
	assert abs(section.creation.y() - section.candidates_caption.y()) < section.creation.height()


def _create(context: Context, answer: str | None) -> None:
	section = _section(context)
	section.ask_name = lambda _parent: answer  # type: ignore[method-assign]
	section.creation.click()


@when(parsers.parse("je crée l'émission « {name} » sur ce créneau partagé"))
def create(context: Context, name: str) -> None:
	_create(context, name)


@when("j'abandonne la création d'une émission sur ce créneau partagé")
def abandon(context: Context) -> None:
	_create(context, None)


@then(parsers.re(r"elle dit, sous ses émissions, « (?P<text>.+) »$"))
def candidates_note(context: Context, text: str) -> None:
	assert _section(context).candidates_note.text() == text


@then(parsers.parse("l'événement « {name} » n'existe pas encore"))
def missing(empty_database: Connection, name: str) -> None:
	assert empty_database.execute("SELECT 1 FROM events WHERE internal_name = %s", (name,)).fetchone() is None


@when(parsers.parse("je choisis « {name} » pour le {rank:d}e rang de la rotation"))
def choose_rank(context: Context, name: str, rank: int) -> None:
	box = _section(context).rotation_boxes[rank - 1]
	box.setCurrentIndex(box.findText(name))


@then(parsers.parse("l'événement « {name} » est une émission, de « {start} » à « {end} », sans jour de récurrence"))
def created(empty_database: Connection, name: str, start: str, end: str) -> None:
	found = empty_database.execute(
		"SELECT priority::text, starts_at, ends_at, recurrence_days::text[] FROM events WHERE internal_name = %s",
		(name,),
	).fetchone()
	assert found == ("show", date_or_none(start), date_or_none(end), [])


@then(parsers.parse("l'alternance de « {meta} » a « {name} » parmi ses émissions, et au {rank:d}e rang de sa rotation"))
def in_alternation(empty_database: Connection, meta: str, name: str, rank: int) -> None:
	found = empty_database.execute("SELECT properties FROM events WHERE internal_name = %s", (meta,)).fetchone()
	assert found is not None
	stored = found[0]["alternation"]  # type: ignore[index]
	identifier = _identifier(empty_database, name)
	assert identifier in stored["candidates"]
	assert stored["rotation"][str(rank)] == identifier


# ─── L'héritage de l'émission créée, et le créneau partagé ─

INHERITED = (
	r"« (?P<name>[^»]+) » masque ses sonores, passe en fin de liste au secours « (?P<end>[^»]+) », et a pour secours"
	r" de stream tombé « (?P<stream>[^»]+) »"
)


@given(parsers.re(INHERITED))
def inheritable(empty_database: Connection, name: str, end: str, stream: str) -> None:
	empty_database.execute(
		"UPDATE events SET hide_metadata = true, end_of_list = 'fallback', properties = properties"
		" || jsonb_build_object('end_fallback_event', %s::bigint, 'stream_fallback_event', %s::bigint)"
		" WHERE internal_name = %s",
		(_identifier(empty_database, end), _identifier(empty_database, stream), name),
	)


@then(parsers.re(INHERITED))
def inherited(empty_database: Connection, name: str, end: str, stream: str) -> None:
	found = empty_database.execute(
		"SELECT hide_metadata, end_of_list::text, properties FROM events WHERE internal_name = %s", (name,)
	).fetchone()
	assert found == (
		True,
		"fallback",
		{
			"end_fallback_event": _identifier(empty_database, end),
			"stream_fallback_event": _identifier(empty_database, stream),
		},
	)


@then(parsers.parse("« {name} » laisse décider le masquage, rejoue sa liste, sans secours"))
def nothing_inherited(empty_database: Connection, name: str) -> None:
	found = empty_database.execute(
		"SELECT hide_metadata, end_of_list::text FROM events WHERE internal_name = %s", (name,)
	).fetchone()
	assert found == (None, "replay")


@then(parsers.parse("l'événement « {name} » a pour nom public « {public_name} »"))
def public_name(empty_database: Connection, name: str, public_name: str) -> None:
	found = empty_database.execute("SELECT public_name FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert found == (public_name,)


@given(parsers.parse("« {name} » revient le lundi et le mercredi, de {start} à {end}"))
def twice_a_week(empty_database: Connection, name: str, start: str, end: str) -> None:
	empty_database.execute(
		"UPDATE events SET recurrence_days = '{monday,wednesday}', starts_at = %s, ends_at = %s WHERE internal_name = %s",
		(date_or_none(f"2026-11-30 {start}"), date_or_none(f"2026-11-30 {end}"), name),
	)


@given("la section des émissions en alternance, dans la fiche d'un événement")
def card_section() -> None:
	def section(data: Any) -> AlternationSection:
		return AlternationSection(data["connection"], data["card"].clock, data["parent"])

	plugins.active().points.subscribe("alternation", "interface.event_card", section)


MODES = {3: "three_weekly", 4: "four_weekly"}


@given(parsers.re(r"l'alternance d'une semaine sur (?P<period>\d) de « (?P<meta>[^»]+) » : (?P<names>«.+»)"))
def every_few_weeks(empty_database: Connection, period: str, meta: str, names: str) -> None:
	ranked: dict[str, int | None] = {}
	candidates: list[int] = []
	for rank, name in enumerate(_names(names), start=1):
		chosen = _identifier(empty_database, name)
		ranked[str(rank)] = chosen
		if chosen not in candidates:
			candidates.append(chosen)
	_update(
		empty_database,
		meta,
		["alternation"],
		{"mode": MODES[int(period)], "candidates": sorted(candidates), "rotation": ranked, "choices": {}},
	)


@given(parsers.re(r"(?P<names>«.+») sont aussi parmi les émissions de « (?P<meta>[^»]+) »$"))
def also_candidates(empty_database: Connection, names: str, meta: str) -> None:
	found = empty_database.execute(
		"SELECT properties -> 'alternation' -> 'candidates' FROM events WHERE internal_name = %s", (meta,)
	).fetchone()
	assert found is not None
	candidates = list(found[0])  # type: ignore[call-overload]
	for name in _names(names):
		candidates.append(_identifier(empty_database, name))
	_update(empty_database, meta, ["alternation", "candidates"], sorted(candidates))


@then(parsers.parse("la case « Émissions en alternance » ne se coche pas, et dit « {tip} »"))
def not_tickable(context: Context, tip: str) -> None:
	box = _section(context).enabled
	assert not box.isEnabled()
	assert box.toolTip() == tip


@then("la case « Émissions en alternance » se coche")
def tickable(context: Context) -> None:
	assert _section(context).enabled.isEnabled()


@when("la fiche coche le jour « mercredi » de la récurrence")
def wednesday_ticked(context: Context) -> None:
	_section(context).days_changed(frozenset({2}))


@when("la fiche décoche tous les jours de la récurrence")
def no_day(context: Context) -> None:
	_section(context).days_changed(frozenset())


def _card_section(interface: InterfaceContext, context: Context) -> AlternationSection:
	"""La section de la fiche ouverte, qui devient celle du scénario."""
	found = opened_card(interface).findChild(AlternationSection, "alternation")
	assert isinstance(found, AlternationSection)
	context.section = found
	return found


@then(parsers.re(r"la case « Émissions en alternance » de la fiche (?P<state>ne se coche pas|se coche)"))
def card_tickable(interface: InterfaceContext, context: Context, state: str) -> None:
	assert _card_section(interface, context).enabled.isEnabled() == (state == "se coche")


@when("je coche le jour « mercredi » de la récurrence de la fiche")
def card_wednesday(interface: InterfaceContext) -> None:
	card = opened_card(interface)
	assert isinstance(card, EventCard)
	card.days[2].setChecked(True)


@then(
	parsers.re(
		r"la fiche montre, à la place de l'encadré de la grille, l'encadré « (?P<title>[^»]+) » : « (?P<text>.+) »$"
	)
)
def card_grid_replaced(interface: InterfaceContext, context: Context, title: str, text: str) -> None:
	card = opened_card(interface)
	assert isinstance(card, EventCard)
	section = _card_section(interface, context)
	assert card.ui.grid_group.isHidden()
	assert not section.shared_box.isHidden()
	assert section.shared_box.title() == title
	assert section.shared_text.text() == text
	top = card.ui.top
	assert top.indexOf(section.shared_box) == top.indexOf(card.ui.grid_group) + 1


@then("la section des émissions en alternance est cachée, et la liste de lecture alignée sur le formulaire")
def section_hidden(interface: InterfaceContext, context: Context) -> None:
	card = opened_card(interface)
	assert isinstance(card, EventCard)
	section = _card_section(interface, context)
	assert section.isHidden()
	assert card.ui.item_group.isVisible()
	group = card.ui.item_group.mapTo(card, QPoint(0, 0)).x()
	caption = card.ui.internal_name_caption.mapTo(card, QPoint(0, 0)).x()
	assert group == caption, (group, caption)


@when("je coche « Émissions en alternance » dans la fiche")
def card_ticks(interface: InterfaceContext, context: Context) -> None:
	_card_section(interface, context).enabled.setChecked(True)


@then("la section des émissions en alternance remplace la liste de lecture")
def section_shown(interface: InterfaceContext, context: Context) -> None:
	card = opened_card(interface)
	assert isinstance(card, EventCard)
	assert _card_section(interface, context).isVisible()
	assert card.ui.item_group.isHidden()


@then("la fiche montre l'encadré de la grille")
def card_grid_shown(interface: InterfaceContext, context: Context) -> None:
	card = opened_card(interface)
	assert isinstance(card, EventCard)
	assert not card.ui.grid_group.isHidden()
	assert _card_section(interface, context).shared_box.isHidden()


@then(parsers.re(r"la section remplace l'encadré de la grille par « (?P<text>.+) »$"))
def section_grid(context: Context, text: str) -> None:
	assert context.grid_replaced[-1] is True
	assert _section(context).shared_text.text() == text


@then("la section laisse l'encadré de la grille")
def section_keeps_grid(context: Context) -> None:
	assert context.grid_replaced[-1] is False


@then("son tableau est :")
def shared_table(context: Context, datatable: list[list[str]]) -> None:
	table = _section(context).shared_table
	headers = []
	for column in range(table.columnCount()):
		header = table.horizontalHeaderItem(column)
		assert header is not None
		headers.append(header.text())
	rows = [headers]
	for row in range(table.rowCount()):
		cells = []
		for column in range(table.columnCount()):
			cell = table.item(row, column)
			assert cell is not None
			cells.append(cell.text())
		rows.append(cells)
	expected = []
	for line in datatable:
		cells = []
		for cell in line:
			cells.append(cell.strip())
		expected.append(cells)
	assert rows == expected


@when(parsers.parse("je double-clique sur la ligne « {name} » du tableau"))
def double_click(context: Context, name: str) -> None:
	table = _section(context).shared_table
	found = []
	for row in range(table.rowCount()):
		cell = table.item(row, 2)
		if (cell is not None) and (cell.text() == name):
			found.append(row)
	(row,) = found
	table.cellDoubleClicked.emit(row, 0)


@then(parsers.parse("l'onglet ouvert est la fiche de l'événement « {name} »"))
def card_opened(interface: InterfaceContext, name: str) -> None:
	card = opened_card(interface)
	assert isinstance(card, EventCard)
	assert card.ui.internal_name.text() == name


@then(parsers.parse("seule la ligne « {name} », l'émission de la fiche, est en gras"))
def bold_row(context: Context, name: str) -> None:
	table = _section(context).shared_table
	bold = []
	for row in range(table.rowCount()):
		cell = table.item(row, 2)
		assert cell is not None
		if cell.font().bold():
			bold.append(cell.text())
	assert bold == [name]
