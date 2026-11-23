"""Les boutons du cartouchier, réglés dans Machin interface (https://github.com/dascritch/machincast/issues/512), dans
la fenêtre du plugin, menu « Plugins » (point « interface.plugin_window »,
https://github.com/dascritch/machincast/issues/587).

Pour chaque compte de l'API : la liste de ses boutons, dans l'ordre du cartouchier, et le formulaire d'un bouton, son
intitulé, sa couleur, son action, ce qu'elle vise et, pour une insertion, son blanc. Chaque changement s'enregistre
aussitôt, au rôle machincast_interface ; la page du cartouchier le montre à sa prochaine lecture.
"""

import re
from collections.abc import Callable
from typing import Any

import psycopg
from PySide6.QtWidgets import (
	QComboBox,
	QFormLayout,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QListWidget,
	QPushButton,
	QVBoxLayout,
	QWidget,
)

from machincast.configuration import Configuration
from machincast.database import Role, open_connection
from machincast_cartwall import queries
from machincast_cartwall.buttons import ACTIONS, BLANKS, DEFAULT_COLOUR, INSERTIONS, Button, action_label, target_kind
from machincast_cartwall.texts import t

COLOUR = re.compile(r"^#[0-9a-f]{6}$")
LABEL = 128
"""La longueur d'un intitulé, celle de cartwall__buttons.label : assez pour l'action et sa cible qu'il propose."""

Connect = Callable[[], queries.Connection]


def connector(configuration: Configuration) -> Connect:
	"""La connexion à la base de production, au rôle de l'interface."""

	def connect() -> queries.Connection:
		settings = configuration.database
		return open_connection(settings.socket, settings.production, Role.INTERFACE)

	return connect


