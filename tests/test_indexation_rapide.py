"""Étapes des scénarios de l'indexation rapide (https://github.com/dascritch/machincast/issues/69).

Les étapes des fichiers, des sonores en base et du passage de l'indexeur sont dans tests/etapes_indexation.py.
"""

import shutil
import subprocess
from pathlib import Path

import psycopg
from pytest_bdd import given, parsers, scenarios, then, when

from tests.etapes_indexation import inserer_sonore, lire_sonore

scenarios("indexation_rapide.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


@given("un troisième sonore, actif, dont le fichier a disparu")
def sonore_disparu(base_vide: Connexion, tmp_path: Path) -> None:
	inserer_sonore(base_vide, str(tmp_path / "disparu.ogg"), "actif")


@then("le sonore n'a pas de durée en base")
def sans_duree(base_vide: Connexion, sonore: int) -> None:
	assert lire_sonore(base_vide, sonore)[1] is None


@when(parsers.parse('je lance "{executable}" avec l\'option "{option}"'), target_fixture="commande")
def lancer(executable: str, option: str) -> subprocess.CompletedProcess[str]:
	chemin = shutil.which(executable)
	assert chemin is not None, f'{executable} n\'est pas installé : lancer pip install -e ".[dev]"'
	return subprocess.run([chemin, option], capture_output=True, text=True, timeout=30)


@then(parsers.parse('la sortie mentionne "{texte}"'))
def mentionne(commande: subprocess.CompletedProcess[str], texte: str) -> None:
	assert texte in commande.stdout
