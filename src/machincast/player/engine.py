"""Moteur audio GStreamer avec crossfade (https://github.com/dascritch/machincast/issues/15, spec § 5.1).

Chaque sonore joue dans sa propre voie : un pipeline playbin3 (machincast.audio.PLAYER) qui sort sur l'élément de
la sortie configurée (machincast.audio), précédé d'un élément volume. Deux voies se superposent pendant un crossfade ;
la sortie mélange leurs sons (PipeWire et PulseAudio le font toujours ; en ALSA, il faut un périphérique qui le
permet, comme « default » avec dmix).

- Crossfade de début : le sonore monte de 0 à plein volume pendant crossfade_start.
- Crossfade de fin : le sonore s'éteint pendant ses crossfade_end dernières secondes, et le sonore suivant démarre
  à ce moment-là (enchainement).
- Les deux sonores ne se superposent que si le sortant a un crossfade de fin et l'entrant un crossfade de début.
  Sinon, le sortant joue jusqu'au bout à plein volume (delete_output_fade), et l'entrant démarre ensuite,
  à plein volume (entry_fade).
- Coupure nette : toutes les voies s'arrêtent aussitôt (début d'un événement, spec § 4.2).
- Stream (https://github.com/dascritch/machincast/issues/16) : la voie lit une adresse HTTP, sans durée connue.
  Elle peut démarrer muette, le temps de vérifier que le flux arrive, puis monter (fondu) ; elle s'éteint en fondu
  et s'arrête d'elle-même à la fin du fondu (eteindre). La source ne retente pas seule une connexion perdue : la
  diffusion s'en charge.

Sonore rogné par la détection de silence (https://github.com/dascritch/machincast/issues/146) : la voie commence à
decalage secondes du début du fichier (son début détecté) et s'arrête d'elle-même après duree secondes (à sa fin
détectée), par une recherche (seek) qui borne la lecture du fichier. La position de la voie, l'enveloppe et les fondus
se comptent depuis ce début : le fichier n'est jamais modifié.

Stream gelé (https://github.com/dascritch/machincast/issues/278) : un stream dont la position n'avance plus pendant
GUARD_DELAY est gelé (gelee) ; la diffusion le tient pour tombé, et sa sonde, pour injoignable.

Lecteur bloqué (https://github.com/dascritch/machincast/issues/281) : playbin se bloquait au démarrage d'un AIFF,
sans erreur ni son, avec GStreamer 1.24 comme avec 1.28 (36 fois sur 300 en temps réel). playbin3, qui le remplace,
ne s'est jamais bloqué (https://github.com/dascritch/machincast/issues/284) ; la garde reste, contre tout lecteur
qui ne démarre pas. Une voie qui n'a pas atteint l'état PLAYING
GUARD_DELAY après son démarrage est bloquée (bloquee) : la diffusion la remplace par le sonore suivant.

Blanc dans un sonore (https://github.com/dascritch/machincast/issues/122) : un élément level, avant l'élément volume,
mesure le niveau du sonore lui-même, sans ses fondus, toutes les LEVEL_MEASURE. Le sonore qui reste
DeadAirSettings.duree sous DeadAirSettings.seuil, en crête sur tous ses canaux, présente un blanc (blanc) : sa
position dans
le fichier, sa durée et son niveau moyen. Un blanc n'est signalé qu'une fois, même s'il dure ; le suivant viendra après
du son. Une voie muette, comme la sonde d'un stream, mesure son son de même (entendue).

Le volume suit une enveloppe posée à l'avance sur l'élément volume (GstController), d'après la durée connue du
sonore. Le moteur ne lit l'heure que par la position des voies : il ne décide de rien, l'ordonnanceur
(machincast.player.rundown) lui dit quoi jouer et quand couper.
"""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Literal, Protocol, cast

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstController", "1.0")
from gi.repository import Gst, GstController  # type: ignore[attr-defined]  # noqa: E402

from machincast.audio import ON_AIR, PLAYER, UnavailableAudioOutput, create_output  # noqa: E402
from machincast.configuration import Audio, DeadAirSettings  # noqa: E402
from machincast.i18n import _  # noqa: E402

