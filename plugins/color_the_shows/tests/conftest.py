"""Les fixtures des scénarios des couleurs des émissions (https://github.com/dascritch/machincast/issues/628).

Ils reprennent celles de MachinCast (tests/conftest.py), sur la même base de test. Les migrations du plugin
s'appliquent à chaque scénario qui les demande, après l'annulation des précédentes : ses tables y ont leurs valeurs
par défaut. Elles s'annulent à la fin de la session : les scénarios du cœur ne voient jamais ses tables.
"""

import sys
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[3]
PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PLUGIN / "src"))

from tests.database_fixtures import sample_database_parameters  # noqa: E402

from machincast.database import url_yoyo  # noqa: E402
from machincast.plugins import schema  # noqa: E402

pytest_plugins = ["tests.conftest"]

Connection = psycopg.Connection[tuple[object, ...]]

_applied = False


def _url() -> str:
	return url_yoyo(*sample_database_parameters())


@pytest.fixture
def base(empty_database: Connection) -> Connection:
	"""La base de test vide, avec les tables du plugin et leurs valeurs par défaut."""
	global _applied
	if _applied:
		schema.cancel(_url(), PLUGIN)
	schema.apply(_url(), PLUGIN)
	_applied = True
	return empty_database


@pytest.fixture(scope="session", autouse=True)
def color_the_shows_cancelled() -> Iterator[None]:
	"""Les migrations du plugin s'annulent à la fin de la session."""
	yield
	if _applied:
		schema.cancel(_url(), PLUGIN)
