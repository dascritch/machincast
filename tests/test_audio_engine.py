"""Étapes du moteur audio GStreamer (https://github.com/dascritch/machincast/issues/15)."""

import dataclasses
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import gi
import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.database import Role, open_connection
from machincast.player.engine import AudioEngine, Track, entry_fade, sequencing
from machincast.player.files import check_before_playback
from tests.database_fixtures import configuration_test, sample_database_parameters
from tests.sounds import SOUND_FILES, sample_copy

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("audio_engine.feature")

Connection = psycopg.Connection[tuple[object, ...]]
MAXIMAL_WAITING = 10.0


@dataclass
class Context:
	engine: AudioEngine | None = None
	tracks: dict[str, Track] = field(default_factory=dict)
	track: Track | None = None
	sound: int | None = None
	file: Path | None = None
	result: Path | None = None
	startups: dict[str, float] = field(default_factory=dict)
	waiting_end: float | None = None
	time: float = 0.0
	"""L'horloge du moteur, en secondes, quand c'est celle du scénario (https://github.com/dascritch/machincast/issues/281)."""


@pytest.fixture
def context() -> Iterator[Context]:
	context = Context()
	yield context
	if context.engine is not None:
		context.engine.shut_down()
	for track in context.tracks.values():
		track.shut_down()


def seconds(text: str) -> timedelta:
	return timedelta(seconds=float(text.replace(",", ".")))


def engine(context: Context) -> AudioEngine:
	assert context.engine is not None
	return context.engine


# ─── Enveloppe et enchaînement ─────────────────────────────


@given(
	parsers.parse(
		"une voie pour un sonore de {duration} secondes, avec {start} secondes de crossfade de début et {end} de fin"
	)
)
def prepared_track(context: Context, duration: str, start: str, end: str) -> None:
	context.track = Track(
		SOUND_FILES / "sain.flac",
		configuration_test().audio,
		seconds(duration),
		seconds(start),
		seconds(end),
		real_time=False,
	)


@given(
	parsers.parse(
		"une voie pour un sonore de {duration} secondes, avec {start} seconde de fade-in depuis le volume {departure}"
		" et"
		" {end} de fade-out jusqu'au volume {arrival}"
	)
)
def overflowing_track(context: Context, duration: str, start: str, departure: str, end: str, arrival: str) -> None:
	"""Des fondus qui débordent du fichier (https://github.com/dascritch/machincast/issues/234)."""
	context.track = Track(
		SOUND_FILES / "sain.flac",
		configuration_test().audio,
		seconds(duration),
		seconds(start),
		seconds(end),
		real_time=False,
		departure=float(departure.replace(",", ".")),
		arrival=float(arrival.replace(",", ".")),
	)


@given(
	parsers.parse(
		"une voie pour un sonore de {duration} secondes commencé à {offset} secondes du début du fichier,"
		" avec {start} secondes de crossfade de début et {end} de fin"
	)
)
def trimmed_track(context: Context, duration: str, offset: str, start: str, end: str) -> None:
	"""Un sonore rogné par la détection de silence (https://github.com/dascritch/machincast/issues/146)."""
	context.track = Track(
		SOUND_FILES / "sain.flac",
		configuration_test().audio,
		seconds(duration),
		seconds(start),
		seconds(end),
		real_time=False,
		offset=seconds(offset),
	)


@given("une voie muette, pour un stream")
def silent_track(context: Context) -> None:
	context.track = Track("http://127.0.0.1:9/aucun-flux", configuration_test().audio, None, silent=True)


@when(parsers.parse("elle monte à plein volume en {duration} secondes"))
def raise_(context: Context, duration: str) -> None:
	assert context.track is not None
	context.track.fade(1.0, seconds(duration))


@when(parsers.parse("elle s'éteint en {duration} secondes"))
def switch_off(context: Context, duration: str) -> None:
	assert context.track is not None
	context.track.switch_off(seconds(duration))


@then(parsers.parse("elle s'arrêtera d'elle-même à {instant} secondes"))
def planned_stop(context: Context, instant: str) -> None:
	assert context.track is not None
	assert context.track.planned_stop == seconds(instant)


@when(parsers.parse("la voie de « {name} » s'éteint en {milliseconds:d} millisecondes"))
def switch_off_track(context: Context, name: str, milliseconds: int) -> None:
	context.tracks[name].switch_off(timedelta(milliseconds=milliseconds))


@then(parsers.parse("elle a fini moins de {milliseconds:d} millisecondes après son démarrage"))
def finished_early(context: Context, milliseconds: int) -> None:
	assert context.waiting_end is not None
	(name, start), *_ = context.startups.items()
	assert (context.waiting_end - start) * 1000 < milliseconds, name


@then(parsers.parse("à {instant} secondes, son volume est de {volume}"))
def volume(context: Context, instant: str, volume: str) -> None:
	assert context.track is not None
	assert context.track.volume_to(seconds(instant)) == pytest.approx(float(volume.replace(",", ".")))


