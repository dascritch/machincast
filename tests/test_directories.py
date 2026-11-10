"""Étapes de l'indexation récursive des répertoires de banques (https://github.com/dascritch/machincast/issues/9)."""

import logging
import re
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import TupleRow
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.database import Role, open_connection
from machincast.indexer import check
from machincast.indexer.check import Report
from machincast.indexer.decoding import Check, check_file
from machincast.indexer.directories import DIRECTORIES_LOCK
from machincast.indexer.indexer import index as index_full
from machincast.indexer.indexer import index_sound
from tests.database_fixtures import sample_database_parameters
from tests.indexing_steps import Execution, OtherIndexing, count, insert_sound, per_file
from tests.sounds import corrupt, sample_copy

scenarios("directories.feature")

Connection = psycopg.Connection[tuple[object, ...]]
ITEM = re.compile(r"« ([^»]+) »")
# Extension du fichier demandé → fichier de test à copier (tests/fichiers-sonores).
FORMATS = {
	"mp3": "mp3",
	"m4a": "m4a",
	"aac": "aac",
	"ogg": "ogg",
	"flac": "flac",
	"wav": "wav",
}


@pytest.fixture
def root(tmp_path: Path) -> Path:
	"""Répertoire temporaire où se trouvent les répertoires des banques du scénario."""
	path = tmp_path / "radio"
	path.mkdir()
	return path


def bank(database: Connection, name: str) -> int:
	line = database.execute("SELECT id FROM banks WHERE internal_name = %s", (name,)).fetchone()
	if line is None:
		line = database.execute(
			"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (name,)
		).fetchone()
	assert line is not None
	return int(str(line[0]))


@given(parsers.parse("une banque « {name} » alimentée par le répertoire « {directory} »"))
def fed_bank(empty_database: Connection, root: Path, name: str, directory: str) -> None:
	empty_database.execute(
		"INSERT INTO bank_directories (bank_id, directory) VALUES (%s, %s)",
		(bank(empty_database, name), str(root / directory)),
	)


@given(parsers.re(r"le fichier « (?P<relative>[^»]+) », (?P<state>sain|endommagé|quelconque)"))
def file(tmp_path: Path, root: Path, relative: str, state: str) -> None:
	target = root / relative
	target.parent.mkdir(parents=True, exist_ok=True)
	if state == "quelconque":
		target.write_bytes(b"pas du son")
		return
	extension = target.suffix.lstrip(".").lower()
	chosen = "mp3"
	if state == "sain":
		chosen = FORMATS[extension]
	source = sample_copy(chosen, tmp_path)
	if state == "endommagé":
		corrupt(source, 1000, 1 / 3)
	shutil.move(source, target)


@given(parsers.parse("{number:d} fichiers sains dans le répertoire « {directory} »"))
def many_files(tmp_path: Path, root: Path, number: int, directory: str) -> None:
	"""Des copies d'un même FLAC sain, « s01.flac », « s02.flac »…"""
	source = sample_copy(FORMATS["flac"], tmp_path)
	(root / directory).mkdir(parents=True, exist_ok=True)
	for rank in range(1, number + 1):
		shutil.copyfile(source, root / directory / f"s{rank:02d}.flac")


@given(parsers.parse("la vérification lit les sonores par lots de {size:d}"))
def batches(monkeypatch: pytest.MonkeyPatch, size: int) -> None:
	monkeypatch.setattr(check, "BATCH", size)


@given(parsers.parse("« {relative} » a été retiré à la main de la banque « {name} »"))
def removes(empty_database: Connection, root: Path, relative: str, name: str) -> None:
	empty_database.execute(
		"DELETE FROM bank_sounds WHERE bank_id = %s AND sound_id = (SELECT id FROM sounds WHERE location = %s)",
		(bank(empty_database, name), str(root / relative)),
	)


@then(parsers.re(r"la banque « (?P<name>[^»]+) » contient, dans l'ordre, (?P<list_>.+)"))
def content(empty_database: Connection, root: Path, name: str, list_: str) -> None:
	lines = empty_database.execute(
		"SELECT s.location FROM bank_sounds bs JOIN sounds s ON s.id = bs.sound_id"
		" WHERE bs.bank_id = %s ORDER BY bs.position",
		(bank(empty_database, name),),
	).fetchall()
	assert [str(line[0]) for line in lines] == [str(root / relative) for relative in ITEM.findall(list_)]


