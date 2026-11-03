"""Écran par défaut de Machin_interface (https://github.com/dascritch/machincast/issues/23, spec § 8.1).

En un coup d'œil : l'heure, le texte public du sonore en cours entre guillemets, l'état du binaire lecture, l'événement
à l'antenne et ses heures, le sonore en cours et le temps qui lui reste, le prochain sonore, chacun avec son événement,
sa séquence, sa banque et son horaire sur une ligne, les sonores à venir après le prochain, le plus lointain en haut
(https://github.com/dascritch/machincast/issues/228), et l'airplay des 12 dernières heures
(https://github.com/dascritch/machincast/issues/144). Les boutons de chaque sonore, et un double-clic dans les sonores
à venir ou l'airplay, demandent la fiche du sonore, de l'événement, de la séquence ou de la banque (ouverte). Le sonore
en cours, le prochain et les sonores à venir viennent de la socket d'état du binaire lecture (StateClient). L'airplay se
lit en base à l'ouverture, puis à chaque changement de sonore annoncé par la socket : jamais en boucle. La disposition
est dessinée dans ui/default_screen.ui (CONTRIBUTION.md).
"""

import logging
import math
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QLineEdit, QMenu, QSizePolicy, QVBoxLayout, QWidget

from machincast.clock import Clock
from machincast.configuration import Audio
from machincast.i18n import _, pgettext
from machincast.interface import display, expandable, icons, interruption, preferences
from machincast.interface.airplay import LAST_LIST, DisplayedPlay, read_airplay
from machincast.interface.calendar import long_date
from machincast.interface.columns import Columns
from machincast.interface.monitor import Monitor, port_name
from machincast.interface.state import STOP, DisplayedSound, PlaybackState, StateClient
from machincast.interface.stream_trial import StreamTrial, trial_result
from machincast.interface.timeline import Plan, Timeline, WaveShape, read_plan
from machincast.interface.ui.default_screen import Ui_DefaultScreen
from machincast.interface.vu_meter import VuMeter

log = logging.getLogger(__name__)

SECOND = 1000
"""Rafraîchissement de l'heure, en millisecondes."""
SHAPE_READING = 100
"""Millisecondes entre deux relèves des formes d'onde en cours de calcul (https://github.com/dascritch/machincast/issues/230)."""
STATES = {"playing": _("Broadcasting"), "dead_air": _("Dead air on air"), "stopped": _("Stopped")}
UPCOMING = 5
"""Lignes que montre la table des sonores à venir, autant que Machin player en prévoit."""
COLLAPSED_PANELS = "accueil/encarts-replies"
"""Dans les réglages des vues du compte : les encarts de l'onglet Antenne repliés, dépliés sinon."""
UPCOMING_LINES_AT_LEAST = 2
"""Lignes de la table des sonores à venir sur un écran trop petit pour les 5."""
ONGOING_TRIAL = _("Stream test running…")
NOT_HEALTHY = _("not healthy")
INCIDENT = _("yes")
"""La colonne Incident d'un passage qui en a eu un."""
"""Colonne « Incident » d'un sonore à venir dont le fichier a posé problème (spec § 4.6)."""
ITEM = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur une cellule de l'airplay, le genre et l'identifiant de l'élément qu'elle désigne."""
LIT_LIGHT = "QLabel {{ background: {tint}; color: white; border-radius: 3px; font-weight: bold; font-size: 7pt; }}"
OFF_LIGHT = "QLabel { color: palette(mid); font-size: 7pt; }"
"""Les voyants « Blanc » et « Saturation » de l'antenne, allumés de leur teinte, ou éteints, grisés."""


PREVIEW_NEXT = _("Listen to the next sound on the pre-listen output, never on air")
"""L'infobulle du bouton « Pré-écoute » du prochain sonore, celle de ecran_par_defaut.ui."""


