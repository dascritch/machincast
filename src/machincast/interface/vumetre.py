"""VU-mètre et bargraph de crête (https://github.com/dascritch/machincast/issues/24,
https://github.com/dascritch/machincast/issues/116).

Une barre par canal, du plancher (-60 dB) à 0 dB : le VU, niveau moyen (RMS), plein ; par-dessus, le bargraph de
crête, plus clair, et un repère qui garde la plus haute crête MAINTIEN_DE_CRETE secondes. Vert, orange au-delà de
-12 dB, rouge au-delà de -3 dB. Horizontal dans la pré-écoute, vertical dans la colonne de l'accueil. Un clic émet
clique : l'accueil s'en sert pour écouter l'antenne.

Une échelle en dB (GRADUATIONS) l'accompagne : couché, sous les canaux ; vertical, entre les canaux gauche et droit
d'un son stéréo, qu'elle sépare, nommés « G » et « D » dessous, ou à droite des canaux sinon. Un nombre qui chevauche
un autre n'est pas écrit ; 0 et -60 le sont toujours.
"""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

PLANCHER = -60.0
MAINTIEN_DE_CRETE = 2.0
"""Secondes pendant lesquelles le repère garde la plus haute crête."""
VERT, ORANGE, ROUGE = QColor("#3c9d5a"), QColor("#e0a020"), QColor("#d03030")
GRADUATIONS = (0, -6, -12, -20, -30, -40, -50, -60)
"""Les graduations de l'échelle, en dB, chacune d'un trait."""
IMPORTANCE = (0, -60, -20, -6, -12, -40, -30, -50)
"""Les nombres de l'échelle, du plus important au moins important : 0 et le plancher sont toujours écrits, un
autre seulement s'il ne chevauche pas un nombre plus important."""
NOMS_DES_CANAUX = ("G", "D")
"""Les noms des canaux d'un son stéréo, sous le VU-mètre vertical."""
TAILLE_DE_L_ECHELLE = 7.0
"""Points de la police de l'échelle et des noms des canaux."""
TRAIT = 3.0
"""Pixels des traits de graduation."""
ECART = 2.0
"""Pixels entre l'échelle et les barres qui l'entourent."""


def couleur(niveau: float) -> QColor:
	if niveau > -3:
		return ROUGE
	if niveau > -12:
		return ORANGE
	return VERT


def part(niveau: float) -> float:
	"""La part de la barre, de 0 au plancher à 1 à 0 dB."""
	return (max(PLANCHER, min(0.0, niveau)) - PLANCHER) / -PLANCHER


