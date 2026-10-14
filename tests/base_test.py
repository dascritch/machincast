"""Accès à la base de test pour les scénarios.

Provisoire : le ticket #5 remplacera ces réglages par la configuration de test,
avec le refus de toute connexion à la base de production.
"""

import os
from pathlib import Path

import psycopg
import pytest

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
