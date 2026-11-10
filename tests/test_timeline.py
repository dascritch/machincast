"""Scénarios de la frise de la pré-écoute d'un fichier (https://github.com/dascritch/machincast/issues/224).

La frise s'essaie seule, hors de la fenêtre de pré-écoute : un plan donné par le scénario, sans base, et pour la forme
d'onde, un fichier de test décodé par GStreamer. Ses positions demandées sont notées.
"""

import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtWidgets import QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Crossfades
from machincast.interface.timeline import Plan, Timeline, WaveShape, sound_plan
from tests.categories import HATCHINGS
from tests.sounds import SOUND_FILES

scenarios("timeline.feature")

DELAY = 5000
"""Millisecondes laissées à GStreamer pour ce qui arrive « bientôt »."""


def seconds(text: str) -> float:
	return float(text.replace(",", ".").removesuffix(" s"))


def optional(text: str) -> timedelta | None:
	"""« 0,5 s », ou « aucun » : pas de silence détecté de ce côté, NULL en base."""
	if text == "aucun":
		return None
	return timedelta(seconds=seconds(text))


@dataclass
class Trial:
	parent: QWidget
	plan: Plan | None = None
	timeline: Timeline | None = None
	requested_list: list[float] = field(default_factory=list)
	shape: WaveShape | None = None
	ongoing_to_returned: bool = False
	mouse: int = 0
	"""Où la souris est, en points depuis la gauche de la frise."""
	"""Le calcul n'était pas fini quand demarrer a rendu la main."""

	def the_timeline(self) -> Timeline:
		if self.timeline is None:
			assert self.plan is not None
			self.timeline = Timeline(self.parent)
			self.timeline.resize(400, 72)
			self.timeline.display(self.plan, self.plan.duration)
			self.timeline.placed.connect(self.requested_list.append)
		return self.timeline


@pytest.fixture
def trial(qtbot: QtBot) -> Trial:
	parent = QWidget()
	qtbot.addWidget(parent)
	return Trial(parent)


# ─── Étant donné ───────────────────────────────────────────


@given(
	parsers.re(
		r"un fichier de (?P<duration>[\d,]+) s, aux silences de (?P<start>[\d,]+ s|aucun) au début"
		r" et (?P<end>[\d,]+ s|aucun) à la fin, (?P<removed_list>retirés|joués) à l'antenne, (?P<crossfades>.+)"
	)
)
def file(trial: Trial, duration: str, start: str, end: str, removed_list: str, crossfades: str) -> None:
	defects = Crossfades()
	sound_start: timedelta | None = timedelta(0)
	sound_end: timedelta | None = timedelta(0)
	setting = re.fullmatch(r"aux crossfades de (?P<cd>[\d,]+) s au début et (?P<cf>[\d,]+) s à la fin", crossfades)
	if setting is not None:
		sound_start = timedelta(seconds=seconds(setting["cd"]))
		sound_end = timedelta(seconds=seconds(setting["cf"]))
	default = re.fullmatch(
		r"aux crossfades non paramétrés, par défaut de (?P<cd>[\d,]+) s au début et absent à la fin", crossfades
	)
	if default is not None:
		sound_start, sound_end = None, None
		defects = Crossfades(start=timedelta(seconds=seconds(default["cd"])))
	assert (crossfades == "sans crossfade") or (setting is not None) or (default is not None), crossfades
	trial.plan = sound_plan(
		timedelta(seconds=seconds(duration)),
		optional(start),
		optional(end),
		removed_list == "retirés",
		sound_start,
		sound_end,
		defects,
		audited=True,
	)


@given(parsers.parse("un fichier de {duration} s jamais audité, sans crossfade"))
def never_audited(trial: Trial, duration: str) -> None:
	trial.plan = sound_plan(
		timedelta(seconds=seconds(duration)), None, None, False, timedelta(0), timedelta(0), Crossfades(), audited=False
	)


@given(parsers.parse("la frise large de {width:d} points"))
def width(trial: Trial, width: int) -> None:
	trial.the_timeline().resize(width, 72)


