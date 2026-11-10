"""Étapes du déroulé de la liste de lecture et des transitions (https://github.com/dascritch/machincast/issues/14).

La diffusion est simulée minute par minute : l'ordonnanceur décide ; la simulation tient le passage en cours et
note chaque passage dans l'airplay, avec sa banque, son événement et son élément, comme le fera le binaire.
"""

import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.database import Role, open_connection
from machincast.player.rundown import Ongoing, Scheduler, ignored_calls
from machincast.player.saving import LEVELS
from machincast.randomness import create_randomness
from tests.categories import inverted
from tests.database_fixtures import sample_database_parameters
from tests.log_texts import stored

scenarios("rundown.feature")

Connection = psycopg.Connection[tuple[object, ...]]
ITEM = re.compile(r"(sonore|banque|séquence) « ([^»]+) »")
COLUMNS = {"sonore": "sound_id", "banque": "bank_id", "séquence": "sequence_id"}
NAME = re.compile(r"« ([^»]+) »")
DAY = date(2026, 10, 14)
MODES = {"séquentielle": "sequential", "aléatoire": "random"}


@dataclass
class Line:
	hour: str
	sound: str
	event: str
	outcome: str


@dataclass
class Context:
	duration: timedelta = timedelta(minutes=10)
	durations: dict[str, timedelta] = field(default_factory=dict)
	log: list[Line] = field(default_factory=list)
	scheduler: Scheduler | None = None
	reported_list: list[int] = field(default_factory=list)


@pytest.fixture
def context() -> Context:
	return Context()


@pytest.fixture
def playback(empty_database: Connection) -> Iterator[Connection]:
	"""Connexion du binaire lecture, avec ses seuls droits."""
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		yield connection


def a(hour: str, day: date = DAY) -> datetime:
	"""« 20:00 » le jour du scénario, en heure du poste, avec fuseau."""
	return datetime.combine(day, time.fromisoformat(hour)).astimezone()


def has_or_none(hour: str) -> datetime | None:
	"""Comme a, et aucune heure pour une cellule vide."""
	if hour == "":
		return None
	return a(hour)


def sound(database: Connection, name: str) -> int:
	location = f"/sons/{name}.flac"
	line = database.execute("SELECT id FROM sounds WHERE location = %s", (location,)).fetchone()
	if line is None:
		line = database.execute(
			"INSERT INTO sounds (type, location, state) VALUES ('file', %s, 'active') RETURNING id", (location,)
		).fetchone()
	assert line is not None
	return int(str(line[0]))


def name_of(database: Connection, table: str, column: str, identifier: int) -> str:
	line = database.execute(f"SELECT {column} FROM {table} WHERE id = %s", (identifier,)).fetchone()  # noqa: S608
	assert line is not None
	return str(line[0]).removeprefix("/sons/").removesuffix(".flac")


def bank(database: Connection, name: str) -> int:
	line = database.execute("SELECT id FROM banks WHERE internal_name = %s", (name,)).fetchone()
	assert line is not None, f"banque {name} inconnue"
	return int(str(line[0]))


def sequence(database: Connection, name: str) -> int:
	line = database.execute("SELECT id FROM sequences WHERE internal_name = %s", (name,)).fetchone()
	assert line is not None, f"séquence {name} inconnue"
	return int(str(line[0]))


def reference(database: Connection, category: str, name: str) -> int:
	if category == "sonore":
		return sound(database, name)
	if category == "banque":
		return bank(database, name)
	return sequence(database, name)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("chaque sonore dure {minutes:d} minutes"))
def duration(context: Context, minutes: int) -> None:
	context.duration = timedelta(minutes=minutes)


@given(parsers.parse("le sonore « {name} » dure {minutes:d} minutes"))
def own_duration(context: Context, name: str, minutes: int) -> None:
	context.durations[name] = timedelta(minutes=minutes)


@given(parsers.re(r"une banque (?P<mode>séquentielle|aléatoire) « (?P<name>[^»]+) » contenant (?P<list_>.+)"))
def container_bank(empty_database: Connection, mode: str, name: str, list_: str) -> None:
	empty_database.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, %s)", (name, MODES[mode]))
	for position, sound_name in enumerate(NAME.findall(list_), start=1):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
			(bank(empty_database, name), sound(empty_database, sound_name), position),
		)


