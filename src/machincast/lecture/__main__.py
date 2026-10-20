"""Point d'entrée de Machin_lecture (https://github.com/dascritch/machincast/issues/88).

Diffuse la grille sur la sortie audio de la configuration, jusqu'à SIGTERM (arrêt du service) ou Ctrl-C. Avec
--simulation DEBUT FIN, simule la diffusion entre ces deux instants, sans son ni écriture en base
(https://github.com/dascritch/machincast/issues/21).
"""

import argparse
import logging
from collections.abc import Sequence
from datetime import datetime

import psycopg

from machincast.audio import SortieAudioIndisponible
from machincast.base import Role, connecter
from machincast.cli import CODE_CONFIGURATION_INVALIDE, lancer
from machincast.configuration import Configuration
from machincast.hasard import creer_hasard
from machincast.horloge import HorlogeSysteme
from machincast.lecture.analyse import Analyseur, commande_d_analyse
from machincast.lecture.diffusion import Diffusion, diffuser, installer_arret
from machincast.lecture.etat import SocketEtat, SocketEtatOccupee
from machincast.lecture.moteur import MoteurAudio
from machincast.lecture.simulation import nom_par_defaut, simuler
from machincast.lecture.sorties import Sorties

EXECUTABLE = "Machin_lecture"
DESCRIPTION = "Lit les événements programmés et les diffuse sur la sortie audio configurée."

CODE_ECHEC = 1

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
journal = logging.getLogger("machincast.lecture")


def instant(texte: str) -> datetime:
	"""Date et heure ISO 8601, en heure du poste : « 2026-10-20 20:00 » ou « 2026-10-20T20:00:00 »."""
	try:
		return datetime.fromisoformat(texte).astimezone()
	except ValueError:
		raise argparse.ArgumentTypeError(
			f"date invalide : « {texte} », attendu par exemple « 2026-10-20 20:00 »"
		) from None


def nom_de_sortie(texte: str) -> str:
	if (not texte) or ("/" in texte) or (texte.startswith(".")):
		raise argparse.ArgumentTypeError(f"nom invalide : « {texte} », sans « / » et sans point au début")
	return texte


def options_propres(analyseur: argparse.ArgumentParser) -> None:
	simulation = analyseur.add_argument_group("simulation (https://github.com/dascritch/machincast/issues/21)")
	simulation.add_argument(
		"--simulation",
		nargs=2,
		type=instant,
		metavar=("DEBUT", "FIN"),
		help="simule la diffusion entre ces deux dates et heures, sans son et sans écrire en base",
	)
	simulation.add_argument("--graine", type=int, metavar="N", help="graine du hasard, pour un résultat reproductible")
	simulation.add_argument(
		"--nom",
		type=nom_de_sortie,
		metavar="NOM",
		help="nom des sorties .csv, .pls et .html de la simulation (par défaut : simulation-DEBUT-FIN)",
	)


def executer(configuration: Configuration, options: argparse.Namespace) -> int:
	if options.simulation is not None:
		return executer_simulation(configuration, options)
	if (options.graine is not None) or (options.nom is not None):
		journal.error("--graine et --nom ne s'emploient qu'avec --simulation")
		return CODE_CONFIGURATION_INVALIDE
	return executer_diffusion(configuration)


def executer_simulation(configuration: Configuration, options: argparse.Namespace) -> int:
	debut, fin = options.simulation
	if fin <= debut:
		journal.error("période de simulation invalide : la fin doit suivre le début")
		return CODE_CONFIGURATION_INVALIDE
	base = configuration.base
	repertoire = configuration.sorties.csv.parent
	try:
		with connecter(base.socket, base.production, Role.LECTURE) as connexion:
			resultat = simuler(
				connexion,
				repertoire,
				debut,
				fin,
				options.graine,
				options.nom,
				configuration.metadonnees,
				configuration.crossfades,
			)
	except psycopg.OperationalError as erreur:
		journal.error(f"base de données injoignable ({base.production} par {base.socket}) : {erreur}")
		return CODE_ECHEC
	except psycopg.Error as erreur:
		journal.error(f"erreur de base de données : {erreur}")
		return CODE_ECHEC
	except OSError as erreur:
		journal.error(f"sorties de la simulation impossibles à écrire : {erreur}")
		return CODE_ECHEC
	anomalies = sum(1 for niveau, _, _ in resultat.log if niveau != "info")
	nom = (options.nom) or (nom_par_defaut(debut, fin))
	journal.info(
		f"simulation {nom} : {len(resultat.passages)} passage(s), {anomalies} alerte(s) ou incident(s),"
		" rien n'a été écrit en base"
	)
	for chemin in (resultat.fichiers) or (()):
		journal.info(f"sortie : {chemin}")
	return 0


def executer_diffusion(configuration: Configuration) -> int:
	base = configuration.base
	arret = installer_arret()
	try:
		with connecter(base.socket, base.production, Role.LECTURE) as connexion:
			moteur = MoteurAudio(configuration.audio)
			try:
				journal.info(f"diffusion sur la sortie {configuration.audio.sortie}, arrêt par Ctrl-C ou SIGTERM")
				diffusion = Diffusion(
					connexion,
					moteur,
					HorlogeSysteme(),
					creer_hasard(None),
					sorties=Sorties.depuis(configuration),
					etat=SocketEtat(configuration.lecture.socket_etat),
					crossfades=configuration.crossfades,
					analyseur=Analyseur(commande_d_analyse(configuration.chemin)),
				)
				diffuser(diffusion, arret)
			finally:
				moteur.fermer()
	except psycopg.OperationalError as erreur:
		journal.error(f"base de données injoignable ({base.production} par {base.socket}) : {erreur}")
		return CODE_ECHEC
	except psycopg.Error as erreur:
		journal.error(f"erreur de base de données : {erreur}")
		return CODE_ECHEC
	except SocketEtatOccupee as erreur:
		journal.error(f"diffusion refusée : {erreur}")
		return CODE_ECHEC
	except SortieAudioIndisponible as erreur:
		journal.error(f"sortie audio indisponible : {erreur}")
		return CODE_ECHEC
	journal.info("diffusion arrêtée")
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer, options_propres)


if __name__ == "__main__":
	raise SystemExit(main())
