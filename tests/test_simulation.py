"""Étapes du mode simulation de Machin player (https://github.com/dascritch/machincast/issues/21).

Les étapes de la diffusion viennent de tests/broadcast_steps.py. Les sorties de la simulation sont écrites dans le
répertoire temporaire du scénario.
"""

import csv
import logging
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import machincast.audio
import machincast.player.engine
from machincast.audio import UnavailableAudioOutput
from machincast.configuration import Crossfades, Metadata
from machincast.database import Role, open_connection
from machincast.player.saving import LEVELS
from machincast.player.simulation import Result, read_only, simulate
from tests.broadcast_steps import Bench, Connection, create_sound, event, hour, sound
from tests.database_fixtures import CONFIGURATION_TEST, sample_database_parameters
from tests.log_texts import shown

scenarios("simulation.feature")


@dataclass
class Context:
	directory: Path | None = None
	results: list[Result] = field(default_factory=list)
	before: tuple[object, ...] | None = None
	metadata: Metadata = field(default_factory=lambda: Metadata(hide=False, public_text=""))
	error: Exception | None = None
	process: subprocess.CompletedProcess[str] | None = None


@pytest.fixture
def context() -> Context:
	return Context()


def result(context: Context) -> Result:
	assert context.results
	return context.results[-1]


def database_state(database: Connection) -> tuple[object, ...]:
	"""Tout ce que la simulation pourrait changer : airplay, log, et chaque sonore."""
	line = database.execute(
		"SELECT (SELECT count(*) FROM airplay), (SELECT count(*) FROM log),"
		" (SELECT COALESCE(jsonb_agg(to_jsonb(s) ORDER BY s.id), '[]') FROM sounds s)"
	).fetchone()
	assert line is not None
	return tuple(line)


def launch_simulation(
	context: Context,
	database: Connection,
	start: str,
	end: str,
	seed: int | None = None,
	name: str | None = None,
	crossfades: Crossfades | None = None,
) -> None:
	assert context.directory is not None
	context.before = database_state(database)
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		context.results.append(
			simulate(
				connection,
				context.directory,
				hour(start),
				hour(end),
				seed,
				name,
				context.metadata,
				(crossfades) or (Crossfades()),
			)
		)


def titles(context: Context) -> list[str]:
	return [str(line.title) for line in result(context).plays]


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("des sorties de simulation dans un répertoire temporaire, avec le texte public « {text} »"))
def temporary_outputs(context: Context, tmp_path: Path, caplog: pytest.LogCaptureFixture, text: str) -> None:
	caplog.set_level(logging.INFO, logger="machincast")
	context.directory = tmp_path / "sorties"
	context.metadata = Metadata(hide=False, public_text=text)


@given(parsers.parse("chaque sonore dure {minutes:d} minute"))
def sound_duration(empty_database: Connection, minutes: int) -> None:
	empty_database.execute("UPDATE sounds SET duration = %s WHERE type = 'file'", (timedelta(minutes=minutes),))


@given(parsers.parse("l'émission « {name} » du « {start} » au « {end} », avec le sonore « {sound_name} »"))
def dated_show(
	bench: Bench, empty_database: Connection, tmp_path: Path, name: str, start: str, end: str, sound_name: str
) -> None:
	event(bench, empty_database, tmp_path, name, "show", hour(start), hour(end), [sound_name])


@given(parsers.parse("le stream « {name} » à l'adresse « {address} »"))
def stream(empty_database: Connection, name: str, address: str) -> None:
	empty_database.execute("INSERT INTO sounds (type, stream_url, title) VALUES ('stream', %s, %s)", (address, name))


@given(parsers.parse("« {name} » a été joué dans le fil « {feed} » le « {instant} »"))
def plays_in_feed(empty_database: Connection, name: str, feed: str, instant: str) -> None:
	line = empty_database.execute(
		"SELECT e.id, ee.id FROM events e JOIN event_items ee ON ee.event_id = e.id"
		" WHERE e.internal_name = %s AND ee.sound_id = %s",
		(feed, sound(empty_database, name)),
	).fetchone()
	assert line is not None
	empty_database.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, event_id, event_item_id, title)"
		" VALUES (%s, 'start', %s, %s, %s, %s, %s)",
		(uuid.uuid4(), hour(instant), sound(empty_database, name), line[0], line[1], name),
	)


