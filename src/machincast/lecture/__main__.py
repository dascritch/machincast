"""Point d'entrée de Machin_lecture (https://github.com/dascritch/machincast/issues/88).

Diffuse la grille sur la sortie audio de la configuration, jusqu'à SIGTERM (arrêt du service) ou Ctrl-C.
"""

import argparse
import logging
from collections.abc import Sequence

import psycopg

from machincast.audio import SortieAudioIndisponible
from machincast.base import Role, connecter
from machincast.cli import lancer
from machincast.configuration import Configuration
from machincast.hasard import creer_hasard
from machincast.horloge import HorlogeSysteme
from machincast.lecture.diffusion import Diffusion, diffuser, installer_arret
from machincast.lecture.moteur import MoteurAudio

EXECUTABLE = "Machin_lecture"
DESCRIPTION = "Lit les événements programmés et les diffuse sur la sortie audio configurée."

CODE_ECHEC = 1

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
journal = logging.getLogger("machincast.lecture")


def executer(configuration: Configuration, options: argparse.Namespace) -> int:
	base = configuration.base
	arret = installer_arret()
	try:
		with connecter(base.socket, base.production, Role.LECTURE) as connexion:
			moteur = MoteurAudio(configuration.audio)
			try:
				journal.info(f"diffusion sur la sortie {configuration.audio.sortie}, arrêt par Ctrl-C ou SIGTERM")
				diffuser(Diffusion(connexion, moteur, HorlogeSysteme(), creer_hasard(None)), arret)
			finally:
				moteur.fermer()
	except psycopg.OperationalError as erreur:
		journal.error(f"base de données injoignable ({base.production} par {base.socket}) : {erreur}")
		return CODE_ECHEC
	except psycopg.Error as erreur:
		journal.error(f"erreur de base de données : {erreur}")
		return CODE_ECHEC
	except SortieAudioIndisponible as erreur:
		journal.error(f"sortie audio indisponible : {erreur}")
		return CODE_ECHEC
	journal.info("diffusion arrêtée")
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer)


if __name__ == "__main__":
	raise SystemExit(main())
