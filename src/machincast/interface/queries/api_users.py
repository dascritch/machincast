"""Requêtes de l'onglet « API » : les comptes de l'intranet et de l'API
(https://github.com/dascritch/machincast/issues/537).

Le mot de passe n'arrive ici que par son empreinte (machincast.shared.passwords).
"""

from datetime import datetime
from typing import NamedTuple

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]
ROLES = ("consult", "actions")
"""Les rôles d'un compte, dans l'ordre du type api_role."""


class User(NamedTuple):
	"""Un compte, tel que le montre l'onglet."""

	identifier: int
	name: str
	role: str
	disabled_at: datetime | None
	created_at: datetime


def users(connection: Connection) -> list[User]:
	"""Les comptes, par nom."""
	found = []
	for row in connection.execute(
		"SELECT id, name, role::text, disabled_at, created_at FROM api_users ORDER BY name, id"
	).fetchall():
		identifier, name, role, disabled_at, created_at = row
		assert isinstance(identifier, int)
		assert isinstance(name, str)
		assert isinstance(role, str)
		assert (disabled_at is None) or (isinstance(disabled_at, datetime))
		assert isinstance(created_at, datetime)
		found.append(User(identifier, name, role, disabled_at, created_at))
	return found


def name_taken(connection: Connection, name: str) -> bool:
	"""Un compte porte déjà ce nom."""
	return connection.execute("SELECT 1 FROM api_users WHERE name = %s", (name,)).fetchone() is not None


def create(connection: Connection, name: str, password_hash: str, role: str) -> int:
	"""Un nouveau compte, actif ; son identifiant."""
	row = connection.execute(
		"INSERT INTO api_users (name, password_hash, role) VALUES (%s, %s, %s) RETURNING id",
		(name, password_hash, role),
	).fetchone()
	assert row is not None
	identifier = row[0]
	assert isinstance(identifier, int)
	return identifier


def set_role(connection: Connection, identifier: int, role: str) -> None:
	connection.execute("UPDATE api_users SET role = %s WHERE id = %s", (role, identifier))


def set_password(connection: Connection, identifier: int, password_hash: str) -> None:
	connection.execute("UPDATE api_users SET password_hash = %s WHERE id = %s", (password_hash, identifier))


def set_disabled(connection: Connection, identifier: int, *, disabled: bool) -> None:
	"""Désactive le compte, à l'heure de la base, ou le réactive."""
	if disabled:
		connection.execute(
			"UPDATE api_users SET disabled_at = clock_timestamp() WHERE id = %s AND disabled_at IS NULL", (identifier,)
		)
		return
	connection.execute("UPDATE api_users SET disabled_at = NULL WHERE id = %s", (identifier,))


def delete(connection: Connection, identifier: int) -> None:
	connection.execute("DELETE FROM api_users WHERE id = %s", (identifier,))