class DefaultScreen(QWidget):
	requested_listening = Signal()
	"""Clic sur le VU-mètre de l'antenne, disponible : l'écouter en pré-écoute
	(https://github.com/dascritch/machincast/issues/24)."""
	reread_airplay = Signal()
	"""L'airplay de l'onglet Antenne a été relu : un nouveau sonore, ou un rafraîchissement."""
	opened = Signal(str, int, str)
	"""Fiche demandée : genre, identifiant et nom de l'élément."""
	requested_preview = Signal(int)
	"""« Pré-écoute… » choisi au clic droit sur une ligne de l'airplay : son sonore
	(https://github.com/dascritch/machincast/issues/226)."""
	requested_skip = Signal()
	"""« Sauter à ce sonore », au clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257)."""
	requested_advance = Signal(int, str)
	"""« Avancer … », au clic droit sur le prochain sonore : l'identifiant et le nom de l'événement suivant annoncé."""
	requested_interruption = Signal(str)
	"""Une interruption du menu « Diffusion », au clic droit sur le prochain sonore : « sequence » ou « evenement »
	(https://github.com/dascritch/machincast/issues/323)."""
	requested_fallback = Signal(object)
	"""« ⏭ Couper par le secours », au clic droit sur le prochain sonore : le secours choisi (interruption.Secours)."""
	AIRPLAY_COLUMNS = (
		("debut", _("Start")),
		("fin", _("End")),
		("duree", _("Duration")),
		("artiste", _("Artist")),
		("titre", _("Title")),
		("evenement", _("Event")),
		("sequence", _("Sequence")),
		("banque", _("Bank")),
		("incident", _("Incident")),
	)

	def __init__(
		self,
		connection: psycopg.Connection[TupleRow],
		state_socket: Path,
		clock: Clock,
		parent: QWidget | None = None,
		audio: Audio | None = None,
	) -> None:
		"""audio : la sortie et le périphérique de l'antenne, dont le VU-mètre lit le port de monitoring
		(https://github.com/dascritch/machincast/issues/24) ; sans elle, il est indisponible."""
		super().__init__(parent)
		self.connection = connection
		self.clock = clock
		self.ui = Ui_DefaultScreen()
		self.ui.setupUi(self)
		self.airplay_model = QStandardItemModel(0, len(self.AIRPLAY_COLUMNS), self)
		self.airplay_model.setHorizontalHeaderLabels([title for _, title in self.AIRPLAY_COLUMNS])
		self.ui.table_airplay.setModel(self.airplay_model)
		self.airplay_columns = Columns(self.ui.table_airplay, "accueil-airplay")
		self.ui.table_airplay.activated.connect(self._open_cell)
		self.airplay_columns.line_menu = lambda position: self.airplay_menu(self.ui.table_airplay.indexAt(position))
		# Les sonores à venir, avec les colonnes de l'airplay (https://github.com/dascritch/machincast/issues/228).
		self.upcoming_model = QStandardItemModel(0, len(self.AIRPLAY_COLUMNS), self)
		self.upcoming_model.setHorizontalHeaderLabels([title for _, title in self.AIRPLAY_COLUMNS])
		upcoming_table = self.ui.upcoming_table
		upcoming_table.setModel(self.upcoming_model)
		self.upcoming_columns = Columns(upcoming_table, "accueil-a-venir")
		upcoming_table.activated.connect(self._open_cell)
		self.upcoming_columns.line_menu = lambda position: self.upcoming_sound_menu(
			self.ui.upcoming_table.indexAt(position)
		)
		# Les 5 sonores à venir quand la place le permet ; sur un petit écran, la table se tasse jusqu'à 2 lignes, et
		# l'airplay jusqu'à une : la fenêtre garde une hauteur raisonnable.
		line = upcoming_table.verticalHeader().defaultSectionSize()
		header = upcoming_table.horizontalHeader().sizeHint().height() + 2 * upcoming_table.frameWidth()
		upcoming_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
		upcoming_table.setMaximumHeight(header + UPCOMING * line)
		upcoming_table.setMinimumHeight(header + UPCOMING_LINES_AT_LEAST * line)
		upcoming_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
		self.ui.table_airplay.setMinimumHeight(header + line)
		# L'airplay ne prend que la place que les sonores à venir lui laissent.
		self.ui.table_airplay.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
		screen_layout = self.layout()
		assert isinstance(screen_layout, QVBoxLayout)
		screen_layout.setStretchFactor(self.ui.airplay_frame, 1)
		# Les deux encarts se replient d'un clic sur leur titre ; un encart replié le reste pour le compte
		# (https://github.com/dascritch/machincast/issues/244).
		collapsed_list = expandable.retained(COLLAPSED_PANELS)
		for group in (self.ui.upcoming_frame, self.ui.airplay_frame):
			expandable.make_expandable(
				group,
				group.objectName() not in collapsed_list,
				expandable.retain_in(COLLAPSED_PANELS, expanded_list=False),
			)
		self._ongoing: DisplayedSound | None = None
		self._next: DisplayedSound | None = None
		self._tested_stream: int | None = None
		"""Le stream dont le flux est testé, ou l'a été : son résultat reste tant qu'il est le prochain sonore."""
		ui = self.ui
		# Chaque bouton « Fiche… » porte l'icône du genre qu'il ouvre (https://github.com/dascritch/machincast/issues/215).
		for category, buttons in (
			("sonore", (ui.open_ongoing_sound, ui.open_next_sound)),
			("événement", (ui.open_ongoing_event, ui.open_next_event)),
			("séquence", (ui.open_ongoing_sequence, ui.open_next_sequence)),
			("banque", (ui.open_ongoing_bank, ui.open_next_bank)),
		):
			for button in buttons:
				button.setIcon(icons.icon(category))
		ui.open_ongoing_sound.clicked.connect(lambda: self._open_sound(self._ongoing))
		ui.open_next_sound.clicked.connect(lambda: self._open_sound(self._next))
		ui.open_ongoing_event.clicked.connect(lambda: self._open_event(self._ongoing))
		ui.open_next_event.clicked.connect(lambda: self._open_event(self._next))
		ui.open_ongoing_sequence.clicked.connect(lambda: self._open_sequence(self._ongoing))
		ui.open_next_sequence.clicked.connect(lambda: self._open_sequence(self._next))
		ui.open_ongoing_bank.clicked.connect(lambda: self._open_bank(self._ongoing))
		ui.open_next_bank.clicked.connect(lambda: self._open_bank(self._next))
		self._known_play: datetime | None = None
		"""Début du sonore en cours que l'airplay affiché connaît : il n'est relu que si un autre est annoncé."""
		# Les frises des deux sonores (https://github.com/dascritch/machincast/issues/230) : elles se regardent, sans
		# déplacer de lecture.
		self.ongoing_timeline = _set_timeline(ui.ongoing_timeline_place)
		self.next_timeline = _set_timeline(ui.next_timeline_place)
		# Écouter le prochain sonore, et tester le flux d'un stream (https://github.com/dascritch/machincast/issues/223).
		ui.preview_next.setIcon(icons.icon("pré-écoute"))
		ui.preview_next.clicked.connect(self._preview_next)
		self.next_timeline.clicked.connect(self._preview_next)
		self.stream_trial = StreamTrial(self)
		self.stream_trial.finished.connect(self._finished_stream_trial)
		ui.test_next_stream.clicked.connect(self._test_next_stream)
		self._shapes: dict[tuple[int, str], WaveShape] = {}
		"""Les formes d'onde, par sonore et fichier : celle du prochain sonore sert encore quand il passe à
		l'antenne."""
		self._plans: dict[tuple[int, int | None], Plan | None] = {}
		"""Les plans lus en base, par sonore et banque."""
		self.ongoing_progress = 0
		"""La part jouée du sonore en cours, en pour cent, que montre sa barre de progression ou sa frise."""
		self._shape_reading = QTimer(self)
		self._shape_reading.setInterval(SHAPE_READING)
		self._shape_reading.timeout.connect(self._read_off_shapes)
		self._show_hour()
		self._clock = QTimer(self)
		self._clock.setInterval(SECOND)
		self._clock.timeout.connect(self._show_hour)
		self._clock.start()
		self.show_state(PlaybackState("stopped"), reread=False)
		plays = self.refresh_airplay()
		if (len(plays) > 0) and (plays[0].end is None):
			self._known_play = plays[0].start
		self.state: PlaybackState = STOP
		"""Le dernier état reçu de Machin player."""
		# Le clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257).
		self.ui.next_frame.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.ui.next_frame.customContextMenuRequested.connect(self._next_menu)
		self.client = StateClient(state_socket, self)
		self.client.received_state.connect(self.show_state)
		self.client.open_connection()
		self.vu_meter = VuMeter(ui.vu_meter_place, vertical=True)
		arrangement = QVBoxLayout(ui.vu_meter_place)
		arrangement.setContentsMargins(0, 0, 0, 0)
		arrangement.addWidget(self.vu_meter)
		self.vu_meter.clicked.connect(self._listen)
		self.monitor = Monitor(audio, self)
		self.monitor.changed.connect(self._display_on_air)
		self.change_on_air(audio)

	def change_on_air(self, audio: Audio | None) -> None:
		"""Le VU-mètre lit le port de monitoring de cette antenne, par exemple après les préférences."""
		self.monitor.audio = audio
		tooltip = _("Unknown monitoring port.")
		if audio is not None:
			tooltip = _("Monitoring port: {port_name}. Click: listen to the on-air output on the pre-listen.").format(
				port_name=port_name(audio)
			)
		self.vu_meter.setToolTip(tooltip)
		self.monitor.start()

	def show_clipping(self, poster: bool) -> None:
		"""Le voyant « Saturation » de la colonne Antenne, affiché ou caché selon les préférences
		(https://github.com/dascritch/machincast/issues/191) ; le VU-mètre montre toujours les crêtes."""
		self.ui.clipping_light.setVisible(poster)

	def _listen(self) -> None:
		if self.monitor.unavailable is None:
			self.requested_listening.emit()

	def _display_on_air(self) -> None:
		ui, monitor = self.ui, self.monitor
		self.vu_meter.display(monitor.levels, monitor.peaks)
		ui.monitor_state.setText((monitor.unavailable) or (""))
		ui.monitor_state.setVisible(monitor.unavailable is not None)
		for light, lit, tint in (
			(ui.dead_air_light, monitor.dead_air, "#e0a020"),
			(ui.clipping_light, monitor.clipping, "#d03030"),
		):
			if light.property("allume") != lit:
				light.setProperty("allume", lit)
				style = OFF_LIGHT
				if lit:
					style = LIT_LIGHT.format(tint=tint)
				light.setStyleSheet(style)

	def closeEvent(self, event: QCloseEvent) -> None:
		self._clock.stop()
		self._shape_reading.stop()
		for shape in self._shapes.values():
			shape.halt()
		self.stream_trial.halt()
		self.client.shut_down()
		self.monitor.halt()
		super().closeEvent(event)

	def _show_hour(self) -> None:
		"""L'heure seule, à la seconde ; la date du jour en infobulle (demandé avec
		https://github.com/dascritch/machincast/issues/191)."""
		now = self.clock.now()
		self.ui.hour.setText(display.hour(now))
		self.ui.hour.setToolTip(long_date(now.astimezone().date()))

	# ─── État du binaire lecture ───────────────────────────

	def show_state(self, state: PlaybackState, reread: bool = True) -> None:
		self.state = state
		self.ui.playback_state.setText(STATES.get(state.state, state.state))
		self._ongoing, self._next = state.ongoing, state.next_
		self._show_sound("ongoing", state.ongoing)
		self._show_sound("next", state.next_)
		self._show_progress(state.ongoing)
		self._show_timeline(self.next_timeline, state.next_)
		self._forget_shapes()
		self._show_on_air(state.ongoing)
		self._show_upcoming(state.upcoming)
		next_ = state.next_
		self.ui.next_healthy.setText(display.EMPTY)
		if next_ is not None:
			self.ui.next_healthy.setText(display.yes_no(next_.healthy, _("not tested")))
		self._offer_listened(next_)
		start = None
		if state.ongoing is not None:
			start = state.ongoing.start
		if (reread) and (start != self._known_play):
			self._known_play = start
			self.refresh_airplay()

	def _show_sound(self, which: str, sound: DisplayedSound | None) -> None:
		"""Titre, événement, séquence, banque, horaire sur une ligne et emplacement d'un des deux sonores."""
		ui = self.ui
		fields = [getattr(ui, f"{which}_{name}") for name in ("title", "event", "sequence", "bank", "schedule")]
		title, event, sequence, bank, schedule = fields
		_show_location(getattr(ui, f"{which}_location"), sound)
		getattr(ui, f"open_{which}_sound").setEnabled(sound is not None)
		getattr(ui, f"open_{which}_event").setEnabled((sound is not None) and (sound.id_event is not None))
		getattr(ui, f"open_{which}_sequence").setEnabled((sound is not None) and (sound.sequence_id is not None))
		getattr(ui, f"open_{which}_bank").setEnabled((sound is not None) and (sound.id_bank is not None))
		if sound is None:
			for field in fields:
				field.setText(display.EMPTY)
			return
		title.setText(display.artist_and_title(sound.artist, sound.title))
		event.setText((sound.event) or (display.EMPTY))
		sequence.setText((sound.sequence) or (display.EMPTY))
		bank.setText((sound.bank) or (display.EMPTY))
		schedule.setText(_schedule(sound))

	def _show_progress(self, sound: DisplayedSound | None) -> None:
		"""Le temps qui reste au sonore en cours, plutôt qu'un pourcentage : sur la barre de progression d'un stream,
		au milieu de la frise d'un fichier, qui la remplace (https://github.com/dascritch/machincast/issues/230)."""
		text, value = _progress(sound)
		self.ongoing_progress = value
		file = (sound is not None) and (not sound.stream)
		bar = self.ui.ongoing_progress
		bar.setVisible(not file)
		bar.setValue(value)
		# Texte composé ici : les codes de format de Qt s'écrivent avec la notation %, que refuse socle.feature.
		bar.setFormat(text)
		# Pour un fichier, au milieu de sa frise ; vide pour un stream, qui garde sa barre.
		legend = ""
		if file:
			legend = text
		self.ongoing_timeline.show_legend(legend)
		self._show_timeline(self.ongoing_timeline, sound)

	# ─── Frises (https://github.com/dascritch/machincast/issues/230) ───

	def _show_timeline(self, timeline: Timeline, sound: DisplayedSound | None) -> None:
		"""La frise d'un fichier : son plan tel que la diffusion le joue, sa forme d'onde, et pour le sonore en cours,
		la tête de lecture, la position jouée comptée depuis le début détecté d'un sonore rogné. Rien pour un stream."""
		file = (sound is not None) and (not sound.stream) and (sound.location is not None)
		place = timeline.parentWidget()
		assert place is not None
		place.setVisible(file)
		if (sound is None) or (not file):
			timeline.display(None, None)
			timeline.show_shape(None)
			return
		plan = self._plan(sound)
		duration = sound.duration
		if plan is not None:
			duration = plan.duration
		if (timeline.plan is not plan) or (timeline.duration != duration):
			timeline.display(plan, duration)
		shape = self._shape(sound)
		if timeline.shape is not shape:
			timeline.show_shape(shape)
		if timeline is not self.ongoing_timeline:
			return
		head = sound.position
		# La position se compte depuis le début de la lecture, qui suit les silences et la position du fade-in.
		if (head is not None) and (plan is not None):
			head += plan.part()[0]
		timeline.put_head(head)

	def _plan(self, sound: DisplayedSound) -> Plan | None:
		"""Lu en base une fois par sonore et par banque ; une base injoignable laisse la frise sans plan."""
		key = (sound.sound, sound.id_bank)
		if key not in self._plans:
			try:
				self._plans[key] = read_plan(self.connection, sound.sound, sound.id_bank, preferences.crossfades())
			except psycopg.Error as error:
				log.error(_("unreadable plan of sound {sound}: {error}").format(sound=sound.sound, error=error))
				return None
		return self._plans[key]

	def _shape(self, sound: DisplayedSound) -> WaveShape:
		"""Calculée en tâche de fond une seule fois par sonore et fichier."""
		key = (sound.sound, str(sound.location))
		shape = self._shapes.get(key)
		if shape is None:
			shape = WaveShape(Path(str(sound.location)), sound.duration)
			self._shapes[key] = shape
			shape.start()
			self._shape_reading.start()
		return shape

	def _forget_shapes(self) -> None:
		"""Seules restent les formes et les plans des deux sonores montrés ; un calcul en cours d'un autre s'arrête."""
		kept_list = {timeline.shape for timeline in (self.ongoing_timeline, self.next_timeline)}
		for file, shape in list(self._shapes.items()):
			if shape not in kept_list:
				shape.halt()
				del self._shapes[file]
		plans = {(sound.sound, sound.id_bank) for sound in (self._ongoing, self._next) if sound is not None}
		for forgotten in [key for key in self._plans if key not in plans]:
			del self._plans[forgotten]

	def _read_off_shapes(self) -> None:
		for shape in self._shapes.values():
			if shape.read_off():
				for timeline in (self.ongoing_timeline, self.next_timeline):
					if timeline.shape is shape:
						timeline.update()
		if all(shape.finished for shape in self._shapes.values()):
			self._shape_reading.stop()

	def _show_on_air(self, sound: DisplayedSound | None) -> None:
		"""Le texte public entre guillemets, et l'événement à l'antenne avec ses heures."""
		ui = self.ui
		ui.public_text.setText(display.EMPTY)
		ui.on_air_event.setText(display.EMPTY)
		if sound is None:
			return
		if sound.public_text:
			ui.public_text.setText(_("“{text}”").format(text=sound.public_text))
		if sound.event is not None:
			ui.on_air_event.setText(f"{sound.event}, {_event_hours(sound)}")

	def _open_sound(self, sound: DisplayedSound | None) -> None:
		if sound is not None:
			self.opened.emit("sonore", sound.sound, display.artist_and_title(sound.artist, sound.title))

	def _open_event(self, sound: DisplayedSound | None) -> None:
		if (sound is not None) and (sound.id_event is not None):
			self.opened.emit("événement", sound.id_event, str(sound.event))

	def _open_sequence(self, sound: DisplayedSound | None) -> None:
		if (sound is not None) and (sound.sequence_id is not None):
			self.opened.emit("séquence", sound.sequence_id, str(sound.sequence))

	def _open_bank(self, sound: DisplayedSound | None) -> None:
		if (sound is not None) and (sound.id_bank is not None):
			self.opened.emit("banque", sound.id_bank, str(sound.bank))

	def _open_cell(self, index: QModelIndex) -> None:
		"""Un double-clic sur une cellule qui désigne un élément demande sa fiche ; ailleurs, il ne fait rien."""
		item = index.data(ITEM)
		if item is not None:
			category, identifier, name = item
			self.opened.emit(category, identifier, name)

	def airplay_menu(self, index: QModelIndex) -> QMenu | None:
		"""Le menu du clic droit sur une ligne de l'airplay : « Pré-écoute… » de son sonore ; aucun hors d'une ligne,
		ou pour un sonore supprimé depuis (https://github.com/dascritch/machincast/issues/226)."""
		return self._line_menu(self.airplay_model, index)

	def upcoming_sound_menu(self, index: QModelIndex) -> QMenu | None:
		"""Le menu du clic droit sur une ligne des sonores à venir : « Pré-écoute… » de son sonore
		(https://github.com/dascritch/machincast/issues/228)."""
		return self._line_menu(self.upcoming_model, index)

	def _line_menu(self, model: QStandardItemModel, index: QModelIndex) -> QMenu | None:
		if not index.isValid():
			return None
		sound = None
		for column in range(model.columnCount()):
			item = model.index(index.row(), column).data(ITEM)
			if (item is not None) and (item[0] == "sonore"):
				sound = int(item[1])
		if sound is None:
			return None
		menu = QMenu(self)
		display.offer_preview(menu, sound, self.requested_preview.emit)
		return menu

	def next_menu(self) -> QMenu:
		"""Le menu du clic droit sur le prochain sonore : sa pré-écoute, y sauter aussitôt, et avancer l'événement
		suivant que Machin player annonce (https://github.com/dascritch/machincast/issues/257). Une entrée inactive dit
		pourquoi dans son infobulle."""
		menu = QMenu(self)
		menu.setToolTipsVisible(True)
		entries = interruption.offer_to_next(self.state)
		skip = menu.addAction(entries["sound"].text)
		skip.triggered.connect(lambda _ticked=False: self.requested_skip.emit())
		following = self.state.following_event
		advances = menu.addAction(entries["advance"].text)
		if following is not None:
			advances.triggered.connect(
				lambda _ticked=False, following=following: self.requested_advance.emit(following.id, following.name)
			)
		# Les coupures du menu « Diffusion » (https://github.com/dascritch/machincast/issues/323), avant l'avance.
		proposals = interruption.offer(self.state)
		for item in ("sequence", "event"):
			cutoff = menu.addAction(interruption.ENTRIES[item])
			cutoff.setEnabled(proposals[item].active)
			cutoff.setToolTip(proposals[item].tooltip)
			cutoff.triggered.connect(lambda _ticked=False, item=item: self.requested_interruption.emit(item))
		fallback = menu.addAction(interruption.CUT_BY_FALLBACK)
		interruption.fill_fallback(
			fallback, self.state, interruption.read_fallback(self.connection), self.requested_fallback.emit
		)
		fallback.triggered.connect(
			lambda _ticked=False: interruption.ask_fallback(fallback, self.requested_fallback.emit)
		)
		menu.addAction(advances)
		for action, entry in ((skip, entries["sound"]), (advances, entries["advance"])):
			action.setEnabled(entry.proposal.active)
			action.setToolTip(entry.proposal.tooltip)
		if self._next is not None:
			display.offer_preview(menu, self._next.sound, self.requested_preview.emit)
		return menu

	def _next_menu(self, position: QPoint) -> None:
		menu = self.next_menu()
		menu.exec(self.ui.next_frame.mapToGlobal(position))
		menu.deleteLater()

	# ─── Écouter le prochain sonore ────────────────────────

	def _offer_listened(self, next_: DisplayedSound | None) -> None:
		"""La pré-écoute, s'il y a un prochain sonore ; le test du flux, pour un stream. Un autre prochain sonore
		efface le résultat du test précédent."""
		ui = self.ui
		display.set_preview(ui.preview_next, next_ is not None, PREVIEW_NEXT)
		stream = (next_ is not None) and (next_.stream)
		ui.test_next_stream.setVisible(stream)
		ui.test_next_stream.setEnabled((stream) and (not self.stream_trial.ongoing()))
		sound = None if next_ is None else next_.sound
		if sound != self._tested_stream:
			self._tested_stream = None
			ui.next_stream.clear()
		ui.next_stream.setVisible(ui.next_stream.text() != "")

	def follow_preview(self) -> None:
		"""Le bouton « Pré-écoute » du prochain sonore suit la pré-écoute, désactivée sur la sortie factice
		(https://github.com/dascritch/machincast/issues/339)."""
		self._offer_listened(self._next)

	def _preview_next(self) -> None:
		if (self._next is not None) and (not display.disabled_preview()):
			self.requested_preview.emit(self._next.sound)

	def _test_next_stream(self) -> None:
		next_ = self._next
		if (next_ is None) or (next_.location is None):
			return
		self._tested_stream = next_.sound
		self.ui.test_next_stream.setEnabled(False)
		self.ui.next_stream.setText(ONGOING_TRIAL)
		self.ui.next_stream.setVisible(True)
		self.stream_trial.launch(next_.location)

	def _finished_stream_trial(self, answers: bool, detail: str) -> None:
		if self._tested_stream is not None:
			self.ui.next_stream.setText(trial_result(answers, detail))
		self._offer_listened(self._next)

	# ─── Sonores à venir ───────────────────────────────────

	def _show_upcoming(self, sounds: tuple[DisplayedSound, ...]) -> None:
		"""Les sonores à venir, le plus lointain en haut : le plus proche est juste au-dessus de l'airplay."""
		self.upcoming_model.setRowCount(0)
		for sound in reversed(sounds):
			cells = [QStandardItem(text) for text in _upcoming_cells(sound)]
			for column, item in _upcoming_items(sound).items():
				cells[column].setData(item, ITEM)
			self.upcoming_model.appendRow(cells)

	# ─── Airplay ───────────────────────────────────────────

	def refresh_airplay(self) -> list[DisplayedPlay]:
		"""Relit les DERNIERS passages de l'airplay (https://github.com/dascritch/machincast/issues/244) ; une base
		injoignable laisse la table telle qu'elle était. reread_airplay le dit, pour l'onglet Airplay."""
		try:
			plays = read_airplay(self.connection, count=LAST_LIST)
		except psycopg.Error as error:
			log.error(_("unreadable airplay: {error}").format(error=error))
			return []
		self.airplay_model.setRowCount(0)
		for play in plays:
			cells = [QStandardItem(text) for text in play_cells(play)]
			for column, item in play_items(play).items():
				cells[column].setData(item, ITEM)
			self.airplay_model.appendRow(cells)
		self.reread_airplay.emit()
		return plays


