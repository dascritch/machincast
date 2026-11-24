"""Les requêtes SQL de Machin player, toutes ici (https://github.com/dascritch/machincast/issues/583).

Chaque fonction prend la connexion, au rôle machincast_player (machincast.database.open_connection), et ses
paramètres, exécute une requête, et rend ses lignes telles quelles ; l'appelant ouvre la transaction et en tire ses
objets. Ce que la lecture lit et écrit en base se relit ici d'un coup, à comparer à la matrice des droits
(tests/features/roles.feature) : elle écrit dans `airplay` et `log` par des insertions seulement, et dans `sounds` le
seul état `expired`.
"""

import uuid
from collections.abc import Collection
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]

# ─── Sonores ───


def file_audit(connection: Connection, sound: int) -> TupleRow | None:
	"""L'emplacement d'un sonore, son dernier audit complet, et la date et la taille de son fichier en base."""
	return connection.execute(
		"SELECT location, audited_at, file_modified_at, file_size FROM sounds WHERE id = %s", (sound,)
	).fetchone()


def file_on_record(connection: Connection, sound: int) -> TupleRow | None:
	"""L'emplacement d'un sonore, et la date et la taille de son fichier en base, avant de le jouer."""
	return connection.execute(
		"SELECT location, file_modified_at, file_size FROM sounds WHERE id = %s", (sound,)
	).fetchone()


def health(connection: Connection, sound: int) -> TupleRow | None:
	"""Le type, l'état et l'emplacement d'un sonore, et si son dernier passage s'est terminé sans incident."""
	return connection.execute(
		"SELECT s.type::text, s.state::text, s.location,"
		" (SELECT f.without_incident FROM airplay f WHERE f.sound_id = s.id AND f.line_type = 'end'"
		" ORDER BY f.logged_at DESC, f.id DESC LIMIT 1)"
		" FROM sounds s WHERE s.id = %s",
		(sound,),
	).fetchone()


def sound_name(connection: Connection, sound: int) -> TupleRow | None:
	"""Le titre d'un sonore, sinon son emplacement."""
	return connection.execute(
		"SELECT COALESCE(title, location, stream_url) FROM sounds WHERE id = %s", (sound,)
	).fetchone()


def sound_metadata(connection: Connection, sound: int) -> TupleRow | None:
	"""L'artiste, le titre et l'emplacement d'un sonore, comme les recopie l'airplay."""
	return connection.execute(
		"SELECT s.artist, s.title, COALESCE(s.location, s.stream_url, m.url) FROM sounds s"
		" LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
		(sound,),
	).fetchone()


def playing_parameters(connection: Connection, bank: int | None, sound: int) -> TupleRow | None:
	"""Ce qu'il faut pour jouer un sonore, avec les crossfades et la détection de silence de la banque qui l'a fourni."""
	return connection.execute(
		"SELECT s.duration, s.crossfade_start, s.crossfade_end, s.type::text, COALESCE(s.stream_url, m.url),"
		" s.fallback_event_id, s.artist, s.title, COALESCE(s.location, s.stream_url, m.url),"
		" s.silence_detection OR COALESCE(b.silence_detection, false), s.detected_start, s.detected_end,"
		" b.crossfade_start_rule::text, b.crossfade_start, b.crossfade_end_rule::text, b.crossfade_end,"
		" CASE WHEN NOT starts_with(m.url, 'input:') THEN m.buffer_duration END"
		" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id"
		" LEFT JOIN banks b ON b.id = %s"
		" WHERE s.id = %s",
		(bank, sound),
	).fetchone()


def expire_sounds(connection: Connection, instant: datetime, sound: int | None) -> list[TupleRow]:
	"""Passe à l'état expired les sonores actifs arrivés au bout, tous, ou ce seul sonore ; rend chacun, son nom, son
	maximum de lectures, ses lectures et sa fin de diffusion."""
	return connection.execute(
		"WITH candidats AS ("
		" SELECT s.id, s.max_plays, s.broadcast_end,"
		" (SELECT count(*) FROM airplay a WHERE a.sound_id = s.id AND a.line_type = 'start') AS lectures"
		" FROM sounds s WHERE s.state = 'active' AND s.deleted_at IS NULL"
		" AND (%s::bigint IS NULL OR s.id = %s::bigint)"
		" AND (s.broadcast_end <= %s OR s.max_plays IS NOT NULL))"
		" UPDATE sounds s SET state = 'expired' FROM candidats c"
		" WHERE s.id = c.id AND (c.broadcast_end <= %s OR c.lectures >= c.max_plays)"
		" RETURNING s.id, COALESCE(s.title, s.location, s.stream_url), c.max_plays, c.lectures,"
		" c.broadcast_end",
		(sound, sound, instant, instant),
	).fetchall()


