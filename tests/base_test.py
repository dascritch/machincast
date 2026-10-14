"""Accès à la base de test pour les scénarios.

Provisoire : ces réglages seront remplacés par la configuration de test,
avec le refus de toute connexion à la base de production.
Voir https://github.com/dascritch/machincast/issues/5
"""

import os
from pathlib import Path

import psycopg
import pytest

from machincast.base import appliquer_migrations, url_yoyo

SOCKET = os.environ.get("MACHINCAST_SOCKET", "/var/run/postgresql")
BASE = os.environ.get("MACHINCAST_BASE_TEST", "machincast_test")


def parametres_base_test() -> tuple[Path, str]:
	return Path(SOCKET), BASE


def connexion_test() -> psycopg.Connection[tuple[object, ...]]:
	"""Connexion en autocommit à la base de test ; le scénario est ignoré si PostgreSQL est injoignable."""
	try:
		return psycopg.connect(host=SOCKET, dbname=BASE, autocommit=True)
	except psycopg.OperationalError as erreur:
		pytest.skip(f"base de test {BASE} injoignable par {SOCKET} : {erreur}")


def reinitialiser_base(connexion: psycopg.Connection[tuple[object, ...]]) -> None:
	"""Vide la base de test puis y applique toutes les migrations."""
	connexion.execute("DROP SCHEMA public CASCADE")
	# Recrée le schéma public comme dans une base neuve (PostgreSQL ≥ 15) : propriétaire de la base, lisible par tous.
	connexion.execute("CREATE SCHEMA public AUTHORIZATION pg_database_owner")
	connexion.execute("GRANT USAGE ON SCHEMA public TO PUBLIC")
	appliquer_migrations(url_yoyo(*parametres_base_test()))
