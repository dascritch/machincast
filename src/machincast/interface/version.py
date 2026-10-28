"""Version de MachinCast, pour l'entrée « Version » du menu « Aide » (https://github.com/dascritch/machincast/issues/117).

MachinCast s'installe depuis son dépôt git (INSTALL.md) : la date de son dernier commit dit de quand date le code
installé, plus finement que le numéro de version. Elle se lit par git, dans le dépôt d'où le paquet est installé.

Releases (https://github.com/dascritch/machincast/issues/208) : une version publiée a son tag git, v<version>, et sa
section dans les nouveautés (NOUVEAUTES), « ## <version> — <AAAA-MM-JJ> », la plus récente d'abord. Installé au
commit du tag, MachinCast se dit publié ce jour-là, avec ce commit ; après lui, il dit aussi combien de modifications
ont suivi.
Hors d'un dépôt git, depuis l'archive d'une release, la date vient des nouveautés. La documentation de l'aide est celle
du tag quand le code installé est celui de la release, celle de main sinon.

Les nouveautés de la version installée s'affichent une fois, au premier lancement de l'interface qui la découvre
(vue_le, la version vue retenue dans les réglages des vues du compte), et dans la fenêtre de « Version ».
"""

import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from machincast import __version__

journal = logging.getLogger(__name__)

DEPOT = Path(__file__).resolve().parents[3]
"""Répertoire d'où MachinCast est installé : src/machincast/interface/ y est trois niveaux plus bas."""

NOUVEAUTES = Path(__file__).with_name("nouveautes.md")
"""Les nouveautés de chaque version publiée, pour l'équipe de l'antenne."""
SECTION = re.compile(r"^## (?P<version>\S+) — (?P<date>\d{4}-\d{2}-\d{2})[ \t]*$", re.MULTILINE)
"""Le titre d'une section des nouveautés : « ## 0.9.0 — 2026-10-28 »."""

DEPOT_EN_LIGNE = "https://github.com/dascritch/machincast"
DOCUMENTATION = "doc/utilisateur/README.md"
"""Le guide de l'antenne, dans le dépôt (https://github.com/dascritch/machincast/issues/128)."""

DELAI_DE_GIT = 5
"""Secondes laissées à git pour répondre."""

CLE_DES_NOUVEAUTES = "nouveautes/vues"
"""La dernière version dont les nouveautés ont été montrées, dans les réglages des vues du compte."""


@dataclass(frozen=True)
class Nouveautes:
	"""Les nouveautés d'une version publiée."""

	version: str
	publiee_le: date
	texte: str
	"""En Markdown, sans le titre de la section."""


@dataclass(frozen=True)
class Installation:
	"""Ce que git dit du code installé."""

	derniere: datetime
	"""Date du dernier commit."""
	commit: str
	"""Le dernier commit, abrégé."""
	depuis_la_release: int | None
	"""Modifications depuis le tag v<version> ; None sans ce tag."""


def nouveautes(chemin: Path | None = None) -> list[Nouveautes]:
	"""Les sections du fichier des nouveautés, dans l'ordre du fichier ; aucune s'il manque."""
	try:
		contenu = ((chemin) or (NOUVEAUTES)).read_text(encoding="utf-8")
	except OSError:
		return []
	titres = list(SECTION.finditer(contenu))
	sections = []
	for rang, titre in enumerate(titres):
		fin = len(contenu)
		if rang + 1 < len(titres):
			fin = titres[rang + 1].start()
		texte = contenu[titre.end() : fin].strip()
		sections.append(Nouveautes(titre["version"], date.fromisoformat(titre["date"]), texte))
	return sections


def de_la_version(version: str = __version__, chemin: Path | None = None) -> Nouveautes | None:
	"""Les nouveautés de cette version, si elle est publiée."""
	return next((section for section in nouveautes(chemin) if section.version == version), None)


def _git(depot: Path, *arguments: str) -> str | None:
	"""La sortie de git dans le dépôt ; None s'il échoue."""
	try:
		return subprocess.run(
			["git", "-C", str(depot), *arguments],
			capture_output=True,
			text=True,
			check=True,
			timeout=DELAI_DE_GIT,
		).stdout.strip()
	except (OSError, subprocess.SubprocessError) as erreur:
		journal.debug(f"git {' '.join(arguments)} impossible dans {depot} : {erreur}")
		return None


def installation(depot: Path) -> Installation | None:
	"""Le dernier commit du dépôt, et les modifications depuis la release ; None hors d'un dépôt git, ou sans git."""
	if not (depot / ".git").exists():
		return None
	# Un dépôt sans commit ne donne aucune date (https://github.com/dascritch/machincast/issues/187).
	sortie = (_git(depot, "log", "-1", "--format=%cI%x09%h")) or ("")
	try:
		instant, commit = sortie.split("\t")
		derniere = datetime.fromisoformat(instant)
	except ValueError as erreur:
		journal.warning(f"date du dernier commit illisible dans {depot} : {erreur}")
		return None
	# « v0.9.0-3-g1a2b3c4 » : 3 modifications depuis le tag ; aucune sortie sans lui.
	description = (_git(depot, "describe", "--tags", "--long", "--match", f"v{__version__}")) or ("")
	trouve = re.fullmatch(r".+-(?P<nombre>\d+)-g[0-9a-f]+", description)
	depuis = None
	if trouve is not None:
		depuis = int(trouve["nombre"])
	return Installation(derniere, commit, depuis)


def derniere_modification(depot: Path) -> datetime | None:
	"""Date du dernier commit du dépôt ; None hors d'un dépôt git, ou sans git."""
	installee = installation(depot)
	if installee is None:
		return None
	return installee.derniere


def _modifications(nombre: int) -> str:
	if nombre == 1:
		return "1 modification"
	return f"{nombre} modifications"


def texte() -> str:
	"""« MachinCast 0.9.0, publiée le 2026-10-28, commit 1a2b3c4. », ou, sans release, « MachinCast 0.1.0, dernière
	modification le 2026-10-18 à 14:05. », à l'heure du poste."""
	installee = installation(DEPOT)
	publiee = de_la_version()
	if installee is None:
		if publiee is not None:
			return f"MachinCast {__version__}, publiée le {publiee.publiee_le:%Y-%m-%d}."
		return (
			f"MachinCast {__version__}, date de dernière modification inconnue : l'installation n'est pas un dépôt git."
		)
	derniere = f"{installee.derniere.astimezone():%Y-%m-%d à %H:%M}"
	if installee.depuis_la_release is None:
		return f"MachinCast {__version__}, dernière modification le {derniere}."
	jour = "date inconnue"
	if publiee is not None:
		jour = f"{publiee.publiee_le:%Y-%m-%d}"
	if installee.depuis_la_release == 0:
		return f"MachinCast {__version__}, publiée le {jour}, commit {installee.commit}."
	return (
		f"MachinCast {__version__}, publiée le {jour}, plus {_modifications(installee.depuis_la_release)}, la dernière"
		f" le {derniere}, commit {installee.commit}."
	)


def documentation() -> str:
	"""Le guide de l'antenne du code installé : celui du tag de la release, ou celui de main."""
	installee = installation(DEPOT)
	reference = "main"
	if installee is None:
		if de_la_version() is not None:
			reference = f"v{__version__}"
	elif installee.depuis_la_release == 0:
		reference = f"v{__version__}"
	return f"{DEPOT_EN_LIGNE}/blob/{reference}/{DOCUMENTATION}"
