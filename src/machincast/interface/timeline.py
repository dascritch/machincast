"""Frise de la pré-écoute d'un fichier (https://github.com/dascritch/machincast/issues/224, spec § 8.3).

La frise remplace la barre de position de la pré-écoute d'un fichier. Elle s'étend sur toute la durée du fichier :

- Plan : ce que l'antenne fera du fichier, d'après la base. Ses silences détectés (detected_start, detected_end,
  https://github.com/dascritch/machincast/issues/146), retirés s'il active la détection ; la partie jouée et ses
  fondus, placés autour des silences comme la diffusion les place (machincast.player.fades.put, selon les positions
  des fondus, https://github.com/dascritch/machincast/issues/234) ; ses crossfades, ceux des préférences pour un
  crossfade non paramétré (machincast.player.broadcast.crossfade), et le volume de l'écoute comme à l'antenne, le
  long de l'enveloppe de la diffusion (machincast.player.engine.envelope). Ouverte depuis une fiche, la pré-écoute
  ne connaît pas la banque par laquelle passera le sonore : ses règles n'y figurent pas ; l'onglet Antenne les connaît.
- FormeDOnde : la forme d'onde, calculée en tâche de fond par un pipeline GStreamer à part (uridecodebin, level,
  fakesink sans synchronisation : aussi vite que le décodage). Le minuteur de la pré-écoute relève son bus : rien ne
  bloque l'interface, et la forme apparaît au fil du décodage. Le fichier n'est que lu.
- Frise : le dessin. La forme d'onde, les silences hachurés (hachures pleines s'ils sont retirés à l'antenne, pâles
  s'ils y sont joués), les fondus en rampes, la tête de lecture. Un clic, ou un glissement relâché, demande une position
  (placee) ; au clavier, les flèches déplacent d'une seconde. L'infobulle nomme la zone sous la souris, ou l'instant.
  Des curseurs, « Début » et « Fin » (show_sliders), se glissent à la souris, même sur une frise qui n'est pas
  interactive : la fiche d'un sonore y règle ses silences détectés (https://github.com/dascritch/machincast/issues/330).
  Le début ne passe jamais après la fin, ni la fin avant le début (moved_slider).
"""

import math
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Literal

import gi

gi.require_version("Gst", "1.0")
import psycopg  # noqa: E402
from gi.repository import Gst  # noqa: E402
from psycopg.rows import TupleRow  # noqa: E402
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
	QBrush,
	QColor,
	QHelpEvent,
	QKeyEvent,
	QMouseEvent,
	QPainter,
	QPaintEvent,
	QPalette,
	QPen,
	QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget  # noqa: E402

from machincast.configuration import Crossfades  # noqa: E402
from machincast.i18n import _, decimal  # noqa: E402
from machincast.interface import states  # noqa: E402
from machincast.player.broadcast import crossfade  # noqa: E402
from machincast.player.engine import envelope  # noqa: E402
from machincast.player.fades import (  # noqa: E402
	DEFAULT_ENTRY,
	DEFAULT_OUTPUT,
	LABELS,
	Placement,
	Position,
	put,
)

APPROACH = 5.0
"""Secondes avant le fondu de sortie où « Fin jouée » place la lecture : de quoi entendre l'enchaînement arriver."""
PEAKS = 1500
"""Nombre de mesures de la forme d'onde sur tout le fichier : bien plus que de points sur la largeur de la frise."""
MINIMAL_STEP = 0.01
"""Secondes de la plus courte mesure de la forme d'onde, celle des fichiers courts."""
STEP_WITHOUT_DURATION = 0.05
"""Secondes d'une mesure, quand la durée du fichier n'est pas connue."""
HEIGHT = 72
"""Points de la frise en hauteur."""
UNAVAILABLE = _("Waveform unavailable:")
LEGEND_MARGIN = 6
"""Points autour du texte de la légende, sur son fond."""
SLIDER_SOCKET_JACK = 6
"""Points de part et d'autre d'un curseur où la souris le prend."""
SLIDER_NAMES = {"start": _("Start"), "end": _("End")}
"""Points autour du texte de la légende, sur son fond."""
Hatching = Literal["full", "pale", "none"]


def seconds(value: float) -> str:
	"""« 0,50 s »."""
	return decimal(f"{value:.2f} s")


def instant(value: float) -> str:
	"""« 0:01,50 », ou « 1:02:03,25 » au-delà d'une heure : au centième de seconde."""
	hundredths = round(max(0.0, value) * 100)
	whole_list, rest = divmod(hundredths, 100)
	hours, whole_list = divmod(whole_list, 3600)
	minutes, units = divmod(whole_list, 60)
	if hours > 0:
		return f"{hours}:{minutes:02d}:{units:02d},{rest:02d}"
	return f"{minutes}:{units:02d},{rest:02d}"


