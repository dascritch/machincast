"""Scénarios des sonores des répertoires personnels (https://github.com/dascritch/machincast/issues/381).

Le répertoire personnel et le répertoire d'accueil sont simulés dans le répertoire du scénario ; la base est la base de
test, jamais celle de production. Seules des copies de fichiers de test se déplacent.
"""

import dataclasses
import hashlib
import logging
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import access, admin_queries, installation, personal
from machincast.configuration import Configuration
from tests.database_fixtures import configuration_test

scenarios("personal_sounds.feature")

Connection = psycopg.Connection[tuple[object, ...]]


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(found=None, error=None, contents={}, code=None)


def _path(tmp_path: Path, text: str) -> Path:
	return tmp_path / text


def _list(tmp_path: Path, text: str) -> list[Path]:
	found = []
	for name in text.split("», «"):
		found.append(_path(tmp_path, name.strip(" «»")))
	return found


@given(parsers.parse("le répertoire personnel « {home} » et le répertoire d'accueil « {welcome} »"))
def homes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, home: str, welcome: str) -> None:
	_path(tmp_path, home).mkdir()
	_path(tmp_path, welcome).mkdir()
	monkeypatch.setenv(access.PERSONAL_ENVIRONMENT, str(_path(tmp_path, home)))
	monkeypatch.setenv(access.WELCOME_ENVIRONMENT, str(_path(tmp_path, welcome)))


def _file(tmp_path: Path, context: SimpleNamespace, name: str) -> Path:
	path = _path(tmp_path, name)
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_bytes(f"son {name}".encode())
	context.contents[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
	return path


def _sound(connection: Connection, path: Path) -> int:
	line = connection.execute(
		"INSERT INTO sounds (type, location, title) VALUES ('file', %s, %s) RETURNING id", (str(path), path.name)
	).fetchone()
	assert line is not None
	return int(str(line[0]))


@given(parsers.parse("la banque « {bank} », du répertoire « {directory} », avec le sonore « {sound} »"))
def bank(
	tmp_path: Path, context: SimpleNamespace, empty_database: Connection, bank: str, directory: str, sound: str
) -> None:
	path = _file(tmp_path, context, sound)
	sound_id = _sound(empty_database, path)
	line = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (bank,)
	).fetchone()
	assert line is not None
	empty_database.execute(
		"INSERT INTO bank_directories (bank_id, directory) VALUES (%s, %s)", (line[0], str(_path(tmp_path, directory)))
	)
	empty_database.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, 1)", (line[0], sound_id)
	)
	empty_database.commit()


@given(parsers.parse("le sonore ajouté « {sound} »"))
def added(tmp_path: Path, context: SimpleNamespace, empty_database: Connection, sound: str) -> None:
	_sound(empty_database, _file(tmp_path, context, sound))
	empty_database.commit()


@given(parsers.parse("le fichier « {name} » déjà présent"))
def present(tmp_path: Path, context: SimpleNamespace, name: str) -> None:
	path = _path(tmp_path, name)
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_bytes(b"autre son")
	context.contents["présent"] = hashlib.sha256(b"autre son").hexdigest()


