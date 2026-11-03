"""Étapes des scénarios de la documentation d'installation (https://github.com/dascritch/machincast/issues/71)."""

import re
import shlex
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

from pytest_bdd import parsers, scenarios, then, when

from machincast.installation import ACTIONS
from machincast.interface import version
from tests.markdown import broken_anchors, broken_links

scenarios("documentation.feature")

ROOT = Path(__file__).resolve().parents[1]
INSTALLS = {"INSTALL.md": ROOT / "INSTALL.md", "INSTALL.fr.md": ROOT / "INSTALL.fr.md"}
"""INSTALL.md, en anglais, et sa source française (https://github.com/dascritch/machincast/issues/355)."""
SCRIPT = ROOT / "install.sh"
CLAUDE = ROOT / "CLAUDE.md"

GRANT = re.compile(
	r"GRANT machincast_player, machincast_indexer, machincast_interface TO .+? WITH INHERIT FALSE, SET TRUE"
)
# Options de createuser qui donneraient au compte des droits sur le serveur.
PARTICULAR_RIGHTS = {"-d", "--createdb", "-r", "--createrole", "-s", "--superuser"}
WRAPPERS = {"Machin", "bin/Machin", "/usr/local/bin/Machin", "/opt/machincast/bin/Machin"}


def text(path: Path) -> str:
	return path.read_text(encoding="utf-8")


def commands(path: Path) -> list[list[str]]:
	"""Commandes des blocs de code bash d'un fichier Markdown, lignes de continuation jointes, découpées en mots."""
	blocks = re.findall(r"^```(?:bash|sh)\n(.*?)^```", text(path), flags=re.MULTILINE | re.DOTALL)
	result = []
	for block in blocks:
		for line in block.replace("\\\n", " ").splitlines():
			line = line.split(" #", 1)[0].strip()
			if (not line) or (line.startswith("#")):
				continue
			for command in re.split(r"\s*(?:&&|\|\||;|\|)\s*", line):
				if command:
					result.append(shlex.split(command))
	return result


def apt_packages(path: Path) -> set[str]:
	"""Paquets de la première commande apt install d'un fichier Markdown."""
	for words in commands(path):
		without_sudo = words[1:] if words[:1] == ["sudo"] else words
		if without_sudo[:2] in (["apt", "install"], ["apt-get", "install"]):
			return {word for word in without_sudo[2:] if not word.startswith("-")}
	raise AssertionError(f"aucune commande apt install dans {path.name}")


def script_packages() -> set[str]:
	table = re.search(r"^PAQUETS=\((.*?)^\)", text(SCRIPT), flags=re.MULTILINE | re.DOTALL)
	assert table, "tableau PAQUETS introuvable dans install.sh"
	return set(table.group(1).split())


@then(parsers.parse("{readme} contient un lien vers {install}"))
def readme_link(readme: str, install: str) -> None:
	assert f"]({install})" in text(ROOT / readme)


@then(parsers.parse("la première commande apt de {document} installe les paquets d'install.sh"))
def apt_install(document: str) -> None:
	assert apt_packages(ROOT / document) == script_packages()


@then(parsers.parse("chaque paquet apt d'install.sh figure dans un tableau de {document}"))
def explained_packages(document: str) -> None:
	tables = "\n".join(line for line in text(INSTALLS[document]).splitlines() if line.startswith("|"))
	absent_list = sorted(package for package in script_packages() if f"`{package}`" not in tables)
	assert not absent_list, absent_list


@then(parsers.parse("{document}, install.sh et CLAUDE.md accordent les trois rôles par le même GRANT"))
def same_grant(document: str) -> None:
	absent_list = [path.name for path in (INSTALLS[document], SCRIPT, CLAUDE) if not GRANT.search(text(path))]
	assert not absent_list, absent_list


@then(parsers.parse("aucune commande createuser de {document} ne donne de droit particulier"))
def createuser_without_right(document: str) -> None:
	createuser = [words for words in commands(INSTALLS[document]) if "createuser" in words]
	assert createuser, f"{document} ne cite pas createuser"
	for words in createuser:
		assert not PARTICULAR_RIGHTS & set(words), words


@then(parsers.parse("chaque option d'install.sh citée dans {document} figure dans son aide"))
def options_install(document: str) -> None:
	help_ = subprocess.run([str(SCRIPT), "--help"], capture_output=True, text=True, check=True).stdout
	cited_list = {word for words in commands(INSTALLS[document]) if words[:1] == ["./install.sh"] for word in words[1:]}
	assert cited_list, f"{document} ne cite pas ./install.sh avec ses options"
	unknown_list = sorted(option for option in cited_list if option not in help_)
	assert not unknown_list, unknown_list


