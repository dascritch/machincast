"""Moniteur de la sortie d'antenne (https://github.com/dascritch/machincast/issues/24, spec § 2 et § 8.1).

Les niveaux de l'antenne se lisent sur le port de monitoring du périphérique de l'antenne (audio.device), sans
rien demander à Machin player :

- PipeWire : pipewiresrc sur le nœud de l'antenne, qui en capture la sortie (stream.capture.sink) ; avec le service
  de diffusion, sur son PipeWire, joint par sa socket (propriété fd, https://github.com/dascritch/machincast/issues/381),
  celui de la session ne voyant pas la carte de l'antenne ;
- PulseAudio : pulsesrc sur son « .monitor » ;
- ALSA n'a pas de port de monitoring : le moniteur est indisponible, sans erreur ;
- l'entrée « sortie factice » de l'antenne d'une sortie PipeWire ou PulseAudio : le port de monitoring de la carte
  virtuelle « MachinCast antenne factice », où Machin player la joue le temps de sa diffusion
  (https://github.com/dascritch/machincast/issues/400, machincast.player.virtual_card) ;
- la sortie factice des tests et des essais, et l'entrée « sortie factice » de l'antenne d'une sortie ALSA
  (https://github.com/dascritch/machincast/issues/339) : un signal de test en stéréo (DUMMY_SIGNAL).

Le port est capté en stéréo (CANAUX) : sans contrainte, pipewiresrc et pulsesrc se contentent d'un canal, et le
VU-mètre n'en montrerait qu'un.

Le pipeline (port ! audioconvert ! level ! fakesink) ne joue rien ; son bus est relevé par un minuteur de Qt. Le
moniteur donne le VU (RMS) et la crête de chaque canal, et deux voyants : le blanc, après DEAD_AIR_DURATION secondes
sous DEAD_AIR_THRESHOLD, et la saturation, dès qu'une crête atteint CLIPPING_THRESHOLD, gardée CLIPPING_HOLD
secondes. Un port qui ne s'ouvre pas est réessayé toutes les REESSAI millisecondes. La pré-écoute écoute le même port
(machincast.interface.preview).

Un port qui ne donne plus aucun relevé pendant FREEZE_DELAY secondes, depuis son ouverture ou son dernier relevé,
est gelé (https://github.com/dascritch/machincast/issues/311) : au retour d'une session verrouillée et d'un écran
éteint, un flux PipeWire peut cesser de donner du son, sans erreur ni fin. Le moniteur l'arrête, ce qui efface ses
niveaux : le VU-mètre ne reste pas figé sur les derniers. Il le dit, et le rouvre comme un port qui ne s'ouvre pas.

Un seul port attend à la fois (https://github.com/dascritch/machincast/issues/346) : un port arrêté a RELEASE secondes
pour libérer son périphérique ; sinon, aucun autre ne s'ouvre, et le moniteur réessaie plus tard. Un serveur audio qui
ne répondait plus retenait sinon un fil, un pipeline et leurs descripteurs à chaque essai, jusqu'à épuiser ceux du
processus. Pendant la veille de la session (machincast.interface.screen_saver), le moniteur est en pause : port
fermé, sans nouvel essai.
"""

import logging
import socket
import time
from collections.abc import Callable

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402
from PySide6.QtCore import QObject, QTimer, Signal  # noqa: E402

from machincast import audio as outputs  # noqa: E402
from machincast import service  # noqa: E402
from machincast.configuration import VIRTUAL_CARD, VIRTUAL_CARD_DESCRIPTION, Audio  # noqa: E402
from machincast.i18n import _  # noqa: E402
from machincast.interface import states  # noqa: E402

log = logging.getLogger(__name__)

