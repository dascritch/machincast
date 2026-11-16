"""Les données de la boucle de diffusion (https://github.com/dascritch/machincast/issues/440) : ce que le moteur doit
savoir d'un sonore (Parameters, read_parameters), le sonore en cours (Playback), le prochain (Reserve), ceux prévus
(Planned, Preload) et la sonde d'un stream tombé (Probe). machincast.player.broadcast les assemble."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import psycopg
from psycopg.rows import TupleRow

from machincast.configuration import Crossfades
from machincast.conversion import integer_or_none, text_or_none
from machincast.i18n import N_
from machincast.player.engine import (
	PlaybackTrack,
)
from machincast.player.fades import Placement, put
from machincast.player.grid import Priority
from machincast.player.rundown import Choice, Cutoff, Ongoing
from machincast.player.saving import Play

log = logging.getLogger(__name__)

NO_CROSSFADE = timedelta(0)
PRIORITIES = {
	Priority.BREAKING: N_("breaking"),
	Priority.SPECIAL: N_("special"),
	Priority.SHOW: N_("show"),
	Priority.BACKGROUND_PROGRAMMING: N_("background programming"),
	Priority.FALLBACK: N_("fallback"),
}
WITHOUT_DEFECTS = Crossfades()
"""Une configuration sans crossfades par défaut."""
CUTOFF_HORIZON = timedelta(hours=12)
"""Jusqu'où chercher l'événement qui coupera un sonore de durée inconnue, un stream
(https://github.com/dascritch/machincast/issues/169)."""


def crossfade(of_sound: object, rule: object, of_the_bank: object, default: timedelta | None = None) -> timedelta:
	"""Le crossfade retenu, d'un côté : celui que la banque impose ; sinon celui du sonore, s'il est paramétré
	(0 seconde en est un) ; sinon celui que la banque applique à défaut ; sinon celui de la configuration ; sinon
	aucun. Sans banque, la règle est None (https://github.com/dascritch/machincast/issues/145)."""
	bank = NO_CROSSFADE
	if isinstance(of_the_bank, timedelta):
		bank = of_the_bank
	if rule == "forced":
		return bank
	if isinstance(of_sound, timedelta):
		return of_sound
	if rule == "default":
		return bank
	return (default) or (NO_CROSSFADE)


@dataclass(frozen=True)
class Parameters:
	"""Ce que le moteur audio doit savoir d'un sonore."""

	duration: timedelta | None
	start_crossfade: timedelta
	end_crossfade: timedelta
	stream: bool = False
	address: str | None = None
	"""Adresse d'un stream : directe, ou celle de son feed."""
	location: str | None = None
	"""Chemin du fichier, ou adresse du stream, comme dans l'airplay
	(https://github.com/dascritch/machincast/issues/23)."""
	fallback: int | None = None
	"""Événement de secours d'un stream."""
	artist: str | None = None
	title: str | None = None
	offset: timedelta | None = None
	"""Sonore rogné par la détection de silence (https://github.com/dascritch/machincast/issues/146) : d'où part la
	lecture du fichier, selon la position de son fade-in (https://github.com/dascritch/machincast/issues/234) ; sa durée
	est alors celle de la partie jouée. None : joué en entier."""
	departure_volume: float = 0.0
	"""Volume au début de la lecture, quand le fade-in déborde avant le début du fichier ; 0 sinon."""
	arrival_volume: float = 0.0
	"""Volume à la fin de la lecture, quand le fade-out déborde après la fin du fichier ; 0 sinon."""
	buffer: timedelta | None = None
	"""Mémoire tampon du stream d'un feed (https://github.com/dascritch/machincast/issues/351) ; None sinon."""


PRELOAD = timedelta(seconds=30)
"""Le stream d'un feed se charge, muet, cette avance avant de prendre l'antenne
(https://github.com/dascritch/machincast/issues/351) : sa mémoire tampon est pleine quand il commence, sans blanc."""


@dataclass
class Preload:
	"""La voie muette du prochain sonore, un stream de feed, qui se charge avant de prendre l'antenne."""

	sound: int
	track: PlaybackTrack


@dataclass
class Playback:
	"""Un sonore sur la sortie : son choix, sa voie et son passage dans l'airplay."""

	choice: Choice
	parameters: Parameters
	track: PlaybackTrack
	play: Play
	following_requested: bool = False
	"""L'ordonnanceur a déjà donné le sonore suivant, au début du crossfade de fin."""
	off: bool = False
	"""La voie s'éteint en fondu et s'arrêtera d'elle-même : la fin du passage est normale."""
	details: dict[str, Any] | None = None
	"""Ce que la socket d'état dit de son contexte, lu une fois (Diffusion._details)."""
	cutoff: Cutoff | None = None
	"""L'événement qui le coupera net, cherché à sa réservation (https://github.com/dascritch/machincast/issues/169)."""

	@property
	def ongoing(self) -> Ongoing:
		start = self.play.start
		planned_end = start + ((self.parameters.duration) or (timedelta(0)))
		return Ongoing(self.choice.occurrence, start, planned_end, self.parameters.stream)


@dataclass(frozen=True)
class Reserve:
	"""Prochain sonore, réservé au début du sonore en cours (https://github.com/dascritch/machincast/issues/20)."""

	choice: Choice
	parameters: Parameters
	healthy: bool | None
	"""Indicateur « sain » (spec § 4.6) ; None pour un stream."""
	early: bool = False
	"""Réservé pour après une coupure : seulement annoncé, il sera choisi par la décision prise à la coupure, qui
	consigne ce qu'il faut (https://github.com/dascritch/machincast/issues/169)."""


@dataclass(frozen=True)
class Planned:
	"""Un sonore à venir, après le prochain (https://github.com/dascritch/machincast/issues/228) : engagé, il sera joué
	si rien d'imprévu n'arrive."""

	choice: Choice
	parameters: Parameters
	healthy: bool | None
	cutoff: Cutoff | None
	"""L'événement qui coupe net le sonore précédent, au début duquel celui-ci démarre ; None s'il enchaîne."""
	finished_list: frozenset[tuple[int, datetime | None]]
	"""Occurrences terminées par l'ordonnanceur une fois ce sonore choisi (Ordonnanceur.engager)."""
	details: dict[str, Any] = field(default_factory=dict, compare=False)
	"""Ce que la socket d'état dit de son contexte (Diffusion._details), lu une fois."""
	recorded_list: tuple[dict[str, Any], ...] = field(default=(), compare=False)
	"""Ce que sa décision consignerait, comme un élément sauté : consigné quand il devient le prochain sonore."""


@dataclass
class Probe:
	"""Reconnexion d'un stream tombé : une voie muette, retentée tous les reconnection_delay."""

	choice: Choice
	parameters: Parameters
	next_attempt: datetime
	since: datetime
	"""Heure de la panne."""
	track: PlaybackTrack | None = None
	dead_air: bool = False
	"""Le stream a laissé l'antenne sur un blanc (https://github.com/dascritch/machincast/issues/122) : sa voie,
	gardée ouverte, ne reprend qu'avec du son."""


def read_parameters(
	connection: psycopg.Connection[TupleRow], choice: Choice, defects: Crossfades = WITHOUT_DEFECTS
) -> Parameters:
	"""Ce qu'il faut pour jouer le sonore choisi. Ses crossfades suivent les règles de la banque qui l'a fourni
	(https://github.com/dascritch/machincast/issues/143), puis, s'il n'en a pas de paramétré, les crossfades par défaut
	de la configuration (https://github.com/dascritch/machincast/issues/145). Un fichier qui active la détection de
	silence, ou fourni par une banque qui l'active, est joué sans ses silences détectés
	(https://github.com/dascritch/machincast/issues/146, machincast.player.fades.put)."""
	with connection.transaction():
		line = connection.execute(
			"SELECT s.duration, s.crossfade_start, s.crossfade_end, s.type::text, COALESCE(s.stream_url, m.url),"
			" s.fallback_event_id, s.artist, s.title, COALESCE(s.location, s.stream_url, m.url),"
			" s.silence_detection OR COALESCE(b.silence_detection, false), s.detected_start, s.detected_end,"
			" b.crossfade_start_rule::text, b.crossfade_start, b.crossfade_end_rule::text, b.crossfade_end,"
			" m.buffer_duration"
			" FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id"
			" LEFT JOIN banks b ON b.id = %s"
			" WHERE s.id = %s",
			(choice.bank, choice.sound),
		).fetchone()
	if line is None:
		return Parameters(None, timedelta(0), timedelta(0))
	duration, start, end, sound_type, address, fallback, artist, title, location, *remainder = line
	detection, detected_start, detected_end, start_rule, bank_start, end_rule, bank_end, buffer = remainder
	start_crossfade = crossfade(start, start_rule, bank_start, defects.start)
	end_crossfade = crossfade(end, end_rule, bank_end, defects.end)
	# Sans durée connue (un stream), les crossfades restent tels quels.
	placement = Placement(timedelta(0), None, start_crossfade, 0.0, end_crossfade, 0.0)
	played_duration = None
	if isinstance(duration, timedelta):
		placement = put(
			duration,
			_interval(detected_start),
			_interval(detected_end),
			(detection is True) and (sound_type == "file"),
			start_crossfade,
			end_crossfade,
			defects.entry,
			defects.output,
		)
		played_duration = placement.duration
	return Parameters(
		played_duration,
		placement.entry_fade,
		placement.output_fade,
		stream=sound_type == "stream",
		address=text_or_none(address),
		fallback=integer_or_none(fallback),
		artist=text_or_none(artist),
		title=text_or_none(title),
		location=text_or_none(location),
		offset=placement.offset,
		departure_volume=placement.departure,
		arrival_volume=placement.arrival,
		buffer=_interval(buffer),
	)


def _interval(value: object) -> timedelta | None:
	if isinstance(value, timedelta):
		return value
	return None
