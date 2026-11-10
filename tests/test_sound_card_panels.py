"""Scénarios des encarts dépliables et de la vérification complète de la fiche d'un sonore
(https://github.com/dascritch/machincast/issues/190).

Les étapes de la fenêtre, des fiches et des sonores en base sont dans tests/interface_steps.py. Le décodage de la
vérification complète passe par machincast.interface.check._check_full_file, que le scénario peut
retenir jusqu'à ce qu'il le laisse finir.
"""

import threading
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QLabel, QPushButton, QSlider
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Crossfades
from machincast.fingerprint import file_state
from machincast.indexer.decoding import Check
from machincast.interface import check, preferences
from machincast.interface.expandable import is_collapsed
from machincast.interface.sound_card import SoundCard
from tests.interface_steps import NAME, Context, window

scenarios("sound_card_panels.feature")

Connection = psycopg.Connection[tuple[object, ...]]
DELAY = 10000
"""Millisecondes laissées à la vérification complète d'un fichier de test."""


def card(interface: Context) -> SoundCard:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, SoundCard), opened
	return opened


def panels(interface: Context) -> list[QGroupBox]:
	"""Les encarts montrés par la fiche, dans l'ordre de leur création."""
	return [group for group in card(interface).findChildren(QGroupBox) if not group.isHidden()]


def title(group: QGroupBox) -> str:
	"""Le titre de l'encart, sans la flèche d'un encart dépliable."""
	return group.title().removeprefix("▸ ").removeprefix("▾ ")


# ─── Étant donné ───────────────────────────────────────────


@pytest.fixture
def retained() -> threading.Event:
	"""Posé par le scénario pour laisser finir la vérification complète retenue."""
	return threading.Event()


@given("la vérification complète retenue par le scénario")
def retain(monkeypatch: pytest.MonkeyPatch, retained: threading.Event) -> None:
	true = check._check_full_file

	def wait(path: Path, *, silence_threshold: float | None = None) -> Check:
		assert retained.wait(timeout=DELAY / 1000), "vérification jamais laissée finir"
		return true(path, silence_threshold=silence_threshold)

	monkeypatch.setattr(check, "_check_full_file", wait)


@given(
	parsers.re(
		r"le sonore « (?P<title>[^»]+) » déjà audité au seuil de (?P<threshold>-?\d+) dB, son fichier inchangé depuis"
	)
)
def already_audited(interface: Context, empty_database: Connection, title: str, threshold: str) -> None:
	"""Sa date et sa taille sont celles du fichier, audité après sa dernière modification."""
	line = empty_database.execute("SELECT location FROM sounds WHERE title = %s", (title,)).fetchone()
	assert line is not None
	location = line[0]
	state = file_state(Path(str(location)))
	assert state is not None
	modified_at, size = state
	empty_database.execute(
		"UPDATE sounds SET file_modified_at = %s, file_size = %s, checked_at = clock_timestamp(),"
		" audited_at = clock_timestamp(), audit_threshold = %s WHERE title = %s",
		(modified_at, size, float(threshold), title),
	)


@given("le refus de rafraîchir la fiche après la vérification")
def refuse(interface: Context) -> None:
	interface.refresh_after_check = False


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je clique sur le titre de l'encart « {name} »"))
def click_title(interface: Context, qtbot: QtBot, name: str) -> None:
	(group,) = [group for group in panels(interface) if title(group) == name]
	# Le titre est en haut de l'encart, à gauche.
	qtbot.mouseClick(group, Qt.MouseButton.LeftButton, pos=QPoint(12, 6))


@when("la vérification complète se termine")
def finish(interface: Context, qtbot: QtBot, retained: threading.Event) -> None:
	retained.set()
	qtbot.waitUntil(lambda: not window(interface).full_check.ongoing(), timeout=DELAY)


@given(parsers.parse("les crossfades des préférences au dixième de seconde, jusqu'à {maximum:d} secondes"))
def preferences_to_tenth(monkeypatch: pytest.MonkeyPatch, maximum: int) -> None:
	monkeypatch.setattr(
		preferences, "_current_list", Crossfades(granularity="tenth", maximum=timedelta(seconds=maximum))
	)


