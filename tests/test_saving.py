"""Étapes de l'enregistrement de l'airplay et du log (https://github.com/dascritch/machincast/issues/17)."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.database import Role, open_connection
from machincast.player.saving import Play, begin_play, finish_play, record
from tests.database_fixtures import sample_database_parameters

scenarios("saving.feature")

Connection = psycopg.Connection[tuple[object, ...]]
PLAYBACK_SOURCES = Path(__file__).resolve().parents[1] / "src" / "machincast" / "player"


@dataclass
class Context:
	ids: dict[str, int] = field(default_factory=dict)
	play: Play | None = None


@pytest.fixture
def context() -> Context:
	return Context()


@pytest.fixture
def playback(empty_database: Connection) -> Iterator[Connection]:
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		yield connection


def hour(text: str) -> datetime:
	return datetime.fromisoformat(text).astimezone()


def create(database: Connection, query: str, values: tuple[object, ...]) -> int:
	line = database.execute(query + " RETURNING id", values).fetchone()
	assert line is not None
	return int(str(line[0]))


def event(database: Connection, name: str) -> int:
	return create(
		database,
		"INSERT INTO events (internal_name, priority, starts_at) VALUES (%s, 'show', %s)",
		(name, hour("2026-10-15 20:00:00")),
	)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le sonore « {location} », de l'artiste « {artist} » et du titre « {title} »"))
def sound(context: Context, empty_database: Connection, location: str, artist: str, title: str) -> None:
	context.ids["sonore"] = create(
		empty_database,
		"INSERT INTO sounds (type, location, state, artist, title) VALUES ('file', %s, 'active', %s, %s)",
		(location, artist, title),
	)


@given(parsers.parse("la banque « {name} » qui le contient"))
def bank(context: Context, empty_database: Connection, name: str) -> None:
	context.ids[name] = create(
		empty_database, "INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential')", (name,)
	)
	empty_database.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, 1)",
		(context.ids[name], context.ids["sonore"]),
	)


@given(parsers.parse("l'émission « {name} », dont il est le 2e élément, via la banque « {name_bank} »"))
def show(context: Context, empty_database: Connection, name: str, name_bank: str) -> None:
	context.ids[name] = event(empty_database, name)
	create(
		empty_database,
		"INSERT INTO event_items (event_id, position, sound_id) VALUES (%s, 1, %s)",
		(context.ids[name], context.ids["sonore"]),
	)
	context.ids["element"] = create(
		empty_database,
		"INSERT INTO event_items (event_id, position, bank_id) VALUES (%s, 2, %s)",
		(context.ids[name], context.ids[name_bank]),
	)


@given(parsers.parse("l'émission « {name} », dont le sonore est le 1er élément, sans banque"))
def direct_show(context: Context, empty_database: Connection, name: str) -> None:
	context.ids[name] = event(empty_database, name)
	context.ids[f"element {name}"] = create(
		empty_database,
		"INSERT INTO event_items (event_id, position, sound_id) VALUES (%s, 1, %s)",
		(context.ids[name], context.ids["sonore"]),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le binaire lecture commence ce passage à « {instant} »"))
def begin(context: Context, playback: Connection, instant: str) -> None:
	i = context.ids
	context.play = begin_play(playback, i["sonore"], i["Titres"], i["Magazine"], i["element"], hour(instant))


@when(parsers.parse("le binaire lecture commence le passage de l'émission « {name} » à « {instant} »"))
def begin_live(context: Context, playback: Connection, name: str, instant: str) -> None:
	i = context.ids
	context.play = begin_play(playback, i["sonore"], None, i[name], i[f"element {name}"], hour(instant))


@when(parsers.parse("le titre du sonore devient « {title} »"))
def new_title(context: Context, empty_database: Connection, title: str) -> None:
	empty_database.execute("UPDATE sounds SET title = %s WHERE id = %s", (title, context.ids["sonore"]))


@when(parsers.re(r"(?:le binaire lecture termine le passage|le termine) à « (?P<instant>[^»]+) », joué en entier"))
def finish_integer(context: Context, playback: Connection, instant: str) -> None:
	assert context.play is not None
	finish_play(playback, context.play, hour(instant))


@when(parsers.parse("le termine à « {instant} », coupé net"))
def finish_cut(context: Context, playback: Connection, instant: str) -> None:
	assert context.play is not None
	finish_play(playback, context.play, hour(instant), cut=True)


@when(parsers.parse("le termine à « {instant} », sur l'erreur « {error} »"))
def finish_error(context: Context, playback: Connection, instant: str, error: str) -> None:
	assert context.play is not None
	finish_play(playback, context.play, hour(instant), error=error)


@when(parsers.parse("le binaire lecture consigne « {level} » « {kind} » : « {message} », à « {instant} »"))
def records(playback: Connection, level: str, kind: str, message: str, instant: str) -> None:
	record(playback, level, kind, message, hour(instant))


# ─── Alors ─────────────────────────────────────────────────


def airplay(database: Connection) -> list[tuple[object, ...]]:
	return database.execute(
		"SELECT play_id, line_type::text, logged_at, location, artist, title, sound_id, bank_id,"
		" event_id, event_item_id, played_duration, without_incident FROM airplay ORDER BY id"
	).fetchall()


@then(parsers.parse("l'airplay contient {count:d} lignes, de début et de fin, avec le même identifiant de passage"))
def line_two(empty_database: Connection, count: int) -> None:
	lines = airplay(empty_database)
	assert [line[1] for line in lines] == ["start", "end"][:count]
	assert len({line[0] for line in lines}) == 1


@then(parsers.parse("la ligne de début est datée de « {start} », celle de fin de « {end} »"))
def dates(empty_database: Connection, start: str, end: str) -> None:
	assert [line[2] for line in airplay(empty_database)] == [hour(start), hour(end)]


@then(
	parsers.parse(
		"chaque ligne d'airplay recopie l'emplacement « {location} », l'artiste « {artist} » et le titre « {title} »"
	)
)
def copies(empty_database: Connection, location: str, artist: str, title: str) -> None:
	lines = airplay(empty_database)
	assert (lines) and (all(line[3:6] == (location, artist, title) for line in lines)), lines


@then(
	parsers.parse(
		"chaque ligne d'airplay référence le sonore, la banque « {name_bank} », l'émission « {name} » et son 2e élément"
	)
)
def references(context: Context, empty_database: Connection, name_bank: str, name: str) -> None:
	i = context.ids
	expected = (i["sonore"], i[name_bank], i[name], i["element"])
	assert all(line[6:10] == expected for line in airplay(empty_database))


@then("la ligne de début ne référence aucune banque")
def without_bank(empty_database: Connection) -> None:
	assert airplay(empty_database)[0][7] is None


@then(parsers.re(r"la ligne de fin indique (?P<seconds>\d+) secondes diffusées, (?P<outcome>sans|avec) incident"))
def end_line(empty_database: Connection, seconds: str, outcome: str) -> None:
	end = airplay(empty_database)[-1]
	assert end[1] == "end"
	assert end[10] == timedelta(seconds=int(seconds))
	assert end[11] is (outcome == "sans")


def log(database: Connection) -> list[tuple[object, ...]]:
	return database.execute(
		"SELECT level::text, kind, message, logged_at, sound_id, bank_id, event_id FROM log ORDER BY id"
	).fetchall()


@then("le log ne contient rien")
def empty_log(empty_database: Connection) -> None:
	assert log(empty_database) == []


@then(parsers.parse("le log contient une ligne « {level} » « {kind} » pour ce sonore, la banque et l'émission"))
def log_line(context: Context, empty_database: Connection, level: str, kind: str) -> None:
	i = context.ids
	lines = log(empty_database)
	assert [(n, t, s, b, e) for n, t, _, _, s, b, e in lines] == [
		(level, kind, i["sonore"], i["Titres"], i["Magazine"])
	], lines


@then(parsers.parse("cette ligne du log mentionne « {text} »"))
def mention(empty_database: Connection, text: str) -> None:
	assert text in str(log(empty_database)[-1][2])


@then(
	parsers.parse(
		"le log contient une ligne « {level} » « {kind} » datée de « {instant} », qui mentionne « {message} »"
	)
)
def dated_line(empty_database: Connection, level: str, kind: str, instant: str, message: str) -> None:
	lines = log(empty_database)
	assert len(lines) == 1, lines
	n, t, m, h, *_ = lines[0]
	assert (n, t, h) == (level, kind, hour(instant))
	assert message in str(m)


@then("aucun module du binaire lecture n'écrit dans le log autrement que par machincast.player.saving")
def a_only_log() -> None:
	faults = [
		path.name
		for path in sorted(PLAYBACK_SOURCES.glob("*.py"))
		if (path.name != "saving.py") and ("INSERT INTO log" in path.read_text(encoding="utf-8"))
	]
	assert not faults, faults
