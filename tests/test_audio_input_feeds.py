"""Scénarios des feeds d'entrée audio, et de leurs streams joués par Machin player
(https://github.com/dascritch/machincast/issues/623).

Les étapes de la fenêtre et des listes sont dans tests/interface_steps.py ; celles des Paramètres du service, dans
tests/test_audio_inputs.py. Le moteur audio joue sur la sortie factice, qui capte un son de test.
"""

import dataclasses
import time
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from PySide6.QtWidgets import QWidget
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import audio, service
from machincast.clock import FixedClock
from machincast.configuration import AudioInput
from machincast.interface import dialogs
from machincast.interface.audio_inputs import InputReservation
from machincast.interface.feed_card import FeedCard
from machincast.interface.preferences import SERVICE, Settings
from machincast.player import queries as player_queries
from machincast.player.engine import AudioEngine, PlaybackTrack, Track
from machincast.player.simulation import SimulatedEngine, SimulatedTrack
from tests.database_fixtures import configuration_test
from tests.interface_steps import Connection, Context, window

scenarios("audio_input_feeds.feature")


@dataclasses.dataclass
class Playing:
	engine: AudioEngine | None = None
	track: PlaybackTrack | None = None
	capture: Any = None


@pytest.fixture
def playing() -> Iterator[Playing]:
	found = Playing()
	yield found
	if found.engine is not None:
		found.engine.shut_down()


def _track(playing: Playing) -> Track:
	assert isinstance(playing.track, Track), playing.track
	return playing.track


# ─── Étant donné ───────────────────────────────────────────


