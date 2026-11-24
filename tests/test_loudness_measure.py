"""Scénarios de la mesure du niveau d'un sonore à l'audit complet (https://github.com/dascritch/machincast/issues/642).

Les fichiers sont des sinusoïdes de 1 kHz écrites en WAV par GStreamer dans le répertoire du scénario ; les étapes de
l'indexeur sont dans tests/indexing_steps.py.
"""

import json
import math
import struct
from pathlib import Path

import gi
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.indexer.decoding import Check, check_file
from tests.indexing_steps import Connection

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("loudness_measure.feature")

CHANNELS = {"mono": 1, "stéréo": 2}
SAMPLES_PER_BUFFER = 1024


def _number(text: str) -> float:
	return float(text.replace(",", "."))


def _write(path: Path, pieces: list[tuple[float, float]], channels: int, rate: int) -> Path:
	"""Un WAV 16 bits de morceaux de sinusoïde de 1 kHz : durée en secondes et niveau crête en dBFS (None : silence)."""
	samples = bytearray()
	for seconds, level in pieces:
		amplitude = 0.0
		if not math.isnan(level):
			amplitude = 10 ** (level / 20)
		for index in range(round(seconds * rate)):
			value = round(amplitude * 32767 * math.sin(2 * math.pi * 1000 * index / rate))
			for _channel in range(channels):
				samples += struct.pack("<h", value)
	Gst.init(None)
	pipeline = Gst.parse_launch(
		f"appsrc name=source format=time caps=audio/x-raw,format=S16LE,layout=interleaved,rate={rate},"
		f"channels={channels} ! wavenc ! filesink name=fichier"
	)
	assert isinstance(pipeline, Gst.Bin)
	source, file = pipeline.get_by_name("source"), pipeline.get_by_name("fichier")
	assert (source is not None) and (file is not None)
	file.set_property("location", str(path))
	pipeline.set_state(Gst.State.PLAYING)
	buffer = Gst.Buffer.new_wrapped(bytes(samples))
	buffer.pts = 0
	buffer.duration = round(len(samples) / 2 / channels / rate * Gst.SECOND)
	source.emit("push-buffer", buffer)
	source.emit("end-of-stream")
	bus = pipeline.get_bus()
	assert bus is not None
	message = bus.timed_pop_filtered(60 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
	pipeline.set_state(Gst.State.NULL)
	assert (message is not None) and (message.type == Gst.MessageType.EOS)
	return path


# ─── Étant donné ───────────────────────────────────────────


@given(
	parsers.re(
		r"un fichier wav de (?P<seconds>[\d,]+) secondes?, (?:sinusoïde de 1 kHz à (?P<level>-?\d+) dBFS|silence),"
		r" (?P<channels>mono|stéréo), à (?P<rate>\d+) Hz"
	),
	target_fixture="file",
)
def sine(tmp_path: Path, seconds: str, level: str | None, channels: str, rate: str) -> Path:
	found = math.nan
	if level is not None:
		found = float(level)
	return _write(tmp_path / "son.wav", [(_number(seconds), found)], CHANNELS[channels], int(rate))


@given(
	parsers.re(
		r"un fichier wav fait de (?P<first>\d+) secondes à (?P<loud>-?\d+) dBFS puis (?P<second>\d+) secondes à"
		r" (?P<soft>-?\d+) dBFS, mono, à (?P<rate>\d+) Hz"
	),
	target_fixture="file",
)
def two_pieces(tmp_path: Path, first: str, loud: str, second: str, soft: str, rate: str) -> Path:
	pieces = [(float(first), float(loud)), (float(second), float(soft))]
	return _write(tmp_path / "son.wav", pieces, 1, int(rate))


@given(parsers.parse("ses propriétés {properties}"))
def properties(empty_database: Connection, sound: int, properties: str) -> None:
	empty_database.execute("UPDATE sounds SET properties = %s::jsonb WHERE id = %s", (properties, sound))


# ─── Quand ─────────────────────────────────────────────────


@when("je vérifie ce fichier en audit complet", target_fixture="result")
def audited(file: Path) -> Check:
	return check_file(file, silence_threshold=-60.0)


# ─── Alors ─────────────────────────────────────────────────


def _measured(result: Check) -> tuple[float | None, float | None]:
	assert result.loudness is not None, result
	return result.loudness.integrated, result.loudness.peak


@then(parsers.re(r"sa sonie intégrée est de (?P<expected>-?\d+) LUFS à 0,1 près"))
def loudness(result: Check, expected: str) -> None:
	integrated, _peak = _measured(result)
	assert integrated == pytest.approx(float(expected), abs=0.1)


@then(parsers.re(r"sa crête est de (?P<expected>-?\d+) dBFS à 0,1 près"))
def peak(result: Check, expected: str) -> None:
	_integrated, found = _measured(result)
	assert found == pytest.approx(float(expected), abs=0.1)


@then("il n'a ni sonie intégrée ni crête")
def nothing(result: Check) -> None:
	assert _measured(result) == (None, None)


@then("il n'a pas de sonie intégrée")
def no_loudness(result: Check) -> None:
	assert _measured(result)[0] is None


@then("le niveau n'a pas été mesuré")
def not_measured(result: Check) -> None:
	assert result.loudness is None


@then(parsers.parse("ses propriétés sont {expected}"))
def stored(empty_database: Connection, sound: int, expected: str) -> None:
	line = empty_database.execute("SELECT properties FROM sounds WHERE id = %s", (sound,)).fetchone()
	assert line is not None
	assert line[0] == json.loads(expected)
