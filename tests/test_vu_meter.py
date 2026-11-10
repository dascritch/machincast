"""Scénarios du VU-mètre de la sortie d'antenne (https://github.com/dascritch/machincast/issues/24).

Les étapes de la fenêtre sont dans tests/interface_steps.py, celles de la pré-écoute dans
tests/preview_steps.py. Sur la sortie factice, le port de monitoring est un signal de test de GStreamer, que le
scénario choisit (monitor.DUMMY_SIGNAL).
"""

import re
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QLabel
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Audio
from machincast.interface import binding, monitor, preview
from machincast.interface.monitor import Monitor, monitor_source
from machincast.interface.vu_meter import VuMeter
from tests.interface_steps import Context, actions, window
from tests.preview_steps import SIGNALS, home

scenarios("vu_meter.feature")

DELAY = 5000


class Pendulum:
	"""Une horloge fictive, en secondes, pour le moniteur et le VU-mètre."""

	def __init__(self) -> None:
		self.instant = 0.0

	def __call__(self) -> float:
		return self.instant


def decibels(text: str) -> list[float]:
	"""« -10, -1,1 » : un niveau par canal, à la virgule décimale."""
	return [float(value.replace(",", ".")) for value in text.split(", ")]


def lines(datatable: list[list[str]]) -> list[dict[str, str]]:
	header, *rest = datatable
	return [dict(zip(header, line, strict=True)) for line in rest]


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.re(r"le blanc de l'antenne constaté après (?P<duration>une demi-seconde|5 secondes)"))
def dead_air_notes(monkeypatch: pytest.MonkeyPatch, duration: str) -> None:
	monkeypatch.setattr(monitor, "DEAD_AIR_DURATION", {"une demi-seconde": 0.5, "5 secondes": 5.0}[duration])


@given("un moniteur de l'antenne, à l'horloge fictive", target_fixture="pendulum")
def fictitious_monitor(qtbot: QtBot) -> tuple[Pendulum, Monitor]:
	pendulum = Pendulum()
	return pendulum, Monitor(None, clock=pendulum)


@given("un VU-mètre, à l'horloge fictive", target_fixture="pendulum")
def fictitious_vu_meter(qtbot: QtBot) -> tuple[Pendulum, VuMeter]:
	pendulum = Pendulum()
	vu_meter = VuMeter(clock=pendulum)
	qtbot.addWidget(vu_meter)
	return pendulum, vu_meter


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le signal de test « {signal} » remplace celui de l'antenne factice"))
def reinstate(monkeypatch: pytest.MonkeyPatch, signal: str) -> None:
	monkeypatch.setattr(monitor, "DUMMY_SIGNAL", SIGNALS[signal])


@when("je clique sur le VU-mètre de l'antenne")
def click(interface: Context, qtbot: QtBot) -> None:
	qtbot.mouseClick(home(interface).vu_meter, Qt.MouseButton.LeftButton)


@when(
	parsers.parse("je construis le port de monitoring de la sortie « {output} », périphérique « {device} »"),
	target_fixture="port",
)
def build(output: str, device: str) -> object:
	return monitor_source(Audio(output, device, "casque"))  # type: ignore[arg-type]


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le VU-mètre de l'antenne est intitulé « {title} », avec l'infobulle « {tooltip} »"))
def heading(interface: Context, title: str, tooltip: str) -> None:
	screen = home(interface)
	assert (screen.ui.on_air_column.title(), screen.vu_meter.toolTip()) == (title, tooltip)


@when(
	parsers.re(
		r"le VU-mètre de l'antenne montre bientôt (?P<count>\d+) canaux, entre (?P<bottom>-?\d+) et (?P<top>-?\d+) dB"
	)
)
@then(
	parsers.re(
		r"le VU-mètre de l'antenne montre bientôt (?P<count>\d+) canaux, entre (?P<bottom>-?\d+) et (?P<top>-?\d+) dB"
	)
)
def channels(interface: Context, qtbot: QtBot, count: str, bottom: str, top: str) -> None:
	vu_meter = home(interface).vu_meter

	def shown_list() -> bool:
		levels = vu_meter.levels
		return (len(levels) == int(count)) and (all(int(bottom) <= level <= int(top) for level in levels))

	qtbot.waitUntil(shown_list, timeout=DELAY)