def expiry_candidates(connection: Connection, instant: datetime, sound: int | None) -> list[TupleRow]:
	"""Les sonores actifs qui pourraient expirer, pour la simulation, qui n'écrit rien."""
	return connection.execute(
		"SELECT id, max_plays, broadcast_end, COALESCE(title, location, stream_url) FROM sounds"
		" WHERE state = 'active' AND (%s::bigint IS NULL OR id = %s::bigint)"
		" AND (broadcast_end <= %s OR max_plays IS NOT NULL)",
		(sound, sound, instant),
	).fetchall()


def sound_hidings(connection: Connection, sounds: list[int]) -> list[TupleRow]:
	"""Le masquage de l'artiste et du titre de chacun de ces sonores."""
	return connection.execute("SELECT id, hide_metadata FROM sounds WHERE id = ANY(%s)", (sounds,)).fetchall()


# ─── Banques ───

CANDIDATE = (
	"SELECT s.id, s.state::text, s.broadcast_start, s.broadcast_end, s.max_plays, COALESCE(s.location, s.stream_url)"
)


def bank_candidates(connection: Connection, bank: int) -> list[TupleRow]:
	"""Les sonores d'une banque, dans leur ordre, avec ce qui dit s'ils sont jouables."""
	return connection.execute(
		f"{CANDIDATE} FROM bank_sounds bs JOIN sounds s ON s.id = bs.sound_id WHERE bs.bank_id = %s ORDER BY bs.position",
		(bank,),
	).fetchall()


def sound_candidate(connection: Connection, sound: int) -> list[TupleRow]:
	"""Un sonore placé directement dans un événement, avec ce qui dit s'il est jouable."""
	return connection.execute(f"{CANDIDATE} FROM sounds s WHERE s.id = %s", (sound,)).fetchall()


def bank_mode(connection: Connection, bank: int) -> TupleRow | None:
	return connection.execute("SELECT mode::text FROM banks WHERE id = %s", (bank,)).fetchone()


def no_repeat_bank(connection: Connection, bank: int) -> TupleRow | None:
	"""Le nom de la banque, si elle est marquée « ne pas répéter »."""
	return connection.execute("SELECT internal_name FROM banks WHERE id = %s AND no_repeat", (bank,)).fetchone()


def bank_name(connection: Connection, bank: int | None) -> TupleRow | None:
	"""Le nom d'une banque qui n'est pas supprimée."""
	return connection.execute(
		"SELECT internal_name FROM banks WHERE id = %s AND deleted_at IS NULL", (bank,)
	).fetchone()


def bank_hidings(connection: Connection, banks: list[int | None]) -> list[TupleRow]:
	"""Le nom, le nom public et le masquage de chacune de ces banques."""
	return connection.execute(
		"SELECT id, internal_name, public_name, hide_metadata FROM banks WHERE id = ANY(%s)", (banks,)
	).fetchall()


# ─── Séquences et événements ───


def sequence_name(connection: Connection, sequence: int | None) -> TupleRow | None:
	return connection.execute("SELECT internal_name FROM sequences WHERE id = %s", (sequence,)).fetchone()


def present_sequence_name(connection: Connection, sequence: int) -> TupleRow | None:
	"""Le nom d'une séquence qui n'est pas supprimée."""
	return connection.execute(
		"SELECT internal_name FROM sequences WHERE id = %s AND deleted_at IS NULL", (sequence,)
	).fetchone()


def sequence_and_bank_names(connection: Connection, sequence: int | None, bank: int | None) -> TupleRow | None:
	"""Les noms d'une séquence et d'une banque, None pour celle qui n'est pas en base."""
	return connection.execute(
		"SELECT (SELECT internal_name FROM sequences WHERE id = %s), (SELECT internal_name FROM banks WHERE id = %s)",
		(sequence, bank),
	).fetchone()


def sequence_items(connection: Connection, sequence: int) -> list[TupleRow]:
	"""Les éléments d'une séquence, dans leur ordre."""
	return connection.execute(
		"SELECT id, position, sound_id, bank_id FROM sequence_items WHERE sequence_id = %s ORDER BY position",
		(sequence,),
	).fetchall()


def sequence_of_item(connection: Connection, item: int) -> TupleRow | None:
	return connection.execute("SELECT sequence_id FROM sequence_items WHERE id = %s", (item,)).fetchone()


def sequence_hidings(connection: Connection, sequences: list[int | None]) -> list[TupleRow]:
	"""Le nom, le nom public et le masquage de chacune de ces séquences."""
	return connection.execute(
		"SELECT id, internal_name, public_name, hide_metadata FROM sequences WHERE id = ANY(%s)", (sequences,)
	).fetchall()


def event_name(connection: Connection, event: int) -> TupleRow | None:
	return connection.execute("SELECT internal_name FROM events WHERE id = %s", (event,)).fetchone()