def _show_location(field: QLineEdit, sound: DisplayedSound | None) -> None:
	"""Chemin du fichier ou adresse du stream, dans un champ en lecture seule : un long chemin ne pousse pas la mise
	en page, sa fin (le nom du fichier) reste visible, et l'infobulle le donne en entier."""
	location = None
	if sound is not None:
		location = (sound.location) or (pgettext("masculine", "unknown"))
	field.setText((location) or (display.EMPTY))
	field.setToolTip((location) or (""))


def play_cells(play: DisplayedPlay) -> list[str]:
	end = _("ongoing")
	duration = ""
	if play.end is not None:
		end = display.hour(play.end)
		duration = display.duration(play.duration)
	return [
		display.hour(play.start),
		end,
		duration,
		(play.artist) or (""),
		(play.title) or (""),
		(play.event) or (""),
		(play.sequence) or (""),
		(play.bank) or (""),
		INCIDENT if play.without_incident is False else "",
	]


def play_items(play: DisplayedPlay) -> dict[int, tuple[str, int, str]]:
	"""Les cellules qui désignent un élément, par colonne : artiste et titre le sonore, puis événement, séquence et
	banque ; un élément supprimé depuis n'en désigne plus."""
	items: dict[int, tuple[str, int, str]] = {}
	if play.id_sound is not None:
		title = (play.title) or (display.artist_and_title(play.artist, play.title))
		items[3] = items[4] = ("sonore", play.id_sound, title)
	for column, category, identifier, name in (
		(5, "événement", play.id_event, play.event),
		(6, "séquence", play.sequence_id, play.sequence),
		(7, "banque", play.id_bank, play.bank),
	):
		if identifier is not None:
			items[column] = (category, identifier, str(name))
	return items


