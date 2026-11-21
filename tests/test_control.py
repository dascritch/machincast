"""Scénarios du pilotage de la diffusion depuis l'interface (https://github.com/dascritch/machincast/issues/25).

Les étapes de la fenêtre et de ses menus sont dans tests/interface_steps.py. systemctl et le terminal du poste sont
remplacés par des imitations, en tête du PATH : un script qui note ses arguments, et répond selon les variables
d'environnement que règle le scénario.
"""

import os
import subprocess
import sys
import time
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import PROJECT_DIRECTORY, Intranet, load
from machincast.installation import systemd_unit
from machincast.interface import broadcast_status, control, intranet_switch
from machincast.interface.control import service_configuration
from machincast.intranet import process
from machincast.service import INTRANET_UNIT
from tests.interface_steps import Context, configuration_file, window
from tests.waiting import quiet

scenarios("control.feature")

SYSTEMCTL = """#!/bin/sh
echo "$*" >> "${MACHINCAST_TEST_SYSTEMCTL}"
if [ "$1" = show ]; then
	case "$*" in *LoadState*) echo "LoadState=$(cat "${MACHINCAST_TEST_SERVICE}/charge")" ;; esac
	case "$*" in *ActiveState*) echo "ActiveState=$(cat "${MACHINCAST_TEST_SERVICE}/actif")" ;; esac
	case "$*" in *SubState*) echo "SubState=$(cat "${MACHINCAST_TEST_SERVICE}/sous" 2>/dev/null)" ;; esac
	case "$*" in *ExecMainStatus*) echo "ExecMainStatus=$(cat "${MACHINCAST_TEST_SERVICE}/code" 2>/dev/null)" ;; esac
	exit 0
fi
if [ -n "${MACHINCAST_TEST_ERREUR}" ]; then
	echo "${MACHINCAST_TEST_ERREUR}" >&2
	exit 4
fi
case "$1" in
	start | restart)
		echo active > "${MACHINCAST_TEST_SERVICE}/actif"
		echo running > "${MACHINCAST_TEST_SERVICE}/sous"
		if [ -n "${MACHINCAST_TEST_ARRET}" ]; then
			# Machin player lancé, puis aussitôt sorti : « code actif sous ».
			set -- ${MACHINCAST_TEST_ARRET}
			echo "$1" > "${MACHINCAST_TEST_SERVICE}/code"
			echo "$2" > "${MACHINCAST_TEST_SERVICE}/actif"
			echo "$3" > "${MACHINCAST_TEST_SERVICE}/sous"
		fi
		;;
	stop) echo inactive > "${MACHINCAST_TEST_SERVICE}/actif" ;;
esac
"""
"""systemctl imité : « show » donne les propriétés demandées de l'état du service, noté dans deux fichiers ; les
autres verbes le changent, ou échouent avec l'erreur et le code de systemctl pour une autorisation refusée (4)."""
JOURNALCTL = """#!/bin/sh
echo "$*" >> "${MACHINCAST_TEST_JOURNALCTL}.log"
cat "${MACHINCAST_TEST_JOURNALCTL}" 2>/dev/null
"""
"""journalctl imité : il note ses arguments, et répond les lignes du journal que donne le scénario."""
TERMINAL = """#!/bin/sh
if [ -e "${MACHINCAST_TEST_ESSAI}" ]; then echo arrêtée; else echo aucune; fi > "${MACHINCAST_TEST_TERMINAL}.essai"
for argument in "$@"; do
	echo "${argument}"
done > "${MACHINCAST_TEST_TERMINAL}"
"""
"""Un terminal imité : il note ses arguments, un par ligne, et si une diffusion d'essai s'était arrêtée avant."""
TRIAL_PLAYER = """
import signal, sys, time
from pathlib import Path
from machincast.player.state import StateSocket

socket = StateSocket(Path(sys.argv[1]))
socket.open_()
socket.publish({"timestamp": "2026-10-20T16:40:00+02:00", "state": sys.argv[3], "current": None, "next": None})


def stop(_signal_number, _frame):
	# Comme Machin player : un dernier état pendant que le passage en cours se termine, puis la socket se ferme.
	socket.publish({"timestamp": "2026-10-20T16:40:01+02:00", "state": "dead_air", "current": None, "next": None})
	time.sleep(0.5)
	Path(sys.argv[2]).write_text("SIGTERM", encoding="utf-8")
	socket.shut_down()
	sys.exit(0)


signal.signal(signal.SIGTERM, stop)
while True:
	time.sleep(1)
"""
"""Un Machin player lancé à la main : il annonce la diffusion sur sa socket d'état, s'arrête proprement à SIGTERM."""
HAND_INTRANET = """
import signal, sys, time
from pathlib import Path
from machincast.intranet import process


def stop(_signal_number, _frame):
	Path(sys.argv[2]).write_text("SIGTERM", encoding="utf-8")
	sys.exit(0)


signal.signal(signal.SIGTERM, stop)
with process.recorded(Path(sys.argv[1])):
	while True:
		time.sleep(1)
"""
"""Un Machin intranet lancé sans le service : son PID noté, il s'arrête à SIGTERM ; lancé par un script nommé
Machin_intranet, comme le vrai."""
STATES = {"arrêté": "inactive", "en marche": "active", "en échec": "failed"}


