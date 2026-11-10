"""Étapes des scénarios des démarrages et fins des binaires dans le log
(https://github.com/dascritch/machincast/issues/341).

Chaque binaire se lance par son main, comme Machin le lance, sur la base de test désignée comme base de production
d'une configuration du scénario : le chargement de la configuration est remplacé par celle-ci, qu'un fichier refuserait.
"""

import dataclasses
import logging
import os
import subprocess
import time
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import __version__, cli, crash, maintenance, purge
from machincast.configuration import Configuration
from machincast.indexer import __main__ as indexer
from machincast.player import __main__ as player
from tests.database_fixtures import configuration_test
from tests.log_texts import shown

scenarios("run_log.feature")

PARIS = ZoneInfo("Europe/Paris")
Connection = psycopg.Connection[tuple[object, ...]]
BINARIES: dict[str, Callable[[list[str]], int]] = {
	"purge": purge.main,
	"indexer": indexer.main,
	"maintenance-db": maintenance.main,
	"player": player.main,
}


@dataclasses.dataclass
class Execution:
	configuration: Configuration
	directory: Path
	code: int = -1
	information: list[str] = dataclasses.field(default_factory=list)
	errors: list[str] = dataclasses.field(default_factory=list)
	old_pid: int | None = None
	end_before_staying_open: bool | None = None

	def text(self, text: str) -> str:
		text = text.replace("<version>", __version__).replace("<pid>", str(os.getpid()))
		text = text.replace("…/", f"{self.directory}/")
		if self.old_pid is not None:
			text = text.replace("<ancien pid>", str(self.old_pid))
		return text


@pytest.fixture
def running() -> Iterator[list[subprocess.Popen[bytes]]]:
	"""Les processus qui tournent encore pendant le scénario, arrêtés à sa fin."""
	processes: list[subprocess.Popen[bytes]] = []
	yield processes
	for process in processes:
		process.kill()
		process.wait()


@given("une configuration dont la base de production est la base de test", target_fixture="execution")
def configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_database: Connection) -> Execution:
	monkeypatch.setenv("TZ", "Europe/Paris")
	time.tzset()
	fetched = configuration_test()
	database = dataclasses.replace(fetched.database, production=fetched.database.test)
	chosen = dataclasses.replace(fetched, database=database, path=tmp_path / "machincast.toml")
	monkeypatch.setattr(cli, "load", lambda _path: chosen)
	return Execution(configuration=chosen, directory=tmp_path)


@given("une configuration dont la base de production est injoignable")
def unreachable(execution: Execution, monkeypatch: pytest.MonkeyPatch) -> None:
	database = dataclasses.replace(execution.configuration.database, socket=execution.directory / "sans-postgresql")
	chosen = dataclasses.replace(execution.configuration, database=database)
	monkeypatch.setattr(cli, "load", lambda _path: chosen)
	execution.configuration = chosen


def _note_start(connection: Connection, program: str, pid: int, instant: datetime | None) -> None:
	connection.execute(
		"INSERT INTO log (logged_at, level, kind, message)"
		" VALUES (COALESCE(%s, clock_timestamp()), 'info', 'start', %s)",
		(instant, f"{program} {__version__}, pid {pid}"),
	)


@given(
	parsers.parse("un démarrage de « {program} » noté le {day} à {hour} par un processus qui ne tourne plus, sans fin")
)
def dead_start(empty_database: Connection, execution: Execution, program: str, day: str, hour: str) -> None:
	finished = subprocess.Popen(["true"])
	finished.wait()
	execution.old_pid = finished.pid
	_note_start(empty_database, program, finished.pid, datetime.fromisoformat(f"{day} {hour}").replace(tzinfo=PARIS))


@given(parsers.parse("un démarrage de « {program} » noté à l'instant par un processus qui tourne encore, sans fin"))
def running_start(
	empty_database: Connection, execution: Execution, running: list[subprocess.Popen[bytes]], program: str
) -> None:
	process = subprocess.Popen(["sleep", "300"])
	running.append(process)
	execution.old_pid = process.pid
	_note_start(empty_database, program, process.pid, None)


