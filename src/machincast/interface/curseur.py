"""Curseur d'une durée de crossfade (https://github.com/dascritch/machincast/issues/223).

Un QSlider horizontal, de 0 à la durée maximale des préférences, au pas des préférences (seconde ou dixième), et la
valeur choisie écrite à sa droite, « 2,5 s ». Une valeur plus longue que la durée maximale reste telle quelle : le
curseur s'allonge pour elle (montrer). Il se lit et s'écrit en secondes, comme le champ de nombre qu'il remplace.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QWidget

from machincast.interface import preferences


class CurseurDeDuree(QWidget):
	valueChanged = Signal(float)
	"""La valeur, en secondes, à chaque mouvement du curseur."""

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.curseur = QSlider(Qt.Orientation.Horizontal, self)
		self.curseur.setObjectName("curseur")
		self.valeur = QLabel(self)
		self.valeur.setObjectName("valeur")
		self.valeur.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
		disposition = QHBoxLayout(self)
		disposition.setContentsMargins(0, 0, 0, 0)
		disposition.addWidget(self.curseur, 1)
		disposition.addWidget(self.valeur)
		self._pas = 0.1
		self._decimales = 1
		self.curseur.valueChanged.connect(self._bouge)
		self.regler_selon_les_preferences()

	def regler(self, decimales: int, pas: float, maximum: float) -> None:
		"""Le pas, les décimales écrites et la durée maximale, en secondes."""
		valeur = self.value()
		self._pas, self._decimales = pas, decimales
		self.curseur.setSingleStep(1)
		self.curseur.setPageStep(max(1, round(1 / pas)))
		self.curseur.setMaximum(round(maximum / pas))
		# La largeur de la plus longue valeur : le curseur ne bouge pas quand elle change.
		self.valeur.setMinimumWidth(self.valeur.fontMetrics().horizontalAdvance(self._ecrire(maximum)))
		self.montrer(valeur)

	def regler_selon_les_preferences(self) -> None:
		reglages = preferences.crossfades()
		decimales, pas = preferences.PAS[reglages.granularite]
		self.regler(decimales, pas, reglages.maximum.total_seconds())

	def maximum(self) -> float:
		return self.curseur.maximum() * self._pas

	def decimals(self) -> int:
		"""Les décimales écrites, comme le champ de nombre qu'il remplace."""
		return self._decimales

	def singleStep(self) -> float:  # noqa: N802 : le nom de QDoubleSpinBox
		"""Le pas, en secondes."""
		return self._pas

	def value(self) -> float:
		return round(self.curseur.value() * self._pas, 6)

	def setValue(self, secondes: float) -> None:
		self.curseur.setValue(round(secondes / self._pas))
		self._ecrire_la_valeur()

	def montrer(self, secondes: float) -> None:
		"""Une valeur plus longue que la durée maximale reste telle quelle : le curseur s'allonge pour elle."""
		crans = round(secondes / self._pas)
		self.curseur.setMaximum(max(self.curseur.maximum(), crans))
		self.setValue(secondes)

	def text(self) -> str:
		"""« 2,5 s », comme l'écrivait le champ de nombre."""
		return self.valeur.text()

	def _bouge(self, _crans: int) -> None:
		self._ecrire_la_valeur()
		self.valueChanged.emit(self.value())

	def _ecrire_la_valeur(self) -> None:
		self.valeur.setText(self._ecrire(self.value()))

	def _ecrire(self, secondes: float) -> str:
		return f"{preferences.FRANCAIS.toString(secondes, 'f', self._decimales)} s"
