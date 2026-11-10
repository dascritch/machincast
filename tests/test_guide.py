"""Étapes de la documentation par public (https://github.com/dascritch/machincast/issues/74,
https://github.com/dascritch/machincast/issues/128).

Le guide utilisateur est doc/fr/utilisateur, le guide d'administration doc/fr/administration, celui du développement
doc/fr/developpement ; chacun a son sommaire, README.md. doc/fr/utilisation.md n'est plus qu'un index.
"""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

from pytest_bdd import parsers, scenarios, then

from machincast.i18n import _
from machincast.indexer.check import LABELS
from machincast.indexer.decoding import FileState
from machincast.indexer.tags import KEYS
from tests.markdown import broken_anchors, broken_links

scenarios("guide.feature")

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "doc" / "fr"
GUIDES = {"utilisateur": DOC / "utilisateur", "d'administration": DOC / "administration"}
OPTION = re.compile(r"(?<![\w-])(--?[a-z][a-z-]*)")
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
COMMAND_BLOCK = re.compile(r"^```(?:bash|sh|shell|console)\s*$", re.MULTILINE)


def pages(folder: Path) -> list[Path]:
	return sorted(folder.glob("*.md"))


def documentation() -> list[Path]:
	"""Toutes les pages de la documentation pour les humains : les trois guides et l'ancien guide."""
	return [*pages(DOC / "utilisateur"), *pages(DOC / "administration"), *pages(DOC / "developpement")] + [
		DOC / "utilisation.md"
	]


def guide_text(guide: str) -> str:
	folder = GUIDES[guide]
	assert pages(folder), f"{folder.relative_to(ROOT)} sans page"
	page_list = []
	for page in pages(folder):
		page_list.append(page.read_text(encoding="utf-8"))
	return "\n".join(page_list)


def absent_list(guide: str, terms: set[str]) -> list[str]:
	"""Termes que le guide ne cite dans aucun code entre accents graves, comme le veut sa mise en forme."""
	codes = re.findall(r"`([^`\n]+)`", guide_text(guide))

	def cites(term: str) -> bool:
		pattern = re.compile(rf"(?<![\w-]){re.escape(term)}(?![\w-])")
		found = False
		for code in codes:
			if pattern.search(code):
				found = True
				break
		return found

	return sorted(term for term in terms if not cites(term))


def options(help_: str) -> set[str]:
	return set(OPTION.findall(help_))


# ─── Organisation ──────────────────────────────────────────


@then(parsers.parse("{file} contient un lien vers {target}"))
def link(file: str, target: str) -> None:
	assert f"]({target}" in (ROOT / file).read_text(encoding="utf-8"), f"{file} ne mène pas à {target}"


@then(parsers.parse("chaque page de doc/{folder} est liée depuis doc/{summary}/README.md"))
def summary(folder: str, summary: str) -> None:
	assert folder == summary
	directory = DOC / folder
	linked = set(LINK.findall((directory / "README.md").read_text(encoding="utf-8")))
	missing_list = []
	for page in pages(directory):
		if (page.name != "README.md") and (page.name not in linked):
			missing_list.append(page.name)
	assert pages(directory), f"doc/{folder} sans page"
	assert not missing_list, missing_list


@then("aucune page du guide utilisateur n'a de bloc de commandes à taper")
def without_commands() -> None:
	faulty = []
	for page in pages(GUIDES["utilisateur"]):
		if COMMAND_BLOCK.search(page.read_text()):
			faulty.append(page.name)
	assert not faulty, faulty


# ─── Couverture ────────────────────────────────────────────


@then(parsers.parse("chaque binaire du wrapper est documenté dans le guide {guide}"))
def wrapper_binaries(guide: str) -> None:
	scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
	name_set = set()
	for name in scripts:
		name_set.add(f"Machin {name.removeprefix('Machin_')}")
	missing_list = absent_list(guide, name_set)
	assert not missing_list, missing_list


@then(parsers.parse("chaque option du wrapper est documentée dans le guide {guide}"))
def options_wrapper(guide: str) -> None:
	help_ = subprocess.run([ROOT / "bin" / "Machin", "--help"], capture_output=True, text=True, check=True).stdout
	section = help_.split("Options du wrapper :", 1)[1].split("Exemples :", 1)[0]
	missing_list = absent_list(guide, options(section))
	assert not missing_list, missing_list


@then(parsers.parse("la commande « Machin logs » est documentée dans le guide {guide}"))
def machin_logs(guide: str) -> None:
	assert not absent_list(guide, {"Machin logs"})


@then(parsers.parse("chaque option de l'aide de « {executable} » est documentée dans le guide {guide}"))
def binary_options(executable: str, guide: str) -> None:
	# Le module du point d'entrée : Machin_player lance machincast.player (https://github.com/dascritch/machincast/issues/356).
	scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
	module = scripts[executable].split(":")[0].removesuffix(".__main__")
	help_ = subprocess.run([sys.executable, "-m", module, "--help"], capture_output=True, text=True, check=True)
	missing_list = absent_list(guide, options(help_.stdout.split("options:", 1)[1]))
	assert not missing_list, f"{executable} : {missing_list}"


@then(parsers.parse("chaque état d'un sonore est documenté dans le guide {guide}"))
def states(guide: str) -> None:
	missing_list = absent_list(guide, set(LABELS.values()))
	assert not missing_list, missing_list


@then(parsers.parse("chaque verdict de la vérification d'un fichier est documenté dans le guide {guide}"))
def verdicts(guide: str) -> None:
	# Le guide, en français, nomme chaque verdict traduit (https://github.com/dascritch/machincast/issues/360).
	state_set = set()
	for state in FileState:
		state_set.add(_(state))
	missing_list = absent_list(guide, state_set)
	assert not missing_list, missing_list


@then(parsers.parse("chaque clé de métadonnées musicales tenue par l'indexeur est documentée dans le guide {guide}"))
def keys(guide: str) -> None:
	missing_list = absent_list(guide, set(KEYS))
	assert not missing_list, missing_list


# ─── Liens ─────────────────────────────────────────────────


@then("chaque lien relatif de la documentation mène à un fichier du dépôt")
def links() -> None:
	broken_list = []
	for page in documentation():
		for broken in broken_links(page):
			broken_list.append(broken)
	assert not broken_list, broken_list


@then("chaque ancre citée par la documentation mène à un titre du fichier visé")
def anchors() -> None:
	broken_list = []
	for page in documentation():
		for broken in broken_anchors(page):
			broken_list.append(broken)
	assert not broken_list, broken_list
