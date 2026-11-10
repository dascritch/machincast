"""Scénarios du statut des indexations (https://github.com/dascritch/machincast/issues/392), sur la base de test."""

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.database import Role, open_connection
from machincast.indexer.__main__ import EXECUTABLE
from machincast.indexer.check import Report
from machincast.indexer.directories import index_directories
from machincast.interface import indexing_status
from tests.database_fixtures import sample_database_parameters
from tests.sounds import sample_copy

scenarios("indexing_status.feature")

Connection = psycopg.Connection[tuple[object, ...]]


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(status=None, window=None, banks={})


def _bank(connection: Connection, context: SimpleNamespace, name: str, directories: list[str]) -> None:
	line = connection.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (name,)
	).fetchone()
	assert line is not None
	context.banks[name] = line[0]
	for directory in directories:
		connection.execute("INSERT INTO bank_directories (bank_id, directory) VALUES (%s, %s)", (line[0], directory))


@given(
	parsers.re(
		r"les banques « (?P<first>[^»]+) », des répertoires « (?P<a>[^»]+) » et « (?P<b>[^»]+) », et « (?P<second>[^»]+) »,"
		r" des répertoires « (?P<c>[^»]+) » et « (?P<d>[^»]+) »"
	)
)
def banks(
	empty_database: Connection, context: SimpleNamespace, first: str, a: str, b: str, second: str, c: str, d: str
) -> None:
	_bank(empty_database, context, first, [a, b])
	_bank(empty_database, context, second, [c, d])


@given("un démarrage de Machin_indexer noté dans le log il y a une heure")
def started(empty_database: Connection) -> None:
	empty_database.execute(
		"INSERT INTO log (logged_at, level, kind, message) VALUES (now() - interval '1 hour', 'info', 'start', %s)",
		(f"{EXECUTABLE} 0.9.0, pid 1234",),
	)
	# Un autre binaire, plus tard : il ne compte pas.
	empty_database.execute(
		"INSERT INTO log (logged_at, level, kind, message) VALUES (now(), 'info', 'start', 'Machin_player 0.9.0, pid 5')"
	)


@given(
	parsers.re(
		r"les répertoires « (?P<a>[^»]+) » et « (?P<b>[^»]+) » parcourus depuis, et « (?P<c>[^»]+) » parcouru avant"
	)
)
def scanned(empty_database: Connection, a: str, b: str, c: str) -> None:
	empty_database.execute(
		"UPDATE bank_directories SET scanned_at = now() - interval '10 minutes' WHERE directory = ANY(%s)", ([a, b],)
	)
	empty_database.execute(
		"UPDATE bank_directories SET scanned_at = now() - interval '1 day' WHERE directory = %s", (c,)
	)


def _sounds(connection: Connection, count: int, checked: bool, audited: bool, prefix: str) -> None:
	for number in range(count):
		connection.execute(
			"INSERT INTO sounds (type, location, title, checked_at, audited_at, audit_threshold)"
			" VALUES ('file', %s, %s, CASE WHEN %s THEN now() END, CASE WHEN %s THEN now() END,"
			" CASE WHEN %s THEN -60 END)",
			(f"/sons/{prefix}-{number}.flac", f"{prefix} {number}", checked, audited, audited),
		)


@given(
	parsers.parse(
		"{none:d} sonore sans indexation, {summary:d} sonores à l'indexation sommaire et {complete:d} sonores à l'indexation complète"
	)
)
def sounds(empty_database: Connection, none: int, summary: int, complete: int) -> None:
	_sounds(empty_database, none, False, False, "aucune")
	_sounds(empty_database, summary, True, False, "sommaire")
	_sounds(empty_database, complete, True, True, "complete")


@given("un sonore supprimé et un stream")
def ignored(empty_database: Connection) -> None:
	empty_database.execute(
		"INSERT INTO sounds (type, location, title, deleted_at) VALUES ('file', '/sons/supprime.flac', 'supprimé', now())"
	)
	empty_database.execute(
		"INSERT INTO sounds (type, stream_url, title) VALUES ('stream', 'https://exemple.org/flux', 'flux')"
	)


