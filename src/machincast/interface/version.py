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


def derniere_modification(depot: Path) -> datetime | None:
	"""Date du dernier commit du dépôt ; None hors d'un dépôt git, ou sans git."""
	if not (depot / ".git").exists():
		return None
	try:
		sortie = subprocess.run(
			["git", "-C", str(depot), "log", "-1", "--format=%cI"], capture_output=True, text=True, check=True
		).stdout
	except (OSError, subprocess.CalledProcessError) as erreur:
		journal.warning(f"date du dernier commit illisible dans {depot} : {erreur}")
		return None
	return datetime.fromisoformat(sortie.strip())


def texte() -> str:
	"""« MachinCast 0.1.0, dernière modification le 2026-10-18 à 14:05. », à l'heure du poste."""
	date = derniere_modification(DEPOT)
	if date is None:
		return (
			f"MachinCast {__version__}, date de dernière modification inconnue : l'installation n'est pas un dépôt git."
		)
	return f"MachinCast {__version__}, dernière modification le {date.astimezone():%Y-%m-%d à %H:%M}."
