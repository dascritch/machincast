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
