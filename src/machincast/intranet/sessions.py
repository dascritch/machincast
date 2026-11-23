"""Les sessions de l'intranet et de l'API, côté serveur (https://github.com/dascritch/machincast/issues/539).

1. Nom et mot de passe valides, d'un compte actif : une session à valider (pending), un cookie aléatoire dont la base
   ne garde que l'empreinte SHA-256, et un code à 6 chiffres. L'interface montre au pupitre qui demande à se
   connecter ; elle n'en montre le code qu'une fois la connexion acceptée (accepted_at), et aucun code n'est essayé
   avant (https://github.com/dascritch/machincast/issues/547).
2. Le code saisi sur le poste distant, avant validate_before : la session devient valide, jusqu'à expires_at.
   Selon intranet.first_login (https://github.com/dascritch/machincast/issues/600), la session à valider n'a pas de
   code, et l'acceptation au pupitre suffit ; ou, sans validation, elle est valide dès la connexion.
   Un code faux est compté ; au cinquième, comme passé le délai, la session est invalide. Un compte n'a que
   MAXIMUM_PENDING sessions à valider à la fois ; le portail freine aussi les codes faux, par adresse et par compte
   (https://github.com/dascritch/machincast/issues/547).
3. Une session valide sert l'intranet comme l'API : le même cookie, ou « Authorization: Bearer ».

Les heures sont celles de la base (clock_timestamp()) ; un délai passé se juge à la lecture (queries.STATE_NOW). Ces
fonctions, sans asyncio, s'appellent hors de la boucle du serveur (asyncio.to_thread), chacune dans sa transaction.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow

from machincast.intranet import queries
from machincast.shared import passwords, totp

Connection = psycopg.Connection[TupleRow]

ATTEMPTS = 5
"""Codes faux permis avant que la session soit invalide."""
MAXIMUM_PENDING = 2
PENDING_LOCK = 547
"""Le premier mot du verrou consultatif qui compte les sessions à valider d'un compte, le second étant son id."""
"""Sessions à valider d'un compte, au plus, à la fois (https://github.com/dascritch/machincast/issues/547)."""
TOKEN_BYTES = 32
COOKIE = "machincast_session"
BROWSER_COOKIE = "machincast_browser"
"""Le cookie d'un navigateur connu (https://github.com/dascritch/machincast/issues/601)."""
BROWSER_DAYS = 400
"""Jours du cookie d'un navigateur connu : la limite des navigateurs courants."""
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
		row = queries.password_of(connection, name)
	if row is None:
		passwords.matches(password, DECOY)
		return None
	identifier, stored = row
	if not passwords.matches(password, str(stored)):
		return None
	assert isinstance(identifier, int)
	return identifier


def open_pending(
	connection: Connection,
	user: int,
	value: str,
	validation: int,
	client: tuple[str, str],
	*,
	with_code: bool = True,
	steps: tuple[bool, bool] = (True, False),
) -> str | None:
	"""Une session à valider dans les minutes de validation ; le code à donner au pupitre, « » sans code, quand
	l'acceptation au pupitre suffit (https://github.com/dascritch/machincast/issues/600). steps : ce qu'elle attend, le
	pupitre et l'application d'authentification (https://github.com/dascritch/machincast/issues/601). None si le compte
	a déjà MAXIMUM_PENDING sessions à valider : le pupitre les valide ou les refuse, ou leur délai passe."""
	user_agent, address = client
	given = ""
	if (with_code) and (steps[0]):
		given = code()
	with connection.transaction():
		_expire(connection)
		# Le compte verrouillé le temps de compter, sans droit d'écriture sur api_users : deux connexions simultanées ne
		# dépassent pas la limite.
		queries.lock_user(connection, PENDING_LOCK, user)
		if queries.pending_count(connection, user) >= MAXIMUM_PENDING:
			return None
		queries.insert_pending(
			connection,
			user,
			fingerprint(value),
			(given) or (None),
			(user_agent[:500], (address) or (None)),
			validation,
			steps,
		)
	return given


def open_valid(connection: Connection, user: int, value: str, hours: int, client: tuple[str, str]) -> None:
	"""Une session valide aussitôt, pour hours heures, sans validation au pupitre
	(https://github.com/dascritch/machincast/issues/600)."""
	user_agent, address = client
	with connection.transaction():
		queries.insert_valid(connection, user, fingerprint(value), (user_agent[:500], (address) or (None)), hours)


def known_browser(connection: Connection, user: int, value: str | None) -> bool:
	"""Le cookie de ce navigateur est celui d'un navigateur connu du compte
	(https://github.com/dascritch/machincast/issues/601)."""
	if not value:
		return False
	with connection.transaction():
		return queries.known_browser(connection, user, fingerprint(value))


def remember_browser(connection: Connection, session: str) -> str:
	"""Le navigateur de cette session, désormais valide, retenu pour son compte : le cookie à lui donner, dont la base
	ne garde que l'empreinte (https://github.com/dascritch/machincast/issues/601)."""
	value = token()
	with connection.transaction():
		queries.remember_browser(connection, fingerprint(value), fingerprint(session))
	return value


def totp_secret(connection: Connection, user: int) -> str | None:
	"""La clé de l'application d'authentification du compte ; None sans elle."""
	with connection.transaction():
		return queries.totp_secret(connection, user)


