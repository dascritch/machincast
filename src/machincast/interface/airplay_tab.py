"""Onglet Airplay (https://github.com/dascritch/machincast/issues/244, spec § 8.1).

L'historique de diffusion, dans un onglet à part, fermé au lancement, que le menu « Affichage » ouvre
(MainWindow._ouvrir_airplay). Il montre les passages des dernières heures, du plus récent au plus ancien, avec
les colonnes de l'airplay de l'onglet Antenne (DefaultScreen.AIRPLAY_COLUMNS). Le nombre d'heures se règle en haut de
l'onglet, de 1 à HOURS_AT_MOST ; il est retenu pour le compte, dans les réglages des vues
(machincast.interface.columns). Comme dans l'onglet Antenne, un double-clic demande la fiche du sonore, de l'événement,
de la séquence ou de la banque (ouverte), et le clic droit sur une ligne propose « Pré-écoute… » de son sonore
(requested_preview).

« Exporter… » enregistre ce que l'onglet montre, relu en base, en CSV, en HTML ou en M3U
(machincast.interface.export_airplay), selon le filtre choisi dans le sélecteur de fichier (dialogs.choose_export).
Le nom reçoit l'extension du format s'il ne l'a pas déjà : un export ne remplace jamais un fichier sonore
(https://github.com/dascritch/machincast/issues/96, machincast.protection). La barre d'état de la fenêtre dit où
l'export est enregistré (annonce).

« Aujourd'hui », à gauche du nombre d'heures, coché au départ, montre les dernières heures ; décoché, il montre à la
place du nombre d'heures deux moments du passé, un début, pas plus loin que la durée de péremption, au-delà de
laquelle Machin purge efface l'airplay, et une fin, entre le début et maintenant ; la table et l'export montrent les
passages commencés entre eux, le début et la fin de chaque passage en ISO 8601, date et heure
(https://github.com/dascritch/machincast/issues/629).

L'onglet se relit à son ouverture, à chaque réglage, et quand l'onglet Antenne voit un nouveau sonore (actualiser) :
jamais en boucle.

Un filtre, comme celui de l'onglet Incidents, garde les passages dont une colonne contient le texte tapé, sans tenir
compte des majuscules ni des accents (FilterWithoutAccents) ; un clic sur un titre de colonne trie les passages,
le début et la fin dans l'ordre du temps, même sur plusieurs jours, la durée dans l'ordre des durées ; avant, ils
gardent l'ordre de la base, le plus récent en tête (https://github.com/dascritch/machincast/issues/393).
"""

import logging
from datetime import datetime, timedelta
from typing import cast

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QDate, QDateTime, QModelIndex, Qt, QTime, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
	QAbstractItemView,
	QCheckBox,
	QDateTimeEdit,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QMenu,
	QPushButton,
	QSpinBox,
	QTableView,
	QVBoxLayout,
	QWidget,
)

from machincast.clock import Clock
from machincast.configuration import Metadata
from machincast.i18n import _, counted, ngettext
from machincast.interface import columns, dialogs, preferences
from machincast.interface.airplay import HOURS, DisplayedPlay, read_airplay
from machincast.interface.columns import Columns
from machincast.interface.default_screen import (
	ITEM,
	LOCATION,
	DefaultScreen,
	line_menu,
	play_cells,
	play_items,
	play_location,
)
from machincast.interface.export_airplay import FORMATS, in_csv, in_html, in_m3u
from machincast.interface.lists import SORT, FilterWithoutAccents, without_accents
from machincast.interface.simulation import with_extension
from machincast.player.outputs import read_plays
from machincast.protection import check_writing

log = logging.getLogger(__name__)

HOURS_AT_MOST = 24 * 31
"""Le plus grand nombre d'heures que l'onglet propose : un mois."""
HOUR_SETTING = "onglet-airplay/heures"
"""Dans les réglages des vues du compte : le nombre d'heures montré."""
WITHOUT_METADATA = Metadata(hide=False, public_text="")
MOMENT = "yyyy-MM-dd'T'HH:mm"
"""L'affichage des deux moments des archives, ISO 8601 (https://github.com/dascritch/machincast/issues/629)."""


