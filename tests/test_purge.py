"""Scénarios de la purge de la base (https://github.com/dascritch/machincast/issues/268).

Comme la maintenance (test_database_maintenance.py), la purge travaille sur la base de test, désignée comme base de
production d'une configuration du scénario, modifiée après lecture : le chargement d'un fichier refuse une base de
production égale à la base de test. Les dates des tableaux sont prises à midi, heure de Paris.
"""

import dataclasses
import logging
import re
import subprocess
import time
import tomllib
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import purge
from machincast.cli import create_analyser
from machincast.clock import FixedClock
from machincast.configuration import PROJECT_DIRECTORY, Configuration
from tests.database_fixtures import configuration_test

scenarios("purge.feature")

PARIS = ZoneInfo("Europe/Paris")
Connection = psycopg.Connection[tuple[object, ...]]


@dataclasses.dataclass
class Execution:
	code: int = -1
	information: list[str] = dataclasses.field(default_factory=list)
	errors: list[str] = dataclasses.field(default_factory=list)


@pytest.fixture
def execution() -> Execution:
	return Execution()


def _day(date: str) -> datetime:
	return datetime.fromisoformat(f"{date} 12:00:00").replace(tzinfo=PARIS)


def _instant(text: str) -> datetime:
	return datetime.fromisoformat(text).replace(tzinfo=PARIS)


@given("une configuration dont la base de production est la base de test", target_fixture="configuration")
def configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_database: Connection) -> Configuration:
	monkeypatch.setenv("TZ", "Europe/Paris")
	time.tzset()
	fetched = configuration_test()
	database = dataclasses.replace(fetched.database, production=fetched.database.test)
	return dataclasses.replace(fetched, database=database, path=tmp_path / "machincast.toml")


@given("une configuration dont la base de production est injoignable", target_fixture="configuration")
def unreachable_configuration(configuration: Configuration, tmp_path: Path) -> Configuration:
	database = dataclasses.replace(configuration.database, socket=tmp_path / "sans-postgresql")
	return dataclasses.replace(configuration, database=database)


@given(parsers.parse("l'horloge de la purge au « {instant} »"))
def clock(monkeypatch: pytest.MonkeyPatch, instant: str) -> None:
	monkeypatch.setattr(purge, "CLOCK", FixedClock(_instant(instant)))


@given(parsers.parse("la durée de péremption de {days:d} jours dans la configuration"), target_fixture="configuration")
def retention(configuration: Configuration, days: int) -> Configuration:
	return dataclasses.replace(configuration, database=dataclasses.replace(configuration.database, retention=days))


def _play(
	connection: Connection,
	title: str,
	start: datetime,
	end: datetime,
	id_sound: object = None,
	location: str | None = None,
) -> None:
	play = uuid.uuid4()
	connection.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, location, title)"
		" VALUES (%s, 'start', %s, %s, %s, %s)",
		(play, start, id_sound, location, title),
	)
	connection.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, location, title, played_duration,"
		" without_incident) VALUES (%s, 'end', %s, %s, %s, %s, %s, true)",
		(play, end, id_sound, location, title, end - start),
	)


@given("les passages de l'airplay, et autant de lignes du log :")
def plays_and_log(empty_database: Connection, datatable: list[list[str]]) -> None:
	_header, *lines = datatable
	for date, title in lines:
		moment = _day(date)
		_play(empty_database, title, moment.replace(minute=0), moment.replace(minute=3))
		empty_database.execute(
			"INSERT INTO log (logged_at, level, kind, message) VALUES (%s, 'warning', 'essai', %s)",
			(moment, title),
		)


def _sound(connection: Connection, name: str, location: str) -> object:
	line = connection.execute(
		"INSERT INTO sounds (type, location, title) VALUES ('file', %s, %s) RETURNING id", (location, name)
	).fetchone()
	assert line is not None
	return line[0]


