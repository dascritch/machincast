"""Liste ordonnée des éléments d'une séquence ou d'un événement (https://github.com/dascritch/machincast/issues/112,
https://github.com/dascritch/machincast/issues/32).

Commune aux fiches d'une séquence (machincast.interface.sequence_card) et d'un événement
(machincast.interface.event_card) :

- les éléments sont des sonores et des banques, et des séquences dans un événement ; un même élément peut revenir.
  Chaque ligne montre son genre, son nom (artiste et titre d'un sonore, le nom du fichier d'un sonore pas encore
  décodé, le nom interne d'une banque ou d'une séquence) et un détail ;
- ils se réordonnent par glisser-déposer, ou par « Monter » et « Descendre » ; une ligne ne se dépose pas dans une
  autre. Ils s'ajoutent parmi ceux déjà en base (machincast.interface.choice), ou par dépôt de fichiers sonores
  (machincast.interface.drop), toujours comme une copie ; un fichier pas encore en base devient un sonore à l'état
  aperçu à l'enregistrement seulement. Dans un événement, un feed choisi ajoute le premier stream, par titre, qui
  le suit ; sans stream qui le suive, un stream actif, titré du nom du feed, est créé à l'enregistrement, un
  seul par feed (https://github.com/dascritch/machincast/issues/167) ;
- une banque « ne pas répéter » appelée juste après elle-même est signalée : cet appel sera sauté à la diffusion
  (machincast.player.rundown.ignored_calls_to_edges). Une séquence compte par la première et la dernière de ses
  lignes, quand ce sont des banques ;
- à l'enregistrement, une ligne restée dans la liste garde son identifiant en base, à sa nouvelle position :
  l'historique de diffusion la désigne pour reprendre la liste. Un élément effacé de la base entre-temps est oublié.
"""

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QGroupBox, QMenu, QPushButton, QTreeWidget, QTreeWidgetItem

from machincast.conversion import integer_or_none, text_or_none
from machincast.i18n import _, counted
from machincast.interface import dialogs, display, preferences
from machincast.interface.card import Card, sound_files
from machincast.interface.columns import Columns
from machincast.interface.drop import FileDrop
from machincast.interface.lists import MODES
from machincast.player.rundown import ignored_calls_to_edges

CATEGORY = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la première colonne d'une ligne, le genre de l'élément : « sonore », « banque », « séquence »."""
ITEM = Qt.ItemDataRole.UserRole + 1
"""Rôle qui porte l'identifiant de l'élément ; None pour un fichier déposé, pas encore en base."""
FILE = Qt.ItemDataRole.UserRole + 2
"""Rôle qui porte le chemin d'un fichier déposé, pas encore en base."""
LINE_IN_DATABASE = Qt.ItemDataRole.UserRole + 3
"""Rôle qui porte l'identifiant de la ligne en base ; None pour une ligne ajoutée."""
ENTRY = Qt.ItemDataRole.UserRole + 4
"""Rôle qui porte la banque par laquelle commence une ligne : la banque elle-même, la première ligne d'une séquence
si c'est une banque ; None sinon."""
OUTPUT = Qt.ItemDataRole.UserRole + 5
"""Rôle qui porte la banque par laquelle finit une ligne, comme ENTREE."""
FEED = Qt.ItemDataRole.UserRole + 6
"""Rôle qui porte le feed d'un stream à créer à l'enregistrement, faute de stream qui le suive."""
LINE = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled
"""Une ligne se glisse, mais rien ne se dépose dedans : la liste reste à plat."""

