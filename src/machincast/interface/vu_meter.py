"""VU-mètre et bargraph de crête (https://github.com/dascritch/machincast/issues/24,
https://github.com/dascritch/machincast/issues/116).

Une barre par canal, du plancher (-60 dB) à 0 dB : le VU, niveau moyen (RMS), plein ; par-dessus, le bargraph de
crête, plus clair, et un repère qui garde la plus haute crête PEAK_HOLD secondes. Vert, orange au-delà de
-12 dB, rouge au-delà de -3 dB. Horizontal dans la pré-écoute, vertical dans la colonne de l'onglet Antenne. Un clic
émet clique : l'onglet Antenne s'en sert pour écouter l'antenne.

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

FLOOR = -60.0
PEAK_HOLD = 2.0
"""Secondes pendant lesquelles le repère garde la plus haute crête."""
GREEN, ORANGE, RED = QColor("#3c9d5a"), QColor("#e0a020"), QColor("#d03030")
TICKS = (0, -6, -12, -20, -30, -40, -50, -60)
"""Les graduations de l'échelle, en dB, chacune d'un trait."""
IMPORTANCE = (0, -60, -20, -6, -12, -40, -30, -50)
"""Les nombres de l'échelle, du plus important au moins important : 0 et le plancher sont toujours écrits, un
autre seulement s'il ne chevauche pas un nombre plus important."""
CHANNEL_NAMES = ("G", "D")
"""Les noms des canaux d'un son stéréo, sous le VU-mètre vertical."""
SCALE_SIZE = 7.0
"""Points de la police de l'échelle et des noms des canaux."""
LINE = 3.0
"""Pixels des traits de graduation."""
GAP = 2.0
"""Pixels entre l'échelle et les barres qui l'entourent."""


def colour(level: float) -> QColor:
	if level > -3:
		return RED
	if level > -12:
		return ORANGE
	return GREEN


def share(level: float) -> float:
	"""La part de la barre, de 0 au plancher à 1 à 0 dB."""
	return (max(FLOOR, min(0.0, level)) - FLOOR) / -FLOOR


@dataclass(frozen=True)
class Arrangement:
	"""Où se dessine chaque partie du VU-mètre."""

	channels: list[QRectF]
	"""La barre de chaque canal, pleine échelle."""
	scale: QRectF
	"""La bande de l'échelle : ses traits et ses nombres."""
	names: list[tuple[str, QRectF]]
	"""Le nom de chaque canal, sous sa barre ; vide s'il n'y en a pas."""


def _valid_list(levels: list[float]) -> list[float]:
	return [level for level in levels if not math.isnan(level)]


