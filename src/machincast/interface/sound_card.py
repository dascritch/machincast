"""Fiche d'un sonore (https://github.com/dascritch/machincast/issues/28, spec § 8.3).

La fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.window), depuis la liste des sonores, ou vide
pour un nouveau stream (https://github.com/dascritch/machincast/issues/30), qui entre en base à l'état actif ; un
fichier s'ajoute depuis la liste (machincast.interface.adding). Enregistrement, annulation et fermeture :
machincast.interface.card.

- Champs : artiste, titre, les métadonnées musicales que tient l'indexeur (année, album, artiste de l'album, genre,
  compositeur, label, piste), crossfades, maximum de lectures, masquage, période de diffusion, état, et pour un fichier
  la détection de silence, avec le début et la fin détectés (https://github.com/dascritch/machincast/issues/146). Les
  autres clés des métadonnées musicales sont montrées, jamais modifiées. L'emplacement et la durée ne se modifient pas.
- Seuls les champs modifiés depuis la lecture de la fiche sont écrits : ce que l'indexation ou la diffusion change
  entre-temps est gardé. Chacun est ajouté à edited_fields, sauf l'état, que l'indexeur peut encore changer
  (fichier défectueux, puis de nouveau sain) : l'indexeur ne modifie plus un champ édité.
- État : l'interface pose « actif » ou « désactivé » ; un sonore expiré, erroné ou supprimé peut y revenir. Un sonore
  en aperçu attend sa première indexation.
- Stream : adresse directe ou feed, événement de secours parmi les événements de priorité secours, et test du
  flux à la demande (machincast.interface.stream_trial), sur l'adresse saisie, même pas encore enregistrée.
- Derniers passages : les 50 derniers, du plus récent au plus ancien, avec les alertes et incidents du log pendant
  chaque passage.
- Début et fin (https://github.com/dascritch/machincast/issues/330) : les silences détectés se nomment « Début
  détecté » et « Fin détectée » tant qu'ils sont ceux de l'indexeur, « Début » et « Fin » dès qu'ils sont saisis à la
  main, dans la fiche ou avant (edited_fields). Cochés, ils ont chacun un curseur sur la frise, qui se glisse à la
  souris et règle sa case. Le début ne passe jamais après la fin : chaque case est bornée par l'autre, comme chaque
  curseur, et l'enregistrement refuse des silences qui ne laissent pas de son.
- Relations (https://github.com/dascritch/machincast/issues/125) : les séquences, banques et événements qui citent le
  sonore dans leur liste ; un double-clic ouvre leur fiche. Le clic droit sur une relation propose de l'en retirer
  (https://github.com/dascritch/machincast/issues/331) : la relation disparaît de la fiche, modifiée, et
  « Enregistrer » retire le sonore de la liste de la séquence, de la banque ou de l'événement, toutes ses places
  comprises ; « Annuler » la rétablit. Une banque dont un répertoire contient le fichier prévient d'abord que la
  prochaine indexation l'y remettra, comme sa fiche. Le fichier n'est jamais touché.
- Fichier : type lu par l'indexeur (https://github.com/dascritch/machincast/issues/121), encodage moyen (taille sur
  durée, pochette et tags compris), taille, dates de création et de modification lues sur le fichier, qui n'est que lu,
  et date de sa dernière vérification complète par l'indexeur. Le bouton du dossier ouvre le dossier du fichier dans
  le navigateur de fichiers du poste.
- Encarts (https://github.com/dascritch/machincast/issues/190) : « Métadonnées », « Diffusion », « Détection de
  silence », « Relations » et « Fichier » sont repliés à l'ouverture de la fiche, et se déplient d'un clic sur leur
  titre (machincast.interface.expandable).
- « Vérification complète », pour un fichier enregistré, demande l'audit complet de ce seul sonore
  (requested_check) ; le bouton attend sa fin (wait_check), puis une question propose de
  rafraîchir la fiche (finished_check).
"""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from psycopg import sql
from psycopg.types.json import Jsonb
from PySide6.QtCore import QDateTime, Qt, QTimer, Signal
from PySide6.QtGui import QIntValidator, QStandardItemModel
from PySide6.QtWidgets import (
	QCheckBox,
	QDateTimeEdit,
	QDoubleSpinBox,
	QLineEdit,
	QMenu,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

from machincast.clock import Clock
from machincast.conformation import conform
from machincast.conversion import duration_or_none, text_or_none
from machincast.i18n import _, logged, pgettext
from machincast.interface import dialogs, display, expandable, icons, preferences
from machincast.interface.bank_card import removal_warning
from machincast.interface.card import Card, Connection, Refusal, rank_of
from machincast.interface.columns import Columns
from machincast.interface.dialogs import Removal
from machincast.interface.intents import REMOVE, label
from machincast.interface.lists import STATES, TYPES
from machincast.interface.slider import DurationSlider
from machincast.interface.stream_trial import StreamTrial, trial_result
from machincast.interface.timeline import Timeline, WaveShape, sound_plan
from machincast.interface.ui.sound_card import Ui_SoundCard

METADATA: tuple[tuple[str, str], ...] = (
	("year", _("year")),
	("album", "album"),
	("album_artist", _("album artist")),
	("genre", "genre"),
	("composer", "compositeur"),
	("label", "label"),
	("track", "piste"),
)
"""Clés de music_metadata tenues par l'indexeur (machincast.indexer.tags.KEYS), et leur nom à l'écran."""
INTEGERS = frozenset({"year", "track"})
"""Clés dont la valeur est un nombre entier."""


def _metadata_labels() -> dict[str, str]:
	"""Le nom à l'écran de chaque champ de music_metadata."""
	labels = {}
	for key, name in METADATA:
		labels[f"music_metadata.{key}"] = name
	return labels


LABELS: dict[str, str] = {
	"artist": "artiste",
	"title": "titre",
	**_metadata_labels(),
	"crossfade_start": _("start crossfade"),
	"crossfade_end": _("end crossfade"),
	"max_plays": _("maximum of plays"),
	"hide_metadata": _("artist and title"),
	"broadcast_start": _("broadcast start"),
	"broadcast_end": _("broadcast end"),
	"stream_url": _("direct address"),
	"feed_id": "feed",
	"fallback_event_id": _("fallback event"),
	"silence_detection": _("silence detection"),
	"detected_start": _("detected start"),
	"detected_end": _("detected end"),
	"duration": _("duration"),
}
"""Nom à l'écran d'un champ de edited_fields."""
STATE_CHOICE: dict[str, tuple[str, ...]] = {
	"preview": ("preview",),
	"active": ("active", "disabled"),
	"disabled": ("disabled", "active"),
	"expired": ("expired", "active", "disabled"),
	"corrupt": ("corrupt", "active", "disabled"),
	"unsupported": ("unsupported", "active", "disabled"),
	"missing": ("missing", "active", "disabled"),
}
"""L'état du sonore, puis ceux que l'interface peut poser."""
HIDINGS: tuple[tuple[bool | None, str], ...] = (
	(None, _("According to the configuration")),
	(True, _("Hidden")),
	(False, _("Shown")),
)
"""Valeurs de sounds.hide_metadata, dans l'ordre du choix de la fiche."""
NEW_STREAM: tuple[object, ...] = (
	"stream",
	None,
	None,
	None,
	None,
	None,
	None,
	None,
	{},
	timedelta(0),
	timedelta(0),
	None,
	"active",
	None,
	None,
	None,
	None,
	[],
	None,
	None,
	False,
	None,
	None,
	False,
)
"""Ce que montre la fiche d'un nouveau stream, dans l'ordre des colonnes lues."""
RELATION = Qt.ItemDataRole.UserRole
SILENCE_MAXIMAL = 86400.0
"""Secondes d'un silence détecté au plus, sans durée connue : celles du champ de la fiche."""
MARKERS = {
	"detected_start": (_("Detected start"), _("Start")),
	"detected_end": (_("Detected end"), _("End")),
}
"""Le nom de chaque silence détecté : mesuré par l'indexeur, ou saisi à la main
(https://github.com/dascritch/machincast/issues/330)."""
ITEMS = {"sequence": _("the sequence"), "bank": _("the bank"), "event": _("the event")}
RELATION_LISTS = {
	"sequence": ("sequence_items", "sequence_id"),
	"bank": ("bank_sounds", "bank_id"),
	"event": ("event_items", "event_id"),
}
"""La table de la liste de chaque genre de relation, et sa colonne qui désigne l'élément."""
"""Rôle qui porte, sur la cellule du nom d'une relation, son genre et son identifiant."""
PLAYS = 50
"""Nombre de derniers passages montrés."""
URL = Qt.ItemDataRole.UserRole + 1
"""Rôle qui porte l'adresse d'un feed, dans son choix."""


EXPANDED_PANELS = "fiche-sonore/encarts-deplies"
"""Dans les réglages des vues du compte (machincast.interface.columns) : les encarts dépliés des fiches de sonore."""
SHAPE_READING = 100
"""Millisecondes entre deux relèves de la forme d'onde en cours de calcul."""
TIMELINE_TITLE = _(
	"The file as the on-air output will play it, according to the settings of the form, even not yet saved"
)

STAT_DELAY = 5
"""Secondes laissées à stat pour lire la date de création d'un fichier, sur un partage réseau par exemple."""


PREVIEW = _("Listen to the sound on the pre-listen output, never on air")
"""L'infobulle de « Pré-écoute… », celle de fiche_sonore.ui."""


class SoundCard(Card):
	# « Pré-écoute… » émet requested_preview, de la Fiche (https://github.com/dascritch/machincast/issues/116).
	requested_check = Signal(int)
	"""« Vérification complète » : le sonore dont faire l'audit complet
	(https://github.com/dascritch/machincast/issues/190)."""
	category = "sound"

	def __init__(
		self, connection: Connection, identifier: int | None, clock: Clock, parent: QWidget | None = None
	) -> None:
		super().__init__(connection, identifier, clock, parent)
		self.ui = Ui_SoundCard()
		self.ui.setupUi(self)
		self.plug(self.ui.save, self.ui.cancel, self.ui.delete, self.ui.message)
		name_dict = {}
		for key, _name in METADATA:
			name_dict[key] = getattr(self.ui, key)
		self.metadata: dict[str, QLineEdit] = name_dict
		for key in INTEGERS:
			self.metadata[key].setValidator(QIntValidator(0, 9999, self))
		# Le pas et la durée maximale des préférences (https://github.com/dascritch/machincast/issues/145), sur un
		# curseur (https://github.com/dascritch/machincast/issues/223).
		for crossfade in (self.ui.start_crossfade, self.ui.end_crossfade):
			crossfade.set_according_to_preferences()
		# La frise, sur toute la largeur de la fiche (https://github.com/dascritch/machincast/issues/223).
		self.timeline = Timeline(self.ui.timeline_place, interactive=False)
		self.timeline.moved_slider.connect(self._put_marker)
		self._edited_fields: set[str] = set()
		"""Les champs saisis à la main avant l'ouverture de la fiche, d'après la base."""
		timeline_layout = QVBoxLayout(self.ui.timeline_place)
		timeline_layout.setContentsMargins(0, 0, 0, 0)
		timeline_layout.addWidget(self.timeline)
		self.shape: WaveShape | None = None
		self._audited = False
		self._shape_reading = QTimer(self)
		self._shape_reading.setInterval(SHAPE_READING)
		self._shape_reading.timeout.connect(self._read_off_shape)
		for _value, text in HIDINGS:
			self.ui.hiding.addItem(text)
		self.trial = StreamTrial(self)
		self.ui.preview.setIcon(icons.icon("preview"))
		self.ui.preview.clicked.connect(self._preview)
		self.ui.check.clicked.connect(self._check)
		self._file = False
		"""Le sonore lu est un fichier : seul un fichier se vérifie."""
		self._in_check = False
		# Les encarts dépliés sont retenus pour le compte (https://github.com/dascritch/machincast/issues/223).
		expanded_list = expandable.retained(EXPANDED_PANELS)
		for group in (
			self.ui.metadata_group,
			self.ui.broadcast_group,
			self.ui.silence_group,
			self.ui.relation_group,
			self.ui.file_group,
		):
			expandable.make_expandable(
				group, group.objectName() in expanded_list, expandable.retain_in(EXPANDED_PANELS)
			)
		self.trial.finished.connect(self._finished_trial)
		self._name = ""
		self._initial_list: dict[str, object] = {}
		"""Champs tels que la fiche les a montrés à la lecture : seuls ceux qui en diffèrent sont écrits."""
		for field in (self.ui.artist, self.ui.title, self.ui.url_stream, *self.metadata.values()):
			field.textChanged.connect(self._modify)
		for choice in (self.ui.state, self.ui.hiding, self.ui.feed, self.ui.fallback):
			choice.currentIndexChanged.connect(self._modify)
		self.ui.playback_max.valueChanged.connect(self._modify)
		for box, slider in (
			(self.ui.has_start_crossfade, self.ui.start_crossfade),
			(self.ui.has_end_crossfade, self.ui.end_crossfade),
		):
			slider.valueChanged.connect(self._modify)
			slider.valueChanged.connect(self._refresh_timeline)
			box.toggled.connect(slider.setEnabled)
			box.toggled.connect(self._modify)
			box.toggled.connect(self._refresh_timeline)
		# Détection de silence (https://github.com/dascritch/machincast/issues/146) : un silence décoché n'est pas
		# détecté.
		self.ui.detection_silences.toggled.connect(self._modify)
		self.ui.detection_silences.toggled.connect(self._refresh_timeline)
		for box, count in (
			(self.ui.has_detected_start, self.ui.detected_start),
			(self.ui.has_detected_end, self.ui.detected_end),
		):
			count.setLocale(preferences.FRENCH)
			count.valueChanged.connect(self._modify)
			count.valueChanged.connect(self._bound_silences)
			count.valueChanged.connect(self._refresh_timeline)
			box.toggled.connect(count.setEnabled)
			box.toggled.connect(self._modify)
			box.toggled.connect(self._bound_silences)
			box.toggled.connect(self._refresh_timeline)
		self._duration: timedelta | None = None
		"""Durée du fichier en base, que les silences détectés ne peuvent pas couvrir à eux deux."""
		for box, date in ((self.ui.has_start, self.ui.broadcast_start), (self.ui.has_end, self.ui.broadcast_end)):
			box.toggled.connect(date.setEnabled)
			box.toggled.connect(self._modify)
			date.dateTimeChanged.connect(self._modify)
		self.ui.by_address.toggled.connect(self._mode_stream)
		self.ui.by_address.toggled.connect(self._modify)
		self.ui.test.clicked.connect(self._test)
		self.ui.open_folder.clicked.connect(lambda: dialogs.open_folder(Path(self.ui.location.text()).parent))
		self.ui.relations.itemActivated.connect(self._open_relation)
		self.relation_columns = Columns(self.ui.relations, "fiche-sonore-relations")
		self.relation_columns.line_menu = lambda position: self.relation_menu(self.ui.relations.rowAt(position.y()))
		self._removed_list: list[tuple[str, int]] = []
		"""Les relations retirées dans la fiche, que « Enregistrer » retire en base : genre et identifiant."""
		self.play_columns = Columns(self.ui.plays, "fiche-sonore-passages")
		self.load()

	def title(self) -> str:
		if self.identifier is None:
			return _("New stream")
		return _("Sound: {name}").format(name=self._name)

	def _refresh_timeline(self) -> None:
		"""Le plan du fichier selon les champs de la fiche, même pas encore enregistrés : crossfades, silences détectés
		et leur retrait, avec les crossfades par défaut et les positions des fondus des préférences."""
		duration = self._duration
		if (not self._file) or (duration is None):
			self.timeline.display(None, None)
			return
		ui = self.ui
		plan = sound_plan(
			duration,
			_crossfade(ui.has_detected_start, ui.detected_start),
			_crossfade(ui.has_detected_end, ui.detected_end),
			ui.detection_silences.isChecked(),
			_crossfade(ui.has_start_crossfade, ui.start_crossfade),
			_crossfade(ui.has_end_crossfade, ui.end_crossfade),
			preferences.crossfades(),
			self._audited,
		)
		self.timeline.display(plan, duration.total_seconds())
		self.ui.timeline_place.setToolTip(f"{plan.summary()}\n{TIMELINE_TITLE}")
		sliders = {}
		if ui.has_detected_start.isChecked():
			sliders["start"] = ui.detected_start.value()
		if ui.has_detected_end.isChecked():
			sliders["end"] = duration.total_seconds() - ui.detected_end.value()
		self.timeline.show_sliders(sliders)
		self._give_name_markers()

	def _put_marker(self, name: str, position: float) -> None:
		"""Un curseur glissé sur la frise règle sa case : le début depuis le début du fichier, la fin depuis sa fin."""
		if self._duration is None:
			return
		if name == "start":
			self.ui.detected_start.setValue(position)
		else:
			self.ui.detected_end.setValue(self._duration.total_seconds() - position)

	def _bound_silences(self) -> None:
		"""Le début ne passe pas après la fin : chaque silence coché laisse au plus à l'autre le reste du fichier."""
		ui = self.ui
		if self._duration is None:
			return
		duration = self._duration.total_seconds()
		for box, count, other_box, other in (
			(ui.has_detected_start, ui.detected_start, ui.has_detected_end, ui.detected_end),
			(ui.has_detected_end, ui.detected_end, ui.has_detected_start, ui.detected_start),
		):
			rest = duration
			if other_box.isChecked():
				rest = max(0.0, duration - other.value())
			if box.isChecked():
				count.setMaximum(rest)

	def _give_name_markers(self) -> None:
		"""« Début détecté » et « Fin détectée » tant qu'ils sont ceux de l'indexeur ; « Début » et « Fin », saisis à
		la main : dans la fiche, ou avant."""
		inputs = {
			"detected_start": _crossfade(self.ui.has_detected_start, self.ui.detected_start),
			"detected_end": _crossfade(self.ui.has_detected_end, self.ui.detected_end),
		}
		initial_list = getattr(self, "_initial_list", {})
		for field, box in (("detected_start", self.ui.has_detected_start), ("detected_end", self.ui.has_detected_end)):
			detected, manual = MARKERS[field]
			entered = (field in self._edited_fields) or (
				(field in initial_list) and (inputs[field] != initial_list[field])
			)
			shown = detected
			if entered:
				shown = manual
			box.setText(shown)

	def _show_shape(self, path: Path | None) -> None:
		"""La forme d'onde du fichier, calculée en tâche de fond, une fois par fichier."""
		if (self.shape is not None) and (path is not None) and (self.shape.path == path):
			return
		self._halt_shape()
		if path is not None:
			duration = None
			if self._duration is not None:
				duration = self._duration.total_seconds()
			self.shape = WaveShape(path, duration)
			self.shape.start()
			self._shape_reading.start()
		self.timeline.show_shape(self.shape)

	def _read_off_shape(self) -> None:
		shape = self.shape
		if shape is None:
			self._shape_reading.stop()
			return
		if shape.read_off():
			self.timeline.update()
		if shape.finished:
			self._shape_reading.stop()

	def _halt_shape(self) -> None:
		self._shape_reading.stop()
		if self.shape is not None:
			self.shape.halt()
		self.shape = None

	def shut_down(self) -> None:
		self.trial.halt()

	def _preview(self) -> None:
		if (self.identifier is not None) and (not display.disabled_preview()):
			self.requested_preview.emit(self.identifier)

	def follow_preview(self) -> None:
		"""« Pré-écoute… » sert à un sonore en base, sauf sur l'entrée « Sortie factice » de la pré-écoute
		(https://github.com/dascritch/machincast/issues/339)."""
		display.set_preview(self.ui.preview, self.identifier is not None, PREVIEW)

	def _check(self) -> None:
		if self.identifier is not None:
			self.requested_check.emit(self.identifier)

	def wait_check(self) -> None:
		"""La vérification complète est lancée : le bouton attend sa fin."""
		self._in_check = True
		self.ui.check.setText(_("Checking…"))
		self._refresh_check()
		self.message.setText(_("Full check running…"))

	def finished_check(self, text: str) -> None:
		"""La vérification complète est finie : une question propose de rafraîchir la fiche, qui montre alors ce que
		l'indexeur a écrit."""
		self._in_check = False
		self.ui.check.setText(_("Full check"))
		self._refresh_check()
		self.message.clear()
		if dialogs.offer_refresh(self, text):
			self.refresh()

	def _refresh_check(self) -> None:
		"""Un fichier enregistré se vérifie, une seule fois à la fois ; un stream ne se vérifie pas."""
		self.ui.check.setEnabled((self.identifier is not None) and (self._file) and (not self._in_check))

	def _read(self) -> None:
		"""Lit le sonore en base ; un nouveau stream est actif, sans adresse ni réglage."""
		# Un nouveau stream n'est pas encore en base : rien à pré-écouter avant son enregistrement.
		self.follow_preview()
		line: tuple[object, ...] | None = NEW_STREAM
		plays: list[tuple[object, ...]] = []
		relations: list[tuple[object, ...]] = []
		with self.connection.transaction():
			if self.identifier is not None:
				line = self._read_sound()
				plays = self._read_plays()
				relations = self._read_relations()
			marks = self.connection.execute("SELECT id, name, url FROM feeds ORDER BY name").fetchall()
			fallback = self.connection.execute(
				"SELECT id, internal_name FROM events WHERE priority = 'fallback' AND deleted_at IS NULL"
				" ORDER BY internal_name"
			).fetchall()
		assert line is not None, f"sonore {self.identifier} absent"
		self._show(line, marks, fallback, plays)
		self._removed_list = []
		self._show_relations(relations)

	def _read_sound(self) -> tuple[object, ...] | None:
		return self.connection.execute(
			"SELECT s.type::text, s.location, s.stream_url, s.feed_id, m.url, s.fallback_event_id,"
			" s.artist, s.title, s.music_metadata, s.crossfade_start, s.crossfade_end, s.max_plays,"
			" s.state::text, s.hide_metadata, s.duration, s.broadcast_start, s.broadcast_end, s.edited_fields,"
			" s.mime_type, s.checked_at, s.silence_detection, s.detected_start, s.detected_end,"
			" s.audited_at IS NOT NULL"
			" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
			(self.identifier,),
		).fetchone()

	def _show(
		self,
		line: tuple[object, ...],
		marks: list[tuple[object, ...]],
		fallback: list[tuple[object, ...]],
		plays: list[tuple[object, ...]],
	) -> None:
		(
			sound_type,
			location,
			url_stream,
			feed,
			url_feed,
			fallback_event,
			artist,
			title,
			metadata,
			start_crossfade,
			end_crossfade,
			playback_max,
			state,
			hiding,
			duration,
			start,
			end,
			edited_fields,
			type_mime,
			checks_at,
			detection_silences,
			detected_start,
			detected_end,
			audited,
		) = line
		self._audited = audited is True
		stream = sound_type == "stream"
		self._name = (text_or_none(title)) or (Path(str(location)).name)
		if stream:
			self._name = (text_or_none(title)) or (str((url_stream) or (url_feed)))
		self.ui.sound_type.setText(TYPES.get(str(sound_type), str(sound_type)))
		self.ui.location.setText(str((location) or ("")))
		self.ui.sound_form.setRowVisible(self.ui.location_caption, not stream)
		self.ui.file_group.setVisible(not stream)
		if not stream:
			self._show_file(Path(str(location)), type_mime, duration, checks_at)
		self._file = sound_type == "file"
		self._refresh_check()
		self.ui.stream_group.setVisible(stream)
		# Un stream n'a pas de silences détectés : seul un fichier est audité.
		self.ui.silence_group.setVisible(not stream)
		self.ui.detection_silences.setChecked(detection_silences is True)
		for box, count, silence in (
			(self.ui.has_detected_start, self.ui.detected_start, detected_start),
			(self.ui.has_detected_end, self.ui.detected_end, detected_end),
		):
			# Le maximum de la fiche précédente ne borne pas les silences de celle-ci : _borner_les_silences le règle.
			count.setMaximum(SILENCE_MAXIMAL)
			count.setValue(_seconds(silence))
			box.setChecked(isinstance(silence, timedelta))
		self._duration = None
		if isinstance(duration, timedelta):
			self._duration = duration
		duration_text = ""
		if stream:
			duration_text = display.duration(None)
		else:
			if isinstance(duration, timedelta):
				duration_text = display.duration(duration)
		self.ui.duration.setText(duration_text)
		# Tous les états, dans leur ordre ; ceux que l'interface ne pose pas sont grisés
		# (https://github.com/dascritch/machincast/issues/223).
		self.ui.state.clear()
		possible = STATE_CHOICE[str(state)]
		model = self.ui.state.model()
		assert isinstance(model, QStandardItemModel)
		for code, state_name in STATES.items():
			self.ui.state.addItem(state_name, code)
			if code not in possible:
				item = model.item(self.ui.state.count() - 1)
				item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
		self.ui.state.setCurrentIndex(self.ui.state.findData(str(state)))
		self.ui.state.setEnabled(len(possible) > 1)
		self.ui.artist.setText(str((artist) or ("")))
		self.ui.title.setText(str((title) or ("")))
		assert isinstance(metadata, dict)
		musical_list = dict(metadata)
		for key, field in self.metadata.items():
			field.setText(str(musical_list.pop(key, "")))
		others = []
		for key, value in sorted(musical_list.items()):
			others.append(_("{key}: {value}").format(key=key, value=value))
		self.ui.other_metadata.setText(", ".join(others))
		# Un crossfade non paramétré (NULL) est décoché ; 0 seconde en est un (https://github.com/dascritch/machincast/issues/145).
		for box, slider, crossfade in (
			(self.ui.has_start_crossfade, self.ui.start_crossfade, start_crossfade),
			(self.ui.has_end_crossfade, self.ui.end_crossfade, end_crossfade),
		):
			slider.display(_seconds(crossfade))
			box.setChecked(isinstance(crossfade, timedelta))
		self.ui.playback_max.setValue(int(str((playback_max) or (0))))
		self.ui.hiding.setCurrentIndex(rank_of(HIDINGS, hiding))
		self._show_date(self.ui.has_start, self.ui.broadcast_start, start)
		self._show_date(self.ui.has_end, self.ui.broadcast_end, end)
		self.ui.feed.clear()
		for identifier, name, url in marks:
			self.ui.feed.addItem(str(name), int(str(identifier)))
			self.ui.feed.setItemData(self.ui.feed.count() - 1, str(url), URL)
		self.ui.by_feed.setEnabled(marks != [])
		self.ui.feed.setCurrentIndex(self.ui.feed.findData(feed))
		self.ui.url_stream.setText(str((url_stream) or ("")))
		self.ui.by_feed.setChecked(feed is not None)
		self.ui.by_address.setChecked(feed is None)
		self._mode_stream()
		self.ui.fallback.clear()
		self.ui.fallback.addItem(_("None: the background programming"), None)
		for identifier, name in fallback:
			self.ui.fallback.addItem(str(name), int(str(identifier)))
		self.ui.fallback.setCurrentIndex(self.ui.fallback.findData(fallback_event))
		field_set = set()
		for edited in _list(edited_fields):
			field_set.add(str(edited))
		self._edited_fields = field_set
		edited_list = []
		for edited in _list(edited_fields):
			edited_list.append(LABELS.get(str(edited), str(edited)))
		edited_text = ""
		if edited_list != []:
			edited_text = _("Entered by hand, no longer changed by the indexer: {list}.").format(
				list=", ".join(edited_list)
			)
		self.ui.edited_fields.setText(edited_text)
		self._show_plays(plays)
		self.ui.timeline_place.setVisible(self._file)
		file = None
		if self._file:
			file = Path(str(location))
		self._show_shape(file)
		self._bound_silences()
		self._refresh_timeline()
		self._initial_list = self._inputs()
		self._give_name_markers()

	def _show_date(self, box: QCheckBox, date: QDateTimeEdit, value: object) -> None:
		"""Une période sans date part de l'heure de l'horloge, à la minute, quand sa case se coche."""
		instant = self.clock.now().replace(second=0, microsecond=0)
		if isinstance(value, datetime):
			instant = value
		date.setDateTime(QDateTime.fromSecsSinceEpoch(int(instant.timestamp())))
		# La case active la date quand elle change d'état (toggled).
		box.setChecked(isinstance(value, datetime))

	def _mode_stream(self) -> None:
		self.ui.url_stream.setEnabled(self.ui.by_address.isChecked())
		self.ui.feed.setEnabled(self.ui.by_feed.isChecked())

	def _inputs(self) -> dict[str, object]:
		"""Les champs modifiables, tels que la fiche les montre : colonne de sonores, ou music_metadata.<clé>."""
		inputs: dict[str, object] = {
			"artist": (conform(self.ui.artist.text())) or (None),
			"title": (conform(self.ui.title.text())) or (None),
		}
		for key, field in self.metadata.items():
			value: str | int | None = (conform(field.text())) or (None)
			if (key in INTEGERS) and (value is not None):
				value = int(value)
			inputs[f"music_metadata.{key}"] = value
		inputs["crossfade_start"] = _crossfade(self.ui.has_start_crossfade, self.ui.start_crossfade)
		inputs["crossfade_end"] = _crossfade(self.ui.has_end_crossfade, self.ui.end_crossfade)
		inputs["max_plays"] = (self.ui.playback_max.value()) or (None)
		inputs["hide_metadata"] = HIDINGS[self.ui.hiding.currentIndex()][0]
		inputs["broadcast_start"] = display.ticked_date(self.ui.has_start, self.ui.broadcast_start)
		inputs["broadcast_end"] = display.ticked_date(self.ui.has_end, self.ui.broadcast_end)
		if self.ui.silence_group.isVisibleTo(self):
			inputs["silence_detection"] = self.ui.detection_silences.isChecked()
			inputs["detected_start"] = _crossfade(self.ui.has_detected_start, self.ui.detected_start)
			inputs["detected_end"] = _crossfade(self.ui.has_detected_end, self.ui.detected_end)
		if self.ui.stream_group.isVisibleTo(self):
			inputs["stream_url"] = None
			inputs["feed_id"] = None
			if self.ui.by_address.isChecked():
				inputs["stream_url"] = (self.ui.url_stream.text().strip()) or (None)
			else:
				inputs["feed_id"] = self.ui.feed.currentData()
			inputs["fallback_event_id"] = self.ui.fallback.currentData()
		inputs["state"] = self.ui.state.currentData()
		return inputs

	def _write(self) -> int:
		inputs = self._inputs()
		start, end = inputs["broadcast_start"], inputs["broadcast_end"]
		if (isinstance(start, datetime)) and (isinstance(end, datetime)) and (end <= start):
			raise Refusal(_("The end of the broadcast must follow its start."), self.ui.has_start, self.ui.has_end)
		if ("stream_url" in inputs) and (inputs["stream_url"] is None) and (inputs["feed_id"] is None):
			raise Refusal(_("The address of the stream is required."), self.ui.by_address, self.ui.by_feed)
		# Seuls des silences saisis sont refusés : l'indexeur ne mesure jamais des silences qui couvrent tout le
		# fichier.
		sides = ("detected_start", "detected_end")
		entered_list = False
		for side in sides:
			if inputs.get(side) != self._initial_list.get(side):
				entered_list = True
				break
		silences = []
		side_list = []
		for side in sides:
			side_list.append(inputs.get(side))
		for silence in side_list:
			if isinstance(silence, timedelta):
				silences.append(silence)
		if (entered_list) and (self._duration is not None) and (sum(silences, timedelta(0)) >= self._duration):
			raise Refusal(
				_("The detected silences must leave some sound: together, shorter than the duration of the sound."),
				self.ui.has_detected_start,
				self.ui.has_detected_end,
			)
		identifier = self.identifier
		if identifier is None:
			# Un nouveau stream entre en base avec son adresse ; ses autres champs s'écrivent comme une modification.
			created = self.connection.execute(
				"INSERT INTO sounds (type, stream_url, feed_id, state)"
				" VALUES ('stream', %s, %s, 'active') RETURNING id",
				(inputs["stream_url"], inputs["feed_id"]),
			).fetchone()
			assert created is not None
			identifier = int(str(created[0]))
		modified_list = []
		for field, value in inputs.items():
			if value != self._initial_list[field]:
				modified_list.append(field)
		line = self.connection.execute(
			"SELECT edited_fields FROM sounds WHERE id = %s FOR UPDATE", (identifier,)
		).fetchone()
		if line is None:
			raise Refusal(_("This sound is no longer in the database."))
		edited_list = list((line[0]) or ([]))
		field_list = []
		for field in modified_list:
			if (field != "state") and (field not in edited_list):
				field_list.append(field)
		edited_list += field_list
		columns = []
		for field in modified_list:
			if not field.startswith("music_metadata."):
				columns.append(field)
		assignments: list[sql.Composable] = []
		for assigned in columns:
			assignments.append(sql.SQL("{} = %s").format(sql.Identifier(assigned)))
		values: list[object] = []
		for given in columns:
			values.append(inputs[given])
		prefix = "music_metadata."
		musical_list = {}
		for field in modified_list:
			if field.startswith(prefix):
				musical_list[field.removeprefix(prefix)] = inputs[field]
		assignments.append(sql.SQL("music_metadata = (music_metadata - %s::text[]) || %s::jsonb"))
		key_dict = {}
		for key, value in musical_list.items():
			if value is not None:
				key_dict[key] = value
		values += [list(musical_list), Jsonb(key_dict)]
		assignments.append(sql.SQL("edited_fields = %s"))
		values.append(edited_list)
		query = sql.SQL("UPDATE sounds SET {} WHERE id = %s").format(sql.SQL(", ").join(assignments))
		self.connection.execute(query, [*values, identifier])
		for category, item in self._removed_list:
			table, column = RELATION_LISTS[category]
			self.connection.execute(
				sql.SQL("DELETE FROM {} WHERE {} = %s AND sound_id = %s").format(
					sql.Identifier(table), sql.Identifier(column)
				),
				(item, identifier),
			)
		return identifier

	def _read_relations(self) -> list[tuple[object, ...]]:
		"""Les séquences, banques et événements dont la liste cite le sonore ; dans une transaction."""
		return self.connection.execute(
			"SELECT category, id, name, minimum, maximum, (SELECT duration FROM sounds WHERE id = %s) FROM ("
			" SELECT 1 AS rank, 'sequence' AS category, q.id, q.internal_name AS name, NULL::interval AS minimum,"
			"  NULL::interval AS maximum FROM sequences q"
			"  WHERE q.deleted_at IS NULL"
			"  AND EXISTS (SELECT 1 FROM sequence_items x WHERE x.sequence_id = q.id AND x.sound_id = %s)"
			" UNION ALL SELECT 2, 'bank', b.id, b.internal_name, b.min_duration, b.max_duration FROM banks b"
			"  WHERE b.deleted_at IS NULL"
			"  AND EXISTS (SELECT 1 FROM bank_sounds x WHERE x.bank_id = b.id AND x.sound_id = %s)"
			" UNION ALL SELECT 3, 'event', e.id, e.internal_name, NULL, NULL FROM events e"
			"  WHERE e.deleted_at IS NULL"
			"  AND EXISTS (SELECT 1 FROM event_items x WHERE x.event_id = e.id AND x.sound_id = %s)"
			") r ORDER BY rank, name, id",
			(self.identifier, self.identifier, self.identifier, self.identifier),
		).fetchall()

	def _show_relations(self, relations: list[tuple[object, ...]]) -> None:
		table = self.ui.relations
		table.setRowCount(0)
		for category, identifier, name, minimum, maximum, duration in relations:
			row = table.rowCount()
			table.insertRow(row)
			# L'icône du genre (https://github.com/dascritch/machincast/issues/215).
			table.setItem(
				row,
				0,
				QTableWidgetItem(icons.icon_of(str(category)), display.CATEGORIES.get(str(category), str(category))),
			)
			cell = QTableWidgetItem(str(name))
			cell.setData(RELATION, (str(category), int(str(identifier))))
			# Une banque dont le sonore sort des durées (https://github.com/dascritch/machincast/issues/147).
			gap = display.outside_durations(
				duration_or_none(duration), duration_or_none(minimum), duration_or_none(maximum), str(name)
			)
			if gap is not None:
				cell.setIcon(display.anomaly_icon(self))
				cell.setToolTip(gap)
			table.setItem(row, 1, cell)
		self.ui.no_relation.setVisible(relations == [])

	def relation_menu(self, row: int) -> QMenu | None:
		"""Le menu du clic droit sur cette ligne des relations : « ➖ Retirer de la banque « Jingles » » ; aucun hors
		d'une ligne, ou pour un sonore supprimé, dont la fiche ne se modifie pas."""
		name = self.ui.relations.item(row, 1)
		if (name is None) or (self.deleted_at is not None):
			return None
		category, _identifier = name.data(RELATION)
		menu = QMenu(self)
		remove = menu.addAction(
			label(REMOVE, _("Remove from {items} “{text}”").format(items=ITEMS[category], text=name.text()))
		)
		remove.triggered.connect(lambda _ticked=False: self.remove_relation(row))
		return menu

	def remove_relation(self, row: int) -> None:
		"""La relation quitte la fiche, jusqu'à « Enregistrer » ; d'une banque qui indexe le fichier, seulement après
		l'avertissement que la prochaine indexation l'y remettra."""
		name = self.ui.relations.item(row, 1)
		assert name is not None
		category, identifier = name.data(RELATION)
		directory = None
		if category == "bank":
			directory = self._bank_directory(identifier)
		if directory is not None:
			response = dialogs.confirm_removal(self, removal_warning(self._name, directory))
			if response is Removal.OPEN_FOLDER:
				dialogs.open_folder(Path(self.ui.location.text()).parent)
			if response is not Removal.REMOVE:
				return
		self._removed_list.append((str(category), int(identifier)))
		self.ui.relations.removeRow(row)
		self.ui.no_relation.setVisible(self.ui.relations.rowCount() == 0)
		self._modify()

	def _bank_directory(self, bank: int) -> str | None:
		"""Le répertoire de la banque où se trouve le fichier du sonore, même dans un sous-répertoire ; None hors de
		tous, ou pour un stream."""
		if not self._file:
			return None
		path = Path(self.ui.location.text())
		with self.connection.transaction():
			directories = self.connection.execute(
				"SELECT directory FROM bank_directories WHERE bank_id = %s ORDER BY directory", (bank,)
			).fetchall()
		for (directory,) in directories:
			if path.is_relative_to(str(directory)):
				return str(directory)
		return None

	def _open_relation(self, cell: QTableWidgetItem) -> None:
		name = self.ui.relations.item(cell.row(), 1)
		assert name is not None
		category, identifier = name.data(RELATION)
		self.requested_opening.emit(category, identifier, name.text())

	def _show_file(self, path: Path, type_mime: object, duration: object, checks_at: object) -> None:
		"""Ce que la base sait du fichier, et ce que le fichier dit de lui-même, sans être modifié."""
		ui = self.ui
		ui.type_mime.setText(str((type_mime) or (pgettext("masculine", "unknown"))))
		ui.checks_at.setText(_("never"))
		if isinstance(checks_at, datetime):
			ui.checks_at.setText(display.date(checks_at))
		ui.encoding.setText("inconnu")
		try:
			state = path.stat()
		except OSError:
			for field in (ui.size, ui.created_at, ui.modified_at):
				field.setText(_("not found"))
			return
		ui.size.setText(display.size(state.st_size))
		ui.modified_at.setText(display.date(datetime.fromtimestamp(state.st_mtime).astimezone()))
		ui.created_at.setText(_("unknown"))
		birth = _birth(path)
		if birth is not None:
			ui.created_at.setText(display.date(birth))
		# La base refuse une durée nulle.
		if isinstance(duration, timedelta):
			ui.encoding.setText(f"≈ {round(state.st_size * 8 / duration.total_seconds() / 1000)} kbit/s")

	def _read_plays(self) -> list[tuple[object, ...]]:
		"""Les derniers passages, avec les alertes et incidents du log pendant chacun ; dans une transaction."""
		return self.connection.execute(
			"SELECT d.logged_at, f.logged_at, f.played_duration, e.internal_name, q.internal_name,"
			" b.internal_name, i.horodatages, i.natures, i.messages"
			" FROM airplay d"
			" LEFT JOIN airplay f ON f.play_id = d.play_id AND f.line_type = 'end'"
			" LEFT JOIN events e ON e.id = COALESCE(d.lender_event_id, d.event_id)"
			" LEFT JOIN sequences q ON q.id = d.sequence_id"
			" LEFT JOIN banks b ON b.id = d.bank_id"
			" LEFT JOIN LATERAL ("
			"  SELECT array_agg(l.logged_at ORDER BY l.logged_at, l.id) AS horodatages,"
			"   array_agg(l.kind::text ORDER BY l.logged_at, l.id) AS natures,"
			"   array_agg(l.message ORDER BY l.logged_at, l.id) AS messages"
			"  FROM log l WHERE l.sound_id = d.sound_id AND l.level <> 'info' AND l.logged_at >= d.logged_at"
			"   AND (f.logged_at IS NULL OR l.logged_at <= f.logged_at)"
			" ) i ON true"
			" WHERE d.line_type = 'start' AND d.sound_id = %s"
			" ORDER BY d.logged_at DESC, d.id DESC LIMIT %s",
			(self.identifier, PLAYS),
		).fetchall()

	def _show_plays(self, plays: list[tuple[object, ...]]) -> None:
		table = self.ui.plays
		table.setRowCount(0)
		for start, end, duration, event, sequence, bank, timestamps, kinds, messages in plays:
			assert isinstance(start, datetime)
			end_text, duration_text = _("ongoing"), ""
			if isinstance(end, datetime):
				end_text = display.hour(end)
			if isinstance(duration, timedelta):
				duration_text = display.duration(duration)
			incidents = list(zip(_list(timestamps), _list(kinds), _list(messages), strict=True))
			cells = [f"{start.astimezone():%Y-%m-%d %H:%M:%S}", end_text, duration_text]
			name_list = []
			for name in (event, sequence, bank):
				name_list.append(str((name) or ("")))
			cells += name_list
			incident_kinds = []
			for _h, kind, _m in incidents:
				incident_kinds.append(logged(str(kind)))
			cells.append(", ".join(incident_kinds))
			items = []
			for text in cells:
				items.append(QTableWidgetItem(text))
			details = []
			for h, kind, message in incidents:
				details.append(
					_("{hour} {kind}: {message}").format(
						hour=_hour(h), kind=logged(str(kind)), message=logged(str(message))
					)
				)
			items[-1].setToolTip("\n".join(details))
			row = table.rowCount()
			table.insertRow(row)
			for column, item in enumerate(items):
				table.setItem(row, column, item)

	def _address(self) -> str:
		if self.ui.by_address.isChecked():
			return self.ui.url_stream.text().strip()
		return str(self.ui.feed.currentData(URL))

	def _test(self) -> None:
		self.ui.test.setEnabled(False)
		self.ui.trial_result.setText(_("Stream test running…"))
		self.trial.launch(self._address())

	def _finished_trial(self, answers: bool, detail: str) -> None:
		self.ui.trial_result.setText(trial_result(answers, detail))
		self.ui.test.setEnabled(True)


def _crossfade(box: QCheckBox, count: QDoubleSpinBox | DurationSlider) -> timedelta | None:
	"""Le crossfade, ou le silence détecté, saisi ; None s'il n'est pas paramétré, ou pas détecté."""
	if not box.isChecked():
		return None
	return timedelta(seconds=count.value())


def _seconds(value: object) -> float:
	if isinstance(value, timedelta):
		return value.total_seconds()
	return 0.0


def _list(value: object) -> list[object]:
	"""Un tableau lu en base, vide pour NULL."""
	if isinstance(value, list):
		return value
	return []


def _hour(value: object) -> str:
	if isinstance(value, datetime):
		return display.hour(value)
	return str(value)


def _birth(path: Path) -> datetime | None:
	"""La date de création du fichier, que stat lit dans le système de fichiers ; None si le système n'en garde pas.

	Python ne la donne pas sous Linux : stat (coreutils) la demande à statx.
	"""
	try:
		output = subprocess.run(
			["stat", "--format=%W", str(path)], capture_output=True, text=True, check=True, timeout=STAT_DELAY
		).stdout
		seconds = int((output.strip()) or ("0"))
	# Un partage réseau qui ne répond plus, ou une réponse inattendue, laisse la date inconnue, sans figer ni faire
	# planter la fiche (https://github.com/dascritch/machincast/issues/187).
	except (OSError, subprocess.SubprocessError, ValueError):
		return None
	if seconds <= 0:
		return None
	return datetime.fromtimestamp(seconds).astimezone()
