"""Autorise un utilisateur système à endosser les rôles MachinCast.

Utilisé par install.sh (https://github.com/dascritch/machincast/issues/40), à lancer par un administrateur
PostgreSQL, par exemple :

	sudo -u postgres python -m machincast.droits --base machincast autoriser machincast lecture
	sudo -u postgres python -m machincast.droits --base machincast autoriser xavier interface indexation

Les rôles eux-mêmes sont créés par la migration 0002.droits.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

import psycopg

from machincast.base import Role, autoriser_utilisateur
from machincast.journal import configurer as configurer_journal

ROLES = {role.name.lower(): role for role in Role}
"""Noms courts acceptés en ligne de commande : lecture, indexation, interface."""


def nom_utilisateur(valeur: str) -> str:
	if not valeur.strip():
		raise argparse.ArgumentTypeError("le nom d'utilisateur ne peut pas être vide")
	return valeur


def main(arguments: Sequence[str] | None = None) -> int:
	analyseur = argparse.ArgumentParser(
		prog="python -m machincast.droits",
		description="Autorise un utilisateur système à endosser des rôles MachinCast, sans en hériter les droits.",
	)
	analyseur.add_argument("--socket", type=Path, default=Path("/var/run/postgresql"), help="répertoire de la socket")
	analyseur.add_argument("--base", required=True, help="base de données à laquelle se connecter")
	actions = analyseur.add_subparsers(dest="action", required=True)
	autoriser = actions.add_parser("autoriser", help="autoriser un utilisateur à endosser des rôles")
	autoriser.add_argument(
		"utilisateur", type=nom_utilisateur, help="nom de l'utilisateur système (authentification peer)"
	)
	autoriser.add_argument("roles", nargs="+", choices=sorted(ROLES), metavar="ROLE", help=", ".join(sorted(ROLES)))
	options = analyseur.parse_args(arguments)

	journal = configurer_journal("machincast.droits")
	try:
		with psycopg.connect(host=str(options.socket), dbname=options.base, autocommit=True) as connexion:
			autoriser_utilisateur(connexion, options.utilisateur, [ROLES[nom] for nom in options.roles])
	except psycopg.Error as erreur:
		journal.error("%s", erreur)
		return 1
	journal.info("%s peut endosser : %s", options.utilisateur, ", ".join(str(ROLES[nom]) for nom in options.roles))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
