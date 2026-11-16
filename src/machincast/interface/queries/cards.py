"""Requêtes communes aux fiches (https://github.com/dascritch/machincast/issues/442).

La table est une constante du code de l'appelant (deletion.CATEGORIES), jamais une saisie."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def name_in_use(connection: Connection, table: str, name: str) -> bool:
	"""Un élément non supprimé de la table porte ce nom interne."""
	taken = connection.execute(
		f"SELECT 1 FROM {table} WHERE internal_name = %s AND deleted_at IS NULL", (name,)
	).fetchone()
	return taken is not None


def exists(connection: Connection, table: str, identifier: int | None) -> bool:
	"""L'élément est en base, même supprimé."""
	return connection.execute(f"SELECT 1 FROM {table} WHERE id = %s", (identifier,)).fetchone() is not None


def sound_of_file(connection: Connection, file: str) -> int | None:
	"""Le sonore non supprimé de ce fichier ; None s'il n'est pas en base."""
	line = connection.execute("SELECT id FROM sounds WHERE location = %s AND deleted_at IS NULL", (file,)).fetchone()
	if line is None:
		return None
	return int(str(line[0]))


def create_preview_sound(connection: Connection, file: str) -> int:
	"""Un fichier déposé entre en base à l'état aperçu."""
	line = connection.execute(
		"INSERT INTO sounds (type, location, state) VALUES ('file', %s, 'preview') RETURNING id", (file,)
	).fetchone()
	assert line is not None
	return int(str(line[0]))
