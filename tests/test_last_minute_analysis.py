"""Scénarios de l'analyse du prochain sonore au dernier moment (https://github.com/dascritch/machincast/issues/181).

Les étapes de la diffusion sont dans tests/broadcast_steps.py. Machin indexer y est remplacé par un script, qui
note ses arguments un par ligne, ou plante ; le dernier scénario lance le vrai, sur la base de test.
"""

import os
import re
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
from pytest_bdd import given, parsers, scenarios, then

from machincast.configuration import SILENCE_THRESHOLD
from machincast.player.analysis import Analyser, analysis_command
from tests.broadcast_steps import Bench, event, hour, sound
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
	calls = []
	for block in text.split("--\n"):
		if block.strip():
			calls.append(block.strip().splitlines())
	return calls


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le sonore « {name} » a été vérifié en entier"))
def checks(empty_database: Connection, name: str) -> None:
	"""Un audit complet, après la dernière modification du fichier, qui a mesuré son niveau
	(https://github.com/dascritch/machincast/issues/642)."""
	now = datetime.now(UTC)
	empty_database.execute(
		"UPDATE sounds SET checked_at = %s, audited_at = %s, audit_threshold = %s, properties = properties"
		' || \'{"loudness": {"integrated": -20.0, "peak": -1.0}}\'::jsonb WHERE id = %s',
		(now, now, SILENCE_THRESHOLD, sound(empty_database, name)),
	)


@given(parsers.parse("le sonore « {name} » a été vérifié en entier, avant la mesure du niveau"))
def checks_unmeasured(empty_database: Connection, name: str) -> None:
	"""Un audit complet d'avant la mesure du niveau (https://github.com/dascritch/machincast/issues/646)."""
	now = datetime.now(UTC)
	empty_database.execute(
		"UPDATE sounds SET checked_at = %s, audited_at = %s, audit_threshold = %s WHERE id = %s",
		(now, now, SILENCE_THRESHOLD, sound(empty_database, name)),
	)


@given(parsers.parse("le sonore « {name} » a été vérifié par une indexation rapide seulement"))
def quick_checks(empty_database: Connection, name: str) -> None:
	"""Décodé, mais sans audit complet : pas de date d'audit (https://github.com/dascritch/machincast/issues/401)."""
	empty_database.execute(
		"UPDATE sounds SET checked_at = %s, audited_at = NULL, audit_threshold = NULL WHERE id = %s",
		(datetime.now(UTC), sound(empty_database, name)),
	)


@given(parsers.parse("le sonore « {name} » a été audité avant la dernière modification de son fichier"))
def audited_before(empty_database: Connection, name: str) -> None:
	"""La date de modification et la taille enregistrées sont celles du fichier, mais l'audit date d'avant."""
	identifier = sound(empty_database, name)
	line = empty_database.execute("SELECT file_modified_at FROM sounds WHERE id = %s", (identifier,)).fetchone()
	assert (line is not None) and (isinstance(line[0], datetime))
	before = line[0] - timedelta(minutes=5)
	empty_database.execute(
		"UPDATE sounds SET checked_at = %s, audited_at = %s, audit_threshold = %s WHERE id = %s",
		(before, before, SILENCE_THRESHOLD, identifier),
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


@given(parsers.parse("une commande d'analyse imitée, qui dure {seconds:d} secondes"), target_fixture="analysis_log")
def slow(bench: Bench, tmp_path: Path, seconds: int) -> Path:
	"""Comme la commande imitée, qui note ses arguments, puis tourne encore : deux analyses à la fois, au plus."""
	log = fake(bench, tmp_path)
	script = tmp_path / "Machin_indexer"
	script.write_text(IMITATION.replace("{journal}", str(log)) + f"sleep {seconds}\n", encoding="utf-8")
	return log


@given(
	parsers.re(
		r"l'émission « (?P<name>[^»]+) » de (?P<start>[\d:]+) à (?P<end>[\d:]+), le lendemain, avec le sonore"
		r" « (?P<sound_name>[^»]+) »"
	)
)
def next_day_show(
	bench: Bench, empty_database: Connection, tmp_path: Path, name: str, start: str, end: str, sound_name: str
) -> None:
	event(
		bench,
		empty_database,
		tmp_path,
		name,
		"show",
		hour(f"2026-10-15 {start}"),
		hour(f"2026-10-15 {end}"),
		[sound_name],
	)


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


@then(
	parsers.re(
		r"les analyses sont demandées bientôt pour les sonores « (?P<first>[^»]+) », « (?P<second>[^»]+) »,"
		r" et pas encore pour « (?P<third>[^»]+) »"
	)
)
def requested_two(empty_database: Connection, analysis_log: Path, first: str, second: str, third: str) -> None:
	expected = []
	for name in (first, second):
		expected.append(["--full-audit", "--sound", str(sound(empty_database, name))])
	assert wait(lambda: len(calls(analysis_log)) >= 2), calls(analysis_log)
	assert sorted(calls(analysis_log)) == sorted(expected)
	unexpected = ["--full-audit", "--sound", str(sound(empty_database, third))]
	assert unexpected not in calls(analysis_log)


@then(parsers.parse("les analyses sont demandées, dans l'ordre, pour les sonores {names}"))
def requested_in_order(empty_database: Connection, analysis_log: Path, names: str) -> None:
	expected = []
	for name in re.findall(r"« ([^»]+) »", names):
		expected.append(["--full-audit", "--sound", str(sound(empty_database, name))])
	assert wait(lambda: len(calls(analysis_log)) >= len(expected)), calls(analysis_log)
	assert calls(analysis_log) == expected


@then("aucune analyse n'a été demandée")
def no(analysis_log: Path) -> None:
	assert calls(analysis_log) == []


@then(parsers.parse("le sonore « {name} » a bientôt sa date de vérification complète, et sa date d'audit"))
def checks_soon(empty_database: Connection, name: str) -> None:
	identifier = sound(empty_database, name)

	def dates() -> tuple[object, ...]:
		line = empty_database.execute(
			"SELECT checked_at, audited_at FROM sounds WHERE id = %s", (identifier,)
		).fetchone()
		assert line is not None
		return tuple(line)

	assert wait(lambda: None not in dates()), "le sonore n'a pas été audité"
	for date in dates():
		assert isinstance(date, datetime)
		assert datetime.now(UTC) - date < timedelta(seconds=DELAY)


@then("l'analyse tourne dans sa propre session, à l'abri d'un Ctrl-C dans le terminal de la diffusion")
def own_session(analysis_log: Path) -> None:
	session = analysis_log.with_name(f"{analysis_log.name}.session")
	assert wait(session.exists)
	assert int(session.read_text(encoding="utf-8")) != os.getsid(0)
