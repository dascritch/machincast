"""Étapes partagées des scénarios de l'indexeur : fichiers sonores, sonores en base, passage de l'indexeur.

Chargé comme greffon pytest par tests/conftest.py, pour servir à check.feature
(https://github.com/dascritch/machincast/issues/7) comme à tags.feature (https://github.com/dascritch/machincast/issues/8).
"""

import argparse
import csv
import dataclasses
import logging
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, then, when

from machincast.configuration import SILENCE_THRESHOLD
from machincast.database import Role, open_connection
from machincast.indexer.__main__ import run
from machincast.indexer.check import Report, report_text
from machincast.indexer.decoding import Check, Silences, UnavailableDecoder, check_file
from machincast.indexer.indexer import FULL_LOCK, LOCKS, QUICK_LOCK, index_sound
from machincast.indexer.indexer import index as index_full
from tests.database_fixtures import configuration_test, sample_database_parameters
from tests.sounds import corrupt, sample_copy

Connection = psycopg.Connection[tuple[object, ...]]
DECIMAL = r"\d+(?:,\d+)?"


def count(text: str) -> float:
	"""« 12,5 » → 12.5 : les scénarios écrivent les nombres à la française."""
	return float(text.replace(",", "."))


@dataclass
class Execution:
	report: Report
	errors: str
	information: list[str] = field(default_factory=list)
	"""Ce qui va sur la sortie standard, ligne par ligne : niveau INFO."""
	rendering_lock: bool = False
	"""Le verrou du mode de l'indexation était libre dès sa fin, sa connexion encore ouverte."""
	queries: int = 0
	"""Les requêtes de la connexion de l'indexation, quand le scénario les compte."""


def free_lock(lock: int) -> bool:
	"""Une autre connexion peut-elle prendre ce verrou de l'indexation ? Elle le rend aussitôt."""
	with open_connection(*sample_database_parameters(), Role.INDEXING) as other:
		taken = other.execute("SELECT pg_try_advisory_lock(%s)", (lock,)).fetchone()
		assert taken is not None
		other.execute("SELECT pg_advisory_unlock(%s)", (lock,))
		return bool(taken[0])


@dataclass
class OtherIndexing:
	"""D'autres connexions, qui tiennent chacune le verrou d'un mode de l'indexation, ou une transaction ouverte,
	jusqu'à leur fin."""

	connections: list[psycopg.Connection[tuple[object, ...]]] = field(default_factory=list)

	def finish(self) -> None:
		for connection in self.connections:
			connection.commit()
			connection.close()
		self.connections = []


@pytest.fixture
def other_indexing() -> Iterator[OtherIndexing]:
	other = OtherIndexing()
	yield other
	other.finish()


OTHER_LOCKS = {"une autre indexation rapide": QUICK_LOCK, "un autre audit complet": FULL_LOCK}
"""Le verrou que tient chaque autre indexation, désignée comme dans les scénarios
(https://github.com/dascritch/machincast/issues/401)."""


@given(
	parsers.re(r"(?P<others>(?:une autre indexation rapide|un autre audit complet)(?: et .+)?) en cours sur la base")
)
def ongoing_indexing(empty_database: Connection, other_indexing: OtherIndexing, others: str) -> None:
	for other in others.split(" et "):
		connection = open_connection(*sample_database_parameters(), Role.INDEXING)
		connection.execute("SELECT pg_advisory_lock(%s)", (OTHER_LOCKS[other],))
		connection.commit()
		other_indexing.connections.append(connection)


@when("l'autre indexation se termine")
def other_end(other_indexing: OtherIndexing) -> None:
	other_indexing.finish()


# ─── Fichiers ──────────────────────────────────────────────


@given(parsers.re(r"un fichier (?P<sound_format>\w+) sain"), target_fixture="file")
def healthy_file(tmp_path: Path, sound_format: str) -> Path:
	return sample_copy(sound_format, tmp_path)


@given(parsers.re(r"un fichier (?P<sound_format>\w+) tagué"), target_fixture="file")
def tagged_file(tmp_path: Path, sound_format: str) -> Path:
	return sample_copy(sound_format, tmp_path, "tags")


@when("je vérifie ce fichier", target_fixture="result")
def check(file: Path) -> Check | UnavailableDecoder:
	try:
		return check_file(file)
	except UnavailableDecoder as error:
		return error


