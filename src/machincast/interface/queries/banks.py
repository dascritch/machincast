"""Requêtes des banques et de leurs sonores, pour la fiche d'une banque (https://github.com/dascritch/machincast/issues/442)."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]

FETCHED_SOUNDS = (
	"SELECT s.id, s.artist, s.title, s.duration, s.location, COALESCE(s.location, s.stream_url, m.url),"
	" s.state::text"
	" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id"
)
PAGE = (
	"SELECT s.id, s.artist, s.title, s.duration, s.location, COALESCE(s.location, s.stream_url, m.url),"
	" s.state::text, bs.position"
	" FROM bank_sounds bs JOIN sounds s ON s.id = bs.sound_id LEFT JOIN feeds m ON m.id = s.feed_id"
	" WHERE bs.bank_id = %s AND bs.position > %s ORDER BY bs.position LIMIT %s"
)
"""Les sonores de la banque qui suivent une position, dans l'ordre de la banque, au plus un nombre : la fiche les lit
par pages (https://github.com/dascritch/machincast/issues/383)."""
TAIL_STATES = (
	"SELECT s.state::text, count(*) FROM bank_sounds bs JOIN sounds s ON s.id = bs.sound_id"
	" WHERE bs.bank_id = %s AND bs.position > %s GROUP BY 1"
)
"""Les états des sonores de la banque qui ne sont pas encore lus, et leur nombre, pour l'avertissement de la fiche."""


def named(connection: Connection) -> list[TupleRow]:
	"""Les banques en base, non supprimées, par nom : identifiant et nom
	(https://github.com/dascritch/machincast/issues/530)."""
	return connection.execute(
		"SELECT id, internal_name FROM banks WHERE deleted_at IS NULL ORDER BY lower(internal_name), id"
	).fetchall()


def all_directories(connection: Connection) -> list[TupleRow]:
	"""Chaque répertoire indexé par une banque non supprimée, avec le nom de la banque, par répertoire
	(https://github.com/dascritch/machincast/issues/533)."""
	return connection.execute(
		"SELECT d.directory, b.internal_name FROM bank_directories d JOIN banks b ON b.id = d.bank_id"
		" WHERE b.deleted_at IS NULL ORDER BY d.directory, lower(b.internal_name)"
	).fetchall()


def read_bank(connection: Connection, bank: int) -> TupleRow | None:
	"""Les champs de la banque, dans l'ordre de la fiche ; None si elle est absente."""
	return connection.execute(
		"SELECT internal_name, public_name, mode::text, hide_metadata, no_repeat,"
		" crossfade_start_rule::text, crossfade_start, crossfade_end_rule::text, crossfade_end,"
		" min_duration, max_duration, silence_detection FROM banks WHERE id = %s",
		(bank,),
	).fetchone()


def directories(connection: Connection, bank: int) -> list[str]:
	"""Les répertoires indexés de la banque."""
	found = []
	for (directory,) in connection.execute("SELECT directory FROM bank_directories WHERE bank_id = %s", (bank,)):
		found.append(str(directory))
	return found


def page(connection: Connection, bank: int, after: int, limit: int | None) -> list[TupleRow]:
	"""Les sonores de la banque après cette position, au plus limit ; la dernière colonne est leur position."""
	return connection.execute(PAGE, (bank, after, limit)).fetchall()


def tail_states(connection: Connection, bank: int, after: int) -> dict[str, int]:
	"""Les états des sonores qui restent après cette position, et leur nombre."""
	counts = {}
	for state, count in connection.execute(TAIL_STATES, (bank, after)):
		counts[str(state)] = int(str(count))
	return counts


def name_taken(connection: Connection, name: str, identifier: int | None) -> bool:
	"""Une autre banque, non supprimée, porte ce nom interne."""
	taken = connection.execute(
		"SELECT 1 FROM banks WHERE internal_name = %s AND id IS DISTINCT FROM %s AND deleted_at IS NULL",
		(name, identifier),
	).fetchone()
	return taken is not None


def insert(connection: Connection, values: list[object]) -> int:
	"""Crée la banque de ces douze valeurs, dans l'ordre de la fiche ; son identifiant."""
	created = connection.execute(
		"INSERT INTO banks (internal_name, public_name, mode, hide_metadata, no_repeat,"
		" crossfade_start_rule, crossfade_start, crossfade_end_rule, crossfade_end, min_duration, max_duration,"
		" silence_detection) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
		values,
	).fetchone()
	assert created is not None
	return int(str(created[0]))


def update(connection: Connection, identifier: int, values: list[object]) -> None:
	connection.execute(
		"UPDATE banks SET internal_name = %s, public_name = %s, mode = %s, hide_metadata = %s,"
		" no_repeat = %s, crossfade_start_rule = %s, crossfade_start = %s, crossfade_end_rule = %s,"
		" crossfade_end = %s, min_duration = %s, max_duration = %s, silence_detection = %s WHERE id = %s",
		(*values, identifier),
	)


def replace_directories(connection: Connection, bank: int, directories: list[str]) -> None:
	connection.execute("DELETE FROM bank_directories WHERE bank_id = %s", (bank,))
	connection.execute(
		"INSERT INTO bank_directories (bank_id, directory) SELECT %s, unnest(%s::text[])", (bank, directories)
	)


def set_sound_state(connection: Connection, sound: int, state: str) -> None:
	"""Un sonore passé en aperçu entre-temps garde son état."""
	connection.execute("UPDATE sounds SET state = %s WHERE id = %s AND state <> 'preview'", (state, sound))


def locked_sounds(connection: Connection, bank: int) -> list[int]:
	"""Les sonores de la banque, dans son ordre, verrouillés pour la réécriture de la liste."""
	found = []
	for (sound,) in connection.execute(
		"SELECT sound_id FROM bank_sounds WHERE bank_id = %s ORDER BY position FOR UPDATE", (bank,)
	):
		found.append(int(str(sound)))
	return found


def existing_sounds(connection: Connection, sounds: list[int]) -> set[int]:
	"""Ceux de ces sonores qui sont en base."""
	existing = set()
	for (sound,) in connection.execute("SELECT id FROM sounds WHERE id = ANY(%s)", (sounds,)):
		existing.add(int(str(sound)))
	return existing


def replace_sounds(connection: Connection, bank: int, order: list[int]) -> None:
	"""La liste de la banque devient celle-ci, numérotée dès 1."""
	connection.execute("DELETE FROM bank_sounds WHERE bank_id = %s", (bank,))
	with connection.cursor() as slider:
		position_list = []
		for position, sound in enumerate(order, start=1):
			position_list.append((bank, sound, position))
		slider.executemany("INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)", position_list)


def sounds_by_location(connection: Connection, files: list[str]) -> list[TupleRow]:
	return connection.execute(f"{FETCHED_SOUNDS} WHERE s.location = ANY(%s)", (files,)).fetchall()


def sounds_by_identifier(connection: Connection, sounds: list[int]) -> list[TupleRow]:
	return connection.execute(f"{FETCHED_SOUNDS} WHERE s.id = ANY(%s)", (sounds,)).fetchall()