@when("le port de monitoring de l'antenne cesse de donner du son, sans erreur ni fin")
def cut_port(interface: Context) -> None:
	"""Le signal « coupable » passe par une valve : fermée, plus rien n'en sort, comme d'un flux PipeWire mis en pause
	(https://github.com/dascritch/machincast/issues/311)."""
	pipeline = home(interface).monitor._pipeline
	assert pipeline is not None
	tap = pipeline.get_by_name("robinet")
	assert tap is not None
	tap.set_property("drop", True)


@then(parsers.parse("le VU-mètre de l'antenne reste disponible pendant {seconds:d} secondes"))
def remains_available(interface: Context, qtbot: QtBot, seconds: int) -> None:
	"""Un port qui donne du son n'est jamais gelé, même passé le délai du gel."""
	monitor_ = home(interface).monitor
	limit = time.monotonic() + seconds
	while time.monotonic() < limit:
		qtbot.wait(100)
		assert monitor_.unavailable is None, monitor_.unavailable


@then("le VU-mètre de l'antenne ne montre aucun canal")
def no_channel(interface: Context) -> None:
	screen = home(interface)
	assert (screen.monitor.levels, screen.vu_meter.levels) == ([], [])


@then("la crête de chaque canal est au moins au niveau du VU")
def peaks(interface: Context) -> None:
	vu_meter = home(interface).vu_meter
	assert all(peak >= level for peak, level in zip(vu_meter.peaks, vu_meter.levels, strict=True))


@then("le VU-mètre de l'antenne est disponible")
def available(interface: Context) -> None:
	screen = home(interface)
	assert screen.monitor.unavailable is None
	assert (screen.ui.monitor_state.text(), screen.ui.monitor_state.isVisibleTo(screen)) == ("", False)


@then(parsers.parse("le VU-mètre de l'antenne ne dit plus « {text} »"))
def says_more(interface: Context, text: str) -> None:
	assert home(interface).ui.monitor_state.text() != text


@then("le port de monitoring ne sera pas rouvert")
def not_reopened(interface: Context) -> None:
	assert not home(interface).monitor.planned_retry()


@then("la colonne de l'antenne montre, de haut en bas : « Saturation », le VU-mètre, « Blanc »")
def column_order(interface: Context) -> None:
	ui = home(interface).ui
	arrangement = ui.on_air_layout
	order = [arrangement.itemAt(index).widget() for index in range(arrangement.count())]
	assert order[:3] == [ui.clipping_light, ui.vu_meter_place, ui.dead_air_light]


@then("ses voyants sont écrits plus petit que le titre de la colonne")
def small_lights(interface: Context) -> None:
	ui = home(interface).ui
	title = ui.on_air_column.font().pointSizeF()
	assert all(lamp.font().pointSizeF() < title for lamp in (ui.dead_air_light, ui.clipping_light))


@then(parsers.parse("le voyant « {name} » de l'antenne reste éteint une seconde"))
def remains_off(interface: Context, qtbot: QtBot, name: str) -> None:
	lamp = light(interface, name)
	for _times in range(10):
		qtbot.wait(100)
		assert not lamp.property("allume")  # type: ignore[attr-defined]


@then("ses voyants suivent ses relevés du VU et de la crête de chaque canal :")
def reading_lights(pendulum: tuple[Pendulum, Monitor], datatable: list[list[str]]) -> None:
	clock, monitor = pendulum
	for line in lines(datatable):
		clock.instant = decibels(line["instant"])[0]
		monitor.note(decibels(line["vu"]), decibels(line["crete"]))
		expected = (line["blanc"] == "oui", line["saturation"] == "oui")
		assert (monitor.dead_air, monitor.clipping) == expected, line


@then("son repère suit le VU et la crête de chaque canal qu'il montre :")
def marker(pendulum: tuple[Pendulum, VuMeter], datatable: list[list[str]]) -> None:
	clock, vu_meter = pendulum
	for line in lines(datatable):
		clock.instant = decibels(line["instant"])[0]
		vu_meter.display(decibels(line["vu"]), decibels(line["crete"]))
		assert vu_meter.peaks == decibels(line["crete"]), line
		assert [kept for kept, _since in vu_meter.maintained] == decibels(line["repere"]), line


@then("les voyants de l'antenne sont éteints")
def off_list(interface: Context) -> None:
	ui = home(interface).ui
	assert [bool(ui.dead_air_light.property("allume")), bool(ui.clipping_light.property("allume"))] == [False] * 2


