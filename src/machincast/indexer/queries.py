"""Les requêtes SQL de Machin indexer, toutes ici (https://github.com/dascritch/machincast/issues/583).

Chaque fonction prend la connexion, au rôle machincast_indexer (machincast.database.open_connection), et ses
paramètres, exécute une requête, et rend ses lignes telles quelles ; l'appelant ouvre la transaction et en tire ses
objets. Ce que l'indexation écrit se relit ici d'un coup, à comparer à la matrice des droits
(tests/features/roles.feature) : `sounds`, `bank_sounds`, et la seule colonne `scanned_at` de `bank_directories`.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import psycopg
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from machincast.conversion import list_or_none

Connection = psycopg.Connection[TupleRow]

DIRECTORIES_LOCK = 0x4D616368_64697273
"""Clé du verrou consultatif, le temps d'une transaction, des enregistrements et rattachements du parcours :
« Machdirs »."""

OUTSIDE_DURATIONS = (
	"s.duration IS NOT NULL AND ((b.min_duration IS NOT NULL AND s.duration < b.min_duration)"
	" OR (b.max_duration IS NOT NULL AND s.duration > b.max_duration))"
)
"""Condition SQL : le sonore s, de durée connue, sort des durées de la banque b, bornes comprises dans les durées
(https://github.com/dascritch/machincast/issues/147, https://github.com/dascritch/machincast/issues/195)."""

# ─── Verrous ───


def try_lock(connection: Connection, lock: int) -> bool:
	"""Prend le verrou consultatif d'un mode d'indexation, pour la session ; False s'il est déjà pris."""
	taken = connection.execute("SELECT pg_try_advisory_lock(%s)", (lock,)).fetchone()
	assert taken is not None
	return taken[0] is True


def unlock(connection: Connection, lock: int) -> None:
	connection.execute("SELECT pg_advisory_unlock(%s)", (lock,))


def take_directories_lock(connection: Connection) -> None:
	"""Le verrou des enregistrements du parcours, jusqu'à la fin de la transaction en cours ; attend l'autre parcours
	qui le tient."""
	connection.execute("SELECT pg_advisory_xact_lock(%s)", (DIRECTORIES_LOCK,))


# ─── Parcours des répertoires ───


def bank_directories(connection: Connection) -> list[TupleRow]:
	"""Chaque répertoire des banques qui ne sont pas supprimées, avec sa banque et son nom."""
	return connection.execute(
		"SELECT b.id, b.internal_name, r.directory FROM bank_directories r JOIN banks b ON b.id = r.bank_id"
		" WHERE b.deleted_at IS NULL ORDER BY b.id, r.directory"
	).fetchall()


def directories(connection: Connection) -> list[TupleRow]:
	"""Les répertoires des banques qui ne sont pas supprimées, une fois chacun."""
	return connection.execute(
		"SELECT DISTINCT d.directory FROM bank_directories d JOIN banks b ON b.id = d.bank_id"
		" WHERE b.deleted_at IS NULL ORDER BY 1"
	).fetchall()


def attached_files(connection: Connection, bank: int) -> list[TupleRow]:
	"""Les emplacements des sonores de la banque qui ne sont pas supprimés."""
	return connection.execute(
		"SELECT s.location FROM bank_sounds bs JOIN sounds s ON s.id = bs.sound_id"
		" WHERE bs.bank_id = %s AND s.deleted_at IS NULL AND s.location IS NOT NULL",
		(bank,),
	).fetchall()


def known_file(connection: Connection, location: str, bank: int) -> TupleRow | None:
	"""Le sonore de ce fichier, et s'il attend sa vérification pour entrer dans la banque : durée inconnue, et la banque
	a des durées."""
	return connection.execute(
		"SELECT s.id, s.duration IS NULL AND (b.min_duration IS NOT NULL OR b.max_duration IS NOT NULL)"
		" FROM sounds s, banks b WHERE s.location = %s AND s.deleted_at IS NULL AND b.id = %s",
		(location, bank),
	).fetchone()


def insert_file(connection: Connection, location: str, state: str, bank: int) -> TupleRow | None:
	"""Un nouveau sonore pour ce fichier ; son identifiant, et s'il attend sa vérification : la banque a des durées."""
	return connection.execute(
		"INSERT INTO sounds (type, location, state, indexed_at)"
		" VALUES ('file', %s, %s, clock_timestamp())"
		" RETURNING id, EXISTS (SELECT 1 FROM banks WHERE id = %s"
		" AND (min_duration IS NOT NULL OR max_duration IS NOT NULL))",
		(location, state, bank),
	).fetchone()


def attach(connection: Connection, bank: int, sound: int) -> bool:
	"""Rattache le sonore à la fin de la banque, s'il n'y est pas et qu'il ne sort pas de ses durées ; True s'il l'a
	été."""
	return (
		connection.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position)"
			" SELECT %s, %s, (SELECT COALESCE(MAX(position), 0) + 1 FROM bank_sounds WHERE bank_id = %s)"
			f" WHERE NOT EXISTS (SELECT 1 FROM sounds s, banks b WHERE s.id = %s AND b.id = %s AND {OUTSIDE_DURATIONS})"
			" ON CONFLICT (bank_id, sound_id) DO NOTHING",
			(bank, sound, bank, sound, bank),
		).rowcount
		> 0
	)


