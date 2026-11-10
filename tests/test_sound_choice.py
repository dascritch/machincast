"""Étapes du choix d'un sonore dans une banque (https://github.com/dascritch/machincast/issues/13)."""

import random
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.clock import FixedClock
from machincast.database import Role, open_connection
from machincast.player.banks import choose_sound, remaining_list
from machincast.randomness import create_randomness
from tests.database_fixtures import sample_database_parameters

scenarios("sound_choice.feature")

Connection = psycopg.Connection[tuple[object, ...]]
ITEM = re.compile(r"« ([^»]+) »")
MODES = {"séquentielle": "sequential", "aléatoire": "random"}


@dataclass
class Context:
	clock: FixedClock | None = None
	randomness: random.Random = field(default_factory=lambda: create_randomness(0))
	played_list: list[str] = field(default_factory=list)


@pytest.fixture
def context() -> Context:
	return Context()


def names(list_: str) -> list[str]:
	return ITEM.findall(list_)


def hour(text: str) -> datetime:
	return datetime.fromisoformat(text).astimezone()


def sound(database: Connection, name: str) -> int:
	line = database.execute("SELECT id FROM sounds WHERE location = %s", (f"/sons/{name}.flac",)).fetchone()
	if line is None:
		line = database.execute(
			"INSERT INTO sounds (type, location, state) VALUES ('file', %s, 'active') RETURNING id",
			(f"/sons/{name}.flac",),
		).fetchone()
	assert line is not None
	return int(str(line[0]))


def sound_name(database: Connection, identifier: int) -> str:
	line = database.execute("SELECT location FROM sounds WHERE id = %s", (identifier,)).fetchone()
	assert line is not None
	return str(line[0]).removeprefix("/sons/").removesuffix(".flac")


def bank(database: Connection, name: str) -> int:
	line = database.execute("SELECT id FROM banks WHERE internal_name = %s", (name,)).fetchone()
	assert line is not None, f"banque {name} inconnue"
	return int(str(line[0]))


def add(database: Connection, bank_name: str, sound_name: str) -> None:
	database.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position)"
		" SELECT %s, %s, COALESCE(MAX(position), 0) + 1 FROM bank_sounds WHERE bank_id = %s",
		(bank(database, bank_name), sound(database, sound_name), bank(database, bank_name)),
	)


def airing(database: Connection, sound_name: str, bank_name: str | None) -> None:
	"""Ligne de début d'un passage dans l'airplay : ce qui compte pour le choix."""
	provided_by = None
	if bank_name is not None:
		provided_by = bank(database, bank_name)
	database.execute(
		"INSERT INTO airplay (play_id, line_type, sound_id, bank_id) VALUES (%s, 'start', %s, %s)",
		(uuid.uuid4(), sound(database, sound_name), provided_by),
	)


def choose(context: Context, bank_name: str) -> int | None:
	assert context.clock is not None
	socket, sample_database = sample_database_parameters()
	with open_connection(socket, sample_database, Role.PLAYBACK) as connection:
		identifier = playback_bank(connection, bank_name)
		return choose_sound(connection, identifier, context.clock.now(), context.randomness)


def playback_bank(connection: psycopg.Connection[tuple[object, ...]], name: str) -> int:
	line = connection.execute("SELECT id FROM banks WHERE internal_name = %s", (name,)).fetchone()
	assert line is not None
	return int(str(line[0]))


def play(context: Context, database: Connection, count: int, bank_name: str) -> list[str]:
	played_list = []
	for _ in range(count):
		chosen = choose(context, bank_name)
		assert chosen is not None, f"la banque {bank_name} n'a rien fourni"
		name = sound_name(database, chosen)
		airing(database, name, bank_name)
		played_list.append(name)
	return played_list


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'heure « {text} »"))
def clock(context: Context, text: str) -> None:
	context.clock = FixedClock(hour(text))


@given(parsers.re(r"une banque (?P<mode>séquentielle|aléatoire) « (?P<name>[^»]+) » contenant (?P<list_>.+)"))
def container_bank(empty_database: Connection, mode: str, name: str, list_: str) -> None:
	empty_database.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, %s)", (name, MODES[mode]))
	for sound_name in names(list_):
		add(empty_database, name, sound_name)


@given(parsers.parse("le sonore « {sound_name} » ajouté à la banque « {bank_name} »"))
def adds(empty_database: Connection, sound_name: str, bank_name: str) -> None:
	add(empty_database, bank_name, sound_name)


@given(parsers.parse("« {sound_name} » a été joué via la banque « {bank_name} »"))
def plays_via(empty_database: Connection, sound_name: str, bank_name: str) -> None:
	airing(empty_database, sound_name, bank_name)