@given(parsers.re(r"une séquence vide « (?P<name>[^»]+) »"))
def empty_sequence(empty_database: Connection, name: str) -> None:
	empty_database.execute("INSERT INTO sequences (internal_name) VALUES (%s)", (name,))


@given(parsers.re(r"une séquence « (?P<name>[^»]+) » jouant (?P<list_>.+)"))
def playing_sequence(empty_database: Connection, name: str, list_: str) -> None:
	created = empty_database.execute(
		"INSERT INTO sequences (internal_name) VALUES (%s) RETURNING id", (name,)
	).fetchone()
	assert created is not None
	for position, (category, item_name) in enumerate(ITEM.findall(list_), start=1):
		empty_database.execute(
			f"INSERT INTO sequence_items (sequence_id, position, {COLUMNS[category]})"  # noqa: S608
			" VALUES (%s, %s, %s)",
			(created[0], position, reference(empty_database, category, item_name)),
		)


@given(parsers.parse("la banque « {name} » est marquée « ne pas répéter »"))
def no_repeat(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE banks SET no_repeat = true WHERE id = %s", (bank(empty_database, name),))


@given(parsers.parse("le sonore « {name} » est à l'état « {state} »"))
def state(empty_database: Connection, name: str, state: str) -> None:
	empty_database.execute("UPDATE sounds SET state = %s WHERE id = %s", (state, sound(empty_database, name)))


@given("les événements :")
def events(empty_database: Connection, datatable: list[list[str]]) -> None:
	headers, *lines = datatable
	for values in lines:
		cells = []
		for v in values:
			cells.append(v.strip())
		line = dict(zip(headers, cells, strict=True))
		days = []
		for j in line.get("jours", "").split(","):
			if j.strip():
				days.append(j.strip())
		created = empty_database.execute(
			"INSERT INTO events (internal_name, priority, starts_at, ends_at, recurrence_days)"
			" VALUES (%s, %s, %s, %s, %s::weekday[]) RETURNING id",
			(
				line["nom"],
				line["priorité"],
				has_or_none(line["début"]),
				has_or_none(line["fin"]),
				days,
			),
		).fetchone()
		assert created is not None
		for position, (category, name) in enumerate(ITEM.findall(line["liste"]), start=1):
			empty_database.execute(
				f"INSERT INTO event_items (event_id, position, {COLUMNS[category]})"  # noqa: S608
				" VALUES (%s, %s, %s)",
				(created[0], position, reference(empty_database, category, name)),
			)


# ─── Quand ─────────────────────────────────────────────────


def unroll(context: Context, database: Connection, playback: Connection, start: datetime, end: datetime) -> None:
	if context.scheduler is None:
		context.scheduler = Scheduler(playback, create_randomness(0))
	ongoing: Ongoing | None = None
	in_dead_air = False
	instant = start
	while instant < end:
		if (ongoing is not None) and (instant >= ongoing.planned_end):
			ongoing = None
		decision = context.scheduler.decide(instant, ongoing)
		if decision.cut:
			context.log[-1].outcome = f"coupé à {instant:%H:%M}"
			ongoing = None
		if decision.play is not None:
			choice = decision.play
			if choice.line is None:
				line_sequence = None
			else:
				line_sequence = choice.line.sequence
			if choice.line is None:
				line_id = None
			else:
				line_id = choice.line.id
			if choice.lender is None:
				event_id = None
			else:
				event_id = choice.lender.event.id
			database.execute(
				"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, bank_id, event_id,"
				" event_item_id, sequence_id, sequence_item_id, lender_event_id)"
				" VALUES (%s, 'start', %s, %s, %s, %s, %s, %s, %s, %s)",
				(
					uuid.uuid4(),
					instant,
					choice.sound,
					choice.bank,
					choice.occurrence.event.id,
					choice.item.id,
					line_sequence,
					line_id,
					event_id,
				),
			)
			name = name_of(database, "sounds", "location", choice.sound)
			ongoing = Ongoing(choice.occurrence, instant, instant + context.durations.get(name, context.duration))
			outcome = "en cours"
			if ongoing.planned_end <= end:
				outcome = "entier"
			event = choice.occurrence.event.name
			if choice.lender is not None:
				# https://github.com/dascritch/machincast/issues/399
				event = f"{event}, au nom de {choice.lender.event.name}"
			context.log.append(Line(f"{instant:%H:%M}", name, event, outcome))
			in_dead_air = False
		else:
			if (decision.dead_air) and (not in_dead_air):
				if decision.occurrence is None:
					event = ""
				else:
					event = decision.occurrence.event.name
				context.log.append(Line(f"{instant:%H:%M}", "blanc", event, ""))
				in_dead_air = True
		instant += timedelta(minutes=1)


@when(parsers.re(r"la diffusion se déroule de (?P<start>\d\d:\d\d) à (?P<end>\d\d:\d\d)"))
def progress(context: Context, empty_database: Connection, playback: Connection, start: str, end: str) -> None:
	unroll(context, empty_database, playback, a(start), a(end))


@when(parsers.re(r"la diffusion se déroule le lendemain de (?P<start>\d\d:\d\d) à (?P<end>\d\d:\d\d)"))
def next_day(context: Context, empty_database: Connection, playback: Connection, start: str, end: str) -> None:
	day = DAY + timedelta(days=1)
	unroll(context, empty_database, playback, a(start, day), a(end, day))


@when(parsers.parse("l'événement suivant est avancé à {hour}"))
def advances(context: Context, hour: str) -> None:
	"""https://github.com/dascritch/machincast/issues/257."""
	assert context.scheduler is not None
	assert context.scheduler.advance(a(hour)) is not None


@when("le binaire redémarre")
def restart(context: Context) -> None:
	"""Un nouvel ordonnanceur, sans rien en mémoire : tout se relit dans l'airplay."""
	context.scheduler = None


@when(parsers.re(r"la liste « (?P<list_>[^»]+) » est vérifiée pour un événement qui (?P<loop>boucle|ne boucle pas)"))
def check_list(context: Context, empty_database: Connection, list_: str, loop: str) -> None:
	names = []
	for name in list_.split(","):
		names.append(name.strip())
	banks: list[int | None] = []
	for name in names:
		banks.append(None)
		if name != "sonore":
			banks[-1] = bank(empty_database, name)
	marked_list = set()
	for line in empty_database.execute("SELECT id FROM banks WHERE no_repeat"):
		marked_list.add(int(str(line[0])))
	context.reported_list = ignored_calls(banks, marked_list, loop == "boucle")


# ─── Alors ─────────────────────────────────────────────────


@then("la diffusion a été :")
def broadcast(context: Context, datatable: list[list[str]]) -> None:
	_, *lines = datatable
	expected = []
	for values in lines:
		cells = []
		for v in values:
			cells.append(v.strip())
		expected.append(Line(*cells))
	line_list = []
	for line in context.log:
		line_list.append(str(line))
	assert context.log == expected, "\n".join(line_list)


LEVEL_IN_DATABASE = inverted(LEVELS)
"""Le niveau du log en base, par le mot des scénarios."""


@then(
	parsers.re(
		r"le log contient (?P<count>\d+) (?P<level>alerte|info) « (?P<kind>[^»]+) » pour l'événement"
		r" « (?P<event>[^»]+) »(?: et la banque « (?P<bank_name>[^»]+) »)?$"
	)
)
def warnings(empty_database: Connection, count: str, level: str, kind: str, event: str, bank_name: str | None) -> None:
	lines = empty_database.execute(
		"SELECT l.level::text, e.internal_name, b.internal_name FROM log l"
		" LEFT JOIN events e ON e.id = l.event_id LEFT JOIN banks b ON b.id = l.bank_id"
		" WHERE l.kind = %s",
		(stored(kind),),
	).fetchall()
	obtained_list = []
	for n, e, b in lines:
		obtained_bank = ()
		if bank_name:
			obtained_bank = (b,)
		obtained_list.append((n, e) + obtained_bank)
	expected_bank = ()
	if bank_name:
		expected_bank = (bank_name,)
	expected = (LEVEL_IN_DATABASE[level], event) + expected_bank
	assert obtained_list == [expected] * int(count), lines


@then(parsers.re(r"le log ne contient aucune (?P<level>alerte|info) « (?P<kind>[^»]+) »"))
def no_line(empty_database: Connection, level: str, kind: str) -> None:
	query = "SELECT message FROM log WHERE level = %s AND kind = %s"
	lines = empty_database.execute(query, (LEVEL_IN_DATABASE[level], stored(kind))).fetchall()
	assert lines == [], lines


@then(parsers.re(r"les lignes signalées sont « (?P<lines>[^»]*) »"))
def reported_lines(context: Context, lines: str) -> None:
	expected_lines = []
	for number in lines.split(","):
		if number.strip():
			expected_lines.append(int(number))
	assert context.reported_list == expected_lines
