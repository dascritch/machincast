"""Listes filtrables des sonores, des banques, des séquences et des événements
(https://github.com/dascritch/machincast/issues/26, spec § 8.2).

Chaque liste est un onglet de la fenêtre (machincast.interface.window). Elle se lit en base avec le rôle de
l'interface, chaque fois que son onglet s'ouvre : jamais en boucle. Le filtre garde les lignes dont une colonne contient
le texte tapé, sans tenir compte des majuscules ni des accents. Ouvrir une ligne (double-clic ou Entrée) demande
l'écran de détail de l'élément (signal ouverte). Une liste peut avoir un bouton qui crée un élément
(signal requested_creation) : « Nouvelle banque » (https://github.com/dascritch/machincast/issues/31). Une ligne en
anomalie a une infobulle qui l'explique, et le compte les dénombre (https://github.com/dascritch/machincast/issues/138,
https://github.com/dascritch/machincast/issues/140) : une séquence ou un événement vide, une banque sans sonore actif,
une banque qui contient un sonore erroné ou non supporté, et ce sonore. Les listes des événements, des séquences, des
banques et des sonores la marquent de ⚠️ dans leur première colonne, ANOMALY_COLUMN
(https://github.com/dascritch/machincast/issues/327).
Le clic droit sur une ligne d'événement, de séquence ou de banque propose « Dupliquer » (signal requested_duplication,
https://github.com/dascritch/machincast/issues/130). Les listes des sonores et des banques sélectionnent plusieurs
lignes (Ctrl, Maj) ; leur clic droit propose les actions sur la sélection, ou sur la seule ligne cliquée hors de la
sélection (signal requested_action, machincast.interface.groups, https://github.com/dascritch/machincast/issues/114).
"""

import logging
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QLabel, QLineEdit, QMenu, QTableView, QWidget

from machincast.i18n import _, counted
from machincast.interface import display, groups
from machincast.interface.columns import Columns
from machincast.interface.drop import FileDrop
from machincast.interface.intents import ADD, label
from machincast.interface.ui.list_view import Ui_List
from machincast.player.grid import DAY_NAMES, DAYS

log = logging.getLogger(__name__)

Connection = psycopg.Connection[TupleRow]
IDENTIFIER = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la première cellule d'une ligne, l'identifiant de l'élément en base."""
SORT = IDENTIFIER + 2
"""Rôle de chaque cellule par lequel la liste se trie : son texte, sauf quand la ligne en donne un autre
(Ligne.tris)."""
STATES = {
	"preview": _("preview"),
	"active": "actif",
	"disabled": _("disabled"),
	"expired": _("expired"),
	"corrupt": _("corrupt"),
	"unsupported": _("unsupported"),
	"missing": _("deleted"),
}
TYPES = {"file": "fichier", "stream": "stream"}
"""Le type d'un sonore à l'écran, par sa valeur en base (https://github.com/dascritch/machincast/issues/358)."""
PRIORITIES = {
	"special": _("special"),
	"show": _("show"),
	"background_programming": _("background programming"),
	"fallback": "secours",
}
IMPORTANCE = {priority: rank for rank, priority in enumerate(PRIORITIES)}
AFTER_ALL = float("inf")
"""Clé de tri d'une durée ou d'une date inconnue : après les autres (https://github.com/dascritch/machincast/issues/302)."""
WITHOUT_DURATION = 1e12
"""Clé de tri d'un fichier dont la durée n'est pas encore mesurée : après les durées connues, avant les streams."""
WITHOUT_DAY = "~"
"""Clé de tri d'un événement sans récurrence : après les jours, que leurs chiffres classent."""
"""Le tri de la colonne « Priorité » : du plus important au moins important, jamais par ordre alphabétique
(https://github.com/dascritch/machincast/issues/272)."""
MODES = {"sequential": _("sequential"), "random": _("random")}
EMPTY_SEQUENCE = _("Empty sequence: it plays nothing, and an event that calls it moves on to its next element.")
_RELAY = _("Empty event: it plays nothing, and the event of lower priority takes over during its slot.")
EMPTY_EVENT = {
	"special": _RELAY,
	"show": _RELAY,
	"background_programming": (
		_("Empty event: it plays nothing, and the broadcast goes silent, with an alert, when it is on air.")
	),
	"fallback": _("Empty event: it plays nothing, and the event of lower priority replaces the dropped stream."),
}
"""Ce que fait la diffusion d'un événement vide, selon sa priorité (spec § 4.2,
https://github.com/dascritch/machincast/issues/140)."""
BANK_WITHOUT_ACTIVE_SOUND = _(
	"Bank without an active sound: it provides nothing, and the element that calls it moves on to its next element."
)