# ─── Sonores en base ───────────────────────────────────────


def insert_sound(
	database: Connection,
	location: str,
	state: str,
	edited_fields: list[str] | None = None,
	duration: float | None = None,
) -> int:
	in_database = None
	if duration is not None:
		in_database = timedelta(seconds=duration)
	line = database.execute(
		"INSERT INTO sounds (type, location, state, edited_fields, duration)"
		" VALUES ('file', %s, %s, %s, %s) RETURNING id",
		(location, state, (edited_fields) or ([]), in_database),
	).fetchone()
	assert line is not None
	return int(str(line[0]))


@given(parsers.parse("un fichier « {name} » qui contient du texte"), target_fixture="file")
def text_file(tmp_path: Path, name: str) -> Path:
	file = tmp_path / name
	file.write_text("Ceci n'est pas un son, malgré son extension.\n", encoding="utf-8")
	return file


@given(parsers.parse("un fichier « {name} » vide"), target_fixture="file")
def empty_named_file(tmp_path: Path, name: str) -> Path:
	file = tmp_path / name
	file.write_bytes(b"")
	return file


@given(parsers.parse("une image « {name} »"), target_fixture="file")
def image(tmp_path: Path, name: str) -> Path:
	"""Le début d'une image PNG d'un pixel : sa signature et son en-tête suffisent à libmagic."""
	file = tmp_path / name
	header = b"\x00\x00\x00\x0dIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
	file.write_bytes(b"\x89PNG\r\n\x1a\n" + header)
	return file


@given("un fichier mp3 endommagé", target_fixture="file")
def damaged_file(tmp_path: Path) -> Path:
	file = sample_copy("mp3", tmp_path)
	corrupt(file, 1000, 1 / 3)
	return file


@given(parsers.parse("un sonore à l'état « {state} » pour ce fichier"), target_fixture="sound")
def sound_in_state(empty_database: Connection, file: Path, state: str) -> int:
	return insert_sound(empty_database, str(file), state)


@given(
	parsers.re(
		r"un sonore à l'état « active » pour ce fichier, dont la durée a été saisie à la main"
		rf" à (?P<seconds>{DECIMAL}) secondes"
	),
	target_fixture="sound",
)
def edited_duration_sound(empty_database: Connection, file: Path, seconds: str) -> int:
	return insert_sound(empty_database, str(file), "active", ["duration"], count(seconds))


@given(
	parsers.re(
		r"un sonore à l'état « (?P<state>[^»]+) » pour ce fichier,"
		r" dont le titre a été saisi à la main « (?P<title>[^»]+) »"
	),
	target_fixture="sound",
)
def edited_title_sound(empty_database: Connection, file: Path, state: str, title: str) -> int:
	sound = insert_sound(empty_database, str(file), state, ["title"])
	empty_database.execute("UPDATE sounds SET title = %s WHERE id = %s", (title, sound))
	return sound


@pytest.fixture
def indexings() -> list[tuple[datetime, datetime]]:
	"""Le début et la fin de chaque indexation du scénario, à l'heure de la base."""
	return []


@given("l'indexeur a fait une indexation rapide")
def prior_indexing(
	empty_database: Connection, caplog: pytest.LogCaptureFixture, indexings: list[tuple[datetime, datetime]]
) -> None:
	index(empty_database, caplog, full_audit=False, indexings=indexings)


@given(
	parsers.re(
		r"ce fichier remplacé, sous le même nom, par un fichier (?P<sound_format>\w+) (?P<state>tagué|endommagé)"
	)
)
def replaced_file(file: Path, tmp_path: Path, sound_format: str, state: str) -> None:
	"""Comme une synchronisation depuis un autre poste : le contenu change, la date de modification aussi."""
	directory = tmp_path / "remplacement"
	directory.mkdir(exist_ok=True)
	source = sample_copy(sound_format, directory, "tags")
	if state == "endommagé":
		source = sample_copy(sound_format, directory)
		corrupt(source, 1000, 1 / 3)
	file.write_bytes(source.read_bytes())
	latest = file.stat().st_mtime + 60
	os.utime(file, (latest, latest))


@given(parsers.parse("le sonore est passé à l'état « {state} »"))
def change_state(empty_database: Connection, sound: int, state: str) -> None:
	empty_database.execute("UPDATE sounds SET state = %s WHERE id = %s", (state, sound))


