"""Scénarios de la normalisation du niveau (https://github.com/dascritch/machincast/issues/43).

Les sonores sont en base de test. La diffusion joue au plus vite sur la sortie factice, avec les étapes de
tests/broadcast_steps.py ; le plugin s'abonne à ses points (Bench.points). Machin indexer et la fiche se connectent à la
base de test, jamais à celle de production ; la fenêtre écrit dans un fichier de configuration du scénario.
"""

import dataclasses
import json
import logging
import re
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import machincast_loudness_normalization
import psycopg
import pytest
from machincast_loudness_normalization.bank_section import BankLevelSection
from machincast_loudness_normalization.gain import sound_gain
from machincast_loudness_normalization.rule import Current, Measure, Settings, applied, read_settings
from machincast_loudness_normalization.section import GROUP, LevelSection
from machincast_loudness_normalization.settings import LevelSettings
from machincast_loudness_normalization.slider import LevelSlider
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QBoxLayout, QGroupBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot
from tests.broadcast_steps import Bench, sound
from tests.database_fixtures import configuration_test, sample_database_parameters

from conftest import PLUGIN
from machincast import plugins
from machincast.clock import FixedClock
from machincast.database import Role, open_connection
from machincast.interface import expandable
from machincast.interface.sound_card import SoundCard
from machincast.plugins.points import Points

scenarios(str(PLUGIN / "tests" / "features" / "loudness_normalization.feature"))

Connection = psycopg.Connection[tuple[object, ...]]
NAME = re.compile(r"« ([^»]*) »")
CONFIGURATION = """# Le poste de l'antenne
[plugins]
enabled = ["loudness_normalization"]

[dead_air]
duration = 10
"""


@dataclass
class Context:
	settings: dict[str, Any] = field(default_factory=dict)
	points: list[str] = field(default_factory=list)
	sound: int | None = None
	location: str = ""
	connection: Connection | None = None
	section: LevelSection | None = None
	changes: list[None] = field(default_factory=list)
	window: LevelSettings | None = None
	path: Path | None = None
	card: SoundCard | None = None
	bank: int | None = None
	bank_section: BankLevelSection | None = None


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


class _Plugin:
	"""Un plugin chargé, abonné aux points donnés, ou qui note seulement ses abonnements."""

	def __init__(
		self,
		executable: str,
		settings: dict[str, Any],
		points: Points | None = None,
		noted: list[str] | None = None,
		path: Path | None = None,
	) -> None:
		configuration = configuration_test()
		if path is not None:
			configuration = dataclasses.replace(configuration, path=path)
		self.context = SimpleNamespace(executable=executable, settings=settings, configuration=configuration)
		self.points = (points) or (plugins.active().points)
		self.noted = noted

	def on(self, point: str, function: Any) -> None:
		if self.noted is not None:
			self.noted.append(point)
			return
		self.points.subscribe("loudness_normalization", point, function)


def _register(plugin: _Plugin) -> None:
	machincast_loudness_normalization.register(plugin)  # type: ignore[arg-type]


def _decibels(text: str) -> float | None:
	if text.strip() == "inconnue":
		return None
	return float(text.strip().replace(",", "."))


