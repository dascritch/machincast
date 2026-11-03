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
INSTALLS = {"INSTALL.md": RACINE / "INSTALL.md", "INSTALL.fr.md": RACINE / "INSTALL.fr.md"}
"""INSTALL.md, en anglais, et sa source française (https://github.com/dascritch/machincast/issues/355)."""
SCRIPT = RACINE / "install.sh"
CLAUDE = RACINE / "CLAUDE.md"

GRANT = re.compile(
	r"GRANT machincast_player, machincast_indexer, machincast_interface TO .+? WITH INHERIT FALSE, SET TRUE"
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


@then(parsers.parse("{readme} contient un lien vers {install}"))
def lien_readme(readme: str, install: str) -> None:
	assert f"]({install})" in texte(RACINE / readme)


@then(parsers.parse("la première commande apt de {document} installe les paquets d'install.sh"))
def apt_install(document: str) -> None:
	assert paquets_apt(RACINE / document) == paquets_script()


@then(parsers.parse("chaque paquet apt d'install.sh figure dans un tableau de {document}"))
def paquets_expliques(document: str) -> None:
	tableaux = "\n".join(ligne for ligne in texte(INSTALLS[document]).splitlines() if ligne.startswith("|"))
	absents = sorted(paquet for paquet in paquets_script() if f"`{paquet}`" not in tableaux)
	assert not absents, absents


@then(parsers.parse("{document}, install.sh et CLAUDE.md accordent les trois rôles par le même GRANT"))
def meme_grant(document: str) -> None:
	absents = [chemin.name for chemin in (INSTALLS[document], SCRIPT, CLAUDE) if not GRANT.search(texte(chemin))]
	assert not absents, absents


@then(parsers.parse("aucune commande createuser de {document} ne donne de droit particulier"))
def createuser_sans_droit(document: str) -> None:
	createuser = [mots for mots in commandes(INSTALLS[document]) if "createuser" in mots]
	assert createuser, f"{document} ne cite pas createuser"
	for mots in createuser:
		assert not DROITS_PARTICULIERS & set(mots), mots


@then(parsers.parse("chaque option d'install.sh citée dans {document} figure dans son aide"))
def options_install(document: str) -> None:
	aide = subprocess.run([str(SCRIPT), "--help"], capture_output=True, text=True, check=True).stdout
	citees = {mot for mots in commandes(INSTALLS[document]) if mots[:1] == ["./install.sh"] for mot in mots[1:]}
	assert citees, f"{document} ne cite pas ./install.sh avec ses options"
	inconnues = sorted(option for option in citees if option not in aide)
	assert not inconnues, inconnues


@then(parsers.parse("chaque commande Machin citée dans {document} appelle un binaire et des options qui existent"))
def commandes_machin(document: str) -> None:
	pyproject = tomllib.loads(texte(RACINE / "pyproject.toml"))
	# Le module de chaque binaire, d'après son point d'entrée : Machin_player lance machincast.lecture
	# (https://github.com/dascritch/machincast/issues/356).
	modules = {
		nom.removeprefix("Machin_"): cible.split(":")[0].removesuffix(".__main__")
		for nom, cible in pyproject["project"]["scripts"].items()
	}
	binaires = set(modules)
	options_wrapper = {"--config", "-h", "--help", "--binaries"}
	citees = [mots[1:] for mots in commandes(INSTALLS[document]) if (mots[:1]) and (mots[0] in WRAPPERS)]
	assert citees, f"{document} ne cite aucune commande Machin"
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
			[sys.executable, "-m", modules[binaire], "--help"], capture_output=True, text=True, check=True
		).stdout
		inconnues = [option for option in options if (option.startswith("-")) and (option.split("=")[0] not in aide)]
		assert not inconnues, f"Machin {binaire} : {inconnues}"


@then(parsers.parse("chaque étape de machincast.installation citée dans {document} existe"))
def etapes_installation(document: str) -> None:
	citees = [
		mots[mots.index("machincast.installation") + 1]
		for mots in commandes(INSTALLS[document])
		if "machincast.installation" in mots[:-1]
	]
	assert citees, f"{document} ne cite aucune étape de machincast.installation"
	inconnues = sorted(set(citees) - set(ACTIONS))
	assert not inconnues, inconnues


