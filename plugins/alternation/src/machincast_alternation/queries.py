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


def name_taken(connection: Connection, name: str) -> bool:
	"""Un événement, non supprimé, porte ce nom interne."""
	found = connection.execute(
		"SELECT 1 FROM events WHERE internal_name = %s AND deleted_at IS NULL", (name,)
	).fetchone()
	return found is not None


CREATED = (
	"INSERT INTO events (internal_name, public_name, priority, starts_at, ends_at, hide_metadata, end_of_list,"
	" properties)"
	" SELECT %(name)s, %(name)s, 'show', starts_at, ends_at, hide_metadata, end_of_list,"
	" jsonb_strip_nulls(jsonb_build_object('end_fallback_event', properties -> 'end_fallback_event',"
	" 'stream_fallback_event', properties -> 'stream_fallback_event'))"
	" FROM events WHERE id = %(meta)s RETURNING id"
)


def create(connection: Connection, name: str, meta: int) -> int:
	"""Une émission sur le créneau de l'événement méta, aux dates de sa première occurrence, sans jour de récurrence :
	hors grille dès qu'elle est dans son alternance, enregistrée dans la même transaction. Son nom est aussi son nom
	public ; elle hérite de l'événement méta, tel que sa fiche vient de l'écrire, son masquage (« Artiste et titre »),
	sa fin de liste et ses secours, de fin de liste et de stream tombé. Son identifiant."""
	found = connection.execute(CREATED, {"name": name, "meta": meta}).fetchone()
	assert found is not None
	return int(str(found[0]))


def sharing(connection: Connection, event: int) -> list[tuple[int, str, list[int]]]:
	"""Les événements méta, non supprimés, dont l'alternance fait jouer cet événement : leur identifiant, leur nom, et
	les émissions de leur alternance."""
	lines = connection.execute(
		"SELECT id, internal_name, properties -> 'alternation' -> 'candidates' FROM events"
		" WHERE deleted_at IS NULL AND properties -> 'alternation' -> 'candidates' @> jsonb_build_array(%s::bigint)"
		" ORDER BY internal_name, id",
		(event,),
	).fetchall()
	found = []
	for identifier, name, candidates in lines:
		shared = []
		if isinstance(candidates, list):
			for candidate in candidates:
				if isinstance(candidate, int):
					shared.append(candidate)
		found.append((int(str(identifier)), str(name), shared))
	return found


def names(connection: Connection, events: list[int]) -> dict[int, str]:
	"""Le nom des événements non supprimés parmi ceux-là."""
	lines = connection.execute(
		"SELECT id, internal_name FROM events WHERE id = ANY(%s) AND deleted_at IS NULL", (events,)
	).fetchall()
	found = {}
	for identifier, name in lines:
		found[int(str(identifier))] = str(name)
	return found
