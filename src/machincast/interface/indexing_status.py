"""Statut des indexations, menu « Maintenance » (https://github.com/dascritch/machincast/issues/392).

Une fenêtre qui compte, d'après la base, où en sont les indexations, et se met à jour toutes les deux secondes tant
qu'elle est ouverte, pour suivre une indexation en cours :

- les répertoires des banques actives, chacun compté une fois même s'il alimente plusieurs banques : parcourus depuis
  le dernier démarrage de Machin_indexer (bank_directories.scanned_at, noté par l'indexeur à la fin de chaque
  répertoire, après la ligne « start » du log), et encore à parcourir. Sans démarrage noté, par exemple purgé du log,
  un répertoire déjà parcouru une fois compte comme parcouru ;
- les sonores fichiers détectés, qui ne sont pas supprimés, en trois parts qui s'ajoutent : ceux qui n'ont eu
  aucune indexation (état aperçu, jamais vérifiés), ceux qui n'ont eu qu'une indexation sommaire (vérifiés,
  checked_at, sans audit), et ceux qui ont eu une indexation complète (audités, audited_at).

Sous les nombres, deux camemberts dessinés par la fenêtre elle-même (Pie) : un pour les répertoires, un pour les
sonores, chaque part avec sa légende, son nombre et sa proportion.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QPainter, QPaintEvent, QPalette
from PySide6.QtWidgets import QSizePolicy, QWidget

from machincast.i18n import _, date_and_hour
from machincast.indexer.__main__ import EXECUTABLE
from machincast.interface.ui.indexing_status import Ui_StatusWindow

REFRESH = 2000
"""Millisecondes entre deux relectures de la base."""

QUERY = """
WITH latest AS (
	SELECT max(logged_at) AS started_at FROM log WHERE kind = 'start' AND starts_with(message, %s || ' ')
),
directories AS (
	SELECT r.directory,
		bool_and((r.scanned_at IS NOT NULL) AND (r.scanned_at >= COALESCE((SELECT started_at FROM latest), '-infinity')))
			AS scanned
	FROM bank_directories r JOIN banks b ON b.id = r.bank_id
	WHERE b.deleted_at IS NULL
	GROUP BY r.directory
)
SELECT
	(SELECT started_at FROM latest),
	(SELECT count(*) FROM directories),
	(SELECT count(*) FROM directories WHERE scanned),
	count(*),
	count(*) FILTER (WHERE (checked_at IS NOT NULL) AND (audited_at IS NULL)),
	count(*) FILTER (WHERE audited_at IS NOT NULL)