@dataclass(frozen=True)
class Area:
	"""Une zone de la frise, en secondes du fichier."""

	name: str
	start: float
	end: float
	hatching: Hatching
	tooltip: str


@dataclass(frozen=True)
class Plan:
	"""Ce que l'antenne fera du fichier : ses silences, sa partie jouée, ses crossfades. Durées en secondes."""

	duration: float
	start_silence: float | None = None
	"""Silence détecté au début ; None : aucun de ce côté."""
	end_silence: float | None = None
	"""Silence détecté à la fin, compté depuis la fin du fichier ; None : aucun de ce côté."""
	removed_silences: bool = False
	"""Le sonore active la détection de silence : ses silences ne sont pas joués."""
	start_crossfade: float = 0.0
	end_crossfade: float = 0.0
	start_origin: str | None = None
	"""D'où vient le crossfade de début, quand ce n'est pas du sonore : « défaut », les préférences, ou la banque
	(« imposé par la banque », « de la banque »). None : celui du sonore, ou aucun."""
	end_origin: str | None = None
	audited: bool = True
	"""Un audit complet a mesuré ses silences (audited_at)."""
	entry_position: Position = DEFAULT_ENTRY
	"""Où le fade-in se place par rapport au début détecté, pour un sonore joué sans ses silences
	(https://github.com/dascritch/machincast/issues/234)."""
	output_position: Position = DEFAULT_OUTPUT
	"""Où le fade-out se place par rapport à la fin détectée, de même."""

	def placement(self) -> Placement:
		"""La lecture et ses fondus, comme la diffusion les place (machincast.player.fades.put) : autour des
		silences détectés d'un sonore joué sans eux, selon les positions des fondus
		(https://github.com/dascritch/machincast/issues/234)."""
		return put(
			timedelta(seconds=self.duration),
			_duration(self.start_silence),
			_duration(self.end_silence),
			self.removed_silences,
			timedelta(seconds=self.start_crossfade),
			timedelta(seconds=self.end_crossfade),
			self.entry_position,
			self.output_position,
		)

	def trims(self) -> bool:
		"""Les silences sont retirés à l'antenne : le sonore les active, et ils laissent quelque chose du fichier."""
		start = (self.start_silence) or (0.0)
		end = self.duration - ((self.end_silence) or (0.0))
		return (self.removed_silences) and (end > start)

	def part(self) -> tuple[float, float]:
		"""Début et fin de la partie jouée à l'antenne, en secondes du fichier."""
		placement = self.placement()
		de = placement.start.total_seconds()
		return de, de + placement.duration.total_seconds()

	def _points(self) -> list[tuple[timedelta, float]]:
		placement = self.placement()
		return envelope(
			placement.duration, placement.entry_fade, placement.output_fade, placement.departure, placement.arrival
		)

	def fades(self) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
		"""Les fondus d'entrée et de sortie, en secondes du fichier, comme l'enveloppe de la diffusion les place, sans
		leur part hors du fichier ; None sans crossfade de ce côté."""
		de, _a = self.part()
		placement = self.placement()
		points = []
		for moment, volume in self._points():
			points.append((de + moment.total_seconds(), volume))
		entry = None
		if placement.entry_fade > timedelta(0):
			entry = (points[0][0], points[1][0])
		output = None
		if placement.output_fade > timedelta(0):
			output = (points[-2][0], points[-1][0])
		return entry, output

	def volumes_to_edges(self) -> tuple[float, float]:
		"""Le volume au début de la lecture, et à sa fin : 0, sauf un fondu qui déborde du fichier."""
		placement = self.placement()
		return placement.departure, placement.arrival

	def areas(self) -> list[Area]:
		"""Les silences et les fondus, dans l'ordre du fichier : silence de début, fondus, silence de fin."""
		hatching: Hatching = "pale"
		sort = _("played on air")
		if self.trims():
			hatching, sort = "full", _("removed on air")
		areas: list[Area] = []
		if (self.start_silence is not None) and (self.start_silence > 0):
			text = _("Start silence: {seconds}, {sort}").format(seconds=seconds(self.start_silence), sort=sort)
			areas.append(Area(_("start silence"), 0.0, self.start_silence, hatching, text))
		entry, output = self.fades()
		if entry is not None:
			text = _(
				"Start crossfade: {seconds}{origin},{position} rising if the previous sound has an end crossfade"
			).format(
				seconds=seconds(self.start_crossfade),
				origin=_origin(self.start_origin),
				position=self._position(self.entry_position, _("at the detected start")),
			)
			areas.append(Area(_("fade in"), entry[0], entry[1], "none", text))
		if output is not None:
			text = _("End crossfade: {seconds}{origin}").format(
				seconds=seconds(self.end_crossfade), origin=_origin(self.end_origin)
			)
			position = self._position(self.output_position, _("at the detected end"))
			if position != "":
				text = f"{text},{position.rstrip(',')}"
			areas.append(Area(_("fade out"), output[0], output[1], "none", text))
		if (self.end_silence is not None) and (self.end_silence > 0):
			text = _("End silence: {seconds}, {sort}").format(seconds=seconds(self.end_silence), sort=sort)
			areas.append(Area(_("end silence"), self.duration - self.end_silence, self.duration, hatching, text))
		return areas

	def _position(self, position: Position, ou: str) -> str:
		"""« se termine au début détecté, » : où le fondu tombe, pour un sonore joué sans ses silences ; rien sinon."""
		if not self.trims():
			return ""
		return f" {LABELS[position]} {ou},"

	def summary(self) -> str:
		"""« Joué à l'antenne : 0:00,50 → 0:01,50 (0:01,00) », et si ses silences n'ont jamais été mesurés, le dire."""
		de, a = self.part()
		text = _("Played on air: {instant} → {instant2} ({instant3})").format(
			instant=instant(de), instant2=instant(a), instant3=instant(a - de)
		)
		if not self.audited:
			text = _("{text} · silences never measured").format(text=text)
		return text

	def start_marker(self) -> float:
		"""Où « Début joué » place la lecture : au début de la partie jouée."""
		return self.part()[0]

	def end_marker(self) -> float:
		"""Où « Fin jouée » place la lecture : APPROCHE secondes avant le fondu de sortie, ou avant la fin de la partie
		jouée sans fondu ; jamais avant son début."""
		de, a = self.part()
		_entry, output = self.fades()
		end = a
		if output is not None:
			end = output[0]
		return max(de, end - APPROACH)

	def volume(self, position: float) -> float:
		"""Le volume de l'écoute comme à l'antenne à cette position du fichier, de 0 à 1 : nul hors de la partie jouée,
		le long de l'enveloppe de la diffusion dedans."""
		de, a = self.part()
		if (position < de) or (position > a):
			return 0.0
		relative = position - de
		points = []
		for moment, point_volume in self._points():
			points.append((moment.total_seconds(), point_volume))
		for (before, since), (after, to) in zip(points, points[1:], strict=False):
			if before <= relative <= after:
				if after == before:
					return to
				return since + (to - since) * (relative - before) / (after - before)
		return points[-1][1]


