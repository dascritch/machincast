"""Étapes du schéma SQL d'un plugin et de son installation (https://github.com/dascritch/machincast/issues/586)."""

import argparse
import dataclasses
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import maintenance, plugins
from machincast.configuration import Backup, Configuration, Plugins
from machincast.database import url_yoyo
from machincast.plugins import installation, schema
from tests.database_fixtures import (
	configuration_test,
	migration_count,
	purge_database,
	sample_connection,
	sample_database_parameters,
)

scenarios("plugin_schema.feature")

Connection = psycopg.Connection[tuple[object, ...]]
DONE = "sauvegarde faite"
"""Le début du message de maintenance.back_up, sa sauvegarde finie."""
CREATED = """CREATE TABLE {table} (
	id bigserial PRIMARY KEY,
	sound_id bigint REFERENCES sounds (id) ON DELETE CASCADE,
	ring text NOT NULL
);
GRANT SELECT ON {table} TO {role};
"""


@pytest.fixture
def database() -> Iterator[Connection]:
	connection = sample_connection()
	purge_database(connection)
	yield connection
	connection.close()


@pytest.fixture
def plugin_directory(tmp_path: Path) -> Path:
	directory = tmp_path / "plugins"
	directory.mkdir()
	return directory


@pytest.fixture
def backups(tmp_path: Path) -> Path:
	return tmp_path / "sauvegardes"


@pytest.fixture
def enabled() -> list[str]:
	return []


@pytest.fixture
def configuration(plugin_directory: Path, backups: Path, enabled: list[str]) -> Configuration:
	"""La configuration des tests, dont la « base de production » est la base de test : jamais la vraie."""
	loaded = configuration_test()
	_socket, name = sample_database_parameters()
	return dataclasses.replace(
		loaded,
		database=dataclasses.replace(loaded.database, production=name, test=f"{name}-jamais"),
		backup=Backup(directory=backups),
		plugins=Plugins(enabled=tuple(enabled), directory=plugin_directory),
	)


def _url() -> str:
	return url_yoyo(*sample_database_parameters())


def _migration(directory: Path, identifier: str, script: str, *, rollback: str | None) -> None:
	migrations = directory / "migrations"
	migrations.mkdir(exist_ok=True)
	(migrations / f"{identifier}.sql").write_text(script, encoding="utf-8")
	if rollback is not None:
		(migrations / f"{identifier}.rollback.sql").write_text(rollback, encoding="utf-8")


