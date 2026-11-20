"""Les lectures de l'API de l'intranet (https://github.com/dascritch/machincast/issues/540), au rôle
machincast_intranet, qui ne fait que lire.

Chaque fonction rend des objets prêts pour JSON : dictionnaires, listes, textes, nombres, dates, que l'API sérialise
(machincast.intranet.api.dumps). Les listes se lisent par pages, triées par identifiant : `after` le dernier
identifiant reçu, `limit` lignes au plus. Un élément supprimé n'est pas dans les listes ; sa fiche se lit encore,
`deleted_at` renseigné.
"""

from typing import Any

import psycopg
from psycopg.rows import TupleRow, dict_row

Connection = psycopg.Connection[TupleRow]
Row = dict[str, Any]

LISTS = {
	"sounds": (
		"SELECT id, type::text, artist, title, location, stream_url, state::text, duration, modified_at FROM sounds"
	),
	"banks": "SELECT id, internal_name, public_name, mode::text, no_repeat, modified_at FROM banks",
	"sequences": "SELECT id, internal_name, public_name, modified_at FROM sequences",
	"events": (
		"SELECT id, internal_name, public_name, priority::text, starts_at, ends_at,"
		" recurrence_days::text[] AS recurrence_days, modified_at FROM events"
	),
}
"""Chaque liste, par son nom dans l'adresse de l'API."""
CARDS = {
	"sounds": "SELECT *, type::text AS type, state::text AS state FROM sounds WHERE id = %s",
	"banks": "SELECT *, mode::text AS mode FROM banks WHERE id = %s",
	"sequences": "SELECT * FROM sequences WHERE id = %s",
	"events": (
		"SELECT *, priority::text AS priority, recurrence_days::text[] AS recurrence_days, end_of_list::text AS"
		" end_of_list FROM events WHERE id = %s"
	),
}
HIDDEN = frozenset({"edited_fields"})
"""Ce qu'une fiche de l'API ne dit pas : la cuisine de l'indexation."""
ITEMS = {
	"events": (
		"SELECT i.position, i.sound_id, i.bank_id, i.sequence_id,"
		" COALESCE(NULLIF(concat_ws(' – ', s.artist, s.title), ''), s.location, b.internal_name, q.internal_name)"
		" AS name FROM event_items i LEFT JOIN sounds s ON s.id = i.sound_id LEFT JOIN banks b ON b.id = i.bank_id"
		" LEFT JOIN sequences q ON q.id = i.sequence_id WHERE i.event_id = %s ORDER BY i.position"
	),
	"sequences": (
		"SELECT i.position, i.sound_id, i.bank_id,"
		" COALESCE(NULLIF(concat_ws(' – ', s.artist, s.title), ''), s.location, b.internal_name) AS name"
		" FROM sequence_items i LEFT JOIN sounds s ON s.id = i.sound_id LEFT JOIN banks b ON b.id = i.bank_id"
		" WHERE i.sequence_id = %s ORDER BY i.position"
	),
	"banks": (
		"SELECT l.position, l.sound_id, COALESCE(NULLIF(concat_ws(' – ', s.artist, s.title), ''), s.location) AS name,"
		" s.state::text AS state FROM bank_sounds l JOIN sounds s ON s.id = l.sound_id WHERE l.bank_id = %s"
		" ORDER BY l.position"
	),
}
DEFAULT_LIMIT = 100
MAXIMUM_LIMIT = 1000
INCIDENTS = 100
"""Incidents lus au plus, les plus récents."""
PLAYS = 5


def _rows(connection: Connection, query: str, parameters: tuple[object, ...]) -> list[Row]:
	with connection.transaction(), connection.cursor(row_factory=dict_row) as cursor:
		return list(cursor.execute(query, parameters).fetchall())


def page(connection: Connection, kind: str, after: int, limit: int) -> list[Row]:
	"""Une page d'une liste : les éléments non supprimés d'identifiant plus grand que after."""
	return _rows(connection, f"{LISTS[kind]} WHERE deleted_at IS NULL AND id > %s ORDER BY id LIMIT %s", (after, limit))


def card(connection: Connection, kind: str, identifier: int) -> Row | None:
	"""La fiche d'un élément, ses éléments ou ses sonores compris ; None s'il n'existe pas."""
	found = _rows(connection, CARDS[kind], (identifier,))
	if found == []:
		return None
	fields: Row = {}
	for name, value in found[0].items():
		if name not in HIDDEN:
			fields[name] = value
	if kind in ITEMS:
		fields["items"] = _rows(connection, ITEMS[kind], (identifier,))
	if kind == "banks":
		fields["directories"] = _rows(
			connection,
			"SELECT directory, scanned_at FROM bank_directories WHERE bank_id = %s ORDER BY directory",
			(identifier,),
		)
	return fields


def incidents(connection: Connection, count: int = INCIDENTS) -> list[Row]:
	"""Les incidents seulement, les plus récents en tête, avec ce qu'ils concernent."""
	return _rows(
		connection,
		"SELECT l.id, l.logged_at, l.kind, l.message, l.sound_id, l.bank_id, l.event_id,"
		" COALESCE(NULLIF(concat_ws(' – ', s.artist, s.title), ''), s.location) AS sound, b.internal_name AS bank,"
		" e.internal_name AS event FROM log l LEFT JOIN sounds s ON s.id = l.sound_id"
		" LEFT JOIN banks b ON b.id = l.bank_id LEFT JOIN events e ON e.id = l.event_id"
		" WHERE l.level = 'incident' ORDER BY l.logged_at DESC, l.id DESC LIMIT %s",
		(count,),
	)


def previous_plays(connection: Connection, count: int = PLAYS) -> list[Row]:
	"""Les derniers passages terminés, le plus récent en tête : début, fin, et ce qui les a joués."""
	return _rows(
		connection,
		"SELECT d.sound_id, d.artist, d.title, d.location, d.logged_at AS start, f.logged_at AS end,"
		" f.played_duration AS duration, d.event_id, e.internal_name AS event, d.sequence_id,"
		" q.internal_name AS sequence, d.bank_id, b.internal_name AS bank FROM airplay d"
		" JOIN airplay f ON f.play_id = d.play_id AND f.line_type = 'end'"
		" LEFT JOIN events e ON e.id = COALESCE(d.lender_event_id, d.event_id)"
		" LEFT JOIN sequences q ON q.id = d.sequence_id LEFT JOIN banks b ON b.id = d.bank_id"
		" WHERE d.line_type = 'start' ORDER BY d.logged_at DESC, d.id DESC LIMIT %s",
		(count,),
	)
