"""La case « Station ID régulier » de la fiche d'un événement, dans Machin interface
(https://github.com/dascritch/machincast/issues/460), par le point « interface.event_card »
(https://github.com/dascritch/machincast/issues/611).

Dans la fiche, elle est une ligne du formulaire, sous « Secours d'un stream tombé » : la section elle-même, cachée,
ne décale pas la liste de lecture. Cochée, elle s'enregistre avec l'événement, dans sa colonne properties, sous la clé
du plugin ; décochée, la clé en part. Son infobulle dit les réglages de machincast.toml.
"""

from PySide6.QtWidgets import QCheckBox, QFormLayout, QVBoxLayout, QWidget

from machincast.interface.card import CardSection
from machincast.interface.event_card import EventCard
from machincast_timely_station_id import queries
from machincast_timely_station_id.rule import Current, Settings
from machincast_timely_station_id.texts import t


def field_row(form: QFormLayout, widget: QWidget) -> int:
	"""La ligne du formulaire dont ce widget est le champ."""
	for row in range(form.rowCount()):
		item = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
		if (item is not None) and (item.widget() is widget):
			return row
	raise LookupError(widget.objectName())


def explanation(settings: Settings | None) -> str:
	if settings is None:
		return t("A station ID at regular intervals, once its settings are in machincast.toml")
	return t(
		"A station ID of the bank “{bank}”, every {minimum} to {maximum} minutes, whatever the length of the songs"
	).format(
		bank=settings.bank,
		minimum=f"{settings.minimum.total_seconds() / 60:g}",
		maximum=f"{settings.maximum.total_seconds() / 60:g}",
	)


class RegularSection(CardSection):
	def __init__(
		self,
		connection: queries.Connection,
		current: Current,
		parent: QWidget | None = None,
		card: EventCard | None = None,
	) -> None:
		super().__init__(parent)
		self.setObjectName("timely_station_id")
		self.connection = connection
		self._loading = False
		self.regular = QCheckBox(t("Regular station ID"), self)
		self.regular.setObjectName("regular_station_id")
		self.regular.setToolTip(explanation(current.settings))
		if card is None:
			layout = QVBoxLayout(self)
			layout.setContentsMargins(0, 0, 0, 0)
			layout.addWidget(self.regular)
		else:
			self.hide()
			form = card.ui.form
			form.insertRow(field_row(form, card.ui.stream_fallback) + 1, "", self.regular)
		self.regular.toggled.connect(self._changed)

	def _changed(self) -> None:
		if not self._loading:
			self.changed.emit()

	def read(self, identifier: int | None) -> None:
		self._loading = True
		chosen = False
		if identifier is not None:
			chosen = queries.chosen(self.connection, identifier)
		self.regular.setChecked(chosen)
		self._loading = False

	def write(self, identifier: int) -> None:
		queries.write_chosen(self.connection, identifier, regular=self.regular.isChecked())
