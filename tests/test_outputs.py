"""Étapes du masquage des métadonnées et des modules de sortie (https://github.com/dascritch/machincast/issues/19).

Les étapes de la diffusion viennent de tests/broadcast_steps.py. Les sorties sont écrites dans le répertoire
temporaire du scénario, jamais aux chemins de la configuration de test.
"""

import csv
import logging
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.configuration import Metadata
from machincast.configuration import Outputs as OutputPaths
from machincast.database import Role, open_connection
from machincast.player.outputs import Outputs
from tests.broadcast_steps import Bench, Connection
from tests.database_fixtures import configuration_test, sample_database_parameters

scenarios("outputs.feature")

START = datetime.fromisoformat("2026-10-14 20:00:00").astimezone()
VALUES = {"vide": None, "oui": True, "non": False}


def bench_outputs(bench: Bench) -> Outputs:
	assert bench.outputs is not None
	return bench.outputs


def prepare_outputs(bench: Bench, directory: Path, hide: bool, public_text: str) -> None:
	paths = OutputPaths(
		csv=directory / "sorties" / "airplay.csv",
		pls=directory / "sorties" / "playlist.pls",
		html=directory / "sorties" / "airplay.html",
	)
	bench.outputs = Outputs(paths, Metadata(hide=hide, public_text=public_text))


def insert(database: Connection, query: str, values: tuple[object, ...]) -> int:
	line = database.execute(query, values).fetchone()
	assert line is not None
	return int(str(line[0]))


def play(
	database: Connection,
	number: int,
	artist: str,
	title: str,
	*,
	finished: bool = True,
	hidden_sound: bool | None = None,
	bank: int | None = None,
	event: int | None = None,
	sequence: int | None = None,
) -> None:
	"""Un passage dans l'airplay, numero minutes après DEBUT, d'une minute s'il est terminé."""
	location = f"/musique/{number}.flac"
	sound = insert(
		database,
		"INSERT INTO sounds (type, location, artist, title, hide_metadata)"
		" VALUES ('file', %s, %s, %s, %s) RETURNING id",
		(location, artist, title, hidden_sound),
	)
	identifier = uuid.uuid4()
	start = START + timedelta(minutes=number)
	columns = "play_id, line_type, logged_at, sound_id, bank_id, event_id, sequence_id, location, artist, title"
	database.execute(
		f"INSERT INTO airplay ({columns}) VALUES (%s, 'start', %s, %s, %s, %s, %s, %s, %s, %s)",
		(identifier, start, sound, bank, event, sequence, location, artist, title),
	)
	if finished:
		database.execute(
			f"INSERT INTO airplay ({columns}, played_duration, without_incident)"
			" VALUES (%s, 'end', %s, %s, %s, %s, %s, %s, %s, %s, '1 min', true)",
			(identifier, start + timedelta(minutes=1), sound, bank, event, sequence) + (location, artist, title),
		)


def show(database: Connection, name: str, public_name: str | None, hide: bool | None) -> int:
	return insert(
		database,
		"INSERT INTO events (internal_name, public_name, priority, starts_at, hide_metadata)"
		" VALUES (%s, %s, 'show', '2026-10-14 19:00', %s) RETURNING id",
		(name, public_name, hide),
	)


def page(bench: Bench) -> str:
	return bench_outputs(bench).paths.html.read_text(encoding="utf-8")


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("des sorties dans un répertoire temporaire, avec le texte public « {text} »"))
def temporary_outputs(bench: Bench, tmp_path: Path, caplog: pytest.LogCaptureFixture, text: str) -> None:
	caplog.set_level(logging.INFO, logger="machincast")
	prepare_outputs(bench, tmp_path, False, text)


@given(
	parsers.parse(
		"le masquage {event} pour l'événement, {sequence} pour la séquence, {bank} pour la banque,"
		" {sound} pour le sonore et {configuration} dans la configuration"
	)
)
def hidings(
	bench: Bench,
	empty_database: Connection,
	tmp_path: Path,
	event: str,
	sequence: str,
	bank: str,
	sound: str,
	configuration: str,
) -> None:
	prepare_outputs(bench, tmp_path, configuration == "oui", "Radio Exemple")
	sequence_identifier = insert(
		empty_database,
		"INSERT INTO sequences (internal_name, hide_metadata) VALUES ('Séquence', %s) RETURNING id",
		(VALUES[sequence],),
	)
	bank_identifier = insert(
		empty_database,
		"INSERT INTO banks (internal_name, mode, hide_metadata) VALUES ('Banque', 'sequential', %s) RETURNING id",
		(VALUES[bank],),
	)
	event_identifier = show(empty_database, "Émission", None, VALUES[event])
	play(
		empty_database,
		0,
		"Artiste secret",
		"Titre secret",
		finished=False,
		hidden_sound=VALUES[sound],
		bank=bank_identifier,
		event=event_identifier,
		sequence=sequence_identifier,
	)


