"""Pré-écoute d'un sonore (https://github.com/dascritch/machincast/issues/116,
https://github.com/dascritch/machincast/issues/29, spec § 8.3).

Une fenêtre indépendante, une seule pour toute l'interface (MainWindow.preecoute) : la fiche d'un sonore
y envoie son sonore, qui remplace le précédent, à l'arrêt ; le menu « Affichage » l'ouvre sans sonore, pour choisir
sa sortie. Son lecteur est un pipeline playbin3 de GStreamer (machincast.audio.PLAYER), dont le bus est relevé par
un minuteur de Qt : rien ne bloque l'interface.

- Sortie : le périphérique de pré-écoute de la configuration (audio.preview), sur la sortie de l'antenne
  (audio.output), jamais le périphérique de l'antenne. Le choix liste les périphériques du poste (peripheriques), celui
  de l'antenne grisé ; un périphérique configuré mais absent reste proposé. Le choix s'enregistre dans le fichier de
  configuration (write_preview), qui garde ses commentaires, et arrête la lecture en cours.
- Lecteur : lecture et pause, arrêt, qui ramène au début. La fin du fichier ramène à l'arrêt ; une erreur aussi, et
  elle est signalée.
- Frise d'un fichier (machincast.interface.timeline, https://github.com/dascritch/machincast/issues/224) : elle tient
  lieu de barre de position, pendant la lecture ou sa pause, et montre sa forme d'onde, calculée en tâche de fond à
  l'ouverture, ses silences et ses crossfades enregistrés, et la partie jouée à l'antenne. « Début joué » et « Fin
  jouée » y placent la lecture, en la lançant au besoin. Écouté comme à l'antenne, le fichier n'est joué que de sa
  partie jouée, au volume de l'enveloppe de la diffusion, réglé à chaque relève : il commence au début de la partie
  jouée, et s'arrête à sa fin. Un stream n'a ni frise ni barre de position.
- VU-mètre : le niveau RMS de chaque canal, par l'élément level de GStreamer, en décibels.
- Informations : format (codec), débit (celui des tags, sinon la taille du fichier sur sa durée), échantillonnage,
  canaux, et pour un stream, les secondes pré-décodées : le son reçu d'avance, que GStreamer garde en mémoire.

L'écoute de l'antenne (https://github.com/dascritch/machincast/issues/24), par le VU-mètre de l'onglet Antenne ou le
bouton « Pré-écoute » de la fenêtre, a pour titre « en cours : » et le texte public du sonore en cours
(https://github.com/dascritch/machincast/issues/223).
"""

import logging
import math
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import gi
import psycopg
import tomlkit
from psycopg.rows import TupleRow

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PySide6.QtCore import Qt, QTimer, Signal  # noqa: E402
from PySide6.QtGui import QCloseEvent, QStandardItemModel  # noqa: E402
from PySide6.QtWidgets import QVBoxLayout, QWidget  # noqa: E402

from machincast import audio as audio_outputs  # noqa: E402
from machincast.audio import PLAYER, PREVIEW, create_output  # noqa: E402
from machincast.configuration import Audio, AudioOutput, Crossfades  # noqa: E402
from machincast.i18n import _, decimal  # noqa: E402
from machincast.interface import binding, display, preferences, states  # noqa: E402
from machincast.interface.monitor import Unavailable, monitor_source, port_name  # noqa: E402
from machincast.interface.timeline import Plan, Timeline, WaveShape, sound_plan  # noqa: E402
from machincast.interface.ui.preview import Ui_PreviewWindow  # noqa: E402
from machincast.interface.vu_meter import VuMeter  # noqa: E402

