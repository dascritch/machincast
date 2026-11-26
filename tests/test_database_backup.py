"""Scénarios de l'export et de la réimportation de la base (https://github.com/dascritch/machincast/issues/347).

Comme la maintenance (tests/test_database_maintenance.py, dont viennent la configuration du scénario et ses étapes
communes), les deux commandes travaillent sur la base de test, désignée comme base de production. La réimportation
demande une base vide : le scénario vide la base de test, et la remet en état à la fin, quoi qu'il arrive.
"""

import dataclasses
import logging
import subprocess
import tomllib
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import backup
from machincast.cli import create_analyser
from machincast.configuration import PROJECT_DIRECTORY, Configuration
from tests.database_fixtures import reset_database
from tests.test_database_maintenance import backup as dated_backup
from tests.test_database_maintenance import configuration as maintenance_configuration
from tests.test_database_maintenance import full_migrations, remove_last, without_dump_pg

scenarios("database_backup.feature")

# Les étapes communes avec la maintenance, déclarées aussi pour ces scénarios.
given("une configuration dont la base de production est la base de test", target_fixture="configuration")(
	maintenance_configuration
)
given("pg_dump absent du poste")(without_dump_pg)
given("la dernière migration retirée de la base de test")(remove_last)
then("la base de test a toutes ses migrations")(full_migrations)
then(
	parsers.parse(
		"une sauvegarde datée de la base est dans le répertoire « {directory} » de la configuration, lisible par le"
		" pg_restore du serveur"
	)
)(dated_backup)


@dataclasses.dataclass
class Command:
	code: int = -1
	information: list[str] = dataclasses.field(default_factory=list)
	errors: list[str] = dataclasses.field(default_factory=list)
	backup: Path | None = None
	"""La sauvegarde faite par « une sauvegarde de la base de test »."""


@pytest.fixture
def command() -> Command:
	return Command()


def connect(configuration: Configuration) -> psycopg.Connection[tuple[object, ...]]:
	return psycopg.connect(host=str(configuration.database.socket), dbname=configuration.database.test, autocommit=True)


@given(parsers.parse("la séquence « {name} » en base"))
def sequence_in_database(configuration: Configuration, name: str) -> None:
	with connect(configuration) as connection:
		connection.execute("INSERT INTO sequences (internal_name) VALUES (%s)", (name,))


@given(parsers.parse("une migration « {identifier} » notée en base, inconnue de cette version"))
def unknown_migration(configuration: Configuration, request: pytest.FixtureRequest, identifier: str) -> None:
	def forget() -> None:
		with connect(configuration) as connection:
			connection.execute("DELETE FROM _yoyo_migration WHERE migration_id = %s", (identifier,))

	request.addfinalizer(forget)
	with connect(configuration) as connection:
		connection.execute(
			"INSERT INTO _yoyo_migration (migration_hash, migration_id, applied_at_utc)"
			" VALUES (md5(%s), %s, now() AT TIME ZONE 'UTC')",
			(identifier, identifier),
		)


@given("une sauvegarde de la base de test")
def database_backup(configuration: Configuration, command: Command) -> None:
	command.backup = backup.back_up(configuration, configuration.backup.directory)


@given("la base de test vidée, comme install.sh vient de la créer")
def emptied_database(configuration: Configuration, request: pytest.FixtureRequest) -> None:
	"""Le schéma public d'une base neuve, sans rien d'autre ; tout est recréé et migré à la fin."""

	def recreate() -> None:
		with connect(configuration) as connection:
			reset_database(connection)

	request.addfinalizer(recreate)
	with connect(configuration) as connection:
		connection.execute("DROP SCHEMA public CASCADE")
		connection.execute("CREATE SCHEMA public AUTHORIZATION pg_database_owner")
		connection.execute("GRANT USAGE ON SCHEMA public TO PUBLIC")


@given(parsers.parse("le fichier « {name} », qui n'est pas une sauvegarde"))
def not_backup(configuration: Configuration, name: str) -> None:
	(configuration.path.parent / name).write_text("ceci n'est pas une sauvegarde\n", encoding="utf-8")


def _arguments(configuration: Configuration, command: Command, text: str) -> list[str]:
	if command.backup is not None:
		text = text.replace("<sauvegarde>", str(command.backup))
	return text.replace("…/", f"{configuration.path.parent}/").split()