class Station:
	def __init__(self, directory: Path) -> None:
		self.commands = directory / "commandes"
		self.commands.mkdir()
		self.systemctl = directory / "systemctl.log"
		self.terminal = directory / "terminal.log"
		self.service = directory / "service"
		self.service.mkdir()
		self.trial: subprocess.Popen[bytes] | None = None
		self.intranet: subprocess.Popen[bytes] | None = None
		self.intranet_state = directory / "intranet"
		self.intranet_stop = directory / "intranet.signal"
		self.trial_stop = directory / "essai.signal"

	def imitate(self, name: str, script: str) -> None:
		path = self.commands / name
		path.write_text(script, encoding="utf-8")
		path.chmod(0o755)

	def set_(self, load: str, active: str) -> None:
		(self.service / "charge").write_text(f"{load}\n", encoding="utf-8")
		(self.service / "actif").write_text(f"{active}\n", encoding="utf-8")

	def calls(self) -> list[str]:
		if not self.systemctl.exists():
			return []
		return self.systemctl.read_text(encoding="utf-8").splitlines()


@pytest.fixture
def station(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Station]:
	fake = Station(tmp_path)
	fake.imitate("systemctl", SYSTEMCTL)
	fake.imitate("journalctl", JOURNALCTL)
	monkeypatch.setenv("MACHINCAST_TEST_JOURNALCTL", str(tmp_path / "journal"))
	monkeypatch.setenv("MACHINCAST_TEST_ARRET", "")
	# Le suivi du démarrage, en dixièmes de seconde (https://github.com/dascritch/machincast/issues/376).
	monkeypatch.setattr(control, "STARTUP_WINDOW", 0.5)
	monkeypatch.setattr(control, "STARTUP_STEP", 0.1)
	monkeypatch.setenv("PATH", f"{fake.commands}{os.pathsep}{os.environ['PATH']}")
	monkeypatch.setenv("MACHINCAST_TEST_SYSTEMCTL", str(fake.systemctl))
	monkeypatch.setenv("MACHINCAST_TEST_TERMINAL", str(fake.terminal))
	monkeypatch.setenv("MACHINCAST_TEST_SERVICE", str(fake.service))
	monkeypatch.setenv("MACHINCAST_TEST_ESSAI", str(fake.trial_stop))
	monkeypatch.setenv("MACHINCAST_TEST_ERREUR", "")
	# Le PID d'un Machin intranet lancé sans le service : jamais celui du compte qui lance les tests.
	monkeypatch.setenv("STATE_DIRECTORY", str(fake.intranet_state))
	yield fake
	for launched in (fake.trial, fake.intranet):
		if launched is not None:
			launched.kill()
			launched.wait()


@given(parsers.re(r"le service de diffusion installé, (?P<state>arrêté|en marche|en échec)"))
def installed_service(station: Station, state: str) -> None:
	station.set_("loaded", STATES[state])


@given("le service de diffusion non installé")
def service_absent(station: Station) -> None:
	station.set_("not-found", "inactive")


