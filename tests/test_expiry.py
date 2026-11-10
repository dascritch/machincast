"""Étapes de l'expiration automatique des sonores (https://github.com/dascritch/machincast/issues/18).

Les étapes de la diffusion viennent de tests/broadcast_steps.py.
"""

import uuid
from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.database import Role, open_connection
from machincast.player.expiry import expire
from tests.broadcast_steps import Connection, hour, sound
from tests.database_fixtures import sample_database_parameters
from tests.log_texts import shown, stored

scenarios("expiry.feature")


@dataclass
class Before:
	lines: dict[str, dict[str, object]] = field(default_factory=dict)


@pytest.fixture
def before() -> Before:
	return Before()


def sound_line(database: Connection, name: str) -> dict[str, object]:
	line = database.execute("SELECT to_jsonb(s) FROM sounds s WHERE title = %s", (name,)).fetchone()
	assert (line is not None) and (isinstance(line[0], dict))
	return dict(line[0])


def play(database: Connection, name: str, count: int, event: object = None, bank: object = None) -> None:
	for _ in range(count):
		database.execute(
			"INSERT INTO airplay (play_id, line_type, sound_id, event_id, bank_id) VALUES (%s, 'start', %s, %s, %s)",
			(uuid.uuid4(), sound(database, name), event, bank),
		)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le sonore actif « {name} » avec un maximum de {maximum:d} lectures"))
def sound_with_maximum(empty_database: Connection, name: str, maximum: int) -> None:
	empty_database.execute(
		"INSERT INTO sounds (type, location, state, title, max_plays) VALUES ('file', %s, 'active', %s, %s)",
		(f"/annonces/{name}.flac", name, maximum),
	)


@given(parsers.re(r"le sonore « (?P<name>[^»]+) » a un maximum de (?P<maximum>\d+) lectures?"))
def sound_maximum(empty_database: Connection, name: str, maximum: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET max_plays = %s WHERE id = %s", (int(maximum), sound(empty_database, name))
	)


@given(parsers.parse("le sonore actif « {name} » diffusable jusqu'au « {end} »"))
def sound_with_end(empty_database: Connection, name: str, end: str) -> None:
	empty_database.execute(
		"INSERT INTO sounds (type, location, state, title, broadcast_end) VALUES ('file', %s, 'active', %s, %s)",
		(f"/annonces/{name}.flac", name, hour(end)),
	)


@given(parsers.parse("le sonore « {name} » est à l'état « {state} »"))
def sound_state(empty_database: Connection, name: str, state: str) -> None:
	empty_database.execute("UPDATE sounds SET state = %s WHERE id = %s", (state, sound(empty_database, name)))


@given(parsers.re(r"« (?P<name>[^»]+) » a été joué (?P<count>\d+) fois$"))
def plays(empty_database: Connection, name: str, count: str) -> None:
	play(empty_database, name, int(count))


@given(parsers.parse("« {name} » a été joué {count:d} fois dans l'émission « {show} »"))
def plays_in_show(empty_database: Connection, name: str, count: int, show: str) -> None:
	created = empty_database.execute(
		"INSERT INTO events (internal_name, priority, starts_at) VALUES (%s, 'show', '2026-10-01 08:00') RETURNING id",
		(show,),
	).fetchone()
	assert created is not None
	play(empty_database, name, count, event=created[0])


@given(parsers.parse("« {name} » a été joué {count:d} fois via la banque « {bank} »"))
def plays_via_bank(empty_database: Connection, name: str, count: int, bank: str) -> None:
	created = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (bank,)
	).fetchone()
	assert created is not None
	play(empty_database, name, count, bank=created[0])


@given(parsers.parse("« {name} » a été joué {count:d} fois sans événement ni banque"))
def plays_without_nothing(empty_database: Connection, name: str, count: int) -> None:
	play(empty_database, name, count)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le binaire lecture vérifie les expirations au « {instant} »"))
def check(empty_database: Connection, before: Before, instant: str) -> None:
	for (title,) in empty_database.execute("SELECT title FROM sounds").fetchall():
		before.lines.setdefault(str(title), sound_line(empty_database, str(title)))
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		expire(connection, hour(instant))


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le sonore « {name} » est à l'état « {state} »"))
def expected_state(empty_database: Connection, name: str, state: str) -> None:
	assert sound_line(empty_database, name)["state"] == state


@then(parsers.parse("le log contient {count:d} info « {kind} », pour ce sonore, qui mentionne « {mention} »"))
def log_line(empty_database: Connection, count: int, kind: str, mention: str) -> None:
	lines = empty_database.execute(
		"SELECT level::text, message, sound_id FROM log WHERE kind = %s", (stored(kind),)
	).fetchall()
	assert len(lines) == count, lines
	identifiers = set()
	for (i,) in empty_database.execute("SELECT id FROM sounds").fetchall():
		identifiers.add(int(str(i)))
	for level, message, id_sound in lines:
		assert (level == "info") and (mention in shown(message)) and (id_sound in identifiers), lines


@then("le log est vide")
def empty_log(empty_database: Connection) -> None:
	assert empty_database.execute("SELECT level, kind, message FROM log").fetchall() == []


@then(parsers.parse("seules les colonnes state et modified_at du sonore « {name} » ont changé"))
def only_state(empty_database: Connection, before: Before, name: str) -> None:
	after = sound_line(empty_database, name)
	changed_list = set()
	for key in after:
		if after[key] != before.lines[name][key]:
			changed_list.add(key)
	assert changed_list == {"state", "modified_at"}, changed_list