def bank_to_sounds_in_anomaly(count: int) -> str:
	"""Une banque qui a des sonores actifs, mais aussi des sonores erronés ou non supportés : ceux-là ne passent pas."""
	return counted(
		"Bank with {count} corrupt or unsupported sound: the broadcast does not play it.",
		"Bank with {count} corrupt or unsupported sounds: the broadcast does not play them.",
		count,
	)


SOUND_IN_ANOMALY = {
	"corrupt": _("Corrupt sound: its file is unreadable or damaged, and the broadcast does not play it."),
	"unsupported": _("Unsupported sound: its file is not a readable sound, and the broadcast does not play it."),
}
"""Les états d'un sonore que la diffusion ne joue pas sans que personne l'ait voulu (spec § 3.1, § 4.5)."""
ANOMALY_COLUMN = "⚠️"
"""Titre de la première colonne des listes en anomalie, et ce qu'elle montre sur une ligne en anomalie
(https://github.com/dascritch/machincast/issues/327)."""
ANOMALY_TOOLTIP = _("Anomaly: the line has a problem, which its tooltip tells")


@dataclass(frozen=True)
class Line:
	identifier: int
	name: str
	"""Nom de l'élément, pour l'annoncer."""
	cells: list[str]
	anomaly: str = ""
	"""Ce qui ne va pas, en une phrase, pour l'infobulle de la ligne ; rien pour une ligne saine."""
	sorts: dict[int, int | float | str] = field(default_factory=dict)
	"""Par colonne, la clé de tri d'une cellule qui ne se trie pas par son texte (TRI)."""


@dataclass(frozen=True)
class Source:
	"""Un type d'élément : ses colonnes, sa lecture en base, et les mots pour le compter."""

	category: str
	columns: tuple[str, ...]
	read: Callable[[Connection], list[Line]]
	counting: Callable[[int], str]
	"""« 1 sonore », « 2 sonores » : le nombre d'éléments, accordé et traduit."""
	plural: str
	"""Le nom des éléments au pluriel, traduit : « sonores »."""
	no: str
	new: str = ""
	"""Texte du bouton qui crée un élément de ce type ; aucun bouton sans texte."""
	files: str = ""
	"""Texte du bouton qui ajoute des fichiers, qui se déposent aussi sur la liste ; ni bouton ni dépôt sans texte."""
	duplicable: bool = False
	"""Le clic droit sur une ligne propose « Dupliquer »."""
	anomalies: bool = False
	"""Une première colonne, COLONNE_D_ANOMALIE, marque les lignes en anomalie."""
	views: str = ""
	"""La clé des réglages de ses vues, qui ne dépend pas de la langue : le pluriel français d'avant
	https://github.com/dascritch/machincast/issues/360, pour garder les dispositions de colonnes déjà retenues."""


def _text(value: object) -> str:
	if value is None:
		return ""
	return str(value)


def _date(value: object) -> str:
	if not isinstance(value, datetime):
		return ""
	return f"{value.astimezone():%Y-%m-%d %H:%M}"


SOUND_COLUMNS = (_("Artist"), _("Title"), _("Type"), _("State"), _("Duration"), _("Location"))
DURATION_POSITION = SOUND_COLUMNS.index(_("Duration"))


