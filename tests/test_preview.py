"""Scénarios de la pré-écoute d'un sonore (https://github.com/dascritch/machincast/issues/116,
https://github.com/dascritch/machincast/issues/29).

Les étapes de la fenêtre et des fiches sont dans tests/interface_steps.py, celles du serveur de flux local dans
tests/broadcast_steps.py. La pré-écoute joue sur la sortie factice des tests, en temps réel : ses positions et son
VU-mètre avancent comme sur un vrai périphérique. Les périphériques du poste sont remplacés par ceux du scénario.
"""

import re
import shutil
import tomllib
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QApplication, QSlider
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.exceptions import TimeoutError as ExceededDelay
from pytestqt.qtbot import QtBot

from machincast.interface.preview import PreviewWindow
from tests.interface_steps import NAME, Context, configuration_file, window
from tests.preview_steps import preview_window
from tests.sounds import SOUND_FILES

scenarios("preview.feature")

Connection = psycopg.Connection[tuple[object, ...]]
DELAY = 5000
"""Millisecondes laissées à GStreamer pour ce qui arrive « bientôt »."""


@given(
	parsers.re(
		r"le sonore « (?P<title>[^»]+) », pour une copie du fichier de test « (?P<file>[^»]+) », de (?P<duration>\d+)"
		r" secondes, aux silences de (?P<start>[\d,]+) s au début et (?P<end>[\d,]+) s à la fin, retirés à l'antenne,"
		r" aux crossfades (?:de (?P<cd>[\d,]+) s au début et (?P<cf>[\d,]+) s à la fin|non paramétrés)"
	)
)
def audited_sound(
	interface: Context,
	empty_database: Connection,
	title: str,
	file: str,
	duration: str,
	start: str,
	end: str,
	cd: str | None,
	cf: str | None,
) -> None:
	"""Un fichier audité, ses silences retirés à l'antenne ; ses crossfades, ou aucun de paramétré (NULL)."""
	copies = interface.directory / file
	shutil.copyfile(SOUND_FILES / file, copies)
	crossfades = [None, None]
	if (cd is not None) and (cf is not None):
		crossfades = [timedelta(seconds=_seconds(cd)), timedelta(seconds=_seconds(cf))]
	empty_database.execute(
		"INSERT INTO sounds (type, location, title, state, duration, detected_start, detected_end, silence_detection,"
		" crossfade_start, crossfade_end, audited_at, audit_threshold)"
		" VALUES ('file', %s, %s, 'active', %s, %s, %s, true, %s, %s, now(), -40)",
		(
			str(copies),
			title,
			timedelta(seconds=int(duration)),
			timedelta(seconds=_seconds(start)),
			timedelta(seconds=_seconds(end)),
			*crossfades,
		),
	)


def _seconds(text: str) -> float:
	return float(text.replace(",", "."))


@given(parsers.parse("le crossfade de début par défaut de {duration} seconde dans la configuration"))
def default_crossfade(interface: Context, duration: str) -> None:
	path = configuration_file(interface)
	with path.open("a", encoding="utf-8") as file:
		file.write(f"\n[crossfades]\nstart = {_seconds(duration)}\n")


@given(parsers.parse("le fichier du sonore « {title} » supprimé"))
def deleted_file(empty_database: Connection, title: str) -> None:
	line = empty_database.execute("SELECT location FROM sounds WHERE title = %s", (title,)).fetchone()
	assert line is not None
	# Une copie de test, dans le répertoire temporaire du scénario.
	Path(str(line[0])).unlink()


