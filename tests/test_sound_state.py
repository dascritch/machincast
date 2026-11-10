"""Étapes des scénarios de l'état d'un sonore (https://github.com/dascritch/machincast/issues/66)."""

import psycopg
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("sound_state.feature")

Connection = psycopg.Connection[tuple[object, ...]]


@given("une base de test vide où les migrations sont appliquées")
def migrated_database(empty_database: Connection) -> None:
	"""empty_database applique déjà toutes les migrations."""


@when("j'enregistre un sonore sans préciser son état", target_fixture="sound")
def save(empty_database: Connection) -> int:
	line = empty_database.execute(
		"INSERT INTO sounds (type, location) VALUES ('file', '/a.flac') RETURNING id"
	).fetchone()
	assert line is not None
	return int(str(line[0]))


@then(parsers.parse('le type "{name}" a pour valeurs, dans l\'ordre : {values}'))
def type_values(empty_database: Connection, name: str, values: str) -> None:
	lines = empty_database.execute(
		"SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid = enumtypid"
		" WHERE typname = %s ORDER BY enumsortorder",
		(name,),
	).fetchall()
	line_list = []
	for line in lines:
		line_list.append(line[0])
	value_list = []
	for value in values.split(","):
		value_list.append(value.strip())
	assert line_list == value_list


@then(parsers.parse("son état est « {state} »"))
def sound_state(empty_database: Connection, sound: int, state: str) -> None:
	line = empty_database.execute("SELECT state::text FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert line == (state,)


@then(parsers.parse("un sonore à l'état « {state} » est refusé"))
def refused_state(empty_database: Connection, state: str) -> None:
	try:
		empty_database.execute("INSERT INTO sounds (type, location, state) VALUES ('file', '/x.flac', %s)", (state,))
	except psycopg.errors.InvalidTextRepresentation:
		return
	raise AssertionError(f"l'état « {state} » aurait dû être refusé")
