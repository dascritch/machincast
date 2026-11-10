"""Scénarios du verrou des sorties PipeWire sur leur périphérique (https://github.com/dascritch/machincast/issues/345).

Les scénarios de comportement font tourner un PipeWire et un WirePlumber à part (PipeWireBench), dans des répertoires
temporaires : jamais ceux du poste. Le son y joue dans un processus à part, lancé avec leur environnement
(tests/pipewire_player.py, https://github.com/dascritch/machincast/issues/384) : celui des tests a pu joindre le
PipeWire du poste, et un pipewiresink y créé le rejoignait. Les sorties sont deux sorties
muettes (support.null-audio-sink) : la pré-écoute, périphérique par défaut, et l'antenne. Sans pipewire ni
wireplumber, ces scénarios sont ignorés.
"""

import json
import os
import select
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import audio
from machincast.configuration import Audio
from machincast.interface import monitor

WAITING = 5.0
"""Secondes que WirePlumber a pour relier un flux."""
CALM = 1.5
"""Secondes au bout desquelles un flux qui n'est pas relié ne le sera pas."""
PROGRAMS = {
	"Machin player": audio.ON_AIR,
	"la pré-écoute": audio.PREVIEW,
	"l'essai de la sortie": audio.TRIAL,
}


def _pipewire_present() -> bool:
	for tool in ("pipewire", "wireplumber", "pw-cli", "pw-dump", "pw-metadata"):
		if not (shutil.which(tool)):
			return False
	return True


class PipeWireBench:
	"""Un PipeWire et un WirePlumber à part, sans bus D-Bus, dans des répertoires temporaires."""

	def __init__(self, root: Path) -> None:
		self.env = dict(os.environ)
		for name in ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME"):
			path = root / name.lower()
			path.mkdir(mode=0o700)
			self.env[name] = str(path)
		self.env["PIPEWIRE_RUNTIME_DIR"] = self.env["XDG_RUNTIME_DIR"]
		for name in ("DBUS_SESSION_BUS_ADDRESS", "PULSE_SERVER", "PIPEWIRE_REMOTE", "PIPEWIRE_CORE"):
			self.env.pop(name, None)
		self.log = root / "pipewire.log"
		self.process: list[subprocess.Popen[bytes]] = []

	def start(self) -> None:
		with self.log.open("ab") as output:
			self.process.append(subprocess.Popen(["pipewire"], env=self.env, stdout=output, stderr=output))
			self._wait(lambda: self._command("pw-cli", "info", "0").returncode == 0)
			self.process.append(subprocess.Popen(["wireplumber"], env=self.env, stdout=output, stderr=output))
		# WirePlumber est prêt quand il a créé le pilote factice.
		self._wait(lambda: self.node("Dummy-Driver") is not None)

	def halt(self) -> None:
		for process in reversed(self.process):
			process.terminate()
			try:
				process.wait(timeout=5)
			except subprocess.TimeoutExpired:
				process.kill()

	def _command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
		return subprocess.run(arguments, env=self.env, capture_output=True, text=True, timeout=10, check=False)

	@staticmethod
	def _wait(condition: Callable[[], bool], delay: float = WAITING) -> bool:
		limit = time.monotonic() + delay
		while time.monotonic() < limit:
			if condition():
				return True
			time.sleep(0.1)
		return condition()

	def objects(self) -> list[dict[str, object]]:
		result = self._command("pw-dump")
		if result.returncode != 0:
			return []
		objects: list[dict[str, object]] = json.loads(result.stdout)
		return objects

	def create_output(self, name: str) -> None:
		self._command(
			"pw-cli",
			"create-node",
			"adapter",
			f"{{ factory.name=support.null-audio-sink node.name={name} media.class=Audio/Sink object.linger=true"
			" audio.position=[ FL FR ] }",
		)
		self._wait(lambda: self.node(name) is not None)

	def destroy_output(self, name: str) -> None:
		identifier = self.node(name)
		assert identifier is not None, name
		self._command("pw-cli", "destroy", str(identifier))
		self._wait(lambda: self.node(name) is None)

	def default(self, name: str) -> None:
		self._command("pw-metadata", "0", "default.configured.audio.sink", json.dumps({"name": name}))

	def move(self, stream: int, name: str) -> None:
		"""Ce que font les réglages du son du poste pour déplacer un flux : la métadonnée target.object."""
		self._command("pw-metadata", str(stream), "target.object", name)

	def node(self, name: str, key: str = "node.name") -> int | None:
		for object_ in self.objects():
			info = object_.get("info")
			if (
				(object_.get("type") == "PipeWire:Interface:Node")
				and (isinstance(info, dict))
				and (info.get("props", {}).get(key) == name)
			):
				return int(str(object_["id"]))
		return None

	def linked_to(self, program: str) -> set[str]:
		"""Les sorties auxquelles le flux du programme (application.name) est relié."""
		objects = self.objects()
		names = {}
		stream = None

		def linked_object_(object_) -> None:
			nonlocal stream
			info = object_.get("info")
			if (object_.get("type") != "PipeWire:Interface:Node") or (not isinstance(info, dict)):
				return
			properties = info.get("props", {})
			names[object_["id"]] = properties.get("node.name")
			if properties.get("application.name") == program:
				stream = object_["id"]

		for object_ in objects:
			linked_object_(object_)
		linked_list = set()
		for object_ in objects:
			info = object_.get("info")
			link = (object_.get("type") == "PipeWire:Interface:Link") and (isinstance(info, dict))
			if (link) and (isinstance(info, dict)) and (info.get("output-node-id") == stream):
				linked_list.add(str(names.get(info.get("input-node-id"))))
		return linked_list


