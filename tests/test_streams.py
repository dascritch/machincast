"""Étapes de la diffusion des streams (https://github.com/dascritch/machincast/issues/16).

Les étapes communes aux scénarios de la diffusion, dont le serveur de flux local (tests/flux.py), sont dans
tests/broadcast_steps.py.
"""

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.player import engine
from tests.broadcast_steps import Bench, Connection, create_sound, hour, plays, sound, sounds_of
from tests.log_texts import shown, stored
from tests.sounds import TEST_TAGS
from tests.stream import StreamServer

scenarios("streams.feature")


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le flux « {stream} » est hors ligne"))
def stream_outside_line(server: StreamServer, stream: str) -> None:
	server.in_line[stream] = False


@given(parsers.parse("le stream « {name} » sur le feed « {feed} » du flux « {stream} »"))
def stream_feed(server: StreamServer, empty_database: Connection, name: str, feed: str, stream: str) -> None:
	created = empty_database.execute(
		"INSERT INTO feeds (name, url) VALUES (%s, %s) RETURNING id",
		(feed, server.address(stream)),
	).fetchone()
	assert created is not None
	empty_database.execute("INSERT INTO sounds (type, feed_id, title) VALUES ('stream', %s, %s)", (created[0], name))


@given(
	parsers.re(
		r"l'émission « (?P<name>[^»]+) » de (?P<start>[\d:]+) à (?P<end>[\d:]+), avec la séquence des sonores"
		r" « (?P<before>[^»]+) », « (?P<stream>[^»]+) », « (?P<after>[^»]+) »"
	)
)
def show_with_sequence(
	bench: Bench,
	empty_database: Connection,
	tmp_path: Path,
	name: str,
	start: str,
	end: str,
	before: str,
	stream: str,
	after: str,
) -> None:
	"""Le stream existe déjà ; les deux autres sonores sont créés."""
	sequence = empty_database.execute(
		"INSERT INTO sequences (internal_name) VALUES (%s) RETURNING id", (f"Séquence de {name}",)
	).fetchone()
	event = empty_database.execute(
		"INSERT INTO events (internal_name, priority, starts_at, ends_at) VALUES (%s, 'show', %s, %s) RETURNING id",
		(name, hour(f"2026-10-14 {start}"), hour(f"2026-10-14 {end}")),
	).fetchone()
	assert (sequence is not None) and (event is not None)
	identifiers = (
		create_sound(bench, empty_database, tmp_path, before),
		sound(empty_database, stream),
		create_sound(bench, empty_database, tmp_path, after),
	)
	for position, identifier in enumerate(identifiers, start=1):
		empty_database.execute(
			"INSERT INTO sequence_items (sequence_id, position, sound_id) VALUES (%s, %s, %s)",
			(sequence[0], position, identifier),
		)
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, sequence_id) VALUES (%s, 1, %s)",
		(event[0], sequence[0]),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le flux « {stream} » tombe"))
def dropped_stream(server: StreamServer, stream: str) -> None:
	server.in_line[stream] = False


