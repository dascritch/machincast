"""Éléments communs aux exécutables en ligne de commande."""

import argparse
import logging
from collections.abc import Callable, Sequence
from pathlib import Path

from machincast import __version__
from machincast.configuration import FICHIER_PAR_DEFAUT, Configuration, ConfigurationInvalide, charger
from machincast.journal import configurer as configurer_journal

journal = logging.getLogger(__name__)

CODE_CONFIGURATION_INVALIDE = 2


def creer_analyseur(executable: str, description: str) -> argparse.ArgumentParser:
	"""Crée l'analyseur d'arguments commun à tous les exécutables Machin_*."""
	analyseur = argparse.ArgumentParser(prog=executable, description=description)
	analyseur.add_argument(
		"--version",
		action="version",
		version=f"{executable} (MachinCast) {__version__}",
	)
	analyseur.add_argument(
		"--config",
		type=Path,
		default=None,
		metavar="FICHIER",
		help=f"fichier de configuration TOML (par défaut : {FICHIER_PAR_DEFAUT} dans le répertoire courant)",
	)
	return analyseur


def lancer(
	executable: str,
	description: str,
	arguments: Sequence[str] | None,
	action: Callable[[Configuration, argparse.Namespace], int],
	options_propres: Callable[[argparse.ArgumentParser], None] | None = None,
) -> int:
	"""Analyse les arguments, charge la configuration, puis exécute l'action du binaire.

	options_propres ajoute à l'analyseur commun les options propres au binaire ; l'action reçoit la configuration
	et toutes les options. Renvoie le code de sortie : celui de l'action, ou CODE_CONFIGURATION_INVALIDE.
	"""
	configurer_journal(executable)
	analyseur = creer_analyseur(executable, description)
	if options_propres is not None:
		options_propres(analyseur)
	options = analyseur.parse_args(arguments)
	try:
		configuration = charger(options.config)
	except ConfigurationInvalide as erreur:
		journal.error("configuration invalide : %s", erreur)
		return CODE_CONFIGURATION_INVALIDE
	return action(configuration, options)


def non_implemente(executable: str, ticket: int) -> int:
	"""Signale une fonctionnalité pas encore développée et renvoie un code d'erreur."""
	journal.error("pas encore implémenté, voir https://github.com/dascritch/machincast/issues/%d", ticket)
	return 1
