"""Étapes des scénarios de l'indexation rapide (https://github.com/dascritch/machincast/issues/69).

Les étapes des fichiers, des sonores en base et du passage de l'indexeur sont dans tests/indexing_steps.py.
"""

import shutil
import subprocess
from pathlib import Path

import psycopg
from pytest_bdd import given, parsers, scenarios, then, when

from tests.indexing_steps import insert_sound, read_sound

scenarios("quick_indexing.feature")

Connection = psycopg.Connection[tuple[object, ...]]


@given("un troisième sonore, actif, dont le fichier a disparu")
def disappeared_sound(empty_database: Connection, tmp_path: Path) -> None:
	insert_sound(empty_database, str(tmp_path / "disparu.ogg"), "active")


@then("le sonore n'a pas de durée en base")
def without_duration(empty_database: Connection, sound: int) -> None:
	assert read_sound(empty_database, sound)[1] is None


@when(parsers.parse('je lance "{executable}" avec l\'option "{option}"'), target_fixture="command")
def launch(executable: str, option: str) -> subprocess.CompletedProcess[str]:
	path = shutil.which(executable)
	assert path is not None, f'{executable} n\'est pas installé : lancer pip install -e ".[dev]"'
	return subprocess.run([path, option], capture_output=True, text=True, timeout=30)


@then(parsers.parse('la sortie mentionne "{text}"'))
def mentions(command: subprocess.CompletedProcess[str], text: str) -> None:
	assert text in command.stdout
