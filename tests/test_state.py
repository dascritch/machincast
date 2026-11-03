"""Étapes de la socket d'état du binaire lecture (https://github.com/dascritch/machincast/issues/20).

Les étapes de la diffusion viennent de tests/broadcast_steps.py. La socket est créée dans le répertoire temporaire
du scénario.
"""

import json
import re
import socket
import stat
import threading
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.player.state import BusyStateSocket, StateSocket
from tests.broadcast_steps import Bench, Connection, create_sound, event, hour, plays, sound

scenarios("state.feature")

SPEC = Path(__file__).resolve().parents[1] / "doc" / "fr" / "spec.md"
DELAY = 3.0


@dataclass
class Client:
	message: dict[str, Any] | None = None
	received_list: list[dict[str, Any]] = field(default_factory=list)
	feed: threading.Thread | None = None


@pytest.fixture
def client() -> Client:
	return Client()


def bench_socket(bench: Bench) -> StateSocket:
	assert bench.state is not None
	return bench.state


def open_connection(bench: Bench) -> socket.socket:
	connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	connection.settimeout(DELAY)
	connection.connect(str(bench_socket(bench).path))
	return connection


def message(client: Client) -> dict[str, Any]:
	assert client.message is not None
	return client.message


def ongoing(client: Client) -> dict[str, Any]:
	current = message(client)["current"]
	assert isinstance(current, dict), message(client)
	return current


def next_(client: Client) -> dict[str, Any]:
	following = message(client)["next"]
	assert isinstance(following, dict), message(client)
	return following


# ─── Étant donné ───────────────────────────────────────────


@given("la socket d'état dans un répertoire temporaire")
def temporary_socket(bench: Bench, tmp_path: Path) -> None:
	bench.state = StateSocket(tmp_path / "run" / "machincast" / "lecture.sock")


@given(parsers.parse("la dernière lecture du sonore « {name} » a fini en incident"))
def last_playback_in_incident(empty_database: Connection, name: str) -> None:
	identifier = uuid.uuid4()
	for line_type, end in (("start", ""), ("end", ", played_duration, without_incident")):
		values = ", '1 s', false" if end else ""
		empty_database.execute(
			f"INSERT INTO airplay (play_id, line_type, logged_at, sound_id{end})"
			f" VALUES (%s, %s, '2026-10-13 12:00', %s{values})",
			(identifier, line_type, sound(empty_database, name)),
		)


# ─── Quand ─────────────────────────────────────────────────


@when("un client lit la socket d'état")
def read(bench: Bench, client: Client) -> None:
	with open_connection(bench) as connection, connection.makefile("r", encoding="utf-8") as playback:
		client.message = json.loads(playback.readline())


@when("un client reste connecté à la socket d'état")
def remain_connected(bench: Bench, client: Client) -> None:
	connection = open_connection(bench)
	connection.settimeout(None)

	def receive() -> None:
		with connection, connection.makefile("r", encoding="utf-8") as playback:
			for line in playback:
				client.received_list.append(json.loads(line))

	client.feed = threading.Thread(target=receive, daemon=True)
	client.feed.start()


@when("un client se connecte puis se déconnecte aussitôt")
def short_connection(bench: Bench) -> None:
	open_connection(bench).close()


