"""Scénarios d'un blanc dans un sonore à l'antenne (https://github.com/dascritch/machincast/issues/122).

Les premiers jouent de vrais fichiers, faits de morceaux de sinusoïde à un niveau crête donné (tests.sounds
.generate_silences), sur la sortie factice, au plus vite. Les suivants tournent sur le moteur simulé : la voie du sonore
nommé imite un blanc, constaté une fois la durée d'un blanc écoulée, comme la voie GStreamer
(machincast.player.engine.Track.dead_air). Les étapes partagées de la diffusion sont dans tests/broadcast_steps.py.
"""

import contextlib
import dataclasses
import re
import time
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.clock import FixedClock
from machincast.configuration import Configuration, DeadAirSettings
from machincast.i18n import decimal
from machincast.player import __main__ as playback_module
from machincast.player import broadcast
from machincast.player.engine import DeadAir, PlaybackTrack, Track
from machincast.player.simulation import SimulatedEngine, SimulatedTrack
from tests.broadcast_steps import Bench, hour, plays, seconds, sound
from tests.database_fixtures import configuration_test
from tests.log_texts import shown, stored
from tests.sounds import generate_silences

scenarios("dead_air_in_sound.feature")

Connection = psycopg.Connection[tuple[object, ...]]
FREQUENCY = 8000
"""Fréquence d'échantillonnage des fichiers des scénarios : basse, pour qu'ils s'écrivent vite."""
MAXIMAL_WAITING = 10.0
POSITION_MARGIN = 0.15
"""Secondes d'écart admises sur la position d'un blanc : une mesure du niveau dure 0,1 seconde."""
LEVEL_MARGIN = 1.0
"""dB d'écart admis sur un niveau moyen : la sinusoïde à -80 dB n'a que quelques pas de quantification."""


@pytest.fixture
def files() -> dict[str, Path]:
	return {}


@pytest.fixture
def playback() -> dict[str, object]:
	"""La voie jouée par le scénario, et les blancs qu'elle a présentés."""
	return {}


def amplitude(level: str) -> float:
	"""Amplitude crête d'un niveau en dB ; 0 pour un silence numérique."""
	if level == "silence numérique":
		return 0.0
	return float(10 ** (seconds(level) / 20))


@given(parsers.re(r"le fichier « (?P<name>[^»]+) » : (?P<pieces>.+)"))
def file_by_pieces(tmp_path: Path, files: dict[str, Path], name: str, pieces: str) -> None:
	"""« 1 seconde à -20 dB, 3 secondes de silence numérique, puis 1 seconde à -20 dB »."""
	found_list = re.findall(r"([\d,]+) secondes? (?:à (-[\d,]+) dB|de (silence numérique))", pieces)
	assert found_list, pieces
	plan = tuple((seconds(duration), amplitude((level) or (silence))) for duration, level, silence in found_list)
	files[name] = generate_silences(tmp_path / f"{name}.flac", plan, FREQUENCY)


@when(
	parsers.re(
		r"une (?P<variety>voie|voie muette) joue le fichier « (?P<name>[^»]+) »(?: à partir de (?P<offset>[\d,]+)"
		r" seconde du fichier,)? jusqu'au bout, au plus vite"
	)
)
def play(
	bench: Bench, files: dict[str, Path], playback: dict[str, object], variety: str, name: str, offset: str | None
) -> None:
	departure = None
	if offset is not None:
		departure = timedelta(seconds=seconds(offset))
	track = Track(
		files[name],
		configuration_test().audio,
		None,
		real_time=False,
		silent=variety == "voie muette",
		offset=departure,
		dead_air=bench.dead_air,
	)
	dead_airs: list[DeadAir] = []
	try:
		track.start()
		limit = time.monotonic() + MAXIMAL_WAITING
		while (track.state == "playing") and (time.monotonic() < limit):
			time.sleep(0.01)
			track.handle()
			while (dead_air := track.dead_air()) is not None:
				dead_airs.append(dead_air)
		while (dead_air := track.dead_air()) is not None:
			dead_airs.append(dead_air)
	finally:
		track.shut_down()
	assert track.state == "finished", (track.state, track.error)
	playback["voie"], playback["blancs"] = track, dead_airs


def dead_airs_of(playback: dict[str, object]) -> list[DeadAir]:
	dead_airs = playback["blancs"]
	assert isinstance(dead_airs, list)
	return dead_airs