class ButtonsSettings(QWidget):
	"""Les boutons de chaque compte de l'API."""

	def __init__(
		self, configuration: Configuration, parent: QWidget | None = None, connect: Connect | None = None
	) -> None:
		super().__init__(parent)
		self.setObjectName("cartwall")
		self.open_base = (connect) or (connector(configuration))
		self.reachable = True
		self.buttons: list[Button] = []
		self.message = QLabel(t("The buttons of each account of the API, in the cartwall of Machin intranet."), self)
		self.message.setObjectName("message")
		self.message.setWordWrap(True)
		self.account = QComboBox(self)
		self.account.setObjectName("account")
		self.list = QListWidget(self)
		self.list.setObjectName("buttons")
		self.label = QLineEdit(self)
		self.label.setObjectName("label")
		self.label.setMaxLength(LABEL)
		self.colour = QLineEdit(DEFAULT_COLOUR, self)
		self.colour.setObjectName("colour")
		self.action = QComboBox(self)
		self.action.setObjectName("action")
		for action in ACTIONS:
			self.action.addItem(action_label(action), action)
		self.target = QComboBox(self)
		self.target.setObjectName("target")
		self.blank = QComboBox(self)
		self.blank.setObjectName("blank")
		for blank, text in BLANKS.items():
			self.blank.addItem(t(text), blank)
		self._layout()
		self._accounts()
		self.account.currentIndexChanged.connect(self._read)
		self.list.currentRowChanged.connect(self._show)
		self.action.currentIndexChanged.connect(self._targets)
		# L'intitulé proposé, tant qu'il n'a pas été écrit : l'action et sa cible.
		self.suggested = ""
		self.action.currentIndexChanged.connect(self._suggest)
		self.target.currentIndexChanged.connect(self._suggest)
		self._targets()
		self._read()

	def _layout(self) -> None:
		layout = QVBoxLayout(self)
		layout.addWidget(self.message)
		form = QFormLayout()
		form.addRow(t("Account"), self.account)
		layout.addLayout(form)
		layout.addWidget(self.list)
		details = QFormLayout()
		details.addRow(t("Label"), self.label)
		details.addRow(t("Colour"), self.colour)
		details.addRow(t("Action"), self.action)
		details.addRow(t("Target"), self.target)
		details.addRow(t("Blank"), self.blank)
		layout.addLayout(details)
		row = QHBoxLayout()
		self.commands: dict[str, QPushButton] = {}
		for name, text, slot in (
			("add", "Add", self._add),
			("replace", "Replace", self._replace),
			("remove", "Remove", self._remove),
			("up", "Up", lambda: self._move(-1)),
			("down", "Down", lambda: self._move(1)),
		):
			button = QPushButton(t(text), self)
			button.setObjectName(name)
			button.clicked.connect(slot)
			row.addWidget(button)
			self.commands[name] = button
		layout.addLayout(row)

	def _failed(self, error: Exception) -> None:
		self.reachable = False
		self.message.setText(t("The buttons cannot be read or saved: {error}").format(error=error))

	def _base[T](self, action: Callable[[queries.Connection], T], default: T) -> T:
		"""Une action sur la base, dans sa connexion, fermée après ; default si la base échoue, et le message le dit."""
		try:
			with self.open_base() as connection:
				return action(connection)
		except psycopg.Error as error:
			self._failed(error)
			return default

	def _accounts(self) -> None:
		empty: list[tuple[int, str]] = []
		found = self._base(queries.accounts, empty)
		for identifier, name in found:
			self.account.addItem(name, identifier)
		if (found == []) and (self.reachable):
			self.message.setText(t("No account of the API: create one in the tab “API”."))

	def _chosen_account(self) -> int | None:
		value = self.account.currentData()
		if isinstance(value, int):
			return value
		return None

	def _read(self, selected: int | None = None) -> None:
		"""Les boutons du compte choisi ; selected, celui à montrer."""
		self.list.clear()
		self.buttons = []
		account = self._chosen_account()
		if account is None:
			self._enable()
			return
		empty: list[Button] = []
		self.buttons = self._base(lambda connection: queries.buttons_of_account(connection, account), empty)
		for button in self.buttons:
			self.list.addItem(f"{button.label} — {self._summary(button)}")
		for row, button in enumerate(self.buttons):
			if button.id == selected:
				self.list.setCurrentRow(row)
		self._enable()

	def _summary(self, button: Button) -> str:
		parts = [action_label(button.action)]
		if button.target_name is not None:
			parts.append(f"« {button.target_name} »")
		if button.blank is not None:
			parts.append(t(BLANKS[button.blank]))
		return ", ".join(parts)

	def _enable(self) -> None:
		chosen = self.list.currentRow() >= 0
		self.commands["add"].setEnabled(self._chosen_account() is not None)
		for name in ("replace", "remove", "up", "down"):
			self.commands[name].setEnabled(chosen)

	def _show(self, row: int) -> None:
		"""Le bouton choisi, dans le formulaire."""
		self._enable()
		if (row < 0) or (row >= len(self.buttons)):
			return
		button = self.buttons[row]
		# L'intitulé d'un bouton enregistré reste le sien : rien n'est plus proposé.
		self.suggested = ""
		self.label.setText(button.label)
		self.colour.setText(button.colour)
		self.action.setCurrentIndex(self.action.findData(button.action))
		self._targets()
		if button.target is not None:
			self.target.setCurrentIndex(self.target.findData(button.target))
		self.blank.setCurrentIndex(self.blank.findData(button.blank))

	def _targets(self) -> None:
		"""Ce que l'action choisie peut viser ; le blanc ne sert qu'à une insertion."""
		self.target.clear()
		action = str(self.action.currentData())
		kind = target_kind(action)
		self.target.setEnabled(kind is not None)
		self.blank.setEnabled(action in INSERTIONS)
		if kind is None:
			return
		empty: list[tuple[int, str]] = []
		for identifier, name in self._base(lambda connection: queries.targets(connection, kind), empty):
			self.target.addItem(name, identifier)

	def _suggest(self) -> None:
		"""Pré-remplit l'intitulé du nom de l'action et de sa cible, tant qu'il est vide ou garde la proposition
		précédente ; un intitulé écrit n'est jamais remplacé."""
		current = self.label.text()
		if (current.strip() != "") and (current != self.suggested):
			return
		suggestion = action_label(str(self.action.currentData()))
		if self.target.currentIndex() >= 0:
			suggestion = f"{suggestion} « {self.target.currentText()} »"
		self.label.setText(suggestion)
		# Coupé à la longueur de l'intitulé, il reste reconnu comme proposé.
		self.suggested = self.label.text()

	def _fields(self) -> queries.Fields | None:
		"""Le bouton du formulaire ; None s'il est incomplet, et le message dit pourquoi."""
		label = self.label.text().strip()
		colour = self.colour.text().strip().lower()
		action = str(self.action.currentData())
		target = self.target.currentData()
		if label == "":
			self.message.setText(t("A label is required."))
			return None
		if not COLOUR.match(colour):
			self.message.setText(t("A colour is written #rrggbb."))
			return None
		if (target_kind(action) is not None) and (not isinstance(target, int)):
			self.message.setText(t("This action needs a target."))
			return None
		if target_kind(action) is None:
			target = None
		blank = None
		if action in INSERTIONS:
			blank = self.blank.currentData()
		return queries.Fields(label, colour, action, target, blank)

	def _change(self, change: Callable[[queries.Connection], Any]) -> None:
		"""Enregistre le changement, puis relit les boutons ; une base en échec le dit."""
		self.reachable = True
		selected = self._base(change, None)
		if not self.reachable:
			return
		self.message.setText(t("The buttons of each account of the API, in the cartwall of Machin intranet."))
		self._read(selected)

	def _current(self) -> Button | None:
		row = self.list.currentRow()
		if (row < 0) or (row >= len(self.buttons)):
			return None
		return self.buttons[row]

	def _add(self) -> None:
		fields = self._fields()
		account = self._chosen_account()
		if (fields is None) or (account is None):
			return
		self._change(lambda connection: queries.add(connection, account, fields))

	def _replace(self) -> None:
		fields = self._fields()
		button = self._current()
		if (fields is None) or (button is None):
			return
		chosen = button.id

		def replace(connection: queries.Connection) -> int:
			queries.replace(connection, chosen, fields)
			return chosen

		self._change(replace)

	def _remove(self) -> None:
		button = self._current()
		if button is None:
			return
		chosen = button.id
		self._change(lambda connection: queries.remove(connection, chosen))

	def _move(self, offset: int) -> None:
		button = self._current()
		if button is None:
			return
		chosen = button.id

		def move(connection: queries.Connection) -> int:
			queries.move(connection, chosen, offset)
			return chosen

		self._change(move)
