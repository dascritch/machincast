"""Calendrier de la grille (https://github.com/dascritch/machincast/issues/36,
https://github.com/dascritch/machincast/issues/118, spec § 8.2).

Un onglet de la fenêtre, ouvert depuis le menu « Affichage », qui montre à la fois ce qui est prévu et ce qui a été
diffusé, en vue semaine (du lundi au dimanche) ou en vue jour, de 0 h à 24 h, jusqu'à 28 jours après aujourd'hui.
Il ne remonte pas avant la durée de péremption des préférences (https://github.com/dascritch/machincast/issues/269) :
Machin purge efface de la base ce qui est plus vieux (https://github.com/dascritch/machincast/issues/268). En vue
semaine, les jours d'avant sont grisés, vides.

- Prévu : chaque occurrence d'un événement, récurrences comprises, et ce qui en joue
  (machincast.player.grid.plan). Un bloc qu'un autre événement masque en entier est estompé ; en partie, seuls ses
  moments à l'antenne sont pleins. Une occurrence de 24 heures ou plus, et un fil musical permanent, vont dans la bande
  de la journée entière, entre le nom du jour et les heures. Deux blocs qui se chevauchent se placent côte à côte.
  Un événement supprimé garde ses occurrences d'avant sa suppression, jusqu'à leur péremption.
- Diffusé : l'airplay, en bandes étroites à droite de chaque jour. Les passages successifs d'un même événement font
  une seule bande ; un passage sans fin dure jusqu'au passage suivant, ou jusqu'à maintenant pour le dernier.
- Une case par priorité montre ou cache ses blocs et ses bandes ; ce qui joue ne change pas.
- Survoler un bloc ou une bande donne son infobulle ; un double-clic ouvre son événement (signal ouverte). Un clic
  sur une heure libre, pas encore passée, demande la création d'un événement sur son heure entière (requested_creation).
- Sessions sautées (https://github.com/dascritch/machincast/issues/273) : le clic droit sur une session à venir d'un
  événement récurrent la saute, seule ou avec les suivantes jusqu'à un jour choisi (dialogs.choose_day) ; sautée,
  elle reste dessinée, hachurée, ne cache rien, se clique comme une heure libre, et se rétablit au clic droit, sauf si
  un événement de même priorité a pris sa place. Chaque saut s'annonce (annonce), et demande à Machin player de
  relire la grille (modified_grid).

Navigation (https://github.com/dascritch/machincast/issues/326) : en tête de ligne, « Aujourd'hui », puis « ◀ Avant »
et « Après ▶ », d'une semaine ou d'un jour selon la vue, que choisit une liste déroulante, « Jour » ou « Semaine ».
Zoom des heures : la liste « 🔍 » montre 4, 8, 12 ou 24 heures dans la hauteur de la grille (ZOOMS, 12 par défaut) ;
Maj + molette, dans la grille, passe au zoom voisin. Le zoom garde l'heure du haut de la grille.

Le calendrier se relit à l'ouverture de son onglet, à chaque changement de période et par « Rafraîchir les onglets » ;
jamais en boucle.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
	QBrush,
	QColor,
	QContextMenuEvent,
	QHelpEvent,
	QIcon,
	QMouseEvent,
	QPainter,
	QPaintEvent,
	QPen,
	QPixmap,
	QWheelEvent,
)
from PySide6.QtWidgets import (
	QCheckBox,
	QComboBox,
	QHBoxLayout,
	QLabel,
	QMenu,
	QPushButton,
	QScrollArea,
	QStyle,
	QToolTip,
	QVBoxLayout,
	QWidget,
)

from machincast.clock import Clock
from machincast.conversion import text_or_none
from machincast.i18n import _, ngettext, pgettext
from machincast.interface import dialogs, preferences
from machincast.interface.display import MONTH
from machincast.interface.sessions import Session, overlapped, reinstate
from machincast.player.grid import (
	DAY_NAMES,
	RANKS,
	Event,
	Planned,
	Priority,
	plan,
	read_grid,
	sessions,
	wall_hour,
)

Connection = psycopg.Connection[TupleRow]

PRIORITIES = (
	(Priority.SPECIAL, _("Special")),
	(Priority.SHOW, _("Show")),
	(Priority.BACKGROUND_PROGRAMMING, _("Background programming")),
)
"""Les priorités de la grille, de la plus haute à la plus basse, et le nom de leur case."""
NAMES = dict(PRIORITIES)
COLOURS = {
	Priority.SPECIAL: QColor("#f08c8c"),
	Priority.SHOW: QColor("#8cb4f0"),
	Priority.BACKGROUND_PROGRAMMING: QColor("#8fd19e"),
}
TINTS = {Priority.SPECIAL: _("red"), Priority.SHOW: _("blue"), Priority.BACKGROUND_PROGRAMMING: _("green")}
"""Le nom de la couleur de chaque priorité, pour l'infobulle de sa case (https://github.com/dascritch/machincast/issues/293)."""
PLURALS = {
	Priority.SPECIAL: _("specials"),
	Priority.SHOW: _("shows"),
	Priority.BACKGROUND_PROGRAMMING: _("background programmings"),
}
SQUARE_SIZE = 14
"""Côté, en pixels, du carré de couleur devant le nom de la case d'une priorité."""
DELETED = QColor("#b0b0b0")
"""La couleur de l'airplay d'un événement supprimé."""
TEXT = QColor(0x20, 0x20, 0x20)
FADE = 70
"""Opacité, sur 255, de ce qu'un autre événement masque."""
SCOPE = timedelta(days=28)
"""Le calendrier va jusqu'à PORTEE après aujourd'hui ; avant, jusqu'à la durée de péremption."""
OUTDATED = QColor(128, 128, 128, 90)
"""Le voile d'un jour d'avant la durée de péremption, dont la base n'a plus rien."""
ONE_HOUR = timedelta(hours=1)
"""Un événement créé depuis le calendrier occupe l'heure entière cliquée : 13:37 donne 13:00 – 14:00."""
ONE_DAY = timedelta(days=1)
MINIMAL_HEIGHT = 16
"""Pixels d'une heure au moins, quel que soit le zoom : la place de son libellé."""
ZOOMS = (4, 8, 12, 24)
"""Les heures que montre la hauteur de la grille, au choix du zoom (https://github.com/dascritch/machincast/issues/326)."""
DEFAULT_ZOOM = 12
MAGNIFIER = "🔍"
ZOOM_TOOLTIP = _("Hours shown in the height of the grid; also Shift + wheel in the grid")
VIEWS = ((_("Day"), False), (_("Week"), True))
"""La liste déroulante des vues : son texte, et s'il s'agit de la vue semaine."""
BEFORE = _("◀ Before")
AFTER = _("After ▶")
FIRST_HOUR = 7
"""L'heure en haut de la grille à l'ouverture du calendrier."""
MARGIN = 52
"""Largeur de la colonne des heures, à gauche."""
PLANNED_SHARE = 0.72
"""Part de la largeur d'un jour pour les blocs prévus ; le reste, moins un écart, pour l'airplay."""
GAP = 4
NAME_HEIGHT = 24
LINE_HEIGHT = 22
"""Hauteur d'un bloc de la journée entière."""
OPEN = _("Double-click: open the event")
DELETED_EVENT = _("Deleted event")
MASK = _("by another event")
DELETED_REMAINDER = _("the rest is no longer planned")
SKIP = _("Skip this session")
SKIP_UNTIL = _("Skip the sessions until…")
REINSTATE = _("Reinstate this session")
SKIPPED = _("Skipped session")