@given("les éléments en base :")
def items(empty_database: Connection, datatable: list[list[str]]) -> None:
	_header, *lines = datatable
	for category, name, deleted, disappeared in lines:
		deleted_at = None
		if deleted:
			deleted_at = _day(deleted)
		if category == "sonore":
			identifier = _sound(empty_database, name, f"/srv/{name}.flac")
			empty_database.execute("UPDATE sounds SET deleted_at = %s WHERE id = %s", (deleted_at, identifier))
			if disappeared:
				empty_database.execute(
					"UPDATE sounds SET state = 'missing', missing_at = %s WHERE id = %s",
					(_day(disappeared), identifier),
				)
		elif category == "banque":
			empty_database.execute(
				"INSERT INTO banks (internal_name, mode, deleted_at) VALUES (%s, 'sequential', %s)", (name, deleted_at)
			)
		elif category == "séquence":
			empty_database.execute(
				"INSERT INTO sequences (internal_name, deleted_at) VALUES (%s, %s)", (name, deleted_at)
			)
		else:
			assert category == "événement", category
			empty_database.execute(
				"INSERT INTO events (internal_name, priority, starts_at, deleted_at) VALUES (%s, 'show', %s, %s)",
				(name, _day("2026-09-01"), deleted_at),
			)


@given(parsers.parse("un passage du sonore « {title} » le {date}"))
def sound_play(empty_database: Connection, title: str, date: str) -> None:
	line = empty_database.execute("SELECT id, location FROM sounds WHERE title = %s", (title,)).fetchone()
	assert line is not None
	moment = _day(date)
	_play(empty_database, title, moment, moment.replace(minute=3), line[0], str(line[1]))


@given(parsers.parse("un passage « {title} », commencé le « {start} » et fini le « {end} »"))
def play_to_straddling(empty_database: Connection, title: str, start: str, end: str) -> None:
	_play(empty_database, title, _instant(start), _instant(end))


@given(parsers.parse("le fichier sonore « {path} » du sonore « {title} », supprimé le {date}"))
def deleted_file(empty_database: Connection, configuration: Configuration, path: str, title: str, date: str) -> None:
	file = Path(path.replace("…/", f"{configuration.path.parent}/"))
	file.parent.mkdir(parents=True, exist_ok=True)
	file.write_bytes(b"fLaC un vieux sonore")
	identifier = _sound(empty_database, title, str(file))
	empty_database.execute("UPDATE sounds SET deleted_at = %s WHERE id = %s", (_day(date), identifier))


@given(parsers.parse("le feed « {feed} », suivi par le stream « {stream} », supprimé le {date}"))
def feed_and_stream(empty_database: Connection, feed: str, stream: str, date: str) -> None:
	empty_database.execute("INSERT INTO feeds (name, url) VALUES (%s, 'http://localhost:8000/direct')", (feed,))
	empty_database.execute(
		"INSERT INTO sounds (type, feed_id, title, deleted_at) SELECT 'stream', id, %s, %s FROM feeds WHERE name = %s",
		(stream, _day(date), feed),
	)


@when(parsers.parse("je lance « {command} »"))
def launch(configuration: Configuration, execution: Execution, caplog: pytest.LogCaptureFixture, command: str) -> None:
	_machin, _binary, *arguments = command.split()
	analyser = create_analyser(purge.EXECUTABLE, purge.DESCRIPTION)
	options = analyser.parse_args(arguments)
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		execution.code = purge.run(configuration, options)
	execution.information = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
	execution.errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


@then(parsers.parse("la purge se termine avec le code {code:d}"))
def output_code(execution: Execution, code: int) -> None:
	assert execution.code == code, (execution.information, execution.errors)


@then(parsers.parse("la purge a annoncé « {text} »"))
def announces(execution: Execution, text: str) -> None:
	assert text in execution.information, execution.information


@then("la purge n'a rien signalé")
def reported_nothing(execution: Execution) -> None:
	assert execution.errors == []


@then("la purge a signalé une base de données injoignable")
def unreachable(execution: Execution) -> None:
	assert any(error.startswith("base de données injoignable") for error in execution.errors), execution.errors


def _list(text: str) -> list[str]:
	return sorted(name.strip().strip("«»").strip() for name in text.split(","))


