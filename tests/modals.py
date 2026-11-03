"""Fenêtres modales des scénarios : un minuteur y fait un geste une fois la fenêtre ouverte."""

from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget


def when_modal(gesture: Callable[[QWidget], None]) -> None:
	"""Le geste, dès que la fenêtre modale est ouverte."""

	def try_() -> None:
		modal = QApplication.activeModalWidget()
		if modal is None:
			QTimer.singleShot(10, try_)
			return
		try:
			gesture(modal)
		except BaseException:
			# Une étape en échec ne laisse pas la fenêtre modale attendre un clic.
			modal.close()
			raise

	QTimer.singleShot(0, try_)
