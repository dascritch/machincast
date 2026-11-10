"""Scénarios de l'interface qui joint l'antenne sur le PipeWire du service (https://github.com/dascritch/machincast/issues/381).

Le service et la session ont chacun leur PipeWire à part, avec WirePlumber (tests/test_locked_output.py), dans des
répertoires temporaires : jamais ceux du poste. Machin player joue dans celui du service (tests/pipewire_player.py) ;
l'écoute se fait dans des processus à part, sans l'environnement du PipeWire du service, qu'ils joignent par
MACHINCAST_SERVICE_RUNTIME (tests/pipewire_levels.py, tests/pipewire_on_air_preview.py). Sans pipewire ni
wireplumber, ces scénarios sont ignorés.
"""

import os
import socket
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import audio, service, service_mixer
from machincast.configuration import Audio, default_state_socket
from machincast.interface import monitor, sound_cards
from machincast.player.state import StateSocket
from machincast.service import ServiceState
from tests.test_locked_output import PipeWireBench, _pipewire_present, _stop

scenarios("service_pipewire.feature")


@pytest.fixture
def context() -> Iterator[SimpleNamespace]:
	context = SimpleNamespace(
		service=None, session=None, players=[], socket=None, refused=None, result=None, error=None
	)
	yield context
	if context.socket is not None:
		context.socket.shut_down()
	if context.refused is not None:
		context.refused.close()


@pytest.fixture
def benches(context: SimpleNamespace) -> Iterator[list[PipeWireBench]]:
	"""Les sons s'arrêtent avant les PipeWire : une sortie dont le serveur a disparu ne s'arrêterait plus."""
	if not _pipewire_present():
		pytest.skip("pipewire ou wireplumber absent")
	started: list[PipeWireBench] = []
	with tempfile.TemporaryDirectory(prefix="machincast-") as root:
		# Un chemin court : celui d'une socket Unix ne dépasse pas 107 octets, et celui de tmp_path est long.
		context.root = Path(root)
		yield started
		_halt(context, started)


def _halt(context: SimpleNamespace, started: list[PipeWireBench]) -> None:
	for player in context.players:
		if player.poll() is None:
			_stop(player)
	for bench in started:
		bench.halt()


def _session(tmp_path: Path, context: SimpleNamespace) -> dict[str, str]:
	"""L'environnement d'une session : son PipeWire s'il y en a un, sinon aucun ; celui du service par
	MACHINCAST_SERVICE_RUNTIME."""
	environment = dict(os.environ)
	for name in (
		"PIPEWIRE_REMOTE",
		"PIPEWIRE_CORE",
		"PIPEWIRE_RUNTIME_DIR",
		"PULSE_SERVER",
		"DBUS_SESSION_BUS_ADDRESS",
	):
		environment.pop(name, None)
	if context.session is not None:
		environment = dict(context.session.env)
	else:
		empty = tmp_path / "session"
		empty.mkdir(mode=0o700, exist_ok=True)
		environment["XDG_RUNTIME_DIR"] = str(empty)
		environment["PIPEWIRE_RUNTIME_DIR"] = str(empty)
	environment[service.RUNTIME_ENVIRONMENT] = context.service.env["PIPEWIRE_RUNTIME_DIR"]
	return environment


def _play(context: SimpleNamespace, command: list[str], environment: dict[str, str]) -> None:
	player = subprocess.Popen(command, env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
	context.players.append(player)
	assert player.stdout is not None
	assert player.stdout.readline().strip() == "prêt"


# ─── Socket d'état ─────────────────────────────────────────


@given("un poste sans service de diffusion")
def without_service(service_runtime: Path) -> None:
	assert not service_runtime.exists()


@then(parsers.parse("la socket d'état par défaut est « {name} » du répertoire d'exécution du compte"))
def state_socket_of_account(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str) -> None:
	monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "compte"))
	assert default_state_socket() == tmp_path / "compte" / name


@given("le répertoire d'exécution du service, au groupe, en mode 2770")
def service_directory(service_runtime: Path) -> None:
	service_runtime.mkdir()
	os.chmod(service_runtime, 0o2770)


@when("Machin player ouvre sa socket d'état par défaut")
def open_state_socket(context: SimpleNamespace) -> None:
	context.socket = StateSocket(default_state_socket())
	context.socket.open_()


@then(parsers.parse("la socket d'état est « {name} » du répertoire du service, en mode {mode}"))
def state_socket_of_service(context: SimpleNamespace, service_runtime: Path, name: str, mode: str) -> None:
	path = service_runtime / name
	assert context.socket.path == path
	assert stat.S_ISSOCK(path.stat().st_mode)
	assert stat.S_IMODE(path.stat().st_mode) == int(mode, 8)


