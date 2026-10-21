"""Étapes de la documentation par public (https://github.com/dascritch/machincast/issues/74,
https://github.com/dascritch/machincast/issues/128).

Le guide utilisateur est doc/utilisateur, le guide d'administration doc/administration, celui du développement
doc/developpement ; chacun a son sommaire, README.md. doc/utilisation.md n'est plus qu'un index.
"""

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
DOC = RACINE / "doc"
GUIDES = {"utilisateur": DOC / "utilisateur", "d'administration": DOC / "administration"}
OPTION = re.compile(r"(?<![\w-])(--?[a-z][a-z-]*)")
LIEN = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
BLOC_DE_COMMANDES = re.compile(r"^```(?:bash|sh|shell|console)\s*$", re.MULTILINE)


def pages(dossier: Path) -> list[Path]:
	return sorted(dossier.glob("*.md"))


def documentation() -> list[Path]:
	"""Toutes les pages de la documentation pour les humains : les trois guides et l'ancien guide."""
	return [*pages(DOC / "utilisateur"), *pages(DOC / "administration"), *pages(DOC / "developpement")] + [
		DOC / "utilisation.md"
	]


def texte_du_guide(guide: str) -> str:
	dossier = GUIDES[guide]
	assert pages(dossier), f"{dossier.relative_to(RACINE)} sans page"
	return "\n".join(page.read_text(encoding="utf-8") for page in pages(dossier))


def absents(guide: str, termes: set[str]) -> list[str]:
	"""Termes que le guide ne cite dans aucun code entre accents graves, comme le veut sa mise en forme."""
	codes = re.findall(r"`([^`\n]+)`", texte_du_guide(guide))

	def cite(terme: str) -> bool:
		motif = re.compile(rf"(?<![\w-]){re.escape(terme)}(?![\w-])")
		return any(motif.search(code) for code in codes)

	return sorted(terme for terme in termes if not cite(terme))


def options(aide: str) -> set[str]:
	return set(OPTION.findall(aide))


# ─── Organisation ──────────────────────────────────────────


@then(parsers.parse("{fichier} contient un lien vers {cible}"))
def lien(fichier: str, cible: str) -> None:
	assert f"]({cible}" in (RACINE / fichier).read_text(encoding="utf-8"), f"{fichier} ne mène pas à {cible}"


@then(parsers.parse("chaque page de doc/{dossier} est liée depuis doc/{sommaire}/README.md"))
def sommaire(dossier: str, sommaire: str) -> None:
	assert dossier == sommaire
	repertoire = DOC / dossier
	liees = set(LIEN.findall((repertoire / "README.md").read_text(encoding="utf-8")))
	manquantes = [page.name for page in pages(repertoire) if (page.name != "README.md") and (page.name not in liees)]
	assert pages(repertoire), f"doc/{dossier} sans page"
	assert not manquantes, manquantes


@then("aucune page du guide utilisateur n'a de bloc de commandes à taper")
def sans_commandes() -> None:
	fautives = [page.name for page in pages(GUIDES["utilisateur"]) if BLOC_DE_COMMANDES.search(page.read_text())]
	assert not fautives, fautives


# ─── Couverture ────────────────────────────────────────────


@then(parsers.parse("chaque binaire du wrapper est documenté dans le guide {guide}"))
def binaires_wrapper(guide: str) -> None:
	scripts = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
	manquants = absents(guide, {f"Machin {nom.removeprefix('Machin_')}" for nom in scripts})
	assert not manquants, manquants


@then(parsers.parse("chaque option du wrapper est documentée dans le guide {guide}"))
def options_wrapper(guide: str) -> None:
	aide = subprocess.run([RACINE / "bin" / "Machin", "--help"], capture_output=True, text=True, check=True).stdout
	section = aide.split("Options du wrapper :", 1)[1].split("Exemples :", 1)[0]
	manquants = absents(guide, options(section))
	assert not manquants, manquants


@then(parsers.parse("la commande « Machin logs » est documentée dans le guide {guide}"))
def machin_logs(guide: str) -> None:
	assert not absents(guide, {"Machin logs"})


@then(parsers.parse("chaque option de l'aide de « {executable} » est documentée dans le guide {guide}"))
def options_binaire(executable: str, guide: str) -> None:
	module = f"machincast.{executable.removeprefix('Machin_')}"
	aide = subprocess.run([sys.executable, "-m", module, "--help"], capture_output=True, text=True, check=True)
	manquants = absents(guide, options(aide.stdout.split("options:", 1)[1]))
	assert not manquants, f"{executable} : {manquants}"


@then(parsers.parse("chaque état d'un sonore est documenté dans le guide {guide}"))
def etats(guide: str) -> None:
	manquants = absents(guide, set(LIBELLES.values()))
	assert not manquants, manquants


@then(parsers.parse("chaque verdict de la vérification d'un fichier est documenté dans le guide {guide}"))
def verdicts(guide: str) -> None:
	manquants = absents(guide, {str(etat) for etat in EtatFichier})
	assert not manquants, manquants


@then(parsers.parse("chaque clé de métadonnées musicales tenue par l'indexeur est documentée dans le guide {guide}"))
def cles(guide: str) -> None:
	manquants = absents(guide, set(CLES))
	assert not manquants, manquants


# ─── Liens ─────────────────────────────────────────────────


@then("chaque lien relatif de la documentation mène à un fichier du dépôt")
def liens() -> None:
	casses = [casse for page in documentation() for casse in liens_casses(page)]
	assert not casses, casses


@then("chaque ancre citée par la documentation mène à un titre du fichier visé")
def ancres() -> None:
	cassees = [cassee for page in documentation() for cassee in ancres_cassees(page)]
	assert not cassees, cassees
