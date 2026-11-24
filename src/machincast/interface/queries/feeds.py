"""Requêtes de la fiche d'un feed (https://github.com/dascritch/machincast/issues/442)."""

from datetime import timedelta

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def read_feed(connection: Connection, feed: int) -> TupleRow | None:
	"""Nom, adresse, mémoire tampon et périphérique d'entrée audio du feed ; None s'il est absent."""
	return connection.execute("SELECT name, url, buffer_duration, device FROM feeds WHERE id = %s", (feed,)).fetchone()


def streams(connection: Connection, feed: int, default_title: str) -> list[TupleRow]:
	"""Les streams qui suivent le feed, par titre (ou, sans titre, default_title) : identifiant et titre."""
	return connection.execute(
		"SELECT id, COALESCE(title, %s) FROM sounds WHERE feed_id = %s AND deleted_at IS NULL ORDER BY 2, id",
		(default_title, feed),
	).fetchall()


def name_taken(connection: Connection, name: str, identifier: int | None) -> bool:
	"""Un autre feed porte ce nom."""
	taken = connection.execute(
		"SELECT 1 FROM feeds WHERE name = %s AND id IS DISTINCT FROM %s", (name, identifier)
	).fetchone()
	return taken is not None


def insert(connection: Connection, name: str, url: str, buffer: timedelta) -> int:
	created = connection.execute(
		"INSERT INTO feeds (name, url, buffer_duration) VALUES (%s, %s, %s) RETURNING id", (name, url, buffer)
	).fetchone()
	assert created is not None
	return int(str(created[0]))


def update(connection: Connection, identifier: int, name: str, url: str, buffer: timedelta) -> None:
	connection.execute(
		"UPDATE feeds SET name = %s, url = %s, buffer_duration = %s WHERE id = %s",
		(name, url, buffer, identifier),
	)


def active_stream(connection: Connection, feed: int) -> TupleRow | None:
	"""Le stream qui suit le feed, un actif d'abord, le plus ancien : identifiant et s'il est actif."""
	return connection.execute(
		"SELECT id, state = 'active' FROM sounds WHERE feed_id = %s AND type = 'stream' AND deleted_at IS NULL"
		" ORDER BY state = 'active' DESC, id LIMIT 1",
		(feed,),
	).fetchone()


# ─── Les feeds d'entrée audio (https://github.com/dascritch/machincast/issues/623) ───


def input_feeds(connection: Connection) -> list[TupleRow]:
	"""Les feeds d'entrée audio : identifiant, nom et périphérique."""
	return connection.execute("SELECT id, name, device FROM feeds WHERE device IS NOT NULL ORDER BY id").fetchall()


def insert_input(connection: Connection, name: str, device: str) -> int:
	"""Le feed d'une entrée audio, et un stream actif qui le suit, du nom de l'entrée."""
	created = connection.execute(
		"INSERT INTO feeds (name, device) VALUES (%s, %s) RETURNING id", (name, device)
	).fetchone()
	assert created is not None
	feed = int(str(created[0]))
	connection.execute(
		"INSERT INTO sounds (type, feed_id, title, state) VALUES ('stream', %s, %s, 'active')", (feed, name)
	)
	return feed


def give_name(connection: Connection, identifier: int, name: str) -> None:
	connection.execute("UPDATE feeds SET name = %s WHERE id = %s", (name, identifier))
