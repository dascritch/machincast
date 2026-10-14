"""Point d'entrée de Machin_interface."""

from collections.abc import Sequence

from machincast.cli import lancer, non_implemente
from machincast.configuration import Configuration

EXECUTABLE = "Machin_interface"
DESCRIPTION = "Interface graphique de supervision et de programmation de MachinCast."


def executer(configuration: Configuration) -> int:
	# PySide6 sera importé ici, après l'analyse des arguments : l'aide reste disponible sans affichage graphique.
	return non_implemente(EXECUTABLE, 23)


def main(arguments: Sequence[str] | None = None) -> int:
	return lancer(EXECUTABLE, DESCRIPTION, arguments, executer)


if __name__ == "__main__":
	raise SystemExit(main())
