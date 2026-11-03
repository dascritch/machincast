"""Machin player --simulation sur la base de test, pour l'écran de simulation de l'interface
(https://github.com/dascritch/machincast/issues/37, tests/test_simulation_interface.py).

Machin player simule sur la base de production de sa configuration ; celle des tests est volontairement
inexistante (tests/configuration-test.toml). Ce programme analyse les mêmes arguments que Machin player, et exécute
la même simulation, mais sur la base de test : jamais sur une base de production. Avec --sans-base en premier
argument, la socket de PostgreSQL est inexistante : la base est injoignable. Avec --attend FICHIER, le programme
attend que le fichier existe avant de simuler : la simulation est en cours tant qu'il n'existe pas. Avec --echoue, il
signale deux erreurs après avoir simulé et écrit ses sorties, puis s'arrête avec le code 1.
"""

import argparse
import dataclasses
import sys
import time
from pathlib import Path

from machincast.cli import launch
from machincast.configuration import Configuration
from machincast.player import __main__ as playback

WITHOUT_DATABASE = "--sans-base"
WAITING = "--attend"
FAILED = "--echoue"
NO_SOCKET = Path("/nonexistent/machincast-aucune-socket")


def main(arguments: list[str]) -> int:
	without_database = WITHOUT_DATABASE in arguments[:1]
	if without_database:
		arguments = arguments[1:]
	if WAITING in arguments[:1]:
		end = Path(arguments[1])
		arguments = arguments[2:]
		while not end.exists():
			time.sleep(0.05)
	failed = FAILED in arguments[:1]
	if failed:
		arguments = arguments[1:]

	def run(configuration: Configuration, options: argparse.Namespace) -> int:
		database = dataclasses.replace(configuration.database, production=configuration.database.test)
		if without_database:
			database = dataclasses.replace(database, socket=NO_SOCKET)
		code = playback.run(dataclasses.replace(configuration, database=database), options)
		if not failed:
			return code
		playback.log.error("premier échec")
		playback.log.error("dernier échec")
		return 1

	return launch(playback.EXECUTABLE, playback.DESCRIPTION, arguments, run, playback.own_options)


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