def scanned(connection: Connection, bank: int, directory: str) -> None:
	"""Le répertoire de la banque est parcouru jusqu'au bout."""
	connection.execute(
		"UPDATE bank_directories SET scanned_at = clock_timestamp() WHERE bank_id = %s AND directory = %s",
		(bank, directory),
	)


def remove_outside_durations(connection: Connection, identifiers: Collection[int] | None) -> list[TupleRow]:
	"""Retire de chaque banque les sonores, tous, ou ceux-là, dont la durée connue sort de ses durées, en une seule
	requête ; rend chaque retrait, dans l'ordre des banques et des positions."""
	return connection.execute(
		"WITH removed AS (DELETE FROM bank_sounds bs USING banks b, sounds s"
		" WHERE b.id = bs.bank_id AND s.id = bs.sound_id"
		f" AND (%s::bigint[] IS NULL OR s.id = ANY(%s)) AND b.deleted_at IS NULL AND {OUTSIDE_DURATIONS}"
		" RETURNING bs.bank_id, bs.position, b.internal_name, s.location, s.duration, b.min_duration, b.max_duration)"
		" SELECT internal_name, location, duration, min_duration, max_duration FROM removed"
		" ORDER BY bank_id, position",
		(list_or_none(identifiers), list_or_none(identifiers)),
	).fetchall()


# ─── Vérification des sonores ───


def is_file(connection: Connection, sound: int) -> bool:
	return connection.execute("SELECT 1 FROM sounds WHERE id = %s AND type = 'file'", (sound,)).fetchone() is not None


def sounds_to_check(
	connection: Connection, identifiers: Collection[int] | None, after: int, count: int
) -> list[TupleRow]:
	"""Un lot de sonores à vérifier, d'identifiant plus grand que after : ce qui décide de leur examen. Un fichier sain
	sans mesure de son niveau compte comme jamais audité : l'audit complet suivant le mesure
	(https://github.com/dascritch/machincast/issues/646)."""
	return connection.execute(
		"SELECT id, location, state::text, file_modified_at, file_size, audit_requested,"
		" CASE WHEN properties ? 'loudness' OR state IN ('corrupt', 'unsupported', 'missing') THEN audited_at END,"
		" audit_threshold FROM sounds WHERE type = 'file' AND deleted_at IS NULL"
		" AND (%s::bigint[] IS NULL OR id = ANY(%s)) AND id > %s ORDER BY id LIMIT %s",
		(list_or_none(identifiers), list_or_none(identifiers), after, count),
	).fetchall()


