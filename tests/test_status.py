"""Scénarios de Machin status (https://github.com/dascritch/machincast/issues/518).

Comme la purge (test_purge.py), la commande lit la base de test, désignée comme base de production d'une
configuration du scénario. Son horloge est fixée, en heure de Paris, et la sortie standard est relevée à chaque appel.
"""

import dataclasses
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import programs, service, status
from machincast.cli import create_analyser
from machincast.clock import FixedClock
from machincast.configuration import Configuration
from tests.database_fixtures import configuration_test

scenarios("status.feature")

PARIS = ZoneInfo("Europe/Paris")
Connection = psycopg.Connection[tuple[object, ...]]


@dataclasses.dataclass
class Answer:
	code: int = -1
	text: str = ""


@pytest.fixture
def answer() -> Answer:
	return Answer()


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


@given(parsers.parse("l'horloge de l'état à « {instant} »"))
def clock(monkeypatch: pytest.MonkeyPatch, instant: str) -> None:
	monkeypatch.setattr(status, "CLOCK", FixedClock(datetime.fromisoformat(instant).replace(tzinfo=PARIS)))


@given("le service de diffusion est installé")
def service_installed(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(service, "read_state", lambda: service.ServiceState(installed=True, active="active"))


@given("le service de diffusion n'est pas installé")
def service_missing(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(service, "read_state", lambda: service.ABSENT)


@given(parsers.parse("le nom de la radio est « {name} »"), target_fixture="configuration")
def radio_name(configuration: Configuration, name: str) -> Configuration:
	return dataclasses.replace(configuration, metadata=dataclasses.replace(configuration.metadata, public_text=name))


def _moment(text: str) -> datetime | None:
	if text == "":
		return None
	return datetime.fromisoformat(text).replace(tzinfo=PARIS)


def _program(name: str, arguments: tuple[str, ...]) -> programs.Program:
	return programs.Program(
		pid=4242, account="radio", name=name, arguments=arguments, service=False, directory="/home/radio/machincast"
	)


@given("Machin player qui diffuse")
def player_broadcasting(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(programs, "ongoing", lambda: [_program("player", ())])


@given("Machin player en simulation")
def player_simulating(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(programs, "ongoing", lambda: [_program("player", ("--simulation", "09:00", "10:00"))])


@given("aucun Machin player ne tourne")
def no_player(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(programs, "ongoing", lambda: [_program("indexer", ())])


@given("les événements en base :")
def events(empty_database: Connection, datatable: list[list[str]]) -> None:
	_header, *lines = datatable
	for name, priority, start, end in lines:
		empty_database.execute(
			"INSERT INTO events (internal_name, priority, starts_at, ends_at) VALUES (%s, %s, %s, %s)",
			(name, priority, _moment(start), _moment(end)),
		)


@given(parsers.parse("l'événement « {name} » est supprimé"))
def event_deleted(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE events SET deleted_at = clock_timestamp() WHERE internal_name = %s", (name,))


@when(parsers.parse("je lance « {command} »"))
def launch(configuration: Configuration, answer: Answer, capsys: pytest.CaptureFixture[str], command: str) -> None:
	_machin, _binary, *arguments = command.split()
	capsys.readouterr()
	analyser = create_analyser(status.EXECUTABLE, status.DESCRIPTION)
	status.add_options(analyser)
	try:
		options = analyser.parse_args(arguments)
	except SystemExit as refusal:
		answer.code = int(str(refusal.code))
		return
	answer.code = status.run(configuration, options)
	answer.text = capsys.readouterr().out


@then(parsers.parse("l'état répond « {text} » avec le code {code:d}"))
def answers(answer: Answer, text: str, code: int) -> None:
	assert (answer.text, answer.code) == (f"{text}\n", code)


@then(parsers.parse("l'état n'écrit rien et se termine avec le code {code:d}"))
def writes_nothing(answer: Answer, code: int) -> None:
	assert (answer.text, answer.code) == ("", code)


@then(parsers.parse("l'état est refusé avec le code {code:d}"))
def refused(answer: Answer, code: int) -> None:
	assert answer.code == code


@then("l'état écrit les lignes :")
def writes_lines(answer: Answer, datatable: list[list[str]]) -> None:
	_header, *rows = datatable
	expected = []
	for key, value in rows:
		expected.append(f"{key}\t{value}")
	assert answer.text.splitlines() == expected, answer.text
	assert answer.code == 0