class VuMeter(QWidget):
	FLOOR = FLOOR
	clicked = Signal()

	def __init__(
		self, parent: QWidget | None = None, vertical: bool = False, clock: Callable[[], float] = time.monotonic
	) -> None:
		super().__init__(parent)
		self.vertical = vertical
		self.clock = clock
		self.levels: list[float] = []
		"""VU de chaque canal, en décibels ; vide sans son à montrer."""
		self.peaks: list[float] = []
		"""Crête de chaque canal, en décibels."""
		self.maintained: list[tuple[float, float]] = []
		"""Plus haute crête récente de chaque canal, et l'instant où elle a été vue."""
		self.font_face = QFont(self.font())
		self.font_face.setPointSizeF(SCALE_SIZE)
		self.setMinimumSize(24, 24)
		self.setToolTip("Niveau de chaque canal, en décibels")

	def display(self, levels: list[float], peaks: list[float] | None = None) -> None:
		self.levels = _valid_list(levels)
		self.peaks = _valid_list((peaks) or (levels))
		now = self.clock()
		if len(self.maintained) != len(self.peaks):
			self.maintained = [(peak, now) for peak in self.peaks]
		for index, peak in enumerate(self.peaks):
			kept, since = self.maintained[index]
			if (peak >= kept) or (now - since > PEAK_HOLD):
				self.maintained[index] = (peak, now)
		if not self.levels:
			self.maintained = []
		self.update()

	def mousePressEvent(self, event: QMouseEvent) -> None:
		if event.button() == Qt.MouseButton.LeftButton:
			self.clicked.emit()

	def arrangement(self) -> Arrangement:
		"""Sans son, la place de deux canaux : l'échelle ne bouge pas quand le son arrive."""
		count = len(self.levels)
		if count == 0:
			count = 2
		frame = QRectF(self.rect()).adjusted(1, 1, -1, -1)
		metrics = QFontMetricsF(self.font_face)
		if self.vertical:
			return self._vertical_layout(frame, count, metrics)
		return self._lying_layout(frame, count, metrics)

	def _vertical_layout(self, frame: QRectF, count: int, metrics: QFontMetricsF) -> Arrangement:
		stereo = count == len(CHANNEL_NAMES)
		name_height = 0.0
		if stereo:
			name_height = metrics.height()
		margin = metrics.height() / 2
		top, bottom = frame.top() + margin, frame.bottom() - max(margin, name_height)
		scale_width = metrics.horizontalAdvance(str(int(FLOOR))) + 2 * LINE + 4
		width = (frame.width() - scale_width - 2 * GAP) / count
		channels = []
		for index in range(count):
			left = frame.left() + index * width
			if (stereo) and (index == 1):
				left += scale_width + 2 * GAP
			channels.append(QRectF(left, top, width, bottom - top))
		scale = QRectF(frame.right() - scale_width, top, scale_width, bottom - top)
		names: list[tuple[str, QRectF]] = []
		if stereo:
			scale.moveLeft(channels[0].right() + GAP)
			names = [
				(name, QRectF(channel.left(), bottom, channel.width(), name_height))
				for name, channel in zip(CHANNEL_NAMES, channels, strict=True)
			]
		return Arrangement(channels, scale, names)

	def _lying_layout(self, frame: QRectF, count: int, metrics: QFontMetricsF) -> Arrangement:
		scale_height = metrics.height() + LINE
		left = frame.left() + metrics.horizontalAdvance(str(int(FLOOR))) / 2
		right = frame.right() - metrics.horizontalAdvance("0") / 2
		bottom = frame.bottom() - scale_height
		height = (bottom - frame.top()) / count
		channels = [QRectF(left, frame.top() + index * height, right - left, height) for index in range(count)]
		scale = QRectF(left, bottom, right - left, scale_height)
		return Arrangement(channels, scale, [])

	def position(self, level: float, arrangement: Arrangement | None = None) -> float:
		"""Où ce niveau se trouve sur les barres : son ordonnée, vertical, son abscisse, couché."""
		scale = (arrangement) or (self.arrangement())
		if self.vertical:
			return scale.scale.bottom() - share(level) * scale.scale.height()
		return scale.scale.left() + share(level) * scale.scale.width()

	def candidates(self) -> list[tuple[int, QRectF]]:
		"""Chaque graduation de l'échelle et le cadre de son nombre, du plus important au moins important
		(IMPORTANCE), qu'il tienne ou non."""
		arrangement = self.arrangement()
		metrics = QFontMetricsF(self.font_face)
		frames = []
		for tick in IMPORTANCE:
			text = str(tick)
			width, height = metrics.horizontalAdvance(text), metrics.height()
			place = self.position(tick, arrangement)
			if self.vertical:
				centre = QPointF(arrangement.scale.center().x(), place)
			else:
				centre = QPointF(place, arrangement.scale.top() + LINE + height / 2)
			frames.append((tick, QRectF(centre.x() - width / 2, centre.y() - height / 2, width, height)))
		return frames

	def captions(self) -> list[tuple[str, QRectF]]:
		"""Les nombres écrits sur l'échelle, de 0 au plancher, et leur cadre : 0 et le plancher toujours, puis, par
		ordre d'importance, ceux qui ne chevauchent pas un nombre déjà gardé. Combien tiennent dépend de la police du
		poste."""
		retained_list: dict[int, QRectF] = {}
		for tick, frame in self.candidates():
			if (tick in (0, int(FLOOR))) or (all(not frame.intersects(other) for other in retained_list.values())):
				retained_list[tick] = frame
		return [(str(tick), frame) for tick, frame in sorted(retained_list.items(), reverse=True)]

	def paintEvent(self, _event: QPaintEvent) -> None:
		painter = QPainter(self)
		arrangement = self.arrangement()
		for channel in arrangement.channels:
			painter.fillRect(channel, self.palette().base())
		for index, level in enumerate(self.levels):
			channel = arrangement.channels[index]
			peak = self.peaks[index]
			more_light = QColor(colour(peak))
			more_light.setAlpha(110)
			painter.fillRect(self._bar(channel, share(peak)), more_light)
			painter.fillRect(self._bar(channel, share(level)), colour(level))
			if index < len(self.maintained):
				kept = self.maintained[index][0]
				painter.setPen(QPen(colour(kept), 2))
				marker = self._bar(channel, share(kept))
				if self.vertical:
					painter.drawLine(marker.topLeft(), marker.topRight())
				else:
					painter.drawLine(marker.topRight(), marker.bottomRight())
		line = self.palette().mid().color()
		painter.setPen(line)
		for channel in arrangement.channels:
			painter.drawRect(channel)
		self._paint_scale(painter, arrangement)
		painter.end()

	def _paint_scale(self, painter: QPainter, arrangement: Arrangement) -> None:
		scale = arrangement.scale
		painter.setPen(self.palette().mid().color())
		for tick in TICKS:
			place = self.position(tick, arrangement)
			if self.vertical:
				painter.drawLine(QPointF(scale.left(), place), QPointF(scale.left() + LINE, place))
				painter.drawLine(QPointF(scale.right() - LINE, place), QPointF(scale.right(), place))
			else:
				painter.drawLine(QPointF(place, scale.top()), QPointF(place, scale.top() + LINE))
		painter.setFont(self.font_face)
		painter.setPen(self.palette().windowText().color())
		centre = Qt.AlignmentFlag.AlignCenter
		for text, frame in self.captions():
			painter.drawText(frame, centre, text)
		for name, frame in arrangement.names:
			painter.drawText(frame, centre, name)

	def _bar(self, channel: QRectF, fraction: float) -> QRectF:
		"""La barre du canal, remplie de cette fraction : de bas en haut, ou de gauche à droite."""
		if self.vertical:
			height = channel.height() * fraction
			return QRectF(channel.left() + 1, channel.bottom() - height, channel.width() - 2, height)
		return QRectF(channel.left(), channel.top() + 1, channel.width() * fraction, channel.height() - 2)
