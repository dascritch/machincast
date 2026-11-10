"""Vérification d'un fichier sonore par décodage complet (https://github.com/dascritch/machincast/issues/7).

Le fichier est décodé en entier par GStreamer, sans être joué et donc bien plus vite que le temps
réel. GStreamer est tolérant : un fichier tronqué ou corrompu se décode le plus souvent sans la
moindre erreur, en donnant un son plus court ou parasité. Le décodage examine donc trois signes :

1. une erreur de GStreamer, aucun son décodé ou un décodage qui n'avance plus : fichier illisible ;
2. une rupture de continuité du son décodé (tampon marqué DISCONT après le premier) : le décodeur
   a dû sauter des données, fichier endommagé ;
3. une durée décodée plus courte que la durée annoncée par l'en-tête : fichier tronqué ou trames
   perdues, fichier endommagé.

Pendant l'audit complet, le décodage mesure aussi les silences au début et à la fin du fichier
(https://github.com/dascritch/machincast/issues/146) : un élément level relève le niveau crête de chaque tranche de
SILENCE_INTERVAL, et le silence s'arrête à la première tranche dont le canal le plus fort atteint le seuil.

Limites, propres aux formats : un WAV ou un AIFF n'a ni somme de contrôle ni structure en trames,
des octets altérés y passent inaperçus ; un WAV, un Ogg ou un MP3 sans en-tête de durée tronqué se
décode comme un fichier plus court, sans rien qui le distingue d'un fichier sain.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast.i18n import N_, _, decimal  # noqa: E402
from machincast.indexer.tags import Tags, extract  # noqa: E402

DELAY_WITHOUT_PROGRESS = timedelta(seconds=30)
"""Un décodage qui ne produit plus aucun son pendant ce délai est abandonné (disque bloqué, fichier sur un
partage réseau qui ne répond plus)."""

STARTUP_DELAY = timedelta(seconds=2.5)
"""Délai accordé au premier son décodé. Au-delà, le décodage est repris depuis le début."""

ATTEMPTS = 6
"""Nombre de démarrages tentés, pour un disque réseau en veille et pour un AIFF déjà en base : l'AIFF n'est plus
indexé (https://github.com/dascritch/machincast/issues/284). decodebin se bloque au démarrage d'un fichier AIFF, avant
le moindre son décodé :
une fois sur cinq à dix avec GStreamer 1.24 (https://github.com/dascritch/machincast/issues/280), encore 44 fois sur
1 000 avec GStreamer 1.28.2, celui d'Ubuntu 26.04 ; les autres formats ne se bloquent pas (python -m
tests.gstreamer_measures, sans le code de MachinCast, https://github.com/dascritch/machincast/issues/284). Un nouveau
démarrage suffit : avec 1.28, six tentatives de 2,5 secondes ne laissent qu'une chance sur cent millions de déclarer
illisible un AIFF sain, contre une sur dix mille avec trois, et laissent à un disque réseau en veille 15 secondes.
Ni une file (queue), qui fait lire le fichier en flux, ni decodebin3 ne conviennent, en 1.28 comme en 1.24 : le
premier bloque des fichiers en cours de décodage (9 WAV sur 1 000), le second, qui ne se bloque jamais au démarrage,
ne rend plus la main sur un fichier qui ne se lit plus."""

DURATION_TOLERANCE = timedelta(milliseconds=75)
"""Écart toléré entre la durée annoncée et la durée décodée : les encodeurs MP3 et AAC ajoutent ou retirent
quelques dizaines de millisecondes de remplissage. Une trame FLAC perdue en fait déjà une centaine."""

TOLERANCE_RELATIVE = 0.001
"""Écart toléré en proportion de la durée annoncée, pour les longs fichiers : 3,6 secondes sur une heure."""

WAIT_STEP = timedelta(milliseconds=250)

SILENCE_INTERVAL = timedelta(milliseconds=10)
"""Durée des tranches dont le niveau crête est mesuré : la précision des silences détectés."""

DECODER_PACKAGES = _("gstreamer1.0-plugins-base, gstreamer1.0-plugins-good and gstreamer1.0-plugins-bad")


class FileState(StrEnum):
	"""Verdict de la vérification d'un fichier."""

	HEALTHY = N_("healthy")
	DAMAGED = N_("damaged")
	UNREADABLE = N_("unreadable")
	NOT_FOUND = N_("not found")
	UNSUPPORTED = N_("unsupported")
	"""Le fichier n'est pas du son, d'après son type (machincast.indexer.file_type) : il n'est pas décodé."""


@dataclass(frozen=True)
class Silences:
	"""Silences détectés au début et à la fin d'un fichier (https://github.com/dascritch/machincast/issues/146).

	La fin se compte depuis la fin du son décodé : c'est la durée du silence final. Un fichier qui n'atteint jamais le
	seuil n'a ni l'un ni l'autre (None)."""

	start: timedelta | None
	end: timedelta | None


@dataclass(frozen=True)
class Check:
	state: FileState
	duration: timedelta | None
	"""Durée effectivement décodée ; None si rien n'a pu être décodé."""
	problem: str | None = None
	"""Description du problème, commençant par l'état (« endommagé : … »), traduite ; None pour un fichier sain."""
	tags: Tags = field(default_factory=lambda: Tags(None, None, {}))
	"""Tags lus pendant le décodage (https://github.com/dascritch/machincast/issues/8)."""
	silences: Silences | None = None
	"""Silences mesurés pendant le décodage d'un fichier sain ; None s'ils n'ont pas été mesurés, sans seuil."""
	detail: str | None = None
	"""Le problème seul, sans l'état qui le précède : pour le document d'audit."""

	@classmethod
	def healthy(cls, duration: timedelta, tags: Tags | None = None, silences: Silences | None = None) -> "Check":
		return cls(FileState.HEALTHY, duration, tags=(tags) or (Tags(None, None, {})), silences=silences)

	@classmethod
	def defective(cls, state: FileState, detail: str, duration: timedelta | None = None) -> "Check":
		return cls(state, duration, _("{state}: {detail}").format(state=_(state), detail=detail), detail=detail)


class Checker(Protocol):
	"""Ce que l'indexeur appelle pour vérifier un fichier : check_file, ou ce qui le remplace."""

	def __call__(self, path: Path, *, silence_threshold: float | None = None) -> Check: ...


class UnavailableDecoder(Exception):
	"""GStreamer n'a pas de décodeur pour ce format : il manque un paquet, le fichier n'y est pour rien.

	La vérification s'arrête au lieu de déclarer le fichier illisible : sinon, un paquet absent
	désactiverait d'un coup tous les sonores du format concerné.
	"""


@dataclass
class _Tracking:
	"""Ce que la sonde voit passer à l'entrée du puits : les tampons de son décodé."""

	buffers: int = 0
	breaks: int = 0
	start: int | None = None
	end: int = 0


@dataclass
class _Levels:
	"""Les tranches dont le niveau crête atteint le seuil : la première et la dernière, en nanosecondes."""

	threshold: float
	first_sound: int | None = None
	sound_end: int | None = None

	def note(self, structure: Gst.Structure) -> None:
		"""Un message de l'élément level : le niveau crête de chaque canal, en dB, sur une tranche."""
		peaks = []
		for value in (structure.get_value("peak")) or ([]):
			peaks.append(float(value))
		if (not peaks) or (max(peaks) < self.threshold):
			return
		start = int(str(structure.get_value("timestamp")))
		end = start + int(str(structure.get_value("duration")))
		if self.first_sound is None:
			self.first_sound = start
		self.sound_end = max(end, (self.sound_end) or (0))


def _probe(tracking: _Tracking) -> Callable[[Gst.Pad, Gst.PadProbeInfo], Gst.PadProbeReturn]:
	def probe(pad: Gst.Pad, info: Gst.PadProbeInfo) -> Gst.PadProbeReturn:
		buffer = info.get_buffer()
		if buffer is None:
			return Gst.PadProbeReturn.OK
		tracking.buffers += 1
		if (tracking.buffers > 1) and (buffer.has_flags(Gst.BufferFlags.DISCONT)):
			tracking.breaks += 1
		if buffer.pts != Gst.CLOCK_TIME_NONE:
			if tracking.start is None:
				tracking.start = buffer.pts
			if buffer.duration != Gst.CLOCK_TIME_NONE:
				duration = buffer.duration
			else:
				duration = 0
			tracking.end = max(tracking.end, buffer.pts + duration)
		return Gst.PadProbeReturn.OK

	return probe


def _in_seconds(duration: timedelta) -> str:
	return decimal(f"{duration.total_seconds():.3f} s")


def _nanoseconds(value: int) -> timedelta:
	return timedelta(microseconds=value / 1000)


class _Decoding:
	"""Un pipeline filesrc ! decodebin ! audioconvert ! fakesink, aussi rapide que le disque le permet.

	Avec un seuil de silence, un élément level, entre audioconvert et fakesink, mesure le niveau crête de chaque
	tranche (https://github.com/dascritch/machincast/issues/146)."""

	def __init__(self, path: Path, silence_threshold: float | None = None) -> None:
		self.pipeline = Gst.Pipeline.new("verification")
		names = ["filesrc", "decodebin", "audioconvert", "fakesink"]
		if silence_threshold is not None:
			names.insert(3, "level")
		items = []
		for name in names:
			items.append(Gst.ElementFactory.make(name, None))
		found = False
		for item in items:
			if item is None:
				found = True
				break
		if found:
			raise UnavailableDecoder(
				_("basic GStreamer elements not found: install {decoder_packages}").format(
					decoder_packages=DECODER_PACKAGES
				)
			)
		found_list = []
		for item in items:
			if item is not None:
				found_list.append(item)
		source, decoder, self.conversion, sink = found_list[0], found_list[1], found_list[2], found_list[-1]
		source.set_property("location", str(path))
		sink.set_property("sync", False)
		for item in found_list:
			self.pipeline.add(item)
		source.link(decoder)
		for upstream, downstream in zip(found_list[2:], found_list[3:], strict=False):
			upstream.link(downstream)
		self.levels: _Levels | None = None
		self.measure: Gst.Element | None = None
		if silence_threshold is not None:
			self.levels = _Levels(silence_threshold)
			self.measure = found_list[3]
			self.measure.set_property("interval", round(SILENCE_INTERVAL.total_seconds() * Gst.SECOND))
			self.measure.set_property("post-messages", True)
		self.decoder = decoder
		self.binding = decoder.connect("pad-added", self._link)
		"""Le gestionnaire de decodebin retient ce décodage, qui retient le pipeline : un cycle que le ramasse-miettes
		de Python ne voit pas. Sans liberer(), chaque décodage garderait les deux descripteurs de son bus
		(https://github.com/dascritch/machincast/issues/149)."""
		self.tracking = _Tracking()
		entry = sink.get_static_pad("sink")
		assert entry is not None
		entry.add_probe(Gst.PadProbeType.BUFFER, _probe(self.tracking))
		bus = self.pipeline.get_bus()
		assert bus is not None
		self.bus = bus
		self.absent_decoder: str | None = None
		self.tags = Gst.TagList.new_empty()

	def release(self) -> None:
		"""Arrête le pipeline et rompt le cycle de liaison : le pipeline et son bus sont alors détruits."""
		self.pipeline.set_state(Gst.State.NULL)
		self.decoder.disconnect(self.binding)

	def _link(self, decoder: Gst.Element, output: Gst.Pad) -> None:
		"""Relie la première sortie audio de decodebin ; les autres flux (pochette, vidéo) sont ignorés."""
		entry = self.conversion.get_static_pad("sink")
		if (entry is None) or (entry.is_linked()):
			return
		# decodebin annonce ses sorties avec des capacités fixées ; sans elles, la liaison décide.
		capabilities = output.get_current_caps()
		structure: Gst.Structure | None = None
		if (capabilities is not None) and (capabilities.get_size() > 0):
			structure = capabilities.get_structure(0)
		if (structure is None) or (structure.get_name().startswith("audio/")):
			output.link(entry)

	def wait(
		self, expected_list: Gst.MessageType, startup_delay: timedelta, delay_without_progress: timedelta
	) -> Gst.Message | None:
		"""Attend un des messages attendus ou une erreur ; None si le son décodé n'avance plus.

		Tant qu'aucun son n'est décodé, le délai est celui du démarrage ; ensuite, celui de la progression.
		"""
		step = round(WAIT_STEP.total_seconds() * Gst.SECOND)
		types = expected_list | Gst.MessageType.ERROR | Gst.MessageType.ELEMENT | Gst.MessageType.TAG
		still = timedelta()
		last = self.tracking.buffers
		while True:
			message = self.bus.timed_pop_filtered(step, types)
			if message is None:
				if self.tracking.buffers == last:
					still += WAIT_STEP
					delay = delay_without_progress
					if self.tracking.buffers == 0:
						delay = startup_delay
					if still >= delay:
						return None
				else:
					last, still = self.tracking.buffers, timedelta()
			else:
				if not self._noted(message):
					return message

	def _noted(self, message: Gst.Message) -> bool:
		"""Un message de tags ou d'élément est noté, et l'attente continue ; un autre message est attendu, ou une
		erreur."""
		if message.type == Gst.MessageType.TAG:
			# Tags du conteneur et de chaque flux : la première valeur trouvée est gardée.
			merge = self.tags.merge(message.parse_tag(), Gst.TagMergeMode.KEEP)
			if merge is not None:
				self.tags = merge
			return True
		if message.type == Gst.MessageType.ELEMENT:
			structure = message.get_structure()
			if (
				(self.levels is not None)
				and (structure is not None)
				and (message.src == self.measure)
				and (structure.get_name() == "level")
			):
				self.levels.note(structure)
				return True
			if (structure is not None) and (structure.get_name() == "missing-plugin"):
				detail = structure.get_value("detail")
				self.absent_decoder = str(detail)
				if isinstance(detail, Gst.Caps):
					self.absent_decoder = detail.to_string()
			return True
		return False

	def error(self, message: Gst.Message) -> Check:
		error, _debug = message.parse_error()
		if (self.absent_decoder is not None) or (
			error.matches(Gst.StreamError.quark(), Gst.StreamError.CODEC_NOT_FOUND)
		):
			format_absent = (self.absent_decoder) or (_("this format"))
			raise UnavailableDecoder(
				_("no GStreamer decoder for {format_absent}: install {decoder_packages}").format(
					format_absent=format_absent, decoder_packages=DECODER_PACKAGES
				)
			)
		return Check.defective(FileState.UNREADABLE, error.message)

	def decoded_duration(self) -> timedelta | None:
		if (self.tracking.buffers == 0) or (self.tracking.start is None):
			return None
		return _nanoseconds(self.tracking.end - self.tracking.start)

	def silences(self) -> Silences | None:
		"""Les silences mesurés, comptés depuis le début et la fin du son décodé ; None sans mesure."""
		levels = self.levels
		if levels is None:
			return None
		if (levels.first_sound is None) or (levels.sound_end is None) or (self.tracking.start is None):
			return Silences(None, None)
		start = max(0, levels.first_sound - self.tracking.start)
		end = max(0, self.tracking.end - levels.sound_end)
		return Silences(_nanoseconds(start), _nanoseconds(end))


def check_file(
	path: Path,
	delay_without_progress: timedelta = DELAY_WITHOUT_PROGRESS,
	startup_delay: timedelta = STARTUP_DELAY,
	silence_threshold: float | None = None,
) -> Check:
	"""Décode le fichier en entier et rend son verdict, avec la durée effectivement décodée.

	Avec un seuil de silence, en dB crête, le verdict d'un fichier sain donne aussi les silences mesurés au début et à
	la fin (https://github.com/dascritch/machincast/issues/146).

	Un décodage qui ne démarre pas est repris, jusqu'à TENTATIVES fois. Lève UnavailableDecoder si GStreamer
	n'a pas de décodeur pour ce format.
	"""
	if not path.exists():
		return Check.defective(FileState.NOT_FOUND, _("no file at this location"))
	Gst.init(None)
	for _attempt_number in range(ATTEMPTS):
		result = _attempt(path, startup_delay, delay_without_progress, silence_threshold)
		if result is not None:
			return result
	return Check.defective(
		FileState.UNREADABLE,
		_("decoding stuck at startup, no sound decoded in {attempts} attempts of {in_seconds}").format(
			attempts=ATTEMPTS, in_seconds=_in_seconds(startup_delay)
		),
	)


def _attempt(
	path: Path, startup_delay: timedelta, delay_without_progress: timedelta, silence_threshold: float | None = None
) -> Check | None:
	"""Un décodage complet ; None s'il s'est bloqué avant le moindre son décodé, pour qu'il soit repris."""
	decoding = _Decoding(path, silence_threshold)
	blocked = Check.defective(
		FileState.UNREADABLE,
		_("decoding stuck, no sound decoded for {in_seconds}").format(in_seconds=_in_seconds(delay_without_progress)),
	)
	try:
		# Pré-lecture : l'en-tête est lu, la durée annoncée devient connue quand le format la donne.
		decoding.pipeline.set_state(Gst.State.PAUSED)
		message = decoding.wait(Gst.MessageType.ASYNC_DONE, startup_delay, delay_without_progress)
		if message is None:
			if decoding.tracking.buffers > 0:
				return blocked
			return None
		if message.type == Gst.MessageType.ERROR:
			return decoding.error(message)
		known, announced = decoding.pipeline.query_duration(Gst.Format.TIME)
		announced_duration: timedelta | None = None
		if (known) and (announced > 0):
			announced_duration = _nanoseconds(announced)

		decoding.pipeline.set_state(Gst.State.PLAYING)
		message = decoding.wait(Gst.MessageType.EOS, startup_delay, delay_without_progress)
		if message is None:
			if decoding.tracking.buffers > 0:
				return blocked
			return None
		if message.type == Gst.MessageType.ERROR:
			return decoding.error(message)
	finally:
		decoding.release()
	duration = decoding.decoded_duration()
	if (duration is None) or (duration <= timedelta()):
		return Check.defective(FileState.UNREADABLE, _("no sound decoded"))
	if decoding.tracking.breaks > 0:
		return Check.defective(
			FileState.DAMAGED,
			_("{breaks} continuity break(s) while decoding, some data was lost").format(
				breaks=decoding.tracking.breaks
			),
			duration,
		)
	if announced_duration is not None:
		tolerance = max(DURATION_TOLERANCE, announced_duration * TOLERANCE_RELATIVE)
		if duration < announced_duration - tolerance:
			return Check.defective(
				FileState.DAMAGED,
				_(
					"{in_seconds} decoded out of {in_seconds2} announced by the header, truncated file or lost frames"
				).format(in_seconds=_in_seconds(duration), in_seconds2=_in_seconds(announced_duration)),
				duration,
			)
	return Check.healthy(duration, extract(decoding.tags), decoding.silences())