@given(parsers.parse("le périphérique de l'antenne « {identifier} »"))
def on_air(interface: Context, identifier: str) -> None:
	interface.audio["device"] = identifier


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je clique sur la frise de la pré-écoute à {percentage:d} % de sa largeur"))
def put(interface: Context, qtbot: QtBot, percentage: int) -> None:
	timeline = preview_window(interface).timeline
	point = QPoint(round(timeline.width() * percentage / 100), timeline.height() // 2)
	qtbot.mouseClick(timeline, Qt.MouseButton.LeftButton, pos=point)


@when(parsers.re(r"je (?P<gesture>coche|décoche) « Écouter comme à l'antenne » dans la pré-écoute"))
def as_on_air(interface: Context, gesture: str) -> None:
	box = preview_window(interface).ui.as_on_air
	assert box.text() == "Écouter comme à l'antenne"
	box.setChecked(gesture == "coche")


@when(parsers.re(r"je clique sur « (?P<name>Début joué|Fin jouée) » dans la pré-écoute"))
def marker(interface: Context, qtbot: QtBot, name: str) -> None:
	ui = preview_window(interface).ui
	button = {"Début joué": ui.played_start, "Fin jouée": ui.played_end}[name]
	assert name in button.text(), button.text()
	qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


@when(parsers.parse("je choisis la sortie « {name} » pour la pré-écoute"))
def choose_output(interface: Context, name: str) -> None:
	choice = preview_window(interface).ui.output
	index = choice.findText(name)
	assert index >= 0, name
	choice.setCurrentIndex(index)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("il n'y a qu'une fenêtre de pré-écoute, titrée « {title} »"))
def a_only(interface: Context, title: str) -> None:
	opened_list = [w for w in QApplication.topLevelWidgets() if (isinstance(w, PreviewWindow)) and (w.isVisible())]
	assert len(opened_list) == 1
	assert opened_list[0].windowTitle() == title


@then(parsers.parse("la sortie de la pré-écoute est « {identifier} »"))
def output(interface: Context, identifier: str) -> None:
	opened = preview_window(interface)
	assert opened.ui.output.currentData() == identifier
	assert opened.player.device == identifier


@then("le VU-mètre de la pré-écoute est au silence")
def to_silence(interface: Context) -> None:
	assert preview_window(interface).vu_meter.levels == []


@then("la pré-écoute montre bientôt les informations :")
def information(interface: Context, qtbot: QtBot, datatable: list[list[str]]) -> None:
	ui = preview_window(interface).ui
	fields = {"Format": ui.format, "Échantillonnage": ui.sampling, "Canaux": ui.channels}
	expected_list = [(name.strip(), value.strip()) for name, value in datatable[1:]]

	def conforms(fetched: str, expected: str) -> bool:
		"""« contient « FLAC » » : le libellé, qui vient de GStreamer, contient ce nom ; sinon, égal."""
		content = re.fullmatch(r"contient « (.+) »", expected)
		if content is not None:
			return content.group(1) in fetched
		return fetched == expected

	def all_() -> bool:
		return all(conforms(fields[name].text(), value) for name, value in expected_list)

	try:
		qtbot.waitUntil(all_, timeout=DELAY)
	except ExceededDelay as error:
		# Les valeurs lues, pour comprendre l'écart sur un autre poste.
		fetched_list = {name: fields[name].text() for name, _value in expected_list}
		raise AssertionError(f"informations lues : {fetched_list}, attendues : {dict(expected_list)}") from error


@then("le débit de la pré-écoute est bientôt donné en kbit/s")
def bitrate(interface: Context, qtbot: QtBot) -> None:
	field = preview_window(interface).ui.bitrate
	qtbot.waitUntil(lambda: field.text().endswith(" kbit/s"), timeout=DELAY)


@then("la pré-écoute donne bientôt des secondes pré-décodées")
def predecoded(interface: Context, qtbot: QtBot) -> None:
	field = preview_window(interface).ui.predecoded
	qtbot.waitUntil(lambda: (field.text().endswith(" s")) and (field.text() != "0,0 s"), timeout=DELAY)


@then(parsers.parse("la position de la pré-écoute est bientôt entre {minimum} et {maximum} seconde"))
def position(interface: Context, qtbot: QtBot, minimum: str, maximum: str) -> None:
	player = preview_window(interface).player
	bottom, top = float(minimum.replace(",", ".")), float(maximum.replace(",", "."))
	qtbot.waitUntil(lambda: bottom <= ((player.position()) or (0.0)) <= top, timeout=DELAY)