def public_name(text: str) -> str | None:
	if text == "vide":
		return None
	return text.strip(" «»")


@given(
	parsers.parse(
		"un passage masqué, de nom public {event} pour l'événement, {sequence} pour la séquence et {bank}"
		" pour la banque"
	)
)
def hidden_public_names_play(empty_database: Connection, event: str, sequence: str, bank: str) -> None:
	bank_identifier = insert(
		empty_database,
		"INSERT INTO banks (internal_name, public_name, mode) VALUES ('Banque', %s, 'sequential') RETURNING id",
		(public_name(bank),),
	)
	sequence_identifier = insert(
		empty_database,
		"INSERT INTO sequences (internal_name, public_name, hide_metadata) VALUES ('Séquence', %s, true) RETURNING id",
		(public_name(sequence),),
	)
	play(
		empty_database,
		0,
		"Artiste secret",
		"Titre secret",
		finished=False,
		bank=bank_identifier,
		event=show(empty_database, "Émission", public_name(event), None),
		sequence=sequence_identifier,
	)


@given(
	parsers.re(
		r"le passage de « (?P<artist>[^»]+) » – « (?P<title>[^»]+) » dans l'émission « (?P<name>[^»]+) »,"
		r" (?:de nom public « (?P<public_name>[^»]+) »|sans nom public), (?P<hiding>masquée|affichée)"
	)
)
def play_in_show(
	empty_database: Connection, artist: str, title: str, name: str, public_name: str | None, hiding: str
) -> None:
	event = show(empty_database, name, public_name, hiding == "masquée")
	play(empty_database, 0, artist, title, finished=False, event=event)


@given(parsers.parse("{count:d} passages terminés, puis un passage en cours de « {artist} » – « {title} »"))
def plays_then_ongoing(empty_database: Connection, count: int, artist: str, title: str) -> None:
	for number in range(1, count + 1):
		play(empty_database, number, f"Artiste {number}", f"Titre {number}")
	play(empty_database, count + 1, artist, title, finished=False)


@given(parsers.parse("{count:d} passages terminés, sans passage en cours"))
def finished_plays(empty_database: Connection, count: int) -> None:
	for number in range(1, count + 1):
		play(empty_database, number, f"Artiste {number}", f"Titre {number}")


@given(parsers.parse("un passage terminé de « {artist} » – « {title} »"))
def finished_play(empty_database: Connection, artist: str, title: str) -> None:
	play(empty_database, -1, artist, title)


@given(parsers.parse("{count:d} passages terminés, masqués"))
def hidden_plays(empty_database: Connection, count: int) -> None:
	for number in range(1, count + 1):
		play(empty_database, number, f"Artiste {number}", f"Titre {number}", hidden_sound=True)


@given("le masquage de tous les sonores")
def hide_all(empty_database: Connection) -> None:
	empty_database.execute("UPDATE sounds SET hide_metadata = true")


@given("la page publique ne peut pas être écrite")
def page_impossible(bench: Bench) -> None:
	# Un répertoire à la place du fichier : même un compte administrateur ne peut pas l'écrire.
	bench_outputs(bench).paths.html.mkdir(parents=True)


# ─── Quand ─────────────────────────────────────────────────


@when("les sorties sont mises à jour")
def update(bench: Bench) -> None:
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		bench_outputs(bench).update(connection, START)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"l'artiste et le titre sont (?P<verdict>affichés|masqués) sur la sortie publique"))
def verdict_public(bench: Bench, verdict: str) -> None:
	update(bench)
	visible_list = ("Artiste secret" in page(bench)) and ("Titre secret" in page(bench))
	assert visible_list is (verdict == "affichés"), page(bench)
	if verdict == "masqués":
		assert "Radio Exemple" in page(bench)


@then(parsers.parse("la page publique montre « {text} »"))
def shown_page(bench: Bench, text: str) -> None:
	assert text in page(bench), page(bench)


@then(parsers.parse("la page publique montre {count:d} fois « {text} »"))
def shown_times_n_page(bench: Bench, count: int, text: str) -> None:
	assert page(bench).count(text) == count, page(bench)


@then(parsers.parse("la page publique ne montre pas « {text} »"))
def shown_page_not_text(bench: Bench, text: str) -> None:
	assert text not in page(bench), page(bench)


