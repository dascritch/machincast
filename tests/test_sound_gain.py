"""Scénarios du gain d'un sonore, répondu par un plugin (https://github.com/dascritch/machincast/issues/643).

La diffusion joue au plus vite sur la sortie factice ; les étapes sont dans tests/broadcast_steps.py. Le plugin des
scénarios s'abonne aux points de la diffusion (Bench.points).
"""

import math
from collections.abc import Mapping
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then

from machincast.player.plugin_points import SOUND_GAIN
from machincast.plugins.points import Points
from tests.broadcast_steps import Bench, Connection, sound

scenarios("sound_gain.feature")


@pytest.fixture
def received() -> list[Mapping[str, Any]]:
	return []


def _points(bench: Bench) -> Points:
	if bench.points is None:
		bench.points = Points()
	return bench.points


@given(parsers.parse("les propriétés du sonore « {name} » {properties}"))
def properties(empty_database: Connection, name: str, properties: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET properties = %s::jsonb WHERE id = %s", (properties, sound(empty_database, name))
	)


@given(parsers.parse("un plugin qui répond un gain de « {answer} »"))
def plugin(bench: Bench, received: list[Mapping[str, Any]], answer: str) -> None:
	def gain(data: Mapping[str, Any]) -> object:
		received.append(data)
		if answer == "-23 moins la sonie intégrée":
			measured = data["properties"].get("loudness")
			if measured is None:
				return None
			return -23 - measured["integrated"]
		if answer == "fort":
			return answer
		return float(answer)

	_points(bench).subscribe("scénario", SOUND_GAIN, gain)


@then(parsers.re(r"la voie de « (?P<name>[^»]+) » a un gain de (?P<gain>-?\d+) dB"))
def track_gain(bench: Bench, name: str, gain: str) -> None:
	assert bench.engine is not None
	track = bench.engine.played_list[str(bench.files[name])]
	assert track.gain == float(gain)
	element = track._player.get_property("audio-sink").get_by_name("gain")
	assert element is not None
	assert element.get_property("volume") == pytest.approx(10 ** (float(gain) / 20))
	assert math.isfinite(element.get_property("volume"))


@then(parsers.parse("le plugin a reçu les propriétés du sonore « {name} », avec sa sonie"))
def received_properties(empty_database: Connection, received: list[Mapping[str, Any]], name: str) -> None:
	identifier = sound(empty_database, name)
	found = []
	for data in received:
		if data["sound"] == identifier:
			found.append(data)
	assert found != [], received
	assert found[0]["properties"]["loudness"] == {"integrated": -17.0, "peak": -1.0}
	assert found[0]["event"] is not None
