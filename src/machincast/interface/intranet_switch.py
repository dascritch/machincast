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
from machincast.service import INTRANET_UNIT, INTRANET_UNIT_FILE

UNIT_FILE = INTRANET_UNIT_FILE
SWITCHED_ON = _("Intranet server switched on: {addresses}")
SWITCHED_OFF = _("Intranet server switched off.")
STARTING = _("Intranet server starting…")
NOT_SWITCHED = _("Intranet server unchanged: systemctl said “{said}”.")
SAVED_ON = _("The setting is saved: the intranet server will start with the computer.")
SAVED_OFF = _("The setting is saved: the intranet server will not start with the computer any more.")
"""Ce qu'ajoute l'alerte d'un échec (https://github.com/dascritch/machincast/issues/558)."""
IN_TERMINAL = _("No password dialog in this session: the password is asked in a terminal window.")
NO_ANSWER = _("Intranet server unchanged: no authentication in the terminal window.")
NO_AUTHENTICATION = _(
	"Intranet server unchanged: no way to ask for the password in this session; run “sudo systemctl {verb} {unit}”."
)
NOT_STARTED = _("Intranet server not started: Machin intranet stopped, exit code {code}.")
NOT_STARTED_WITHOUT_CODE = _("Intranet server not started: Machin intranet stopped.")
CODES = {
	2: _("Its configuration is invalid."),
	4: _("It is switched off in machincast.toml of the MachinCast directory, which the service reads."),
	127: _("A program is missing: after an update of MachinCast, run ./install.sh again, which updates the service."),
}
"""Ce que veut dire le code de sortie de Machin intranet, ou de Machin qui le lance."""
LAUNCHED = _("Machin intranet launched in a terminal, in test mode under your account: {addresses}")
TEST_MODE = _(
	"Test mode: without the broadcast service, Machin intranet runs under your account, without the partitioning of "
	"the service; for a computer open to the network of the radio, install the service (./install.sh --service)."
)
"""Ce que dit la page « Intranet » des paramètres sans le service (https://github.com/dascritch/machincast/issues/549) :
la documentation de la sécurité dit ce qui diffère (doc/fr/administration/securite.md)."""
WITHOUT_TERMINAL = _("No terminal found (konsole, x-terminal-emulator): run Machin intranet by hand.")
STILL_RUNNING = _("Machin intranet still running (PID {pid}): stop it in its terminal, with Ctrl-C.")
STOP_WINDOW = 10.0
"""Secondes pour que Machin intranet, lancé sans le service, s'arrête à SIGTERM."""
STOP_STEP = 0.1
"""Secondes entre deux regards sur son PID pendant cette attente."""


def service_installed() -> bool:
	"""L'unité du serveur intranet est installée : il tourne sous son propre compte, cloisonné."""
	return UNIT_FILE.exists()


RUNNING = _("Intranet server: running.")
STOPPED = _("Intranet server: stopped.")
"""L'état réel du serveur, à côté de la case de son réglage (https://github.com/dascritch/machincast/issues/558)."""


def running() -> bool:
	"""Le serveur intranet tourne : son unité, avec le service ; sinon, le Machin intranet du compte."""
	if service_installed():
		return service.read_startup(INTRANET_UNIT).running
	return process.running_pid() is not None


def command(configuration: Path | None) -> list[str]:
	"""Machin intranet, sur la configuration de l'interface, son terminal gardé ouvert sur une erreur."""
	called = [str(control.MACHIN)]
	if configuration is not None:
		called += ["--config", str(configuration)]
	return [*called, "intranet", "--keep-open"]


