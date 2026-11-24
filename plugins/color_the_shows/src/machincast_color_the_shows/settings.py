"""Les genres et les couleurs des événements sans genre, réglés dans Machin interface
(https://github.com/dascritch/machincast/issues/628), dans la fenêtre du plugin, menu « Plugins » (point
« interface.plugin_window », https://github.com/dascritch/machincast/issues/587).

Le tableau des genres, chacun avec son nom et sa couleur « #rrggbb », qui s'écrit ou se choisit ; puis la couleur du
fil antenne, des émissions et des spéciales sans genre. « Enregistrer » vérifie les noms et les couleurs, puis écrit
le tout dans une transaction, au rôle machincast_interface : un genre retiré quitte les événements qui l'avaient.
"""

import re
from collections.abc import Callable
from typing import Any

import psycopg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QAbstractItemView,
	QColorDialog,
	QFormLayout,
	QGroupBox,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QLineEdit,
	QPushButton,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from machincast.configuration import Configuration
from machincast.database import Role, open_connection
from machincast.shared.colours import readable_text
from machincast_color_the_shows import queries
from machincast_color_the_shows.texts import t

COLOUR = re.compile(r"^#[0-9a-f]{6}$")
NAME = 64
"""La longueur d'un nom de genre, celle de color_the_shows__genres.name."""
NAME_COLUMN = 0
COLOUR_COLUMN = 1
IDENTIFIER = Qt.ItemDataRole.UserRole
NEW_COLOUR = "#999999"
PRIORITIES = (
	("background_programming", "Background programming"),
	("show", "Show"),
	("special", "Special"),
)

Connect = Callable[[], queries.Connection]


def connector(configuration: Configuration) -> Connect:
	"""La connexion à la base de production, au rôle de l'interface."""

	def connect() -> queries.Connection:
		settings = configuration.database
		return open_connection(settings.socket, settings.production, Role.INTERFACE)

	return connect


def choose_colour(parent: QWidget, current: str) -> str | None:
	"""La couleur choisie dans le sélecteur de Qt, ou None s'il est annulé."""
	chosen = QColorDialog.getColor(QColor(current), parent, t("Colour"))
	if not chosen.isValid():
		return None
	return str(chosen.name()).lower()


def normalised(text: str) -> str:
	return text.strip().lower()