def _duration(value: float | None) -> timedelta | None:
	if value is None:
		return None
	return timedelta(seconds=value)


def _origin(origin: str | None) -> str:
	if origin is None:
		return ""
	return f" ({origin})"


@dataclass(frozen=True)
class BankRule:
	"""La règle d'un côté des crossfades de la banque qui fournit le sonore (crossfade_rule), et sa durée."""

	rule: str | None = None
	duration: timedelta | None = None


WITHOUT_BANK = BankRule()


def crossfade_origin(of_sound: timedelta | None, bank: BankRule, default: timedelta | None) -> str | None:
	"""D'où vient le crossfade que retient machincast.player.broadcast.crossfade, dans le même ordre."""
	if bank.rule == "forced":
		return _("imposed by the bank")
	if of_sound is not None:
		return None
	if bank.rule == "default":
		return _("from the bank")
	if default is not None:
		return _("default")
	return None


def sound_plan(
	duration: timedelta,
	detected_start: timedelta | None,
	detected_end: timedelta | None,
	detection_silences: bool,
	start_crossfade: timedelta | None,
	end_crossfade: timedelta | None,
	defects: Crossfades,
	audited: bool,
	bank: tuple[BankRule, BankRule] = (WITHOUT_BANK, WITHOUT_BANK),
) -> Plan:
	"""Le plan d'un sonore d'après ses colonnes en base. Sans banque, un crossfade non paramétré (None) est celui des
	préférences ; avec, les règles de crossfade de début et de fin de la banque s'appliquent avant, comme à la
	diffusion (https://github.com/dascritch/machincast/issues/230). silence_detection : celle du sonore, ou de sa
	banque. Les fondus se placent selon les positions des préférences
	(https://github.com/dascritch/machincast/issues/234)."""

	def optional(value: timedelta | None) -> float | None:
		if value is None:
			return None
		return value.total_seconds()

	start, end = bank
	return Plan(
		duration=duration.total_seconds(),
		start_silence=optional(detected_start),
		end_silence=optional(detected_end),
		removed_silences=detection_silences,
		start_crossfade=crossfade(start_crossfade, start.rule, start.duration, defects.start).total_seconds(),
		end_crossfade=crossfade(end_crossfade, end.rule, end.duration, defects.end).total_seconds(),
		start_origin=crossfade_origin(start_crossfade, start, defects.start),
		end_origin=crossfade_origin(end_crossfade, end, defects.end),
		audited=audited,
		entry_position=defects.entry,
		output_position=defects.output,
	)


