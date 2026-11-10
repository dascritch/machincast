"""Test d'un flux à la demande, depuis la fiche d'un stream (https://github.com/dascritch/machincast/issues/28,
spec § 4.6).

GStreamer se connecte à l'adresse et décode le flux, sans rien jouer. Le flux répond dès qu'une seconde de son est
décodée ; il ne répond pas si GStreamer signale une erreur (adresse injoignable, réponse en erreur), ou si cette seconde
de son n'arrive pas dans le délai. Qui répond dit aussi le type du flux et son débit, lus dans les tags que GStreamer
trouve en le décodant (https://github.com/dascritch/machincast/issues/223) : le codec, puis le débit nominal, sinon le
débit mesuré. Le test terminé, la connexion au flux est fermée. Le test ne bloque pas l'interface :
le bus de GStreamer est relevé par un minuteur de Qt.
"""

from datetime import timedelta

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PySide6.QtCore import QObject, QTimer, Signal  # noqa: E402

from machincast.i18n import _  # noqa: E402
from machincast.interface import states  # noqa: E402

DELAY = timedelta(seconds=10)
"""Au-delà, sans son, le flux ne répond pas."""
EXPECTED_SOUND = timedelta(seconds=1)
"""Son décodé qui prouve que le flux répond."""
READING = timedelta(milliseconds=100)
"""Intervalle de relève du bus de GStreamer."""


def _milliseconds(duration: timedelta) -> int:
	return int(duration.total_seconds() * 1000)


def trial_result(answers: bool, detail: str) -> str:
	"""« Le flux répond : du son arrive. », ou « Le flux ne répond pas : … », pour la fiche qui a lancé l'essai."""
	if answers:
		return _("The stream answers: {detail}").format(detail=detail)
	return _("The stream does not answer: {detail}").format(detail=detail)


def describe(stream_type: str | None, bitrate: int | None) -> str:
	"""« en MPEG-1 Layer 3 (MP3) à 128 kbit/s », ce qu'on en sait."""
	fetched_type = _("of unknown type")
	if stream_type is not None:
		fetched_type = _("in {stream_type}").format(stream_type=stream_type)
	fetched_bitrate = _("at unknown bitrate")
	if bitrate is not None:
		fetched_bitrate = _("at {bitrate} kbit/s").format(bitrate=round(bitrate / 1000))
	return f"{fetched_type} {fetched_bitrate}"


class StreamTrial(QObject):
	finished = Signal(bool, str)
	"""Fin du test : le flux répond-il, et sinon pourquoi."""

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		Gst.init(None)
		self._pipeline: Gst.Pipeline | None = None
		self._piloted: states.Pilot | None = None
		self._sound = 0
		"""Son décodé, en nanosecondes."""
		self._type: str | None = None
		self._bitrate: int | None = None
		"""En bits par seconde : le débit nominal du flux, sinon le dernier mesuré."""
		self._reading = QTimer(self)
		self._reading.setInterval(_milliseconds(READING))
		self._reading.timeout.connect(self._read_off)
		self._limit = QTimer(self)
		self._limit.setSingleShot(True)
		self._limit.timeout.connect(self._expire)

	def ongoing(self) -> bool:
		return self._pipeline is not None

	def launch(self, address: str) -> None:
		"""Un seul test à la fois : la fiche n'en relance pas un tant que le précédent n'est pas terminé."""
		if not Gst.uri_is_valid(address):
			self.finished.emit(False, _("“{address}” is not an address.").format(address=address))
			return
		pipeline = Gst.parse_launch(
			"uridecodebin name=source ! audioconvert ! fakesink name=sortie sync=false signal-handoffs=true"
		)
		assert isinstance(pipeline, Gst.Pipeline)
		source, output = pipeline.get_by_name("source"), pipeline.get_by_name("sortie")
		assert (source is not None) and (output is not None)
		source.set_property("uri", address)
		output.connect("handoff", self._received)
		self._sound = 0
		self._type, self._bitrate = None, None
		self._pipeline = pipeline
		self._piloted = states.Pilot(pipeline)
		self._piloted.to(Gst.State.PLAYING)
		self._reading.start()
		self._limit.start(_milliseconds(DELAY))

	def halt(self) -> None:
		self._reading.stop()
		self._limit.stop()
		if self._piloted is not None:
			self._piloted.switch_off()
		self._pipeline, self._piloted = None, None

	def _received(self, _output: Gst.Element, buffer: Gst.Buffer, _pad: Gst.Pad) -> None:
		"""Appelé dans un fil de GStreamer : il ne fait que compter."""
		self._sound += buffer.duration

	def _read_off(self) -> None:
		assert self._pipeline is not None
		bus = self._pipeline.get_bus()
		# pop_filtered jette les messages d'autres types : les tags et les erreurs se lisent ensemble.
		while (message := bus.pop_filtered(Gst.MessageType.TAG | Gst.MessageType.ERROR)) is not None:
			if message.type != Gst.MessageType.TAG:
				error, _detail = message.parse_error()
				self._finish(False, f"{error.message.rstrip('.')}.")
				return
			self._read_tags(message.parse_tag())
		if self._sound >= EXPECTED_SOUND.total_seconds() * Gst.SECOND:
			self._finish(True, _("sound arrives, {describe}.").format(describe=describe(self._type, self._bitrate)))

	def _read_tags(self, tags: Gst.TagList) -> None:
		found, codec = tags.get_string(Gst.TAG_AUDIO_CODEC)
		if found:
			self._type = codec
		found, nominal = tags.get_uint(Gst.TAG_NOMINAL_BITRATE)
		if (found) and (nominal > 0):
			self._bitrate = nominal
			return
		found, measure = tags.get_uint(Gst.TAG_BITRATE)
		if (found) and (measure > 0) and (self._bitrate is None):
			self._bitrate = measure

	def _expire(self) -> None:
		self._finish(False, _("the sound does not arrive within {delay} s.").format(delay=int(DELAY.total_seconds())))

	def _finish(self, answers: bool, detail: str) -> None:
		self.halt()
		self.finished.emit(answers, detail)
