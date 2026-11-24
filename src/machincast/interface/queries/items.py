"""Requêtes des listes d'éléments d'une séquence ou d'un événement (https://github.com/dascritch/machincast/issues/442).

La table (sequence_items ou event_items) et sa colonne parente (sequence_id ou event_id) sont des constantes du code de
l'appelant, jamais une saisie."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]

TABLES = {"sound": "sounds", "bank": "banks", "sequence": "sequences"}
PLAYS = {
	"sound": (
		"SELECT s.id, s.artist, s.title, s.location, COALESCE(s.location, s.stream_url, COALESCE(m.url, 'input:' || m.device))"
		" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = ANY(%s)"
	),
	"bank": "SELECT b.id, b.internal_name, b.mode::text, b.no_repeat FROM banks b WHERE b.id = ANY(%s)",
	"sequence": (
		"SELECT q.id, q.internal_name, (SELECT count(*) FROM sequence_items e WHERE e.sequence_id = q.id),"
		" (SELECT e.bank_id FROM sequence_items e WHERE e.sequence_id = q.id ORDER BY e.position LIMIT 1),"
		" (SELECT e.bank_id FROM sequence_items e WHERE e.sequence_id = q.id ORDER BY e.position DESC LIMIT 1)"
		" FROM sequences q WHERE q.id = ANY(%s)"
	),
}
"""Ce que montre la ligne d'un élément, lu par identifiants."""
SOUNDS_PER_FILE = PLAYS["sound"].replace("s.id = ANY(%s)", "s.location = ANY(%s)")
FEED_STREAM = "SELECT id FROM sounds WHERE feed_id = %s AND deleted_at IS NULL ORDER BY title, id LIMIT 1"


def page(
	connection: Connection, table: str, column_parent: str, columns: str, parent: int, after: int, limit: int | None
) -> list[TupleRow]:
	"""Les lignes de la liste qui suivent une position, au plus limit ; leurs colonnes d'éléments sont columns."""
	return connection.execute(
		f"SELECT e.id, e.position, {columns} FROM {table} e"
		f" WHERE e.{column_parent} = %s AND e.position > %s ORDER BY e.position LIMIT %s",
		(parent, after, limit),
	).fetchall()


def tail(connection: Connection, table: str, column_parent: str, parent: int, after: int) -> tuple[int, bool]:
	"""Le nombre de lignes qui restent après cette position, et si l'une est un stream."""
	found = connection.execute(
		f"SELECT count(*), COALESCE(bool_or(s.type = 'stream'), false) FROM {table} e"
		f" LEFT JOIN sounds s ON s.id = e.sound_id WHERE e.{column_parent} = %s AND e.position > %s",
		(parent, after),
	).fetchone()
	assert found is not None
	return int(str(found[0])), bool(found[1])


def existing(connection: Connection, category: str, identifiers: list[int]) -> set[int]:
	"""Ceux de ces éléments d'un genre qui sont en base."""
	found = set()
	for (identifier,) in connection.execute(f"SELECT id FROM {TABLES[category]} WHERE id = ANY(%s)", (identifiers,)):
		found.add(int(str(identifier)))
	return found


def delete_others(connection: Connection, table: str, column_parent: str, parent: int, kept: list[int]) -> None:
	"""La liste ne garde que ces lignes."""
	connection.execute(f"DELETE FROM {table} WHERE {column_parent} = %s AND NOT (id = ANY(%s))", (parent, kept))


def renumber(
	connection: Connection, table: str, column_parent: str, parent: int, lines: list[int], positions: list[int]
) -> None:
	"""Les lignes prennent ces positions ; une ligne n'est jamais reprise d'une autre séquence ou d'un autre événement."""
	connection.execute(
		f"UPDATE {table} e SET position = v.position FROM unnest(%s::bigint[], %s::int[])"
		f" AS v(id, position) WHERE e.id = v.id AND e.{column_parent} = %s",
		(lines, positions, parent),
	)


def insert_new(
	connection: Connection,
	table: str,
	column_parent: str,
	column: str,
	parent: int,
	positions: list[int],
	items: list[int],
) -> None:
	"""Les nouvelles lignes d'un genre, en une requête."""
	connection.execute(
		f"INSERT INTO {table} ({column_parent}, position, {column})"
		" SELECT %s, v.position, v.item FROM unnest(%s::int[], %s::bigint[]) AS v(position, item)",
		(parent, positions, items),
	)


def feed_exists(connection: Connection, feed: int) -> bool:
	return connection.execute("SELECT 1 FROM feeds WHERE id = %s", (feed,)).fetchone() is not None


def feed_stream(connection: Connection, feed: int) -> int | None:
	"""Le stream qui suit ce feed, le premier par titre ; None s'il n'y en a pas."""
	line = connection.execute(FEED_STREAM, (feed,)).fetchone()
	if line is None:
		return None
	return int(str(line[0]))


def create_feed_stream(connection: Connection, feed: int, name: str) -> int:
	"""Le stream actif de ce feed, titré du nom du feed."""
	line = connection.execute(
		"INSERT INTO sounds (type, feed_id, title, state) VALUES ('stream', %s, %s, 'active') RETURNING id",
		(feed, name),
	).fetchone()
	assert line is not None
	return int(str(line[0]))


def feed_marks(connection: Connection, feed: int) -> TupleRow | None:
	"""Le nom et l'adresse du feed ; None s'il est absent."""
	return connection.execute(
		"SELECT name, COALESCE(url, 'input:' || device) FROM feeds WHERE id = %s", (feed,)
	).fetchone()


def no_repeat_banks(connection: Connection) -> dict[int, str]:
	"""Les banques « ne pas répéter », par identifiant, avec leur nom."""
	found = {}
	for identifier, name in connection.execute("SELECT id, internal_name FROM banks WHERE no_repeat").fetchall():
		found[int(str(identifier))] = str(name)
	return found


def plays(connection: Connection, category: str, identifiers: list[int]) -> list[TupleRow]:
	"""Ce que montre la ligne de chaque élément de ce genre."""
	return connection.execute(PLAYS[category], (identifiers,)).fetchall()


def sounds_per_file(connection: Connection, files: list[str]) -> list[TupleRow]:
	return connection.execute(SOUNDS_PER_FILE, (files,)).fetchall()
