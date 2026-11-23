"""Les lectures de l'API de l'intranet (https://github.com/dascritch/machincast/issues/540), au rôle
machincast_intranet, qui ne fait que lire.

Chaque fonction rend des objets prêts pour JSON : dictionnaires, listes, textes, nombres, dates, que l'API sérialise
(machincast.intranet.api.dumps). Les listes se lisent par pages, triées par identifiant : `after` le dernier
identifiant reçu, `limit` lignes au plus. Un élément supprimé n'est pas dans les listes ; sa fiche se lit encore,
`deleted_at` renseigné.
"""

from typing import Any

import psycopg
from psycopg.rows import TupleRow, dict_row

Connection = psycopg.Connection[TupleRow]
Row = dict[str, Any]

LISTS = {
	"sounds": (
		"SELECT id, type::text, artist, title, location, stream_url, state::text, duration, modified_at FROM sounds"
	),
	"banks": "SELECT id, internal_name, public_name, mode::text, no_repeat, modified_at FROM banks",
	"sequences": "SELECT id, internal_name, public_name, modified_at FROM sequences",
	"events": (
		"SELECT id, internal_name, public_name, priority::text, starts_at, ends_at,"
		" recurrence_days::text[] AS recurrence_days, modified_at FROM events"
	),
}
"""Chaque liste, par son nom dans l'adresse de l'API."""
CARDS = {
	"sounds": "SELECT *, type::text AS type, state::text AS state FROM sounds WHERE id = %s",
	"banks": "SELECT *, mode::text AS mode FROM banks WHERE id = %s",
	"sequences": "SELECT * FROM sequences WHERE id = %s",
	"events": (
		"SELECT *, priority::text AS priority, recurrence_days::text[] AS recurrence_days, end_of_list::text AS"
		" end_of_list FROM events WHERE id = %s"
	),
}
HIDDEN = frozenset({"edited_fields"})
"""Ce qu'une fiche de l'API ne dit pas : la cuisine de l'indexation."""
ITEMS = {
	"events": (
		"SELECT i.position, i.sound_id, i.bank_id, i.sequence_id,"
		" COALESCE(NULLIF(concat_ws(' – ', s.artist, s.title), ''), s.location, b.internal_name, q.internal_name)"
		" AS name FROM event_items i LEFT JOIN sounds s ON s.id = i.sound_id LEFT JOIN banks b ON b.id = i.bank_id"
		" LEFT JOIN sequences q ON q.id = i.sequence_id WHERE i.event_id = %s ORDER BY i.position"
	),
	"sequences": (
		"SELECT i.position, i.sound_id, i.bank_id,"
		" COALESCE(NULLIF(concat_ws(' – ', s.artist, s.title), ''), s.location, b.internal_name) AS name"
		" FROM sequence_items i LEFT JOIN sounds s ON s.id = i.sound_id LEFT JOIN banks b ON b.id = i.bank_id"
		" WHERE i.sequence_id = %s ORDER BY i.position"
	),
	"banks": (
		"SELECT l.position, l.sound_id, COALESCE(NULLIF(concat_ws(' – ', s.artist, s.title), ''), s.location) AS name,"
		" s.state::text AS state FROM bank_sounds l JOIN sounds s ON s.id = l.sound_id WHERE l.bank_id = %s"
		" ORDER BY l.position"
	),
}
DEFAULT_LIMIT = 100
MAXIMUM_LIMIT = 1000
INCIDENTS = 100
"""Incidents lus au plus, les plus récents."""
PLAYS = 5


def _rows(connection: Connection, query: str, parameters: tuple[object, ...]) -> list[Row]:
	with connection.transaction(), connection.cursor(row_factory=dict_row) as cursor:
		return list(cursor.execute(query, parameters).fetchall())


def page(connection: Connection, kind: str, after: int, limit: int) -> list[Row]:
	"""Une page d'une liste : les éléments non supprimés d'identifiant plus grand que after."""
	return _rows(connection, f"{LISTS[kind]} WHERE deleted_at IS NULL AND id > %s ORDER BY id LIMIT %s", (after, limit))


def card(connection: Connection, kind: str, identifier: int) -> Row | None:
	"""La fiche d'un élément, ses éléments ou ses sonores compris ; None s'il n'existe pas."""
	found = _rows(connection, CARDS[kind], (identifier,))
	if found == []:
		return None
	fields: Row = {}
	for name, value in found[0].items():
		if name not in HIDDEN:
			fields[name] = value
	if kind in ITEMS:
		fields["items"] = _rows(connection, ITEMS[kind], (identifier,))
	if kind == "banks":
		fields["directories"] = _rows(
			connection,
			"SELECT directory, scanned_at FROM bank_directories WHERE bank_id = %s ORDER BY directory",
			(identifier,),
		)
	return fields