def retained_hours() -> int:
	value = columns.settings().value(HOUR_SETTING)
	try:
		hours = int(str(value))
	except ValueError:
		return HOURS
	return min(HOURS_AT_MOST, max(1, hours))


def _sort_keys(play: DisplayedPlay) -> list[object]:
	"""Ce qui trie chaque colonne : le début et la fin par leur instant, le passage en cours après les autres, la durée
	en secondes, le reste par son texte, sans majuscules ni accents."""
	end: float = float("inf")
	if play.end is not None:
		end = play.end.timestamp()
	duration = -1.0
	if play.duration is not None:
		duration = play.duration.total_seconds()
	keys: list[object] = [play.start.timestamp(), end, duration]
	for text in play_cells(play)[3:]:
		keys.append(without_accents(text))
	return keys


class AirplayScreen(QWidget):
	opened = Signal(str, int, str)
	"""Fiche demandée : genre, identifiant et nom de l'élément."""
	requested_preview = Signal(int)
	"""« Pré-écoute… » choisi au clic droit sur une ligne : son sonore."""
	announces = Signal(str)
	"""Ce que la barre d'état de la fenêtre dit d'un export."""
	COLUMNS = DefaultScreen.AIRPLAY_COLUMNS

	def __init__(
		self,
		connection: psycopg.Connection[TupleRow],
		clock: Clock,
		metadata: Metadata = WITHOUT_METADATA,
		parent: QWidget | None = None,
	) -> None:
		"""metadonnees : le masquage et le texte public de la configuration, pour le texte public des exports."""
		super().__init__(parent)
		self.connection = connection
		self.clock = clock
		self.metadata = metadata
		self.hours = QSpinBox(self)
		self.hours.setObjectName("hours")
		self.hours.setRange(1, HOURS_AT_MOST)
		self.hours.setSuffix(" h")
		self.hours.setValue(retained_hours())
		self.hours.setToolTip(_("The plays started within this number of hours; kept for the next openings"))
		caption = QLabel(_("&Last hours"), self)
		caption.setBuddy(self.hours)
		self.hours_caption = caption
		self.today = QCheckBox(_("&Today"), self)
		self.today.setObjectName("today")
		self.today.setChecked(True)
		self.today.setToolTip(_("Ticked: the last hours; unticked: the plays started between two moments of the past"))
		self.since = self._moment("since", _("The plays started from this moment, within the retention period"))
		self.until = self._moment("until", _("The plays started until this moment, between the start and now"))
		self.since_caption = QLabel(_("&From"), self)
		self.since_caption.setBuddy(self.since)
		self.until_caption = QLabel(_("t&o"), self)
		self.until_caption.setBuddy(self.until)
		self.export = QPushButton(_("&Export…"), self)
		self.export.setToolTip(_("Save what the tab shows, as CSV, HTML or M3U"))
		self.table = QTableView(self)
		self.table.setObjectName("table_airplay")
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setAlternatingRowColors(True)
		self.table.verticalHeader().setVisible(False)
		self.table.horizontalHeader().setStretchLastSection(True)
		self.table.setToolTip(_("Double-click on a sound, an event, a sequence or a bank: open its card"))
		self.model = QStandardItemModel(0, len(self.COLUMNS), self)
		item_list = []
		for _key, title in self.COLUMNS:
			item_list.append(title)
		self.model.setHorizontalHeaderLabels(item_list)
		self.proxy = FilterWithoutAccents(self)
		self.proxy.setSourceModel(self.model)
		self.proxy.setSortRole(SORT)
		self.table.setModel(self.proxy)
		self.columns = Columns(self.table, "onglet-airplay")
		# Un clic sur un titre de colonne trie les passages ; avant, ils gardent l'ordre de la base.
		self.table.setSortingEnabled(True)
		self.table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
		self.filter_ = QLineEdit(self)
		self.filter_.setObjectName("filter_airplay")
		self.filter_.setPlaceholderText(_("Filter…"))
		self.filter_.setClearButtonEnabled(True)
		self.filter_.setToolTip(_("The plays of which a column contains this text, whatever the case and the accents"))
		self.count = QLabel(self)
		top = QHBoxLayout()
		top.addWidget(self.today)
		top.addWidget(caption)
		top.addWidget(self.hours)
		top.addWidget(self.since_caption)
		top.addWidget(self.since)
		top.addWidget(self.until_caption)
		top.addWidget(self.until)
		top.addWidget(self.filter_, 1)
		top.addWidget(self.count)
		top.addWidget(self.export)
		arrangement = QVBoxLayout(self)
		arrangement.addLayout(top)
		arrangement.addWidget(self.table, 1)
		self.hours.valueChanged.connect(self._set)
		self.today.toggled.connect(self._show_period)
		self.since.dateTimeChanged.connect(self._bound_until)
		self.until.dateTimeChanged.connect(self.refresh)
		self._show_period(checked=True)
		self.filter_.textChanged.connect(self._apply_filter)
		self.export.clicked.connect(self._export)
		self.table.activated.connect(self._open_cell)
		self.columns.line_menu = lambda position: self.line_menu(self.table.indexAt(position))
		self.refresh()

	def _moment(self, name: str, tooltip: str) -> QDateTimeEdit:
		field = QDateTimeEdit(self)
		field.setObjectName(name)
		field.setDisplayFormat(MOMENT)
		field.setCalendarPopup(True)
		field.setToolTip(tooltip)
		return field

	def _show_period(self, checked: bool) -> None:  # noqa: FBT001  # le booléen du signal
		"""Coché, le nombre d'heures ; décoché, le début et la fin, d'abord les dernières heures, bornés par la durée de
		péremption et maintenant (https://github.com/dascritch/machincast/issues/629)."""
		hours: tuple[QWidget, ...] = (self.hours_caption, self.hours)
		moments: tuple[QWidget, ...] = (self.since_caption, self.since, self.until_caption, self.until)
		for widget in hours:
			widget.setVisible(checked)
		for widget in moments:
			widget.setVisible(not checked)
		if not checked:
			now = self.clock.now().astimezone().replace(second=0, microsecond=0)
			for field in (self.since, self.until):
				field.blockSignals(True)
			self.since.setDateTimeRange(_qt_moment(now - timedelta(days=preferences.retention())), _qt_moment(now))
			self.since.setDateTime(_qt_moment(now - timedelta(hours=self.hours.value())))
			self.until.setDateTimeRange(self.since.dateTime(), _qt_moment(now))
			self.until.setDateTime(_qt_moment(now))
			for field in (self.since, self.until):
				field.blockSignals(False)
		self.refresh()

	def _bound_until(self) -> None:
		"""La fin ne précède jamais le début : elle le suit au besoin."""
		self.until.setMinimumDateTime(self.since.dateTime())
		self.refresh()

	def period(self) -> tuple[datetime, datetime | None]:
		"""Le début et la fin des passages montrés : les dernières heures, sans fin, ou les deux moments choisis."""
		if self.today.isChecked():
			return self.clock.now() - timedelta(hours=self.hours.value()), None
		return _python_moment(self.since), _python_moment(self.until)

	def refresh(self) -> None:
		"""Relit les passages ; une base injoignable laisse la table telle qu'elle était."""
		since, until = self.period()
		try:
			plays = read_airplay(self.connection, since, until=until)
		except psycopg.Error as error:
			log.error(_("unreadable airplay: {error}").format(error=error))
			return
		self.model.setRowCount(0)
		for play in plays:
			cells = []
			for text, key in zip(play_cells(play, dated=until is not None), _sort_keys(play), strict=True):
				cell = QStandardItem(text)
				cell.setData(key, SORT)
				cells.append(cell)
			for column, item in play_items(play).items():
				cells[column].setData(item, ITEM)
			cells[0].setData(play_location(play), LOCATION)
			self.model.appendRow(cells)
		self._count()

	def _apply_filter(self, text: str) -> None:
		self.proxy.apply_filter(text)
		self._count()

	def _count(self) -> None:
		"""Combien de passages l'onglet montre ; avec un filtre, sur combien."""
		total = self.model.rowCount()
		shown = self.proxy.rowCount()
		text = counted("{count} play", "{count} plays", total)
		if self.filter_.text() != "":
			text = ngettext("{count} play out of {total}", "{count} plays out of {total}", shown).format(
				count=shown, total=total
			)
		self.count.setText(text)

	def _set(self, hours: int) -> None:
		columns.settings().setValue(HOUR_SETTING, hours)
		self.refresh()

	def _open_cell(self, index: QModelIndex) -> None:
		item = index.data(ITEM)
		if item is not None:
			category, identifier, name = item
			self.opened.emit(category, identifier, name)

	def line_menu(self, index: QModelIndex) -> QMenu | None:
		"""« Pré-écoute… » du sonore de la ligne, puis son emplacement, comme l'airplay de l'onglet Antenne ; aucun
		menu hors d'une ligne."""
		return line_menu(self, self.model, self.proxy.mapToSource(index), self.requested_preview.emit)

	def _export(self) -> None:
		now = self.clock.now()
		hours = self.hours.value()
		since, until = self.period()
		offers = f"airplay-{now.astimezone():%Y-%m-%d-%H%M}-{hours}h.csv"
		title = _("Airplay of the last {hours} hours, at {now:%d/%m/%Y %H:%M}").format(
			hours=hours, now=now.astimezone()
		)
		if until is not None:
			offers = f"airplay-{since.astimezone():%Y-%m-%d-%H%M}-{until.astimezone():%Y-%m-%d-%H%M}.csv"
			title = _("Airplay from {since:%Y-%m-%dT%H:%M} to {until:%Y-%m-%dT%H:%M}").format(
				since=since.astimezone(), until=until.astimezone()
			)
		choice = dialogs.choose_export(self, offers, list(FORMATS), _("Export the airplay"))
		if choice is None:
			return
		path, filter_ = choice
		extension = FORMATS[filter_]
		destination = with_extension(path, extension)
		try:
			lines = read_plays(self.connection, None, since=since, until=until)
			contents = {
				".csv": lambda: in_csv(lines, self.metadata),
				".html": lambda: in_html(lines, self.metadata, title, now),
				".m3u": lambda: in_m3u(lines, self.metadata),
			}
			content = contents[extension]()
			check_writing(destination)
			# Le BOM laisse les tableurs reconnaître l'UTF-8 du CSV.
			encoding = "utf-8"
			if extension == ".csv":
				encoding = "utf-8-sig"
			destination.write_text(content, encoding=encoding, newline="")
		except (OSError, psycopg.Error) as error:
			self.announces.emit(_("Export impossible: {error}").format(error=error))
			return
		self.announces.emit(_("Airplay exported to {destination}.").format(destination=destination))


def _qt_moment(moment: datetime) -> QDateTime:
	return QDateTime(QDate(moment.year, moment.month, moment.day), QTime(moment.hour, moment.minute))


def _python_moment(field: QDateTimeEdit) -> datetime:
	"""Le moment d'un champ, en heure du poste, avec son fuseau ; à la fin de sa minute pour la fin, au début pour le
	début : un passage commencé à 19:00:30 est dans « jusqu'à 19:00 »."""
	moment = cast(datetime, field.dateTime().toPython()).astimezone()
	if field.objectName() == "until":
		return moment + timedelta(seconds=59)
	return moment
