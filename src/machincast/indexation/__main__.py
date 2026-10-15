"""Point d'entrée de Machin_indexation.

Parcours des répertoires des banques (https://github.com/dascritch/machincast/issues/9), puis vérification
des sonores (https://github.com/dascritch/machincast/issues/7), en indexation rapide par défaut ou en audit
complet (https://github.com/dascritch/machincast/issues/69).
"""

import argparse
import logging
from collections.abc import Sequence

import psycopg

from machincast.base import Role, connecter
from machincast.cli import lancer
from machincast.configuration import Configuration
from machincast.indexation.decodage import DecodeurIndisponible
from machincast.indexation.indexeur import indexer
from machincast.indexation.verification import texte_bilan

EXECUTABLE = "Machin_indexation"
DESCRIPTION = "Vérifie les sonores et indexe les répertoires des banques."

CODE_ECHEC = 1

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
journal = logging.getLogger("machincast.indexation")


def options_propres(analyseur: argparse.ArgumentParser) -> None:
	analyseur.add_argument(
		"--audit-complet",
		action="store_true",
		help="décode tous les sonores ; par défaut, l'indexation rapide ne décode que les sonores en aperçu",
	)


def executer(configuration: Configuration, options: argparse.Namespace) -> int:
	base = configuration.base
	try:
		with connecter(base.socket, base.production, Role.INDEXATION) as connexion:
			bilan = indexer(connexion, audit_complet=options.audit_complet)
	except psycopg.OperationalError as erreur:
		journal.error(f"base de données injoignable ({base.production} par {base.socket}) : {erreur}")
		return CODE_ECHEC
	except psycopg.Error as erreur:
		journal.error(f"erreur de base de données : {erreur}")
		return CODE_ECHEC
	except DecodeurIndisponible as erreur:
		journal.error(f"vérification interrompue : {erreur}")
		return CODE_ECHEC
	journal.info(texte_bilan(bilan))
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer, options_propres)


if __name__ == "__main__":
	raise SystemExit(main())
