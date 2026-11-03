"""Scénarios de l'analyse du prochain sonore au dernier moment (https://github.com/dascritch/machincast/issues/181).

Les étapes de la diffusion sont dans tests/broadcast_steps.py. Machin indexer y est remplacé par un script, qui
note ses arguments un par ligne, ou plante ; le dernier scénario lance le vrai, sur la base de test.
"""

import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
from pytest_bdd import given, parsers, scenarios, then

from machincast.player.analysis import Analyser, analysis_command
from tests.broadcast_steps import Bench, sound
from tests.database_fixtures import configuration_test

scenarios("last_minute_analysis.feature")

Connection = psycopg.Connection[tuple[object, ...]]
DELAY = 20.0
"""Secondes laissées à une analyse lancée pour se faire : le vrai Machin indexer charge GStreamer."""
IMITATION = """#!/bin/sh
cut -d ' ' -f 6 /proc/$$/stat > "{journal}.session"
for argument in "$@"; do
	echo "${argument}"
done >> "{journal}"
echo -- >> "{journal}"
"""
"""Machin indexer imité : chaque appel note ses arguments, un par ligne, puis « -- », et sa session."""


def wait(condition: object, delay: float = DELAY) -> bool:
	"""Vrai dès que la condition, une fonction sans argument, est remplie ; faux au bout du délai."""
	assert callable(condition)
	end = time.monotonic() + delay
	while time.monotonic() < end:
		if condition():
			return True
		time.sleep(0.05)
	return bool(condition())


def calls(log: Path) -> list[list[str]]:
	if not log.exists():
		return []
	text = log.read_text(encoding="utf-8")
	return [block.strip().splitlines() for block in text.split("--\n") if block.strip()]


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le sonore « {name} » a été vérifié en entier"))
def checks(empty_database: Connection, name: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET checked_at = %s WHERE id = %s", (datetime.now(UTC), sound(empty_database, name))
	)


@given(parsers.parse("le fichier du sonore « {name} » a changé depuis sa vérification"))
def changed_file(empty_database: Connection, name: str) -> None:
	"""La taille enregistrée n'est plus celle du fichier : il a été remplacé depuis sa vérification."""
	empty_database.execute("UPDATE sounds SET file_size = file_size + 1 WHERE id = %s", (sound(empty_database, name),))


@given("une commande d'analyse imitée", target_fixture="analysis_log")
def fake(bench: Bench, tmp_path: Path) -> Path:
	log = tmp_path / "analyses.txt"
	script = tmp_path / "Machin_indexer"
	script.write_text(IMITATION.replace("{journal}", str(log)), encoding="utf-8")
	script.chmod(0o755)
	bench.analyser = Analyser([str(script), "--full-audit", "--sound"])
	return log


@given("une commande d'analyse introuvable")
def not_found(bench: Bench, tmp_path: Path) -> None:
	bench.analyser = Analyser([str(tmp_path / "absent" / "Machin_indexer"), "--sound"])


@given("une commande d'analyse qui plante")
def crashes(bench: Bench, tmp_path: Path) -> None:
	script = tmp_path / "Machin_indexer"
	script.write_text("#!/bin/sh\necho 'plantage imité' >&2\nexit 1\n", encoding="utf-8")
	script.chmod(0o755)
	bench.analyser = Analyser([str(script), "--sound"])


@given("Machin indexer comme commande d'analyse, sur la base de test")
def indexing_machin_true(bench: Bench, tmp_path: Path) -> None:
	"""La configuration des tests, recopiée avec la base de test comme base de production : sa base de test, qui doit
	en différer, en devient une autre, que Machin indexer n'ouvre pas."""
	source = configuration_test()
	text = (
		source.path.read_text(encoding="utf-8")
		.replace(f'test = "{source.database.test}"', f'test = "{source.database.test}_inutilisee"')
		.replace(f'production = "{source.database.production}"', f'production = "{source.database.test}"')
	)
	assert f'production = "{source.database.test}"' in text
	configuration = tmp_path / "machincast.toml"
	configuration.write_text(text, encoding="utf-8")
	command = analysis_command(configuration)
	assert command[:3] == [sys.executable, "-m", "machincast.indexer"]
	bench.analyser = Analyser(command)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("l'analyse est demandée bientôt pour le sonore « {name} », en audit complet"))
def requested(empty_database: Connection, analysis_log: Path, name: str) -> None:
	expected = ["--full-audit", "--sound", str(sound(empty_database, name))]
	assert wait(lambda: calls(analysis_log) != []), "aucune analyse lancée"
	assert calls(analysis_log) == [expected]


@then("aucune analyse n'a été demandée")
def no(analysis_log: Path) -> None:
	assert calls(analysis_log) == []


@then(parsers.parse("le sonore « {name} » a bientôt sa date de vérification complète"))
def checks_soon(empty_database: Connection, name: str) -> None:
	identifier = sound(empty_database, name)

	def checks_at() -> object:
		line = empty_database.execute("SELECT checked_at FROM sounds WHERE id = %s", (identifier,)).fetchone()
		assert line is not None
		return line[0]

	assert wait(lambda: checks_at() is not None), "le sonore n'a pas été vérifié"
	date = checks_at()
	assert isinstance(date, datetime)
	assert datetime.now(UTC) - date < timedelta(seconds=DELAY)


@then("l'analyse tourne dans sa propre session, à l'abri d'un Ctrl-C dans le terminal de la diffusion")
def own_session(analysis_log: Path) -> None:
	session = analysis_log.with_name(f"{analysis_log.name}.session")
	assert wait(session.exists)
	assert int(session.read_text(encoding="utf-8")) != os.getsid(0)
