"""Scénarios de la carte virtuelle de l'antenne factice (https://github.com/dascritch/machincast/issues/400).

Ceux qui ont besoin de PipeWire en lancent un à part, avec WirePlumber (tests/test_locked_output.py), et jouent ou
écoutent dans des processus à part, qui ont son environnement (tests/pipewire_player.py, tests/pipewire_levels.py).
Sans pipewire ni wireplumber, ils sont ignorés.
"""

import logging
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import audio
from machincast.configuration import DUMMY, VIRTUAL_CARD, Audio
from machincast.player import virtual_card
from tests.test_locked_output import PipeWireBench, _pipewire_present, _stop

scenarios("virtual_on_air.feature")


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(audio=None, played=None, bench=None, players=[])


@pytest.fixture
def bench(tmp_path: Path, context: SimpleNamespace) -> Iterator[PipeWireBench]:
	"""Les sons s'arrêtent avant PipeWire : une sortie dont le serveur a disparu ne s'arrêterait plus."""
	if not _pipewire_present():
		pytest.skip("pipewire ou wireplumber absent")
	bench = PipeWireBench(tmp_path)
	bench.start()
	yield bench
	for player in context.players:
		if player.poll() is None:
			_stop(player)
	bench.halt()


@given(parsers.parse("l'antenne sur l'entrée « sortie factice » de la sortie « {output} »"))
def dummy_on_air(context: SimpleNamespace, output: str) -> None:
	context.audio = Audio(output=output, device=DUMMY, preview="casque")  # type: ignore[arg-type]


@then(parsers.parse("l'antenne est jouée et écoutée sur « {card} »"))
def played_and_monitored(context: SimpleNamespace, card: str) -> None:
	expected = (context.audio.output, card)
	if card == "la sortie factice":
		expected = ("dummy", None)
	assert context.audio.monitored_on_air() == expected
	assert context.audio.virtual_on_air() is (card == VIRTUAL_CARD)


@given("un PipeWire à part")
def pipewire(context: SimpleNamespace, bench: PipeWireBench) -> None:
	context.bench = bench


@when(parsers.parse("Machin player joue l'antenne factice d'une sortie « {output} »"))
def player_plays(context: SimpleNamespace, output: str) -> None:
	assert output == "pipewire"
	player = subprocess.Popen(
		[sys.executable, "-m", "tests.pipewire_player", "factice"],
		env=context.bench.env,
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		text=True,
	)
	context.players.append(player)
	assert player.stdout is not None
	assert player.stdout.readline().strip() == "prêt"
	assert context.bench._wait(lambda: VIRTUAL_CARD in context.bench.linked_to(audio.ON_AIR.program))


@when("Machin player s'arrête")
def player_stops(context: SimpleNamespace) -> None:
	_stop(context.players[-1])


@when("Machin player est tué")
def player_killed(context: SimpleNamespace) -> None:
	player = context.players[-1]
	player.kill()
	player.wait()


@then(parsers.parse("PipeWire a la carte « {name} », décrite « {description} »"))
def card_present(context: SimpleNamespace, name: str, description: str) -> None:
	assert context.bench.node(name) is not None
	assert context.bench.node(description, "node.description") == context.bench.node(name)


@then(parsers.parse("le flux de Machin player joue sur « {name} »"))
def stream_on_card(context: SimpleNamespace, name: str) -> None:
	assert context.bench.linked_to(audio.ON_AIR.program) == {name}


@then(parsers.parse("PipeWire n'a plus la carte « {name} »"))
def card_absent(context: SimpleNamespace, name: str) -> None:
	assert context.bench._wait(lambda: context.bench.node(name) is None)


@then(parsers.parse("le port de monitoring de l'antenne factice relève un son au-dessus de {threshold:g} dB"))
def monitored_sound(context: SimpleNamespace, threshold: float) -> None:
	result = subprocess.run(
		[sys.executable, "-m", "tests.pipewire_levels", "pipewire", DUMMY],
		env=context.bench.env,
		capture_output=True,
		text=True,
		timeout=30,
		check=True,
	)
	assert float(result.stdout.strip()) > threshold, result


@when(parsers.parse("Machin player prépare l'antenne factice d'une sortie « {output} », sans PipeWire joignable"))
def without_pipewire(context: SimpleNamespace, output: str, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
	environment = {"PATH": "/usr/bin:/bin", "XDG_RUNTIME_DIR": str(tmp_path), "PIPEWIRE_RUNTIME_DIR": str(tmp_path)}
	caplog.set_level(logging.INFO, logger="machincast")
	on_air = Audio(output=output, device=DUMMY, preview="casque")  # type: ignore[arg-type]
	with virtual_card.on_air(on_air, environment) as played:
		context.played = played


@then("l'antenne est jouée sur la sortie factice")
def played_dummy(context: SimpleNamespace) -> None:
	assert context.played.on_air() == ("dummy", None)


@then(parsers.parse("le log dit « {text} »"))
def logged(caplog: pytest.LogCaptureFixture, text: str) -> None:
	messages = []
	for record in caplog.records:
		messages.append(record.getMessage())
	found = False
	for message in messages:
		if text in message:
			found = True
	assert found, messages
