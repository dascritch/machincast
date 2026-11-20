"""Allumer et éteindre le serveur intranet depuis les paramètres du service
(https://github.com/dascritch/machincast/issues/538).

La page « Intranet » écrit intranet.enabled, port et validation dans machincast.toml. Avec le service installé
(install.sh --service), l'unité machincast-intranet.service les prend aussitôt : systemctl restart pour l'allumer, ou
pour qu'il prenne un nouveau réglage, systemctl stop pour l'éteindre ; la règle polkit demande le mot de passe d'un
administrateur. Sans le service, Machin intranet se lance à la main : la barre d'état le dit.
"""

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from machincast.i18n import _
from machincast.service import INTRANET_UNIT

UNIT_FILE = Path("/etc/systemd/system") / INTRANET_UNIT
SWITCHED_ON = _("Intranet server switched on: {addresses}")
SWITCHED_OFF = _("Intranet server switched off.")
NOT_SWITCHED = _("Intranet server unchanged: systemctl said “{said}”.")
BY_HAND_ON = _(
	"Intranet switched on in machincast.toml: without the broadcast service, launch it with Machin intranet."
)
BY_HAND_OFF = _("Intranet switched off in machincast.toml: stop Machin intranet if it is running.")


class IntranetSwitch(QObject):
	announced = Signal(str)
	"""Ce qu'il advient du serveur, pour la barre d'état."""

	def __init__(self, parent: QObject | None = None, unit_file: Path | None = None) -> None:
		super().__init__(parent)
		self.unit_file = unit_file
		self.processes: list[QProcess] = []

	def apply(self, *, enabled: bool, addresses: list[str]) -> None:
		"""Rallume ou éteint l'unité du service, sans attendre : l'authentification peut prendre du temps."""
		if not ((self.unit_file) or (UNIT_FILE)).exists():
			# Après ce qu'annoncent les paramètres enregistrés, qui viennent juste ensuite.
			said = BY_HAND_OFF
			if enabled:
				said = BY_HAND_ON
			QTimer.singleShot(0, lambda: self.announced.emit(said))
			return
		verb = "stop"
		done = SWITCHED_OFF
		if enabled:
			verb = "restart"
			done = SWITCHED_ON.format(addresses=", ".join(addresses))
		process = QProcess(self)
		self.processes.append(process)
		process.finished.connect(lambda code, _status: self._end(process, code, done))
		process.start("systemctl", [verb, INTRANET_UNIT])

	def _end(self, process: QProcess, code: int, done: str) -> None:
		self.processes.remove(process)
		if code == 0:
			self.announced.emit(done)
			return
		said = bytes(process.readAllStandardError().data()).decode("utf-8", "replace").strip()
		self.announced.emit(NOT_SWITCHED.format(said=said))