@then(parsers.parse("chaque commande Machin citée dans {document} appelle un binaire et des options qui existent"))
def machin_commands(document: str) -> None:
	pyproject = tomllib.loads(text(ROOT / "pyproject.toml"))
	# Le module de chaque binaire, d'après son point d'entrée : Machin_player lance machincast.player
	# (https://github.com/dascritch/machincast/issues/356).
	modules = {
		name.removeprefix("Machin_"): target.split(":")[0].removesuffix(".__main__")
		for name, target in pyproject["project"]["scripts"].items()
	}
	binaries = set(modules)
	options_wrapper = {"--config", "-h", "--help", "--binaries"}
	cited_list = [words[1:] for words in commands(INSTALLS[document]) if (words[:1]) and (words[0] in WRAPPERS)]
	assert cited_list, f"{document} ne cite aucune commande Machin"
	for arguments in cited_list:
		# Options du wrapper avant le binaire : --config FICHIER ou --config=FICHIER.
		while (arguments) and (arguments[0].startswith("-")):
			assert arguments[0].split("=")[0] in options_wrapper, arguments
			arguments = arguments[2:] if arguments[0] == "--config" else arguments[1:]
		if (not arguments) or (arguments[0] == "logs"):
			continue
		binary, *options = arguments
		assert binary in binaries, f"binaire inconnu : {binary}"
		help_ = subprocess.run(
			[sys.executable, "-m", modules[binary], "--help"], capture_output=True, text=True, check=True
		).stdout
		unknown_list = [
			option for option in options if (option.startswith("-")) and (option.split("=")[0] not in help_)
		]
		assert not unknown_list, f"Machin {binary} : {unknown_list}"


@then(parsers.parse("chaque étape de machincast.installation citée dans {document} existe"))
def installation_steps(document: str) -> None:
	cited_list = [
		words[words.index("machincast.installation") + 1]
		for words in commands(INSTALLS[document])
		if "machincast.installation" in words[:-1]
	]
	assert cited_list, f"{document} ne cite aucune étape de machincast.installation"
	unknown_list = sorted(set(cited_list) - set(ACTIONS))
	assert not unknown_list, unknown_list


@then(parsers.parse("chaque lien relatif de {document} mène à un fichier du dépôt"))
def relative_links(document: str) -> None:
	broken_list = broken_links(ROOT / document)
	assert not broken_list, broken_list


@then(parsers.parse("chaque ancre citée par {document} mène à un titre du fichier visé"))
def valid_anchors(document: str) -> None:
	broken_list = broken_anchors(ROOT / document)
	assert not broken_list, broken_list


@then("les règles de développement ont une section « Definition of done » qui exige la documentation humaine")
def section_definition_of_done() -> None:
	rules = text(ROOT / "doc" / "fr" / "regles" / "developpement.md")
	section = re.search(r"^## Definition of done\n(.*?)(?=^## |\Z)", rules, flags=re.MULTILINE | re.DOTALL)
	assert section, "section « Definition of done » absente"
	assert "documentées pour les humains" in section.group(1)


@then("les impératifs de CLAUDE.md renvoient à la definition of done")
def imperatives() -> None:
	imperatives = text(CLAUDE).split("## Impératifs", 1)[1]
	assert "doc/fr/regles/developpement.md#definition-of-done" in imperatives


@then("le modèle de description de PR comporte la case « documentation humaine à jour »")
def pr_model() -> None:
	model = ROOT / ".github" / "pull_request_template.md"
	assert model.exists(), "modèle de PR absent"
	assert "- [ ] documentation humaine à jour" in text(model)


# ─── Releases (https://github.com/dascritch/machincast/issues/208) ───

README_VERSION = {
	"README.md": "**Version {version}**, released on {date}",
	"README.fr.md": "**Version {version}**, publiée le {date}",
}
"""La phrase qui donne la dernière version publiée, dans chaque langue (https://github.com/dascritch/machincast/issues/355)."""


def published_list() -> list[version.News]:
	return version.news(ROOT / "src" / "machincast" / "interface" / "news.md")


def number(text: str) -> tuple[int, ...]:
	"""« 0.9.0 » → (0, 9, 0) ; les suffixes (« 1.0.0rc1 ») ne comptent pas."""
	return tuple(int(count) for count in re.findall(r"\d+", text)[:3])


