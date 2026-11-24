"""Requêtes de la suppression et de la restauration d'un élément (machincast.interface.deletion,
https://github.com/dascritch/machincast/issues/267, https://github.com/dascritch/machincast/issues/583).

Les tables et les colonnes viennent des descriptions de machincast.interface.deletion (CATEGORIES, CONTAINERS) :
des constantes du code, jamais une saisie ; une valeur passe toujours en paramètre. Sans transaction : l'appelant
l'ouvre.
"""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def name(connection: Connection, table: str, column: str, identifier: int) -> TupleRow | None:
	"""Le nom d'un élément, par sa colonne de nom."""
	return connection.execute(f"SELECT {column} FROM {table} WHERE id = %s", (identifier,)).fetchone()


def sound_names(connection: Connection, sound: int) -> TupleRow | None:
	"""L'artiste, le titre, le fichier et l'adresse du stream d'un sonore."""
	return connection.execute(
		"SELECT artist, title, location, stream_url FROM sounds WHERE id = %s", (sound,)
	).fetchone()


def containers(connection: Connection, container: tuple[str, str, str], column: str, identifier: int) -> list[TupleRow]:
	"""Les listes d'un genre (table, table de ses éléments, colonne de la liste) qui contiennent l'élément, par nom, et
	si elles n'auront plus rien sans lui."""
	table, items, parent = container
	return connection.execute(
		f"SELECT c.internal_name, NOT EXISTS (SELECT 1 FROM {items} x WHERE x.{parent} = c.id"
		f" AND x.{column} IS DISTINCT FROM %s) FROM {table} c WHERE EXISTS (SELECT 1 FROM {items} x"
		f" WHERE x.{parent} = c.id AND x.{column} = %s) ORDER BY c.internal_name, c.id",
		(identifier, identifier),
	).fetchall()


def sound_location(connection: Connection, sound: int) -> TupleRow | None:
	return connection.execute("SELECT location FROM sounds WHERE id = %s", (sound,)).fetchone()


def all_bank_directories(connection: Connection) -> list[TupleRow]:
	"""Chaque répertoire de banque, avec le nom de sa banque."""
	return connection.execute(
		"SELECT b.internal_name, r.directory FROM bank_directories r JOIN banks b ON b.id = r.bank_id"
		" ORDER BY b.internal_name, r.directory"
	).fetchall()


def bank_directories(connection: Connection, bank: int) -> list[TupleRow]:
	return connection.execute(
		"SELECT directory FROM bank_directories WHERE bank_id = %s ORDER BY directory", (bank,)
	).fetchall()


def secured_streams(connection: Connection, event: int) -> list[TupleRow]:
	"""Le nom des streams que l'événement secourt."""
	return connection.execute(
		"SELECT COALESCE(title, stream_url) FROM sounds WHERE fallback_event_id = %s ORDER BY 1", (event,)
	).fetchall()


def following_streams(connection: Connection, feed: int) -> list[TupleRow]:
	"""Le nom des streams qui suivent le feed."""
	return connection.execute(
		"SELECT COALESCE(s.title, COALESCE(m.url, 'input:' || m.device)) FROM sounds s JOIN feeds m ON m.id = s.feed_id WHERE m.id = %s ORDER BY 1",
		(feed,),
	).fetchall()


def remove(connection: Connection, table: str, identifier: int) -> None:
	"""L'élément quitte la base."""
	connection.execute(f"DELETE FROM {table} WHERE id = %s", (identifier,))


def remove_from_lists(connection: Connection, items: str, column: str, identifier: int) -> None:
	"""L'élément quitte les listes d'un genre."""
	connection.execute(f"DELETE FROM {items} WHERE {column} = %s", (identifier,))


def no_more_fallback(connection: Connection, event: int) -> None:
	"""L'événement ne secourt plus aucun stream."""
	connection.execute("UPDATE sounds SET fallback_event_id = NULL WHERE fallback_event_id = %s", (event,))


def mark_deleted(connection: Connection, table: str, identifier: int, instant: object) -> None:
	connection.execute(f"UPDATE {table} SET deleted_at = %s WHERE id = %s", (instant, identifier))


def deleted_at(connection: Connection, table: str, identifier: int) -> TupleRow | None:
	return connection.execute(f"SELECT deleted_at FROM {table} WHERE id = %s", (identifier,)).fetchone()


def taken_by_another(connection: Connection, table: str, column: str, identifier: int) -> TupleRow | None:
	"""Le nom, ou l'emplacement, d'un autre élément non supprimé qui a repris celui de l'élément."""
	return connection.execute(
		f"SELECT o.{column} FROM {table} s JOIN {table} o ON o.{column} = s.{column}"
		" AND o.id <> s.id AND o.deleted_at IS NULL WHERE s.id = %s",
		(identifier,),
	).fetchone()


def restore(connection: Connection, table: str, identifier: int) -> None:
	connection.execute(f"UPDATE {table} SET deleted_at = NULL WHERE id = %s", (identifier,))