@then(parsers.re(r"la voie a présenté (?P<count>\d+) blancs?$"))
def present_dead_airs(playback: dict[str, object], count: str) -> None:
	assert len(dead_airs_of(playback)) == int(count), dead_airs_of(playback)


@then(
	parsers.re(
		r"le blanc n°(?P<rank>\d+) commence à (?P<position>[\d,]+) secondes? du fichier, (?:au niveau moyen de"
		r" (?P<level>-[\d,]+) dB|en (?P<silence>silence numérique))"
	)
)
def n_dead_air(playback: dict[str, object], rank: str, position: str, level: str | None, silence: str | None) -> None:
	dead_air = dead_airs_of(playback)[int(rank) - 1]
	assert abs(dead_air.position.total_seconds() - seconds(position)) <= POSITION_MARGIN, dead_air
	if silence is not None:
		assert dead_air.level is None, dead_air
	else:
		assert (dead_air.level is not None) and (abs(dead_air.level - seconds(str(level))) <= LEVEL_MARGIN), dead_air


@then(parsers.re(r"la voie (?P<what>a été entendue|n'est plus entendue)"))
def heard(playback: dict[str, object], what: str) -> None:
	track = playback["voie"]
	assert isinstance(track, Track)
	assert track.heard() is (what == "a été entendue")


# ─── Diffusion, sur le moteur simulé ───────────────────────


class DeadAirTrack(SimulatedTrack):
	"""Une voie simulée qui présente un blanc à une position donnée, constaté une fois la durée d'un blanc écoulée ;
	son son revient à retour, s'il est donné."""

	def __init__(
		self,
		clock: FixedClock,
		duration: timedelta | None,
		dead_air: DeadAir,
		return_: timedelta | None,
	) -> None:
		super().__init__(clock, duration)
		self._dead_air: DeadAir | None = dead_air
		self._start = dead_air.position
		self._return = return_

	def dead_air(self) -> DeadAir | None:
		dead_air = self._dead_air
		if (dead_air is None) or (self.position() < dead_air.position + dead_air.duration):
			return None
		self._dead_air = None
		return dead_air

	def heard(self) -> bool:
		"""Pas de son du début du blanc au retour du son."""
		position = self.position()
		return not ((self._start <= position) and ((self._return is None) or (position < self._return)))


@pytest.fixture
def openings() -> dict[str, int]:
	"""Les voies ouvertes par le moteur simulé, par sonore nommé."""
	return {}


@given(
	parsers.re(
		r"le sonore « (?P<name>[^»]+) » présente un blanc à (?P<position>\d+) secondes de son début, au niveau moyen de"
		r" (?P<level>-[\d,]+) dB(?:, et son son revient à (?P<return_>\d+) secondes)?"
	)
)
def sound_to_dead_air(
	monkeypatch: pytest.MonkeyPatch,
	bench: Bench,
	openings: dict[str, int],
	name: str,
	position: str,
	level: str,
	return_: str | None,
) -> None:
	"""Les fichiers des sonores sont dans un répertoire à leur nom (broadcast_steps.create_sound) ; l'adresse d'un
	stream factice finit par son nom. Seule la première voie du sonore présente le blanc."""
	true_play = SimulatedEngine.play
	dead_air_end = None
	if return_ is not None:
		dead_air_end = timedelta(seconds=int(return_))

	def play(
		self: SimulatedEngine, path: Path | str, duration: timedelta | None, *args: object, **options: object
	) -> PlaybackTrack:
		targeted = (Path(str(path)).parent.name == name) or (str(path).endswith(f"/{name}"))
		if not targeted:
			return true_play(self, path, duration, *args, **options)  # type: ignore[arg-type]
		openings[name] = openings.get(name, 0) + 1
		if openings[name] > 1:
			return true_play(self, path, duration, *args, **options)  # type: ignore[arg-type]
		assert isinstance(self.clock, FixedClock)
		dead_air = DeadAir(timedelta(seconds=int(position)), bench.dead_air.duration, seconds(level))
		track = DeadAirTrack(self.clock, duration, dead_air, dead_air_end)
		self._tracks.append(track)
		return track

	monkeypatch.setattr(SimulatedEngine, "play", play)


def log_lines(database: Connection, kind: str) -> list[tuple[str, object, object, object]]:
	lines = database.execute(
		"SELECT message, logged_at, sound_id, event_id FROM log WHERE kind = %s ORDER BY id", (stored(kind),)
	).fetchall()
	return [(shown(message), timestamp, id_sound, id_event) for message, timestamp, id_sound, id_event in lines]