@then(
	parsers.parse(
		"après un sonore de {duration} secondes avec {end} secondes de crossfade de fin, un sonore avec {start}"
		" secondes"
		" de crossfade de début démarre après {after} secondes, {fade}"
	)
)
def sequencing_point(duration: str, end: str, start: str, after: str, fade: str) -> None:
	assert sequencing(seconds(duration), seconds(end), seconds(start)) == seconds(after)
	expected = timedelta(0)
	if fade == "avec fondu d'entrée":
		expected = seconds(start)
	assert entry_fade(seconds(end), seconds(start)) == expected


@when("le sonore suivant n'a pas de crossfade de début")
def without_following_fade(context: Context) -> None:
	assert context.track is not None
	context.track.delete_output_fade()


# ─── Lecture ───────────────────────────────────────────────


@given(parsers.re(r"un moteur audio sur la sortie de la configuration de test, (?P<rhythm>au plus vite|en temps réel)"))
def sample_engine(context: Context, rhythm: str) -> None:
	context.engine = AudioEngine(configuration_test().audio, real_time=rhythm == "en temps réel")


@given(parsers.parse("un moteur audio sur la sortie « {output} », antenne « {on_air} », au plus vite"))
def engine_on_on_air(context: Context, output: str, on_air: str) -> None:
	"""https://github.com/dascritch/machincast/issues/339"""
	audio = dataclasses.replace(configuration_test().audio, output=output, device=on_air)  # type: ignore[arg-type]
	context.engine = AudioEngine(audio, real_time=False)


@given("un moteur audio sur la sortie de la configuration de test, en temps réel, à l'horloge du scénario")
def engine_to_scenario_clock(context: Context) -> None:
	context.engine = AudioEngine(configuration_test().audio, clock=lambda: context.time)


@when(parsers.parse("il joue le fichier de test « {name} », dont la sortie ne reçoit jamais de son"))
def play_without_sound(context: Context, name: str) -> None:
	"""Un lecteur bloqué au démarrage, comme playbin sur un AIFF, avant playbin3
	(https://github.com/dascritch/machincast/issues/284) : la sortie de la voie bloque tout son entrant, et la voie
	n'atteint jamais l'état PLAYING."""
	engine_ = engine(context)
	track = Track(SOUND_FILES / name, engine_.audio, timedelta(seconds=1), clock=engine_.clock)
	output = track._player.get_property("audio-sink")
	entry = output.get_static_pad("sink")
	assert entry is not None
	entry.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM, lambda _pad, _info: Gst.PadProbeReturn.OK)
	track.start()
	context.tracks[name] = track


@when(parsers.parse("le son de « {name} » avance"))
def the_advance_sound(context: Context, name: str) -> None:
	limit = time.monotonic() + MAXIMAL_WAITING
	while (context.tracks[name].position() <= timedelta(0)) and (time.monotonic() < limit):
		time.sleep(0.01)
	assert context.tracks[name].position() > timedelta(0)


@when(parsers.re(r"(?P<duration>[\d,]+) secondes? passent à l'horloge du moteur"))
def advance_clock(context: Context, duration: str) -> None:
	context.time += float(duration.replace(",", "."))


@then("aucune voie n'est bloquée")
def no_blocked(context: Context) -> None:
	assert {name: track.blocked() for name, track in context.tracks.items()} == dict.fromkeys(context.tracks, False)


@then(parsers.parse("seule la voie de « {name} » est bloquée"))
def only_blocked(context: Context, name: str) -> None:
	assert {other: track.blocked() for other, track in context.tracks.items()} == {
		other: other == name for other in context.tracks
	}


@when(parsers.parse("il joue le fichier de test « {name} »"))
def play(context: Context, name: str) -> None:
	context.tracks[name] = engine(context).play(SOUND_FILES / name, timedelta(seconds=1))
	context.startups[name] = time.monotonic()


@when(parsers.parse("il joue le fichier de test « {name} » de {start} à {end} seconde du fichier"))
def play_trimmed(context: Context, name: str, start: str, end: str) -> None:
	context.tracks[name] = engine(context).play(
		SOUND_FILES / name, seconds(end) - seconds(start), offset=seconds(start)
	)
	context.track = context.tracks[name]


@then(
	parsers.parse(
		"elle s'est arrêtée à {end} seconde du fichier, à {margin} seconde près, après avoir joué {played} seconde"
	)
)
def stopped_to(context: Context, end: str, margin: str, played: str) -> None:
	track = context.track
	assert (track is not None) and (track.final_position is not None)
	gap = seconds(margin)
	assert abs(track.offset + track.final_position - seconds(end)) <= gap, (track.offset, track.final_position)
	assert abs(track.final_position - seconds(played)) <= gap, track.final_position


@when("il joue un fichier qui contient du texte")
def play_text(context: Context, tmp_path: Path) -> None:
	fake = tmp_path / "faux.mp3"
	fake.write_text("ceci n'est pas du son", encoding="utf-8")
	context.tracks["texte"] = engine(context).play(fake, timedelta(seconds=1))