def _upcoming_cells(sound: DisplayedSound) -> list[str]:
	"""Les colonnes de l'airplay, pour un sonore à venir : son début et sa fin estimés, sa durée."""
	duration = ""
	if sound.duration is not None:
		duration = display.duration(sound.duration)
	return [
		display.hour(sound.start, ""),
		display.hour(sound.estimated_end, ""),
		duration,
		(sound.artist) or (""),
		(sound.title) or (""),
		(sound.event) or (""),
		(sound.sequence) or (""),
		(sound.bank) or (""),
		NOT_HEALTHY if sound.healthy is False else "",
	]


def _upcoming_items(sound: DisplayedSound) -> dict[int, tuple[str, int, str]]:
	"""Les cellules qui désignent un élément, par colonne, comme dans l'airplay."""
	title = (sound.title) or (display.artist_and_title(sound.artist, sound.title))
	items: dict[int, tuple[str, int, str]] = {
		3: ("sonore", sound.sound, title),
		4: ("sonore", sound.sound, title),
	}
	for column, category, identifier, name in (
		(5, "événement", sound.id_event, sound.event),
		(6, "séquence", sound.sequence_id, sound.sequence),
		(7, "banque", sound.id_bank, sound.bank),
	):
		if identifier is not None:
			items[column] = (category, identifier, str(name))
	return items