DUMMY_SIGNAL = "audiotestsrc is-live=true wave=sine volume=0.1"
"""Le port de monitoring de la sortie factice : un signal de test, que les scénarios choisissent."""
DEAD_AIR_THRESHOLD = -50.0
DEAD_AIR_DURATION = 5.0
CLIPPING_THRESHOLD = -1.0
CLIPPING_HOLD = 3.0
READING = 50
"""Millisecondes entre deux relèves du bus."""
RETRY = 5000
"""Millisecondes avant de rouvrir un port de monitoring qui ne s'est pas ouvert, ou qui s'est fermé."""
LEVEL_INTERVAL = 50 * Gst.MSECOND
RELEASE = 0.5
"""Secondes qu'un port arrêté a pour libérer son périphérique avant qu'un autre s'ouvre
(https://github.com/dascritch/machincast/issues/346)."""
FREEZE_DELAY = 3.0
"""Secondes sans relevé au-delà desquelles le port de monitoring est gelé
(https://github.com/dascritch/machincast/issues/311)."""
FROZEN = _("Unavailable: the monitoring port has given nothing for {freeze_delay:g} seconds.").format(
	freeze_delay=FREEZE_DELAY
)
SLOW_WINDOW = 2.0
"""Secondes sur lesquelles se compte le rythme des relevés (https://github.com/dascritch/machincast/issues/627)."""
SLOW_RATIO = 0.5
"""Part des relevés attendus en deçà de laquelle le port est tenu pour ralenti : sous PipeWire, l'écoute de l'antenne
qui s'ouvre et se ferme sur sa carte fait des décrochages (colonne ERR de pw-top) sur le port du moniteur, qui ne
donne plus ensuite qu'une part du son, de moins en moins grande."""
SLOW_SILENCE = 0.5
"""Secondes sans relevé au-delà desquelles un port n'est plus ralenti, mais en train de se figer."""
REOPENING = 600
"""Millisecondes avant de rouvrir un port ralenti : le temps que le précédent libère la carte (RELEASE)."""
SLOW_REOPENINGS = 3
"""Réouvertures d'affilée d'un port ralenti, sans rythme retrouvé, au-delà desquelles il est laissé tel quel."""
NOT_RELEASED = _("Unavailable: the previous monitoring port has not closed yet.")
PAUSED = _("Paused: session locked or screen saver active.")
CHANNELS = "audio/x-raw,channels=2"
"""Ce que donne le port de monitoring : les deux canaux de l'antenne."""
WITHOUT_ALSA = _("Unavailable with the ALSA output, which has no monitoring port.")
WITHOUT_ON_AIR = _("Unavailable: on-air device to fill in.")
NO_SERVICE_ACCESS = _(
	"Unavailable: the PipeWire of the broadcast service does not answer ({error}); the account must belong to the "
	"machincast group, from a session opened after ./install.sh --service."
)


class Unavailable(Exception):
	"""Le port de monitoring ne peut pas s'ouvrir : le message dit pourquoi. action : la raison demande une action de
	l'équipe ou de l'administrateur, que la barre d'état annonce (https://github.com/dascritch/machincast/issues/497)."""

	def __init__(self, message: str, *, action: bool = False) -> None:
		super().__init__(message)
		self.action = action


def port_name(audio: Audio) -> str:
	"""Ce que le port de monitoring écoute, pour l'infobulle du VU-mètre et la source de la pré-écoute."""
	output, device = audio.monitored_on_air()
	name = (device) or (_("device to fill in"))
	if device == VIRTUAL_CARD:
		name = VIRTUAL_CARD_DESCRIPTION
	if output == "dummy":
		return _("dummy output, test signal")
	if output == "pulseaudio":
		return _("PulseAudio, {name}.monitor").format(name=name)
	if (output == "pipewire") and (service.pipewire_socket() is not None):
		return _("PipeWire of the broadcast service, {name}").format(name=name)
	if output == "pipewire":
		return _("PipeWire, {name}").format(name=name)
	return _("ALSA, {name}").format(name=name)


def check(audio: Audio) -> None:
	"""Lève Indisponible si l'antenne n'a pas de port de monitoring."""
	if audio.on_air()[0] == "alsa":
		raise Unavailable(WITHOUT_ALSA, action=True)
	if audio.to_fill_in_on_air():
		raise Unavailable(WITHOUT_ON_AIR, action=True)


def monitor_source(audio: Audio) -> Gst.Element:
	"""L'élément qui donne le son de l'antenne ; lève Indisponible s'il n'y en a pas. Sur l'entrée « sortie factice »
	(https://github.com/dascritch/machincast/issues/339), le signal de test, comme sur la sortie factice."""
	Gst.init(None)
	check(audio)
	output, device = audio.monitored_on_air()
	if output == "dummy":
		try:
			return Gst.parse_bin_from_description(f"{DUMMY_SIGNAL} ! capsfilter caps={CHANNELS}", True)
		except GLib.Error as error:
			raise Unavailable(_("Unavailable: {message}").format(message=error.message)) from None
	if output == "pulseaudio":
		source = _item("pulsesrc")
		source.set_property("device", f"{device}.monitor")
		outputs.present(source, outputs.MONITORING)
		return _in_stereo(source)
	connection = _service_connection()
	source = _item("pipewiresrc")
	if connection is not None:
		# L'antenne joue sur le PipeWire du service (https://github.com/dascritch/machincast/issues/381).
		source.set_property("fd", connection.fileno())
	source.set_property("target-object", device)
	properties, _end = Gst.Structure.from_string("props, stream.capture.sink=(boolean)true")
	source.set_property("stream-properties", properties)
	outputs.present(source, outputs.MONITORING)
	# Jamais l'écoute d'un autre périphérique que l'antenne (https://github.com/dascritch/machincast/issues/345).
	outputs.lock(source)
	return _in_stereo(source, connection)


