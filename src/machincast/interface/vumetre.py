"""VU-mètre et bargraph de crête (https://github.com/dascritch/machincast/issues/24,
https://github.com/dascritch/machincast/issues/116).

Une barre par canal, du plancher (-60 dB) à 0 dB : le VU, niveau moyen (RMS), plein ; par-dessus, le bargraph de
crête, plus clair, et un repère qui garde la plus haute crête MAINTIEN_DE_CRETE secondes. Vert, orange au-delà de
-12 dB, rouge au-delà de -3 dB. Horizontal dans la pré-écoute, vertical dans la colonne de l'accueil. Un clic émet
clique : l'accueil s'en sert pour écouter l'antenne.
"""

import math
import time
from collections.abc import Callable

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

PLANCHER = -60.0
MAINTIEN_DE_CRETE = 2.0
"""Secondes pendant lesquelles le repère garde la plus haute crête."""
VERT, ORANGE, ROUGE = QColor("#3c9d5a"), QColor("#e0a020"), QColor("#d03030")


def couleur(niveau: float) -> QColor:
	if niveau > -3:
		return ROUGE
	if niveau > -12:
		return ORANGE
	return VERT


def part(niveau: float) -> float:
	"""La part de la barre, de 0 au plancher à 1 à 0 dB."""
	return (max(PLANCHER, min(0.0, niveau)) - PLANCHER) / -PLANCHER


def _valides(niveaux: list[float]) -> list[float]:
	return [niveau for niveau in niveaux if not math.isnan(niveau)]


class VuMetre(QWidget):
	PLANCHER = PLANCHER
	clique = Signal()

	def __init__(
		self, parent: QWidget | None = None, vertical: bool = False, horloge: Callable[[], float] = time.monotonic
	) -> None:
		super().__init__(parent)
		self.vertical = vertical
		self.horloge = horloge
		self.niveaux: list[float] = []
		"""VU de chaque canal, en décibels ; vide sans son à montrer."""
		self.cretes: list[float] = []
		"""Crête de chaque canal, en décibels."""
		self.maintenues: list[tuple[float, float]] = []
		"""Plus haute crête récente de chaque canal, et l'instant où elle a été vue."""
		self.setMinimumSize(24, 24)
		self.setToolTip("Niveau de chaque canal, en décibels")

	def montrer(self, niveaux: list[float], cretes: list[float] | None = None) -> None:
		self.niveaux = _valides(niveaux)
		self.cretes = _valides((cretes) or (niveaux))
		maintenant = self.horloge()
		if len(self.maintenues) != len(self.cretes):
			self.maintenues = [(crete, maintenant) for crete in self.cretes]
		for indice, crete in enumerate(self.cretes):
			gardee, depuis = self.maintenues[indice]
			if (crete >= gardee) or (maintenant - depuis > MAINTIEN_DE_CRETE):
				self.maintenues[indice] = (crete, maintenant)
		if not self.niveaux:
			self.maintenues = []
		self.update()

	def mousePressEvent(self, evenement: QMouseEvent) -> None:
		if evenement.button() == Qt.MouseButton.LeftButton:
			self.clique.emit()

	def paintEvent(self, _evenement: QPaintEvent) -> None:
		peintre = QPainter(self)
		cadre = QRectF(self.rect()).adjusted(1, 1, -1, -1)
		peintre.fillRect(cadre, self.palette().base())
		nombre = max(1, len(self.niveaux))
		for indice, niveau in enumerate(self.niveaux):
			crete = self.cretes[indice]
			plus_claire = QColor(couleur(crete))
			plus_claire.setAlpha(110)
			peintre.fillRect(self._barre(cadre, indice, nombre, part(crete)), plus_claire)
			peintre.fillRect(self._barre(cadre, indice, nombre, part(niveau)), couleur(niveau))
			if indice < len(self.maintenues):
				gardee = self.maintenues[indice][0]
				peintre.setPen(QPen(couleur(gardee), 2))
				repere = self._barre(cadre, indice, nombre, part(gardee))
				if self.vertical:
					peintre.drawLine(repere.topLeft(), repere.topRight())
				else:
					peintre.drawLine(repere.topRight(), repere.bottomRight())
		peintre.setPen(self.palette().mid().color())
		peintre.drawRect(cadre)
		peintre.end()

	def _barre(self, cadre: QRectF, indice: int, nombre: int, fraction: float) -> QRectF:
		"""La barre du canal, remplie de cette fraction : de bas en haut, ou de gauche à droite."""
		if self.vertical:
			largeur = cadre.width() / nombre
			hauteur = cadre.height() * fraction
			return QRectF(cadre.left() + indice * largeur + 1, cadre.bottom() - hauteur, largeur - 2, hauteur)
		hauteur = cadre.height() / nombre
		return QRectF(cadre.left(), cadre.top() + indice * hauteur + 1, cadre.width() * fraction, hauteur - 2)
