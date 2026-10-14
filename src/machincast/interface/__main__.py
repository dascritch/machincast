"""Point d'entrée de Machin_interface."""

from collections.abc import Sequence

from machincast.cli import creer_analyseur, non_implemente

EXECUTABLE = "Machin_interface"


def main(arguments: Sequence[str] | None = None) -> int:
	analyseur = creer_analyseur(
		EXECUTABLE,
		"Interface graphique de supervision et de programmation de MachinCast.",
	)
	analyseur.parse_args(arguments)
	# PySide6 sera importé ici, après l'analyse des arguments : l'aide reste disponible sans affichage graphique.
	return non_implemente(EXECUTABLE, 23)


if __name__ == "__main__":
	raise SystemExit(main())