@then(parsers.parse("le répertoire du service garde son mode {mode}"))
def service_directory_mode(service_runtime: Path, mode: str) -> None:
	assert stat.S_IMODE(service_runtime.stat().st_mode) == int(mode, 8)


# ─── PipeWire du service ───────────────────────────────────


@given(parsers.parse("un PipeWire à part pour le service, avec la carte « {card} », où Machin player joue"))
def service_pipewire(context: SimpleNamespace, benches: list[PipeWireBench], card: str) -> None:
	root = context.root / "service"
	root.mkdir()
	bench = PipeWireBench(root)
	bench.start()
	benches.append(bench)
	bench.create_output(card)
	context.service = bench
	assert card == "antenne", "tests.pipewire_player joue sur « antenne »"
	_play(context, [sys.executable, "-m", "tests.pipewire_player", "antenne"], bench.env)
	assert bench._wait(lambda: card in bench.linked_to(audio.ON_AIR.program))


@given(parsers.parse("un PipeWire à part pour la session, avec la carte « {card} »"))
def session_pipewire(context: SimpleNamespace, benches: list[PipeWireBench], card: str) -> None:
	root = context.root / "session"
	root.mkdir()
	bench = PipeWireBench(root)
	bench.start()
	benches.append(bench)
	bench.create_output(card)
	bench.default(card)
	context.session = bench


@when(parsers.parse("le port de monitoring de l'antenne « {card} » est écouté depuis une session sans PipeWire"))
def listened(tmp_path: Path, context: SimpleNamespace, card: str) -> None:
	context.result = subprocess.run(
		[sys.executable, "-m", "tests.pipewire_levels", "pipewire", card],
		env=_session(tmp_path, context),
		capture_output=True,
		text=True,
		timeout=30,
		check=False,
	)


@then(parsers.parse("il relève un son au-dessus de {threshold:g} dB"))
def heard(context: SimpleNamespace, threshold: float) -> None:
	assert context.result.returncode == 0, context.result.stderr
	assert float(context.result.stdout.strip()) > threshold, context.result


@when(parsers.parse("la pré-écoute de l'interface écoute l'antenne « {on_air} » sur « {preview} »"))
def preview_on_air(tmp_path: Path, context: SimpleNamespace, on_air: str, preview: str) -> None:
	command = [sys.executable, "-m", "tests.pipewire_on_air_preview", on_air, preview]
	_play(context, command, _session(tmp_path, context))


@then(parsers.parse("le flux de la pré-écoute joue sur « {card} » dans le PipeWire de la session"))
def preview_plays(context: SimpleNamespace, card: str) -> None:
	session = context.session
	assert session._wait(lambda: session.linked_to(audio.PREVIEW.program) == {card}), session.objects()


@when("les cartes de l'antenne sont listées depuis une session sans PipeWire")
def list_cards(tmp_path: Path, context: SimpleNamespace) -> None:
	program = "from machincast import audio\nfor d in audio.on_air_devices('pipewire'):\n\tprint(d.identifier)"
	context.result = subprocess.run(
		[sys.executable, "-c", program],
		env=_session(tmp_path, context),
		capture_output=True,
		text=True,
		timeout=30,
		check=False,
	)


@then(parsers.parse("la liste a « {card} »"))
def listed(context: SimpleNamespace, card: str) -> None:
	assert context.result.returncode == 0, context.result.stderr
	assert card in context.result.stdout.split(), context.result.stdout


TEST_SOUND = """
import sys
from machincast import service
from machincast.interface.sound_cards import Gst, sample_sound
connection = service.connect_pipewire()
pipeline = sample_sound("pipewire", sys.argv[1], connection)
pipeline.set_state(Gst.State.PLAYING)
print("prêt", flush=True)
sys.stdin.read()
pipeline.set_state(Gst.State.NULL)
"""


@when(parsers.parse("le son de test de la carte de l'antenne « {card} » est lancé depuis une session sans PipeWire"))
def trial_sound(tmp_path: Path, context: SimpleNamespace, card: str) -> None:
	_play(context, [sys.executable, "-c", TEST_SOUND, card], _session(tmp_path, context))


@then(parsers.parse("le son de test joue sur « {card} » dans le PipeWire du service"))
def trial_sound_plays(context: SimpleNamespace, card: str) -> None:
	bench = context.service
	assert bench._wait(lambda: bench.linked_to(sound_cards.TEST_SOUND.program) == {card}), bench.objects()


# ─── Service injoignable ───────────────────────────────────


@given("un service dont le PipeWire refuse la connexion")
def refused(context: SimpleNamespace, service_runtime: Path) -> None:
	"""Une socket liée qui n'écoute pas : connect() est refusé, comme pour un compte hors du groupe."""
	service_runtime.mkdir()
	context.refused = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	context.refused.bind(str(service_runtime / service.PIPEWIRE_SOCKET))