def light(interface: Context, name: str) -> object:
	ui = home(interface).ui
	return {"Blanc": ui.dead_air_light, "Saturation": ui.clipping_light}[name]


@then(parsers.parse("le voyant « {name} » de l'antenne s'allume bientôt"))
def lit_s(interface: Context, qtbot: QtBot, name: str) -> None:
	lamp = light(interface, name)
	qtbot.waitUntil(lambda: bool(lamp.property("allume")), timeout=DELAY)  # type: ignore[attr-defined]


@then(parsers.parse("le voyant « {name} » de l'antenne est éteint"))
def is_off(interface: Context, name: str) -> None:
	assert not light(interface, name).property("allume")  # type: ignore[attr-defined]


@then(parsers.parse("le VU-mètre de l'antenne est indisponible : « {text} »"))
def unavailable(interface: Context, text: str) -> None:
	screen = home(interface)
	assert screen.ui.monitor_state.text() == text
	assert screen.ui.monitor_state.isVisibleTo(screen)
	assert screen.vu_meter.levels == []


@then("l'onglet Antenne ne capture rien")
def nothing_screenshot(interface: Context) -> None:
	monitor = home(interface).monitor
	assert (monitor.active(), monitor.levels, monitor.peaks) == (False, [], [])


@then(parsers.re(r"c'est l'élément « (?P<factory>[^»]+) », avec (?P<properties>.+)"))
def item(port: object, factory: str, properties: str) -> None:
	found_list = [child for child in port.children if child.get_factory().get_name() == factory]  # type: ignore[attr-defined]
	assert len(found_list) == 1, port.children  # type: ignore[attr-defined]
	source = found_list[0]
	for key, value in re.findall(r"([\w-]+) « ([^»]+) »", properties):
		if key == "stream-properties":
			field, expected = value.split("=")
			assert source.get_property(key).get_value(field) == (expected == "true")
			continue
		assert source.get_property(key) == value


@then(parsers.parse("le port de monitoring donne {count:d} canaux"))
def port_channels(port: object, count: int) -> None:
	"""Sans contrainte, pipewiresrc et pulsesrc se contentent d'un canal : le port en demande deux."""
	output = port.get_static_pad("src")  # type: ignore[attr-defined]
	assert output is not None
	caps = output.query_caps(None)
	assert not caps.is_empty()
	for index in range(caps.get_size()):
		found, channels = caps.get_structure(index).get_int("channels")
		assert (found, channels) == (True, count), caps.to_string()


@then("il n'y a pas de fenêtre de pré-écoute")
def without_preview(interface: Context) -> None:
	assert window(interface).preview is None


@when("l'onglet Antenne rouvre le port de monitoring de la même antenne", target_fixture="previous_screenshot")
def reopen(interface: Context) -> object:
	screen = home(interface)
	previous = screen.monitor._pipeline
	assert previous is not None
	screen.change_on_air(screen.monitor.audio)
	return previous


@then("la capture précédente de l'antenne est arrêtée")
def previous_stopped(previous_screenshot: object) -> None:
	_return, state, _waiting = previous_screenshot.get_state(0)  # type: ignore[attr-defined]
	assert state.value_nick == "null"


# ─── Échelle ───────────────────────────────────────────────


@given(
	parsers.re(r"un VU-mètre (?P<direction>vertical|couché) de (?P<width>\d+) × (?P<height>\d+) pixels"),
	target_fixture="only_vu_meter",
)
def size_vu_meter(qtbot: QtBot, direction: str, width: str, height: str) -> VuMeter:
	vu_meter = VuMeter(vertical=direction == "vertical")
	qtbot.addWidget(vu_meter)
	vu_meter.setFixedSize(int(width), int(height))
	vu_meter.display([-20.0, -20.0])
	return vu_meter


@then(parsers.parse("son échelle porte les nombres « {counts} »"))
def scale_counts(only_vu_meter: VuMeter, counts: str) -> None:
	assert [text for text, _frame in only_vu_meter.captions()] == counts.split(", ")


@then("son échelle commence à 0 et finit à -60")
def bounds(only_vu_meter: VuMeter) -> None:
	texts = [text for text, _frame in only_vu_meter.captions()]
	assert (texts[0], texts[-1]) == ("0", "-60"), texts


@then("ses nombres ne se chevauchent pas, hors 0 et -60, toujours écrits même sur un tout petit VU-mètre")
def without_only_overlap(only_vu_meter: VuMeter) -> None:
	captions = only_vu_meter.captions()
	for index, (text, frame) in enumerate(captions):
		for other, other_frame in captions[index + 1 :]:
			if {text, other} != {"0", "-60"}:
				assert not frame.intersects(other_frame), captions