@given("ce fichier remplacé, sous le même nom, par un fichier flac tagué, en gardant sa date de modification")
def replaced_same_date_file(file: Path, tmp_path: Path) -> None:
	"""Comme une copie qui garde la date d'origine : seule la taille trahit le changement."""
	state = file.stat()
	directory = tmp_path / "remplacement"
	directory.mkdir(exist_ok=True)
	file.write_bytes(sample_copy("flac", directory, "tags").read_bytes())
	assert file.stat().st_size != state.st_size
	os.utime(file, ns=(state.st_atime_ns, state.st_mtime_ns))


@given("ce fichier supprimé")
def deleted_file(file: Path) -> None:
	file.unlink()


@given("ce fichier touché, sans changer son contenu")
def key_file(file: Path) -> None:
	latest = file.stat().st_mtime + 60
	os.utime(file, (latest, latest))


@given(parsers.parse("un deuxième fichier {sound_format} sain, dont le sonore est à l'état « {state} »"))
def sound_second(empty_database: Connection, tmp_path: Path, sound_format: str, state: str) -> None:
	directory = tmp_path / "deuxieme"
	directory.mkdir()
	insert_sound(empty_database, str(sample_copy(sound_format, directory)), state)


@given("un fichier introuvable", target_fixture="file")
def not_found_file(tmp_path: Path) -> Path:
	return tmp_path / "disparu.flac"


@given("un stream enregistré", target_fixture="stream")
def stream(empty_database: Connection) -> tuple[int, object]:
	line = empty_database.execute(
		"INSERT INTO sounds (type, stream_url) VALUES ('stream', 'https://flux.exemple/direct')"
		" RETURNING id, modified_at"
	).fetchone()
	assert line is not None
	return int(str(line[0])), line[1]


def now_in_database(database: Connection) -> datetime:
	line = database.execute("SELECT clock_timestamp()").fetchone()
	assert (line is not None) and (isinstance(line[0], datetime))
	return line[0]


ANALYSIS = " : analyse…"
"""La fin de la ligne qui ouvre l'analyse d'un fichier ; son résultat suit, en retrait, sans le nom
(https://github.com/dascritch/machincast/issues/413)."""


def per_file(records: list[logging.LogRecord]) -> list[tuple[int, str]]:
	"""Le niveau et le message de chaque ligne du journal, le résultat d'une analyse précédé du nom de son fichier,
	« chemin : résultat », comme on le lit : les scénarios parlent d'un fichier et de son verdict."""
	lines: list[tuple[int, str]] = []
	opened: str | None = None
	for saving in records:
		message = saving.getMessage()
		if (opened is not None) and (message.startswith("  ")):
			lines.append((saving.levelno, f"{opened} : {message.strip()}"))
			opened = None
			continue
		if opened is not None:
			lines.append((logging.INFO, f"{opened}{ANALYSIS}"))
			opened = None
		if message.endswith(ANALYSIS):
			opened = message.removesuffix(ANALYSIS)
			continue
		lines.append((saving.levelno, message))
	if opened is not None:
		lines.append((logging.INFO, f"{opened}{ANALYSIS}"))
	return lines


def index(
	empty_database: Connection,
	caplog: pytest.LogCaptureFixture,
	full_audit: bool,
	stop: threading.Event | None = None,
	indexings: list[tuple[datetime, datetime]] | None = None,
	silence_threshold: list[float] | None = None,
	force: bool = False,
) -> Execution:
	# Le compte qui lance les tests endosse déjà le rôle de l'indexation (vérifié par empty_database).
	caplog.clear()
	with (
		caplog.at_level(logging.INFO, logger="machincast"),
		open_connection(*sample_database_parameters(), Role.INDEXING) as c,
	):
		start = now_in_database(empty_database)
		threshold = SILENCE_THRESHOLD
		if silence_threshold:
			threshold = silence_threshold[-1]
		report = index_full(c, full_audit=full_audit, stop=stop, silence_threshold=threshold, force=force)
		if indexings is not None:
			indexings.append((start, now_in_database(empty_database)))
		rendering_lock = free_lock(LOCKS[full_audit])
	# Les anomalies et les erreurs vont sur la sortie d'erreur : niveau WARNING et au-delà.
	lines = per_file(caplog.records)
	anomalies = [message for level, message in lines if level >= logging.WARNING]
	information = [message for level, message in lines if level == logging.INFO]
	return Execution(report, "\n".join(anomalies), information, rendering_lock)


