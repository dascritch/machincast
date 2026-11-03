"""Point d'entrée de Machin_player (https://github.com/dascritch/machincast/issues/88).

Diffuse la grille sur la sortie audio de la configuration, jusqu'à SIGTERM (arrêt du service) ou Ctrl-C. Avec
--simulation DEBUT FIN, simule la diffusion entre ces deux instants, sans son ni écriture en base
(https://github.com/dascritch/machincast/issues/21) ; --directory place ses sorties ailleurs que dans le répertoire
des sorties de la configuration, comme le fait l'écran de simulation de l'interface
(https://github.com/dascritch/machincast/issues/37).
"""

import argparse
import logging
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import psycopg

from machincast.audio import UnavailableAudioOutput
from machincast.cli import INVALID_CONFIGURATION_CODE, launch
from machincast.clock import SystemClock
from machincast.configuration import Configuration
from machincast.database import Role, open_connection
from machincast.player.analysis import Analyser, analysis_command
from machincast.player.broadcast import Broadcast, air, install_stop
from machincast.player.engine import AudioEngine
from machincast.player.outputs import Outputs
from machincast.player.simulation import default_name, simulate
from machincast.player.state import BusyStateSocket, StateSocket
from machincast.randomness import create_randomness

EXECUTABLE = "Machin_player"
DESCRIPTION = "Lit les événements programmés et les diffuse sur la sortie audio configurée."

FAILURE_CODE = 1

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
log = logging.getLogger("machincast.player")


def instant(text: str) -> datetime:
	"""Date et heure ISO 8601, en heure du poste : « 2026-10-20 20:00 » ou « 2026-10-20T20:00:00 »."""
	try:
		return datetime.fromisoformat(text).astimezone()
	except ValueError:
		raise argparse.ArgumentTypeError(
			f"date invalide : « {text} », attendu par exemple « 2026-10-20 20:00 »"
		) from None


def output_name(text: str) -> str:
	if (not text) or ("/" in text) or (text.startswith(".")):
		raise argparse.ArgumentTypeError(f"nom invalide : « {text} », sans « / » et sans point au début")
	return text


def own_options(analyser: argparse.ArgumentParser) -> None:
	simulation = analyser.add_argument_group("simulation (https://github.com/dascritch/machincast/issues/21)")
	simulation.add_argument(
		"--simulation",
		nargs=2,
		type=instant,
		metavar=("DEBUT", "FIN"),
		help="simule la diffusion entre ces deux dates et heures, sans son et sans écrire en base",
	)
	simulation.add_argument("--seed", type=int, metavar="N", help="graine du hasard, pour un résultat reproductible")
	simulation.add_argument(
		"--name",
		type=output_name,
		metavar="NOM",
		help="nom des sorties .csv, .pls et .html de la simulation (par défaut : simulation-DEBUT-FIN)",
	)
	simulation.add_argument(
		"--directory",
		type=Path,
		metavar="REPERTOIRE",
		help="répertoire des sorties de la simulation (par défaut : celui de outputs.csv de la configuration)",
	)


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	if options.simulation is not None:
		return run_simulation(configuration, options)
	if (options.seed is not None) or (options.name is not None) or (options.directory is not None):
		log.error("--seed, --name et --directory ne s'emploient qu'avec --simulation")
		return INVALID_CONFIGURATION_CODE
	return run_broadcast(configuration)


def run_simulation(configuration: Configuration, options: argparse.Namespace) -> int:
	start, end = options.simulation
	if end <= start:
		log.error("période de simulation invalide : la fin doit suivre le début")
		return INVALID_CONFIGURATION_CODE
	database = configuration.database
	directory = configuration.outputs.csv.parent
	if options.directory is not None:
		directory = options.directory
	try:
		with open_connection(database.socket, database.production, Role.PLAYBACK) as connection:
			result = simulate(
				connection,
				directory,
				start,
				end,
				options.seed,
				options.name,
				configuration.metadata,
				configuration.crossfades,
			)
	except psycopg.OperationalError as error:
		log.error(f"base de données injoignable ({database.production} par {database.socket}) : {error}")
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(f"erreur de base de données : {error}")
		return FAILURE_CODE
	except OSError as error:
		log.error(f"sorties de la simulation impossibles à écrire : {error}")
		return FAILURE_CODE
	anomalies = sum(1 for level, _, _ in result.log if level != "info")
	name = (options.name) or (default_name(start, end))
	log.info(
		f"simulation {name} : {len(result.plays)} passage(s), {anomalies} alerte(s) ou incident(s),"
		" rien n'a été écrit en base"
	)
	for path in (result.files) or (()):
		log.info(f"sortie : {path}")
	return 0


def run_broadcast(configuration: Configuration) -> int:
	database = configuration.database
	audio = configuration.audio
	if audio.to_fill_in_on_air():
		# Le périphérique par défaut pourrait être celui de la pré-écoute, ou changer avec un branchement.
		log.error(
			f"périphérique de l'antenne non renseigné : le donner dans audio.device de {configuration.path},"
			" ou dans Fichier → Préférences… de Machin interface, page Audio"
		)
		return INVALID_CONFIGURATION_CODE
	stop = install_stop()
	try:
		with open_connection(database.socket, database.production, Role.PLAYBACK) as connection:
			engine = AudioEngine(configuration.audio, dead_air=configuration.dead_air)
			try:
				on_air_output, on_air_device = audio.on_air()
				device = ""
				if on_air_device is not None:
					device = f", périphérique {on_air_device}"
				log.info(
					f"diffusion sur la sortie {on_air_output}{device},"
					f" configuration {configuration.path}, arrêt par Ctrl-C ou SIGTERM"
				)
				broadcast = Broadcast(
					connection,
					engine,
					SystemClock(),
					create_randomness(None),
					outputs=Outputs.since(configuration),
					state=StateSocket(configuration.player.state_socket),
					crossfades=configuration.crossfades,
					analyser=Analyser(analysis_command(configuration.path)),
					dead_air=configuration.dead_air,
				)
				air(broadcast, stop)
			finally:
				engine.shut_down()
	except psycopg.OperationalError as error:
		log.error(f"base de données injoignable ({database.production} par {database.socket}) : {error}")
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(f"erreur de base de données : {error}")
		return FAILURE_CODE
	except BusyStateSocket as error:
		log.error(f"diffusion refusée : {error}")
		return FAILURE_CODE
	except UnavailableAudioOutput as error:
		log.error(f"sortie audio indisponible : {error}")
		return FAILURE_CODE
	log.info("diffusion arrêtée")
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, own_options)


if __name__ == "__main__":
	raise SystemExit(main())
