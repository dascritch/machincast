"""Scénarios des préférences de l'interface (https://github.com/dascritch/machincast/issues/145).

Les étapes de la fenêtre, de sa barre de menus et des fiches sont dans tests/interface_steps.py, où la fenêtre des
préférences est remplacée par les réglages du scénario. La vraie fenêtre des préférences s'ouvre ici, hors de l'écran
du poste.
"""

import dataclasses
import re
import stat
import tomllib
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
import tomlkit
from PySide6.QtGui import QColor, QIcon, QImage, QStandardItemModel
from PySide6.QtWidgets import QApplication, QComboBox, QDialogButtonBox, QDoubleSpinBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import shortcut
from machincast.configuration import Crossfades, DeadAirSettings, load
from machincast.interface import __main__ as module_interface
from machincast.interface import application as module_application
from machincast.interface import dialogs, preferences
from machincast.interface.bank_card import BankCard
from machincast.interface.preferences import PreferencesWindow, Settings
from machincast.interface.sound_card import SoundCard
from machincast.interface.suggestions import Response
from machincast.interface.window import MainWindow
from machincast.shortcut import ICON
from tests.database_fixtures import configuration_test
from tests.interface_steps import NAME, Connection, Context, configuration_file, open_window, window
from tests.modals import when_modal

scenarios("preferences.feature")

SETTINGS = (
	r"granularité « (?P<granularity>second|tenth) », maximum (?P<maximum>[\d,]+) s,"
	r" début par défaut (?:(?P<start>[\d,]+) s|aucune), fin par défaut (?:(?P<end>[\d,]+) s|aucune)"
)
"""Les réglages des crossfades, tels que les écrit un scénario."""
TEST_PREVIEW = "preecoute-factice"
"""Le périphérique de pré-écoute de la configuration des tests."""


def _seconds(text: str | None) -> timedelta | None:
	if text is None:
		return None
	return timedelta(seconds=float(text.replace(",", ".")))


def settings(granularity: str, maximum: str, start: str | None, end: str | None) -> Crossfades:
	duration = _seconds(maximum)
	assert duration is not None
	assert granularity in ("second", "tenth")
	return Crossfades(_seconds(start), _seconds(end), duration, "second" if granularity == "second" else "tenth")


def read_settings(text: str) -> Crossfades:
	found = re.fullmatch(SETTINGS, text)
	assert found is not None, text
	return settings(**found.groupdict())


# ─── Fenêtre de l'interface ────────────────────────────────


@given("le fichier de configuration de l'interface, avec :")
def configuration_with(interface: Context, docstring: str) -> None:
	path = configuration_file(interface)
	path.write_text(f"{path.read_text(encoding='utf-8')}\n{docstring}\n", encoding="utf-8")


@given("le fichier de configuration de l'interface, que le poste refuse d'écrire")
def refused_configuration(interface: Context, monkeypatch: pytest.MonkeyPatch) -> None:
	"""Les tests tournent parfois sous root, que les droits d'un fichier n'arrêtent pas : l'écriture est refusée."""
	configuration_file(interface)

	def refuse(path: Path, _settings: Settings) -> None:
		raise PermissionError(13, "Permission non accordée", str(path))

	monkeypatch.setattr(preferences, "write", refuse)


@given(parsers.re(rf"les préférences seront réglées : {SETTINGS}"))
def adjusted_preferences(
	interface: Context, granularity: str, maximum: str, start: str | None, end: str | None
) -> None:
	interface.adjusted_preferences = settings(granularity, maximum, start, end)


@then(parsers.re(rf"les préférences ont montré : {SETTINGS}"))
def shown_preferences(interface: Context, granularity: str, maximum: str, start: str | None, end: str | None) -> None:
	assert interface.shown_preferences == [settings(granularity, maximum, start, end)]


@then(parsers.re(rf"le fichier de configuration donne les crossfades : {SETTINGS}"))
def file_crossfades(interface: Context, granularity: str, maximum: str, start: str | None, end: str | None) -> None:
	assert load(configuration_file(interface)).crossfades == settings(granularity, maximum, start, end)


@then(parsers.parse("le fichier de configuration contient encore « {line} »"))
def contains_still(interface: Context, line: str) -> None:
	assert line in configuration_file(interface).read_text(encoding="utf-8").splitlines()


@then(
	parsers.re(r"le fichier de configuration contient encore les autres sections(?P<outside_audio>, hors \[audio\])?")
)
def other_sections(interface: Context, outside_audio: str | None) -> None:
	before = tomllib.loads(interface.initial_configuration.decode("utf-8"))
	after = tomllib.loads(configuration_file(interface).read_text(encoding="utf-8"))
	# Les préférences tiennent toujours [crossfades], [silences] (https://github.com/dascritch/machincast/issues/146) et
	# [interface] (https://github.com/dascritch/machincast/issues/191), et [dead_air]
	# (https://github.com/dascritch/machincast/issues/122).
	removed_list = ["crossfades", "silences", "dead_air", "interface"]
	if outside_audio is not None:
		removed_list.append("audio")
	for section in removed_list:
		before.pop(section, None)
		after.pop(section, None)
	assert after == before