@then(parsers.re(r"chaque nombre écarté chevauche un nombre gardé plus important, dans l'ordre (?P<order>.+)"))
def discarded_list(only_vu_meter: VuMeter, order: str) -> None:
	"""Un nombre n'est écarté que parce qu'il chevauche un nombre gardé, venu avant lui dans l'ordre d'importance."""
	importance = [int(count) for count in order.split(", ")]
	candidates = only_vu_meter.candidates()
	assert [tick for tick, _frame in candidates] == importance
	kept_list = {int(text) for text, _frame in only_vu_meter.captions()}
	for rank, (tick, frame) in enumerate(candidates):
		if tick in kept_list:
			continue
		before = [
			other
			for other, other_frame in candidates[:rank]
			if (other in kept_list) and (frame.intersects(other_frame))
		]
		assert before != [], f"{tick} écarté sans chevaucher un nombre gardé plus important"


def without_overlap(vu_meter: VuMeter) -> list[tuple[str, QRectF]]:
	captions = vu_meter.captions()
	for index, (_text, frame) in enumerate(captions):
		assert all(not frame.intersects(other) for _t, other in captions[index + 1 :]), captions
		assert vu_meter.rect().toRectF().contains(frame), (frame, vu_meter.rect())
	return captions


@then("de gauche à droite, le VU-mètre de l'antenne montre le canal « G », l'échelle, le canal « D »")
def separated_channels(interface: Context) -> None:
	vu_meter = home(interface).vu_meter
	arrangement = vu_meter.arrangement()
	left, right = arrangement.channels
	assert left.right() < arrangement.scale.left() < arrangement.scale.right() < right.left()
	assert [name for name, _frame in arrangement.names] == ["G", "D"]
	assert [frame.center().x() for _name, frame in arrangement.names] == [left.center().x(), right.center().x()]
	assert all(frame.top() >= left.bottom() for _name, frame in arrangement.names)


@then("l'échelle du VU-mètre de l'antenne va de 0 dB en haut à -60 dB en bas, sans nombres qui se chevauchent")
def vertical_scale(interface: Context) -> None:
	vu_meter = home(interface).vu_meter
	captions = without_overlap(vu_meter)
	channel = vu_meter.arrangement().channels[0]
	assert (captions[0][0], captions[-1][0]) == ("0", "-60")
	assert abs(captions[0][1].center().y() - channel.top()) <= 1
	assert abs(captions[-1][1].center().y() - channel.bottom()) <= 1
	tops = [frame.center().y() for _text, frame in captions]
	assert tops == sorted(tops)


@then(
	"l'échelle du VU-mètre de la pré-écoute va de -60 dB à gauche à 0 dB à droite, sous ses canaux, "
	"sans nombres qui se chevauchent"
)
def lying_scale(interface: Context) -> None:
	preview = window(interface).preview
	assert preview is not None
	vu_meter = preview.vu_meter
	captions = without_overlap(vu_meter)
	arrangement = vu_meter.arrangement()
	channel = arrangement.channels[0]
	assert (captions[0][0], captions[-1][0]) == ("0", "-60")
	assert abs(captions[0][1].center().x() - channel.right()) <= 1
	assert abs(captions[-1][1].center().x() - channel.left()) <= 1
	assert arrangement.scale.top() >= max(frame.bottom() for frame in arrangement.channels)
	assert all(frame.top() >= arrangement.scale.top() for _text, frame in captions)


# ─── PipeWire simulé ───────────────────────────────────────

FAKE_LINK_PW = """#!/bin/bash
# Le pw-link des scénarios : il note chaque appel, et liste les ports du scénario.
dossier="${0%/*}"
echo "$*" >> "${dossier}/journal"
case "$1" in
	-o) cat "${dossier}/sorties" ;;
	-i) cat "${dossier}/entrees" ;;
	-d) ;;
	*)
		if [[ -f "${dossier}/refus" ]]; then
			cat "${dossier}/refus" >&2
			exit 1
		fi
		;;
esac
"""


