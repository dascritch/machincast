"""Les requêtes des couleurs des émissions (https://github.com/dascritch/machincast/issues/628).

Les genres et les couleurs des priorités sont dans les tables du plugin ; le genre d'un événement dans sa colonne
properties, sous la clé du plugin, sans toucher aux autres clés.
"""

from typing import Any

import psycopg

Connection = psycopg.Connection[Any]
KEY = "color_the_shows"
"""La clé du plugin, dans la colonne properties des événements."""


def genres(connection: Connection) -> list[tuple[int, str, str]]:
	"""Les genres, par nom : identifiant, nom et couleur."""
	found = []
	for identifier, name, colour in connection.execute(
		"SELECT id, name, colour FROM color_the_shows__genres ORDER BY lower(name), id"
	).fetchall():
		found.append((int(identifier), str(name), str(colour)))
	return found


def priorities(connection: Connection) -> dict[str, str]:
	"""La couleur de chaque priorité qui en a une."""
	found = {}
	for priority, colour in connection.execute(
		"SELECT priority::text, colour FROM color_the_shows__priorities"
	).fetchall():
		found[str(priority)] = str(colour)
	return found


def event_genres(connection: Connection) -> dict[int, int]:
	"""Le genre de chaque événement qui en a un."""
	found = {}
	for event, genre in connection.execute(
		"SELECT id, (properties -> %s ->> 'genre')::bigint FROM events WHERE properties -> %s ->> 'genre' IS NOT NULL",
		(KEY, KEY),
	).fetchall():
		found[int(event)] = int(genre)
	return found


def event_genre(connection: Connection, event: int) -> int | None:
	found = connection.execute(
		"SELECT (properties -> %s ->> 'genre')::bigint FROM events WHERE id = %s", (KEY, event)
	).fetchone()
	if (found is None) or (found[0] is None):
		return None
	return int(found[0])


def write_genre(connection: Connection, event: int, genre: int | None) -> None:
	"""Le genre de l'événement ; sans genre, la clé du plugin quitte ses propriétés."""
	if genre is None:
		connection.execute("UPDATE events SET properties = properties - %s WHERE id = %s", (KEY, event))
		return
	connection.execute(
		"UPDATE events SET properties = properties || jsonb_build_object(%s::text, jsonb_build_object('genre', %s::bigint))"
		" WHERE id = %s",
		(KEY, genre, event),
	)


def save(connection: Connection, kept: list[tuple[int | None, str, str]], priority_colours: dict[str, str]) -> None:
	"""Les genres tels qu'ils sont réglés, identifiant, nom et couleur, un nouveau sans identifiant ; ceux qui manquent
	partent, et les événements qui les avaient perdent leur genre. Puis la couleur de chaque priorité. À appeler dans
	une transaction."""
	kept_list = []
	for identifier, _name, _colour in kept:
		if identifier is not None:
			kept_list.append(identifier)
	connection.execute(
		"UPDATE events SET properties = properties - %s"
		" WHERE properties -> %s ->> 'genre' IS NOT NULL AND NOT (properties -> %s ->> 'genre')::bigint = ANY(%s)",
		(KEY, KEY, KEY, kept_list),
	)
	connection.execute("DELETE FROM color_the_shows__genres WHERE NOT id = ANY(%s)", (kept_list,))
	# Deux genres qui échangent leurs noms : les noms passent d'abord par des valeurs uniques, sans conflit.
	for identifier, _name, _colour in kept:
		if identifier is not None:
			connection.execute("UPDATE color_the_shows__genres SET name = '#' || id::text WHERE id = %s", (identifier,))
	for identifier, name, colour in kept:
		if identifier is None:
			connection.execute("INSERT INTO color_the_shows__genres (name, colour) VALUES (%s, %s)", (name, colour))
		else:
			connection.execute(
				"UPDATE color_the_shows__genres SET name = %s, colour = %s WHERE id = %s", (name, colour, identifier)
			)
	for priority, colour in priority_colours.items():
		connection.execute(
			"UPDATE color_the_shows__priorities SET colour = %s WHERE priority = %s::event_priority", (colour, priority)
		)