@pytest.fixture
def test_database(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Les connexions du plugin vont à la base de test, au rôle demandé : jamais à la base de production."""

	def opened(_socket: object, _database: object, role: Role) -> Connection:
		return open_connection(*sample_database_parameters(), role)

	monkeypatch.setattr(machincast_loudness_normalization, "open_connection", opened)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.re(r"les réglages : cible (?P<target>-?\d+) LUFS, plafond (?P<ceiling>-?\d+) dBFS"))
def settings(context: Context, target: str, ceiling: str) -> None:
	context.settings = {"target": int(target), "ceiling": int(ceiling)}


@given(parsers.parse("les propriétés du sonore « {name} » {properties}"))
def sound_properties(empty_database: Connection, name: str, properties: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET properties = %s::jsonb WHERE id = %s", (properties, sound(empty_database, name))
	)


@given(parsers.parse("le sonore « {location} », de propriétés {properties}"))
def stored_sound(empty_database: Connection, context: Context, location: str, properties: str) -> None:
	line = empty_database.execute(
		"INSERT INTO sounds (type, location, state, properties) VALUES ('file', %s, 'active', %s::jsonb) RETURNING id",
		(location, properties),
	).fetchone()
	assert line is not None
	context.sound = int(str(line[0]))
	context.location = location


@given(parsers.parse("les propriétés de la banque « {name} » {properties}"))
def bank_properties(empty_database: Connection, name: str, properties: str) -> None:
	empty_database.execute("UPDATE banks SET properties = %s::jsonb WHERE internal_name = %s", (properties, name))


@given(
	parsers.re(
		r"la banque « (?P<name>[^»]+) », de propriétés (?P<properties>\{.*\})(?P<holds>, qui contient ce sonore)?$"
	)
)
def stored_bank(empty_database: Connection, context: Context, name: str, properties: str, holds: str | None) -> None:
	line = empty_database.execute(
		"INSERT INTO banks (internal_name, mode, properties) VALUES (%s, 'sequential', %s::jsonb) RETURNING id",
		(name, properties),
	).fetchone()
	assert line is not None
	context.bank = int(str(line[0]))
	if holds is not None:
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, 1)", (context.bank, context.sound)
		)


@given(parsers.parse("le stream « {name} »"))
def stream(empty_database: Connection, context: Context, name: str) -> None:
	line = empty_database.execute(
		"INSERT INTO sounds (type, title, stream_url, state) VALUES ('stream', %s, 'https://flux.exemple/direct',"
		" 'active') RETURNING id",
		(name,),
	).fetchone()
	assert line is not None
	context.sound = int(str(line[0]))


@given("le plugin de la normalisation du niveau, chargé dans Machin player")
def loaded_in_player(bench: Bench, context: Context) -> None:
	if bench.points is None:
		bench.points = Points()
	_register(_Plugin("Machin_player", context.settings, bench.points))


@given("le plugin de la normalisation du niveau, chargé dans Machin indexer")
def loaded_in_indexer(context: Context, test_database: None) -> None:
	_register(_Plugin("Machin_indexer", context.settings))


@given("le plugin de la normalisation du niveau, chargé dans Machin interface")
def loaded_in_interface(context: Context, tmp_path: Path) -> None:
	context.path = tmp_path / "machincast.toml"
	context.path.write_text(CONFIGURATION, encoding="utf-8")
	_register(_Plugin("Machin_interface", context.settings, path=context.path))


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le plugin de la normalisation du niveau s'enregistre dans « {executable} »"))
def register(context: Context, executable: str) -> None:
	_register(_Plugin(executable, context.settings, noted=context.points))


@when("l'audit complet de Machin indexer le mesure")
def detailed(empty_database: Connection, context: Context) -> None:
	"""Ce que Machin indexer notifie aux plugins une fois le sonore audité, sa mesure comprise."""
	assert context.sound is not None
	line = empty_database.execute("SELECT properties FROM sounds WHERE id = %s", (context.sound,)).fetchone()
	assert line is not None
	assert isinstance(line[0], dict)
	data = {"sound": context.sound, "location": context.location, "audited": True, "loudness": line[0]["loudness"]}
	plugins.active().points.collect("indexer.sound_detailed", data)


@when("j'ouvre la fiche de ce sonore")
def open_card(context: Context, qtbot: QtBot) -> None:
	context.connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	context.card = SoundCard(context.connection, context.sound, FixedClock(datetime(2026, 10, 14, 20, tzinfo=UTC)))
	qtbot.addWidget(context.card)
	context.card.load()
	context.card.show()
	qtbot.waitExposed(context.card)


@when("la section « Niveau » de cette banque s'ouvre")
def open_bank_section(context: Context, qtbot: QtBot) -> None:
	found = read_settings(context.settings)
	assert isinstance(found, Settings)
	context.connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	context.bank_section = BankLevelSection(context.connection, Current(found))
	qtbot.addWidget(context.bank_section)
	context.bank_section.changed.connect(lambda: context.changes.append(None))
	with context.connection.transaction():
		context.bank_section.read(context.bank)


def _bank_section(context: Context) -> BankLevelSection:
	assert context.bank_section is not None
	return context.bank_section


@when(parsers.re(r"je coche « Sonie visée propre à la banque » et règle son curseur à (?P<value>-?\d+) LUFS"))
def tick_target(context: Context, value: str) -> None:
	section = _bank_section(context)
	section.has_target.setChecked(True)
	section.target.setValue(float(value))


@when("je décoche « Sonie visée propre à la banque »")
def untick_target(context: Context) -> None:
	_bank_section(context).has_target.setChecked(False)


@when("la section de la banque s'enregistre")
def write_bank_section(context: Context) -> None:
	assert (context.connection is not None) and (context.bank is not None)
	with context.connection.transaction():
		_bank_section(context).write(context.bank)


@when("la section « Niveau » de ce sonore s'ouvre")
def open_section(empty_database: Connection, context: Context, qtbot: QtBot) -> None:
	found = read_settings(context.settings)
	assert isinstance(found, Settings)
	context.connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	context.section = LevelSection(context.connection, Current(found))
	qtbot.addWidget(context.section)
	context.section.changed.connect(lambda: context.changes.append(None))
	with context.connection.transaction():
		context.section.read(context.sound)


def _section(context: Context) -> LevelSection:
	assert context.section is not None
	return context.section


@when(parsers.re(r"je coche l'ajustement manuel et règle son curseur à (?P<gain>-?[\d,]+) dB"))
def adjust(context: Context, gain: str) -> None:
	value = _decibels(gain)
	assert value is not None
	section = _section(context)
	section.has_adjustment.setChecked(True)
	section.adjustment.setValue(value)


@when("je décoche l'ajustement manuel")
def no_adjustment(context: Context) -> None:
	_section(context).has_adjustment.setChecked(False)


@when("la section s'enregistre")
def write_section(context: Context) -> None:
	assert (context.connection is not None) and (context.sound is not None)
	with context.connection.transaction():
		_section(context).write(context.sound)


def _window(context: Context) -> LevelSettings:
	assert context.window is not None
	return context.window


@when("j'ouvre la fenêtre du plugin")
def open_window(context: Context, qtbot: QtBot) -> None:
	answers = plugins.active().points.collect_from(
		"loudness_normalization", "interface.plugin_window", {"parent": None}
	)
	assert len(answers) == 1, answers
	window = answers[0]
	assert isinstance(window, LevelSettings), window
	context.window = window
	qtbot.addWidget(window)


@when(parsers.re(r"je règle la sonie visée à (?P<target>-?\d+) LUFS et le plafond à (?P<ceiling>-?\d+) dBFS"))
def set_window(context: Context, target: str, ceiling: str) -> None:
	window = _window(context)
	window.target.setValue(float(target))
	window.ceiling.setValue(float(ceiling))


@when("j'enregistre les réglages du plugin")
def save_window(context: Context) -> None:
	_window(context).save_button.click()


# ─── Alors ─────────────────────────────────────────────────


@then(
	parsers.re(
		r"un sonore de sonie (?P<integrated>\S+), de crête (?P<peak>\S+), ajusté de (?P<manual>\S+) dB,"
		r" reçoit un gain de (?P<gain>\S+) dB"
	)
)
def rule(context: Context, integrated: str, peak: str, manual: str, gain: str) -> None:
	found = read_settings(context.settings)
	assert isinstance(found, Settings), found
	adjustment = _decibels(manual)
	assert adjustment is not None
	measured = Measure(_decibels(integrated), _decibels(peak))
	assert applied(found, measured, adjustment) == _decibels(gain)


@then(parsers.re(r"les réglages (?P<written>.+) sont refusés : « (?P<reason>.+) »$"))
def refused(written: str, reason: str) -> None:
	section: dict[str, Any] = {"target": -23, "ceiling": -1}
	if written == "cible « fort »":
		section["target"] = "fort"
	found = re.fullmatch(r"(cible|plafond) (-?\d+)", written)
	if found is not None:
		section[{"cible": "target", "plafond": "ceiling"}[found.group(1)]] = int(found.group(2))
	assert read_settings(section) == reason


@then(parsers.parse("il s'abonne seulement à {points}"))
def subscribed(context: Context, points: str) -> None:
	assert context.points == NAME.findall(points)


@then(parsers.re(r"la voie de « (?P<name>[^»]+) »(?:, pas encore mesuré,)? joue avec un gain de (?P<gain>-?\d+) dB"))
def track_gain(bench: Bench, name: str, gain: str) -> None:
	assert bench.engine is not None
	track = bench.engine.played_list[str(bench.files[name])]
	assert track.gain == float(gain)


@then(parsers.parse("le journal dit « {text} »"))
def journal(caplog: pytest.LogCaptureFixture, text: str) -> None:
	found = []
	for record in caplog.records:
		if (record.levelno >= logging.ERROR) and (record.getMessage() == text):
			found.append(record)
	assert found != [], caplog.records


@then("le gain répondu pour un sonore de sonie -17 est nul")
def no_gain() -> None:
	assert sound_gain(Current())({"properties": {"loudness": {"integrated": -17.0, "peak": -3.0}}}) is None


@then(parsers.parse("ses propriétés sont {expected}"))
def stored(empty_database: Connection, context: Context, expected: str) -> None:
	line = empty_database.execute("SELECT properties FROM sounds WHERE id = %s", (context.sound,)).fetchone()
	assert line is not None
	assert line[0] == json.loads(expected)


@then(parsers.re(r"le log a l'incident « (?P<kind>[^»]+) » : « (?P<message>.+) »$"))
def incident(empty_database: Connection, context: Context, kind: str, message: str) -> None:
	found = empty_database.execute(
		"SELECT level::text, kind, message, sound_id FROM log WHERE level <> 'info'"
	).fetchall()
	assert found == [("incident", kind, message, context.sound)], found


@then("le log n'a aucun incident")
def no_incident(empty_database: Connection) -> None:
	assert empty_database.execute("SELECT kind FROM log WHERE level <> 'info'").fetchall() == []


@then(parsers.parse("elle montre « {text} »"))
def shows(context: Context, text: str) -> None:
	section = _section(context)
	lines = [section.measure.text(), *section.applied.text().split("\n")]
	assert text in lines, lines


@then(
	parsers.re(
		r"l'ajustement manuel est (?P<state>coché|décoché), son curseur (?:grisé )?à « (?P<shown>[^»]+) »,"
		r" au plus (?P<highest>-?[\d,]+) dB"
	)
)
def adjustment(context: Context, state: str, shown: str, highest: str) -> None:
	section = _section(context)
	ticked = state == "coché"
	assert section.has_adjustment.isChecked() == ticked
	assert section.adjustment.isEnabled() == ticked
	assert section.adjustment.value_label.text() == shown
	assert section.adjustment.maximum() == _decibels(highest)


@then("la fiche est modifiée")
def modified(context: Context) -> None:
	assert context.changes != []


@then(
	parsers.re(
		r"la sonie visée et le plafond sont des curseurs, à (?P<target>-?[\d,]+) LUFS et (?P<ceiling>-?[\d,]+) dBFS"
	)
)
def window_values(context: Context, target: str, ceiling: str) -> None:
	window = _window(context)
	assert isinstance(window.target, LevelSlider)
	assert isinstance(window.ceiling, LevelSlider)
	assert (window.target.value(), window.ceiling.value()) == (_decibels(target), _decibels(ceiling))


@then("la fenêtre est assez large pour lire ses textes")
def wide(context: Context) -> None:
	window = _window(context)
	assert window.minimumWidth() >= window.fontMetrics().averageCharWidth() * 60


def _group(context: Context) -> QGroupBox:
	assert context.card is not None
	found = context.card.findChild(QGroupBox, GROUP)
	assert isinstance(found, QGroupBox)
	return found


@then("l'encart « Niveau » est juste sous l'encart « Fichier », replié, et se déplie d'un clic sur son titre")
def below_file(context: Context, qtbot: QtBot) -> None:
	assert context.card is not None
	group = _group(context)
	file_group = context.card.ui.file_group
	holder = file_group.parentWidget()
	assert holder is not None
	arrangement = holder.layout()
	assert isinstance(arrangement, QBoxLayout)
	assert arrangement.indexOf(group) == arrangement.indexOf(file_group) + 1
	content = group.findChild(QWidget, expandable.CONTENT)
	assert content is not None
	assert not content.isVisible()
	qtbot.mouseClick(group, Qt.MouseButton.LeftButton, pos=QPoint(12, 4))
	assert content.isVisible()


@then("la section du plugin est cachée")
def section_hidden(context: Context) -> None:
	assert context.card is not None
	found = context.card.findChild(LevelSection, "loudness_normalization")
	assert isinstance(found, LevelSection)
	assert found.isHidden()


@then("l'encart « Niveau » est caché")
def group_hidden(context: Context) -> None:
	assert _group(context).isHidden()


@then(parsers.re(r"« (?P<label>[^»]+) » est décochée, son curseur grisé sur « (?P<shown>[^»]+) »"))
def unticked(context: Context, label: str, shown: str) -> None:
	section = _bank_section(context)
	box, slider = section.has_target, section.target
	if label == "Plafond de crête propre à la banque":
		box, slider = section.has_ceiling, section.ceiling
	assert box.text() == label
	assert not box.isChecked()
	assert not slider.isEnabled()
	assert slider.value_label.text() == shown


def _bank_content(context: Context) -> tuple[QGroupBox, QWidget]:
	group = _bank_section(context).group
	content = group.findChild(QWidget, expandable.CONTENT)
	assert content is not None
	return group, content


@then("son encart « Niveau » est déplié, et se replie d'un clic sur son titre")
def bank_expanded(context: Context, qtbot: QtBot) -> None:
	group, content = _bank_content(context)
	assert not content.isHidden()
	qtbot.mouseClick(group, Qt.MouseButton.LeftButton, pos=QPoint(12, 4))
	assert content.isHidden()


@then("son encart « Niveau » est replié")
def bank_collapsed(context: Context) -> None:
	_group, content = _bank_content(context)
	assert content.isHidden()


@then(parsers.parse("les propriétés de la banque sont {expected}"))
def bank_stored(empty_database: Connection, context: Context, expected: str) -> None:
	line = empty_database.execute("SELECT properties FROM banks WHERE id = %s", (context.bank,)).fetchone()
	assert line is not None
	assert line[0] == json.loads(expected)


@then(parsers.parse("le message de la fenêtre dit « {text} »"))
def window_message(context: Context, text: str) -> None:
	assert _window(context).message.text() == text


@then("le fichier de configuration a gardé son commentaire et ses autres sections")
def kept(context: Context) -> None:
	assert context.path is not None
	written = context.path.read_text(encoding="utf-8")
	assert written.startswith('# Le poste de l\'antenne\n[plugins]\nenabled = ["loudness_normalization"]\n'), written
	assert "[dead_air]\nduration = 10\n" in written, written


@then(
	parsers.re(r"sa section \[plugins.loudness_normalization\] est target (?P<target>\S+), ceiling (?P<ceiling>\S+)$")
)
def section_written(context: Context, target: str, ceiling: str) -> None:
	assert context.path is not None
	written = tomllib.loads(context.path.read_text(encoding="utf-8"))
	assert written["plugins"]["loudness_normalization"] == {"target": float(target), "ceiling": float(ceiling)}


@then(parsers.parse("la fiche d'un sonore de sonie -20 montre aussitôt un gain automatique de {gain} dB"))
def card_now(empty_database: Connection, context: Context, qtbot: QtBot, gain: str) -> None:
	stored_sound(empty_database, context, "mesuré.flac", '{"loudness": {"integrated": -20.0, "peak": -30.0}}')
	context.connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	answers = plugins.active().points.collect(
		"interface.sound_card", {"connection": context.connection, "parent": None}
	)
	assert len(answers) == 1, answers
	section = answers[0][1]
	assert isinstance(section, LevelSection)
	qtbot.addWidget(section)
	with context.connection.transaction():
		section.read(context.sound)
	assert f"automatique {gain} dB" in section.applied.text(), section.applied.text()
