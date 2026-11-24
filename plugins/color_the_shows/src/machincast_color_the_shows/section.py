"""La section « Genre » de la fiche d'un événement, dans Machin interface
(https://github.com/dascritch/machincast/issues/628), par le point « interface.event_card »
(https://github.com/dascritch/machincast/issues/611).

Une liste de choix : aucun genre, ou l'un des genres réglés dans la fenêtre du plugin, chacun avec un carré de sa
couleur. Dans la fiche, elle est la ligne « Genre » du formulaire, sous « Secours d'un stream tombé » : la section
elle-même, cachée, ne prend pas de place à gauche de la liste de lecture, qui reste alignée comme dans les autres
fiches. Le genre s'enregistre avec l'événement, dans sa colonne properties, sous la clé du plugin ; sans genre, la clé
en part.
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QWidget

from machincast.interface.card import CardSection
from machincast.interface.event_card import EventCard
from machincast_color_the_shows import queries
from machincast_color_the_shows.texts import t

SWATCH = 14
"""Le côté, en pixels, du carré de la couleur d'un genre."""


def swatch(colour: str) -> QIcon:
	"""Un carré de la couleur."""
	picture = QPixmap(SWATCH, SWATCH)
	picture.fill(QColor(colour))
	return QIcon(picture)


def field_row(form: QFormLayout, widget: QWidget) -> int:
	"""La ligne du formulaire dont ce widget est le champ."""
	for row in range(form.rowCount()):
		item = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
		if (item is not None) and (item.widget() is widget):
			return row
	raise LookupError(widget.objectName())


class GenreSection(CardSection):
	def __init__(
		self,
		connection: queries.Connection,
		parent: QWidget | None = None,
		written: Callable[[], Any] | None = None,
		card: EventCard | None = None,
	) -> None:
		"""written est appelé après l'écriture du genre : la palette relit la base au prochain dessin. card, la fiche
		qui reçoit la ligne « Genre » ; sans elle, la section la garde."""
		super().__init__(parent)
		self.setObjectName("color_the_shows")
		self.connection = connection
		self.written = written
		self._loading = False
		self.genre = QComboBox(self)
		self.genre.setObjectName("genre")
		self.genre.setToolTip(
			t(
				"The colour of the event in the calendars and the tables of airplay; without genre, the colour of its"
				" priority."
			)
		)
		self.caption = QLabel(t("&Genre"), self)
		self.caption.setObjectName("genre_caption")
		self.caption.setBuddy(self.genre)
		if card is None:
			form = QFormLayout(self)
			form.setContentsMargins(0, 0, 0, 0)
			form.addRow(self.caption, self.genre)
		else:
			self.hide()
			card_form = card.ui.form
			card_form.insertRow(field_row(card_form, card.ui.stream_fallback) + 1, self.caption, self.genre)
		self.genre.currentIndexChanged.connect(self._changed)

	def _changed(self) -> None:
		if not self._loading:
			self.changed.emit()

	def read(self, identifier: int | None) -> None:
		self._loading = True
		self.genre.clear()
		self.genre.addItem(t("no genre"), None)
		for genre, name, colour in queries.genres(self.connection):
			self.genre.addItem(swatch(colour), name, genre)
		chosen = None
		if identifier is not None:
			chosen = queries.event_genre(self.connection, identifier)
		index = self.genre.findData(chosen)
		if index < 0:
			# Un genre retiré depuis : l'événement n'en a plus.
			index = 0
		self.genre.setCurrentIndex(index)
		self._loading = False

	def chosen(self) -> int | None:
		value = self.genre.currentData()
		if isinstance(value, int):
			return value
		return None

	def write(self, identifier: int) -> None:
		queries.write_genre(self.connection, identifier, self.chosen())
		if self.written is not None:
			self.written()
