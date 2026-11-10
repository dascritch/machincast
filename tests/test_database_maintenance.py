"""Scénarios de la maintenance de la base de données (https://github.com/dascritch/machincast/issues/127).

La maintenance travaille sur la base de test, désignée comme base de production d'une configuration du scénario : le
chargement d'un fichier refuse une base de production égale à la base de test, la configuration est donc modifiée
après lecture, et la maintenance exécutée sans passer par le fichier. pg_dump peut être retiré du PATH.
"""

import dataclasses
import io
import logging
import subprocess
import time
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from yoyo import get_backend, read_migrations

from machincast import maintenance
from machincast.cli import create_analyser
from machincast.clock import FixedClock
from machincast.configuration import PROJECT_DIRECTORY, Configuration
from machincast.database import MIGRATION_DIRECTORY, apply_migrations, url_yoyo
from tests.database_fixtures import configuration_test

scenarios("database_maintenance.feature")

LAUNCHING = datetime(2026, 10, 22, 8, 30, tzinfo=ZoneInfo("Europe/Paris"))


@dataclasses.dataclass
class Execution:
	code: int = -1
	information: list[str] = dataclasses.field(default_factory=list)
	errors: list[str] = dataclasses.field(default_factory=list)
	asks: str = ""
	remaining_entry: str = ""
	"""Ce qui reste à lire sur l'entrée standard après la maintenance : vide, si elle a attendu sa fin."""
	start: datetime | None = None
	"""L'heure du serveur PostgreSQL au lancement : le VACUUM de la maintenance la suit."""


@pytest.fixture
def execution() -> Execution:
	return Execution()


@given("une configuration dont la base de production est la base de test", target_fixture="configuration")
def configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_database: object) -> Configuration:
	"""La configuration des tests, comme si elle était dans le répertoire du scénario."""
	monkeypatch.setenv("TZ", "Europe/Paris")
	time.tzset()
	monkeypatch.setattr(maintenance, "CLOCK", FixedClock(LAUNCHING))
	fetched = configuration_test()
	database = dataclasses.replace(fetched.database, production=fetched.database.test)
	return dataclasses.replace(fetched, database=database, path=tmp_path / "machincast.toml")


@given("la dernière migration retirée de la base de test")
def remove_last(configuration: Configuration, request: pytest.FixtureRequest) -> None:
	"""La base de test sert aux autres scénarios : son schéma est remis en état à la fin, quoi qu'il arrive."""
	url = url_yoyo(configuration.database.socket, configuration.database.test)
	request.addfinalizer(lambda: apply_migrations(url))
	with get_backend(url) as backend, backend.lock():
		backend.rollback_migrations(backend.to_rollback(read_migrations(str(MIGRATION_DIRECTORY)))[:1])


@given("pg_dump absent du poste")
def without_dump_pg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	empty = tmp_path / "sans-pg-dump"
	empty.mkdir()
	monkeypatch.setenv("PATH", str(empty))
	monkeypatch.setattr(maintenance, "POSTGRESQL", empty)


