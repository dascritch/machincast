"""Boucle de diffusion de Machin player (https://github.com/dascritch/machincast/issues/88, spec § 5).

Assemble l'ordonnanceur (machincast.player.rundown), le moteur audio (machincast.player.engine), la vérification
des fichiers (machincast.player.files) et l'enregistrement (machincast.player.saving). La diffusion
avance par pas, à l'heure de son horloge ; à chaque pas :

1. les voies finies, ou en erreur, terminent leur passage dans l'airplay ;
2. pendant un sonore, l'ordonnanceur dit s'il faut le couper net (début d'un événement) : toutes les voies
   s'arrêtent, et le sonore de l'événement démarre aussitôt, sans fondu ;
3. quand le sonore atteint le début de son crossfade de fin (enchainement), l'ordonnanceur donne le suivant. Si les
   deux sonores se superposent (chacun son crossfade), le suivant démarre aussitôt avec sa montée ; sinon, le
   sonore en cours joue jusqu'au bout à plein volume, et le suivant attend sa fin ;
4. sans rien sur la sortie, le sonore en attente démarre, ou celui que l'ordonnanceur donne ; sinon, un blanc.

Avant de jouer un sonore, son fichier est vérifié : introuvable, il est écarté par l'ordonnanceur, et le suivant
est demandé. L'arrêt termine les passages en cours, sans incident, puis consigne l'arrêt.

Streams (https://github.com/dascritch/machincast/issues/16, spec § 4.7) :

- à la fin de son événement, le stream s'éteint pendant son crossfade de fin ; le sonore suivant se superpose s'il a
  un crossfade de début, sinon il attend la fin du fondu ;
- un flux qui s'arrête ou qui ne répond pas, avant la fin de son événement, est tombé : son passage se termine en
  incident « flux tombé », et l'ordonnanceur remplace l'événement (Ordonnanceur.suspendre). Une sonde, voie
  muette, retente la connexion tous les reconnection_delay ; dès que le flux arrive, le stream monte pendant son
  crossfade de début et les sonores de remplacement s'éteignent pendant ce temps (coupure nette sans crossfade de
  début), et l'incident « reprise du flux » donne la durée de la panne ;
- si l'événement du stream n'est plus actif, la reconnexion est abandonnée.

Blanc dans un sonore (https://github.com/dascritch/machincast/issues/122, engine.Track.blanc) : le sonore en cours qui
reste DeadAirSettings.duree sous DeadAirSettings.seuil est noté en incident « blanc dans un sonore », avec sa position
et son
niveau moyen. Avec DeadAirSettings.secours, un fichier laisse aussitôt l'antenne au sonore suivant, son passage
terminé en
incident ; un stream la laisse à son secours, comme un flux tombé, mais sa voie reste ouverte, muette, comme sonde : il
reprend l'antenne, en fondu, dès que son son revient (Voie.entendue). Sans DeadAirSettings.secours, le blanc est
seulement
noté. À ne pas confondre avec l'alerte « blanc », rien à diffuser, ni avec un silence, qui borne un fichier
(https://github.com/dascritch/machincast/issues/291).

Playlist immédiate (https://github.com/dascritch/machincast/issues/228) : après le prochain sonore, réservé au début
du sonore en cours, la diffusion prévoit les UPCOMING sonores suivants (upcoming), chacun à l'heure où il serait choisi,
en tenant compte des coupures par les événements qui commencent. Ils sont engagés : à chaque changement de sonore, si
c'est le prochain sonore qui a démarré, que la grille n'a pas changé et que la coupure du sonore en cours est celle
qui était prévue, le premier sonore à venir devient le prochain, et un nouveau est prévu au bout de la liste ; sinon,
sur un imprévu, le prochain sonore et toute la liste sont recalculés. Un sonore à venir qui n'est plus jouable à son
tour est remplacé par la décision de l'ordonnanceur, qui fait recalculer la liste.

Interruption manuelle (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228, interrompre) : demandée par l'interface sur la socket d'état, et
traitée au début du pas suivant. Le sonore en cours s'éteint aussitôt pendant le crossfade de fin par défaut de la
configuration, ou s'arrête net sans lui ; son passage se termine sans incident, et le suivant démarre avec le crossfade
de début par défaut, ou à plein volume : le prochain sonore pour un sonore, le premier sonore prévu après la séquence
pour une séquence (les sonores à venir qui le suivent sont gardés), le fil musical pour un événement
(Ordonnanceur.return_to_background_programming). Le log note l'info « interruption manuelle », avec ce qui est
interrompu. Sans
rien à l'antenne, hors d'une séquence pour une séquence, ou dans le fil musical pour un événement, la demande est
ignorée et signalée dans le journal du binaire.

Coupure par le secours ou par un feed (https://github.com/dascritch/machincast/issues/323, cut_by_fallback,
cut_by_feed) : demandée de même, et traitée comme une interruption de l'événement : le sonore en cours s'éteint,
une séquence en cours ne continue pas, et le remplacement de l'ordonnanceur (Ordonnanceur.cut_by) tient l'antenne
jusqu'à la fin prévue de l'événement coupé, ou, sous le fil musical, jusqu'à l'événement suivant. Le log note
l'« interruption manuelle », avec ce qui est coupé et par quoi. Sans rien à l'antenne, avec un secours inconnu,
supprimé ou qui n'est pas de priorité secours, ou un feed qu'aucun stream actif ne suit, la demande est ignorée et
signalée dans le journal du binaire. Un feed qui tombe rend l'antenne à la grille, sans reconnexion.

Expiration (https://github.com/dascritch/machincast/issues/18, machincast.player.expiry) : chaque passage qui
commence vérifie si son sonore a atteint son maximum de lectures ; tous les sonores sont vérifiés au démarrage, puis
toutes les EXPIRY_CHECK, pour les périodes de diffusion terminées.
"""

import dataclasses
import json
import logging
import signal
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import FrameType
from typing import Any

import psycopg
from psycopg.rows import TupleRow

from machincast import crash
from machincast.clock import Clock
from machincast.configuration import Crossfades, DeadAirSettings, Metadata
from machincast.conversion import integer_or_none, text_or_none
from machincast.i18n import N_, _, logged
from machincast.player.analysis import Analyser, to_analyse
from machincast.player.engine import (
	GUARD_DELAY,
	DeadAir,
	Engine,
	PlaybackTrack,
	entry_fade,
	overlay,
	sequencing,
)
from machincast.player.fades import Placement, put
from machincast.player.files import check_before_playback
from machincast.player.grid import Event, Occurrence, Priority, read_event, wall_hour
from machincast.player.history import IN_DATABASE, History
from machincast.player.outputs import Outputs, public_text, read_plays
from machincast.player.rundown import OUTSIDE_LIST, Choice, Cutoff, Decision, Ongoing, Scheduler
from machincast.player.saving import Play
from machincast.player.state import (
	ADVANCE,
	CUT_BY_FALLBACK,
	CUT_BY_FEED,
	MINIMAL_PUBLICATION,
	REREAD_GRID,
	BusyStateSocket,
	StateSocket,
	is_healthy,
)
from machincast.player.state import instant as iso
from machincast.randomness import Randomness

log = logging.getLogger(__name__)

PAUSE = 0.05
NO_CROSSFADE = timedelta(0)
EVENT_START, EVENT_END = N_("event start"), N_("event end")
SEQUENCE_START, SEQUENCE_END = N_("sequence start"), N_("sequence end")
"""Natures, au niveau info, des débuts et des fins à l'antenne (https://github.com/dascritch/machincast/issues/153)."""
PRIORITIES = {
	Priority.SPECIAL: N_("special"),
	Priority.SHOW: N_("show"),
	Priority.BACKGROUND_PROGRAMMING: N_("background programming"),
	Priority.FALLBACK: N_("fallback"),
}
"""Les priorités, en anglais, dans les messages du log."""
WITHOUT_DEFECTS = Crossfades()
"""Une configuration sans crossfades par défaut."""
CUTOFF_HORIZON = timedelta(hours=12)
"""Jusqu'où chercher l'événement qui coupera un sonore de durée inconnue, un stream
(https://github.com/dascritch/machincast/issues/169)."""
UPCOMING = 5
"""Sonores prévus après le prochain : la playlist immédiate (https://github.com/dascritch/machincast/issues/228)."""
GRID_FINGERPRINT = (
	"SELECT md5(concat_ws('|',"
	" (SELECT string_agg(concat_ws(';', e.id, e.priority, e.starts_at, e.ends_at, e.recurrence_days, e.deleted_at), ','"
	" ORDER BY e.id) FROM events e),"
	" (SELECT string_agg(x::text, ',' ORDER BY x.id) FROM event_items x),"
	" (SELECT string_agg(l::text, ',' ORDER BY l.id) FROM sequence_items l),"
	" (SELECT string_agg(s::text, ',' ORDER BY s.event_id, s.day) FROM event_skips s)))"
)
"""Empreinte de ce qui règle l'antenne dans la grille : les dates, les jours, la priorité et la suppression des
événements, leurs listes, leurs sessions sautées et les listes des séquences. Changée, elle fait recalculer les
sonores à venir ; un nom, un nom public, un masquage ou la date de modification n'y sont pas : les sonores à venir,
déjà tirés, restent ceux qui passeront (https://github.com/dascritch/machincast/issues/266)."""

RECONNECTION_DELAY = timedelta(seconds=5)
"""Délai entre deux tentatives de reconnexion d'un stream tombé."""

EXPIRY_CHECK = timedelta(minutes=1)
"""Intervalle entre deux vérifications de tous les sonores (fin de période de diffusion)."""