@then(parsers.parse("le sonore de « {relative} » est à l'état « {state} »"))
def sound_state(empty_database: Connection, root: Path, relative: str, state: str) -> None:
	line = empty_database.execute(
		"SELECT state::text FROM sounds WHERE location = %s", (str(root / relative),)
	).fetchone()
	assert line is not None, f"aucun sonore pour {relative}"
	assert line[0] == state


@then(parsers.re(r"la base contient (?P<count>\d+) sonores?"))
def sound_count(empty_database: Connection, count: str) -> None:
	line = empty_database.execute("SELECT count(*) FROM sounds").fetchone()
	assert (line is not None) and (line[0] == int(count))


@then(
	parsers.parse(
		"la sortie d'erreur signale le répertoire « {directory} » comme introuvable, pour la banque « {name} »"
	)
)
def reported_directory(execution: Execution, root: Path, directory: str, name: str) -> None:
	lines = [line for line in execution.errors.splitlines() if str(root / directory) in line]
	assert lines, execution.errors
	assert ("introuvable" in lines[0]) and (name in lines[0]), lines[0]


@then("la sortie standard montre, ligne par ligne :")
def standard_output(execution: Execution, root: Path, datatable: list[list[str]]) -> None:
	"""Un chemin qui commence par « …/ » est dans le répertoire du scénario."""
	_header, *lines = datatable
	assert execution.information == [line.strip().replace("…/", f"{root}/") for (line,) in lines]


@then(parsers.parse("la sortie d'erreur signale « {path} », avec « {consequence} »"))
def reported_error(execution: Execution, root: Path, path: str, consequence: str) -> None:
	(line,) = execution.errors.splitlines()
	assert line.startswith(f"{path.replace('…/', f'{root}/')} : "), line
	assert line.endswith(f" ; {consequence}"), line


@then("le verrou de l'indexation rapide a été rendu dès la fin de l'indexation")
def rendering_lock(execution: Execution) -> None:
	assert execution.rendering_lock


@then(parsers.parse("Machin indexer se termine avec le code {code:d}"))
def finished_launching(launching: tuple[int, list[str]], code: int) -> None:
	obtained, messages = launching
	assert obtained == code, messages


# ─── Deux parcours en même temps (https://github.com/dascritch/machincast/issues/401) ───


@dataclass
class Background:
	"""Une indexation lancée dans un fil, et ce qu'elle a rendu ou levé."""

	feed: threading.Thread
	report: Report | None = None
	error: BaseException | None = None


@given(parsers.parse("une autre indexation qui enregistre « {relative} » dans la banque « {name} », sans avoir fini"))
def other_registering(
	empty_database: Connection, other_indexing: OtherIndexing, root: Path, relative: str, name: str
) -> None:
	"""Comme le parcours d'une autre indexation : le verrou des enregistrements, le nouveau sonore et son rattachement,
	dans une transaction encore ouverte."""
	connection = open_connection(*sample_database_parameters(), Role.INDEXING)
	connection.execute("SELECT pg_advisory_xact_lock(%s)", (DIRECTORIES_LOCK,))
	line = connection.execute(
		"INSERT INTO sounds (type, location, state) VALUES ('file', %s, 'preview') RETURNING id",
		(str(root / relative),),
	).fetchone()
	assert line is not None
	connection.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, 1)",
		(bank(empty_database, name), line[0]),
	)
	other_indexing.connections.append(connection)


def _waiting_lock(database: Connection) -> bool:
	"""Une connexion attend-elle un verrou consultatif ?"""
	line = database.execute("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted").fetchone()
	return (line is not None) and (int(str(line[0])) > 0)


