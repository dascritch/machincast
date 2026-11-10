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

from machincast import audio, crash
from machincast.audio import UnavailableAudioOutput
from machincast.cli import INVALID_CONFIGURATION_CODE, launch
from machincast.clock import SystemClock
from machincast.configuration import Configuration
from machincast.database import Role, open_connection
from machincast.i18n import _, counted
from machincast.player import virtual_card
from machincast.player.analysis import Analyser, analysis_command
from machincast.player.broadcast import Broadcast, air, install_stop
from machincast.player.engine import AudioEngine
from machincast.player.outputs import Outputs
from machincast.player.simulation import default_name, simulate
from machincast.player.state import BusyStateSocket, StateSocket
from machincast.randomness import create_randomness
from machincast.runs import Recording

EXECUTABLE = "Machin_player"
DESCRIPTION = _("Reads the programmed events and broadcasts them on the configured audio output.")

FAILURE_CODE = 1
ON_AIR_CARD = _("On-air sound card")
WPCTL_STATUS = "wpctl status"
"""Les rubriques des rapports de crash de Machin player, avec les sonores de l'antenne
(machincast.player.broadcast.SOUNDS_ON_AIR, https://github.com/dascritch/machincast/issues/342)."""
RECORDING = Recording(role=Role.PLAYBACK, when=lambda options: options.simulation is None)
"""Le démarrage et la fin de la diffusion, au journal et au log de la base, comme les autres binaires, avec le plantage
probable du lancement précédent (https://github.com/dascritch/machincast/issues/342) ; pas la simulation, qui n'écrit
rien en base."""

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
log = logging.getLogger("machincast.player")


def instant(text: str) -> datetime:
	"""Date et heure ISO 8601, en heure du poste : « 2026-10-20 20:00 » ou « 2026-10-20T20:00:00 »."""
	try:
		return datetime.fromisoformat(text).astimezone()
	except ValueError:
		raise argparse.ArgumentTypeError(
			_("invalid date: “{text}”, expected for instance “2026-10-20 20:00”").format(text=text)
		) from None


def output_name(text: str) -> str:
	if (not text) or ("/" in text) or (text.startswith(".")):
		raise argparse.ArgumentTypeError(
			_("invalid name: “{text}”, without “/” and without a dot at the start").format(text=text)
		)
	return text


def own_options(analyser: argparse.ArgumentParser) -> None:
	simulation = analyser.add_argument_group(_("simulation (https://github.com/dascritch/machincast/issues/21)"))
	simulation.add_argument(
		"--simulation",
		nargs=2,
		type=instant,
		metavar=("DEBUT", "FIN"),
		help=_(
			"simulates the broadcast between these two dates and times, without sound and without "
			"writing to the database"
		),
	)
	simulation.add_argument("--seed", type=int, metavar="N", help=_("random seed, for a reproducible result"))
	simulation.add_argument(
		"--name",
		type=output_name,
		metavar="NOM",
		help=_("name of the .csv, .pls and .html outputs of the simulation (by default: simulation-START-END)"),
	)
	simulation.add_argument(
		"--directory",
		type=Path,
		metavar="REPERTOIRE",
		help=_("directory of the outputs of the simulation (by default: the one of outputs.csv of the configuration)"),
	)


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	audio.identify(audio.ON_AIR, EXECUTABLE)
	if options.simulation is not None:
		return run_simulation(configuration, options)
	if (options.seed is not None) or (options.name is not None) or (options.directory is not None):
		log.error(_("--seed, --name and --directory are only used with --simulation"))
		return INVALID_CONFIGURATION_CODE
	return run_broadcast(configuration)


def run_simulation(configuration: Configuration, options: argparse.Namespace) -> int:
	start, end = options.simulation
	if end <= start:
		log.error(_("invalid simulation period: the end must follow the start"))
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
		log.error(
			_("database unreachable ({production} through {socket}): {error}").format(
				production=database.production, socket=database.socket, error=error
			)
		)
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(_("database error: {error}").format(error=error))
		return FAILURE_CODE
	except OSError as error:
		log.error(_("outputs of the simulation impossible to write: {error}").format(error=error))
		return FAILURE_CODE
	anomalies = 0
	for level, *_details in result.log:
		if level != "info":
			anomalies += 1
	name = (options.name) or (default_name(start, end))
	log.info(
		_("simulation {name}: {plays}, {anomalies}, nothing was written to the database").format(
			name=name,
			plays=counted("{count} play", "{count} plays", len(result.plays)),
			anomalies=counted("{count} alert or incident", "{count} alerts or incidents", anomalies),
		)
	)
	for path in (result.files) or (()):
		log.info(_("output: {path}").format(path=path))
	return 0


def run_broadcast(configuration: Configuration) -> int:
	database = configuration.database
	audio = configuration.audio
	if audio.to_fill_in_on_air():
		# Le périphérique par défaut pourrait être celui de la pré-écoute, ou changer avec un branchement.
		log.error(
			_(
				"on-air device not filled in: give it in audio.device of {path}, or in File → Preferences… "
				"of Machin interface, Audio page"
			).format(path=configuration.path)
		)
		return INVALID_CONFIGURATION_CODE
	stop = install_stop()
	try:
		with (
			open_connection(database.socket, database.production, Role.PLAYBACK) as connection,
			virtual_card.on_air(audio) as played,
		):
			engine = AudioEngine(played, dead_air=configuration.dead_air)
			try:
				on_air_output, on_air_device = played.on_air()
				device = ""
				if on_air_device is not None:
					device = _(", device {on_air_device}").format(on_air_device=on_air_device)
				log.info(
					_(
						"broadcast on output {on_air_output}{device}, configuration {path}, stop with Ctrl-C or SIGTERM"
					).format(on_air_output=on_air_output, device=device, path=configuration.path)
				)
				# Pour un rapport de crash (https://github.com/dascritch/machincast/issues/342).
				crash.note(
					ON_AIR_CARD,
					_("output {output}, device {device}").format(output=on_air_output, device=on_air_device),
				)
				crash.provide(WPCTL_STATUS, crash.wpctl_status)
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
		log.error(
			_("database unreachable ({production} through {socket}): {error}").format(
				production=database.production, socket=database.socket, error=error
			)
		)
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(_("database error: {error}").format(error=error))
		return FAILURE_CODE
	except BusyStateSocket as error:
		log.error(_("broadcast refused: {error}").format(error=error))
		return FAILURE_CODE
	except UnavailableAudioOutput as error:
		log.error(_("audio output unavailable: {error}").format(error=error))
		return FAILURE_CODE
	log.info(_("broadcast stopped"))
	return 0


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, own_options, recording=RECORDING)


if __name__ == "__main__":
	raise SystemExit(main())