@when(parsers.parse("le sonore « {name} » est désactivé"))
def disable(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE sounds SET state = 'disabled' WHERE id = %s", (sound(empty_database, name),))


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le message est en version {version:d}, à l'état « {state} »"))
def version_and_state(client: Client, version: int, state: str) -> None:
	assert (message(client)["version"] == version) and (message(client)["state"] == state), message(client)


@then(
	parsers.re(
		r"le sonore en cours est « (?P<title>[^»]+) », un (?P<type>fichier|stream)"
		r" de l'événement « (?P<event>[^»]+) »"
	)
)
def ongoing_sound(client: Client, title: str, type: str, event: str) -> None:
	current = ongoing(client)
	# Le texte du scénario dit « fichier » ; la socket donne la valeur du protocole, « file ».
	kind = {"fichier": "file"}.get(type, type)
	assert (current["title"], current["type"], current["event"]) == (title, kind, event), current


@then(parsers.parse("il a commencé au « {start} », dure {duration:d} seconde et finira au « {end} »"))
def ongoing_time(client: Client, start: str, duration: int, end: str) -> None:
	current = ongoing(client)
	assert hour(current["start"]) == hour(start), current
	assert (current["duration"] == duration) and (hour(current["estimated_end"]) == hour(end)), current


@then(parsers.re(r"l'emplacement du (?P<which>sonore en cours|prochain sonore) est le fichier de « (?P<name>[^»]+) »"))
def file_location(client: Client, bench: Bench, which: str, name: str) -> None:
	if which == "sonore en cours":
		announced_sound = ongoing(client)
	else:
		announced_sound = next_(client)
	assert announced_sound["location"] == str(bench.files[name]), announced_sound


@then(parsers.parse("l'emplacement du sonore en cours est l'adresse du flux « {stream} »"))
def stream_location(client: Client, server: Any, stream: str) -> None:
	assert ongoing(client)["location"] == server.address(stream), ongoing(client)


@then("sa progression est entre 0 et 1")
def progress(client: Client) -> None:
	value = ongoing(client)["progress"]
	assert (isinstance(value, float)) and (0 < value < 1), ongoing(client)


@then(parsers.parse("sa durée et sa progression sont inconnues, et il finira au « {end} », avec son événement"))
def unknown_duration(client: Client, end: str) -> None:
	current = ongoing(client)
	assert (current["duration"] is None) and (current["progress"] is None), current
	assert hour(current["estimated_end"]) == hour(end), current
	assert current["position"] > 0, current


@then("il n'y a ni sonore en cours ni prochain sonore")
def nothing(client: Client) -> None:
	assert (message(client)["current"] is None) and (message(client)["next"] is None), message(client)


@then(parsers.re(r"le prochain sonore est « (?P<title>[^»]+) », (?P<healthy>sain|pas sain|à l'état sain inconnu)$"))
def next_sound(client: Client, title: str, healthy: str) -> None:
	following = next_(client)
	expected = {"sain": True, "pas sain": False, "à l'état sain inconnu": None}[healthy]
	assert (following["title"] == title) and (following["healthy"] is expected), following


@then(parsers.parse("il commencera au « {start} », dure {duration:d} seconde et finira au « {end} »"))
def next_time(client: Client, start: str, duration: int, end: str) -> None:
	following = next_(client)
	assert hour(following["estimated_start"]) == hour(start), following
	assert (following["duration"] == duration) and (hour(following["estimated_end"]) == hour(end)), following


@then(parsers.parse("le prochain sonore commencera au « {start} » et finira au « {end} »"))
def start_and_next_end(client: Client, start: str, end: str) -> None:
	following = next_(client)
	assert hour(following["estimated_start"]) == hour(start), following
	assert hour(following["estimated_end"]) == hour(end), following


@then(parsers.parse("le prochain sonore commencera au « {start} »"))
def next_start(client: Client, start: str) -> None:
	following = next_(client)
	assert hour(following["estimated_start"]) == hour(start), following


@then("le deuxième passage est le prochain sonore annoncé")
def held_reservation(empty_database: Connection, client: Client) -> None:
	names = [p[0] for p in plays(empty_database)]
	assert (len(names) == 2) and (names[1] == next_(client)["title"]), (names, next_(client))


def wait_end(client: Client) -> None:
	assert client.feed is not None
	client.feed.join(DELAY)
	assert not client.feed.is_alive(), "le client attend toujours la fin de la socket"


@then(parsers.re(r"le client a vu passer en cours (?P<list_>.+)"))
def seen_list(client: Client, list_: str) -> None:
	wait_end(client)
	titles: list[str] = []
	for received in client.received_list:
		current = received["current"]
		if (current is not None) and ((not titles) or (titles[-1] != current["title"])):
			titles.append(current["title"])
	assert titles == [n.strip(" «»") for n in list_.split(",")], titles


@then(parsers.parse("son dernier message est à l'état « {state} »"))
def last(client: Client, state: str) -> None:
	wait_end(client)
	assert (client.received_list) and (client.received_list[-1]["state"] == state), client.received_list[-1:]


@then("la socket d'état n'existe plus")
def erased_socket(bench: Bench) -> None:
	assert not bench_socket(bench).path.exists()


@then("le répertoire de la socket d'état n'est accessible qu'à son propriétaire")
def private_directory(bench: Bench) -> None:
	assert stat.S_IMODE(bench_socket(bench).path.parent.stat().st_mode) == 0o700


@then("la socket d'état n'est lisible et modifiable que par son propriétaire")
def private_socket(bench: Bench) -> None:
	assert stat.S_IMODE(bench_socket(bench).path.stat().st_mode) == 0o600


@then("une seconde diffusion sur la même socket d'état est refusée, car un autre Machin player diffuse déjà")
def broadcast_second(bench: Bench) -> None:
	with pytest.raises(BusyStateSocket, match="un autre Machin player diffuse déjà"):
		StateSocket(bench_socket(bench).path).open_()
	assert bench_socket(bench).path.exists()


def fields(value: object) -> set[str]:
	if not isinstance(value, dict):
		return set()
	return set(value) | {key for under in value.values() for key in fields(under)}


@then("chaque champ du message figure dans la spécification, § 5.4")
def documented_fields(client: Client) -> None:
	text = SPEC.read_text(encoding="utf-8")
	section = re.search(r"### 5\.4 Socket d'état\n(.*?)\n### ", text, re.DOTALL)
	assert section is not None
	absent_list = {key for key in fields(message(client)) if f"`{key}`" not in section.group(1)}
	assert not absent_list, f"absents de spec § 5.4 : {sorted(absent_list)}"


# ─── Playlist immédiate (https://github.com/dascritch/machincast/issues/228) ─────


def upcoming(client: Client) -> list[dict[str, Any]]:
	sounds = message(client)["upcoming"]
	assert isinstance(sounds, list), message(client)
	return sounds


@then(parsers.re(r"la socket annonce les sonores à venir (?P<list_>.+), sains"))
def upcoming_sounds(client: Client, list_: str) -> None:
	sounds = upcoming(client)
	assert [s["title"] for s in sounds] == [n.strip(" «»") for n in list_.split(",")], sounds
	assert all(s["healthy"] is True for s in sounds), sounds


@then(
	parsers.re(
		r"le (?P<which>premier|dernier) sonore à venir commencera au « (?P<start>[^»]+) »"
		r" et finira au « (?P<end>[^»]+) »"
	)
)
def upcoming_hours(client: Client, which: str, start: str, end: str) -> None:
	fetched_sound = upcoming(client)[0 if which == "premier" else -1]
	assert hour(fetched_sound["estimated_start"]) == hour(start), fetched_sound
	assert hour(fetched_sound["estimated_end"]) == hour(end), fetched_sound


@then(parsers.parse("le premier sonore à venir vient de l'événement « {event} », permanent"))
def upcoming_event(client: Client, event: str) -> None:
	fetched_sound = upcoming(client)[0]
	assert (fetched_sound["event"], fetched_sound["event_start"], fetched_sound["event_end"]) == (
		event,
		None,
		None,
	), fetched_sound


@then("il n'y a aucun sonore à venir")
def no_upcoming(client: Client) -> None:
	assert upcoming(client) == []


@then(parsers.parse("le sonore en cours est joué par un événement de priorité « {priority} »"))
def ongoing_priority(client: Client, priority: str) -> None:
	assert ongoing(client)["event_priority"] == priority


# ─── Contexte du sonore (https://github.com/dascritch/machincast/issues/144) ─────


def identifier_of(database: Connection, table: str, name: str | None) -> int | None:
	if name is None:
		return None
	line = database.execute(f"SELECT id FROM {table} WHERE internal_name = %s", (name,)).fetchone()  # noqa: S608
	assert line is not None, name
	return int(str(line[0]))


@then(
	parsers.re(
		r"le (?P<which>sonore en cours|prochain sonore) vient de (?:la banque « (?P<bank>[^»]+) »|la séquence"
		r" « (?P<sequence>[^»]+) »), sans (?:séquence|banque), de l'événement « (?P<event>[^»]+) », permanent"
	)
)
def sound_context(
	client: Client,
	empty_database: Connection,
	which: str,
	bank: str | None,
	sequence: str | None,
	event: str,
) -> None:
	fetched_sound = next_(client)
	if which == "sonore en cours":
		fetched_sound = ongoing(client)
	expected = {
		"bank": bank,
		"bank_id": identifier_of(empty_database, "banks", bank),
		"sequence": sequence,
		"sequence_id": identifier_of(empty_database, "sequences", sequence),
		"event": event,
		"event_id": identifier_of(empty_database, "events", event),
		"event_start": None,
		"event_end": None,
	}
	assert {key: fetched_sound.get(key) for key in expected} == expected, fetched_sound


@then(parsers.parse("l'événement du sonore en cours va du « {start} » au « {end} »"))
def event_bounds(client: Client, start: str, end: str) -> None:
	current = ongoing(client)
	assert (current["event_start"], current["event_end"]) == (
		hour(start).replace(tzinfo=None).isoformat(),
		hour(end).replace(tzinfo=None).isoformat(),
	), current


@then(parsers.parse("le texte public du sonore en cours est « {text} »"))
def public_text(client: Client, text: str) -> None:
	assert ongoing(client)["public_text"] == text


@then("le prochain sonore n'a pas de texte public")
def without_public_text(client: Client) -> None:
	assert "public_text" not in next_(client)


# ─── Coupure par un événement à venir (https://github.com/dascritch/machincast/issues/169) ─────


@given(parsers.parse("le sonore « {name} » dure {duration:d} secondes en base"))
def duration_in_database(empty_database: Connection, name: str, duration: int) -> None:
	"""La durée en base décide des heures annoncées ; le fichier joué reste le court fichier de test."""
	empty_database.execute(
		"UPDATE sounds SET duration = %s WHERE id = %s", (timedelta(seconds=duration), sound(empty_database, name))
	)


@given(parsers.parse("la banque « {name} » est marquée « ne pas répéter »"))
def no_repeat(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE banks SET no_repeat = true WHERE internal_name = %s", (name,))


@given(
	parsers.re(
		r"l'émission « (?P<name>[^»]+) » de (?P<start>[\d:]+) à (?P<end>[\d:]+),"
		r" qui joue la banque « (?P<bank>[^»]+) », puis le sonore « (?P<sound_name>[^»]+) »"
	)
)
def bank_show_then_sound(
	bench: Bench,
	empty_database: Connection,
	tmp_path: Path,
	name: str,
	start: str,
	end: str,
	bank: str,
	sound_name: str,
) -> None:
	event(bench, empty_database, tmp_path, name, "show", hour(f"2026-10-14 {start}"), hour(f"2026-10-14 {end}"), [])
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, bank_id)"
		" SELECT e.id, 1, b.id FROM events e, banks b WHERE e.internal_name = %s AND b.internal_name = %s",
		(name, bank),
	)
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, sound_id) SELECT id, 2, %s FROM events WHERE internal_name = %s",
		(create_sound(bench, empty_database, tmp_path, sound_name), name),
	)