@given(parsers.parse("la tête de lecture de la frise à {position} secondes"))
def head(trial: Trial, position: str) -> None:
	trial.the_timeline().put_head(seconds(position))


@given(parsers.parse("la forme d'onde du fichier de test « {file} », de {duration:d} secondes, en cours de calcul"))
def ongoing_shape(trial: Trial, file: str, duration: int) -> None:
	trial.shape = WaveShape(SOUND_FILES / file, float(duration))
	trial.shape.start()
	trial.ongoing_to_returned = not trial.shape.finished


@given("la forme d'onde d'un fichier qui n'est pas un sonore, en cours de calcul")
def unreadable_shape(trial: Trial, tmp_path: Path) -> None:
	fake = tmp_path / "faux.flac"
	fake.write_text("Ceci n'est pas un sonore.\n" * 200, encoding="utf-8")
	trial.shape = WaveShape(fake, 2.0)
	trial.shape.start()


# ─── Quand ─────────────────────────────────────────────────


def _point(timeline: Timeline, x: int) -> QPoint:
	return QPoint(x, timeline.height() // 2)


@when(parsers.parse("je clique sur la frise à {x:d} points"))
def click(trial: Trial, qtbot: QtBot, x: int) -> None:
	timeline = trial.the_timeline()
	qtbot.mouseClick(timeline, Qt.MouseButton.LeftButton, pos=_point(timeline, x))


@when(parsers.parse("j'appuie sur la frise à {departure:d} points, puis glisse jusqu'à {arrival:d} points"))
def slide(trial: Trial, qtbot: QtBot, departure: int, arrival: int) -> None:
	timeline = trial.the_timeline()
	qtbot.mousePress(timeline, Qt.MouseButton.LeftButton, pos=_point(timeline, departure))
	qtbot.mouseMove(timeline, _point(timeline, arrival))
	trial.mouse = arrival


@when("je relâche la frise")
def release(trial: Trial, qtbot: QtBot) -> None:
	timeline = trial.the_timeline()
	qtbot.mouseRelease(timeline, Qt.MouseButton.LeftButton, pos=_point(timeline, trial.mouse))


@when(parsers.re(r"je tape la flèche (?P<direction>droite|gauche) sur la frise"))
def arrow(trial: Trial, qtbot: QtBot, direction: str) -> None:
	key = {"droite": Qt.Key.Key_Right, "gauche": Qt.Key.Key_Left}[direction]
	qtbot.keyClick(trial.the_timeline(), key)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("la frise joue le fichier de {de} à {a} seconde"))
def part(trial: Trial, de: str, a: str) -> None:
	assert trial.plan is not None
	assert trial.plan.part() == pytest.approx((seconds(de), seconds(a)))


@then(parsers.parse("la frise résume « {text} »"))
def summary(trial: Trial, text: str) -> None:
	assert trial.plan is not None
	assert trial.plan.summary() == text


@then("la frise ne montre aucune zone")
def no_area(trial: Trial) -> None:
	assert trial.plan is not None
	assert trial.plan.areas() == []


@then("la frise montre les zones :")
def areas(trial: Trial, datatable: list[list[str]]) -> None:
	assert trial.plan is not None
	fetched_list = []
	for area in trial.plan.areas():
		fetched_list.append(
			[
				area.name,
				f"{area.start:.2f}".replace(".", ","),
				f"{area.end:.2f}".replace(".", ","),
				HATCHINGS[area.hatching],
				area.tooltip,
			]
		)
	row_list = []
	for row in datatable[1:]:
		cell_list = []
		for cell in row:
			cell_list.append(cell.strip())
		row_list.append(cell_list)
	assert fetched_list == row_list


@then(parsers.parse("l'infobulle de la frise à {x:d} points est « {text} »"))
def tooltip(trial: Trial, x: int, text: str) -> None:
	assert trial.the_timeline().tooltip_to(x) == text


@then(parsers.parse("« Début joué » place la lecture à {start} seconde, et « Fin jouée » à {end} seconde"))
def markers(trial: Trial, start: str, end: str) -> None:
	assert trial.plan is not None
	assert trial.plan.start_marker() == pytest.approx(seconds(start))
	assert trial.plan.end_marker() == pytest.approx(seconds(end))


