"""Point d'entrée de Machin_indexation."""

from collections.abc import Sequence

from machincast.cli import lancer, non_implemente
from machincast.configuration import Configuration

EXECUTABLE = "Machin_indexation"
DESCRIPTION = "Vérifie les sonores et indexe les répertoires des banques."


def executer(configuration: Configuration) -> int:
	return non_implemente(EXECUTABLE, 7)


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer)


if __name__ == "__main__":
	raise SystemExit(main())
