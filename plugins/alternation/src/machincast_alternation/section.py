"""La section « Émissions en alternance » de la fiche d'un événement, dans Machin interface
(https://github.com/dascritch/machincast/issues/609), par le point « interface.event_card »
(https://github.com/dascritch/machincast/issues/611).

Cochée, elle remplace la liste de lecture de l'événement : ses émissions qui se partagent le créneau, leur rotation
dans le mois, de la 1re à la 5e occurrence de son jour, et ses prochains passages, chacun selon la rotation ou choisi
à la main. Elle s'enregistre avec l'événement, dans sa colonne properties, sous la clé du plugin.
"""

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QCheckBox,
	QComboBox,
	QFormLayout,
	QLabel,
	QListWidget,
	QListWidgetItem,
	QVBoxLayout,
	QWidget,
)

from machincast.clock import Clock
from machincast.i18n import date_and_hour, short_date
from machincast.interface.card import Refusal
from machincast.interface.event_card import CardSection
from machincast.shared import grid
from machincast_alternation import queries, rotation
from machincast_alternation.queries import Connection
from machincast_alternation.texts import t

IDENTIFIER = Qt.ItemDataRole.UserRole
COMING = 8
"""Les prochains passages montrés."""
HORIZON = timedelta(days=7 * 26)
"""Jusqu'où les chercher : une émission mensuelle en a huit en six mois."""
RANKS = ("1st", "2nd", "3rd", "4th", "5th")


def ordinal(rank: int, *, feminine: bool = False) -> str:
	"""1er, 2e… ; 1re pour « semaine »."""
	if (rank == 1) and (feminine):
		return t("1st (feminine)")
	return t(RANKS[rank - 1])


MODE_LABELS = {
	rotation.MONTHLY: "Monthly, by the week of the month",
	rotation.FORTNIGHTLY: "Fortnightly, every other week",
}


def fortnight_label(rank: int, following: date | None) -> str:
	"""« 1re semaine de la quinzaine, dont le 16/12/2026 » : son prochain passage, s'il est connu."""
	text = t("{rank} week of the fortnight").format(rank=ordinal(rank, feminine=True))
	if following is None:
		return text
	return t("{week}, including {day}").format(week=text, day=short_date(following))


def rank_label(rank: int, day: int | None) -> str:
	"""« 1er mercredi du mois », ou « 1re semaine du mois » pour un événement de plusieurs jours, ou sans jour."""
	if day is None:
		return t("week {rank} of the month").format(rank=ordinal(rank, feminine=True))
	return t("{rank} {day} of the month").format(rank=ordinal(rank), day=grid.DAY_NAMES[day].lower())


