"""Pilotage de la diffusion depuis l'interface (https://github.com/dascritch/machincast/issues/25, spec § 8.11).

Avec le service (install.sh --service, https://github.com/dascritch/machincast/issues/22), démarrer et arrêter
appellent systemctl sur machincast.service, dans un processus à part : la règle polkit du service les
autorise avec l'authentification d'un administrateur, que demande l'agent polkit de la session. Jamais sudo.

Sans le service, l'installation n'est pas définitive, et le menu pilote une diffusion d'essai : Machin player lancé
dans une fenêtre de terminal (konsole, sinon x-terminal-emulator), par la commande du service, sur sa configuration :
la diffusion d'essai sort sur le même périphérique que sortirait le service. L'arrêter
lui envoie SIGTERM, comme Ctrl-C dans ce terminal ; son processus est celui qui répond sur la socket d'état
(StateClient.player_pid). Ce n'est pas « Machin player --simulation », qui ne joue rien.
"""

import os
import shutil
import signal
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from machincast import service
from machincast.clock import Clock, SystemClock
from machincast.configuration import PROJECT_DIRECTORY, default_file
from machincast.i18n import _
from machincast.interface.intents import HALT, START, label
from machincast.maintenance import default_backups
from machincast.service import UNIT

VERBS = {
	"start": (label(START, _("Start the broadcast")), _("Broadcast started."), _("Broadcast not started")),
	"stop": (label(HALT, _("Stop the broadcast")), _("Broadcast stopped."), _("Broadcast not stopped")),
}
"""Pour chaque verbe de systemctl : l'entrée du menu, ce qu'annonce sa réussite, et son échec."""
TRIAL = {
	"start": label(START, _("Start the trial broadcast")),
	"stop": label(HALT, _("Stop the trial broadcast")),
}
"""Les entrées du menu sans le service."""
TERMINALS = ("konsole", "x-terminal-emulator")
"""Les terminaux essayés, dans l'ordre : celui de Kubuntu, puis celui que choisit le poste."""
WITHOUT_TERMINAL = _("No terminal found (konsole, x-terminal-emulator): run Machin player by hand.")
SERVICE_COMMAND = [str(PROJECT_DIRECTORY / "bin" / "Machin"), "player"]
"""Comme l'ExecStart de machincast.service : la diffusion d'essai sort là où sortirait le service."""
LAUNCHED = _("Trial broadcast launched in a terminal: Ctrl-C stops it there.")
MAINTENANCE = _("Database maintenance…")
"""L'entrée du menu « Maintenance » (https://github.com/dascritch/machincast/issues/127)."""
LAUNCHED_MAINTENANCE = _("Database maintenance launched in a terminal: backup, schema check, optimisation.")
ABANDONED_MAINTENANCE = _("Database maintenance abandoned: nothing was launched.")
WITHOUT_TERMINAL_FOR_MAINTENANCE = _(
	"No terminal found (konsole, x-terminal-emulator): run Machin maintenance-db by hand."
)
GRANT_READ = _("Let the broadcast service read the sound files…")
"""L'entrée du menu « Maintenance » (https://github.com/dascritch/machincast/issues/381)."""
LAUNCHED_GRANT_READ = _("Machin grant-read launched in a terminal: the bank directories and the added files.")
WITHOUT_TERMINAL_FOR_GRANT_READ = _("No terminal found (konsole, x-terminal-emulator): run Machin grant-read by hand.")
WITHOUT_SERVICE_ACCOUNT = _("Without the broadcast service, Machin player reads the sound files with your account.")
STARTING = _("Broadcast starting…")
STARTUP_WINDOW = 8.0
"""Secondes pendant lesquelles un service qui vient de démarrer est suivi : Machin player qui s'arrête dans ce délai,
le plus souvent sur une configuration ou une base injoignable, n'a pas démarré la diffusion
(https://github.com/dascritch/machincast/issues/376)."""
STARTUP_STEP = 1.0
"""Secondes entre deux lectures de l'état du service pendant ce suivi."""
CLOCK: Clock = SystemClock()
"""L'heure de la demande, d'où se lit le journal du service."""
NOT_STARTED = _("Broadcast not started: Machin player stopped, exit code {code}.")
NOT_STARTED_WITHOUT_CODE = _("Broadcast not started: Machin player stopped.")
CODES = {
	1: _(
		"The database is unreachable, the audio output unavailable, or another Machin player is already broadcasting."
	),
	2: _(
		"Its configuration or its call is invalid: after an update of MachinCast, run ./install.sh again, which "
		"updates the service."
	),
	127: _("A program is missing: after an update of MachinCast, run ./install.sh again, which updates the service."),
}
"""Ce que veut dire le code de sortie de Machin player, ou de Machin qui le lance (doc/fr/administration)."""
SEE_LOGS = _("Machin logs, in a terminal, tells more.")
REQUESTED_STOP = _("Stop of the trial broadcast requested…")
STOPPED = _("Trial broadcast stopped.")


