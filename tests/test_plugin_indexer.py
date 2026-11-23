"""Scénarios des points d'extension de Machin indexer (https://github.com/dascritch/machincast/issues/590).

L'indexation vient de tests/indexing_steps.py ; le plugin est abonné aux points des plugins chargés
(machincast.plugins.active), que tests/conftest.py remet à vide après chaque scénario. Ses notifications sont attendues
(Points.close) avant d'être lues.
"""

import shutil
from pathlib import Path
from typing import Any

import psycopg
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import plugins
from tests.plugin_steps import Recorder, core_points, subscribe_failing
from tests.sounds import corrupt, sample_copy

scenarios("plugin_indexer.feature")

Connection = psycopg.Connection[tuple[object, ...]]
POINTS = core_points("indexer.")


def _location(tmp_path: Path, relative: str) -> str:
	return str(tmp_path / "radio" / relative)


def _found(recorder: Recorder, point: str, location: str) -> dict[str, Any]:
	plugins.active().points.close()
	for data in recorder.of(point):
		if data["location"] == location:
			return data
	raise AssertionError(f"{point} de {location} : {recorder.received}")


@given(
	parsers.parse(
		"une banque « {name} » alimentée par le répertoire « {directory} », avec un fichier « {healthy} » sain et un"
		" fichier « {broken} » endommagé"
	)
)
def bank_with_files(
	empty_database: Connection, tmp_path: Path, name: str, directory: str, healthy: str, broken: str
) -> None:
	folder = tmp_path / "radio" / directory
	folder.mkdir(parents=True)
	shutil.move(sample_copy("flac", tmp_path), folder / healthy)
	damaged = sample_copy("mp3", tmp_path)
	corrupt(damaged, 1000, 1 / 3)
	shutil.move(damaged, folder / broken)
	bank = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (name,)
	).fetchone()
	assert bank is not None
	empty_database.execute("INSERT INTO bank_directories (bank_id, directory) VALUES (%s, %s)", (bank[0], str(folder)))


@given("un plugin chargé, abonné aux points de Machin indexer")
def subscribed(recorder: Recorder) -> None:
	recorder.subscribe(plugins.active().points, "témoin", POINTS)


@given(parsers.parse("un plugin chargé « {name} », qui échoue à chaque point de Machin indexer"))
def failing(name: str) -> None:
	subscribe_failing(plugins.active().points, name, POINTS)


@when("le plugin oublie ce qu'il a reçu")
def forget(recorder: Recorder) -> None:
	plugins.active().points.close()
	recorder.received.clear()


@then(
	parsers.parse(
		"le plugin a été prévenu de « indexer.sound_spotted » pour « {relative} », trouvé par la banque « {bank} »"
	)
)
def spotted(empty_database: Connection, tmp_path: Path, recorder: Recorder, relative: str, bank: str) -> None:
	data = _found(recorder, "indexer.sound_spotted", _location(tmp_path, relative))
	sound = empty_database.execute("SELECT id FROM sounds WHERE location = %s", (data["location"],)).fetchone()
	found = empty_database.execute("SELECT id FROM banks WHERE internal_name = %s", (bank,)).fetchone()
	assert (sound is not None) and (found is not None)
	assert (data["sound"], data["bank"], data["bank_name"]) == (sound[0], found[0], bank)


@then(
	parsers.re(
		r"le plugin a été prévenu de « indexer.sound_detailed » pour « (?P<relative>[^»]+) », de l'état"
		r" « (?P<before>[^»]+) » à l'état « (?P<after>[^»]+) », (?P<duration>avec sa durée|sans durée),"
		r" (?P<problem>sans problème|avec son problème)"
	)
)
def detailed(
	empty_database: Connection,
	tmp_path: Path,
	recorder: Recorder,
	relative: str,
	before: str,
	after: str,
	duration: str,
	problem: str,
) -> None:
	data = _found(recorder, "indexer.sound_detailed", _location(tmp_path, relative))
	line = empty_database.execute(
		"SELECT id, EXTRACT(EPOCH FROM duration)::float8 FROM sounds WHERE location = %s", (data["location"],)
	).fetchone()
	assert line is not None
	assert (data["sound"], data["previous_state"], data["state"], data["duration"]) == (line[0], before, after, line[1])
	assert (data["duration"] is not None) == (duration == "avec sa durée")
	assert (data["problem"] is not None) == (problem == "avec son problème")


@then("le plugin n'a été prévenu de rien")
def nothing(recorder: Recorder) -> None:
	plugins.active().points.close()
	assert recorder.received == []


@then(
	parsers.re(r"le sonore de « (?P<relative>[^»]+) » est à l'état « (?P<state>[^»]+) »(?P<bank>, dans la banque .+)?")
)
def sound_state(empty_database: Connection, tmp_path: Path, relative: str, state: str, bank: str | None) -> None:
	plugins.active().points.close()
	line = empty_database.execute(
		"SELECT state::text, (SELECT count(*) FROM bank_sounds WHERE sound_id = sounds.id) FROM sounds"
		" WHERE location = %s",
		(_location(tmp_path, relative),),
	).fetchone()
	assert line is not None
	assert line[0] == state
	if bank is not None:
		assert line[1] == 1