def read_sounds(connection: Connection) -> list[Line]:
	with connection.transaction():
		rows = connection.execute(
			"SELECT s.id, s.artist, s.title, s.type::text, s.state::text, s.audit_requested, s.duration,"
			" COALESCE(s.location, s.stream_url, m.url)"
			" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.deleted_at IS NULL"
			" ORDER BY s.artist NULLS LAST, s.title, s.id"
		).fetchall()
	lines = []
	for identifier, artist, title, sound_type, state, requested_audit, duration, location in rows:
		duration_text = ""
		if sound_type == "stream":
			duration_text = display.duration(None)
		elif isinstance(duration, timedelta):
			duration_text = display.duration(duration)
		state_text = STATES.get(str(state), str(state))
		if requested_audit is True:
			# https://github.com/dascritch/machincast/issues/114
			state_text = _("{state_text}, audit requested").format(state_text=state_text)
		# Les durées d'une banque ne se signalent que dans sa fiche, et parmi les relations du sonore, jamais ici
		# (https://github.com/dascritch/machincast/issues/210).
		cells = [
			_text(artist),
			_text(title),
			TYPES.get(str(sound_type), str(sound_type)),
			state_text,
			duration_text,
		]
		cells.append(_text(location))
		# https://github.com/dascritch/machincast/issues/302 : par les secondes ; sans durée mesurée, après les durées
		# connues ; un stream, sans fin, en dernier.
		duration_sort: float = WITHOUT_DURATION
		if sound_type == "stream":
			duration_sort = AFTER_ALL
		elif isinstance(duration, timedelta):
			duration_sort = duration.total_seconds()
		sound_name = (_text(title)) or (_text(location))
		anomaly = SOUND_IN_ANOMALY.get(str(state), "")
		sorts: dict[int, int | float | str] = {DURATION_POSITION: duration_sort}
		lines.append(Line(int(str(identifier)), sound_name, cells, anomaly, sorts))
	return lines


def read_banks(connection: Connection) -> list[Line]:
	with connection.transaction():
		rows = connection.execute(
			"SELECT b.id, b.internal_name, b.public_name, b.mode::text, b.no_repeat,"
			" (SELECT min(r.directory) FROM bank_directories r WHERE r.bank_id = b.id),"
			" NOT EXISTS (SELECT 1 FROM bank_sounds x JOIN sounds s ON s.id = x.sound_id"
			" WHERE x.bank_id = b.id AND s.state = 'active' AND s.deleted_at IS NULL),"
			" (SELECT count(*) FROM bank_sounds x JOIN sounds s ON s.id = x.sound_id"
			" WHERE x.bank_id = b.id AND s.state IN ('corrupt', 'unsupported') AND s.deleted_at IS NULL)"
			" FROM banks b WHERE b.deleted_at IS NULL ORDER BY b.internal_name, b.id"
		).fetchall()
	lines = []
	for identifier, name, public_name, mode, marked, directory, without_active_sound, in_anomaly in rows:
		cells = [str(name), _text(public_name), MODES.get(str(mode), str(mode))]
		cells += [display.yes_no(bool(marked)), _text(directory)]
		anomaly = ""
		if without_active_sound:
			anomaly = BANK_WITHOUT_ACTIVE_SOUND
		elif int(str(in_anomaly)) > 0:
			anomaly = bank_to_sounds_in_anomaly(int(str(in_anomaly)))
		lines.append(Line(int(str(identifier)), str(name), cells, anomaly))
	return lines


def read_sequences(connection: Connection) -> list[Line]:
	with connection.transaction():
		rows = connection.execute(
			"SELECT q.id, q.internal_name, q.public_name,"
			" NOT EXISTS (SELECT 1 FROM sequence_items e WHERE e.sequence_id = q.id)"
			" FROM sequences q WHERE q.deleted_at IS NULL ORDER BY q.internal_name, q.id"
		).fetchall()
	lines = []
	for identifier, name, public_name, empty in rows:
		cells = [str(name), _text(public_name), ""]
		anomaly = ""
		if empty:
			cells[2] = _("empty sequence")
			anomaly = EMPTY_SEQUENCE
		lines.append(Line(int(str(identifier)), str(name), cells, anomaly))
	return lines


def read_feeds(connection: Connection) -> list[Line]:
	"""Par nom, avec le nombre de streams qui suivent chacun (https://github.com/dascritch/machincast/issues/34)."""
	with connection.transaction():
		rows = connection.execute(
			"SELECT m.id, m.name, m.url,"
			" (SELECT count(*) FROM sounds s WHERE s.feed_id = m.id AND s.deleted_at IS NULL)"
			" FROM feeds m ORDER BY m.name, m.id"
		).fetchall()
	return [
		Line(int(str(identifier)), str(name), [str(name), str(url), str(streams)])
		for identifier, name, url, streams in rows
	]


EVENT_COLUMNS = (_("Name"), _("Public name"), _("Priority"), _("Start"), _("End"), _("Recurrence"), _("Anomaly"))
PRIORITY_POSITION = EVENT_COLUMNS.index(_("Priority"))
START_POSITION = EVENT_COLUMNS.index(_("Start"))
END_POSITION = EVENT_COLUMNS.index(_("End"))
RECURRENCE_POSITION = EVENT_COLUMNS.index(_("Recurrence"))