def number(day: date) -> str:
	"""Le jour du mois : « 1er » en français pour le premier."""
	if day.day == 1:
		return pgettext("first day of the month", "1")
	return str(day.day)


def day_label(day: date) -> str:
	"""« mardi 20 », « dimanche 1er »."""
	return _("{weekday} {day}").format(weekday=DAY_NAMES[day.weekday()], day=number(day))


def day_and_month(day: date) -> str:
	"""« mardi 20 octobre »."""
	return _("{day} {month}").format(day=day_label(day), month=MONTH[day.month - 1])


def long_date(day: date) -> str:
	"""« mardi 20 octobre 2026 »."""
	return _("{date} {year}").format(date=day_and_month(day), year=day.year)


def week_title(monday: date) -> str:
	"""« Semaine du lundi 19 au dimanche 25 octobre 2026 » ; le mois, ou l'année, du lundi quand ils changent."""
	sunday = monday + timedelta(days=6)
	departure = number(monday)
	if monday.year != sunday.year:
		departure = _("{day} {month} {year}").format(day=departure, month=MONTH[monday.month - 1], year=monday.year)
	elif monday.month != sunday.month:
		departure = _("{day} {month}").format(day=departure, month=MONTH[monday.month - 1])
	return _("Week from Monday {start} to Sunday {day} {month} {year}").format(
		start=departure, day=number(sunday), month=MONTH[sunday.month - 1], year=sunday.year
	)


def schedule(day: date, moment: datetime) -> str:
	"""« 07:00 », ou « 24:00 » pour la fin du jour."""
	if moment == midnight(day + ONE_DAY):
		return "24:00"
	return f"{moment:%H:%M}"


def midnight(day: date) -> datetime:
	return datetime.combine(day, time())


def _cross(
	moments: Iterable[tuple[datetime, datetime]], start: datetime, end: datetime
) -> tuple[tuple[datetime, datetime], ...]:
	crossed = ((max(departure, start), min(arrival, end)) for departure, arrival in moments)
	return tuple((departure, arrival) for departure, arrival in crossed if departure < arrival)


@dataclass(frozen=True)
class Block:
	"""Une occurrence prévue, sur un jour du calendrier."""

	planned: Planned
	day: date
	start: datetime
	end: datetime
	plays: tuple[tuple[datetime, datetime], ...]
	"""Ses moments à l'antenne, ce jour-là."""
	whole_day: bool
	"""Dans la bande de la journée entière."""
	public_name: str | None

	@property
	def event(self) -> Event:
		return self.planned.occurrence.event

	@property
	def skipped(self) -> bool:
		return self.planned.skipped

	@property
	def state(self) -> str:
		if self.skipped:
			return _("skipped")
		if not self.plays:
			return _("faded")
		if self.plays == ((self.start, self.end),):
			return "joue"
		return _("partly plays")

	def tooltip(self) -> str:
		event = self.event
		name = event.name
		if self.public_name:
			name = f"{name} ({self.public_name})"
		lines = [f"{name} — {NAMES[event.priority]}", self._schedules()]
		if event.days:
			lines.append(_("Comes back on {days}").format(days=", ".join(DAY_NAMES[day] for day in sorted(event.days))))
		if event.deleted_at is not None:
			deleted = wall_hour(event.deleted_at)
			lines.append(
				_("Deleted on {day_and_month} at {deleted:%H:%M}: {deleted_remainder}").format(
					day_and_month=day_and_month(deleted.date()), deleted=deleted, deleted_remainder=DELETED_REMAINDER
				)
			)
		lines += [self._what_plays(), OPEN]
		return "\n".join(lines)

	def tooltip_to(self, now: datetime) -> str:
		"""L'infobulle ; celle d'une session sautée à venir dit comment la rétablir."""
		text = self.tooltip()
		if (self.skipped) and (_upcoming(self, now)):
			return text.replace(
				f"\n{SKIPPED}\n",
				_("\n{skipped}: “{reinstate}” with a right click\n").format(skipped=SKIPPED, reinstate=REINSTATE),
			)
		return text

	def _schedules(self) -> str:
		occurrence = self.planned.occurrence
		if occurrence.start is None:
			return _("Permanent background programming")
		departure = f"{day_and_month(occurrence.start.date())}, "
		if occurrence.end is None:
			return _("{departure}from {start:%H:%M}, endless: until its list runs out").format(
				departure=departure, start=occurrence.start
			)
		if occurrence.end.date() == occurrence.start.date():
			return f"{departure}{occurrence.start:%H:%M} – {occurrence.end:%H:%M}"
		return f"{departure}{occurrence.start:%H:%M} – {day_and_month(occurrence.end.date())}, {occurrence.end:%H:%M}"

	def _what_plays(self) -> str:
		state = self.state
		if state == "sauté":
			return SKIPPED
		if state == "joue":
			return _("Plays in full")
		if state == "estompé":
			return _("Hidden in full {mask}").format(mask=MASK)
		moments = _(" and ").join(
			_("from {schedule} to {schedule2}").format(schedule=schedule(self.day, d), schedule2=schedule(self.day, f))
			for d, f in self.plays
		)
		return _("Plays {moments}; hidden the rest of the time {mask}").format(moments=moments, mask=MASK)


