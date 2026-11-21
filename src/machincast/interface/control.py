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
import re
import shutil
import signal
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal

from machincast import service
from machincast.clock import Clock, SystemClock
from machincast.configuration import PROJECT_DIRECTORY, InvalidConfiguration, default_file, load
from machincast.i18n import _
from machincast.service import UNIT

VERBS = {
	"start": (_("Start the broadcast"), _("Broadcast started."), _("Broadcast not started")),
	"stop": (_("Stop the broadcast"), _("Broadcast stopped."), _("Broadcast not stopped")),
}
"""Pour chaque verbe de systemctl : l'entrée du menu, ce qu'annonce sa réussite, et son échec."""
RESTART = (_("Broadcast restarted."), _("Broadcast not restarted"))
"""Ce qu'annonce un redémarrage, demandé par les paramètres du service (https://github.com/dascritch/machincast/issues/389) :
sa réussite, et son échec ; il n'a pas d'entrée de menu."""
TRIAL = {
	"start": _("Start the trial broadcast"),
	"stop": _("Stop the trial broadcast"),
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
EXPORT = _("Export the database…")
"""L'entrée du menu « Maintenance » (https://github.com/dascritch/machincast/issues/347)."""
EXPORTING = _("Database export in progress, into {directory}…")
EXPORTED = _("Database exported into {directory}.")
EXPORT_FAILED = _("Database export impossible: {error}")
MACHIN = PROJECT_DIRECTORY / "bin" / "Machin"
"""Le wrapper que l'export lance ; les scénarios en donnent un imité."""
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\S+ ")
"""L'horodatage qui ouvre chaque ligne du journal d'un binaire (machincast.log)."""
GRANT_READ = _("Give the broadcast service the right to read the sound files…")
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
	restarted = Signal(bool)
	"""systemctl restart a réussi, ou échoué : authentification refusée, service qui ne redémarre pas."""
	not_started = Signal(str, list)
	"""Le service a démarré, mais Machin player s'est arrêté aussitôt : ce qu'il en est, et les dernières lignes du
	journal du service (https://github.com/dascritch/machincast/issues/376)."""

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self._process: list[QProcess] = []
		self._started_at = CLOCK.now()

	def control(self, verb: str) -> None:
		"""systemctl <verbe> machincast.service, sans attendre : l'authentification peut prendre du temps."""
		process = systemctl(self, [verb, UNIT])
		self._process.append(process)
		process.finished.connect(lambda code, _status: self._end(process, verb, code))
		self._started_at = CLOCK.now()
		process.start()

	def _end(self, process: QProcess, verb: str, code: int) -> None:
		self._process.remove(process)
		if code != 0:
			said = bytes(process.readAllStandardError().data()).decode("utf-8", "replace")
			if without_agent(said):
				self._in_terminal(verb)
				return
			process.setProperty("said", said)
		self._report(process, verb, code)

	def _in_terminal(self, verb: str) -> None:
		"""Sans agent graphique (ssh -X, su) : la même commande dans une fenêtre de terminal, où systemctl demande le
		mot de passe ; le service suivi jusqu'à ce qu'il change (https://github.com/dascritch/machincast/issues/558)."""
		before = service.invocation()
		if not authenticate_in_terminal([verb, UNIT]):
			self.finished.emit(NO_AUTHENTICATION.format(verb=verb, unit=UNIT))
			self._unrestarted(verb)
			return
		self.finished.emit(IN_TERMINAL)
		self._watch(round(AUTHENTICATION_WINDOW / STARTUP_STEP), before, verb)

	def _watch(self, remaining: int, before: str, verb: str) -> None:
		"""Un démarrage se voit à un nouveau démarrage de l'unité ; un arrêt, au service arrêté."""
		changed = (verb == "stop") and (not service.read_startup().running)
		if verb in ("start", "restart"):
			changed = service.invocation() not in ("", before)
		if changed:
			self._started_at = CLOCK.now()
			self._report(None, verb, 0)
			return
		if remaining <= 0:
			self.finished.emit(NO_ANSWER)
			self._unrestarted(verb)
			return
		# Rattachée à l'objet : elle ne part pas s'il est détruit entre-temps.
		QTimer.singleShot(int(STARTUP_STEP * 1000), self, lambda: self._watch(remaining - 1, before, verb))

	def _unrestarted(self, verb: str) -> None:
		"""Un redémarrage sans authentification : les paramètres du service précédents reviennent."""
		if verb == "restart":
			self.restarted.emit(False)

	def _report(self, process: QProcess | None, verb: str, code: int) -> None:
		if verb == "restart":
			success, failure = RESTART
		else:
			_entry, success, failure = VERBS[verb]
		self.finished.emit(self._outcome(process, verb, code, success, failure))
		if (code == 0) and (verb in ("start", "restart")):
			# systemctl réussit dès que Machin player est lancé : il reste à voir s'il tient.
			self._follow(round(STARTUP_WINDOW / STARTUP_STEP))
		if verb == "restart":
			# Après le message de systemctl : les paramètres du service gardés, ou revenus, ont le dernier mot.
			self.restarted.emit(code == 0)

	def _outcome(self, process: QProcess | None, verb: str, code: int, success: str, failure: str) -> str:
		"""Ce qu'annonce la commande finie."""
		if (code == 0) and (verb in ("start", "restart")):
			return STARTING
		if (code == 0) or (process is None):
			return success
		error = str((process.property("said")) or ("")).strip()
		return _("{failure}: {error}").format(failure=failure, error=(error) or (process.errorString()))

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
		QTimer.singleShot(int(STARTUP_STEP * 1000), self, lambda: self._follow(remaining - 1))

	def _not_started(self, startup: service.Startup) -> None:
		text = NOT_STARTED_WITHOUT_CODE
		if (startup.code is not None) and (startup.code != 0):
			text = NOT_STARTED.format(code=startup.code)
		meaning = CODES.get((startup.code) or (0))
		if meaning is not None:
			text = f"{text} {meaning}"
		self.finished.emit(text)
		self.not_started.emit(f"{text} {SEE_LOGS}", service.journal(self._started_at))


IN_TERMINAL = _("No password dialog in this session: the password is asked in a terminal window.")
NO_ANSWER = _("Service unchanged: no authentication in the terminal window.")
NO_AUTHENTICATION = _("No way to ask for the password in this session: run “sudo systemctl {verb} {unit}”.")
INTERACTIVE = "Interactive authentication required"
"""Ce que répond systemctl, en anglais, quand aucun agent polkit ne peut demander le mot de passe : une session à
distance (ssh -X), ou ouverte par su (https://github.com/dascritch/machincast/issues/558)."""
AUTHENTICATION_WINDOW = 120.0
"""Secondes laissées pour s'authentifier dans la fenêtre de terminal, sans agent graphique."""


def systemctl(parent: QObject, arguments: list[str]) -> QProcess:
	"""systemctl, à lancer, dans une session à lui, sans terminal : l'authentification passe par l'agent polkit du
	bureau, jamais par celui, en mode texte, du terminal d'où l'interface a été lancée, que le shell lit aussi
	(https://github.com/dascritch/machincast/issues/558). Ses messages en anglais, pour reconnaître INTERACTIVE."""
	process = QProcess(parent)
	parameters = QProcess.UnixProcessParameters()
	parameters.flags = QProcess.UnixProcessFlag.CreateNewSession
	process.setUnixProcessParameters(parameters)
	environment = QProcessEnvironment.systemEnvironment()
	environment.insert("LC_ALL", "C.UTF-8")
	process.setProcessEnvironment(environment)
	process.setProgram("systemctl")
	process.setArguments(arguments)
	return process


def without_agent(said: str) -> bool:
	"""systemctl n'a trouvé aucun agent pour demander le mot de passe."""
	return INTERACTIVE in said


def authenticate_in_terminal(arguments: list[str]) -> bool:
	"""La même commande, dans une fenêtre de terminal à part, où systemctl demande le mot de passe, en mode texte ;
	False sans terminal."""
	return open_terminal(["systemctl", *arguments])


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
	"""Où la maintenance et l'export lancés par l'interface écriront leur sauvegarde, en chemin absolu : le répertoire
	des sauvegardes de la configuration de l'interface, ou du machincast.toml du répertoire de MachinCast
	(backup.directory, https://github.com/dascritch/machincast/issues/347) ; le répertoire personnel du compte, si elle
	ne se lit pas."""
	file = default_file()
	if configuration is not None:
		file = configuration
	try:
		return load(file.resolve()).backup.directory.absolute()
	except InvalidConfiguration:
		return Path.home()


def launch_maintenance(configuration: Path | None, backups: Path) -> str:
	"""Machin maintenance-db sur la base de l'interface, avec ses sauvegardes dans sauvegardes, dans un terminal
	qui reste ouvert à la fin (https://github.com/dascritch/machincast/issues/127) ; ce qu'en dit la barre d'état."""
	command = [str(PROJECT_DIRECTORY / "bin" / "Machin")]
	if configuration is not None:
		command += ["--config", str(configuration)]
	if open_terminal([*command, "maintenance-db", "--backups", str(backups), "--keep-open"]):
		return LAUNCHED_MAINTENANCE
	return WITHOUT_TERMINAL_FOR_MAINTENANCE


class Export(QObject):
	"""Machin backup-db dans son propre processus, sans terminal : rapide, il ne demande rien
	(https://github.com/dascritch/machincast/issues/347). Sa fin émet finished, avec ce qu'en dit la barre d'état."""

	finished = Signal(str)

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.process: QProcess | None = None
		self.directory = Path()

	def running(self) -> bool:
		return self.process is not None

	def start(self, configuration: Path | None, directory: Path) -> str:
		"""Lance l'export de la base de l'interface dans directory ; ce qu'en dit la barre d'état."""
		arguments = []
		if configuration is not None:
			arguments += ["--config", str(configuration)]
		arguments += ["backup-db", "--backups", str(directory)]
		self.directory = directory
		process = QProcess(self)
		process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
		process.finished.connect(self._finished)
		self.process = process
		process.start(str(MACHIN), arguments)
		return EXPORTING.format(directory=directory)

	def _finished(self, code: int, status: QProcess.ExitStatus) -> None:
		process = self.process
		assert process is not None
		self.process = None
		output = bytes(process.readAll().data()).decode(errors="replace")
		process.deleteLater()
		if (code == 0) and (status == QProcess.ExitStatus.NormalExit):
			self.finished.emit(EXPORTED.format(directory=self.directory))
			return
		error = _("exit code {code}").format(code=code)
		for line in output.splitlines():
			if line.strip():
				error = TIMESTAMP.sub("", line.strip())
		self.finished.emit(EXPORT_FAILED.format(error=error))


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
