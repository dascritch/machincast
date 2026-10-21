"""Machin lecture --simulation sur la base de test, pour l'écran de simulation de l'interface
(https://github.com/dascritch/machincast/issues/37, tests/test_simulation_interface.py).

Machin lecture simule sur la base de production de sa configuration ; celle des tests est volontairement
inexistante (tests/configuration-test.toml). Ce programme analyse les mêmes arguments que Machin lecture, et exécute
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

from machincast.cli import lancer
from machincast.configuration import Configuration
from machincast.lecture import __main__ as lecture

SANS_BASE = "--sans-base"
ATTEND = "--attend"
ECHOUE = "--echoue"
AUCUNE_SOCKET = Path("/nonexistent/machincast-aucune-socket")


def main(arguments: list[str]) -> int:
	sans_base = SANS_BASE in arguments[:1]
	if sans_base:
		arguments = arguments[1:]
	if ATTEND in arguments[:1]:
		fin = Path(arguments[1])
		arguments = arguments[2:]
		while not fin.exists():
			time.sleep(0.05)
	echoue = ECHOUE in arguments[:1]
	if echoue:
		arguments = arguments[1:]

	def executer(configuration: Configuration, options: argparse.Namespace) -> int:
		base = dataclasses.replace(configuration.base, production=configuration.base.test)
		if sans_base:
			base = dataclasses.replace(base, socket=AUCUNE_SOCKET)
		code = lecture.executer(dataclasses.replace(configuration, base=base), options)
		if not echoue:
			return code
		lecture.journal.error("premier échec")
		lecture.journal.error("dernier échec")
		return 1

	return lancer(lecture.EXECUTABLE, lecture.DESCRIPTION, arguments, executer, lecture.options_propres)


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
