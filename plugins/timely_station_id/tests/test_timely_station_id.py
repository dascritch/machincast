"""Scénarios du station ID régulier (https://github.com/dascritch/machincast/issues/460).

La diffusion est déroulée sonore après sonore par l'ordonnanceur de Machin player, au rôle de la lecture, sur la base de
test ; chaque passage est noté dans l'airplay, comme le fait le binaire. Le plugin s'abonne aux points des plugins du
binaire (machincast.plugins.active), que tests/conftest.py remet à vide après chaque scénario. La fiche de l'événement
s'ouvre seule, au rôle machincast_interface.
"""

import dataclasses
import json
import logging
import re
import tomllib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import machincast_timely_station_id
import psycopg
import pytest
from machincast_timely_station_id import settings as settings_window
from machincast_timely_station_id.rule import Settings, due, read_settings
from machincast_timely_station_id.section import RegularSection, field_row
from machincast_timely_station_id.settings import StationSettings
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot
from tests.database_fixtures import configuration_test, sample_database_parameters

from conftest import PLUGIN
from machincast import plugins
from machincast.clock import FixedClock
from machincast.database import Role, open_connection
from machincast.interface.event_card import EventCard
from machincast.player.rundown import INSERTED, OUTSIDE_LIST, Scheduler
from machincast.randomness import create_randomness

scenarios(str(PLUGIN / "tests" / "features" / "timely_station_id.feature"))

Connection = psycopg.Connection[tuple[object, ...]]
START = datetime(2026, 10, 14, 20, tzinfo=ZoneInfo("Europe/Paris"))
NAME = re.compile(r"« ([^»]*) »")
ONE_MINUTE = timedelta(minutes=1)


@dataclass
class Context:
	settings: dict[str, Any] = field(default_factory=dict)
	played: list[str] = field(default_factory=list)
	points: list[str] = field(default_factory=list)
	connection: Connection | None = None
	card: EventCard | None = None
	window: StationSettings | None = None
	path: Path | None = None


@pytest.fixture
def context(qtbot: QtBot) -> Iterator[Context]:
	found = Context()
	yield found
	if found.card is not None:
		found.card.close()
	if found.window is not None:
		found.window.close()
	if found.connection is not None:
		found.connection.close()


CONFIGURATION = """# Le poste de l'antenne
[plugins]
enabled = ["timely_station_id"]

[dead_air]
duration = 10
"""
"""Le fichier de configuration des scénarios : sa section du plugin s'y écrit, le reste doit y rester."""


@pytest.fixture
def configuration_file(context: Context, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
	"""Un fichier de configuration à part, jamais celui du dépôt ; la fenêtre lit les banques de la base de test."""
	context.path = tmp_path / "machincast.toml"
	context.path.write_text(CONFIGURATION, encoding="utf-8")

	def opened(_socket: object, _database: object, role: Role) -> Connection:
		return open_connection(*sample_database_parameters(), role)

	monkeypatch.setattr(settings_window, "open_connection", opened)
	return context.path


class _Plugin:
	"""Un plugin chargé, abonné aux points du binaire, ou qui note seulement ses abonnements."""

	def __init__(
		self, executable: str, settings: dict[str, Any], noted: list[str] | None = None, path: Path | None = None
	) -> None:
		configuration = configuration_test()
		if path is not None:
			configuration = dataclasses.replace(configuration, path=path)
		self.context = SimpleNamespace(executable=executable, settings=settings, configuration=configuration)
		self.noted = noted

	def on(self, point: str, function: Any) -> None:
		if self.noted is not None:
			self.noted.append(point)
			return
		plugins.active().points.subscribe("timely_station_id", point, function)


def _sound(database: Connection, name: str, minutes: int = 1) -> int:
	location = f"/sons/{name}.flac"
	line = database.execute("SELECT id FROM sounds WHERE location = %s", (location,)).fetchone()
	if line is None:
		line = database.execute(
			"INSERT INTO sounds (type, location, state, duration) VALUES ('file', %s, 'active', %s) RETURNING id",
			(location, timedelta(minutes=minutes)),
		).fetchone()
	assert line is not None
	return int(str(line[0]))


def _event(database: Connection, name: str) -> int:
	line = database.execute("SELECT id FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert line is not None, name
	return int(str(line[0]))


def _card(context: Context) -> EventCard:
	assert context.card is not None
	return context.card


def _section(context: Context) -> RegularSection:
	found = _card(context).findChild(RegularSection, "timely_station_id")
	assert isinstance(found, RegularSection)
	return found


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.re(r"une banque « (?P<name>[^»]+) » contenant (?P<sounds>.+)$"))
def bank(empty_database: Connection, name: str, sounds: str) -> None:
	line = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (name,)
	).fetchone()
	assert line is not None
	for position, sound_name in enumerate(NAME.findall(sounds), start=1):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
			(line[0], _sound(empty_database, sound_name), position),
		)