STOPPED_STREAM = N_("the stream stopped before the end of its event")
DROPPED_STREAM = N_("dropped stream")
FROZEN_STREAM = N_(
	"no sound for {guard_delay:g} seconds, without a player error: the connection stays open, "
	"but nothing arrives any more"
).format(guard_delay=GUARD_DELAY.total_seconds())
"""Le message d'un stream gelé (https://github.com/dascritch/machincast/issues/278)."""
STREAM_RESUMPTION = N_("stream resumption")
DEAD_AIR_IN_SOUND = N_("dead air in a sound")
"""Incident d'un sonore qui ne donne plus de son à l'antenne (https://github.com/dascritch/machincast/issues/122)."""
BLOCKED_PLAYBACK = N_("blocked playback")
"""Incident d'un sonore dont le lecteur n'a pas démarré (https://github.com/dascritch/machincast/issues/281)."""
BLOCKED_PLAYER = N_("no sound {guard_delay:g} seconds after its start, the next sound is played").format(
	guard_delay=GUARD_DELAY.total_seconds()
)
MANUAL_INTERRUPTION = N_("manual interruption")
IGNORED = N_("{manual_interruption} ignored").format(manual_interruption=MANUAL_INTERRUPTION)
ADVANCED_EVENT = N_("advanced event")
"""Nature de la ligne du log d'une avance de l'événement suivant (https://github.com/dascritch/machincast/issues/257)."""
IGNORED_ADVANCE = N_("advance ignored")
FOLLOWING_EVENT_SEARCH = timedelta(minutes=1)
"""L'événement suivant publié se cherche de nouveau au plus tard après ce délai, même si rien n'a changé."""


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