@when("l'indexeur commence une indexation rapide", target_fixture="background")
def starts_indexing(empty_database: Connection) -> Background:
	"""L'indexation, dans un fil, jusqu'à ce qu'elle attende le verrou des enregistrements que tient l'autre."""

	def run() -> None:
		try:
			with open_connection(*sample_database_parameters(), Role.INDEXING) as connection:
				background.report = index_full(connection, full_audit=False)
		except BaseException as error:  # noqa: BLE001 : rendue au scénario
			background.error = error

	background = Background(threading.Thread(target=run, daemon=True))
	background.feed.start()
	end = time.monotonic() + 20
	while (not _waiting_lock(empty_database)) and (time.monotonic() < end) and (background.feed.is_alive()):
		time.sleep(0.05)
	assert _waiting_lock(empty_database), "l'indexation n'attend pas le verrou des enregistrements"
	return background


@then("l'indexation rapide se termine sans erreur")
def finished_without_error(background: Background) -> None:
	background.feed.join(60)
	assert not background.feed.is_alive()
	assert background.error is None, background.error
	assert background.report is not None


@then(parsers.re(r"la banque « (?P<name>[^»]+) » contient (?P<count>\d+) sonores?"))
def bank_count(empty_database: Connection, name: str, count: str) -> None:
	line = empty_database.execute(
		"SELECT count(*) FROM bank_sounds WHERE bank_id = %s", (bank(empty_database, name),)
	).fetchone()
	assert (line is not None) and (line[0] == int(count))


@given(parsers.parse("« {relative} » déplacé en « {destination} »"))
def move(root: Path, relative: str, destination: str) -> None:
	"""Un déplacement hors de MachinCast, comme le ferait le navigateur de fichiers."""
	target = root / destination
	target.parent.mkdir(parents=True, exist_ok=True)
	shutil.move(root / relative, target)


# ─── Durées des sonores d'une banque (https://github.com/dascritch/machincast/issues/195) ───


@given(
	parsers.re(
		r"la banque « (?P<name>[^»]+) » n'accepte que les sonores (?:d'au moins (?P<minimum>[\d,]+)"
		r"|d'au plus (?P<maximum>[\d,]+)|de (?P<de>[\d,]+) à (?P<a>[\d,]+)) secondes?"
	)
)
def bank_durations(
	empty_database: Connection, name: str, minimum: str | None, maximum: str | None, de: str | None, a: str | None
) -> None:
	bounds: list[timedelta | None] = []
	for value in ((minimum) or (de), (maximum) or (a)):
		bound = None
		if value is not None:
			bound = timedelta(seconds=count(value))
		bounds.append(bound)
	empty_database.execute(
		"UPDATE banks SET min_duration = %s, max_duration = %s WHERE id = %s", (*bounds, bank(empty_database, name))
	)


def _add(database: Connection, name: str, sound: object) -> None:
	identifier = bank(database, name)
	database.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position)"
		" SELECT %s, %s, COALESCE(MAX(position), 0) + 1 FROM bank_sounds WHERE bank_id = %s",
		(identifier, sound, identifier),
	)


def sound_of(database: Connection, root: Path, relative: str) -> int:
	line = database.execute("SELECT id FROM sounds WHERE location = %s", (str(root / relative),)).fetchone()
	assert line is not None, f"aucun sonore pour {relative}"
	return int(str(line[0]))


@given(parsers.parse("« {relative} » est ajouté à la main à la banque « {name} »"))
def adds_to_main(empty_database: Connection, root: Path, relative: str, name: str) -> None:
	_add(empty_database, name, sound_of(empty_database, root, relative))


@given(parsers.parse("le stream « {title} » est ajouté à la main à la banque « {name} »"))
def added_stream(empty_database: Connection, title: str, name: str) -> None:
	line = empty_database.execute(
		"INSERT INTO sounds (type, stream_url, title, state) VALUES ('stream', 'https://flux.exemple', %s, 'active')"
		" RETURNING id",
		(title,),
	).fetchone()
	assert line is not None
	_add(empty_database, name, line[0])


@given(parsers.re(r"la durée en base du sonore de « (?P<relative>[^»]+) » est de (?P<seconds>[\d,]+) secondes"))
def duration_in_database(empty_database: Connection, root: Path, relative: str, seconds: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET duration = %s WHERE id = %s",
		(timedelta(seconds=count(seconds)), sound_of(empty_database, root, relative)),
	)