def _schedule(sound: DisplayedSound) -> str:
	"""« 20:00:00 – 20:03:34 (3:34) » : début, fin et durée sur une ligne ; « 20:00:00, durée inconnue » sans durée.
	Un sonore qu'un événement coupera finit à la coupure : « 20:00:00 – 20:02:00 (coupé par « Journal », sur 3:34) »
	(https://github.com/dascritch/machincast/issues/169)."""
	start = display.hour(sound.start, pgettext("masculine", "unknown"))
	if sound.cut_by is not None:
		duration = _("unknown duration")
		if sound.duration is not None:
			duration = _("out of {duration}").format(duration=display.duration(sound.duration))
		return _("{start} – {hour} (cut by “{cut_by}”, {duration})").format(
			start=start, hour=display.hour(sound.estimated_end), cut_by=sound.cut_by, duration=duration
		)
	if (sound.duration is None) and (sound.estimated_end is not None):
		# Un stream finit avec son événement (https://github.com/dascritch/machincast/issues/242).
		return _("{start} – {hour} (end of the event)").format(start=start, hour=display.hour(sound.estimated_end))
	if sound.duration is None:
		return _("{start}, unknown duration").format(start=start)
	return f"{start} – {display.hour(sound.estimated_end)} ({display.duration(sound.duration)})"