@then(parsers.parse("le fichier de configuration n'a plus de clé « {key} »"))
def more_key(interface: Context, key: str) -> None:
	document = tomllib.loads(configuration_file(interface).read_text(encoding="utf-8"))
	assert key not in document["crossfades"], document["crossfades"]


@then("le fichier de configuration n'a pas changé")
def unchanged(interface: Context) -> None:
	assert configuration_file(interface).read_bytes() == interface.initial_configuration


@then(parsers.parse("la barre d'état annonce une erreur qui commence par « {start} »"))
def announced_error(interface: Context, start: str) -> None:
	message = window(interface).statusBar().currentMessage()
	assert message.startswith(interface.path_in(start)), message


@then(
	parsers.re(
		r"les crossfades de la fiche se règlent (?P<granularity>au dixième de seconde|à la seconde),"
		r" jusqu'à (?P<maximum>\d+) s"
	)
)
def card_crossfades(interface: Context, granularity: str, maximum: str) -> None:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, (SoundCard, BankCard)), opened
	fields = (opened.ui.start_crossfade, opened.ui.end_crossfade)
	decimals, step = {"au dixième de seconde": (1, 0.1), "à la seconde": (0, 1.0)}[granularity]
	fetched_settings = [(field.decimals(), field.singleStep(), field.maximum()) for field in fields]
	assert fetched_settings == [(decimals, step, float(maximum))] * 2


# ─── Fenêtre des préférences ───────────────────────────────


@pytest.fixture
def parent(qtbot: QtBot) -> Iterator[QWidget]:
	widget = QWidget()
	qtbot.addWidget(widget)
	yield widget


class Opened:
	window: PreferencesWindow | None = None
	provided_list: Settings | None = None


@pytest.fixture
def opened() -> Opened:
	return Opened()


def the_window(opened: Opened) -> PreferencesWindow:
	assert opened.window is not None
	return opened.window


@when(parsers.re(rf"la fenêtre des préférences s'ouvre sur : {SETTINGS}"))
def open_preferences(
	opened: Opened, parent: QWidget, granularity: str, maximum: str, start: str | None, end: str | None
) -> None:
	all_ = Settings(settings(granularity, maximum, start, end), None, TEST_PREVIEW)
	opened.window = PreferencesWindow(all_, "dummy", parent)


@then(parsers.re(r"elle s'intitule « (?P<title>[^»]+) », avec les pages (?P<pages>«.+)"))
def title_and_pages(opened: Opened, title: str, pages: str) -> None:
	"""Les pages dans l'ordre, la première ouverte : les crossfades ont la leur
	(https://github.com/dascritch/machincast/issues/234)."""
	ui = the_window(opened).ui
	fetched_list = [ui.pages.tabText(rank) for rank in range(ui.pages.count())]
	assert (the_window(opened).windowTitle(), fetched_list) == (title, NAME.findall(pages))
	assert ui.pages.currentIndex() == 0


def _shown(box_and_field: tuple[object, QDoubleSpinBox] | QDoubleSpinBox) -> str | None:
	if isinstance(box_and_field, QDoubleSpinBox):
		return box_and_field.text()
	box, field = box_and_field
	assert hasattr(box, "isChecked")
	if not box.isChecked():  # type: ignore[attr-defined]
		assert not field.isEnabled()
		return None
	assert field.isEnabled()
	return field.text()


@then(
	parsers.re(
		r"elle montre : granularité « (?P<granularity>[^»]+) », maximum « (?P<maximum>[^»]+) »,"
		r" début par défaut (?:« (?P<start>[^»]+) »|aucune), fin par défaut (?:« (?P<end>[^»]+) »|aucune)"
	)
)
def shows(opened: Opened, granularity: str, maximum: str, start: str | None, end: str | None) -> None:
	ui = the_window(opened).ui
	shown_list = (
		ui.granularity.currentText(),
		_shown(ui.maximum),
		_shown((ui.has_start, ui.start)),
		_shown((ui.has_end, ui.end)),
	)
	assert shown_list == (granularity, maximum, start, end)


@when(parsers.parse("j'y choisis la granularité « {text} »"))
def choose_granularity(opened: Opened, text: str) -> None:
	list_ = the_window(opened).ui.granularity
	rank = list_.findText(text)
	assert rank >= 0, text
	list_.setCurrentIndex(rank)


@when(parsers.parse("j'y saisis le maximum {seconds:d}"))
def enter_maximum(opened: Opened, seconds: int) -> None:
	the_window(opened).ui.maximum.setValue(seconds)


@when(parsers.re(r"j'y retire la durée de (?P<side>début|fin) par défaut"))
def remove_default(opened: Opened, side: str) -> None:
	ui = the_window(opened).ui
	box = {"début": ui.has_start, "fin": ui.has_end}[side]
	assert box.isChecked(), side
	box.setChecked(False)


@when(parsers.re(r"j'y saisis la durée de (?P<side>début|fin) par défaut (?P<seconds>[\d,]+)"))
def enter_default(opened: Opened, side: str, seconds: str) -> None:
	ui = the_window(opened).ui
	box, field = {"début": (ui.has_start, ui.start), "fin": (ui.has_end, ui.end)}[side]
	box.setChecked(True)
	field.setValue(float(seconds.replace(",", ".")))


