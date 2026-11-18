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
  (machincast.shared.no_repeat.ignored_calls_to_edges). Une séquence compte par la première et la dernière de ses
  lignes, quand ce sont des banques ;
- à l'enregistrement, une ligne restée dans la liste garde son identifiant en base, à sa nouvelle position :
  l'historique de diffusion la désigne pour reprendre la liste. Un élément effacé de la base entre-temps est oublié ;
- plusieurs lignes se choisissent à la fois (Ctrl, Maj) ; Ctrl+C, ou « Copier » au clic droit, les copie dans le
  presse-papiers, dans leur ordre, et en texte, une ligne par élément ; Ctrl+V, ou « Coller », les ajoute après la
  ligne courante, ou en fin de liste, dans cette fiche ou dans une autre, d'un événement ou d'une séquence, ou
  dans une banque (machincast.interface.clipboard, machincast.interface.bank_card). Une
  séquence collée dans une séquence est laissée de côté, comme un événement copié depuis la recherche
  (machincast.interface.search), et la fiche le dit ; un élément effacé de la base depuis la
  copie n'est pas collé (https://github.com/dascritch/machincast/issues/129).
"""

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, QObject, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QGroupBox, QMenu, QPushButton, QTreeWidget, QTreeWidgetItem

from machincast.conversion import integer_or_none, text_or_none
from machincast.i18n import _, counted
from machincast.interface import clipboard, dialogs, display, preferences
from machincast.interface.card import Card, sound_files
from machincast.interface.columns import Columns
from machincast.interface.drop import FileDrop
from machincast.interface.lists import MODES
from machincast.interface.queries import items as queries
from machincast.shared.no_repeat import ignored_calls_to_edges

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
SET_ASIDE = _("Set aside, a sequence does not contain a sequence: {list}.")
EVENTS_ASIDE = _("Set aside, an event is not an item of a playlist: {list}.")
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
		list_.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		clipboard.shortcuts(list_, self.copy, self.paste)
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

	def load(self, parent: int | None, *, copies: bool = False) -> None:
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
			limit = None
		else:
			limit = rows + 1
		rows_read = queries.page(
			self.card.connection, self.table, self.column_parent, columns, self._parent, after, limit
		)
		if (rows is not None) and (len(rows_read) > rows):
			rows_read = rows_read[:rows]
			self._after = int(str(rows_read[-1][1]))
			self._tail, self.tail_stream = queries.tail(
				self.card.connection, self.table, self.column_parent, self._parent, self._after
			)
		categories = list(self._columns())
		items = []
		for line_in_database, _position, *identifiers in rows_read:
			given = []
			for g, i in zip(categories, identifiers, strict=True):
				if i is not None:
					given.append((g, i))
			((category, identifier),) = given
			items.append((int(str(line_in_database)), category, int(str(identifier))))
		category_dict = {}
		for wanted_category in categories:
			wanted_identifiers = []
			for _l, g, i in items:
				if g == wanted_category:
					wanted_identifiers.append(i)
			category_dict[wanted_category] = wanted_identifiers
		fetched_list = self._read(category_dict)
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

	def warnings(self, *, loop: bool) -> list[str]:
		"""Une ligne par appel d'une banque « ne pas répéter » juste après elle-même ; pour une liste qui boucle, la
		première ligne suit la dernière. Tant que tous les éléments ne sont pas lus, seulement parmi ceux qui le sont, et
		sans boucler (https://github.com/dascritch/machincast/issues/383)."""
		loop = (loop) and (self._after is None)
		lines = self.lines()
		edges = []
		for edge_line in lines:
			edges.append((edge_line.data(0, ENTRY), edge_line.data(0, OUTPUT)))
		texts = []
		for number in ignored_calls_to_edges(edges, self.marked_list, loop=loop):
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
			for _line, item_category, item_id in items:
				if item_category == category:
					requests.append(item_id)
			for identifier in queries.existing(connection, category, requests):
				existing_list.add((category, identifier))
		kept_list = []
		for line, category, item_id in items:
			if (category, item_id) in existing_list:
				kept_list.append((line, category, item_id))
		# Une requête pour les lignes gardées, une par genre pour les nouvelles, quel que soit leur nombre
		# (https://github.com/dascritch/machincast/issues/383).
		kept_lines = []
		kept_positions = []
		for position, (line, _category, _item) in enumerate(kept_list, start=1):
			if line is not None:
				kept_lines.append(line)
				kept_positions.append(position)
		queries.delete_others(connection, self.table, self.column_parent, parent, kept_lines)
		queries.renumber(connection, self.table, self.column_parent, parent, kept_lines, kept_positions)
		for category, column in COLUMNS.items():
			self._insert_new(parent, kept_list, category, column)

	def _insert_new(
		self, parent: int, kept_list: list[tuple[int | None, str, int]], category: str, column: str
	) -> None:
		"""Les nouvelles lignes d'un genre, en une requête ; aucune s'il n'y en a pas."""
		new_positions = []
		new_items = []
		for position, (line, line_category, item_id) in enumerate(kept_list, start=1):
			if (line is None) and (line_category == category):
				new_positions.append(position)
				new_items.append(item_id)
		if new_positions == []:
			return
		queries.insert_new(
			self.card.connection, self.table, self.column_parent, column, parent, new_positions, new_items
		)

	def _save_stream(self, feed: int, name: str) -> int | None:
		"""Dans la transaction d'« Enregistrer » : le stream qui suit le feed, créé s'il n'y en a pas, actif et
		titré du nom du feed ; un second ajout du même feed le reprend. None pour un feed effacé
		de la base entre-temps : la ligne est oubliée."""
		connection = self.card.connection
		if not queries.feed_exists(connection, feed):
			return None
		stream = queries.feed_stream(connection, feed)
		if stream is None:
			stream = queries.create_feed_stream(connection, feed, name)
		return stream

	def _columns(self) -> dict[str, str]:
		"""Les genres d'éléments de la liste, et leur colonne : jamais une séquence dans une séquence."""
		columns = {}
		for category, column in COLUMNS.items():
			if column != self.column_parent:
				columns[category] = column
		return columns

	def _read_marked(self) -> None:
		self.marked_list = queries.no_repeat_banks(self.card.connection)

	def _read(self, identifiers: dict[str, list[int]]) -> dict[str, dict[int, QTreeWidgetItem]]:
		"""Les lignes des éléments, par genre et par identifiant ; un élément absent de la base n'en a pas."""
		build = {"sound": self._sound_line, "bank": self._bank_line, "sequence": self._sequence_line}
		lines: dict[str, dict[int, QTreeWidgetItem]] = {}
		for category, requests in identifiers.items():
			fetched_list = queries.plays(self.card.connection, category, requests)
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
		chosen_lines = []
		for chosen in chosen_list:
			if chosen in fetched_list:
				chosen_lines.append(fetched_list[chosen])
		self.list_.addTopLevelItems(chosen_lines)
		self._refresh_buttons()

	def _add_feeds(self) -> None:
		"""Pour chaque feed choisi, le stream qui le suit ; sans stream, une ligne qui en créera un à
		l'enregistrement (https://github.com/dascritch/machincast/issues/167)."""
		chosen_list = dialogs.choose_feeds(self.card, self.card.connection, self.remark)
		self.load_all()
		connection = self.card.connection
		lines: list[QTreeWidgetItem] = []
		with connection.transaction():

			def add_feed(feed: int) -> None:
				nonlocal lines
				marks = queries.feed_marks(connection, feed)
				if marks is None:
					return
				stream = queries.feed_stream(connection, feed)
				if stream is not None:
					lines += self._read({"sound": [stream]})["sound"].values()
					return
				name, url = marks
				line = self._line("sound", [str(name), _("{url}, new stream").format(url=url)], (None, None))
				line.setData(0, FEED, feed)
				lines.append(line)

			for feed in chosen_list:
				add_feed(feed)
		self.list_.addTopLevelItems(lines)
		self._refresh_buttons()

	def _drop_in(self, paths: list[Path]) -> None:
		"""Les fichiers sonores déposés s'ajoutent en fin de liste. Un fichier pas encore en base est montré par son
		nom, et deviendra un sonore à l'état aperçu à l'enregistrement."""
		files, ignored = sound_files(paths)
		self.load_all()
		with self.card.connection.transaction():
			fetched_list = queries.sounds_per_file(self.card.connection, files)
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
		"""Retire les lignes choisies, ou la ligne courante."""
		chosen_list = self.chosen()
		if chosen_list == []:
			chosen_list = [self.list_.currentItem()]
		for line in chosen_list:
			self.list_.takeTopLevelItem(self.list_.indexOfTopLevelItem(line))

	def chosen(self) -> list[QTreeWidgetItem]:
		"""Les lignes choisies, dans l'ordre de la liste."""
		chosen_list = []
		for line in self.lines():
			if line.isSelected():
				chosen_list.append(line)
		return chosen_list

	def copy(self) -> None:
		"""Les lignes choisies vont au presse-papiers : pour une liste d'éléments, et en texte, une ligne par élément,
		ses colonnes séparées par des tabulations."""
		chosen_list = self.chosen()
		if chosen_list == []:
			return
		entries = []
		text_list = []
		for line in chosen_list:
			entries.append(
				clipboard.entry(
					line.data(0, CATEGORY), line.data(0, ITEM), line.data(0, FILE), line.data(0, FEED), line.text(1)
				)
			)
			text_list.append(clipboard.text(self.list_, line))
		clipboard.put(entries, text_list)

	def paste(self) -> None:
		"""Les éléments copiés s'ajoutent après la ligne courante, ou en fin de liste, et restent choisis."""
		copied_list = clipboard.copied()
		if copied_list == []:
			return
		self.load_all()
		with self.card.connection.transaction():
			self._read_marked()
			lines, aside, events = self._copied_lines(copied_list)
		row = self.list_.topLevelItemCount()
		current = self.list_.currentItem()
		if current is not None:
			row = self.list_.indexOfTopLevelItem(current) + 1
		count = len(lines)
		self.list_.insertTopLevelItems(row, lines)
		self.list_.clearSelection()
		# Relues dans la liste : insérées, les lignes sont à elle.
		last = None
		for index in range(row, row + count):
			last = self.list_.topLevelItem(index)
			assert last is not None
			last.setSelected(True)
		if last is not None:
			self.list_.setCurrentItem(last, 0, QItemSelectionModel.SelectionFlag.NoUpdate)
		self._refresh_buttons()
		said = []
		if aside != []:
			said.append(SET_ASIDE.format(list=", ".join(aside)))
		if events != []:
			said.append(EVENTS_ASIDE.format(list=", ".join(events)))
		if said != []:
			self.card.message.setText(" ".join(said))

	def _copied_lines(self, copied_list: list[dict[str, object]]) -> tuple[list[QTreeWidgetItem], list[str], list[str]]:
		"""Les lignes des éléments copiés, dans leur ordre, lues en base ; les noms des séquences laissées de côté, et
		ceux des événements, copiés depuis la recherche. Un élément effacé de la base depuis la copie n'a pas de ligne."""
		identifiers: dict[str, list[int]] = {}
		files = []
		for copied in copied_list:
			category, item = str(copied["category"]), copied["item"]
			if (isinstance(item, int)) and (category in self.buttons.add):
				identifiers.setdefault(category, []).append(item)
			if (item is None) and (copied["file"] is not None):
				files.append(str(copied["file"]))
		fetched = self._read(identifiers)
		by_file = {}
		for sound in queries.sounds_per_file(self.card.connection, files):
			by_file[str(sound[3])] = sound
		lines: list[QTreeWidgetItem] = []
		aside: list[str] = []
		events: list[str] = []
		for copied in copied_list:
			category = str(copied["category"])
			if category == "event":
				events.append(str(copied["name"]))
			else:
				if category not in self.buttons.add:
					aside.append(str(copied["name"]))
				else:
					self._copied_line(copied, fetched, by_file, lines)
		return lines, aside, events

	def _copied_line(
		self,
		copied: dict[str, object],
		fetched: dict[str, dict[int, QTreeWidgetItem]],
		by_file: dict[str, tuple[object, ...]],
		lines: list[QTreeWidgetItem],
	) -> None:
		"""Ajoute la ligne d'un élément copié : une nouvelle à chaque fois, un même élément pouvant revenir."""
		category, item = str(copied["category"]), copied["item"]
		if isinstance(item, int):
			if item in fetched.get(category, {}):
				lines.append(fetched[category][item].clone())
			return
		if copied["feed"] is not None:
			feed = int(str(copied["feed"]))
			marks = queries.feed_marks(self.card.connection, feed)
			if marks is not None:
				line = self._line("sound", [str(marks[0]), _("{url}, new stream").format(url=marks[1])], (None, None))
				line.setData(0, FEED, feed)
				lines.append(line)
			return
		file = str(copied["file"])
		lines.append(self._sound_line(by_file.get(file, (None, None, None, file, file))))

	def _move(self, offset: int) -> None:
		line = self.list_.currentItem()
		row = self.list_.indexOfTopLevelItem(line)
		self.list_.takeTopLevelItem(row)
		self.list_.insertTopLevelItem(row + offset, line)
		# Rendue courante, la ligne déplacée met à jour les boutons (currentItemChanged).
		self.list_.setCurrentItem(line)

	def line_menu(self, line: QTreeWidgetItem | None) -> QMenu:
		"""Le menu du clic droit : « Pré-écoute… » d'un sonore en base (https://github.com/dascritch/machincast/issues/226),
		puis « Copier » les lignes choisies et « Coller » les éléments copiés, inactifs sans elles
		(https://github.com/dascritch/machincast/issues/129)."""
		menu = QMenu(self.list_)
		if (line is not None) and (line.data(0, CATEGORY) == "sound") and (line.data(0, ITEM) is not None):
			display.offer_preview(menu, int(line.data(0, ITEM)), self.card.requested_preview.emit)
			menu.addSeparator()
		clipboard.offer(menu, chosen=self.chosen() != [], copy=self.copy, paste=self.paste)
		return menu

	def _open(self, line: QTreeWidgetItem) -> None:
		"""Ouvrir un élément demande sa fiche ; un fichier déposé n'en a pas avant l'enregistrement."""
		identifier = line.data(0, ITEM)
		if identifier is not None:
			self.card.requested_opening.emit(str(line.data(0, CATEGORY)), int(identifier), line.text(1))
