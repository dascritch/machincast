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
from tests.markdown import ancres_cassees, liens_casses

scenarios("documentation.feature")

RACINE = Path(__file__).resolve().parents[1]
INSTALL = RACINE / "INSTALL.md"
SCRIPT = RACINE / "install.sh"
CLAUDE = RACINE / "CLAUDE.md"

GRANT = re.compile(
	r"GRANT machincast_lecture, machincast_indexation, machincast_interface TO .+? WITH INHERIT FALSE, SET TRUE"
)
# Options de createuser qui donneraient au compte des droits sur le serveur.
DROITS_PARTICULIERS = {"-d", "--createdb", "-r", "--createrole", "-s", "--superuser"}
WRAPPERS = {"Machin", "bin/Machin", "/usr/local/bin/Machin", "/opt/machincast/bin/Machin"}


def texte(chemin: Path) -> str:
	return chemin.read_text(encoding="utf-8")


def commandes(chemin: Path) -> list[list[str]]:
	"""Commandes des blocs de code bash d'un fichier Markdown, lignes de continuation jointes, découpées en mots."""
	blocs = re.findall(r"^```(?:bash|sh)\n(.*?)^```", texte(chemin), flags=re.MULTILINE | re.DOTALL)
	resultat = []
	for bloc in blocs:
		for ligne in bloc.replace("\\\n", " ").splitlines():
			ligne = ligne.split(" #", 1)[0].strip()
			if (not ligne) or (ligne.startswith("#")):
				continue
			for commande in re.split(r"\s*(?:&&|\|\||;|\|)\s*", ligne):
				if commande:
					resultat.append(shlex.split(commande))
	return resultat


def paquets_apt(chemin: Path) -> set[str]:
	"""Paquets de la première commande apt install d'un fichier Markdown."""
	for mots in commandes(chemin):
		sans_sudo = mots[1:] if mots[:1] == ["sudo"] else mots
		if sans_sudo[:2] in (["apt", "install"], ["apt-get", "install"]):
			return {mot for mot in sans_sudo[2:] if not mot.startswith("-")}
	raise AssertionError(f"aucune commande apt install dans {chemin.name}")


def paquets_script() -> set[str]:
	tableau = re.search(r"^PAQUETS=\((.*?)^\)", texte(SCRIPT), flags=re.MULTILINE | re.DOTALL)
	assert tableau, "tableau PAQUETS introuvable dans install.sh"
	return set(tableau.group(1).split())


@then("README.md contient un lien vers INSTALL.md")
def lien_readme() -> None:
	assert "](INSTALL.md)" in texte(RACINE / "README.md")


@then("la première commande apt d'INSTALL.md installe les paquets d'install.sh")
def apt_install() -> None:
	assert paquets_apt(INSTALL) == paquets_script()


@then("la première commande apt de CLAUDE.md installe les paquets d'install.sh")
def apt_claude() -> None:
	assert paquets_apt(CLAUDE) == paquets_script()


@then("chaque paquet apt d'install.sh figure dans un tableau d'INSTALL.md")
def paquets_expliques() -> None:
	tableaux = "\n".join(ligne for ligne in texte(INSTALL).splitlines() if ligne.startswith("|"))
	absents = sorted(paquet for paquet in paquets_script() if f"`{paquet}`" not in tableaux)
	assert not absents, absents


@then("INSTALL.md, install.sh et CLAUDE.md accordent les trois rôles par le même GRANT")
def meme_grant() -> None:
	absents = [chemin.name for chemin in (INSTALL, SCRIPT, CLAUDE) if not GRANT.search(texte(chemin))]
	assert not absents, absents


@then("aucune commande createuser d'INSTALL.md ne donne de droit particulier")
def createuser_sans_droit() -> None:
	createuser = [mots for mots in commandes(INSTALL) if "createuser" in mots]
	assert createuser, "INSTALL.md ne cite pas createuser"
	for mots in createuser:
		assert not DROITS_PARTICULIERS & set(mots), mots