@given(
	parsers.parse(
		"le plugin « {name} », pour « {binary} », avec la migration « {identifier} » qui crée la table « {table} », "
		"lisible par « {role} »"
	),
	target_fixture="plugin",
)
def plugin(
	plugin_directory: Path, database: Connection, name: str, binary: str, identifier: str, table: str, role: str
) -> Iterator[Path]:
	directory = plugin_directory / name
	directory.mkdir()
	manifest = {"name": name, "version": "1.0", "description": "A clock", "binaries": [binary]}
	(directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
	_migration(directory, identifier, CREATED.format(table=table, role=role), rollback=f"DROP TABLE {table};\n")
	yield directory
	# Les migrations du plugin, appliquées par le scénario, ne restent pas pour le suivant ; seulement la première,
	# celle du contexte : les fautives ne sont jamais appliquées.
	for path in sorted((directory / "migrations").glob("*.sql")):
		if path.name not in (f"{identifier}.sql", f"{identifier}.rollback.sql"):
			path.unlink()  # fichier de MachinCast : migration fautive du scénario
	schema.cancel(_url(), directory)


FAULTS: dict[str, tuple[str, str, str | None]] = {
	"la migration « 0002.alarmes »": ("0002.alarmes", "SELECT 1;\n", "SELECT 1;\n"),
	"la migration « horloge.0002.alarmes » sans son annulation": ("horloge.0002.alarmes", "SELECT 1;\n", None),
	"la migration « horloge.0002.alarmes » qui donne à « machincast_indexer »": (
		"horloge.0002.alarmes",
		"GRANT SELECT ON sounds TO machincast_indexer;\n",
		"SELECT 1;\n",
	),
}


@given(parsers.parse("le plugin « {name} » a {fault}"))
def faulty(plugin: Path, fault: str) -> None:
	identifier, script, rollback = FAULTS[fault]
	_migration(plugin, identifier, script, rollback=rollback)


@given(parsers.re(r"les plugins activés « (?P<name>[^»]+) »$"))
def enabled_plugin(enabled: list[str], name: str) -> None:
	enabled.append(name)


@given(parsers.parse("le plugin « {name} » installé, et un sonore en base"))
def installed(plugin: Path, database: Connection) -> None:
	schema.apply(_url(), plugin)
	database.execute("INSERT INTO sounds (type, location, state) VALUES ('file', '/musique/a.mp3', 'active')")


def _install(
	configuration: Configuration, plugin: Path, caplog: pytest.LogCaptureFixture, *options: str
) -> dict[str, Any]:
	before = len(_backups(configuration.backup.directory))
	caplog.set_level(logging.INFO)
	caplog.clear()
	analyser = argparse.ArgumentParser()
	installation.own_options(analyser)
	parsed = analyser.parse_args([str(plugin), *options])
	code = installation.run(configuration, parsed)
	messages = []
	for record in caplog.records:
		messages.append(record.getMessage())
	return {"code": code, "messages": messages, "backups": len(_backups(configuration.backup.directory)) - before}


@when(parsers.parse("le plugin « {name} » est installé"), target_fixture="outcome")
def install(configuration: Configuration, plugin: Path, caplog: pytest.LogCaptureFixture) -> dict[str, Any]:
	return _install(configuration, plugin, caplog)


@when(parsers.parse("le plugin « {name} » est installé avec --simulation"), target_fixture="outcome")
def simulate(configuration: Configuration, plugin: Path, caplog: pytest.LogCaptureFixture) -> dict[str, Any]:
	return _install(configuration, plugin, caplog, "--simulation")


@when(parsers.parse("le plugin « {name} » est désinstallé"), target_fixture="outcome")
def remove(configuration: Configuration, plugin: Path, caplog: pytest.LogCaptureFixture) -> dict[str, Any]:
	return _install(configuration, plugin, caplog, "--remove")


def _backups(backups: Path) -> list[Path]:
	if not backups.is_dir():
		return []
	return sorted(backups.iterdir())


@then("l'installation réussit")
def succeeded(outcome: dict[str, Any]) -> None:
	assert outcome["code"] == 0, outcome["messages"]


@then(parsers.parse("l'installation réussit, et dit « {message} », sans sauvegarde"))
def succeeded_saying(outcome: dict[str, Any], message: str, backups: Path) -> None:
	assert outcome["code"] == 0, outcome["messages"]
	assert message in outcome["messages"]
	assert outcome["backups"] == 0


@then(parsers.parse("une sauvegarde de la base précède « {message} »"))
def backup_first(outcome: dict[str, Any], message: str, backups: Path) -> None:
	assert outcome["backups"] == 1
	messages = outcome["messages"]
	saved = -1
	for index, said in enumerate(messages):
		if said.startswith(DONE):
			saved = index
	assert messages.index(message) > saved >= 0, messages


@then(parsers.parse("l'installation est refusée, code 2, parce que « {reason} », sans sauvegarde"))
def refused(outcome: dict[str, Any], reason: str, backups: Path) -> None:
	assert outcome["code"] == installation.INVALID
	assert f"plugin « horloge » : {reason}" in outcome["messages"], outcome["messages"]
	assert outcome["backups"] == 0


def _exists(database: Connection, table: str) -> bool:
	line = database.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",)).fetchone()
	return (line is not None) and (line[0] is True)


@then(parsers.parse("la table « {table} » existe, et « {role} » peut la lire"))
def table_readable(database: Connection, table: str, role: str) -> None:
	assert _exists(database, table)
	line = database.execute("SELECT has_table_privilege(%s, %s, 'SELECT')", (role, table)).fetchone()
	assert line == (True,)


@then(parsers.parse("la table « {table} » n'existe pas"))
def table_absent(database: Connection, table: str) -> None:
	assert not _exists(database, table)


def _core_applied(database: Connection) -> int:
	line = database.execute("SELECT count(*) FROM _yoyo_migration WHERE migration_id ~ '^[0-9]'").fetchone()
	assert line is not None
	return int(str(line[0]))


@then("les migrations du cœur sont toutes appliquées")
def core_applied(database: Connection) -> None:
	assert _core_applied(database) == migration_count()


@then("les migrations du cœur sont toutes appliquées, et le sonore est toujours en base")
def core_and_sound(database: Connection) -> None:
	assert _core_applied(database) == migration_count()
	assert database.execute("SELECT location FROM sounds").fetchall() == [("/musique/a.mp3",)]


@when("la maintenance met à jour le schéma de la base")
def maintain(configuration: Configuration, caplog: pytest.LogCaptureFixture) -> None:
	caplog.set_level(logging.INFO)
	maintenance.update_schema(configuration)


@then(parsers.parse("le journal dit « {message} »"))
def journal_says(caplog: pytest.LogCaptureFixture, message: str) -> None:
	messages = []
	for record in caplog.records:
		messages.append(record.getMessage())
	assert message in messages, messages


@given(parsers.parse("le plugin « {name} » demande la table « {table} »"))
def requires_table(plugin: Path, name: str, table: str) -> None:
	manifest = json.loads((plugin / "manifest.json").read_text(encoding="utf-8"))
	manifest["requires"] = {"tables": [table]}
	(plugin / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@when(parsers.parse("MachinCast vérifie si « {name} » peut être activé"), target_fixture="reasons")
def check_availability(configuration: Configuration, plugin_directory: Path, name: str) -> list[str]:
	found = plugins.discover(plugin_directory)
	manifests = {}
	for each in found:
		if each.manifest is not None:
			manifests[each.name] = each.manifest
	chosen = []
	for each in found:
		if each.name == name:
			chosen.append(each)
	return plugins.availability(chosen[0], manifests, configuration, "Machin_player")


@then(parsers.parse("il ne peut pas l'être, parce que « {reason} »"))
def unavailable(reasons: list[str], plugin_directory: Path, reason: str) -> None:
	assert reasons == [reason.replace("{plugins}", str(plugin_directory))]


@then("il peut l'être")
def available(reasons: list[str]) -> None:
	assert reasons == []
