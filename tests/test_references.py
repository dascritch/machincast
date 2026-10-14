"""Étapes du scénario des liens vers les tickets et les PR (https://github.com/dascritch/machincast/issues/57)."""

import re
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then

scenarios("references.feature")

RACINE = Path(__file__).resolve().parents[1]
EXTENSIONS = (".md", ".py", ".toml", ".sql", ".sh", ".feature")

# Migrations déjà fusionnées : jamais modifiées, même leurs commentaires.
EXCLUSIONS = (
	"src/machincast/migrations/0001.",
	# Ce scénario et ses étapes contiennent volontairement des références nues, comme exemples.
	"tests/features/references.feature",
	"tests/test_references.py",
)

# « #51 » : un dièse suivi de chiffres, ni précédé d'une lettre ou d'un « / », ni suivi d'une lettre ou d'un tiret
# (ce qui écarte les ancres Markdown comme #48-metadonnees et les couleurs comme #1d76db).
REFERENCE = re.compile(r"(?<![\w/&])#(\d+)(?![\w-])")
# Un lien Markdown dont le texte contient la référence et qui pointe vers le ticket ou la PR.
LIEN = re.compile(r"\[[^\]]*#(\d+)[^\]]*\]\(https://github\.com/dascritch/machincast/(?:issues|pull)/(\d+)\)")


def references_nues(ligne: str) -> list[str]:
	"""Références « #N » d'une ligne qui ne sont pas le texte d'un lien vers le ticket ou la PR N."""
	liees = {m.span(0): m for m in LIEN.finditer(ligne)}
	nues = []
	for reference in REFERENCE.finditer(ligne):
		dans_un_lien = any(
			debut <= reference.start() < fin and m.group(1) == m.group(2) == reference.group(1)
			for (debut, fin), m in liees.items()
		)
		if not dans_un_lien:
			nues.append(reference.group(0))
	return nues


@pytest.fixture
def contexte() -> dict[str, object]:
	return {}


@given("les fichiers Markdown, Python, TOML, SQL, shell et Gherkin du dépôt")
def fichiers(contexte: dict[str, object]) -> None:
	suivis = subprocess.run(
		["git", "ls-files", "--cached", "--others", "--exclude-standard"],
		cwd=RACINE,
		capture_output=True,
		text=True,
		check=True,
	).stdout.splitlines()
	contexte["fichiers"] = [
		chemin for chemin in suivis if chemin.endswith(EXTENSIONS) and not chemin.startswith(EXCLUSIONS)
	]


@given(parsers.parse("la ligne « {ligne} »"))
def une_ligne(contexte: dict[str, object], ligne: str) -> None:
	contexte["ligne"] = ligne


@then("chaque référence à un ticket ou une PR est un lien vers GitHub")
def toutes_liees(contexte: dict[str, object]) -> None:
	fautes = []
	for chemin in contexte["fichiers"]:  # type: ignore[attr-defined]
		for numero, ligne in enumerate((RACINE / chemin).read_text(encoding="utf-8").splitlines(), start=1):
			for reference in references_nues(ligne):
				fautes.append(f"{chemin}:{numero} : {reference}")
	assert not fautes, "références sans lien :\n" + "\n".join(fautes)


@then(parsers.parse("le détecteur y trouve {nombre:d} référence(s) nue(s)"))
def detecteur(contexte: dict[str, object], nombre: int) -> None:
	assert len(references_nues(str(contexte["ligne"]))) == nombre
