"""Fixtures communes aux scénarios (https://github.com/dascritch/machincast/issues/5)."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest

from machincast import crash
from machincast.clock import FixedClock
from machincast.indexer import audit
from machincast.interface.application import translate_screens
from tests.database_fixtures import check_authorisations, purge_database, reset_database, sample_connection

# Étapes partagées par plusieurs fonctionnalités : pytest-bdd les trouve comme celles de conftest.py.
pytest_plugins = [
	"tests.indexing_steps",
	"tests.playback_steps",
	"tests.broadcast_steps",
	"tests.interface_steps",
	"tests.preview_steps",
	"tests.end_of_list_steps",
]

# Les écrans de l'interface s'affichent hors de l'écran du poste : aucune fenêtre ne s'ouvre pendant les tests
# (https://github.com/dascritch/machincast/issues/23).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True, scope="session")
def translated_screens(qapp: Any) -> None:
	"""Les écrans se traduisent en français, comme dans l'interface
	(https://github.com/dascritch/machincast/issues/360) : l'application de pytest-qt reçoit la traduction des écrans,
	sans celle de Qt, qu'un scénario charge à part."""
	translate_screens(qapp)


_recreated_schema = False

AUDIT_LAUNCHING = datetime(2026, 10, 15, 6, 15, tzinfo=UTC)
"""Lancement de toute indexation des scénarios : 08:15 à Paris, pour le nom du document d'audit."""


@pytest.fixture(autouse=True)
def audit_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
	"""Les documents d'audit de l'indexation vont dans le répertoire du scénario, jamais dans /tmp, à heure fixe
	(https://github.com/dascritch/machincast/issues/11)."""
	directory = tmp_path / "audit"
	directory.mkdir()
	monkeypatch.setattr(audit, "DIRECTORY", directory)
	monkeypatch.setattr(audit, "CLOCK", FixedClock(AUDIT_LAUNCHING))
	return directory


@pytest.fixture(autouse=True)
def crash_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
	"""Les rapports de crash des binaires lancés par les scénarios, dans le répertoire du scénario : jamais dans
	crash-dump/ du dépôt (https://github.com/dascritch/machincast/issues/342)."""
	directory = tmp_path / "crash-dump"
	monkeypatch.setattr(crash, "DIRECTORY", directory)
	# Les binaires que les scénarios lancent dans un autre processus aussi.
	monkeypatch.setenv(crash.ENVIRONMENT, str(directory))
	monkeypatch.setattr(crash, "FALLBACK", tmp_path / "crash-dump-de-secours")
	return directory


@pytest.fixture(autouse=True)
def view_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
	"""Les réglages des colonnes de l'interface, dans le répertoire du test : jamais ceux du compte qui lance les tests
	(https://github.com/dascritch/machincast/issues/207)."""
	from machincast.interface import columns

	path = tmp_path / "vues.ini"
	monkeypatch.setattr(columns, "FILE", path)
	return path


@pytest.fixture(autouse=True)
def sample_news(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
	"""Les nouveautés des versions publiées, dans le répertoire du test, absentes tant que le scénario ne les écrit
	pas : jamais celles du dépôt, qui ouvriraient leur fenêtre au lancement
	(https://github.com/dascritch/machincast/issues/208)."""
	from machincast.interface import version

	path = tmp_path / "news.md"
	monkeypatch.setattr(version, "NEWS", path)
	return path


@pytest.fixture(autouse=True)
def sample_shortcuts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Le menu des applications et le bureau, dans le répertoire du test : jamais les raccourcis du compte qui lance
	les tests (https://github.com/dascritch/machincast/issues/111)."""
	from machincast import shortcut

	monkeypatch.setattr(shortcut, "MENU_FOLDER", tmp_path / "applications")
	monkeypatch.setattr(shortcut, "DESKTOP_FOLDER", tmp_path / "Bureau")


@pytest.fixture
def empty_database() -> Iterator[psycopg.Connection[tuple[object, ...]]]:
	"""Base de test migrée et vide : le schéma est recréé une fois par session, puis les tables sont purgées."""
	global _recreated_schema
	with sample_connection() as connection:
		check_authorisations(connection)
		if not _recreated_schema:
			reset_database(connection)
			_recreated_schema = True
		purge_database(connection)
		yield connection