def event_hidings(connection: Connection, events: list[int | None]) -> list[TupleRow]:
	"""Le nom, le nom public et le masquage de chacun de ces événements."""
	return connection.execute(
		"SELECT id, internal_name, public_name, hide_metadata FROM events WHERE id = ANY(%s)", (events,)
	).fetchall()


def event_items(connection: Connection, event: int) -> list[TupleRow]:
	"""Les éléments d'un événement, dans leur ordre."""
	return connection.execute(
		"SELECT id, position, sound_id, bank_id, sequence_id FROM event_items WHERE event_id = %s ORDER BY position",
		(event,),
	).fetchall()


def event_item(connection: Connection, item: int) -> list[TupleRow]:
	return connection.execute(
		"SELECT id, position, sound_id, bank_id, sequence_id FROM event_items WHERE id = %s", (item,)
	).fetchall()


def feed_stream(connection: Connection, feed: int | None) -> TupleRow | None:
	"""Le nom d'un feed, et le plus ancien stream actif qui le suit."""
	return connection.execute(
		"SELECT m.name, (SELECT s.id FROM sounds s WHERE s.feed_id = m.id AND s.type = 'stream'"
		" AND s.state = 'active' AND s.deleted_at IS NULL ORDER BY s.id LIMIT 1) FROM feeds m WHERE m.id = %s",
		(feed,),
	).fetchone()


GRID_FINGERPRINT = (
	"SELECT md5(concat_ws('|',"
	" (SELECT string_agg(concat_ws(';', e.id, e.priority, e.starts_at, e.ends_at, e.recurrence_days, e.deleted_at,"
	" e.end_of_list, e.properties), ',' ORDER BY e.id) FROM events e),"
	" (SELECT string_agg(x::text, ',' ORDER BY x.id) FROM event_items x),"
	" (SELECT string_agg(l::text, ',' ORDER BY l.id) FROM sequence_items l),"
	" (SELECT string_agg(s::text, ',' ORDER BY s.event_id, s.day) FROM event_skips s)))"
)
"""Empreinte de ce qui règle l'antenne dans la grille : les dates, les jours, la priorité et la suppression des
événements, leur fin de liste et leurs propriétés, secours compris (https://github.com/dascritch/machincast/issues/564,
https://github.com/dascritch/machincast/issues/607), leurs listes,
leurs sessions sautées et les listes des séquences. Changée, elle fait recalculer les
sonores à venir ; un nom, un nom public, un masquage ou la date de modification n'y sont pas : les sonores à venir,
déjà tirés, restent ceux qui passeront (https://github.com/dascritch/machincast/issues/266)."""


def grid_fingerprint(connection: Connection) -> TupleRow | None:
	return connection.execute(GRID_FINGERPRINT).fetchone()


# ─── Airplay et log ───


def play_counts(connection: Connection, sounds: Collection[int]) -> list[TupleRow]:
	"""Le nombre de passages de chacun de ces sonores qui en a."""
	return connection.execute(
		"SELECT sound_id, count(*) FROM airplay WHERE line_type = 'start' AND sound_id = ANY(%s) GROUP BY sound_id",
		(list(sounds),),
	).fetchall()


def played_via_bank(connection: Connection, bank: int) -> list[TupleRow]:
	"""Les sonores joués par une banque, du plus récent au plus ancien."""
	return connection.execute(
		"SELECT sound_id FROM airplay WHERE bank_id = %s AND line_type = 'start' AND sound_id IS NOT NULL"
		" ORDER BY logged_at DESC, id DESC",
		(bank,),
	).fetchall()


def last_item(connection: Connection, event: int, since: datetime | None) -> TupleRow | None:
	"""Le dernier élément joué d'un événement, depuis cet instant s'il est donné."""
	return connection.execute(
		"SELECT event_item_id FROM airplay WHERE event_id = %s AND line_type = 'start'"
		" AND event_item_id IS NOT NULL"
		" AND (%s::timestamptz IS NULL OR logged_at >= %s::timestamptz)"
		" ORDER BY logged_at DESC, id DESC LIMIT 1",
		(event, since, since),
	).fetchone()


def last_play(connection: Connection) -> TupleRow | None:
	"""Le passage le plus récent, tous événements confondus."""
	return connection.execute(
		"SELECT play_id, bank_id, logged_at, event_id, event_item_id, sequence_item_id FROM airplay"
		" WHERE line_type = 'start' ORDER BY logged_at DESC, id DESC LIMIT 1"
	).fetchone()