@dataclass
class Broadcast:
	"""La diffusion de la grille sur la sortie audio, pas à pas.

	La connexion a endossé le rôle de la lecture (machincast.database.open_connection). Les heures de l'airplay et du
	log
	viennent de l'horloge ; le moment d'enchaîner vient de la position de la voie dans le sonore.
	"""

	connection: psycopg.Connection[TupleRow]
	engine: Engine
	clock: Clock
	randomness: Randomness
	reconnection_delay: timedelta = RECONNECTION_DELAY
	outputs: Outputs | None = None
	"""Modules de sortie : journal, CSV, .pls et HTML (https://github.com/dascritch/machincast/issues/19)."""
	state: StateSocket | None = None
	"""Socket d'état pour l'interface (https://github.com/dascritch/machincast/issues/20)."""
	history: History = IN_DATABASE
	"""Où se lisent et s'écrivent passages et log : la base, ou la mémoire en simulation."""
	minimal_publication: float = MINIMAL_PUBLICATION
	"""Intervalle maximal entre deux publications de l'état, en secondes, pour suivre la progression."""
	metadata: Metadata | None = None
	"""Masquage et texte public par défaut, pour le texte public de la socket d'état ; à défaut, ceux des sorties."""
	crossfades: Crossfades = WITHOUT_DEFECTS
	"""Crossfades par défaut des sonores qui n'en ont pas de paramétré (https://github.com/dascritch/machincast/issues/145)."""
	analyser: Analyser | None = None
	"""Analyse du prochain sonore qui n'a pas été vérifié en entier
	(https://github.com/dascritch/machincast/issues/181) ; aucune en simulation."""
	dead_air: DeadAirSettings = field(default_factory=DeadAirSettings)
	"""Ce que fait un blanc dans un sonore (https://github.com/dascritch/machincast/issues/122) : le moteur le mesure,
	la diffusion le note, et passe au secours si BlancAntenne.secours."""
	scheduler: Scheduler = field(init=False)
	current: Playback | None = field(default=None, init=False)
	outgoing_list: list[Playback] = field(default_factory=list, init=False)
	"""Sonores qui finissent leur crossfade de fin sous le sonore courant."""
	in_waiting: Choice | None = field(default=None, init=False)
	"""Sonore suivant, qui attend la fin du sonore courant faute de superposition."""
	probe: Probe | None = field(default=None, init=False)
	"""Reconnexion du stream tombé, s'il y en a un."""
	checked_expiries: datetime | None = field(default=None, init=False)
	"""Heure de la dernière vérification de tous les sonores."""
	reserve: Reserve | None = field(default=None, init=False)
	"""Prochain sonore, réservé au début du sonore en cours : il sera joué s'il est encore valable."""
	preload: Preload | None = field(default=None, init=False)
	"""La voie muette du prochain sonore, un stream de feed, qui se charge avant de prendre l'antenne
	(https://github.com/dascritch/machincast/issues/351)."""
	_publication: tuple[str, datetime | None] = field(default=("", None), init=False)
	"""Dernier état publié sur la socket, sans ce qui change à chaque pas, et heure de sa publication."""
	_reserved_details: tuple[Reserve, dict[str, Any]] | None = field(default=None, init=False)
	"""Contexte du sonore réservé, lu une fois pour lui."""
	_on_air: Choice | None = field(default=None, init=False)
	"""Le dernier passage commencé, pour noter les débuts et les fins d'événements et de séquences."""
	_on_air_occurrence: Occurrence | None = field(default=None, init=False)
	"""L'occurrence à l'antenne : celle du dernier passage, ou celle qui lui prête son nom
	(https://github.com/dascritch/machincast/issues/399)."""
	lender: Occurrence | None = field(default=None, init=False)
	"""L'occurrence qui prête son nom à l'antenne, selon la dernière décision de l'ordonnanceur."""
	_crash_current: dict[str, Any] | None = field(default=None, init=False)
	"""Le sonore en cours, tel que le dernier rapport de crash l'a noté : le précédent du suivant."""
	_announced_lender: Occurrence | None = field(default=None, init=False)
	"""Celle que les sorties et le log connaissent : un changement s'y annonce dès l'heure, sans attendre de passage."""
	_on_air_sequence: str = field(default="", init=False)
	"""Le message de la séquence à l'antenne, gardé pour sa fin."""
	upcoming: list[Planned] = field(default_factory=list, init=False)
	"""Les sonores prévus après le prochain, dans l'ordre (https://github.com/dascritch/machincast/issues/228)."""
	_expected: Choice | None = field(default=None, init=False)
	"""Le prochain sonore, pris pour être joué : s'il démarre, les sonores à venir avancent d'un cran."""
	_fingerprint: str | None = field(default=None, init=False)
	"""Empreinte de la grille quand les sonores à venir ont été prévus (EMPREINTE_DE_LA_GRILLE)."""
	_following: tuple[datetime, Occurrence | None] | None = field(default=None, init=False)
	"""L'événement suivant publié, et l'heure où il a été cherché ; None pour le chercher de nouveau
	(https://github.com/dascritch/machincast/issues/257)."""

	def __post_init__(self) -> None:
		self.scheduler = Scheduler(self.connection, self.randomness, self.history)

	def start(self) -> None:
		"""Ouvre la socket d'état ; lève BusyStateSocket si un autre Machin player diffuse déjà. Le démarrage du binaire
		se note au log par machincast.runs (https://github.com/dascritch/machincast/issues/342)."""
		instant = self.clock.now()
		if self.state is not None:
			try:
				self.state.open_()
			except BusyStateSocket:
				raise
			except OSError as error:
				self.history.record(
					self.connection,
					"warning",
					N_("state socket unavailable"),
					N_("{path}: {error}").format(path=self.state.path, error=error),
					instant,
				)
				self.state = None
		self._check_expiries(instant)
		self._publish(instant)

	def step(self) -> None:
		instant = self.clock.now()
		self._check_expiries(instant)
		self.engine.handle_messages()
		self._finish_stopped_tracks(instant)
		self._discard_blocked_playback(instant)
		self._discard_frozen_stream(instant)
		self._handle_dead_air(instant)
		if self.state is not None:
			for asks in self.state.requests():
				if asks.command == REREAD_GRID:
					self.reread_grid()
				else:
					if asks.command == ADVANCE:
						self.advance(asks.event)
					else:
						if asks.command == CUT_BY_FALLBACK:
							self.cut_by_fallback(asks.event)
						else:
							if asks.command == CUT_BY_FEED:
								self.cut_by_feed(asks.feed)
							else:
								self.interrupt(asks.item)
		current = self.current
		if current is not None:
			decision = self._decide(instant, current.ongoing)
			if decision.cut:
				reserve = self.reserve
				self._cut(instant)
				self._play_decision(decision, reserve, instant)
			else:
				if decision.switch_off:
					self._switch_off(current, (self._take_reserve(instant)) or (decision.play), instant)
				else:
					if (not current.following_requested) and (self._to_end_crossfade(current)):
						current.following_requested = True
						self._prepare_following(current, instant)
		else:
			if not self.outgoing_list:
				# Rien sur la sortie ; tant qu'un stream s'éteint sans superposition, le suivant attend.
				reserve = self.reserve
				choice, self.in_waiting = self.in_waiting, None
				choice = (choice) or (self._take_reserve(instant))
				if choice is not None:
					self._play(choice, instant)
				else:
					self._play_decision(self._decide(instant, None), reserve, instant)
		self._follow_probe(instant)
		self._preload(instant)
		self._follow_lender(instant)
		self._publish(instant)

	def _decide(self, instant: datetime, ongoing: Ongoing | None) -> Decision:
		"""La décision de l'ordonnanceur, dont l'occurrence qui prête alors son nom est retenue."""
		decision = self.scheduler.decide(instant, ongoing)
		self.lender = decision.lender
		return decision

	def _lent(self, choice: Choice, start: datetime | None = None) -> Choice:
		"""Le sonore, au nom de l'occurrence qui prête alors le sien à son événement, s'il y en a une
		(https://github.com/dascritch/machincast/issues/399) ; pour un sonore à venir qui commencera à start, si le prêt
		dure encore. Un sonore réservé avant le début du prêt, ou après sa fin, suit ainsi le prêt du moment."""
		lender = self.lender
		if (lender is not None) and (lender.event.id == choice.occurrence.event.id):
			lender = None
		if (
			(lender is not None)
			and (start is not None)
			and (lender.end is not None)
			and (wall_hour(start) >= lender.end)
		):
			lender = None
		if lender is None:
			current_key = None
		else:
			current_key = lender.key
		if choice.lender is None:
			lender_key = None
		else:
			lender_key = choice.lender.key
		if current_key == lender_key:
			# Le même objet : le prochain sonore attendu se reconnaît à lui (_reserve).
			return choice
		return dataclasses.replace(choice, lender=lender)

	def _follow_lender(self, instant: datetime) -> None:
		"""Une occurrence commence ou cesse de prêter son nom pendant un sonore : le log, le journal, la page publique
		et la socket d'état le disent dès l'heure, sans couper le sonore (https://github.com/dascritch/machincast/issues/399)."""
		lender, announced = self.lender, self._announced_lender
		if lender is None:
			lender_key = None
		else:
			lender_key = lender.key
		if announced is None:
			announced_key = None
		else:
			announced_key = announced.key
		if lender_key == announced_key:
			return
		self._announced_lender = lender
		current = self.current
		if current is None:
			return
		current.choice = self._lent(current.choice)
		current.details = None
		self._note_events(current.choice, instant)
		if self.outputs is not None:
			self.outputs.lend(self.connection, _lender_id(current.choice), instant)

	def _preload(self, instant: datetime) -> None:
		"""PRELOAD avant son début estimé, le prochain stream d'un feed, le prochain sonore ou l'un des sonores à venir,
		se charge, muet (https://github.com/dascritch/machincast/issues/351) : sa mémoire tampon est pleine quand il
		prend l'antenne. Une voie préchargée qui tombe est abandonnée : le stream démarrera comme un autre."""
		preload = self.preload
		if (preload is not None) and (preload.track.state != "playing"):
			self._drop_preload()
		reserve, current = self.reserve, self.current
		if (self.preload is not None) or (reserve is None) or (current is None):
			return
		item_list = []
		for item in self.upcoming:
			item_list.append((item.choice, item.parameters))
		planned = [(reserve.choice, reserve.parameters)] + item_list
		starts = self._starts()
		if (reserve.early) and (current.cutoff is not None) and (starts != []):
			starts[0] = current.cutoff.instant
		for (choice, parameters), start in zip(planned, starts, strict=False):
			if start is None:
				return
			if start - instant > PRELOAD:
				return
			if (parameters.stream) and (parameters.buffer is not None) and (parameters.address is not None):
				track = self.engine.play(parameters.address, None, silent=True, buffer=parameters.buffer)
				self.preload = Preload(choice.sound, track)
				return

	def _planned_sounds(self) -> set[int]:
		reserve = self.reserve
		if reserve is None:
			return set()
		item_set = set()
		for item in self.upcoming:
			item_set.add(item.choice.sound)
		return {reserve.choice.sound} | item_set

	def _drop_preload(self, sound: int | None = None) -> None:
		"""Abandonne la voie préchargée, sauf celle de ce sonore."""
		preload = self.preload
		if (preload is None) or (preload.sound == sound):
			return
		preload.track.shut_down()
		self.preload = None

	def halt(self) -> None:
		"""Arrête la sortie : les passages en cours se terminent sans incident, puis l'arrêt est consigné."""
		instant = self.clock.now()
		self.engine.handle_messages()
		self._finish_stopped_tracks(instant)
		self.engine.cut()
		for playback in self._plays():
			self._finish(playback.play, instant)
		self.current, self.outgoing_list, self.in_waiting, self.probe, self.reserve = None, [], None, None, None
		self.preload = None
		self.upcoming = []
		self._note_on_air(None, instant)
		self.history.record(self.connection, "info", N_("stop"), N_("stop requested"), instant)
		self._publish(instant, stop=True)
		if self.state is not None:
			self.state.shut_down()

	def reread_grid(self) -> None:
		"""La grille a pu changer, et le changement doit valoir aussitôt
		(https://github.com/dascritch/machincast/issues/273, https://github.com/dascritch/machincast/issues/266) : si
		ce qui règle l'antenne a changé (GRID_FINGERPRINT), la coupure du sonore en cours, le prochain sonore et
		les sonores à venir sont recalculés, comme au début d'un sonore ; sinon, rien ne change. Rien à recalculer sans
		sonore à l'antenne, ni quand le suivant est déjà lancé, au crossfade de fin : la grille se relit alors au pas
		suivant, comme toujours."""
		current = self.current
		if (current is None) or (current.following_requested) or (self._grid_fingerprint() == self._fingerprint):
			return
		instant = self.clock.now()
		self._expected = None
		self._reserve(instant)
		self._publish(instant)

	def advance(self, event: int | None) -> bool:
		"""L'événement suivant commence aussitôt (https://github.com/dascritch/machincast/issues/257), s'il est bien
		celui que la demande attend : l'interface nomme celui que Machin player a publié. Le sonore en cours
		s'éteint comme pour une interruption manuelle, une séquence en cours ne continue pas, et les sonores à venir
		sont recalculés. False si la demande est ignorée."""
		instant = self.clock.now()
		following = self.scheduler.following_event(instant)
		if following is None:
			log.warning(_("{ignored_advance}: no next event").format(ignored_advance=logged(IGNORED_ADVANCE)))
			return False
		if following.event.id != event:
			expected = self._expected_name(event)
			log.warning(
				_("{ignored_advance}: the next event is “{name}”, not {expected}").format(
					ignored_advance=logged(IGNORED_ADVANCE), name=following.event.name, expected=expected
				)
			)
			return False
		self.scheduler.advance(instant)
		assert following.start is not None
		message = N_("of the event “{name}”, planned on {start:%Y-%m-%d %H:%M}").format(
			name=following.event.name, start=following.start
		)
		current = self.current
		if current is None:
			sound = None
		else:
			sound = current.choice.sound
		self.history.record(
			self.connection, "info", ADVANCED_EVENT, message, instant, sound=sound, event=following.event.id
		)
		if self.outputs is not None:
			self.outputs.announce(ADVANCED_EVENT, message)
		self._following = None
		if current is not None:
			# Une séquence en cours ne continue pas : l'occurrence avancée a commencé après son dernier passage.
			self.upcoming = []
			self._expected = None
			play = self._decide(instant, None).play
			fade = (self.crossfades.end) or (NO_CROSSFADE)
			self._switch_off(current, play, instant, fade, (self.crossfades.start) or (NO_CROSSFADE))
		self._publish(instant)
		return True

	def _expected_name(self, event: int | None) -> str:
		"""L'événement qu'attendait une demande d'avance, pour le journal."""
		if event is None:
			return _("none")
		with self.connection.transaction():
			line = self.connection.execute("SELECT internal_name FROM events WHERE id = %s", (event,)).fetchone()
		if line is None:
			return _("event no. {event}, unknown").format(event=event)
		return _("“{line}”").format(line=line[0])

	def _the_following_event(self, instant: datetime) -> Occurrence | None:
		"""L'événement suivant à publier, cherché de nouveau quand il a pu changer : au début d'un sonore, après une
		demande, quand il commence, et au moins chaque minute."""
		following = self._following
		if (
			(following is None)
			or (instant - following[0] >= FOLLOWING_EVENT_SEARCH)
			or (
				(following[1] is not None)
				and (following[1].start is not None)
				and (wall_hour(instant) >= following[1].start)
			)
		):
			following = (instant, self.scheduler.following_event(instant))
			self._following = following
		return following[1]

	def interrupt(self, item: str) -> bool:
		"""Interruption manuelle (https://github.com/dascritch/machincast/issues/228) : sauter au sonore suivant
		(« sonore »), sauter après la séquence (« sequence »), ou couper l'événement par le fil musical
		(« evenement ») ; False si elle est ignorée, faute de rien à interrompre."""
		instant = self.clock.now()
		current = self.current
		if current is None:
			log.warning(_("{ignored}: nothing on air").format(ignored=logged(IGNORED)))
			return False
		choice = current.choice
		# L'événement à l'antenne : celui qui prête son nom, s'il y en a un (https://github.com/dascritch/machincast/issues/399).
		event = ((choice.lender) or (choice.occurrence)).event
		if (item == "sequence") and (choice.line is None):
			log.warning(_("{ignored}: no sequence on air").format(ignored=logged(IGNORED)))
			return False
		if (item == "event") and (event.priority is Priority.BACKGROUND_PROGRAMMING):
			log.warning(_("{ignored}: the background programming is already on air").format(ignored=logged(IGNORED)))
			return False
		self._following = None
		message = N_("of the sound “{sound_name}”").format(sound_name=self._sound_name(choice.sound))
		if item == "sequence":
			message = N_("of the sequence {on_air_sequence}").format(on_air_sequence=self._on_air_sequence)
		if item == "event":
			message = N_("of the event “{name}”").format(name=event.name)
		self.history.record(
			self.connection,
			"info",
			MANUAL_INTERRUPTION,
			message,
			instant,
			sound=choice.sound,
			event=event.id,
		)
		if self.outputs is not None:
			self.outputs.announce(MANUAL_INTERRUPTION, message)
		if item != "sound":
			self.scheduler.abandon_sequence(current.play.id)
		following = None
		if item == "event":
			self.scheduler.return_to_background_programming(instant)
			self.upcoming = []
		else:
			following = self._skip(current, item == "sequence", instant)
		if following is None:
			following = self._decide(instant, None).play
		fade = (self.crossfades.end) or (NO_CROSSFADE)
		self._switch_off(current, following, instant, fade, (self.crossfades.start) or (NO_CROSSFADE))
		self._publish(instant)
		return True

	def cut_by_fallback(self, event: int | None) -> bool:
		"""Coupe l'antenne par cet événement de secours (https://github.com/dascritch/machincast/issues/323) ; False si
		la demande est ignorée : rien à l'antenne, ou pas un secours en base."""
		fallback = None
		if event is not None:
			with self.connection.transaction():
				fallback = read_event(self.connection, event)
		if (fallback is None) or (fallback.priority is not Priority.FALLBACK) or (fallback.deleted_at is not None):
			log.warning(
				_("{ignored}: event no. {event} is not a fallback").format(ignored=logged(IGNORED), event=event)
			)
			return False
		return self._cut_by(fallback, None, fallback.name)

	def cut_by_feed(self, feed: int | None) -> bool:
		"""Coupe l'antenne par le stream actif qui suit ce feed, le plus ancien
		(https://github.com/dascritch/machincast/issues/323) ; False si la demande est ignorée."""
		with self.connection.transaction():
			line = self.connection.execute(
				"SELECT m.name, (SELECT s.id FROM sounds s WHERE s.feed_id = m.id AND s.type = 'stream'"
				" AND s.state = 'active' AND s.deleted_at IS NULL ORDER BY s.id LIMIT 1) FROM feeds m WHERE m.id = %s",
				(feed,),
			).fetchone()
		if line is None:
			log.warning(_("{ignored}: feed no. {feed} does not exist").format(ignored=logged(IGNORED), feed=feed))
			return False
		name, stream = line
		if stream is None:
			log.warning(
				_("{ignored}: no active stream follows the feed “{name}”").format(ignored=logged(IGNORED), name=name)
			)
			return False
		return self._cut_by(None, int(str(stream)), str(name))

	def _cut_by(self, fallback: Event | None, stream: int | None, by: str) -> bool:
		"""Comme une interruption de l'événement, mais le secours ou le stream remplace la grille jusqu'à la fin de
		l'événement coupé ; by : le nom du secours, ou celui du feed du stream."""
		instant = self.clock.now()
		current = self.current
		if current is None:
			log.warning(_("{ignored}: nothing on air").format(ignored=logged(IGNORED)))
			return False
		event = current.choice.occurrence.event
		# Une phrase entière par cas, que le log traduit d'un seul gabarit.
		if event.priority is Priority.BACKGROUND_PROGRAMMING:
			message = N_("of the background programming “{name}” by the fallback “{by}”")
			if fallback is None:
				message = N_("of the background programming “{name}” by the feed “{by}”")
		else:
			message = N_("of the event “{name}” by the fallback “{by}”")
			if fallback is None:
				message = N_("of the event “{name}” by the feed “{by}”")
		message = message.format(name=event.name, by=by)
		self.history.record(
			self.connection,
			"info",
			MANUAL_INTERRUPTION,
			message,
			instant,
			sound=current.choice.sound,
			event=event.id,
		)
		if self.outputs is not None:
			self.outputs.announce(MANUAL_INTERRUPTION, message)
		self._following = None
		self.scheduler.abandon_sequence(current.play.id)
		self.scheduler.cut_by(instant, fallback, stream)
		self.upcoming = []
		self._expected = None
		following = self._decide(instant, None).play
		fade = (self.crossfades.end) or (NO_CROSSFADE)
		self._switch_off(current, following, instant, fade, (self.crossfades.start) or (NO_CROSSFADE))
		self._publish(instant)
		return True

	def _skip(self, current: Playback, after_sequence: bool, instant: datetime) -> Choice | None:
		"""Le sonore où sauter : le prochain, ou, après la séquence, le premier sonore prévu qui ne la continue pas ;
		les sonores à venir qui le suivent sont gardés. None s'il n'est pas prévu, ou plus jouable : l'ordonnanceur
		décide alors, et la liste sera recalculée."""
		reserve = self.reserve
		if (reserve is None) or (reserve.early):
			return None
		candidates: list[tuple[Choice, Planned | None]] = [(reserve.choice, None)]
		for upcoming in self.upcoming:
			candidates.append((upcoming.choice, upcoming))
		previous = current.choice
		for rank, (choice, planned) in enumerate(candidates):
			same_occurrence = previous.occurrence.key == choice.occurrence.key
			if (after_sequence) and (same_occurrence) and (_continues_sequence(previous, choice)):
				# Un sonore de la séquence est passé avec elle.
				previous = choice
			else:
				if not self.scheduler.validate(choice, instant):
					return None
				if planned is not None:
					self._engage(planned, instant)
				self.upcoming = self.upcoming[rank:]
				self._expected = choice
				return choice
		return None

	def _sound_name(self, sound: int) -> str:
		with self.connection.transaction():
			line = self.connection.execute(
				"SELECT COALESCE(title, location, stream_url) FROM sounds WHERE id = %s", (sound,)
			).fetchone()
		if (line is None) or (line[0] is None):
			return str(sound)
		return str(line[0])

	# ─── Étapes ────────────────────────────────────────────

	def _plays(self) -> list[Playback]:
		if self.current is None:
			ongoing = []
		else:
			ongoing = [self.current]
		return ongoing + self.outgoing_list

	def _finish_stopped_tracks(self, instant: datetime) -> None:
		def finish_playback(playback: Playback) -> None:
			if playback.track.state not in ("finished", "error"):
				return
			if (playback.parameters.stream) and (not playback.off):
				# Un stream n'a pas de fin : arrêté avant son extinction, il est tombé.
				error = N_("{path}: {error}").format(
					path=playback.parameters.address, error=(playback.track.error) or (STOPPED_STREAM)
				)
				self._finish(playback.play, instant, error=error, kind=DROPPED_STREAM)
				self._suspend(playback, instant)
			else:
				self._finish(playback.play, instant, error=playback.track.error)

		for playback in self._plays():
			finish_playback(playback)
		outgoing_playing = []
		for s in self.outgoing_list:
			if s.track.state == "playing":
				outgoing_playing.append(s)
		self.outgoing_list = outgoing_playing
		if (self.current is not None) and (self.current.track.state != "playing"):
			self.current = None

	def _discard_blocked_playback(self, instant: datetime) -> None:
		"""Un sonore dont le lecteur n'a pas démarré ne jouera rien : son passage se termine en incident, et le sonore
		suivant prend sa place, comme après un sonore fini (https://github.com/dascritch/machincast/issues/281). Un
		stream a son propre délai de connexion, et sa chute son repli : il n'est pas concerné."""
		current = self.current
		if (current is None) or (current.parameters.stream) or (not current.track.blocked()):
			return
		current.track.cut()
		self._finish(
			current.play,
			instant,
			error=N_("{path}: {error}").format(path=current.parameters.location, error=BLOCKED_PLAYER),
			kind=BLOCKED_PLAYBACK,
		)
		self.current = None

	def _discard_frozen_stream(self, instant: datetime) -> None:
		"""Un stream qui ne donne plus de son pendant le délai de garde est tombé, même si le lecteur ne le dit pas
		(https://github.com/dascritch/machincast/issues/278) : comme pour un flux arrêté, son passage se termine en
		incident, le secours ou l'événement inférieur prend l'antenne, et la sonde le reconnectera."""
		current = self.current
		if (current is None) or (not current.parameters.stream) or (current.off) or (not current.track.frozen()):
			return
		current.track.cut()
		error = N_("{path}: {error}").format(path=current.parameters.address, error=FROZEN_STREAM)
		self._finish(current.play, instant, error=error, kind=DROPPED_STREAM)
		self._suspend(current, instant)
		self.current = None

	def _handle_dead_air(self, instant: datetime) -> None:
		"""Un blanc dans le sonore en cours est noté (https://github.com/dascritch/machincast/issues/122) ; avec
		DeadAirSettings.secours, le fichier laisse l'antenne au sonore suivant, et le stream à son secours, sa voie
		gardée
		pour reprendre l'antenne quand son son revient. Un sonore sortant, comme un stream qui s'éteint à la fin de son
		événement, n'est pas concerné : il laisse déjà l'antenne."""
		current = self.current
		if current is None:
			return
		dead_air = current.track.dead_air()
		if dead_air is None:
			return
		parameters = current.parameters
		message = _dead_air_message(dead_air, parameters)
		if not self.dead_air.fallback:
			self.history.record(
				self.connection,
				"incident",
				DEAD_AIR_IN_SOUND,
				message,
				instant,
				sound=current.choice.sound,
				event=current.choice.occurrence.event.id,
			)
			return
		if not parameters.stream:
			current.track.cut()
			self._finish(
				current.play,
				instant,
				error=N_("{message}, the next sound is played").format(message=message),
				kind=DEAD_AIR_IN_SOUND,
			)
			self.current = None
			return
		# La voie se tait, mais reste ouverte : elle sert de sonde, et reprendra l'antenne avec son son.
		current.track.fade(0.0, NO_CROSSFADE)
		error = N_("{message}, the stream leaves the on-air output until its sound comes back").format(message=message)
		self._finish(current.play, instant, error=error, kind=DEAD_AIR_IN_SOUND)
		self._suspend(current, instant)
		probe = self.probe
		assert probe is not None
		probe.track, probe.dead_air = current.track, True
		self.current = None

	@staticmethod
	def _to_end_crossfade(playback: Playback) -> bool:
		duration = playback.parameters.duration
		return (duration is not None) and (playback.track.position() >= duration - playback.parameters.end_crossfade)

	def _take_reserve(self, instant: datetime) -> Choice | None:
		"""Le sonore réservé, s'il est encore valable ; la réserve est vidée dans tous les cas."""
		reserve, self.reserve = self.reserve, None
		if (reserve is not None) and (not reserve.early) and (self.scheduler.validate(reserve.choice, instant)):
			self._expected = reserve.choice
			return reserve.choice
		return None

	def _play_decision(self, decision: Decision, reserve: Reserve | None, instant: datetime) -> None:
		"""Joue le sonore de la décision ; à la coupure par un événement, ou quand le sonore coupé a fini plus tôt, le
		sonore réservé pour cet événement est joué à sa place, même tiré au hasard, s'il est encore valable."""
		choice = decision.play
		if (
			(choice is not None)
			and (reserve is not None)
			and (reserve.early)
			and (reserve.choice.occurrence.key == choice.occurrence.key)
			and (self.scheduler.validate(reserve.choice, instant))
		):
			choice = reserve.choice
			self._expected = choice
		if choice is not None:
			self._play(choice, instant)

	def _reserve(self, instant: datetime) -> None:
		"""Au début du sonore en cours, réserve le prochain sonore, puis prévoit les sonores à venir.

		Si c'est le prochain sonore attendu qui a démarré, que la grille n'a pas changé et que la coupure du sonore en
		cours est celle qui était prévue, le premier sonore à venir devient le prochain
		(https://github.com/dascritch/machincast/issues/228). Sinon, le prochain est choisi : si un événement doit
		couper le sonore en cours, c'est celui que cet événement jouera, anticipé à l'instant de la coupure
		(https://github.com/dascritch/machincast/issues/169) ; et les sonores à venir sont recalculés."""
		current = self.current
		expected, self._expected = self._expected, None
		self._following = None
		cutoff = None
		if current is not None:
			cutoff = self.scheduler.cutoff(current.ongoing, instant, _horizon(current, instant))
			current.cutoff = cutoff
		fingerprint = self._grid_fingerprint()
		engaged = (
			(current is not None)
			and (expected is not None)
			and (expected is current.choice)
			and (self.upcoming != [])
			and (fingerprint == self._fingerprint)
			and (_same_cutoff(self.upcoming[0].cutoff, cutoff))
		)
		self._fingerprint = fingerprint
		if engaged:
			planned = self.upcoming.pop(0)
			self._engage(planned, instant)
			self.reserve = Reserve(planned.choice, planned.parameters, planned.healthy, planned.cutoff is not None)
		else:
			self.upcoming = []
			self.reserve = self._choose_reserve(cutoff, instant)
		if self.reserve is not None:
			self._analyse(self.reserve, instant)
		self._extend(instant)
		# Les sonores prévus ont pu changer : la voie préchargée d'un stream qui n'y est plus ne sert plus.
		preload = self.preload
		if (preload is not None) and (preload.sound not in self._planned_sounds()):
			self._drop_preload()
		self._note_for_crash(instant)

	def _note_for_crash(self, instant: datetime) -> None:
		"""Pour un rapport de crash (https://github.com/dascritch/machincast/issues/342) : les sonores précédent, en
		cours et les CRASH_UPCOMING suivants annoncés, à chaque début de sonore, en mémoire : le rapport d'une exception
		les donne ; après un signal fatal, le journal donne les sonores joués
		(https://github.com/dascritch/machincast/issues/413). Seulement pendant un lancement surveillé, et sans jamais
		gêner la diffusion."""
		if crash.current() is None:
			return
		try:
			message = self._state(instant, False)
		except Exception as error:  # noqa: BLE001 : le contexte d'un rapport ne doit pas arrêter l'antenne
			log.debug(_("crash report context unavailable: {error}").format(error=error))
			return
		previous, self._crash_current = self._crash_current, message["current"]
		crash.note(SOUNDS_ON_AIR, crash_text(previous, message))

	def _engage(self, planned: Planned, instant: datetime) -> None:
		"""Le sonore prévu devient le prochain : ce que sa décision a terminé l'est pour de bon, et ce qu'elle
		consignerait est consigné, à l'heure où le prochain sonore est réservé."""
		self.scheduler.engage(planned.finished_list)
		for records in planned.recorded_list:
			self.history.record(self.connection, instant=instant, **records)

	def _choose_reserve(self, cutoff: Cutoff | None, instant: datetime) -> Reserve | None:
		"""Le prochain sonore, choisi au début du sonore en cours ; pour un stream qui s'éteindra à la fin de son
		événement, choisi pour cette fin, où un autre événement reprendra l'antenne
		(https://github.com/dascritch/machincast/issues/242) ; après une coupure, anticipé à son instant."""
		if cutoff is None:
			moment = instant
			current = self.current
			if (current is not None) and (current.parameters.stream):
				moment = (_occurrence_end(current.choice.occurrence)) or (instant)
			choice = self.scheduler.reserve(max(instant, moment))
		else:
			choice = self.scheduler.anticipate(cutoff.instant)
		if choice is None:
			return None
		return Reserve(
			choice,
			read_parameters(self.connection, choice, self.crossfades),
			is_healthy(self.connection, choice.sound),
			cutoff is not None,
		)

	def _grid_fingerprint(self) -> str:
		with self.connection.transaction():
			line = self.connection.execute(GRID_FINGERPRINT).fetchone()
		if line is None:
			return ""
		return str(line[0])

	def _extend(self, instant: datetime) -> None:
		"""Prévoit les sonores à venir jusqu'à UPCOMING, au bout de la liste : chacun est choisi à l'heure où le
		précédent appellera son suivant, ou à celle de l'événement qui le coupera. La liste s'arrête sur un blanc, ou
		après un sonore dont la fin est inconnue."""
		current, reserve = self.current, self.reserve
		if (current is None) or (reserve is None):
			self.upcoming = []
			return
		starts = self._starts()
		upcoming_list = []
		for upcoming in self.upcoming:
			upcoming_list.append((upcoming.choice, upcoming.parameters))
		string = [(reserve.choice, reserve.parameters)] + upcoming_list
		found = False
		for known_start in starts:
			if known_start is None:
				found = True
				break
		if found:
			return
		planned_list = []
		for (planned_choice, _parameters), planned_start in zip(string, starts, strict=True):
			if planned_start:
				planned_list.append(_planned_play(planned_choice, planned_start))
		previous, parameters = string[-1]
		start = starts[-1]
		finished_list: frozenset[tuple[int, datetime | None]] = frozenset()
		if self.upcoming != []:
			finished_list = self.upcoming[-1].finished_list
		with self.scheduler.forecast(planned_list, finished_list) as forecast:
			while (len(self.upcoming) < UPCOMING) and (start is not None):
				occurrence = previous.occurrence
				ongoing = Ongoing(
					occurrence, start, start + ((parameters.duration) or (timedelta(0))), parameters.stream
				)
				horizon = _horizon_of(start, parameters, occurrence, instant)
				cutoff = self.scheduler.cutoff(ongoing, start, horizon)
				moment = _following_instant(start, parameters, occurrence, cutoff)
				if moment is None:
					return
				already = len(forecast.recorded_list)
				choice = self.scheduler.reserve(moment)
				if choice is None:
					return
				incoming = read_parameters(self.connection, choice, self.crossfades)
				planned = Planned(
					choice,
					incoming,
					is_healthy(self.connection, choice.sound),
					cutoff,
					frozenset(self.scheduler.finished_list),
					self._details(choice, None),
					tuple(forecast.recorded_list[already:]),
				)
				self.upcoming.append(planned)
				start = _following_start(start, parameters, occurrence, cutoff, incoming)
				if start is not None:
					planned_list.append(_planned_play(choice, start))
				previous, parameters = choice, incoming

	def _starts(self) -> list[datetime | None]:
		"""Débuts estimés du prochain sonore et des sonores à venir, enchaînés depuis le sonore en cours ; None à partir
		d'un sonore dont la fin est inconnue."""
		current, reserve = self.current, self.reserve
		if (current is None) or (reserve is None):
			return []
		planned_list = []
		for planned in self.upcoming:
			planned_list.append((planned.choice, planned.parameters))
		remainder = [(reserve.choice, reserve.parameters)] + planned_list
		upcoming_cutoffs = []
		for planned in self.upcoming:
			upcoming_cutoffs.append(planned.cutoff)
		cutoffs = [current.cutoff] + upcoming_cutoffs
		start: datetime | None = current.play.start
		parameters, occurrence = current.parameters, current.choice.occurrence
		starts: list[datetime | None] = []
		for (choice, incoming), cutoff in zip(remainder, cutoffs, strict=True):
			if start is not None:
				start = _following_start(start, parameters, occurrence, cutoff, incoming)
			starts.append(start)
			parameters, occurrence = incoming, choice.occurrence
		return starts

	def _analyse(self, reserve: Reserve, instant: datetime) -> None:
		"""Fait analyser le sonore réservé s'il n'a pas été vérifié en entier, sans attendre l'analyse."""
		analyser = self.analyser
		sound = reserve.choice.sound
		if (analyser is None) or (not analyser.to_ask(sound, instant)):
			return
		with self.connection.transaction():
			if not to_analyse(self.connection, sound):
				return
		location = reserve.parameters.location
		try:
			analyser.launch(sound, instant)
		except OSError as error:
			self.history.record(
				self.connection,
				"warning",
				N_("analysis impossible"),
				N_("{path}: {error}").format(path=location, error=error),
				instant,
				sound=sound,
			)
			return
		self.history.record(
			self.connection,
			"info",
			N_("analysis of the next sound"),
			N_("{location}: full audit by Machin indexer, before its playback").format(location=location),
			instant,
			sound=sound,
		)

	def _prepare_following(self, current: Playback, instant: datetime) -> None:
		choice = (self._take_reserve(instant)) or (self._decide(instant, None).play)
		if choice is None:
			# Rien ensuite : le sonore finit avec son fondu, et le prochain pas sans voie redemande.
			return
		parameters = read_parameters(self.connection, choice, self.crossfades)
		if overlay(current.parameters.end_crossfade, parameters.start_crossfade):
			self._play(choice, instant, current.parameters.end_crossfade)
		else:
			current.track.delete_output_fade()
			self.in_waiting = choice

	def _switch_off(
		self,
		current: Playback,
		choice: Choice | None,
		instant: datetime,
		fade: timedelta | None = None,
		rise: timedelta | None = None,
	) -> None:
		"""Fin de l'événement d'un stream : le sonore s'éteint pendant son crossfade de fin, et le sonore choisi
		enchaîne. Pour une interruption manuelle, le sonore s'éteint pendant fondu, aussitôt sans durée, et le sonore
		choisi monte pendant montee : il démarre aussitôt, sauf s'il doit attendre la fin d'un fondu sans montée."""
		if fade is None:
			fade = current.parameters.end_crossfade
		current.off = True
		self.reserve = None
		current.track.switch_off(fade)
		self.current = None
		self.outgoing_list.append(current)
		self._finish_stopped_tracks(instant)
		if choice is None:
			return
		entry = rise
		if entry is None:
			entry = read_parameters(self.connection, choice, self.crossfades).start_crossfade
		if ((rise is not None) and (fade <= timedelta(0))) or (overlay(fade, entry)):
			self._play(choice, instant, fade, rise)
		else:
			self.in_waiting = choice

	def _suspend(self, playback: Playback, instant: datetime) -> None:
		"""Stream tombé : l'ordonnanceur le remplace, et la sonde le reconnectera."""
		self.scheduler.suspend(playback.choice.occurrence, playback.parameters.fallback)
		self.upcoming = []
		self.probe = Probe(playback.choice, playback.parameters, instant + self.reconnection_delay, instant)

	def _follow_probe(self, instant: datetime) -> None:
		probe = self.probe
		if probe is None:
			return
		suspension = self.scheduler.suspension
		if (suspension is None) or (suspension.occurrence.key != probe.choice.occurrence.key):
			if probe.track is not None:
				probe.track.shut_down()
			self.probe = None
			self.history.record(
				self.connection,
				"info",
				N_("reconnection abandoned"),
				N_("{address}: the event of the stream is no longer on air").format(address=probe.parameters.address),
				instant,
				sound=probe.choice.sound,
				event=probe.choice.occurrence.event.id,
			)
			return
		if probe.track is None:
			if (instant >= probe.next_attempt) and (probe.parameters.address is not None):
				probe.track = self.engine.play(
					probe.parameters.address, None, silent=True, buffer=probe.parameters.buffer
				)
			return
		probe.track.handle()
		# Le même délai de garde : une tentative qui ne donne aucun son est abandonnée, puis reprise.
		if (probe.track.state != "playing") or (probe.track.frozen()):
			probe.track.shut_down()
			probe.track = None
			probe.next_attempt = instant + self.reconnection_delay
		else:
			if (probe.track.position() > timedelta(0)) and ((not probe.dead_air) or (probe.track.heard())):
				self._resume(probe, probe.track, instant)

	def _resume(self, probe: Probe, track: PlaybackTrack, instant: datetime) -> None:
		"""Le flux est revenu : crossfade immédiat vers le stream, pendant son crossfade de début."""
		fade = probe.parameters.start_crossfade
		track.fade(1.0, fade)
		for playback in self._plays():
			if fade > timedelta(0):
				playback.off = True
				playback.track.switch_off(fade)
			else:
				playback.track.cut()
				self._finish(playback.play, instant)
		playback_list = []
		for ongoing in self._plays():
			if ongoing.track.state == "playing":
				playback_list.append(ongoing)
		self.outgoing_list = playback_list
		self.in_waiting, self.probe = None, None
		self.scheduler.resume()
		self.lender = self.scheduler.lender(instant)
		choice = self._lent(probe.choice)
		play = self._begin(choice, instant)
		self.current = Playback(choice, probe.parameters, track, play)
		self.history.expire(self.connection, instant, choice.sound)
		self._reserve(instant)
		breakdown = round((instant - probe.since).total_seconds())
		self.history.record(
			self.connection,
			"incident",
			STREAM_RESUMPTION,
			N_("{address}: the stream came back after {breakdown} s of failure").format(
				address=probe.parameters.address, breakdown=breakdown
			),
			instant,
			sound=choice.sound,
			event=choice.occurrence.event.id,
		)

	def _cut(self, instant: datetime) -> None:
		"""Coupe net les voies à l'antenne et celle de la reprise d'un stream tombé, pas la voie préchargée du sonore
		qui coupe (https://github.com/dascritch/machincast/issues/351)."""
		for playback in self._plays():
			playback.track.cut()
		if (self.probe is not None) and (self.probe.track is not None):
			self.probe.track.cut()
		for playback in self._plays():
			self._finish(playback.play, instant, cut=True)
		self.current, self.outgoing_list, self.in_waiting, self.reserve = None, [], None, None

	def _play(
		self,
		choice: Choice,
		instant: datetime,
		previous_end_crossfade: timedelta = timedelta(0),
		rise: timedelta | None = None,
	) -> None:
		"""Démarre le sonore ; un fichier introuvable est écarté, et l'ordonnanceur donne le suivant. montee : la durée
		de la montée, imposée par une interruption manuelle ; sinon, son crossfade de début s'il se superpose au
		précédent."""
		following: Choice | None = choice
		path: Path | str | None = None
		tried: set[int] = set()
		# Chaque sonore n'est essayé qu'une fois : la boucle s'arrête même si l'ordonnanceur le redonne.
		while (following is not None) and (following.sound not in tried):
			parameters = read_parameters(self.connection, following, self.crossfades)
			path = parameters.address
			if not parameters.stream:
				path = check_before_playback(self.connection, following.sound, self.history)
			if path is not None:
				break
			tried.add(following.sound)
			self.scheduler.exclude(following.sound, instant)
			following = self._decide(instant, None).play
		if (following is None) or (path is None):
			return
		# Un sonore réservé commence sans nouvelle décision : le prêt de nom se relit à son début.
		self.lender = self.scheduler.lender(instant)
		following = self._lent(following)
		if rise is None:
			rise = entry_fade(previous_end_crossfade, parameters.start_crossfade)
		preload = self.preload
		if (preload is not None) and (preload.sound == following.sound):
			# Le stream préchargé prend l'antenne, sa mémoire tampon pleine ; une autre voie préchargée attend son
			# tour, ou est abandonnée si son stream n'est plus prévu (_reserve).
			track = preload.track
			self.preload = None
			track.take_air()
			track.fade(1.0, rise)
		else:
			track = self.engine.play(
				path,
				parameters.duration,
				rise,
				parameters.end_crossfade,
				offset=parameters.offset,
				departure=parameters.departure_volume,
				arrival=parameters.arrival_volume,
				buffer=parameters.buffer,
			)
		play = self._begin(following, instant)
		if self.current is not None:
			self.outgoing_list.append(self.current)
		self.current = Playback(following, parameters, track, play)
		self.history.expire(self.connection, instant, following.sound)
		self._reserve(instant)

	def _begin(self, choice: Choice, instant: datetime) -> Play:
		self._note_on_air(choice, instant)
		line = choice.line
		if line is None:
			sequence = None
		else:
			sequence = line.sequence
		if line is None:
			sequence_item = None
		else:
			sequence_item = line.id
		play = self.history.begin_play(
			self.connection,
			choice.sound,
			choice.bank,
			choice.occurrence.event.id,
			_play_item(choice),
			instant,
			sequence,
			sequence_item,
			_lender_id(choice),
		)
		self._announced_lender = self.lender
		if self.outputs is not None:
			self.outputs.lend(self.connection, _lender_id(choice))
			self.outputs.started_play(self.connection, play)
		return play

	def _finish(
		self,
		play: Play,
		instant: datetime,
		cut: bool = False,
		error: str | None = None,
		kind: str = N_("interrupted playback"),
	) -> None:
		self.history.finish_play(self.connection, play, instant, cut=cut, error=error, kind=kind)
		if self.outputs is not None:
			self.outputs.finished_play(self.connection, play, instant)

	# ─── Socket d'état (https://github.com/dascritch/machincast/issues/20) ───

	def _publish(self, instant: datetime, stop: bool = False) -> None:
		"""Publie l'état s'il a changé, ou si le dernier date de minimal_publication, pour la progression."""
		if self.state is None:
			return
		message = self._state(instant, stop)
		stable = json.dumps({**message, "current": _without_progress(message["current"])}, default=str)
		previous, published_to = self._publication
		old = (published_to is None) or (instant - published_to >= timedelta(seconds=self.minimal_publication))
		if (stop) or (stable != previous) or (old):
			self.state.publish({"timestamp": iso(instant), **message})
			self._publication = (stable, instant)

	def _state(self, instant: datetime, stop: bool) -> dict[str, Any]:
		current = self.current
		ongoing = None
		if current is not None:
			parameters = current.parameters
			position = current.track.position()
			duration = parameters.duration
			if current.details is None:
				current.details = self._details(current.choice, current.play)
			ongoing = {
				**_display(current.choice, parameters),
				**current.details,
				"start": iso(current.play.start),
				"duration": _seconds(duration),
				"estimated_end": iso(_estimated_end(current)),
				"cut_by": None,
				"cut_by_id": None,
				"position": round(position.total_seconds(), 3),
				"progress": _progress(position, duration),
				"buffer": _buffer(current.track, parameters),
			}
			if current.cutoff is not None:
				event = current.cutoff.occurrence.event
				ongoing |= {"cut_by": event.name, "cut_by_id": event.id}
		next_ = None
		upcoming: list[dict[str, Any]] = []
		reserve = self.reserve
		if reserve is not None:
			if (self._reserved_details is None) or (self._reserved_details[0] is not reserve):
				self._reserved_details = (reserve, self._details(reserve.choice, None))
			starts = self._starts()
			if starts == []:
				starts = [None]
			# La fin de chaque sonore : le début de l'événement qui coupera le suivant, sinon sa durée.
			planned_list = []
			for planned in self.upcoming:
				planned_list.append(planned.cutoff)
			cutoffs = planned_list + [None]
			remainder = [(reserve.choice, reserve.parameters, reserve.healthy, self._reserved_details[1])]
			upcoming_list = []
			for planned in self.upcoming:
				upcoming_list.append((planned.choice, planned.parameters, planned.healthy, planned.details))
			remainder += upcoming_list
			announcements = []
			for (choice, announced_parameters, healthy, announced_details), start, cutoff in zip(
				remainder, starts, cutoffs, strict=False
			):
				announcements.append(
					_announces(
						self._lent(choice, start), announced_parameters, healthy, announced_details, start, cutoff
					)
				)
			next_, upcoming = announcements[0], announcements[1:]
		if stop:
			running = "stopped"
		else:
			if (current is not None) or (self.outgoing_list):
				running = "playing"
			else:
				running = "dead_air"
		following = None
		if not stop:
			following = _event_announcement(self._the_following_event(instant))
		return {
			"state": running,
			"current": ongoing,
			"next": next_,
			"upcoming": upcoming,
			"next_event": following,
		}

	def _note_on_air(self, choice: Choice | None, instant: datetime) -> None:
		"""Avant le passage qui commence, ou à l'arrêt (None) : la fin de la séquence et de l'événement qu'il ne
		continue pas, puis le début des siens, dans le log et le journal du binaire
		(https://github.com/dascritch/machincast/issues/153). Les heures sont celles de l'antenne. L'événement à
		l'antenne est celui qui prête son nom, s'il y en a un (https://github.com/dascritch/machincast/issues/399)."""
		previous, self._on_air = self._on_air, choice
		same_occurrence = (
			(previous is not None) and (choice is not None) and (previous.occurrence.key == choice.occurrence.key)
		)
		remainder = (same_occurrence) and (_continues_sequence(previous, choice))
		if (previous is not None) and (previous.line is not None) and (not remainder):
			self._note(SEQUENCE_END, self._on_air_sequence, previous.occurrence.event.id, instant)
		self._note_events(choice, instant)
		if choice is None:
			return
		if (choice.line is not None) and (not remainder):
			# Dans sa propre transaction : la connexion n'en laisse jamais une ouverte, qui retiendrait l'airplay.
			with self.connection.transaction():
				line = self.connection.execute(
					"SELECT internal_name FROM sequences WHERE id = %s", (choice.line.sequence,)
				).fetchone()
			name = str(choice.line.sequence)
			if line is not None:
				name = str(line[0])
			self._on_air_sequence = N_("“{name}”, in “{name2}”").format(name=name, name2=choice.occurrence.event.name)
			self._note(SEQUENCE_START, self._on_air_sequence, choice.occurrence.event.id, instant)

	def _note_events(self, choice: Choice | None, instant: datetime) -> None:
		"""La fin de l'événement à l'antenne, puis le début du nouveau, s'il change : au début d'un passage, ou quand
		une occurrence commence ou cesse de prêter son nom pendant un sonore."""
		if choice is None:
			on_air = None
		else:
			on_air = (choice.lender) or (choice.occurrence)
		previous, self._on_air_occurrence = self._on_air_occurrence, on_air
		same = (previous is not None) and (on_air is not None) and (previous.key == on_air.key)
		if (previous is not None) and (not same):
			self._note(EVENT_END, N_("“{name}”").format(name=previous.event.name), previous.event.id, instant)
		if (choice is None) or (on_air is None) or (same):
			return
		message = _on_air_event(on_air)
		if choice.lender is not None:
			message = N_("{on_air}, lending its name to “{name}”").format(
				on_air=message, name=choice.occurrence.event.name
			)
		self._note(EVENT_START, message, on_air.event.id, instant)

	def _note(self, kind: str, message: str, event: int, instant: datetime) -> None:
		self.history.record(self.connection, "info", kind, message, instant, event=event)
		if self.outputs is not None:
			self.outputs.announce(kind, message)

	def _details(self, choice: Choice, play: Play | None) -> dict[str, Any]:
		"""Le contexte d'un sonore pour la socket d'état (https://github.com/dascritch/machincast/issues/144) :
		l'occurrence de son événement, sa séquence et sa banque ; pour le sonore en cours, le texte que la page
		publique affiche de son passage, masquage appliqué."""
		occurrence = choice.occurrence
		sequence = choice.item.sequence
		with self.connection.transaction():
			names = self.connection.execute(
				"SELECT (SELECT internal_name FROM sequences WHERE id = %s),"
				" (SELECT internal_name FROM banks WHERE id = %s)",
				(sequence, choice.bank),
			).fetchone()
		assert names is not None
		details: dict[str, Any] = {
			"event_id": occurrence.event.id,
			"event_priority": occurrence.event.priority.value,
			"event_start": iso(occurrence.start),
			"event_end": iso(occurrence.end),
			"sequence": names[0],
			"sequence_id": sequence,
			"bank": names[1],
			"bank_id": choice.bank,
		}
		if play is not None:
			lines = read_plays(self.connection, 1, play.id, ongoing_lender=(_lender_id(choice),))
			details["public_text"] = None
			if lines != []:
				details["public_text"] = public_text(lines[0], self._metadata())
		return details

	def _metadata(self) -> Metadata:
		if self.metadata is not None:
			return self.metadata
		if self.outputs is not None:
			return self.outputs.metadata
		return Metadata(hide=False, public_text="")

	def _check_expiries(self, instant: datetime) -> None:
		last = self.checked_expiries
		if (last is None) or (instant - last >= EXPIRY_CHECK):
			self.checked_expiries = instant
			self.history.expire(self.connection, instant)