@given("le service de diffusion non installé")
def service_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Enregistrer les Paramètres du service ne réserve rien (audio_inputs.feature)."""
	absent = service.ServiceState(installed=False, active="inactive")
	monkeypatch.setattr(service, "read_state", lambda: absent)
	monkeypatch.setattr(InputReservation, "start", lambda _self, _path: None)


@given(parsers.parse("le feed d'entrée « {name} » sur « {device} », suivi de son stream"))
def input_feed(empty_database: Connection, name: str, device: str) -> None:
	created = empty_database.execute(
		"INSERT INTO feeds (name, device) VALUES (%s, %s) RETURNING id", (name, device)
	).fetchone()
	assert created is not None
	empty_database.execute(
		"INSERT INTO sounds (type, feed_id, title, state) VALUES ('stream', %s, %s, 'active')", (created[0], name)
	)


@given(parsers.re(r"un moteur audio sur la sortie factice, en temps réel(?P<blind>, qui ne voit aucune entrée)?$"))
def dummy_engine(playing: Playing, blind: str | None) -> None:
	settings = dataclasses.replace(configuration_test().audio, output="dummy", device=None)
	present = None
	if blind is not None:
		present = lambda _device: False  # noqa: E731
	playing.engine = AudioEngine(settings, real_time=True, input_present=present)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("j'enregistre dans les Paramètres du service l'entrée « {name} » sur « {device} »"))
def save_in_window(interface: Context, monkeypatch: pytest.MonkeyPatch, name: str, device: str) -> None:
	def answered(_parent: QWidget, shown: Settings, *_arguments: Any, **_keywords: Any) -> Settings:
		return dataclasses.replace(shown, inputs=(AudioInput(device, name),))

	monkeypatch.setattr(dialogs, "set_preferences", answered)
	window(interface)._preferences(SERVICE)


@when(parsers.parse("les Paramètres du service ont l'entrée « {name} » sur « {device} »"))
def configured_inputs(interface: Context, name: str, device: str) -> None:
	opened = window(interface)
	opened.audio = dataclasses.replace(opened.audio, inputs=(AudioInput(device, name),))


@when(parsers.parse("il joue l'adresse « {address} »"))
def play_address(playing: Playing, address: str) -> None:
	assert playing.engine is not None
	playing.track = playing.engine.play(address, None)


@when(parsers.parse("{milliseconds:d} millisecondes s'écoulent"))
def elapse(playing: Playing, milliseconds: int) -> None:
	assert playing.engine is not None
	end = time.monotonic() + milliseconds / 1000
	while time.monotonic() < end:
		playing.engine.handle_messages()
		time.sleep(0.02)


@when("il coupe net")
def cut(playing: Playing) -> None:
	assert playing.engine is not None
	playing.engine.cut()


@when(parsers.parse("la simulation joue l'adresse « {address} »"))
def simulate(playing: Playing, address: str) -> None:
	clock = FixedClock(datetime(2026, 11, 24, 10, tzinfo=ZoneInfo("Europe/Paris")))
	playing.track = SimulatedEngine(clock).play(address, None)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le feed « {name} » est en base, sur l'entrée « {device} »"))
def feed_in_database(empty_database: Connection, name: str, device: str) -> None:
	found = empty_database.execute("SELECT url, device FROM feeds WHERE name = %s", (name,)).fetchall()
	assert found == [(None, device)], found


@then(parsers.parse("aucun feed n'est sur l'entrée « {device} »"))
def no_feed(empty_database: Connection, device: str) -> None:
	assert empty_database.execute("SELECT id FROM feeds WHERE device = %s", (device,)).fetchall() == []


@then(parsers.parse("la barre d'état dit, entre autres, « {text} »"))
def state_bar_contains(interface: Context, text: str) -> None:
	message = window(interface).statusBar().currentMessage()
	assert text in message, message


@then(parsers.parse("la fiche du feed d'entrée montre « {caption} » « {device} », sans mémoire tampon ni test"))
def input_card(interface: Context, caption: str, device: str) -> None:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, FeedCard), opened
	ui = opened.ui
	assert (ui.url_caption.text(), ui.url.text(), ui.url.isReadOnly()) == (caption, device, True)
	for widget in (ui.buffer, ui.buffer_caption, ui.buffer_explanation, ui.test, ui.trial_result):
		assert not widget.isVisibleTo(opened), widget.objectName()


@then("son nom ne se change pas dans la fiche")
def name_read_only(interface: Context) -> None:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, FeedCard), opened
	assert opened.ui.name.isReadOnly()
	assert "Paramètres du service" in opened.ui.name.toolTip()


@then(parsers.parse("Machin player joue le stream « {title} » à l'adresse « {address} », sans mémoire tampon"))
def player_parameters(empty_database: Connection, title: str, address: str) -> None:
	sound = empty_database.execute("SELECT id FROM sounds WHERE title = %s", (title,)).fetchone()
	assert sound is not None
	line = player_queries.playing_parameters(empty_database, None, int(str(sound[0])))
	assert line is not None
	assert (line[3], line[4], line[16]) == ("stream", address, None), line


@then(parsers.parse("la voie capte « {factory} », et sa position avance"))
def captures(playing: Playing, factory: str) -> None:
	track = _track(playing)
	assert track.state == "playing", track.error
	assert track.capture is not None
	factories: list[str] = []

	def note(element: Any) -> None:
		element_factory = element.get_factory()
		if element_factory is not None:
			factories.append(element_factory.get_name())

	track._player.iterate_elements().foreach(note)  # noqa: SLF001
	assert factory in factories, factories
	assert track.position() > timedelta(0)


@then("la voie est coupée")
def track_cut(playing: Playing) -> None:
	assert _track(playing).state == "cut"


@then(parsers.parse("la voie est en erreur « {error} »"))
def track_error(playing: Playing, error: str) -> None:
	track = _track(playing)
	assert (track.state, track.error) == ("error", error)


@then(
	parsers.parse(
		"la capture de « {device} » sur la sortie « {output} » est un élément « {factory} », dont « {name} » vaut"
		" « {value} »"
	)
)
def capture_element(device: str, output: str, factory: str, name: str, value: str) -> None:
	element = audio.create_capture(output, device)  # type: ignore[arg-type]
	element_factory = element.get_factory()
	assert element_factory is not None
	assert (element_factory.get_name(), element.get_property(name)) == (factory, value)


@then(parsers.parse("la capture de « {device} » sur la sortie « {output} » ne se replie jamais sur une autre entrée"))
def locked_capture(playing: Playing, device: str, output: str) -> None:
	playing.capture = audio.create_capture(output, device)  # type: ignore[arg-type]
	properties = playing.capture.get_property("stream-properties")
	for key in audio.LOCK:
		assert properties.get_value(key) is True, key


@then(parsers.parse("elle se présente comme le flux « {stream} » de « {program} »"))
def presented(playing: Playing, stream: str, program: str) -> None:
	assert playing.capture is not None
	properties = playing.capture.get_property("stream-properties")
	assert (properties.get_value("media.name"), properties.get_value("application.name")) == (stream, program)


@then("sa voie joue, sans fin prévue")
def simulated(playing: Playing) -> None:
	track = playing.track
	assert isinstance(track, SimulatedTrack), track
	assert (track.state, track.planned_end()) == ("playing", None)
