"""Recherche globale (https://github.com/dascritch/machincast/issues/27,
https://github.com/dascritch/machincast/issues/105, spec § 8.2).

L'onglet « Recherche » (SearchScreen), qui se ferme, s'ouvre par « Affichage → Rechercher… » ou Ctrl+F
(machincast.interface.window). Dès MINIMUM caractères, le texte tapé est cherché, sans tenir compte des majuscules ni
des accents, dans le nom interne et le nom public des événements, des séquences et des banques, et dans l'artiste et
le titre des sonores (chercher). Les résultats vont dans l'ordre : événements, séquences, banques, sonores, chacun par
nom. La table les donne au fil de la frappe, jusqu'à LIMITE, avec le compte ; le champ ne propose pas de suggestions.
Ouvrir une ligne de la table (double-clic, Entrée) demande la fiche de l'élément (signal ouverte), sans toucher au texte
cherché. Plusieurs lignes se choisissent à la fois (Ctrl, Maj) ; Ctrl+C, ou « Copier » au clic droit, les copie dans
le presse-papiers des listes d'éléments (machincast.interface.clipboard,
https://github.com/dascritch/machincast/issues/129) : une banque, un événement ou une séquence y colle ce qu'elle peut
contenir. La recherche se relance à l'ouverture de l'onglet et au
rafraîchissement des onglets : jamais en boucle.

Les accents sont retirés des deux côtés : en base par translate(), pour les lettres de ACCENTUEES ; dans le texte tapé
par lists.without_accents. Les caractères % et _ de LIKE sont cherchés tels quels.
"""

import logging
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, QPoint, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
	QAbstractItemView,
	QLabel,
	QLineEdit,
	QMenu,
	QTableView,
	QVBoxLayout,
	QWidget,
)

from machincast.i18n import _, counted
from machincast.interface import clipboard, icons
from machincast.interface.columns import Columns
from machincast.interface.lists import STATES, without_accents
from machincast.interface.queries import search as queries

log = logging.getLogger(__name__)

Connection = psycopg.Connection[TupleRow]
MINIMUM = 2
"""Caractères à taper avant de chercher."""
LIMIT = 500
"""Lignes de la table des résultats, au plus."""
COLUMNS = (_("Type"), _("Internal name"), _("Public name"), _("Status"))
TYPES = {"event": _("Event"), "sequence": _("Sequence"), "bank": _("Bank"), "sound": _("Sound")}
TOO_SHORT = _("Type at least {minimum} characters.").format(minimum=MINIMUM)


@dataclass(frozen=True)
class Result:
	category: str
	"""« événement », « séquence », « banque » ou « sonore », comme les fiches."""
	identifier: int
	name: str
	"""Le nom interne ; pour un sonore, son artiste et son titre."""
	public_name: str
	status: str
	"""L'état d'un sonore ; rien pour les autres."""


