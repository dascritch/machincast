"""Requête de l'écran des incidents (https://github.com/dascritch/machincast/issues/442)."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def log_lines(connection: Connection, levels: list[str], limit: int) -> list[TupleRow]:
	"""Les dernières lignes du log de ces niveaux, avec le sonore, la banque et l'événement cités ; dans une
	transaction."""
	return connection.execute(
		"SELECT l.logged_at, l.level::text, l.kind, l.message, s.id, s.artist, s.title, s.location,"
		" COALESCE(s.stream_url, m.url), b.id, b.internal_name, e.id, e.internal_name FROM log l"
		" LEFT JOIN sounds s ON s.id = l.sound_id"
		" LEFT JOIN feeds m ON m.id = s.feed_id"
		" LEFT JOIN banks b ON b.id = l.bank_id LEFT JOIN events e ON e.id = l.event_id"
		" WHERE l.level::text = ANY(%s) ORDER BY l.logged_at DESC, l.id DESC LIMIT %s",
		(levels, limit),
	).fetchall()
