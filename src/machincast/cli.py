"""Éléments communs aux exécutables en ligne de commande."""

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from machincast import __version__, crash, created_files, plugins, runs
from machincast.configuration import Configuration, InvalidConfiguration, default_file, load
from machincast.i18n import _
from machincast.log import configure as configure_log
from machincast.plugins.manifest import BINARIES

log = logging.getLogger(__name__)

INVALID_CONFIGURATION_CODE = 2


def create_analyser(executable: str, description: str) -> argparse.ArgumentParser:
	"""Crée l'analyseur d'arguments commun à tous les exécutables Machin_*."""
	analyser = argparse.ArgumentParser(prog=executable, description=description)
	analyser.add_argument(
		"--version",
		action="version",
		version=f"{executable} (MachinCast) {__version__}",
	)
	analyser.add_argument(
		"--config",
		type=Path,
		default=None,
		metavar=_("FILE"),
		help=_("TOML configuration file (default: {default_file})").format(default_file=default_file()),
	)
	return analyser


def launch(
	executable: str,
	description: str,
	arguments: Sequence[str] | None,
	action: Callable[[Configuration, argparse.Namespace], int],
	own_options: Callable[[argparse.ArgumentParser], None] | None = None,
	recording: runs.Recording | None = None,
	then: Callable[[argparse.Namespace], None] | None = None,
) -> int:
	"""Analyse les arguments, charge la configuration, puis exécute l'action du binaire.

	own_options ajoute à l'analyseur commun les options propres au binaire ; l'action reçoit la configuration
	et toutes les options. Avec recording, le démarrage et la fin de l'action sont notés dans le journal et dans le log
	de la base (https://github.com/dascritch/machincast/issues/341) ; then vient après la fin, comme le terminal que la
	maintenance garde ouvert. L'action est surveillée (machincast.crash) : un plantage laisse un rapport dans
	crash-dump/ (https://github.com/dascritch/machincast/issues/342). Les plugins activés qui s'accrochent au binaire
	sont chargés avant l'action (machincast.plugins.load, https://github.com/dascritch/machincast/issues/585), et
	leurs notifications en cours attendues après. Renvoie le code de sortie : celui de l'action, ou
	INVALID_CONFIGURATION_CODE.
	"""
	configure_log(executable)
	analyser = create_analyser(executable, description)
	if own_options is not None:
		own_options(analyser)
	options = analyser.parse_args(arguments)
	try:
		configuration = load(options.config)
	except InvalidConfiguration as error:
		log.error(_("invalid configuration: {error}").format(error=error))
		return INVALID_CONFIGURATION_CODE
	# Les fichiers que le binaire crée, et les seuls qu'il touche (https://github.com/dascritch/machincast/issues/652).
	created_files.use(configuration.path)
	given = sys.argv[1:]
	if arguments is not None:
		given = list(arguments)
	with crash.watch(executable, given, configuration=options.config):
		if executable in BINARIES:
			plugins.load(configuration, executable)
		try:
			if (recording is None) or (not recording.when(options)):
				code = action(configuration, options)
			else:
				code = runs.recorded(
					configuration.database, executable, given, recording.role, lambda: action(configuration, options)
				)
		finally:
			plugins.active().points.close()
	if then is not None:
		then(options)
	return code