def _display(choice: Choice, parameters: Parameters) -> dict[str, Any]:
	kind = "file"
	if parameters.stream:
		kind = "stream"
	if choice.lender is None:
		event_name = None
	else:
		event_name = choice.lender.event.name
	return {
		"sound_id": choice.sound,
		"type": kind,
		"artist": parameters.artist,
		"title": parameters.title,
		"location": parameters.location,
		"event": choice.occurrence.event.name,
		# https://github.com/dascritch/machincast/issues/399, sans changer la version.
		"lender": event_name,
		"lender_id": _lender_id(choice),
	}


def _announces(
	choice: Choice,
	parameters: Parameters,
	healthy: bool | None,
	details: dict[str, Any],
	start: datetime | None,
	cutoff: Cutoff | None,
) -> dict[str, Any]:
	"""Ce que la socket d'état dit du prochain sonore, ou d'un sonore à venir."""
	duration = parameters.duration
	end = None
	if (start is not None) and (duration is not None):
		end = start + duration
	if cutoff is not None:
		end = cutoff.instant
	return {
		**_display(choice, parameters),
		**details,
		"estimated_start": iso(start),
		"duration": _seconds(duration),
		"estimated_end": iso(end),
		"healthy": healthy,
	}


def _dead_air_message(dead_air: DeadAir, parameters: Parameters) -> str:
	"""« <fichier> : blanc de 10 s à 1:23,4 du sonore, niveau moyen -95,2 dB » ; un stream compte depuis le début de
	sa lecture (https://github.com/dascritch/machincast/issues/122)."""
	level = N_("digital silence")
	if dead_air.level is not None:
		level = N_("average level {level:.1f} dB").format(level=dead_air.level)
	duration = f"{dead_air.duration.total_seconds():.1f}".removesuffix(".0")
	ou = N_("of the sound")
	if parameters.stream:
		ou = N_("of its playback")
	sound = (parameters.location) or (parameters.address)
	return N_("{sound}: dead air of {duration} s at {timecode} {ou}, {level}").format(
		sound=sound, duration=duration, timecode=_timecode(dead_air.position), ou=ou, level=level
	)