@pytest.fixture
def context() -> SimpleNamespace:
	return SimpleNamespace(output=None, source=None, bench=None, players=[], program=None)


@pytest.fixture
def bench(tmp_path: Path, context: SimpleNamespace) -> Iterator[PipeWireBench]:
	"""Les sons s'arrêtent avant PipeWire : une sortie dont le serveur a disparu ne s'arrêterait plus."""
	if not _pipewire_present():
		pytest.skip("pipewire ou wireplumber absent")
	bench = PipeWireBench(tmp_path)
	bench.start()
	yield bench
	for player in context.players:
		_stop(player)
	bench.halt()


def _stop(player: subprocess.Popen[str]) -> None:
	assert player.stdin is not None
	player.stdin.close()
	try:
		player.wait(timeout=5)
	except subprocess.TimeoutExpired:
		player.kill()
		player.wait()


# ─── Propriétés ────────────────────────────────────────────


@when(
	parsers.re(r"je crée la sortie « (?P<output>[^»]+) » de (?P<program>.+), sur le périphérique « (?P<device>[^»]*) »")
)
def create(context: SimpleNamespace, output: str, program: str, device: str) -> None:
	context.output = audio.create_output(
		output,  # type: ignore[arg-type]
		(device) or (None),
		presentation=PROGRAMS[program],
	)


@when(parsers.parse("je crée la source du VU-mètre de l'antenne « {device} », sur PipeWire"))
def create_source(context: SimpleNamespace, device: str) -> None:
	block = monitor.monitor_source(Audio(output="pipewire", device=device, preview="casque"))
	item_list = []
	for item in block.children:
		if item.get_factory().get_name() == "pipewiresrc":
			item_list.append(item)
	(context.source,) = item_list


def _locked(item: audio.Gst.Element, device: str) -> None:
	properties = item.get_property("stream-properties")
	assert item.get_property("target-object") == device
	assert properties is not None
	key_dict = {}
	for key in audio.LOCK:
		key_dict[key] = properties.get_value(key)
	assert key_dict == dict.fromkeys(audio.LOCK, True)


@then(parsers.parse("la sortie vise « {device} », sans repli, en l'attendant, sans déplacement"))
def locked_output(context: SimpleNamespace, device: str) -> None:
	_locked(context.output, device)