@when(
	parsers.re(
		r"je coche le crossfade de (?P<side>début|fin) de la fiche, et pousse son curseur de (?P<notches>\d+) crans"
	)
)
def push(interface: Context, qtbot: QtBot, side: str, notches: str) -> None:
	ui = card(interface).ui
	if side == "début":
		box, field = (ui.has_start_crossfade, ui.start_crossfade)
	else:
		box, field = (ui.has_end_crossfade, ui.end_crossfade)
	box.setChecked(True)
	slider = field.findChild(QSlider)
	assert slider is not None
	slider.setFocus()
	for _ in range(int(notches)):
		qtbot.keyClick(slider, Qt.Key.Key_Right)


@when(parsers.parse("je coche le début détecté de la fiche, à {seconds} seconde"))
def detected_start(interface: Context, seconds: str) -> None:
	ui = card(interface).ui
	ui.has_detected_start.setChecked(True)
	ui.detected_start.setValue(float(seconds.replace(",", ".")))


@when(parsers.re(r"je (?P<gesture>coche|décoche) « Jouer sans les silences détectés » dans la fiche"))
def play_without_silences(interface: Context, gesture: str) -> None:
	card(interface).ui.detection_silences.setChecked(gesture == "coche")


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"les encarts (?P<state>repliés|dépliés) de la fiche sont (?P<names>«.+)"))
def panels_according_to_state(interface: Context, state: str, names: str) -> None:
	found_list = [title(group) for group in panels(interface) if is_collapsed(group) is (state == "repliés")]
	assert found_list == NAME.findall(names)


@then(parsers.parse("la fiche montre la dernière vérification complète « {text} »"))
def last_check(interface: Context, text: str) -> None:
	assert card(interface).ui.checks_at.text() == text


@then("la fiche montre une dernière vérification complète datée")
def dated_check(interface: Context) -> None:
	assert card(interface).ui.checks_at.text() not in ("", "jamais")


@then(parsers.re(r"le bouton « (?P<text>[^»]+) » de la fiche est (?P<state>actif|inactif)"))
def button(interface: Context, text: str, state: str) -> None:
	(found,) = [button for button in card(interface).findChildren(QPushButton) if button.text() == text]
	assert found.isEnabled() is (state == "actif")


@then(parsers.parse("la question après la vérification a dit « {text} »"))
def question(interface: Context, text: str) -> None:
	assert interface.questions == [f"après vérification : {text}"]


@then(parsers.parse("le sonore du fichier « {path} » a été vérifié en entier, ses silences mesurés"))
def checks_in_integer(interface: Context, empty_database: Connection, qtbot: QtBot, path: str) -> None:
	def lu() -> tuple[object, ...] | None:
		return empty_database.execute(
			"SELECT checked_at IS NOT NULL, duration IS NOT NULL, detected_end IS NOT NULL FROM sounds"
			" WHERE location = %s",
			(interface.path(path),),
		).fetchone()

	qtbot.waitUntil(lambda: lu() == (True, True, True), timeout=DELAY)


@when(parsers.parse("je clique dans l'encart « {name} », sous son titre"))
def click_content(interface: Context, qtbot: QtBot, name: str) -> None:
	(group,) = [group for group in panels(interface) if title(group) == name]
	# Déplié, l'encart grandit quand sa disposition s'applique.
	qtbot.waitUntil(lambda: group.height() > 4 * group.fontMetrics().height(), timeout=1000)
	qtbot.mouseClick(group, Qt.MouseButton.LeftButton, pos=QPoint(12, group.height() - 4))


@then(
	parsers.re(
		r"l'encart « (?P<name>[^»]+) » a pour titre « (?P<text>[^»]+) », et (?P<gesture>cache|montre)"
		r" la dernière vérification complète"
	)
)
def title_and_content(interface: Context, name: str, text: str, gesture: str) -> None:
	(group,) = [group for group in panels(interface) if title(group) == name]
	assert group.title() == text
	assert card(interface).ui.checks_at.isVisible() is (gesture == "montre")


def labels(group: QGroupBox) -> list[str]:
	"""Les libellés des lignes du formulaire de l'encart, dans l'ordre : l'étiquette, la case, ou la case seule."""
	form = group.findChild(QFormLayout)
	assert form is not None
	found_list: list[str] = []
	for line in range(form.rowCount()):
		for role in (QFormLayout.ItemRole.LabelRole, QFormLayout.ItemRole.SpanningRole):
			item = form.itemAt(line, role)
			if item is None:
				continue
			widget = item.widget()
			if isinstance(widget, (QLabel, QCheckBox)):
				found_list.append(widget.text())
	return found_list