READING = 50
"""Millisecondes entre deux relèves du bus et de l'affichage."""
LEVEL_INTERVAL = 50 * Gst.MSECOND
STREAM_BUFFER = 5
"""Secondes de son qu'un stream reçoit d'avance : le pré-décodé en est la part remplie."""
STATES = {"stopped": _("Stopped"), "playing": _("Playing"), "paused": _("Paused")}
NO = _("No sound")
CHANNELS = {1: "mono", 2: _("stereo")}
BROADCAST = _("(broadcast)")
"""Ce qui suit, grisé dans le choix de sortie, le nom du périphérique de la diffusion."""
PLAYBACK = ("⏵", _("Play"))
PAUSE = ("⏸", _("Pause"))
"""Le symbole du bouton, et son infobulle, qui le nomme aussi pour les technologies d'assistance ; l'arrêt est « ⏹ »."""

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Source:
	"""Ce que la pré-écoute joue."""

	title: str
	address: str
	"""Chemin du fichier, ou adresse du stream."""
	stream: bool
	duration: float | None
	"""Durée en base, en secondes, montrée avant la lecture."""
	on_air: Audio | None = None
	"""L'antenne, écoutée sur son port de monitoring (https://github.com/dascritch/machincast/issues/24) ; None pour
	un sonore."""
	plan: Plan | None = None
	"""Ce que l'antenne fera d'un fichier de durée connue, montré par sa frise
	(https://github.com/dascritch/machincast/issues/224) ; None pour un stream, ou sans durée."""


def write_preview(path: Path, identifier: str) -> None:
	"""audio.preview dans le fichier de configuration, qui garde ses commentaires et ses autres réglages."""
	document = tomlkit.parse(path.read_text(encoding="utf-8"))
	preferences.write_audio(document, None, None, identifier)
	path.write_text(tomlkit.dumps(document), encoding="utf-8")


def read_source(
	connection: psycopg.Connection[TupleRow], sound: int, defects: Crossfades | None = None
) -> Source | None:
	"""Le fichier ou l'adresse du sonore, ce qui le nomme, et pour un fichier, le plan de sa frise, ses crossfades non
	paramétrés pris dans defauts ; None s'il n'est plus en base."""
	with connection.transaction():
		line = connection.execute(
			"SELECT s.type::text, s.location, coalesce(s.stream_url, m.url), s.artist, s.title,"
			" extract(epoch FROM s.duration), s.duration, s.detected_start, s.detected_end, s.silence_detection,"
			" s.crossfade_start, s.crossfade_end, s.audited_at IS NOT NULL"
			" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
			(sound,),
		).fetchone()
	if line is None:
		return None
	sound_type, location, url, artist, title, duration, interval, *details = line
	stream = sound_type == "stream"
	address = str((location) or (""))
	if stream:
		address = str((url) or (""))
	name = display.sound_name(artist, title, location, url)
	seconds = None
	if duration is not None:
		seconds = float(str(duration))
	plan = None
	if (not stream) and (isinstance(interval, timedelta)):
		detected_start, detected_end, detection, start_crossfade, end_crossfade, audited = details
		plan = sound_plan(
			interval,
			_interval(detected_start),
			_interval(detected_end),
			bool(detection),
			_interval(start_crossfade),
			_interval(end_crossfade),
			(defects) or (Crossfades()),
			bool(audited),
		)
	return Source(name, address, stream, seconds, plan=plan)


def _interval(value: object) -> timedelta | None:
	if isinstance(value, timedelta):
		return value
	return None