@then("la pré-écoute ne joue plus rien")
def more_nothing(interface: Context) -> None:
	assert not preview_window(interface).player.active()


@then(parsers.re(r"la pré-écoute propose les sorties (?P<names>«.+)"))
def offered_outputs(interface: Context, names: str) -> None:
	choice = preview_window(interface).ui.output
	assert [choice.itemText(index) for index in range(choice.count())] == NAME.findall(names)


@then(parsers.parse("le fichier de configuration a pour pré-écoute « {identifier} », avec ses commentaires"))
def written_configuration(interface: Context, identifier: str) -> None:
	path = configuration_file(interface)
	text = path.read_text(encoding="utf-8")
	assert tomllib.loads(text)["audio"]["preview"] == identifier
	initial = interface.initial_configuration.decode("utf-8")
	comments = [line for line in initial.splitlines() if line.startswith("#")]
	assert comments == [line for line in text.splitlines() if line.startswith("#")]


@then("le bouton « Pré-écoute… » de la fiche est inactif")
def inactive_button(interface: Context) -> None:
	card = window(interface).ui.tabs.currentWidget()
	assert not card.ui.preview.isEnabled()


@when(parsers.parse("je force la sortie « {name} » pour la pré-écoute"))
def force_output(interface: Context, name: str) -> None:
	"""Une ligne grisée ne se choisit pas à la souris : le programme la choisit, comme le ferait au pire le clavier."""
	choice = preview_window(interface).ui.output
	index = choice.findText(name)
	assert index >= 0, name
	choice.setCurrentIndex(index)


@then("la pré-écoute propose les sorties :")
def outputs_and_states(interface: Context, datatable: list[list[str]]) -> None:
	choice = preview_window(interface).ui.output
	model = choice.model()
	assert isinstance(model, QStandardItemModel)
	fetched_list = []
	for index in range(choice.count()):
		line_state = "inactive"
		if model.item(index).isEnabled():
			line_state = "active"
		fetched_list.append([choice.itemText(index), line_state])
	assert fetched_list == [[cell.strip() for cell in row] for row in datatable[1:]]


@then(parsers.parse("le fichier de configuration a toujours pour pré-écoute « {identifier} »"))
def intact_configuration(interface: Context, identifier: str) -> None:
	path = configuration_file(interface)
	assert tomllib.loads(path.read_text(encoding="utf-8"))["audio"]["preview"] == identifier
	assert path.read_bytes() == interface.initial_configuration


# ─── Frise (https://github.com/dascritch/machincast/issues/224) ───


@then("la pré-écoute a une frise")
def has_timeline(interface: Context) -> None:
	opened = preview_window(interface)
	assert opened.ui.timeline_area.isVisibleTo(opened)


@then("la pré-écoute n'a ni frise ni barre de position")
def without_timeline(interface: Context) -> None:
	opened = preview_window(interface)
	assert not opened.ui.timeline_area.isVisibleTo(opened)
	assert opened.findChildren(QSlider) == []


@then(parsers.re(r"la frise de la pré-écoute montre les zones (?P<names>«.+)"))
def areas(interface: Context, names: str) -> None:
	plan = preview_window(interface).timeline.plan
	assert plan is not None
	assert [area.name for area in plan.areas()] == NAME.findall(names)


@then(parsers.parse("la frise de la pré-écoute résume « {text} »"))
def summary(interface: Context, text: str) -> None:
	assert preview_window(interface).ui.range_.text() == text


@then(parsers.parse("l'infobulle « {name} » de la frise de la pré-écoute est « {text} »"))
def tooltip(interface: Context, name: str, text: str) -> None:
	plan = preview_window(interface).timeline.plan
	assert plan is not None
	assert [area.tooltip for area in plan.areas() if area.name == name] == [text]