@then(parsers.parse("l'airplay garde les passages « {titles} »"))
def kept_airplay(empty_database: Connection, titles: str) -> None:
	lines = empty_database.execute("SELECT DISTINCT title FROM airplay ORDER BY title").fetchall()
	assert [title for (title,) in lines] == _list(titles)


@then(parsers.parse("l'airplay garde le début et la fin du passage « {title} »"))
def integer_airplay(empty_database: Connection, title: str) -> None:
	lines = empty_database.execute(
		"SELECT line_type::text AS genre FROM airplay WHERE title = %s ORDER BY line_type", (title,)
	).fetchall()
	assert lines == [("start",), ("end",)]


@then(parsers.parse("l'airplay garde le passage « {title} », à l'emplacement « {location} », sans sonore en base"))
def airplay_without_sound(empty_database: Connection, title: str, location: str) -> None:
	lines = empty_database.execute("SELECT title, location, sound_id FROM airplay").fetchall()
	assert lines == [(title, location, None), (title, location, None)]
	assert empty_database.execute("SELECT count(*) FROM sounds").fetchone() == (0,)


@then(parsers.parse("le log garde ses lignes du {date}, et une ligne « purge » qui reprend l'annonce"))
def kept_log(empty_database: Connection, execution: Execution, date: str) -> None:
	lines = empty_database.execute("SELECT logged_at, level::text, kind, message FROM log ORDER BY id").fetchall()
	kept, purged = lines
	assert kept[0] == _day(date)
	assert purged[1:] == ("info", "purge", execution.information[-1])


TABLES = {
	"sonores": ("sounds", "title"),
	"banques": ("banks", "internal_name"),
	"événements": ("events", "internal_name"),
}


@then(parsers.parse("en base restent les {category} « {names} »"))
def remain(empty_database: Connection, category: str, names: str) -> None:
	table, column = TABLES[category]
	lines = empty_database.execute(f"SELECT {column} FROM {table} ORDER BY {column}").fetchall()  # noqa: S608
	assert [name for (name,) in lines] == _list(names)


@then(parsers.parse("en base ne reste aucune séquence"))
def no_sequence(empty_database: Connection) -> None:
	assert empty_database.execute("SELECT count(*) FROM sequences").fetchone() == (0,)


@then("en base ne reste aucun sonore")
def no_sound(empty_database: Connection) -> None:
	assert empty_database.execute("SELECT count(*) FROM sounds").fetchone() == (0,)


@then(parsers.parse("le fichier « {path} » est toujours là, intact"))
def intact_file(configuration: Configuration, path: str) -> None:
	file = Path(path.replace("…/", f"{configuration.path.parent}/"))
	assert file.read_bytes() == b"fLaC un vieux sonore"


@then(parsers.parse("aucun stream ne suit plus le feed « {feed} », qui peut se supprimer"))
def free_feed(empty_database: Connection, feed: str) -> None:
	assert empty_database.execute("SELECT count(*) FROM sounds").fetchone() == (0,)
	empty_database.execute("DELETE FROM feeds WHERE name = %s", (feed,))


@then(parsers.re(r"les sessions sautées de « (?P<name>[^»]+) » sont (?P<days>«.+)"))
def skipped_sessions(empty_database: Connection, name: str, days: str) -> None:
	lines = empty_database.execute(
		"SELECT s.day FROM event_skips s JOIN events e ON e.id = s.event_id WHERE e.internal_name = %s ORDER BY s.day",
		(name,),
	).fetchall()
	assert [str(day) for (day,) in lines] == re.findall(r"« ([^»]+) »", days)


@then(parsers.parse("« {binary} » est un binaire du wrapper, déclaré dans pyproject.toml"))
def wrapper_binary(binary: str) -> None:
	scripts = tomllib.loads((PROJECT_DIRECTORY / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
	assert scripts[f"Machin_{binary}"] == "machincast.purge:main"
	output = subprocess.run(
		[str(PROJECT_DIRECTORY / "bin" / "Machin"), "--binaries"], capture_output=True, text=True, timeout=30
	)
	assert binary in output.stdout.split(), output.stdout