@given("aucun démarrage de Machin_indexer dans le log")
def no_start(empty_database: Connection) -> None:
	empty_database.execute("DELETE FROM log WHERE kind = 'start'")


@when("le statut des indexations est lu")
def read(empty_database: Connection, context: SimpleNamespace) -> None:
	context.status = indexing_status.read(empty_database)


@then(parsers.parse("il compte {to_scan:d} répertoire à scanner et {done:d} répertoires scannés"))
def directories(context: SimpleNamespace, to_scan: int, done: int) -> None:
	assert (context.status.to_scan, context.status.scanned) == (to_scan, done)


@then(
	parsers.parse(
		"il compte {found:d} sonores détectés, {summary:d} à l'indexation sommaire et {complete:d} à l'indexation complète"
	)
)
def counted(context: SimpleNamespace, found: int, summary: int, complete: int) -> None:
	assert (context.status.sounds, context.status.summary, context.status.complete) == (found, summary, complete)


@given("la fenêtre « Statut des indexations » ouverte")
@when("j'ouvre « Statut des indexations… » dans le menu « Maintenance »")
def opened(empty_database: Connection, context: SimpleNamespace, qtbot: QtBot) -> None:
	context.window = indexing_status.StatusWindow(empty_database)
	qtbot.addWidget(context.window)
	context.window.open_()
	assert context.window.timer.isActive()


@when(parsers.parse("le répertoire « {directory} » est parcouru"))
def scanned_now(empty_database: Connection, directory: str) -> None:
	empty_database.execute("UPDATE bank_directories SET scanned_at = now() WHERE directory = %s", (directory,))


@when("la fenêtre se met à jour")
def refreshed(context: SimpleNamespace, qtbot: QtBot) -> None:
	before = context.window.status
	qtbot.waitUntil(lambda: context.window.status != before, timeout=indexing_status.REFRESH * 3)


@then("la fenêtre « Statut des indexations » montre :")
def shown(context: SimpleNamespace, datatable: list[list[str]]) -> None:
	ui = context.window.ui
	assert context.window.windowTitle() == "Statut des indexations"
	values = {
		ui.to_scan_caption.text(): ui.to_scan.text(),
		ui.scanned_caption.text(): ui.scanned.text(),
		ui.found_caption.text(): ui.found.text(),
		ui.summary_caption.text(): ui.summary.text(),
		ui.complete_caption.text(): ui.complete.text(),
	}
	_headers, *rows = datatable
	for line, value in rows:
		assert values[line.strip()] == value.strip(), values


@then(parsers.re(r"le camembert « (?P<title>[^»]+) » a les parts : (?P<parts>.+)"))
def pie(context: SimpleNamespace, title: str, parts: str) -> None:
	charts = {
		context.window.directories_pie.title: context.window.directories_pie,
		context.window.sounds_pie.title: context.window.sounds_pie,
	}
	found = []
	for item in charts[title].slices:
		found.append(f"« {item.label} » {item.value}")
	assert ", ".join(found) == parts
	assert context.window.isVisible()
	charts[title].repaint()


@given(parsers.parse("une banque « {name} » du répertoire de test « {directory} », qui contient un fichier flac"))
def live_bank(empty_database: Connection, context: SimpleNamespace, tmp_path: Path, name: str, directory: str) -> None:
	folder = tmp_path / directory
	folder.mkdir()
	sample_copy("flac", folder)
	context.directory = folder
	_bank(empty_database, context, name, [str(folder)])


@when("l'indexeur parcourt les répertoires des banques")
def indexed(empty_database: Connection) -> None:
	with open_connection(*sample_database_parameters(), Role.INDEXING) as connection:
		index_directories(connection, Report())
		connection.commit()


@then(parsers.parse("le répertoire « {directory} » a une date de parcours"))
def has_date(empty_database: Connection, context: SimpleNamespace, directory: str) -> None:
	line = empty_database.execute(
		"SELECT scanned_at > now() - %s FROM bank_directories WHERE directory = %s",
		(timedelta(minutes=5), str(context.directory)),
	).fetchone()
	assert line == (True,)
