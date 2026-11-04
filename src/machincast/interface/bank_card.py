"""Fiche d'une banque (https://github.com/dascritch/machincast/issues/31, spec § 8.4).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.window), depuis la liste des banques, ou vide pour
une nouvelle banque. Enregistrement, annulation et fermeture : machincast.interface.card.

- Les noms sont enregistrés conformés (machincast.conformation, https://github.com/dascritch/machincast/issues/108) ; un
  nom public vide n'en est pas un (NULL).
- Le masquage « hérité du sonore » (NULL) laisse décider le sonore ; « masqués » et « affichés » l'imposent.
- Les répertoires sont enregistrés sous leur forme normale, comme les lit Machin indexer.
- Crossfades (https://github.com/dascritch/machincast/issues/143) : pour le début comme pour la fin, une règle et une
  durée. « Garder ceux des sonores » laisse le crossfade de chaque sonore, et la durée de la banque, gardée pour
  plus tard, ne se modifie pas ; « Appliquer si le sonore n'en a pas » la donne aux sonores sans crossfade
  (0 seconde) ; « Imposer à tous les sonores », à tous. La diffusion l'applique aux sonores joués via la banque
  (machincast.player.broadcast.crossfade).
- Durées des sonores (https://github.com/dascritch/machincast/issues/147) : une durée minimale et une durée maximale,
  facultatives, à cocher. Un sonore qui en sort est marqué dans la liste, d'après les durées de la fiche, avant même
  l'enregistrement ; rien n'est refusé, la diffusion n'en tient pas compte. Une minimale qui dépasse la maximale
  n'est pas enregistrée.
- Ouvrir un sonore, par un double-clic ou Entrée, ouvre sa fiche (https://github.com/dascritch/machincast/issues/115) ;
  la banque reste telle quelle, modifications comprises. Un fichier déposé n'a de fiche qu'une fois enregistré.
- Les sonores se réordonnent par glisser-déposer, ou par les boutons « Monter » et « Descendre », en mode séquentiel
  seulement. Ils s'ajoutent parmi les sonores déjà en base (machincast.interface.choice), y compris hors des
  répertoires de la banque.
- Des dossiers déposés depuis le navigateur de fichiers s'ajoutent aux répertoires, des fichiers sonores aux sonores
  (machincast.interface.drop), toujours comme une copie. Un fichier pas encore en base devient un sonore à l'état
  aperçu à l'enregistrement seulement.
- Retirer un sonore dont le fichier est dans l'un des répertoires de la fiche prévient que la prochaine indexation
  l'y remettra, et propose d'ouvrir son dossier : le fichier ne s'écarte que hors de MachinCast
  (https://github.com/dascritch/machincast/issues/96).
- À l'enregistrement, les sonores qu'une indexation a rattachés à la banque depuis l'ouverture de la fiche sont gardés,
  en fin de liste ; un sonore effacé de la base entre-temps est oublié.
- Sélection multiple (https://github.com/dascritch/machincast/issues/114) : Ctrl et Maj choisissent plusieurs sonores.
  « Retirer le sonore » les retire tous, avec un seul avertissement pour ceux des répertoires de la fiche ; « Monter »
  et « Descendre » ne servent qu'à un sonore seul. Le clic droit propose « Activer » et « Désactiver » : la colonne
  État montre aussitôt l'état choisi, que « Enregistrer » écrit avec le reste de la fiche et qu'« Annuler » oublie.
  Un sonore en aperçu reste en aperçu, un fichier déposé aussi.
- Sa copie (https://github.com/dascritch/machincast/issues/130) garde tout sauf sa liste de sonores : nom public, mode,
  masquage, « ne pas répéter », crossfades, durées et répertoires. Ses répertoires la rempliront à la prochaine
  indexation.

Les fenêtres de dialogue sont celles de machincast.interface.dialogs.
"""

import os
from datetime import timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
	QAbstractItemView,
	QCheckBox,
	QComboBox,
	QDoubleSpinBox,
	QMenu,
	QTimeEdit,
	QTreeWidgetItem,
	QWidget,
)