@dataclass(frozen=True)
class Play:
	start: datetime
	end: datetime | None
	id_event: int | None
	name: str | None
	priority: Priority | None


@dataclass(frozen=True)
class Strip:
	"""Des passages successifs d'un même événement, sur un jour du calendrier."""

	day: date
	start: datetime
	end: datetime
	id_event: int | None
	name: str
	priority: Priority | None
	plays: int
	departure: datetime
	"""Début du premier passage, à la seconde."""
	arrival: datetime | None
	"""Fin du dernier passage, à la seconde ; None pour un passage en cours."""

	def tooltip(self) -> str:
		departure = f"{day_and_month(self.departure.date())}, "
		if self.arrival is None:
			moments = _("{departure}since {departure2:%H:%M:%S}, ongoing").format(
				departure=departure, departure2=self.departure
			)
		elif self.arrival.date() == self.departure.date():
			moments = f"{departure}{self.departure:%H:%M:%S} – {self.arrival:%H:%M:%S}"
		else:
			moments = (
				f"{departure}{self.departure:%H:%M:%S} – {day_and_month(self.arrival.date())}, {self.arrival:%H:%M:%S}"
			)
		plays = ngettext("{count} play", "{count} plays", self.plays).format(count=self.plays)
		lines = [_("Played: {name}").format(name=self.name), moments, plays]
		if self.id_event is not None:
			lines.append(OPEN)
		return "\n".join(lines)


def split(planned_list: Iterable[Planned], days: list[date], public_names: dict[int, str | None]) -> list[Block]:
	"""Les blocs de chaque jour : une occurrence qui passe minuit en donne un par jour qu'elle touche."""
	blocks = []
	for planned in planned_list:
		whole_day = (planned.occurrence.start is None) or (planned.end - planned.start >= ONE_DAY)
		for day in days:
			start, end = max(planned.start, midnight(day)), min(planned.end, midnight(day + ONE_DAY))
			if start >= end:
				continue
			public_name = public_names.get(planned.occurrence.event.id)
			blocks.append(Block(planned, day, start, end, _cross(planned.plays, start, end), whole_day, public_name))
	return sorted(blocks, key=lambda b: (b.day, b.start, RANKS[b.event.priority], b.event.id))


def read_plays(connection: Connection, de: datetime, a: datetime, first: datetime | None = None) -> list[Play]:
	"""Les passages commencés dans la période, ou la veille : ceux-là peuvent encore la toucher ; jamais avant le
	premier moment montré, que la purge efface."""
	since = de - ONE_DAY
	if first is not None:
		since = max(since, first)
	lines = connection.execute(
		"SELECT d.logged_at, f.logged_at, d.event_id, e.internal_name, e.priority::text"
		" FROM airplay d"
		" LEFT JOIN airplay f ON (f.play_id = d.play_id) AND (f.line_type = 'end')"
		" LEFT JOIN events e ON e.id = d.event_id"
		" WHERE (d.line_type = 'start') AND (d.logged_at >= %s) AND (d.logged_at < %s)"
		" ORDER BY d.logged_at, d.id",
		(since.astimezone(), a.astimezone()),
	).fetchall()
	plays = []
	for start, end, id_event, name, priority in lines:
		assert isinstance(start, datetime)
		arrival = None
		if isinstance(end, datetime):
			arrival = wall_hour(end)
		identifier = None
		if id_event is not None:
			identifier = int(str(id_event))
		rank = None
		if priority is not None:
			rank = Priority(str(priority))
		plays.append(Play(wall_hour(start), arrival, identifier, text_or_none(name), rank))
	return plays


