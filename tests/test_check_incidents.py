"""Scénarios des incidents pendant la vérification d'un sonore (https://github.com/dascritch/machincast/issues/401).

La panne et le blocage sont imités dans machincast.indexer.check.type_mime, le premier examen de chaque fichier, appelé
dans le fil de l'examen : le décodage n'est pas remplacé. Le fil bloqué est libéré à la fin du scénario.
"""

import threading
import time
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.indexer import check
from tests.indexing_steps import Execution, index

scenarios("check_incidents.feature")

Connection = psycopg.Connection[tuple[object, ...]]


@pytest.fixture
def release() -> Iterator[threading.Event]:
	"""Libère, en fin de scénario, l'examen bloqué."""
	event = threading.Event()
	yield event
	event.set()


def _replace_type(monkeypatch: pytest.MonkeyPatch, file: Path, failure: object) -> None:
	"""L'examen du type de ce fichier appelle failure ; celui des autres est le vrai."""
	true_type = check.type_mime

	def type_mime(path: Path) -> str | None:
		if path == file:
			assert callable(failure)
			failure()
		return true_type(path)

	monkeypatch.setattr(check, "type_mime", type_mime)


@given("l'examen de ce fichier lève une erreur imprévue")
def raises(monkeypatch: pytest.MonkeyPatch, file: Path) -> None:
	def failure() -> None:
		raise RuntimeError("panne imitée")

	_replace_type(monkeypatch, file, failure)


@given("l'examen de ce fichier se bloque")
def blocks(monkeypatch: pytest.MonkeyPatch, file: Path, release: threading.Event) -> None:
	_replace_type(monkeypatch, file, release.wait)


@given(parsers.parse("une limite de {seconds:d} seconde pour l'examen d'un fichier"))
def limit(monkeypatch: pytest.MonkeyPatch, seconds: int) -> None:
	monkeypatch.setattr(check, "AUDIT_LIMIT", timedelta(seconds=seconds))


@when("l'indexeur fait un audit complet", target_fixture="execution")
def full_audit(
	empty_database: Connection, caplog: pytest.LogCaptureFixture, indexings: list[tuple[datetime, datetime]]
) -> Execution:
	"""Comme l'étape partagée, en notant la durée de l'audit."""
	start = time.monotonic()
	execution = index(empty_database, caplog, full_audit=True, indexings=indexings)
	execution.information.append(f"durée {time.monotonic() - start}")
	return execution


@then(parsers.parse("l'audit complet a duré moins de {seconds:d} secondes"))
def lasted(execution: Execution, seconds: int) -> None:
	(duration,) = [line for line in execution.information if line.startswith("durée ")]
	assert float(duration.removeprefix("durée ")) < seconds, duration


@then(parsers.parse("le deuxième sonore est à l'état « {state} »"))
def second_state(empty_database: Connection, sound: int, state: str) -> None:
	line = empty_database.execute("SELECT state::text FROM sounds WHERE id <> %s", (sound,)).fetchone()
	assert line == (state,)


@then(parsers.parse("la sortie d'erreur signale ce fichier en incident : « {text} »"))
def reported_incident(execution: Execution, file: Path, text: str) -> None:
	assert f"{file} : {text}" in execution.errors.splitlines(), execution.errors


@then(parsers.parse("l'examen d'un fichier est abandonné au bout de {minutes:d} minutes"))
def default_limit(minutes: int) -> None:
	assert timedelta(minutes=minutes) == check.AUDIT_LIMIT
