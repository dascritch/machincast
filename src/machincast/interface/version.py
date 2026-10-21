"""Version de MachinCast, pour l'entrée « Version » du menu « Aide » (https://github.com/dascritch/machincast/issues/117).

MachinCast s'installe depuis son dépôt git (INSTALL.md) : la date de son dernier commit dit de quand date le code
installé, plus finement que le numéro de version. Elle se lit par git, dans le dépôt d'où le paquet est installé.
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path

from machincast import __version__

journal = logging.getLogger(__name__)

DEPOT = Path(__file__).resolve().parents[3]
"""Répertoire d'où MachinCast est installé : src/machincast/interface/ y est trois niveaux plus bas."""


DELAI_DE_GIT = 5
"""Secondes laissées à git pour donner la date du dernier commit."""


def derniere_modification(depot: Path) -> datetime | None:
	"""Date du dernier commit du dépôt ; None hors d'un dépôt git, ou sans git."""
	if not (depot / ".git").exists():
		return None
	try:
		sortie = subprocess.run(
			["git", "-C", str(depot), "log", "-1", "--format=%cI"],
			capture_output=True,
			text=True,
			check=True,
			timeout=DELAI_DE_GIT,
		).stdout
		# Un dépôt sans commit ne donne aucune date (https://github.com/dascritch/machincast/issues/187).
		return datetime.fromisoformat(sortie.strip())
	except (OSError, subprocess.SubprocessError, ValueError) as erreur:
		journal.warning(f"date du dernier commit illisible dans {depot} : {erreur}")
		return None


def texte() -> str:
	"""« MachinCast 0.1.0, dernière modification le 2026-10-18 à 14:05. », à l'heure du poste."""
	date = derniere_modification(DEPOT)
	if date is None:
		return (
			f"MachinCast {__version__}, date de dernière modification inconnue : l'installation n'est pas un dépôt git."
		)
	return f"MachinCast {__version__}, dernière modification le {date.astimezone():%Y-%m-%d à %H:%M}."
