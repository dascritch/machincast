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
from machincast.i18n import _, counted, pgettext

log = logging.getLogger(__name__)

DROP = Path(__file__).resolve().parents[3]
"""Répertoire d'où MachinCast est installé : src/machincast/interface/ y est trois niveaux plus bas."""

NEWS = Path(__file__).with_name("news.md")
"""Les nouveautés de chaque version publiée, pour l'équipe de l'antenne."""
SECTION = re.compile(r"^## (?P<version>\S+) — (?P<date>\d{4}-\d{2}-\d{2})[ \t]*$", re.MULTILINE)
"""Le titre d'une section des nouveautés : « ## 0.9.0 — 2026-10-28 »."""

DROP_IN_LINE = "https://github.com/dascritch/machincast"
DOCUMENTATION = "doc/fr/utilisateur/README.md"
"""Le guide de l'antenne, dans le dépôt (https://github.com/dascritch/machincast/issues/128)."""

GIT_DELAY = 5
"""Secondes laissées à git pour répondre."""

NEWS_KEY = "nouveautes/vues"
"""La dernière version dont les nouveautés ont été montrées, dans les réglages des vues du compte."""


@dataclass(frozen=True)
class News:
	"""Les nouveautés d'une version publiée."""

	version: str
	published_at: date
	text: str
	"""En Markdown, sans le titre de la section."""


@dataclass(frozen=True)
class Installation:
	"""Ce que git dit du code installé."""

	last: datetime
	"""Date du dernier commit."""
	commit: str
	"""Le dernier commit, abrégé."""
	since_release: int | None
	"""Modifications depuis le tag v<version> ; None sans ce tag."""


def news(path: Path | None = None) -> list[News]:
	"""Les sections du fichier des nouveautés, dans l'ordre du fichier ; aucune s'il manque."""
	try:
		content = ((path) or (NEWS)).read_text(encoding="utf-8")
	except OSError:
		return []
	titles = list(SECTION.finditer(content))
	sections = []
	for rank, title in enumerate(titles):
		end = len(content)
		if rank + 1 < len(titles):
			end = titles[rank + 1].start()
		text = content[title.end() : end].strip()
		sections.append(News(title["version"], date.fromisoformat(title["date"]), text))
	return sections


def of_the_version(version: str = __version__, path: Path | None = None) -> News | None:
	"""Les nouveautés de cette version, si elle est publiée."""
	return next((section for section in news(path) if section.version == version), None)


def _git(drop: Path, *arguments: str) -> str | None:
	"""La sortie de git dans le dépôt ; None s'il échoue."""
	try:
		return subprocess.run(
			["git", "-C", str(drop), *arguments],
			capture_output=True,
			text=True,
			check=True,
			timeout=GIT_DELAY,
		).stdout.strip()
	except (OSError, subprocess.SubprocessError) as error:
		log.debug(
			_("git {list} impossible in {drop}: {error}").format(list=" ".join(arguments), drop=drop, error=error)
		)
		return None


def installation(drop: Path) -> Installation | None:
	"""Le dernier commit du dépôt, et les modifications depuis la release ; None hors d'un dépôt git, ou sans git."""
	if not (drop / ".git").exists():
		return None
	# Un dépôt sans commit ne donne aucune date (https://github.com/dascritch/machincast/issues/187).
	output = (_git(drop, "log", "-1", "--format=%cI%x09%h")) or ("")
	try:
		instant, commit = output.split("\t")
		last = datetime.fromisoformat(instant)
	except ValueError as error:
		log.warning(_("unreadable date of the last commit in {drop}: {error}").format(drop=drop, error=error))
		return None
	# « v0.9.0-3-g1a2b3c4 » : 3 modifications depuis le tag ; aucune sortie sans lui.
	description = (_git(drop, "describe", "--tags", "--long", "--match", f"v{__version__}")) or ("")
	found = re.fullmatch(r".+-(?P<nombre>\d+)-g[0-9a-f]+", description)
	since = None
	if found is not None:
		since = int(found["nombre"])
	return Installation(last, commit, since)


def last_change(drop: Path) -> datetime | None:
	"""Date du dernier commit du dépôt ; None hors d'un dépôt git, ou sans git."""
	installed = installation(drop)
	if installed is None:
		return None
	return installed.last


def _changes(count: int) -> str:
	return counted("{count} change", "{count} changes", count)


def text() -> str:
	"""« MachinCast 0.9.0, publiée le 2026-10-28, commit 1a2b3c4. », ou, sans release, « MachinCast 0.1.0, dernière
	modification le 2026-10-18 à 14:05. », à l'heure du poste."""
	installed = installation(DROP)
	published = of_the_version()
	if installed is None:
		if published is not None:
			return _("MachinCast {version}, published on {published_at:%Y-%m-%d}.").format(
				version=__version__, published_at=published.published_at
			)
		return _("MachinCast {version}, date of last change unknown: the installation is not a git repository.").format(
			version=__version__
		)
	last = pgettext("version date", "{last:%Y-%m-%d at %H:%M}").format(last=installed.last.astimezone())
	if installed.since_release is None:
		return _("MachinCast {version}, last change on {last}.").format(version=__version__, last=last)
	day = _("unknown date")
	if published is not None:
		day = f"{published.published_at:%Y-%m-%d}"
	if installed.since_release == 0:
		return _("MachinCast {version}, published on {day}, commit {commit}.").format(
			version=__version__, day=day, commit=installed.commit
		)
	return _("MachinCast {version}, published on {day}, plus {changes}, the last on {last}, commit {commit}.").format(
		version=__version__, day=day, changes=_changes(installed.since_release), last=last, commit=installed.commit
	)


def documentation() -> str:
	"""Le guide de l'antenne du code installé : celui du tag de la release, ou celui de main."""
	installed = installation(DROP)
	reference = "main"
	if installed is None:
		if of_the_version() is not None:
			reference = f"v{__version__}"
	elif installed.since_release == 0:
		reference = f"v{__version__}"
	return f"{DROP_IN_LINE}/blob/{reference}/{DOCUMENTATION}"