TrackState = Literal["ready", "playing", "finished", "cut", "error"]

# GstPlayFlags : audio seulement, sans vidéo ni sous-titres.
ONLY_AUDIO_PLAYBACK = 0x00000002
BUFFERING = 0x00000100
"""Drapeau de playbin3 : la mise en mémoire tampon d'un stream, qui publie son remplissage (messages BUFFERING)."""

PREROLL_DELAY = timedelta(seconds=2)
"""Délai accordé à la pré-lecture d'un fichier rogné, avant la recherche de son début détecté : au-delà, la voie joue
le fichier depuis son début."""

GUARD_DELAY = timedelta(seconds=10)
"""Le même délai de garde dans tous les cas, celui d'un flux HTTP/1.1 qui ne répond plus (DELAI_CONNEXION_SECONDES) :
une voie qui n'a pas atteint l'état PLAYING au bout de ce délai est bloquée
(https://github.com/dascritch/machincast/issues/281) ; un stream qui ne donne plus de son pendant ce délai est gelé
(https://github.com/dascritch/machincast/issues/278)."""

PREFILL_MARGIN = 1.5
"""Au-delà de sa durée fois cette marge, une mémoire tampon qui ne se remplit pas n'est plus attendue
(https://github.com/dascritch/machincast/issues/351) : le flux arrive en temps réel, la durée devrait suffire."""
CONNECTION_DELAY_SECONDS = round(GUARD_DELAY.total_seconds())
"""Délai de connexion et de réponse d'un flux HTTP, au-delà duquel la voie passe en erreur : le délai de garde."""

LEVEL_MEASURE = timedelta(milliseconds=100)
"""Intervalle entre deux mesures du niveau d'une voie (https://github.com/dascritch/machincast/issues/122)."""
NUMERIC_SILENCE = -200.0
"""Niveau moyen, en dB, sous lequel un blanc est un silence numérique : level donne -700 dB pour des zéros."""


@dataclass(frozen=True)
class DeadAir:
	"""Un blanc dans un sonore (https://github.com/dascritch/machincast/issues/122)."""

	position: timedelta
	"""Position de son début dans le fichier ; depuis le début de la voie pour un stream."""
	duration: timedelta
	"""Durée mesurée quand il a été constaté : la durée d'un blanc, au moins."""
	level: float | None
	"""Niveau moyen (RMS), en dB ; None pour un silence numérique."""


def mean_level(measures: list[tuple[float, float]]) -> float | None:
	"""Niveau moyen de mesures (RMS en dB, durée en secondes), en énergie ; None pour un silence numérique."""
	duration = sum(seconds for _rms, seconds in measures)
	energy = sum((10 ** (rms / 10)) * seconds for rms, seconds in measures)
	if (duration <= 0) or (energy <= 0):
		return None
	level = 10 * math.log10(energy / duration)
	if level < NUMERIC_SILENCE:
		return None
	return level


def overlay(outgoing_end_crossfade: timedelta, incoming_start_crossfade: timedelta) -> bool:
	"""Deux sonores ne se superposent que si chacun a son crossfade, de fin pour l'un, de début pour l'autre."""
	return (outgoing_end_crossfade > timedelta(0)) and (incoming_start_crossfade > timedelta(0))


def sequencing(duration: timedelta, end_crossfade: timedelta, following_start_crossfade: timedelta) -> timedelta:
	"""Après combien de temps le sonore suivant démarre : avant la fin du crossfade s'ils se superposent."""
	if overlay(end_crossfade, following_start_crossfade):
		return max(timedelta(0), duration - end_crossfade)
	return duration


def entry_fade(previous_end_crossfade: timedelta, start_crossfade: timedelta) -> timedelta:
	"""Durée de la montée du sonore entrant : son crossfade de début s'il se superpose au précédent, sinon rien."""
	if not overlay(previous_end_crossfade, start_crossfade):
		return timedelta(0)
	return start_crossfade


