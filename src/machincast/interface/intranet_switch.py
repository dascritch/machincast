"""Allumer et éteindre le serveur intranet depuis les paramètres du service
(https://github.com/dascritch/machincast/issues/538, https://github.com/dascritch/machincast/issues/544).

La page « Intranet » écrit intranet.enabled, port et validation dans machincast.toml, puis :

- avec le service installé (install.sh --service), l'unité machincast-intranet.service les prend aussitôt :
  systemctl restart pour l'allumer, ou pour qu'il prenne un nouveau réglage, systemctl stop pour l'éteindre ; la règle
  polkit demande le mot de passe d'un administrateur. systemctl réussit dès que Machin intranet est lancé : l'unité
  est suivie quelques secondes, comme celle de Machin player (https://github.com/dascritch/machincast/issues/376), et
  « allumé » ne s'annonce que si elle tourne encore ; sinon, son code de sortie et la dernière ligne de son journal ;
- sans le service, Machin intranet se lance dans un terminal, comme la diffusion d'essai, sur la configuration de
  l'interface, et l'y garde ouvert s'il s'arrête sur une erreur ; il s'arrête par SIGTERM, comme Ctrl-C, retrouvé par
  le PID qu'il note (machincast.intranet.process). Un nouveau réglage l'arrête, puis le relance.
"""

import os
import signal
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from machincast import service
from machincast.clock import Clock, SystemClock
from machincast.i18n import _
from machincast.interface import control
from machincast.intranet import process
from machincast.service import INTRANET_UNIT

UNIT_FILE = Path("/etc/systemd/system") / INTRANET_UNIT
SWITCHED_ON = _("Intranet server switched on: {addresses}")
SWITCHED_OFF = _("Intranet server switched off.")
STARTING = _("Intranet server starting…")
NOT_SWITCHED = _("Intranet server unchanged: systemctl said “{said}”.")
NOT_STARTED = _("Intranet server not started: Machin intranet stopped, exit code {code}.")
NOT_STARTED_WITHOUT_CODE = _("Intranet server not started: Machin intranet stopped.")
CODES = {
	2: _("Its configuration is invalid."),
	4: _("It is switched off in machincast.toml of the MachinCast directory, which the service reads."),
	127: _("A program is missing: after an update of MachinCast, run ./install.sh again, which updates the service."),
}
"""Ce que veut dire le code de sortie de Machin intranet, ou de Machin qui le lance."""
LAUNCHED = _("Machin intranet launched in a terminal: {addresses}")
WITHOUT_TERMINAL = _("No terminal found (konsole, x-terminal-emulator): run Machin intranet by hand.")
STILL_RUNNING = _("Machin intranet still running (PID {pid}): stop it in its terminal, with Ctrl-C.")
STOP_WINDOW = 10.0
"""Secondes pour que Machin intranet, lancé sans le service, s'arrête à SIGTERM."""
STOP_STEP = 0.1
"""Secondes entre deux regards sur son PID pendant cette attente."""


def command(configuration: Path | None) -> list[str]:
	"""Machin intranet, sur la configuration de l'interface, son terminal gardé ouvert sur une erreur."""
	called = [str(control.MACHIN)]
	if configuration is not None:
		called += ["--config", str(configuration)]
	return [*called, "intranet", "--keep-open"]


