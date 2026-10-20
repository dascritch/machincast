"""Fenêtres modales des scénarios : un minuteur y fait un geste une fois la fenêtre ouverte."""

from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget


def quand_modale(geste: Callable[[QWidget], None]) -> None:
	"""Le geste, dès que la fenêtre modale est ouverte."""

	def essayer() -> None:
		modale = QApplication.activeModalWidget()
		if modale is None:
			QTimer.singleShot(10, essayer)
			return
		try:
			geste(modale)
		except BaseException:
			# Une étape en échec ne laisse pas la fenêtre modale attendre un clic.
			modale.close()
			raise

	QTimer.singleShot(0, essayer)