def plays(
	connection: Connection,
	count: int | None,
	play: uuid.UUID | None,
	since: datetime | None,
	lender: tuple[bool, int | None],
) -> list[TupleRow]:
	"""Les derniers passages, du plus récent au plus ancien, ou un seul, avec leur événement, leur séquence, leur banque
	et le masquage de chaque niveau. lender : s'il faut prendre, pour un passage en cours, l'événement qui prête son nom
	à cet instant, et lequel."""
	override, event = lender
	return connection.execute(
		"SELECT d.logged_at, f.logged_at, f.played_duration, f.without_incident, d.artist, d.title, d.location,"
		" e.internal_name, e.public_name, q.public_name, b.public_name, q.internal_name, b.internal_name,"
		" e.hide_metadata, q.hide_metadata, b.hide_metadata, s.hide_metadata"
		" FROM airplay d"
		" LEFT JOIN airplay f ON f.play_id = d.play_id AND f.line_type = 'end'"
		" LEFT JOIN events e ON e.id = CASE WHEN %s AND f.play_id IS NULL THEN COALESCE(%s::bigint, d.event_id)"
		" ELSE COALESCE(d.lender_event_id, d.event_id) END"
		" LEFT JOIN sequences q ON q.id = d.sequence_id"
		" LEFT JOIN banks b ON b.id = d.bank_id"
		" LEFT JOIN sounds s ON s.id = d.sound_id"
		" WHERE d.line_type = 'start' AND (%s::uuid IS NULL OR d.play_id = %s::uuid)"
		" AND (%s::timestamptz IS NULL OR d.logged_at >= %s::timestamptz)"
		" ORDER BY d.logged_at DESC, d.id DESC LIMIT %s",
		(override, event, play, play, since, since, count),
	).fetchall()


def insert_log(
	connection: Connection,
	line: tuple[datetime | None, str, str, str],
	subjects: tuple[int | None, int | None, int | None],
	origin: str | None,
	api_user: str | None,
) -> None:
	"""Une ligne du log : son instant (sans lui, l'heure du serveur), son niveau, son type et son message ; le sonore,
	la banque et l'événement qu'elle concerne. Jamais de RETURNING : la lecture n'a pas le droit de lire le log."""
	instant, level, kind, message = line
	sound, bank, event = subjects
	connection.execute(
		"INSERT INTO log (logged_at, level, kind, message, sound_id, bank_id, event_id, origin, api_user)"
		" VALUES (COALESCE(%s, clock_timestamp()), %s, %s, %s, %s, %s, %s, %s, %s)",
		(instant, level, kind, message, sound, bank, event, origin, api_user),
	)


def insert_play_start(
	connection: Connection,
	play: uuid.UUID,
	start: datetime,
	where: tuple[int | None, int | None, int | None, int | None, int | None, int | None],
	sound: int,
) -> None:
	"""La ligne de début d'un passage : où il joue (banque, événement, élément, séquence, élément de séquence,
	événement prêteur), et l'emplacement, l'artiste et le titre du sonore à cet instant."""
	bank, event, item, sequence, item_sequence, lender = where
	connection.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, bank_id, event_id, event_item_id,"
		" sequence_id, sequence_item_id, lender_event_id, location, artist, title)"
		" SELECT %s, 'start', %s, s.id, %s, %s, %s, %s, %s, %s, COALESCE(s.location, s.stream_url, m.url),"
		" s.artist, s.title FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
		(play, start, bank, event, item, sequence, item_sequence, lender, sound),
	)


def insert_play_end(
	connection: Connection, play: uuid.UUID, instant: datetime, duration: timedelta, *, without_incident: bool
) -> None:
	"""La ligne de fin d'un passage, qui recopie sa ligne de début : l'artiste et le titre restent ceux du moment du
	passage."""
	connection.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, bank_id, event_id, event_item_id,"
		" sequence_id, sequence_item_id, lender_event_id, location, artist, title, played_duration, without_incident)"
		" SELECT play_id, 'end', %s, sound_id, bank_id, event_id, event_item_id, sequence_id,"
		" sequence_item_id, lender_event_id, location, artist, title, %s, %s FROM airplay"
		" WHERE play_id = %s AND line_type = 'start'",
		(instant, duration, without_incident, play),
	)


def read_only_transaction(connection: Connection) -> None:
	"""La transaction en cours, en lecture répétable et en lecture seule : celle de la simulation."""
	connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")


def event_public_name(connection: Connection, event: int) -> TupleRow | None:
	"""Le nom public d'un événement, pour les plugins (https://github.com/dascritch/machincast/issues/589)."""
	return connection.execute("SELECT public_name FROM events WHERE id = %s", (event,)).fetchone()


def sequence_names(connection: Connection, sequence: int) -> TupleRow | None:
	"""Les noms interne et public d'une séquence, pour les plugins (https://github.com/dascritch/machincast/issues/589)."""
	return connection.execute("SELECT internal_name, public_name FROM sequences WHERE id = %s", (sequence,)).fetchone()