@then(parsers.parse("à {position} seconde, le volume de l'écoute comme à l'antenne est de {volume:d} %"))
def volume(trial: Trial, position: str, volume: int) -> None:
	assert trial.plan is not None
	assert trial.plan.volume(seconds(position)) == pytest.approx(volume / 100)


@then(parsers.re(r"la frise a demandé la position (?P<position>[\d,]+) secondes?"))
def requested(trial: Trial, position: str) -> None:
	assert trial.requested_list, "aucune position demandée"
	assert trial.requested_list[-1] == pytest.approx(seconds(position), abs=0.01)


@then("la frise n'a demandé aucune position")
def requested_nothing(trial: Trial) -> None:
	assert trial.requested_list == []


@then(parsers.parse("la tête de lecture de la frise est à {position} seconde"))
def head_to(trial: Trial, position: str) -> None:
	head = trial.the_timeline().head
	assert head is not None
	assert head == pytest.approx(seconds(position), abs=0.01)


@then("l'interface a rendu la main avant la fin du calcul")
def main_rendering(trial: Trial) -> None:
	assert trial.ongoing_to_returned


def _read_off_until(qtbot: QtBot, shape: WaveShape, condition: str) -> None:
	def reached() -> bool:
		shape.read_off()
		return bool(getattr(shape, condition))

	qtbot.waitUntil(reached, timeout=DELAY)


@given("la forme d'onde est bientôt complète")
@then("la forme d'onde est bientôt complète")
def full(trial: Trial, qtbot: QtBot) -> None:
	assert trial.shape is not None
	_read_off_until(qtbot, trial.shape, "finished")
	assert trial.shape.error is None


@then(parsers.parse("la forme d'onde est silencieuse de {de} à {a} seconde, et de {of_2} à {has_2} secondes"))
def silent(trial: Trial, de: str, a: str, of_2: str, has_2: str) -> None:
	assert trial.shape is not None
	for start, end in ((de, a), (of_2, has_2)):
		amplitudes = trial.shape.amplitudes(seconds(start), seconds(end))
		assert (amplitudes) and (max(amplitudes) < 0.01), amplitudes


@then(parsers.parse("la forme d'onde est sonore de {de} à {a} seconde, à mi-hauteur"))
def sound(trial: Trial, de: str, a: str) -> None:
	assert trial.shape is not None
	amplitudes = trial.shape.amplitudes(seconds(de), seconds(a))
	assert amplitudes, amplitudes
	for amplitude in amplitudes:
		assert 0.4 <= amplitude <= 0.6, amplitudes


@then(
	parsers.parse(
		"le niveau moyen de la forme d'onde est de {level} de {de} à {a} seconde, et nul de {of_2} à {has_2} seconde"
	)
)
def mean_level(trial: Trial, level: str, de: str, a: str, of_2: str, has_2: str) -> None:
	shape = trial.shape
	assert shape is not None
	assert len(shape.means) == len(shape.peaks)
	means = shape.means_between(seconds(de), seconds(a))
	assert means, means
	for mean in means:
		assert abs(mean - seconds(level)) < 0.03, means
	silences = shape.means_between(seconds(of_2), seconds(has_2))
	assert (silences) and (max(silences) < 0.01), silences


@then(
	parsers.parse("dessinée sur une frise de {width:d} points, le niveau moyen reste sous les crêtes, en chaque point")
)
def mean_under_peaks(trial: Trial, width: int) -> None:
	timeline = Timeline(trial.parent)
	timeline.resize(width, 40)
	timeline.display(None, 2.0)
	timeline.show_shape(trial.shape)
	peaks, means = timeline.columns(), timeline.medium_columns()
	assert len(peaks) == len(means)
	every_one = True
	for mean, peak in zip(means, peaks, strict=True):
		if not (mean <= peak):
			every_one = False
			break
	assert every_one
	assert max(means) > 0.3


