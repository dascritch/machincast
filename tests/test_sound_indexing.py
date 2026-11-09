"""Scénarios de l'indexation d'un seul sonore (https://github.com/dascritch/machincast/issues/181).

Les étapes des fichiers, des sonores et de l'autre indexation sont dans tests/indexing_steps.py.
"""

import argparse
import dataclasses
import logging
from datetime import datetime
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import parsers, scenarios, then, when

from machincast.indexer.__main__ import run
from tests.database_fixtures import configuration_test
from tests.indexing_steps import checks_at, now_in_database, per_file

scenarios("sound_indexing.feature")

Connection = psycopg.Connection[tuple[object, ...]]


@dataclasses.dataclass
class Launching:
	code: int
	messages: list[str]
	start: datetime
	end: datetime


def launch(
	database: Connection, caplog: pytest.LogCaptureFixture, sound: int, full_audit: bool = True, window: bool = False
) -> Launching:
	"""L'action de Machin indexer, avec une configuration dont la base de production est la base de test."""
	configuration = configuration_test()
	on_test_database = dataclasses.replace(
		configuration, database=dataclasses.replace(configuration.database, production=configuration.database.test)
	)
	caplog.clear()
	start = now_in_database(database)
	with caplog.at_level(logging.INFO, logger="machincast"):
		options = argparse.Namespace(full_audit=full_audit, window=window, sound=sound, force=False)
		code = run(on_test_database, options)
	messages = [message for _level, message in per_file(caplog.records)]
	return Launching(code, messages, start, now_in_database(database))


@when(
	"Machin indexer est lancé sur la base de test, en audit complet, pour ce sonore seulement",
	target_fixture="launching",
)
def for_this_sound(empty_database: Connection, caplog: pytest.LogCaptureFixture, sound: int) -> Launching:
	return launch(empty_database, caplog, sound)


@when(
	parsers.parse("Machin indexer est lancé sur la base de test, en audit complet, pour le sonore {number:d}"),
	target_fixture="launching",
)
def for_sound(empty_database: Connection, caplog: pytest.LogCaptureFixture, number: int) -> Launching:
	return launch(empty_database, caplog, number)


@when("Machin indexer est lancé sur la base de test, en audit complet, pour ce stream", target_fixture="launching")
def for_stream(empty_database: Connection, caplog: pytest.LogCaptureFixture, stream: tuple[int, object]) -> Launching:
	return launch(empty_database, caplog, stream[0])


@when("Machin indexer est lancé avec --window et --sound 1", target_fixture="launching")
def with_window(empty_database: Connection, caplog: pytest.LogCaptureFixture) -> Launching:
	return launch(empty_database, caplog, 1, full_audit=False, window=True)


@then(parsers.parse("Machin indexer se termine avec le code {code:d}"))
def finished(launching: Launching, code: int) -> None:
	assert launching.code == code, launching.messages


@then(parsers.parse("Machin indexer se termine avec le code {code:d}, en signalant « {text} »"))
def finished_in_reporting(launching: Launching, code: int, text: str) -> None:
	assert (launching.code, text in launching.messages) == (code, True), launching.messages


@then("Machin indexer refuse ce stream, qui n'est pas un fichier")
def refuses_stream(launching: Launching, stream: tuple[int, object]) -> None:
	assert launching.code == 1
	assert f"sonore {stream[0]} : inconnu, ou pas un fichier" in launching.messages, launching.messages


@then("la date de vérification complète du sonore est celle de ce lancement")
def checks_during_launching(empty_database: Connection, sound: int, launching: Launching) -> None:
	date = checks_at(empty_database, sound)
	assert isinstance(date, datetime)
	assert launching.start <= date <= launching.end


@then("le deuxième sonore n'a pas de date de vérification complète")
def second_not_checked(empty_database: Connection, sound: int) -> None:
	line = empty_database.execute("SELECT checked_at FROM sounds WHERE id <> %s", (sound,)).fetchone()
	assert line == (None,)


@then("aucun document d'audit n'est écrit")
def without_document(audit_directory: Path) -> None:
	assert list(audit_directory.iterdir()) == []
