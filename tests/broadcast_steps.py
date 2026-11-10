"""Étapes partagées des scénarios de la diffusion (https://github.com/dascritch/machincast/issues/88).

Chargé comme greffon pytest par tests/conftest.py : la boucle de diffusion
(https://github.com/dascritch/machincast/issues/88) et les streams (https://github.com/dascritch/machincast/issues/16)
s'en servent. Le banc tient l'horloge, le moteur sur la sortie factice et la diffusion, connectée avec le rôle de
la lecture.
"""

import socket
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, then, when

from machincast.clock import FixedClock
from machincast.configuration import Audio, Crossfades, DeadAirSettings
from machincast.database import Role, open_connection
from machincast.player.analysis import Analyser
from machincast.player.broadcast import Broadcast
from machincast.player.engine import AudioEngine, PlaybackTrack, Track
from machincast.player.outputs import Outputs
from machincast.player.saving import LEVELS
from machincast.player.simulation import SimulatedEngine
from machincast.player.state import StateSocket, request_reread_grid
from machincast.randomness import create_randomness
from tests.database_fixtures import configuration_test, sample_database_parameters
from tests.log_texts import shown, stored
from tests.sounds import sample_copy
from tests.stream import StreamServer

Connection = psycopg.Connection[tuple[object, ...]]
REAL_STEP = 0.05
TEST_RECONNECTION_DELAY = timedelta(seconds=0.2)
"""Délai entre deux tentatives de reconnexion d'un stream, raccourci pour les scénarios."""


class RecordingEngine(AudioEngine):
	"""Le moteur audio de la diffusion, qui garde chaque voie jouée, par fichier, même finie."""

	def __init__(self, audio: Audio, real_time: bool = True, dead_air: DeadAirSettings | None = None) -> None:
		super().__init__(audio, real_time, dead_air=dead_air)
		self.played_list: dict[str, Track] = {}

	def play(
		self,
		path: Path | str,
		duration: timedelta | None,
		start_crossfade: timedelta = timedelta(0),
		end_crossfade: timedelta = timedelta(0),
		silent: bool = False,
		offset: timedelta | None = None,
		departure: float = 0.0,
		arrival: float = 0.0,
		buffer: timedelta | None = None,
	) -> Track:
		track = super().play(path, duration, start_crossfade, end_crossfade, silent, offset, departure, arrival, buffer)
		self.played_list[str(path)] = track
		return track


class RecordingSimulatedEngine(SimulatedEngine):
	"""Le moteur simulé de la simulation, qui garde la montée de chaque sonore joué, par nom de sonore : chaque
	fichier est dans un répertoire au nom de son sonore (create_sound)."""

	def __init__(self, clock: FixedClock) -> None:
		super().__init__(clock)
		self.rises: dict[str, timedelta] = {}
		self.opened_list: list[tuple[str, datetime, bool]] = []
		"""Chaque voie ouverte : son chemin ou son adresse, l'heure du binaire, et si elle est muette."""

	def play(
		self,
		path: Path | str,
		duration: timedelta | None,
		start_crossfade: timedelta = timedelta(0),
		end_crossfade: timedelta = timedelta(0),
		silent: bool = False,
		offset: timedelta | None = None,
		departure: float = 0.0,
		arrival: float = 0.0,
		buffer: timedelta | None = None,
	) -> PlaybackTrack:
		self.rises[Path(str(path)).parent.name] = start_crossfade
		self.opened_list.append((str(path), self.clock.now(), silent))
		return super().play(path, duration, start_crossfade, end_crossfade, silent, offset, departure, arrival, buffer)


ITEMS = {
	"saute au sonore suivant": "sound",
	"saute après la séquence": "sequence",
	"coupe l'événement par le fil musical": "event",
}
"""Interruptions manuelles (https://github.com/dascritch/machincast/issues/228), par leur texte dans les scénarios."""


@dataclass
class Bench:
	clock: FixedClock | None = None
	broadcast: Broadcast | None = None
	engine: RecordingEngine | None = None
	connection: Connection | None = None
	outputs: Outputs | None = None
	"""Modules de sortie de la diffusion ; aucun par défaut."""
	state: StateSocket | None = None
	"""Socket d'état de la diffusion ; aucune par défaut."""
	files: dict[str, Path] = field(default_factory=dict)
	crossfades: Crossfades = field(default_factory=Crossfades)
	"""Crossfades de la configuration : sans durée par défaut, sauf si le scénario en donne."""
	analyser: Analyser | None = None
	"""Analyse du prochain sonore (https://github.com/dascritch/machincast/issues/181) : aucune par défaut."""
	simulated: RecordingSimulatedEngine | None = None
	"""Moteur simulé, qui suit l'horloge du binaire, quand la diffusion démarre sur lui."""
	dead_air: DeadAirSettings = field(default_factory=DeadAirSettings)
	"""Blanc dans un sonore (https://github.com/dascritch/machincast/issues/122) : celui de la configuration par
	défaut, sauf si le scénario en règle un."""


@pytest.fixture
def bench() -> Iterator[Bench]:
	bench = Bench()
	yield bench
	if bench.state is not None:
		bench.state.shut_down()
	if bench.engine is not None:
		bench.engine.shut_down()
	if bench.connection is not None:
		bench.connection.close()


def seconds(text: str) -> float:
	return float(text.replace(",", "."))


def hour(text: str) -> datetime:
	return datetime.fromisoformat(text).astimezone()


def clock(bench: Bench) -> FixedClock:
	assert bench.clock is not None
	return bench.clock