def _timecode(position: timedelta) -> str:
	"""« 1:23.4 », ou « 1:02:03.4 » au-delà d'une heure : minutes, secondes et dixièmes, pour le log, en anglais."""
	tenths = round(position.total_seconds() * 10)
	hours, rest = divmod(tenths, 36000)
	minutes, rest = divmod(rest, 600)
	seconds = f"{rest // 10:02d}.{rest % 10}"
	if hours > 0:
		return f"{hours}:{minutes:02d}:{seconds}"
	return f"{minutes}:{seconds}"


SOUNDS_ON_AIR = _("Sounds on air")
"""La rubrique des rapports de crash de Machin player (https://github.com/dascritch/machincast/issues/342)."""
CRASH_UPCOMING = 5


def _crash_line(label: str, sound: dict[str, Any] | None) -> str:
	"""« À l'antenne : Matinale / Séquence / Banque / Artiste – Titre / /srv/fichier.flac »."""
	if sound is None:
		return f"{label} : —"
	event = str((sound.get("event")) or ("—"))
	if sound.get("lender"):
		event = _("{event}, in the name of “{lender}”").format(event=event, lender=sound["lender"])
	part_list = []
	for part in (sound.get("artist"), sound.get("title")):
		if part:
			part_list.append(str(part))
	title = " – ".join(part_list)
	parts = [
		event,
		(sound.get("sequence")) or ("—"),
		(sound.get("bank")) or ("—"),
		(title) or ("—"),
		(sound.get("location")) or ("—"),
	]
	texts = []
	for part in parts:
		texts.append(str(part))
	return f"{label} : {' / '.join(texts)}"