def _instant(value: object) -> float:
	"""Clé de tri d'une date : son instant ; sans date, après les autres."""
	if not isinstance(value, datetime):
		return AFTER_ALL
	return value.timestamp()


def _days(value: object) -> str:
	"""Clé de tri d'une récurrence : le rang de ses jours, du lundi au dimanche, « 01 » pour lundi et mardi ; sans
	jour, après les autres."""
	if (not isinstance(value, list)) or (value == []):
		return WITHOUT_DAY
	return "".join(sorted(str(DAYS.index(str(day))) for day in value))


def read_events(connection: Connection) -> list[Line]:
	"""Du plus prioritaire au moins prioritaire, puis par nom."""
	with connection.transaction():
		rows = connection.execute(
			"SELECT e.id, e.internal_name, e.public_name, e.priority::text, e.starts_at, e.ends_at,"
			" e.recurrence_days::text[],"
			" NOT EXISTS (SELECT 1 FROM event_items x WHERE x.event_id = e.id)"
			# e.priorite : l'ordre du type énuméré, pas celui du texte de la colonne affichée.
			" FROM events e WHERE e.deleted_at IS NULL ORDER BY e.priority DESC, e.internal_name, e.id"
		).fetchall()
	lines = []
	for identifier, name, public_name, priority, start, end, days, empty in rows:
		recurrence = ""
		if isinstance(days, list):
			recurrence = ", ".join(DAY_NAMES[DAYS.index(str(day))] for day in days)
		cells = [str(name), _text(public_name), PRIORITIES.get(str(priority), str(priority)), _date(start), _date(end)]
		cells += [recurrence, ""]
		anomaly = ""
		if empty:
			cells[-1] = _("empty event")
			anomaly = EMPTY_EVENT[str(priority)]
		sorts: dict[int, int | float | str] = {
			PRIORITY_POSITION: IMPORTANCE.get(str(priority), len(IMPORTANCE)),
			START_POSITION: _instant(start),
			END_POSITION: _instant(end),
			RECURRENCE_POSITION: _days(days),
		}
		lines.append(Line(int(str(identifier)), str(name), cells, anomaly, sorts))
	return lines


SOUNDS = Source(
	"sonore",
	SOUND_COLUMNS,
	read_sounds,
	lambda n: counted("{count} sound", "{count} sounds", n),
	_("sounds"),
	_("no sound"),
	_("New stream"),
	label(ADD, _("Add files…")),
	anomalies=True,
	views="sonores",
)
BANKS = Source(
	"banque",
	(_("Name"), _("Public name"), _("Mode"), _("Do not repeat"), _("Directory")),
	read_banks,
	lambda n: counted("{count} bank", "{count} banks", n),
	_("banks"),
	_("no bank"),
	_("New bank"),
	duplicable=True,
	anomalies=True,
	views="banques",
)
SEQUENCES = Source(
	"séquence",
	(_("Name"), _("Public name"), _("Anomaly")),
	read_sequences,
	lambda n: counted("{count} sequence", "{count} sequences", n),
	_("sequences"),
	_("no sequence"),
	_("New sequence"),
	duplicable=True,
	anomalies=True,
	views="séquences",
)
EVENTS = Source(
	"événement",
	EVENT_COLUMNS,
	read_events,
	lambda n: counted("{count} event", "{count} events", n),
	_("events"),
	_("no event"),
	_("New event"),
	duplicable=True,
	anomalies=True,
	views="événements",
)
FEEDS = Source(
	"feed",
	(_("Name"), _("Address"), _("Streams")),
	read_feeds,
	lambda n: counted("{count} feed", "{count} feeds", n),
	_("feeds"),
	_("no feed"),
	_("New feed"),
	views="feeds",
)


def view_name(text: str) -> str:
	"""« feeds », « evenements » : sans accents, ni majuscules, ni espaces."""
	return without_accents(text).replace(" ", "-")


def without_accents(text: str) -> str:
	"""Le texte en minuscules, sans accents ni cédilles : « Été » donne « ete »."""
	breaks_down = unicodedata.normalize("NFKD", text.casefold())
	return "".join(letter for letter in breaks_down if not unicodedata.combining(letter))


