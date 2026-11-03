"""Recherche globale (https://github.com/dascritch/machincast/issues/27,
https://github.com/dascritch/machincast/issues/105, spec § 8.2).

L'onglet « Recherche » (SearchScreen), qui se ferme, s'ouvre par « Affichage → Rechercher… » ou Ctrl+F
(machincast.interface.window). Dès MINIMUM caractères, le texte tapé est cherché, sans tenir compte des majuscules ni
des accents, dans le nom interne et le nom public des événements, des séquences et des banques, et dans l'artiste et
le titre des sonores (chercher). Les résultats vont dans l'ordre : événements, séquences, banques, sonores, chacun par
nom. La table les donne au fil de la frappe, jusqu'à LIMITE, avec le compte ; le champ ne propose pas de suggestions.
Ouvrir une ligne de la table (double-clic, Entrée) demande la fiche de l'élément (signal ouverte), sans toucher au texte
cherché. La recherche se relance à l'ouverture de l'onglet et au
rafraîchissement des onglets : jamais en boucle.

Les accents sont retirés des deux côtés : en base par translate(), pour les lettres de ACCENTUEES ; dans le texte tapé
par lists.without_accents. Les caractères % et _ de LIKE sont cherchés tels quels.
"""

import logging
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
	QAbstractItemView,
	QLabel,
	QLineEdit,
	QTableView,
	QVBoxLayout,
	QWidget,
)

from machincast.i18n import _, counted
from machincast.interface import icons
from machincast.interface.columns import Columns
from machincast.interface.lists import STATES, without_accents

log = logging.getLogger(__name__)

Connection = psycopg.Connection[TupleRow]
MINIMUM = 2
"""Caractères à taper avant de chercher."""
LIMIT = 500
"""Lignes de la table des résultats, au plus."""
COLUMNS = (_("Type"), _("Internal name"), _("Public name"), _("Status"))
TYPES = {"événement": _("Event"), "séquence": _("Sequence"), "banque": _("Bank"), "sonore": _("Sound")}
ACCENTED = "àâäáãåçéèêëíìîïñóòôöõúùûüýÿÀÂÄÁÃÅÇÉÈÊËÍÌÎÏÑÓÒÔÖÕÚÙÛÜÝ"
WITHOUT_ACCENT = "aaaaaaceeeeiiiinooooouuuuyyaaaaaaceeeeiiiinooooouuuuy"
"""Les lettres accentuées, minuscules et majuscules, que la base ramène à leur lettre de base, dans le même ordre :
avant lower(), qui ne sait pas toujours abaisser une majuscule accentuée, selon la locale de la base."""
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


def _normalised(column: str) -> str:
	return f"lower(translate(COALESCE({column}, ''), '{ACCENTED}', '{WITHOUT_ACCENT}'))"


def _pattern(text: str) -> str:
	"""Le texte, sans accents ni majuscules, entre deux % de LIKE ; ses \\, % et _ sont cherchés tels quels."""
	escapes = without_accents(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return f"%{escapes}%"


def _finds(*columns: str) -> str:
	return " OR ".join(f"{_normalised(column)} LIKE recherche.motif" for column in columns)


FOUND_LIST = f"""
	WITH recherche AS (SELECT %s::text AS motif)
	SELECT 1 AS rang, 'événement' AS genre, id, internal_name AS name, public_name, NULL AS state FROM events, recherche
		WHERE (deleted_at IS NULL) AND ({_finds("internal_name", "public_name")})
	UNION ALL
	SELECT 2, 'séquence', id, internal_name, public_name, NULL FROM sequences, recherche
		WHERE (deleted_at IS NULL) AND ({_finds("internal_name", "public_name")})
	UNION ALL
	SELECT 3, 'banque', id, internal_name, public_name, NULL FROM banks, recherche
		WHERE (deleted_at IS NULL) AND ({_finds("internal_name", "public_name")})
	UNION ALL
	SELECT 4, 'sonore', id, concat_ws(' – ', artist, title), NULL, state::text FROM sounds, recherche
		WHERE (deleted_at IS NULL) AND ({_finds("artist", "title")})
"""
"""Les éléments où se trouve le motif, lié une seule fois (recherche.motif), avec le rang de leur type ; jamais un
élément supprimé (https://github.com/dascritch/machincast/issues/267)."""


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
		lines = connection.execute(
			f"SELECT genre, id, name, public_name, state FROM ({FOUND_LIST}) t ORDER BY rang, lower(name), id"  # noqa: S608
			" LIMIT %s",
			(pattern, limit),
		).fetchall()
		line = connection.execute(f"SELECT count(*) FROM ({FOUND_LIST}) t", (pattern,)).fetchone()  # noqa: S608
	assert line is not None
	results = [
		Result(
			str(category),
			int(str(identifier)),
			str(name),
			str((public_name) or ("")),
			_status(state),
		)
		for category, identifier, name, public_name, state in lines
	]
	return results, int(str(line[0]))


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
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.verticalHeader().hide()
		self.table.horizontalHeader().setStretchLastSection(True)
		self.columns = Columns(self.table, "recherche")
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
		self._show(total, len(text.strip()) >= MINIMUM)

	def _show(self, total: int, looks_for: bool) -> None:
		self.model.setRowCount(0)
		for result in self.results:
			cells = [QStandardItem(text) for text in (TYPES[result.category], result.name, result.public_name)]
			# L'icône du genre (https://github.com/dascritch/machincast/issues/215).
			cells[0].setIcon(icons.icon_of(result.category))
			cells.append(QStandardItem(result.status))
			self.model.appendRow(cells)
		text = TOO_SHORT
		if (looks_for) and (total == 0):
			text = _("no result")
		elif total > len(self.results):
			text = _("first {count} results out of {total}").format(count=len(self.results), total=total)
		elif looks_for:
			text = counted("{count} result", "{count} results", total)
		self.count.setText(text)

	def _opened_line(self, index: QModelIndex) -> None:
		self._open(index.row())

	def _open(self, row: int) -> None:
		if 0 <= row < len(self.results):
			result = self.results[row]
			self.opened.emit(result.category, result.identifier, result.name)
