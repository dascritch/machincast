"""Tâche quotidienne à l'heure réglée (https://github.com/dascritch/machincast/issues/455).

	python -m machincast.schedule claim --config machincast.toml

install.sh --service installe un minuteur systemd fixe, machincast-tasks.timer, qui lance Machin tasks tous les
quarts d'heure ; le wrapper ne lance la tâche quotidienne (Machin purge, puis Machin indexer --full-audit) que si
`claim` la réserve :

- elle est due quand l'heure réglée (schedule.daily, 10:00 par défaut) de sa dernière occurrence passée n'a pas encore
  été servie : une fois par jour, à partir de cette heure ; une tâche manquée, poste éteint, passe au quart d'heure qui
  suit son démarrage ; une heure changée vaut dès le jour même ;
- `claim` note son passage dans le répertoire d'état de l'unité (STATE_DIRECTORY, que systemd crée au compte de
  l'unité) avant la tâche : une tâche en échec n'est pas relancée tous les quarts d'heure, son échec est dans le
  journal et dans le log de la base (machincast.runs).

L'heure se règle dans machincast.toml, depuis l'interface (Fichier → Paramètres du service…, page Tâches) ou par un outil
de déploiement, sans droit d'administrateur : le minuteur ne change pas. Codes de sortie : 0, tâche due et réservée ;
1, pas encore due ; 2, configuration invalide ou répertoire d'état absent.
"""

import argparse
import logging
import os
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from pathlib import Path

from machincast.cli import INVALID_CONFIGURATION_CODE, launch
from machincast.clock import Clock, SystemClock
from machincast.configuration import Configuration
from machincast.i18n import _
from machincast.protection import check_writing

EXECUTABLE = "machincast.schedule"
DESCRIPTION = _("Claims the daily tasks, once a day from the set hour.")
NOT_DUE_CODE = 1
STAMP = "daily"
"""Le fichier du répertoire d'état où se note le dernier passage de la tâche quotidienne."""
CLOCK: Clock = SystemClock()

log = logging.getLogger("machincast.schedule")


def due(now: datetime, daily: time, last: datetime | None) -> bool:
	"""Vrai si la dernière occurrence passée de l'heure réglée n'a pas été servie par le dernier passage."""
	latest = datetime.combine(now.date(), daily).astimezone()
	if latest > now:
		latest = datetime.combine(now.date() - timedelta(days=1), daily).astimezone()
	return (last is None) or (last < latest)


def _state_directory() -> Path | None:
	"""Le répertoire d'état que systemd donne à l'unité ; le premier, s'il y en a plusieurs."""
	directories = os.environ.get("STATE_DIRECTORY", "")
	if not directories:
		return None
	return Path(directories.split(":")[0])


def _last(stamp: Path) -> datetime | None:
	"""Le dernier passage noté ; None sans passage, ou s'il est illisible."""
	try:
		return datetime.fromisoformat(stamp.read_text(encoding="utf-8").strip())
	except (OSError, ValueError):
		return None


def claim(configuration: Configuration, _options: argparse.Namespace) -> int:
	"""Réserve la tâche quotidienne si elle est due, en notant son passage ; le code de sortie dit si elle l'est."""
	directory = _state_directory()
	if directory is None:
		log.error(_("STATE_DIRECTORY is not set: the daily tasks are claimed by their systemd unit"))
		return INVALID_CONFIGURATION_CODE
	stamp = directory / STAMP
	now = CLOCK.now()
	daily = configuration.schedule.daily
	if not due(now, daily, _last(stamp)):
		log.info(_("daily tasks already done since {hour}").format(hour=daily.isoformat(timespec="minutes")))
		return NOT_DUE_CODE
	check_writing(stamp)
	stamp.write_text(now.isoformat() + "\n", encoding="utf-8")
	log.info(_("daily tasks claimed, set at {hour}").format(hour=daily.isoformat(timespec="minutes")))
	return 0


def _options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument("action", choices=["claim"], help=_("claim the daily tasks if they are due"))


def main(arguments: Sequence[str] | None = None) -> int:
	"""Lance l'action demandée ; le code de sortie de claim."""
	return launch(EXECUTABLE, DESCRIPTION, arguments, claim, _options)


if __name__ == "__main__":
	raise SystemExit(main())