@then(parsers.re(r"l'encart « (?P<name>[^»]+) » a les champs (?P<names>«.+)"))
def panel_fields(interface: Context, name: str, names: str) -> None:
	(group,) = [group for group in panels(interface) if title(group) == name]
	assert labels(group) == NAME.findall(names)


@then(
	parsers.re(
		r"le crossfade de début de la fiche est un curseur horizontal de 0 à (?P<maximum>\d+) secondes,"
		r" au pas de (?P<step>[\d,]+) seconde"
	)
)
def crossfade_slider(interface: Context, maximum: str, step: str) -> None:
	field = card(interface).ui.start_crossfade
	slider = field.findChild(QSlider)
	assert slider is not None
	assert slider.orientation() == Qt.Orientation.Horizontal
	assert (slider.minimum(), field.maximum()) == (0, float(maximum))
	assert slider.maximum() * float(step.replace(",", ".")) == float(maximum)


@given(parsers.parse("le sonore « {name} » a {seconds:d} secondes de crossfade de début en base"))
def crossfade_in_database(empty_database: Connection, name: str, seconds: int) -> None:
	empty_database.execute(
		"UPDATE sounds SET crossfade_start = %s WHERE title = %s", (timedelta(seconds=seconds), name)
	)


@then(parsers.parse("la frise de la fiche montre un crossfade de fin de {end} seconde"))
def timeline_end_crossfade(interface: Context, end: str) -> None:
	plan = card(interface).timeline.plan
	assert (plan is not None) and (plan.end_crossfade == float(end.replace(",", "."))), plan


@then(parsers.parse("le crossfade de début de la fiche montre « {text} »"))
def crossfade_value(interface: Context, text: str) -> None:
	assert card(interface).ui.start_crossfade.text() == text


@then("l'état de la fiche propose :")
def offered_states(interface: Context, datatable: list[list[str]]) -> None:
	choice = card(interface).ui.state
	model = choice.model()
	found_list = []
	for rank in range(choice.count()):
		active = bool(model.flags(model.index(rank, 0)) & Qt.ItemFlag.ItemIsEnabled)
		state = "grisé"
		if active:
			state = "possible"
		if rank == choice.currentIndex():
			state = "choisi"
		found_list.append([choice.itemText(rank), state])
	_headers, *rows = datatable
	assert found_list == [[state.strip(), what.strip()] for state, what in rows]


@then("la frise de la fiche est sur toute sa largeur, au-dessus des encarts")
def full_width_timeline(interface: Context, qtbot: QtBot) -> None:
	opened = card(interface)
	window(interface).show()
	qtbot.wait(50)
	timeline = opened.timeline
	assert timeline.isVisibleTo(opened)
	assert timeline.width() >= opened.width() - 40, (timeline.width(), opened.width())
	bottom = timeline.mapTo(opened, QPoint(0, timeline.height())).y()
	assert bottom <= opened.ui.sound_group.mapTo(opened, QPoint(0, 0)).y()


@then("la frise de la fiche dessine bientôt la forme d'onde de son fichier")
def card_shape(interface: Context, qtbot: QtBot) -> None:
	timeline = card(interface).timeline
	qtbot.waitUntil(
		lambda: (timeline.shape is not None) and (timeline.shape.finished) and (timeline.shape.error is None),
		timeout=DELAY,
	)
	assert timeline.shape is not None
	assert len(timeline.shape.peaks) > 0


@then(
	parsers.parse(
		"la frise de la fiche montre un crossfade de fin de {end} seconde, un silence de {silence} seconde au début,"
		" retiré à l'antenne"
	)
)
def card_plan(interface: Context, end: str, silence: str) -> None:
	plan = card(interface).timeline.plan
	assert plan is not None
	assert (plan.end_crossfade, plan.start_silence, plan.removed_silences) == (
		float(end.replace(",", ".")),
		float(silence.replace(",", ".")),
		True,
	), plan


@then("la frise de la fiche montre les silences joués")
def played_silences(interface: Context) -> None:
	plan = card(interface).timeline.plan
	assert (plan is not None) and (not plan.removed_silences), plan


@then("la fiche n'a pas de frise")
def without_timeline(interface: Context) -> None:
	assert not card(interface).ui.timeline_place.isVisibleTo(card(interface))
