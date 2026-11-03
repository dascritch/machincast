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

from PySide6.QtCore import QObject, QProcess, Signal

from machincast.configuration import PROJECT_DIRECTORY, default_file
from machincast.interface.intents import HALT, START, label
from machincast.maintenance import default_backups
from machincast.service import UNIT

VERBS = {
	"start": (label(START, "Démarrer la diffusion"), "Diffusion démarrée.", "Diffusion non démarrée"),
	"stop": (label(HALT, "Arrêter la diffusion"), "Diffusion arrêtée.", "Diffusion non arrêtée"),
}
"""Pour chaque verbe de systemctl : l'entrée du menu, ce qu'annonce sa réussite, et son échec."""
TRIAL = {
	"start": label(START, "Démarrer la diffusion d'essai"),
	"stop": label(HALT, "Arrêter la diffusion d'essai"),
}
"""Les entrées du menu sans le service."""
TERMINALS = ("konsole", "x-terminal-emulator")
"""Les terminaux essayés, dans l'ordre : celui de Kubuntu, puis celui que choisit le poste."""
WITHOUT_TERMINAL = "Aucun terminal trouvé (konsole, x-terminal-emulator) : lancer Machin player à la main."
SERVICE_COMMAND = [str(PROJECT_DIRECTORY / "bin" / "Machin"), "player"]
"""Comme l'ExecStart de machincast.service : la diffusion d'essai sort là où sortirait le service."""
LAUNCHED = "Diffusion d'essai lancée dans un terminal : Ctrl-C l'y arrête."
MAINTENANCE = "Maintenance de la base de données…"
"""L'entrée du menu « Maintenance » (https://github.com/dascritch/machincast/issues/127)."""
LAUNCHED_MAINTENANCE = (
	"Maintenance de la base de données lancée dans un terminal : sauvegarde, vérification du schéma, optimisation."
)
ABANDONED_MAINTENANCE = "Maintenance de la base de données abandonnée : rien n'a été lancé."
WITHOUT_TERMINAL_FOR_MAINTENANCE = (
	"Aucun terminal trouvé (konsole, x-terminal-emulator) : lancer Machin maintenance-db à la main."
)
REQUESTED_STOP = "Arrêt de la diffusion d'essai demandé…"
STOPPED = "Diffusion d'essai arrêtée."


class Control(QObject):
	finished = Signal(str)
	"""Ce qu'il advient d'une commande : réussite ou échec, avec le message de systemctl."""

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self._process: list[QProcess] = []

	def control(self, verb: str) -> None:
		"""systemctl <verbe> machincast.service, sans attendre : l'authentification peut prendre du temps."""
		process = QProcess(self)
		self._process.append(process)
		process.finished.connect(lambda code, _status: self._end(process, verb, code))
		process.start("systemctl", [verb, UNIT])

	def _end(self, process: QProcess, verb: str, code: int) -> None:
		self._process.remove(process)
		_entry, success, failure = VERBS[verb]
		if code == 0:
			self.finished.emit(success)
			return
		error = bytes(process.readAllStandardError().data()).decode("utf-8", "replace").strip()
		self.finished.emit(f"{failure} : {(error) or (process.errorString())}")


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


def _gap(configuration: Path | None) -> str:
	of_service = service_configuration()
	if (configuration is None) or (configuration.resolve() == of_service.resolve()):
		return ""
	return f" Elle lit {of_service}, comme le service, et non {configuration}, celle de l'interface."


def service_configuration() -> Path:
	"""Le fichier que lit le service, lancé sans --config (machincast.installation.systemd_unit)."""
	return default_file()


def halt_player(pid: int) -> str:
	"""SIGTERM, comme Ctrl-C : Machin player termine proprement le passage en cours, puis ferme sa socket d'état."""
	try:
		os.kill(pid, signal.SIGTERM)
	except OSError as error:
		return f"Diffusion d'essai non arrêtée : {error.strerror}"
	return REQUESTED_STOP