@given(parsers.parse("un rôle « {role} » attendu en plus par MachinCast"))
def role_in_more(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
	monkeypatch.setattr(maintenance, "ROLES", (*maintenance.ROLES, role))


def _launch(
	configuration: Configuration,
	execution: Execution,
	caplog: pytest.LogCaptureFixture,
	command: str,
	entry: str = "",
	monkeypatch: pytest.MonkeyPatch | None = None,
) -> None:
	_machin, _binary, *arguments = command.replace("…/", f"{configuration.path.parent}/").split()
	analyser = create_analyser(maintenance.EXECUTABLE, maintenance.DESCRIPTION)
	maintenance.own_options(analyser)
	options = analyser.parse_args(arguments)
	with psycopg.connect(host=str(configuration.database.socket), dbname=configuration.database.test) as connection:
		line = connection.execute("SELECT clock_timestamp()").fetchone()
	assert line is not None
	execution.start = line[0]
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		execution.code = maintenance.run(configuration, options)
		maintenance.after(options)
	r_list = []
	for r in caplog.records:
		if r.levelno == logging.INFO:
			r_list.append(r.getMessage())
	execution.information = r_list
	r_list_2 = []
	for r in caplog.records:
		if r.levelno >= logging.WARNING:
			r_list_2.append(r.getMessage())
	execution.errors = r_list_2


@when(parsers.parse("je lance « {command} »"))
def launch(configuration: Configuration, execution: Execution, caplog: pytest.LogCaptureFixture, command: str) -> None:
	_launch(configuration, execution, caplog, command)


class CtrlC(io.StringIO):
	def read(self, _size: int | None = -1) -> str:
		raise KeyboardInterrupt


@when(parsers.parse("je lance « {command} », puis je tape Ctrl-C"))
def launch_and_interrupt(
	configuration: Configuration,
	execution: Execution,
	caplog: pytest.LogCaptureFixture,
	monkeypatch: pytest.MonkeyPatch,
	command: str,
) -> None:
	monkeypatch.setattr("sys.stdin", CtrlC())
	monkeypatch.setattr("sys.stdout", io.StringIO())
	_launch(configuration, execution, caplog, command)


@when(parsers.parse("je lance « {command} », j'appuie deux fois sur Entrée, puis je ferme le terminal"))
def launch_and_close(
	configuration: Configuration,
	execution: Execution,
	caplog: pytest.LogCaptureFixture,
	monkeypatch: pytest.MonkeyPatch,
	command: str,
) -> None:
	output = io.StringIO()
	# Deux fois Entrée, puis la fin de l'entrée standard : le terminal se ferme.
	keyboard = io.StringIO("\n\n")
	monkeypatch.setattr("sys.stdin", keyboard)
	monkeypatch.setattr("sys.stdout", output)
	_launch(configuration, execution, caplog, command)
	execution.asks = output.getvalue()
	execution.remaining_entry = keyboard.read()


@then(parsers.parse("la maintenance se termine avec le code {code:d}"))
def output_code(execution: Execution, code: int) -> None:
	assert execution.code == code, (execution.information, execution.errors)


def _backups(configuration: Configuration, directory: str) -> list[Path]:
	return sorted((configuration.path.parent / directory).glob("*.dump"))


@then(
	parsers.parse(
		"une sauvegarde datée de la base est dans le répertoire « {directory} » de la configuration,"
		" lisible par le pg_restore du serveur"
	)
)
def backup(configuration: Configuration, directory: str) -> None:
	"""Le pg_restore de la version du serveur, comme le documente la restauration
	(https://github.com/dascritch/machincast/issues/384)."""
	(file,) = _backups(configuration, directory)
	assert file.name == f"{configuration.database.test}-2026-10-22T08-30-00.dump"
	restore = maintenance.tool("pg_restore", maintenance.server_version(configuration.database))
	assert restore is not None
	list_ = subprocess.run([restore, "--list", str(file)], capture_output=True, text=True, timeout=60)
	assert (list_.returncode == 0) and ("TABLE public sounds" in list_.stdout), list_.stderr


@then("la maintenance a annoncé, dans l'ordre :")
def announcements(configuration: Configuration, execution: Execution, datatable: list[list[str]]) -> None:
	_header, *lines = datatable
	expected_list = []
	for (line,) in lines:
		expected_list.append(line.strip().replace("…/", f"{configuration.path.parent}/"))
	line_list = []
	for line in execution.information:
		if not line.startswith("sauvegarde faite"):
			line_list.append(line)
	line_list_2 = []
	for line in expected_list:
		if line != "sauvegarde faite":
			line_list_2.append(line)
	assert line_list == line_list_2
	found = False
	for line in execution.information:
		if line.startswith("sauvegarde faite"):
			found = True
			break
	assert found, execution.information


@then(parsers.parse("la maintenance a annoncé « {text} »"))
def announces(execution: Execution, text: str) -> None:
	assert text in execution.information, execution.information


@then(parsers.parse("la maintenance a signalé « {text} »"))
def reports(execution: Execution, text: str) -> None:
	expected = text.replace("<compte>", maintenance.account())
	assert expected in execution.errors, execution.errors


@then("la maintenance n'a annoncé ni le schéma ni l'optimisation")
def other_nothing(execution: Execution) -> None:
	# Le chemin de la sauvegarde porte le nom du scénario, qui peut contenir « schéma ».
	announcements = []
	for line in execution.information:
		if not line.startswith("sauvegarde"):
			announcements.append(line)
	found = False
	for line in announcements:
		if ("schéma" in line) or ("optimisée" in line):
			found = True
			break
	assert not found, announcements


@then(parsers.parse("la maintenance a dit « {text} »"))
def asks(execution: Execution, text: str) -> None:
	assert text in execution.asks, execution.asks


@then("la maintenance n'a rendu la main qu'à la fermeture du terminal")
def fetched_entry(execution: Execution) -> None:
	assert execution.remaining_entry == "", repr(execution.remaining_entry)


@then(parsers.parse("la table « {table} » vient d'être nettoyée par VACUUM, et ses statistiques recalculées"))
def statistics(configuration: Configuration, execution: Execution, table: str) -> None:
	"""Les statistiques cumulées parviennent au serveur peu après la fin du VACUUM : jusqu'à 5 secondes. Seuls un
	VACUUM et un ANALYZE lancés à la main, après le lancement de la maintenance, comptent : pas ceux d'autovacuum."""
	limit = time.monotonic() + 5
	while True:
		with psycopg.connect(host=str(configuration.database.socket), dbname=configuration.database.test) as connection:
			line = connection.execute(
				"SELECT (last_vacuum >= %s) AND (last_analyze >= %s) FROM pg_stat_user_tables WHERE relname = %s",
				(execution.start, execution.start, table),
			).fetchone()
		if (line == (True,)) or (time.monotonic() > limit):
			break
		time.sleep(0.2)
	assert line == (True,), line


@then("la base de test a toutes ses migrations")
def full_migrations(configuration: Configuration) -> None:
	with get_backend(url_yoyo(configuration.database.socket, configuration.database.test)) as backend:
		assert len(backend.to_apply(read_migrations(str(MIGRATION_DIRECTORY)))) == 0


@then(parsers.parse("« {binary} » est un binaire du wrapper, déclaré dans pyproject.toml"))
def wrapper_binary(binary: str) -> None:
	scripts = tomllib.loads((PROJECT_DIRECTORY / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
	assert scripts[f"Machin_{binary}"] == "machincast.maintenance:main"
	output = subprocess.run(
		[str(PROJECT_DIRECTORY / "bin" / "Machin"), "--binaries"], capture_output=True, text=True, timeout=30
	)
	assert binary in output.stdout.split(), output.stdout


# ─── Programmes de la version du serveur (https://github.com/dascritch/machincast/issues/384) ───


@given(parsers.parse("les programmes de PostgreSQL {versions} installés"), target_fixture="installed")
def installed_versions(tmp_path: Path, versions: str) -> Path:
	"""Comme les paquets : /usr/lib/postgresql/<version>/bin/pg_dump, un par version."""
	root = tmp_path / "postgresql"
	for version in versions.replace(" et ", ", ").split(", "):
		program = root / version / "bin" / "pg_dump"
		program.parent.mkdir(parents=True)
		program.write_text("#!/bin/sh\n", encoding="utf-8")
		program.chmod(0o755)
	return root


@then(parsers.parse("pour un serveur {version:d}, la maintenance prend « {chosen} »"))
def chosen_program(installed: Path, monkeypatch: pytest.MonkeyPatch, version: int, chosen: str) -> None:
	monkeypatch.setenv("PATH", str(installed / "16" / "bin"))
	expected = str(installed / chosen.removeprefix("…/"))
	assert maintenance.tool("pg_dump", version, installed) == expected
