"""Scénarios de l'audit complet demandé pour certains sonores (https://github.com/dascritch/machincast/issues/114).

Les étapes des fichiers, des sonores et de l'indexeur sont dans tests/indexing_steps.py.
"""

import psycopg
from pytest_bdd import given, scenarios, then

scenarios("requested_audit.feature")

Connection = psycopg.Connection[tuple[object, ...]]


def requested_audit(database: Connection, sound: int) -> object:
	line = database.execute("SELECT audit_requested FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert line is not None
	return line[0]


@given("un audit complet demandé pour ce sonore")
def ask(empty_database: Connection, sound: int) -> None:
	empty_database.execute("UPDATE sounds SET audit_requested = true WHERE id = %s", (sound,))


@then("ce sonore n'a plus d'audit complet demandé")
def more_requested(empty_database: Connection, sound: int) -> None:
	assert requested_audit(empty_database, sound) is False


@then("ce sonore a toujours un audit complet demandé")
def always_requested(empty_database: Connection, sound: int) -> None:
	assert requested_audit(empty_database, sound) is True
