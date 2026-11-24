"""Les requêtes du station ID régulier (https://github.com/dascritch/machincast/issues/460).

Le choix d'un événement est dans sa colonne properties, sous la clé du plugin : {"timely_station_id": true} ; non
coché, la clé en est retirée, sans toucher aux autres.
"""

from typing import Any

import psycopg

Connection = psycopg.Connection[Any]
KEY = "timely_station_id"


def chosen(connection: Connection, event: int) -> bool:
	"""L'événement a-t-il le station ID régulier."""
	found = connection.execute(
		"SELECT COALESCE((properties ->> %s)::boolean, false) FROM events WHERE id = %s", (KEY, event)
	).fetchone()
	return (found is not None) and (found[0] is True)


def write_chosen(connection: Connection, event: int, *, regular: bool) -> None:
	if regular:
		connection.execute(
			"UPDATE events SET properties = properties || jsonb_build_object(%s::text, true) WHERE id = %s",
			(KEY, event),
		)
		return
	connection.execute("UPDATE events SET properties = properties - %s WHERE id = %s", (KEY, event))


def banks(connection: Connection, names: tuple[str, ...]) -> dict[str, int]:
	"""L'identifiant de chaque banque nommée, non supprimée."""
	found = {}
	for identifier, name in connection.execute(
		"SELECT id, internal_name FROM banks WHERE internal_name = ANY(%s) AND deleted_at IS NULL", (list(names),)
	).fetchall():
		found[str(name)] = int(identifier)
	return found