@when(parsers.parse("j'y clique sur « {button} »"))
def click(opened: Opened, button: str) -> None:
	preferences_window = the_window(opened)
	role = {"OK": QDialogButtonBox.StandardButton.Ok, "Annuler": QDialogButtonBox.StandardButton.Cancel}[button]
	preferences_window.ui.buttons.button(role).click()
	opened.provided_list = None
	if preferences_window.result() == PreferencesWindow.DialogCode.Accepted:
		opened.provided_list = preferences_window.settings()


@then(parsers.re(rf"elle a donné : {SETTINGS}"))
def provided_list(opened: Opened, granularity: str, maximum: str, start: str | None, end: str | None) -> None:
	assert opened.provided_list is not None
	assert opened.provided_list.crossfades == settings(granularity, maximum, start, end)


@when(parsers.re(rf"je réponds « (?P<button>OK|Annuler) » à la fenêtre des préférences ouverte sur : {SETTINGS}"))
def answer(
	opened: Opened,
	parent: QWidget,
	button: str,
	granularity: str,
	maximum: str,
	start: str | None,
	end: str | None,
) -> None:
	def make(modal: QWidget) -> None:
		assert isinstance(modal, PreferencesWindow), modal
		role = {"OK": QDialogButtonBox.StandardButton.Ok, "Annuler": QDialogButtonBox.StandardButton.Cancel}[button]
		modal.ui.buttons.button(role).click()

	when_modal(make)
	all_ = Settings(settings(granularity, maximum, start, end), None, TEST_PREVIEW)
	opened.provided_list = dialogs.set_preferences(parent, all_, "dummy")


@then(parsers.re(rf"les réglages donnés sont (?:aucun|{SETTINGS})"))
def provided_settings(
	opened: Opened,
	granularity: str | None,
	maximum: str | None,
	start: str | None,
	end: str | None,
) -> None:
	expected_list = None
	if (granularity is not None) and (maximum is not None):
		expected_list = Settings(settings(granularity, maximum, start, end), None, TEST_PREVIEW, output="dummy")
	assert opened.provided_list == expected_list


@then(parsers.parse("le fichier de configuration contient la ligne « {line} »"))
def contains_line(interface: Context, line: str) -> None:
	assert line in configuration_file(interface).read_text(encoding="utf-8").splitlines()


@then("le fichier de configuration n'a plus de section [blancs]")
def more_dead_airs(interface: Context) -> None:
	"""https://github.com/dascritch/machincast/issues/291"""
	assert "blancs" not in tomllib.loads(configuration_file(interface).read_text(encoding="utf-8"))


@when("la fenêtre de l'interface s'ouvre, sans fichier de configuration")
def open_without_configuration(interface: Context, empty_database: Connection, qtbot: QtBot) -> None:
	open_window(interface, qtbot, with_configuration=False)


@then(parsers.re(r"son maximum se règle par pas de (?P<step>[\d,]+) s, à partir de (?P<minimum>[\d,]+) s"))
def not_maximum(opened: Opened, step: str, minimum: str) -> None:
	field = the_window(opened).ui.maximum
	expected_list = tuple(float(value.replace(",", ".")) for value in (step, minimum))
	assert (field.singleStep(), field.minimum()) == expected_list


# ─── Page « Audio » ────────────────────────────────────────


@when(
	parsers.re(
		r"la fenêtre des préférences s'ouvre sur l'antenne (?:« (?P<on_air>[^»]+) »|non renseignée)"
		r" et la pré-écoute « (?P<preview>[^»]+) »"
	)
)
def open_on_audio(opened: Opened, parent: QWidget, on_air: str | None, preview: str) -> None:
	opened.window = PreferencesWindow(Settings(Crossfades(), on_air, preview), "pipewire", parent)


def audio_choice(opened: Opened, name: str) -> QComboBox:
	"""Les choix du bloc des cartes son (https://github.com/dascritch/machincast/issues/339)."""
	ui = the_window(opened).cards.ui
	return {"antenne": ui.on_air, "pré-écoute": ui.preview}[name]


@then(parsers.re(r"le choix (?:de l'|de la )(?P<name>antenne|pré-écoute) propose :"))
def offered_choice(opened: Opened, name: str, datatable: list[list[str]]) -> None:
	choice = audio_choice(opened, name)
	model = choice.model()
	assert isinstance(model, QStandardItemModel)
	fetched_list = []
	for index in range(choice.count()):
		line_state = "inactive"
		if model.item(index).isEnabled():
			line_state = "active"
		fetched_list.append([choice.itemText(index), line_state])
	assert fetched_list == [[cell.strip() for cell in row] for row in datatable[1:]]


@when(parsers.re(r"j'y choisis (?:pour l'|pour la )(?P<name>antenne|pré-écoute) « (?P<text>[^»]+) »"))
def choose_device(opened: Opened, name: str, text: str) -> None:
	choice = audio_choice(opened, name)
	index = choice.findText(text)
	assert index >= 0, text
	choice.setCurrentIndex(index)


@then(parsers.re(r"son bouton « OK » est (?P<state>actif|inactif)"))
def ok_button(opened: Opened, state: str) -> None:
	button = the_window(opened).ui.buttons.button(QDialogButtonBox.StandardButton.Ok)
	assert button.isEnabled() == (state == "actif")