@given(parsers.re(r"la banque séquentielle « (?P<name>[^»]+) » des sonores (?P<list_>.+), marquée « ne pas répéter »"))
def bank_to_no_repeat(bench: Bench, empty_database: Connection, tmp_path: Path, name: str, list_: str) -> None:
	created = empty_database.execute(
		"INSERT INTO banks (internal_name, mode, no_repeat) VALUES (%s, 'sequential', true) RETURNING id", (name,)
	).fetchone()
	assert created is not None
	for position, sound_name in enumerate(re.findall(r"« ([^»]+) »", list_), start=1):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
			(created[0], create_sound(bench, empty_database, tmp_path, sound_name), position),
		)


@given(parsers.re(r"la banque « (?P<name>[^»]+) » des sonores (?P<list_>.+), de nom public « (?P<public_name>[^»]+) »"))
def named_bank(
	bench: Bench, empty_database: Connection, tmp_path: Path, name: str, list_: str, public_name: str
) -> None:
	created = empty_database.execute(
		"INSERT INTO banks (internal_name, public_name, mode) VALUES (%s, %s, 'sequential') RETURNING id",
		(name, public_name),
	).fetchone()
	assert created is not None
	for position, sound_name in enumerate(re.findall(r"« ([^»]+) »", list_), start=1):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
			(created[0], create_sound(bench, empty_database, tmp_path, sound_name), position),
		)


@given(
	parsers.re(
		r"la séquence « (?P<name>[^»]+) », qui appelle deux fois la banque « (?P<bank>[^»]+) »,"
		r" de nom public « (?P<public_name>[^»]+) », masquée"
	)
)
def hidden_sequence(empty_database: Connection, name: str, bank: str, public_name: str) -> None:
	created = empty_database.execute(
		"INSERT INTO sequences (internal_name, public_name, hide_metadata) VALUES (%s, %s, true) RETURNING id",
		(name, public_name),
	).fetchone()
	line = empty_database.execute("SELECT id FROM banks WHERE internal_name = %s", (bank,)).fetchone()
	assert (created is not None) and (line is not None)
	for position in (1, 2):
		empty_database.execute(
			"INSERT INTO sequence_items (sequence_id, position, bank_id) VALUES (%s, %s, %s)",
			(created[0], position, line[0]),
		)


@given(
	parsers.re(
		r"le fil musical permanent « (?P<name>[^»]+) », avec (?P<list_>(?:la banque|la séquence|le sonore) « .+)"
	)
)
def feed_with_items(bench: Bench, empty_database: Connection, tmp_path: Path, name: str, list_: str) -> None:
	created = empty_database.execute(
		"INSERT INTO events (internal_name, priority) VALUES (%s, 'background_programming') RETURNING id", (name,)
	).fetchone()
	assert created is not None
	for position, (category, item_name) in enumerate(
		re.findall(r"(banque|séquence|sonore) « ([^»]+) »", list_), start=1
	):
		table = {"banque": "banks", "séquence": "sequences"}.get(category)
		if table is not None:
			line = empty_database.execute(
				f"SELECT id FROM {table} WHERE internal_name = %s",  # noqa: S608
				(item_name,),
			).fetchone()
			assert line is not None
			reference = int(str(line[0]))
		else:
			reference = create_sound(bench, empty_database, tmp_path, item_name)
		column = {"banque": "bank_id", "séquence": "sequence_id"}.get(category, "sound_id")
		empty_database.execute(
			f"INSERT INTO event_items (event_id, position, {column}) VALUES (%s, %s, %s)",  # noqa: S608
			(created[0], position, reference),
		)


@given(parsers.parse("« {name} » a été joué via la banque « {bank} » le « {instant} »"))
def plays_via_bank(empty_database: Connection, name: str, bank: str, instant: str) -> None:
	line = empty_database.execute("SELECT id FROM banks WHERE internal_name = %s", (bank,)).fetchone()
	assert line is not None
	empty_database.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, bank_id, title)"
		" VALUES (%s, 'start', %s, %s, %s, %s)",
		(uuid.uuid4(), hour(instant), sound(empty_database, name), line[0], name),
	)


@given("le masquage de tous les sonores")
def hide_all(empty_database: Connection) -> None:
	empty_database.execute("UPDATE sounds SET hide_metadata = true")


@given("aucune sortie audio ne peut être créée")
def without_audio_output(monkeypatch: pytest.MonkeyPatch) -> None:
	def refuse(*arguments: object, **options: object) -> object:
		raise UnavailableAudioOutput("aucune sortie audio dans ce scénario")

	monkeypatch.setattr(machincast.audio, "create_output", refuse)
	monkeypatch.setattr(machincast.player.engine, "create_output", refuse)