@then("la frise de cette forme d'onde dessine le niveau moyen par-dessus les crêtes, plus foncé")
def drawn_mean(trial: Trial) -> None:
	"""Au milieu de la frise, sur la ligne médiane, le niveau moyen ; près du bord haut de la partie sonore, la crête
	seule, plus claire."""
	timeline = Timeline(trial.parent)
	timeline.resize(400, 100)
	timeline.display(None, 2.0)
	timeline.show_shape(trial.shape)
	image = timeline.grab().toImage()
	background = image.pixelColor(200, 3).lightness()
	mean = image.pixelColor(200, 50).lightness()
	# La crête monte à mi-hauteur au-dessus du milieu (0,5 de 48 points), le niveau moyen à 0,35.
	peak = image.pixelColor(200, 50 - 21).lightness()
	assert mean < peak < background, (mean, peak, background)


@then("la forme d'onde est bientôt indisponible")
def unavailable(trial: Trial, qtbot: QtBot) -> None:
	assert trial.shape is not None
	_read_off_until(qtbot, trial.shape, "error")


@then(parsers.parse("la frise de cette forme d'onde dit « {start} » suivi de l'erreur de GStreamer"))
def remark(trial: Trial, start: str) -> None:
	assert trial.shape is not None
	timeline = Timeline(trial.parent)
	timeline.display(None, 2.0)
	timeline.show_shape(trial.shape)
	text = timeline.remark()
	assert text.startswith(f"{start} "), text
	assert text != f"{start} ", text
	# Le calcul s'arrête sur l'erreur : rien ne reste en cours.
	assert trial.shape.finished


@then(
	parsers.parse(
		"dessinée sur une frise de {width:d} points, la forme d'onde couvre chaque point de {de} à {a} seconde,"
		" sans trou"
	)
)
def without_hole(trial: Trial, width: int, de: str, a: str) -> None:
	"""Des mesures plus larges qu'un point : chacune remplit tous les points qu'elle couvre."""
	assert trial.shape is not None
	timeline = Timeline(trial.parent)
	timeline.resize(width, 72)
	timeline.display(None, 2.0)
	timeline.show_shape(trial.shape)
	columns = timeline.columns()
	left, right = round(timeline.seconds_to_x(seconds(de))), round(timeline.seconds_to_x(seconds(a)))
	every_one = True
	for height in columns[left:right]:
		if not (height > 0.4):
			every_one = False
			break
	assert every_one, columns[left:right]


@then("la frise de cette forme d'onde se dessine pareil, active ou inactive")
def same(trial: Trial) -> None:
	"""Inactive, à l'arrêt, la frise ne se grise pas : sa forme d'onde, ses silences et ses fondus gardent leurs
	couleurs."""
	assert trial.shape is not None
	timeline = Timeline(trial.parent)
	timeline.resize(400, 72)
	timeline.display(
		sound_plan(
			timedelta(seconds=2),
			timedelta(seconds=0.5),
			timedelta(seconds=0.5),
			True,
			timedelta(seconds=0.2),
			timedelta(seconds=0.3),
			Crossfades(),
			audited=True,
		),
		2.0,
	)
	timeline.show_shape(trial.shape)
	active = timeline.grab().toImage()
	timeline.setEnabled(False)
	inactive = timeline.grab().toImage()
	assert active == inactive


@when(parsers.parse("la frise a pour légende « {text} »"))
def legend(trial: Trial, text: str) -> None:
	trial.the_timeline().show_legend(text)


@then("la légende de la frise est centrée, sur un fond qui l'entoure")
def centred_legend(trial: Trial) -> None:
	"""Calculée à part du dessin (https://github.com/dascritch/machincast/issues/230) : le fond, centré sur la frise,
	contient le texte, et tient dans la frise."""
	timeline = trial.the_timeline()
	background = timeline.legend_background()
	assert background is not None
	centre = QRectF(timeline.rect()).center()
	assert abs(background.center().x() - centre.x()) <= 1, (background, centre)
	assert abs(background.center().y() - centre.y()) <= 1, (background, centre)
	text = timeline.fontMetrics().boundingRect(timeline.legend)
	assert (background.width() > text.width()) and (background.height() > text.height()), (background, text)
	assert QRectF(timeline.rect()).contains(background), (background, timeline.rect())
