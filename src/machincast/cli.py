"""Éléments communs aux exécutables en ligne de commande."""

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from machincast import __version__
from machincast.configuration import FICHIER_PAR_DEFAUT, Configuration, ConfigurationInvalide, charger

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
	action: Callable[[Configuration], int],
) -> int:
	"""Analyse les arguments, charge la configuration, puis exécute l'action du binaire.

	Renvoie le code de sortie : celui de l'action, ou CODE_CONFIGURATION_INVALIDE.
	"""
	options = creer_analyseur(executable, description).parse_args(arguments)
	try:
		configuration = charger(options.config)
	except ConfigurationInvalide as erreur:
		print(f"{executable} : configuration invalide : {erreur}", file=sys.stderr)
		return CODE_CONFIGURATION_INVALIDE
	return action(configuration)


def non_implemente(executable: str, ticket: int) -> int:
	"""Signale une fonctionnalité pas encore développée et renvoie un code d'erreur."""
	print(
		f"{executable} : pas encore implémenté, voir https://github.com/dascritch/machincast/issues/{ticket}",
		file=sys.stderr,
	)
	return 1
