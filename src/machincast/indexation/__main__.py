"""Point d'entrée de Machin_indexation."""

from collections.abc import Sequence

from machincast.cli import creer_analyseur, non_implemente

EXECUTABLE = "Machin_indexation"


def main(arguments: Sequence[str] | None = None) -> int:
	analyseur = creer_analyseur(
		EXECUTABLE,
		"Vérifie les sonores et indexe les répertoires des banques.",
	)
	analyseur.parse_args(arguments)
	return non_implemente(EXECUTABLE, 7)


if __name__ == "__main__":
	raise SystemExit(main())