class AlternationSection(CardSection):
	def __init__(self, connection: Connection, clock: Clock, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("alternation")
		self.connection = connection
		self.clock = clock
		self.identifier: int | None = None
		self.kept_choices: dict[date, int] = {}
		self.days: list[date] = []
		self.weekday: int | None = None
		self.first: date | None = None
		"""Le jour de la première occurrence de l'événement, d'où part la quinzaine."""
		self._loading = False
		self.enabled = QCheckBox(t("Shows in alternation"), self)
		self.enabled.setToolTip(t("This event plays, each week, one of the shows below, instead of a play list"))
		self.content = QWidget(self)
		self.candidates = QListWidget(self.content)
		self.candidates.setObjectName("candidates")
		self.mode = QComboBox(self.content)
		self.mode.setObjectName("mode")
		for value in rotation.MODES:
			self.mode.addItem(t(MODE_LABELS[value]), value)
		self.rotation_boxes: list[QComboBox] = []
		self.coming_boxes: list[QComboBox] = []
		self.rotation_form = QFormLayout()
		self.coming_form = QFormLayout()
		self.coming_note = QLabel(self.content)
		self.coming_note.setWordWrap(True)
		inner = QVBoxLayout(self.content)
		inner.setContentsMargins(0, 0, 0, 0)
		inner.addWidget(QLabel(t("Shows that share the slot"), self.content))
		inner.addWidget(self.candidates)
		inner.addWidget(QLabel(t("Rhythm"), self.content))
		inner.addWidget(self.mode)
		inner.addWidget(QLabel(t("Rotation"), self.content))
		inner.addLayout(self.rotation_form)
		inner.addWidget(QLabel(t("Coming broadcasts"), self.content))
		inner.addLayout(self.coming_form)
		inner.addWidget(self.coming_note)
		inner.addStretch()
		arrangement = QVBoxLayout(self)
		arrangement.addWidget(self.enabled)
		arrangement.addWidget(self.content)
		for rank in rotation.WEEKS:
			box = QComboBox(self.content)
			box.setObjectName(f"rotation_{rank}")
			box.currentIndexChanged.connect(self._changed)
			box.currentIndexChanged.connect(self._show_rotation)
			self.rotation_boxes.append(box)
			self.rotation_form.addRow(rank_label(rank, None), box)
		self.enabled.toggled.connect(self._toggled)
		self.mode.currentIndexChanged.connect(self._mode_changed)
		self.candidates.itemChanged.connect(self._candidates_changed)
		self.content.setVisible(False)

	def grid_widget(self) -> QWidget | None:
		"""La case « Émissions en alternance », sous les jours de la récurrence, dans la fiche."""
		return self.enabled

	# ─── Lecture ───────────────────────────────────────────

	def read(self, identifier: int | None) -> None:
		self._loading = True
		self.identifier = identifier
		properties: dict[str, object] = {}
		event = None
		if identifier is not None:
			properties = queries.properties(self.connection, identifier)
			event = grid.read_event(self.connection, identifier)
		found = rotation.read(properties)
		if found is None:
			found = rotation.Alternation()
		self._fill_candidates(found.candidates)
		self.weekday = _weekday(event)
		self.first = None
		if event is not None:
			self.first = rotation.first_day(event)
		self.mode.setCurrentIndex(max(self.mode.findData(found.mode), 0))
		self._fill_boxes()
		for rank, box in zip(rotation.WEEKS, self.rotation_boxes, strict=True):
			box.setCurrentIndex(max(box.findData(found.rotation.get(rank)), 0))
		self.kept_choices = dict(found.choices)
		self._fill_coming(event)
		self._show_mode()
		self.enabled.setChecked(rotation.KEY in properties)
		self._loading = False
		self._toggled()

	def _fill_candidates(self, chosen: tuple[int, ...]) -> None:
		self.candidates.clear()
		offered = queries.candidates(self.connection, self.identifier)
		for identifier, name in offered:
			item = QListWidgetItem(name, self.candidates)
			item.setData(IDENTIFIER, identifier)
			item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
			state = Qt.CheckState.Unchecked
			if identifier in chosen:
				state = Qt.CheckState.Checked
			item.setCheckState(state)
		if not offered:
			self.coming_note.setText(t("No show or special to share the slot: create them first."))

	# ─── Le rythme ─────────────────────────────────────────

	def chosen_mode(self) -> str:
		return str(self.mode.currentData())

	def rank_boxes(self) -> list[QComboBox]:
		"""Les listes de la rotation du rythme choisi : cinq semaines du mois, ou deux de la quinzaine."""
		return self.rotation_boxes[: len(rotation.RANKS[self.chosen_mode()])]

	def _alternation_rank(self, day: date) -> int:
		return rotation.Alternation(mode=self.chosen_mode()).rank(day, self.first)

	def _show_mode(self) -> None:
		"""Les rangs du rythme, chacun nommé ; par quinzaine, avec son prochain passage."""
		fortnightly = self.chosen_mode() == rotation.FORTNIGHTLY
		for index, box in enumerate(self.rotation_boxes):
			rank = index + 1
			self.rotation_form.setRowVisible(index, rank in rotation.RANKS[self.chosen_mode()])
			text = rank_label(rank, self.weekday)
			if fortnightly:
				text = fortnight_label(rank, self._following(rank))
			caption = self.rotation_form.labelForField(box)
			if isinstance(caption, QLabel):
				caption.setText(text)
		self._show_rotation()

	def _following(self, rank: int) -> date | None:
		for day in self.days:
			if self._alternation_rank(day) == rank:
				return day
		return None

	def _mode_changed(self) -> None:
		self._show_mode()
		self._changed()

	def _fill_coming(self, event: grid.Event | None) -> None:
		while self.coming_form.rowCount() > 0:
			self.coming_form.removeRow(0)
		self.coming_boxes = []
		self.days = []
		if (event is None) or (event.start is None):
			self.coming_note.setText(t("Save the event to see its coming broadcasts."))
			return
		self.coming_note.clear()
		today = grid.wall_hour(self.clock.now()).date()
		for start, _end in grid.sessions(event, today, today + HORIZON)[:COMING]:
			box = QComboBox(self.content)
			box.setObjectName(f"coming_{start.date().isoformat()}")
			box.currentIndexChanged.connect(self._changed)
			self.coming_boxes.append(box)
			self.days.append(start.date())
			self.coming_form.addRow(f"{grid.DAY_NAMES[start.weekday()].lower()} {date_and_hour(start)}", box)
		self._fill_boxes()
		for day, box in zip(self.days, self.coming_boxes, strict=True):
			box.setCurrentIndex(max(box.findData(self.kept_choices.get(day)), 0))

	# ─── Changements ───────────────────────────────────────

	def chosen_candidates(self) -> list[tuple[int, str]]:
		found = []
		for index in range(self.candidates.count()):
			item = self.candidates.item(index)
			if (item is not None) and (item.checkState() == Qt.CheckState.Checked):
				found.append((int(item.data(IDENTIFIER)), item.text()))
		return found

	def _fill_boxes(self) -> None:
		"""Les émissions choisies, dans chaque liste ; chacune garde son choix s'il y est encore."""
		loading = self._loading
		self._loading = True
		chosen = self.chosen_candidates()
		for box in self.rotation_boxes:
			kept = box.currentData()
			box.clear()
			box.addItem(t("— the event itself"), None)
			for identifier, name in chosen:
				box.addItem(name, identifier)
			box.setCurrentIndex(max(box.findData(kept), 0))
		for box in self.coming_boxes:
			kept = box.currentData()
			box.clear()
			box.addItem("", None)
			for identifier, name in chosen:
				box.addItem(name, identifier)
			box.setCurrentIndex(max(box.findData(kept), 0))
		self._loading = loading
		self._show_rotation()

	def _show_rotation(self) -> None:
		"""Le premier choix d'un passage dit qui joue selon la rotation."""
		for day, box in zip(self.days, self.coming_boxes, strict=True):
			rotated = self.rotation_boxes[self._alternation_rank(day) - 1]
			box.setItemText(0, t("According to the rotation: {name}").format(name=rotated.currentText()))

	def _candidates_changed(self) -> None:
		if self._loading:
			return
		self._fill_boxes()
		self.changed.emit()

	def _changed(self) -> None:
		if not self._loading:
			self.changed.emit()

	def _toggled(self) -> None:
		on = self.enabled.isChecked()
		self.content.setVisible(on)
		self.replaces_items.emit(on)
		self._changed()

	# ─── Écriture ──────────────────────────────────────────

	def alternation(self) -> rotation.Alternation:
		"""L'alternance montrée ; les choix des dates qui ne sont pas montrées, à venir, sont gardés."""
		candidates = []
		for identifier, _name in self.chosen_candidates():
			candidates.append(identifier)
		ranks: dict[int, int | None] = {}
		for rank, box in enumerate(self.rank_boxes(), start=1):
			ranks[rank] = box.currentData()
		choices: dict[date, int] = {}
		today = grid.wall_hour(self.clock.now()).date()
		for day, chosen in self.kept_choices.items():
			if (day >= today) and (day not in self.days):
				choices[day] = chosen
		for day, box in zip(self.days, self.coming_boxes, strict=True):
			if box.currentData() is not None:
				choices[day] = int(box.currentData())
		return rotation.Alternation(tuple(candidates), ranks, choices, self.chosen_mode())

	def write(self, identifier: int) -> None:
		if not self.enabled.isChecked():
			queries.write(self.connection, identifier, None)
			return
		found = self.alternation()
		if not found.candidates:
			raise Refusal(t("Choose at least one show that shares the slot."), self.candidates)
		queries.write(self.connection, identifier, found.stored())


def _weekday(event: grid.Event | None) -> int | None:
	"""Le jour de l'événement, s'il n'en a qu'un : celui de ses jours, ou de sa seule occurrence."""
	if event is None:
		return None
	if len(event.days) == 1:
		(day,) = tuple(event.days)
		return day
	if (not event.days) and (event.start is not None):
		return grid.wall_hour(event.start).weekday()
	return None
