"""Curseur d'une durée de crossfade (https://github.com/dascritch/machincast/issues/223).

Un QSlider horizontal, de 0 à la durée maximale des préférences, au pas des préférences (seconde ou dixième), et la
valeur choisie écrite à sa droite, « 2,5 s ». Une valeur plus longue que la durée maximale reste telle quelle : le
curseur s'allonge pour elle (montrer). Il se lit et s'écrit en secondes, comme le champ de nombre qu'il remplace.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

from machincast.interface import preferences


class DurationSlider(QWidget):
	valueChanged = Signal(float)
	"""La valeur, en secondes, à chaque mouvement du curseur."""

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.slider = QSlider(Qt.Orientation.Horizontal, self)
		self.slider.setObjectName("slider")
		self.value_label = QLabel(self)
		self.value_label.setObjectName("value_label")
		self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
		arrangement = QHBoxLayout(self)
		arrangement.setContentsMargins(0, 0, 0, 0)
		arrangement.addWidget(self.slider, 1)
		arrangement.addWidget(self.value_label)
		self._step = 0.1
		self._decimals = 1
		self.slider.valueChanged.connect(self._moves)
		self.set_according_to_preferences()

	def set_(self, decimals: int, step: float, maximum: float) -> None:
		"""Le pas, les décimales écrites et la durée maximale, en secondes."""
		value_label = self.value()
		self._step, self._decimals = step, decimals
		self.slider.setSingleStep(1)
		self.slider.setPageStep(max(1, round(1 / step)))
		self.slider.setMaximum(round(maximum / step))
		# La largeur de la plus longue valeur : le curseur ne bouge pas quand elle change.
		self.value_label.setMinimumWidth(self.value_label.fontMetrics().horizontalAdvance(self._write(maximum)))
		self.display(value_label)

	def set_according_to_preferences(self) -> None:
		settings = preferences.crossfades()
		decimals, step = preferences.STEPS[settings.granularity]
		self.set_(decimals, step, settings.maximum.total_seconds())

	def maximum(self) -> float:
		return self.slider.maximum() * self._step

	def decimals(self) -> int:
		"""Les décimales écrites, comme le champ de nombre qu'il remplace."""
		return self._decimals

	def singleStep(self) -> float:  # noqa: N802 : le nom de QDoubleSpinBox
		"""Le pas, en secondes."""
		return self._step

	def value(self) -> float:
		return round(self.slider.value() * self._step, 6)

	def setValue(self, seconds: float) -> None:
		self.slider.setValue(round(seconds / self._step))
		self._write_value()

	def display(self, seconds: float) -> None:
		"""Une valeur plus longue que la durée maximale reste telle quelle : le curseur s'allonge pour elle."""
		notches = round(seconds / self._step)
		self.slider.setMaximum(max(self.slider.maximum(), notches))
		self.setValue(seconds)

	def text(self) -> str:
		"""« 2,5 s », comme l'écrivait le champ de nombre."""
		return self.value_label.text()

	def _moves(self, _notches: int) -> None:
		self._write_value()
		self.valueChanged.emit(self.value())

	def _write_value(self) -> None:
		self.value_label.setText(self._write(self.value()))

	def _write(self, seconds: float) -> str:
		return f"{preferences.FRENCH.toString(seconds, 'f', self._decimals)} s"