class IntranetSwitch(QObject):
	announced = Signal(str)
	"""Ce qu'il advient du serveur, pour la barre d'état."""
	alerted = Signal(str)
	"""Un échec, pour une boîte d'alerte : le serveur ne tourne pas comme le dit le réglage
	(https://github.com/dascritch/machincast/issues/558)."""

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
			QTimer.singleShot(0, self, lambda: self._by_hand(enabled=enabled, addresses=addresses))
			return
		verb = "stop"
		if enabled:
			verb = "restart"
		started_at = self.clock.now()
		launched = control.systemctl(self, [verb, INTRANET_UNIT])
		self.processes.append(launched)
		launched.finished.connect(lambda code, _status: self._end(launched, code, verb, addresses, started_at))
		launched.start()

	def _alert(self, said: str, verb: str) -> None:
		"""Dans la barre d'état, et dans une boîte d'alerte, avec ce que devient le réglage enregistré."""
		self.announced.emit(said)
		saved = SAVED_OFF
		if verb == "restart":
			saved = SAVED_ON
		self.alerted.emit(f"{said}\n\n{saved}")

	def _end(self, launched: QProcess, code: int, verb: str, addresses: list[str], started_at: datetime) -> None:
		self.processes.remove(launched)
		if code != 0:
			said = bytes(launched.readAllStandardError().data()).decode("utf-8", "replace").strip()
			if control.without_agent(said):
				self._in_terminal(verb, addresses, started_at)
				return
			self._alert(NOT_SWITCHED.format(said=said), verb)
			return
		self._done(verb, addresses, started_at)

	def _done(self, verb: str, addresses: list[str], started_at: datetime) -> None:
		if verb == "stop":
			self.announced.emit(SWITCHED_OFF)
			return
		self.announced.emit(STARTING)
		self._follow(round(control.STARTUP_WINDOW / control.STARTUP_STEP), addresses, started_at)

	def _in_terminal(self, verb: str, addresses: list[str], started_at: datetime) -> None:
		"""Sans agent graphique (ssh -X, su) : la même commande dans une fenêtre de terminal, où systemctl demande le
		mot de passe ; l'unité suivie jusqu'à ce qu'elle change, ou que le délai passe."""
		before = service.invocation(INTRANET_UNIT)
		if not control.authenticate_in_terminal([verb, INTRANET_UNIT]):
			self._alert(NO_AUTHENTICATION.format(verb=verb, unit=INTRANET_UNIT), verb)
			return
		self.announced.emit(IN_TERMINAL)
		remaining = round(control.AUTHENTICATION_WINDOW / control.STARTUP_STEP)
		self._watch(remaining, before, verb, addresses, started_at)

	def _watch(self, remaining: int, before: str, verb: str, addresses: list[str], started_at: datetime) -> None:
		"""Un redémarrage se voit à un nouveau démarrage de l'unité ; un arrêt, à l'unité arrêtée."""
		startup = service.read_startup(INTRANET_UNIT)
		changed = (verb == "stop") and (not startup.running)
		if verb == "restart":
			changed = service.invocation(INTRANET_UNIT) not in ("", before)
		if changed:
			self._done(verb, addresses, started_at)
			return
		if remaining <= 0:
			self._alert(NO_ANSWER, verb)
			return
		# Rattachée à l'objet : elle ne part pas s'il est détruit entre-temps.
		QTimer.singleShot(
			int(control.STARTUP_STEP * 1000),
			self,
			lambda: self._watch(remaining - 1, before, verb, addresses, started_at),
		)

	def _follow(self, remaining: int, addresses: list[str], started_at: datetime) -> None:
		"""Relit l'état de l'unité, encore remaining fois, une fois par control.STARTUP_STEP."""
		startup = service.read_startup(INTRANET_UNIT)
		if (startup.stopped) or ((remaining <= 0) and (not startup.running)):
			self._not_started(startup, started_at)
			return
		if remaining <= 0:
			self.announced.emit(SWITCHED_ON.format(addresses=", ".join(addresses)))
			return
		QTimer.singleShot(
			int(control.STARTUP_STEP * 1000), self, lambda: self._follow(remaining - 1, addresses, started_at)
		)

	def _not_started(self, startup: service.Startup, started_at: datetime) -> None:
		parts = [NOT_STARTED_WITHOUT_CODE]
		if (startup.code is not None) and (startup.code != 0):
			parts = [NOT_STARTED.format(code=startup.code)]
		meaning = CODES.get((startup.code) or (0))
		if meaning is not None:
			parts.append(meaning)
		# La dernière ligne de son journal dit le plus souvent pourquoi.
		parts.extend(service.journal(started_at, 1, INTRANET_UNIT)[-1:])
		self._alert(" ".join(parts), "restart")

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
			int(STOP_STEP * 1000), self, lambda: self._wait(pid, remaining - 1, enabled=enabled, addresses=addresses)
		)

	def _after_stop(self, *, enabled: bool, addresses: list[str]) -> None:
		if not enabled:
			self.announced.emit(SWITCHED_OFF)
			return
		if control.open_terminal(command(self.configuration)):
			self.announced.emit(LAUNCHED.format(addresses=", ".join(addresses)))
			return
		self.announced.emit(WITHOUT_TERMINAL)
