"""Scénarios des effets d'un sonore, répondus par un plugin (https://github.com/dascritch/machincast/issues/644).

La diffusion joue au plus vite sur la sortie factice ; les étapes sont dans tests/broadcast_steps.py. Les plugins des
scénarios s'abonnent aux points de la diffusion (Bench.points).
"""

import logging
from collections.abc import Mapping
from typing import Any

import pytest
from gi.repository import Gst
from pytest_bdd import given, parsers, scenarios, then

from machincast.player.engine import Track
from machincast.player.plugin_points import SOUND_EFFECTS
from machincast.plugins.points import Points
from tests.broadcast_steps import Bench, Connection, sound

scenarios("sound_effects.feature")


@pytest.fixture
def received() -> list[Mapping[str, Any]]:
	return []


def _points(bench: Bench) -> Points:
	if bench.points is None:
		bench.points = Points()
	return bench.points


def _subscribe(bench: Bench, received: list[Mapping[str, Any]], plugin: str, answer: str) -> None:
	def effects(data: Mapping[str, Any]) -> str:
		received.append(data)
		return answer

	_points(bench).subscribe(plugin, SOUND_EFFECTS, effects)


@given(parsers.parse("un plugin qui répond les effets « {answer} »"))
def plugin(bench: Bench, received: list[Mapping[str, Any]], answer: str) -> None:
	_subscribe(bench, received, "scénario", answer)


@given(parsers.parse("un second plugin qui répond les effets « {answer} »"))
def second(bench: Bench, received: list[Mapping[str, Any]], answer: str) -> None:
	_subscribe(bench, received, "second", answer)


def _track(bench: Bench, name: str) -> Track:
	assert bench.engine is not None
	return bench.engine.played_list[str(bench.files[name])]


def _factories(element: Gst.Bin) -> list[str]:
	"""Les fabriques des éléments du bin, de l'entrée vers la sortie."""
	found = []
	inner = element.iterate_sorted()
	items: list[Gst.Element] = []
	inner.foreach(items.append)
	for item in reversed(items):
		factory = item.get_factory()
		if factory is not None:
			found.append(factory.get_name())
	return found


@then(parsers.parse("la voie de « {name} » n'a aucun effet"))
def no_effect(bench: Bench, name: str) -> None:
	track = _track(bench, name)
	assert track.effects is None
	gain = track._player.get_property("audio-sink").get_by_name("gain")
	following = gain.get_static_pad("src").get_peer().get_parent_element()
	assert following.get_factory().get_name() == "volume"


@then(parsers.re(r"la voie de « (?P<name>[^»]+) » passe par « (?P<first>[^»]+) »(?: puis « (?P<second>[^»]+) »)?$"))
def through(bench: Bench, name: str, first: str, second: str | None) -> None:
	track = _track(bench, name)
	assert track.effects is not None
	expected = [first]
	if second is not None:
		expected.append(second)
	assert _factories(track.effects) == expected


@then(parsers.parse("la voie de « {name} » passe par « {factory} », entre son gain et son enveloppe de volume"))
def between(bench: Bench, name: str, factory: str) -> None:
	track = _track(bench, name)
	assert track.effects is not None
	sink = track._player.get_property("audio-sink")
	gain = sink.get_by_name("gain")
	assert gain.get_static_pad("src").get_peer().get_parent_element() == track.effects
	following = track.effects.get_static_pad("src").get_peer().get_parent_element()
	assert following.get_factory().get_name() == "volume"
	assert _factories(track.effects) == [factory]


@then(
	parsers.re(r"son « (?P<factory>[^»]+) » a « threshold » à (?P<threshold>[\d.]+) et « ratio » à (?P<ratio>[\d.]+)")
)
def properties(bench: Bench, factory: str, threshold: str, ratio: str) -> None:
	track = _track(bench, "a")
	assert track.effects is not None
	items: list[Gst.Element] = []
	track.effects.iterate_elements().foreach(items.append)
	(found,) = items
	assert found.get_factory().get_name() == factory
	assert found.get_property("threshold") == pytest.approx(float(threshold))
	assert found.get_property("ratio") == pytest.approx(float(ratio))


@then(parsers.parse("le plugin a reçu le sonore « {name} », qui n'est pas un stream"))
def received_data(empty_database: Connection, received: list[Mapping[str, Any]], name: str) -> None:
	identifier = sound(empty_database, name)
	found = []
	for data in received:
		if data["sound"] == identifier:
			found.append(data)
	assert found != [], received
	assert found[0]["stream"] is False
	assert "properties" in found[0]


@then(parsers.parse("le journal dit que les effets « {description} » sont refusés"))
def journal(caplog: pytest.LogCaptureFixture, description: str) -> None:
	found = []
	for record in caplog.records:
		if (record.levelno >= logging.WARNING) and (description in record.getMessage()):
			found.append(record.getMessage())
	assert found != [], caplog.records
