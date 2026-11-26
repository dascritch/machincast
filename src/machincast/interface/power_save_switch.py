"""« Cartes son toujours éveillées » (https://github.com/dascritch/machincast/issues/499), dans les paramètres du
service, page « Audio » (https://github.com/dascritch/machincast/issues/532).

Sans service de diffusion, en essai, la case active ou désactive les réglages de machincast.power_save, aussitôt, lancé
par pkexec, avec l'authentification d'un administrateur, que demande l'agent polkit de la session. Avec le service,
install.sh --service les tient : la case est inactive, et montre s'ils sont installés.
"""

import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal
from PySide6.QtWidgets import QCheckBox

from machincast import access, created_files, power_save
from machincast.i18n import _

ENTRY = _("Sound cards always awake")
ENABLED = _("Sound cards always awake: they no longer go to power saving.")
DISABLED = _("Sound cards back to power saving, at the next restart.")
REFUSED = _("Sound cards not set: authentication refused.")
FAILED = _("Sound cards not set: {error}")
WITHOUT_PKEXEC = _("Sound cards not set: pkexec missing, install the pkexec package.")
BY_SERVICE = _("Set by install.sh --service, with the broadcast service.")
REFUSED_CODES = (126, 127)
"""Les codes de pkexec : authentification refusée ou annulée, ou autorisation impossible à demander."""


class PowerSaveSwitch(QObject):
	"""La case des paramètres du service, et la commande pkexec qu'elle lance."""

	announced = Signal(str)

	def __init__(self, action: QCheckBox, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.action = action
		self.action.setText(ENTRY)
		self.action.clicked.connect(self.switch)
		self.process: QProcess | None = None
		self._verb = ""
		self.reread()

	def reread(self) -> None:
		"""L'entrée suit les réglages installés ; inactive avec le service, ou le temps d'une commande."""
		by_service = access.service_account() is not None
		self.action.setChecked(power_save.enabled())
		self.action.setEnabled((not by_service) and (self.process is None))
		self.action.setToolTip("")
		if by_service:
			self.action.setToolTip(BY_SERVICE)

	def switch(self, checked: bool) -> None:  # noqa: FBT001 (signal clicked de Qt)
		"""Active ou désactive les réglages par pkexec, l'entrée inactive le temps de la commande ; sans pkexec, le
		dit."""
		self._verb = "disable"
		if checked:
			self._verb = "enable"
		pkexec = shutil.which("pkexec")
		if pkexec is None:
			self.reread()
			self.announced.emit(WITHOUT_PKEXEC)
			return
		arguments = [sys.executable, "-m", "machincast.power_save", self._verb]
		if Path("/") != power_save.ROOT:
			arguments += ["--root", str(power_save.ROOT)]
		if created_files.LIST is not None:
			# Ses réglages de /etc, dans la liste des fichiers créés (https://github.com/dascritch/machincast/issues/652).
			arguments += ["--list", str(created_files.LIST)]
		process = QProcess(self)
		process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
		process.finished.connect(self._finished)
		self.process = process
		self.reread()
		process.start(pkexec, arguments)

	def _finished(self, code: int, status: QProcess.ExitStatus) -> None:
		process = self.process
		assert process is not None
		self.process = None
		output = bytes(process.readAll().data()).decode(errors="replace")
		process.deleteLater()
		self.reread()
		if (code == 0) and (status == QProcess.ExitStatus.NormalExit):
			message = DISABLED
			if self._verb == "enable":
				message = ENABLED
			self.announced.emit(message)
			return
		if code in REFUSED_CODES:
			self.announced.emit(REFUSED)
			return
		error = _("exit code {code}").format(code=code)
		for line in output.splitlines():
			if line.strip():
				error = line.strip()
		self.announced.emit(FAILED.format(error=error))
