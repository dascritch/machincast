"""Étapes partagées de la fin de liste et des secours d'un événement (https://github.com/dascritch/machincast/issues/350).

Les événements nommés existent déjà en base, écrits par les étapes de chaque fonctionnalité ; un secours est un
événement de priorité fallback.
"""

import psycopg
from pytest_bdd import given, parsers

Connection = psycopg.Connection[tuple[object, ...]]


def _event(database: Connection, name: str) -> int:
	line = database.execute("SELECT id FROM events WHERE internal_name = %s AND deleted_at IS NULL", (name,)).fetchone()
	assert line is not None, f"aucun événement « {name} »"
	return int(str(line[0]))


@given(parsers.parse("l'événement « {name} » passe, à la fin de sa liste, au fil musical"))
def to_background(empty_database: Connection, name: str) -> None:
	empty_database.execute(
		"UPDATE events SET end_of_list = 'background_programming' WHERE id = %s", (_event(empty_database, name),)
	)


@given(parsers.parse("l'événement « {name} » passe, à la fin de sa liste, au secours « {fallback} »"))
def to_fallback(empty_database: Connection, name: str, fallback: str) -> None:
	empty_database.execute(
		"UPDATE events SET end_of_list = 'fallback', end_fallback_event_id = %s WHERE id = %s",
		(_event(empty_database, fallback), _event(empty_database, name)),
	)


@given(parsers.parse("l'événement « {name} » a pour secours d'un stream tombé « {fallback} »"))
def stream_fallback(empty_database: Connection, name: str, fallback: str) -> None:
	empty_database.execute(
		"UPDATE events SET stream_fallback_event_id = %s WHERE id = %s",
		(_event(empty_database, fallback), _event(empty_database, name)),
	)


@given(parsers.parse("l'événement « {name} » prête, à la fin de sa liste, son nom au fil musical"))
def lends_name(empty_database: Connection, name: str) -> None:
	"""https://github.com/dascritch/machincast/issues/399 : le fil musical, ou l'événement en dessous, joue sous son
	nom jusqu'à sa fin."""
	empty_database.execute("UPDATE events SET end_of_list = 'lend_name' WHERE id = %s", (_event(empty_database, name),))
