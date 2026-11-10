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
from PySide6.QtCore import (
	QAbstractTableModel,
	QIdentityProxyModel,
	QModelIndex,
	QPersistentModelIndex,
	QSortFilterProxyModel,
	Qt,
	Signal,
)
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QLabel, QLineEdit, QMenu, QTableView, QWidget

from machincast.i18n import _, counted
from machincast.interface import display, groups, preferences
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
	paged: bool = False
	"""La liste se lit par pages, triée et filtrée par la base, la suite en descendant (PagedSounds, https://github.com/dascritch/machincast/issues/383)."""


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


SOUND_FIELDS = (
	"s.id, s.artist, s.title, s.type::text, s.state::text, s.audit_requested, s.duration,"
	" COALESCE(s.location, s.stream_url, m.url)"
)
SOUND_TABLES = "FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.deleted_at IS NULL"
SOUND_ORDER = "s.artist NULLS LAST, s.title, s.id"
"""L'ordre de la base, avant tout clic sur un titre de colonne."""


def read_sounds(connection: Connection) -> list[Line]:
	with connection.transaction():
		rows = connection.execute(f"SELECT {SOUND_FIELDS} {SOUND_TABLES} ORDER BY {SOUND_ORDER}").fetchall()  # noqa: S608
	return [sound_line(row) for row in rows]


def _state_text(state: str, requested_audit: bool) -> str:
	state_text = STATES.get(state, state)
	if requested_audit:
		# https://github.com/dascritch/machincast/issues/114
		state_text = _("{state_text}, audit requested").format(state_text=state_text)
	return state_text


