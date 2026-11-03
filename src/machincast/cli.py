"""Éléments communs aux exécutables en ligne de commande."""

import argparse
import logging
from collections.abc import Callable, Sequence
from pathlib import Path

from machincast import __version__
from machincast.configuration import Configuration, InvalidConfiguration, default_file, load
from machincast.i18n import _
from machincast.log import configure as configure_log

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
) -> int:
	"""Analyse les arguments, charge la configuration, puis exécute l'action du binaire.

	own_options ajoute à l'analyseur commun les options propres au binaire ; l'action reçoit la configuration
	et toutes les options. Renvoie le code de sortie : celui de l'action, ou INVALID_CONFIGURATION_CODE.
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
	return action(configuration, options)


def not_implemented(executable: str, ticket: int) -> int:
	"""Signale une fonctionnalité pas encore développée et renvoie un code d'erreur."""
	log.error(
		_("not implemented yet, see https://github.com/dascritch/machincast/issues/{ticket}").format(ticket=ticket)
	)
	return 1