@given(parsers.parse("un sonore à l'état « {state} », de durée inconnue, pour « {relative} »"))
def sound_without_duration(empty_database: Connection, root: Path, state: str, relative: str) -> None:
	"""Comme un fichier enregistré par une indexation interrompue avant de le vérifier."""
	insert_sound(empty_database, str(root / relative), state)


@when("l'indexeur fait une indexation rapide, en comptant ses requêtes", target_fixture="execution")
def counted_indexing(
	empty_database: Connection, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> Execution:
	"""Les requêtes de la connexion de l'indexation, sans celles du scénario
	(https://github.com/dascritch/machincast/issues/390)."""
	queries: list[object] = []
	original = psycopg.Connection.execute

	def execute(
		connection: psycopg.Connection[TupleRow], query: object, *arguments: object, **options: object
	) -> object:
		if connection is not empty_database:
			queries.append(query)
		return original(connection, query, *arguments, **options)  # type: ignore[arg-type]

	monkeypatch.setattr(psycopg.Connection, "execute", execute)
	caplog.clear()
	with (
		caplog.at_level(logging.INFO, logger="machincast"),
		open_connection(*sample_database_parameters(), Role.INDEXING) as c,
	):
		queries.clear()
		report = index_full(c)
	monkeypatch.undo()
	lines = per_file(caplog.records)
	anomalies = [message for level, message in lines if level >= logging.WARNING]
	information = [message for level, message in lines if level == logging.INFO]
	execution = Execution(report, "\n".join(anomalies), information)
	execution.queries = len(queries)
	return execution


@then(parsers.parse("l'indexation a fait au plus {maximum:d} requêtes"))
def at_most_queries(execution: Execution, maximum: int) -> None:
	assert execution.queries <= maximum, execution.queries


@when(
	"l'indexeur fait une indexation rapide, arrêtée pendant la vérification du premier sonore",
	target_fixture="execution",
)
def stopped_during_check(empty_database: Connection, caplog: pytest.LogCaptureFixture) -> Execution:
	"""L'arrêt est demandé pendant le décodage du premier sonore : la vérification s'arrête avant le suivant."""
	stop = threading.Event()

	def check(path: Path, *, silence_threshold: float | None = None) -> Check:
		stop.set()
		return check_file(path, silence_threshold=silence_threshold)

	caplog.clear()
	with (
		caplog.at_level(logging.INFO, logger="machincast"),
		open_connection(*sample_database_parameters(), Role.INDEXING) as c,
	):
		report = index_full(c, check=check, stop=stop)
	lines = per_file(caplog.records)
	anomalies = [message for level, message in lines if level >= logging.WARNING]
	information = [message for level, message in lines if level == logging.INFO]
	return Execution(report, "\n".join(anomalies), information)


@when(
	parsers.parse("l'indexeur vérifie seulement le sonore de « {relative} », en audit complet"),
	target_fixture="execution",
)
def a_only_sound(empty_database: Connection, root: Path, caplog: pytest.LogCaptureFixture, relative: str) -> Execution:
	"""Comme Machin_indexer --full-audit --sound N."""
	caplog.clear()
	sound = sound_of(empty_database, root, relative)
	with (
		caplog.at_level(logging.INFO, logger="machincast"),
		open_connection(*sample_database_parameters(), Role.INDEXING) as c,
	):
		report = index_sound(c, sound, full_audit=True)
	lines = per_file(caplog.records)
	anomalies = [message for level, message in lines if level >= logging.WARNING]
	information = [message for level, message in lines if level == logging.INFO]
	return Execution(report, "\n".join(anomalies), information)


@then(parsers.parse("la banque « {name} » ne contient aucun sonore"))
def empty_bank(empty_database: Connection, name: str) -> None:
	line = empty_database.execute(
		"SELECT count(*) FROM bank_sounds WHERE bank_id = %s", (bank(empty_database, name),)
	).fetchone()
	assert line == (0,), line


@then(parsers.parse("la banque « {name} » contient le stream « {title} »"))
def contains_stream(empty_database: Connection, name: str, title: str) -> None:
	line = empty_database.execute(
		"SELECT count(*) FROM bank_sounds bs JOIN sounds s ON s.id = bs.sound_id"
		" WHERE bs.bank_id = %s AND s.title = %s",
		(bank(empty_database, name), title),
	).fetchone()
	assert line == (1,), line