def strips(plays: list[Play], days: list[date], now: datetime) -> list[Strip]:
	"""Les passages successifs d'un même événement réunis, puis découpés par jour.

	Un passage sans fin dure jusqu'au passage suivant ; le dernier, s'il n'a pas de fin, est en cours."""
	groups: list[tuple[Play, datetime, datetime | None, int]] = []
	for index, play in enumerate(plays):
		arrival = play.end
		if (arrival is None) and (index + 1 < len(plays)):
			arrival = plays[index + 1].start
		if (groups) and (groups[-1][0].id_event == play.id_event):
			first, departure, _arrival, count = groups[-1]
			groups[-1] = (first, departure, arrival, count + 1)
			continue
		groups.append((play, play.start, arrival, 1))
	found_list = []
	for play, departure, arrival, count in groups:
		end = (arrival) or (now)
		for day in days:
			day_start, day_end = max(departure, midnight(day)), min(end, midnight(day + ONE_DAY))
			if day_start >= day_end:
				continue
			name = (play.name) or (DELETED_EVENT)
			found_list.append(
				Strip(
					day,
					day_start,
					day_end,
					play.id_event,
					name,
					play.priority,
					count,
					departure,
					arrival,
				)
			)
	return found_list


def columns(blocks: list[Block]) -> dict[Block, tuple[int, int]]:
	"""La colonne de chaque bloc d'un jour, et le nombre de colonnes de son groupe : ceux qui se chevauchent se
	placent côte à côte, à la première colonne libre."""
	places: dict[Block, tuple[int, int]] = {}
	group: list[tuple[Block, int]] = []
	group_end: datetime | None = None
	for block in sorted(blocks, key=lambda b: (b.start, b.end)):
		if (group_end is not None) and (block.start >= group_end):
			_put(group, places)
			group, group_end = [], None
		busy_list = {column for other, column in group if other.end > block.start}
		column = next(number for number in range(len(group) + 1) if number not in busy_list)
		group.append((block, column))
		group_end = max((group_end) or (block.end), block.end)
	_put(group, places)
	return places


def _put(group: list[tuple[Block, int]], places: dict[Block, tuple[int, int]]) -> None:
	count = max((column for _block, column in group), default=-1) + 1
	for block, column in group:
		places[block] = (column, count)


def colour_square(colour: QColor) -> QIcon:
	"""Un carré plein de la couleur, bordé comme un bloc du calendrier."""
	image = QPixmap(SQUARE_SIZE, SQUARE_SIZE)
	image.fill(Qt.GlobalColor.transparent)
	painter = QPainter(image)
	painter.fillRect(0, 0, SQUARE_SIZE, SQUARE_SIZE, colour)
	painter.setPen(QPen(colour.darker(140)))
	painter.drawRect(0, 0, SQUARE_SIZE - 1, SQUARE_SIZE - 1)
	painter.end()
	return QIcon(image)


