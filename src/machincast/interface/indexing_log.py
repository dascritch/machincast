"""Journal d'une indexation lancée depuis l'interface (https://github.com/dascritch/machincast/issues/120).

La fenêtre de Machin indexer --window, dans un processus à part de l'interface (machincast.interface.indexer) :
elle montre ligne par ligne ce que Machin indexer écrirait dans le terminal, au fil de l'indexation, chaque sonore
indexé avec son statut, les anomalies, puis le bilan. À la fin, elle conclut par le bilan et le nombre d'anomalies.

La fermer pendant l'indexation demande s'il faut l'arrêter : elle s'arrête alors après le fichier en cours, et le
travail fait est gardé ; sinon, la fenêtre reste ouverte. Une fois l'indexation finie, elle se ferme sans question,
et le processus s'arrête.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFontDatabase
from PySide6.QtWidgets import QWidget

from machincast.configuration import SILENCE_THRESHOLD
from machincast.indexer.__main__ import EXECUTABLE
from machincast.interface import dialogs
from machincast.interface.application import application
from machincast.interface.indexer import TITLES, Indexing
from machincast.interface.ui.indexing_log import Ui_LogWindow


class LogWindow(QWidget):
	def __init__(
		self,
		socket: Path,
		database: str,
		full_audit: bool,
		parent: QWidget | None = None,
		silence_threshold: float = SILENCE_THRESHOLD,
	) -> None:
		super().__init__(parent, Qt.WindowType.Window)
		self.ui = Ui_LogWindow()
		self.ui.setupUi(self)
		self.ui.log.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
		self.ui.shut_down.clicked.connect(self.close)
		self.full_audit = full_audit
		self.setWindowTitle(TITLES[full_audit])
		self.anomalies: list[str] = []
		"""Les lignes d'anomalie et d'erreur de l'indexation."""
		self.indexer = Indexing(socket, database, self, silence_threshold)
		self.indexer.line.connect(self.add)
		self.indexer.finished.connect(self.conclude)

	def launch(self) -> None:
		"""Ouvre la fenêtre, puis lance l'indexation."""
		self.ui.conclusion.setText(f"{self.windowTitle()} en cours…")
		self.show()
		self.indexer.launch(self.full_audit)

	def add(self, text: str, anomaly: bool) -> None:
		self.ui.log.appendPlainText(text)
		if anomaly:
			self.anomalies.append(text)

	def conclude(self, report: str) -> None:
		text = report
		count = len(self.anomalies)
		if count == 1:
			text = f"{report} 1 anomalie, dans le journal ci-dessus."
		elif count > 1:
			text = f"{report} {count} anomalies, dans le journal ci-dessus."
		self.ui.conclusion.setText(text)

	def lines(self) -> list[str]:
		return self.ui.log.toPlainText().splitlines()

	def closeEvent(self, event: QCloseEvent) -> None:
		"""Pendant l'indexation, demande s'il faut l'arrêter ; sinon, la fenêtre reste ouverte."""
		if self.indexer.ongoing():
			if not dialogs.confirm_indexing_stop(self, self.windowTitle()):
				event.ignore()
				return
			self.indexer.halt()
		super().closeEvent(event)


def launch_window(
	socket: Path, database: str, full_audit: bool, silence_threshold: float = SILENCE_THRESHOLD, force: bool = False
) -> int:
	"""Machin indexer --window : la fenêtre du journal, jusqu'à sa fermeture ; forcer, avec --force."""
	qt = application(EXECUTABLE)
	window = LogWindow(socket, database, full_audit, silence_threshold=silence_threshold)
	window.indexer.force = force
	window.launch()
	return qt.exec()