COLUMNS = {"sound": "sound_id", "bank": "bank_id", "sequence": "sequence_id"}
"""Colonne de chaque genre d'élément, dans sequence_items et event_items."""
TABLES = {"sound": "sounds", "bank": "banks", "sequence": "sequences"}
PLAYS = {
	"sound": (
		"SELECT s.id, s.artist, s.title, s.location, COALESCE(s.location, s.stream_url, m.url)"
		" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = ANY(%s)"
	),
	"bank": "SELECT b.id, b.internal_name, b.mode::text, b.no_repeat FROM banks b WHERE b.id = ANY(%s)",
	"sequence": (
		"SELECT q.id, q.internal_name, (SELECT count(*) FROM sequence_items e WHERE e.sequence_id = q.id),"
		" (SELECT e.bank_id FROM sequence_items e WHERE e.sequence_id = q.id ORDER BY e.position LIMIT 1),"
		" (SELECT e.bank_id FROM sequence_items e WHERE e.sequence_id = q.id ORDER BY e.position DESC LIMIT 1)"
		" FROM sequences q WHERE q.id = ANY(%s)"
	),
}
"""Ce que montre la ligne d'un élément, lu par identifiants."""
SOUNDS_PER_FILE = PLAYS["sound"].replace("s.id = ANY(%s)", "s.location = ANY(%s)")
FEED_STREAM = "SELECT id FROM sounds WHERE feed_id = %s AND deleted_at IS NULL ORDER BY title, id LIMIT 1"
PARTIAL_ITEMS = _("Items: {shown} shown out of {total}, the rest is loaded as you scroll down")
"""Le titre de la liste tant que tous ses éléments ne sont pas lus (https://github.com/dascritch/machincast/issues/383)."""
"""Le stream repris pour un feed : le premier par titre qui le suit."""
SKIPPED = _("never plays twice in a row: this call will be skipped.")


@dataclass(frozen=True)
class Buttons:
	"""Les boutons qui agissent sur la liste : un bouton d'ajout par genre, et ceux de la ligne choisie."""

	add: dict[str, QPushButton]
	remove: QPushButton
	raise_: QPushButton
	go_down: QPushButton


VIEWS = {"sequence_items": "fiche-sequence-elements", "event_items": "fiche-evenement-elements"}
"""Le nom de la vue des éléments, selon la table de la fiche (https://github.com/dascritch/machincast/issues/207)."""