@then("les nouveautés de l'interface ont une section par version, de la plus récente à la plus ancienne")
def ordinates_sections() -> None:
	sections = published_list()
	versions = [number(section.version) for section in sections]
	assert versions == sorted(set(versions), reverse=True), versions
	days = [section.published_at for section in sections]
	assert days == sorted(days, reverse=True), days
	assert all(section.text != "" for section in sections)


@then(parsers.parse("{release} a les mêmes versions, aux mêmes dates, dans le même ordre"))
def release_md(release: str) -> None:
	expected_list = [(section.version, section.published_at) for section in published_list()]
	if expected_list == []:
		return
	fetched_list = [(section.version, section.published_at) for section in version.news(ROOT / release)]
	assert fetched_list == expected_list, fetched_list


@then(parsers.parse("{readme} donne la dernière version publiée et sa date"))
def readme_version(readme: str) -> None:
	sections = published_list()
	if sections == []:
		return
	last = sections[0]
	sentence = README_VERSION[readme].format(version=last.version, date=f"{last.published_at:%Y-%m-%d}")
	assert sentence in text(ROOT / readme)


@then("la version de pyproject.toml n'est pas plus ancienne que la dernière publiée")
def project_version() -> None:
	sections = published_list()
	if sections == []:
		return
	project = tomllib.loads(text(ROOT / "pyproject.toml"))["project"]["version"]
	assert number(project) >= number(sections[0].version), project


# ─── Archive d'une release (https://github.com/dascritch/machincast/issues/41) ───


@when("je fais l'archive de la version de pyproject.toml", target_fixture="archive")
def make_archive(tmp_path: Path) -> dict[str, tarfile.TarInfo]:
	project_number = tomllib.loads(text(ROOT / "pyproject.toml"))["project"]["version"]
	path = tmp_path / f"machincast-{project_number}.tar.gz"
	subprocess.run(
		[
			"git",
			"-C",
			str(ROOT),
			"archive",
			"--format=tar.gz",
			f"--prefix=machincast-{project_number}/",
			f"--output={path}",
			"HEAD",
		],
		check=True,
	)
	with tarfile.open(path) as archive:
		return {member.name: member for member in archive.getmembers()}


def project() -> str:
	return str(tomllib.loads(text(ROOT / "pyproject.toml"))["project"]["version"])


@then(parsers.parse("l'archive a pour répertoire « {directory} »"))
def archive_directory(archive: dict[str, tarfile.TarInfo], directory: str) -> None:
	expected = directory.replace("<version>", project())
	assert all((name == expected) or (name.startswith(f"{expected}/")) for name in archive), sorted(archive)[:5]


@then(parsers.parse("l'archive contient « {name} », exécutable"))
def executable(archive: dict[str, tarfile.TarInfo], name: str) -> None:
	member = archive[f"machincast-{project()}/{name}"]
	assert member.mode & 0o111, oct(member.mode)


@then(parsers.re(r"l'archive contient (?P<names>«.+»)$"))
def contains(archive: dict[str, tarfile.TarInfo], names: str) -> None:
	missing_list = [
		name for name in re.findall(r"« ([^»]+) »", names) if f"machincast-{project()}/{name}" not in archive
	]
	assert missing_list == [], missing_list


# ─── Documentation par langue (https://github.com/dascritch/machincast/issues/355) ───

FIRST_LEVEL = ("README", "INSTALL", "TROUBLESHOOTING", "CONTRIBUTION", "RELEASE")


@then("chaque document de premier niveau est en anglais, avec sa source française, et chacun mène à l'autre")
def first_level() -> None:
	for name in FIRST_LEVEL:
		english, french = text(ROOT / f"{name}.md"), text(ROOT / f"{name}.fr.md")
		assert f"*[Version française]({name}.fr.md)*" in english, name
		assert f"*[English version]({name}.md)*" in french, name


@then("doc ne contient que des répertoires de langue, dont la source française doc/fr")
def doc_by_language() -> None:
	content = sorted(path.name for path in (ROOT / "doc").iterdir())
	assert "fr" in content, content
	assert set(content) <= {"fr", "en"}, content


@then(
	parsers.parse("chaque lien relatif des documents de premier niveau et de doc/{language} mène à un fichier du dépôt")
)
def documentation_links(language: str) -> None:
	documents = [ROOT / f"{name}{suffix}.md" for name in FIRST_LEVEL for suffix in ("", ".fr")]
	documents += sorted((ROOT / "doc" / language).rglob("*.md"))
	broken_list = [link for document in documents for link in broken_links(document)]
	assert not broken_list, broken_list