@given(parsers.parse("« {sound_name} » a été joué sans banque"))
def plays_without_bank(empty_database: Connection, sound_name: str) -> None:
	airing(empty_database, sound_name, None)


@given(parsers.parse("le hasard créé avec la graine {seed:d}"))
def randomness(context: Context, seed: int) -> None:
	context.randomness = create_randomness(seed)


@given(parsers.parse("le sonore « {name} » est à l'état « {state} »"))
def state(empty_database: Connection, name: str, state: str) -> None:
	empty_database.execute("UPDATE sounds SET state = %s WHERE id = %s", (state, sound(empty_database, name)))


@given(parsers.parse("le sonore « {name} » n'est diffusable qu'à partir du « {start} »"))
def playable_to_leave(empty_database: Connection, name: str, start: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET broadcast_start = %s WHERE id = %s", (hour(start), sound(empty_database, name))
	)


@given(parsers.parse("le sonore « {name} » n'est plus diffusable depuis le « {end} »"))
def more_playable(empty_database: Connection, name: str, end: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET broadcast_end = %s WHERE id = %s", (hour(end), sound(empty_database, name))
	)


@given(parsers.parse("le sonore « {name} » est diffusable du « {start} » au « {end} »"))
def playable(empty_database: Connection, name: str, start: str, end: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET broadcast_start = %s, broadcast_end = %s WHERE id = %s",
		(hour(start), hour(end), sound(empty_database, name)),
	)


@given(parsers.parse("le sonore « {name} » a atteint son maximum de {maximum:d} lectures"))
def reached_maximum(empty_database: Connection, name: str, maximum: int) -> None:
	plays(empty_database, name, maximum, maximum)


@given(parsers.parse("le sonore « {name} » a été lu {count:d} fois sur un maximum de {maximum:d} lectures"))
def plays(empty_database: Connection, name: str, count: int, maximum: int) -> None:
	empty_database.execute("UPDATE sounds SET max_plays = %s WHERE id = %s", (maximum, sound(empty_database, name)))
	for _ in range(count):
		airing(empty_database, name, None)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je joue (?P<count>\d+) sonores? de la banque « (?P<name>[^»]+) »"))
def play_sounds(context: Context, empty_database: Connection, count: str, name: str) -> None:
	context.played_list = play(context, empty_database, int(count), name)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("les sonores joués sont {list_}"))
def played_sounds(context: Context, list_: str) -> None:
	assert context.played_list == names(list_)


@then(parsers.parse("chaque tranche de {size:d} sonores joués contient {list_}, une fois chacun"))
def slices(context: Context, size: int, list_: str) -> None:
	expected_list = sorted(names(list_))
	for start in range(0, len(context.played_list), size):
		assert sorted(context.played_list[start : start + size]) == expected_list, context.played_list


def remainder(context: Context, database: Connection, seed: int, count: int, bank_name: str) -> list[str]:
	database.execute("DELETE FROM airplay")
	context.randomness = create_randomness(seed)
	return play(context, database, count, bank_name)


@then(parsers.parse("deux tirages de {count:d} sonores avec la graine {seed:d} donnent la même suite"))
def same_remainder(context: Context, empty_database: Connection, count: int, seed: int) -> None:
	first = remainder(context, empty_database, seed, count, "Titres")
	assert remainder(context, empty_database, seed, count, "Titres") == first


@then(
	parsers.parse(
		"des tirages de {count:d} sonores avec les graines {first:d} à {last:d} ne donnent pas tous la même suite"
	)
)
def different_remainders(context: Context, empty_database: Connection, count: int, first: int, last: int) -> None:
	remainders = set()
	for g in range(first, last + 1):
		remainders.add(tuple(remainder(context, empty_database, g, count, "Titres")))
	assert len(remainders) > 1


@then(parsers.parse("les sonores qui restent à jouer dans le cycle de « {name} » sont {list_}"))
def remaining_cycle(context: Context, empty_database: Connection, name: str, list_: str) -> None:
	assert context.clock is not None
	socket, sample_database = sample_database_parameters()
	with open_connection(socket, sample_database, Role.PLAYBACK) as connection:
		rest = remaining_list(connection, playback_bank(connection, name), context.clock.now())
	rest_names = []
	for sound in rest:
		rest_names.append(sound_name(empty_database, sound))
	assert sorted(rest_names) == sorted(names(list_))


@then(parsers.parse("la banque « {name} » ne fournit aucun sonore"))
def no(context: Context, name: str) -> None:
	assert choose(context, name) is None