def broadcast(bench: Bench) -> Broadcast:
	assert bench.broadcast is not None
	return bench.broadcast


def sound(database: Connection, name: str) -> int:
	line = database.execute("SELECT id FROM sounds WHERE title = %s", (name,)).fetchone()
	assert line is not None, f"sonore {name} inconnu"
	return int(str(line[0]))


def create_sound(bench: Bench, database: Connection, directory: Path, name: str) -> int:
	folder = directory / name
	folder.mkdir()
	file = sample_copy("flac", folder)
	bench.files[name] = file
	state = file.stat()
	line = database.execute(
		"INSERT INTO sounds (type, location, state, title, duration, file_modified_at, file_size)"
		" VALUES ('file', %s, 'active', %s, '1 s', %s, %s) RETURNING id",
		(str(file), name, datetime.fromtimestamp(state.st_mtime, tz=UTC), state.st_size),
	).fetchone()
	assert line is not None
	return int(str(line[0]))


def event(
	bench: Bench,
	database: Connection,
	directory: Path,
	name: str,
	priority: str,
	start: datetime | None,
	end: datetime | None,
	sounds: list[str],
) -> None:
	created = database.execute(
		"INSERT INTO events (internal_name, priority, starts_at, ends_at) VALUES (%s, %s, %s, %s) RETURNING id",
		(name, priority, start, end),
	).fetchone()
	assert created is not None
	for position, sound_name in enumerate(sounds, start=1):
		existing = database.execute("SELECT id FROM sounds WHERE title = %s", (sound_name,)).fetchone()
		if existing is None:
			identifier = create_sound(bench, database, directory, sound_name)
		else:
			identifier = int(str(existing[0]))
		database.execute(
			"INSERT INTO event_items (event_id, position, sound_id) VALUES (%s, %s, %s)",
			(created[0], position, identifier),
		)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'horloge du binaire au « {instant} »"))
def clock_to(bench: Bench, instant: str) -> None:
	bench.clock = FixedClock(hour(instant))


@given(parsers.re(r"le fil musical permanent « (?P<name>[^»]+) », avec les sonores (?P<list_>.+)"))
def feed(bench: Bench, empty_database: Connection, tmp_path: Path, name: str, list_: str) -> None:
	names = []
	for n in list_.split(","):
		names.append(n.strip(" «»"))
	event(bench, empty_database, tmp_path, name, "background_programming", None, None, names)


@given(
	parsers.re(
		r"le fil musical permanent « (?P<name>[^»]+) », avec la banque (?P<mode>séquentielle|aléatoire)"
		r" « (?P<bank>[^»]+) » des sonores (?P<list_>.+)"
	)
)
def feed_with_bank(
	bench: Bench, empty_database: Connection, tmp_path: Path, name: str, mode: str, bank: str, list_: str
) -> None:
	chosen = "random"
	if mode == "séquentielle":
		chosen = "sequential"
	created = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, %s) RETURNING id",
		(bank, chosen),
	).fetchone()
	assert created is not None
	n_list = []
	for n in list_.split(","):
		n_list.append(n.strip(" «»"))
	for position, sound_name in enumerate(n_list, start=1):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
			(created[0], create_sound(bench, empty_database, tmp_path, sound_name), position),
		)
	created_event = empty_database.execute(
		"INSERT INTO events (internal_name, priority) VALUES (%s, 'background_programming') RETURNING id", (name,)
	).fetchone()
	assert created_event is not None
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, bank_id) VALUES (%s, 1, %s)",
		(created_event[0], created[0]),
	)


@given(
	parsers.re(
		r"(?P<category>l'émission|le spécial) « (?P<name>[^»]+) » de (?P<start>[\d:]+) à (?P<end>[\d:]+),"
		r" avec le sonore « (?P<sound_name>[^»]+) »"
	)
)
def show(
	bench: Bench,
	empty_database: Connection,
	tmp_path: Path,
	category: str,
	name: str,
	start: str,
	end: str,
	sound_name: str,
) -> None:
	chosen = "special"
	if category == "l'émission":
		chosen = "show"
	event(
		bench,
		empty_database,
		tmp_path,
		name,
		chosen,
		hour(f"2026-10-14 {start}"),
		hour(f"2026-10-14 {end}"),
		[sound_name],
	)


@given(
	parsers.re(
		r"(?P<category>l'émission|le spécial) « (?P<name>[^»]+) » de (?P<start>[\d:]+) à (?P<end>[\d:]+),"
		r" avec les sonores (?P<list_>.+)"
	)
)
def sound_show(
	bench: Bench, empty_database: Connection, tmp_path: Path, category: str, name: str, start: str, end: str, list_: str
) -> None:
	chosen = "special"
	if category == "l'émission":
		chosen = "show"
	n_list = []
	for n in list_.split(","):
		n_list.append(n.strip(" «»"))
	event(
		bench,
		empty_database,
		tmp_path,
		name,
		chosen,
		hour(f"2026-10-14 {start}"),
		hour(f"2026-10-14 {end}"),
		n_list,
	)


@given(parsers.re(r"l'émission « (?P<name>[^»]+) » de (?P<start>[\d:]+) à (?P<end>[\d:]+), sans élément"))
def empty_show(bench: Bench, empty_database: Connection, tmp_path: Path, name: str, start: str, end: str) -> None:
	"""Une émission à compléter plus tard (https://github.com/dascritch/machincast/issues/253)."""
	event(bench, empty_database, tmp_path, name, "show", hour(f"2026-10-14 {start}"), hour(f"2026-10-14 {end}"), [])