@when("l'indexeur fait un audit complet", target_fixture="execution")
def full_audit(
	empty_database: Connection,
	caplog: pytest.LogCaptureFixture,
	indexings: list[tuple[datetime, datetime]],
	silence_threshold: list[float],
) -> Execution:
	return index(empty_database, caplog, full_audit=True, indexings=indexings, silence_threshold=silence_threshold)


@when("l'indexeur fait une indexation rapide, dont l'arrêt est déjà demandé", target_fixture="execution")
def stopped_indexing(empty_database: Connection, caplog: pytest.LogCaptureFixture) -> Execution:
	stop = threading.Event()
	stop.set()
	return index(empty_database, caplog, full_audit=False, stop=stop)


@when("l'indexeur fait une indexation rapide", target_fixture="execution")
def quick_indexing(
	empty_database: Connection,
	caplog: pytest.LogCaptureFixture,
	indexings: list[tuple[datetime, datetime]],
	silence_threshold: list[float],
) -> Execution:
	"""Le seuil de silence sert aux sonores dont l'audit complet est demandé
	(https://github.com/dascritch/machincast/issues/114)."""
	return index(empty_database, caplog, full_audit=False, indexings=indexings, silence_threshold=silence_threshold)


def read_sound(database: Connection, sound: int) -> tuple[object, ...]:
	line = database.execute(
		"SELECT state::text, duration, file_modified_at, file_size, modified_at FROM sounds WHERE id = %s",
		(sound,),
	).fetchone()
	assert line is not None
	return line


@then(parsers.parse("le sonore est à l'état « {state} »"))
def state_sound(empty_database: Connection, sound: int, state: str) -> None:
	assert read_sound(empty_database, sound)[0] == state


@then(parsers.re(rf"sa durée en base est de (?P<expected>{DECIMAL}) secondes? à (?P<margin>{DECIMAL}) seconde près"))
def duration_in_database(empty_database: Connection, sound: int, expected: str, margin: str) -> None:
	duration = read_sound(empty_database, sound)[1]
	assert isinstance(duration, timedelta), duration
	assert abs(duration.total_seconds() - count(expected)) <= count(margin), duration


@then("la date de modification et la taille du fichier sont enregistrées")
def date_and_size(empty_database: Connection, sound: int, file: Path) -> None:
	_, _, modified_at, size, _ = read_sound(empty_database, sound)
	state = file.stat()
	assert size == state.st_size
	assert modified_at == datetime.fromtimestamp(state.st_mtime, tz=UTC)


@then("rien n'est signalé sur la sortie d'erreur")
def reported_nothing(execution: Execution) -> None:
	assert execution.errors == ""


@then(parsers.parse("la sortie d'erreur signale ce fichier comme « {verdict} », avec « {consequence} »"))
def reported_error(execution: Execution, file: Path, verdict: str, consequence: str) -> None:
	lines = [line for line in execution.errors.splitlines() if line.startswith(f"{file} : ")]
	assert len(lines) == 1, execution.errors
	assert (f" : {verdict} : " in lines[0]) and (lines[0].endswith(f" ; {consequence}")), lines[0]


@then(parsers.parse("le bilan indique « {text} »"))
def indicated_report(execution: Execution, text: str) -> None:
	assert report_text(execution.report) == text


@then("le stream n'a pas été modifié")
def stream_intact(empty_database: Connection, stream: tuple[int, object]) -> None:
	state, duration, modified_file, size, modified_at = read_sound(empty_database, stream[0])
	assert (state, duration, modified_file, size) == ("active", None, None, None)
	assert modified_at == stream[1]


