"""Le service de diffusion, machincast.service (https://github.com/dascritch/machincast/issues/22).

Installé sur demande par install.sh --service, il fait tourner Machin player sous son propre compte, machincast, avec
son PipeWire (https://github.com/dascritch/machincast/issues/381). Ce module dit son nom et son état, que lit systemctl
sans aucun droit particulier, et où joindre son PipeWire ; l'interface le pilote
(machincast.interface.control, https://github.com/dascritch/machincast/issues/25), et machincast.installation rédige
son unité et sa règle polkit.
"""

import os
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ACCOUNT = "machincast"
"""Le compte système du service de diffusion, et son groupe (https://github.com/dascritch/machincast/issues/381) : les
mêmes noms dans install.sh."""
ACCOUNT_ENVIRONMENT = "MACHINCAST_SERVICE_ACCOUNT"
"""La variable d'environnement qui le remplace : les scénarios éprouvent la lecture avec un autre compte."""
UNIT = "machincast.service"
"""L'unité systemd du service de lecture, celle que suit « Machin logs » : le même nom dans bin/Machin."""
DELAY = 5
"""Secondes laissées à systemctl pour dire l'état du service."""
RUNTIME = Path("/run/machincast")
"""Le répertoire d'exécution du service (https://github.com/dascritch/machincast/issues/381), au groupe machincast :
la socket de son PipeWire et sa socket d'état. tmpfiles.d le recrée à chaque démarrage du poste."""
RUNTIME_ENVIRONMENT = "MACHINCAST_SERVICE_RUNTIME"
"""La variable d'environnement qui le remplace : les scénarios n'atteignent jamais le service du poste."""
PIPEWIRE_SOCKET = "pipewire-0"


def account() -> str:
	"""Le compte du service : celui de ACCOUNT_ENVIRONMENT, sinon ACCOUNT."""
	return (os.environ.get(ACCOUNT_ENVIRONMENT)) or (ACCOUNT)


def runtime() -> Path:
	"""Le répertoire d'exécution du service : celui de RUNTIME_ENVIRONMENT, sinon RUNTIME."""
	value = os.environ.get(RUNTIME_ENVIRONMENT)
	if value:
		return Path(value)
	return RUNTIME


def shared_runtime() -> bool:
	"""Vrai si le répertoire d'exécution du service existe et que ce compte y écrit : le service, ou un compte de son
	groupe."""
	directory = runtime()
	return (directory.is_dir()) and (os.access(directory, os.W_OK | os.X_OK))


def pipewire_socket() -> Path | None:
	"""La socket du PipeWire du service, s'il tourne ; None sinon."""
	path = runtime() / PIPEWIRE_SOCKET
	if path.is_socket():
		return path
	return None


def connect_pipewire() -> socket.socket | None:
	"""Une connexion au PipeWire du service, pour un élément GStreamer (sa propriété fd) ; None sans PipeWire du
	service. Lève OSError s'il tourne mais ne se joint pas : un compte hors du groupe machincast, ou qui n'a pas rouvert
	sa session depuis qu'il y est entré."""
	path = pipewire_socket()
	if path is None:
		return None
	connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	try:
		connection.connect(str(path))
	except OSError:
		connection.close()
		raise
	return connection


@dataclass(frozen=True)
class ServiceState:
	installed: bool
	active: str
	"""ActiveState de systemd : « active », « inactive », « failed », « activating »…"""

	@property
	def running(self) -> bool:
		return self.active == "active"


ABSENT = ServiceState(installed=False, active="inactive")


def read_state() -> ServiceState:
	"""L'état du service, d'après systemctl ; absent si systemctl manque, échoue ou ne connaît pas l'unité."""
	try:
		output = subprocess.run(
			["systemctl", "show", UNIT, "--property=LoadState,ActiveState"],
			capture_output=True,
			text=True,
			timeout=DELAY,
			check=False,
		)
	except (OSError, subprocess.TimeoutExpired):
		return ABSENT
	# Sans systemd, ou sans l'unité, systemctl ne dit rien sur sa sortie standard : le service est absent.
	line_list = []
	for line in output.stdout.splitlines():
		if "=" in line:
			line_list.append(line.split("=", 1))
	properties = dict(line_list)
	if properties.get("LoadState") != "loaded":
		return ABSENT
	return ServiceState(installed=True, active=properties.get("ActiveState", "inactive"))


@dataclass(frozen=True)
class Startup:
	"""Ce que devient le service après « systemctl start » (https://github.com/dascritch/machincast/issues/376) :
	systemctl réussit dès que Machin player est lancé, même s'il s'arrête aussitôt."""

	active: str
	"""ActiveState : « active », « activating », « failed », « inactive »…"""
	sub: str
	"""SubState : « running », « auto-restart » quand systemd s'apprête à le relancer…"""
	result: str
	"""Result : « success », « exit-code », « signal »…"""
	code: int | None
	"""ExecMainStatus : le code de sortie du dernier Machin player, None tant qu'il n'est pas sorti."""

	@property
	def running(self) -> bool:
		return (self.active == "active") and (self.sub == "running")

	@property
	def stopped(self) -> bool:
		"""Machin player est sorti : en échec, arrêté, ou relancé par systemd après un échec."""
		return (self.active in ("failed", "inactive")) or (self.sub == "auto-restart")


def read_startup() -> Startup:
	"""L'état du service et le code de sortie de son dernier Machin player, d'après systemctl ; arrêté si systemctl
	manque ou échoue."""
	try:
		output = subprocess.run(
			["systemctl", "show", UNIT, "--property=ActiveState,SubState,Result,ExecMainStatus"],
			capture_output=True,
			text=True,
			timeout=DELAY,
			check=False,
		)
	except (OSError, subprocess.TimeoutExpired):
		return Startup(active="inactive", sub="dead", result="", code=None)
	line_list = []
	for line in output.stdout.splitlines():
		if "=" in line:
			line_list.append(line.split("=", 1))
	properties = dict(line_list)
	code = None
	if properties.get("ExecMainStatus", "").isdigit():
		code = int(properties["ExecMainStatus"])
	return Startup(
		active=properties.get("ActiveState", "inactive"),
		sub=properties.get("SubState", ""),
		result=properties.get("Result", ""),
		code=code,
	)


JOURNAL_LINES = 5
"""Les dernières lignes du journal du service montrées après un démarrage manqué."""


def journal(since: datetime, lines: int = JOURNAL_LINES) -> list[str]:
	"""Les dernières lignes du journal du service depuis cet instant ; aucune si journalctl
	manque, échoue, ou si le compte ne peut pas le lire (groupe systemd-journal, que donne install.sh)."""
	try:
		output = subprocess.run(
			[
				"journalctl",
				f"--unit={UNIT}",
				f"--since=@{int(since.timestamp())}",
				f"--lines={lines}",
				"--output=cat",
				"--no-pager",
				"--quiet",
			],
			capture_output=True,
			text=True,
			timeout=DELAY,
			check=False,
		)
	except (OSError, subprocess.TimeoutExpired):
		return []
	if output.returncode != 0:
		return []
	journal = []
	for line in output.stdout.splitlines():
		if line.strip():
			journal.append(line)
	return journal
