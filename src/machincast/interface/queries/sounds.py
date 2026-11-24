"""Requêtes de la fiche d'un sonore (https://github.com/dascritch/machincast/issues/442)."""

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

Connection = psycopg.Connection[TupleRow]

RELATION_LISTS = {
	"sequence": ("sequence_items", "sequence_id"),
	"bank": ("bank_sounds", "bank_id"),
	"event": ("event_items", "event_id"),
}


def feeds(connection: Connection) -> list[TupleRow]:
	"""Les feeds, par nom : identifiant, nom, adresse."""
	return connection.execute("SELECT id, name, COALESCE(url, 'input:' || device) FROM feeds ORDER BY name").fetchall()


def fallback_events(connection: Connection) -> list[TupleRow]:
	"""Les événements de secours, non supprimés, par nom."""
	return connection.execute(
		"SELECT id, internal_name FROM events WHERE priority = 'fallback' AND deleted_at IS NULL ORDER BY internal_name"
	).fetchall()


def read_sound(connection: Connection, sound: int) -> TupleRow | None:
	return connection.execute(
		"SELECT s.type::text, s.location, s.stream_url, s.feed_id, COALESCE(m.url, 'input:' || m.device), s.fallback_event_id,"
		" s.artist, s.title, s.music_metadata, s.crossfade_start, s.crossfade_end, s.max_plays,"
		" s.state::text, s.hide_metadata, s.duration, s.broadcast_start, s.broadcast_end, s.edited_fields,"
		" s.mime_type, s.checked_at, s.silence_detection, s.detected_start, s.detected_end,"
		" s.audited_at IS NOT NULL"
		" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
		(sound,),
	).fetchone()


def insert_stream(connection: Connection, stream_url: object, feed: object) -> int:
	"""Un nouveau stream entre en base avec son adresse ; ses autres champs s'écrivent comme une modification."""
	created = connection.execute(
		"INSERT INTO sounds (type, stream_url, feed_id, state) VALUES ('stream', %s, %s, 'active') RETURNING id",
		(stream_url, feed),
	).fetchone()
	assert created is not None
	return int(str(created[0]))


def forget_edited(connection: Connection, sound: int, fields: list[str]) -> None:
	"""Ces champs ne sont plus saisis à la main : l'indexeur les remplit de nouveau
	(https://github.com/dascritch/machincast/issues/388)."""
	connection.execute(
		"UPDATE sounds SET edited_fields = ARRAY(SELECT field FROM unnest(edited_fields) AS field"
		" WHERE NOT field = ANY(%s)) WHERE id = %s",
		(fields, sound),
	)


def edited_fields(connection: Connection, sound: int) -> list[str] | None:
	"""Les champs que l'indexeur ne change plus, verrouillés pour la modification ; None si le sonore est absent."""
	line = connection.execute("SELECT edited_fields FROM sounds WHERE id = %s FOR UPDATE", (sound,)).fetchone()
	if line is None:
		return None
	return list((line[0]) or ([]))


def update_fields(
	connection: Connection,
	sound: int,
	columns: list[str],
	values: list[object],
	musical: dict[str, object],
	edited: list[str],
) -> None:
	"""Écrit ces colonnes, les métadonnées musicales (une valeur None retire la clé) et les champs édités."""
	assignments: list[sql.Composable] = []
	for assigned in columns:
		assignments.append(sql.SQL("{} = %s").format(sql.Identifier(assigned)))
	assignments.append(sql.SQL("music_metadata = (music_metadata - %s::text[]) || %s::jsonb"))
	key_dict = {}
	for key, value in musical.items():
		if value is not None:
			key_dict[key] = value
	assignments.append(sql.SQL("edited_fields = %s"))
	query = sql.SQL("UPDATE sounds SET {} WHERE id = %s").format(sql.SQL(", ").join(assignments))
	connection.execute(query, [*values, list(musical), Jsonb(key_dict), edited, sound])


def remove_relation(connection: Connection, category: str, item: int, sound: int) -> None:
	"""Retire le sonore de la liste de cette séquence, banque ou cet événement."""
	table, column = RELATION_LISTS[category]
	connection.execute(
		sql.SQL("DELETE FROM {} WHERE {} = %s AND sound_id = %s").format(sql.Identifier(table), sql.Identifier(column)),
		(item, sound),
	)