def locked_sound(connection: Connection, sound: object, location: str) -> TupleRow | None:
	"""Relit, verrouillé jusqu'à la fin de la transaction, ce que le verdict d'un examen change dans la ligne du
	sonore ; None s'il a été supprimé ou son fichier déplacé."""
	return connection.execute(
		"SELECT state::text, edited_fields, artist, title, music_metadata, detected_start, detected_end"
		" FROM sounds WHERE id = %s AND type = 'file' AND deleted_at IS NULL AND location = %s FOR UPDATE",
		(sound, location),
	).fetchone()


def audit_done(connection: Connection, sound: object) -> None:
	"""La demande d'audit d'un sonore est faite."""
	connection.execute("UPDATE sounds SET audit_requested = false WHERE id = %s", (sound,))


@dataclass(frozen=True)
class Verdict:
	"""Ce que l'examen d'un fichier écrit dans la ligne de son sonore."""

	state: str
	duration: timedelta | None
	modified_at: datetime | None
	size: int | None
	artist: str | None
	title: str | None
	metadata: dict[str, Any]
	file_type: str | None
	detected_start: timedelta | None
	detected_end: timedelta | None
	found: bool
	"""Le fichier est là : il est vérifié en entier, et la demande d'audit tombe."""
	audited: bool
	"""Audit complet d'un fichier trouvé : retenu, avec son seuil, quel que soit le verdict."""
	silence_threshold: float
	missing: bool
	"""Le fichier a disparu : la date de sa disparition, une seule fois."""
	loudness: dict[str, Any] | None = None
	"""La crête et la sonie mesurées à l'audit complet d'un fichier sain, rangées dans properties sous la clé
	« loudness » (https://github.com/dascritch/machincast/issues/642) ; None : la mesure en place reste."""


def _jsonb_or_none(value: dict[str, Any] | None) -> Jsonb | None:
	if value is None:
		return None
	return Jsonb(value)


def write_check(connection: Connection, sound: object, verdict: Verdict) -> None:
	"""Écrit le verdict de l'examen dans la ligne du sonore. Un fichier introuvable garde la date, la taille et la date
	de sa dernière vérification ; un fichier revenu n'est plus daté disparu
	(https://github.com/dascritch/machincast/issues/267)."""
	connection.execute(
		"UPDATE sounds SET state = %s, duration = COALESCE(%s, duration),"
		" file_modified_at = COALESCE(%s, file_modified_at), file_size = COALESCE(%s, file_size),"
		" artist = %s, title = %s, music_metadata = %s, mime_type = COALESCE(%s, mime_type),"
		" checked_at = CASE WHEN %s THEN clock_timestamp() ELSE checked_at END,"
		" detected_start = %s, detected_end = %s, audit_requested = audit_requested AND NOT %s,"
		" audited_at = CASE WHEN %s THEN clock_timestamp() ELSE audited_at END,"
		" audit_threshold = CASE WHEN %s THEN %s ELSE audit_threshold END,"
		" missing_at = CASE WHEN %s THEN COALESCE(missing_at, clock_timestamp()) END,"
		" properties = CASE WHEN %s::jsonb IS NULL THEN properties"
		" ELSE properties || jsonb_build_object('loudness', %s::jsonb) END"
		" WHERE id = %s",
		(
			verdict.state,
			verdict.duration,
			verdict.modified_at,
			verdict.size,
			verdict.artist,
			verdict.title,
			Jsonb(verdict.metadata),
			verdict.file_type,
			verdict.found,
			verdict.detected_start,
			verdict.detected_end,
			verdict.found,
			verdict.audited,
			verdict.audited,
			verdict.silence_threshold,
			verdict.missing,
			_jsonb_or_none(verdict.loudness),
			_jsonb_or_none(verdict.loudness),
			sound,
		),
	)
