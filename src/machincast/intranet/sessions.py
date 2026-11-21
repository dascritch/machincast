"""Les sessions de l'intranet et de l'API, côté serveur (https://github.com/dascritch/machincast/issues/539).

1. Nom et mot de passe valides, d'un compte actif : une session à valider (pending), un cookie aléatoire dont la base
   ne garde que l'empreinte SHA-256, et un code à 6 chiffres. L'interface montre au pupitre qui demande à se
   connecter ; elle n'en montre le code qu'une fois la connexion acceptée (accepted_at), et aucun code n'est essayé
   avant (https://github.com/dascritch/machincast/issues/547).
2. Le code saisi sur le poste distant, avant validate_before : la session devient valide, jusqu'à expires_at.
   Un code faux est compté ; au cinquième, comme passé le délai, la session est invalide. Un compte n'a que
   MAXIMUM_PENDING sessions à valider à la fois ; le portail freine aussi les codes faux, par adresse et par compte
   (https://github.com/dascritch/machincast/issues/547).
3. Une session valide sert l'intranet comme l'API : le même cookie, ou « Authorization: Bearer ».

Les heures sont celles de la base (clock_timestamp()) ; un délai passé se juge à la lecture (STATE_NOW). Ces
fonctions, sans asyncio, s'appellent hors de la boucle du serveur (asyncio.to_thread), chacune dans sa transaction.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow

from machincast.shared import passwords

Connection = psycopg.Connection[TupleRow]

ATTEMPTS = 5
"""Codes faux permis avant que la session soit invalide."""
MAXIMUM_PENDING = 2
PENDING_LOCK = 547
"""Le premier mot du verrou consultatif qui compte les sessions à valider d'un compte, le second étant son id."""
"""Sessions à valider d'un compte, au plus, à la fois (https://github.com/dascritch/machincast/issues/547)."""
TOKEN_BYTES = 32
COOKIE = "machincast_session"
DECOY = passwords.digest("machincast-decoy-password")
"""Une empreinte vérifiée pour un nom inconnu : la réponse prend le même temps, et ne dit pas si le compte existe."""


def token() -> str:
	"""Un jeton de session aléatoire, à mettre dans le cookie."""
	return secrets.token_urlsafe(TOKEN_BYTES)


def fingerprint(value: str) -> str:
	"""L'empreinte d'un jeton, seule gardée en base."""
	return hashlib.sha256(value.encode("utf-8")).hexdigest()


def code() -> str:
	"""Un code à 6 chiffres, de 000000 à 999999."""
	return f"{secrets.randbelow(1_000_000):06d}"


@dataclass(frozen=True)
class Session:
	"""Une session, telle que le serveur la lit."""

	identifier: int
	user: str
	role: str
	state: str
	expires_at: datetime | None


def authenticate(connection: Connection, name: str, password: str) -> int | None:
	"""L'identifiant du compte actif à ce nom et ce mot de passe ; None sinon, dans le même temps."""
	with connection.transaction():
		row = connection.execute(
			"SELECT id, password_hash FROM api_users WHERE name = %s AND disabled_at IS NULL", (name,)
		).fetchone()
	if row is None:
		passwords.matches(password, DECOY)
		return None
	identifier, stored = row
	if not passwords.matches(password, str(stored)):
		return None
	assert isinstance(identifier, int)
	return identifier


def open_pending(
	connection: Connection, user: int, value: str, validation: int, user_agent: str, address: str
) -> str | None:
	"""Une session à valider dans les minutes de validation ; le code à donner au pupitre. None si le compte a déjà
	MAXIMUM_PENDING sessions à valider : le pupitre les valide ou les refuse, ou leur délai passe."""
	given = code()
	with connection.transaction():
		_expire(connection)
		# Le compte verrouillé le temps de compter, sans droit d'écriture sur api_users : deux connexions simultanées ne
		# dépassent pas la limite.
		connection.execute("SELECT pg_advisory_xact_lock(%s, %s)", (PENDING_LOCK, user))
		waiting = connection.execute(
			"SELECT count(*) FROM api_sessions WHERE user_id = %s AND state = 'pending'", (user,)
		).fetchone()
		if (waiting is not None) and (int(waiting[0]) >= MAXIMUM_PENDING):
			return None
		connection.execute(
			"INSERT INTO api_sessions (user_id, token_hash, code, user_agent, source_ip, validate_before)"
			" VALUES (%s, %s, %s, %s, %s, clock_timestamp() + make_interval(mins => %s))",
			(user, fingerprint(value), given, user_agent[:500], (address) or (None), validation),
		)
	return given


