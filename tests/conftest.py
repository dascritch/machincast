"""Fixtures communes aux scénarios (https://github.com/dascritch/machincast/issues/5)."""

from collections.abc import Iterator

import psycopg
import pytest

from tests.base_test import connexion_test, purger_base, reinitialiser_base, verifier_autorisations

# Étapes partagées par plusieurs fonctionnalités : pytest-bdd les trouve comme celles de conftest.py.
pytest_plugins = ["tests.etapes_indexation"]

_schema_recree = False


@pytest.fixture
def base_vide() -> Iterator[psycopg.Connection[tuple[object, ...]]]:
	"""Base de test migrée et vide : le schéma est recréé une fois par session, puis les tables sont purgées."""
	global _schema_recree
	with connexion_test() as connexion:
		verifier_autorisations(connexion)
		if not _schema_recree:
			reinitialiser_base(connexion)
			_schema_recree = True
		purger_base(connexion)
		yield connexion