def envelope(
	duration: timedelta | None,
	start_crossfade: timedelta,
	end_crossfade: timedelta,
	departure: float = 0.0,
	arrival: float = 0.0,
) -> list[tuple[timedelta, float]]:
	"""Points du volume au fil du sonore, reliés par des droites : montée, plein volume, extinction. Un fade-in qui a
	commencé avant le fichier part du volume depart ; un fade-out qui finit après lui s'arrête au volume arrivee
	(https://github.com/dascritch/machincast/issues/234)."""
	points: list[tuple[timedelta, float]] = []
	if start_crossfade > timedelta(0):
		points += [(timedelta(0), departure), (start_crossfade, 1.0)]
	else:
		points.append((timedelta(0), 1.0))
	if (duration is not None) and (end_crossfade > timedelta(0)):
		points += [(max(duration - end_crossfade, points[-1][0]), 1.0), (duration, arrival)]
	return points


def _nanoseconds(duration: timedelta) -> int:
	return round(duration.total_seconds() * Gst.SECOND)


class Track:
	"""Un sonore joué sur la sortie, avec son enveloppe de volume."""

	def __init__(
		self,
		path: Path | str,
		audio: Audio,
		duration: timedelta | None,
		start_crossfade: timedelta = timedelta(0),
		end_crossfade: timedelta = timedelta(0),
		real_time: bool = True,
		silent: bool = False,
		offset: timedelta | None = None,
		departure: float = 0.0,
		arrival: float = 0.0,
		clock: Callable[[], float] = time.monotonic,
		dead_air: DeadAirSettings | None = None,
		buffer: timedelta | None = None,
	) -> None:
		"""chemin : un fichier, ou l'adresse d'un stream. Muette, la voie joue à volume nul jusqu'à un fondu.

		depart, arrivee : volumes au début et à la fin de la voie, quand ses fondus débordent du fichier
		(https://github.com/dascritch/machincast/issues/234, machincast.player.fades).

		decalage : pour un sonore rogné par la détection de silence, la voie commence à cette position du fichier, et
		s'arrête après duree (https://github.com/dascritch/machincast/issues/146) ; None : le fichier est joué en
		entier.

		blanc : la durée et le seuil d'un blanc dans le sonore (https://github.com/dascritch/machincast/issues/122) ;
		ceux de la configuration par défaut, sans lui.

		tampon : pour le stream d'un feed, la durée de sa mémoire tampon
		(https://github.com/dascritch/machincast/issues/351) : la voie attend qu'elle soit pleine pour jouer, et en
		publie le remplissage (tampon_rempli) ; None : le stream joue dès son premier son, comme un fichier."""
		Gst.init(None)
		self.path = path
		self.state: TrackState = "ready"
		self.error: str | None = None
		self.offset = timedelta(0)
		"""Position du fichier où la voie commence : son début détecté ; 0 pour un sonore joué en entier."""
		self._trimmed = (offset is not None) and (not isinstance(path, str))
		"""La voie ne joue qu'une partie du fichier, du début détecté à la fin détectée."""
		if offset is not None:
			self.offset = max(offset, timedelta(0))
		self.final_position: timedelta | None = None
		"""Position atteinte quand la voie a été coupée, ou quand elle s'est finie."""
		self.planned_stop: timedelta | None = None
		"""Position où la voie s'arrête d'elle-même, à la fin d'un fondu de sortie (eteindre)."""

		player = Gst.ElementFactory.make(PLAYER, None)
		volume = Gst.ElementFactory.make("volume", None)
		level = Gst.ElementFactory.make("level", None)
		if (player is None) or (volume is None) or (level is None):
			raise UnavailableAudioOutput(
				_(
					"{player}, volume or level not found, install gstreamer1.0-plugins-base and "
					"gstreamer1.0-plugins-good"
				).format(player=PLAYER)
			)
		level.set_property("interval", _nanoseconds(LEVEL_MEASURE))
		level.set_property("post-messages", True)
		output = create_output(*audio.on_air(), presentation=ON_AIR)
		# Une vraie sortie suit l'horloge ; la sortie factice peut aller au plus vite, pour les tests.
		output.set_property("sync", real_time)
		factory = output.get_factory()
		self.output_factory: str | None = ""
		if factory is not None:
			self.output_factory = factory.get_name()

		# Le niveau se mesure avant le volume : les fondus ne sont pas des blancs.
		plugged = Gst.Bin.new(None)
		plugged.add(level)
		plugged.add(volume)
		plugged.add(output)
		level.link(volume)
		volume.link(output)
		entry = level.get_static_pad("sink")
		assert entry is not None
		plugged.add_pad(Gst.GhostPad.new("sink", entry))

		self.buffer = None
		"""Durée de la mémoire tampon du stream d'un feed ; None sinon."""
		self.buffering = 0
		"""Remplissage de la mémoire tampon, en pour cent, d'après le dernier message BUFFERING."""
		self._prefilling = False
		"""La voie attend que sa mémoire tampon soit pleine pour jouer."""
		flags = ONLY_AUDIO_PLAYBACK
		if (isinstance(path, str)) and (buffer is not None):
			self.buffer = buffer
			flags |= BUFFERING
			player.set_property("buffer-duration", _nanoseconds(buffer))
		player.set_property("flags", flags)
		player.set_property("audio-sink", plugged)
		address: Path | str | None = path
		if not isinstance(path, str):
			address = Gst.filename_to_uri(str(path.absolute()))
		player.set_property("uri", address)
		player.connect("source-setup", _set_source)

		source = GstController.InterpolationControlSource()
		source.set_property("mode", GstController.InterpolationMode.LINEAR)
		points = [(timedelta(0), 0.0)]
		if not silent:
			points = envelope(duration, start_crossfade, end_crossfade, departure, arrival)
		volume.add_control_binding(GstController.DirectControlBinding.new_absolute(volume, "volume", source))

		self._player = player
		self._clock = clock
		self._started_to: float | None = None
		"""Instant du démarrage, à l'horloge de la voie : pour constater un lecteur bloqué."""
		self._has_played = False
		self._last_position = timedelta(0)
		self._advance_at: float | None = None
		"""Instant où la position a avancé pour la dernière fois, à l'horloge de la voie ; son démarrage d'abord."""
		"""La voie a atteint l'état PLAYING : elle n'est plus bloquée au démarrage."""
		self._dead_air = (dead_air) or (DeadAirSettings())
		self._under_threshold: list[tuple[float, float]] = []
		"""Mesures du blanc en cours (RMS en dB, durée en secondes), depuis la dernière mesure au-dessus du seuil."""
		self._dead_air_start: timedelta | None = None
		self._reported = False
		"""Le blanc en cours a été signalé."""
		self._dead_airs: list[DeadAir] = []
		"""Blancs constatés, pas encore demandés (blanc)."""
		self._heard = False
		self._volume = volume
		self._source = source
		self._duration = duration
		self._start_crossfade = start_crossfade
		self._departure = departure
		for instant, value in points:
			self._set(instant, value)

	def _set(self, instant: timedelta, value: float) -> None:
		"""Un point de l'enveloppe, à cet instant de la voie : l'élément volume suit la position dans le fichier."""
		self._source.set(_nanoseconds(self.offset + instant), value)

	def delete_output_fade(self) -> None:
		"""Le sonore suivant ne se superpose pas : celui-ci joue jusqu'au bout, à plein volume."""
		self._source.unset_all()
		for instant, value in envelope(self._duration, self._start_crossfade, timedelta(0), self._departure):
			self._set(instant, value)

	def fade(self, target: float, duration: timedelta) -> None:
		"""Le volume va de sa valeur actuelle à la cible pendant la durée, à partir de la position actuelle."""
		position = self.position()
		current = self.volume_to(position)
		self._source.unset_all()
		if duration > timedelta(0):
			self._set(position, current)
		self._set(position + duration, target)

	def switch_off(self, duration: timedelta) -> None:
		"""Fondu de sortie à partir de maintenant ; la voie s'arrête à la fin du fondu, aussitôt sans durée."""
		if duration <= timedelta(0):
			self.planned_stop = self.position()
			self.handle()
			return
		self.fade(0.0, duration)
		self.planned_stop = self.position() + duration

	def volume_to(self, instant: timedelta) -> float:
		"""Volume prévu à cet instant du sonore, entre 0 et 1."""
		value = self._volume.get_value("volume", _nanoseconds(self.offset + instant))
		if value is None:
			return 1.0
		return float(value)

	def position(self) -> timedelta:
		"""Position de la voie, depuis son début : pour un sonore rogné, depuis son début détecté."""
		found, nanoseconds = self._player.query_position(Gst.Format.TIME)
		if not found:
			return timedelta(0)
		return max(timedelta(0), timedelta(microseconds=nanoseconds / 1000) - self.offset)

	def start(self) -> None:
		self.state = "playing"
		self._started_to = self._clock()
		self._advance_at = self._started_to
		if self._trimmed:
			self._bound()
		target = Gst.State.PLAYING
		if self.buffer is not None:
			# Le stream d'un feed attend sa mémoire tampon (https://github.com/dascritch/machincast/issues/351).
			self._prefilling = True
			target = Gst.State.PAUSED
		if self._player.set_state(target) == Gst.StateChangeReturn.FAILURE:
			self.handle()

	def take_air(self) -> None:
		"""Une voie préchargée prend l'antenne (https://github.com/dascritch/machincast/issues/351) : sa position
		repart de zéro, comme celle d'une voie qui démarre, pour l'enveloppe, le gel et la socket d'état."""
		found, nanoseconds = self._player.query_position(Gst.Format.TIME)
		if found:
			self.offset = timedelta(microseconds=nanoseconds / 1000)
		self._last_position = timedelta(0)
		self._advance_at = self._clock()

	def buffer_level(self) -> timedelta | None:
		"""Ce que contient la mémoire tampon du stream d'un feed, d'après son remplissage ; None sans elle."""
		if self.buffer is None:
			return None
		return self.buffer * min(self.buffering, 100) / 100

	def _grace(self) -> float:
		"""Le délai de garde, allongé de la mémoire tampon tant qu'elle se remplit, avant le premier son."""
		guard = GUARD_DELAY.total_seconds()
		if (self.buffer is not None) and (self._last_position == timedelta(0)):
			guard += self.buffer.total_seconds()
		return guard

	def _fill(self, percent: int) -> None:
		"""Un message BUFFERING : la voie qui attendait joue dès que sa mémoire tampon est pleine."""
		self.buffering = percent
		if (self._prefilling) and (percent >= 100):
			self._play_now()

	def _play_now(self) -> None:
		self._prefilling = False
		if self._player.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
			self.state, self.error = "error", _("the stream did not start after its buffer")

	def blocked(self) -> bool:
		"""Le lecteur n'a pas atteint l'état PLAYING GUARD_DELAY après son démarrage, sans erreur ni fin : il
		ne jouera rien (https://github.com/dascritch/machincast/issues/281). Jamais bloquée une fois qu'elle a joué."""
		if (self.state != "playing") or (self._started_to is None) or (self._has_played):
			return False
		_result, current, _expected = self._player.get_state(0)
		if current == Gst.State.PLAYING:
			self._has_played = True
			return False
		return self._clock() - self._started_to >= self._grace()

	def frozen(self) -> bool:
		"""Aucun son depuis GUARD_DELAY : la position n'a pas avancé depuis le démarrage de la voie, ou depuis sa
		dernière avance, sans erreur ni fin (https://github.com/dascritch/machincast/issues/278). C'est ce que fait un
		flux qui ne donne plus rien sans fermer sa connexion, quand le lecteur ne le signale pas : en HTTP/2, libsoup 3
		ne remonte pas l'expiration de son délai. À demander à chaque pas : chaque appel note l'avance de la
		position."""
		if (self.state != "playing") or (self._advance_at is None):
			return False
		now = self._clock()
		position = self.position()
		if position > self._last_position:
			self._last_position, self._advance_at = position, now
			return False
		return now - self._advance_at >= self._grace()

	def dead_air(self) -> DeadAir | None:
		"""Le premier blanc constaté dans le sonore depuis la dernière demande, une seule fois chacun
		(https://github.com/dascritch/machincast/issues/122) ; les mesures se lisent à traiter."""
		if self._dead_airs == []:
			return None
		return self._dead_airs.pop(0)

	def heard(self) -> bool:
		"""La dernière mesure du niveau est au-dessus du seuil d'un blanc : le sonore donne du son, même voie
		muette."""
		return self._heard

	def _measure(self, structure: Gst.Structure) -> None:
		"""Une mesure de l'élément level : la crête la plus haute de ses canaux dit si le sonore donne du son. La mesure
		vide que level donne à la fin du fichier ne compte pas : elle dit -350 dB."""
		nanoseconds = cast(int, structure.get_value("duration"))
		if nanoseconds <= 0:
			return
		duration = nanoseconds / Gst.SECOND
		peak = max(cast(list[float], structure.get_value("peak")))
		rms = max(cast(list[float], structure.get_value("rms")))
		position = timedelta(microseconds=cast(int, structure.get_value("stream-time")) / 1000)
		self._heard = peak >= self._dead_air.threshold
		if self._heard:
			self._under_threshold, self._dead_air_start, self._reported = [], None, False
			return
		if self._dead_air_start is None:
			self._dead_air_start = position
		self._under_threshold.append((rms, duration))
		measure = timedelta(seconds=sum(seconds for _rms, seconds in self._under_threshold))
		if (not self._reported) and (measure >= self._dead_air.duration):
			self._reported = True
			self._dead_airs.append(DeadAir(self._dead_air_start, measure, mean_level(self._under_threshold)))

	def _bound(self) -> None:
		"""Pré-lit le fichier, puis borne sa lecture : du début détecté à la fin détectée
		(https://github.com/dascritch/machincast/issues/146). Un fichier qui ne se pré-lit pas est joué en entier ;
		son erreur viendra à la lecture."""
		if self._player.set_state(Gst.State.PAUSED) == Gst.StateChangeReturn.FAILURE:
			return
		result, _state, _expected = self._player.get_state(_nanoseconds(PREROLL_DELAY))
		if result == Gst.StateChangeReturn.FAILURE:
			return
		type_end, end = Gst.SeekType.NONE, -1
		if self._duration is not None:
			type_end, end = Gst.SeekType.SET, _nanoseconds(self.offset + self._duration)
		self._player.seek(
			1.0,
			Gst.Format.TIME,
			Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
			Gst.SeekType.SET,
			_nanoseconds(self.offset),
			type_end,
			end,
		)
		self._player.get_state(_nanoseconds(PREROLL_DELAY))

	def cut(self) -> None:
		"""Arrêt net, sans fondu."""
		if self.state == "playing":
			self.final_position = self.position()
			self.state = "cut"
		self._player.set_state(Gst.State.NULL)

	def handle(self) -> None:
		"""Lit les messages du pipeline : fin du sonore, ou erreur de lecture ; arrête la voie à la fin d'un fondu
		de sortie."""
		if (self.state == "playing") and (self.planned_stop is not None) and (self.position() >= self.planned_stop):
			self.state = "finished"
			self._player.set_state(Gst.State.NULL)
			return
		if (
			(self._prefilling)
			and (self.buffer is not None)
			and (self._started_to is not None)
			and (self._clock() - self._started_to >= self.buffer.total_seconds() * PREFILL_MARGIN)
		):
			# Un flux plus lent que le temps réel ne remplit jamais sa mémoire tampon : la voie joue ce qu'elle a.
			self._play_now()
		bus = self._player.get_bus()
		wanted = Gst.MessageType.EOS | Gst.MessageType.ERROR | Gst.MessageType.ELEMENT | Gst.MessageType.BUFFERING
		while (self.state == "playing") and (bus is not None):
			message = bus.pop_filtered(wanted)
			if message is None:
				return
			if message.type == Gst.MessageType.BUFFERING:
				self._fill(message.parse_buffering())
				continue
			structure = message.get_structure()
			if message.type == Gst.MessageType.ELEMENT:
				if (structure is not None) and (structure.get_name() == "level"):
					self._measure(structure)
				continue
			if message.type == Gst.MessageType.ERROR:
				error, _debug = message.parse_error()
				self.state, self.error = "error", error.message
			else:
				self.state = "finished"
				self.final_position = self.position()
			self._player.set_state(Gst.State.NULL)

	def shut_down(self) -> None:
		self._player.set_state(Gst.State.NULL)