@then(
	parsers.re(
		r"elle a donné l'antenne (?:« (?P<on_air>[^»]+) »|non renseignée) et la pré-écoute « (?P<preview>[^»]+) »"
	)
)
def audio_gives(opened: Opened, on_air: str | None, preview: str) -> None:
	assert opened.provided_list is not None
	assert (opened.provided_list.on_air, opened.provided_list.preview) == (on_air, preview)


@then(
	parsers.re(
		r"les préférences ont montré l'antenne (?:« (?P<on_air>[^»]+) »|non renseignée)"
		r" et la pré-écoute « (?P<preview>[^»]+) »"
	)
)
def shown_audio(interface: Context, on_air: str | None, preview: str) -> None:
	assert interface.shown_audio[-1] == (on_air, preview)


@then(
	parsers.re(
		r"le fichier de configuration donne (?:la sortie « (?P<output>[^»]+) », )?l'antenne « (?P<on_air>[^»]+) »"
		r" et la pré-écoute « (?P<preview>[^»]+) »"
	)
)
def file_audio(interface: Context, output: str | None, on_air: str, preview: str) -> None:
	audio = load(configuration_file(interface)).audio
	assert (audio.device, audio.preview) == (on_air, preview)
	if output is not None:
		assert audio.output == output


@then(parsers.re(r"la barre d'état (?P<reports>signale|ne signale pas) « Périphérique de l'antenne à renseigner »"))
def reported_on_air(interface: Context, reports: str) -> None:
	caption = window(interface).to_fill_in_on_air
	assert caption.isVisibleTo(window(interface)) == (reports == "signale")
	assert caption.text() == "Périphérique de l'antenne à renseigner"
	assert caption.toolTip().startswith("Machin player refuse de diffuser sans lui")


# ─── Machin interface ──────────────────────────────────────


@given(
	parsers.parse(
		"un fichier de configuration sur la base de test, la sortie « {output} », l'antenne « {on_air} »"
		" et la pré-écoute « {preview} »"
	),
	target_fixture="launched_configuration",
)
def launched_configuration(empty_database: Connection, tmp_path: Path, output: str, on_air: str, preview: str) -> Path:
	"""La configuration des tests, sur la base de test comme base de production : sa base de test, qui doit en
	différer, en devient une autre, que l'interface n'ouvre pas."""
	source = configuration_test()
	text = (
		source.path.read_text(encoding="utf-8")
		.replace(f'test = "{source.database.test}"', f'test = "{source.database.test}_inutilisee"')
		.replace(f'production = "{source.database.production}"', f'production = "{source.database.test}"')
		.replace('output = "dummy"', f'output = "{output}"\ndevice = "{on_air}"')
		.replace(f'preview = "{source.audio.preview}"', f'preview = "{preview}"')
	)
	path = tmp_path / "machincast.toml"
	path.write_text(text, encoding="utf-8")
	return path


class Launching:
	window: MainWindow | None = None
	shown_list: tuple[Settings, str] | None = None


@pytest.fixture
def launching() -> Launching:
	return Launching()


@when("Machin interface est lancé avec ce fichier")
def launch_interface(
	launched_configuration: Path, launching: Launching, monkeypatch: pytest.MonkeyPatch, qtbot: QtBot
) -> None:
	"""Son point d'entrée, jusqu'à la boucle de Qt, qui rend la main aussitôt : la fenêtre reste à examiner."""

	class Application:
		def exec(self) -> int:
			return 0

	def display(window: MainWindow) -> None:
		qtbot.addWidget(window)
		launching.window = window

	monkeypatch.setattr(module_application, "application", lambda _name: Application())
	monkeypatch.setattr(MainWindow, "show", display)
	# La fenêtre des suggestions au lancement est refermée par « Plus tard »
	# (https://github.com/dascritch/machincast/issues/119).
	monkeypatch.setattr(dialogs, "suggest", lambda _parent, _gaps, _service=None: Response(create=False))
	assert module_interface.main(["--config", str(launched_configuration)]) == 0


@then(parsers.parse("sa fenêtre a la sortie « {output} », l'antenne « {on_air} » et la pré-écoute « {preview} »"))
def window_audio(launching: Launching, output: str, on_air: str, preview: str) -> None:
	assert launching.window is not None
	audio = launching.window.audio
	assert (audio.output, audio.device, audio.preview) == (output, on_air, preview)


@then(
	parsers.parse(
		"ses préférences montrent l'antenne « {on_air} » et la pré-écoute « {preview} », sur la sortie « {output} »"
	)
)
def window_preferences(
	launching: Launching, monkeypatch: pytest.MonkeyPatch, on_air: str, preview: str, output: str
) -> None:
	def set_(_parent: QWidget, shown_list: Settings, shown_output: str, _service: object = None) -> None:
		launching.shown_list = (shown_list, shown_output)

	monkeypatch.setattr(dialogs, "set_preferences", set_)
	assert launching.window is not None
	launching.window._preferences()
	assert launching.shown_list is not None
	shown_list, shown_output = launching.shown_list
	assert (shown_list.on_air, shown_list.preview, shown_output) == (on_air, preview, output)


# ─── Seuil de silence (https://github.com/dascritch/machincast/issues/146) ───


def _decibels(text: str) -> float:
	return float(text.replace(",", "."))


@given(parsers.re(r"les préférences seront réglées avec le seuil de silence (?P<threshold>-?[\d,]+) dB"))
def rule_threshold(interface: Context, threshold: str) -> None:
	interface.rule_threshold = _decibels(threshold)


