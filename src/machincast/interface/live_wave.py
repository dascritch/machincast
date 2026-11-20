"""La forme d'onde du direct, dans le moniteur de l'antenne (https://github.com/dascritch/machincast/issues/531).

À la place de la frise d'un fichier, que le direct n'a pas, le moniteur de l'antenne dessine à la volée ce qu'il
entend : à chaque relevé de la fenêtre, le niveau du canal le plus fort devient une colonne, ajoutée à droite ; les plus
anciennes sortent à gauche, au-delà de COLUMNS. Une colonne va de 0, le silence (SILENCE dB et moins), à 1, le niveau
plein (0 dB). Ce qui est calculé (columns) l'est à part du dessin, pour que les scénarios le vérifient sans lire de
pixels.
"""

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter, QPaintEvent, QPalette
from PySide6.QtWidgets import QWidget

COLUMNS = 300
"""Colonnes gardées : à un relevé toutes les 100 ms, les trente dernières secondes."""
SILENCE = -60.0
"""Décibels en dessous desquels une colonne est vide."""


def height_of(levels: list[float]) -> float:
	"""La hauteur d'une colonne, de 0 à 1, pour les niveaux des canaux, en dB ; 0 sans niveau."""
	if levels == []:
		return 0.0
	loudest = max(levels)
	if loudest <= SILENCE:
		return 0.0
	if loudest >= 0:
		return 1.0
	return (loudest - SILENCE) / -SILENCE


class LiveWave(QWidget):
	"""La forme d'onde qui défile, de la gauche, le plus ancien, à la droite, le plus récent."""

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._columns: list[float] = []
		self.setMinimumHeight(48)

	def columns(self) -> list[float]:
		"""Les hauteurs gardées, de la plus ancienne à la plus récente."""
		return list(self._columns)

	def add(self, levels: list[float]) -> None:
		"""Un relevé de plus : sa colonne s'ajoute à droite."""
		self._columns.append(height_of(levels))
		if len(self._columns) > COLUMNS:
			self._columns = self._columns[-COLUMNS:]
		self.update()

	def clear(self) -> None:
		self._columns = []
		self.update()

	def paintEvent(self, event: QPaintEvent) -> None:
		"""Une colonne par relevé, centrée sur la ligne du milieu, symétrique comme une forme d'onde."""
		with QPainter(self) as painter:
			colour = self.palette().color(QPalette.ColorRole.Highlight)
			painter.setPen(colour)
			width = self.width()
			middle = self.height() / 2
			step = width / COLUMNS
			first = COLUMNS - len(self._columns)
			for rank, height in enumerate(self._columns):
				x = (first + rank) * step
				half = max(0.5, height * middle)
				painter.fillRect(QRectF(QPointF(x, middle - half), QPointF(x + max(step, 1.0), middle + half)), colour)
