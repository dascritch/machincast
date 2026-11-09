"""Scénarios des rapports de crash (https://github.com/dascritch/machincast/issues/342).

Les binaires se lancent par leur main, sur la base de test désignée comme base de production d'une configuration du
scénario, comme dans run_log.feature. Leurs plantages sont imités : l'action d'un binaire remplacée par une qui lève, un
fil qui lève, un processus Python à part qui plante sur un signal ou que l'on tue. Les rapports vont dans le
répertoire du scénario (conftest.crash_directory), y compris ceux des processus à part (MACHINCAST_CRASH_DUMP).
"""

import dataclasses
import logging
import os
import subprocess
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import __version__, cli, crash, purge
from machincast.configuration import Configuration
from machincast.indexer import __main__ as indexer
from machincast.indexer import directories
from tests.database_fixtures import configuration_test

scenarios("crash_report.feature")

Connection = psycopg.Connection[tuple[object, ...]]
BINARIES: dict[str, Callable[[list[str]], int]] = {"purge": purge.main, "indexer": indexer.main}
CRASHING = """
import faulthandler, sys, time
from machincast import crash
from machincast.indexer.check import ANALYSED
with crash.watch(sys.argv[1]):
	crash.note(ANALYSED, sys.argv[2])
	crash.refresh()
	if sys.argv[3] == "segv":
		faulthandler._sigsegv()
	print("prêt", flush=True)
	time.sleep(300)
"""
"""Un binaire imité : surveillé, il note un fichier en cours d'analyse, puis plante sur SIGSEGV ou attend."""


@dataclasses.dataclass
class Execution:
	configuration: Configuration
	directory: Path
	code: int = -1
	information: list[str] = dataclasses.field(default_factory=list)
	errors: list[str] = dataclasses.field(default_factory=list)
	crashed: BaseException | None = None
	old_pid: int | None = None
	seen: list[str] = dataclasses.field(default_factory=list)
	"""Ce que crash-dump contenait pendant le lancement."""

	def text(self, text: str) -> str:
		text = text.replace("<version>", __version__).replace("<pid>", str(os.getpid()))
		return text.replace("…/", f"{self.directory}/")


@pytest.fixture
def surveillance() -> Iterator[ExitStack]:
	"""Les surveillances ouvertes par le scénario, fermées à sa fin."""
	with ExitStack() as stack:
		yield stack


@pytest.fixture
def processes() -> Iterator[list[subprocess.Popen[str]]]:
	"""Les processus imités qui tournent encore, arrêtés à la fin du scénario."""
	started: list[subprocess.Popen[str]] = []
	yield started
	for process in started:
		process.kill()
		process.wait()


@given("une configuration de test pour les binaires", target_fixture="execution")
def configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_database: Connection) -> Execution:
	fetched = configuration_test()
	database = dataclasses.replace(fetched.database, production=fetched.database.test)
	chosen = dataclasses.replace(fetched, database=database, path=tmp_path / "machincast.toml")
	monkeypatch.setattr(cli, "load", lambda _path: chosen)
	return Execution(configuration=chosen, directory=tmp_path)


