"""Éléments communs aux exécutables en ligne de commande."""

import argparse
import sys

from machincast import __version__


def creer_analyseur(executable: str, description: str) -> argparse.ArgumentParser:
	"""Crée l'analyseur d'arguments commun à tous les exécutables Machin_*."""
	analyseur = argparse.ArgumentParser(prog=executable, description=description)
	analyseur.add_argument(
		"--version",
		action="version",
		version=f"{executable} (MachinCast) {__version__}",
	)
	return analyseur


def non_implemente(executable: str, ticket: int) -> int:
	"""Signale une fonctionnalité pas encore développée et renvoie un code d'erreur."""
	print(
		f"{executable} : pas encore implémenté, voir https://github.com/dascritch/machincast/issues/{ticket}",
		file=sys.stderr,
	)
	return 1
