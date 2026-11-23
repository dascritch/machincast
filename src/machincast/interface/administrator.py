"""Le mot de passe d'un administrateur, par polkit, pour régler les paramètres du service
(https://github.com/dascritch/machincast/issues/603).

Le service installé, ouvrir « Paramètres du service… » demande à polkit l'action org.machincast.service-settings, que
déclare la politique installée par install.sh --service : pkcheck, dans un QProcess, jamais attendu dans le fil de
l'interface, fait demander par l'agent polkit du bureau le mot de passe d'un administrateur, celui du compte s'il l'est.
Autorisée, la fenêtre se règle ; refusée, annulée, ou pkcheck absent, elle s'ouvre en consultation.
"""

import os

from PySide6.QtCore import QObject, QProcess, Signal

from machincast.service import SERVICE_SETTINGS_ACTION

PROGRAM = "pkcheck"


def arguments(pid: int) -> list[str]:
	"""Les arguments de pkcheck : l'action, pour ce processus, en laissant l'agent polkit demander le mot de passe."""
	return ["--action-id", SERVICE_SETTINGS_ACTION, "--process", str(pid), "--allow-user-interaction"]


class Administrator(QObject):
	"""Demande l'action à polkit ; decided dit si elle est autorisée."""

	decided = Signal(bool)

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.program = PROGRAM
		self._process: QProcess | None = None

	def ask(self) -> None:
		"""Une seule demande à la fois : une autre, en cours, est laissée à sa réponse."""
		if self._process is not None:
			return
		process = QProcess(self)
		process.finished.connect(self._finished)
		process.errorOccurred.connect(self._failed)
		self._process = process
		process.start(self.program, arguments(os.getpid()))

	def _finished(self, code: int, status: QProcess.ExitStatus) -> None:
		self._answer(allowed=(status == QProcess.ExitStatus.NormalExit) and (code == 0))

	def _failed(self, error: QProcess.ProcessError) -> None:
		# pkcheck absent : finished ne vient pas.
		if error == QProcess.ProcessError.FailedToStart:
			self._answer(allowed=False)

	def _answer(self, *, allowed: bool) -> None:
		process = self._process
		self._process = None
		if process is not None:
			process.deleteLater()
		self.decided.emit(allowed)