@given("un délai de garde de 2 secondes, et un lecteur qui ne signale pas un flux muet")
def keeps_short(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Le délai de connexion de la source HTTP, d'ordinaire le délai de garde, n'expire plus : comme libsoup en HTTP/2
	(https://github.com/dascritch/machincast/issues/278), seule la garde voit le flux gelé."""
	monkeypatch.setattr(engine, "GUARD_DELAY", timedelta(seconds=2))
	monkeypatch.setattr(engine, "CONNECTION_DELAY_SECONDS", 3600)


@when(parsers.parse("le flux « {stream} » gèle, sans fermer sa connexion"))
def frozen_stream(server: StreamServer, stream: str) -> None:
	"""https://github.com/dascritch/machincast/issues/278 : comme un réseau coupé."""
	server.frozen_list.add(stream)


@when(parsers.parse("le flux « {stream} » dégèle"))
def thawed_stream(server: StreamServer, stream: str) -> None:
	server.frozen_list.discard(stream)


@when(parsers.re(r"le flux « (?P<stream>[^»]+) » (?P<what>devient muet, sa connexion ouverte|retrouve son son)"))
def silent_stream(server: StreamServer, stream: str, what: str) -> None:
	"""https://github.com/dascritch/machincast/issues/122"""
	if what == "retrouve son son":
		server.silent_list.discard(stream)
	else:
		server.silent_list.add(stream)


@then(parsers.parse("la voie du flux « {stream} » est muette"))
def silent_track(bench: Bench, server: StreamServer, stream: str) -> None:
	"""https://github.com/dascritch/machincast/issues/122 : la voie gardée pour la reprise ne s'entend pas."""
	assert bench.engine is not None
	track = bench.engine.played_list[server.address(stream)]
	assert (track.state == "playing") and (track.volume_to(track.position()) == 0.0), (
		track.state,
		track.volume_to(track.position()),
	)


@then(parsers.parse("le serveur de flux n'a reçu qu'une connexion"))
def a_connection(server: StreamServer) -> None:
	assert server.received_list == 1, server.received_list


@when(parsers.parse("le flux « {stream} » revient"))
def stream_comes_back(server: StreamServer, stream: str) -> None:
	server.in_line[stream] = True


# ─── Alors ─────────────────────────────────────────────────


def locations(database: Connection, name: str) -> list[str]:
	lines = database.execute("SELECT DISTINCT location FROM airplay WHERE title = %s", (name,)).fetchall()
	return [str(line[0]) for line in lines]


@then(parsers.parse("le passage « {name} » a pour emplacement l'adresse du flux « {stream} »"))
def stream_location(server: StreamServer, empty_database: Connection, name: str, stream: str) -> None:
	assert locations(empty_database, name) == [server.address(stream)]


@then("aucun passage ne porte l'artiste ou le titre des tags du flux")
def without_stream_tags(empty_database: Connection) -> None:
	lines = empty_database.execute("SELECT artist, title FROM airplay").fetchall()
	assert lines
	for artist, title in lines:
		assert artist is None, artist
		assert str(title) not in TEST_TAGS, title


@then(
	parsers.re(
		r"l'airplay montre « (?P<stream>[^»]+) », puis des sonores de « (?P<event>[^»]+) »,"
		r" puis « (?P<end_stream>[^»]+) »$"
	)
)
def replacement(
	empty_database: Connection, stream: str, event: str, end_stream: str, names: list[str] | None = None
) -> None:
	if names is None:
		names = [p[0] for p in plays(empty_database)]
	assert (len(names) >= 3) and (names[0] == stream) and (names[-1] == end_stream), names
	assert set(names[1:-1]) <= sounds_of(empty_database, event), names


@then(
	parsers.parse("l'airplay montre « {before} », « {stream} », puis des sonores de « {event} », puis « {end_stream} »")
)
def replacement_after(empty_database: Connection, before: str, stream: str, event: str, end_stream: str) -> None:
	names = [p[0] for p in plays(empty_database)]
	assert names[0] == before, names
	replacement(empty_database, stream, event, end_stream, names[1:])


@then(parsers.re(r"l'airplay montre « (?P<stream>[^»]+) », puis des sonores de « (?P<event>[^»]+) »$"))
def fallback(empty_database: Connection, stream: str, event: str) -> None:
	names = [p[0] for p in plays(empty_database)]
	assert (len(names) >= 2) and (names[0] == stream), names
	assert set(names[1:]) <= sounds_of(empty_database, event), names


@then(parsers.parse("le premier passage « {name} » a fini en incident"))
def first_in_incident(empty_database: Connection, name: str) -> None:
	first = next(p for p in plays(empty_database) if p[0] == name)
	assert (first[2] is not None) and (first[3] is False), first


@then(parsers.re(r"le sonore joué avant la reprise a fini (?P<moment>au début|après le début) de la reprise"))
def end_before_resumption(empty_database: Connection, moment: str) -> None:
	lines = plays(empty_database)
	resumption = lines[-1]
	before = lines[-2]
	assert before[2] is not None, before
	if moment == "au début":
		assert before[2] == resumption[1], (before, resumption)
	else:
		assert before[2] > resumption[1], (before, resumption)


@then(parsers.parse("l'airplay montre {count:d} passage « {name} »"))
def play_count(empty_database: Connection, count: int, name: str) -> None:
	assert [p[0] for p in plays(empty_database)].count(name) == count, plays(empty_database)


@then("le stream repris joue à plein volume")
def stream_to_full_volume(bench: Bench) -> None:
	assert (bench.broadcast is not None) and (bench.broadcast.current is not None)
	current = bench.broadcast.current
	assert current.parameters.stream, current
	assert current.track.volume_to(current.track.position()) == pytest.approx(1.0)


def log_lines(database: Connection, kind: str) -> list[tuple[int, str, str]]:
	lines = database.execute(
		"SELECT id, level::text, message FROM log WHERE kind = %s ORDER BY id", (stored(kind),)
	).fetchall()
	return [(int(str(i)), str(n), shown(m)) for i, n, m in lines]


@then(parsers.parse("le log contient {count:d} incident « {kind} », qui donne l'adresse du flux « {stream} »"))
def stream_incident(server: StreamServer, empty_database: Connection, count: int, kind: str, stream: str) -> None:
	lines = log_lines(empty_database, kind)
	assert len(lines) == count, lines
	assert all((level == "incident") and (server.address(stream) in message) for _, level, message in lines), lines


@then(parsers.parse("l'incident « {kind} » dit « {text} »"))
def incident_says(empty_database: Connection, kind: str, text: str) -> None:
	assert all(text in message for _, _, message in log_lines(empty_database, kind)), log_lines(empty_database, kind)


def soup_forces_http1(environment: dict[str, str]) -> str:
	"""Ce que vaut SOUP_FORCE_HTTP1 dans un programme de MachinCast, une fois le paquet chargé."""
	command = [sys.executable, "-c", "import os, machincast; print(os.environ.get('SOUP_FORCE_HTTP1'))"]
	return subprocess.run(command, env=environment, capture_output=True, text=True, check=True).stdout.strip()


@then("un programme de MachinCast demande HTTP/1.1 à libsoup")
def http1() -> None:
	environment = {key: value for key, value in os.environ.items() if key != "SOUP_FORCE_HTTP1"}
	assert soup_forces_http1(environment) == "1"


@then(parsers.parse("l'incident « {following} » suit l'incident « {first} »"))
def incident_order(empty_database: Connection, following: str, first: str) -> None:
	assert log_lines(empty_database, first)[0][0] < log_lines(empty_database, following)[0][0]


@then(parsers.parse("l'airplay montre des sonores de « {before} », puis « {stream} », puis des sonores de « {after} »"))
def cutoff_by_feed(empty_database: Connection, before: str, stream: str, after: str) -> None:
	"""Le stream passe une seule fois, entre des sonores des événements (https://github.com/dascritch/machincast/issues/323)."""
	names = [p[0] for p in plays(empty_database)]
	assert names.count(stream) == 1, names
	rank = names.index(stream)
	assert 0 < rank < len(names) - 1, names
	assert set(names[:rank]) <= sounds_of(empty_database, before), names
	assert set(names[rank + 1 :]) <= sounds_of(empty_database, after), names


@given(parsers.parse("le feed « {feed} » a une mémoire tampon de {seconds:d} secondes"))
def feed_buffer(empty_database: Connection, feed: str, seconds: int) -> None:
	empty_database.execute("UPDATE feeds SET buffer_duration = %s WHERE name = %s", (timedelta(seconds=seconds), feed))


@then(
	parsers.parse(
		"la voie du flux « {stream} » a rempli sa mémoire tampon de {seconds:d} secondes, en attendant au moins "
		"{wait:d} secondes avant de jouer"
	)
)
def prefilled(bench: Bench, server: StreamServer, stream: str, seconds: int, wait: int) -> None:
	"""Elle a joué, mais moins longtemps que la diffusion n'a tourné : elle a d'abord attendu sa mémoire tampon
	(https://github.com/dascritch/machincast/issues/351)."""
	assert bench.engine is not None
	track = bench.engine.played_list[server.address(stream)]
	assert track.buffer == timedelta(seconds=seconds)
	assert track.buffering >= 100, track.buffering
	assert track.final_position is not None
	assert timedelta(seconds=0.5) < track.final_position <= timedelta(seconds=6 - wait), track.final_position