@given(parsers.re(r"le sonore « (?P<name>[^»]+) » a un maximum de (?P<maximum>\d+) lectures?"))
def sound_maximum(empty_database: Connection, name: str, maximum: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET max_plays = %s WHERE id = %s", (int(maximum), sound(empty_database, name))
	)


# ─── Quand ─────────────────────────────────────────────────


@when(
	parsers.re(
		r"je simule la diffusion du « (?P<start>[^»]+) » au « (?P<end>[^»]+) »"
		r"(?:, avec la graine (?P<seed>\d+))?(?:, sous le nom « (?P<name>[^»]+) »)?$"
	)
)
def simulate_broadcast(
	context: Context, bench: Bench, empty_database: Connection, start: str, end: str, seed: str | None, name: str | None
) -> None:
	launch_simulation(context, empty_database, start, end, None if seed is None else int(seed), name, bench.crossfades)


@when(parsers.parse("je simule deux fois la diffusion du « {start} » au « {end} », avec la graine {seed:d}"))
def simulate_times_two(context: Context, empty_database: Connection, start: str, end: str, seed: int) -> None:
	launch_simulation(context, empty_database, start, end, seed)
	launch_simulation(context, empty_database, start, end, seed)


@when("une écriture dans le log est tentée pendant une simulation")
def write_during_simulation(context: Context, empty_database: Connection) -> None:
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		try:
			with read_only(connection):
				connection.execute("INSERT INTO log (level, kind, message) VALUES ('info', 'essai', 'interdit')")
		except psycopg.Error as error:
			context.error = error


def playback_machin() -> str:
	return (shutil.which("Machin_player")) or (str(Path(sys.executable).parent / "Machin_player"))


@when(
	parsers.re(r"je lance Machin_player avec « (?P<arguments>.+) »(?P<without_database> et une socket inexistante)?$")
)
def launch(context: Context, tmp_path: Path, arguments: str, without_database: str | None) -> None:
	configuration = CONFIGURATION_TEST
	if without_database:
		configuration = tmp_path / "sans-base.toml"
		text = CONFIGURATION_TEST.read_text(encoding="utf-8")
		configuration.write_text(
			text.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'),
			encoding="utf-8",
		)
	context.process = subprocess.run(
		[playback_machin(), "--config", str(configuration), *shlex.split(arguments)],
		capture_output=True,
		text=True,
		timeout=60,
	)


# ─── Alors ─────────────────────────────────────────────────


def displayed_end(end: datetime | None) -> str:
	if end is None:
		return ""
	return f"{end.astimezone():%Y-%m-%d %H:%M:%S}"


@then("la simulation donne les passages :")
def expected_plays(context: Context, datatable: list[list[str]]) -> None:
	_, *lines = datatable
	obtained_list = [
		[f"{p.start.astimezone():%Y-%m-%d %H:%M:%S}", displayed_end(p.end), str(p.title)] for p in result(context).plays
	]
	assert obtained_list == lines, obtained_list


@then(parsers.parse("la simulation donne {count:d} passages"))
def play_count(context: Context, count: int) -> None:
	assert len(result(context).plays) == count


@then(parsers.re(r"la simulation donne les titres (?P<list_>.+)"))
def expected_titles(context: Context, list_: str) -> None:
	assert titles(context) == [n.strip(" «»") for n in list_.split(",")], titles(context)


@then("la base n'a pas changé")
def intact_database(context: Context, empty_database: Connection) -> None:
	assert database_state(empty_database) == context.before


@then("PostgreSQL la refuse, la transaction étant en lecture seule")
def refusal(context: Context, empty_database: Connection) -> None:
	assert isinstance(context.error, psycopg.errors.ReadOnlySqlTransaction), repr(context.error)
	assert empty_database.execute("SELECT count(*) FROM log WHERE kind = 'essai'").fetchone() == (0,)


@then(parsers.parse("chaque tranche de 3 passages joue « a », « b » et « c », chacun une fois"))
def cycles(context: Context) -> None:
	seen_list = titles(context)
	assert len(seen_list) == 6, seen_list
	assert (sorted(seen_list[:3]) == ["a", "b", "c"]) and (sorted(seen_list[3:]) == ["a", "b", "c"]), seen_list


@then("les deux simulations donnent les mêmes passages")
def same_plays(context: Context) -> None:
	first, second = ([str(p.title) for p in r.plays] for r in context.results)
	assert (first == second) and (len(set(first)) > 1), (first, second)


@then(parsers.re(r"la simulation a consigné (?P<count>\d+) (?P<level>info|alerte|incident) « (?P<kind>[^»]+) »"))
def records(context: Context, count: str, level: str, kind: str) -> None:
	lines = Counter((n, shown(t)) for n, t, _ in result(context).log)
	in_database = {label: value for value, label in LEVELS.items()}[level]
	assert lines[(in_database, kind)] == int(count), result(context).log


