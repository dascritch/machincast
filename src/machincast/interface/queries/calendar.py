"""Requêtes du calendrier de la grille (https://github.com/dascritch/machincast/issues/442)."""

from datetime import date, datetime

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def airplay(connection: Connection, since: datetime, until: datetime) -> list[TupleRow]:
	"""Les passages commencés dans la période : début, fin, événement à l'antenne (celui qui prête son nom), son nom et
	sa priorité (https://github.com/dascritch/machincast/issues/399)."""
	return connection.execute(
		"SELECT d.logged_at, f.logged_at, e.id, e.internal_name, e.priority::text"
		" FROM airplay d"
		" LEFT JOIN airplay f ON (f.play_id = d.play_id) AND (f.line_type = 'end')"
		" LEFT JOIN events e ON e.id = COALESCE(d.lender_event_id, d.event_id)"
		" WHERE (d.line_type = 'start') AND (d.logged_at >= %s) AND (d.logged_at < %s)"
		" ORDER BY d.logged_at, d.id",
		(since, until),
	).fetchall()


def public_names(connection: Connection) -> list[TupleRow]:
	"""L'identifiant et le nom public de chaque événement."""
	return connection.execute("SELECT id, public_name FROM events").fetchall()


def skip_session(connection: Connection, event: int, day: date) -> None:
	"""Saute la session de ce jour ; déjà sautée, elle le reste."""
	connection.execute("INSERT INTO event_skips (event_id, day) VALUES (%s, %s) ON CONFLICT DO NOTHING", (event, day))


def reinstate_session(connection: Connection, event: int, day: date) -> None:
	"""La session de ce jour de l'événement joue de nouveau (machincast.interface.sessions)."""
	connection.execute("DELETE FROM event_skips WHERE event_id = %s AND day = %s", (event, day))


# ─── Session décalée (https://github.com/dascritch/machincast/issues/631) ───

MOVED = (
	"INSERT INTO events (internal_name, public_name, priority, starts_at, ends_at, hide_metadata, end_of_list,"
	" properties)"
	" SELECT %s, public_name, priority, %s, %s, hide_metadata, end_of_list, properties"
	" FROM events WHERE id = %s RETURNING id"
)


def name_taken(connection: Connection, name: str) -> bool:
	"""Un événement, non supprimé, porte ce nom interne."""
	found = connection.execute(
		"SELECT 1 FROM events WHERE internal_name = %s AND deleted_at IS NULL", (name,)
	).fetchone()
	return found is not None


def copy_event(connection: Connection, event: int, name: str, start: datetime, end: datetime | None) -> int:
	"""Une copie ponctuelle de l'événement, sans jour de récurrence, de ce début et de cette fin : même nom public,
	priorité, masquage, fin de liste et propriétés (secours, plugins), mêmes éléments dans le même ordre. Son
	identifiant."""
	found = connection.execute(MOVED, (name, start, end, event)).fetchone()
	assert found is not None
	copy = int(str(found[0]))
	connection.execute(
		"INSERT INTO event_items (event_id, position, bank_id, sound_id, sequence_id)"
		" SELECT %s, position, bank_id, sound_id, sequence_id FROM event_items WHERE event_id = %s ORDER BY position",
		(copy, event),
	)
	return copy
