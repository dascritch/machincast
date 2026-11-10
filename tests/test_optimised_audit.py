"""Scénarios de l'audit complet optimisé (https://github.com/dascritch/machincast/issues/206).

Les étapes des fichiers, des sonores et de l'indexeur sont dans tests/indexing_steps.py.
"""

import logging
from datetime import datetime

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.indexer.__main__ import main
from tests.database_fixtures import sample_configuration_path
from tests.indexing_steps import DECIMAL, Execution, count, index, per_file

scenarios("optimised_audit.feature")

Connection = psycopg.Connection[tuple[object, ...]]


def _audit(database: Connection, sound: int) -> tuple[object, object]:
	line = database.execute("SELECT audited_at, audit_threshold FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert line is not None
	return line[0], line[1]


@given("l'indexeur a fait un audit complet")
def prior_audit(
	empty_database: Connection,
	caplog: pytest.LogCaptureFixture,
	indexings: list[tuple[datetime, datetime]],
	silence_threshold: list[float],
) -> None:
	index(empty_database, caplog, full_audit=True, indexings=indexings, silence_threshold=silence_threshold)


@when("l'indexeur fait un audit complet forcé", target_fixture="execution")
def audit_forces(
	empty_database: Connection,
	caplog: pytest.LogCaptureFixture,
	indexings: list[tuple[datetime, datetime]],
	silence_threshold: list[float],
) -> Execution:
	return index(
		empty_database, caplog, full_audit=True, indexings=indexings, silence_threshold=silence_threshold, force=True
	)


@given("un audit complet demandé pour ce sonore")
def ask(empty_database: Connection, sound: int) -> None:
	empty_database.execute("UPDATE sounds SET audit_requested = true WHERE id = %s", (sound,))


@then("ce sonore n'a plus d'audit complet demandé")
def more_requested(empty_database: Connection, sound: int) -> None:
	line = empty_database.execute("SELECT audit_requested FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert line == (False,), line


@then(
	parsers.re(
		rf"le sonore a été audité au seuil de (?P<threshold>-?{DECIMAL}) dB,"
		r" pendant (?P<moment>cette indexation|l'indexation précédente)"
	)
)
def audited(
	empty_database: Connection, sound: int, indexings: list[tuple[datetime, datetime]], threshold: str, moment: str
) -> None:
	chosen = -2
	if moment == "cette indexation":
		chosen = -1
	start, end = indexings[chosen]
	date, audit_threshold = _audit(empty_database, sound)
	assert isinstance(date, datetime), date
	assert start <= date <= end, (start, date, end)
	assert audit_threshold == count(threshold), audit_threshold


@then("le sonore n'a jamais été audité")
def never_audited(empty_database: Connection, sound: int) -> None:
	assert _audit(empty_database, sound) == (None, None)


@then(parsers.parse("la sortie standard annonce « {text} »"))
def announces(execution: Execution, text: str) -> None:
	assert text in execution.information, execution.information


@when(parsers.parse("je lance Machin indexer avec les options « {options} »"), target_fixture="launching")
def launch(caplog: pytest.LogCaptureFixture, options: str) -> tuple[int, list[str]]:
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		code = main(["--config", str(sample_configuration_path()), *options.split()])
	return code, [message for _level, message in per_file(caplog.records)]