class FilterWithoutAccents(QSortFilterProxyModel):
	"""Garde les lignes dont une colonne contient le texte, sans tenir compte des majuscules ni des accents."""

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._text = ""

	def apply_filter(self, text: str) -> None:
		self.beginFilterChange()
		self._text = without_accents(text)
		self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

	def filterAcceptsRow(self, row: int, parent: QModelIndex | QPersistentModelIndex) -> bool:
		model = self.sourceModel()
		for column in range(model.columnCount()):
			value = model.index(row, column, parent).data()
			if self._text in without_accents(str((value) or (""))):
				return True
		return False


class List(QWidget):
	opened = Signal(str, int, str)
	"""Ligne ouverte : genre, identifiant et nom de l'élément."""
	requested_creation = Signal(str)
	"""Bouton de création cliqué : genre de l'élément à créer."""
	requested_addition = Signal()
	"""Bouton d'ajout de fichiers cliqué."""
	dropped_files = Signal(list)
	"""Fichiers déposés sur la liste (list[Path]) : https://github.com/dascritch/machincast/issues/30."""
	requested_duplication = Signal(str, int)
	"""« Dupliquer » choisi au clic droit sur une ligne : genre et identifiant de l'élément."""
	requested_action = Signal(str, list)
	"""Une action choisie au clic droit (machincast.interface.groups) : sa clé, et les éléments (list[int])."""
	requested_preview = Signal(int)
	"""« Pré-écoute… » choisi au clic droit sur une ligne de la liste des sonores : le sonore de cette ligne
	(https://github.com/dascritch/machincast/issues/226)."""

	def __init__(
		self,
		source: Source,
		connection: Connection,
		parent: QWidget | None = None,
		actions: bool = True,
		view: str | None = None,
	) -> None:
		"""vue : le nom sous lequel ses colonnes sont gardées ; par défaut, « liste- » suivi du pluriel du genre
		({I})."""
		"""actions : les boutons de création et d'ajout, et le dépôt de fichiers ; pas dans un choix d'éléments."""
		super().__init__(parent)
		self.source = source
		self.connection = connection
		self.ui = Ui_List()
		self.ui.setupUi(self)
		titles = list(source.columns)
		if source.anomalies:
			titles.insert(0, ANOMALY_COLUMN)
		self.model = QStandardItemModel(0, len(titles), self)
		self.model.setHorizontalHeaderLabels(titles)
		if source.anomalies:
			self.model.setHeaderData(0, Qt.Orientation.Horizontal, ANOMALY_TOOLTIP, Qt.ItemDataRole.ToolTipRole)
		self.proxy = FilterWithoutAccents(self)
		self.proxy.setSourceModel(self.model)
		self.proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
		self.proxy.setSortRole(SORT)
		self.table.setModel(self.proxy)
		header = self.table.horizontalHeader()
		if view is None:
			view = f"liste-{view_name(source.views)}"
		self.columns = Columns(self.table, view)
		# Un clic sur un titre de colonne trie la liste ; avant, elle garde l'ordre de la base.
		self.table.setSortingEnabled(True)
		header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
		self.filter_.textChanged.connect(self._apply_filter)
		self.table.activated.connect(self._open)
		self.ui.new.setText(source.new)
		self.ui.new.setVisible((actions) and (source.new != ""))
		self.ui.new.clicked.connect(lambda: self.requested_creation.emit(source.category))
		self.ui.add_files.setText(source.files)
		self.ui.add_files.setVisible((actions) and (source.files != ""))
		self.ui.add_files.clicked.connect(self.requested_addition)
		if (actions) and (source.files != ""):
			self.drop = FileDrop(self.table)
			self.drop.dropped.connect(self.dropped_files)
		self.duplicable = (actions) and (source.duplicable)
		self.grouped_actions: tuple[groups.Action, ...] = ()
		"""Les actions sur la sélection ; aucune hors des listes des sonores et des banques, ou dans un choix."""
		if actions:
			self.grouped_actions = groups.ACTIONS.get(source.category, ())
		if self.grouped_actions != ():
			self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		self.previewable = (actions) and (source.category == "sonore")
		"""La liste des sonores, hors d'un choix : le clic droit sur une ligne en propose la pré-écoute."""
		self.item_menu: Callable[[QMenu, int, str], None] | None = None
		"""Des entrées que la fenêtre ajoute au clic droit sur une ligne : le menu, l'élément et son nom. Celles
		d'un feed, sa pré-écoute et la coupure de l'antenne par lui (https://github.com/dascritch/machincast/issues/323)."""
		self.columns.line_menu = lambda position: self.line_menu(self.table.indexAt(position))
		self._count()

	@property
	def filter_(self) -> QLineEdit:
		return self.ui.filter_

	@property
	def count(self) -> QLabel:
		return self.ui.count

	@property
	def table(self) -> QTableView:
		return self.ui.table

	def refresh(self) -> None:
		"""Relit la liste en base ; une base injoignable laisse la liste telle qu'elle était."""
		try:
			lines = self.source.read(self.connection)
		except psycopg.Error as error:
			log.error(_("unreadable list of {plural}: {error}").format(plural=self.source.plural, error=error))
			return
		self.model.setRowCount(0)
		for line in lines:
			cells = [QStandardItem(text) for text in line.cells]
			for column, cell in enumerate(cells):
				cell.setData(line.sorts.get(column, cell.text()), SORT)
			if self.source.anomalies:
				marks = ""
				if line.anomaly:
					marks = ANOMALY_COLUMN
				cells.insert(0, QStandardItem(marks))
				cells[0].setData(marks, SORT)
				cells[0].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			cells[0].setData(line.identifier, IDENTIFIER)
			cells[0].setData(line.name, IDENTIFIER + 1)
			if line.anomaly:
				for cell in cells:
					cell.setToolTip(line.anomaly)
			self.model.appendRow(cells)
		self._count()

	def _apply_filter(self, text: str) -> None:
		self.proxy.apply_filter(text)
		self._count()

	def _count(self) -> None:
		total = self.model.rowCount()
		visible_list = self.proxy.rowCount()
		if self.filter_.text() != "":
			text = _("{elements} out of {total}").format(elements=self.source.counting(visible_list), total=total)
		elif total == 0:
			text = self.source.no
		else:
			text = self.source.counting(total)
		# Les lignes en anomalie parmi celles que montre le filtre.
		anomalies = sum(1 for row in range(visible_list) if self.proxy.index(row, 0).data(Qt.ItemDataRole.ToolTipRole))
		if anomalies > 0:
			text = _("{text}, of which {anomalies} in anomaly").format(text=text, anomalies=anomalies)
		self.count.setText(text)

	def selection(self) -> list[int]:
		"""Les éléments des lignes sélectionnées, dans l'ordre de la liste affichée."""
		rows = sorted(index.row() for index in self.table.selectionModel().selectedRows())
		return [self._item(self.proxy.index(row, 0)) for row in rows]

	def _item(self, index: QModelIndex) -> int:
		first = self.model.index(self.proxy.mapToSource(index).row(), 0)
		return int(first.data(IDENTIFIER))

	def line_menu(self, index: QModelIndex) -> QMenu | None:
		"""Le menu du clic droit sur cette ligne de la table : sur la sélection si elle en fait partie, sur elle seule
		sinon ; aucun hors d'une ligne, ou pour une liste sans actions. « Dupliquer » ne vaut que pour un élément.
		« Pré-écoute… », en tête, vaut pour la ligne cliquée seule, même dans une sélection."""
		without_actions = (
			(not self.duplicable)
			and (self.grouped_actions == ())
			and (not self.previewable)
			and (self.item_menu is None)
		)
		if (not index.isValid()) or (without_actions):
			return None
		clicked = self._item(index)
		items = self.selection()
		if clicked not in items:
			items = [clicked]
		menu = QMenu(self)
		if (self.duplicable) and (len(items) == 1):
			duplicate = menu.addAction(_("Duplicate"))
			duplicate.triggered.connect(lambda: self.requested_duplication.emit(self.source.category, clicked))
		for action in self.grouped_actions:
			entry = menu.addAction(action.text)
			entry.triggered.connect(lambda _ticked=False, key=action.key: self.requested_action.emit(key, items))
		if self.previewable:
			display.offer_preview(menu, clicked, self.requested_preview.emit)
		if self.item_menu is not None:
			first = self.model.index(self.proxy.mapToSource(index).row(), 0)
			self.item_menu(menu, clicked, str(first.data(IDENTIFIER + 1)))
		return menu

	def _open(self, index: QModelIndex) -> None:
		first = self.model.index(self.proxy.mapToSource(index).row(), 0)
		self.opened.emit(self.source.category, int(first.data(IDENTIFIER)), str(first.data(IDENTIFIER + 1)))
