"""Le curseur d'une sonie ou d'une crête, en décibels, par demi-décibel, sa valeur écrite à sa droite :
« −23,0 LUFS » (https://github.com/dascritch/machincast/issues/43)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

from machincast.i18n import decimal

STEPS = 2
"""Pas du curseur par décibel : un demi-décibel."""


def written(value: float, unit: str) -> str:
	"""« −23,0 LUFS », au dixième, avec la virgule de la langue."""
	return decimal(f"{value:.1f}").replace("-", "−") + unit


class LevelSlider(QWidget):
	valueChanged = Signal(float)
	"""La valeur, en décibels, à chaque mouvement du curseur."""

	def __init__(self, lowest: float, highest: float, unit: str, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.unit = unit
		self.slider = QSlider(Qt.Orientation.Horizontal, self)
		self.slider.setObjectName("slider")
		self.slider.setRange(round(lowest * STEPS), round(highest * STEPS))
		self.slider.setSingleStep(1)
		self.slider.setPageStep(STEPS)
		self.value_label = QLabel(self)
		self.value_label.setObjectName("value_label")
		self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
		# La largeur de la plus longue valeur : le curseur ne bouge pas quand elle change.
		width = max(
			self.value_label.fontMetrics().horizontalAdvance(written(lowest, unit)),
			self.value_label.fontMetrics().horizontalAdvance(written(highest, unit)),
		)
		self.value_label.setMinimumWidth(width)
		arrangement = QHBoxLayout(self)
		arrangement.setContentsMargins(0, 0, 0, 0)
		arrangement.addWidget(self.slider, 1)
		arrangement.addWidget(self.value_label)
		self.slider.valueChanged.connect(self._moves)
		self._moves(self.slider.value())

	def _moves(self, position: int) -> None:
		self.value_label.setText(written(position / STEPS, self.unit))
		self.valueChanged.emit(position / STEPS)

	def value(self) -> float:
		return self.slider.value() / STEPS

	def setValue(self, value: float) -> None:  # comme le champ de nombre qu'il remplace
		self.slider.setValue(round(value * STEPS))
		self._moves(self.slider.value())

	def minimum(self) -> float:
		return self.slider.minimum() / STEPS

	def maximum(self) -> float:
		return self.slider.maximum() / STEPS