@given(
	parsers.re(
		r"le spécial « (?P<name>[^»]+) » à partir de (?P<start>[\d:]+), sans fin, avec les sonores (?P<list_>.+)"
	)
)
def special_without_sound_end(
	bench: Bench, empty_database: Connection, tmp_path: Path, name: str, start: str, list_: str
) -> None:
	names = []
	for n in list_.split(","):
		names.append(n.strip(" «»"))
	event(bench, empty_database, tmp_path, name, "special", hour(f"2026-10-14 {start}"), None, names)


@given(
	parsers.re(
		r"un blanc dans un sonore réglé à (?P<duration>[\d,]+) secondes? sous (?P<threshold>-[\d,]+) dB, qui"
		r" (?P<remainder>est"
		r" noté seulement|fait passer au secours)"
	)
)
def rule_dead_air(bench: Bench, duration: str, threshold: str, remainder: str) -> None:
	"""La section [dead_air] de la configuration (https://github.com/dascritch/machincast/issues/122)."""
	bench.dead_air = DeadAirSettings(
		timedelta(seconds=seconds(duration)), seconds(threshold), remainder == "fait passer au secours"
	)


@given("la socket d'état dans un répertoire temporaire")
def temporary_socket(bench: Bench, tmp_path: Path) -> None:
	bench.state = StateSocket(tmp_path / "run" / "machincast" / "lecture.sock")


@when("l'interface demande à Machin player de relire la grille")
def reread_grid(bench: Bench) -> None:
	"""Comme après une session sautée (https://github.com/dascritch/machincast/issues/273) ou un événement enregistré
	(https://github.com/dascritch/machincast/issues/266) : la demande est envoyée, puis la socket attend qu'elle
	arrive."""
	state = bench.state
	assert state is not None
	with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
		client.connect(str(state.path))
		client.sendall(request_reread_grid().encode())
		client.settimeout(5.0)
		client.recv(1)
		limit = time.monotonic() + 5.0
		while (state._requests.empty()) and (time.monotonic() < limit):
			time.sleep(0.01)
	assert not state._requests.empty()


@given(parsers.parse("chaque sonore dure {duration:d} secondes"))
def sound_duration(empty_database: Connection, duration: int) -> None:
	"""Chaque fichier : un stream n'a pas de durée."""
	empty_database.execute("UPDATE sounds SET duration = %s WHERE type = 'file'", (timedelta(seconds=duration),))


@given(
	parsers.re(
		r"la séquence « (?P<name>[^»]+) » des sonores « (?P<first>[^»]+) », « (?P<second>[^»]+) », jouée par le fil"
		r" musical permanent « (?P<feed>[^»]+) », avant le sonore « (?P<after>[^»]+) »"
	)
)
def feed_sequence(
	bench: Bench, empty_database: Connection, tmp_path: Path, name: str, first: str, second: str, feed: str, after: str
) -> None:
	sequence = empty_database.execute(
		"INSERT INTO sequences (internal_name) VALUES (%s) RETURNING id", (name,)
	).fetchone()
	event = empty_database.execute(
		"INSERT INTO events (internal_name, priority) VALUES (%s, 'background_programming') RETURNING id", (feed,)
	).fetchone()
	assert (sequence is not None) and (event is not None)
	for position, sound_name in enumerate((first, second), start=1):
		empty_database.execute(
			"INSERT INTO sequence_items (sequence_id, position, sound_id) VALUES (%s, %s, %s)",
			(sequence[0], position, create_sound(bench, empty_database, tmp_path, sound_name)),
		)
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, sequence_id) VALUES (%s, 1, %s)",
		(event[0], sequence[0]),
	)
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, sound_id) VALUES (%s, 2, %s)",
		(event[0], create_sound(bench, empty_database, tmp_path, after)),
	)


@given(parsers.re(r"le fil musical permanent « (?P<feed>[^»]+) » joue les séquences (?P<list_>.+)"))
def sequence_feed(bench: Bench, empty_database: Connection, tmp_path: Path, feed: str, list_: str) -> None:
	"""« A » des sonores « a1 », « a2 », puis « B » des sonores « b1 » : chaque séquence est un élément du fil."""
	created_event = empty_database.execute(
		"INSERT INTO events (internal_name, priority) VALUES (%s, 'background_programming') RETURNING id", (feed,)
	).fetchone()
	assert created_event is not None
	for rank, part in enumerate(list_.split(", puis "), start=1):
		name, sounds = part.split(" des sonores ")
		sequence = empty_database.execute(
			"INSERT INTO sequences (internal_name) VALUES (%s) RETURNING id", (name.strip(" «»"),)
		).fetchone()
		assert sequence is not None
		n_list = []
		for n in sounds.split(","):
			n_list.append(n.strip(" «»"))
		for position, sound_name in enumerate(n_list, start=1):
			empty_database.execute(
				"INSERT INTO sequence_items (sequence_id, position, sound_id) VALUES (%s, %s, %s)",
				(sequence[0], position, create_sound(bench, empty_database, tmp_path, sound_name)),
			)
		empty_database.execute(
			"INSERT INTO event_items (event_id, position, sequence_id) VALUES (%s, %s, %s)",
			(created_event[0], rank, sequence[0]),
		)


