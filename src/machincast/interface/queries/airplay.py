"""Requêtes de l'onglet Airplay (machincast.interface.airplay, https://github.com/dascritch/machincast/issues/583)."""

from datetime import datetime

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def plays(connection: Connection, since: datetime | None, count: int | None) -> list[TupleRow]:
	"""Les passages commencés depuis cet instant, ou les derniers, du plus récent au plus ancien, count au plus, avec
	leur événement, celui qui leur prête son nom s'il y en a un, leur séquence et leur banque."""
	return connection.execute(
		"SELECT d.logged_at, f.logged_at, f.played_duration, f.without_incident, d.artist, d.title,"
		" e.internal_name, q.internal_name, b.internal_name, d.sound_id, e.id, q.id, b.id, d.location"
		" FROM airplay d"
		" LEFT JOIN airplay f ON f.play_id = d.play_id AND f.line_type = 'end'"
		" LEFT JOIN events e ON e.id = COALESCE(d.lender_event_id, d.event_id)"
		" LEFT JOIN sequences q ON q.id = d.sequence_id"
		" LEFT JOIN banks b ON b.id = d.bank_id"
		" WHERE d.line_type = 'start' AND (%s::timestamptz IS NULL OR d.logged_at >= %s::timestamptz)"
		" ORDER BY d.logged_at DESC, d.id DESC LIMIT %s",
		(since, since, count),
	).fetchall()