from machincast.clock import Clock
from machincast.conformation import conform
from machincast.conversion import text_or_none
from machincast.i18n import _
from machincast.interface import dialogs, display, preferences
from machincast.interface.card import Card, Connection, Refusal, sound_files
from machincast.interface.columns import Columns
from machincast.interface.dialogs import Removal
from machincast.interface.drop import FileDrop
from machincast.interface.lists import (
	BANK_WITHOUT_ACTIVE_SOUND,
	SOUND_IN_ANOMALY,
	STATES,
	bank_to_sounds_in_anomaly,
)
from machincast.interface.ui.bank_card import Ui_BankCard

MODES = (("sequential", _("Sequential")), ("random", _("Random")))
CROSSFADE_RULES = (
	("sound", _("Keep the sounds' own")),
	("default", _("Apply if the sound has none")),
	("forced", _("Impose on all sounds")),
)
HIDINGS: tuple[tuple[bool | None, str], ...] = (
	(None, _("Inherited from the sound")),
	(True, _("Hidden by the bank's public name")),
	(False, _("Shown")),
)
"""Valeurs de banks.hide_metadata, dans l'ordre du choix de la fiche."""
SOUND = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la première colonne d'une ligne de sonore, son identifiant en base."""
FILE = Qt.ItemDataRole.UserRole + 1
"""Rôle qui porte le chemin du fichier du sonore, None pour un stream."""
DURATION = Qt.ItemDataRole.UserRole + 2
"""Rôle qui porte la durée du sonore, absente quand elle est inconnue."""
STATE = Qt.ItemDataRole.UserRole + 3
"""Rôle qui porte l'état du sonore en base ; « apercu » pour un fichier déposé."""
CHOSEN_STATE = Qt.ItemDataRole.UserRole + 4
"""Rôle qui porte l'état choisi au clic droit, écrit à l'enregistrement ; absent sans choix."""
STATE_COLUMN = 2
CHOSEN_STATES = (("active", _("Enable")), ("disabled", _("Disable")))
"""Les états qui se choisissent au clic droit sur les sonores, et leur entrée de menu."""
LINE = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled
"""Une ligne de sonore se glisse, mais rien ne se dépose dedans : la liste reste à plat."""
FETCHED_SOUNDS = (
	"SELECT s.id, s.artist, s.title, s.duration, s.location, COALESCE(s.location, s.stream_url, m.url),"
	" s.state::text"
	" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id"
)


ALREADY_IN_BANK = _("A sound already in the bank is not added a second time.")
"""Remarque du choix des sonores."""
FOLDER_ON_SOUNDS = _(" A folder is dropped on the indexed directories.")
"""Conseil pour un dossier déposé sur les sonores."""


def group_removal_warning(sounds: list[str], directories: list[str]) -> str:
	"""L'avertissement d'un retrait de sonores des répertoires de la banque ; celui d'un seul sonore, pour un seul."""
	if (len(sounds) == 1) and (len(directories) == 1):
		return removal_warning(sounds[0], directories[0])
	names = ", ".join(_("“{sound}”").format(sound=sound) for sound in sounds)
	ou = _("of directory {directories}, indexed").format(directories=directories[0])
	if len(directories) > 1:
		ou = _("of directories {list}, indexed").format(list=", ".join(directories))
	return _(
		"{names} are files {ou} by this bank: the next indexing will put them back. To remove them "
		"for good, move their files out of these directories, outside MachinCast."
	).format(names=names, ou=ou)


def removal_warning(sound: str, directory: str) -> str:
	return _(
		"“{sound}” is a file of directory {directory}, indexed by this bank: the next indexing "
		"will put it back. To remove it for good, move its file out of this directory, outside "
		"MachinCast."
	).format(sound=sound, directory=directory)