@when(parsers.parse("je lance « {line} »"))
def launch(configuration: Configuration, command: Command, caplog: pytest.LogCaptureFixture, line: str) -> None:
	_machin, binary, *arguments = _arguments(configuration, command, line)
	executables = {
		"backup-db": (backup.BACKUP_EXECUTABLE, backup.BACKUP_DESCRIPTION, backup.backup_options, backup.run_backup),
		"restore-db": (
			backup.RESTORE_EXECUTABLE,
			backup.RESTORE_DESCRIPTION,
			backup.restore_options,
			backup.run_restore,
		),
	}
	executable, description, own_options, action = executables[binary]
	analyser = create_analyser(executable, description)
	own_options(analyser)
	options = analyser.parse_args(arguments)
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		command.code = action(configuration, options)
	information = []
	errors = []
	for record in caplog.records:
		if record.levelno == logging.INFO:
			information.append(record.getMessage())
		if record.levelno >= logging.WARNING:
			errors.append(record.getMessage())
	command.information = information
	command.errors = errors


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def output_code(command: Command, code: int) -> None:
	assert command.code == code, (command.information, command.errors)


def _text(configuration: Configuration, command: Command, text: str) -> str:
	if command.backup is not None:
		text = text.replace("<sauvegarde>", str(command.backup))
	return text.replace("…/", f"{configuration.path.parent}/")


@then("la commande a annoncé, dans l'ordre :")
def announcements(configuration: Configuration, command: Command, datatable: list[list[str]]) -> None:
	_header, *rows = datatable
	expected = []
	for row in rows:
		expected.append(_text(configuration, command, row[0].strip()))
	found = []
	for line in command.information:
		if line.startswith("sauvegarde faite : "):
			line = "sauvegarde faite"
		if line in expected:
			found.append(line)
	assert found == expected, command.information


@then(parsers.parse("la commande a annoncé « {text} »"))
def announces(configuration: Configuration, command: Command, text: str) -> None:
	assert _text(configuration, command, text) in command.information, command.information


@then(parsers.parse("la commande a signalé « {text} »"))
def reports(configuration: Configuration, command: Command, text: str) -> None:
	assert _text(configuration, command, text) in command.errors, command.errors


@then(parsers.parse("la commande a signalé un fichier « {file} » qui n'est pas une sauvegarde de MachinCast"))
def not_a_backup(configuration: Configuration, command: Command, file: str) -> None:
	start = _text(configuration, command, f"{file} n'est pas une sauvegarde de MachinCast")
	found = []
	for error in command.errors:
		if error.startswith(start):
			found.append(error)
	assert found, command.errors


@then(parsers.parse("la séquence « {name} » est en base"))
def sequence_found(configuration: Configuration, name: str) -> None:
	with connect(configuration) as connection:
		line = connection.execute("SELECT count(*) FROM sequences WHERE internal_name = %s", (name,)).fetchone()
	assert line == (1,), line


@then("la base de test est toujours vide")
def still_empty(configuration: Configuration) -> None:
	with connect(configuration) as connection:
		line = connection.execute(
			"SELECT count(*) FROM pg_class JOIN pg_namespace ON pg_namespace.oid = relnamespace"
			" WHERE nspname = 'public'"
		).fetchone()
	assert line == (0,), line


@then(parsers.parse("« {binary} » est un binaire du wrapper, déclaré dans pyproject.toml par « {entry} »"))
def wrapper_binary(binary: str, entry: str) -> None:
	scripts = tomllib.loads((PROJECT_DIRECTORY / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
	assert scripts[f"Machin_{binary}"] == entry
	output = subprocess.run(
		[str(PROJECT_DIRECTORY / "bin" / "Machin"), "--binaries"],
		capture_output=True,
		text=True,
		timeout=30,
		check=False,
	)
	assert binary in output.stdout.split(), output.stdout


@when("le script d'une sauvegarde d'avant est traduit :", target_fixture="replayed")
def translate(docstring: str) -> str:
	translation = backup.Translation()
	lines = []
	for line in docstring.splitlines(keepends=True):
		lines.append(translation.line(line))
	return "".join(lines)


@then("le script rejoué est :")
def replayed_script(replayed: str, docstring: str) -> None:
	assert replayed == docstring
