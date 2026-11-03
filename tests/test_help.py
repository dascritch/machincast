"""Étapes des scénarios d'aide et de version des exécutables."""

import shutil
import subprocess

from pytest_bdd import parsers, scenarios, then, when

import machincast

scenarios("help_.feature")


@when(
	parsers.parse('je lance "{executable}" avec l\'option "{option}"'),
	target_fixture="result",
)
def launch(executable: str, option: str) -> subprocess.CompletedProcess[str]:
	path = shutil.which(executable)
	assert path is not None, f'{executable} n\'est pas installé : lancer pip install -e ".[dev]"'
	return subprocess.run([path, option], capture_output=True, text=True, timeout=30)


@then("la commande se termine sans erreur")
def without_error(result: subprocess.CompletedProcess[str]) -> None:
	assert result.returncode == 0, result.stderr


@then(parsers.parse('la sortie mentionne "{text}"'))
def mentions(result: subprocess.CompletedProcess[str], text: str) -> None:
	assert text in result.stdout


@then("la sortie mentionne la version de MachinCast")
def mentions_version(result: subprocess.CompletedProcess[str]) -> None:
	assert machincast.__version__ in result.stdout
