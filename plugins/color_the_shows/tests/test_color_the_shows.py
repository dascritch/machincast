"""Scénarios des couleurs des émissions (https://github.com/dascritch/machincast/issues/628).

Les événements sont en base de test. Le plugin chargé répond au point « grid.event_colour » des plugins du binaire
(machincast.plugins.active), que tests/conftest.py remet à vide après chaque scénario ; ses connexions vont à la base
de test, jamais à celle de production. La section de la fiche et la fenêtre du plugin s'ouvrent seules, au rôle
machincast_interface.
"""

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import machincast_color_the_shows
import psycopg
import pytest
from machincast_color_the_shows import queries, settings
from machincast_color_the_shows.palette import LIFETIME, Palette
from machincast_color_the_shows.section import SWATCH, GenreSection, field_row
from machincast_color_the_shows.settings import COLOUR_COLUMN, NAME_COLUMN, ColoursSettings
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot
from tests.database_fixtures import configuration_test, sample_database_parameters

from conftest import PLUGIN, Connection
from machincast import plugins
from machincast.clock import FixedClock
from machincast.database import Role, open_connection
from machincast.interface import calendar
from machincast.interface.event_card import EventCard
from machincast.shared.colours import event_colour
from machincast.shared.grid import Priority

scenarios(str(PLUGIN / "tests" / "features" / "color_the_shows.feature"))

FIELDS = {"Fil antenne": "background_programming", "Émission": "show", "Spéciale": "special"}
"""Les couleurs des priorités, par leur intitulé dans la fenêtre."""


def _connect() -> Connection:
	return _connect_as(Role.INTERFACE)


def _connect_as(role: Role) -> Connection:
	socket, database = sample_database_parameters()
	return open_connection(socket, database, role)


def _unreachable() -> Connection:
	raise psycopg.OperationalError("connexion refusée")


@dataclass
class Clock:
	now: float = 1000.0

	def __call__(self) -> float:
		return self.now


@dataclass
class Context:
	palette: Palette | None = None
	clock: Clock = field(default_factory=Clock)
	section: GenreSection | None = None
	connection: Connection | None = None
	changes: list[None] = field(default_factory=list)
	window: ColoursSettings | None = None
	card: EventCard | None = None
	points: list[str] = field(default_factory=list)


@pytest.fixture
def context(qtbot: QtBot) -> Iterator[Context]:
	found = Context()
	yield found
	if found.window is not None:
		found.window.close()
	if found.card is not None:
		found.card.close()
	if found.connection is not None:
		found.connection.close()


def _names(text: str) -> list[str]:
	return re.findall(r"« ([^»]*) »", text)


