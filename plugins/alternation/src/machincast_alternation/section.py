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
	QAbstractItemView,
	QCheckBox,
	QComboBox,
	QFormLayout,
	QGroupBox,
	QHBoxLayout,
	QInputDialog,
	QLabel,
	QListWidget,
	QListWidgetItem,
	QPushButton,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from machincast.clock import Clock
from machincast.conformation import conform
from machincast.i18n import date_and_hour
from machincast.interface.card import CardSection, Refusal
from machincast.shared import grid
from machincast_alternation import queries, rotation, sharing
from machincast_alternation.labels import MODE_LABELS, cycle_label, rank_label
from machincast_alternation.queries import Connection
from machincast_alternation.texts import t

IDENTIFIER = Qt.ItemDataRole.UserRole
NAME_COLUMN = 2
"""La colonne du nom de l'émission, dans le tableau du créneau partagé."""
COMING = 8
"""Les prochains passages montrés."""
HORIZON = timedelta(days=7 * 26)
"""Jusqu'où les chercher : une émission mensuelle en a huit en six mois."""


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
		self.weekdays: frozenset[int] = frozenset()
		"""Les jours de la récurrence cochés dans la fiche."""
		self.first: date | None = None
		"""Le jour de la première occurrence de l'événement, d'où part la quinzaine."""
		self._loading = False
		self.enabled = QCheckBox(t("Shows in alternation"), self)
		self.enabled.setToolTip(t("This event plays, each week, one of the shows below, instead of a play list"))
		self.content = QWidget(self)
		self.candidates = QListWidget(self.content)
		self.candidates.setObjectName("candidates")
		self.candidates_caption = QLabel(t("Shows that share the slot"), self.content)
		self.creation = QPushButton(t("Create a show on this shared slot"), self.content)
		self.creation.setObjectName("creation")
		self.creation.setToolTip(
			t("A new show, created with the event, on its slot: fill in its play list in its own card afterwards")
		)
		self.candidates_note = QLabel(self.content)
		self.candidates_note.setWordWrap(True)
		self.to_create: dict[int, str] = {}
		"""Les émissions à créer, à l'enregistrement : un identifiant provisoire, négatif, et leur nom."""
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
		header = QHBoxLayout()
		header.addWidget(self.candidates_caption)
		header.addStretch()
		header.addWidget(self.creation)
		inner.addLayout(header)
		inner.addWidget(self.candidates)
		inner.addWidget(self.candidates_note)
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
		self.creation.clicked.connect(self._create)
		self.content.setVisible(False)
		# Sans alternance, la section ne montre rien à côté de la liste de lecture : cachée, elle ne la décale pas.
		self.setVisible(False)
		self.shared_box = QGroupBox(t("Shared slot"))
		self.shared_box.setObjectName("shared_slot")
		self.shared_text = QLabel(self.shared_box)
		self.shared_text.setWordWrap(True)
		self.shared_table = QTableWidget(0, 3, self.shared_box)
		self.shared_table.setObjectName("shared_shows")
		self.shared_table.setHorizontalHeaderLabels([t("Rotation"), t("Next broadcast"), t("Show")])
		self.shared_table.verticalHeader().hide()
		self.shared_table.horizontalHeader().setStretchLastSection(True)
		self.shared_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.shared_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.shared_table.cellDoubleClicked.connect(self._open_member)
		shared_arrangement = QVBoxLayout(self.shared_box)
		shared_arrangement.addWidget(self.shared_text)
		shared_arrangement.addWidget(self.shared_table)

	def grid_widget(self) -> QWidget | None:
		"""La case « Émissions en alternance », sous les jours de la récurrence, dans la fiche."""
		return self.enabled

	# ─── Lecture ───────────────────────────────────────────

	def read(self, identifier: int | None) -> None:
		self._loading = True
		self.identifier = identifier
		self.to_create = {}
		self.candidates_note.clear()
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
		self.weekdays = frozenset()
		if event is not None:
			self.weekdays = event.days
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
		self._fill_shared(identifier)

	# ─── Le créneau partagé, dans la fiche d'une de ses émissions ───

	def grid_replacement(self) -> QWidget | None:
		"""L'encadré du créneau partagé, à la place de celui de la grille de la fiche d'une émission de l'alternance."""
		return self.shared_box

	def _fill_shared(self, identifier: int | None) -> None:
		"""Le créneau que l'émission partage, et les autres émissions de son alternance, une par ligne
		(https://github.com/dascritch/machincast/issues/609) ; rien pour un autre événement."""
		found: list[sharing.Slot] = []
		if identifier is not None:
			found = sharing.slots(self.connection, identifier, self.clock)
		texts = []
		members = []
		for slot in found:
			texts.append(slot.text)
			members.extend(slot.members)
		self.shared_text.setText("\n".join(texts))
		self.shared_table.setRowCount(len(members))
		for row, member in enumerate(members):
			for column, text in enumerate((member.rule, member.following(), member.name)):
				cell = QTableWidgetItem(text)
				cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
				cell.setData(IDENTIFIER, member.identifier)
				cell.setToolTip(t("Double-click to open the card of “{name}”").format(name=member.name))
				if member.current:
					font = cell.font()
					font.setBold(True)
					cell.setFont(font)
					cell.setToolTip(t("The show of this card"))
				self.shared_table.setItem(row, column, cell)
		self.shared_table.setVisible(bool(members))
		self.shared_table.resizeColumnsToContents()
		self.replaces_grid.emit(bool(found))

	def _open_member(self, row: int, _column: int) -> None:
		"""Le double clic sur une ligne ouvre la fiche de son émission ; rien sur celle de la fiche affichée."""
		cell = self.shared_table.item(row, NAME_COLUMN)
		if (cell is not None) and (int(cell.data(IDENTIFIER)) != self.identifier):
			self.opens.emit("event", int(cell.data(IDENTIFIER)), cell.text())

	# ─── Seulement avec un jour de la semaine ──────────────

	def days_changed(self, days: frozenset[int]) -> None:
		"""Les jours de la récurrence cochés dans la fiche : sans eux, pas d'alternance."""
		self.weekdays = days
		self._allow()

	def _allow(self) -> None:
		"""La case ne se coche qu'avec un jour de la semaine ; cochée, elle peut toujours se décocher."""
		self.enabled.setEnabled((bool(self.weekdays)) or (self.enabled.isChecked()))
		tip = t("This event plays, each week, one of the shows below, instead of a play list")
		if not self.weekdays:
			tip = t("Tick a day of the week first: the shows alternate on the days of the recurrence")
		self.enabled.setToolTip(tip)

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

	# ─── Créer une émission sur le créneau partagé ─────────

	def ask_name(self, parent: QWidget) -> str | None:
		"""Le nom de l'émission à créer ; None, abandonnée."""
		text, accepted = QInputDialog.getText(parent, t("Create a show on this shared slot"), t("Name of the show"))
		if not accepted:
			return None
		return text

	def _create(self) -> None:
		"""Une émission à créer, cochée, enregistrée avec l'événement méta ; un nom vide ou pris est refusé."""
		answer = self.ask_name(self)
		if answer is None:
			return
		name = conform(answer.strip())
		if name == "":
			self.candidates_note.setText(t("A name is required."))
			return
		with self.connection.transaction():
			taken = queries.name_taken(self.connection, name)
		if (taken) or (name in self.to_create.values()):
			self.candidates_note.setText(t("Another event is already called “{name}”.").format(name=name))
			return
		self.candidates_note.clear()
		provisional = -(len(self.to_create) + 1)
		self.to_create[provisional] = name
		item = QListWidgetItem(t("{name} (to create)").format(name=name), self.candidates)
		item.setData(IDENTIFIER, provisional)
		item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
		item.setCheckState(Qt.CheckState.Checked)

	# ─── Le rythme ─────────────────────────────────────────

	def chosen_mode(self) -> str:
		return str(self.mode.currentData())

	def rank_boxes(self) -> list[QComboBox]:
		"""Les listes de la rotation du rythme choisi : cinq semaines du mois, ou celles de son cycle."""
		return self.rotation_boxes[: len(rotation.RANKS[self.chosen_mode()])]

	def _alternation_rank(self, day: date) -> int:
		return rotation.Alternation(mode=self.chosen_mode()).rank(day, self.first)

	def _show_mode(self) -> None:
		"""Les rangs du rythme, chacun nommé ; une semaine sur deux, trois ou quatre, avec son prochain passage."""
		period = rotation.PERIODS.get(self.chosen_mode())
		for index, box in enumerate(self.rotation_boxes):
			rank = index + 1
			self.rotation_form.setRowVisible(index, rank in rotation.RANKS[self.chosen_mode()])
			text = rank_label(rank, self.weekday)
			if period is not None:
				text = cycle_label(rank, period, self._following(rank))
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
		self._allow()
		on = self.enabled.isChecked()
		self.content.setVisible(on)
		self.setVisible(on)
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
		if not self.weekdays:
			raise Refusal(t("Tick a day of the week: the shows alternate on the days of the recurrence."), self.enabled)
		found = self.alternation()
		if not found.candidates:
			raise Refusal(t("Choose at least one show that shares the slot."), self.candidates)
		queries.write(self.connection, identifier, self._created(found, identifier).stored())

	def _created(self, found: rotation.Alternation, meta: int) -> rotation.Alternation:
		"""Les émissions à créer qui sont cochées, créées sur le créneau : leurs identifiants à la place des
		provisoires."""
		real: dict[int, int] = {}
		for provisional, name in self.to_create.items():
			if provisional in found.candidates:
				real[provisional] = queries.create(self.connection, name, meta)

		def actual(value: int | None) -> int | None:
			if value is None:
				return None
			return real.get(value, value)

		candidates = []
		for candidate in found.candidates:
			candidates.append(real.get(candidate, candidate))
		ranks: dict[int, int | None] = {}
		for rank, chosen in found.rotation.items():
			ranks[rank] = actual(chosen)
		choices: dict[date, int] = {}
		for day, chosen_day in found.choices.items():
			choices[day] = real.get(chosen_day, chosen_day)
		return rotation.Alternation(tuple(candidates), ranks, choices, found.mode)


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