class Player:
	"""Le pipeline de la pré-écoute : un seul sonore à la fois, sur le périphérique de pré-écoute."""

	def __init__(self, output: AudioOutput, device: str) -> None:
		Gst.init(None)
		self.output = output
		self.device = device
		self.source: Source | None = None
		self._pipeline: Gst.Element | None = None
		self._piloted: states.Pilot | None = None
		"""Les changements d'état du pipeline, hors du fil de l'interface (https://github.com/dascritch/machincast/issues/259)."""
		self._level: Gst.Element | None = None
		self._links: list[binding.Pair] = []
		"""Les liens de PipeWire qui copient l'antenne sur la pré-écoute, tant qu'elle joue."""
		self.state = "stopped"
		self.levels: list[float] = []
		"""Niveau RMS de chaque canal, en décibels ; vide à l'arrêt."""
		self.error: str | None = None
		self.codec: str | None = None
		self.bitrate: int | None = None
		"""Débit annoncé par les tags, en bits par seconde."""
		self.frequency: int | None = None
		self.channels: int | None = None
		self.as_on_air = False
		"""Ne jouer que la partie jouée à l'antenne, au volume de ses fondus
		(https://github.com/dascritch/machincast/issues/224)."""
		self.volume = 1.0
		"""Volume de la lecture, de 0 à 1 : plein, sauf écouté comme à l'antenne."""
		self.last_position: float | None = None
		"""La dernière position relevée pendant la lecture, gardée après l'arrêt."""

	def load(self, source: Source | None) -> None:
		self.halt()
		self.last_position = None
		self.source = source
		# Dans le journal, que l'achèvement d'un rapport de crash reprend
		# (https://github.com/dascritch/machincast/issues/413).
		if source is not None:
			log.info(_("pre-listen: {title} ({address})").format(title=source.title, address=source.address))
		self.error = None
		self.codec, self.bitrate, self.frequency, self.channels = None, None, None, None

	def change_output(self, device: str) -> None:
		self.halt()
		self.device = device

	def active(self) -> bool:
		return self._pipeline is not None

	def read(self) -> None:
		if self.source is None:
			return
		if (not self.source.stream) and (not Path(self.source.address).is_file()):
			self.error = _("file not found, {address}").format(address=self.source.address)
			return
		since_start = self._pipeline is None
		if self._pipeline is None:
			self.error = None
			try:
				self._pipeline = self._build(self.source)
			except Unavailable as error:
				self.error = str(error)
				return
			self._piloted = states.Pilot(self._pipeline)
		plan = self._on_air_plan()
		if plan is not None:
			self._set_volume(plan.volume(plan.start_marker()))
		assert self._piloted is not None
		self._piloted.to(Gst.State.PLAYING)
		self.state = "playing"
		if (plan is not None) and (since_start):
			self.put_to(plan.start_marker())
		on_air = self._on_air_by_pipewire(self.source.on_air)
		if (on_air is not None) and (not self._links):
			try:
				self._links = binding.pairs(on_air, self.device)
				binding.link(self._links)
			except binding.ImpossibleBinding as error:
				self.halt()
				self.error = str(error)

	def pause(self) -> None:
		if self._piloted is not None:
			self._piloted.to(Gst.State.PAUSED)
			self.state = "paused"
		self._unbind()

	def halt(self) -> None:
		self._unbind()
		if self._piloted is not None:
			self._piloted.switch_off()
		self._pipeline, self._piloted, self._level = None, None, None
		self.state = "stopped"
		self.levels = []

	def _unbind(self) -> None:
		binding.unbind(self._links)
		self._links = []

	def _on_air_by_pipewire(self, on_air: Audio | None) -> str | None:
		"""Le périphérique de l'antenne, quand elle s'écoute par un lien de PipeWire : sur la sortie pipewire, qui est
		aussi celle de la pré-écoute."""
		if (on_air is None) or (on_air.on_air()[0] != "pipewire"):
			return None
		return on_air.on_air()[1]

	def put_to(self, position: float) -> None:
		"""Va à cette position du fichier, en secondes ; écouté comme à l'antenne, dans sa partie jouée."""
		duration = self.duration()
		if (self._pipeline is None) or (duration is None):
			return
		plan = self._on_air_plan()
		if plan is not None:
			de, a = plan.part()
			position = max(de, min(a, position))
		instant = round(max(0.0, min(duration, position)) * Gst.SECOND)
		# Un déplacement demandé pendant un changement d'état (une pause qui s'installe) serait perdu : il attend sa
		# fin, une demi-seconde au plus, après que son pilote l'a demandé, une demi-seconde au plus.
		if self._piloted is not None:
			self._piloted.wait(0.5)
		self._pipeline.get_state(Gst.SECOND // 2)
		self._pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE, instant)

	def position(self) -> float | None:
		if self._pipeline is None:
			return None
		found, position = self._pipeline.query_position(Gst.Format.TIME)
		if not found:
			return None
		return position / Gst.SECOND

	def duration(self) -> float | None:
		"""Durée du fichier selon GStreamer, sinon celle de la base ; aucune pour un stream."""
		if (self.source is None) or (self.source.stream):
			return None
		if self._pipeline is not None:
			found, duration = self._pipeline.query_duration(Gst.Format.TIME)
			if (found) and (duration > 0):
				return duration / Gst.SECOND
		return self.source.duration

	def predecoded(self) -> float | None:
		"""Secondes de son reçues d'avance par un stream, d'après le remplissage de son tampon ; None pour un fichier,
		ou si GStreamer ne le dit pas."""
		if (self._pipeline is None) or (self.source is None) or (not self.source.stream):
			return None
		query = Gst.Query.new_buffering(Gst.Format.TIME)
		if not self._pipeline.query(query):
			return None
		_busy, percentage = query.parse_buffering_percent()
		return percentage / 100 * STREAM_BUFFER

	def bitrate_in_kbits(self) -> str | None:
		"""« 320 kbit/s » des tags, sinon « ≈ 705 kbit/s » d'après la taille du fichier sur sa durée."""
		if self.bitrate is not None:
			return f"{round(self.bitrate / 1000)} kbit/s"
		duration = self.duration()
		if (self.source is None) or (self.source.stream) or (not duration):
			return None
		try:
			size = Path(self.source.address).stat().st_size
		except OSError:
			return None
		return f"≈ {round(size * 8 / duration / 1000)} kbit/s"

	def read_off(self) -> None:
		"""Les messages de GStreamer : niveaux, tags, fin et erreurs."""
		pipeline = self._pipeline
		if pipeline is None:
			return
		bus = pipeline.get_bus()
		assert bus is not None
		while (message := bus.pop()) is not None:
			if message.type == Gst.MessageType.EOS:
				self.halt()
				return
			if message.type == Gst.MessageType.ERROR:
				error, _detail = message.parse_error()
				self.halt()
				self.error = str(error.message)
				return
			if message.type == Gst.MessageType.TAG:
				self._read_tags(message.parse_tag())
			if (message.type == Gst.MessageType.ELEMENT) and (message.src == self._level):
				self._read_levels(message.get_structure())
		self._read_format()
		self._follow_played_part()

	def _on_air_plan(self) -> Plan | None:
		"""Le plan du fichier, s'il est écouté comme à l'antenne ; None sinon."""
		if (not self.as_on_air) or (self.source is None) or (self.source.on_air is not None):
			return None
		return self.source.plan

	def _set_volume(self, volume: float) -> None:
		self.volume = volume
		if (self._pipeline is not None) and (self.source is not None) and (self.source.on_air is None):
			self._pipeline.set_property("volume", volume)

	def _follow_played_part(self) -> None:
		"""Note la position ; écouté comme à l'antenne, règle le volume de l'enveloppe, et s'arrête à la fin de la
		partie jouée. Sinon, le volume est plein."""
		position = self.position()
		if (self.state == "playing") and (position is not None):
			self.last_position = position
		plan = self._on_air_plan()
		if plan is None:
			if self.volume != 1.0:
				self._set_volume(1.0)
			return
		if (position is None) or (self.state != "playing"):
			return
		_de, a = plan.part()
		if (a < plan.duration) and (position >= a):
			self.halt()
			return
		self._set_volume(plan.volume(position))

	def _build(self, source: Source) -> Gst.Element:
		if source.on_air is not None:
			return self._build_listening(source.on_air)
		player = Gst.ElementFactory.make(PLAYER, None)
		level = Gst.ElementFactory.make("level", None)
		assert (player is not None) and (level is not None), _("install gstreamer1.0-plugins-base and -good")
		level.set_property("interval", LEVEL_INTERVAL)
		level.set_property("post-messages", True)
		output = create_output(self.output, self.device, presentation=PREVIEW)
		if self.output == "dummy":
			# La sortie factice joue au rythme du temps réel, comme un vrai périphérique.
			output.set_property("sync", True)
		player.set_property("audio-filter", level)
		player.set_property("audio-sink", output)
		address = source.address
		if source.stream:
			player.set_property("buffer-duration", STREAM_BUFFER * Gst.SECOND)
		else:
			address = str(Gst.filename_to_uri(address))
		player.set_property("uri", address)
		self._level = level
		return player

	def _build_listening(self, on_air: Audio) -> Gst.Element:
		"""Le port de monitoring de l'antenne, joué sur la sortie de pré-écoute. Sous PipeWire, le son passe par un
		lien (machincast.interface.binding) : le pipeline ne fait que mesurer, pour le VU-mètre."""
		pipeline = Gst.Pipeline.new("ecoute-antenne")
		output = Gst.ElementFactory.make("fakesink", None)
		assert output is not None
		output.set_property("sync", False)
		if self._on_air_by_pipewire(on_air) is None:
			output = create_output(self.output, self.device, presentation=PREVIEW)
		created_list = [
			monitor_source(on_air),
			Gst.ElementFactory.make("audioconvert", None),
			Gst.ElementFactory.make("audioresample", None),
			Gst.ElementFactory.make("level", None),
			output,
		]
		# ElementFactory.make rend None pour un élément introuvable : pygobject-stubs le type ainsi depuis sa
		# version 2.19, et mypy refuse alors de l'ajouter au pipeline sans l'avoir écarté.
		items = [item for item in created_list if item is not None]
		assert len(items) == len(created_list), _("install gstreamer1.0-plugins-base and -good")
		level = items[3]
		level.set_property("interval", LEVEL_INTERVAL)
		level.set_property("post-messages", True)
		for item in items:
			pipeline.add(item)
		for before, after in zip(items, items[1:], strict=False):
			before.link(after)
		self._level = level
		return pipeline

	def _read_tags(self, tags: Gst.TagList) -> None:
		found, codec = tags.get_string(Gst.TAG_AUDIO_CODEC)
		if found:
			self.codec = codec
		for name in (Gst.TAG_BITRATE, Gst.TAG_NOMINAL_BITRATE):
			found, bitrate = tags.get_uint(name)
			if (found) and (bitrate > 0):
				self.bitrate = int(bitrate)
				return

	def _read_levels(self, structure: Gst.Structure | None) -> None:
		if (structure is None) or (structure.get_name() != "level"):
			return
		values = structure.get_value("rms")
		if values is not None:
			self.levels = [float(value) for value in values]

	def _read_format(self) -> None:
		if (self._level is None) or ((self.frequency is not None) and (self.channels is not None)):
			return
		entry = self._level.get_static_pad("sink")
		caps = None
		if entry is not None:
			caps = entry.get_current_caps()
		if (caps is None) or (caps.get_size() == 0):
			return
		structure = caps.get_structure(0)
		found, frequency = structure.get_int("rate")
		if found:
			self.frequency = frequency
		found_list, channels = structure.get_int("channels")
		if found_list:
			self.channels = channels


