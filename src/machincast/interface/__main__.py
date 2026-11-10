"""Point d'entrée de Machin_interface (https://github.com/dascritch/machincast/issues/23).

Se connecte à la base de production avec le rôle de l'interface, puis ouvre sa fenêtre à onglets, sur l'écran par
défaut (https://github.com/dascritch/machincast/issues/26). Sans base joignable, s'arrête avec le code 1, après une
fenêtre d'erreur qui renvoie à INSTALL.md quand un affichage graphique peut la montrer.
"""

import argparse
import logging
import os
from collections.abc import Mapping, Sequence

import psycopg

from machincast import audio
from machincast.cli import launch
from machincast.clock import SystemClock
from machincast.configuration import PROJECT_DIRECTORY, Configuration
from machincast.database import Role, open_connection
from machincast.i18n import _

EXECUTABLE = "Machin_interface"
DESCRIPTION = _("MachinCast graphical interface, for supervision and programming.")

FAILURE_CODE = 1

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
log = logging.getLogger("machincast.interface")


INVISIBLE_PLATFORMS = frozenset({"offscreen", "minimal"})
"""Plateformes Qt qui ne montrent rien à personne, comme celle des tests."""


def available_display(environment: Mapping[str, str] = os.environ) -> bool:
	"""Une fenêtre peut-elle être vue ? Pas sans affichage graphique, par exemple dans une session SSH, où Qt
	s'arrêterait net, ni sur une plateforme Qt invisible."""
	platform = environment.get("QT_QPA_PLATFORM", "")
	if platform in INVISIBLE_PLATFORMS:
		return False
	return (platform != "") or (environment.get("DISPLAY", "") != "") or (environment.get("WAYLAND_DISPLAY", "") != "")


def flag_database(configuration: Configuration, error: psycopg.Error) -> None:
	"""Sans base, une fenêtre d'erreur explique pourquoi l'interface n'est pas utilisable."""
	if not available_display():
		return
	from machincast.interface.application import application
	from machincast.interface.error import UnreachableDatabaseWindow

	# L'application doit exister tant que la fenêtre est montrée.
	qt = application(EXECUTABLE)
	database = configuration.database
	window = UnreachableDatabaseWindow(
		database.production, database.socket, str(error), PROJECT_DIRECTORY / "INSTALL.md"
	)
	window.display()
	qt.processEvents()


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	audio.identify(audio.PREVIEW, EXECUTABLE)
	database = configuration.database
	try:
		connection = open_connection(database.socket, database.production, Role.INTERFACE)
	except psycopg.OperationalError as error:
		log.error(
			_("database unreachable ({production} through {socket}): {error}").format(
				production=database.production, socket=database.socket, error=error
			)
		)
		flag_database(configuration, error)
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(_("database error: {error}").format(error=error))
		flag_database(configuration, error)
		return FAILURE_CODE
	with connection:
		# PySide6 n'est importé qu'ici : l'aide et les erreurs de configuration ou de base restent disponibles sans
		# affichage graphique.
		from machincast.interface.application import application
		from machincast.interface.indexer import indexing_command
		from machincast.interface.window import MainWindow

		qt = application(EXECUTABLE)
		window = MainWindow(
			connection,
			configuration.player.state_socket,
			SystemClock(),
			indexing_command=indexing_command(options.config),
			configuration=configuration.path,
			crossfades=configuration.crossfades,
			audio=configuration.audio,
			silences=configuration.silences,
			interface=configuration.interface,
			retention=configuration.database.retention,
			dead_air=configuration.dead_air,
		)
		window.show()
		window.offer_to_launching()
		return qt.exec()


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run)


if __name__ == "__main__":
	raise SystemExit(main())