@then(parsers.parse("la source vise « {device} », sans repli, en l'attendant, sans déplacement"))
def locked_source(context: SimpleNamespace, device: str) -> None:
	_locked(context.source, device)
	assert context.source.get_property("stream-properties").get_value("stream.capture.sink") is True


@then(parsers.parse("la sortie se présente toujours comme « {name} »"))
def always_presented(context: SimpleNamespace, name: str) -> None:
	properties = context.output.get_property("stream-properties")
	assert (context.output.get_property("client-name"), properties.get_string("application.name")) == (name, name)


@then("la sortie n'a pas de verrou")
def without_lock(context: SimpleNamespace) -> None:
	output = context.output
	if output.find_property("stream-properties") is None:
		return
	properties = output.get_property("stream-properties")
	if properties is not None:
		for key in audio.LOCK:
			assert not properties.has_field(key), key


# ─── Comportement ──────────────────────────────────────────


@given(parsers.re(r"un PipeWire à part, avec la pré-écoute par défaut(?P<on_air> et l'antenne)?"))
def pipewire_to_share(context: SimpleNamespace, bench: PipeWireBench, on_air: str | None) -> None:
	bench.create_output("preecoute")
	bench.default("preecoute")
	if on_air is not None:
		bench.create_output("antenne")
	context.bench = bench


def _play(context: SimpleNamespace, kind: str, program: str) -> None:
	"""Un son continu sur la sortie, dans un processus à part, avec l'environnement du PipeWire à part : le flux
	existe même sans périphérique où aller."""
	player = subprocess.Popen(
		[sys.executable, "-m", "tests.pipewire_player", kind],
		env=context.bench.env,
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		text=True,
	)
	context.players.append(player)
	assert player.stdout is not None
	assert player.stdout.readline().strip() == "prêt"
	context.program = program
	context.bench._wait(lambda: context.bench.node(program, "application.name") is not None)


@when("l'antenne joue sur sa sortie")
def played_on_air(context: SimpleNamespace) -> None:
	_play(context, "antenne", audio.ON_AIR.program)


@when("une sortie sans verrou joue sur l'antenne")
def without_played_lock(context: SimpleNamespace) -> None:
	_play(context, "sans-verrou", "Sans verrou")


@when(parsers.parse("le périphérique « {name} » disparaît"))
def disappears(context: SimpleNamespace, name: str) -> None:
	context.bench.destroy_output(name)


@when(parsers.parse("le périphérique « {name} » revient"))
def comes_back(context: SimpleNamespace, name: str) -> None:
	context.bench.create_output(name)


@when(parsers.parse("les réglages du son du poste déplacent l'antenne vers « {name} »"))
def move(context: SimpleNamespace, name: str) -> None:
	stream = context.bench.node(audio.ON_AIR.program, "application.name")
	assert stream is not None
	context.bench.move(stream, name)
	time.sleep(CALM)


@then(parsers.re(r"(?:l'antenne|la sortie sans verrou) est reliée à « (?P<name>[^»]+) »"))
def linked(context: SimpleNamespace, name: str) -> None:
	bench = context.bench
	assert bench._wait(lambda: bench.linked_to(context.program) == {name}), bench.linked_to(context.program)


@then("l'antenne n'est reliée à rien")
def linked_to_nothing(context: SimpleNamespace) -> None:
	time.sleep(CALM)
	assert context.bench.linked_to(context.program) == set()


@then("l'antenne joue toujours")
def plays_always(context: SimpleNamespace) -> None:
	"""Ni erreur, ni flux détruit : WirePlumber attend le périphérique, sans envoyer « defined target not found ». Le
	processus qui joue tourne encore, sans avoir rien écrit d'autre que « prêt »."""
	(player,) = context.players
	assert player.poll() is None
	assert player.stdout is not None
	readable, _writable, _exceptional = select.select([player.stdout], [], [], 0)
	assert readable == [], player.stdout.readline()
	assert context.bench.node(context.program, "application.name") is not None


scenarios("locked_output.feature")