@then(
	parsers.re(
		r"le sonore en cours finira au « (?P<end>[^»]+) »,"
		r" (?:coupé par l'événement « (?P<event>[^»]+) »|sans être coupé)"
	)
)
def ongoing_sound_end(client: Client, empty_database: Connection, end: str, event: str | None) -> None:
	current = ongoing(client)
	assert hour(current["estimated_end"]) == hour(end), current
	expected = None
	if event is not None:
		expected = identifier_of(empty_database, "events", event)
	assert (current["cut_by"], current["cut_by_id"]) == (event, expected), current


@then(parsers.parse("le prochain sonore est joué par l'événement « {event} »"))
def next_event(client: Client, event: str) -> None:
	assert next_(client)["event"] == event, next_(client)


@given(
	parsers.re(
		r"l'émission « (?P<name>[^»]+) » de (?P<start>[\d:]+) à (?P<end>[\d:]+), avec la banque aléatoire"
		r" « (?P<bank>[^»]+) » des sonores (?P<list_>.+)"
	)
)
def random_bank_show(
	bench: Bench, empty_database: Connection, tmp_path: Path, name: str, start: str, end: str, bank: str, list_: str
) -> None:
	event(bench, empty_database, tmp_path, name, "show", hour(f"2026-10-14 {start}"), hour(f"2026-10-14 {end}"), [])
	created = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'random') RETURNING id", (bank,)
	).fetchone()
	assert created is not None
	for position, sound_name in enumerate((n.strip(" «»") for n in list_.split(",")), start=1):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
			(created[0], create_sound(bench, empty_database, tmp_path, sound_name), position),
		)
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, bank_id) SELECT id, 1, %s FROM events WHERE internal_name = %s",
		(created[0], name),
	)


@then("le sonore en cours n'a pas de fin estimée, sans être coupé")
def nor_end_nor_cutoff(client: Client) -> None:
	current = ongoing(client)
	assert (current["estimated_end"], current["cut_by"], current["cut_by_id"]) == (None, None, None), current