class Calendar(QWidget):
	opened = Signal(str, int, str)
	"""Double-clic sur un bloc ou une bande : genre, identifiant et nom de son événement."""
	requested_creation = Signal(object)
	"""Clic sur une heure libre : le début, en heure murale, de l'événement à créer."""
	announces = Signal(str)
	"""Ce qu'a fait un clic droit, pour la barre d'état."""
	modified_grid = Signal()
	"""Une session sautée ou rétablie : Machin player doit relire la grille."""

	def __init__(self, connection: Connection, clock: Clock, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.connection = connection
		self.clock = clock
		self._week = True
		self._start = self._monday(self._today())
		self._blocks: list[Block] = []
		self._strips: list[Strip] = []
		self.visible_hours = DEFAULT_ZOOM
		self.top_hour: float = FIRST_HOUR
		"""L'heure au bord haut de la grille, que gardent un zoom et un changement de taille."""
		self._adjustment = False
		"""La hauteur de la grille change : la barre de défilement bouge, sans que l'heure du haut change."""
		self.today = QPushButton(_("Today"))
		self.previous = QPushButton(BEFORE)
		self.following = QPushButton(AFTER)
		self.title = QLabel()
		font_face = self.title.font()
		font_face.setBold(True)
		self.title.setFont(font_face)
		self.view = QComboBox()
		for text, week in VIEWS:
			self.view.addItem(text, week)
		self.view.setToolTip(_("View of a day or a week"))
		self.magnifier = QLabel(MAGNIFIER)
		self.zoom = QComboBox()
		for hours in ZOOMS:
			self.zoom.addItem(_("{hours}h view").format(hours=hours), hours)
		self.zoom.setCurrentIndex(ZOOMS.index(DEFAULT_ZOOM))
		self.magnifier.setBuddy(self.zoom)
		self.magnifier.setToolTip(ZOOM_TOOLTIP)
		self.zoom.setToolTip(ZOOM_TOOLTIP)
		self.boxes: dict[Priority, QCheckBox] = {}
		bar = QHBoxLayout()
		for widget in (self.today, self.previous, self.following):
			bar.addWidget(widget)
		bar.addWidget(self.title, 1)
		for priority, name in PRIORITIES:
			ticked = QCheckBox(name)
			# La couleur de ses blocs, devant son nom (https://github.com/dascritch/machincast/issues/293).
			ticked.setIcon(colour_square(COLOURS[priority]))
			ticked.setToolTip(
				_("Show or hide the {plurals}, in {tints}").format(plurals=PLURALS[priority], tints=TINTS[priority])
			)
			ticked.setChecked(True)
			ticked.toggled.connect(self._apply_filter)
			self.boxes[priority] = ticked
			bar.addWidget(ticked)
		bar.addWidget(self.view)
		bar.addWidget(self.magnifier)
		bar.addWidget(self.zoom)
		self.previous.clicked.connect(lambda: self._advance(-1))
		self.following.clicked.connect(lambda: self._advance(1))
		self.today.clicked.connect(self._come_back)
		self.view.activated.connect(lambda index: self._change_view(VIEWS[index][1]))
		self.zoom.activated.connect(lambda index: self.zoom_in(ZOOMS[index]))
		self.header = Header(self)
		self.grid = Grid(self)
		self.scrolling = QScrollArea()
		self.scrolling.setWidget(self.grid)
		self.scrolling.setWidgetResizable(True)
		self.scrolling.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
		# L'en-tête s'aligne sur les jours de la grille, que la barre de défilement rétrécit.
		scrolling_bar = self.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
		self.header.setContentsMargins(0, 0, scrolling_bar + 2 * self.scrolling.frameWidth(), 0)
		arrangement = QVBoxLayout(self)
		arrangement.addLayout(bar)
		arrangement.addWidget(self.header)
		arrangement.addWidget(self.scrolling, 1)
		# La hauteur d'une heure suit celle de la grille visible : elle change avec la fenêtre.
		self.scrolling.viewport().installEventFilter(self)
		self.scrolling.verticalScrollBar().valueChanged.connect(self._follow_scrolling)
		self.refresh()
		self._adjust_height()

	def hour_height(self) -> float:
		"""Les pixels d'une heure : la hauteur visible de la grille, moins le trait de minuit en bas, partagée entre
		les heures du zoom."""
		return max(MINIMAL_HEIGHT, (self.scrolling.viewport().height() - 1) / self.visible_hours)

	def zoom_in(self, hours: int) -> None:
		"""Montre ces heures dans la hauteur de la grille, en gardant l'heure du haut."""
		self.visible_hours = hours
		self.zoom.setCurrentIndex(ZOOMS.index(hours))
		self._adjust_height()

	def zoom_in_notch(self, more_near: bool) -> None:
		"""Le zoom voisin : moins d'heures, plus près, ou plus d'heures ; rien au-delà des bouts."""
		rank = ZOOMS.index(self.visible_hours) + (-1 if more_near else 1)
		if 0 <= rank < len(ZOOMS):
			self.zoom_in(ZOOMS[rank])

	def _adjust_height(self) -> None:
		"""La hauteur de la grille selon le zoom et la place visible, puis l'heure du haut à sa place, si la grille
		descend jusque-là ; sinon, le bas de la grille au bas de la place."""
		self._adjustment = True
		try:
			self.grid.setFixedHeight(int(24 * self.hour_height()) + 1)
			# La barre de défilement prend aussitôt la nouvelle hauteur : la position suivante n'est pas
			# bornée par l'ancienne.
			self.scrolling.setWidgetResizable(True)
			self.scrolling.verticalScrollBar().setValue(round(self.top_hour * self.hour_height()))
		finally:
			self._adjustment = False
		self.grid.update()

	def _follow_scrolling(self, value: int) -> None:
		"""Défilée à la main ou à la molette, la grille a une autre heure en haut."""
		if not self._adjustment:
			self.top_hour = value / self.hour_height()

	def eventFilter(self, object_: QObject, event: QEvent) -> bool:
		if (object_ is self.scrolling.viewport()) and (event.type() == QEvent.Type.Resize):
			self._adjust_height()
		return False

	def _today(self) -> date:
		return wall_hour(self.clock.now()).date()

	@staticmethod
	def _monday(day: date) -> date:
		return day - timedelta(days=day.weekday())

	def now(self) -> datetime:
		return wall_hour(self.clock.now())

	def days(self) -> list[date]:
		count = 1
		if self._week:
			count = 7
		return [self._start + timedelta(days=gap) for gap in range(count)]

	def first_day(self) -> date:
		"""Le premier jour que montre le calendrier : la base n'a plus rien d'avant la durée de péremption."""
		return self._today() - timedelta(days=preferences.retention())

	def outdated_days(self) -> list[date]:
		"""Les jours montrés d'avant le premier jour : grisés, vides."""
		return [day for day in self.days() if day < self.first_day()]

	def blocks(self) -> list[Block]:
		"""Les blocs des heures, des priorités cochées."""
		return [block for block in self._blocks if (not block.whole_day) and (self._shown(block.event.priority))]

	def whole_day(self) -> list[Block]:
		"""Les blocs de la journée entière, des priorités cochées."""
		return [block for block in self._blocks if (block.whole_day) and (self._shown(block.event.priority))]

	def strips(self) -> list[Strip]:
		"""L'airplay des priorités cochées ; celui d'un événement effacé de la base est toujours montré."""
		return [strip for strip in self._strips if (strip.priority is None) or (self._shown(strip.priority))]

	def _shown(self, priority: Priority) -> bool:
		return self.boxes[priority].isChecked()

	def refresh(self) -> None:
		"""Relit la grille et l'airplay de la période, ramenée au premier jour si la péremption l'a dépassée."""
		self._bound()
		self._present()
		outdated_list = set(self.outdated_days())
		days = [day for day in self.days() if day not in outdated_list]
		self._blocks, self._strips = [], []
		if days != []:
			self._reread(days)
		self._apply_filter()

	def _reread(self, days: list[date]) -> None:
		de, a = midnight(days[0]), midnight(days[-1] + ONE_DAY)
		with self.connection.transaction():
			events = read_grid(self.connection, deleted_list=True)
			public_names = {
				int(str(identifier)): text_or_none(public_name)
				for identifier, public_name in self.connection.execute("SELECT id, public_name FROM events")
			}
			plays = read_plays(self.connection, de, a, midnight(self.first_day()))
		self._blocks = split(plan(events, de, a), days, public_names)
		self._strips = strips(plays, days, self.now())

	def _apply_filter(self) -> None:
		self.header.reread()
		self.grid.update()

	def _advance(self, direction: int) -> None:
		self._start += direction * timedelta(days=len(self.days()))
		self.refresh()

	def _come_back(self) -> None:
		self._start = self._today()
		if self._week:
			self._start = self._monday(self._start)
		self.refresh()

	def _change_view(self, week: bool) -> None:
		"""La vue jour montre aujourd'hui s'il est dans la semaine montrée, sinon son lundi."""
		today = self._today()
		if week:
			self._start = self._monday(self._start)
		elif today in self.days():
			self._start = today
		self._week = week
		self.refresh()

	# ─── Sessions sautées (https://github.com/dascritch/machincast/issues/273) ───

	def skip(self, block: Block) -> None:
		"""Saute la session du bloc."""
		start = block.planned.occurrence.start
		assert start is not None
		self._skip(block.event, [start])

	def skip_until(self, block: Block) -> None:
		"""Saute la session du bloc, et les suivantes jusqu'au jour choisi, compris."""
		start = block.planned.occurrence.start
		assert start is not None
		name = block.event.name
		text = _("Skip the sessions of “{name}” from {day_and_month}, until:").format(
			name=name, day_and_month=day_and_month(start.date())
		)
		last = dialogs.choose_day(self, _("Skip sessions"), text, start.date())
		if last is None:
			return
		# Les sessions déjà sautées le restent, sans compter de nouveau.
		to_skip = [
			departure
			for departure, _end in sessions(block.event, start.date(), last + ONE_DAY)
			if departure.date() not in block.event.skipped_list
		]
		self._skip(block.event, to_skip)

	def _skip(self, event: Event, starts: list[datetime]) -> None:
		with self.connection.transaction():
			for start in starts:
				self.connection.execute(
					"INSERT INTO event_skips (event_id, day) VALUES (%s, %s) ON CONFLICT DO NOTHING",
					(event.id, start.date()),
				)
		first, last = starts[0], starts[-1]
		text = _("Session of “{name}” of {day_and_month} at {first:%H:%M} skipped.").format(
			name=event.name, day_and_month=day_and_month(first.date()), first=first
		)
		if len(starts) > 1:
			text = _("{count} sessions of “{name}” skipped, from {day_and_month} to {day_and_month2}.").format(
				count=len(starts),
				name=event.name,
				day_and_month=day_and_month(first.date()),
				day_and_month2=day_and_month(last.date()),
			)
		self._changed_grid(text)

	def reinstate(self, block: Block) -> None:
		"""Rétablit la session sautée du bloc, sauf si un événement de même priorité a pris sa place
		(machincast.interface.sessions)."""
		occurrence = block.planned.occurrence
		assert occurrence.start is not None
		session = Session(occurrence.event, occurrence.start, occurrence.end)
		name, day = session.event.name, session.start.date()
		with self.connection.transaction():
			found = overlapped(self.connection, session, self.now())
			if found is None:
				reinstate(self.connection, session)
		if found is not None:
			other, instant = found
			self.announces.emit(
				_(
					"Session of “{name}” of {day_and_month} not reinstated: it would overlap “{name2}” at "
					"{instant:%H:%M}."
				).format(name=name, day_and_month=day_and_month(day), name2=other.name, instant=instant)
			)
			return
		self._changed_grid(
			_("Session of “{name}” of {day_and_month} at {start:%H:%M} reinstated.").format(
				name=name, day_and_month=day_and_month(day), start=session.start
			)
		)

	def _changed_grid(self, text: str) -> None:
		self.refresh()
		self.announces.emit(text)
		self.modified_grid.emit()

	def _bound(self) -> None:
		"""Une période tout entière d'avant le premier jour, après une durée de péremption raccourcie, revient à
		celle du premier jour."""
		first = self.first_day()
		if self.days()[-1] >= first:
			return
		self._start = first
		if self._week:
			self._start = self._monday(first)

	def _present(self) -> None:
		period = timedelta(days=len(self.days()))
		today = self._today()
		self.title.setText(long_date(self._start))
		self.previous.setToolTip(_("Previous day"))
		self.following.setToolTip(_("Next day"))
		if self._week:
			self.title.setText(week_title(self._start))
			self.previous.setToolTip(_("Previous week"))
			self.following.setToolTip(_("Next week"))
		# Une période se montre tant qu'elle touche les jours d'après le premier, et les PORTEE jours après aujourd'hui.
		self.previous.setEnabled(self._start - timedelta(days=1) >= self.first_day())
		self.following.setEnabled(self._start + period <= today + SCOPE)
		self.view.setCurrentIndex([week for _text, week in VIEWS].index(self._week))


def _day_x(widget: QWidget, count: int) -> list[float]:
	"""Le bord gauche de chaque jour, et le bord droit du dernier."""
	width = (widget.contentsRect().width() - MARGIN) / count
	return [MARGIN + index * width for index in range(count + 1)]


class Header(QWidget):
	"""Le nom des jours, et la bande de la journée entière."""

	def __init__(self, calendar: Calendar) -> None:
		super().__init__(calendar)
		self.calendar = calendar

	def labels(self) -> list[str]:
		return [day_label(day) for day in self.calendar.days()]

	def reread(self) -> None:
		by_day = [sum(1 for b in self.calendar.whole_day() if b.day == day) for day in self.calendar.days()]
		self.setFixedHeight(NAME_HEIGHT + max([1, *by_day]) * LINE_HEIGHT + GAP)
		self.update()

	def rectangle(self, block: Block) -> QRectF:
		days = self.calendar.days()
		x = _day_x(self, len(days))
		index = days.index(block.day)
		rank = [b for b in self.calendar.whole_day() if b.day == block.day].index(block)
		y = NAME_HEIGHT + rank * LINE_HEIGHT
		return QRectF(x[index] + 1, y + 1, x[index + 1] - x[index] - 2, LINE_HEIGHT - 2)

	def _block_in(self, point: QPointF) -> Block | None:
		return next((b for b in self.calendar.whole_day() if self.rectangle(b).contains(point)), None)

	def event(self, radio_event: QEvent) -> bool:
		if (isinstance(radio_event, QHelpEvent)) and (radio_event.type() == QEvent.Type.ToolTip):
			_tooltip(self, radio_event, self._block_in(QPointF(radio_event.pos())), self.calendar.now())
			return True
		return super().event(radio_event)

	def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
		_open(self.calendar, self._block_in(event.position()))

	def menu_in(self, point: QPointF) -> QMenu | None:
		return _menu(self.calendar, self._block_in(point), self)

	def contextMenuEvent(self, event: QContextMenuEvent) -> None:
		menu = self.menu_in(QPointF(event.pos()))
		if menu is not None:
			menu.exec(event.globalPos())

	def paintEvent(self, _event: QPaintEvent) -> None:
		painter = QPainter(self)
		days = self.calendar.days()
		x = _day_x(self, len(days))
		painter.setPen(self.palette().text().color())
		outdated_list = self.calendar.outdated_days()
		for index, day in enumerate(days):
			frame = QRectF(x[index], 0, x[index + 1] - x[index], NAME_HEIGHT)
			colour = self.palette().text().color()
			if day in outdated_list:
				colour = self.palette().placeholderText().color()
				painter.fillRect(QRectF(x[index], 0, x[index + 1] - x[index], self.height()), OUTDATED)
			painter.setPen(colour)
			font_face = painter.font()
			font_face.setBold(day == self.calendar.now().date())
			painter.setFont(font_face)
			painter.drawText(frame, Qt.AlignmentFlag.AlignCenter, day_label(day))
		font_face = painter.font()
		font_face.setBold(False)
		painter.setFont(font_face)
		for block in self.calendar.whole_day():
			_paint_block(painter, self.rectangle(block), block, _day_share)
		painter.end()


def _day_share(frame: QRectF, block: Block, start: datetime, end: datetime) -> QRectF:
	"""La part d'un bloc de la journée entière qui va de debut à fin, de gauche à droite."""
	departure = midnight(block.day)
	left = frame.left() + frame.width() * (start - departure) / ONE_DAY
	right = frame.left() + frame.width() * (end - departure) / ONE_DAY
	return QRectF(left, frame.top(), right - left, frame.height())


class Grid(QWidget):
	"""Les heures de chaque jour : les blocs prévus à gauche, l'airplay à droite."""

	def __init__(self, calendar: Calendar) -> None:
		super().__init__(calendar)
		self.calendar = calendar
		self.setMouseTracking(True)

	def _x(self) -> list[float]:
		return _day_x(self, len(self.calendar.days()))

	def _y(self, day: date, moment: datetime) -> float:
		return (moment - midnight(day)) / timedelta(hours=1) * self.calendar.hour_height()

	def rectangle(self, item: Block | Strip) -> QRectF:
		days = self.calendar.days()
		x = self._x()
		index = days.index(item.day)
		width = x[index + 1] - x[index]
		top, bottom = self._y(item.day, item.start), self._y(item.day, item.end)
		if isinstance(item, Strip):
			left = x[index] + width * PLANNED_SHARE + GAP
			return QRectF(left, top, x[index + 1] - GAP - left, bottom - top)
		column, count = columns([b for b in self.calendar.blocks() if b.day == item.day])[item]
		share = (width * PLANNED_SHARE - GAP) / count
		return QRectF(x[index] + GAP + column * share, top, share - 1, bottom - top)

	def point(self, moment: datetime) -> QPointF:
		"""Un point à l'heure dite, du côté des blocs prévus de son jour."""
		x = self._x()
		index = self.calendar.days().index(moment.date())
		return QPointF(x[index] + 2 * GAP, self._y(moment.date(), moment))

	def item_in(self, point: QPointF) -> Block | Strip | None:
		items: list[Block | Strip] = [*self.calendar.strips(), *self.calendar.blocks()]
		return next((item for item in items if self.rectangle(item).contains(point)), None)

	def _moment_in(self, point: QPointF) -> datetime | None:
		x = self._x()
		for index, day in enumerate(self.calendar.days()):
			if x[index] <= point.x() < x[index + 1]:
				return midnight(day) + timedelta(hours=point.y() / self.calendar.hour_height())
		return None

	def event(self, radio_event: QEvent) -> bool:
		if (isinstance(radio_event, QHelpEvent)) and (radio_event.type() == QEvent.Type.ToolTip):
			_tooltip(self, radio_event, self.item_in(QPointF(radio_event.pos())), self.calendar.now())
			return True
		return super().event(radio_event)

	def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
		_open(self.calendar, self.item_in(event.position()))

	def menu_in(self, point: QPointF) -> QMenu | None:
		item = self.item_in(point)
		if not isinstance(item, Block):
			return None
		return _menu(self.calendar, item, self)

	def contextMenuEvent(self, event: QContextMenuEvent) -> None:
		menu = self.menu_in(QPointF(event.pos()))
		if menu is not None:
			menu.exec(event.globalPos())

	def wheelEvent(self, event: QWheelEvent) -> None:
		"""Maj + molette passe au zoom voisin : vers le haut, plus près ; sans Maj, la grille défile."""
		if not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
			super().wheelEvent(event)
			return
		# Avec Maj, certains bureaux donnent la molette à l'horizontale.
		angle = event.angleDelta()
		notch = (angle.y()) or (angle.x())
		if notch != 0:
			self.calendar.zoom_in_notch(notch > 0)
		event.accept()

	def mousePressEvent(self, event: QMouseEvent) -> None:
		"""Une heure libre, pas encore passée, propose un événement sur l'heure entière : 13:00 – 14:00 pour 13:37. Le
		créneau d'une session sautée est libre."""
		item = self.item_in(event.position())
		free = (item is None) or ((isinstance(item, Block)) and (item.skipped))
		if (event.button() != Qt.MouseButton.LeftButton) or (not free):
			return
		moment = self._moment_in(event.position())
		if moment is None:
			return
		start = moment.replace(minute=0, second=0, microsecond=0)
		if start + ONE_HOUR <= self.calendar.now():
			return
		self.calendar.requested_creation.emit(start)

	def paintEvent(self, _event: QPaintEvent) -> None:
		painter = QPainter(self)
		days = self.calendar.days()
		x = self._x()
		line = QPen(self.palette().mid().color())
		painter.setPen(line)
		hour_height = self.calendar.hour_height()
		for hour in range(25):
			y = hour * hour_height
			painter.drawLine(QPointF(MARGIN, y), QPointF(x[-1], y))
			if hour < 24:
				painter.setPen(self.palette().text().color())
				painter.drawText(QRectF(0, y, MARGIN - GAP, 16), Qt.AlignmentFlag.AlignRight, f"{hour:02d}:00")
				painter.setPen(line)
		for edge in x:
			painter.drawLine(QPointF(edge, 0), QPointF(edge, 24 * hour_height))
		for block in self.calendar.blocks():
			_paint_block(painter, self.rectangle(block), block, self._hour_share)
		now = self.calendar.now()
		for day in self.calendar.outdated_days():
			index = days.index(day)
			painter.fillRect(QRectF(x[index], 0, x[index + 1] - x[index], 24 * hour_height), OUTDATED)
		# Le passé de chaque jour, du côté de l'airplay : la place de ce qui a été diffusé.
		for index, day in enumerate(days):
			passes = min(max(now, midnight(day)), midnight(day + ONE_DAY))
			left = x[index] + (x[index + 1] - x[index]) * PLANNED_SHARE + GAP
			background = QRectF(left, 0, x[index + 1] - GAP - left, self._y(day, passes))
			painter.fillRect(background, self.palette().alternateBase())
		for strip in self.calendar.strips():
			colour = DELETED
			if strip.priority is not None:
				colour = COLOURS[strip.priority].darker(130)
			frame = self.rectangle(strip)
			painter.fillRect(frame, colour)
			painter.setPen(QPen(colour.darker(150)))
			painter.drawRect(frame)
		if now.date() in days:
			index = days.index(now.date())
			height = self._y(now.date(), now)
			painter.setPen(QPen(QColor("#d03030"), 2))
			painter.drawLine(QPointF(x[index], height), QPointF(x[index + 1], height))
		painter.end()

	def _hour_share(self, frame: QRectF, block: Block, start: datetime, end: datetime) -> QRectF:
		top, bottom = self._y(block.day, start), self._y(block.day, end)
		return QRectF(frame.left(), top, frame.width(), bottom - top)


Part = Callable[[QRectF, Block, datetime, datetime], QRectF]
"""Le rectangle d'un bloc qui va d'un moment à un autre."""


def _paint_block(painter: QPainter, frame: QRectF, block: Block, share: Part) -> None:
	"""Estompé là où il ne joue pas, plein là où il joue, avec son nom ; hachuré pour une session sautée."""
	colour = COLOURS[block.event.priority]
	faded = QColor(colour)
	faded.setAlpha(FADE)
	painter.fillRect(frame, faded)
	if block.skipped:
		painter.fillRect(frame, QBrush(colour.darker(140), Qt.BrushStyle.BDiagPattern))
	for start, end in block.plays:
		painter.fillRect(share(frame, block, start, end), colour)
	painter.setPen(QPen(colour.darker(140)))
	painter.setBrush(QBrush())
	painter.drawRect(frame)
	painter.setPen(TEXT)
	painter.drawText(
		frame.adjusted(3, 1, -2, -1), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, block.event.name
	)


def _tooltip(widget: QWidget, event: QHelpEvent, item: Block | Strip | None, now: datetime) -> None:
	if item is None:
		QToolTip.hideText()
		event.ignore()
		return
	text = item.tooltip()
	if isinstance(item, Block):
		text = item.tooltip_to(now)
	QToolTip.showText(event.globalPos(), text, widget)


def _upcoming(block: Block, now: datetime) -> bool:
	"""Une session pas encore commencée, d'un événement récurrent qui n'est pas supprimé : elle se saute, ou se
	rétablit."""
	occurrence = block.planned.occurrence
	event = occurrence.event
	return (
		(occurrence.start is not None)
		and (occurrence.start > now)
		and (event.days != frozenset())
		and (event.deleted_at is None)
	)


def _menu(calendar: "Calendar", block: Block | None, parent: QWidget) -> QMenu | None:
	"""Le menu du clic droit sur un bloc : sauter une session à venir, ou la rétablir ; aucun pour un autre bloc."""
	if (block is None) or (not _upcoming(block, calendar.now())):
		return None
	menu = QMenu(parent)
	if block.skipped:
		menu.addAction(REINSTATE).triggered.connect(lambda: calendar.reinstate(block))
		return menu
	menu.addAction(SKIP).triggered.connect(lambda: calendar.skip(block))
	menu.addAction(SKIP_UNTIL).triggered.connect(lambda: calendar.skip_until(block))
	return menu


def _open(calendar: Calendar, item: Block | Strip | None) -> None:
	if isinstance(item, Block):
		calendar.opened.emit("événement", item.event.id, item.event.name)
	if (isinstance(item, Strip)) and (item.id_event is not None):
		calendar.opened.emit("événement", item.id_event, item.name)
