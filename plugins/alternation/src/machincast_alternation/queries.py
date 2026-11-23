"""Les requêtes des émissions en alternance, dans Machin interface (https://github.com/dascritch/machincast/issues/609) :
au rôle de l'interface, sur la colonne properties des événements, sous la seule clé du plugin."""

import json
from typing import Any

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def properties(connection: Connection, event: int) -> dict[str, Any]:
	"""Les propriétés de l'événement ; aucune s'il est absent."""
	found = connection.execute("SELECT properties FROM events WHERE id = %s", (event,)).fetchone()
	if (found is None) or (not isinstance(found[0], dict)):
		return {}
	return found[0]


def candidates(connection: Connection, event: int | None) -> list[tuple[int, str]]:
	"""Les émissions et spéciaux, non supprimés, qui peuvent jouer le créneau : tous, sauf l'événement lui-même."""
	lines = connection.execute(
		"SELECT id, internal_name FROM events WHERE priority IN ('show', 'special') AND deleted_at IS NULL"
		" AND id IS DISTINCT FROM %s ORDER BY internal_name, id",
		(event,),
	).fetchall()
	found = []
	for identifier, name in lines:
		found.append((int(str(identifier)), str(name)))
	return found


def write(connection: Connection, event: int, stored: dict[str, object] | None) -> None:
	"""Range l'alternance sous la clé du plugin, ou la retire (None), sans toucher aux autres propriétés."""
	if stored is None:
		connection.execute("UPDATE events SET properties = properties - 'alternation' WHERE id = %s", (event,))
		return
	connection.execute(
		"UPDATE events SET properties = properties || jsonb_build_object('alternation', %s::jsonb) WHERE id = %s",
		(json.dumps(stored), event),
	)