@given(parsers.parse("Machin purge qui plante sur l'erreur imprévue « {text} »"))
def failing_purge(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
	def imitated_failure(_configuration: Configuration, _options: object) -> int:
		raise RuntimeError(text)

	monkeypatch.setattr(purge, "run", imitated_failure)


@given("Machin purge qui plante sur une requête PostgreSQL vers une table absente")
def failing_query(monkeypatch: pytest.MonkeyPatch) -> None:
	def run(configuration: Configuration, _options: object) -> int:
		database = configuration.database
		with psycopg.connect(host=str(database.socket), dbname=database.production) as connection:
			connection.execute("SELECT * FROM table_absente")
		return 0

	monkeypatch.setattr(purge, "run", run)


@given("Machin purge qui plante sur un pipeline GStreamer impossible")
def failing_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
	def run(_configuration: Configuration, _options: object) -> int:
		from machincast import audio

		audio.Gst.init(None)
		audio.Gst.parse_launch("element_qui_nexiste_pas")
		return 0

	monkeypatch.setattr(purge, "run", run)


@given(parsers.parse("Machin purge dont un fil plante sur l'erreur imprévue « {text} »"))
def failing_thread(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
	def fail() -> None:
		raise RuntimeError(text)

	def run(_configuration: Configuration, _options: object) -> int:
		feed = threading.Thread(target=fail, name="fil-imité")
		feed.start()
		feed.join()
		return 0

	monkeypatch.setattr(purge, "run", run)


@given("Machin purge qui regarde crash-dump pendant qu'il tourne")
def watching_purge(monkeypatch: pytest.MonkeyPatch, execution: Execution, crash_directory: Path) -> None:
	def run(_configuration: Configuration, _options: object) -> int:
		execution.seen = sorted(path.name for path in crash_directory.iterdir())
		return 0

	monkeypatch.setattr(purge, "run", run)


@given(parsers.parse("une banque « {name} » alimentée par le répertoire « {directory} », où est le fichier « {file} »"))
def fed_bank(empty_database: Connection, tmp_path: Path, name: str, directory: str, file: str) -> None:
	"""Le contenu du fichier ne compte pas : son enregistrement plante."""
	path = tmp_path / directory
	path.mkdir()
	(path / file).write_bytes(b"son")
	line = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (name,)
	).fetchone()
	assert line is not None
	empty_database.execute("INSERT INTO bank_directories (bank_id, directory) VALUES (%s, %s)", (line[0], str(path)))


@given("Machin indexer qui plante en enregistrant un fichier")
def failing_indexer(monkeypatch: pytest.MonkeyPatch) -> None:
	def imitated_save(*_arguments: object) -> None:
		raise RuntimeError("panne de l'enregistrement")

	monkeypatch.setattr(directories, "_save", imitated_save)


@given("un dépôt du code sans droit d'écriture")
def read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	depot = tmp_path / "depot"
	depot.mkdir()
	depot.chmod(0o500)
	monkeypatch.setattr(crash, "DIRECTORY", depot / "crash-dump")
	monkeypatch.delenv(crash.ENVIRONMENT)


def _imitated_binary(program: str, file: str, mode: str) -> subprocess.Popen[str]:
	return subprocess.Popen(
		[sys.executable, "-c", CRASHING, program, file, mode],
		stdout=subprocess.PIPE,
		stderr=subprocess.DEVNULL,
		text=True,
		env={**os.environ, "LANGUAGE": "fr"},
	)


@given(
	parsers.parse(
		"un binaire « {program} » qui note « {file} » comme fichier en cours d'analyse, puis plante sur un signal SIGSEGV"
	)
)
def segfault(execution: Execution, program: str, file: str) -> None:
	process = _imitated_binary(program, file, "segv")
	process.wait(timeout=60)
	assert process.returncode < 0, process.returncode
	execution.old_pid = process.pid


@given(
	parsers.parse(
		"un binaire « {program} » qui note « {file} » comme fichier en cours d'analyse, puis est tué par kill -9"
	)
)
def killed(execution: Execution, program: str, file: str) -> None:
	process = _imitated_binary(program, file, "attente")
	assert process.stdout is not None
	assert process.stdout.readline().strip() == "prêt"
	process.kill()
	process.wait(timeout=60)
	execution.old_pid = process.pid


@given(parsers.parse("un binaire « {program} » qui tourne encore, avec son rapport en cours"))
def still_running(execution: Execution, processes: list[subprocess.Popen[str]], program: str) -> None:
	process = _imitated_binary(program, "/srv/musique/c.flac", "attente")
	processes.append(process)
	assert process.stdout is not None
	assert process.stdout.readline().strip() == "prêt"
	execution.old_pid = process.pid


@given(parsers.parse("le lancement surveillé, comme « {program} »"))
def watched(surveillance: ExitStack, program: str) -> None:
	surveillance.enter_context(crash.watch(program))


@given(parsers.parse("« wpctl status » qui répond « {text} »"))
def imitated_wpctl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str) -> None:
	program = tmp_path / "wpctl"
	program.write_text(f'#!/bin/sh\necho "{text}"\n', encoding="utf-8")
	program.chmod(0o755)
	monkeypatch.setattr(crash, "WPCTL", str(program))


def _launch(execution: Execution, caplog: pytest.LogCaptureFixture, command: str) -> None:
	_machin, binary, *arguments = execution.text(command).split()
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		try:
			execution.code = BINARIES[binary](arguments)
		except Exception as error:  # noqa: BLE001 : le plantage du scénario
			execution.crashed = error
	execution.information = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
	execution.errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