@then(parsers.parse("l'incident « {kind} » dit « {text} »"))
def incident_says(empty_database: Connection, kind: str, text: str) -> None:
	lines = log_lines(empty_database, kind)
	assert (lines) and (all(text in message for message, *_ in lines)), lines


@then(parsers.parse("l'incident « {kind} » a été noté au « {instant} », pour le sonore « {name} » de « {event} »"))
def noted_incident(empty_database: Connection, kind: str, instant: str, name: str, event: str) -> None:
	line = empty_database.execute("SELECT id FROM events WHERE internal_name = %s", (event,)).fetchone()
	assert line is not None, event
	lines = [(timestamp, id_sound, id_event) for _, timestamp, id_sound, id_event in log_lines(empty_database, kind)]
	assert lines == [(hour(instant), sound(empty_database, name), line[0])], lines


@then(parsers.parse("le moteur n'a ouvert qu'une voie pour « {name} »"))
def a_only_track(openings: dict[str, int], name: str) -> None:
	assert openings.get(name) == 1, openings


@then(parsers.parse("le passage « {name} » a fini sans incident"))
def finished_without_incident(empty_database: Connection, name: str) -> None:
	found_list = [(end, healthy) for title, _start, end, healthy in plays(empty_database) if title == name]
	assert (found_list) and (all((end is not None) and (healthy is True) for end, healthy in found_list)), found_list


# ─── Machin player ────────────────────────────────────────


@pytest.fixture
def launching() -> dict[str, object]:
	"""La configuration de Machin player, et ce que son moteur et sa diffusion ont reçu."""
	return {}


@given(
	parsers.re(
		r"la configuration des tests, avec un blanc dans un sonore de (?P<duration>[\d,]+) secondes sous"
		r" (?P<threshold>-[\d,]+) dB, qui fait passer au secours"
	)
)
def configuration_with_dead_air(launching: dict[str, object], duration: str, threshold: str) -> None:
	dead_air = DeadAirSettings(timedelta(seconds=seconds(duration)), seconds(threshold), True)
	launching["configuration"] = dataclasses.replace(configuration_test(), dead_air=dead_air)


@when("Machin player diffuse avec cette configuration, sans base ni sortie audio")
def air(monkeypatch: pytest.MonkeyPatch, launching: dict[str, object]) -> None:
	"""La base de production n'est jamais jointe : la connexion est remplacée."""

	@contextlib.contextmanager
	def open_connection(*_arguments: object) -> Iterator[object]:
		yield object()

	class Engine:
		def __init__(self, _audio: object, **options: object) -> None:
			launching["moteur"] = options

		def shut_down(self) -> None:
			pass

	def broadcast(*_arguments: object, **options: object) -> object:
		launching["diffusion"] = options
		return object()

	monkeypatch.setattr(playback_module, "open_connection", open_connection)
	monkeypatch.setattr(playback_module, "AudioEngine", Engine)
	monkeypatch.setattr(playback_module, "Broadcast", broadcast)
	monkeypatch.setattr(playback_module, "air", lambda _broadcast, _stop: None)
	configuration = launching["configuration"]
	assert isinstance(configuration, Configuration)
	assert playback_module.run_broadcast(configuration) == 0


@then(
	parsers.re(
		r"son moteur mesure un blanc de (?P<duration>[\d,]+) secondes sous (?P<threshold>-[\d,]+) dB, et sa diffusion"
		r" fait"
		r" passer au secours"
	)
)
def taken_dead_air(launching: dict[str, object], duration: str, threshold: str) -> None:
	expected = DeadAirSettings(timedelta(seconds=seconds(duration)), seconds(threshold), True)
	engine, broadcast = launching["moteur"], launching["diffusion"]
	assert (isinstance(engine, dict)) and (isinstance(broadcast, dict)), launching
	assert (engine["dead_air"], broadcast["dead_air"]) == (expected, expected)


@then(parsers.parse("un blanc à {position} secondes s'écrit « {text} »"))
def timecode(position: str, text: str) -> None:
	# Gardée en anglais dans le log, la position s'affiche à la décimale du français (https://github.com/dascritch/machincast/issues/360).
	assert decimal(broadcast._timecode(timedelta(seconds=seconds(position)))) == text