@then(parsers.parse("la page publique ne montre ni « {first} » ni « {second} »"))
def shown_page_not(bench: Bench, first: str, second: str) -> None:
	assert (first not in page(bench)) and (second not in page(bench)), page(bench)


@then(parsers.parse("la page publique montre « {title} » comme sonore à l'antenne"))
def on_air(bench: Bench, title: str) -> None:
	ongoing = re.search(r'<section class="en-cours">(.*?)</section>', page(bench), re.DOTALL)
	assert (ongoing is not None) and (title in ongoing.group(1)), page(bench)


@then(parsers.parse("la page publique liste {count:d} passages précédents, du plus récent au plus ancien"))
def previous_list(bench: Bench, count: int) -> None:
	list_ = re.search(r'<ol class="precedents">(.*?)</ol>', page(bench), re.DOTALL)
	assert list_ is not None, page(bench)
	titles = re.findall(r"Titre (\d+)", list_.group(1))
	assert titles == [str(n) for n in range(25, 25 - count, -1)], titles


@then("la page publique se rafraîchit toutes les 30 secondes")
def refreshed(bench: Bench) -> None:
	assert '<meta http-equiv="refresh" content="30">' in page(bench)


@then("la page publique ne montre pas l'emplacement du fichier")
def without_location(bench: Bench) -> None:
	assert ("/musique/" not in page(bench)) and (".flac" not in page(bench)), page(bench)


@then(parsers.parse("la playlist compte {count:d} entrées, du passage {first:d} au passage {last:d}"))
def playlist(bench: Bench, count: int, first: int, last: int) -> None:
	text = bench_outputs(bench).paths.pls.read_text(encoding="utf-8")
	files = re.findall(r"^File\d+=(.*)$", text, re.MULTILINE)
	assert text.startswith("[playlist]\n")
	assert (f"NumberOfEntries={count}" in text) and ("Version=2" in text)
	assert files == [f"/musique/{n}.flac" for n in range(first, last + 1)], files


@then("chaque entrée de la playlist donne l'artiste et le titre")
def playlist_titles(bench: Bench) -> None:
	text = bench_outputs(bench).paths.pls.read_text(encoding="utf-8")
	titles = re.findall(r"^Title(\d+)=(.*)$", text, re.MULTILINE)
	assert (titles) and (all(re.fullmatch(r"Artiste \d+ – Titre \d+", title) for _, title in titles)), titles


def csv_lines(bench: Bench, name: str) -> list[dict[str, str]]:
	path = bench_outputs(bench).paths.csv.parent / name
	with path.open(encoding="utf-8-sig", newline="") as file:
		return list(csv.DictReader(file, delimiter=";"))


@then(parsers.parse("le CSV « {name} » commence par l'en-tête et le BOM"))
def csv_header(bench: Bench, name: str) -> None:
	bytes_ = (bench_outputs(bench).paths.csv.parent / name).read_bytes()
	header = "﻿debut;fin;duree;artiste;titre;emplacement;evenement;sequence;banque;sans_incident\r\n"
	assert bytes_.startswith(header.encode()), bytes_[:120]


@then(parsers.parse("le CSV « {name} » a les lignes :"))
def expected_lines(bench: Bench, name: str, datatable: list[list[str]]) -> None:
	columns, *expected_list = datatable
	fetched_list = [[line[column] for column in columns] for line in csv_lines(bench, name)]
	assert fetched_list == expected_list, fetched_list


@then(parsers.re(r"le CSV « (?P<name>[^»]+) » a (?P<count>\d+) lignes? de passage"))
def line_count(bench: Bench, name: str, count: str) -> None:
	assert len(csv_lines(bench, name)) == int(count)


@then(parsers.parse("le journal du binaire a annoncé « {text} », en information"))
def announces(caplog: pytest.LogCaptureFixture, text: str) -> None:
	assert any((r.levelno == logging.INFO) and (text in r.getMessage()) for r in caplog.records), caplog.text


@then(parsers.parse("le journal du binaire a signalé « {text} », en anomalie"))
def anomaly(caplog: pytest.LogCaptureFixture, text: str) -> None:
	assert any((r.levelno == logging.WARNING) and (text in r.getMessage()) for r in caplog.records), caplog.text


@then("les sorties de Machin player sont celles de la configuration de test")
def configuration_outputs() -> None:
	configuration = configuration_test()
	outputs = Outputs.since(configuration)
	assert outputs.paths == configuration.outputs
	assert outputs.metadata == configuration.metadata
