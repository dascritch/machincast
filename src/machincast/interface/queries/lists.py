"""Requêtes des listes de l'interface : sonores, banques, séquences, événements et feeds (https://github.com/dascritch/machincast/issues/442)."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]

STREAMS_CALLED = (
	"SELECT EXISTS (SELECT 1 FROM sounds s WHERE s.type = 'stream' AND s.deleted_at IS NULL AND (s.id = ANY(%s)"
	" OR s.id IN (SELECT b.sound_id FROM bank_sounds b WHERE b.bank_id = ANY(%s))"
	" OR s.id IN (SELECT q.sound_id FROM sequence_items q WHERE q.sequence_id = ANY(%s))"
	" OR s.id IN (SELECT b.sound_id FROM sequence_items q JOIN bank_sounds b ON b.bank_id = q.bank_id"
	" WHERE q.sequence_id = ANY(%s))))"
)
"""Un stream parmi des sonores, des banques et des séquences, en une requête : les sonores, les banques, et deux fois
les séquences."""
EVENT_CALLS_STREAM = (
	"EXISTS (SELECT 1 FROM event_items x LEFT JOIN sequence_items q ON q.sequence_id = x.sequence_id"
	" LEFT JOIN bank_sounds b ON b.bank_id IN (x.bank_id, q.bank_id)"
	" JOIN sounds s ON s.id IN (x.sound_id, q.sound_id, b.sound_id)"
	" WHERE x.event_id = e.id AND s.type = 'stream' AND s.deleted_at IS NULL)"
)
"""L'événement e fait appel à un stream, directement, par une banque ou par une séquence."""
SOUND_FIELDS = (
	"s.id, s.artist, s.title, s.type::text, s.state::text, s.audit_requested, s.duration,"
	" COALESCE(s.location, s.stream_url, m.url)"
)
SOUND_TABLES = "FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.deleted_at IS NULL"
SOUND_ORDER = "s.artist NULLS LAST, s.title, s.id"
"""L'ordre de la base, avant tout clic sur un titre de colonne."""
SOUND_LOCATION = "COALESCE(s.location, s.stream_url, m.url)"


def streams_called(connection: Connection, sounds: list[int], banks: list[int], sequences: list[int]) -> bool:
	"""Un stream parmi ces sonores, dans ces banques, ou dans ces séquences et leurs banques ; dans une transaction."""
	line = connection.execute(STREAMS_CALLED, (sounds, banks, sequences, sequences)).fetchone()
	return (line is not None) and (bool(line[0]))


def sounds(connection: Connection) -> list[TupleRow]:
	"""Les sonores non supprimés, dans l'ordre de la base."""
	return connection.execute(f"SELECT {SOUND_FIELDS} {SOUND_TABLES} ORDER BY {SOUND_ORDER}").fetchall()


def sound_counts(connection: Connection, where: str, values: list[object], anomalies: list[str]) -> TupleRow:
	"""Les sonores qui passent le filtre, ceux d'entre eux en anomalie, et tous ; where et ses values sont du code."""
	counts = connection.execute(
		f"SELECT count(*) FILTER (WHERE {where}), count(*) FILTER (WHERE ({where}) AND s.state::text = ANY(%s)),"
		f" count(*) {SOUND_TABLES}",
		[*values, *values, anomalies],
	).fetchone()
	assert counts is not None
	return counts


def sound_page(
	connection: Connection, where: str, values: list[object], order: str, limit: int, offset: int
) -> list[TupleRow]:
	"""Une page des sonores qui passent le filtre ; where, order et leurs values sont du code, jamais une saisie."""
	return connection.execute(
		f"SELECT {SOUND_FIELDS} {SOUND_TABLES} AND ({where}) ORDER BY {order} LIMIT %s OFFSET %s",
		[*values, limit, offset],
	).fetchall()


def banks(connection: Connection) -> list[TupleRow]:
	"""Les banques non supprimées, par nom, avec leur premier répertoire et leurs sonores en anomalie."""
	return connection.execute(
		"SELECT b.id, b.internal_name, b.public_name, b.mode::text, b.no_repeat,"
		" (SELECT min(r.directory) FROM bank_directories r WHERE r.bank_id = b.id),"
		" NOT EXISTS (SELECT 1 FROM bank_sounds x JOIN sounds s ON s.id = x.sound_id"
		" WHERE x.bank_id = b.id AND s.state = 'active' AND s.deleted_at IS NULL),"
		" (SELECT count(*) FROM bank_sounds x JOIN sounds s ON s.id = x.sound_id"
		" WHERE x.bank_id = b.id AND s.state IN ('corrupt', 'unsupported') AND s.deleted_at IS NULL)"
		" FROM banks b WHERE b.deleted_at IS NULL ORDER BY b.internal_name, b.id"
	).fetchall()


def sequences(connection: Connection) -> list[TupleRow]:
	"""Les séquences non supprimées, par nom, avec si elles sont vides."""
	return connection.execute(
		"SELECT q.id, q.internal_name, q.public_name,"
		" NOT EXISTS (SELECT 1 FROM sequence_items e WHERE e.sequence_id = q.id)"
		" FROM sequences q WHERE q.deleted_at IS NULL ORDER BY q.internal_name, q.id"
	).fetchall()


def feeds(connection: Connection) -> list[TupleRow]:
	"""Les feeds, par nom, avec le nombre de streams qui suivent chacun."""
	return connection.execute(
		"SELECT m.id, m.name, m.url,"
		" (SELECT count(*) FROM sounds s WHERE s.feed_id = m.id AND s.deleted_at IS NULL)"
		" FROM feeds m ORDER BY m.name, m.id"
	).fetchall()


def events(connection: Connection) -> list[TupleRow]:
	"""Du plus prioritaire au moins prioritaire, puis par nom."""
	return connection.execute(
		"SELECT e.id, e.internal_name, e.public_name, e.priority::text, e.starts_at, e.ends_at,"
		" e.recurrence_days::text[],"
		# Une liste vide qui prête son nom n'est pas une anomalie (https://github.com/dascritch/machincast/issues/399).
		" NOT EXISTS (SELECT 1 FROM event_items x WHERE x.event_id = e.id) AND e.end_of_list <> 'lend_name',"
		# Un secours non local (https://github.com/dascritch/machincast/issues/403).
		f" e.priority = 'fallback' AND {EVENT_CALLS_STREAM}"
		# e.priorite : l'ordre du type énuméré, pas celui du texte de la colonne affichée.
		" FROM events e WHERE e.deleted_at IS NULL ORDER BY e.priority DESC, e.internal_name, e.id"
	).fetchall()