def _pattern(text: str) -> str:
	"""Le texte, sans accents ni majuscules, entre deux % de LIKE ; ses \\, % et _ sont cherchés tels quels."""
	escapes = without_accents(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return f"%{escapes}%"


def _status(state: object) -> str:
	"""L'état d'un sonore, en clair ; rien pour un autre élément."""
	if state is None:
		return ""
	return STATES.get(str(state), str(state))


def find(connection: Connection, text: str, limit: int) -> tuple[list[Result], int]:
	"""Les premiers résultats, jusqu'à la limite, et leur nombre total ; rien en dessous de MINIMUM caractères."""
	if len(text.strip()) < MINIMUM:
		return [], 0
	pattern = _pattern(text.strip())
	with connection.transaction():
		lines = queries.found(connection, pattern, limit)
		total = queries.count(connection, pattern)
	results = []
	for category, identifier, name, public_name, state in lines:
		results.append(
			Result(
				str(category),
				int(str(identifier)),
				str(name),
				str((public_name) or ("")),
				_status(state),
			)
		)
	return results, total


class SearchScreen(QWidget):
	opened = Signal(str, int, str)
	"""Ligne ouverte : genre, identifiant et nom de l'élément."""

	def __init__(self, connection: Connection, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.connection = connection
		self.results: list[Result] = []
		arrangement = QVBoxLayout(self)
		self.field = QLineEdit(self)
		self.field.setPlaceholderText(_("Search an event, a sequence, a bank or a sound…"))
		self.field.setClearButtonEnabled(True)
		self.field.setToolTip(
			_("Internal name and public name of the events, sequences and banks; artist and title of the sounds")
		)
		arrangement.addWidget(self.field)
		self.count = QLabel(TOO_SHORT, self)
		arrangement.addWidget(self.count)
		self.model = QStandardItemModel(0, len(COLUMNS), self)
		self.model.setHorizontalHeaderLabels(list(COLUMNS))
		self.table = QTableView(self)
		self.table.setModel(self.model)
		self.table.setAlternatingRowColors(True)
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.verticalHeader().hide()
		self.table.horizontalHeader().setStretchLastSection(True)
		self.columns = Columns(self.table, "recherche")
		self.columns.line_menu = self.line_menu
		clipboard.shortcuts(self.table, self.copy)
		arrangement.addWidget(self.table)
		self.field.textChanged.connect(self._find)
		self.table.activated.connect(self._opened_line)

	def focus(self) -> None:
		"""Le curseur dans le champ, son texte sélectionné : une nouvelle frappe le remplace."""
		self.field.setFocus()
		self.field.selectAll()

	def refresh(self) -> None:
		"""Relance la recherche du texte tapé."""
		self._find(self.field.text())

	def _find(self, text: str) -> None:
		try:
			self.results, total = find(self.connection, text, LIMIT)
		except psycopg.Error as error:
			log.error(_("search impossible: {error}").format(error=error))
			self.count.setText(_("Search impossible: {error}").format(error=error))
			return
		self._show(total, looks_for=len(text.strip()) >= MINIMUM)

	def _show(self, total: int, *, looks_for: bool) -> None:
		self.model.setRowCount(0)
		for result in self.results:
			cells = []
			for cell_text in (TYPES[result.category], result.name, result.public_name):
				cells.append(QStandardItem(cell_text))
			# L'icône du genre (https://github.com/dascritch/machincast/issues/215).
			cells[0].setIcon(icons.icon_of(result.category))
			cells.append(QStandardItem(result.status))
			self.model.appendRow(cells)
		text = TOO_SHORT
		if (looks_for) and (total == 0):
			text = _("no result")
		else:
			if total > len(self.results):
				text = _("first {count} results out of {total}").format(count=len(self.results), total=total)
			else:
				if looks_for:
					text = counted("{count} result", "{count} results", total)
		self.count.setText(text)

	def _opened_line(self, index: QModelIndex) -> None:
		self._open(index.row())

	def _open(self, row: int) -> None:
		if 0 <= row < len(self.results):
			result = self.results[row]
			self.opened.emit(result.category, result.identifier, result.name)

	def chosen(self) -> list[int]:
		"""Les rangs des lignes choisies, dans l'ordre de la table."""
		rows = []
		for index in self.table.selectionModel().selectedRows():
			rows.append(index.row())
		return sorted(rows)

	def copy(self) -> None:
		"""Les résultats choisis vont au presse-papiers, dans l'ordre de la table, avec leur texte."""
		entries = []
		text_list = []
		for row in self.chosen():
			result = self.results[row]
			entries.append(clipboard.entry(result.category, result.identifier, None, None, result.name))
			cells = []
			for column in range(self.model.columnCount()):
				cells.append(self.model.item(row, column).text())
			text_list.append("\t".join(cells))
		if entries != []:
			clipboard.put(entries, text_list)

	def line_menu(self, _position: QPoint) -> QMenu:
		"""« Copier » les résultats choisis, sur une ligne ou hors des lignes."""
		menu = QMenu(self.table)
		clipboard.offer(menu, chosen=self.chosen() != [], copy=self.copy)
		return menu