def read_plan(
	connection: psycopg.Connection[TupleRow], sound: int, bank: int | None, defects: Crossfades
) -> Plan | None:
	"""Le plan d'un fichier tel que la diffusion le joue, fourni par cette banque ou sans banque (None) : ses silences
	retirés si le sonore ou la banque active la détection, ses crossfades selon les règles de la banque ; None pour un
	stream, un fichier sans durée, ou un sonore qui n'est plus en base (https://github.com/dascritch/machincast/issues/230)."""
	with connection.transaction():
		line = connection.execute(
			"SELECT s.type::text, s.duration, s.detected_start, s.detected_end,"
			" s.silence_detection OR coalesce(b.silence_detection, false), s.crossfade_start, s.crossfade_end,"
			" s.audited_at IS NOT NULL, b.crossfade_start_rule::text, b.crossfade_start, b.crossfade_end_rule::text,"
			" b.crossfade_end"
			" FROM sounds s LEFT JOIN banks b ON b.id = %s WHERE s.id = %s",
			(bank, sound),
		).fetchone()
	if line is None:
		return None
	category, duration, start, end, detection, cd, cf, audited, *rules = line
	start_rule, start_bank, end_rule, end_bank = rules
	if (category != "file") or (not isinstance(duration, timedelta)):
		return None
	return sound_plan(
		duration,
		_interval(start),
		_interval(end),
		bool(detection),
		_interval(cd),
		_interval(cf),
		defects,
		bool(audited),
		(
			BankRule(_text(start_rule), _interval(start_bank)),
			BankRule(_text(end_rule), _interval(end_bank)),
		),
	)


def _interval(value: object) -> timedelta | None:
	if isinstance(value, timedelta):
		return value
	return None


def _text(value: object) -> str | None:
	if value is None:
		return None
	return str(value)


PEAK_OPACITY, MEAN_OPACITY = 90, 90
"""Opacité, sur 255, des crêtes de la forme d'onde, et du niveau moyen par-dessus : là où ils se superposent, le
niveau moyen est plus foncé."""
DEMONSTRATION_REPORT = 0.6
"""Niveau moyen de la forme d'onde de démonstration, rapporté à sa crête."""


class WaveShape:
	"""La forme d'onde d'un fichier : le niveau crête et le niveau moyen (RMS) de chaque mesure, de 0 à 1, calculés en
	tâche de fond (https://github.com/dascritch/machincast/issues/223)."""

	def __init__(self, path: Path, duration: float | None) -> None:
		Gst.init(None)
		self.path = path
		self.step = STEP_WITHOUT_DURATION
		"""Secondes de chaque mesure."""
		if (duration is not None) and (duration > 0):
			self.step = max(MINIMAL_STEP, duration / PEAKS)
		self.peaks: list[float] = []
		self.means: list[float] = []
		"""Niveau moyen de chaque mesure, au rang de sa crête."""
		self.finished = False
		"""Le calcul est fini : tout le fichier est mesuré, ou une erreur l'a arrêté."""
		self.error: str | None = None
		self._pipeline: Gst.Element | None = None
		self._level: Gst.Element | None = None
		self._piloted: states.Pilot | None = None

	def start(self) -> None:
		"""Lance le décodage, sans l'attendre."""
		if not self.path.is_file():
			self._fail(_("file not found, {path}").format(path=self.path))
			return
		pipeline = Gst.parse_launch("uridecodebin name=source ! audioconvert ! level name=niveau ! fakesink sync=false")
		assert isinstance(pipeline, Gst.Bin)
		source, level = pipeline.get_by_name("source"), pipeline.get_by_name("niveau")
		assert (source is not None) and (level is not None), _("install gstreamer1.0-plugins-base and -good")
		source.set_property("uri", Gst.filename_to_uri(str(self.path)))
		level.set_property("interval", round(self.step * Gst.SECOND))
		level.set_property("post-messages", True)
		self._pipeline, self._level = pipeline, level
		self._piloted = states.Pilot(pipeline)
		self._piloted.to(Gst.State.PLAYING)

	def read_off(self) -> bool:
		"""Les mesures arrivées depuis la dernière relève ; vrai s'il y en a de nouvelles, ou si le calcul vient de
		finir."""
		pipeline = self._pipeline
		if pipeline is None:
			return False
		bus = pipeline.get_bus()
		assert bus is not None
		new_list = False
		while (message := bus.pop()) is not None:
			if message.type == Gst.MessageType.EOS:
				self.halt()
				self.finished = True
				return True
			if message.type == Gst.MessageType.ERROR:
				error, _detail = message.parse_error()
				self._fail(str(error.message))
				return True
			if (message.type == Gst.MessageType.ELEMENT) and (message.src == self._level):
				new_list = (self._measure(message.get_structure())) or (new_list)
		return new_list

	def halt(self) -> None:
		if self._piloted is not None:
			self._piloted.switch_off()
		self._pipeline, self._piloted, self._level = None, None, None

	def covered(self) -> float:
		"""Secondes du fichier déjà mesurées."""
		return len(self.peaks) * self.step

	def amplitudes(self, de: float, a: float) -> list[float]:
		"""Les mesures entièrement comprises entre ces deux instants."""
		amplitudes = []
		for index, peak in enumerate(self.peaks):
			if (index * self.step >= de) and ((index + 1) * self.step <= a):
				amplitudes.append(peak)
		return amplitudes

	def means_between(self, de: float, a: float) -> list[float]:
		"""Les niveaux moyens des mesures entièrement comprises entre ces deux instants."""
		means_between = []
		for index, mean in enumerate(self.means):
			if (index * self.step >= de) and ((index + 1) * self.step <= a):
				means_between.append(mean)
		return means_between

	def _fail(self, error: str) -> None:
		self.halt()
		self.error = error
		self.finished = True

	def _measure(self, structure: Gst.Structure | None) -> bool:
		if (structure is None) or (structure.get_name() != "level"):
			return False
		peak, mean = structure.get_value("peak"), structure.get_value("rms")
		if (not peak) or (not mean):
			return False
		self.peaks.append(_amplitude(peak))
		self.means.append(min(self.peaks[-1], _amplitude(mean)))
		return True