@given("une base qui refuse la mise à jour des emplacements")
def refusing(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(
		admin_queries, "RELOCATE", "UPDATE {table} SET {column} = nothing_like_this(%s, %s, %s, %s, %s)"
	)


@when("les sonores des répertoires personnels sont listés")
def listed(context: SimpleNamespace, empty_database: Connection) -> None:
	context.found = personal.find(empty_database)


@when("les sonores des répertoires personnels sont déplacés")
def moved(context: SimpleNamespace, empty_database: Connection) -> None:
	moves = personal.plan(personal.find(empty_database), access.welcome())
	assert personal.foreign(moves) == []
	try:
		personal.move(empty_database, moves)
	except psycopg.Error as error:
		empty_database.rollback()
		context.error = error


@when("les sonores des répertoires personnels sont retirés de la base")
def forgotten(empty_database: Connection) -> None:
	personal.forget(empty_database, personal.find(empty_database))


@then(parsers.parse("la liste est {names}"))
def listing(tmp_path: Path, context: SimpleNamespace, names: str) -> None:
	assert [*context.found.directories, *context.found.files] == _list(tmp_path, names)


@then(parsers.parse("le fichier « {present} » existe, et plus « {absent} »"))
def exists(tmp_path: Path, present: str, absent: str) -> None:
	assert _path(tmp_path, present).is_file()
	assert not _path(tmp_path, absent).exists()


@then(parsers.parse("la banque « {bank} » a le répertoire « {directory} »"))
def bank_directory(tmp_path: Path, empty_database: Connection, bank: str, directory: str) -> None:
	rows = empty_database.execute(
		"SELECT d.directory FROM bank_directories d JOIN banks b ON b.id = d.bank_id WHERE b.internal_name = %s",
		(bank,),
	).fetchall()
	assert rows == [(str(_path(tmp_path, directory)),)]


@then(parsers.parse("la banque « {bank} » n'a plus de répertoire"))
def no_directory(empty_database: Connection, bank: str) -> None:
	rows = empty_database.execute(
		"SELECT d.directory FROM bank_directories d JOIN banks b ON b.id = d.bank_id WHERE b.internal_name = %s",
		(bank,),
	).fetchall()
	assert rows == []


@then(parsers.parse("les sonores sont {names}"))
def sounds(tmp_path: Path, empty_database: Connection, names: str) -> None:
	rows = empty_database.execute("SELECT location FROM sounds WHERE deleted_at IS NULL ORDER BY location").fetchall()
	expected = []
	for path in _list(tmp_path, names):
		expected.append((str(path),))
	assert rows == expected


@then("le contenu des fichiers déplacés est inchangé")
def same_content(tmp_path: Path, context: SimpleNamespace) -> None:
	for path in access.welcome().rglob("*.flac"):
		assert hashlib.sha256(path.read_bytes()).hexdigest() == context.contents[path.name], path


@then(parsers.parse("le fichier « {name} » est inchangé"))
def unchanged(tmp_path: Path, context: SimpleNamespace, name: str) -> None:
	assert hashlib.sha256(_path(tmp_path, name).read_bytes()).hexdigest() == context.contents["présent"]


@then("le déplacement échoue")
def failed(context: SimpleNamespace) -> None:
	assert context.error is not None


def _configuration(production: str) -> Configuration:
	"""La configuration des tests, dont la « production » est la base de test : une commande de l'installation ne
	touche jamais la vraie."""
	configuration = configuration_test()
	return dataclasses.replace(
		configuration, database=dataclasses.replace(configuration.database, production=production)
	)


@when(parsers.parse("la commande d'installation « {command} » est lancée sur la base de test"))
def installation_command(context: SimpleNamespace, capsys: pytest.CaptureFixture[str], command: str) -> None:
	context.code = installation.ACTIONS[command](_configuration(configuration_test().database.test))
	context.written = capsys.readouterr().out


@when(parsers.parse("la commande d'installation « {command} » est lancée sur une base introuvable"))
def installation_without_database(context: SimpleNamespace, caplog: pytest.LogCaptureFixture, command: str) -> None:
	caplog.set_level(logging.INFO, logger="machincast")
	context.code = installation.ACTIONS[command](_configuration("machincast_base_qui_n_existe_pas"))


@then(parsers.parse("la commande rend le code {code:d}"))
def returns(context: SimpleNamespace, code: int) -> None:
	assert context.code == code


@then(parsers.parse("elle écrit {names}"))
def writes(tmp_path: Path, context: SimpleNamespace, names: str) -> None:
	expected = ""
	for path in _list(tmp_path, names):
		expected += f"{path}\n"
	assert context.written == expected


@then(parsers.parse("le log dit « {text} »"))
def logged(caplog: pytest.LogCaptureFixture, text: str) -> None:
	messages = []
	for record in caplog.records:
		messages.append(record.getMessage())
	found = False
	for message in messages:
		if text in message:
			found = True
	assert found, messages
