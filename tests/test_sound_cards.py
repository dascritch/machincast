"""Scénarios du bloc des cartes son (https://github.com/dascritch/machincast/issues/339).

Le bloc s'ouvre hors de l'écran du poste, sur les périphériques du scénario (« les périphériques audio du poste »,
tests/interface_steps.py). Le son de test joue sur une sortie factice, raccourci : aucun son ne part du poste.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QComboBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import audio
from machincast.audio import UnavailableAudioOutput
from machincast.configuration import AudioOutput
from machincast.interface import sound_cards
from machincast.interface.sound_cards import SoundCards
from machincast.service import ABSENT, ServiceState

scenarios("sound_cards.feature")

SERVICES = {
	"sans service de diffusion": ABSENT,
	"service de diffusion à l'arrêt": ServiceState(installed=True, active="inactive"),
	"service de diffusion en marche": ServiceState(installed=True, active="active"),
}
WAITING = 5000
"""Millisecondes laissées au son de test pour finir."""


@dataclass
class Block:
	cards: SoundCards | None = None
	requests: list[tuple[str, str | None]] = field(default_factory=list)


@pytest.fixture
def block() -> Block:
	return Block()


@pytest.fixture
def parent(qtbot: QtBot) -> Iterator[QWidget]:
	widget = QWidget()
	qtbot.addWidget(widget)
	yield widget


def opened(block: Block) -> SoundCards:
	assert block.cards is not None
	return block.cards


def _list(text: str) -> list[str]:
	return re.findall(r"« ([^»]+) »", text)


# ─── Ouverture ─────────────────────────────────────────────


@when(
	parsers.re(
		r"le bloc des cartes son s'ouvre sur la sortie « (?P<output>[^»]+) »,"
		r" l'antenne (?:« (?P<on_air>[^»]+) »|non renseignée) et la pré-écoute « (?P<preview>[^»]+) »,"
		r" (?P<service>.+)"
	)
)
def open_(
	block: Block, parent: QWidget, qtbot: QtBot, output: str, on_air: str | None, preview: str, service: str
) -> None:
	block.cards = SoundCards(output, on_air, preview, SERVICES[service], parent)  # type: ignore[arg-type]
	parent.show()
	qtbot.waitExposed(parent)


# ─── Choix ─────────────────────────────────────────────────


def _choice(block: Block, name: str) -> QComboBox:
	ui = opened(block).ui
	return {"l'antenne": ui.on_air, "la pré-écoute": ui.preview}[name]


@then(parsers.re(r"son type de sortie est « (?P<type>[^»]+) », parmi (?P<types>«.+)"))
def output_type(block: Block, type: str, types: str) -> None:
	choice = opened(block).ui.output
	assert choice.currentText() == type
	assert [choice.itemText(index) for index in range(choice.count())] == _list(types)


@then(parsers.re(r"son choix de (?P<name>l'antenne|la pré-écoute) propose :"))
def offers(block: Block, name: str, datatable: list[list[str]]) -> None:
	choice = _choice(block, name)
	model = choice.model()
	assert isinstance(model, QStandardItemModel)
	shown_list = [
		[choice.itemText(index), "active" if model.item(index).isEnabled() else "inactive"]
		for index in range(choice.count())
	]
	assert shown_list == [[card.strip(), state.strip()] for card, state in datatable[1:]]


@when(parsers.re(r"j'y choisis pour (?P<name>l'antenne|la pré-écoute) « (?P<text>[^»]+) »"))
def choose(block: Block, name: str, text: str) -> None:
	choice = _choice(block, name)
	index = choice.findText(text)
	assert index >= 0, text
	choice.setCurrentIndex(index)


@when(parsers.parse("j'y choisis le type de sortie « {text} »"))
def choose_type(block: Block, text: str) -> None:
	choice = opened(block).ui.output
	index = choice.findText(text)
	assert index >= 0, text
	choice.setCurrentIndex(index)


@then(
	parsers.re(
		r"il donne la sortie « (?P<output>[^»]+) », l'antenne (?:« (?P<on_air>[^»]+) »|non renseignée)"
		r" et la pré-écoute « (?P<preview>[^»]+) »"
	)
)
def gives(block: Block, output: str, on_air: str | None, preview: str) -> None:
	cards = opened(block)
	assert (cards.chosen_output(), cards.chosen_on_air(), cards.chosen_preview()) == (
		output,
		on_air,
		preview,
	)


@then(parsers.parse("dans son choix de l'antenne, « {text} » a pour infobulle « {tooltip} »"))
def line_tooltip(block: Block, text: str, tooltip: str) -> None:
	choice = opened(block).ui.on_air
	model = choice.model()
	assert isinstance(model, QStandardItemModel)
	assert model.item(choice.findText(text)).toolTip() == tooltip


# ─── Service de diffusion ──────────────────────────────────


@then(
	parsers.re(
		r"le choix de l'antenne, son bouton « Tester » et le type de sortie sont"
		r" (?P<state>actifs|inactifs, avec l'infobulle « (?P<tooltip>[^»]+) »)"
	)
)
def locked_on_air(block: Block, state: str, tooltip: str | None) -> None:
	ui = opened(block).ui
	items = (ui.on_air, ui.test_on_air, ui.output)
	assert [item.isEnabled() for item in items] == [state == "actifs"] * 3
	if tooltip is not None:
		assert [item.toolTip() for item in items] == [tooltip] * 3


@then("le choix de la pré-écoute et son bouton « Tester » sont actifs")
def free_preview(block: Block) -> None:
	ui = opened(block).ui
	assert (ui.preview.isEnabled(), ui.test_preview.isEnabled()) == (True, True)


# ─── Son de test ───────────────────────────────────────────


@when(
	parsers.parse("je construis le son de test de la sortie « {output} », carte « {card} »"),
	target_fixture="pipeline",
)
def build(output: str, card: str) -> Iterator[audio.Gst.Pipeline]:
	pipeline = sound_cards.sample_sound(output, card)  # type: ignore[arg-type]
	yield pipeline
	pipeline.set_state(audio.Gst.State.NULL)


@then("c'est une sinusoïde à 1000 Hz, à -3 dB, de 2 secondes")
def sine(pipeline: audio.Gst.Pipeline) -> None:
	source = pipeline.get_by_name("source")
	assert source is not None
	assert source.get_property("wave").value_nick == "sine"
	assert source.get_property("freq") == 1000
	assert source.get_property("volume") == pytest.approx(0.708, abs=0.001)
	samples = source.get_property("num-buffers") * source.get_property("samplesperbuffer")
	assert samples / sound_cards.RATE == pytest.approx(2.0)


@then(
	parsers.parse(
		"il joue sur l'élément « {factory} », carte « {card} », présenté comme « {program} », flux « {stream} »"
	)
)
def sink(pipeline: audio.Gst.Pipeline, factory: str, card: str, program: str, stream: str) -> None:
	item = pipeline.get_by_name("puits")
	assert item is not None
	builder = item.get_factory()
	assert (builder is not None) and (builder.get_name() == factory)
	assert item.get_property("target-object") == card
	properties = item.get_property("stream-properties")
	assert (properties.get_string("application.name"), properties.get_string("media.name")) == (program, stream)


@given("des sons de test de 0,2 seconde, sur une sortie factice")
def dummy_sounds(block: Block, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(sound_cards, "TEST_SOUND_DURATION", 0.2)

	def create(output: AudioOutput, device: str | None, presentation: audio.Presentation) -> audio.Gst.Element:
		block.requests.append((output, device))
		sink = audio.create_output("dummy", None, presentation=presentation)
		# Au rythme du temps réel, pour que le scénario voie le son en cours.
		sink.set_property("sync", True)
		return sink

	monkeypatch.setattr(sound_cards, "output_factory", create)


@given("des sons de test sur une sortie qui ne peut pas être créée")
def impossible_sounds(monkeypatch: pytest.MonkeyPatch) -> None:
	def create(_output: AudioOutput, _device: str | None, presentation: audio.Presentation) -> audio.Gst.Element:
		raise UnavailableAudioOutput("sortie introuvable")

	monkeypatch.setattr(sound_cards, "output_factory", create)


@when(parsers.re(r"je clique sur « Tester » de (?P<name>l'antenne|la pré-écoute)"))
def click_on_test(block: Block, name: str) -> None:
	ui = opened(block).ui
	button = {"l'antenne": ui.test_on_air, "la pré-écoute": ui.test_preview}[name]
	assert button.isEnabled()
	button.click()


@then(parsers.parse("le bloc dit « {text} »"))
def says(block: Block, text: str) -> None:
	assert opened(block).text() == text


@then(parsers.parse("le bloc dit bientôt « {text} »"))
def says_soon(block: Block, qtbot: QtBot, text: str) -> None:
	qtbot.waitUntil(lambda: opened(block).text() == text, timeout=WAITING)


@then(parsers.re(r"ses boutons « Tester » sont (?P<state>actifs|inactifs)"))
def buttons(block: Block, state: str) -> None:
	ui = opened(block).ui
	assert (ui.test_on_air.isEnabled(), ui.test_preview.isEnabled()) == (state == "actifs",) * 2


@then(parsers.parse("le son de test a été demandé sur la sortie « {output} », carte « {card} »"))
def asks(block: Block, output: str, card: str) -> None:
	assert block.requests[-1] == (output, card)


@then(parsers.parse("le bouton « Tester » de l'antenne est inactif, avec l'infobulle « {tooltip} »"))
def button_test_inactive(block: Block, tooltip: str) -> None:
	button = opened(block).ui.test_on_air
	assert (button.isEnabled(), button.toolTip()) == (False, tooltip)
