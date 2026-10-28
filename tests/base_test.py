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

from machincast.base import (
	CONTRAINTES_RENOMMEES,
	MIGRATIONS_FUSIONNEES,
	REPERTOIRE_MIGRATIONS,
	Role,
	appliquer_migrations,
	url_yoyo,
)
from machincast.configuration import Configuration, charger

CONFIGURATION_TEST = Path(__file__).parent / "configuration-test.toml"


def chemin_configuration_test() -> Path:
	"""Fichier de configuration des tests : celui que désigne MACHINCAST_CONFIG_TEST, sinon celui du dépôt."""
	return Path(os.environ.get("MACHINCAST_CONFIG_TEST", CONFIGURATION_TEST))


@cache
def configuration_test() -> Configuration:
	"""Configuration des tests ; son chargement refuse une base de test identique à la base de production."""
	return charger(chemin_configuration_test())


def parametres_base_test() -> tuple[Path, str]:
	base = configuration_test().base
	return base.socket, base.test


def connexion_test() -> psycopg.Connection[tuple[object, ...]]:
	"""Connexion en autocommit à la base de test ; le scénario est ignoré si PostgreSQL est injoignable."""
	socket, nom = parametres_base_test()
	if nom == configuration_test().base.production:
		pytest.exit(f"la base de test « {nom} » est la base de production : tests arrêtés", returncode=3)
	try:
		connexion = psycopg.connect(host=str(socket), dbname=nom, autocommit=True)
	except psycopg.OperationalError as erreur:
		pytest.skip(f"base de test {nom} injoignable par {socket} : {erreur}")
	return connexion


def reinitialiser_base(connexion: psycopg.Connection[tuple[object, ...]]) -> None:
	"""Recrée entièrement le schéma de la base de test puis y applique toutes les migrations."""
	connexion.execute("DROP SCHEMA public CASCADE")
	# Recrée le schéma public comme dans une base neuve (PostgreSQL ≥ 15) : propriétaire de la base, lisible par tous.
	connexion.execute("CREATE SCHEMA public AUTHORIZATION pg_database_owner")
	connexion.execute("GRANT USAGE ON SCHEMA public TO PUBLIC")
	appliquer_migrations(url_yoyo(*parametres_base_test()))


ORDRE_DE_PURGE: tuple[str, ...] = (
	"log",
	"airplay",
	"sequences_elements",
	"evenements_elements",
	"evenements_sauts",
	"banques_sonores",
	"banques_repertoires",
	"sonores",
	"feeds",
	"sequences",
	"evenements",
	"banques",
)
"""Les tables de machincast.base.TABLES, chacune vidée avant celles qu'elle désigne : un DELETE ne cascade pas."""


@cache
def nombre_de_migrations() -> int:
	return len(read_migrations(str(REPERTOIRE_MIGRATIONS)))


def purger_base(connexion: psycopg.Connection[tuple[object, ...]]) -> None:
	"""Applique les migrations manquantes, puis vide toutes les tables et remet les identifiants à 1.

	Entre deux scénarios (https://github.com/dascritch/machincast/issues/280), yoyo ne repasse que si une migration
	manque, après un scénario qui en a annulé : compter celles qu'il a appliquées suffit sinon. Les tables, presque
	vides, se vident par DELETE : dix fois plus vite qu'un TRUNCATE, qui recrée leurs fichiers."""
	appliquees = connexion.execute("SELECT count(*) FROM _yoyo_migration").fetchone()
	if appliquees != (nombre_de_migrations(),):
		appliquer_migrations(url_yoyo(*parametres_base_test()))
	sequences = connexion.execute(
		"SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' ORDER BY 1"
	).fetchall()
	with connexion.transaction():
		for table in ORDRE_DE_PURGE:
			connexion.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))
		for (sequence,) in sequences:
			connexion.execute(sql.SQL("ALTER SEQUENCE {} RESTART").format(sql.Identifier(str(sequence))))