@given(parsers.parse("les morceaux, en minutes : {songs}"))
def songs(empty_database: Connection, songs: str) -> None:
	for name, minutes in re.findall(r"« ([^»]+) » (\d+)", songs):
		_sound(empty_database, name, int(minutes))


@given(
	parsers.re(
		r"les réglages : minimum (?P<minimum>\d+), maximum (?P<maximum>\d+), placement « (?P<placement>[^»]+) »"
		r"(?:, banques surveillées « (?P<watched>[^»]+) »)?(?:, banque « (?P<bank>[^»]+) »)?$"
	)
)
def settings(
	context: Context, minimum: str, maximum: str, placement: str, watched: str | None, bank: str | None
) -> None:
	context.settings = {
		"bank": (bank) or ("Station ID"),
		"minimum": int(minimum),
		"maximum": int(maximum),
		"placement": placement,
	}
	if watched is not None:
		context.settings["watched"] = [watched]


@given(parsers.re(r"le fil musical « (?P<name>[^»]+) », (?P<state>coché|pas coché), jouant (?P<sounds>.+)$"))
def background(empty_database: Connection, name: str, state: str, sounds: str) -> None:
	properties = {}
	if state == "coché":
		properties["timely_station_id"] = True
	line = empty_database.execute(
		"INSERT INTO events (internal_name, priority, properties) VALUES (%s, 'background_programming', %s::jsonb)"
		" RETURNING id",
		(name, json.dumps(properties)),
	).fetchone()
	assert line is not None
	for position, sound_name in enumerate(NAME.findall(sounds), start=1):
		empty_database.execute(
			"INSERT INTO event_items (event_id, position, sound_id) VALUES (%s, %s, %s)",
			(line[0], position, _sound(empty_database, sound_name)),
		)


@given("aucun réglage")
def no_settings(context: Context) -> None:
	context.settings = {}


@given(parsers.parse("le plugin du station ID régulier, chargé dans « {executable} »"))
def loaded(context: Context, configuration_file: Path, executable: str) -> None:
	plugin = _Plugin(executable, context.settings, path=configuration_file)
	machincast_timely_station_id.register(plugin)  # type: ignore[arg-type]


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("la diffusion se déroule pendant {minutes:d} minutes"))
def unroll(context: Context, empty_database: Connection, minutes: int) -> None:
	"""Chaque sonore va jusqu'au bout ; le suivant est décidé à sa fin."""
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as playback:
		scheduler = Scheduler(playback, create_randomness(0))
		instant = START
		while instant < START + timedelta(minutes=minutes):
			decision = scheduler.decide(instant, None)
			choice = decision.play
			if choice is None:
				break
			item = choice.item.id
			if item in (OUTSIDE_LIST, INSERTED):
				item = None
			empty_database.execute(
				"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, bank_id, event_id, event_item_id)"
				" VALUES (%s, 'start', %s, %s, %s, %s, %s)",
				(uuid.uuid4(), instant, choice.sound, choice.bank, choice.occurrence.event.id, item),
			)
			line = empty_database.execute(
				"SELECT location, duration FROM sounds WHERE id = %s", (choice.sound,)
			).fetchone()
			assert line is not None
			name = str(line[0]).removeprefix("/sons/").removesuffix(".flac")
			context.played.append(f"{int((instant - START).total_seconds() // 60)} {name}")
			assert isinstance(line[1], timedelta)
			instant += line[1]


@when(parsers.parse("le plugin du station ID régulier s'enregistre dans « {executable} »"))
def register(context: Context, executable: str) -> None:
	machincast_timely_station_id.register(_Plugin(executable, context.settings, context.points))  # type: ignore[arg-type]


@when(parsers.parse("j'ouvre la fiche de l'événement « {name} »"))
def open_card(empty_database: Connection, context: Context, qtbot: QtBot, name: str) -> None:
	context.connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	clock = FixedClock(START)
	context.card = EventCard(context.connection, _event(empty_database, name), clock)
	qtbot.addWidget(context.card)
	context.card.load()
	context.card.show()