class BankCard(Card):
	category = "bank"

	def __init__(
		self, connection: Connection, identifier: int | None, clock: Clock, parent: QWidget | None = None
	) -> None:
		super().__init__(connection, identifier, clock, parent)
		self.ui = Ui_BankCard()
		self.ui.setupUi(self)
		self.plug(self.ui.save, self.ui.cancel, self.ui.delete, self.ui.message, self.ui.duplicate)
		for value, text in MODES:
			self.ui.mode.addItem(text, value)
		for _value, text in HIDINGS:
			self.ui.hiding.addItem(text)
		self.columns = Columns(self.ui.sounds, "fiche-banque-sonores")
		self._name = ""
		self._loaded_list: set[int] = set()
		"""Sonores de la banque à la dernière lecture : ceux qui manquent à la fiche en ont été retirés."""
		self.directory_drop = FileDrop(self.ui.directories)
		self.directory_drop.dropped.connect(self._drop_in_directories)
		self.sound_drop = FileDrop(self.ui.sounds)
		self.sound_drop.dropped.connect(self._drop_in_sounds)
		self.ui.internal_name.textChanged.connect(self._modify)
		self.ui.public_name.textChanged.connect(self._modify)
		self.ui.mode.currentIndexChanged.connect(self._modify)
		self.ui.mode.currentIndexChanged.connect(self._refresh_buttons)
		self.ui.hiding.currentIndexChanged.connect(self._modify)
		self.ui.no_repeat.toggled.connect(self._modify)
		self.ui.detection_silences.toggled.connect(self._modify)
		for rule, duration in self._crossfades():
			for value, text in CROSSFADE_RULES:
				rule.addItem(text, value)
			# Le pas et la durée maximale des préférences (https://github.com/dascritch/machincast/issues/145).
			preferences.set_according_to_preferences(duration)
			rule.currentIndexChanged.connect(self._modify)
			rule.currentIndexChanged.connect(self._refresh_crossfades)
			duration.valueChanged.connect(self._modify)
		for box, field in self._durations():
			box.toggled.connect(field.setEnabled)
			box.toggled.connect(self._modify)
			box.toggled.connect(self._mark_outside_durations)
			field.timeChanged.connect(self._modify)
			field.timeChanged.connect(self._mark_outside_durations)
		model = self.ui.sounds.model()
		# Le glisser-déposer déplace une ligne en la retirant, puis en l'insérant.
		model.rowsInserted.connect(self._modify)
		model.rowsInserted.connect(self._mark_outside_durations)
		model.rowsRemoved.connect(self._modify)
		model.rowsInserted.connect(self._warn)
		model.rowsRemoved.connect(self._warn)
		self.ui.directories.currentItemChanged.connect(self._refresh_buttons)
		self.ui.sounds.currentItemChanged.connect(self._refresh_buttons)
		self.ui.sounds.itemSelectionChanged.connect(self._refresh_buttons)
		self.columns.line_menu = lambda position: self.sound_menu(self.ui.sounds.itemAt(position))
		self.ui.sounds.itemActivated.connect(self._open_sound)
		self.ui.add_directory.clicked.connect(self._add_directory)
		self.ui.remove_directory.clicked.connect(self._remove_directory)
		self.ui.add_sounds.clicked.connect(self._add_sounds)
		self.ui.remove_sound.clicked.connect(self._remove_sound)
		self.ui.raise_.clicked.connect(lambda: self._move(-1))
		self.ui.go_down.clicked.connect(lambda: self._move(1))
		self.load()

	def title(self) -> str:
		if self.is_copy():
			return _("New bank, copy of {name}").format(name=self._name)
		if self.identifier is None:
			return _("New bank")
		return _("Bank: {name}").format(name=self._name)

	def _read(self) -> None:
		"""Lit la banque en base, ou celle qu'elle copie, sans ses sonores ; une nouvelle banque est vide, séquentielle,
		au masquage hérité du sonore, sans détection de silence (https://github.com/dascritch/machincast/issues/146)."""
		bank: tuple[object, ...] = (
			"",
			None,
			MODES[0][0],
			None,
			False,
			"sound",
			timedelta(0),
			"sound",
			timedelta(0),
			None,
			None,
			False,
		)
		directories: list[str] = []
		sounds: list[tuple[object, ...]] = []
		lu = self.lu()
		with self.connection.transaction():
			if lu is not None:
				line = self.connection.execute(
					"SELECT internal_name, public_name, mode::text, hide_metadata, no_repeat,"
					" crossfade_start_rule::text, crossfade_start, crossfade_end_rule::text, crossfade_end,"
					" min_duration, max_duration, silence_detection FROM banks WHERE id = %s",
					(lu,),
				).fetchone()
				assert line is not None, f"banque {lu} absente"
				bank = line
				directories = [
					str(directory)
					for (directory,) in self.connection.execute(
						"SELECT directory FROM bank_directories WHERE bank_id = %s", (lu,)
					)
				]
			if self.identifier is not None:
				sounds = self.connection.execute(
					f"{FETCHED_SOUNDS} JOIN bank_sounds bs ON bs.sound_id = s.id"
					" WHERE bs.bank_id = %s ORDER BY bs.position",
					(self.identifier,),
				).fetchall()
		name, public_name, mode, hiding, no_repeat, *crossfades, min_duration, max_duration, detection = bank
		self._name = str(name)
		self.ui.internal_name.setText(self._name)
		if self.is_copy():
			self.ui.internal_name.setText(self.name_of_copy(self._name))
		self.ui.public_name.setText(str((public_name) or ("")))
		self.ui.mode.setCurrentIndex(self.ui.mode.findData(mode))
		self.ui.hiding.setCurrentIndex(next(i for i, (value, _text) in enumerate(HIDINGS) if value is hiding))
		self.ui.no_repeat.setChecked(bool(no_repeat))
		self.ui.detection_silences.setChecked(detection is True)
		for (rule, duration), (value, seconds) in zip(
			self._crossfades(), (crossfades[:2], crossfades[2:]), strict=True
		):
			rule.setCurrentIndex(rule.findData(value))
			if isinstance(seconds, timedelta):
				preferences.display(duration, seconds.total_seconds())
		self._refresh_crossfades()
		for (box, field), bound in zip(self._durations(), (min_duration, max_duration), strict=True):
			box.setChecked(isinstance(bound, timedelta))
			if isinstance(bound, timedelta):
				field.setTime(QTime(0, 0).addSecs(int(bound.total_seconds())))
		self._show_directories(directories)
		self.ui.sounds.clear()
		self.ui.sounds.addTopLevelItems([self._line(sound) for sound in sounds])
		self._loaded_list = set(self._sounds())
		self._warn()
		self._refresh_buttons()

	def _write(self) -> int:
		name = conform(self.ui.internal_name.text())
		if name == "":
			raise Refusal(_("The internal name is required."), self.ui.internal_name)
		taken = self.connection.execute(
			"SELECT 1 FROM banks WHERE internal_name = %s AND id IS DISTINCT FROM %s AND deleted_at IS NULL",
			(name, self.identifier),
		).fetchone()
		if taken is not None:
			raise Refusal(_("Another bank is already called “{name}”.").format(name=name), self.ui.internal_name)
		values: list[object] = [
			name,
			(conform(self.ui.public_name.text())) or (None),
			self.ui.mode.currentData(),
			HIDINGS[self.ui.hiding.currentIndex()][0],
			self.ui.no_repeat.isChecked(),
		]
		for rule, duration in self._crossfades():
			values += [rule.currentData(), timedelta(seconds=duration.value())]
		minimum, maximum = self._bounds()
		if (minimum is not None) and (maximum is not None) and (minimum > maximum):
			raise Refusal(
				_("The minimum duration of the sounds exceeds the maximum duration."),
				self.ui.has_min_duration,
				self.ui.has_max_duration,
			)
		values += [minimum, maximum, self.ui.detection_silences.isChecked()]
		if self.identifier is None:
			created = self.connection.execute(
				"INSERT INTO banks (internal_name, public_name, mode, hide_metadata, no_repeat,"
				" crossfade_start_rule, crossfade_start, crossfade_end_rule, crossfade_end, min_duration, max_duration,"
				" silence_detection) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
				values,
			).fetchone()
			assert created is not None
			identifier = int(str(created[0]))
		else:
			identifier = self.identifier
			self.connection.execute(
				"UPDATE banks SET internal_name = %s, public_name = %s, mode = %s, hide_metadata = %s,"
				" no_repeat = %s, crossfade_start_rule = %s, crossfade_start = %s, crossfade_end_rule = %s,"
				" crossfade_end = %s, min_duration = %s, max_duration = %s, silence_detection = %s WHERE id = %s",
				(*values, identifier),
			)
		self.connection.execute("DELETE FROM bank_directories WHERE bank_id = %s", (identifier,))
		self.connection.execute(
			"INSERT INTO bank_directories (bank_id, directory) SELECT %s, unnest(%s::text[])",
			(identifier, self._directories()),
		)
		self._write_sounds(identifier)
		self._write_states()
		return identifier

	def _write_states(self) -> None:
		"""Les états choisis au clic droit ; un sonore passé en aperçu entre-temps y reste."""
		for line in self._lines():
			chosen = line.data(0, CHOSEN_STATE)
			sound = line.data(0, SOUND)
			if (chosen is not None) and (sound is not None):
				self.connection.execute(
					"UPDATE sounds SET state = %s WHERE id = %s AND state <> 'preview'", (chosen, int(sound))
				)

	def sound_menu(self, line: QTreeWidgetItem | None) -> QMenu | None:
		"""Le menu du clic droit sur cette ligne : « Pré-écoute… » de son sonore, puis l'état des sonores choisis si
		elle en fait partie, d'elle seule sinon ; aucun hors d'une ligne."""
		if line is None:
			return None
		lines = self.ui.sounds.selectedItems()
		if line not in lines:
			lines = [line]
		menu = QMenu(self)
		for state, text in CHOSEN_STATES:
			entry = menu.addAction(text)
			entry.triggered.connect(lambda _ticked=False, state=state: self._choose_state(lines, state))
		# La ligne cliquée seule, si son sonore est en base : un fichier déposé ne l'est pas avant l'enregistrement
		# (https://github.com/dascritch/machincast/issues/226).
		sound = line.data(0, SOUND)
		if sound is not None:
			display.offer_preview(menu, int(sound), self.requested_preview.emit)
		return menu

	def _choose_state(self, lines: list[QTreeWidgetItem], state: str) -> None:
		"""L'état choisi se montre aussitôt ; un sonore en aperçu, ou pas encore en base, garde le sien."""
		for line in lines:
			if line.data(0, STATE) == "preview":
				continue
			line.setData(0, CHOSEN_STATE, state)
			line.setText(STATE_COLUMN, STATES[state])
		self._warn()
		self._modify()

	def _crossfades(self) -> tuple[tuple[QComboBox, QDoubleSpinBox], tuple[QComboBox, QDoubleSpinBox]]:
		"""La règle et la durée du crossfade de début, puis celles du crossfade de fin."""
		ui = self.ui
		return ((ui.start_crossfade_rule, ui.start_crossfade), (ui.end_crossfade_rule, ui.end_crossfade))

	def _durations(self) -> tuple[tuple[QCheckBox, QTimeEdit], tuple[QCheckBox, QTimeEdit]]:
		"""La case et le champ de la durée minimale des sonores, puis ceux de la durée maximale."""
		ui = self.ui
		return ((ui.has_min_duration, ui.min_duration), (ui.has_max_duration, ui.max_duration))

	def _bounds(self) -> tuple[timedelta | None, timedelta | None]:
		"""Les durées minimale et maximale de la fiche ; None pour une durée décochée."""
		bounds: list[timedelta | None] = []
		for box, field in self._durations():
			bound = None
			if box.isChecked():
				bound = timedelta(seconds=QTime(0, 0).secsTo(field.time()))
			bounds.append(bound)
		return bounds[0], bounds[1]

	def _warn(self) -> None:
		"""Une banque sans sonore actif ne fournit rien ; ses sonores erronés ou non supportés ne passent pas : en haut
		de la fiche, d'après les états qu'elle montre, choisis compris (https://github.com/dascritch/machincast/issues/328),
		comme la liste des banques (machincast.interface.lists)."""
		states = [(line.data(0, CHOSEN_STATE)) or (line.data(0, STATE)) for line in self._lines()]
		text = ""
		if "active" not in states:
			text = BANK_WITHOUT_ACTIVE_SOUND
		elif any(state in SOUND_IN_ANOMALY for state in states):
			text = bank_to_sounds_in_anomaly(sum(1 for state in states if state in SOUND_IN_ANOMALY))
		self.warn(text)

	def _mark_outside_durations(self) -> None:
		"""Les sonores hors des durées de la fiche ont l'icône d'anomalie et une infobulle qui dit pourquoi ; un sonore
		de durée inconnue, ou dans les durées, n'a ni l'une ni l'autre.

		Seules les lignes dont la marque change sont touchées, et la liste n'est prévenue qu'une fois, à la fin : chaque
		changement prévenu à part faisait recalculer la largeur de toute la colonne (ResizeToContents), et une banque
		de milliers de sonores gelait l'interface quand on cochait une durée (https://github.com/dascritch/machincast/issues/194)."""
		minimum, maximum = self._bounds()
		icon = display.anomaly_icon(self)
		model = self.ui.sounds.model()
		changed_list: list[int] = []
		blocked = model.blockSignals(True)
		try:
			for row, line in enumerate(self._lines()):
				gap = (display.outside_durations(line.data(0, DURATION), minimum, maximum)) or ("")
				if line.toolTip(0) == gap:
					continue
				changed_list.append(row)
				line.setToolTip(0, gap)
				line.setIcon(0, QIcon())
				if gap != "":
					line.setIcon(0, icon)
		finally:
			model.blockSignals(blocked)
		if changed_list:
			model.dataChanged.emit(model.index(min(changed_list), 0), model.index(max(changed_list), 0))

	def _refresh_crossfades(self) -> None:
		"""La durée d'une banque qui garde les crossfades de ses sonores ne sert pas : elle ne se modifie pas."""
		for rule, duration in self._crossfades():
			duration.setEnabled(rule.currentData() != "sound")

	def _write_sounds(self, bank: int) -> None:
		wanted = []
		for line in self._lines():
			identifier = line.data(0, SOUND)
			if identifier is None:
				identifier = self.save_file(str(line.data(0, FILE)))
			wanted.append(int(identifier))
		in_database = [
			int(str(sound))
			for (sound,) in self.connection.execute(
				"SELECT sound_id FROM bank_sounds WHERE bank_id = %s ORDER BY position FOR UPDATE", (bank,)
			)
		]
		# Rattachés par une indexation depuis la lecture de la fiche : gardés, en fin de liste. Un ensemble, et non la
		# liste voulue, pour qu'une banque de milliers de sonores s'enregistre en un temps linéaire
		# (https://github.com/dascritch/machincast/issues/187).
		kept_list = set(wanted)
		attached_list = [
			sound for sound in in_database if (sound not in self._loaded_list) and (sound not in kept_list)
		]
		existing_list = {
			int(str(sound))
			for (sound,) in self.connection.execute("SELECT id FROM sounds WHERE id = ANY(%s)", (wanted,))
		}
		order = [sound for sound in wanted if sound in existing_list] + attached_list
		self.connection.execute("DELETE FROM bank_sounds WHERE bank_id = %s", (bank,))
		with self.connection.cursor() as slider:
			slider.executemany(
				"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
				[(bank, sound, position) for position, sound in enumerate(order, start=1)],
			)

	def _line(self, sound: tuple[object, ...]) -> QTreeWidgetItem:
		"""Une ligne de sonore ; un fichier déposé, pas encore en base, n'a pas d'identifiant."""
		identifier, artist, title, duration, file, location, state = sound
		duration_text = ""
		if file is None:
			duration_text = display.duration(None)
		elif isinstance(duration, timedelta):
			duration_text = display.duration(duration)
		text = display.artist_and_title(text_or_none(artist), text_or_none(title))
		if (artist is None) and (title is None) and (file is not None):
			# Pas encore décodé : le nom du fichier en attendant ses tags.
			text = Path(str(file)).name
		line = QTreeWidgetItem([text, duration_text, STATES.get(str(state), str(state)), str((location) or (""))])
		line.setData(0, STATE, str(state))
		if identifier is not None:
			line.setData(0, SOUND, int(str(identifier)))
		line.setData(0, FILE, text_or_none(file))
		if isinstance(duration, timedelta):
			line.setData(0, DURATION, duration)
		line.setFlags(LINE)
		return line

	def _open_sound(self, line: QTreeWidgetItem) -> None:
		"""Ouvrir un sonore demande sa fiche ; un fichier déposé n'en a pas avant l'enregistrement."""
		identifier = line.data(0, SOUND)
		if identifier is not None:
			self.requested_opening.emit("sonore", int(identifier), line.text(0))

	def _lines(self) -> list[QTreeWidgetItem]:
		list_ = self.ui.sounds
		lines = [list_.topLevelItem(row) for row in range(list_.topLevelItemCount())]
		return [line for line in lines if line is not None]

	def _sounds(self) -> list[int]:
		"""Les sonores de la fiche déjà en base."""
		identifiers = [line.data(0, SOUND) for line in self._lines()]
		return [int(identifier) for identifier in identifiers if identifier is not None]

	def _directories(self) -> list[str]:
		list_ = self.ui.directories
		return [list_.item(row).text() for row in range(list_.count())]

	def _refresh_buttons(self) -> None:
		"""Les boutons d'une ligne ne servent qu'à une ligne choisie. L'ordre des sonores ne compte, et ne se change,
		qu'en mode séquentiel : « Monter » et « Descendre » ne servent pas en tête et en fin de liste."""
		self.ui.remove_directory.setEnabled(self.ui.directories.currentItem() is not None)
		sequential = self.ui.mode.currentData() == "sequential"
		mode = QAbstractItemView.DragDropMode.NoDragDrop
		if sequential:
			mode = QAbstractItemView.DragDropMode.InternalMove
		self.ui.sounds.setDragDropMode(mode)
		self.sound_drop.accept()
		list_ = self.ui.sounds
		chosen_list = list_.selectedItems()
		self.ui.remove_sound.setEnabled(chosen_list != [])
		row = -1
		if len(chosen_list) == 1:
			row = list_.indexOfTopLevelItem(chosen_list[0])
		self.ui.raise_.setEnabled((sequential) and (row > 0))
		self.ui.go_down.setEnabled((sequential) and (0 <= row < list_.topLevelItemCount() - 1))

	def _add_directory(self) -> None:
		chosen = dialogs.choose_directory(self)
		if chosen is None:
			return
		self._add_directories([chosen])

	def _add_directories(self, chosen_list: list[str]) -> None:
		"""Sous leur forme normale, sans doublon."""
		present_list = self._directories()
		new_list = [directory for directory in map(os.path.normpath, chosen_list) if directory not in present_list]
		if new_list == []:
			return
		self._show_directories(present_list + list(dict.fromkeys(new_list)))
		self._modify()

	def _drop_in_directories(self, paths: list[Path]) -> None:
		"""Les dossiers déposés s'ajoutent aux répertoires ; un fichier est ignoré, et la fiche le dit."""
		self._add_directories([str(path) for path in paths if path.is_dir()])
		self.flag_ignored([path for path in paths if not path.is_dir()], _("these are not directories"))

	def _drop_in_sounds(self, paths: list[Path]) -> None:
		"""Les fichiers sonores déposés s'ajoutent en fin de liste, une fois chacun. Un fichier pas encore en base est
		montré par son nom, et deviendra un sonore à l'état aperçu à l'enregistrement."""
		files, ignored = sound_files(paths)
		with self.connection.transaction():
			fetched_list = self.connection.execute(f"{FETCHED_SOUNDS} WHERE s.location = ANY(%s)", (files,)).fetchall()
		by_file = {str(sound[4]): sound for sound in fetched_list}
		present_list: set[object] = set(self._sounds())
		present_list |= {line.data(0, FILE) for line in self._lines()}
		lines = []
		for file in files:
			sound = by_file.get(file, (None, None, None, None, file, file, "preview"))
			key = sound[0]
			if key is None:
				key = file
			if key not in present_list:
				present_list.add(key)
				lines.append(self._line(sound))
		self.ui.sounds.addTopLevelItems(lines)
		self._refresh_buttons()
		self.flag_ignored(ignored, _("these are not sound files"), FOLDER_ON_SOUNDS)

	def _show_directories(self, directories: list[str]) -> None:
		"""Dans l'ordre de leurs caractères, quelle que soit la langue du poste."""
		self.ui.directories.clear()
		self.ui.directories.addItems(sorted(directories))

	def _remove_directory(self) -> None:
		self.ui.directories.takeItem(self.ui.directories.currentRow())
		self._modify()

	def _add_sounds(self) -> None:
		chosen_list = dialogs.choose_sounds(self, self.connection, ALREADY_IN_BANK)
		present_list = set(self._sounds())
		new_list = [sound for sound in chosen_list if sound not in present_list]
		with self.connection.transaction():
			fetched_list = self.connection.execute(f"{FETCHED_SOUNDS} WHERE s.id = ANY(%s)", (new_list,)).fetchall()
		by_identifier = {int(str(sound[0])): sound for sound in fetched_list}
		lines = [self._line(by_identifier[sound]) for sound in new_list if sound in by_identifier]
		self.ui.sounds.addTopLevelItems(lines)
		self._refresh_buttons()

	def _remove_sound(self) -> None:
		"""Les sonores choisis ; ceux des répertoires de la fiche y reviendront à la prochaine indexation, ce qu'un seul
		avertissement dit pour tous. « Ouvrir le dossier » ouvre celui du premier."""
		lines = [line for line in self._lines() if line.isSelected()]
		if lines == []:
			return
		reinstated = [
			(line, directory) for line in lines if (directory := self._directory_of(line.data(0, FILE))) is not None
		]
		response = Removal.REMOVE
		if reinstated != []:
			sounds = [line.text(0) for line, _directory in reinstated]
			directories = list(dict.fromkeys(directory for _line, directory in reinstated))
			response = dialogs.confirm_removal(self, group_removal_warning(sounds, directories))
		if response is Removal.REMOVE:
			for line in lines:
				self.ui.sounds.takeTopLevelItem(self.ui.sounds.indexOfTopLevelItem(line))
			# La ligne qui suit devient la ligne choisie, prête à être retirée à son tour.
			following = self.ui.sounds.currentItem()
			if following is not None:
				self.ui.sounds.setCurrentItem(following)
		elif response is Removal.OPEN_FOLDER:
			first, _directory = reinstated[0]
			dialogs.open_folder(Path(str(first.data(0, FILE))).parent)
		self._refresh_buttons()

	def _directory_of(self, file: object) -> str | None:
		"""Le répertoire de la fiche où se trouve le fichier, même dans un sous-répertoire ; None hors de tous."""
		if not isinstance(file, str):
			return None
		path = Path(file)
		for directory in self._directories():
			if path.is_relative_to(directory):
				return directory
		return None

	def _move(self, offset: int) -> None:
		list_ = self.ui.sounds
		line = list_.currentItem()
		if line is None:
			return
		row = list_.indexOfTopLevelItem(line)
		list_.takeTopLevelItem(row)
		list_.insertTopLevelItem(row + offset, line)
		# Rendue courante, la ligne déplacée met à jour les boutons (currentItemChanged).
		list_.setCurrentItem(line)