class ColoursSettings(QWidget):
	"""Les genres, et les couleurs des priorités."""

	def __init__(
		self,
		configuration: Configuration | None,
		parent: QWidget | None = None,
		connect: Connect | None = None,
		saved: Callable[[], Any] | None = None,
	) -> None:
		super().__init__(parent)
		self.setObjectName("color_the_shows")
		if connect is None:
			assert configuration is not None
			connect = connector(configuration)
		self.open_base = connect
		self.saved = saved
		self.message = QLabel(
			t(
				"The genres of the shows, and the colours of the events without genre, in the calendar of Machin"
				" interface, the one of Machin intranet and the tables of airplay."
			),
			self,
		)
		self.message.setObjectName("message")
		self.message.setWordWrap(True)
		self.table = QTableWidget(0, 2, self)
		self.table.setObjectName("genres")
		self.table.setHorizontalHeaderLabels([t("Name"), t("Colour")])
		self.table.horizontalHeader().setSectionResizeMode(NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.table.verticalHeader().hide()
		self.priorities: dict[str, QLineEdit] = {}
		self.commands: dict[str, QPushButton] = {}
		self._layout()
		self.table.itemChanged.connect(self._painted)
		self.table.itemSelectionChanged.connect(self._enable)
		self._read()

	def _button(self, name: str, text: str, slot: Callable[[], Any]) -> QPushButton:
		button = QPushButton(t(text), self)
		button.setObjectName(name)
		button.clicked.connect(slot)
		self.commands[name] = button
		return button

	def _layout(self) -> None:
		layout = QVBoxLayout(self)
		layout.addWidget(self.message)
		genres = QGroupBox(t("Genres"), self)
		inner = QVBoxLayout(genres)
		inner.addWidget(self.table)
		row = QHBoxLayout()
		row.addWidget(self._button("add", "Add", self._add))
		row.addWidget(self._button("remove", "Remove", self._remove))
		row.addWidget(self._button("choose", "Choose…", self._choose_genre))
		row.addStretch()
		inner.addLayout(row)
		layout.addWidget(genres)
		box = QGroupBox(t("Colours of the events without genre"), self)
		form = QFormLayout(box)
		for priority, text in PRIORITIES:
			field = QLineEdit(box)
			field.setObjectName(priority)
			field.setMaxLength(7)
			field.textChanged.connect(lambda _text, edited=field: self._paint_field(edited))
			chooser = QPushButton(t("Choose…"), box)
			chooser.setObjectName(f"choose_{priority}")
			chooser.clicked.connect(lambda _checked=False, edited=field: self._choose_field(edited))
			line = QHBoxLayout()
			line.addWidget(field)
			line.addWidget(chooser)
			form.addRow(t(text), line)
			self.priorities[priority] = field
		layout.addWidget(box)
		end = QHBoxLayout()
		end.addStretch()
		end.addWidget(self._button("save", "Save", self.save))
		layout.addLayout(end)

	# ─── Lecture ───────────────────────────────────────────

	def _failed(self, error: Exception) -> None:
		self.message.setText(t("The colours cannot be read or saved: {error}").format(error=error))

	def _read(self) -> None:
		try:
			with self.open_base() as connection:
				found = queries.genres(connection)
				colours = queries.priorities(connection)
		except psycopg.Error as error:
			self._failed(error)
			self._enable()
			return
		self.table.setRowCount(0)
		for identifier, name, colour in found:
			self._append(identifier, name, colour)
		for priority, field in self.priorities.items():
			field.setText(colours.get(priority, ""))
		self._enable()

	def _append(self, identifier: int | None, name: str, colour: str) -> int:
		row = self.table.rowCount()
		self.table.insertRow(row)
		named = QTableWidgetItem(name)
		named.setData(IDENTIFIER, identifier)
		self.table.setItem(row, NAME_COLUMN, named)
		self.table.setItem(row, COLOUR_COLUMN, QTableWidgetItem(colour))
		return row

	# ─── Couleurs montrées ─────────────────────────────────

	def _painted(self, item: QTableWidgetItem) -> None:
		"""La cellule d'une couleur valide prend cette couleur, avec un texte lisible."""
		if item.column() != COLOUR_COLUMN:
			return
		colour = normalised(item.text())
		self.table.blockSignals(True)
		if COLOUR.match(colour) is None:
			item.setData(Qt.ItemDataRole.BackgroundRole, None)
			item.setData(Qt.ItemDataRole.ForegroundRole, None)
		else:
			item.setBackground(QColor(colour))
			item.setForeground(QColor(readable_text(colour)))
		self.table.blockSignals(False)

	def _paint_field(self, field: QLineEdit) -> None:
		colour = normalised(field.text())
		if COLOUR.match(colour) is None:
			field.setStyleSheet("")
			return
		field.setStyleSheet(f"QLineEdit {{ background: {colour}; color: {readable_text(colour)}; }}")

	# ─── Commandes ─────────────────────────────────────────

	def _enable(self) -> None:
		chosen = self.table.currentRow() >= 0
		self.commands["remove"].setEnabled(chosen)
		self.commands["choose"].setEnabled(chosen)

	def _add(self) -> None:
		row = self._append(None, t("new genre"), NEW_COLOUR)
		self.table.setCurrentCell(row, NAME_COLUMN)
		named = self.table.item(row, NAME_COLUMN)
		if named is not None:
			self.table.editItem(named)

	def _remove(self) -> None:
		row = self.table.currentRow()
		if row >= 0:
			self.table.removeRow(row)
		self._enable()

	def _choose_genre(self) -> None:
		row = self.table.currentRow()
		item = self.table.item(row, COLOUR_COLUMN)
		if item is None:
			return
		chosen = choose_colour(self, normalised(item.text()))
		if chosen is not None:
			item.setText(chosen)

	def _choose_field(self, field: QLineEdit) -> None:
		chosen = choose_colour(self, normalised(field.text()))
		if chosen is not None:
			field.setText(chosen)

	# ─── Enregistrement ────────────────────────────────────

	def settings(self) -> tuple[list[tuple[int | None, str, str]], dict[str, str]] | str:
		"""Les genres et les couleurs des priorités, tels qu'ils sont réglés ; ou pourquoi ils sont refusés."""
		kept: list[tuple[int | None, str, str]] = []
		names: list[str] = []
		for row in range(self.table.rowCount()):
			named = self.table.item(row, NAME_COLUMN)
			coloured = self.table.item(row, COLOUR_COLUMN)
			name = ""
			identifier = None
			if named is not None:
				name = named.text().strip()
				identifier = named.data(IDENTIFIER)
			colour = ""
			if coloured is not None:
				colour = normalised(coloured.text())
			if name == "":
				return t("A genre has no name.")
			if len(name) > NAME:
				return t("The genre name “{name}” is too long: {length} characters at most.").format(
					name=name, length=NAME
				)
			if name.lower() in names:
				return t("Two genres are named “{name}”.").format(name=name)
			if COLOUR.match(colour) is None:
				return t("“{colour}” is not a colour #rrggbb, for “{name}”.").format(colour=colour, name=name)
			names.append(name.lower())
			kept.append((identifier, name, colour))
		colours: dict[str, str] = {}
		for priority, text in PRIORITIES:
			colour = normalised(self.priorities[priority].text())
			if COLOUR.match(colour) is None:
				return t("“{colour}” is not a colour #rrggbb, for “{name}”.").format(colour=colour, name=t(text))
			colours[priority] = colour
		return kept, colours

	def save(self) -> bool:
		found = self.settings()
		if isinstance(found, str):
			self.message.setText(found)
			return False
		kept, colours = found
		try:
			with self.open_base() as connection, connection.transaction():
				queries.save(connection, kept, colours)
		except psycopg.Error as error:
			self._failed(error)
			return False
		self._read()
		self.message.setText(t("Saved."))
		if self.saved is not None:
			self.saved()
		return True