@when(parsers.parse("le port de monitoring de l'antenne « {card} » s'ouvre"))
def opens(context: SimpleNamespace, card: str) -> None:
	try:
		monitor.monitor_source(Audio(output="pipewire", device=card, preview="casque"))
	except monitor.Unavailable as error:
		context.error = str(error)


@then(parsers.parse("il est indisponible : « {text} »"))
def unavailable(context: SimpleNamespace, text: str) -> None:
	assert (context.error is not None) and (text in context.error), context.error


@then(parsers.parse("le port de monitoring de l'antenne « {card} » se nomme « {name} »"))
def named(card: str, name: str) -> None:
	assert monitor.port_name(Audio(output="pipewire", device=card, preview="casque")) == name


# ─── Niveau de l'antenne ───────────────────────────────────


def _reach_service(context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Le processus du scénario joint le PipeWire du service à part, comme l'interface joint /run/machincast."""
	monkeypatch.setenv(service.RUNTIME_ENVIRONMENT, context.service.env["PIPEWIRE_RUNTIME_DIR"])


@given(parsers.parse("le niveau de la carte de l'antenne « {card} » réglé à {percent:d} %"))
def level_set(context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, card: str, percent: int) -> None:
	_reach_service(context, monkeypatch)
	service_mixer.set_volume(card, percent / 100)
	service_mixer.set_muted(card, False)


@when(parsers.parse("le niveau de la carte de l'antenne « {card} » est réglé à {percent:d} %, sourdine mise"))
def level_and_mute(context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, card: str, percent: int) -> None:
	_reach_service(context, monkeypatch)
	service_mixer.set_volume(card, percent / 100)
	service_mixer.set_muted(card, True)


@when(parsers.parse("la sourdine de la carte de l'antenne « {card} » est levée"))
def unmute(context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, card: str) -> None:
	_reach_service(context, monkeypatch)
	service_mixer.set_muted(card, False)


@then(
	parsers.re(
		r"le PipeWire du service a la carte « (?P<card>[^»]+) » à (?P<percent>\d+) %, (?P<state>en sourdine|sans sourdine)"
	)
)
def card_level(context: SimpleNamespace, qtbot: QtBot, card: str, percent: str, state: str) -> None:
	expected = (int(percent), state == "en sourdine")

	def found() -> tuple[int, bool]:
		level = service_mixer.level(card)
		return round(level.volume * 100), level.muted

	# La page règle le niveau après un court délai : le scénario l'attend.
	qtbot.waitUntil(lambda: found() == expected, timeout=3000)


def _page(
	context: SimpleNamespace, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, state: ServiceState, card: str
) -> None:
	"""La page Audio, ses listes de cartes réduites à la carte de l'antenne et au casque, sans moniteur de
	périphériques : seul le niveau joint le PipeWire du service."""
	cards = [audio.Device(card, card), audio.Device("casque", "casque")]
	monkeypatch.setattr(audio, "devices", lambda _output: cards)
	monkeypatch.setattr(audio, "on_air_devices", lambda _output: cards)
	context.page = sound_cards.SoundCards("pipewire", card, "casque", state)
	qtbot.addWidget(context.page)


@when(parsers.parse("la page Audio s'ouvre en mode service, l'antenne sur « {card} »"))
def page_service(context: SimpleNamespace, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, card: str) -> None:
	_reach_service(context, monkeypatch)
	_page(context, qtbot, monkeypatch, ServiceState(installed=True, active="active"), card)


@when(parsers.parse("la page Audio s'ouvre sans service, l'antenne sur « {card} »"))
def page_without(context: SimpleNamespace, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, card: str) -> None:
	_page(context, qtbot, monkeypatch, service.ABSENT, card)


@then(parsers.re(r"la page montre le niveau de l'antenne à (?P<percent>\d+) %, (?P<state>en sourdine|sans sourdine)"))
def page_level(context: SimpleNamespace, percent: str, state: str) -> None:
	ui = context.page.ui
	assert not ui.on_air_level.isHidden()
	assert ui.on_air_level.isEnabled(), ui.on_air_level.toolTip()
	assert (ui.on_air_level.value(), ui.on_air_mute.isChecked()) == (int(percent), state == "en sourdine")
	assert ui.on_air_level_value.text() == f"{percent} %"


@when(parsers.parse("je règle le niveau de l'antenne à {percent:d} % et coche « Muet »"))
def page_set(context: SimpleNamespace, percent: int) -> None:
	ui = context.page.ui
	ui.on_air_level.setValue(percent)
	ui.on_air_mute.setChecked(True)


@then("la page ne montre pas le niveau de l'antenne")
def page_hidden(context: SimpleNamespace) -> None:
	ui = context.page.ui
	for item in (ui.on_air_level_caption, ui.on_air_level, ui.on_air_mute):
		assert item.isHidden()