class ItemList(QObject):
	changed = Signal()
	"""Une ligne a été ajoutée, retirée ou déplacée par l'utilisateur : le glisser-déposer déplace en retirant, puis en
	insérant. Pas les lignes que la liste lit en base."""
	loaded = Signal()
	"""La liste a lu des lignes en base : toutes à l'ouverture, ou la page suivante (https://github.com/dascritch/machincast/issues/383)."""

	def __init__(
		self,
		card: Card,
		list_: QTreeWidget,
		buttons: Buttons,
		table: str,
		column_parent: str,
		remark: str,
		group: QGroupBox | None = None,
	) -> None:
		"""table et column_parent : la table des éléments, et sa colonne qui désigne la séquence ou l'événement.
		remarque : celle des choix d'éléments, qu'un élément peut revenir. group : le cadre de la liste, dont le titre
		dit combien d'éléments sont montrés, tant que tous ne le sont pas (https://github.com/dascritch/machincast/issues/383)."""
		super().__init__(card)
		self.group = group
		self._title = ""
		if group is not None:
			self._title = group.title()
		self._parent: int | None = None
		self._after: int | None = None
		"""La position du dernier élément lu, quand il y en a d'autres après ; None : tous sont lus (https://github.com/dascritch/machincast/issues/383)."""
		self._tail = 0
		"""Le nombre d'éléments pas encore lus."""
		self.tail_stream = False
		"""Un stream parmi les éléments pas encore lus."""
		self._paging = False
		"""Pendant la lecture de lignes en base, elles ne modifient pas la liste."""
		self.modified = False
		"""L'utilisateur a changé la liste depuis sa lecture : sans changement, l'enregistrement ne la réécrit pas."""
		self._copies = False
		self.card = card
		self.list_ = list_
		self.buttons = buttons
		self.table = table
		self.column_parent = column_parent
		self.remark = remark
		self.marked_list: dict[int, str] = {}
		"""Banques « ne pas répéter », par identifiant, avec leur nom."""
		self.columns = Columns(list_, VIEWS[table])
		self.columns.before_export = self.load_all
		list_.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
		self.drop = FileDrop(list_)
		self.drop.dropped.connect(self._drop_in)
		model = list_.model()
		for signal in (model.rowsInserted, model.rowsRemoved):
			signal.connect(self._lines_changed)
		list_.verticalScrollBar().valueChanged.connect(self._scrolled)
		list_.currentItemChanged.connect(self._refresh_buttons)
		list_.itemActivated.connect(self._open)
		self.columns.line_menu = lambda position: self.line_menu(self.list_.itemAt(position))
		for category, button in buttons.add.items():
			button.clicked.connect(lambda _ticked=False, category=category: self._add(category))
		buttons.remove.clicked.connect(self._remove)
		buttons.raise_.clicked.connect(lambda: self._move(-1))
		buttons.go_down.clicked.connect(lambda: self._move(1))

	def load(self, parent: int | None, copies: bool = False) -> None:
		"""Lit en base les éléments de la séquence ou de l'événement, dans l'ordre, par pages de
		preferences.table_rows ; aucun pour un nouveau (https://github.com/dascritch/machincast/issues/383). Une copie
		(https://github.com/dascritch/machincast/issues/130) les lit tous, comme des lignes ajoutées : l'enregistrement
		les crée pour elle, et laisse celles de l'original. À appeler dans une transaction."""
		self._read_marked()
		self._parent = parent
		self._copies = copies
		self._after = None
		rows: int | None = None
		if not copies:
			rows = preferences.table_rows()
		lines = self._page(0, rows)
		self._paging = True
		try:
			self.list_.clear()
			self.list_.addTopLevelItems(lines)
		finally:
			self._paging = False
		self.modified = False
		self._show_count()
		self._refresh_buttons()
		self.loaded.emit()

	def _page(self, after: int, rows: int | None) -> list[QTreeWidgetItem]:
		"""Les lignes des éléments qui suivent la position, au plus rows ; note la position du dernier, s'il en reste
		après, leur nombre, et s'il y a un stream parmi eux. À appeler dans une transaction."""
		self._after = None
		self._tail = 0
		self.tail_stream = False
		if self._parent is None:
			return []
		column_list = []
		for column in self._columns().values():
			column_list.append(f"e.{column}")
		columns = ", ".join(column_list)
		if rows is None:
			chosen = None
		else:
			chosen = rows + 1
		rows_read = self.card.connection.execute(
			f"SELECT e.id, e.position, {columns} FROM {self.table} e"  # noqa: S608
			f" WHERE e.{self.column_parent} = %s AND e.position > %s ORDER BY e.position LIMIT %s",
			(self._parent, after, chosen),
		).fetchall()
		if (rows is not None) and (len(rows_read) > rows):
			rows_read = rows_read[:rows]
			self._after = int(str(rows_read[-1][1]))
			tail = self.card.connection.execute(
				f"SELECT count(*), COALESCE(bool_or(s.type = 'stream'), false) FROM {self.table} e"  # noqa: S608
				f" LEFT JOIN sounds s ON s.id = e.sound_id WHERE e.{self.column_parent} = %s AND e.position > %s",
				(self._parent, self._after),
			).fetchone()
			assert tail is not None
			self._tail = int(str(tail[0]))
			self.tail_stream = bool(tail[1])
		categories = list(self._columns())
		items = []
		for line_in_database, _position, *identifiers in rows_read:
			g_list = []
			for g, i in zip(categories, identifiers, strict=True):
				if i is not None:
					g_list.append((g, i))
			((category, identifier),) = g_list
			items.append((int(str(line_in_database)), category, int(str(identifier))))
		fetched_list = self._read({category: [i for _l, g, i in items if g == category] for category in categories})
		lines = []
		for line_in_database, category, identifier in items:
			# Un même élément peut revenir : chaque ligne a son exemplaire.
			line = fetched_list[category][identifier].clone()
			if not self._copies:
				line.setData(0, LINE_IN_DATABASE, line_in_database)
			lines.append(line)
		return lines

	def load_more(self, rows: int | None = None) -> None:
		"""La page suivante des éléments, ou tous ceux qui restent avec rows None, sans modifier la liste."""
		if self._after is None:
			return
		with self.card.connection.transaction():
			lines = self._page(self._after, rows)
		self._paging = True
		try:
			self.list_.addTopLevelItems(lines)
		finally:
			self._paging = False
		self._show_count()
		self._refresh_buttons()
		self.loaded.emit()

	def load_all(self) -> None:
		"""Tous les éléments qui restent : avant un ajout, qui va en fin de liste, et avant d'enregistrer une liste
		modifiée."""
		self.load_more(None)

	def complete(self) -> bool:
		"""Tous les éléments sont lus."""
		return self._after is None

	def _scrolled(self, value: int) -> None:
		"""La page suivante, quand la liste arrive à sa dernière page visible."""
		bar = self.list_.verticalScrollBar()
		if (self._after is not None) and (value >= bar.maximum() - bar.pageStep()):
			self.load_more(preferences.table_rows())

	def _lines_changed(self) -> None:
		if self._paging:
			return
		self.modified = True
		self.changed.emit()

	def _show_count(self) -> None:
		if self.group is None:
			return
		title = self._title
		if self._after is not None:
			shown = self.list_.topLevelItemCount()
			title = PARTIAL_ITEMS.format(shown=shown, total=shown + self._tail)
		self.group.setTitle(title)

	def lines(self) -> list[QTreeWidgetItem]:
		lines = []
		for row in range(self.list_.topLevelItemCount()):
			lines.append(self.list_.topLevelItem(row))
		line_list = []
		for line in lines:
			if line is not None:
				line_list.append(line)
		return line_list

	def warnings(self, loop: bool) -> list[str]:
		"""Une ligne par appel d'une banque « ne pas répéter » juste après elle-même ; pour une liste qui boucle, la
		première ligne suit la dernière. Tant que tous les éléments ne sont pas lus, seulement parmi ceux qui le sont, et
		sans boucler (https://github.com/dascritch/machincast/issues/383)."""
		loop = (loop) and (self._after is None)
		lines = self.lines()
		edges = [(line.data(0, ENTRY), line.data(0, OUTPUT)) for line in lines]
		texts = []
		for number in ignored_calls_to_edges(edges, self.marked_list, loop):
			line = lines[number - 1]
			bank = self.marked_list[edges[number - 1][0]]
			text = _("Line {number}: the bank “{bank}” has just played, and {skipped}").format(
				number=number, bank=bank, skipped=SKIPPED
			)
			if line.data(0, CATEGORY) == "sequence":
				text = _(
					"Line {number}: the sequence “{text}” starts with the bank “{bank}”, which has just "
					"played, and {skipped}"
				).format(number=number, text=line.text(1), bank=bank, skipped=SKIPPED)
			texts.append(text)
		return texts

	def write(self, parent: int) -> None:
		"""Dans la transaction d'« Enregistrer » : les lignes restées dans la liste gardent leur identifiant, à leur
		nouvelle position ; les autres sont retirées ou ajoutées. L'unicité des positions n'est vérifiée qu'en fin de
		transaction. Une liste que l'utilisateur n'a pas changée n'est pas réécrite ; une liste changée lit d'abord ses
		éléments qui ne le sont pas encore, qui restent à sa suite (https://github.com/dascritch/machincast/issues/383)."""
		if (not self.modified) and (not self._copies) and (parent == self._parent):
			return
		self.load_all()
		connection = self.card.connection
		items: list[tuple[int | None, str, int]] = []
		"""Ligne en base, genre et identifiant de l'élément."""
		for item in self.lines():
			identifier = item.data(0, ITEM)
			if item.data(0, FEED) is not None:
				identifier = self._save_stream(int(item.data(0, FEED)), item.text(1))
			else:
				if identifier is None:
					identifier = self.card.save_file(str(item.data(0, FILE)))
			if identifier is not None:
				items.append((item.data(0, LINE_IN_DATABASE), str(item.data(0, CATEGORY)), int(identifier)))
		existing_list: set[tuple[str, int]] = set()
		for category in self._columns():
			requests = []
			for _line, g, item_id in items:
				if g == category:
					requests.append(item_id)
			fetched_list = connection.execute(f"SELECT id FROM {TABLES[category]} WHERE id = ANY(%s)", (requests,))  # noqa: S608
			existing_list |= {(category, int(str(identifier))) for (identifier,) in fetched_list}
		kept_list = []
		for line, category, item_id in items:
			if (category, item_id) in existing_list:
				kept_list.append((line, category, item_id))
		in_database = []
		for line, _category, _item in kept_list:
			if line is not None:
				in_database.append(line)
		connection.execute(
			f"DELETE FROM {self.table} WHERE {self.column_parent} = %s AND NOT (id = ANY(%s))",  # noqa: S608
			(parent, in_database),
		)
		# Une requête pour les lignes gardées, une par genre pour les nouvelles, quel que soit leur nombre (https://github.com/dascritch/machincast/issues/383).
		kept = []
		for position, (line, _g, _i) in enumerate(kept_list, start=1):
			if line is not None:
				kept.append((line, position))
		# Une ligne n'est jamais reprise d'une autre séquence ou d'un autre événement.
		p_list_2 = []
		for line, _p in kept:
			p_list_2.append(line)
		l_list = []
		for _l, position in kept:
			l_list.append(position)
		connection.execute(
			f"UPDATE {self.table} e SET position = v.position FROM unnest(%s::bigint[], %s::int[])"  # noqa: S608
			f" AS v(id, position) WHERE e.id = v.id AND e.{self.column_parent} = %s",
			(p_list_2, l_list, parent),
		)
		for category, column in COLUMNS.items():
			new = []
			for position, (line, g, item_id) in enumerate(kept_list, start=1):
				if (line is None) and (g == category):
					new.append((position, item_id))
			if new == []:
				continue
			i_list = []
			for position, _i in new:
				i_list.append(position)
			p_list = []
			for _p, item_id in new:
				p_list.append(item_id)
			connection.execute(
				f"INSERT INTO {self.table} ({self.column_parent}, position, {column})"  # noqa: S608
				" SELECT %s, v.position, v.item FROM unnest(%s::int[], %s::bigint[]) AS v(position, item)",
				(parent, i_list, p_list),
			)

	def _save_stream(self, feed: int, name: str) -> int | None:
		"""Dans la transaction d'« Enregistrer » : le stream qui suit le feed, créé s'il n'y en a pas, actif et
		titré du nom du feed ; un second ajout du même feed le reprend. None pour un feed effacé
		de la base entre-temps : la ligne est oubliée."""
		connection = self.card.connection
		if connection.execute("SELECT 1 FROM feeds WHERE id = %s", (feed,)).fetchone() is None:
			return None
		line = connection.execute(FEED_STREAM, (feed,)).fetchone()
		if line is None:
			line = connection.execute(
				"INSERT INTO sounds (type, feed_id, title, state) VALUES ('stream', %s, %s, 'active') RETURNING id",
				(feed, name),
			).fetchone()
			assert line is not None
		return int(str(line[0]))

	def _columns(self) -> dict[str, str]:
		"""Les genres d'éléments de la liste, et leur colonne : jamais une séquence dans une séquence."""
		columns = {}
		for category, column in COLUMNS.items():
			if column != self.column_parent:
				columns[category] = column
		return columns

	def _read_marked(self) -> None:
		fetched_list = self.card.connection.execute("SELECT id, internal_name FROM banks WHERE no_repeat").fetchall()
		identifier_dict = {}
		for identifier, name in fetched_list:
			identifier_dict[int(str(identifier))] = str(name)
		self.marked_list = identifier_dict

	def _read(self, identifiers: dict[str, list[int]]) -> dict[str, dict[int, QTreeWidgetItem]]:
		"""Les lignes des éléments, par genre et par identifiant ; un élément absent de la base n'en a pas."""
		build = {"sound": self._sound_line, "bank": self._bank_line, "sequence": self._sequence_line}
		lines: dict[str, dict[int, QTreeWidgetItem]] = {}
		for category, requests in identifiers.items():
			fetched_list = self.card.connection.execute(PLAYS[category], (requests,)).fetchall()
			lu_dict = {}
			for lu in fetched_list:
				lu_dict[int(str(lu[0]))] = build[category](lu)
			lines[category] = lu_dict
		return lines

	def _bank_line(self, bank: tuple[object, ...]) -> QTreeWidgetItem:
		identifier, name, mode, marked = bank
		detail = MODES.get(str(mode), str(mode))
		if marked:
			detail = _("{detail}, do not repeat").format(detail=detail)
		line = self._line("bank", [str(name), detail], (integer_or_none(identifier), integer_or_none(identifier)))
		line.setData(0, ITEM, int(str(identifier)))
		return line

	def _sequence_line(self, sequence: tuple[object, ...]) -> QTreeWidgetItem:
		identifier, name, count, first, last = sequence
		detail = counted("{count} element", "{count} elements", int(str(count)))
		line = self._line("sequence", [str(name), detail], (integer_or_none(first), integer_or_none(last)))
		line.setData(0, ITEM, int(str(identifier)))
		return line

	def _sound_line(self, sound: tuple[object, ...]) -> QTreeWidgetItem:
		"""Une ligne de sonore ; un fichier déposé, pas encore en base, n'a pas d'identifiant."""
		identifier, artist, title, file, location = sound
		text = display.artist_and_title(text_or_none(artist), text_or_none(title))
		if (artist is None) and (title is None) and (file is not None):
			# Pas encore décodé : le nom du fichier en attendant ses tags.
			text = Path(str(file)).name
		line = self._line("sound", [text, str((location) or (""))], (None, None))
		if identifier is not None:
			line.setData(0, ITEM, int(str(identifier)))
		else:
			line.setData(0, FILE, str(file))
		return line

	def _line(self, category: str, cells: list[str], edges: tuple[int | None, int | None]) -> QTreeWidgetItem:
		line = QTreeWidgetItem([display.CATEGORIES.get(category, category), *cells])
		line.setData(0, CATEGORY, category)
		line.setData(0, ITEM, None)
		line.setData(0, ENTRY, edges[0])
		line.setData(0, OUTPUT, edges[1])
		line.setFlags(LINE)
		return line

	def _refresh_buttons(self) -> None:
		"""Les boutons d'une ligne ne servent qu'à une ligne choisie ; « Monter » et « Descendre », pas aux
		extrémités."""
		line = self.list_.currentItem()
		self.buttons.remove.setEnabled(line is not None)
		row = -1
		if line is not None:
			row = self.list_.indexOfTopLevelItem(line)
		self.buttons.raise_.setEnabled(row > 0)
		self.buttons.go_down.setEnabled(0 <= row < self.list_.topLevelItemCount() - 1)

	def _add(self, category: str) -> None:
		"""Les éléments choisis s'ajoutent en fin de liste, dans l'ordre du choix ; un élément effacé de la base
		pendant le choix est oublié."""
		if category == "feed":
			self._add_feeds()
			return
		choose = {
			"sound": dialogs.choose_sounds,
			"bank": dialogs.choose_banks,
			"sequence": dialogs.choose_sequences,
		}[category]
		chosen_list = choose(self.card, self.card.connection, self.remark)
		self.load_all()
		with self.card.connection.transaction():
			self._read_marked()
			fetched_list = self._read({category: chosen_list})[category]
		chosen_list_2 = []
		for chosen in chosen_list:
			if chosen in fetched_list:
				chosen_list_2.append(fetched_list[chosen])
		self.list_.addTopLevelItems(chosen_list_2)
		self._refresh_buttons()

	def _add_feeds(self) -> None:
		"""Pour chaque feed choisi, le stream qui le suit ; sans stream, une ligne qui en créera un à
		l'enregistrement (https://github.com/dascritch/machincast/issues/167)."""
		chosen_list = dialogs.choose_feeds(self.card, self.card.connection, self.remark)
		self.load_all()
		connection = self.card.connection
		lines: list[QTreeWidgetItem] = []
		with connection.transaction():
			for feed in chosen_list:
				marks = connection.execute("SELECT name, url FROM feeds WHERE id = %s", (feed,)).fetchone()
				if marks is None:
					continue
				stream = connection.execute(FEED_STREAM, (feed,)).fetchone()
				if stream is not None:
					lines += self._read({"sound": [int(str(stream[0]))]})["sound"].values()
					continue
				name, url = marks
				line = self._line("sound", [str(name), _("{url}, new stream").format(url=url)], (None, None))
				line.setData(0, FEED, feed)
				lines.append(line)
		self.list_.addTopLevelItems(lines)
		self._refresh_buttons()

	def _drop_in(self, paths: list[Path]) -> None:
		"""Les fichiers sonores déposés s'ajoutent en fin de liste. Un fichier pas encore en base est montré par son
		nom, et deviendra un sonore à l'état aperçu à l'enregistrement."""
		files, ignored = sound_files(paths)
		self.load_all()
		with self.card.connection.transaction():
			fetched_list = self.card.connection.execute(SOUNDS_PER_FILE, (files,)).fetchall()
		by_file = {}
		for sound in fetched_list:
			by_file[str(sound[3])] = sound
		lines = []
		for file in files:
			lines.append(self._sound_line(by_file.get(file, (None, None, None, file, file))))
		self.list_.addTopLevelItems(lines)
		self._refresh_buttons()
		self.card.flag_ignored(ignored, _("these are not sound files"))

	def _remove(self) -> None:
		self.list_.takeTopLevelItem(self.list_.indexOfTopLevelItem(self.list_.currentItem()))

	def _move(self, offset: int) -> None:
		line = self.list_.currentItem()
		row = self.list_.indexOfTopLevelItem(line)
		self.list_.takeTopLevelItem(row)
		self.list_.insertTopLevelItem(row + offset, line)
		# Rendue courante, la ligne déplacée met à jour les boutons (currentItemChanged).
		self.list_.setCurrentItem(line)

	def line_menu(self, line: QTreeWidgetItem | None) -> QMenu | None:
		"""Le menu du clic droit sur une ligne : « Pré-écoute… » d'un sonore en base ; aucun pour une banque, une
		séquence, un fichier déposé pas encore enregistré, ou hors d'une ligne (https://github.com/dascritch/machincast/issues/226)."""
		if (line is None) or (line.data(0, CATEGORY) != "sound") or (line.data(0, ITEM) is None):
			return None
		menu = QMenu(self.list_)
		display.offer_preview(menu, int(line.data(0, ITEM)), self.card.requested_preview.emit)
		return menu

	def _open(self, line: QTreeWidgetItem) -> None:
		"""Ouvrir un élément demande sa fiche ; un fichier déposé n'en a pas avant l'enregistrement."""
		identifier = line.data(0, ITEM)
		if identifier is not None:
			self.card.requested_opening.emit(str(line.data(0, CATEGORY)), int(identifier), line.text(1))