@when(parsers.parse("je lance « {command} »"))
def launch(
	execution: Execution, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
	_machin, binary, *arguments = execution.text(command).split()

	def stay_open() -> None:
		"""À la place du terminal gardé ouvert : la fin est-elle déjà au log ?"""
		with psycopg.connect(
			host=str(execution.configuration.database.socket), dbname=execution.configuration.database.test
		) as connection:
			line = connection.execute("SELECT count(*) FROM log WHERE kind = 'end'").fetchone()
		execution.end_before_staying_open = (line is not None) and (line[0] == 1)

	monkeypatch.setattr(maintenance, "stay_open", stay_open)
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		execution.code = BINARIES[binary](arguments)
	information = []
	for record in caplog.records:
		if record.levelno == logging.INFO:
			information.append(record.getMessage())
	execution.information = information
	errors = []
	for record in caplog.records:
		if record.levelno >= logging.WARNING:
			errors.append(record.getMessage())
	execution.errors = errors


@then(parsers.parse("le lancement se termine avec le code {code:d}"))
def output_code(execution: Execution, code: int) -> None:
	assert execution.code == code, (execution.information, execution.errors)


@then(parsers.parse("le journal a noté « {text} »"))
def noted(execution: Execution, text: str) -> None:
	assert execution.text(text) in execution.information, execution.information


@then(parsers.parse("le journal a signalé « {text} »"))
def reported(execution: Execution, text: str) -> None:
	assert execution.text(text) in execution.errors, execution.errors


@then(parsers.parse("le journal a signalé que le démarrage de « {program} » n'a pas été noté dans la base"))
def start_not_noted(execution: Execution, program: str) -> None:
	start = f"{program} : démarrage non noté dans la base : "
	found = False
	for error in execution.errors:
		if error.startswith(start):
			found = True
			break
	assert found, execution.errors


def _lines(connection: Connection) -> list[tuple[str, str, str]]:
	lines = connection.execute("SELECT level::text, kind, message FROM log ORDER BY logged_at, id").fetchall()
	kind_list = []
	for level, kind, message in lines:
		kind_list.append((str(level), shown(kind), shown(message)))
	return kind_list


@then(
	parsers.parse("le log de la base a noté, au niveau info, le « {kind} » « {start} », puis la « {other} » « {end} »")
)
def start_and_end(
	empty_database: Connection, execution: Execution, kind: str, start: str, other: str, end: str
) -> None:
	"""Les lignes du démarrage et de la fin, sans celles du travail du binaire, comme le bilan de la purge."""
	lines = []
	for line in _lines(empty_database):
		if line[1] in (kind, other):
			lines.append(line)
	assert lines == [
		("info", kind, execution.text(start)),
		("info", other, execution.text(end)),
	]


@then(
	parsers.re(
		r"le log de la base a noté, au niveau (?P<level>\w+), (?:le|la) « (?P<kind>[^»]+) » "
		r"« (?P<text>[^»]+) »$"
	)
)
def line_noted(empty_database: Connection, execution: Execution, level: str, kind: str, text: str) -> None:
	expected = (level, kind, execution.text(text))
	assert expected in _lines(empty_database), _lines(empty_database)


@then("le log de la base n'a noté aucun plantage probable")
def no_crash(empty_database: Connection) -> None:
	every_one = True
	for _level, kind, _message in _lines(empty_database):
		if kind == "plantage probable":
			every_one = False
			break
	assert every_one


@then("le log de la base n'a noté ni démarrage ni fin")
def nothing_noted(empty_database: Connection) -> None:
	assert _lines(empty_database) == []


@then("le terminal est resté ouvert après la « fin » notée au log de la base")
def end_before_staying_open(execution: Execution) -> None:
	assert execution.end_before_staying_open is True


# ─── Machin player (https://github.com/dascritch/machincast/issues/342) ───


@given(parsers.parse("une diffusion de Machin player qui s'arrête avec le code {code:d}"))
def stopping_broadcast(monkeypatch: pytest.MonkeyPatch, code: int) -> None:
	monkeypatch.setattr(player, "run_broadcast", lambda _configuration: code)


@given("une configuration sans périphérique d'antenne")
def without_device(execution: Execution, monkeypatch: pytest.MonkeyPatch) -> None:
	audio = dataclasses.replace(execution.configuration.audio, output="pipewire", device=None)
	chosen = dataclasses.replace(execution.configuration, audio=audio)
	monkeypatch.setattr(cli, "load", lambda _path: chosen)
	execution.configuration = chosen


@given("le rapport de crash en cours de ce démarrage, laissé par son processus")
def leftover_report(execution: Execution, crash_directory: Path) -> None:
	"""Comme le laisse un Machin player tué : le rapport en cours, au nom de son démarrage et de son pid."""
	assert execution.old_pid is not None
	started = datetime(2026, 11, 1, 3, 0, tzinfo=PARIS)
	crash_directory.mkdir(parents=True, exist_ok=True)
	(crash_directory / crash.pending_name("Machin_player", started, execution.old_pid)).write_text(
		"MachinCast\n", encoding="utf-8"
	)