def _set_source(player: Gst.Element, source: Gst.Element) -> None:
	"""Source HTTP d'un stream : pas de nouvelle tentative de la source elle-même, et un délai de réponse borné."""
	if hasattr(source.props, "retries"):
		source.set_property("retries", 0)
	if hasattr(source.props, "timeout"):
		source.set_property("timeout", CONNECTION_DELAY_SECONDS)


class PlaybackTrack(Protocol):
	"""Ce que la diffusion attend d'une voie : la voie GStreamer (Voie), ou la voie simulée de la simulation."""

	state: TrackState
	error: str | None

	def position(self) -> timedelta: ...

	def blocked(self) -> bool: ...

	def frozen(self) -> bool: ...

	def dead_air(self) -> DeadAir | None: ...

	def heard(self) -> bool: ...

	def handle(self) -> None: ...

	def cut(self) -> None: ...

	def shut_down(self) -> None: ...

	def fade(self, target: float, duration: timedelta) -> None: ...

	def switch_off(self, duration: timedelta) -> None: ...

	def delete_output_fade(self) -> None: ...

	def volume_to(self, instant: timedelta) -> float: ...

	def buffer_level(self) -> timedelta | None: ...

	def take_air(self) -> None: ...


class Engine(Protocol):
	"""Ce que la diffusion attend du moteur : AudioEngine, ou le moteur simulé de la simulation."""

	def play(
		self,
		path: Path | str,
		duration: timedelta | None,
		start_crossfade: timedelta = ...,
		end_crossfade: timedelta = ...,
		silent: bool = ...,
		offset: timedelta | None = ...,
		departure: float = ...,
		arrival: float = ...,
		buffer: timedelta | None = ...,
	) -> PlaybackTrack: ...

	def handle_messages(self) -> None: ...

	def cut(self) -> None: ...

	def shut_down(self) -> None: ...


