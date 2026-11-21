"""Requêtes des actions groupées sur des sonores ou des banques (machincast.interface.groups,
https://github.com/dascritch/machincast/issues/583). Sans transaction : l'appelant l'ouvre.
"""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def change_state(connection: Connection, state: str, sounds: list[int]) -> list[TupleRow]:
	"""Change l'état des sonores qui ne sont ni en aperçu, ni déjà dans cet état ; rend ceux qui changent."""
	return connection.execute(
		"UPDATE sounds SET state = %s WHERE id = ANY(%s) AND state NOT IN ('preview', %s) RETURNING id",
		(state, sounds, state),
	).fetchall()


def bank_sounds_locked(connection: Connection, bank: int) -> list[TupleRow]:
	"""Les sonores de la banque, verrouillés jusqu'à la fin de la transaction."""
	return connection.execute("SELECT sound_id FROM bank_sounds WHERE bank_id = %s FOR UPDATE", (bank,)).fetchall()


def last_position(connection: Connection, bank: int) -> int:
	line = connection.execute(
		"SELECT COALESCE(MAX(position), 0) FROM bank_sounds WHERE bank_id = %s", (bank,)
	).fetchone()
	assert line is not None
	return int(str(line[0]))


def append_to_bank(connection: Connection, rows: list[tuple[int, int, int]]) -> None:
	"""Ajoute des sonores à des banques : banque, sonore, position."""
	with connection.cursor() as slider:
		slider.executemany("INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)", rows)


def remove_from_banks(connection: Connection, sounds: list[int], banks: list[int]) -> list[TupleRow]:
	"""Retire les sonores des banques ; rend chaque retrait, sonore et banque."""
	return connection.execute(
		"DELETE FROM bank_sounds WHERE sound_id = ANY(%s) AND bank_id = ANY(%s) RETURNING sound_id, bank_id",
		(sounds, banks),
	).fetchall()


def tighten(connection: Connection, banks: list[int]) -> None:
	"""Les positions restantes des banques se resserrent ; leur unicité n'est vérifiée qu'en fin de transaction."""
	connection.execute(
		"UPDATE bank_sounds bs SET position = r.rang FROM ("
		" SELECT bank_id, sound_id, row_number() OVER (PARTITION BY bank_id ORDER BY position) AS rang"
		" FROM bank_sounds WHERE bank_id = ANY(%s)) r"
		" WHERE bs.bank_id = r.bank_id AND bs.sound_id = r.sound_id",
		(banks,),
	)


def ask_audit(connection: Connection, sounds: list[int]) -> list[TupleRow]:
	"""Demande l'audit complet des fichiers parmi ces sonores ; rend ceux qui sont marqués."""
	return connection.execute(
		"UPDATE sounds SET audit_requested = true WHERE id = ANY(%s) AND type = 'file' RETURNING id", (sounds,)
	).fetchall()


def ask_bank_audit(connection: Connection, banks: list[int]) -> list[TupleRow]:
	"""Demande l'audit complet des fichiers de ces banques ; rend ceux qui sont marqués."""
	return connection.execute(
		"UPDATE sounds SET audit_requested = true WHERE type = 'file'"
		" AND id IN (SELECT sound_id FROM bank_sounds WHERE bank_id = ANY(%s)) RETURNING id",
		(banks,),
	).fetchall()


def hide(connection: Connection, banks: list[int], *, value: bool | None) -> list[TupleRow]:
	"""Le masquage de l'artiste et du titre de ces banques ; rend celles qui changent."""
	return connection.execute(
		"UPDATE banks SET hide_metadata = %s WHERE id = ANY(%s) RETURNING id", (value, banks)
	).fetchall()


def sound_banks(connection: Connection, sounds: list[int]) -> list[TupleRow]:
	"""Les banques où figure l'un des sonores, par nom."""
	return connection.execute(
		"SELECT b.id FROM banks b WHERE b.id IN (SELECT bank_id FROM bank_sounds WHERE sound_id = ANY(%s))"
		" ORDER BY b.internal_name, b.id",
		(sounds,),
	).fetchall()


def bank_names(connection: Connection, banks: list[int]) -> list[TupleRow]:
	return connection.execute("SELECT id, internal_name FROM banks WHERE id = ANY(%s)", (banks,)).fetchall()