def relations(connection: Connection, sound: int) -> list[TupleRow]:
	"""Les séquences, banques et événements dont la liste cite le sonore."""
	return connection.execute(
		"SELECT category, id, name, minimum, maximum, (SELECT duration FROM sounds WHERE id = %s) FROM ("
		" SELECT 1 AS rank, 'sequence' AS category, q.id, q.internal_name AS name, NULL::interval AS minimum,"
		"  NULL::interval AS maximum FROM sequences q"
		"  WHERE q.deleted_at IS NULL"
		"  AND EXISTS (SELECT 1 FROM sequence_items x WHERE x.sequence_id = q.id AND x.sound_id = %s)"
		" UNION ALL SELECT 2, 'bank', b.id, b.internal_name, b.min_duration, b.max_duration FROM banks b"
		"  WHERE b.deleted_at IS NULL"
		"  AND EXISTS (SELECT 1 FROM bank_sounds x WHERE x.bank_id = b.id AND x.sound_id = %s)"
		" UNION ALL SELECT 3, 'event', e.id, e.internal_name, NULL, NULL FROM events e"
		"  WHERE e.deleted_at IS NULL"
		"  AND EXISTS (SELECT 1 FROM event_items x WHERE x.event_id = e.id AND x.sound_id = %s)"
		") r ORDER BY rank, name, id",
		(sound, sound, sound, sound),
	).fetchall()


def bank_directories(connection: Connection, bank: int) -> list[TupleRow]:
	"""Les répertoires de la banque, par nom."""
	return connection.execute(
		"SELECT directory FROM bank_directories WHERE bank_id = %s ORDER BY directory", (bank,)
	).fetchall()


def plays(connection: Connection, sound: int, limit: int) -> list[TupleRow]:
	"""Les derniers passages, avec les alertes et incidents du log pendant chacun."""
	return connection.execute(
		"SELECT d.logged_at, f.logged_at, f.played_duration, e.internal_name, q.internal_name,"
		" b.internal_name, i.horodatages, i.natures, i.messages"
		" FROM airplay d"
		" LEFT JOIN airplay f ON f.play_id = d.play_id AND f.line_type = 'end'"
		" LEFT JOIN events e ON e.id = COALESCE(d.lender_event_id, d.event_id)"
		" LEFT JOIN sequences q ON q.id = d.sequence_id"
		" LEFT JOIN banks b ON b.id = d.bank_id"
		" LEFT JOIN LATERAL ("
		"  SELECT array_agg(l.logged_at ORDER BY l.logged_at, l.id) AS horodatages,"
		"   array_agg(l.kind::text ORDER BY l.logged_at, l.id) AS natures,"
		"   array_agg(l.message ORDER BY l.logged_at, l.id) AS messages"
		"  FROM log l WHERE l.sound_id = d.sound_id AND l.level <> 'info' AND l.logged_at >= d.logged_at"
		"   AND (f.logged_at IS NULL OR l.logged_at <= f.logged_at)"
		" ) i ON true"
		" WHERE d.line_type = 'start' AND d.sound_id = %s"
		" ORDER BY d.logged_at DESC, d.id DESC LIMIT %s",
		(sound, limit),
	).fetchall()


def states(connection: Connection, identifiers: list[int]) -> list[TupleRow]:
	"""Artiste, titre, emplacement et état de ces sonores, par identifiant."""
	return connection.execute(
		"SELECT artist, title, location, state::text FROM sounds WHERE id = ANY(%s) ORDER BY id", (identifiers,)
	).fetchall()


def plan_row(connection: Connection, bank: int | None, sound: int) -> TupleRow | None:
	"""Ce qui place un fichier comme la diffusion le joue, fourni par cette banque ou sans banque ; None si le sonore
	est absent (https://github.com/dascritch/machincast/issues/230)."""
	return connection.execute(
		"SELECT s.type::text, s.duration, s.detected_start, s.detected_end,"
		" s.silence_detection OR coalesce(b.silence_detection, false), s.crossfade_start, s.crossfade_end,"
		" s.audited_at IS NOT NULL, b.crossfade_start_rule::text, b.crossfade_start, b.crossfade_end_rule::text,"
		" b.crossfade_end"
		" FROM sounds s LEFT JOIN banks b ON b.id = %s WHERE s.id = %s",
		(bank, sound),
	).fetchone()


def preview_row(connection: Connection, sound: int) -> TupleRow | None:
	"""Ce que la pré-écoute sait du sonore ; None s'il est absent."""
	return connection.execute(
		"SELECT s.type::text, s.location, coalesce(s.stream_url, COALESCE(m.url, 'input:' || m.device)), s.artist, s.title,"
		" extract(epoch FROM s.duration), s.duration, s.detected_start, s.detected_end, s.silence_detection,"
		" s.crossfade_start, s.crossfade_end, s.audited_at IS NOT NULL"
		" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
		(sound,),
	).fetchone()


def present_file(connection: Connection, location: str) -> TupleRow | None:
	"""Le sonore non supprimé de ce fichier (machincast.interface.adding)."""
	return connection.execute(
		"SELECT id FROM sounds WHERE location = %s AND deleted_at IS NULL", (location,)
	).fetchone()


def insert_preview(connection: Connection, location: str) -> int:
	"""Un nouveau sonore pour ce fichier, en aperçu ; son identifiant (machincast.interface.adding)."""
	created = connection.execute(
		"INSERT INTO sounds (type, location, state) VALUES ('file', %s, 'preview') RETURNING id", (location,)
	).fetchone()
	assert created is not None
	return int(str(created[0]))
