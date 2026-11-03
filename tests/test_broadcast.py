"""Étapes de la boucle de diffusion de Machin player (https://github.com/dascritch/machincast/issues/88).

Les étapes communes aux scénarios de la diffusion sont dans tests/broadcast_steps.py.
"""

import shutil
import signal
import subprocess
import sys
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.player.broadcast import install_stop
from tests.broadcast_steps import Connection
from tests.database_fixtures import CONFIGURATION_TEST

scenarios("broadcast.feature")


@dataclass
class Process:
	stop: threading.Event | None = None
	result: subprocess.CompletedProcess[str] | None = None


@pytest.fixture
def process() -> Process:
	return Process()


@then(
	parsers.parse(
		"chaque passage de « {first} » et de « {second} » note la séquence « {name} » et son élément, au début"
		" comme à la fin"
	)
)
def sequence_plays(empty_database: Connection, first: str, second: str, name: str) -> None:
	lines = empty_database.execute(
		"SELECT a.title, a.line_type::text, q.internal_name, e.position FROM airplay a"
		" LEFT JOIN sequences q ON q.id = a.sequence_id"
		" LEFT JOIN sequence_items e ON e.id = a.sequence_item_id AND e.sequence_id = a.sequence_id"
		" WHERE a.title IN (%s, %s) ORDER BY a.id",
		(first, second),
	).fetchall()
	positions = {first: 1, second: 2}
	assert len(lines) == 6, lines
	assert all((sequence == name) and (position == positions[str(title)]) for title, _, sequence, position in lines), (
		lines
	)
	assert {line_type for _, line_type, _, _ in lines} == {"start", "end"}, lines


@given("l'arrêt de la diffusion branché sur les signaux")
def plugged_stop(process: Process) -> Iterator[None]:
	old_list = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
	process.stop = install_stop()
	yield
	for number, old in old_list.items():
		signal.signal(number, old)


@when("le processus reçoit SIGTERM")
def sigterm() -> None:
	# raise_signal le délivre au fil principal, aussitôt : jamais à un fil de GStreamer, ni après la restauration
	# des gestionnaires d'origine, qui arrêterait pytest.
	signal.raise_signal(signal.SIGTERM)


@when("je lance Machin_player avec une configuration dont la socket n'existe pas")
def launch_without_database(process: Process, tmp_path: Path) -> None:
	configuration = tmp_path / "sans-base.toml"
	text = CONFIGURATION_TEST.read_text(encoding="utf-8")
	configuration.write_text(
		text.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'), encoding="utf-8"
	)
	path = (shutil.which("Machin_player")) or (str(Path(sys.executable).parent / "Machin_player"))
	process.result = subprocess.run([path, "--config", str(configuration)], capture_output=True, text=True, timeout=60)


@then("l'arrêt de la diffusion est demandé")
def requested_stop(process: Process) -> None:
	assert (process.stop is not None) and (process.stop.wait(2))


@then("il s'arrête avec le code 1, en signalant la base de données injoignable")
def code(process: Process) -> None:
	assert process.result is not None
	assert process.result.returncode == 1, process.result.stderr
	assert "base de données injoignable" in process.result.stderr


@when(parsers.parse("je lance Machin_player sur la sortie « {output} », sans périphérique d'antenne"))
def launch_without_on_air(process: Process, tmp_path: Path, output: str) -> None:
	"""La configuration des tests n'a pas de périphérique d'antenne : sa sortie factice n'en demande pas."""
	configuration = tmp_path / "sans-antenne.toml"
	text = CONFIGURATION_TEST.read_text(encoding="utf-8")
	assert "device =" not in text
	configuration.write_text(text.replace('output = "dummy"', f'output = "{output}"'), encoding="utf-8")
	path = (shutil.which("Machin_player")) or (str(Path(sys.executable).parent / "Machin_player"))
	process.result = subprocess.run([path, "--config", str(configuration)], capture_output=True, text=True, timeout=60)


@then(parsers.parse("il s'arrête avec le code {code:d}, en signalant « {text} »"))
def code_and_message(process: Process, code: int, text: str) -> None:
	assert process.result is not None
	assert process.result.returncode == code, process.result.stderr
	assert text in process.result.stderr, process.result.stderr