@then("chaque option d'install.sh citée dans INSTALL.md figure dans son aide")
def options_install() -> None:
	aide = subprocess.run([str(SCRIPT), "--help"], capture_output=True, text=True, check=True).stdout
	citees = {mot for mots in commandes(INSTALL) if mots[:1] == ["./install.sh"] for mot in mots[1:]}
	assert citees, "INSTALL.md ne cite pas ./install.sh avec ses options"
	inconnues = sorted(option for option in citees if option not in aide)
	assert not inconnues, inconnues


@then("chaque commande Machin citée dans INSTALL.md appelle un binaire et des options qui existent")
def commandes_machin() -> None:
	pyproject = tomllib.loads(texte(RACINE / "pyproject.toml"))
	binaires = {nom.removeprefix("Machin_") for nom in pyproject["project"]["scripts"]}
	options_wrapper = {"--config", "-h", "--help", "--binaires"}
	citees = [mots[1:] for mots in commandes(INSTALL) if (mots[:1]) and (mots[0] in WRAPPERS)]
	assert citees, "INSTALL.md ne cite aucune commande Machin"
	for arguments in citees:
		# Options du wrapper avant le binaire : --config FICHIER ou --config=FICHIER.
		while (arguments) and (arguments[0].startswith("-")):
			assert arguments[0].split("=")[0] in options_wrapper, arguments
			arguments = arguments[2:] if arguments[0] == "--config" else arguments[1:]
		if (not arguments) or (arguments[0] == "logs"):
			continue
		binaire, *options = arguments
		assert binaire in binaires, f"binaire inconnu : {binaire}"
		aide = subprocess.run(
			[sys.executable, "-m", f"machincast.{binaire}", "--help"], capture_output=True, text=True, check=True
		).stdout
		inconnues = [option for option in options if (option.startswith("-")) and (option.split("=")[0] not in aide)]
		assert not inconnues, f"Machin {binaire} : {inconnues}"


@then("chaque étape de machincast.installation citée dans INSTALL.md existe")
def etapes_installation() -> None:
	citees = [
		mots[mots.index("machincast.installation") + 1]
		for mots in commandes(INSTALL)
		if "machincast.installation" in mots[:-1]
	]
	assert citees, "INSTALL.md ne cite aucune étape de machincast.installation"
	inconnues = sorted(set(citees) - set(ACTIONS))
	assert not inconnues, inconnues


@then("chaque lien relatif d'INSTALL.md mène à un fichier du dépôt")
def liens_relatifs() -> None:
	casses = liens_casses(INSTALL)
	assert not casses, casses


@then("chaque ancre citée par INSTALL.md mène à un titre du fichier visé")
def ancres_valides() -> None:
	cassees = ancres_cassees(INSTALL)
	assert not cassees, cassees


@then("les règles de développement ont une section « Definition of done » qui exige la documentation humaine")
def section_definition_of_done() -> None:
	regles = texte(RACINE / "doc" / "regles" / "developpement.md")
	section = re.search(r"^## Definition of done\n(.*?)(?=^## |\Z)", regles, flags=re.MULTILINE | re.DOTALL)
	assert section, "section « Definition of done » absente"
	assert "documentées pour les humains" in section.group(1)


@then("les impératifs de CLAUDE.md renvoient à la definition of done")
def imperatifs() -> None:
	imperatifs = texte(CLAUDE).split("## Impératifs", 1)[1]
	assert "doc/regles/developpement.md#definition-of-done" in imperatifs


@then("le modèle de description de PR comporte la case « documentation humaine à jour »")
def modele_pr() -> None:
	modele = RACINE / ".github" / "pull_request_template.md"
	assert modele.exists(), "modèle de PR absent"
	assert "- [ ] documentation humaine à jour" in texte(modele)


