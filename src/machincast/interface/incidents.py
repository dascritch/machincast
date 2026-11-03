"""Écran des incidents (https://github.com/dascritch/machincast/issues/35, spec § 8.6).

Les entrées du log que Machin player a notées, du plus récent au plus ancien : par défaut les alertes et les
incidents, les informations sur demande ; seules les LIMITE plus récentes sont lues. Chaque entrée donne son horaire,
son niveau, sa nature, son message, et ce qu'elle concerne : sonore, banque, événement, quand c'est renseigné. Un
double-clic sur l'un d'eux demande sa fiche (ouverte) ; un élément supprimé depuis laisse sa cellule vide, l'entrée
garde son message. Comme une liste (machincast.interface.lists), l'écran se relit à l'ouverture de son onglet, et se
filtre sans tenir compte des majuscules ni des accents.

L'indexeur n'écrit pas dans le log : ses anomalies n'y figurent pas.
"""

import logging
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QTableView, QWidget

from machincast.i18n import _, counted, logged, ngettext
from machincast.interface import display
from machincast.interface.columns import Columns
from machincast.interface.lists import FilterWithoutAccents
from machincast.interface.ui.incidents import Ui_IncidentScreen
from machincast.player.saving import LEVELS

log = logging.getLogger(__name__)

LIMIT = 500
"""Nombre d'entrées lues au plus, les plus récentes."""
COLUMNS = (_("Time"), _("Level"), _("Kind"), _("Message"), _("Sound"), _("Bank"), _("Event"))
LINKS = {4: "sonore", 5: "banque", 6: "événement"}
"""Colonnes qui désignent un élément, et son genre."""
ITEM = Qt.ItemDataRole.UserRole
"""Rôle qui porte l'identifiant de l'élément d'une cellule de lien."""


class IncidentScreen(QWidget):
	opened = Signal(str, int, str)
	"""Élément ouvert depuis une entrée : genre, identifiant et nom."""

	def __init__(self, connection: psycopg.Connection[TupleRow], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.connection = connection
		self.ui = Ui_IncidentScreen()
		self.ui.setupUi(self)
		self.model = QStandardItemModel(0, len(COLUMNS), self)
		self.model.setHorizontalHeaderLabels(list(COLUMNS))
		self.proxy = FilterWithoutAccents(self)
		self.proxy.setSourceModel(self.model)
		self.table.setModel(self.proxy)
		self.columns = Columns(self.table, "incidents")
		self._reached_limit = False
		self.ui.filter_.textChanged.connect(self._apply_filter)
		self.ui.information.toggled.connect(self.refresh)
		self.table.activated.connect(self._open)
		self._count()

	@property
	def table(self) -> QTableView:
		return self.ui.table

	def refresh(self) -> None:
		"""Relit le log ; une base injoignable laisse l'écran tel qu'il était."""
		levels = ["warning", "incident"]
		if self.ui.information.isChecked():
			levels.append("info")
		try:
			with self.connection.transaction():
				rows = self.connection.execute(
					"SELECT l.logged_at, l.level::text, l.kind, l.message, s.id, s.artist, s.title, s.location,"
					" COALESCE(s.stream_url, m.url), b.id, b.internal_name, e.id, e.internal_name FROM log l"
					" LEFT JOIN sounds s ON s.id = l.sound_id"
					" LEFT JOIN feeds m ON m.id = s.feed_id"
					" LEFT JOIN banks b ON b.id = l.bank_id LEFT JOIN events e ON e.id = l.event_id"
					" WHERE l.level::text = ANY(%s) ORDER BY l.logged_at DESC, l.id DESC LIMIT %s",
					(levels, LIMIT),
				).fetchall()
		except psycopg.Error as error:
			log.error(_("unreadable incidents screen: {error}").format(error=error))
			return
		self.model.setRowCount(0)
		for timestamp, level, kind, message, *references in rows:
			sound, artist, title, location, address, bank, bank_name, event, event_name = references
			assert isinstance(timestamp, datetime)
			cells = [
				QStandardItem(f"{timestamp.astimezone():%Y-%m-%d %H:%M:%S}"),
				QStandardItem(LEVELS.get(str(level), str(level))),
				QStandardItem(logged(str(kind))),
				QStandardItem(logged(str(message))),
				_link(sound, display.sound_name(artist, title, location, address)),
				_link(bank, str(bank_name)),
				_link(event, str(event_name)),
			]
			self.model.appendRow(cells)
		self._reached_limit = len(rows) == LIMIT
		self._count()

	def _apply_filter(self, text: str) -> None:
		self.proxy.apply_filter(text)
		self._count()

	def _count(self) -> None:
		total = self.model.rowCount()
		visible_list = self.proxy.rowCount()
		text = counted("{count} entry", "{count} entries", total)
		if total == 0:
			text = _("no entry")
		elif self.ui.filter_.text() != "":
			text = ngettext("{count} entry out of {total}", "{count} entries out of {total}", visible_list).format(
				count=visible_list, total=total
			)
		elif self._reached_limit:
			text = _("{text}, the most recent").format(text=text)
		self.ui.count.setText(text)

	def _open(self, index: QModelIndex) -> None:
		"""Un double-clic sur un lien demande la fiche de son élément ; ailleurs, il ne fait rien."""
		# Seule une cellule de lien porte un élément.
		identifier = index.data(ITEM)
		if identifier is not None:
			self.opened.emit(LINKS[index.column()], int(identifier), str(index.data()))


def _link(identifier: object, name: str) -> QStandardItem:
	"""La cellule d'un élément ; vide quand l'entrée n'en désigne pas, ou plus."""
	if identifier is None:
		return QStandardItem("")
	cell = QStandardItem(name)
	cell.setData(int(str(identifier)), ITEM)
	return cell