@then(parsers.re(r"les préférences ont montré le seuil de silence (?P<threshold>-?[\d,]+) dB"))
def shown_threshold(interface: Context, threshold: str) -> None:
	assert interface.shown_thresholds == [_decibels(threshold)]


@when(parsers.re(r"la fenêtre des préférences s'ouvre sur le seuil de silence (?P<threshold>-?[\d,]+) dB"))
def open_on_threshold(opened: Opened, parent: QWidget, threshold: str) -> None:
	all_ = Settings(Crossfades(), None, TEST_PREVIEW, _decibels(threshold))
	opened.window = PreferencesWindow(all_, "dummy", parent)


@then(
	parsers.re(
		r"elle montre le seuil de silence « (?P<text>[^»]+) », réglable de (?P<minimum>-?[\d,]+)"
		r" à (?P<maximum>-?[\d,]+) dB"
	)
)
def displayed_threshold(opened: Opened, text: str, minimum: str, maximum: str) -> None:
	field = the_window(opened).ui.silence_threshold
	assert (field.text(), field.minimum(), field.maximum()) == (text, _decibels(minimum), _decibels(maximum))


@when(parsers.re(r"j'y saisis le seuil de silence (?P<threshold>-?[\d,]+)"))
def enter_threshold(opened: Opened, threshold: str) -> None:
	the_window(opened).ui.silence_threshold.setValue(_decibels(threshold))


@then(parsers.re(r"elle a donné le seuil de silence (?P<threshold>-?[\d,]+) dB"))
def threshold_gives(opened: Opened, threshold: str) -> None:
	assert opened.provided_list is not None
	assert opened.provided_list.silence_threshold == _decibels(threshold)


@then(parsers.parse("le champ « {name} » est à la page « {page} »"))
def field_page(opened: Opened, name: str, page: str) -> None:
	"""https://github.com/dascritch/machincast/issues/324"""
	window = the_window(opened)
	field = getattr(window.ui, name)
	pages = window.ui.pages
	(found,) = [index for index in range(pages.count()) if pages.widget(index).isAncestorOf(field)]
	assert pages.tabText(found) == page


# ─── Blanc dans un sonore (https://github.com/dascritch/machincast/issues/122) ───

DEAD_AIR = (
	r"un blanc de (?P<duration>[\d,]+) secondes sous (?P<threshold>-[\d,]+) dB, qui"
	r" (?P<remainder>est noté seulement|fait passer au secours)"
)
"""Un blanc dans un sonore, tel que l'écrit un scénario."""


def dead_air(duration: str, threshold: str, remainder: str) -> DeadAirSettings:
	return DeadAirSettings(
		timedelta(seconds=_decibels(duration)), _decibels(threshold), remainder == "fait passer au secours"
	)


@given(parsers.re(rf"les préférences seront réglées avec {DEAD_AIR}"))
def rule_dead_air(interface: Context, duration: str, threshold: str, remainder: str) -> None:
	interface.rule_dead_air = dead_air(duration, threshold, remainder)


@then(parsers.re(rf"les préférences (?P<moment>ont|suivantes ont) montré {DEAD_AIR}"))
def shown_dead_air(interface: Context, moment: str, duration: str, threshold: str, remainder: str) -> None:
	rank = 0 if moment == "ont" else -1
	assert interface.shown_dead_airs[rank] == dead_air(duration, threshold, remainder), interface.shown_dead_airs


@then(parsers.re(rf"le fichier de configuration donne {DEAD_AIR}"))
def file_dead_air(interface: Context, duration: str, threshold: str, remainder: str) -> None:
	assert load(configuration_file(interface)).dead_air == dead_air(duration, threshold, remainder)


@when(parsers.re(rf"la fenêtre des préférences s'ouvre sur {DEAD_AIR}"))
def open_on_dead_air(opened: Opened, parent: QWidget, duration: str, threshold: str, remainder: str) -> None:
	all_ = Settings(Crossfades(), None, TEST_PREVIEW, dead_air=dead_air(duration, threshold, remainder))
	opened.window = PreferencesWindow(all_, "dummy", parent)


@then(
	parsers.re(
		r"elle montre un blanc de « (?P<duration>[^»]+) », réglable de (?P<minimum>[\d,]+) à (?P<maximum>[\d,]+) s,"
		r" sous"
		r" « (?P<threshold>[^»]+) », réglable de (?P<more_bottom>-[\d,]+) à (?P<more_top>-[\d,]+) dB, et le passage au"
		r" secours (?P<box>coché|décoché)"
	)
)
def displayed_dead_air(
	opened: Opened,
	duration: str,
	minimum: str,
	maximum: str,
	threshold: str,
	more_bottom: str,
	more_top: str,
	box: str,
) -> None:
	ui = the_window(opened).ui
	assert (ui.dead_air_duration.text(), ui.dead_air_duration.minimum(), ui.dead_air_duration.maximum()) == (
		duration,
		_decibels(minimum),
		_decibels(maximum),
	)
	assert (ui.dead_air_threshold.text(), ui.dead_air_threshold.minimum(), ui.dead_air_threshold.maximum()) == (
		threshold,
		_decibels(more_bottom),
		_decibels(more_top),
	)
	assert ui.dead_air_fallback.isChecked() is (box == "coché")