@when("j'attends la fin de ses voies")
def wait(context: Context) -> None:
	limit = time.monotonic() + MAXIMAL_WAITING
	while (engine(context).ongoing_tracks()) and (time.monotonic() < limit):
		engine(context).handle_messages()
		time.sleep(0.01)
	assert not engine(context).ongoing_tracks(), "voies toujours en cours"
	context.waiting_end = time.monotonic()


@when(parsers.parse("{milliseconds:d} millisecondes passent"))
def hold_on(context: Context, milliseconds: int) -> None:
	time.sleep(milliseconds / 1000)
	engine(context).handle_messages()


@when("il coupe net")
def cut(context: Context) -> None:
	engine(context).cut()


@then(parsers.parse("la voie de « {name} » est finie"))
def finished(context: Context, name: str) -> None:
	track = context.tracks[name]
	assert track.state == "finie", f"{track.state} : {track.error}"


@then(parsers.parse("elle a joué sur l'élément GStreamer « {factory} »"))
def output_item(context: Context, factory: str) -> None:
	track = next(iter(context.tracks.values()))
	assert track.output_factory == factory


@then(parsers.parse("elle a été lue par l'élément GStreamer « {factory} »"))
def player_item(context: Context, factory: str) -> None:
	"""https://github.com/dascritch/machincast/issues/284 : playbin3, qui ne se bloque pas au démarrage d'un AIFF."""
	track = next(iter(context.tracks.values()))
	builder = track._player.get_factory()
	assert (builder is not None) and (builder.get_name() == factory)


@then(parsers.parse("{count:d} voies sont en cours"))
def ongoing(context: Context, count: int) -> None:
	assert len(engine(context).ongoing_tracks()) == count


@then("aucune voie n'est en cours")
def no(context: Context) -> None:
	assert engine(context).ongoing_tracks() == []


@then(parsers.parse("la voie de « {name} » est coupée avant {milliseconds:d} millisecondes"))
def was_cut(context: Context, name: str, milliseconds: int) -> None:
	track = context.tracks[name]
	assert track.state == "coupée", track.state
	assert (track.final_position is not None) and (track.final_position < timedelta(milliseconds=milliseconds))


@then("la voie du fichier texte est en erreur, avec le motif de GStreamer")
def in_error(context: Context) -> None:
	track = context.tracks["texte"]
	assert track.state == "en erreur"
	assert track.error


# ─── Vérification avant lecture ────────────────────────────


@given(parsers.parse("un sonore indexé pour le fichier de test « {name} »"))
def indexed_sound(context: Context, empty_database: Connection, tmp_path: Path, name: str) -> None:
	file = sample_copy(name.split(".")[-1], tmp_path)
	state = file.stat()
	line = empty_database.execute(
		"INSERT INTO sounds (type, location, state, file_modified_at, file_size)"
		" VALUES ('file', %s, 'active', %s, %s) RETURNING id",
		(str(file), datetime.fromtimestamp(state.st_mtime, tz=UTC), state.st_size),
	).fetchone()
	assert line is not None
	context.sound, context.file = int(str(line[0])), file


@given("la date de modification du fichier a changé")
def changed_date(context: Context) -> None:
	assert context.file is not None
	state = context.file.stat()
	os.utime(context.file, (state.st_atime, state.st_mtime + 60))


@given("la taille du fichier a changé")
def changed_size(context: Context) -> None:
	assert context.file is not None
	state = context.file.stat()
	with context.file.open("ab") as file:
		file.write(b"\0" * 16)
	os.utime(context.file, (state.st_atime, state.st_mtime))


@given("le fichier a été supprimé")
def deleted(context: Context) -> None:
	assert context.file is not None
	context.file.unlink()


@when("le binaire lecture vérifie ce fichier avant de le jouer")
def check(context: Context, empty_database: Connection) -> None:
	assert context.sound is not None
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as connection:
		context.result = check_before_playback(connection, context.sound)


@then("le fichier est prêt à être joué")
def ready(context: Context) -> None:
	assert context.result == context.file


@then("le fichier n'est pas joué")
def not_played(context: Context) -> None:
	assert context.result is None


def log(database: Connection) -> list[tuple[object, ...]]:
	return database.execute("SELECT level::text, kind, message, sound_id FROM log ORDER BY id").fetchall()


@then("le log ne contient rien")
def empty_log(empty_database: Connection) -> None:
	assert log(empty_database) == []


@then(parsers.parse("le log contient une alerte « {kind} » pour ce sonore, qui mentionne « {mention} »"))
def warning(context: Context, empty_database: Connection, kind: str, mention: str) -> None:
	lines = log(empty_database)
	assert len(lines) == 1, lines
	level, found, message, sound = lines[0]
	assert (level, found, sound) == ("warning", kind, context.sound)
	assert mention in str(message), message


@then(parsers.parse("le log contient un incident « {kind} » pour ce sonore"))
def incident(context: Context, empty_database: Connection, kind: str) -> None:
	lines = log(empty_database)
	assert [(n, t, s) for n, t, _, s in lines] == [("incident", kind, context.sound)], lines