def crash_text(previous: dict[str, Any] | None, message: dict[str, Any]) -> str:
	"""Les sonores précédent, en cours, et les CRASH_UPCOMING suivants annoncés, une ligne chacun : événement,
	séquence, banque, artiste et titre, fichier."""
	coming = [message.get("next"), *((message.get("upcoming")) or ([]))]
	sound_list = []
	for sound in coming:
		if sound is not None:
			sound_list.append(sound)
	coming = sound_list[:CRASH_UPCOMING]
	lines = [
		_("Event / sequence / bank / sound / file"),
		_crash_line(_("Previous"), previous),
		_crash_line(_("Playing now"), message.get("current")),
	]
	rank_list = []
	for rank, sound in enumerate(coming, 1):
		rank_list.append(_crash_line(_("Next {rank}").format(rank=rank), sound))
	lines += rank_list
	return "\n".join(lines)


def _lender_id(choice: Choice) -> int | None:
	"""L'événement au nom de qui le sonore passe (https://github.com/dascritch/machincast/issues/399)."""
	if choice.lender is None:
		return None
	return choice.lender.event.id


def _play_item(choice: Choice) -> int | None:
	"""L'élément de liste qui a fait jouer le sonore ; aucun pour le stream d'un feed qui coupe l'antenne."""
	if choice.item.id == OUTSIDE_LIST:
		return None
	return choice.item.id