@when(
	parsers.re(
		r"j'y saisis un blanc de (?P<duration>[\d,]+) secondes sous (?P<threshold>-[\d,]+) dB, et"
		r" (?P<action>coche|décoche) le"
		r" passage au secours"
	)
)
def enter_dead_air(opened: Opened, duration: str, threshold: str, action: str) -> None:
	ui = the_window(opened).ui
	ui.dead_air_duration.setValue(_decibels(duration))
	ui.dead_air_threshold.setValue(_decibels(threshold))
	ui.dead_air_fallback.setChecked(action == "coche")


@then(parsers.re(rf"elle a donné {DEAD_AIR}"))
def dead_air_gives(opened: Opened, duration: str, threshold: str, remainder: str) -> None:
	assert opened.provided_list is not None
	assert opened.provided_list.dead_air == dead_air(duration, threshold, remainder)


# ─── Voyant « Saturation » (https://github.com/dascritch/machincast/issues/191) ───


@given(parsers.re(r"les préférences seront réglées avec le voyant « Saturation » (?P<state>affiché|caché)"))
def adjusted_clipping(interface: Context, state: str) -> None:
	interface.adjusted_clipping = state == "affiché"


@then(parsers.re(r"les préférences ont montré le voyant « Saturation » (?P<state>affiché|caché)"))
def shown_clipping(interface: Context, state: str) -> None:
	assert interface.shown_clippings == [state == "affiché"]


@then(parsers.re(r"le voyant « (?P<name>Saturation|Blanc) » de l'antenne est (?P<state>affiché|caché) dans l'onglet"))
def on_air_light(interface: Context, name: str, state: str) -> None:
	ui = window(interface).home.ui
	light = {"Saturation": ui.clipping_light, "Blanc": ui.dead_air_light}[name]
	assert light.isHidden() is (state == "caché")


@when(parsers.re(r"la fenêtre des préférences s'ouvre sur le voyant « Saturation » (?P<state>affiché|caché)"))
def open_on_clipping(opened: Opened, parent: QWidget, state: str) -> None:
	all_ = Settings(Crossfades(), None, TEST_PREVIEW, clipping=state == "affiché")
	opened.window = PreferencesWindow(all_, "dummy", parent)


@then(parsers.re(r"elle montre la case « (?P<text>[^»]+) », (?P<state>cochée|décochée)"))
def clipping_box(opened: Opened, text: str, state: str) -> None:
	box = the_window(opened).ui.clipping
	assert (box.text(), box.isChecked()) == (text, state == "cochée")


@when("j'y décoche la case du voyant « Saturation »")
def untick_clipping(opened: Opened) -> None:
	the_window(opened).ui.clipping.setChecked(False)


@then(parsers.re(r"elle a donné le voyant « Saturation » (?P<state>affiché|caché)"))
def data_clipping(opened: Opened, state: str) -> None:
	assert opened.provided_list is not None
	assert opened.provided_list.clipping is (state == "affiché")


# ─── Suggestions au lancement (https://github.com/dascritch/machincast/issues/119) ───


@when(parsers.re(r"la fenêtre des préférences s'ouvre sur les suggestions au lancement (?P<state>actives|éteintes)"))
def open_on_suggestions(opened: Opened, parent: QWidget, state: str) -> None:
	all_ = Settings(Crossfades(), None, TEST_PREVIEW, suggestions=state == "actives")
	opened.window = PreferencesWindow(all_, "dummy", parent)


@then(parsers.re(r"elle montre la case des suggestions « (?P<text>[^»]+) », (?P<state>cochée|décochée)"))
def suggestions_box(opened: Opened, text: str, state: str) -> None:
	box = the_window(opened).ui.suggestions
	assert (box.text(), box.isChecked()) == (text, state == "cochée")


@when("j'y décoche la case des suggestions au lancement")
def untick_suggestions(opened: Opened) -> None:
	the_window(opened).ui.suggestions.setChecked(False)


@then(parsers.re(r"elle a donné les suggestions au lancement (?P<state>actives|éteintes)"))
def data_suggestions(opened: Opened, state: str) -> None:
	assert opened.provided_list is not None
	assert opened.provided_list.suggestions is (state == "actives")


# ─── Icône de l'interface (https://github.com/dascritch/machincast/issues/111) ───


def _image(path: Path | None) -> QImage:
	"""L'icône, à 32 pixels : celle de MachinCast pour None."""
	return QIcon(str((path) or (ICON))).pixmap(32).toImage()


def _icon(interface: Context, text: str | None) -> Path | None:
	"""« de MachinCast » donne None, « « …/logo.png » » le chemin dans le répertoire du scénario."""
	if text is None:
		return None
	return Path(interface.path_in(text))


SCENARIO_ICON = r"(?:de MachinCast|« (?P<path>[^»]+) »)"


@given(parsers.parse("une image PNG « {path} »"))
def image_png(interface: Context, path: str) -> None:
	image = QImage(32, 32, QImage.Format.Format_ARGB32)
	image.fill(QColor("#c0392b"))
	assert image.save(interface.path_in(path), "PNG")


@given(parsers.parse("un fichier « {path} » qui n'est pas une image"))
def false_image(interface: Context, path: str) -> None:
	Path(interface.path_in(path)).write_text("pas une image", encoding="utf-8")