@when(parsers.re(r"je (?P<action>coche|décoche) « Station ID régulier »"))
def tick(context: Context, action: str) -> None:
	_section(context).regular.setChecked(action == "coche")


def _window(context: Context) -> StationSettings:
	assert context.window is not None
	return context.window


@when("j'ouvre la fenêtre du plugin")
def open_window(context: Context, qtbot: QtBot) -> None:
	answers = plugins.active().points.collect_from("timely_station_id", "interface.plugin_window", {"parent": None})
	assert len(answers) == 1, answers
	window = answers[0]
	assert isinstance(window, StationSettings), window
	context.window = window
	qtbot.addWidget(window)


@when(
	parsers.re(
		r"je choisis la banque « (?P<bank>[^»]+) », surveille « (?P<watched>[^»]+) », de (?P<minimum>\d+) à"
		r" (?P<maximum>\d+) minutes, placement « (?P<placement>[^»]+) »$"
	)
)
def choose(context: Context, bank: str, watched: str, minimum: str, maximum: str, placement: str) -> None:
	window = _window(context)
	window.bank.setCurrentIndex(window.bank.findText(bank))
	for row in range(window.watched.count()):
		item = window.watched.item(row)
		if item.text() == watched:
			item.setCheckState(Qt.CheckState.Checked)
	gap(context, minimum, maximum)
	window.placement.setCurrentIndex(window.placement.findText(placement))


@when(parsers.parse("je règle l'écart de {minimum} à {maximum} minutes"))
def gap(context: Context, minimum: str, maximum: str) -> None:
	window = _window(context)
	window.minimum.setValue(int(minimum))
	window.maximum.setValue(int(maximum))


@when("j'enregistre les réglages du plugin")
def save_window(context: Context) -> None:
	_window(context).save_button.click()


@when("j'enregistre la fiche de l'événement")
def save_card(context: Context) -> None:
	assert _card(context).save()


# ─── Alors ─────────────────────────────────────────────────


@then(
	parsers.re(
		r"depuis le dernier station ID (?P<gap>inconnu|\d+ minutes), un morceau de (?P<length>\d+ minutes|stream)"
		r" (?P<decision>passe tel quel|passe après un station ID)$"
	)
)
def rule(context: Context, gap: str, length: str, decision: str) -> None:
	found = read_settings(context.settings)
	assert isinstance(found, Settings), found
	elapsed = None
	if gap != "inconnu":
		elapsed = timedelta(minutes=int(gap.split()[0]))
	duration = None
	if length != "stream":
		duration = timedelta(minutes=int(length.split()[0]))
	assert due(found, elapsed, duration) == (decision == "passe après un station ID")


@then(parsers.re(r"les réglages (?P<written>.+) sont refusés : « (?P<reason>.+) »$"))
def refused(written: str, reason: str) -> None:
	section: dict[str, Any] = {"bank": "Station ID", "minimum": 12, "maximum": 18}
	if written == "sans banque":
		del section["bank"]
	found = re.fullmatch(r"minimum (\d+), maximum (\d+)", written)
	if found is not None:
		section["minimum"] = int(found.group(1))
		section["maximum"] = int(found.group(2))
	placement = re.fullmatch(r"placement « ([^»]+) »", written)
	if placement is not None:
		section["placement"] = placement.group(1)
	if written == "watched « Saison » sans liste":
		section["watched"] = "Saison"
	assert read_settings(section) == reason


@then(parsers.parse("la diffusion a été {plays}"))
def broadcast(context: Context, plays: str) -> None:
	assert context.played == NAME.findall(plays)


@then(parsers.re(r"le journal dit (?P<once>une fois )?« (?P<text>.+) »$"))
def journal(caplog: pytest.LogCaptureFixture, once: str | None, text: str) -> None:
	found = []
	for record in caplog.records:
		if (record.levelno >= logging.WARNING) and (record.getMessage() == text):
			found.append(record)
	if once is None:
		assert found != [], caplog.records
	else:
		assert len(found) == 1, caplog.records


@then("il ne s'abonne à aucun point")
def nothing(context: Context) -> None:
	assert context.points == []