def _planned_play(choice: Choice, start: datetime) -> Play:
	line = choice.line
	if line is None:
		sequence = None
	else:
		sequence = line.sequence
	if line is None:
		sequence_item = None
	else:
		sequence_item = line.id
	return Play(
		uuid.uuid4(),
		choice.sound,
		choice.bank,
		choice.occurrence.event.id,
		_play_item(choice),
		start,
		sequence,
		sequence_item,
	)


def _same_cutoff(planned: Cutoff | None, cutoff: Cutoff | None) -> bool:
	if (planned is None) or (cutoff is None):
		return (planned is None) and (cutoff is None)
	return (planned.instant == cutoff.instant) and (planned.occurrence.key == cutoff.occurrence.key)


def _occurrence_end(occurrence: Occurrence) -> datetime | None:
	if occurrence.end is None:
		return None
	return occurrence.end.astimezone()


def _following_instant(
	start: datetime, parameters: Parameters, occurrence: Occurrence, cutoff: Cutoff | None
) -> datetime | None:
	"""Quand le sonore qui commence à debut appellera son suivant : à la coupure, au début de son crossfade de fin, ou,
	pour un stream, à la fin de son événement ; None si on ne le sait pas."""
	if cutoff is not None:
		return cutoff.instant
	if parameters.duration is not None:
		return start + max(timedelta(0), parameters.duration - parameters.end_crossfade)
	if not parameters.stream:
		return None
	return _occurrence_end(occurrence)