def _set_timeline(place: QWidget) -> Timeline:
	timeline = Timeline(place, interactive=False)
	arrangement = QVBoxLayout(place)
	arrangement.setContentsMargins(0, 0, 0, 0)
	arrangement.addWidget(timeline)
	return timeline


def _progress(sound: DisplayedSound | None) -> tuple[str, int]:
	"""Le temps qui reste au sonore en cours, et la part jouée en pour cent : « — » sans sonore, « durée inconnue »
	sans fin estimée. Un sonore qui dépasse sa durée est à 100 %."""
	if sound is None:
		return display.EMPTY, 0
	length = _length(sound)
	if (length is None) or (sound.position is None):
		return _("unknown duration"), 0
	value = 100
	if length > 0:
		value = min(100, round(sound.position / length * 100))
	# Le temps qui reste se compte à la seconde entamée : « reste 0:01 » jusqu'à la fin, puis « reste 0:00 ».
	rest = math.ceil(max(0.0, length - sound.position))
	text = _("{duration} left").format(duration=display.duration(rest))
	if sound.cut_by is not None:
		text = _("{text} before “{cut_by}”").format(text=text, cut_by=sound.cut_by)
	return text, value


def _length(sound: DisplayedSound) -> float | None:
	"""Combien de secondes le sonore passera, de son début à sa fin estimée : sa durée, ou jusqu'à la coupure annoncée ;
	None sans fin estimée, pour un stream que rien ne coupera."""
	if (sound.start is None) or (sound.estimated_end is None):
		return None
	return (sound.estimated_end - sound.start).total_seconds()


def _event_hours(sound: DisplayedSound) -> str:
	"""« de 20:00 à 22:00 », « depuis 19:00 » pour une occurrence sans fin, « permanent » pour un fil musical."""
	start, end = sound.start_event, sound.end_event
	if start is None:
		return "permanent"
	if end is None:
		return _("since {start:%H:%M}").format(start=start)
	return _("from {start:%H:%M} to {end:%H:%M}").format(start=start, end=end)