@when(parsers.re(r"je lance « (?P<command>[^»]+) »$"))
def launch(execution: Execution, caplog: pytest.LogCaptureFixture, command: str) -> None:
	_launch(execution, caplog, command)
	assert execution.crashed is None, execution.crashed


@when(parsers.re(r"je lance « (?P<command>[^»]+) », qui plante"))
def launch_crashing(execution: Execution, caplog: pytest.LogCaptureFixture, command: str) -> None:
	_launch(execution, caplog, command)
	assert execution.crashed is not None


@when(parsers.parse("le lancement suivant de « {program} » achève les rapports en cours"))
def next_launch(program: str) -> None:
	crash.finish_leftovers(program)


@when(parsers.parse("une erreur imprévue « {text} » arrête le lancement surveillé"))
def stopping_error(surveillance: ExitStack, text: str) -> None:
	"""Comme une exception qui sort du lancement surveillé : la surveillance écrit le rapport, puis la laisse passer."""
	try:
		raise RuntimeError(text)
	except RuntimeError as error:
		assert not surveillance.__exit__(type(error), error, error.__traceback__)


@then(parsers.parse("le lancement se termine avec le code {code:d}"))
def output_code(execution: Execution, code: int) -> None:
	assert execution.code == code, (execution.information, execution.errors)


def _reports(directory: Path) -> list[Path]:
	if not directory.exists():
		return []
	return sorted(directory.glob("*.txt"))


def _pending(directory: Path) -> list[Path]:
	if not directory.exists():
		return []
	return sorted(directory.glob(f".*{crash.PENDING}"))


@then(
	parsers.re(
		r"crash-dump contient un seul rapport, celui de « (?P<program>[^»]+) » pour (?P<which>ce lancement|le lancement"
		r" planté), et aucun rapport en cours"
	)
)
def one_report(execution: Execution, crash_directory: Path, program: str, which: str) -> None:
	pid = execution.old_pid
	if which == "ce lancement":
		pid = os.getpid()
	(report,) = _reports(crash_directory)
	assert (report.name.startswith(f"{program}-")) and (report.name.endswith(f"-{pid}.txt")), report.name
	assert _pending(crash_directory) == []


@then("crash-dump ne contient aucun rapport, ni aucun rapport en cours")
def nothing(crash_directory: Path) -> None:
	assert (_reports(crash_directory), _pending(crash_directory)) == ([], [])


@then("crash-dump ne contient aucun rapport, mais un rapport en cours")
def only_pending(crash_directory: Path) -> None:
	assert _reports(crash_directory) == []
	assert len(_pending(crash_directory)) == 1


@then(
	parsers.parse("crash-dump contenait, pendant le lancement, un rapport en cours de « {program} » pour ce lancement")
)
def pending_seen(execution: Execution, program: str) -> None:
	(name,) = execution.seen
	assert (name.startswith(f".{program}-")) and (name.endswith(f"-{os.getpid()}{crash.PENDING}")), name


@then(parsers.parse("le répertoire de secours contient le rapport de « {program} » pour ce lancement"))
def in_fallback(program: str) -> None:
	(report,) = _reports(crash.FALLBACK)
	assert (report.name.startswith(f"{program}-")) and (report.name.endswith(f"-{os.getpid()}.txt")), report.name


def _contains(text: str, execution: Execution | None, datatable: list[list[str]]) -> None:
	_header, *rows = datatable
	for (expected,) in rows:
		wanted = expected.strip()
		if execution is not None:
			wanted = execution.text(wanted)
		assert wanted in text, f"{wanted!r} absent de :\n{text}"


@then("le rapport dit :")
def says(request: pytest.FixtureRequest, crash_directory: Path, datatable: list[list[str]]) -> None:
	execution = None
	if "execution" in request.fixturenames:
		execution = request.getfixturevalue("execution")
	watch = crash.current()
	if (watch is not None) and (watch.written != []):
		(report,) = watch.written
	else:
		(report,) = _reports(crash_directory)
	_contains(report.read_text(encoding="utf-8"), execution, datatable)


@then("le rapport en cours dit :")
def pending_says(datatable: list[list[str]]) -> None:
	watch = crash.current()
	assert watch is not None
	_contains(watch.pending_path.read_text(encoding="utf-8"), None, datatable)


@then("le journal a signalé le rapport de crash écrit")
def announced(execution: Execution, crash_directory: Path) -> None:
	(report,) = _reports(crash_directory)
	assert f"rapport de crash écrit : {report}" in execution.errors, execution.errors
