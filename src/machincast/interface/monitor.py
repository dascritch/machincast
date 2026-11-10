"""Moniteur de la sortie d'antenne (https://github.com/dascritch/machincast/issues/24, spec § 2 et § 8.1).

Les niveaux de l'antenne se lisent sur le port de monitoring du périphérique de l'antenne (audio.device), sans
rien demander à Machin player :

- PipeWire : pipewiresrc sur le nœud de l'antenne, qui en capture la sortie (stream.capture.sink) ;
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
"""

import time
from collections.abc import Callable

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402
from PySide6.QtCore import QObject, QTimer, Signal  # noqa: E402

from machincast import audio as outputs  # noqa: E402
from machincast.configuration import VIRTUAL_CARD, VIRTUAL_CARD_DESCRIPTION, Audio  # noqa: E402
from machincast.i18n import _  # noqa: E402
from machincast.interface import states  # noqa: E402

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
FREEZE_DELAY = 3.0
"""Secondes sans relevé au-delà desquelles le port de monitoring est gelé
(https://github.com/dascritch/machincast/issues/311)."""
FROZEN = _("Unavailable: the monitoring port has given nothing for {freeze_delay:g} seconds.").format(
	freeze_delay=FREEZE_DELAY
)
CHANNELS = "audio/x-raw,channels=2"
"""Ce que donne le port de monitoring : les deux canaux de l'antenne."""
WITHOUT_ALSA = _("Unavailable with the ALSA output, which has no monitoring port.")
WITHOUT_ON_AIR = _("Unavailable: on-air device to fill in.")


class Unavailable(Exception):
	"""Le port de monitoring ne peut pas s'ouvrir : le message dit pourquoi."""


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
	if output == "pipewire":
		return _("PipeWire, {name}").format(name=name)
	return _("ALSA, {name}").format(name=name)


def check(audio: Audio) -> None:
	"""Lève Indisponible si l'antenne n'a pas de port de monitoring."""
	if audio.on_air()[0] == "alsa":
		raise Unavailable(WITHOUT_ALSA)
	if audio.to_fill_in_on_air():
		raise Unavailable(WITHOUT_ON_AIR)


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
	source = _item("pipewiresrc")
	source.set_property("target-object", device)
	properties, _end = Gst.Structure.from_string("props, stream.capture.sink=(boolean)true")
	source.set_property("stream-properties", properties)
	outputs.present(source, outputs.MONITORING)
	# Jamais l'écoute d'un autre périphérique que l'antenne (https://github.com/dascritch/machincast/issues/345).
	outputs.lock(source)
	return _in_stereo(source)


def _in_stereo(source: Gst.Element) -> Gst.Element:
	"""La source, suivie d'un filtre qui lui demande les deux canaux de l'antenne."""
	block = Gst.Bin.new(None)
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
		self._level: Gst.Element | None = None
		self.levels: list[float] = []
		self.peaks: list[float] = []
		self.unavailable: str | None = None
		self.dead_air = False
		self.clipping = False
		self._sound_since: float | None = None
		"""Dernier instant où un canal dépassait le seuil du blanc."""
		self._clipping_since: float | None = None
		self._read_off_levels: float | None = None
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
		"""Ouvre le port de monitoring ; indisponible, il le dit, et réessaie si l'antenne a bien un port."""
		self.halt()
		if self.audio is None:
			self.unavailable = _("Unavailable: unknown on-air output.")
			self.changed.emit()
			return
		try:
			source = monitor_source(self.audio)
		except Unavailable as error:
			self._unavailable(str(error))
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
		self.unavailable = None
		self._sound_since = self._read_off_levels = self.clock()
		# Ouvrir le port peut attendre le serveur audio : son pilote l'ouvre, et la relève dit s'il ne s'ouvre pas.
		self._piloted.to(Gst.State.PLAYING)
		self._reading.start()
		self.changed.emit()

	def halt(self) -> None:
		self._reading.stop()
		self._retry.stop()
		if self._piloted is not None:
			self._piloted.switch_off()
		self._pipeline, self._piloted, self._level = None, None, None
		self.levels, self.peaks = [], []
		self.dead_air, self.clipping = False, False

	def _unavailable(self, message: str) -> None:
		self.halt()
		self.unavailable = message
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
				self.note(list((structure.get_value("rms")) or ([])), list((structure.get_value("peak")) or ([])))
		if (self._read_off_levels is not None) and (self.clock() - self._read_off_levels >= FREEZE_DELAY):
			self._unavailable(FROZEN)
			return
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