def incidents(connection: Connection, count: int = INCIDENTS) -> list[Row]:
	"""Les incidents seulement, les plus récents en tête, avec ce qu'ils concernent."""
	return _rows(
		connection,
		"SELECT l.id, l.logged_at, l.kind, l.message, l.sound_id, l.bank_id, l.event_id,"
		" COALESCE(NULLIF(concat_ws(' – ', s.artist, s.title), ''), s.location) AS sound, b.internal_name AS bank,"
		" e.internal_name AS event FROM log l LEFT JOIN sounds s ON s.id = l.sound_id"
		" LEFT JOIN banks b ON b.id = l.bank_id LEFT JOIN events e ON e.id = l.event_id"
		" WHERE l.level = 'incident' ORDER BY l.logged_at DESC, l.id DESC LIMIT %s",
		(count,),
	)


def previous_plays(connection: Connection, count: int = PLAYS) -> list[Row]:
	"""Les derniers passages terminés, le plus récent en tête : début, fin, et ce qui les a joués."""
	return _rows(
		connection,
		"SELECT d.sound_id, d.artist, d.title, d.location, d.logged_at AS start, f.logged_at AS end,"
		" f.played_duration AS duration, d.event_id, e.internal_name AS event, d.sequence_id,"
		" q.internal_name AS sequence, d.bank_id, b.internal_name AS bank FROM airplay d"
		" JOIN airplay f ON f.play_id = d.play_id AND f.line_type = 'end'"
		" LEFT JOIN events e ON e.id = COALESCE(d.lender_event_id, d.event_id)"
		" LEFT JOIN sequences q ON q.id = d.sequence_id LEFT JOIN banks b ON b.id = d.bank_id"
		" WHERE d.line_type = 'start' ORDER BY d.logged_at DESC, d.id DESC LIMIT %s",
		(count,),
	)


# ─── Sessions (machincast.intranet.sessions, https://github.com/dascritch/machincast/issues/539) ───
# Sans transaction : machincast.intranet.sessions les ouvre, et y enchaîne ces requêtes.

STATE_NOW = (
	"CASE WHEN (s.state = 'pending' AND s.validate_before < clock_timestamp())"
	" OR (s.state = 'valid' AND s.expires_at < clock_timestamp()) THEN 'invalid' ELSE s.state::text END"
)
"""L'état d'une session à l'instant, son délai passé : invalide."""


def password_of(connection: Connection, name: str) -> TupleRow | None:
	"""L'identifiant et l'empreinte du mot de passe du compte actif à ce nom."""
	return connection.execute(
		"SELECT id, password_hash FROM api_users WHERE name = %s AND disabled_at IS NULL", (name,)
	).fetchone()


def lock_user(connection: Connection, lock: int, user: int) -> None:
	"""Le compte verrouillé jusqu'à la fin de la transaction, sans droit d'écriture sur api_users."""
	connection.execute("SELECT pg_advisory_xact_lock(%s, %s)", (lock, user))


def pending_count(connection: Connection, user: int) -> int:
	"""Les sessions à valider du compte."""
	row = connection.execute(
		"SELECT count(*) FROM api_sessions WHERE user_id = %s AND state = 'pending'", (user,)
	).fetchone()
	assert row is not None
	return int(row[0])


def insert_pending(
	connection: Connection,
	user: int,
	token_hash: str,
	code: str | None,
	client: tuple[str, str | None],
	minutes: int,
	steps: tuple[bool, bool] = (True, False),
) -> None:
	"""Une session à valider dans les minutes données : l'empreinte de son jeton, son code, aucun quand le pupitre
	suffit (https://github.com/dascritch/machincast/issues/600), le navigateur et l'adresse du poste distant, et ce
	qu'elle attend, le pupitre et l'application d'authentification (https://github.com/dascritch/machincast/issues/601)."""
	user_agent, address = client
	desk, totp = steps
	connection.execute(
		"INSERT INTO api_sessions (user_id, token_hash, code, user_agent, source_ip, validate_before, desk, totp)"
		" VALUES (%s, %s, %s, %s, %s, clock_timestamp() + make_interval(mins => %s), %s, %s)",
		(user, token_hash, code, user_agent, address, minutes, desk, totp),
	)


def insert_valid(
	connection: Connection, user: int, token_hash: str, client: tuple[str, str | None], hours: int
) -> None:
	"""Une session valide aussitôt, pour hours heures, sans validation au pupitre
	(https://github.com/dascritch/machincast/issues/600) : l'empreinte de son jeton, le navigateur et l'adresse du
	poste distant."""
	user_agent, address = client
	connection.execute(
		"INSERT INTO api_sessions (user_id, token_hash, user_agent, source_ip, state, validated_at, expires_at)"
		" SELECT %s, %s, %s, %s, 'valid', moment.now, moment.now + make_interval(hours => %s)"
		" FROM (SELECT clock_timestamp() AS now) moment",
		(user, token_hash, user_agent, address, hours),
	)