@given(
	parsers.re(
		r"le fil musical permanent « (?P<feed>[^»]+) » joue la séquence « (?P<sequence>[^»]+) » des sonores"
		r" (?P<of_the_sequence>.+), puis la banque aléatoire « (?P<bank>[^»]+) » des sonores (?P<of_the_bank>.+)"
	)
)
def sequence_feed_then_bank(
	bench: Bench,
	empty_database: Connection,
	tmp_path: Path,
	feed: str,
	sequence: str,
	of_the_sequence: str,
	bank: str,
	of_the_bank: str,
) -> None:
	sequence_feed(bench, empty_database, tmp_path, feed, f"« {sequence} » des sonores {of_the_sequence}")
	created = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'random') RETURNING id", (bank,)
	).fetchone()
	assert created is not None
	n_list = []
	for n in of_the_bank.split(","):
		n_list.append(n.strip(" «»"))
	for position, sound_name in enumerate(n_list, start=1):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
			(created[0], create_sound(bench, empty_database, tmp_path, sound_name), position),
		)
	empty_database.execute(
		"INSERT INTO event_items (event_id, position, bank_id) SELECT id, 2, %s FROM events WHERE internal_name = %s",
		(created[0], feed),
	)


@given(
	parsers.re(
		r"le spécial « (?P<name>[^»]+) » à partir de (?P<start>[\d:]+), sans fin,"
		r" avec le sonore « (?P<sound_name>[^»]+) »"
	)
)
def special_without_end(
	bench: Bench, empty_database: Connection, tmp_path: Path, name: str, start: str, sound_name: str
) -> None:
	event(bench, empty_database, tmp_path, name, "special", hour(f"2026-10-14 {start}"), None, [sound_name])


@given(parsers.parse("l'événement « {name} » a pour nom public « {public_name} », et masque ses sonores"))
def hidden_event(empty_database: Connection, name: str, public_name: str) -> None:
	empty_database.execute(
		"UPDATE events SET public_name = %s, hide_metadata = true WHERE internal_name = %s", (public_name, name)
	)


@given(parsers.parse("chaque sonore a {duration} seconde de crossfade de début et de fin"))
def crossfades(empty_database: Connection, duration: str) -> None:
	value = timedelta(seconds=seconds(duration))
	empty_database.execute("UPDATE sounds SET crossfade_start = %s, crossfade_end = %s", (value, value))


@given(parsers.re(r"les crossfades de chaque sonore sont (?:de (?P<duration>[\d,]+) seconde|non paramétrés)"))
def sound_crossfades(empty_database: Connection, duration: str | None) -> None:
	"""Non paramétrés : NULL ; 0 seconde est un crossfade paramétré (https://github.com/dascritch/machincast/issues/145)."""
	value = None
	if duration is not None:
		value = timedelta(seconds=seconds(duration))
	empty_database.execute("UPDATE sounds SET crossfade_start = %s, crossfade_end = %s", (value, value))


@given(
	parsers.re(
		r"les crossfades par défaut de la configuration sont (?:absents|de (?P<start>[\d,]+) seconde au début"
		r"(?: et de (?P<end>[\d,]+) à la fin|, et absent à la fin)"
		r"|absent au début, et de (?P<only_end>[\d,]+) à la fin)"
	)
)
def default_crossfades(bench: Bench, start: str | None, end: str | None, only_end: str | None) -> None:
	durations: list[timedelta | None] = []
	for value in (start, (end) or (only_end)):
		duration = None
		if value is not None:
			duration = timedelta(seconds=seconds(value))
		durations.append(duration)
	bench.crossfades = Crossfades(start=durations[0], end=durations[1])


CROSSFADE_RULES = {
	"laisse ses sonores décider, malgré": "sound",
	"applique à défaut": "default",
	"impose": "forced",
}
"""La règle de crossfade d'une banque, telle que la disent les scénarios (https://github.com/dascritch/machincast/issues/143)."""


@given(
	parsers.re(
		r"la banque « (?P<name>[^»]+) » (?P<rule>laisse ses sonores décider, malgré|applique à défaut|impose)"
		r" (?P<duration>[\d,]+) seconde de crossfade de (?P<side>début|fin)"
	)
)
def bank_crossfade(empty_database: Connection, name: str, rule: str, duration: str, side: str) -> None:
	column = {"début": "crossfade_start", "fin": "crossfade_end"}[side]
	empty_database.execute(
		f"UPDATE banks SET {column}_rule = %s, {column} = %s WHERE internal_name = %s",  # noqa: S608
		(CROSSFADE_RULES[rule], timedelta(seconds=seconds(duration)), name),
	)


@given(parsers.re(r"la banque « (?P<name>[^»]+) », séquentielle, avec les sonores (?P<list_>.+)"))
def sound_bank(empty_database: Connection, name: str, list_: str) -> None:
	"""Une banque des sonores déjà en base, sans qu'un événement l'appelle."""
	created = empty_database.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (name,)
	).fetchone()
	assert created is not None
	n_list = []
	for n in list_.split(","):
		n_list.append(n.strip(" «»"))
	for position, sound_name in enumerate(n_list, start=1):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
			(created[0], sound(empty_database, sound_name), position),
		)


@given(parsers.parse("chaque sonore a {duration} seconde de crossfade de fin, et aucun de début"))
def end_crossfade(empty_database: Connection, duration: str) -> None:
	empty_database.execute("UPDATE sounds SET crossfade_end = %s", (timedelta(seconds=seconds(duration)),))


# ─── Détection de silence (https://github.com/dascritch/machincast/issues/146) ───