@given(parsers.parse("systemctl refuse en disant « {error} »"))
def refusal(monkeypatch: pytest.MonkeyPatch, error: str) -> None:
	monkeypatch.setenv("MACHINCAST_TEST_ERREUR", error)


@given(
	parsers.re(
		r"Machin player qui s'arrête aussitôt lancé par le service, avec le code (?P<code>\d+), le service "
		r"(?P<state>en échec|relancé par systemd)"
	)
)
def immediate_stop(monkeypatch: pytest.MonkeyPatch, code: str, state: str) -> None:
	active, sub = {"en échec": ("failed", "failed"), "relancé par systemd": ("activating", "auto-restart")}[state]
	monkeypatch.setenv("MACHINCAST_TEST_ARRET", f"{code} {active} {sub}")


@given(parsers.parse("le journal du service qui finit par « {line} »"))
def service_journal(tmp_path: Path, line: str) -> None:
	(tmp_path / "journal").write_text(f"Started machincast.service\n{line}\n", encoding="utf-8")


@then(parsers.parse("une alerte dit bientôt « {text} »"))
def alert_soon(interface: Context, qtbot: QtBot, text: str) -> None:
	def said_alone() -> bool:
		said_list = []
		for said, _journal in interface.not_started:
			said_list.append(said)
		return said_list == [text]

	qtbot.waitUntil(said_alone, timeout=5000)


@then(parsers.parse("elle montre en détails les lignes du journal « {first} » et « {second} »"))
def alert_journal(interface: Context, first: str, second: str) -> None:
	said_list = []
	for _said, journal in interface.not_started:
		said_list.append(journal)
	assert said_list == [[first, second]]


@then("aucune alerte ne dit que la diffusion n'a pas démarré")
def no_alert(interface: Context) -> None:
	assert interface.not_started == []


@given(parsers.parse("le terminal « {name} » du poste"))
def terminal(station: Station, name: str) -> None:
	station.imitate(name, TERMINAL)