class Control(QObject):
	finished = Signal(str)
	"""Ce qu'il advient d'une commande : réussite ou échec, avec le message de systemctl."""
	not_started = Signal(str, list)
	"""Le service a démarré, mais Machin player s'est arrêté aussitôt : ce qu'il en est, et les dernières lignes du
	journal du service (https://github.com/dascritch/machincast/issues/376)."""

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self._process: list[QProcess] = []
		self._started_at = CLOCK.now()

	def control(self, verb: str) -> None:
		"""systemctl <verbe> machincast.service, sans attendre : l'authentification peut prendre du temps."""
		process = QProcess(self)
		self._process.append(process)
		process.finished.connect(lambda code, _status: self._end(process, verb, code))
		self._started_at = CLOCK.now()
		process.start("systemctl", [verb, UNIT])

	def _end(self, process: QProcess, verb: str, code: int) -> None:
		self._process.remove(process)
		_entry, success, failure = VERBS[verb]
		if (code == 0) and (verb == "start"):
			# systemctl réussit dès que Machin player est lancé : il reste à voir s'il tient.
			self.finished.emit(STARTING)
			self._follow(round(STARTUP_WINDOW / STARTUP_STEP))
			return
		if code == 0:
			self.finished.emit(success)
			return
		error = bytes(process.readAllStandardError().data()).decode("utf-8", "replace").strip()
		self.finished.emit(_("{failure}: {error}").format(failure=failure, error=(error) or (process.errorString())))

	def _follow(self, remaining: int) -> None:
		"""Relit l'état du service, encore remaining fois, une fois par STARTUP_STEP."""
		startup = service.read_startup()
		if startup.stopped:
			self._not_started(startup)
			return
		if remaining <= 0:
			if startup.running:
				self.finished.emit(VERBS["start"][1])
			else:
				self._not_started(startup)
			return
		QTimer.singleShot(int(STARTUP_STEP * 1000), lambda: self._follow(remaining - 1))

	def _not_started(self, startup: service.Startup) -> None:
		text = NOT_STARTED_WITHOUT_CODE
		if (startup.code is not None) and (startup.code != 0):
			text = NOT_STARTED.format(code=startup.code)
		meaning = CODES.get((startup.code) or (0))
		if meaning is not None:
			text = f"{text} {meaning}"
		self.finished.emit(text)
		self.not_started.emit(f"{text} {SEE_LOGS}", service.journal(self._started_at))


def open_terminal(command: list[str]) -> bool:
	"""La commande, détachée de l'interface, dans le premier terminal trouvé ; False sans terminal."""
	for terminal in TERMINALS:
		path = shutil.which(terminal)
		if path is not None:
			QProcess.startDetached(path, ["-e", *command])
			return True
	return False


def launch_in_terminal(configuration: Path | None, launched: str = LAUNCHED) -> str:
	"""Machin player, détaché, dans le premier terminal trouvé, par la commande même du service : il lit la
	configuration du service, le machincast.toml du répertoire de MachinCast, et diffuse donc sur le même périphérique
	que lui. Ce que la barre d'état en dit : lance, et l'écart avec la configuration de l'interface s'il y en a un."""
	if open_terminal(SERVICE_COMMAND):
		return f"{launched}{_gap(configuration)}"
	return WITHOUT_TERMINAL


def maintenance_backups(configuration: Path | None) -> Path:
	"""Où la maintenance lancée par l'interface écrira sa sauvegarde, en chemin absolu : le répertoire « sauvegardes »
	à côté de la configuration de l'interface, ou du machincast.toml du répertoire de MachinCast."""
	file = default_file()
	if configuration is not None:
		file = configuration
	return default_backups(file.resolve())


def launch_maintenance(configuration: Path | None, backups: Path) -> str:
	"""Machin maintenance-db sur la base de l'interface, avec ses sauvegardes dans sauvegardes, dans un terminal
	qui reste ouvert à la fin (https://github.com/dascritch/machincast/issues/127) ; ce qu'en dit la barre d'état."""
	command = [str(PROJECT_DIRECTORY / "bin" / "Machin")]
	if configuration is not None:
		command += ["--config", str(configuration)]
	if open_terminal([*command, "maintenance-db", "--backups", str(backups), "--keep-open"]):
		return LAUNCHED_MAINTENANCE
	return WITHOUT_TERMINAL_FOR_MAINTENANCE


def launch_grant_read(configuration: Path | None) -> str:
	"""Machin grant-read sur la base de l'interface, dans un terminal qui dit ce qu'il fait, et ce qu'un administrateur
	doit faire pour un répertoire d'un autre compte (https://github.com/dascritch/machincast/issues/381)."""
	command = [str(PROJECT_DIRECTORY / "bin" / "Machin")]
	if configuration is not None:
		command += ["--config", str(configuration)]
	if open_terminal([*command, "grant-read", "--keep-open"]):
		return LAUNCHED_GRANT_READ
	return WITHOUT_TERMINAL_FOR_GRANT_READ


def _gap(configuration: Path | None) -> str:
	of_service = service_configuration()
	if (configuration is None) or (configuration.resolve() == of_service.resolve()):
		return ""
	return _(" It reads {of_service}, like the service, and not {configuration}, the interface's one.").format(
		of_service=of_service, configuration=configuration
	)


def service_configuration() -> Path:
	"""Le fichier que lit le service, lancé sans --config (machincast.installation.systemd_unit)."""
	return default_file()


def halt_player(pid: int) -> str:
	"""SIGTERM, comme Ctrl-C : Machin player termine proprement le passage en cours, puis ferme sa socket d'état."""
	try:
		os.kill(pid, signal.SIGTERM)
	except OSError as error:
		return _("Trial broadcast not stopped: {strerror}").format(strerror=error.strerror)
	return REQUESTED_STOP
