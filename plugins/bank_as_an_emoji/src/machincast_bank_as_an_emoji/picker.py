"""Le choix d'un emoji : le sélecteur d'emojis de KDE, sinon une grille d'emojis
(https://github.com/dascritch/machincast/issues/505).

Le sélecteur de KDE, plasma-emojier, ne rend pas l'emoji choisi : il le copie dans le presse-papiers, et reste ouvert.
Le plugin le lance, détaché, puis prend chaque emoji copié dans le presse-papiers, tant que le choix est ouvert :
ARMED millisecondes, ou jusqu'au choix suivant. Sous Wayland, le presse-papiers n'arrive qu'à la fenêtre qui a le
focus : l'emoji vient quand la fiche le retrouve. Ce qui est copié n'est pas un emoji, ou est copié hors d'un choix, est
ignoré.

Sans plasma-emojier, une grille des emojis proposés s'ouvre sous le bouton, avec un champ où coller tout autre emoji.
"""

import shutil

from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QGridLayout, QLineEdit, QMenu, QToolButton, QVBoxLayout, QWidget, QWidgetAction

from machincast_bank_as_an_emoji.names import PALETTE, is_emoji
from machincast_bank_as_an_emoji.texts import t

EMOJIER = "plasma-emojier"
"""Le sélecteur d'emojis de KDE Plasma."""
ARMED = 10 * 60 * 1000
"""Millisecondes pendant lesquelles un emoji copié est pris, après l'ouverture du sélecteur de KDE."""
COLUMNS = 6
"""Les colonnes de la grille d'emojis."""


def emojier() -> str | None:
	"""Le chemin de plasma-emojier, ou None s'il n'est pas installé."""
	return shutil.which(EMOJIER)


class KdePicker(QObject):
	"""Le sélecteur d'emojis de KDE, et le presse-papiers qu'il remplit."""

	picked = Signal(str)

	def __init__(self, program: str, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.program = program
		self.armed = False
		self.before = ""
		self.timer = QTimer(self)
		self.timer.setSingleShot(True)
		self.timer.setInterval(ARMED)
		self.timer.timeout.connect(self.disarm)
		QGuiApplication.clipboard().dataChanged.connect(self._copied)

	def open(self) -> bool:
		"""Lance le sélecteur, détaché : il reste ouvert si la fiche se ferme. Faux s'il n'a pas pu se lancer."""
		self.before = QGuiApplication.clipboard().text()
		started = bool(QProcess.startDetached(self.program, []))
		self.armed = started
		if started:
			self.timer.start()
		return started

	def disarm(self) -> None:
		self.armed = False
		self.timer.stop()

	def _copied(self) -> None:
		if not self.armed:
			return
		text = QGuiApplication.clipboard().text().strip()
		if (text == self.before) or (not is_emoji(text)):
			return
		self.before = text
		self.picked.emit(text)


class EmojiGrid(QMenu):
	"""Les emojis proposés, en grille, et un champ où coller tout autre emoji."""

	picked = Signal(str)

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("emoji_grid")
		content = QWidget(self)
		layout = QVBoxLayout(content)
		grid = QGridLayout()
		self.buttons: list[QToolButton] = []
		for position, emoji in enumerate(PALETTE):
			button = QToolButton(content)
			button.setText(emoji)
			button.setAutoRaise(True)
			button.clicked.connect(lambda _checked=False, chosen=emoji: self._pick(chosen))
			grid.addWidget(button, position // COLUMNS, position % COLUMNS)
			self.buttons.append(button)
		layout.addLayout(grid)
		self.pasted = QLineEdit(content)
		self.pasted.setObjectName("pasted_emoji")
		self.pasted.setPlaceholderText(t("Paste another emoji, then Enter"))
		self.pasted.returnPressed.connect(self._paste)
		layout.addWidget(self.pasted)
		action = QWidgetAction(self)
		action.setDefaultWidget(content)
		self.addAction(action)

	def _pick(self, emoji: str) -> None:
		self.picked.emit(emoji)
		self.close()

	def _paste(self) -> None:
		"""Un texte collé qui n'est pas un emoji est ignoré : la grille reste ouverte."""
		text = self.pasted.text().strip()
		if is_emoji(text):
			self.pasted.clear()
			self._pick(text)