@given(
	parsers.re(
		r"chaque sonore a (?:aucun silence détecté|(?P<start>[\d,]+) secondes? de silence détecté au début"
		r"(?:, et aucun à la fin| et (?P<end>[\d,]+) à la fin))"
	)
)
def detected_silences(empty_database: Connection, start: str | None, end: str | None) -> None:
	"""La fin détectée se compte depuis la fin du fichier ; aucun silence détecté : NULL."""
	durations: list[timedelta | None] = []
	for value in (start, end):
		duration = None
		if value is not None:
			duration = timedelta(seconds=seconds(value))
		durations.append(duration)
	empty_database.execute(
		"UPDATE sounds SET detected_start = %s, detected_end = %s WHERE type = 'file'", (durations[0], durations[1])
	)


@given(parsers.parse("la banque « {name} » active la détection de silence"))
def detected_silence_bank(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE banks SET silence_detection = true WHERE internal_name = %s", (name,))


@given(parsers.re(r"le sonore « (?P<name>[^»]+) » active la détection de silence$"))
def detected_silence_sound(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE sounds SET silence_detection = true WHERE id = %s", (sound(empty_database, name),))


@given(
	parsers.re(
		r"le sonore « (?P<name>[^»]+) » active la détection de silence, avec (?P<start>[\d,]+) secondes? de silence"
		r" détecté au début et (?P<end>[\d,]+) à la fin"
	)
)
def trimmed_sound(empty_database: Connection, name: str, start: str, end: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET silence_detection = true, detected_start = %s, detected_end = %s WHERE id = %s",
		(timedelta(seconds=seconds(start)), timedelta(seconds=seconds(end)), sound(empty_database, name)),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"la diffusion démarre (?P<rhythm>au plus vite|en temps réel)"))
def start(bench: Bench, empty_database: Connection, rhythm: str) -> None:
	bench.connection = open_connection(*sample_database_parameters(), Role.PLAYBACK)
	bench.engine = RecordingEngine(
		configuration_test().audio, real_time=rhythm == "en temps réel", dead_air=bench.dead_air
	)
	bench.broadcast = Broadcast(
		bench.connection,
		bench.engine,
		clock(bench),
		create_randomness(0),
		reconnection_delay=TEST_RECONNECTION_DELAY,
		outputs=bench.outputs,
		state=bench.state,
		# À chaque pas, pour que la socket d'état donne la progression du moment.
		minimal_publication=0.0,
		crossfades=bench.crossfades,
		analyser=bench.analyser,
		dead_air=bench.dead_air,
	)
	bench.broadcast.start()


@given(parsers.parse("le sonore « {name} » dure {duration:d} secondes en base"))
def duration_in_database(empty_database: Connection, name: str, duration: int) -> None:
	"""La durée en base décide des heures annoncées, et de la fin d'un sonore sur le moteur simulé ; le fichier joué
	reste le court fichier de test."""
	empty_database.execute(
		"UPDATE sounds SET duration = %s WHERE id = %s", (timedelta(seconds=duration), sound(empty_database, name))
	)


@when("la diffusion démarre sur un moteur simulé")
def start_on_simulated_engine(bench: Bench, empty_database: Connection) -> None:
	"""Le moteur simulé suit l'horloge du binaire : un sonore d'une minute se joue sans attendre."""
	bench.connection = open_connection(*sample_database_parameters(), Role.PLAYBACK)
	bench.simulated = RecordingSimulatedEngine(clock(bench))
	bench.broadcast = Broadcast(
		bench.connection,
		bench.simulated,
		clock(bench),
		create_randomness(0),
		state=bench.state,
		crossfades=bench.crossfades,
		dead_air=bench.dead_air,
		outputs=bench.outputs,
	)
	bench.broadcast.start()


@when(parsers.re(r"la diffusion avance de (?P<count>\d+) secondes?"))
def advance(bench: Bench, count: str) -> None:
	"""Un pas par seconde, sur le moteur simulé."""
	for _ in range(int(count)):
		broadcast(bench).step()
		clock(bench).advance(timedelta(seconds=1))


@when(parsers.re(r"je (?P<what>saute au sonore suivant|saute après la séquence|coupe l'événement par le fil musical)$"))
def interrupt(bench: Bench, what: str) -> None:
	broadcast(bench).interrupt(ITEMS[what])


@when(parsers.parse("je coupe l'antenne par le secours « {name} »"))
def cut_by_fallback(bench: Bench, empty_database: Connection, name: str) -> None:
	"""https://github.com/dascritch/machincast/issues/323 ; un secours absent a l'identifiant 0, qu'aucun n'a."""
	line = empty_database.execute("SELECT id FROM events WHERE internal_name = %s", (name,)).fetchone()
	if line is None:
		chosen = 0
	else:
		chosen = int(str(line[0]))
	broadcast(bench).cut_by_fallback(chosen)


@when(parsers.parse("je coupe l'antenne par le feed « {name} »"))
def cut_by_feed(bench: Bench, empty_database: Connection, name: str) -> None:
	line = empty_database.execute("SELECT id FROM feeds WHERE name = %s", (name,)).fetchone()
	if line is None:
		chosen = 0
	else:
		chosen = int(str(line[0]))
	broadcast(bench).cut_by_feed(chosen)


@given(parsers.parse("le stream « {name} » sur le feed « {feed} », à une adresse factice"))
def dummy_stream_on_feed(empty_database: Connection, name: str, feed: str) -> None:
	"""Comme un stream à une adresse factice, mais l'adresse est celle du feed (https://github.com/dascritch/machincast/issues/323)."""
	created = empty_database.execute(
		"INSERT INTO feeds (name, url) VALUES (%s, %s) RETURNING id", (feed, f"http://flux.invalid/{name}")
	).fetchone()
	assert created is not None
	empty_database.execute("INSERT INTO sounds (type, feed_id, title) VALUES ('stream', %s, %s)", (created[0], name))


@then(parsers.parse("le passage « {name} » est au nom de l'événement « {event} », sans élément de liste"))
def play_outside_list(empty_database: Connection, name: str, event: str) -> None:
	line = empty_database.execute(
		"SELECT e.internal_name, a.event_item_id FROM airplay a JOIN events e ON e.id = a.event_id"
		" WHERE a.line_type = 'start' AND a.title = %s ORDER BY a.id LIMIT 1",
		(name,),
	).fetchone()
	assert line == (event, None), line


@when(parsers.re(r"la diffusion tourne (?P<count>\d+) pas d(?:'une|e (?P<duration>[\d,]+)) seconde"))
def run(bench: Bench, count: str, duration: str | None) -> None:
	gap = 1.0
	if duration is not None:
		gap = seconds(duration)
	real_rhythm = (bench.engine is not None) and (bench.engine.real_time)
	for _ in range(int(count)):
		broadcast(bench).step()
		# En temps réel, la pause suit l'horloge ; au plus vite, la voie finit pendant une courte pause réelle.
		if real_rhythm:
			time.sleep(gap)
		else:
			wait_track_end(bench)
		clock(bench).advance(timedelta(seconds=gap))


def wait_track_end(bench: Bench, delay: float = 5.0) -> None:
	assert bench.engine is not None
	limit = time.monotonic() + delay
	while (any(v.state == "playing" for v in bench.engine.ongoing_tracks())) and (time.monotonic() < limit):
		time.sleep(REAL_STEP / 5)
		for track in bench.engine.ongoing_tracks():
			track.handle()


@when(parsers.re(r"la diffusion tourne pendant (?P<duration>[\d,]+) secondes? en temps réel"))
def run_in_real_time(bench: Bench, duration: str) -> None:
	end = time.monotonic() + seconds(duration)
	previous = time.monotonic()
	while time.monotonic() < end:
		broadcast(bench).step()
		time.sleep(REAL_STEP)
		now = time.monotonic()
		clock(bench).advance(timedelta(seconds=now - previous))
		previous = now


@when(parsers.parse("l'horloge du binaire passe au « {instant} »"))
def clock_passes(bench: Bench, instant: str) -> None:
	clock(bench).advance(hour(instant) - clock(bench).now())


@when(parsers.parse("le sonore « {name} » redevient actif"))
def becomes_again_active(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE sounds SET state = 'active' WHERE id = %s", (sound(empty_database, name),))


@when("la diffusion s'arrête")
def halt(bench: Bench) -> None:
	broadcast(bench).halt()


# ─── Alors ─────────────────────────────────────────────────


def plays(database: Connection) -> list[tuple[str, datetime, datetime | None, bool | None]]:
	lines = database.execute(
		"SELECT d.title, d.logged_at, f.logged_at, f.without_incident FROM airplay d"
		" LEFT JOIN airplay f ON f.play_id = d.play_id AND f.line_type = 'end'"
		" WHERE d.line_type = 'start' ORDER BY d.logged_at, d.id"
	).fetchall()
	plays = []
	for t, d, f, s in lines:
		plays.append((str(t), d, f, s))
	return plays  # type: ignore[misc]


def play(database: Connection, name: str) -> tuple[str, datetime, datetime | None, bool | None]:
	p_list = []
	for p in plays(database):
		if p[0] == name:
			p_list.append(p)
	return p_list[0]


def log(database: Connection) -> list[tuple[str, str]]:
	log = []
	for n, t in database.execute("SELECT level::text, kind FROM log ORDER BY id").fetchall():
		log.append((str(n), shown(t)))
	return log


@then(parsers.re(r"l'airplay montre les passages (?P<list_>.+)"))
def airplay(empty_database: Connection, list_: str) -> None:
	p_list = []
	for p in plays(empty_database):
		p_list.append(p[0])
	n_list = []
	for n in list_.split(","):
		n_list.append(n.strip(" «»"))
	assert p_list == n_list, plays(empty_database)


def title(database: Connection, sound: int) -> str:
	line = database.execute("SELECT title FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert line is not None
	return str(line[0])


def announcements(bench: Bench, database: Connection) -> list[str]:
	announcements = []
	for planned in broadcast(bench).upcoming:
		announcements.append(title(database, planned.choice.sound))
	return announcements


def list_(text: str) -> list[str]:
	name_list = []
	for name in text.split(","):
		name_list.append(name.strip(" «»"))
	return name_list


@then(parsers.parse("le prochain sonore réservé est « {name} »"))
def next_reserved(bench: Bench, empty_database: Connection, name: str) -> None:
	reserve = broadcast(bench).reserve
	assert reserve is not None
	assert title(empty_database, reserve.choice.sound) == name


@then(parsers.re(r"les sonores à venir sont (?P<names>.+)"))
def upcoming(bench: Bench, empty_database: Connection, names: str) -> None:
	assert announcements(bench, empty_database) == list_(names)


@pytest.fixture
def notes() -> list[str]:
	"""Les sonores annoncés, notés par le scénario."""
	return []


@when("je note les sonores annoncés")
def note(bench: Bench, empty_database: Connection, notes: list[str]) -> None:
	reserve = broadcast(bench).reserve
	assert reserve is not None
	notes.extend([title(empty_database, reserve.choice.sound), *announcements(bench, empty_database)])


@then(parsers.parse("le passage n°{play:d} est le sonore noté n°{rank:d}"))
def noted_play(empty_database: Connection, notes: list[str], play: int, rank: int) -> None:
	played_list = []
	for p in plays(empty_database):
		played_list.append(p[0])
	assert played_list[play - 1] == notes[rank - 1], (played_list, notes)


@then(parsers.parse("le prochain sonore et les sonores à venir reprennent les sonores notés à partir du n°{rank:d}"))
def noted_remainder(bench: Bench, empty_database: Connection, notes: list[str], rank: int) -> None:
	reserve = broadcast(bench).reserve
	assert reserve is not None
	announcements_ = [title(empty_database, reserve.choice.sound), *announcements(bench, empty_database)]
	assert announcements_[: len(notes) - rank + 1] == notes[rank - 1 :], (announcements_, notes)


def end_hour(end: datetime | None) -> str:
	if end is None:
		return ""
	return f"{end.astimezone():%H:%M:%S}"


@then("l'airplay montre :")
def detailed_airplay(empty_database: Connection, datatable: list[list[str]]) -> None:
	_, *lines = datatable
	obtained_list = [
		[title, f"{start.astimezone():%H:%M:%S}", end_hour(end), "oui" if without_incident else "non"]
		for title, start, end, without_incident in plays(empty_database)
	]
	line_list = []
	for line in lines:
		value_list = []
		for value in line:
			value_list.append(value.strip())
		line_list.append(value_list)
	assert obtained_list == line_list, obtained_list


@then(
	parsers.re(
		r"le sonore « (?P<name>[^»]+) » a démarré (?:avec une montée de (?P<duration>[\d,]+) secondes|sans montée)"
	)
)
def rise(bench: Bench, name: str, duration: str | None) -> None:
	assert bench.simulated is not None
	expected = timedelta(0)
	if duration is not None:
		expected = timedelta(seconds=seconds(duration))
	assert bench.simulated.rises[name] == expected, bench.simulated.rises


@then("chaque passage a sa ligne de fin, sans incident")
def end_lines(empty_database: Connection) -> None:
	lines = plays(empty_database)
	assert (lines) and (all((end is not None) and (without_incident) for _, _, end, without_incident in lines)), lines


@then(parsers.parse("le log finit par « {level} » « {kind} »"))
def log_end(empty_database: Connection, level: str, kind: str) -> None:
	assert log(empty_database)[-1] == (level, kind)


LEVEL_IN_DATABASE = {label: level for level, label in LEVELS.items()}
"""Le niveau du log en base, par le mot des scénarios."""


@then(parsers.re(r"le log contient (?P<count>\d+) (?P<level>info|alerte|incident) « (?P<kind>[^»]+) »"))
def log_lines(empty_database: Connection, count: str, level: str, kind: str) -> None:
	assert log(empty_database).count((LEVEL_IN_DATABASE[level], kind)) == int(count), log(empty_database)


ON_AIR_KINDS = ("début d'événement", "fin d'événement", "début de séquence", "fin de séquence")
"""Ce que le log note des événements et des séquences à l'antenne (https://github.com/dascritch/machincast/issues/153)."""


@then("le log note pour les événements et les séquences :")
def on_air_log(empty_database: Connection, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	kind_list = []
	for kind in ON_AIR_KINDS:
		kind_list.append(stored(kind))
	fetched_list = empty_database.execute(
		"SELECT l.logged_at, l.level::text, l.kind, l.message, e.internal_name FROM log l"
		" LEFT JOIN events e ON e.id = l.event_id WHERE l.kind = ANY(%s) ORDER BY l.id",
		(kind_list,),
	).fetchall()
	e_list = []
	for t, n, k, m, e in fetched_list:
		e_list.append((t, n, shown(k), shown(m), e))
	fetched_list = e_list
	expected_list = [
		(hour(timestamp.strip()), "info", kind.strip(), message.strip(), event.strip())
		for timestamp, kind, message, event in rows
	]
	assert fetched_list == expected_list, fetched_list


@then(parsers.parse("le passage « {name} » a été coupé net au « {instant} »"))
def cuts_clean(empty_database: Connection, name: str, instant: str) -> None:
	assert play(empty_database, name)[2] == hour(instant)


@then(
	parsers.re(
		r"le passage « (?P<following>[^»]+) » a commencé (?P<moment>avant|après) la fin du passage « (?P<name>[^»]+) »"
	)
)
def overlap(empty_database: Connection, following: str, moment: str, name: str) -> None:
	end = play(empty_database, name)[2]
	start = play(empty_database, following)[1]
	assert end is not None
	if moment == "avant":
		chosen = start < end
	else:
		chosen = start >= end
	assert chosen, (start, end)


@given(parsers.re(r"le sonore « (?P<name>[^»]+) » a (?P<duration>[\d,]+) seconde de crossfade de (?P<side>début|fin)"))
def sound_crossfade(empty_database: Connection, name: str, duration: str, side: str) -> None:
	column = "crossfade_end"
	if side == "début":
		column = "crossfade_start"
	empty_database.execute(
		f"UPDATE sounds SET {column} = %s WHERE id = %s",
		(timedelta(seconds=seconds(duration)), sound(empty_database, name)),
	)


@given(parsers.re(r"l'événement de secours « (?P<name>[^»]+) », avec les sonores (?P<list_>.+)"))
def fallback_event(bench: Bench, empty_database: Connection, tmp_path: Path, name: str, list_: str) -> None:
	n_list = []
	for n in list_.split(","):
		n_list.append(n.strip(" «»"))
	event(bench, empty_database, tmp_path, name, "fallback", None, None, n_list)


@given(parsers.parse("le fichier du sonore « {name} » a été supprimé"))
def deleted_file(bench: Bench, name: str) -> None:
	bench.files[name].unlink()


@given(parsers.parse("le sonore « {name} » est à l'état « {state} »"))
def state(empty_database: Connection, name: str, state: str) -> None:
	empty_database.execute("UPDATE sounds SET state = %s WHERE id = %s", (state, sound(empty_database, name)))


@given(parsers.parse("le fil musical « {name} » est supprimé"))
def deleted_feed(empty_database: Connection, name: str) -> None:
	empty_database.execute("DELETE FROM events WHERE internal_name = %s", (name,))


def sounds_of(database: Connection, event: str) -> set[str]:
	lines = database.execute(
		"SELECT s.title FROM events e JOIN event_items ee ON ee.event_id = e.id"
		" JOIN sounds s ON s.id = ee.sound_id WHERE e.internal_name = %s",
		(event,),
	).fetchall()
	sounds_of = set()
	for line in lines:
		sounds_of.add(str(line[0]))
	return sounds_of


@then("l'airplay ne montre aucun passage")
def no_play(empty_database: Connection) -> None:
	assert plays(empty_database) == []


# ─── Streams (https://github.com/dascritch/machincast/issues/16) ───


@pytest.fixture
def server() -> Iterator[StreamServer]:
	server = StreamServer()
	yield server
	server.shut_down()


@given(parsers.parse("un serveur de flux local, avec le flux « {stream} » en ligne"))
def stream_in_line(server: StreamServer, stream: str) -> None:
	server.in_line[stream] = True


@given(parsers.parse("le stream « {name} » à l'adresse du flux « {stream} »"))
def live_stream(server: StreamServer, empty_database: Connection, name: str, stream: str) -> None:
	empty_database.execute(
		"INSERT INTO sounds (type, stream_url, title) VALUES ('stream', %s, %s)", (server.address(stream), name)
	)


@then(parsers.parse("le passage « {name} » a duré {duration} seconde, à {margin} seconde près"))
def play_duration(empty_database: Connection, name: str, duration: str, margin: str) -> None:
	"""Du début à la fin du passage, à l'heure du binaire (https://github.com/dascritch/machincast/issues/146)."""
	found_list = [(start, end) for title, start, end, _ in plays(empty_database) if title == name]
	assert found_list, f"aucun passage de {name}"
	start, end = found_list[0]
	assert end is not None, f"passage de {name} sans fin"
	assert abs((end - start).total_seconds() - seconds(duration)) <= seconds(margin), end - start


@then(parsers.parse("la voie de « {name} » a joué son fichier de {start} à {end} seconde, à {margin} seconde près"))
def played_track(bench: Bench, name: str, start: str, end: str, margin: str) -> None:
	assert bench.engine is not None
	track = bench.engine.played_list[str(bench.files[name])]
	assert track.final_position is not None, track.state
	gap = seconds(margin)
	assert abs(track.offset.total_seconds() - seconds(start)) <= gap, track.offset
	assert abs((track.offset + track.final_position).total_seconds() - seconds(end)) <= gap, track.final_position


@given(parsers.parse("le stream « {name} » est secouru par « {fallback} »"))
def rescued_stream(empty_database: Connection, name: str, fallback: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET fallback_event_id = (SELECT id FROM events WHERE internal_name = %s) WHERE id = %s",
		(fallback, sound(empty_database, name)),
	)


@given(parsers.parse("le stream « {name} » à une adresse factice"))
def dummy_stream(empty_database: Connection, name: str) -> None:
	"""Le moteur simulé ne se connecte à rien ; l'adresse finit par le nom du stream."""
	empty_database.execute(
		"INSERT INTO sounds (type, stream_url, title) VALUES ('stream', %s, %s)", (f"http://flux.invalid/{name}", name)
	)


@then(parsers.parse("le passage « {name} » a fini en incident « {kind} » au « {instant} »"))
def finished_in_incident(empty_database: Connection, name: str, kind: str, instant: str) -> None:
	found_list = [(end, healthy) for title, _start, end, healthy in plays(empty_database) if title == name]
	assert found_list, name
	end, healthy = found_list[0]
	assert (isinstance(end, datetime)) and (end == hour(instant)) and (healthy is False), found_list
	line = empty_database.execute(
		"SELECT message FROM log WHERE level = 'incident' AND kind = %s AND logged_at = %s", (stored(kind), end)
	).fetchone()
	assert line is not None, kind


@then(
	parsers.re(
		r"le passage « (?P<name>[^»]+) », de l'événement « (?P<event>[^»]+) », est au nom (?:de « (?P<lender>[^»]+) »|d'aucun"
		r" autre)"
	)
)
def lent_play(empty_database: Connection, name: str, event: str, lender: str | None) -> None:
	"""https://github.com/dascritch/machincast/issues/399 : l'événement du passage, et celui qui lui prête son nom."""
	lines = empty_database.execute(
		"SELECT e.internal_name, l.internal_name FROM airplay a JOIN events e ON e.id = a.event_id"
		" LEFT JOIN events l ON l.id = a.lender_event_id WHERE a.line_type = 'start' AND a.sound_id = %s"
		" ORDER BY a.logged_at DESC, a.id DESC LIMIT 1",
		(sound(empty_database, name),),
	).fetchall()
	assert lines == [(event, lender)], lines