def expire_sessions(connection: Connection) -> None:
	"""Les sessions à valider dont le délai est passé, et les valides expirées, deviennent invalides."""
	connection.execute(
		"UPDATE api_sessions SET state = 'invalid', code = NULL, ended_at = clock_timestamp()"
		" WHERE (state = 'pending' AND validate_before < clock_timestamp())"
		" OR (state = 'valid' AND expires_at < clock_timestamp())"
	)


def session_of(connection: Connection, token_hash: str) -> TupleRow | None:
	"""La session de ce jeton, d'un compte actif : son identifiant, son compte, son rôle, son état à l'instant et sa
	fin ; sans rien écrire (https://github.com/dascritch/machincast/issues/553)."""
	return connection.execute(
		f"SELECT s.id, u.name, u.role::text, {STATE_NOW}, s.expires_at FROM api_sessions s"
		" JOIN api_users u ON u.id = s.user_id WHERE s.token_hash = %s AND u.disabled_at IS NULL",
		(token_hash,),
	).fetchone()


def pending_session(connection: Connection, token_hash: str, *, lock: bool = True) -> TupleRow | None:
	"""La session à valider de ce jeton, verrouillée sauf pour la lire : son identifiant, son code, ses essais, son
	acceptation au pupitre, si son délai est passé, ce qu'elle attend, le pupitre et l'application d'authentification,
	et son compte, avec la clé de son application (https://github.com/dascritch/machincast/issues/601)."""
	locking = ""
	if lock:
		locking = " FOR UPDATE OF s"
	return connection.execute(
		"SELECT s.id, s.code, s.attempts, s.accepted_at, s.validate_before < clock_timestamp(), s.desk, s.totp,"
		" s.user_id, u.totp_secret FROM api_sessions s JOIN api_users u ON u.id = s.user_id"
		f" WHERE s.token_hash = %s AND s.state = 'pending'{locking}",
		(token_hash,),
	).fetchone()


def clear_code(connection: Connection, session: object) -> None:
	"""Le code du pupitre, saisi : la session n'attend plus que l'application d'authentification."""
	connection.execute("UPDATE api_sessions SET code = NULL WHERE id = %s", (session,))


def totp_secret(connection: Connection, user: int) -> str | None:
	"""La clé de l'application d'authentification du compte ; None sans elle."""
	row = connection.execute("SELECT totp_secret FROM api_users WHERE id = %s", (user,)).fetchone()
	if (row is None) or (row[0] is None):
		return None
	return str(row[0])


def known_browser(connection: Connection, user: int, token_hash: str) -> bool:
	"""Ce navigateur est connu du compte : sa dernière connexion notée."""
	return (
		connection.execute(
			"UPDATE api_browsers SET used_at = clock_timestamp() WHERE user_id = %s AND token_hash = %s",
			(user, token_hash),
		).rowcount
		> 0
	)


def remember_browser(connection: Connection, token_hash: str, session_hash: str) -> None:
	"""Le navigateur de cette session, retenu pour son compte, avec son navigateur."""
	connection.execute(
		"INSERT INTO api_browsers (user_id, token_hash, user_agent)"
		" SELECT user_id, %s, user_agent FROM api_sessions WHERE token_hash = %s",
		(token_hash, session_hash),
	)


def invalidate(connection: Connection, session: object) -> None:
	connection.execute(
		"UPDATE api_sessions SET state = 'invalid', code = NULL, ended_at = clock_timestamp() WHERE id = %s",
		(session,),
	)


def validate(connection: Connection, session: object, hours: int) -> None:
	"""La session validée pour hours heures : un seul instant pour la validation et la fin, elle dure exactement hours."""
	connection.execute(
		"UPDATE api_sessions SET state = 'valid', code = NULL, validated_at = moment.now,"
		" expires_at = moment.now + make_interval(hours => %s) FROM (SELECT clock_timestamp() AS now) moment"
		" WHERE id = %s",
		(hours, session),
	)


def exhaust(connection: Connection, session: object) -> None:
	"""Le dernier code faux permis : la session devient invalide."""
	connection.execute(
		"UPDATE api_sessions SET state = 'invalid', code = NULL, attempts = attempts + 1,"
		" ended_at = clock_timestamp() WHERE id = %s",
		(session,),
	)


def wrong_attempt(connection: Connection, session: object) -> None:
	connection.execute("UPDATE api_sessions SET attempts = attempts + 1 WHERE id = %s", (session,))


def end(connection: Connection, token_hash: str) -> None:
	"""La déconnexion : la session de ce jeton devient invalide."""
	connection.execute(
		"UPDATE api_sessions SET state = 'invalid', code = NULL, ended_at = clock_timestamp()"
		" WHERE token_hash = %s AND state <> 'invalid'",
		(token_hash,),
	)
