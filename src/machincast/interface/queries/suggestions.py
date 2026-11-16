"""Requêtes des suggestions de premier lancement (https://github.com/dascritch/machincast/issues/442)."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def has_background_programming(connection: Connection) -> bool:
	"""Un fil musical existe, non supprimé."""
	found = connection.execute(
		"SELECT 1 FROM events WHERE priority = 'background_programming' AND deleted_at IS NULL LIMIT 1"
	).fetchone()
	return found is not None


def bank_names(connection: Connection) -> set[str]:
	"""Les noms des banques non supprimées, sans casse."""
	names = set()
	for (name,) in connection.execute("SELECT internal_name FROM banks WHERE deleted_at IS NULL"):
		names.add(str(name).casefold())
	return names


def insert_bank(connection: Connection, name: str, mode: str, no_repeat: bool, max_duration: object, rule: str) -> None:
	"""Crée une banque suggérée, sans crossfade propre."""
	connection.execute(
		"INSERT INTO banks (internal_name, mode, no_repeat, max_duration, crossfade_start_rule,"
		" crossfade_start, crossfade_end_rule, crossfade_end)"
		" VALUES (%s, %s, %s, %s, %s, '0 s', %s, '0 s')",
		(name, mode, no_repeat, max_duration, rule, rule),
	)


def empty_background_programming(connection: Connection) -> int | None:
	"""Le premier fil musical sans élément, par nom ; None s'il n'y en a pas."""
	empty = connection.execute(
		"SELECT e.id FROM events e WHERE e.priority = 'background_programming' AND e.deleted_at IS NULL"
		" AND NOT EXISTS (SELECT 1 FROM event_items x WHERE x.event_id = e.id)"
		" ORDER BY e.internal_name LIMIT 1"
	).fetchone()
	if empty is None:
		return None
	return int(str(empty[0]))


def banks_by_name(connection: Connection) -> dict[str, int]:
	"""Les banques non supprimées, par nom sans casse ; la dernière de même nom l'emporte."""
	banks = {}
	for identifier, name in connection.execute(
		"SELECT id, internal_name FROM banks WHERE deleted_at IS NULL ORDER BY id"
	):
		banks[str(name).casefold()] = int(str(identifier))
	return banks


def add_bank_item(connection: Connection, event: int, position: int, bank: int) -> None:
	connection.execute(
		"INSERT INTO event_items (event_id, position, bank_id) VALUES (%s, %s, %s)", (event, position, bank)
	)