@given("aucun terminal sur le poste")
def without_terminal(station: Station, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Seules les commandes imitées restent dans le PATH : aucun terminal n'y est."""
	monkeypatch.setenv("PATH", str(station.commands))


@given("la maintenance de la base non confirmée")
def refused_maintenance(interface: Context) -> None:
	interface.maintenance = False


@given(parsers.re(r"une diffusion d'essai qui (?P<doing>tourne|laisse un blanc), lancée à la main"))
def trial_broadcast(interface: Context, station: Station, doing: str) -> None:
	"""Dans un processus à part, sur la socket d'état où l'interface la cherche : c'est lui qu'arrête SIGTERM."""
	socket = interface.directory / "lecture.sock"
	state = {"tourne": "playing", "laisse un blanc": "dead_air"}[doing]
	station.trial = subprocess.Popen([sys.executable, "-c", TRIAL_PLAYER, str(socket), str(station.trial_stop), state])


@when("le service de diffusion passe en marche")
def running(station: Station) -> None:
	station.set_("loaded", "active")


@when("le service de diffusion s'installe, arrêté")
def service_installation(station: Station) -> None:
	"""./install.sh --service, lancé pendant que l'interface est ouverte."""
	station.set_("loaded", "inactive")


@when("l'état du binaire lecture est bientôt « En diffusion » sur l'onglet Antenne")
def broadcast_on_on_air(interface: Context, qtbot: QtBot) -> None:
	caption = window(interface).home.ui.playback_state
	qtbot.waitUntil(lambda: caption.text() == "En diffusion", timeout=5000)


@then(parsers.parse("systemctl a reçu bientôt « {call} »"))
def received_call(station: Station, qtbot: QtBot, call: str) -> None:
	qtbot.waitUntil(lambda: call in station.calls(), timeout=5000)


@then("systemctl n'a reçu que des demandes d'état")
def state_requests(station: Station) -> None:
	calls = station.calls()
	assert calls, calls
	for call in calls:
		assert call.startswith("show "), calls


@then(parsers.parse("la barre d'état annonce bientôt « {text} »"))
def announces_soon(interface: Context, qtbot: QtBot, text: str) -> None:
	bar = window(interface).statusBar()
	qtbot.waitUntil(lambda: bar.currentMessage() == text, timeout=5000)


@then("la barre d'état ne signale pas d'installation à terminer")
def without_signal(interface: Context) -> None:
	assert not window(interface).without_service.isVisibleTo(window(interface))


@then(parsers.parse("la barre d'état signale « {text} », avec l'infobulle « {tooltip} »"))
def signal(interface: Context, text: str, tooltip: str) -> None:
	caption = window(interface).without_service
	assert caption.isVisibleTo(window(interface))
	assert (caption.text(), caption.toolTip()) == (text, tooltip)


@then(parsers.parse("le titre de l'onglet Antenne est « {title} »"))
def on_air_title(interface: Context, title: str) -> None:
	"""Le titre brut, témoin compris : les autres scénarios le lisent sans lui (tab_title)."""
	tabs = window(interface).ui.tabs
	assert tabs.tabText(tabs.indexOf(window(interface).home)) == title


def _status_style(interface: Context) -> str:
	return window(interface).home.ui.playback_state.styleSheet()


@then(
	parsers.parse("l'état de la diffusion est sur fond {background}, en texte {text}, avec un liseré {border} de 2 px")
)
def coloured_status(interface: Context, background: str, text: str, border: str) -> None:
	style = _status_style(interface)
	for part in (f"background-color: {background};", f"color: {text};", f"border: 2px solid {border};"):
		assert part in style, style


@then(
	parsers.parse(
		"l'état de la diffusion devient bientôt « {state} », sans fond coloré, avec un liseré {border} de 2 px"
	)
)
def uncoloured_status(interface: Context, qtbot: QtBot, state: str, border: str) -> None:
	caption = window(interface).home.ui.playback_state
	qtbot.waitUntil(lambda: caption.text() == state, timeout=5000)
	style = _status_style(interface)
	assert f"border: 2px solid {border};" in style, style
	assert "background-color" not in style, style


@then(parsers.parse("le titre de la fenêtre est « {title} »"))
def window_title(interface: Context, qtbot: QtBot, title: str) -> None:
	qtbot.waitUntil(lambda: window(interface).windowTitle() == title, timeout=5000)


@then(parsers.parse("sur le fond {background}, le texte de l'état de la diffusion est {text}"))
def contrasted(background: str, text: str) -> None:
	assert broadcast_status.contrasting_text(background) == text


@then(parsers.parse("la dernière ligne de la fenêtre ne dit pas « {text} »"))
def says_not(interface: Context, text: str) -> None:
	caption = window(interface).stopped_broadcast
	assert caption.text() == text
	assert not caption.isVisibleTo(window(interface))


@then(parsers.parse("la dernière ligne de la fenêtre dit bientôt « {text} »"))
def says_soon(interface: Context, qtbot: QtBot, text: str) -> None:
	"""Un élément permanent de la barre d'état : aucun message ne le recouvre."""
	caption = window(interface).stopped_broadcast
	assert caption.text() == text
	qtbot.waitUntil(lambda: caption.isVisibleTo(window(interface)), timeout=5000)
	assert caption.parent() is window(interface).statusBar()


@then("le terminal a lancé bientôt Machin player, comme le service")
def launches_in_terminal(station: Station, qtbot: QtBot) -> None:
	"""La commande de l'ExecStart de machincast.service, sans --config : la configuration du service."""
	qtbot.waitUntil(station.terminal.exists, timeout=5000)
	arguments = station.terminal.read_text(encoding="utf-8").splitlines()
	assert arguments == ["-e", str(PROJECT_DIRECTORY / "bin" / "Machin"), "player"], arguments
	assert systemd_unit(PROJECT_DIRECTORY).count(f"ExecStart={PROJECT_DIRECTORY}/bin/Machin player\n") == 1


@given("l'interface lancée sur la configuration du service")
def on_service_configuration(interface: Context, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Le machincast.toml du répertoire de MachinCast n'est jamais touché : la copie des tests en tient lieu."""
	copies = configuration_file(interface)
	monkeypatch.setattr(control, "service_configuration", lambda: copies)


@then("la barre d'état annonce que la diffusion d'essai lit la configuration du service, et non celle de l'interface")
def announced_gap(interface: Context) -> None:
	expected = (
		f"{control.LAUNCHED} Elle lit {service_configuration()}, comme le service,"
		f" et non {configuration_file(interface)}, celle de l'interface."
	)
	assert window(interface).statusBar().currentMessage() == expected


@then("la diffusion d'essai s'est arrêtée par SIGTERM")
def stopped_trial(station: Station) -> None:
	assert station.trial is not None
	assert station.trial.wait(timeout=5) == 0
	assert station.trial_stop.read_text(encoding="utf-8") == "SIGTERM"


@then("le terminal a été lancé après l'arrêt de la diffusion d'essai")
def restarts_after_stop(station: Station) -> None:
	trial = station.terminal.with_name(f"{station.terminal.name}.essai")
	assert trial.read_text(encoding="utf-8") == "arrêtée\n"


@given(parsers.parse("l'emplacement « {directory} » choisi pour les sauvegardes de la maintenance"))
def chosen_location(interface: Context, directory: str) -> None:
	interface.chosen_backups = Path(directory)


@then(
	parsers.re(
		r"le terminal a lancé bientôt Machin maintenance-db, sur la configuration de l'interface, avec les sauvegardes"
		r" dans (?:« (?P<backups>[^»]+) »|le répertoire des sauvegardes de sa configuration), le terminal restant ouvert"
	)
)
def maintenance_in_terminal(interface: Context, station: Station, qtbot: QtBot, backups: str | None) -> None:
	"""Sans emplacement choisi, le répertoire des sauvegardes de la configuration de l'interface (backup.directory,
	https://github.com/dascritch/machincast/issues/347)."""
	directory = load(configuration_file(interface).resolve()).backup.directory
	if backups is not None:
		directory = Path(backups)
	qtbot.waitUntil(station.terminal.exists, timeout=5000)
	arguments = station.terminal.read_text(encoding="utf-8").splitlines()
	assert arguments == [
		"-e",
		str(PROJECT_DIRECTORY / "bin" / "Machin"),
		"--config",
		str(configuration_file(interface)),
		"maintenance-db",
		"--backups",
		str(directory),
		"--keep-open",
	], arguments


@then(
	"l'interface a demandé confirmation, avec l'emplacement des sauvegardes : le répertoire des sauvegardes de sa"
	" configuration"
)
def requested_confirmation(interface: Context) -> None:
	expected = load(configuration_file(interface).resolve()).backup.directory
	assert interface.questions == [f"maintenance : {expected}"], interface.questions


@then("le terminal n'a rien lancé")
def launched_nothing(station: Station) -> None:
	"""Le terminal se lance avant que la barre d'état ne le dise : après l'annonce, il n'y a plus rien à attendre."""
	assert not station.terminal.exists()


# ─── Paramètres du service (https://github.com/dascritch/machincast/issues/389) ───


@given("le fichier de configuration de l'interface noté tel qu'il est", target_fixture="noted_configuration")
def noted_configuration(interface: Context) -> str:
	return configuration_file(interface).read_text(encoding="utf-8")


@given(parsers.parse("les préférences régleront seulement la pré-écoute « {preview} »"))
def only_preview(interface: Context, preview: str) -> None:
	interface.audio_settings = (None, preview, None)  # type: ignore[assignment]


@then(parsers.re(r"la fenêtre ouverte est celle (?P<kind>des paramètres du service|des préférences de l'interface)"))
def opened_kind(interface: Context, kind: str) -> None:
	expected = "service"
	if kind == "des préférences de l'interface":
		expected = "interface"
	assert interface.shown_kinds == [expected]


def _audio(interface: Context) -> dict[str, object]:
	audio = tomllib.loads(configuration_file(interface).read_text(encoding="utf-8"))["audio"]
	assert isinstance(audio, dict)
	return audio


@then(parsers.parse("le fichier de configuration donne l'antenne « {device} »"))
def configured_on_air(interface: Context, device: str) -> None:
	assert _audio(interface).get("device") == device


@then(parsers.parse("le fichier de configuration donne la pré-écoute « {preview} »"))
def configured_preview(interface: Context, preview: str) -> None:
	assert _audio(interface).get("preview") == preview


@then("le fichier de configuration est revenu tel qu'il était")
def configuration_back(interface: Context, noted_configuration: str) -> None:
	assert configuration_file(interface).read_text(encoding="utf-8") == noted_configuration


@then("l'interface n'a pas d'antenne réglée")
def no_on_air(interface: Context) -> None:
	assert window(interface).audio.device is None


# ─── Export de la base (https://github.com/dascritch/machincast/issues/347) ───


@given(parsers.re(r"l'export de la base qui (?:réussit|échoue avec « (?P<error>[^»]+) »)"))
def database_export(station: Station, monkeypatch: pytest.MonkeyPatch, error: str | None) -> None:
	"""Un Machin imité, qui note ses arguments, un par ligne, et répond comme Machin backup-db : son journal sur la
	sortie d'erreur, chaque ligne horodatée. La base de production n'est jamais atteinte."""
	machin = station.commands.parent / "Machin"
	exported = station.commands.parent / "export.log"
	lines = ["#!/bin/bash", f': >"{exported}"', f'for argument; do echo "$argument" >>"{exported}"; done', "sleep 0.3"]
	if error is not None:
		lines += [f"echo '2026-11-17T13:00:00+01:00 {error}' >&2", "exit 1"]
	machin.write_text("\n".join(lines) + "\n", encoding="utf-8")
	machin.chmod(0o755)
	monkeypatch.setattr(control, "MACHIN", machin)


@then("la barre d'état annonce bientôt la base exportée dans le répertoire des sauvegardes de sa configuration")
def exported_announced(interface: Context, qtbot: QtBot) -> None:
	directory = load(configuration_file(interface).resolve()).backup.directory.absolute()
	text = f"Base exportée dans {directory}."
	bar = window(interface).statusBar()
	qtbot.waitUntil(lambda: bar.currentMessage() == text, timeout=5000)


@then(
	"l'export a lancé Machin backup-db sur la configuration de l'interface, dans le répertoire des sauvegardes de sa"
	" configuration"
)
def export_launched(interface: Context, station: Station) -> None:
	directory = load(configuration_file(interface).resolve()).backup.directory.absolute()
	arguments = (station.commands.parent / "export.log").read_text(encoding="utf-8").splitlines()
	assert arguments == ["--config", str(configuration_file(interface)), "backup-db", "--backups", str(directory)]


# ─── Serveur intranet (https://github.com/dascritch/machincast/issues/538) ───


@given(parsers.re(r"l'unité du serveur intranet (?P<state>installée|non installée)"))
def intranet_unit(station: Station, monkeypatch: pytest.MonkeyPatch, state: str) -> None:
	unit = station.commands.parent / INTRANET_UNIT
	if state == "installée":
		unit.write_text("[Unit]\n", encoding="utf-8")
	monkeypatch.setattr(intranet_switch, "UNIT_FILE", unit)


@given(parsers.re(r"les paramètres du service allumeront l'intranet sur « (?P<address>[^»]+) », port (?P<port>\d+)"))
def switch_on(interface: Context, address: str, port: str) -> None:
	interface.adjusted_intranet = Intranet(enabled=True, address=address, port=int(port))


@given("les paramètres du service éteindront l'intranet")
def switch_off(interface: Context) -> None:
	interface.adjusted_intranet = Intranet(enabled=False)


@given("le fichier de configuration de l'interface allume l'intranet")
def configured_on(interface: Context) -> None:
	path = configuration_file(interface)
	path.write_text(path.read_text(encoding="utf-8") + "\n[intranet]\nenabled = true\n", encoding="utf-8")


@then(parsers.parse("le fichier de configuration allume l'intranet, sur le port {port:d}"))
def configured_intranet(interface: Context, port: int) -> None:
	intranet = load(configuration_file(interface)).intranet
	assert (intranet.enabled, intranet.port) == (True, port)


@then(parsers.parse("systemctl n'a pas reçu « {call} »"))
def not_received(station: Station, qtbot: QtBot, call: str) -> None:
	quiet(qtbot, 200, reason="systemctl, que lancerait l'interrupteur de l'intranet")
	assert call not in station.calls()


# ─── Serveur intranet sans le service (https://github.com/dascritch/machincast/issues/544) ───


@given(parsers.parse("Machin intranet qui s'arrête aussitôt lancé par son unité, avec le code {code:d}"))
def intranet_immediate_stop(monkeypatch: pytest.MonkeyPatch, code: int) -> None:
	monkeypatch.setenv("MACHINCAST_TEST_ARRET", f"{code} failed failed")


@given(parsers.parse("le journal de l'unité du serveur intranet qui finit par « {line} »"))
def intranet_journal(tmp_path: Path, line: str) -> None:
	(tmp_path / "journal").write_text(f"Started machincast-intranet.service\n{line}\n", encoding="utf-8")


@given("un Machin intranet lancé sans le service")
def hand_intranet(station: Station, qtbot: QtBot) -> None:
	# Un script nommé comme l'exécutable de Machin intranet : c'est ainsi qu'il se reconnaît
	# (https://github.com/dascritch/machincast/issues/550).
	script = station.commands.parent / process.EXECUTABLE
	script.write_text(HAND_INTRANET, encoding="utf-8")
	station.intranet = subprocess.Popen(
		[sys.executable, str(script), str(station.intranet_state), str(station.intranet_stop)]
	)
	qtbot.waitUntil(lambda: process.running_pid() == station.intranet.pid, timeout=5000)  # type: ignore[union-attr]


@given("un PID resté d'un Machin intranet arrêté brutalement")
def stale_pid(station: Station) -> None:
	ended = subprocess.Popen([sys.executable, "-c", "pass"])
	ended.wait()
	station.intranet_state.mkdir(parents=True, exist_ok=True)
	(station.intranet_state / process.PID_FILE).write_text(f"{ended.pid}\n", encoding="utf-8")
	assert process.running_pid() is None


@then("le Machin intranet lancé sans le service a reçu SIGTERM, et ne tourne plus")
def hand_intranet_stopped(station: Station, qtbot: QtBot) -> None:
	launched = station.intranet
	assert launched is not None
	qtbot.waitUntil(lambda: launched.poll() is not None, timeout=5000)
	assert station.intranet_stop.read_text(encoding="utf-8") == "SIGTERM"
	assert process.running_pid() is None


@then("le terminal a lancé bientôt Machin intranet sur la configuration de l'interface, gardé ouvert sur une erreur")
def intranet_in_terminal(interface: Context, station: Station, qtbot: QtBot) -> None:
	qtbot.waitUntil(station.terminal.exists, timeout=5000)
	arguments = station.terminal.read_text(encoding="utf-8").splitlines()
	expected = ["-e", str(control.MACHIN), "--config", str(configuration_file(interface)), "intranet", "--keep-open"]
	assert arguments == expected


SLEEPER = "import time\nwhile True:\n\ttime.sleep(1)\n"


@given(
	parsers.re(
		r"(?P<kind>un éditeur ouvert sur « (?P<file>[^»]+) »|un Machin intranet démarré une heure après l'écriture du"
		r" fichier de son PID), dont le PID est resté dans le répertoire d'état de l'intranet"
	)
)
def reused_pid(station: Station, kind: str, file: str | None) -> None:
	"""https://github.com/dascritch/machincast/issues/550"""
	command = [sys.executable, "-c", SLEEPER, str(file)]
	if file is None:
		# Lancé comme Machin intranet, mais après l'écriture du fichier : ce PID-là n'est pas le sien.
		script = station.commands.parent / process.EXECUTABLE
		script.write_text(SLEEPER, encoding="utf-8")
		command = [sys.executable, str(script)]
	station.intranet = subprocess.Popen(command)
	station.intranet_state.mkdir(parents=True, exist_ok=True)
	recorded = station.intranet_state / process.PID_FILE
	recorded.write_text(f"{station.intranet.pid}\n", encoding="utf-8")
	if file is None:
		hour_ago = time.time() - 3600
		os.utime(recorded, (hour_ago, hour_ago))
	assert process.running_pid() is None, kind


@then("ce programme tourne toujours")
def still_running(station: Station) -> None:
	assert station.intranet is not None
	assert station.intranet.poll() is None