def sound_line(row: tuple[object, ...]) -> Line:
	"""La ligne d'un sonore, lu par SOUND_FIELDS."""
	identifier, artist, title, sound_type, state, requested_audit, duration, location = row
	duration_text = ""
	if sound_type == "stream":
		duration_text = display.duration(None)
	else:
		if isinstance(duration, timedelta):
			duration_text = display.duration(duration)
	# Les durées d'une banque ne se signalent que dans sa fiche, et parmi les relations du sonore, jamais ici
	# (https://github.com/dascritch/machincast/issues/210).
	cells = [
		_text(artist),
		_text(title),
		TYPES.get(str(sound_type), str(sound_type)),
		_state_text(str(state), requested_audit is True),
		duration_text,
	]
	cells.append(_text(location))
	# https://github.com/dascritch/machincast/issues/302 : par les secondes ; sans durée mesurée, après les durées
	# connues ; un stream, sans fin, en dernier.
	duration_sort: float = WITHOUT_DURATION
	if sound_type == "stream":
		duration_sort = AFTER_ALL
	else:
		if isinstance(duration, timedelta):
			duration_sort = duration.total_seconds()
	sound_name = (_text(title)) or (_text(location))
	anomaly = SOUND_IN_ANOMALY.get(str(state), "")
	sorts: dict[int, int | float | str] = {DURATION_POSITION: duration_sort}
	return Line(int(str(identifier)), sound_name, cells, anomaly, sorts)


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
		else:
			if int(str(in_anomaly)) > 0:
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
			# Une liste vide qui prête son nom n'est pas une anomalie (https://github.com/dascritch/machincast/issues/399).
			" NOT EXISTS (SELECT 1 FROM event_items x WHERE x.event_id = e.id) AND e.end_of_list <> 'lend_name'"
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
	"sound",
	SOUND_COLUMNS,
	read_sounds,
	lambda n: counted("{count} sound", "{count} sounds", n),
	_("sounds"),
	_("no sound"),
	_("New stream"),
	label(ADD, _("Add files…")),
	anomalies=True,
	views="sonores",
	paged=True,
)
BANKS = Source(
	"bank",
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
	"sequence",
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
	"event",
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


def _folding() -> tuple[str, str]:
	"""Les lettres accentuées latines, et leur lettre sans accent en minuscule, comme les donne without_accents :
	pour que la base filtre comme FilterWithoutAccents (https://github.com/dascritch/machincast/issues/383)."""
	accented, plain = "", ""
	for code in range(0xC0, 0x250):
		letter = chr(code)
		folded = without_accents(letter)
		if (len(folded) == 1) and (folded.isascii()) and (folded.isalpha()) and (folded != letter):
			accented += letter
			plain += folded
	return accented, plain


ACCENTED, PLAIN = _folding()


def _fold(expression: str) -> str:
	"""L'expression SQL en minuscules, sans accents latins : à comparer à un texte passé par without_accents."""
	return f"lower(translate({expression}, %s, %s))"


SOUND_LOCATION = "COALESCE(s.location, s.stream_url, m.url)"
DURATION_SECONDS = "floor(extract(epoch FROM s.duration))::bigint"
DURATION_TEXT = (
	"CASE WHEN s.type = 'stream' THEN %s WHEN s.duration IS NULL THEN ''"
	f" WHEN {DURATION_SECONDS} >= 3600 THEN ({DURATION_SECONDS} / 3600)::text || ':'"
	f" || lpad((mod({DURATION_SECONDS}, 3600) / 60)::text, 2, '0') || ':' || lpad(mod({DURATION_SECONDS}, 60)::text, 2, '0')"
	f" ELSE ({DURATION_SECONDS} / 60)::text || ':' || lpad(mod({DURATION_SECONDS}, 60)::text, 2, '0') END"
)
"""La durée comme display.duration : « 3:34 », « 1:02:05 », « inconnue » pour un stream, rien sans durée mesurée."""


def _state_expression() -> tuple[str, list[object]]:
	"""Le texte de l'état d'un sonore, comme _state_text, en SQL, et ses paramètres."""
	parts: list[str] = []
	values: list[object] = []
	for state, text in STATES.items():
		parts.append("WHEN s.state::text = %s AND s.audit_requested THEN %s WHEN s.state::text = %s THEN %s")
		values += [state, _state_text(state, True), state, text]
	return f"CASE {' '.join(parts)} ELSE s.state::text END", values


def _type_expression() -> tuple[str, list[object]]:
	parts: list[str] = []
	values: list[object] = []
	for sound_type, text in TYPES.items():
		parts.append("WHEN s.type::text = %s THEN %s")
		values += [sound_type, text]
	return f"CASE {' '.join(parts)} ELSE s.type::text END", values


class PagedSounds(QAbstractTableModel):
	"""Les sonores de la liste, lus par pages de preferences.table_rows, triés et filtrés par la base : la vue lit la
	page suivante en arrivant au bas de la table (canFetchMore, fetchMore). Trier ou filtrer relit la première page.
	Les tris et le filtre suivent ceux de FilterWithoutAccents et du tri par SORT, sur les textes montrés
	(https://github.com/dascritch/machincast/issues/383)."""

	def __init__(self, connection: Connection, titles: list[str], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.connection = connection
		self.titles = titles
		self._lines: list[Line] = []
		self.total = 0
		"""Les sonores qui passent le filtre."""
		self.overall = 0
		"""Tous les sonores."""
		self.anomalies = 0
		"""Les sonores en anomalie qui passent le filtre."""
		self._text = ""
		self._column = -1
		self._order = Qt.SortOrder.AscendingOrder
		self._read = False

	def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:  # noqa: B008, N802
		if parent.isValid():
			return 0
		return len(self._lines)

	def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:  # noqa: B008, N802
		if parent.isValid():
			return 0
		return len(self.titles)

	def headerData(  # noqa: N802
		self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
	) -> object:
		if orientation != Qt.Orientation.Horizontal:
			return None
		if role == Qt.ItemDataRole.DisplayRole:
			return self.titles[section]
		if (role == Qt.ItemDataRole.ToolTipRole) and (section == 0):
			return ANOMALY_TOOLTIP
		return None

	def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
		if (not index.isValid()) or (index.row() >= len(self._lines)):
			return None
		line = self._lines[index.row()]
		column = index.column()
		if role == Qt.ItemDataRole.DisplayRole:
			if column == 0:
				if line.anomaly:
					return ANOMALY_COLUMN
				return ""
			return line.cells[column - 1]
		if role == Qt.ItemDataRole.ToolTipRole:
			return (line.anomaly) or (None)
		if (role == Qt.ItemDataRole.TextAlignmentRole) and (column == 0):
			return Qt.AlignmentFlag.AlignCenter
		if (role == IDENTIFIER) and (column == 0):
			return line.identifier
		if (role == IDENTIFIER + 1) and (column == 0):
			return line.name
		return None

	def canFetchMore(self, parent: QModelIndex | QPersistentModelIndex) -> bool:  # noqa: N802
		return (not parent.isValid()) and (len(self._lines) < self.total)

	def fetchMore(self, parent: QModelIndex | QPersistentModelIndex) -> None:  # noqa: N802
		if not self.canFetchMore(parent):
			return
		lines = self._page(len(self._lines))
		if lines == []:
			self.total = len(self._lines)
			return
		self.beginInsertRows(QModelIndex(), len(self._lines), len(self._lines) + len(lines) - 1)
		self._lines += lines
		self.endInsertRows()

	def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
		self._column, self._order = column, order
		if self._read:
			self.reload()

	def set_filter(self, text: str) -> None:
		self._text = without_accents(text)
		self.reload()

	def reload(self) -> None:
		"""Les comptes, et la première page ; psycopg.Error laisse la liste telle qu'elle était."""
		where, values = self._filter()
		anomaly = "s.state::text = ANY(%s)"
		with self.connection.transaction():
			counts = self.connection.execute(
				f"SELECT count(*) FILTER (WHERE {where}), count(*) FILTER (WHERE ({where}) AND {anomaly}), count(*)"  # noqa: S608
				f" {SOUND_TABLES}",
				[*values, *values, list(SOUND_IN_ANOMALY)],
			).fetchone()
			assert counts is not None
			self.total, self.anomalies, self.overall = (int(str(count)) for count in counts)
			lines = self._page(0)
		self.beginResetModel()
		self._lines = lines
		self._read = True
		self.endResetModel()

	def _page(self, offset: int) -> list[Line]:
		where, values = self._filter()
		order, order_values = self._ordering()
		rows = self.connection.execute(
			f"SELECT {SOUND_FIELDS} {SOUND_TABLES} AND ({where}) ORDER BY {order} LIMIT %s OFFSET %s",  # noqa: S608
			[*values, *order_values, preferences.table_rows(), offset],
		).fetchall()
		return [sound_line(row) for row in rows]

	def _filter(self) -> tuple[str, list[object]]:
		"""La condition du filtre, sur chaque colonne montrée, et ses paramètres ; vraie sans filtre."""
		if self._text == "":
			return "true", []
		text = self._text
		escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
		pattern = f"%{escaped}%"
		parts: list[str] = []
		values: list[object] = []
		for expression in ("COALESCE(s.artist, '')", "COALESCE(s.title, '')", f"COALESCE({SOUND_LOCATION}, '')"):
			parts.append(f"{_fold(expression)} LIKE %s ESCAPE '\\'")
			values += [ACCENTED, PLAIN, pattern]
		parts.append(f"{_fold(DURATION_TEXT)} LIKE %s ESCAPE '\\'")
		values += [display.duration(None), ACCENTED, PLAIN, pattern]
		types = [sound_type for sound_type, label_ in TYPES.items() if text in without_accents(label_)]
		plain = [state for state in STATES if text in without_accents(_state_text(state, False))]
		audited = [state for state in STATES if text in without_accents(_state_text(state, True))]
		parts += [
			"s.type::text = ANY(%s)",
			"s.state::text = ANY(%s)",
			"(s.audit_requested AND s.state::text = ANY(%s))",
		]
		values += [types, plain, audited]
		if text in without_accents(ANOMALY_COLUMN):
			parts.append("s.state::text = ANY(%s)")
			values.append(list(SOUND_IN_ANOMALY))
		return " OR ".join(f"({part})" for part in parts), values

	def _ordering(self) -> tuple[str, list[object]]:
		"""L'ordre de la colonne choisie, comme le tri de la table par SORT, puis l'ordre de la base ; celui de la
		base seul sans colonne choisie."""
		direction = "ASC"
		if self._order == Qt.SortOrder.DescendingOrder:
			direction = "DESC"
		column = self._column
		keys: list[str] = []
		values: list[object] = []
		match column:
			case 0:
				keys = [f"(s.state::text = ANY(%s)) {direction}"]
				values = [list(SOUND_IN_ANOMALY)]
			case _ if column in (1, 2, len(self.titles) - 1):
				expression = {1: "s.artist", 2: "s.title"}.get(column, SOUND_LOCATION)
				keys = [f"lower(COALESCE({expression}, '')) COLLATE \"C\" {direction}"]
			case 3:
				expression, values = _type_expression()
				keys = [f'lower({expression}) COLLATE "C" {direction}']
			case 4:
				expression, values = _state_expression()
				keys = [f'lower({expression}) COLLATE "C" {direction}']
			case 5:
				rank = "CASE WHEN s.type = 'stream' THEN 2 WHEN s.duration IS NULL THEN 1 ELSE 0 END"
				keys = [f"{rank} {direction}", f"s.duration {direction}"]
		return ", ".join([*keys, SOUND_ORDER]), values


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
		self.model: QStandardItemModel | PagedSounds
		self.proxy: FilterWithoutAccents | QIdentityProxyModel
		self.paged: PagedSounds | None = None
		if source.paged:
			# Triée et filtrée par la base, par pages (https://github.com/dascritch/machincast/issues/383) : la vue
			# passe le tri à PagedSounds à travers le proxy, et lui demande la page suivante en descendant.
			self.paged = PagedSounds(connection, titles, self)
			self.model = self.paged
			self.proxy = QIdentityProxyModel(self)
			self.proxy.setSourceModel(self.model)
		else:
			standard = QStandardItemModel(0, len(titles), self)
			standard.setHorizontalHeaderLabels(titles)
			if source.anomalies:
				standard.setHeaderData(0, Qt.Orientation.Horizontal, ANOMALY_TOOLTIP, Qt.ItemDataRole.ToolTipRole)
			self.model = standard
			filtering = FilterWithoutAccents(self)
			filtering.setSourceModel(standard)
			filtering.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
			filtering.setSortRole(SORT)
			self.proxy = filtering
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
		self.previewable = (actions) and (source.category == "sound")
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
			if self.paged is not None:
				self.paged.reload()
				self._count()
				return
			lines = self.source.read(self.connection)
		except psycopg.Error as error:
			log.error(_("unreadable list of {plural}: {error}").format(plural=self.source.plural, error=error))
			return
		assert isinstance(self.model, QStandardItemModel)
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
		if isinstance(self.proxy, FilterWithoutAccents):
			self.proxy.apply_filter(text)
		else:
			if self.paged is not None:
				try:
					self.paged.set_filter(text)
				except psycopg.Error as error:
					log.error(_("unreadable list of {plural}: {error}").format(plural=self.source.plural, error=error))
		self._count()

	def _count(self) -> None:
		if self.paged is not None:
			self._show_count(self.paged.overall, self.paged.total, self.paged.anomalies)
			return
		total = self.model.rowCount()
		visible_list = self.proxy.rowCount()
		# Les lignes en anomalie parmi celles que montre le filtre.
		anomalies = sum(1 for row in range(visible_list) if self.proxy.index(row, 0).data(Qt.ItemDataRole.ToolTipRole))
		self._show_count(total, visible_list, anomalies)

	def _show_count(self, total: int, visible_list: int, anomalies: int) -> None:
		if self.filter_.text() != "":
			text = _("{elements} out of {total}").format(elements=self.source.counting(visible_list), total=total)
		else:
			if total == 0:
				text = self.source.no
			else:
				text = self.source.counting(total)
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
