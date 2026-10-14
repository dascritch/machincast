"""Étapes des scénarios d'aide et de version des exécutables."""

import shutil
import subprocess

from pytest_bdd import parsers, scenarios, then, when

import machincast

scenarios("aide.feature")


@when(
	parsers.parse('je lance "{executable}" avec l\'option "{option}"'),
	target_fixture="resultat",
)
def lancer(executable: str, option: str) -> subprocess.CompletedProcess[str]:
	chemin = shutil.which(executable)
	assert chemin is not None, f'{executable} n\'est pas installé : lancer pip install -e ".[dev]"'
	return subprocess.run([chemin, option], capture_output=True, text=True, timeout=30)


@then("la commande se termine sans erreur")
def sans_erreur(resultat: subprocess.CompletedProcess[str]) -> None:
	assert resultat.returncode == 0, resultat.stderr


@then(parsers.parse('la sortie mentionne "{texte}"'))
def mentionne(resultat: subprocess.CompletedProcess[str], texte: str) -> None:
	assert texte in resultat.stdout


@then("la sortie mentionne la version de MachinCast")
def mentionne_version(resultat: subprocess.CompletedProcess[str]) -> None:
	assert machincast.__version__ in resultat.stdout
