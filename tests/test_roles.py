"""Étapes des scénarios des rôles PostgreSQL (https://github.com/dascritch/machincast/issues/4)."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

import psycopg
import pytest
from psycopg import sql
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.database import Role, cancel_migrations, open_connection, url_yoyo
from tests.database_fixtures import authorisation_command, sample_database_parameters

scenarios("roles.feature")

Connection = psycopg.Connection[tuple[object, ...]]

# Une requête par table et par opération. Les clauses WHERE false suffisent : PostgreSQL vérifie
# les droits avant d'exécuter, même quand aucune ligne n'est concernée.
INSERTIONS: dict[str, str] = {
	"sounds": "INSERT INTO sounds (type, location) VALUES ('file', '/essai/insertion.flac')",
	"feeds": "INSERT INTO feeds (name, url) VALUES ('Essai', 'https://flux.exemple/essai')",
	"banks": "INSERT INTO banks (internal_name, mode) VALUES ('Essai', 'random')",
	"bank_directories": "INSERT INTO bank_directories (bank_id, directory) VALUES ({banque}, '/essai')",
	"bank_sounds": "INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES ({banque}, {sonore}, 1)",
	"events": "INSERT INTO events (internal_name, priority) VALUES ('Essai', 'background_programming')",
	"event_items": ("INSERT INTO event_items (event_id, position, sound_id) VALUES ({evenement}, 1, {sonore})"),
	"event_skips": "INSERT INTO event_skips (event_id, day) VALUES ({evenement}, '2026-10-21')",
	"sequences": "INSERT INTO sequences (internal_name) VALUES ('Essai')",
	"sequence_items": ("INSERT INTO sequence_items (sequence_id, position, sound_id) VALUES ({sequence}, 1, {sonore})"),
	"airplay": "INSERT INTO airplay (play_id, line_type) VALUES (gen_random_uuid(), 'start')",
	"log": "INSERT INTO log (level, kind) VALUES ('info', 'essai')",
}
CHANGES: dict[str, str] = {
	"sounds": "title = NULL",
	"feeds": "url = 'https://flux.exemple/autre'",
	"banks": "hide_metadata = NULL",
	"bank_directories": "directory = '/autre'",
	"bank_sounds": "position = 2",
	"events": "public_name = NULL",
	"event_items": "position = 2",
	"event_skips": "day = '2026-10-22'",
	"sequences": "public_name = NULL",
	"sequence_items": "position = 2",
	"airplay": "title = NULL",
	"log": "message = ''",
}


@dataclass
class Context:
	connection: Connection
	references: dict[str, int] = field(default_factory=dict)


@pytest.fixture
def context(empty_database: psycopg.Connection[tuple[object, ...]]) -> Context:
	return Context(connection=empty_database)


@contextmanager
def in_as_long_as_that(connection: Connection, role: str, validate: bool = False) -> Iterator[None]:
	"""Exécute un bloc dans une transaction avec le rôle donné ; annulée sauf si valider."""
	with connection.transaction(force_rollback=not validate):
		connection.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
		yield


def allowed(context: Context, role: str, query: str) -> bool:
	"""Vrai si le rôle peut exécuter la requête ; faux si PostgreSQL la refuse faute de droits."""
	try:
		with in_as_long_as_that(context.connection, role):
			context.connection.execute(query.format(**context.references))
	except psycopg.errors.InsufficientPrivilege:
		return False
	return True


def insert(context: Context, query: str) -> int:
	line = context.connection.execute(query + " RETURNING id").fetchone()
	assert line is not None
	return int(str(line[0]))


# ─── Étant donné ───────────────────────────────────────────


@given("une base de test migrée avec les éléments de référence")
def database(context: Context) -> None:
	"""La fixture empty_database fournit déjà une base migrée et purgée."""
	r = context.references
	r["banque"] = insert(context, "INSERT INTO banks (internal_name, mode) VALUES ('Jingles', 'random')")
	r["sonore"] = insert(
		context, "INSERT INTO sounds (type, location, title) VALUES ('file', '/reference.flac', 'Référence')"
	)
	r["evenement"] = insert(
		context, "INSERT INTO events (internal_name, priority) VALUES ('Fil', 'background_programming')"
	)
	r["sequence"] = insert(context, "INSERT INTO sequences (internal_name) VALUES ('Passage publicitaire')")


@given("un passage du sonore de référence dans l'airplay")
def play(context: Context) -> None:
	context.connection.execute(
		"INSERT INTO airplay (play_id, line_type, sound_id, title) "
		"VALUES (gen_random_uuid(), 'start', %s, 'Référence')",
		(context.references["sonore"],),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse('le rôle "{role}" enregistre le début et la fin d\'un passage, puis une entrée de log'))
def full_play(context: Context, role: str) -> None:
	with in_as_long_as_that(context.connection, role, validate=True):
		c = context.connection
		c.execute(
			"INSERT INTO airplay (play_id, line_type, sound_id, title) "
			"VALUES ('7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', 'start', %s, 'Référence')",
			(context.references["sonore"],),
		)
		c.execute(
			"INSERT INTO airplay (play_id, line_type, sound_id, played_duration, without_incident) "
			"VALUES ('7f0c1c2e-5d39-4a87-9a52-0c3c8c1f9a01', 'end', %s, '3 min', true)",
			(context.references["sonore"],),
		)
		c.execute("INSERT INTO log (level, kind, message) VALUES ('info', 'passage', 'Référence')")


@when(parsers.parse('le rôle "{role}" supprime le sonore de référence'))
def delete(context: Context, role: str) -> None:
	with in_as_long_as_that(context.connection, role, validate=True):
		context.connection.execute("DELETE FROM sounds WHERE id = %s", (context.references["sonore"],))


@when(parsers.parse('je me connecte à la base de test avec le rôle "{role}"'), target_fixture="current_role")
def log_in(role: str) -> str:
	socket, sample_database = sample_database_parameters()
	with open_connection(socket, sample_database, Role(role)) as connection:
		line = connection.execute("SELECT current_user").fetchone()
		assert line is not None
		return str(line[0])


@when("j'annule toutes les migrations")
def cancel_right_migrations() -> None:
	# Les rôles appartiennent au serveur : l'annulation retire les droits, pas les rôles. empty_database réapplique
	# ensuite.
	cancel_migrations(url_yoyo(*sample_database_parameters()))


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse('le rôle "{role}" a exactement ces droits :'))
def rights(context: Context, role: str, datatable: list[list[str]]) -> None:
	gaps = []
	for table, read, insert_, modify, delete_ in datatable[1:]:
		queries = {
			"lire": f"SELECT * FROM {table} LIMIT 1",
			"inserer": INSERTIONS[table],
			"modifier": f"UPDATE {table} SET {CHANGES[table]} WHERE false",
			"supprimer": f"DELETE FROM {table} WHERE false",
		}
		expected_list = {"lire": read, "inserer": insert_, "modifier": modify, "supprimer": delete_}
		for operation, query in queries.items():
			obtained = "oui" if allowed(context, role, query) else "non"
			if obtained != expected_list[operation]:
				gaps.append(f"{table}.{operation} : attendu {expected_list[operation]}, obtenu {obtained}")
	assert not gaps, f"droits de {role} :\n" + "\n".join(gaps)


@then(parsers.parse('le rôle "{role}" {verdict} modifier la colonne "{column}" des sonores'))
def column(context: Context, role: str, verdict: str, column: str) -> None:
	query = f"UPDATE sounds SET {column} = {column} WHERE false"
	assert allowed(context, role, query) is (verdict == "peut")


@then(parsers.parse('le rôle "{role}" {verdict} retrouver le démarrage précédent d\'un binaire'))
def previous_start(context: Context, role: str, verdict: str) -> None:
	query = "SELECT * FROM machincast_previous_start('Machin_purge')"
	assert allowed(context, role, query) is (verdict == "peut")


@then("les deux lignes d'airplay et l'entrée de log sont en base")
def saved_play(context: Context) -> None:
	lines = context.connection.execute("SELECT line_type::text FROM airplay ORDER BY id").fetchall()
	assert [line[0] for line in lines] == ["start", "end"]
	log = context.connection.execute("SELECT kind FROM log").fetchall()
	assert log == [("passage",)]


@then("la ligne d'airplay existe toujours, sans référence au sonore")
def kept_airplay(context: Context) -> None:
	lines = context.connection.execute("SELECT sound_id, title FROM airplay").fetchall()
	assert lines == [(None, "Référence")]


@then(parsers.parse('la connexion agit en tant que "{role}"'))
def acts_in_as_long_as_that(current_role: str, role: str) -> None:
	assert current_role == role


@then("les trois rôles existent toujours")
def roles_exist(context: Context) -> None:
	lines = context.connection.execute(
		"SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", ([str(r) for r in Role],)
	).fetchall()
	assert len(lines) == 3


@then("le compte courant peut endosser chacun des trois rôles, sans en hériter les droits")
def current_count(context: Context) -> None:
	lines = context.connection.execute(
		"SELECT r.rolname, m.inherit_option, m.set_option FROM pg_auth_members m"
		" JOIN pg_roles r ON r.oid = m.roleid WHERE m.member = (SELECT oid FROM pg_roles WHERE rolname = current_user)"
		" AND r.rolname = ANY(%s)",
		([str(role) for role in Role],),
	).fetchall()
	count = context.connection.execute(
		"SELECT current_user, rolsuper FROM pg_roles WHERE rolname = current_user"
	).fetchone()
	assert count is not None
	name, superuser = count
	explanation = (
		f"le compte {name} n'a aucune autorisation sur les rôles de MachinCast : {authorisation_command(str(name))}"
	)
	if superuser:
		# Un superutilisateur endosse tous les rôles sans autorisation : les autres scénarios passent, celui-ci non.
		explanation = (
			f"le compte {name} est superutilisateur de PostgreSQL, et endosse les rôles sans autorisation ;"
			f" l'installation voulue ne lui donne aucun droit particulier sur le serveur (doc/fr/regles/tests.md,"
			f" Base de test). Lancer :"
			f" {authorisation_command(str(name))}, puis sudo -u postgres psql -c 'ALTER ROLE \"{name}\" NOSUPERUSER'"
		)
	assert lines != [], explanation
	# Aucune autorisation n'hérite des droits, et chaque rôle peut être endossé par au moins l'une d'elles.
	assert not any(inheritance for _, inheritance, _ in lines), lines
	assert {str(name) for name, _, assumable in lines if assumable} == {str(role) for role in Role}, lines