class AudioEngine:
	"""Joue les sonores sur la sortie de la configuration, une voie par sonore."""

	def __init__(
		self,
		audio: Audio,
		real_time: bool = True,
		clock: Callable[[], float] = time.monotonic,
		dead_air: DeadAirSettings | None = None,
	) -> None:
		self.audio = audio
		self.real_time = real_time
		self.clock = clock
		self.dead_air = (dead_air) or (DeadAirSettings())
		"""La durée et le seuil d'un blanc dans un sonore (https://github.com/dascritch/machincast/issues/122)."""
		"""L'horloge des voies, qui constate un lecteur bloqué ; les scénarios la remplacent."""
		self._tracks: list[Track] = []

	def play(
		self,
		path: Path | str,
		duration: timedelta | None,
		start_crossfade: timedelta = timedelta(0),
		end_crossfade: timedelta = timedelta(0),
		silent: bool = False,
		offset: timedelta | None = None,
		departure: float = 0.0,
		arrival: float = 0.0,
		buffer: timedelta | None = None,
	) -> Track:
		"""Démarre le sonore dans une nouvelle voie, en plus de celles en cours (crossfade) ; un sonore rogné commence à
		decalage secondes du début de son fichier (https://github.com/dascritch/machincast/issues/146)."""
		track = Track(
			path,
			self.audio,
			duration,
			start_crossfade,
			end_crossfade,
			self.real_time,
			silent,
			offset,
			departure,
			arrival,
			self.clock,
			self.dead_air,
			buffer,
		)
		track.start()
		self._tracks.append(track)
		return track

	def handle_messages(self) -> None:
		for track in self._tracks:
			track.handle()
		self._tracks = [track for track in self._tracks if track.state == "playing"]

	def ongoing_tracks(self) -> list[Track]:
		return [track for track in self._tracks if track.state == "playing"]

	def cut(self) -> None:
		"""Coupure nette de toutes les voies en cours."""
		for track in self._tracks:
			track.cut()
		self._tracks = []

	def shut_down(self) -> None:
		for track in self._tracks:
			track.shut_down()
		self._tracks = []
