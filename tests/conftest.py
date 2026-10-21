"""Fixtures communes aux scénarios (https://github.com/dascritch/machincast/issues/5)."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from machincast.horloge import HorlogeFixe
from machincast.indexation import audit
from tests.base_test import connexion_test, purger_base, reinitialiser_base, verifier_autorisations

# Étapes partagées par plusieurs fonctionnalités : pytest-bdd les trouve comme celles de conftest.py.
pytest_plugins = [
	"tests.etapes_indexation",
	"tests.etapes_lecture",
	"tests.etapes_diffusion",
	"tests.etapes_interface",
	"tests.etapes_preecoute",
]

# Les écrans de l'interface s'affichent hors de l'écran du poste : aucune fenêtre ne s'ouvre pendant les tests
# (https://github.com/dascritch/machincast/issues/23).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_schema_recree = False

LANCEMENT_DE_L_AUDIT = datetime(2026, 10, 15, 6, 15, tzinfo=UTC)
"""Lancement de toute indexation des scénarios : 08:15 à Paris, pour le nom du document d'audit."""


@pytest.fixture(autouse=True)
def repertoire_d_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
	"""Les documents d'audit de l'indexation vont dans le répertoire du scénario, jamais dans /tmp, à heure fixe
	(https://github.com/dascritch/machincast/issues/11)."""
	repertoire = tmp_path / "audit"
	repertoire.mkdir()
	monkeypatch.setattr(audit, "REPERTOIRE", repertoire)
	monkeypatch.setattr(audit, "HORLOGE", HorlogeFixe(LANCEMENT_DE_L_AUDIT))
	return repertoire


@pytest.fixture(autouse=True)
def reglages_des_vues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
	"""Les réglages des colonnes de l'interface, dans le répertoire du test : jamais ceux du compte qui lance les tests
	(https://github.com/dascritch/machincast/issues/207)."""
	from machincast.interface import colonnes

	chemin = tmp_path / "vues.ini"
	monkeypatch.setattr(colonnes, "FICHIER", chemin)
	return chemin


@pytest.fixture(autouse=True)
def raccourcis_du_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Le menu des applications et le bureau, dans le répertoire du test : jamais les raccourcis du compte qui lance
	les tests (https://github.com/dascritch/machincast/issues/111)."""
	from machincast import raccourci

	monkeypatch.setattr(raccourci, "DOSSIER_MENU", tmp_path / "applications")
	monkeypatch.setattr(raccourci, "DOSSIER_BUREAU", tmp_path / "Bureau")


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
