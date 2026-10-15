"""Étapes du guide d'utilisation (https://github.com/dascritch/machincast/issues/74)."""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

from pytest_bdd import parsers, scenarios, then

from machincast.indexation.decodage import EtatFichier
from machincast.indexation.tags import CLES
from machincast.indexation.verification import LIBELLES
from tests.markdown import ancres_cassees, liens_casses

scenarios("guide.feature")

RACINE = Path(__file__).resolve().parents[1]
GUIDE = RACINE / "doc" / "utilisation.md"
OPTION = re.compile(r"(?<![\w-])(--?[a-z][a-z-]*)")


def guide() -> str:
	assert GUIDE.exists(), "doc/utilisation.md absent"
	return GUIDE.read_text(encoding="utf-8")


def absents(termes: set[str]) -> list[str]:
	"""Termes que le guide ne cite dans aucun code entre accents graves, comme le veut sa mise en forme."""
	codes = re.findall(r"`([^`\n]+)`", guide())

	def cite(terme: str) -> bool:
		motif = re.compile(rf"(?<![\w-]){re.escape(terme)}(?![\w-])")
		return any(motif.search(code) for code in codes)

	return sorted(terme for terme in termes if not cite(terme))


def options(aide: str) -> set[str]:
	return set(OPTION.findall(aide))


@then(parsers.parse("{fichier} contient un lien vers doc/utilisation.md"))
def lien_vers_guide(fichier: str) -> None:
	assert "](doc/utilisation.md" in (RACINE / fichier).read_text(encoding="utf-8")


@then("chaque binaire du wrapper est documenté dans le guide")
def binaires_wrapper() -> None:
	scripts = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
	manquants = absents({f"Machin {nom.removeprefix('Machin_')}" for nom in scripts})
	assert not manquants, manquants


@then("chaque option du wrapper est documentée dans le guide")
def options_wrapper() -> None:
	aide = subprocess.run([RACINE / "bin" / "Machin", "--help"], capture_output=True, text=True, check=True).stdout
	section = aide.split("Options du wrapper :", 1)[1].split("Exemples :", 1)[0]
	manquants = absents(options(section))
	assert not manquants, manquants


@then("la commande « Machin logs » est documentée dans le guide")
def machin_logs() -> None:
	assert not absents({"Machin logs"})


@then(parsers.parse("chaque option de l'aide de « {executable} » est documentée dans le guide"))
def options_binaire(executable: str) -> None:
	module = f"machincast.{executable.removeprefix('Machin_')}"
	aide = subprocess.run([sys.executable, "-m", module, "--help"], capture_output=True, text=True, check=True)
	manquants = absents(options(aide.stdout.split("options:", 1)[1]))
	assert not manquants, f"{executable} : {manquants}"


@then("chaque état d'un sonore est documenté dans le guide")
def etats() -> None:
	manquants = absents(set(LIBELLES.values()))
	assert not manquants, manquants


@then("chaque verdict de la vérification d'un fichier est documenté dans le guide")
def verdicts() -> None:
	manquants = absents({str(etat) for etat in EtatFichier})
	assert not manquants, manquants


@then("chaque clé de métadonnées musicales tenue par l'indexeur est documentée dans le guide")
def cles() -> None:
	manquants = absents(set(CLES))
	assert not manquants, manquants


@then("chaque lien relatif du guide mène à un fichier du dépôt")
def liens() -> None:
	guide()
	casses = liens_casses(GUIDE)
	assert not casses, casses


@then("chaque ancre citée par le guide mène à un titre du fichier visé")
def ancres_du_guide() -> None:
	guide()
	cassees = ancres_cassees(GUIDE)
	assert not cassees, cassees
