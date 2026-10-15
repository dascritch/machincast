"""Point d'entrée de Machin_indexation.

Vérification des sonores existants (https://github.com/dascritch/machincast/issues/7). L'indexation des
répertoires de banques suivra (https://github.com/dascritch/machincast/issues/9).
"""

import logging
from collections.abc import Sequence

import psycopg

from machincast.base import Role, connecter
from machincast.cli import lancer
from machincast.configuration import Configuration
from machincast.indexation.decodage import DecodeurIndisponible
from machincast.indexation.verification import texte_bilan, verifier_sonores

EXECUTABLE = "Machin_indexation"
DESCRIPTION = "Vérifie les sonores et indexe les répertoires des banques."

CODE_ECHEC = 1

journal = logging.getLogger(__name__)


def executer(configuration: Configuration) -> int:
	base = configuration.base
	try:
		with connecter(base.socket, base.production, Role.INDEXATION) as connexion:
			bilan = verifier_sonores(connexion)
	except psycopg.OperationalError as erreur:
		journal.error("base de données injoignable (%s par %s) : %s", base.production, base.socket, erreur)
		return CODE_ECHEC
	except psycopg.Error as erreur:
		journal.error("erreur de base de données : %s", erreur)
		return CODE_ECHEC
	except DecodeurIndisponible as erreur:
		journal.error("vérification interrompue : %s", erreur)
		return CODE_ECHEC
	journal.info("%s", texte_bilan(bilan))
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer)


if __name__ == "__main__":
	raise SystemExit(main())
