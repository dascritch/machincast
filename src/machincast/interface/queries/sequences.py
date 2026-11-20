"""Requêtes de la fiche d'une séquence (https://github.com/dascritch/machincast/issues/442)."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def named(connection: Connection) -> list[TupleRow]:
	"""Les séquences en base, non supprimées, par nom : identifiant et nom
	(https://github.com/dascritch/machincast/issues/530)."""
	return connection.execute(
		"SELECT id, internal_name FROM sequences WHERE deleted_at IS NULL ORDER BY lower(internal_name), id"
	).fetchall()


def read_sequence(connection: Connection, sequence: int) -> TupleRow | None:
	"""Nom interne, nom public et masquage de la séquence ; None si elle est absente."""
	return connection.execute(
		"SELECT internal_name, public_name, hide_metadata FROM sequences WHERE id = %s", (sequence,)
	).fetchone()


def events_calling(connection: Connection, sequence: int) -> list[TupleRow]:
	"""Les événements, non supprimés, dont la liste appelle la séquence, par nom."""
	return connection.execute(
		"SELECT DISTINCT ev.id, ev.internal_name FROM events ev"
		" JOIN event_items ee ON ee.event_id = ev.id"
		" WHERE ee.sequence_id = %s AND ev.deleted_at IS NULL ORDER BY ev.internal_name, ev.id",
		(sequence,),
	).fetchall()


def name_taken(connection: Connection, name: str, identifier: int | None) -> bool:
	"""Une autre séquence, non supprimée, porte ce nom interne."""
	taken = connection.execute(
		"SELECT 1 FROM sequences WHERE internal_name = %s AND id IS DISTINCT FROM %s AND deleted_at IS NULL",
		(name, identifier),
	).fetchone()
	return taken is not None


def insert(connection: Connection, values: tuple[object, ...]) -> int:
	created = connection.execute(
		"INSERT INTO sequences (internal_name, public_name, hide_metadata) VALUES (%s, %s, %s) RETURNING id",
		values,
	).fetchone()
	assert created is not None
	return int(str(created[0]))


def update(connection: Connection, identifier: int, values: tuple[object, ...]) -> None:
	connection.execute(
		"UPDATE sequences SET internal_name = %s, public_name = %s, hide_metadata = %s WHERE id = %s",
		(*values, identifier),
	)
