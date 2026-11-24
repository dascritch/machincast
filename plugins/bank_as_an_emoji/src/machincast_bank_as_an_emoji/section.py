"""L'emoji de la banque, devant son nom interne, dans sa fiche (https://github.com/dascritch/machincast/issues/505),
par le point « interface.bank_card » (https://github.com/dascritch/machincast/issues/591).

La section n'a rien à montrer sous la fiche : elle remplace, dans la ligne « Nom interne » du formulaire, le champ du
nom interne par le sélecteur d'emoji, suivi du nom sans son emoji. Le champ de la fiche, caché, garde le nom complet,
« 🌟 Publicités », que la fiche vérifie et enregistre comme avant : son libellé, son raccourci et ses signalements
d'erreur passent au nom sans emoji.
"""

from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QWidget

from machincast.interface.bank_card import BankCard
from machincast.interface.card import CardSection, Refusal
from machincast_bank_as_an_emoji.names import PALETTE, is_emoji, joined, split
from machincast_bank_as_an_emoji.texts import t

EMOJI_WIDTH = 4
"""La largeur du sélecteur, en caractères : assez pour un emoji et sa flèche."""


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
		self.emoji = QComboBox(self.field)
		self.emoji.setObjectName("emoji")
		self.emoji.setEditable(True)
		self.emoji.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
		self.emoji.setMinimumContentsLength(EMOJI_WIDTH)
		self.emoji.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
		self.emoji.setAccessibleName(t("Emoji of the bank"))
		self.emoji.setToolTip(
			t(
				"The emoji at the start of the internal name, shown in the tables of airplay and of the coming sounds;"
				" choose one, write or paste another, or leave it empty."
			)
		)
		self.emoji.addItem("")
		for emoji in PALETTE:
			self.emoji.addItem(emoji)
		self.name = QLineEdit(self.field)
		self.name.setObjectName("internal_name_without_emoji")
		self.name.setPlaceholderText(self.full.placeholderText())
		self.name.setAccessibleName(t("Internal name, without its emoji"))
		self.name.setMaxLength(self.full.maxLength())
		line.addWidget(self.emoji)
		line.addWidget(self.name, 1)
		line.addWidget(self.full)
		self.full.hide()
		self.full.setFocusProxy(self.name)
		form.setWidget(row, QFormLayout.ItemRole.FieldRole, self.field)
		self.name.textChanged.connect(self._compose)
		self.emoji.currentTextChanged.connect(self._compose)

	def chosen(self) -> str:
		return self.emoji.currentText().strip()

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
		index = self.emoji.findText(emoji)
		if index < 0:
			self.emoji.setEditText(emoji)
		else:
			self.emoji.setCurrentIndex(index)
		self.name.setText(name)
		self._loading = False
		self._limit()

	def write(self, identifier: int) -> None:
		"""La fiche a écrit le nom complet ; un emoji qui n'en est pas un la refuse."""
		emoji = self.chosen()
		if (emoji != "") and (not is_emoji(emoji)):
			raise Refusal(t("“{emoji}” is not an emoji.").format(emoji=emoji), self.full)
