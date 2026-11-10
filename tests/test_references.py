"""Étapes du scénario des liens vers les tickets et les PR (https://github.com/dascritch/machincast/issues/57)."""

import re
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then

scenarios("references.feature")

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = (".md", ".py", ".toml", ".sql", ".sh", ".bash", ".bats", ".feature")
# Scripts bash sans extension : wrapper et autocomplétion (https://github.com/dascritch/machincast/issues/6).
SCRIPTS_DIRECTORIES = ("bin/", "bash-completion/")

EXCLUSIONS = (
	# Ce scénario et ses étapes contiennent volontairement des références nues, comme exemples.
	"tests/features/references.feature",
	"tests/test_references.py",
)

# « #51 » : un dièse suivi de chiffres, ni précédé d'une lettre ou d'un « / », ni suivi d'une lettre ou d'un tiret
# (ce qui écarte les ancres Markdown comme #48-metadonnees et les couleurs comme #1d76db). Six chiffres tout juste
# sont une couleur, comme #000000 ou #767676, pas un ticket (https://github.com/dascritch/machincast/issues/412).
REFERENCE = re.compile(r"(?<![\w/&])#(?!\d{6}(?!\d))(\d+)(?![\w-])")
# Un lien Markdown dont le texte contient la référence et qui pointe vers le ticket ou la PR.
LINK = re.compile(r"\[[^\]]*#(\d+)[^\]]*\]\(https://github\.com/dascritch/machincast/(?:issues|pull)/(\d+)\)")


def bare_references(line: str) -> list[str]:
	"""Références « #N » d'une ligne qui ne sont pas le texte d'un lien vers le ticket ou la PR N."""
	linked = {}
	for m in LINK.finditer(line):
		linked[m.span(0)] = m
	bare = []
	for reference in REFERENCE.finditer(line):
		in_link = False
		for (start, end), m in linked.items():
			if (start <= reference.start() < end) and (m.group(1) == m.group(2) == reference.group(1)):
				in_link = True
				break
		if not in_link:
			bare.append(reference.group(0))
	return bare


@pytest.fixture
def context() -> dict[str, object]:
	return {}


@given("les fichiers Markdown, Python, TOML, SQL, shell et Gherkin du dépôt")
def files(context: dict[str, object]) -> None:
	tracked_list = subprocess.run(
		["git", "ls-files", "--cached", "--others", "--exclude-standard"],
		cwd=ROOT,
		capture_output=True,
		text=True,
		check=True,
	).stdout.splitlines()
	path_list = []
	for path in tracked_list:
		if (
			((path.endswith(EXTENSIONS)) or (path.startswith(SCRIPTS_DIRECTORIES)))
			and (not path.startswith(EXCLUSIONS))
			# Un fichier supprimé mais pas encore retiré de l'index git n'est plus à lire.
			and ((ROOT / path).is_file())
		):
			path_list.append(path)
	context["fichiers"] = path_list


@given(parsers.parse("la ligne « {line} »"))
def a_line(context: dict[str, object], line: str) -> None:
	context["ligne"] = line


@then("chaque référence à un ticket ou une PR est un lien vers GitHub")
def linked_all(context: dict[str, object]) -> None:
	faults = []
	for path in context["fichiers"]:  # type: ignore[attr-defined]
		for number, line in enumerate((ROOT / path).read_text(encoding="utf-8").splitlines(), start=1):
			for reference in bare_references(line):
				faults.append(f"{path}:{number} : {reference}")
	assert not faults, "références sans lien :\n" + "\n".join(faults)


@then(parsers.parse("le détecteur y trouve {count:d} référence(s) nue(s)"))
def detector(context: dict[str, object], count: int) -> None:
	assert len(bare_references(str(context["ligne"]))) == count
