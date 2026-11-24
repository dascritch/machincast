"""La section « Genre » de la fiche d'un événement, dans Machin interface
(https://github.com/dascritch/machincast/issues/628), par le point « interface.event_card »
(https://github.com/dascritch/machincast/issues/611).

Une liste de choix : aucun genre, ou l'un des genres réglés dans la fenêtre du plugin, chacun avec un carré de sa
couleur. Le genre s'enregistre avec l'événement, dans sa colonne properties, sous la clé du plugin ; sans genre, la clé
en part.
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QComboBox, QFormLayout, QWidget

from machincast.interface.card import CardSection
from machincast_color_the_shows import queries
from machincast_color_the_shows.texts import t

SWATCH = 14
"""Le côté, en pixels, du carré de la couleur d'un genre."""


def swatch(colour: str) -> QIcon:
	"""Un carré de la couleur."""
	picture = QPixmap(SWATCH, SWATCH)
	picture.fill(QColor(colour))
	return QIcon(picture)


class GenreSection(CardSection):
	def __init__(
		self,
		connection: queries.Connection,
		parent: QWidget | None = None,
		written: Callable[[], Any] | None = None,
	) -> None:
		"""written est appelé après l'écriture du genre : la palette relit la base au prochain dessin."""
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
		form = QFormLayout(self)
		form.setContentsMargins(0, 0, 0, 0)
		form.addRow(t("Genre"), self.genre)
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