@dataclass(frozen=True)
class Disposition:
	"""Où se dessine chaque partie du VU-mètre."""

	canaux: list[QRectF]
	"""La barre de chaque canal, pleine échelle."""
	echelle: QRectF
	"""La bande de l'échelle : ses traits et ses nombres."""
	noms: list[tuple[str, QRectF]]
	"""Le nom de chaque canal, sous sa barre ; vide s'il n'y en a pas."""


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
		self.police = QFont(self.font())
		self.police.setPointSizeF(TAILLE_DE_L_ECHELLE)
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

	def disposition(self) -> Disposition:
		"""Sans son, la place de deux canaux : l'échelle ne bouge pas quand le son arrive."""
		nombre = len(self.niveaux)
		if nombre == 0:
			nombre = 2
		cadre = QRectF(self.rect()).adjusted(1, 1, -1, -1)
		metriques = QFontMetricsF(self.police)
		if self.vertical:
			return self._disposition_verticale(cadre, nombre, metriques)
		return self._disposition_couchee(cadre, nombre, metriques)

	def _disposition_verticale(self, cadre: QRectF, nombre: int, metriques: QFontMetricsF) -> Disposition:
		stereo = nombre == len(NOMS_DES_CANAUX)
		hauteur_des_noms = 0.0
		if stereo:
			hauteur_des_noms = metriques.height()
		marge = metriques.height() / 2
		haut, bas = cadre.top() + marge, cadre.bottom() - max(marge, hauteur_des_noms)
		largeur_de_l_echelle = metriques.horizontalAdvance(str(int(PLANCHER))) + 2 * TRAIT + 4
		largeur = (cadre.width() - largeur_de_l_echelle - 2 * ECART) / nombre
		canaux = []
		for indice in range(nombre):
			gauche = cadre.left() + indice * largeur
			if (stereo) and (indice == 1):
				gauche += largeur_de_l_echelle + 2 * ECART
			canaux.append(QRectF(gauche, haut, largeur, bas - haut))
		echelle = QRectF(cadre.right() - largeur_de_l_echelle, haut, largeur_de_l_echelle, bas - haut)
		noms: list[tuple[str, QRectF]] = []
		if stereo:
			echelle.moveLeft(canaux[0].right() + ECART)
			noms = [
				(nom, QRectF(canal.left(), bas, canal.width(), hauteur_des_noms))
				for nom, canal in zip(NOMS_DES_CANAUX, canaux, strict=True)
			]
		return Disposition(canaux, echelle, noms)

	def _disposition_couchee(self, cadre: QRectF, nombre: int, metriques: QFontMetricsF) -> Disposition:
		hauteur_de_l_echelle = metriques.height() + TRAIT
		gauche = cadre.left() + metriques.horizontalAdvance(str(int(PLANCHER))) / 2
		droite = cadre.right() - metriques.horizontalAdvance("0") / 2
		bas = cadre.bottom() - hauteur_de_l_echelle
		hauteur = (bas - cadre.top()) / nombre
		canaux = [QRectF(gauche, cadre.top() + indice * hauteur, droite - gauche, hauteur) for indice in range(nombre)]
		echelle = QRectF(gauche, bas, droite - gauche, hauteur_de_l_echelle)
		return Disposition(canaux, echelle, [])

	def position(self, niveau: float, disposition: Disposition | None = None) -> float:
		"""Où ce niveau se trouve sur les barres : son ordonnée, vertical, son abscisse, couché."""
		echelle = (disposition) or (self.disposition())
		if self.vertical:
			return echelle.echelle.bottom() - part(niveau) * echelle.echelle.height()
		return echelle.echelle.left() + part(niveau) * echelle.echelle.width()

	def candidates(self) -> list[tuple[int, QRectF]]:
		"""Chaque graduation de l'échelle et le cadre de son nombre, du plus important au moins important
		(IMPORTANCE), qu'il tienne ou non."""
		disposition = self.disposition()
		metriques = QFontMetricsF(self.police)
		cadres = []
		for graduation in IMPORTANCE:
			texte = str(graduation)
			largeur, hauteur = metriques.horizontalAdvance(texte), metriques.height()
			endroit = self.position(graduation, disposition)
			if self.vertical:
				centre = QPointF(disposition.echelle.center().x(), endroit)
			else:
				centre = QPointF(endroit, disposition.echelle.top() + TRAIT + hauteur / 2)
			cadres.append((graduation, QRectF(centre.x() - largeur / 2, centre.y() - hauteur / 2, largeur, hauteur)))
		return cadres

	def etiquettes(self) -> list[tuple[str, QRectF]]:
		"""Les nombres écrits sur l'échelle, de 0 au plancher, et leur cadre : 0 et le plancher toujours, puis, par
		ordre d'importance, ceux qui ne chevauchent pas un nombre déjà gardé. Combien tiennent dépend de la police du
		poste."""
		retenues: dict[int, QRectF] = {}
		for graduation, cadre in self.candidates():
			if (graduation in (0, int(PLANCHER))) or (all(not cadre.intersects(autre) for autre in retenues.values())):
				retenues[graduation] = cadre
		return [(str(graduation), cadre) for graduation, cadre in sorted(retenues.items(), reverse=True)]

	def paintEvent(self, _evenement: QPaintEvent) -> None:
		peintre = QPainter(self)
		disposition = self.disposition()
		for canal in disposition.canaux:
			peintre.fillRect(canal, self.palette().base())
		for indice, niveau in enumerate(self.niveaux):
			canal = disposition.canaux[indice]
			crete = self.cretes[indice]
			plus_claire = QColor(couleur(crete))
			plus_claire.setAlpha(110)
			peintre.fillRect(self._barre(canal, part(crete)), plus_claire)
			peintre.fillRect(self._barre(canal, part(niveau)), couleur(niveau))
			if indice < len(self.maintenues):
				gardee = self.maintenues[indice][0]
				peintre.setPen(QPen(couleur(gardee), 2))
				repere = self._barre(canal, part(gardee))
				if self.vertical:
					peintre.drawLine(repere.topLeft(), repere.topRight())
				else:
					peintre.drawLine(repere.topRight(), repere.bottomRight())
		trait = self.palette().mid().color()
		peintre.setPen(trait)
		for canal in disposition.canaux:
			peintre.drawRect(canal)
		self._peindre_l_echelle(peintre, disposition)
		peintre.end()

	def _peindre_l_echelle(self, peintre: QPainter, disposition: Disposition) -> None:
		echelle = disposition.echelle
		peintre.setPen(self.palette().mid().color())
		for graduation in GRADUATIONS:
			endroit = self.position(graduation, disposition)
			if self.vertical:
				peintre.drawLine(QPointF(echelle.left(), endroit), QPointF(echelle.left() + TRAIT, endroit))
				peintre.drawLine(QPointF(echelle.right() - TRAIT, endroit), QPointF(echelle.right(), endroit))
			else:
				peintre.drawLine(QPointF(endroit, echelle.top()), QPointF(endroit, echelle.top() + TRAIT))
		peintre.setFont(self.police)
		peintre.setPen(self.palette().windowText().color())
		centre = Qt.AlignmentFlag.AlignCenter
		for texte, cadre in self.etiquettes():
			peintre.drawText(cadre, centre, texte)
		for nom, cadre in disposition.noms:
			peintre.drawText(cadre, centre, nom)

	def _barre(self, canal: QRectF, fraction: float) -> QRectF:
		"""La barre du canal, remplie de cette fraction : de bas en haut, ou de gauche à droite."""
		if self.vertical:
			hauteur = canal.height() * fraction
			return QRectF(canal.left() + 1, canal.bottom() - hauteur, canal.width() - 2, hauteur)
		return QRectF(canal.left(), canal.top() + 1, canal.width() * fraction, canal.height() - 2)
