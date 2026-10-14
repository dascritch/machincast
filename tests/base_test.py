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

from machincast.base import TABLES, appliquer_migrations, url_yoyo
from machincast.configuration import Configuration, charger

CONFIGURATION_TEST = Path(__file__).parent / "configuration-test.toml"


@cache
def configuration_test() -> Configuration:
	"""Configuration des tests ; son chargement refuse une base de test identique à la base de production."""
	return charger(Path(os.environ.get("MACHINCAST_CONFIG_TEST", CONFIGURATION_TEST)))


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


def purger_base(connexion: psycopg.Connection[tuple[object, ...]]) -> None:
	"""Applique les migrations manquantes, puis vide toutes les tables et remet les identifiants à 1."""
	appliquer_migrations(url_yoyo(*parametres_base_test()))
	connexion.execute(
		sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(sql.SQL(", ").join(sql.Identifier(t) for t in TABLES))
	)