@given(parsers.re(rf"les préférences seront réglées avec l'icône {SCENARIO_ICON}"))
def adjusted_icon(interface: Context, path: str | None) -> None:
	interface.adjusted_icon = (_icon(interface, path),)


@given(parsers.parse("le fichier de configuration de l'interface a l'icône « {path} »"))
def configuration_with_icon(interface: Context, path: str) -> None:
	file = configuration_file(interface)
	document = tomlkit.parse(file.read_text(encoding="utf-8"))
	if "interface" not in document:
		document.add("interface", tomlkit.table())
	section = document["interface"]
	assert isinstance(section, tomlkit.items.Table)
	section["icon"] = interface.path_in(path)
	file.write_text(tomlkit.dumps(document), encoding="utf-8")


def _place(place: str) -> Path:
	if place == "dans le menu des applications":
		return shortcut.menu_folder() / shortcut.NAME
	folder = shortcut.desktop_folder()
	assert folder is not None
	return folder / shortcut.NAME


@given(parsers.re(r"le raccourci de MachinCast installé (?P<place>dans le menu des applications|sur le bureau)"))
def installed_shortcut(place: str) -> None:
	path = _place(place)
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(shortcut.write(), encoding="utf-8")
	path.chmod(0o755 if place == "sur le bureau" else 0o644)


def _shortcut_icon(path: Path) -> str:
	lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("Icon=")]
	assert len(lines) == 1, lines
	return lines[0].removeprefix("Icon=")


@then(parsers.re(rf"le raccourci du menu des applications a l'icône {SCENARIO_ICON}"))
def menu_shortcut(interface: Context, path: str | None) -> None:
	expected = (_icon(interface, path)) or (ICON)
	assert _shortcut_icon(_place("dans le menu des applications")) == str(expected)


@then(parsers.re(rf"le raccourci du bureau a l'icône {SCENARIO_ICON}, et reste exécutable"))
def desktop_shortcut(interface: Context, path: str | None) -> None:
	file = _place("sur le bureau")
	assert _shortcut_icon(file) == str((_icon(interface, path)) or (ICON))
	assert stat.S_IMODE(file.stat().st_mode) == 0o755


@then("il n'y a pas de raccourci de MachinCast sur le bureau")
def not_shortcut_on_desktop() -> None:
	assert not _place("sur le bureau").exists()


@then(parsers.re(rf"l'application a l'icône {SCENARIO_ICON}"))
def application_icon(interface: Context, path: str | None) -> None:
	application = QApplication.instance()
	assert isinstance(application, QApplication)
	assert application.windowIcon().pixmap(32).toImage() == _image(_icon(interface, path))


@then(parsers.re(rf"les préférences ont montré l'icône {SCENARIO_ICON}"))
def shown_icon(interface: Context, path: str | None) -> None:
	assert interface.shown_icons == [_icon(interface, path)]


@then(parsers.parse("le fichier de configuration donne l'icône « {path} »"))
def file_icon(interface: Context, path: str) -> None:
	document = tomllib.loads(configuration_file(interface).read_text(encoding="utf-8"))
	assert document["interface"]["icon"] == interface.path_in(path)


@then("le fichier de configuration n'a pas d'icône")
def without_icon(interface: Context) -> None:
	document = tomllib.loads(configuration_file(interface).read_text(encoding="utf-8"))
	assert "icone" not in document.get("interface", {}), document


@then(parsers.re(r"la barre d'état (?P<direction>dit|ne dit pas) « (?P<text>[^»]+) »"))
def state_bar_says(interface: Context, direction: str, text: str) -> None:
	message = window(interface).statusBar().currentMessage()
	assert (interface.path_in(text) in message) is (direction == "dit"), message


@when(parsers.re(rf"la fenêtre des préférences s'ouvre sur l'icône {SCENARIO_ICON}"))
def open_on_icon(interface: Context, opened: Opened, parent: QWidget, path: str | None) -> None:
	all_ = Settings(Crossfades(), None, TEST_PREVIEW, icon=_icon(interface, path))
	opened.window = PreferencesWindow(all_, "dummy", parent)


@then(parsers.re(rf"elle montre l'icône {SCENARIO_ICON}"))
def shows_icon(interface: Context, opened: Opened, path: str | None) -> None:
	ui = the_window(opened).ui
	expected = _icon(interface, path)
	text = preferences.DEFAULT_ICON
	if expected is not None:
		text = str(expected)
	assert ui.path_icon.text() == text
	assert ui.preview_icon.pixmap().toImage() == QIcon(str((expected) or (ICON))).pixmap(48).toImage()


@then(parsers.re(r"son bouton « Icône de MachinCast » est (?P<state>actif|inactif)"))
def default_button(opened: Opened, state: str) -> None:
	assert the_window(opened).ui.default_icon.isEnabled() is (state == "actif")


@when(parsers.re(r"j'y (?:choisis l'image « (?P<path>[^»]+) »|renonce au choix d'une image)"))
def choose_image(interface: Context, opened: Opened, monkeypatch: pytest.MonkeyPatch, path: str | None) -> None:
	monkeypatch.setattr(dialogs, "choose_icon", lambda _parent: _icon(interface, path))
	the_window(opened).ui.choose_icon.click()


