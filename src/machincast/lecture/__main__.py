"""Point d'entrée de Machin_lecture."""

from collections.abc import Sequence

from machincast.cli import creer_analyseur, non_implemente

EXECUTABLE = "Machin_lecture"


def main(arguments: Sequence[str] | None = None) -> int:
	analyseur = creer_analyseur(
		EXECUTABLE,
		"Lit les événements programmés et les diffuse sur la sortie audio configurée.",
	)
	analyseur.parse_args(arguments)
	return non_implemente(EXECUTABLE, 12)


if __name__ == "__main__":
	raise SystemExit(main())