@then("la forme d'onde de la pré-écoute est bientôt complète, silencieuse au début et sonore au milieu")
def full_shape(interface: Context, qtbot: QtBot) -> None:
	opened = preview_window(interface)

	def finished() -> bool:
		shape = opened.shape
		return (shape is not None) and (shape.finished)

	qtbot.waitUntil(finished, timeout=DELAY)
	shape = opened.shape
	assert (shape is not None) and (shape.error is None)
	assert max(shape.amplitudes(0.0, 0.45)) < 0.01
	assert min(shape.amplitudes(0.6, 1.4)) > 0.4
	# La frise dessine ce que la forme a calculé.
	assert opened.timeline.shape is shape


@then(parsers.parse("la frise de la pré-écoute dit « {text} »"))
def remark(interface: Context, qtbot: QtBot, text: str) -> None:
	timeline = preview_window(interface).timeline
	expected = text.replace("…/", f"{interface.directory}/")
	qtbot.waitUntil(lambda: timeline.remark() == expected, timeout=DELAY)


@then(parsers.re(r"le volume de la pré-écoute est (?P<soon>bientôt )?de (?P<volume>\d+) %"))
def volume(interface: Context, qtbot: QtBot, soon: str | None, volume: str) -> None:
	player = preview_window(interface).player
	expected = int(volume) / 100
	if soon is not None:
		qtbot.waitUntil(lambda: abs(player.volume - expected) < 0.001, timeout=DELAY)
	assert player.volume == pytest.approx(expected), player.volume


@then(parsers.parse("le volume de la pré-écoute est sous {volume:d} %, au début de la montée"))
def rising_volume(interface: Context, volume: int) -> None:
	"""Juste après le lancement : la montée de 0,2 seconde commence, au plus une relève de l'affichage plus tôt."""
	player = preview_window(interface).player
	assert player.volume < volume / 100, player.volume


@then(parsers.parse("la pré-écoute s'est arrêtée avant {limit} seconde, à la fin de la partie jouée"))
def stopped_before(interface: Context, limit: str) -> None:
	player = preview_window(interface).player
	last = player.last_position
	assert last is not None
	assert 1.3 <= last <= _seconds(limit), last


@then(parsers.parse("la pré-écoute s'est arrêtée après {limit} seconde"))
def stopped_after(interface: Context, limit: str) -> None:
	last = preview_window(interface).player.last_position
	assert (last is not None) and (last >= _seconds(limit)), last


@then(
	parsers.re(
		r"la position de la pré-écoute passe d'emblée au début de la partie jouée, (?P<start>[\d,]+) seconde"
		r"(?:, .+)?$"
	)
)
def of_outset(interface: Context, qtbot: QtBot, start: str) -> None:
	"""Bien avant que la lecture ne l'atteigne d'elle-même : la lecture y a sauté."""
	player = preview_window(interface).player
	expected = _seconds(start)
	qtbot.waitUntil(lambda: expected - 0.05 <= ((player.position()) or (0.0)) <= expected + 0.3, timeout=250)


@then("la pré-écoute ne calcule plus de forme d'onde")
def more_shape(interface: Context) -> None:
	assert preview_window(interface).shape is None


@then("la fenêtre de pré-écoute est une fenêtre à part, sans fenêtre parente ni premier plan imposé")
def has_share(interface: Context) -> None:
	"""https://github.com/dascritch/machincast/issues/325 : une fenêtre de premier niveau, que le bureau ne rattache pas
	à l'interface (transientParent), et que rien ne garde au-dessus des autres."""
	preview = preview_window(interface)
	assert preview.isWindow()
	assert preview.parentWidget() is None
	assert preview in QApplication.topLevelWidgets()
	flags = preview.windowFlags()
	assert flags & Qt.WindowType.WindowType_Mask == Qt.WindowType.Window
	assert not flags & Qt.WindowType.WindowStaysOnTopHint
	handle = preview.windowHandle()
	assert handle is not None
	assert handle.transientParent() is None


@then("la fenêtre de pré-écoute est fermée avec elle")
def closed_with(interface: Context) -> None:
	assert not preview_window(interface).isVisible()
