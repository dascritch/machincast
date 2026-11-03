"""Accès à la base de test pour les scénarios (https://github.com/dascritch/machincast/issues/5).

Les réglages viennent de tests/configuration-test.toml, ou du fichier désigné par la variable
d'environnement MACHINCAST_CONFIG_TEST. Toute connexion à la base de production est refusée.
"""

import os
from functools import cache
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from yoyo import read_migrations

from machincast.configuration import Configuration, load
from machincast.database import (
	MIGRATION_DIRECTORY,
	OLD_MIGRATIONS,
	Role,
	apply_migrations,
	url_yoyo,
)

CONFIGURATION_TEST = Path(__file__).parent / "configuration-test.toml"


def sample_configuration_path() -> Path:
	"""Fichier de configuration des tests : celui que désigne MACHINCAST_CONFIG_TEST, sinon celui du dépôt."""
	return Path(os.environ.get("MACHINCAST_CONFIG_TEST", CONFIGURATION_TEST))


@cache
def configuration_test() -> Configuration:
	"""Configuration des tests ; son chargement refuse une base de test identique à la base de production."""
	return load(sample_configuration_path())


def sample_database_parameters() -> tuple[Path, str]:
	database = configuration_test().database
	return database.socket, database.test


def sample_connection() -> psycopg.Connection[tuple[object, ...]]:
	"""Connexion en autocommit à la base de test ; le scénario est ignoré si PostgreSQL est injoignable."""
	socket, name = sample_database_parameters()
	if name == configuration_test().database.production:
		pytest.exit(f"la base de test « {name} » est la base de production : tests arrêtés", returncode=3)
	try:
		connection = psycopg.connect(host=str(socket), dbname=name, autocommit=True)
	except psycopg.OperationalError as error:
		pytest.skip(f"base de test {name} injoignable par {socket} : {error}")
	return connection


def reset_database(connection: psycopg.Connection[tuple[object, ...]]) -> None:
	"""Recrée entièrement le schéma de la base de test puis y applique toutes les migrations."""
	connection.execute("DROP SCHEMA public CASCADE")
	# Recrée le schéma public comme dans une base neuve (PostgreSQL ≥ 15) : propriétaire de la base, lisible par tous.
	connection.execute("CREATE SCHEMA public AUTHORIZATION pg_database_owner")
	connection.execute("GRANT USAGE ON SCHEMA public TO PUBLIC")
	apply_migrations(url_yoyo(*sample_database_parameters()))


PURGE_ORDER: tuple[str, ...] = (
	"log",
	"airplay",
	"sequence_items",
	"event_items",
	"event_skips",
	"bank_sounds",
	"bank_directories",
	"sounds",
	"feeds",
	"sequences",
	"events",
	"banks",
)
"""Les tables de machincast.database.TABLES, chacune vidée avant celles qu'elle désigne : un DELETE ne cascade pas."""


@cache
def migration_count() -> int:
	return len(read_migrations(str(MIGRATION_DIRECTORY)))


def purge_database(connection: psycopg.Connection[tuple[object, ...]]) -> None:
	"""Applique les migrations manquantes, puis vide toutes les tables et remet les identifiants à 1.

	Entre deux scénarios (https://github.com/dascritch/machincast/issues/280), yoyo ne repasse que si une migration
	manque, après un scénario qui en a annulé : compter celles qu'il a appliquées suffit sinon. Les tables, presque
	vides, se vident par DELETE : dix fois plus vite qu'un TRUNCATE, qui recrée leurs fichiers."""
	applied = connection.execute("SELECT count(*) FROM _yoyo_migration").fetchone()
	if applied != (migration_count(),):
		apply_migrations(url_yoyo(*sample_database_parameters()))
	sequences = connection.execute(
		"SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' ORDER BY 1"
	).fetchall()
	with connection.transaction():
		for table in PURGE_ORDER:
			connection.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))
		for (sequence,) in sequences:
			connection.execute(sql.SQL("ALTER SEQUENCE {} RESTART").format(sql.Identifier(str(sequence))))


def authorisation_command(name: str) -> str:
	"""La commande qui autorise le compte à endosser les trois rôles, comme le fait install.sh."""
	roles = ", ".join(str(role) for role in Role)
	return f"sudo -u postgres psql -c 'GRANT {roles} TO \"{name}\" WITH INHERIT FALSE, SET TRUE'"


def check_authorisations(connection: psycopg.Connection[tuple[object, ...]]) -> None:
	"""Ignore le scénario si le compte qui lance les tests ne peut pas endosser les trois rôles de MachinCast.

	Les tests ne créent jamais de compte PostgreSQL et n'attribuent jamais de rôle : le compte doit déjà y être
	autorisé, par install.sh ou par l'utilisateur postgres (https://github.com/dascritch/machincast/pull/72).
	"""
	roles = [str(role) for role in Role]
	lines = connection.execute(
		"SELECT rolname FROM pg_roles WHERE rolname = ANY(%s) AND pg_has_role(current_user, oid, 'SET')", (roles,)
	).fetchall()
	missing_list = sorted(set(roles) - {str(line[0]) for line in lines})
	if missing_list:
		count = connection.execute("SELECT current_user").fetchone()
		name = count[0] if count is not None else "?"
		pytest.skip(
			f"le compte {name} ne peut pas endosser {', '.join(missing_list)} : lancer ./install.sh, ou en tant que"
			f' postgres : GRANT {", ".join(roles)} TO "{name}" WITH INHERIT FALSE, SET TRUE'
		)


# ─── Bases à l'ancien schéma, aux noms français (https://github.com/dascritch/machincast/issues/358) ───


def mark_old_migrations(connection: psycopg.Connection[tuple[object, ...]], migration: str) -> None:
	"""Comme une base créée avec l'ancien schéma : yoyo y note cette migration d'alors, par l'empreinte de son nom. À
	défaire par return_migrations, à la fin du scénario."""
	connection.execute(
		"INSERT INTO _yoyo_migration (migration_hash, migration_id, applied_at_utc)"
		" VALUES (encode(sha256(convert_to(%s, 'UTF8')), 'hex'), %s, now() AT TIME ZONE 'UTC')",
		(migration, migration),
	)
	connection.commit()


def return_migrations() -> None:
	"""La base de test sert aux autres scénarios : les traces des anciennes migrations en sont retirées."""
	socket, name = sample_database_parameters()
	with psycopg.connect(host=str(socket), dbname=name) as put_back:
		put_back.execute("DELETE FROM _yoyo_migration WHERE migration_id = ANY(%s)", (list(OLD_MIGRATIONS),))