ONGOING = _("ongoing: ")
"""Début du titre de l'écoute de l'antenne, suivi du texte public du sonore en cours."""


class PreviewWindow(QWidget):
	"""La fenêtre de pré-écoute : indépendante, elle ne se ferme pas avec la fiche qui l'a ouverte. L'interface l'ouvre
	sans fenêtre parente, comme une fenêtre à part (https://github.com/dascritch/machincast/issues/325)."""

	changed_listening = Signal(bool)
	"""L'écoute de l'antenne commence (vrai) ou cesse (faux) : lecture lancée, arrêtée, fenêtre fermée ou autre
	sonore (https://github.com/dascritch/machincast/issues/256)."""

	def __init__(
		self,
		connection: psycopg.Connection[TupleRow],
		audio: Audio,
		configuration: Path | None = None,
		parent: QWidget | None = None,
	) -> None:
		super().__init__(parent, Qt.WindowType.Window)
		self.connection = connection
		self.audio = audio
		self.configuration = configuration
		self.ui = Ui_PreviewWindow()
		self.ui.setupUi(self)
		self.vu_meter = VuMeter(self.ui.vu_meter_place)
		self.ui.vu_meter_place.setMinimumHeight(48)
		self.ui.vu_meter_place.setMaximumHeight(56)
		arrangement = QVBoxLayout(self.ui.vu_meter_place)
		arrangement.setContentsMargins(0, 0, 0, 0)
		arrangement.addWidget(self.vu_meter)
		self.timeline = Timeline(self.ui.timeline_place)
		timeline_layout = QVBoxLayout(self.ui.timeline_place)
		timeline_layout.setContentsMargins(0, 0, 0, 0)
		timeline_layout.addWidget(self.timeline)
		self.shape: WaveShape | None = None
		"""La forme d'onde du fichier, calculée en tâche de fond (https://github.com/dascritch/machincast/issues/224)."""
		self.player = Player(audio.output, audio.preview)
		self._fill_outputs()
		self.ui.output.currentIndexChanged.connect(self._change_output)
		self.ui.playback.clicked.connect(self._play_or_pause)
		self.ui.stop.clicked.connect(self._halt)
		self.timeline.placed.connect(self._put)
		self.ui.played_start.clicked.connect(lambda: self._go_to_marker(start=True))
		self.ui.played_end.clicked.connect(lambda: self._go_to_marker(start=False))
		self.ui.as_on_air.toggled.connect(self._listen_as_on_air)
		self._reading = QTimer(self)
		self._reading.setInterval(READING)
		self._reading.timeout.connect(self._refresh)
		self._reading.start()
		self.on_air = False
		"""La fenêtre écoute l'antenne : son titre suit le texte public du sonore en cours."""
		self._announced_listening = False
		self.preview(None)

	def on_air_listening(self) -> bool:
		"""L'antenne est chargée, et sa lecture lancée, ou en pause."""
		return (self.on_air) and (self.player.active())

	def halt(self) -> None:
		"""Arrête la lecture, comme le bouton « ⏹ »."""
		self._halt()

	def preview(self, sound: int | None) -> None:
		"""Le sonore à pré-écouter, à l'arrêt, à la place du précédent ; None : aucun."""
		self.on_air = False
		source = None
		if sound is not None:
			source = read_source(self.connection, sound, preferences.crossfades())
		self.player.load(source)
		self._show_timeline(source)
		self.setWindowTitle(_("Pre-listen"))
		self.ui.source.setText(display.EMPTY)
		if source is not None:
			self.setWindowTitle(_("Pre-listen: {title}").format(title=source.title))
			self.ui.source.setText(source.address)
		self.ui.message.clear()
		self._refresh()

	def listen_on_air(self, public_text: str | None, launch: bool = False) -> None:
		"""L'antenne, sur son port de monitoring, à la place du sonore précédent : à l'arrêt, ou lancée aussitôt. Le
		titre de la fenêtre est « en cours : » et le texte public du sonore en cours
		(https://github.com/dascritch/machincast/issues/223)."""
		name = port_name(self.audio)
		source = Source(_("On air"), _("On air: {name}").format(name=name), True, None, self.audio)
		self.player.load(source)
		self._show_timeline(source)
		self.on_air = True
		self.follow_on_air(public_text)
		self.ui.source.setText(_("On air: {name}").format(name=name))
		self.ui.message.clear()
		if launch:
			self._play_or_pause()
		self._refresh()

	def follow_on_air(self, public_text: str | None) -> None:
		"""Le texte public du sonore en cours a changé : le titre le suit, tant que la fenêtre écoute l'antenne."""
		if self.on_air:
			self.setWindowTitle(f"{ONGOING}{(public_text) or (display.EMPTY)}")

	def _show_timeline(self, source: Source | None) -> None:
		"""La frise d'un fichier, et le calcul de sa forme d'onde, lancé en tâche de fond ; rien pour un stream."""
		self._halt_shape()
		file = (source is not None) and (not source.stream)
		self.ui.timeline_area.setVisible(file)
		plan = None
		duration = None
		if (source is not None) and (file):
			plan, duration = source.plan, source.duration
			self.shape = WaveShape(Path(source.address), duration)
			self.shape.start()
		self.timeline.display(plan, duration)
		self.timeline.show_shape(self.shape)
		summary = ""
		if plan is not None:
			summary = plan.summary()
		self.ui.range_.setText(summary)
		for command in (self.ui.played_start, self.ui.played_end, self.ui.as_on_air):
			command.setEnabled(plan is not None)

	def _halt_shape(self) -> None:
		if self.shape is not None:
			self.shape.halt()
		self.shape = None

	def closeEvent(self, event: QCloseEvent) -> None:
		self._halt_shape()
		self.player.halt()
		self._refresh()
		super().closeEvent(event)

	def _fill_outputs(self) -> None:
		"""Le périphérique configuré d'abord, puis les autres du poste, dans leur ordre. Celui de la diffusion y est,
		grisé : il ne peut pas être choisi."""
		choice = self.ui.output
		found_list = audio_outputs.devices(self.audio.output)
		configured = next((p for p in found_list if p.identifier == self.audio.preview), None)
		name = _("{device} (not found)").format(device=self.audio.preview)
		if configured is not None:
			name = configured.name
		choice.addItem(name, self.audio.preview)
		model = choice.model()
		assert isinstance(model, QStandardItemModel)
		for device in found_list:
			if device.identifier == self.audio.preview:
				continue
			if device.identifier != self.audio.device:
				choice.addItem(device.name, device.identifier)
				continue
			choice.addItem(f"{device.name} {BROADCAST}", device.identifier)
			line = model.item(choice.count() - 1)
			line.setEnabled(False)
			line.setToolTip(_("The broadcast device cannot be used for the pre-listen."))

	def _change_output(self) -> None:
		identifier = str(self.ui.output.currentData())
		if identifier == self.audio.device:
			# Jamais la sortie de la diffusion, même choisie autrement qu'à la souris : retour à la précédente.
			self.ui.output.setCurrentIndex(self.ui.output.findData(self.player.device))
			self.ui.message.setText(_("The broadcast device cannot be used for the pre-listen."))
			return
		self.player.change_output(identifier)
		text = _("Pre-listen output changed for this session.")
		if self.configuration is not None:
			try:
				write_preview(self.configuration, identifier)
			except OSError as error:
				text = _("Pre-listen output not saved in {configuration}: {error}").format(
					configuration=self.configuration, error=error
				)
			else:
				text = _("Pre-listen output saved in {configuration}.").format(configuration=self.configuration)
		self.ui.message.setText(text)
		self._refresh()

	def _play_or_pause(self) -> None:
		if self.player.state == "playing":
			self.player.pause()
		else:
			self.ui.message.clear()
			self.player.read()
		self._refresh()

	def _halt(self) -> None:
		self.player.halt()
		self._refresh()

	def _put(self, position: float) -> None:
		self.player.put_to(position)
		self._refresh()

	def _go_to_marker(self, start: bool) -> None:
		"""« Début joué » ou « Fin jouée » : la lecture y va, lancée au besoin."""
		source = self.player.source
		if (source is None) or (source.plan is None):
			return
		marker = source.plan.end_marker()
		if start:
			marker = source.plan.start_marker()
		if self.player.state != "playing":
			self.ui.message.clear()
			self.player.read()
		self.player.put_to(marker)
		self._refresh()

	def _listen_as_on_air(self, ticked: bool) -> None:
		self.player.as_on_air = ticked
		self._refresh()

	def _refresh(self) -> None:
		player = self.player
		player.read_off()
		if self.on_air_listening() != self._announced_listening:
			self._announced_listening = self.on_air_listening()
			self.changed_listening.emit(self._announced_listening)
		ui = self.ui
		source = player.source
		if player.error is not None:
			ui.message.setText(_("Playback impossible: {error}").format(error=player.error))
		ui.state.setText(STATES[player.state])
		if source is None:
			ui.state.setText(NO)
		ui.playback.setEnabled(source is not None)
		button = PLAYBACK
		if player.state == "playing":
			button = PAUSE
		ui.playback.setText(button[0])
		ui.playback.setToolTip(button[1])
		ui.playback.setAccessibleName(button[1])
		ui.stop.setEnabled(player.active())
		duration = player.duration()
		self.timeline.setEnabled((player.active()) and (duration is not None))
		ui.time.setText(self._time(duration))
		head = None
		if player.active():
			head = player.position()
		self.timeline.put_head(head)
		if (self.shape is not None) and (self.shape.read_off()):
			self.timeline.update()
		self.vu_meter.display(player.levels)
		ui.format.setText((player.codec) or (display.EMPTY))
		ui.bitrate.setText((player.bitrate_in_kbits()) or (display.EMPTY))
		ui.sampling.setText(display.EMPTY)
		if player.frequency is not None:
			ui.sampling.setText(f"{player.frequency:,} Hz".replace(",", " "))
		ui.channels.setText(display.EMPTY)
		if player.channels is not None:
			ui.channels.setText(
				CHANNELS.get(player.channels, _("{channels} channels").format(channels=player.channels))
			)
		ui.predecoded.setText(display.EMPTY)
		predecoded = player.predecoded()
		if predecoded is not None:
			ui.predecoded.setText(decimal(f"{predecoded:.1f} s"))

	def _time(self, duration: float | None) -> str:
		"""« 0:12 / 3:34 » pour un fichier ; la position seule pour un stream en lecture ; « — » sinon."""
		player = self.player
		position = player.position()
		if (player.source is None) or ((duration is None) and (position is None)):
			return display.EMPTY
		if duration is None:
			return display.duration(position)
		# Une durée se compte à la seconde entamée : un fichier de 0,998 seconde dure « 0:01 ».
		return f"{display.duration((position) or (0))} / {display.duration(math.ceil(duration))}"
