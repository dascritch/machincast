"""Étapes partagées des scénarios du binaire lecture (https://github.com/dascritch/machincast/issues/12).

Chargé comme greffon pytest par tests/conftest.py.
"""

import os
import time
from collections.abc import Iterator

import pytest
from pytest_bdd import given


@pytest.fixture
def paris_hour() -> Iterator[None]:
	"""Règle le processus sur l'heure de Paris, celle du poste, puis rétablit le réglage d'origine."""
	before = os.environ.get("TZ")
	os.environ["TZ"] = "Europe/Paris"
	time.tzset()
	yield
	if before is None:
		del os.environ["TZ"]
	else:
		os.environ["TZ"] = before
	time.tzset()


@given("le poste à l'heure de Paris")
def station_to_paris(paris_hour: None) -> None:
	"""Le poste de diffusion travaille en heure locale, celle de Paris."""