@when("j'y clique sur le bouton « Icône de MachinCast »")
def come_back_to_default_icon(opened: Opened) -> None:
	the_window(opened).ui.default_icon.click()


@then(parsers.re(rf"elle a donné l'icône {SCENARIO_ICON}"))
def data_icon(interface: Context, opened: Opened, path: str | None) -> None:
	assert opened.provided_list is not None
	assert opened.provided_list.icon == _icon(interface, path)


@then(parsers.parse("elle signale « {text} »"))
def reports(interface: Context, opened: Opened, text: str) -> None:
	assert the_window(opened).ui.error_icon.text() == interface.path_in(text)


# ─── Positions des fondus (https://github.com/dascritch/machincast/issues/234) ───


def _position_choice(opened: Opened, fade: str) -> QComboBox:
	ui = the_window(opened).ui
	return {"fade-in": ui.entry_position, "fade-out": ui.output_position}[fade]


@then(
	parsers.re(
		r"le (?P<fade>fade-in|fade-out) se propose (?P<texts>«.+») (?:au début détecté|à la fin détectée),"
		r" et « (?P<chosen>[^»]+) » est choisi"
	)
)
def offered_positions(opened: Opened, fade: str, texts: str, chosen: str) -> None:
	choice = _position_choice(opened, fade)
	assert [choice.itemText(rank) for rank in range(choice.count())] == NAME.findall(texts)
	assert choice.currentText() == chosen


@when(parsers.parse("j'y choisis le fade-in « {entry} » et le fade-out « {output} »"))
def choose_positions(opened: Opened, entry: str, output: str) -> None:
	for fade, text in (("fade-in", entry), ("fade-out", output)):
		choice = _position_choice(opened, fade)
		rank = choice.findText(text)
		assert rank >= 0, text
		choice.setCurrentIndex(rank)


@then(parsers.parse("elle a donné les positions : fade-in « {entry} », fade-out « {output} »"))
def data_positions(opened: Opened, entry: str, output: str) -> None:
	assert opened.provided_list is not None
	assert (opened.provided_list.crossfades.entry, opened.provided_list.crossfades.output) == (entry, output)


@then(
	parsers.parse(
		"la frise de démonstration montre le fade-in de {of_entry:d} à {has_entry:d} s, et le fade-out de"
		" {of_output:d} à {has_output:d} s"
	)
)
def demonstration_timeline(opened: Opened, of_entry: int, has_entry: int, of_output: int, has_output: int) -> None:
	plan = the_window(opened).demonstration.plan
	assert plan is not None
	entry, output = plan.fades()
	assert (entry, output) == (
		pytest.approx((of_entry, has_entry)),
		pytest.approx((of_output, has_output)),
	), (entry, output)


@then("la frise de démonstration a sa forme d'onde, sans tête de lecture")
def demonstration_shape(opened: Opened) -> None:
	timeline = the_window(opened).demonstration
	assert (timeline.shape is not None) and (timeline.shape.finished) and (timeline.shape.peaks)
	assert timeline.head is None
	assert not timeline.interactive


@given(parsers.parse("les positions des fondus seront réglées : fade-in « {entry} », fade-out « {output} »"))
def adjusted_positions(interface: Context, entry: str, output: str) -> None:
	interface.adjusted_preferences = dataclasses.replace(
		(interface.adjusted_preferences) or (Crossfades()), entry=entry, output=output
	)


@then(
	parsers.parse(
		"le fichier de configuration donne les positions des fondus : fade-in « {entry} », fade-out « {output} »"
	)
)
def file_positions(interface: Context, entry: str, output: str) -> None:
	crossfades = load(configuration_file(interface)).crossfades
	assert (crossfades.entry, crossfades.output) == (entry, output)


# ─── Durée de péremption (https://github.com/dascritch/machincast/issues/268) ───


@then(parsers.parse("les préférences ont montré la durée de péremption de {days:d} jours"))
def shown_retention(interface: Context, days: int) -> None:
	assert interface.shown_retentions == [days]


@then(parsers.parse("la durée de péremption de l'interface est de {days:d} jours"))
def session_retention(days: int) -> None:
	assert preferences.retention() == days


@when(parsers.parse("la fenêtre des préférences s'ouvre sur la durée de péremption de {days:d} jours"))
def open_on_retention(opened: Opened, parent: QWidget, days: int) -> None:
	all_ = Settings(Crossfades(), None, TEST_PREVIEW, retention=days)
	opened.window = PreferencesWindow(all_, "dummy", parent)


@then(parsers.parse("elle montre la durée de péremption « {text} », réglable de {minimum:d} à {maximum:d} jours"))
def displayed_retention(opened: Opened, text: str, minimum: int, maximum: int) -> None:
	field = the_window(opened).ui.retention
	assert (field.text(), field.minimum(), field.maximum()) == (text, minimum, maximum)


@when(parsers.parse("j'y saisis la durée de péremption de {days:d} jours"))
def enter_retention(opened: Opened, days: int) -> None:
	the_window(opened).ui.retention.setValue(days)


@then(parsers.parse("elle a donné la durée de péremption de {days:d} jours"))
def data_retention(opened: Opened, days: int) -> None:
	assert opened.provided_list is not None
	assert opened.provided_list.retention == days