INPUT_NOT_FOUND = _("Not found: this computer does not see this audio input.")
"""Une entrée audio que le poste ne voit pas (https://github.com/dascritch/machincast/issues/624)."""


def input_source(audio: Audio, device: str) -> Gst.Element:
	"""L'élément qui donne le son d'une entrée audio, en stéréo (https://github.com/dascritch/machincast/issues/624) :
	sous PipeWire, par le PipeWire du service quand il tourne, comme le moniteur de l'antenne, verrouillé sur l'entrée ;
	sous PulseAudio ou ALSA, la source de la sortie ; le signal de test sur la sortie factice. Lève Indisponible pour
	une entrée que le poste ne voit pas."""
	Gst.init(None)
	if audio.output == "dummy":
		try:
			return Gst.parse_bin_from_description(f"{DUMMY_SIGNAL} ! capsfilter caps={CHANNELS}", True)
		except GLib.Error as error:
			raise Unavailable(_("Unavailable: {message}").format(message=error.message)) from None
	seen = False
	for appliance in outputs.input_devices(audio.output):
		if appliance.identifier == device:
			seen = True
	if not seen:
		raise Unavailable(INPUT_NOT_FOUND)
	if audio.output in ("pulseaudio", "alsa"):
		source = _item(outputs.CAPTURES[audio.output].factory)
		source.set_property("device", device)
		outputs.present(source, outputs.INPUT_MONITORING)
		return _in_stereo(source)
	connection = _service_connection()
	source = _item("pipewiresrc")
	if connection is not None:
		source.set_property("fd", connection.fileno())
	source.set_property("target-object", device)
	outputs.present(source, outputs.INPUT_MONITORING)
	outputs.lock(source)
	return _in_stereo(source, connection)


def _service_connection() -> socket.socket | None:
	"""La connexion au PipeWire du service, s'il tourne ; lève Indisponible s'il ne se joint pas."""
	try:
		return service.connect_pipewire()
	except OSError as error:
		raise Unavailable(NO_SERVICE_ACCESS.format(error=error.strerror), action=True) from None


class _ServiceBin(Gst.Bin):
	"""Un bin qui garde la connexion au PipeWire du service le temps de sa vie : pipewiresrc la duplique en
	s'ouvrant."""

	def __init__(self, connection: socket.socket) -> None:
		super().__init__()
		self.connection = connection


def _in_stereo(source: Gst.Element, connection: socket.socket | None = None) -> Gst.Element:
	"""La source, suivie d'un filtre qui lui demande les deux canaux de l'antenne."""
	block: Gst.Bin = Gst.Bin.new(None)
	if connection is not None:
		block = _ServiceBin(connection)
	filter_ = _item("capsfilter")
	filter_.set_property("caps", Gst.Caps.from_string(CHANNELS))
	block.add(source)
	block.add(filter_)
	source.link(filter_)
	output = filter_.get_static_pad("src")
	assert output is not None
	block.add_pad(Gst.GhostPad.new("src", output))
	return block


def _item(factory: str) -> Gst.Element:
	item = Gst.ElementFactory.make(factory, None)
	if item is None:
		raise Unavailable(_("Unavailable: GStreamer element {factory} not found.").format(factory=factory))
	return item


