"""L'emoji de la banque, devant son nom interne, dans sa fiche (https://github.com/dascritch/machincast/issues/505),
par le point « interface.bank_card » (https://github.com/dascritch/machincast/issues/591).

La section n'a rien à montrer sous la fiche : elle remplace, dans la ligne « Nom interne » du formulaire, le champ du
nom interne par le bouton de l'emoji, qui ouvre le sélecteur d'emojis de KDE, ou une grille d'emojis
(machincast_bank_as_an_emoji.picker), celui qui retire l'emoji, puis le nom sans son emoji. Le champ de la fiche, caché, garde le nom complet,
« 🌟 Publicités », que la fiche vérifie et enregistre comme avant : son libellé, son raccourci et ses signalements
d'erreur passent au nom sans emoji.
"""

from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLineEdit, QToolButton, QWidget

from machincast.interface.bank_card import BankCard
from machincast.interface.card import CardSection
from machincast_bank_as_an_emoji.names import is_emoji, joined, split
from machincast_bank_as_an_emoji.picker import EmojiGrid, KdePicker, emojier
from machincast_bank_as_an_emoji.texts import t

CLEAR = "✕"


def field_row(form: QFormLayout, widget: QWidget) -> int:
	"""La ligne du formulaire dont ce widget est le champ."""
	for row in range(form.rowCount()):
		item = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
		if (item is not None) and (item.widget() is widget):
			return row
	raise LookupError(widget.objectName())


class EmojiSection(CardSection):
	def __init__(self, card: BankCard, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("bank_as_an_emoji")
		self.hide()
		self.full = card.ui.internal_name
		"""Le champ du nom interne de la fiche, caché : le nom complet, emoji compris."""
		self._loading = False
		form = card.ui.form
		row = field_row(form, self.full)
		form.removeWidget(self.full)
		self.field = QWidget(card)
		self.field.setObjectName("bank_as_an_emoji_field")
		line = QHBoxLayout(self.field)
		line.setContentsMargins(0, 0, 0, 0)
		self._emoji = ""
		self.emoji = QToolButton(self.field)
		self.emoji.setObjectName("emoji")
		self.emoji.setAccessibleName(t("Emoji of the bank"))
		self.emoji.setToolTip(
			t(
				"The emoji at the start of the internal name, shown in the tables of airplay and of the coming sounds:"
				" choose it in the emoji selector, which copies it"
			)
		)
		self.clear = QToolButton(self.field)
		self.clear.setObjectName("clear_emoji")
		self.clear.setText(CLEAR)
		self.clear.setAccessibleName(t("Remove the emoji"))
		self.clear.setToolTip(t("Remove the emoji"))
		self.kde: KdePicker | None = None
		program = emojier()
		if program is not None:
			self.kde = KdePicker(program, self)
			self.kde.picked.connect(self.set_emoji)
		self.grid = EmojiGrid(self.field)
		self.grid.picked.connect(self.set_emoji)
		self.name = QLineEdit(self.field)
		self.name.setObjectName("internal_name_without_emoji")
		self.name.setPlaceholderText(self.full.placeholderText())
		self.name.setAccessibleName(t("Internal name, without its emoji"))
		self.name.setMaxLength(self.full.maxLength())
		line.addWidget(self.emoji)
		line.addWidget(self.clear)
		line.addWidget(self.name, 1)
		line.addWidget(self.full)
		self.full.hide()
		self.full.setFocusProxy(self.name)
		form.setWidget(row, QFormLayout.ItemRole.FieldRole, self.field)
		self.name.textChanged.connect(self._compose)
		self.emoji.clicked.connect(self.choose)
		self.clear.clicked.connect(lambda: self.set_emoji(""))
		self._show_emoji()

	def chosen(self) -> str:
		return self._emoji

	def choose(self) -> None:
		"""Le sélecteur d'emojis de KDE, sinon la grille, sous le bouton."""
		if (self.kde is not None) and (self.kde.open()):
			return
		self.grid.popup(self.emoji.mapToGlobal(self.emoji.rect().bottomLeft()))

	def set_emoji(self, emoji: str) -> None:
		"""L'emoji choisi, ou aucun : la fiche est modifiée."""
		if (emoji != "") and (not is_emoji(emoji)):
			return
		self._emoji = emoji
		self._show_emoji()
		self._compose()

	def _show_emoji(self) -> None:
		text = self._emoji
		if text == "":
			text = t("Emoji…")
		self.emoji.setText(text)
		self.clear.setEnabled(self._emoji != "")

	def _compose(self) -> None:
		"""Le nom complet, dans le champ caché de la fiche, qui la rend modifiée."""
		self._limit()
		if not self._loading:
			self.full.setText(joined(self.chosen(), self.name.text()))

	def _limit(self) -> None:
		"""Le nom sans emoji laisse la place de l'emoji et de son espace, dans la longueur du nom interne."""
		taken = 0
		if self.chosen() != "":
			taken = len(self.chosen().encode("utf-16-le")) // 2 + 1
		self.name.setMaxLength(self.full.maxLength() - taken)

	def read(self, identifier: int | None) -> None:
		"""Le nom interne que la fiche vient de lire, ou de copier, séparé de son emoji."""
		self._loading = True
		emoji, name = split(self.full.text())
		self._emoji = emoji
		self._show_emoji()
		self.name.setText(name)
		self._loading = False
		self._limit()