STATE_NOW = (
	"CASE WHEN (s.state = 'pending' AND s.validate_before < clock_timestamp())"
	" OR (s.state = 'valid' AND s.expires_at < clock_timestamp()) THEN 'invalid' ELSE s.state::text END"
)
"""L'état d'une session à l'instant, son délai passé : invalide."""


def _expire(connection: Connection) -> None:
	"""Les sessions à valider dont le délai est passé, et les valides expirées, deviennent invalides."""
	connection.execute(
		"UPDATE api_sessions SET state = 'invalid', code = NULL, ended_at = clock_timestamp()"
		" WHERE (state = 'pending' AND validate_before < clock_timestamp())"
		" OR (state = 'valid' AND expires_at < clock_timestamp())"
	)


def find(connection: Connection, value: str) -> Session | None:
	"""La session de ce jeton, d'un compte actif ; None, jeton inconnu ou compte désactivé."""
	with connection.transaction():
		# Le délai se juge à la lecture, sans rien écrire : chaque requête lit, seule la connexion ou la validation
		# écrit (https://github.com/dascritch/machincast/issues/553).
		row = connection.execute(
			f"SELECT s.id, u.name, u.role::text, {STATE_NOW}, s.expires_at FROM api_sessions s"
			" JOIN api_users u ON u.id = s.user_id WHERE s.token_hash = %s AND u.disabled_at IS NULL",
			(fingerprint(value),),
		).fetchone()
	if row is None:
		return None
	identifier, user, role, state, expires_at = row
	assert isinstance(identifier, int)
	assert (expires_at is None) or (isinstance(expires_at, datetime))
	return Session(identifier, str(user), str(role), str(state), expires_at)


def validate(connection: Connection, value: str, given: str, hours: int) -> str:
	"""Le code saisi : « waiting », la connexion pas encore acceptée au pupitre, sans essayer le code ; « valid », la
	session validée pour hours heures ; « wrong », un code faux, encore permis ;
	« exhausted », un code faux, le dernier permis, qui rend la session invalide ; « invalid », la session ne se
	valide plus."""
	with connection.transaction():
		row = connection.execute(
			"SELECT id, code, attempts, accepted_at, validate_before < clock_timestamp() FROM api_sessions"
			" WHERE token_hash = %s AND state = 'pending' FOR UPDATE",
			(fingerprint(value),),
		).fetchone()
		if row is None:
			return "invalid"
		identifier, expected, attempts, accepted_at, late = row
		if late:
			connection.execute(
				"UPDATE api_sessions SET state = 'invalid', code = NULL, ended_at = clock_timestamp() WHERE id = %s",
				(identifier,),
			)
			return "invalid"
		if accepted_at is None:
			# Pas encore acceptée au pupitre : le code n'y est pas encore donné, aucun n'est essayé.
			return "waiting"
		if secrets.compare_digest(str(expected), given.strip().replace(" ", "")):
			connection.execute(
				# Un seul instant pour la validation et la fin de la session : elle dure exactement hours.
				"UPDATE api_sessions SET state = 'valid', code = NULL, validated_at = moment.now,"
				" expires_at = moment.now + make_interval(hours => %s) FROM (SELECT clock_timestamp() AS now) moment"
				" WHERE id = %s",
				(hours, identifier),
			)
			return "valid"
		assert isinstance(attempts, int)
		if attempts + 1 >= ATTEMPTS:
			connection.execute(
				"UPDATE api_sessions SET state = 'invalid', code = NULL, attempts = attempts + 1,"
				" ended_at = clock_timestamp() WHERE id = %s",
				(identifier,),
			)
			return "exhausted"
		connection.execute("UPDATE api_sessions SET attempts = attempts + 1 WHERE id = %s", (identifier,))
		return "wrong"


def end(connection: Connection, value: str) -> None:
	"""La déconnexion : la session devient invalide."""
	with connection.transaction():
		connection.execute(
			"UPDATE api_sessions SET state = 'invalid', code = NULL, ended_at = clock_timestamp()"
			" WHERE token_hash = %s AND state <> 'invalid'",
			(fingerprint(value),),
		)