def read_tags_in_database(database: Connection, sound: int) -> tuple[object, object, object]:
	line = database.execute("SELECT artist, title, music_metadata FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert line is not None
	return line[0], line[1], line[2]


@then(parsers.parse("en base, l'artiste est « {artist} » et le titre « {title} »"))
def artist_and_title_in_database(empty_database: Connection, sound: int, artist: str, title: str) -> None:
	assert read_tags_in_database(empty_database, sound)[:2] == (artist, title)


# ─── Machin indexer ─────────────────────────────────────


@when(
	parsers.re(r"Machin indexer est lancé sur la base de test(?P<audit>, en audit complet)?"),
	target_fixture="launching",
)
def launch_on_test_database(
	empty_database: Connection, caplog: pytest.LogCaptureFixture, audit: str | None
) -> tuple[int, list[str]]:
	"""Son action, avec une configuration dont la base de production est la base de test."""
	configuration = configuration_test()
	on_test_database = dataclasses.replace(
		configuration, database=dataclasses.replace(configuration.database, production=configuration.database.test)
	)
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		code = run(
			on_test_database,
			argparse.Namespace(full_audit=audit is not None, window=False, sound=None, force=False),
		)
	return code, [message for _level, message in per_file(caplog.records)]


@then(parsers.parse("Machin indexer se termine avec le code {code:d}, en signalant « {text} »"))
def finished_launching(launching: tuple[int, list[str]], tmp_path: Path, code: int, text: str) -> None:
	"""Un « …/ » désigne le répertoire du scénario."""
	obtained, messages = launching
	text = text.replace("…/", f"{tmp_path}/")
	assert (obtained, text in messages) == (code, True), messages


@then(parsers.parse("le type du fichier en base est « {type_mime} »"))
def type_in_database(empty_database: Connection, sound: int, type_mime: str) -> None:
	assert empty_database.execute("SELECT mime_type FROM sounds WHERE id = %s", (sound,)).fetchone() == (type_mime,)


@then(parsers.parse("la sortie d'erreur mentionne « {text} »"))
def mentioned_error(execution: Execution, text: str) -> None:
	assert text in execution.errors, execution.errors


def read_csv(directory: Path, name: str) -> list[list[str]]:
	with (directory / name).open(encoding="utf-8-sig", newline="") as file:
		return list(csv.reader(file, delimiter=";"))


@then(parsers.parse("le document d'audit « {name} » signale ce fichier, « {verdict} », avec « {consequence} »"))
def csv_anomaly(audit_directory: Path, file: Path, name: str, verdict: str, consequence: str) -> None:
	_header, anomaly, _report = read_csv(audit_directory, name)
	_date, path, lu, problem, remainder = anomaly
	assert (path, lu, remainder) == (str(file), verdict, consequence)
	assert (problem != "") and (not problem.startswith(verdict)), problem


def checks_at(database: Connection, sound: int) -> object:
	line = database.execute("SELECT checked_at FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert line is not None
	return line[0]


@then(parsers.re(r"la date de vérification complète du sonore est celle de l'indexation(?P<previous> précédente)?"))
def check_date(
	empty_database: Connection, sound: int, indexings: list[tuple[datetime, datetime]], previous: str | None
) -> None:
	if previous is not None:
		chosen = -2
	else:
		chosen = -1
	start, end = indexings[chosen]
	date = checks_at(empty_database, sound)
	assert isinstance(date, datetime)
	assert start <= date <= end, (start, date, end)


@then("le sonore n'a pas de date de vérification complète")
def without_check_date(empty_database: Connection, sound: int) -> None:
	assert checks_at(empty_database, sound) is None


# ─── Détection de silence (https://github.com/dascritch/machincast/issues/146) ───


@given(parsers.re(r"un fichier (?P<sound_format>\w+) avec des silences"), target_fixture="file")
def file_with_silences(tmp_path: Path, sound_format: str) -> Path:
	return sample_copy(sound_format, tmp_path, "silences")


@when(
	parsers.re(rf"je vérifie ce fichier en détectant les silences au seuil de (?P<threshold>-?{DECIMAL}) dB"),
	target_fixture="result",
)
def check_silences(file: Path, threshold: str) -> Check:
	return check_file(file, silence_threshold=count(threshold))


def _near(value: timedelta | None, expected: str, margin: str) -> bool:
	return (value is not None) and (abs(value.total_seconds() - count(expected)) <= count(margin))


@then(parsers.re(rf"son début détecté est de (?P<expected>{DECIMAL}) secondes? à (?P<margin>{DECIMAL}) seconde près"))
def detected_start(result: Check, expected: str, margin: str) -> None:
	assert result.silences is not None
	assert _near(result.silences.start, expected, margin), result.silences


@then(parsers.re(rf"sa fin détectée est de (?P<expected>{DECIMAL}) secondes? à (?P<margin>{DECIMAL}) seconde près"))
def detected_end(result: Check, expected: str, margin: str) -> None:
	assert result.silences is not None
	assert _near(result.silences.end, expected, margin), result.silences


@then("aucun silence n'est détecté")
def no_silence(result: Check) -> None:
	assert result.silences == Silences(None, None), result.silences


@then("les silences n'ont pas été mesurés")
def silences_not_measures(result: Check) -> None:
	assert result.silences is None, result.silences


@pytest.fixture
def silence_threshold() -> list[float]:
	"""Le seuil de silence de la configuration, s'il est donné par le scénario ; celui par défaut sinon."""
	return []


@given(parsers.re(rf"un seuil de silence de (?P<threshold>-?{DECIMAL}) dB dans la configuration"))
def configured_threshold(silence_threshold: list[float], threshold: str) -> None:
	silence_threshold.append(count(threshold))


@given(
	parsers.re(
		rf"un sonore à l'état « active » pour ce fichier, avec (?P<seconds>{DECIMAL}) secondes? de début et de fin"
		r" détectés"
	),
	target_fixture="sound",
)
def sound_with_silences(empty_database: Connection, file: Path, seconds: str) -> int:
	sound = insert_sound(empty_database, str(file), "active")
	duration = timedelta(seconds=count(seconds))
	empty_database.execute(
		"UPDATE sounds SET detected_start = %s, detected_end = %s WHERE id = %s", (duration, duration, sound)
	)
	return sound


@given(
	parsers.re(
		r"un sonore à l'état « active » pour ce fichier, dont le début et la fin détectés ont été saisis à la main"
		rf" à (?P<seconds>{DECIMAL}) secondes?"
	),
	target_fixture="sound",
)
def edited_silence_sound(empty_database: Connection, file: Path, seconds: str) -> int:
	sound = insert_sound(empty_database, str(file), "active", ["detected_start", "detected_end"])
	duration = timedelta(seconds=count(seconds))
	empty_database.execute(
		"UPDATE sounds SET detected_start = %s, detected_end = %s WHERE id = %s", (duration, duration, sound)
	)
	return sound


@when("l'indexeur fait l'audit complet de ce seul sonore", target_fixture="execution")
def sound_audit(empty_database: Connection, caplog: pytest.LogCaptureFixture, sound: int) -> Execution:
	"""Comme Machin_indexer --full-audit --sound N, avec le seuil par défaut."""
	caplog.clear()
	with (
		caplog.at_level(logging.INFO, logger="machincast"),
		open_connection(*sample_database_parameters(), Role.INDEXING) as c,
	):
		report = index_sound(c, sound, full_audit=True)
	lines = per_file(caplog.records)
	anomalies = [message for level, message in lines if level >= logging.WARNING]
	information = [message for level, message in lines if level == logging.INFO]
	return Execution(report, "\n".join(anomalies), information)


def silences_in_database(database: Connection, sound: int) -> tuple[object, object]:
	line = database.execute("SELECT detected_start, detected_end FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert line is not None
	return line[0], line[1]


@then(
	parsers.re(
		rf"en base, le début détecté du sonore est de (?P<start>{DECIMAL}) secondes? et sa fin détectée"
		rf" de (?P<end>{DECIMAL}) secondes?, à (?P<margin>{DECIMAL}) seconde près"
	)
)
def sound_silences(empty_database: Connection, sound: int, start: str, end: str, margin: str) -> None:
	in_database = silences_in_database(empty_database, sound)
	assert all(isinstance(value, timedelta) for value in in_database), in_database
	start_value, end_value = (value for value in in_database if isinstance(value, timedelta))
	assert _near(start_value, start, margin), in_database
	assert _near(end_value, end, margin), in_database


@then("en base, le sonore n'a ni début ni fin détectés")
def without_silences_in_database(empty_database: Connection, sound: int) -> None:
	assert silences_in_database(empty_database, sound) == (None, None)


@given("le sonore est supprimé depuis l'interface")
def deleted_sound(empty_database: Connection, sound: int) -> None:
	"""https://github.com/dascritch/machincast/issues/267"""
	empty_database.execute("UPDATE sounds SET deleted_at = clock_timestamp() WHERE id = %s", (sound,))


@then("la disparition du fichier du sonore est datée")
def dated_disappearance(empty_database: Connection, sound: int) -> None:
	line = empty_database.execute("SELECT missing_at FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert (line is not None) and (line[0] is not None), line