# ─── Releases (https://github.com/dascritch/machincast/issues/208) ───

RELEASE = RACINE / "RELEASE.md"
README = RACINE / "README.md"


def publiees() -> list[version.Nouveautes]:
	return version.nouveautes(RACINE / "src" / "machincast" / "interface" / "nouveautes.md")


def numero(texte: str) -> tuple[int, ...]:
	"""« 0.9.0 » → (0, 9, 0) ; les suffixes (« 1.0.0rc1 ») ne comptent pas."""
	return tuple(int(nombre) for nombre in re.findall(r"\d+", texte)[:3])


@then("les nouveautés de l'interface ont une section par version, de la plus récente à la plus ancienne")
def sections_ordonnees() -> None:
	sections = publiees()
	versions = [numero(section.version) for section in sections]
	assert versions == sorted(set(versions), reverse=True), versions
	jours = [section.publiee_le for section in sections]
	assert jours == sorted(jours, reverse=True), jours
	assert all(section.texte != "" for section in sections)


@then("RELEASE.md a les mêmes versions, aux mêmes dates, dans le même ordre")
def release_md() -> None:
	attendues = [(section.version, section.publiee_le) for section in publiees()]
	if attendues == []:
		return
	lues = [(section.version, section.publiee_le) for section in version.nouveautes(RELEASE)]
	assert lues == attendues, lues


@then("README.md donne la dernière version publiée et sa date")
def readme_version() -> None:
	sections = publiees()
	if sections == []:
		return
	derniere = sections[0]
	assert f"**Version {derniere.version}**, publiée le {derniere.publiee_le:%Y-%m-%d}" in texte(README)


@then("la version de pyproject.toml n'est pas plus ancienne que la dernière publiée")
def version_du_projet() -> None:
	sections = publiees()
	if sections == []:
		return
	projet = tomllib.loads(texte(RACINE / "pyproject.toml"))["project"]["version"]
	assert numero(projet) >= numero(sections[0].version), projet


# ─── Archive d'une release (https://github.com/dascritch/machincast/issues/41) ───


@when("je fais l'archive de la version de pyproject.toml", target_fixture="archive")
def faire_l_archive(tmp_path: Path) -> dict[str, tarfile.TarInfo]:
	numero_du_projet = tomllib.loads(texte(RACINE / "pyproject.toml"))["project"]["version"]
	chemin = tmp_path / f"machincast-{numero_du_projet}.tar.gz"
	subprocess.run(
		[
			"git",
			"-C",
			str(RACINE),
			"archive",
			"--format=tar.gz",
			f"--prefix=machincast-{numero_du_projet}/",
			f"--output={chemin}",
			"HEAD",
		],
		check=True,
	)
	with tarfile.open(chemin) as archive:
		return {membre.name: membre for membre in archive.getmembers()}


def projet() -> str:
	return str(tomllib.loads(texte(RACINE / "pyproject.toml"))["project"]["version"])


@then(parsers.parse("l'archive a pour répertoire « {repertoire} »"))
def repertoire_de_l_archive(archive: dict[str, tarfile.TarInfo], repertoire: str) -> None:
	attendu = repertoire.replace("<version>", projet())
	assert all((nom == attendu) or (nom.startswith(f"{attendu}/")) for nom in archive), sorted(archive)[:5]


@then(parsers.parse("l'archive contient « {nom} », exécutable"))
def executable(archive: dict[str, tarfile.TarInfo], nom: str) -> None:
	membre = archive[f"machincast-{projet()}/{nom}"]
	assert membre.mode & 0o111, oct(membre.mode)


@then(parsers.re(r"l'archive contient (?P<noms>«.+»)$"))
def contient(archive: dict[str, tarfile.TarInfo], noms: str) -> None:
	manquants = [nom for nom in re.findall(r"« ([^»]+) »", noms) if f"machincast-{projet()}/{nom}" not in archive]
	assert manquants == [], manquants
