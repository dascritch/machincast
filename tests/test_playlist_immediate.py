"""Scénarios de la playlist immédiate du binaire lecture (https://github.com/dascritch/machincast/issues/228).

La diffusion tourne sur le moteur simulé (tests/broadcast_steps.py, RecordingSimulatedEngine), qui suit l'horloge du
binaire. Les sonores à venir se lisent dans la diffusion : la socket d'état les publie (tests/test_state.py).
"""

from pathlib import Path

from pytest_bdd import parsers, scenarios, then, when

from tests.broadcast_steps import Bench, Connection, plays, sound_show

scenarios("playlist_immediate.feature")


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le sonore « {name} » est désactivé"))
def disable(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE sounds SET state = 'disabled' WHERE title = %s", (name,))


@when(parsers.parse("le fichier de test du sonore « {name} » disparaît"))
def disappeared_file(bench: Bench, name: str) -> None:
	"""La copie de test du fichier, dans le répertoire temporaire du scénario, est effacée par le test lui-même."""
	bench.files[name].unlink()


@when(
	parsers.re(
		r"(?P<category>l'émission|le spécial) « (?P<name>[^»]+) » de (?P<start>[\d:]+) à (?P<end>[\d:]+),"
		r" avec les sonores (?P<sound_list>.+), est ajoutée? à la grille"
	)
)
def add_to_grid(
	bench: Bench,
	empty_database: Connection,
	tmp_path: Path,
	category: str,
	name: str,
	start: str,
	end: str,
	sound_list: str,
) -> None:
	sound_show(bench, empty_database, tmp_path, category, name, start, end, sound_list)


# ─── Alors ─────────────────────────────────────────────────


@then("les passages, à partir du deuxième, sont les sonores notés")
def engaged_list(empty_database: Connection, notes: list[str]) -> None:
	played_list = []
	for p in plays(empty_database):
		played_list.append(p[0])
	assert len(notes) == 6, notes
	assert played_list[1 : 1 + len(notes)] == notes, (played_list, notes)
