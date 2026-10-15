"""Point d'entrée de Machin_lecture."""

import argparse
from collections.abc import Sequence

from machincast.cli import lancer, non_implemente
from machincast.configuration import Configuration

EXECUTABLE = "Machin_lecture"
DESCRIPTION = "Lit les événements programmés et les diffuse sur la sortie audio configurée."


def executer(configuration: Configuration, options: argparse.Namespace) -> int:
	return non_implemente(EXECUTABLE, 12)


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer)


if __name__ == "__main__":
	raise SystemExit(main())