class IntranetSwitch(QObject):
	announced = Signal(str)
	"""Ce qu'il advient du serveur, pour la barre d'état."""

	def __init__(
		self,
		parent: QObject | None = None,
		unit_file: Path | None = None,
		configuration: Path | None = None,
		clock: Clock | None = None,
	) -> None:
		super().__init__(parent)
		self.unit_file = unit_file
		self.configuration = configuration
		self.clock = (clock) or (SystemClock())
		self.processes: list[QProcess] = []

	def apply(self, *, enabled: bool, addresses: list[str]) -> None:
		"""Rallume ou éteint le serveur, sans attendre : l'authentification peut prendre du temps."""
		if not ((self.unit_file) or (UNIT_FILE)).exists():
			# Après ce qu'annoncent les paramètres enregistrés, qui viennent juste ensuite.
			QTimer.singleShot(0, lambda: self._by_hand(enabled=enabled, addresses=addresses))
			return
		verb = "stop"
		if enabled:
			verb = "restart"
		started_at = self.clock.now()
		systemctl = QProcess(self)
		self.processes.append(systemctl)
		systemctl.finished.connect(lambda code, _status: self._end(systemctl, code, verb, addresses, started_at))
		systemctl.start("systemctl", [verb, INTRANET_UNIT])

	def _end(self, systemctl: QProcess, code: int, verb: str, addresses: list[str], started_at: datetime) -> None:
		self.processes.remove(systemctl)
		if code != 0:
			said = bytes(systemctl.readAllStandardError().data()).decode("utf-8", "replace").strip()
			self.announced.emit(NOT_SWITCHED.format(said=said))
			return
		if verb == "stop":
			self.announced.emit(SWITCHED_OFF)
			return
		self.announced.emit(STARTING)
		self._follow(round(control.STARTUP_WINDOW / control.STARTUP_STEP), addresses, started_at)

	def _follow(self, remaining: int, addresses: list[str], started_at: datetime) -> None:
		"""Relit l'état de l'unité, encore remaining fois, une fois par control.STARTUP_STEP."""
		startup = service.read_startup(INTRANET_UNIT)
		if (startup.stopped) or ((remaining <= 0) and (not startup.running)):
			self._not_started(startup, started_at)
			return
		if remaining <= 0:
			self.announced.emit(SWITCHED_ON.format(addresses=", ".join(addresses)))
			return
		QTimer.singleShot(int(control.STARTUP_STEP * 1000), lambda: self._follow(remaining - 1, addresses, started_at))

	def _not_started(self, startup: service.Startup, started_at: datetime) -> None:
		parts = [NOT_STARTED_WITHOUT_CODE]
		if (startup.code is not None) and (startup.code != 0):
			parts = [NOT_STARTED.format(code=startup.code)]
		meaning = CODES.get((startup.code) or (0))
		if meaning is not None:
			parts.append(meaning)
		# La dernière ligne de son journal dit le plus souvent pourquoi.
		parts.extend(service.journal(started_at, 1, INTRANET_UNIT)[-1:])
		self.announced.emit(" ".join(parts))

	def _by_hand(self, *, enabled: bool, addresses: list[str]) -> None:
		"""Sans le service : arrête celui qui tourne, puis le relance s'il est allumé."""
		pid = process.running_pid()
		if pid is None:
			self._after_stop(enabled=enabled, addresses=addresses)
			return
		try:
			os.kill(pid, signal.SIGTERM)
		except OSError:
			self._after_stop(enabled=enabled, addresses=addresses)
			return
		self._wait(pid, round(STOP_WINDOW / STOP_STEP), enabled=enabled, addresses=addresses)

	def _wait(self, pid: int, remaining: int, *, enabled: bool, addresses: list[str]) -> None:
		"""Attend que Machin intranet s'arrête, encore remaining fois, une fois par STOP_STEP."""
		if process.running_pid() is None:
			self._after_stop(enabled=enabled, addresses=addresses)
			return
		if remaining <= 0:
			self.announced.emit(STILL_RUNNING.format(pid=pid))
			return
		QTimer.singleShot(
			int(STOP_STEP * 1000), lambda: self._wait(pid, remaining - 1, enabled=enabled, addresses=addresses)
		)

	def _after_stop(self, *, enabled: bool, addresses: list[str]) -> None:
		if not enabled:
			self.announced.emit(SWITCHED_OFF)
			return
		if control.open_terminal(command(self.configuration)):
			self.announced.emit(LAUNCHED.format(addresses=", ".join(addresses)))
			return
		self.announced.emit(WITHOUT_TERMINAL)