def simulate_monitoring_port(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Les ports de PipeWire n'existent pas en test : le VU-mètre et la pré-écoute écoutent le signal de test."""

	def sample_signal(_audio: Audio) -> object:
		return monitor_source(Audio("dummy", None, "casque"))  # type: ignore[arg-type]

	monkeypatch.setattr(monitor, "monitor_source", sample_signal)
	monkeypatch.setattr(preview, "monitor_source", sample_signal)


@given(
	parsers.re(r"PipeWire simulé, avec les ports de sortie « (?P<outputs>[^»]+) » et d'entrée « (?P<entries>[^»]+) »"),
	target_fixture="pipewire",
)
def simulated_pipewire(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, outputs: str, entries: str) -> Path:
	folder = tmp_path / "pipewire"
	folder.mkdir()
	command = folder / "pw-link"
	command.write_text(FAKE_LINK_PW)
	command.chmod(0o755)
	(folder / "sorties").write_text("\n".join(outputs.split(", ")) + "\n")
	(folder / "entrees").write_text("\n".join(entries.split(", ")) + "\n")
	monkeypatch.setattr(binding, "COMMAND", str(command))
	simulate_monitoring_port(monkeypatch)
	return folder


@given("PipeWire simulé, sans pw-link", target_fixture="pipewire")
def pipewire_without_link_pw(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
	monkeypatch.setattr(binding, "COMMAND", str(tmp_path / "pw-link-absent"))
	simulate_monitoring_port(monkeypatch)
	return tmp_path


def pipewire_links(pipewire: Path) -> set[tuple[str, str]]:
	"""Les liens en place, d'après les appels notés : « sortie entrée » relie, « -d sortie entrée » délie."""
	log = pipewire / "journal"
	links: set[tuple[str, str]] = set()
	if not log.exists():
		return links
	for line in log.read_text().splitlines():
		arguments = line.split(" ")
		if arguments[0] == "-d":
			links.discard((arguments[1], arguments[2]))
		else:
			if (arguments[0] not in ("-o", "-i")) and (not (pipewire / "refus").exists()):
				links.add((arguments[0], arguments[1]))
	return links


@then(parsers.re(r"PipeWire relie (?P<pairs>« .+)"))
def links(pipewire: Path, pairs: str) -> None:
	expected_list = set(re.findall(r"« ([^»]+) » à « ([^»]+) »", pairs))
	assert expected_list
	assert pipewire_links(pipewire) == expected_list


@then("PipeWire ne relie plus rien")
def linked_nothing(pipewire: Path) -> None:
	assert pipewire_links(pipewire) == set()


@given(parsers.parse("PipeWire simulé refuse de relier : « {message} »"))
def refused_pipewire(pipewire: Path, message: str) -> None:
	(pipewire / "refus").write_text(f"{message}\n")


@when(
	parsers.parse("je construis l'écoute de l'antenne sur la sortie « {output} », pré-écoute « {device} »"),
	target_fixture="listening",
)
def build_listening(output: str, device: str) -> object:
	on_air = Audio(output, "antenne-ua22", device)  # type: ignore[arg-type]
	player = preview.Player(output, device)  # type: ignore[arg-type]
	return player._build(preview.Source("Antenne", "Antenne", True, None, on_air))


@then(parsers.parse("l'écoute de l'antenne finit par l'élément « {factory} »"))
def finishes_by(listening: object, factory: str) -> None:
	sink = [item for item in listening.children if not item.srcpads]  # type: ignore[attr-defined]
	assert [item.get_factory().get_name() for item in sink] == [factory]


# ─── Entrée d'écoute de l'antenne (https://github.com/dascritch/machincast/issues/256) ───


@then(
	parsers.parse(
		"l'entrée d'écoute de l'antenne du menu « {menu} » est « {text} », raccourci « {shortcut} », infobulle"
		" « {tooltip} »"
	)
)
def listening_entry(interface: Context, menu: str, text: str, shortcut: str, tooltip: str) -> None:
	"""L'entrée en tête du menu (https://github.com/dascritch/machincast/issues/245)."""
	first = actions(interface, menu)[0]
	assert (first.text(), first.shortcut().toString(), first.toolTip()) == (text, shortcut, tooltip)


@then(parsers.parse("le nom public de la fiche se saisit par « {keys} »"))
def public_name_to_keyboard(interface: Context, keys: str) -> None:
	card = window(interface).ui.tabs.currentWidget()
	captions = [caption for caption in card.findChildren(QLabel) if caption.buddy() is card.ui.public_name]
	assert len(captions) == 1, captions
	assert QKeySequence.mnemonic(captions[0].text()).toString() == keys
