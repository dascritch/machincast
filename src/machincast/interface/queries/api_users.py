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


# ─── Sessions (https://github.com/dascritch/machincast/issues/539) ───


class Pending(NamedTuple):
	"""Une connexion à distance, à valider au pupitre."""

	identifier: int
	user: str
	user_agent: str
	address: str
	code: str
	validate_before: datetime


class Opened(NamedTuple):
	"""Une session d'un compte, telle que la montre l'onglet."""

	identifier: int
	state: str
	origin: str
	created_at: datetime
	limit: datetime | None
	address: str
	user_agent: str


def _expire(connection: Connection) -> None:
	"""Comme le serveur : les sessions dont le délai est passé deviennent invalides."""
	connection.execute(
		"UPDATE api_sessions SET state = 'invalid', code = NULL, ended_at = clock_timestamp()"
		" WHERE (state = 'pending' AND validate_before < clock_timestamp())"
		" OR (state = 'valid' AND expires_at < clock_timestamp())"
	)


def pending(connection: Connection) -> list[Pending]:
	"""Les connexions à valider de comptes actifs, la plus ancienne en tête."""
	_expire(connection)
	found = []
	for row in connection.execute(
		"SELECT s.id, u.name, COALESCE(s.user_agent, ''), COALESCE(host(s.source_ip), ''), s.code,"
		" s.validate_before FROM api_sessions s JOIN api_users u ON u.id = s.user_id"
		" WHERE s.state = 'pending' AND u.disabled_at IS NULL ORDER BY s.created_at, s.id"
	).fetchall():
		identifier, user, agent, address, code, before = row
		assert isinstance(identifier, int)
		assert isinstance(before, datetime)
		found.append(Pending(identifier, str(user), str(agent), str(address), str(code), before))
	return found


def sessions_of(connection: Connection, user: int) -> list[Opened]:
	"""Les sessions d'un compte, la plus récente en tête ; la limite est celle de la validation, ou de la session."""
	_expire(connection)
	found = []
	for row in connection.execute(
		"SELECT id, state::text, origin::text, created_at,"
		" CASE WHEN state = 'pending' THEN validate_before ELSE expires_at END,"
		" COALESCE(host(source_ip), ''), COALESCE(user_agent, '')"
		" FROM api_sessions WHERE user_id = %s ORDER BY created_at DESC, id DESC",
		(user,),
	).fetchall():
		identifier, state, origin, created_at, limit, address, agent = row
		assert isinstance(identifier, int)
		assert isinstance(created_at, datetime)
		assert (limit is None) or (isinstance(limit, datetime))
		found.append(Opened(identifier, str(state), str(origin), created_at, limit, str(address), str(agent)))
	return found


def invalidate(connection: Connection, session: int) -> None:
	"""Refusée au pupitre, ou invalidée depuis l'onglet : la session ne sert plus."""
	connection.execute(
		"UPDATE api_sessions SET state = 'invalid', code = NULL, ended_at = clock_timestamp()"
		" WHERE id = %s AND state <> 'invalid'",
		(session,),
	)


def create_session(connection: Connection, user: int, token_hash: str, hours: int) -> None:
	"""Une session générée au pupitre, pour l'API : valide aussitôt, pour hours heures."""
	connection.execute(
		"INSERT INTO api_sessions (user_id, token_hash, origin, state, validated_at, expires_at)"
		" VALUES (%s, %s, 'interface', 'valid', clock_timestamp(), clock_timestamp() + make_interval(hours => %s))",
		(user, token_hash, hours),
	)