def _event(connection: Connection, name: str) -> tuple[int, str]:
	found = connection.execute("SELECT id, priority::text FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert found is not None, name
	return int(str(found[0])), str(found[1])


def _genre(connection: Connection, name: str) -> int:
	found = connection.execute("SELECT id FROM color_the_shows__genres WHERE name = %s", (name,)).fetchone()
	assert found is not None, name
	return int(str(found[0]))


def _genres(connection: Connection) -> list[list[str]]:
	found = []
	for _identifier, name, colour in queries.genres(connection):
		found.append([name, colour])
	return found


def _window(context: Context) -> ColoursSettings:
	assert context.window is not None
	return context.window


def _section(context: Context) -> GenreSection:
	assert context.section is not None
	return context.section


class _Plugin:
	"""Un plugin chargé, abonné aux points du binaire, ou qui note seulement ses abonnements."""

	def __init__(self, executable: str, noted: list[str] | None = None) -> None:
		self.context = SimpleNamespace(executable=executable, configuration=configuration_test())
		self.noted = noted

	def on(self, point: str, function: Any) -> None:
		if self.noted is not None:
			self.noted.append(point)
			return
		plugins.active().points.subscribe("color_the_shows", point, function)


@pytest.fixture
def test_database(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Les connexions du plugin vont à la base de test, au rôle demandé : jamais à la base de production."""

	def opened(_socket: object, _database: object, role: Role) -> Connection:
		return _connect_as(role)

	monkeypatch.setattr(machincast_color_the_shows, "open_connection", opened)
	monkeypatch.setattr(settings, "open_connection", opened)


# ─── Étant donné ───────────────────────────────────────────


@given("les tables du plugin des couleurs des émissions")
def tables(base: Connection) -> None:
	pass


@given("les événements :")
def events(base: Connection, datatable: list[list[str]]) -> None:
	for name, priority in datatable[1:]:
		# Un secours est hors de la grille : sans dates.
		start = None
		end = None
		if priority.strip() != "fallback":
			start = "2026-11-23 10:00+01"
			end = "2026-11-23 11:00+01"
		base.execute(
			"INSERT INTO events (internal_name, priority, starts_at, ends_at) VALUES (%s, %s, %s, %s)",
			(name.strip(), priority.strip(), start, end),
		)


@given(parsers.parse("le genre « {genre} » de « {name} »"))
def genre_of(base: Connection, genre: str, name: str) -> None:
	queries.write_genre(base, _event(base, name)[0], _genre(base, genre))


@given(parsers.parse("les propriétés de « {name} » : {properties}"))
def properties(base: Connection, name: str, properties: str) -> None:
	base.execute("UPDATE events SET properties = %s::jsonb WHERE internal_name = %s", (properties, name))


@given(parsers.parse("le plugin des couleurs des émissions, chargé dans « {executable} »"))
def loaded(test_database: None, executable: str) -> None:
	machincast_color_the_shows.register(_Plugin(executable))  # type: ignore[arg-type]


@given("une palette lue")
def palette_read(base: Connection, context: Context) -> None:
	context.palette = Palette(_connect, context.clock)
	identifier, priority = _event(base, "Le débat")
	assert context.palette.answer({"event": identifier, "priority": priority}) == "#8fd19e"


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le genre « {genre} » est donné à « {name} », directement en base"))
def genre_in_base(base: Connection, genre: str, name: str) -> None:
	genre_of(base, genre, name)


@when(parsers.parse("{seconds:d} secondes passent"))
def elapse(context: Context, seconds: int) -> None:
	context.clock.now += seconds


@when("la palette apprend un enregistrement")
def forget(context: Context) -> None:
	assert context.palette is not None
	context.palette.forget()


@when("la base devient injoignable et que 30 secondes passent")
def unreachable(context: Context) -> None:
	assert context.palette is not None
	context.palette.connect = _unreachable
	context.clock.now += LIFETIME


@when(parsers.parse("le plugin des couleurs des émissions s'enregistre dans « {executable} »"))
def register(context: Context, executable: str) -> None:
	machincast_color_the_shows.register(_Plugin(executable, context.points))  # type: ignore[arg-type]


@when(parsers.re(r"la section « Genre » de « (?P<name>[^»]+) »(?P<loaded> du plugin chargé)? s'ouvre$"))
def open_section(base: Connection, context: Context, qtbot: QtBot, name: str, loaded: str | None) -> None:
	context.connection = _connect()
	if loaded is None:
		context.section = GenreSection(context.connection)
	else:
		answers = plugins.active().points.collect(
			"interface.event_card", {"connection": context.connection, "parent": None}
		)
		assert len(answers) == 1, answers
		section = answers[0][1]
		assert isinstance(section, GenreSection), section
		context.section = section
	qtbot.addWidget(context.section)
	context.section.changed.connect(lambda: context.changes.append(None))
	identifier = _event(base, name)[0]
	with context.connection.transaction():
		context.section.read(identifier)
	context.section.setProperty("event", identifier)


@when(parsers.parse("j'ouvre la fiche de l'événement « {name} »"))
def open_card(base: Connection, context: Context, qtbot: QtBot, name: str) -> None:
	context.connection = _connect()
	clock = FixedClock(datetime(2026, 11, 24, 10, tzinfo=ZoneInfo("Europe/Paris")))
	context.card = EventCard(context.connection, _event(base, name)[0], clock)
	qtbot.addWidget(context.card)
	context.card.load()
	context.card.show()


def _card(context: Context) -> EventCard:
	assert context.card is not None
	return context.card


def _card_section(context: Context) -> GenreSection:
	found = _card(context).findChild(GenreSection, "color_the_shows")
	assert isinstance(found, GenreSection)
	return found


@when(parsers.parse("je choisis le genre « {genre} » dans la fiche"))
def choose_in_card(context: Context, genre: str) -> None:
	box = _card_section(context).genre
	box.setCurrentIndex(box.findText(genre))


@when("j'enregistre la fiche de l'événement")
def save_card(context: Context) -> None:
	assert _card(context).save()


@when(parsers.parse("je choisis le genre « {genre} »"))
def choose_genre(context: Context, genre: str) -> None:
	box = _section(context).genre
	index = box.findText(genre)
	assert index >= 0, genre
	box.setCurrentIndex(index)


@when("la section s'enregistre")
def write_section(context: Context) -> None:
	section = _section(context)
	assert context.connection is not None
	with context.connection.transaction():
		section.write(int(section.property("event")))


@when(parsers.re(r"j'ouvre les réglages des couleurs(?P<how>, sans base| du plugin chargé)?$"))
def open_settings(base: Connection, context: Context, qtbot: QtBot, how: str | None) -> None:
	if how == " du plugin chargé":
		answers = plugins.active().points.collect("interface.plugin_window", {"parent": None})
		assert len(answers) == 1, answers
		window = answers[0][1]
		assert isinstance(window, ColoursSettings), window
		context.window = window
	else:
		connect = _connect
		if how is not None:
			connect = _unreachable
		context.window = ColoursSettings(None, None, connect)
	qtbot.addWidget(context.window)


@when(parsers.re(r"j'ajoute le genre « ?(?P<name>[^»]*?) ?», « (?P<colour>[^»]*) »"))
def add_genre(context: Context, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, name: str, colour: str) -> None:
	"""Le genre ajouté, son nom écrit, sa couleur choisie dans le sélecteur."""
	window = _window(context)
	window.commands["add"].click()
	row = window.table.currentRow()
	named = window.table.item(row, NAME_COLUMN)
	assert named is not None
	named.setText(name)
	_click_colour(qtbot, monkeypatch, window, row, colour)


def _click_colour(
	qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, window: ColoursSettings, row: int, colour: str | None
) -> None:
	"""Un clic sur la cellule de la couleur, et ce que le sélecteur rend : None s'il est abandonné."""
	asked: list[str] = []

	def chosen(_parent: object, current: str) -> str | None:
		asked.append(current)
		return colour

	monkeypatch.setattr(settings, "choose_colour", chosen)
	window.show()
	qtbot.waitExposed(window)
	item = window.table.item(row, COLOUR_COLUMN)
	assert item is not None
	place = window.table.visualItemRect(item).center()
	qtbot.mouseClick(window.table.viewport(), Qt.MouseButton.LeftButton, pos=place)
	assert len(asked) == 1, asked


@when(parsers.parse("j'écris « {colour} » pour « {label} »"))
def write_priority(context: Context, colour: str, label: str) -> None:
	_window(context).priorities[FIELDS[label]].setText(colour)


@when("j'enregistre les couleurs")
def save(context: Context) -> None:
	_window(context).commands["save"].click()


def _row(window: ColoursSettings, name: str) -> int:
	for row in range(window.table.rowCount()):
		item = window.table.item(row, NAME_COLUMN)
		if (item is not None) and (item.text() == name):
			return row
	raise AssertionError(name)


@when(parsers.parse("je choisis la ligne « {name} »"))
def choose_row(context: Context, name: str) -> None:
	window = _window(context)
	window.table.setCurrentCell(_row(window, name), NAME_COLUMN)


@when(
	parsers.re(
		r"je clique sur la couleur de « (?P<name>[^»]+) », et (?:choisis « (?P<colour>[^»]+) » dans le|abandonne le) sélecteur$"
	)
)
def click_colour(
	context: Context, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, name: str, colour: str | None
) -> None:
	window = _window(context)
	_click_colour(qtbot, monkeypatch, window, _row(window, name), colour)


@when(parsers.parse("j'appuie sur Entrée sur la couleur de « {name} », et choisis « {colour} » dans le sélecteur"))
def enter_colour(context: Context, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, name: str, colour: str) -> None:
	window = _window(context)
	monkeypatch.setattr(settings, "choose_colour", lambda _parent, _current: colour)
	window.table.setCurrentCell(_row(window, name), COLOUR_COLUMN)
	qtbot.keyClick(window.table, Qt.Key.Key_Return)


@when(parsers.parse("je renomme « {first} » en « {second} », et « {other} » en « {last} »"))
def swap(context: Context, first: str, second: str, other: str, last: str) -> None:
	window = _window(context)
	first_item = window.table.item(_row(window, first), NAME_COLUMN)
	other_item = window.table.item(_row(window, other), NAME_COLUMN)
	assert (first_item is not None) and (other_item is not None)
	first_item.setText(second)
	other_item.setText(last)


@when(parsers.parse("j'appuie sur « {label} »"))
def press(context: Context, label: str) -> None:
	for button in _window(context).commands.values():
		if button.text() == label:
			assert button.isEnabled(), label
			button.click()
			return
	raise AssertionError(label)


# ─── Alors ─────────────────────────────────────────────────


@then("les genres sont :")
def stored_genres(base: Connection, datatable: list[list[str]]) -> None:
	expected = []
	for name, colour in datatable[1:]:
		expected.append([name.strip(), colour.strip()])
	assert _genres(base) == expected


@then("les genres sont toujours les quatre de l'installation")
def default_genres(base: Connection) -> None:
	assert _genres(base) == [["jazz", "#5b8def"], ["metal", "#3d3d3d"], ["reggae", "#e07b39"], ["talk", "#f2c14e"]]


@then("les couleurs des priorités sont :")
def stored_priorities(base: Connection, datatable: list[list[str]]) -> None:
	expected = {}
	for priority, colour in datatable[1:]:
		expected[priority.strip()] = colour.strip()
	assert queries.priorities(base) == expected


@then(parsers.parse("la couleur de la priorité « {priority} » est « {colour} »"))
def priority_colour(base: Connection, priority: str, colour: str) -> None:
	assert queries.priorities(base)[priority] == colour


@then(parsers.parse("le genre « {name} » est « {colour} »"))
def genre_colour(base: Connection, name: str, colour: str) -> None:
	assert [name, colour] in _genres(base), _genres(base)


@given(parsers.parse("la couleur de « {name} » est « {colour} »"))
@then(parsers.parse("la couleur de « {name} » est « {colour} »"))
def colour_of(base: Connection, name: str, colour: str) -> None:
	identifier, priority = _event(base, name)
	assert event_colour(identifier, priority) == colour


@then(parsers.parse("« {first} » et « {second} » gardent la couleur du cœur"))
def core_colour(base: Connection, first: str, second: str) -> None:
	for name in (first, second):
		identifier, priority = _event(base, name)
		assert event_colour(identifier, priority) is None, name


@then(parsers.parse("le bloc de « {name} » du calendrier est « {colour} », son nom en noir à l'antenne"))
def block(base: Connection, name: str, colour: str) -> None:
	identifier, priority = _event(base, name)
	event = SimpleNamespace(id=identifier, priority=Priority(priority))
	found = calendar.block_colour(event)  # type: ignore[arg-type]
	assert found.name() == colour
	assert calendar.name_colour(found, on_air=True).name() == "#000000"


@then(parsers.parse("sans sa priorité, la couleur de « {name} » est « {colour} »"))
def airplay_colour(base: Connection, name: str, colour: str) -> None:
	assert event_colour(_event(base, name)[0], None) == colour


@then(parsers.parse("sans sa priorité, « {name} » n'a pas de couleur"))
def airplay_none(base: Connection, name: str) -> None:
	assert event_colour(_event(base, name)[0], None) is None


@then(parsers.re(r"la palette donne (?:encore )?« (?P<colour>[^»]+) » à « (?P<name>[^»]+) »"))
def palette_gives(base: Connection, context: Context, colour: str, name: str) -> None:
	assert context.palette is not None
	identifier, priority = _event(base, name)
	assert context.palette.answer({"event": identifier, "priority": priority}) == colour


@then(parsers.parse("il s'abonne seulement à {points}"))
def subscribed(context: Context, points: str) -> None:
	assert context.points == _names(points)


@then(parsers.parse("elle propose {names}"))
def proposed(context: Context, names: str) -> None:
	box = _section(context).genre
	found = []
	for index in range(box.count()):
		found.append(box.itemText(index))
	assert found == _names(names)


@then(parsers.parse("elle montre « {genre} »"))
def shows(context: Context, genre: str) -> None:
	assert _section(context).genre.currentText() == genre


@then(parsers.parse("« {genre} » a un carré « {colour} »"))
def square(context: Context, genre: str, colour: str) -> None:
	box = _section(context).genre
	icon = box.itemIcon(box.findText(genre))
	picture = icon.pixmap(SWATCH, SWATCH).toImage()
	assert picture.pixelColor(SWATCH // 2, SWATCH // 2).name() == colour


@then(parsers.parse("la ligne sous « {caption} » est « {genre_caption} », qui montre « {genre} »"))
def row_under(context: Context, caption: str, genre_caption: str, genre: str) -> None:
	card = _card(context)
	section = _card_section(context)
	form = card.ui.form
	above = form.labelForField(card.ui.stream_fallback)
	assert isinstance(above, QLabel)
	assert above.text().replace("&", "") == caption
	row = field_row(form, card.ui.stream_fallback) + 1
	assert field_row(form, section.genre) == row
	assert form.labelForField(section.genre) is section.caption
	assert section.caption.text().replace("&", "") == genre_caption
	assert section.genre.currentText() == genre
	assert section.genre.isVisible()


@then("la section du plugin est cachée : la liste de lecture n'est pas décalée")
def section_hidden(context: Context) -> None:
	card = _card(context)
	section = _card_section(context)
	assert section.isHidden()
	assert card.ui.lists.indexOf(section) == 0


@then("la fiche de l'événement est modifiée")
def card_modified(context: Context) -> None:
	assert _card(context).modified


@then("la fiche est modifiée")
def modified(context: Context) -> None:
	assert context.changes != []


@then(parsers.parse("les propriétés de « {name} » ont « {key} », et le genre « {genre} »"))
def kept_properties(base: Connection, name: str, key: str, genre: str) -> None:
	found = base.execute("SELECT properties FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert found is not None
	stored = found[0]
	assert isinstance(stored, dict), stored
	assert key in stored, stored
	assert stored["color_the_shows"] == {"genre": _genre(base, genre)}, stored


@then(parsers.parse("les propriétés de « {name} » sont {expected}"))
def all_properties(base: Connection, name: str, expected: str) -> None:
	found = base.execute("SELECT properties FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert found is not None
	assert found[0] == json.loads(expected)


@then(parsers.parse("« {name} » a toujours le genre « {genre} »"))
def still_genre(base: Connection, name: str, genre: str) -> None:
	assert queries.event_genre(base, _event(base, name)[0]) == _genre(base, genre)


@then(parsers.parse("le tableau des genres est {rows}"))
def table(context: Context, rows: str) -> None:
	window = _window(context)
	found = []
	for row in range(window.table.rowCount()):
		named = window.table.item(row, NAME_COLUMN)
		coloured = window.table.item(row, COLOUR_COLUMN)
		assert (named is not None) and (coloured is not None)
		found.append(f"{named.text()} {coloured.text()}")
	assert found == _names(rows)


@then(parsers.parse("la cellule de « {name} » est sur « {colour} », en texte blanc"))
def cell(context: Context, name: str, colour: str) -> None:
	window = _window(context)
	item = window.table.item(_row(window, name), COLOUR_COLUMN)
	assert item is not None
	assert item.background().color().name() == colour
	assert item.foreground().color().name() == "#ffffff"


@then(parsers.parse("seule la cellule du nom de « {name} » s'écrit"))
def editable(context: Context, name: str) -> None:
	window = _window(context)
	row = _row(window, name)
	named = window.table.item(row, NAME_COLUMN)
	coloured = window.table.item(row, COLOUR_COLUMN)
	assert (named is not None) and (coloured is not None)
	assert named.flags() & Qt.ItemFlag.ItemIsEditable
	assert not coloured.flags() & Qt.ItemFlag.ItemIsEditable


@then(parsers.parse("la couleur « {label} » est « {colour} »"))
def field_colour(context: Context, label: str, colour: str) -> None:
	assert _window(context).priorities[FIELDS[label]].text() == colour


@then(parsers.re(r"le message dit(?P<partly>, entre autres,)? « (?P<text>.+) »$"))
def message(context: Context, partly: str | None, text: str) -> None:
	shown = _window(context).message.text()
	if partly is None:
		assert shown == text
	else:
		assert text in shown, shown