@then(parsers.parse("la banque des station ID est « {bank} », parmi {banks}"))
def bank_shown(context: Context, bank: str, banks: str) -> None:
	window = _window(context)
	found = []
	for index in range(window.bank.count()):
		found.append(window.bank.itemText(index))
	assert (window.bank.currentText(), found) == (bank, NAME.findall(banks))


@then(parsers.parse("les banques surveillées cochées sont {banks}"))
def watched_shown(context: Context, banks: str) -> None:
	window = _window(context)
	found = []
	for row in range(window.watched.count()):
		item = window.watched.item(row)
		if item.checkState() == Qt.CheckState.Checked:
			found.append(item.text())
	assert found == NAME.findall(banks)


@then(parsers.parse("l'écart va de {minimum:d} à {maximum:d} minutes, placement « {placement} »"))
def gap_shown(context: Context, minimum: int, maximum: int, placement: str) -> None:
	window = _window(context)
	assert (window.minimum.value(), window.maximum.value()) == (minimum, maximum)
	assert window.placement.currentText() == placement


@then(parsers.parse("le message de la fenêtre dit « {text} »"))
def window_message(context: Context, text: str) -> None:
	assert _window(context).message.text() == text


@then("le fichier de configuration est inchangé")
def unchanged(context: Context) -> None:
	assert context.path is not None
	assert context.path.read_text(encoding="utf-8") == CONFIGURATION


@then("le fichier de configuration a gardé son commentaire et ses autres sections")
def kept(context: Context) -> None:
	assert context.path is not None
	written = context.path.read_text(encoding="utf-8")
	assert written.startswith('# Le poste de l\'antenne\n[plugins]\nenabled = ["timely_station_id"]\n'), written
	assert "[dead_air]\nduration = 10\n" in written, written


@then(
	parsers.re(
		r"sa section \[plugins.timely_station_id\] est bank « (?P<bank>[^»]+) », watched « (?P<watched>[^»]+) »,"
		r" minimum (?P<minimum>\d+), maximum (?P<maximum>\d+), placement « (?P<placement>[^»]+) »$"
	)
)
def section_written(context: Context, bank: str, watched: str, minimum: str, maximum: str, placement: str) -> None:
	assert context.path is not None
	written = tomllib.loads(context.path.read_text(encoding="utf-8"))
	assert written["plugins"]["timely_station_id"] == {
		"bank": bank,
		"watched": [watched],
		"minimum": int(minimum),
		"maximum": int(maximum),
		"placement": placement,
	}


@then(parsers.parse("l'infobulle de la case de la fiche dit aussitôt « {text} »"))
def tooltip_now(context: Context, empty_database: Connection, qtbot: QtBot, text: str) -> None:
	context.connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	answers = plugins.active().points.collect(
		"interface.event_card", {"connection": context.connection, "parent": None}
	)
	assert len(answers) == 1, answers
	section = answers[0][1]
	assert isinstance(section, RegularSection)
	qtbot.addWidget(section)
	assert section.regular.toolTip() == text


@then(parsers.parse("il s'abonne seulement à {points}"))
def subscribed(context: Context, points: str) -> None:
	assert context.points == NAME.findall(points)


@then(parsers.parse("la ligne sous « {caption} » est la case « {text} », pas cochée"))
def row_under(context: Context, caption: str, text: str) -> None:
	card = _card(context)
	section = _section(context)
	form = card.ui.form
	above = form.labelForField(card.ui.stream_fallback)
	assert isinstance(above, QLabel)
	assert above.text().replace("&", "") == caption
	assert field_row(form, section.regular) == field_row(form, card.ui.stream_fallback) + 1
	assert section.regular.text() == text
	assert not section.regular.isChecked()
	assert section.regular.isVisible()


@then(parsers.parse("son infobulle dit « {text} »"))
def tooltip(context: Context, text: str) -> None:
	assert _section(context).regular.toolTip() == text


@then("la section du plugin est cachée : la liste de lecture n'est pas décalée")
def hidden(context: Context) -> None:
	section = _section(context)
	assert section.isHidden()
	assert _card(context).ui.lists.indexOf(section) == 0


@then("la fiche de l'événement est modifiée")
def modified(context: Context) -> None:
	assert _card(context).modified


@then(parsers.parse("les propriétés de « {name} » sont {expected}"))
def properties(empty_database: Connection, name: str, expected: str) -> None:
	line = empty_database.execute("SELECT properties FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert line is not None
	assert line[0] == json.loads(expected)