@then(parsers.parse("le sonore « {name} » est toujours à l'état « {state} » en base"))
def state_in_database(empty_database: Connection, name: str, state: str) -> None:
	line = empty_database.execute(
		"SELECT state::text FROM sounds WHERE id = %s", (sound(empty_database, name),)
	).fetchone()
	assert line == (state,)


@then(parsers.parse("la simulation a écrit « {name} » en .csv, .pls et .html"))
def written_files(context: Context, name: str) -> None:
	assert context.directory is not None
	expected_list = tuple(context.directory / f"{name}{extension}" for extension in (".csv", ".pls", ".html"))
	assert result(context).files == expected_list
	assert all(path.is_file() for path in expected_list), list(context.directory.iterdir())


def file(context: Context, extension: str) -> Path:
	return next(path for path in result(context).files if path.suffix == extension)


@then(parsers.parse("le CSV de la simulation a {count:d} lignes de passage, sur les deux jours"))
def simulation_csv(context: Context, count: int) -> None:
	with file(context, ".csv").open(encoding="utf-8-sig", newline="") as source:
		lines = list(csv.DictReader(source, delimiter=";"))
	assert len(lines) == count
	assert {line["start"][:10] for line in lines} == {"2026-10-20", "2026-10-21"}, lines


@then(parsers.parse("la playlist de la simulation compte {count:d} entrées"))
def simulation_playlist(context: Context, count: int) -> None:
	assert f"NumberOfEntries={count}" in file(context, ".pls").read_text(encoding="utf-8")


@then("la page de la simulation montre l'emplacement de chaque fichier joué")
def page_with_locations(context: Context) -> None:
	page = file(context, ".html").read_text(encoding="utf-8")
	for line in result(context).plays:
		assert f">{line.location}<" in page, page
	assert (">f1<" not in page) and (">f2<" not in page), page


@given(parsers.parse("le masquage du sonore « {name} »"))
def hide_sound(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE sounds SET hide_metadata = true WHERE id = %s", (sound(empty_database, name),))


def fetched_outputs(context: Context) -> dict[str, str]:
	return {path.suffix: path.read_text(encoding="utf-8-sig") for path in (result(context).files) or (())}


@then(
	parsers.parse("les sorties de la simulation montrent « {visible} », mais pas « {hides} », remplacé par « {text} »")
)
def hidden_outputs(context: Context, visible: str, hides: str, text: str) -> None:
	for extension, content in fetched_outputs(context).items():
		assert (visible in content) and (text in content), (extension, content)
		assert (f">{hides}<" not in content) and (f";{hides};" not in content) and (f"={hides}\n" not in content), (
			extension,
			content,
		)


@then(parsers.parse("le CSV de la simulation nomme la séquence « {name} » pour {count:d} passages"))
def sequence_in_csv(context: Context, name: str, count: int) -> None:
	with file(context, ".csv").open(encoding="utf-8-sig", newline="") as source:
		lines = list(csv.DictReader(source, delimiter=";"))
	assert sum(1 for line in lines if line["sequence"] == name) == count, lines


@then(
	parsers.parse("les sorties de la simulation donnent l'emplacement des fichiers de « {first} » et de « {second} »")
)
def outputs_with_locations(context: Context, empty_database: Connection, first: str, second: str) -> None:
	for name in (first, second):
		line = empty_database.execute(
			"SELECT location FROM sounds WHERE id = %s", (sound(empty_database, name),)
		).fetchone()
		assert line is not None
		for extension, content in fetched_outputs(context).items():
			assert str(line[0]) in content, (extension, name)


@then(parsers.parse("la page de la simulation signale l'alerte « {kind} »"))
def warning_page(context: Context, kind: str) -> None:
	page = file(context, ".html").read_text(encoding="utf-8")
	assert ("alerte" in page) and (kind in page), page


@then(parsers.parse("il s'arrête avec le code {code:d}, en signalant « {pattern} »"))
def stop(context: Context, code: int, pattern: str) -> None:
	assert context.process is not None
	assert context.process.returncode == code, context.process.stderr
	assert pattern in context.process.stderr, context.process.stderr


@then(parsers.parse("le journal du binaire a signalé « {text} »"))
def reported_log(caplog: pytest.LogCaptureFixture, text: str) -> None:
	assert any((r.levelno == logging.WARNING) and (text in r.getMessage()) for r in caplog.records), caplog.text