def _amplitude(levels: object) -> float:
	"""Le canal le plus fort, de 0 à 1 ; un silence numérique donne -inf, ou un niveau très bas."""
	assert isinstance(levels, (list, tuple))
	value_list = []
	for value in levels:
		value_list.append(float(value))
	decibels = max(value_list)
	if not math.isfinite(decibels):
		return 0.0
	return min(1.0, max(0.0, 10 ** (decibels / 20)))


def demonstration_shape(duration: float, start_silence: float, end_silence: float) -> WaveShape:
	"""Une forme d'onde déjà calculée, sans fichier, pour montrer une frise
	(https://github.com/dascritch/machincast/issues/234) : un son qui respire, silencieux pendant ses silences."""
	shape = WaveShape(Path("demonstration"), duration)
	measures = round(duration / shape.step)
	for index in range(measures):
		instant = index * shape.step
		amplitude = 0.0
		if start_silence <= instant < duration - end_silence:
			amplitude = 0.5 + 0.25 * math.sin(instant * 1.7) + 0.15 * math.sin(instant * 6.3)
		shape.peaks.append(amplitude)
		shape.means.append(amplitude * DEMONSTRATION_REPORT)
	shape.finished = True
	return shape


class Timeline(QWidget):
	"""La frise d'un fichier : forme d'onde, silences, fondus et tête de lecture."""

	placed = Signal(float)
	"""Une position demandée, en secondes du fichier."""
	clicked = Signal()
	"""Un clic sur une frise qui n'est pas interactive : sur l'onglet Antenne, il demande la pré-écoute du sonore
	(https://github.com/dascritch/machincast/issues/223)."""
	moved_slider = Signal(str, float)
	"""Un curseur glissé, « debut » ou « fin », et sa position en secondes du fichier, bornée par l'autre curseur."""

	def __init__(self, parent: QWidget | None = None, interactive: bool = True) -> None:
		"""interactive : un clic, un glissement ou les flèches demandent une position ; sur l'onglet Antenne, la frise
		ne fait que se regarder (https://github.com/dascritch/machincast/issues/230)."""
		super().__init__(parent)
		self.interactive = interactive
		self.plan: Plan | None = None
		self.duration: float | None = None
		self.shape: WaveShape | None = None
		self.head: float | None = None
		"""La tête de lecture, en secondes du fichier ; None : pas de lecture."""
		self.legend = ""
		"""Un texte écrit au milieu de la frise, sur un fond qui le garde lisible : le temps qui reste au sonore en
		cours, sur l'onglet Antenne (https://github.com/dascritch/machincast/issues/230) ; vide : aucun."""
		self._slides = False
		self.sliders: dict[str, float] = {}
		"""Les curseurs montrés, « debut » et « fin », en secondes du fichier."""
		self._taken_slider: str | None = None
		self.setMinimumHeight(HEIGHT)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
		self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
		self.setAccessibleName(_("File timeline"))
		if interactive:
			self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
			self.setAccessibleName(_("Position in the file"))
		self.setAttribute(Qt.WidgetAttribute.WA_Hover)
		# La souris change d'allure au-dessus d'un curseur, même sans bouton enfoncé.
		self.setMouseTracking(True)

	def display(self, plan: Plan | None, duration: float | None) -> None:
		"""Le plan du fichier, et sa durée ; sans plan, la frise ne montre que la forme d'onde et la tête."""
		self.plan = plan
		self.duration = duration
		if plan is not None:
			self.duration = plan.duration
		self.head = None
		description = ""
		if plan is not None:
			description = plan.summary()
		self.setAccessibleDescription(description)
		self.update()

	def show_shape(self, shape: WaveShape | None) -> None:
		self.shape = shape
		self.update()

	def put_head(self, position: float | None) -> None:
		"""La tête de lecture suit la lecture, sauf pendant un glissement : elle suit alors la souris."""
		if self._slides:
			return
		if position != self.head:
			self.head = position
			self.update()

	def show_sliders(self, sliders: dict[str, float]) -> None:
		"""Les curseurs à montrer, et leur position ; aucun : la frise n'en a pas. Un curseur pris par la souris garde
		la sienne."""
		taken = self._taken_slider
		if (taken is not None) and (taken not in sliders):
			self._taken_slider = None
		else:
			if taken is not None:
				sliders = {**sliders, taken: self.sliders.get(taken, sliders[taken])}
		if sliders != self.sliders:
			self.sliders = dict(sliders)
			self.update()

	def slider_in(self, x: float) -> str | None:
		"""Le curseur sous ce point, à SLIDER_SOCKET_JACK près ; le plus proche, si les deux y sont."""
		near_list = []
		for name, position in self.sliders.items():
			if abs(self.seconds_to_x(position) - x) <= SLIDER_SOCKET_JACK:
				near_list.append((abs(self.seconds_to_x(position) - x), name))
		if near_list == []:
			return None
		return min(near_list)[1]

	def bound(self, name: str, position: float) -> float:
		"""La position d'un curseur dans le fichier, le début jamais après la fin, ni la fin avant le début."""
		bottom, top = 0.0, self.extent()
		if name == "start":
			top = min(top, self.sliders.get("end", top))
		else:
			bottom = max(bottom, self.sliders.get("start", bottom))
		return max(bottom, min(top, position))

	def show_legend(self, text: str) -> None:
		if text != self.legend:
			self.legend = text
			self.update()

	def legend_background(self) -> QRectF | None:
		"""Le fond de la légende, centré sur la frise : le texte, avec une marge ; None sans légende."""
		if self.legend == "":
			return None
		text = self.fontMetrics().boundingRect(self.legend)
		width = min(float(self.width() - 2), text.width() + 2.0 * LEGEND_MARGIN)
		height = min(float(self.height() - 2), text.height() + float(LEGEND_MARGIN))
		centre = QRectF(self.rect()).center()
		return QRectF(centre.x() - width / 2, centre.y() - height / 2, width, height)

	def remark(self) -> str:
		"""Ce que la frise dit en clair : « Forme d'onde indisponible : … », ou rien."""
		if (self.shape is not None) and (self.shape.error is not None):
			return f"{UNAVAILABLE} {self.shape.error}"
		return ""

	def extent(self) -> float:
		"""Les secondes que couvre la largeur de la frise : la durée du fichier, sinon ce que la forme en a mesuré."""
		if (self.duration is not None) and (self.duration > 0):
			return self.duration
		if self.shape is not None:
			return max(self.shape.covered(), STEP_WITHOUT_DURATION)
		return 1.0

	def x_to_seconds(self, x: float) -> float:
		width = max(1, self.width())
		return max(0.0, min(1.0, x / width)) * self.extent()

	def seconds_to_x(self, value: float) -> float:
		return value / self.extent() * self.width()

	def tooltip_to(self, x: float) -> str:
		"""La zone sous ce point, la plus précise d'abord, ou l'instant du fichier."""
		position = self.x_to_seconds(x)
		if self.plan is not None:
			for area in self.plan.areas():
				if area.start <= position <= area.end:
					return area.tooltip
		return instant(position)

	# ─── Événements ────────────────────────────────────────

	def event(self, radio_event: QEvent) -> bool:
		if radio_event.type() == QEvent.Type.ToolTip:
			assert isinstance(radio_event, QHelpEvent)
			QToolTip.showText(radio_event.globalPos(), self.tooltip_to(radio_event.pos().x()), self)
			return True
		return super().event(radio_event)

	def mousePressEvent(self, event: QMouseEvent) -> None:
		if event.button() == Qt.MouseButton.LeftButton:
			self._taken_slider = self.slider_in(event.position().x())
			if self._taken_slider is not None:
				self._slide_slider(event.position().x())
				return
		if not self.interactive:
			if event.button() == Qt.MouseButton.LeftButton:
				self.clicked.emit()
			super().mousePressEvent(event)
			return
		if event.button() != Qt.MouseButton.LeftButton:
			super().mousePressEvent(event)
			return
		self._slides = True
		self._follow(event.position().x())

	def mouseMoveEvent(self, event: QMouseEvent) -> None:
		if self._taken_slider is not None:
			self._slide_slider(event.position().x())
			return
		if self.slider_in(event.position().x()) is not None:
			self.setCursor(Qt.CursorShape.SizeHorCursor)
		else:
			self.unsetCursor()
		if not self.interactive:
			super().mouseMoveEvent(event)
			return
		if self._slides:
			self._follow(event.position().x())

	def mouseReleaseEvent(self, event: QMouseEvent) -> None:
		if (self._taken_slider is not None) and (event.button() == Qt.MouseButton.LeftButton):
			self._slide_slider(event.position().x())
			self._taken_slider = None
			return
		if not self.interactive:
			super().mouseReleaseEvent(event)
			return
		if (event.button() != Qt.MouseButton.LeftButton) or (not self._slides):
			super().mouseReleaseEvent(event)
			return
		self._follow(event.position().x())
		self._slides = False
		assert self.head is not None
		self.placed.emit(self.head)

	def keyPressEvent(self, event: QKeyEvent) -> None:
		if not self.interactive:
			super().keyPressEvent(event)
			return
		step = {Qt.Key.Key_Right: 1.0, Qt.Key.Key_Left: -1.0}.get(Qt.Key(event.key()))
		if step is None:
			super().keyPressEvent(event)
			return
		position = max(0.0, min(self.extent(), ((self.head) or (0.0)) + step))
		self.head = position
		self.update()
		self.placed.emit(position)

	def _slide_slider(self, x: float) -> None:
		name = self._taken_slider
		assert name is not None
		position = self.bound(name, self.x_to_seconds(x))
		if position != self.sliders.get(name):
			self.sliders[name] = position
			self.update()
			self.moved_slider.emit(name, position)

	def _follow(self, x: float) -> None:
		self.head = self.x_to_seconds(x)
		self.update()

	# ─── Dessin ────────────────────────────────────────────

	def paintEvent(self, _event: QPaintEvent) -> None:
		with QPainter(self) as painter:
			painter.setRenderHint(QPainter.RenderHint.Antialiasing)
			palette = self.palette()
			# Jamais grisée : à l'arrêt, la frise reste lisible, et se lit comme pendant la lecture.
			group = QPalette.ColorGroup.Normal
			frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
			painter.fillRect(frame, palette.color(group, QPalette.ColorRole.Base))
			self._draw_shape(painter, palette.color(group, QPalette.ColorRole.Text))
			if self.plan is not None:
				self._draw_areas(painter, palette.color(group, QPalette.ColorRole.Text))
				self._draw_fades(painter, palette.color(group, QPalette.ColorRole.Highlight))
			self._draw_head(painter, palette.color(group, QPalette.ColorRole.Highlight))
			self._draw_sliders(painter, palette.color(group, QPalette.ColorRole.Link))
			remark = self.remark()
			background = self.legend_background()
			if remark != "":
				# Sous la légende, s'il y en a une : la remarque prend le bas de la frise.
				place = QRectF(frame)
				if background is not None:
					place.setTop(background.bottom())
				painter.setPen(palette.color(group, QPalette.ColorRole.Text))
				painter.drawText(place, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, remark)
			if background is not None:
				veil = QColor(palette.color(group, QPalette.ColorRole.Base))
				veil.setAlpha(225)
				painter.setPen(QPen(palette.color(group, QPalette.ColorRole.Mid), 1))
				painter.setBrush(veil)
				painter.drawRoundedRect(background, 4, 4)
				painter.setPen(palette.color(group, QPalette.ColorRole.Text))
				painter.drawText(background, Qt.AlignmentFlag.AlignCenter, self.legend)
			painter.setPen(QPen(palette.color(group, QPalette.ColorRole.Mid), 1))
			painter.setBrush(Qt.BrushStyle.NoBrush)
			painter.drawRect(frame)

	def columns(self) -> list[float]:
		"""L'amplitude crête de chaque colonne de points : la plus forte des mesures qui y tombent."""
		if self.shape is None:
			return []
		return self._columns(self.shape.peaks)

	def medium_columns(self) -> list[float]:
		"""Le niveau moyen de chaque colonne de points : le plus fort des mesures qui y tombent, sous la crête."""
		if self.shape is None:
			return []
		return self._columns(self.shape.means)

	def _columns(self, measures: list[float]) -> list[float]:
		if (self.shape is None) or (not measures):
			return []
		heights = [0.0] * max(1, self.width())
		step = self.shape.step
		for index, peak in enumerate(measures):
			# Une mesure plus large qu'un point en couvre plusieurs : aucune colonne ne reste vide entre deux mesures.
			left = min(len(heights) - 1, int(self.seconds_to_x(index * step)))
			right = max(left + 1, min(len(heights), math.ceil(self.seconds_to_x((index + 1) * step))))
			for column in range(left, right):
				heights[column] = max(heights[column], peak)
		last = min(len(heights), math.ceil(self.seconds_to_x(self.shape.covered())))
		return heights[:last]

	def _draw_shape(self, painter: QPainter, colour: QColor) -> None:
		"""Les crêtes, pâles, puis par-dessus le niveau moyen, plus foncé
		(https://github.com/dascritch/machincast/issues/223)."""

		def draw_heights(heights: list[float], opacity: int) -> None:
			if not heights:
				return
			middle = self.height() / 2
			half = middle - 2
			top = []
			for x, height in enumerate(heights):
				top.append(QPointF(x + 0.5, middle - height * half))
			bottom = []
			for x, height in reversed(list(enumerate(heights))):
				bottom.append(QPointF(x + 0.5, middle + height * half))
			tint = QColor(colour)
			tint.setAlpha(opacity)
			painter.setPen(Qt.PenStyle.NoPen)
			painter.setBrush(tint)
			painter.drawPolygon(QPolygonF(top + bottom))

		for heights, opacity in ((self.columns(), PEAK_OPACITY), (self.medium_columns(), MEAN_OPACITY)):
			draw_heights(heights, opacity)

	def _draw_areas(self, painter: QPainter, colour: QColor) -> None:
		"""Les silences : hachures pleines et voile s'ils sont retirés à l'antenne, hachures pâles sans voile s'ils y
		sont joués. La différence tient au motif, pas qu'à la couleur."""
		assert self.plan is not None

		def draw_area(area: Area) -> None:
			if area.hatching == "none":
				return
			rectangle = QRectF(
				self.seconds_to_x(area.start), 0, self.seconds_to_x(area.end - area.start), self.height()
			)
			line = QColor(colour)
			pattern = Qt.BrushStyle.BDiagPattern
			if area.hatching == "full":
				veil = QColor(colour)
				veil.setAlpha(45)
				painter.fillRect(rectangle, veil)
				line.setAlpha(190)
			else:
				pattern = Qt.BrushStyle.FDiagPattern
				line.setAlpha(70)
			painter.fillRect(rectangle, QBrush(line, pattern))

		for area in self.plan.areas():
			draw_area(area)

	def _draw_fades(self, painter: QPainter, colour: QColor) -> None:
		"""Les fondus : une rampe, et le volume retiré au-dessus d'elle, voilé."""
		assert self.plan is not None
		entry, output = self.plan.fades()
		departure, arrival = self.plan.volumes_to_edges()
		top, bottom = 1.0, self.height() - 1.0
		# Un fondu qui déborde du fichier part, ou s'arrête, au volume qu'il a au bord du fichier.
		entry_bottom = bottom - departure * (bottom - top)
		output_bottom = bottom - arrival * (bottom - top)
		veil = QColor(colour)
		veil.setAlpha(50)

		def draw_fade(fade: tuple[float, float] | None, rise: bool) -> None:
			if fade is None:
				return
			left, right = self.seconds_to_x(fade[0]), self.seconds_to_x(fade[1])
			origin, end = QPointF(left, entry_bottom), QPointF(right, top)
			corner = QPointF(left, top)
			if not rise:
				origin, end = QPointF(left, top), QPointF(right, output_bottom)
				corner = QPointF(right, top)
			painter.setPen(Qt.PenStyle.NoPen)
			painter.setBrush(veil)
			painter.drawPolygon(QPolygonF([origin, end, corner]))
			painter.setPen(QPen(colour, 2))
			painter.drawLine(origin, end)

		for fade, rise in ((entry, True), (output, False)):
			draw_fade(fade, rise)

	def _draw_sliders(self, painter: QPainter, colour: QColor) -> None:
		"""Chaque curseur : un trait pointillé, une poignée en bas, et son nom, vers l'intérieur de la partie jouée."""
		for name, position in self.sliders.items():
			x = self.seconds_to_x(position)
			painter.setPen(QPen(colour, 2, Qt.PenStyle.DashLine))
			painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
			painter.setPen(Qt.PenStyle.NoPen)
			painter.setBrush(colour)
			bottom = float(self.height())
			painter.drawRect(QRectF(x - SLIDER_SOCKET_JACK / 2, bottom - 10, SLIDER_SOCKET_JACK, 10))
			text = SLIDER_NAMES[name]
			width = self.fontMetrics().horizontalAdvance(text)
			left = x + 4
			if name == "end":
				left = x - 4 - width
			painter.setPen(colour)
			painter.drawText(QPointF(left, bottom - 14), text)

	def _draw_head(self, painter: QPainter, colour: QColor) -> None:
		if self.head is None:
			return
		x = self.seconds_to_x(self.head)
		painter.setPen(QPen(colour, 2))
		painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(colour)
		painter.drawPolygon(QPolygonF([QPointF(x - 5, 0), QPointF(x + 5, 0), QPointF(x, 6)]))