FROM sounds
WHERE type = 'file' AND deleted_at IS NULL
"""


@dataclass(frozen=True)
class Status:
	started_at: datetime | None
	"""Le dernier démarrage noté de Machin_indexer ; None s'il n'y en a aucun dans le log."""
	directories: int
	scanned: int
	sounds: int
	summary: int
	"""Les sonores qui n'ont eu qu'une indexation sommaire."""
	complete: int

	@property
	def to_scan(self) -> int:
		return self.directories - self.scanned

	@property
	def not_indexed(self) -> int:
		return self.sounds - self.summary - self.complete


def read(connection: psycopg.Connection[TupleRow]) -> Status:
	with connection.transaction():
		line = connection.execute(QUERY, (EXECUTABLE,)).fetchone()
	assert line is not None
	started_at = line[0]
	if not isinstance(started_at, datetime):
		started_at = None
	numbers = []
	for value in line[1:]:
		numbers.append(int(str(value)))
	return Status(started_at, *numbers)


@dataclass(frozen=True)
class Slice:
	label: str
	value: int
	color: QColor


def share(value: int, total: int) -> str:
	"""« 12 (40 %) » ; « 0 » sans total."""
	if total == 0:
		return str(value)
	return _("{value} ({percent} %)").format(value=value, percent=round(100 * value / total))


def _legend(item: Slice, total: int) -> str:
	return _("{label}: {share}").format(label=item.label, share=share(item.value, total))


class Pie(QWidget):
	"""Un camembert et sa légende : chaque part, son nombre et sa proportion. Sans total, un disque vide et « aucun »."""

	def __init__(self, title: str, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.title = title
		self.slices: list[Slice] = []
		self.setMinimumSize(220, 260)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

	def set_slices(self, slices: list[Slice]) -> None:
		self.slices = slices
		total = self.total()
		lines = [self.title]
		for item in slices:
			lines.append(_legend(item, total))
		self.setToolTip("\n".join(lines))
		self.update()

	def total(self) -> int:
		total = 0
		for item in self.slices:
			total += item.value
		return total

	def legend(self) -> list[str]:
		total = self.total()
		lines = []
		for item in self.slices:
			lines.append(_legend(item, total))
		return lines

	def paintEvent(self, _event: QPaintEvent) -> None:
		with QPainter(self) as painter:
			self._paint(painter)

	def _paint(self, painter: QPainter) -> None:
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		metrics = painter.fontMetrics()
		line = metrics.height()
		legend_height = line * (len(self.slices) + 1) + 4
		side = max(10, min(self.width(), self.height() - legend_height - line) - 8)
		disc = QRectF((self.width() - side) / 2, line + 4, side, side)
		painter.drawText(QRectF(0, 0, self.width(), line), Qt.AlignmentFlag.AlignHCenter, self.title)
		total = self.total()
		painter.setPen(self.palette().color(QPalette.ColorRole.Mid))
		if total == 0:
			painter.setBrush(self.palette().color(QPalette.ColorRole.Base))
			painter.drawEllipse(disc)
		start = 90 * 16
		for item in self.slices:
			if (total > 0) and (item.value > 0):
				span = round(-360 * 16 * item.value / total)
				painter.setBrush(item.color)
				painter.drawPie(disc, start, span)
				start += span
		top = disc.bottom() + line / 2
		painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
		for index, item in enumerate(self.slices):
			y = top + index * line
			painter.setBrush(item.color)
			painter.drawRect(QRectF(8, y + line / 4, line / 2, line / 2))
			painter.drawText(QRectF(8 + line, y, self.width() - line - 8, line), self.legend()[index])


def _colors(widget: QWidget) -> tuple[QColor, QColor, QColor]:
	"""Fait, en partie, pas encore : la couleur d'accent du thème, plus claire, et une couleur neutre ; elles se
	lisent en clair comme en sombre."""
	accent = widget.palette().color(QPalette.ColorRole.Highlight)
	partial = QColor(accent)
	partial.setAlphaF(0.45)
	return accent, partial, widget.palette().color(QPalette.ColorRole.Mid)


class StatusWindow(QWidget):
	def __init__(
		self,
		connection: psycopg.Connection[TupleRow],
		parent: QWidget | None = None,
		reading: Callable[[psycopg.Connection[TupleRow]], Status] = read,
	) -> None:
		super().__init__(parent, Qt.WindowType.Window)
		self.ui = Ui_StatusWindow()
		self.ui.setupUi(self)
		self.connection = connection
		self.reading = reading
		self.directories_pie = Pie(_("Directories"), self)
		self.sounds_pie = Pie(_("Sounds"), self)
		self.ui.charts.addWidget(self.directories_pie)
		self.ui.charts.addWidget(self.sounds_pie)
		self.ui.shut_down.clicked.connect(self.close)
		self.timer = QTimer(self)
		self.timer.setInterval(REFRESH)
		self.timer.timeout.connect(self.refresh)
		self.status: Status | None = None

	def open_(self) -> None:
		self.refresh()
		self.show()
		self.raise_()
		self.activateWindow()
		self.timer.start()

	def refresh(self) -> None:
		try:
			status = self.reading(self.connection)
		except psycopg.Error as error:
			self.ui.since.setText(_("Status unreadable: {error}").format(error=error))
			return
		self.status = status
		ui = self.ui
		ui.to_scan.setText(share(status.to_scan, status.directories))
		ui.scanned.setText(share(status.scanned, status.directories))
		ui.found.setText(str(status.sounds))
		ui.summary.setText(share(status.summary, status.sounds))
		ui.complete.setText(share(status.complete, status.sounds))
		done, partial, none = _colors(self)
		self.directories_pie.set_slices(
			[Slice(_("Scanned"), status.scanned, done), Slice(_("To scan"), status.to_scan, none)]
		)
		self.sounds_pie.set_slices(
			[
				Slice(_("Full audit"), status.complete, done),
				Slice(_("Quick indexing only"), status.summary, partial),
				Slice(_("Not indexed yet"), status.not_indexed, none),
			]
		)
		if status.started_at is None:
			ui.since.setText(_("No start of Machin indexer in the log: a directory scanned once counts as scanned."))
		else:
			ui.since.setText(
				_("Directories scanned since the last start of Machin indexer, on {date}.").format(
					date=date_and_hour(status.started_at)
				)
			)

	def closeEvent(self, event: QCloseEvent) -> None:
		self.timer.stop()
		super().closeEvent(event)
