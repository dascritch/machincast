"""Requêtes de la fiche d'un événement (https://github.com/dascritch/machincast/issues/442)."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def read_event(connection: Connection, event: int) -> TupleRow | None:
	"""Les champs de l'événement, dans l'ordre de la fiche ; None s'il est absent."""
	return connection.execute(
		"SELECT internal_name, public_name, priority::text, starts_at, ends_at, recurrence_days::text[],"
		" hide_metadata, end_of_list::text, end_fallback_event_id, stream_fallback_event_id"
		" FROM events WHERE id = %s",
		(event,),
	).fetchone()


def fallbacks(connection: Connection, except_event: int | None) -> list[TupleRow]:
	"""Les événements de secours, non supprimés, par nom, sauf celui-ci."""
	return connection.execute(
		"SELECT id, internal_name FROM events WHERE priority = 'fallback' AND deleted_at IS NULL"
		" AND id IS DISTINCT FROM %s ORDER BY internal_name",
		(except_event,),
	).fetchall()


def any_stream(connection: Connection, sounds: list[int]) -> bool:
	"""L'un de ces sonores est un stream."""
	found = connection.execute(
		"SELECT 1 FROM sounds WHERE type = 'stream' AND id = ANY(%s) LIMIT 1", (sounds,)
	).fetchone()
	return found is not None


def name_taken(connection: Connection, name: str, identifier: int | None) -> bool:
	"""Un autre événement, non supprimé, porte ce nom interne."""
	taken = connection.execute(
		"SELECT 1 FROM events WHERE internal_name = %s AND id IS DISTINCT FROM %s AND deleted_at IS NULL",
		(name, identifier),
	).fetchone()
	return taken is not None


def insert(connection: Connection, values: tuple[object, ...]) -> int:
	"""Crée l'événement de ces dix valeurs, dans l'ordre de la fiche ; son identifiant."""
	created = connection.execute(
		"INSERT INTO events"
		" (internal_name, public_name, priority, starts_at, ends_at, recurrence_days, hide_metadata,"
		" end_of_list, end_fallback_event_id, stream_fallback_event_id)"
		" VALUES (%s, %s, %s, %s, %s, %s::weekday[], %s, %s, %s, %s) RETURNING id",
		values,
	).fetchone()
	assert created is not None
	return int(str(created[0]))


def update(connection: Connection, identifier: int, values: tuple[object, ...]) -> None:
	connection.execute(
		"UPDATE events SET internal_name = %s, public_name = %s, priority = %s, starts_at = %s, ends_at = %s,"
		" recurrence_days = %s::weekday[], hide_metadata = %s, end_of_list = %s, end_fallback_event_id = %s,"
		" stream_fallback_event_id = %s WHERE id = %s",
		(*values, identifier),
	)


def skips(connection: Connection, event: int) -> list[TupleRow]:
	"""Les jours des sessions sautées de l'événement."""
	return connection.execute("SELECT day FROM event_skips WHERE event_id = %s", (event,)).fetchall()


def streams_with_fallback(connection: Connection, event: int) -> list[TupleRow]:
	"""Les streams qui désignent cet événement pour secours, par nom."""
	return connection.execute(
		"SELECT COALESCE(title, stream_url) FROM sounds WHERE fallback_event_id = %s ORDER BY 1", (event,)
	).fetchall()


def events_with_fallback(connection: Connection, event: int) -> list[TupleRow]:
	"""Les événements, non supprimés, qui désignent cet événement pour secours, par nom."""
	return connection.execute(
		"SELECT internal_name FROM events WHERE (end_fallback_event_id = %s OR stream_fallback_event_id = %s)"
		" AND deleted_at IS NULL ORDER BY 1",
		(event, event),
	).fetchall()


def fallback_events(connection: Connection) -> list[TupleRow]:
	"""Les événements de secours, non supprimés, par nom puis identifiant."""
	return connection.execute(
		"SELECT id, internal_name FROM events WHERE priority = 'fallback' AND deleted_at IS NULL"
		" ORDER BY internal_name, id"
	).fetchall()


def background_programming_exists(connection: Connection) -> bool:
	"""Un fil musical non supprimé existe (machincast.interface.background_programming)."""
	return (
		connection.execute(
			"SELECT 1 FROM events WHERE priority = 'background_programming' AND deleted_at IS NULL LIMIT 1"
		).fetchone()
		is not None
	)


def names_like(connection: Connection, name: str) -> list[TupleRow]:
	"""Les noms des événements non supprimés qui sont ce nom, ou ce nom suivi d'une espace et d'autre chose."""
	return connection.execute(
		"SELECT internal_name FROM events WHERE (internal_name = %s OR internal_name LIKE %s || ' %%')"
		" AND deleted_at IS NULL",
		(name, name),
	).fetchall()


def insert_background_programming(connection: Connection, name: str) -> None:
	"""Un fil musical permanent et vide, à ce nom."""
	connection.execute("INSERT INTO events (internal_name, priority) VALUES (%s, 'background_programming')", (name,))