class Monitor(QObject):
	"""Les niveaux de l'antenne, relevés tant qu'il tourne."""

	changed = Signal()
	"""Nouveaux niveaux, voyants, ou disponibilité."""

	def __init__(
		self, audio: Audio | None, parent: QObject | None = None, clock: Callable[[], float] = time.monotonic
	) -> None:
		super().__init__(parent)
		self.audio = audio
		self.clock = clock
		self._pipeline: Gst.Pipeline | None = None
		self._piloted: states.Pilot | None = None
		"""Les changements d'état du port, hors du fil de l'interface (https://github.com/dascritch/machincast/issues/259)."""
		self._closing: states.Pilot | None = None
		"""Le pilote du port arrêté en dernier, tant qu'il n'a pas libéré son périphérique."""
		self.paused = False
		"""La session est en veille : le port reste fermé (https://github.com/dascritch/machincast/issues/346)."""
		self._level: Gst.Element | None = None
		self.levels: list[float] = []
		self.peaks: list[float] = []
		self.unavailable: str | None = None
		self.action = False
		"""La raison de l'indisponibilité demande une action : l'onglet Antenne l'annonce dans la barre d'état."""
		self.dead_air = False
		self.clipping = False
		self._sound_since: float | None = None
		"""Dernier instant où un canal dépassait le seuil du blanc."""
		self._clipping_since: float | None = None
		self._read_off_levels: float | None = None
		self._window_start: float | None = None
		"""Le début de la fenêtre où se comptent les relevés, au premier relevé du port ouvert."""
		self._window_readings = 0
		self._reopenings = 0
		"""Réouvertures d'affilée d'un port ralenti."""
		"""Instant de l'ouverture du port, puis de son dernier relevé : pour constater un port gelé."""
		self._reading = QTimer(self)
		self._reading.setInterval(READING)
		self._reading.timeout.connect(self._read_off)
		self._retry = QTimer(self)
		self._retry.setSingleShot(True)
		self._retry.timeout.connect(self.start)

	def active(self) -> bool:
		return self._pipeline is not None

	def planned_retry(self) -> bool:
		"""Un port indisponible sera rouvert ; jamais avec ALSA ni sans périphérique d'antenne."""
		return self._retry.isActive()

	def start(self) -> None:
		"""Ouvre le port de monitoring ; indisponible, il le dit, et réessaie si l'antenne a bien un port. En pause, il
		reste fermé ; tant que le port précédent n'a pas libéré son périphérique, aucun autre ne s'ouvre."""
		self.halt()
		if self.paused:
			self.unavailable, self.action = PAUSED, False
			self.changed.emit()
			return
		if not self._previous_released():
			self._unavailable(NOT_RELEASED)
			return
		if self.audio is None:
			self.action = False
			self.unavailable = _("Unavailable: unknown on-air output.")
			self.changed.emit()
			return
		try:
			source = self.source(self.audio)
		except Unavailable as error:
			self._unavailable(str(error), action=error.action)
			return
		pipeline = Gst.Pipeline.new("moniteur-antenne")
		conversion = Gst.ElementFactory.make("audioconvert", None)
		level = Gst.ElementFactory.make("level", None)
		sink = Gst.ElementFactory.make("fakesink", None)
		assert (conversion is not None) and (level is not None) and (sink is not None)
		level.set_property("interval", LEVEL_INTERVAL)
		level.set_property("post-messages", True)
		sink.set_property("sync", False)
		for item in (source, conversion, level, sink):
			pipeline.add(item)
		source.link(conversion)
		conversion.link(level)
		level.link(sink)
		self._pipeline, self._level = pipeline, level
		self._piloted = states.Pilot(pipeline)
		self.unavailable, self.action = None, False
		self._sound_since = self._read_off_levels = self.clock()
		self._window_start, self._window_readings = None, 0
		# Ouvrir le port peut attendre le serveur audio : son pilote l'ouvre, et la relève dit s'il ne s'ouvre pas.
		self._piloted.to(Gst.State.PLAYING)
		self._reading.start()
		self.changed.emit()

	def source(self, audio: Audio) -> Gst.Element:
		"""Ce que le moniteur écoute : le port de monitoring de l'antenne."""
		return monitor_source(audio)

	def pause(self) -> None:
		"""Ferme le port le temps de la veille de la session, sans le rouvrir."""
		self.paused = True
		self.start()

	def resume(self) -> None:
		"""Rouvre le port au retour de la session."""
		self.paused = False
		self.start()

	def _previous_released(self) -> bool:
		"""Le port arrêté en dernier a libéré son périphérique : sinon, un serveur audio qui ne répond plus retiendrait
		un fil, un pipeline et leurs descripteurs à chaque essai (https://github.com/dascritch/machincast/issues/346)."""
		closing = self._closing
		if (closing is not None) and (not closing.released(RELEASE)):
			return False
		self._closing = None
		return True

	def halt(self) -> None:
		self._reading.stop()
		self._retry.stop()
		if self._piloted is not None:
			self._piloted.switch_off()
			self._closing = self._piloted
		self._pipeline, self._piloted, self._level = None, None, None
		self.levels, self.peaks = [], []
		self.dead_air, self.clipping = False, False

	def _unavailable(self, message: str, *, action: bool = False) -> None:
		self.halt()
		self.unavailable, self.action = message, action
		if (self.audio is not None) and (message not in (WITHOUT_ALSA, WITHOUT_ON_AIR)):
			self._retry.start(RETRY)
		self.changed.emit()

	def _read_off(self) -> None:
		pipeline = self._pipeline
		if pipeline is None:
			return
		if (self._piloted is not None) and (self._piloted.has_failed()):
			self._unavailable(_("Unavailable: the monitoring port does not open."))
			return
		bus = pipeline.get_bus()
		assert bus is not None
		while (message := bus.pop()) is not None:
			if message.type in (Gst.MessageType.ERROR, Gst.MessageType.EOS):
				text = _("the monitoring port has closed.")
				if message.type == Gst.MessageType.ERROR:
					error, _detail = message.parse_error()
					text = str(error.message)
				self._unavailable(_("Unavailable: {text}").format(text=text))
				return
			structure = message.get_structure()
			if (message.src == self._level) and (structure is not None) and (structure.get_name() == "level"):
				self._read_off_levels = self.clock()
				self._count_reading()
				self.note(list((structure.get_value("rms")) or ([])), list((structure.get_value("peak")) or ([])))
		if (self._read_off_levels is not None) and (self.clock() - self._read_off_levels >= FREEZE_DELAY):
			self._unavailable(FROZEN)
			return
		if self._slowed():
			self._reopen()
			return
		self.changed.emit()

	def _count_reading(self) -> None:
		if self._window_start is None:
			self._window_start = self.clock()
		self._window_readings += 1

	def _slowed(self) -> bool:
		"""Une fenêtre de SLOW_WINDOW secondes vient de finir, avec moins de SLOW_RATIO des relevés attendus, le dernier
		il y a moins de SLOW_SILENCE secondes ; une fenêtre au bon rythme remet à zéro les réouvertures d'affilée."""
		if (self._window_start is None) or (self.clock() - self._window_start < SLOW_WINDOW):
			return False
		expected = SLOW_WINDOW / (LEVEL_INTERVAL / Gst.SECOND)
		# Un port qui ne donne plus rien depuis un moment se fige : le gel le dit (FREEZE_DELAY), pas la lenteur.
		still_giving = (self._read_off_levels is not None) and (self.clock() - self._read_off_levels < SLOW_SILENCE)
		slowed = (still_giving) and (self._window_readings < SLOW_RATIO * expected)
		self._window_start, self._window_readings = self.clock(), 0
		if not slowed:
			self._reopenings = 0
		return slowed

	def _reopen(self) -> None:
		"""Un port ralenti se rouvre, sans être dit indisponible, au plus SLOW_REOPENINGS fois d'affilée
		(https://github.com/dascritch/machincast/issues/627)."""
		if self._reopenings >= SLOW_REOPENINGS:
			self.changed.emit()
			return
		self._reopenings += 1
		log.warning(_("monitoring port slowed down, reopened"))
		self.halt()
		self._retry.start(REOPENING)
		self.changed.emit()

	def note(self, levels: list[float], peaks: list[float]) -> None:
		"""Un relevé de level : le VU (RMS) et la crête de chaque canal, en décibels ; met à jour les voyants."""
		now = self.clock()
		rms_levels = []
		for n in levels:
			rms_levels.append(float(n))
		peak_levels = []
		for c in peaks:
			peak_levels.append(float(c))
		self.levels, self.peaks = rms_levels, peak_levels
		found = False
		for level in self.levels:
			if level > DEAD_AIR_THRESHOLD:
				found = True
				break
		if found:
			self._sound_since = now
		self.dead_air = (self._sound_since is not None) and (now - self._sound_since >= DEAD_AIR_DURATION)
		clipping = False
		for peak in self.peaks:
			if peak >= CLIPPING_THRESHOLD:
				clipping = True
				break
		if clipping:
			self._clipping_since = now
		self.clipping = (self._clipping_since is not None) and (now - self._clipping_since < CLIPPING_HOLD)


class InputMonitor(Monitor):
	"""Les niveaux d'une entrée audio (https://github.com/dascritch/machincast/issues/624), relevés tant qu'il tourne ;
	une entrée introuvable le dit, et se réessaie, comme un port qui ne s'ouvre pas."""

	def __init__(
		self,
		audio: Audio | None,
		device: str,
		parent: QObject | None = None,
		clock: Callable[[], float] = time.monotonic,
	) -> None:
		super().__init__(audio, parent, clock)
		self.device = device

	def source(self, audio: Audio) -> Gst.Element:
		return input_source(audio, self.device)