@then(parsers.parse("chaque lien relatif de {document} mène à un fichier du dépôt"))
def liens_relatifs(document: str) -> None:
	casses = liens_casses(RACINE / document)
	assert not casses, casses


@then(parsers.parse("chaque ancre citée par {document} mène à un titre du fichier visé"))
def ancres_valides(document: str) -> None:
	cassees = ancres_cassees(RACINE / document)
	assert not cassees, cassees


@then("les règles de développement ont une section « Definition of done » qui exige la documentation humaine")
def section_definition_of_done() -> None:
	regles = texte(RACINE / "doc" / "fr" / "regles" / "developpement.md")
	section = re.search(r"^## Definition of done\n(.*?)(?=^## |\Z)", regles, flags=re.MULTILINE | re.DOTALL)
	assert section, "section « Definition of done » absente"
	assert "documentées pour les humains" in section.group(1)


@then("les impératifs de CLAUDE.md renvoient à la definition of done")
def imperatifs() -> None:
	imperatifs = texte(CLAUDE).split("## Impératifs", 1)[1]
	assert "doc/fr/regles/developpement.md#definition-of-done" in imperatifs


@then("le modèle de description de PR comporte la case « documentation humaine à jour »")
def modele_pr() -> None:
	modele = RACINE / ".github" / "pull_request_template.md"
	assert modele.exists(), "modèle de PR absent"
	assert "- [ ] documentation humaine à jour" in texte(modele)


# ─── Releases (https://github.com/dascritch/machincast/issues/208) ───

VERSION_DU_README = {
	"README.md": "**Version {version}**, released on {date}",
	"README.fr.md": "**Version {version}**, publiée le {date}",
}
"""La phrase qui donne la dernière version publiée, dans chaque langue (https://github.com/dascritch/machincast/issues/355)."""


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


@then(parsers.parse("{release} a les mêmes versions, aux mêmes dates, dans le même ordre"))
def release_md(release: str) -> None:
	attendues = [(section.version, section.publiee_le) for section in publiees()]
	if attendues == []:
		return
	lues = [(section.version, section.publiee_le) for section in version.nouveautes(RACINE / release)]
	assert lues == attendues, lues


@then(parsers.parse("{readme} donne la dernière version publiée et sa date"))
def readme_version(readme: str) -> None:
	sections = publiees()
	if sections == []:
		return
	derniere = sections[0]
	phrase = VERSION_DU_README[readme].format(version=derniere.version, date=f"{derniere.publiee_le:%Y-%m-%d}")
	assert phrase in texte(RACINE / readme)


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


# ─── Documentation par langue (https://github.com/dascritch/machincast/issues/355) ───

PREMIER_NIVEAU = ("README", "INSTALL", "TROUBLESHOOTING", "CONTRIBUTION", "RELEASE")


@then("chaque document de premier niveau est en anglais, avec sa source française, et chacun mène à l'autre")
def premier_niveau() -> None:
	for nom in PREMIER_NIVEAU:
		anglais, francais = texte(RACINE / f"{nom}.md"), texte(RACINE / f"{nom}.fr.md")
		assert f"*[Version française]({nom}.fr.md)*" in anglais, nom
		assert f"*[English version]({nom}.md)*" in francais, nom


@then("doc ne contient que des répertoires de langue, dont la source française doc/fr")
def doc_par_langue() -> None:
	contenu = sorted(chemin.name for chemin in (RACINE / "doc").iterdir())
	assert "fr" in contenu, contenu
	assert set(contenu) <= {"fr", "en"}, contenu


@then(
	parsers.parse("chaque lien relatif des documents de premier niveau et de doc/{langue} mène à un fichier du dépôt")
)
def liens_de_la_documentation(langue: str) -> None:
	documents = [RACINE / f"{nom}{suffixe}.md" for nom in PREMIER_NIVEAU for suffixe in ("", ".fr")]
	documents += sorted((RACINE / "doc" / langue).rglob("*.md"))
	casses = [lien for document in documents for lien in liens_casses(document)]
	assert not casses, casses