def _following_start(
	start: datetime, parameters: Parameters, occurrence: Occurrence, cutoff: Cutoff | None, incoming: Parameters
) -> datetime | None:
	"""Quand démarrera le sonore entrant, après celui qui commence à debut : à la coupure, qui est nette ; au début du
	crossfade de fin s'ils se superposent, sinon à la fin ; pour un stream, à la fin de son événement, où il s'éteint.
	None si on ne le sait pas."""
	if cutoff is not None:
		return cutoff.instant
	if parameters.duration is not None:
		return start + sequencing(parameters.duration, parameters.end_crossfade, incoming.start_crossfade)
	end = None
	if parameters.stream:
		end = _occurrence_end(occurrence)
	if (end is None) or (overlay(parameters.end_crossfade, incoming.start_crossfade)):
		return end
	return end + parameters.end_crossfade


def _continues_sequence(previous: Choice | None, choice: Choice | None) -> bool:
	"""Le passage suit-il le précédent dans la même séquence, un élément plus loin ?"""
	if (previous is None) or (choice is None) or (previous.line is None) or (choice.line is None):
		return False
	return (previous.item.id == choice.item.id) and (choice.line.position > previous.line.position)


def _hour(instant: datetime) -> str:
	"""« 20:00 », ou « 19:59:51 » quand les secondes comptent."""
	if instant.second == 0:
		return f"{instant:%H:%M}"
	return f"{instant:%H:%M:%S}"


def _on_air_event(occurrence: Occurrence) -> str:
	"""« « Journal », émission, de 20:00 à 20:30 » ; « depuis 19:00 » sans fin, « permanent » pour un fil musical."""
	start, end = occurrence.start, occurrence.end
	hours = N_("permanent")
	if (start is not None) and (end is None):
		hours = N_("since {hour}").format(hour=_hour(start))
	if (start is not None) and (end is not None):
		hours = N_("from {hour} to {hour2}").format(hour=_hour(start), hour2=_hour(end))
	return N_("“{name}”, {priorities}, {hours}").format(
		name=occurrence.event.name, priorities=PRIORITIES[occurrence.event.priority], hours=hours
	)


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


def _horizon(playback: Playback, instant: datetime) -> datetime:
	"""Jusqu'où un événement qui commence coupe le sonore : jusqu'à ce que le suivant soit demandé, au début de son
	crossfade de fin ; pour un stream, jusqu'à la fin de son occurrence, où il s'éteint, ou CUTOFF_HORIZON."""
	return _horizon_of(playback.play.start, playback.parameters, playback.choice.occurrence, instant)


def _horizon_of(start: datetime, parameters: Parameters, occurrence: Occurrence, instant: datetime) -> datetime:
	duration = parameters.duration
	if duration is not None:
		return start + duration - parameters.end_crossfade
	horizon = max(instant, start) + CUTOFF_HORIZON
	end = _occurrence_end(occurrence)
	if end is not None:
		horizon = min(horizon, end)
	return horizon


def _estimated_end(playback: Playback) -> datetime | None:
	"""L'instant de la coupure annoncée, sinon la fin du sonore ; pour un stream, la fin de son événement, où il
	s'éteint (https://github.com/dascritch/machincast/issues/242), None sans elle."""
	if playback.cutoff is not None:
		return playback.cutoff.instant
	if playback.parameters.duration is None:
		if not playback.parameters.stream:
			return None
		return _occurrence_end(playback.choice.occurrence)
	return playback.play.start + playback.parameters.duration


def _seconds(duration: timedelta | None) -> float | None:
	if duration is None:
		return None
	return round(duration.total_seconds(), 3)


def _progress(position: timedelta, duration: timedelta | None) -> float | None:
	"""Part jouée du sonore, de 0 à 1, au millième ; None sans durée connue."""
	if not duration:
		return None
	return round(min(1.0, position / duration), 3)


def _buffer(track: PlaybackTrack, parameters: Parameters) -> dict[str, float] | None:
	"""La mémoire tampon du stream d'un feed, en secondes : ce qu'elle contient, sur sa durée
	(https://github.com/dascritch/machincast/issues/351) ; None sans elle."""
	level = track.buffer_level()
	if (parameters.buffer is None) or (level is None):
		return None
	return {"level": round(level.total_seconds(), 1), "target": round(parameters.buffer.total_seconds(), 1)}


def _without_progress(ongoing: object) -> object:
	if not isinstance(ongoing, dict):
		return ongoing
	without_progress = {}
	for key, value in ongoing.items():
		if key not in ("position", "progression", "buffer"):
			without_progress[key] = value
	return without_progress


def install_stop() -> threading.Event:
	"""SIGTERM (arrêt du service) et SIGINT (Ctrl-C) demandent l'arrêt de la diffusion, sans l'interrompre en
	plein pas : la boucle le voit à la fin du pas, et arrête proprement."""
	stop = threading.Event()

	def ask(number: int, frame: FrameType | None) -> None:
		stop.set()

	signal.signal(signal.SIGTERM, ask)
	signal.signal(signal.SIGINT, ask)
	return stop


def air(broadcast: Broadcast, stop: threading.Event, pause: float = PAUSE) -> None:
	"""Fait tourner la diffusion jusqu'à la demande d'arrêt, puis l'arrête proprement.

	Sur une erreur (base de données perdue, par exemple), la sortie est coupée, la socket d'état fermée et effacée,
	pour que l'interface voie aussitôt l'arrêt (https://github.com/dascritch/machincast/issues/187), et l'erreur
	remonte.
	"""
	broadcast.start()
	try:
		while not stop.is_set():
			broadcast.step()
			stop.wait(pause)
	except BaseException:
		broadcast.engine.cut()
		if broadcast.state is not None:
			broadcast.state.shut_down()
		raise
	broadcast.halt()


def _event_announcement(occurrence: Occurrence | None) -> dict[str, Any] | None:
	"""L'événement suivant, tel que la socket d'état le publie (https://github.com/dascritch/machincast/issues/257)."""
	if occurrence is None:
		return None
	event = occurrence.event
	return {
		"id": event.id,
		"name": event.name,
		"priority": event.priority.value,
		"start": iso(occurrence.start),
		"end": iso(occurrence.end),
	}
