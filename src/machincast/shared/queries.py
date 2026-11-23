"""Les requêtes SQL communes à plusieurs binaires, toutes ici (https://github.com/dascritch/machincast/issues/583) :
la grille, que lisent Machin player, l'interface et l'intranet (machincast.shared.grid), et le démarrage précédent d'un
binaire, que Machin player et Machin indexer vérifient (machincast.runs). Sans Qt ni GStreamer ; l'appelant ouvre la
transaction.
"""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]

EVENT_COLUMNS = (
	"id, internal_name, priority::text, starts_at, ends_at, recurrence_days::text[], modified_at, deleted_at,"
	" ARRAY(SELECT s.day FROM event_skips s WHERE s.event_id = events.id), end_of_list::text,"
	" (properties ->> 'end_fallback_event')::bigint, (properties ->> 'stream_fallback_event')::bigint"
)
"""Ce que la grille lit d'un événement (machincast.shared.grid._events), ses sessions sautées comprises."""


def grid_events(connection: Connection, *, deleted_list: bool) -> list[TupleRow]:
	"""Les événements de la grille, sans les événements de secours ; les supprimés aussi, avec deleted_list."""
	condition = "deleted_at IS NULL"
	if deleted_list:
		condition = "TRUE"
	return connection.execute(
		f"SELECT {EVENT_COLUMNS} FROM events WHERE priority <> 'fallback' AND {condition} ORDER BY id"
	).fetchall()


def event(connection: Connection, identifier: int) -> list[TupleRow]:
	"""Un événement, quelle que soit sa priorité."""
	return connection.execute(f"SELECT {EVENT_COLUMNS} FROM events WHERE id = %s", (identifier,)).fetchall()


def previous_start(connection: Connection, program: str) -> TupleRow | None:
	"""Le démarrage précédent de ce binaire : son instant, son PID, et s'il a une fin
	(machincast_previous_start, SECURITY DEFINER, https://github.com/dascritch/machincast/issues/341)."""
	return connection.execute("SELECT started_at, pid, ended FROM machincast_previous_start(%s)", (program,)).fetchone()