@dataclass(frozen=True)
class Pending:
	"""Une session à valider, telle que la validation la lit (https://github.com/dascritch/machincast/issues/601)."""

	identifier: int
	code: str | None
	attempts: int
	accepted: bool
	late: bool
	desk: bool
	totp: bool
	user: int
	secret: str | None

	def stage(self) -> str:
		"""Ce qu'elle attend : « waiting », l'acceptation au pupitre, sans code ; « code », le code du pupitre ;
		« totp », celui de l'application d'authentification ; « ready », plus rien."""
		if (self.desk) and (self.code is not None):
			return "code"
		if (self.desk) and (not self.accepted):
			return "waiting"
		if self.totp:
			return "totp"
		return "ready"


def _pending(connection: Connection, value: str, *, lock: bool) -> Pending | None:
	row = queries.pending_session(connection, fingerprint(value), lock=lock)
	if row is None:
		return None
	identifier, expected, attempts, accepted_at, late, desk, totp, user, secret = row
	assert isinstance(identifier, int)
	assert isinstance(attempts, int)
	assert isinstance(user, int)
	found_code = None
	if expected is not None:
		found_code = str(expected)
	found_secret = None
	if secret is not None:
		found_secret = str(secret)
	return Pending(
		identifier,
		found_code,
		attempts,
		accepted_at is not None,
		bool(late),
		bool(desk),
		bool(totp),
		user,
		found_secret,
	)


def stage(connection: Connection, value: str) -> str:
	"""Ce qu'attend la session à valider de ce jeton (Pending.stage), sans rien écrire ; « invalid », elle ne se valide
	plus."""
	with connection.transaction():
		found = _pending(connection, value, lock=False)
	if (found is None) or (found.late):
		return "invalid"
	return found.stage()


def _expire(connection: Connection) -> None:
	"""Les sessions à valider dont le délai est passé, et les valides expirées, deviennent invalides."""
	queries.expire_sessions(connection)


def find(connection: Connection, value: str) -> Session | None:
	"""La session de ce jeton, d'un compte actif ; None, jeton inconnu ou compte désactivé."""
	with connection.transaction():
		# Le délai se juge à la lecture, sans rien écrire : chaque requête lit, seule la connexion ou la validation
		# écrit (https://github.com/dascritch/machincast/issues/553).
		row = queries.session_of(connection, fingerprint(value))
	if row is None:
		return None
	identifier, user, role, state, expires_at = row
	assert isinstance(identifier, int)
	assert (expires_at is None) or (isinstance(expires_at, datetime))
	return Session(identifier, str(user), str(role), str(state), expires_at)


@dataclass
class Validation:
	"""Ce qu'il faut pour valider une session : le jeton, ce qui est saisi, la durée de la session, et, pour
	l'application d'authentification, l'heure et le dernier pas accepté de chaque compte, qu'un code ne serve qu'une
	fois (https://github.com/dascritch/machincast/issues/601)."""

	value: str
	given: str | None
	hours: int
	at: datetime | None = None
	used: dict[int, int] = field(default_factory=dict)


def validate(connection: Connection, validation: Validation) -> str:
	"""Le code saisi : « waiting », la connexion pas encore acceptée au pupitre, sans essayer le code ; « valid », la
	session validée pour hours heures ; « totp », le code du pupitre exact, reste celui de l'application
	d'authentification (https://github.com/dascritch/machincast/issues/601) ; « wrong » et « wrong_totp », un code
	faux, encore permis ; « exhausted », un code faux, le dernier permis, qui rend la session invalide ; « invalid », la
	session ne se valide plus. Sans code du pupitre, son acceptation suffit
	(https://github.com/dascritch/machincast/issues/600) ; given None, rien de saisi, n'essaie aucun code."""
	with connection.transaction():
		found = _pending(connection, validation.value, lock=True)
		if found is None:
			return "invalid"
		if found.late:
			queries.invalidate(connection, found.identifier)
			return "invalid"
		if (found.desk) and (not found.accepted):
			# Pas encore acceptée au pupitre : le code n'y est pas encore donné, aucun n'est essayé.
			return "waiting"
		chosen = found.stage()
		if chosen == "ready":
			queries.validate(connection, found.identifier, validation.hours)
			return "valid"
		if validation.given is None:
			# Rien de saisi : la page relue, qui ne fait entrer qu'une session qui n'attend plus rien.
			return "waiting"
		if chosen == "code":
			return _desk_code(connection, found, validation)
		return _totp_code(connection, found, validation)


def _desk_code(connection: Connection, found: Pending, validation: Validation) -> str:
	assert validation.given is not None
	if not secrets.compare_digest(str(found.code), validation.given.strip().replace(" ", "")):
		return _wrong(connection, found, "wrong")
	if found.totp:
		queries.clear_code(connection, found.identifier)
		return "totp"
	queries.validate(connection, found.identifier, validation.hours)
	return "valid"


def _totp_code(connection: Connection, found: Pending, validation: Validation) -> str:
	assert validation.given is not None
	matched = None
	if (found.secret is not None) and (validation.at is not None):
		matched = totp.matching_step(found.secret, validation.given, validation.at)
	# Un code déjà accepté pour ce compte ne sert pas deux fois.
	if (matched is None) or (matched <= validation.used.get(found.user, -1)):
		return _wrong(connection, found, "wrong_totp")
	validation.used[found.user] = matched
	queries.validate(connection, found.identifier, validation.hours)
	return "valid"


def _wrong(connection: Connection, found: Pending, outcome: str) -> str:
	if found.attempts + 1 >= ATTEMPTS:
		queries.exhaust(connection, found.identifier)
		return "exhausted"
	queries.wrong_attempt(connection, found.identifier)
	return outcome


def end(connection: Connection, value: str) -> None:
	"""La déconnexion : la session devient invalide."""
	with connection.transaction():
		queries.end(connection, fingerprint(value))