def commande_d_autorisation(nom: str) -> str:
	"""La commande qui autorise le compte à endosser les trois rôles, comme le fait install.sh."""
	roles = ", ".join(str(role) for role in Role)
	return f"sudo -u postgres psql -c 'GRANT {roles} TO \"{nom}\" WITH INHERIT FALSE, SET TRUE'"


def verifier_autorisations(connexion: psycopg.Connection[tuple[object, ...]]) -> None:
	"""Ignore le scénario si le compte qui lance les tests ne peut pas endosser les trois rôles de MachinCast.

	Les tests ne créent jamais de compte PostgreSQL et n'attribuent jamais de rôle : le compte doit déjà y être
	autorisé, par install.sh ou par l'utilisateur postgres (https://github.com/dascritch/machincast/pull/72).
	"""
	roles = [str(role) for role in Role]
	lignes = connexion.execute(
		"SELECT rolname FROM pg_roles WHERE rolname = ANY(%s) AND pg_has_role(current_user, oid, 'SET')", (roles,)
	).fetchall()
	manquants = sorted(set(roles) - {str(ligne[0]) for ligne in lignes})
	if manquants:
		compte = connexion.execute("SELECT current_user").fetchone()
		nom = compte[0] if compte is not None else "?"
		pytest.skip(
			f"le compte {nom} ne peut pas endosser {', '.join(manquants)} : lancer ./install.sh, ou en tant que"
			f' postgres : GRANT {", ".join(roles)} TO "{nom}" WITH INHERIT FALSE, SET TRUE'
		)


# ─── Bases d'avant le schéma unique (https://github.com/dascritch/machincast/issues/314) ───


def renommer_les_contraintes(connexion: psycopg.Connection[tuple[object, ...]], vers_les_anciens: bool) -> None:
	"""Les contraintes NOT NULL que PostgreSQL 18 nomme, et qu'un renommage gardait ; aucune avant lui."""
	for table, ancien, nouveau in CONTRAINTES_RENOMMEES:
		depuis, vers = (nouveau, ancien) if vers_les_anciens else (ancien, nouveau)
		existe = connexion.execute(
			"SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = %s AND conrelid = %s::regclass)",
			(depuis, table),
		).fetchone()
		if existe == (True,):
			connexion.execute(
				sql.SQL("ALTER TABLE {} RENAME CONSTRAINT {} TO {}").format(
					sql.Identifier(table), sql.Identifier(depuis), sql.Identifier(vers)
				)
			)


def marquer_les_anciennes_migrations(connexion: psycopg.Connection[tuple[object, ...]], derniere: str | None) -> None:
	"""Comme une base d'avant le schéma unique : yoyo y note les migrations d'alors, par l'empreinte de leur nom,
	jusqu'à la dernière donnée ; toutes, et avec les anciens noms de contraintes, sans elle. À défaire par
	rendre_les_migrations, à la fin du scénario."""
	fusionnees = list(MIGRATIONS_FUSIONNEES)
	if derniere is not None:
		fusionnees = fusionnees[: fusionnees.index(derniere) + 1]
	for migration in fusionnees:
		connexion.execute(
			"INSERT INTO _yoyo_migration (migration_hash, migration_id, applied_at_utc)"
			" VALUES (encode(sha256(convert_to(%s, 'UTF8')), 'hex'), %s, now() AT TIME ZONE 'UTC')",
			(migration, migration),
		)
	if derniere is None:
		renommer_les_contraintes(connexion, vers_les_anciens=True)
	connexion.commit()


def rendre_les_migrations() -> None:
	"""La base de test sert aux autres scénarios : les traces des anciennes migrations en sont retirées, et ses
	contraintes reprennent leur nom."""
	socket, nom = parametres_base_test()
	with psycopg.connect(host=str(socket), dbname=nom) as remise:
		remise.execute("DELETE FROM _yoyo_migration WHERE migration_id = ANY(%s)", (list(MIGRATIONS_FUSIONNEES),))
		renommer_les_contraintes(remise, vers_les_anciens=False)
