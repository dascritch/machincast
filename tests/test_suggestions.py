"""Suggestions au lancement de l'interface (https://github.com/dascritch/machincast/issues/119).

La fenêtre des suggestions est remplacée par les réponses du scénario (tests/interface_steps.py) ; la vraie fenêtre
s'ouvre ici, hors de l'écran du poste.
"""

import re
from collections.abc import Iterator
from datetime import timedelta

import pytest
import tomlkit
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QDialogButtonBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.configuration import Audio
from machincast.interface.sound_cards import SoundCards
from machincast.interface.suggestions import (
	BACKGROUND_PROGRAMMING,
	BANKS,
	Response,
	Shortfalls,
	SuggestionsWindow,
	label,
)
from machincast.service import ABSENT, ServiceState
from tests.interface_steps import NAME, Connection, Context, configuration_file, window

scenarios("suggestions.feature")


# ─── Étant donné ───────────────────────────────────────────


@given("les suggestions au lancement sont actives")
def active_list(interface: Context) -> None:
	interface.active_suggestions = True


@given("les suggestions au lancement sont éteintes dans le fichier de configuration")
def off_list(interface: Context) -> None:
	path = configuration_file(interface)
	document = tomlkit.parse(path.read_text(encoding="utf-8"))
	section = tomlkit.table()
	section["suggestions"] = False
	document["interface"] = section
	path.write_text(tomlkit.dumps(document), encoding="utf-8")


@given("les banques suggérées existent déjà")
def existing_banks(empty_database: Connection) -> None:
	for name in BANKS:
		empty_database.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, 'random')", (name,))


@given(
	parsers.re(
		r"les suggestions seront refermées par « Plus tard »(?P<box>, en cochant « Ne plus proposer au lancement »)?"
	)
)
def latest(interface: Context, box: str | None) -> None:
	interface.response_to_suggestions = lambda _gaps: Response(create=False, more_offer=box is not None)


@given(
	parsers.re(
		r"les suggestions seront acceptées par « Créer »(?:, sans « (?P<without>.+) »)?"
		r"(?:, avec la sortie « (?P<output>[^»]+) », l'antenne « (?P<on_air>[^»]+) »"
		r" et la pré-écoute « (?P<preview>[^»]+) »)?$"
	)
)
def create(
	interface: Context, without: str | None, output: str | None, on_air: str | None, preview: str | None
) -> None:
	def answer(gaps: Shortfalls) -> Response:
		bank_list = []
		for bank in gaps.banks:
			if label(bank) != without:
				bank_list.append(bank)
		banks = tuple(bank_list)
		return Response(
			create=True,
			background_programming=(gaps.background_programming) and (without != BACKGROUND_PROGRAMMING),
			banks=banks,
			output=output,  # type: ignore[arg-type]
			on_air=on_air,
			preview=preview,
		)

	interface.response_to_suggestions = answer


# ─── Alors ─────────────────────────────────────────────────


def first_list(interface: Context) -> Shortfalls:
	assert interface.done_suggestions, "aucune suggestion"
	return interface.done_suggestions[0]


@then("les suggestions ont proposé :")
def offered_list(interface: Context, datatable: list[list[str]]) -> None:
	_header, *lines = datatable
	line_list = []
	for (line,) in lines:
		line_list.append(line.strip())
	assert first_list(interface).items() == line_list


@then("les suggestions n'ont pas proposé les cartes son")
def without_cards(interface: Context) -> None:
	assert first_list(interface).audio is None


@then(
	parsers.re(
		r"les suggestions ont proposé les cartes son de la sortie « (?P<output>[^»]+) », l'antenne non renseignée"
		r" et la pré-écoute « (?P<preview>[^»]+) »"
	)
)
def offered_cards(interface: Context, output: str, preview: str) -> None:
	assert first_list(interface).audio == Audio(output, None, preview)  # type: ignore[arg-type]


@then("aucune suggestion n'a été faite")
def no(interface: Context) -> None:
	assert interface.done_suggestions == []


@then(parsers.parse("les suggestions ont été faites {count:d} fois"))
def times_count(interface: Context, count: int) -> None:
	assert len(interface.done_suggestions) == count


@then(parsers.re(r"il n'y a aucun(?:e)? (?P<category>événement|banque) en base"))
def nothing_in_database(empty_database: Connection, category: str) -> None:
	table = {"événement": "events", "banque": "banks"}[category]
	line = empty_database.execute(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608
	assert line == (0,), line


@then(parsers.parse("le fil musical « {name} » est en base, permanent"))
def permanent_feed(empty_database: Connection, name: str) -> None:
	lines = empty_database.execute(
		"SELECT priority::text, starts_at, ends_at, recurrence_days::text[] FROM events WHERE internal_name = %s",
		(name,),
	).fetchall()
	assert lines == [("background_programming", None, None, [])], lines


@then(parsers.re(r"la liste de l'événement « (?P<name>[^»]+) » est en base (?P<banks>«.+)"))
def feed_list(empty_database: Connection, name: str, banks: str) -> None:
	lines = empty_database.execute(
		"SELECT b.internal_name FROM event_items x JOIN events e ON e.id = x.event_id"
		" JOIN banks b ON b.id = x.bank_id WHERE e.internal_name = %s ORDER BY x.position",
		(name,),
	).fetchall()
	bank_list = []
	for (bank,) in lines:
		bank_list.append(str(bank))
	assert bank_list == NAME.findall(banks)


@then(parsers.re(r"les fils musicaux en base sont (?P<names>«.+)"))
def feeds(empty_database: Connection, names: str) -> None:
	lines = empty_database.execute(
		"SELECT internal_name FROM events WHERE priority = 'background_programming' AND deleted_at IS NULL"
		" ORDER BY internal_name"
	).fetchall()
	name_list = []
	for (name,) in lines:
		name_list.append(str(name))
	assert name_list == NAME.findall(names)


def _crossfade(rule: str, duration: timedelta) -> str:
	if rule == "sound":
		return "des sonores"
	return f"{RULES[rule]}, {duration.total_seconds():g} s"


RULES = {"default": "à défaut", "forced": "imposé"}


@then("les banques en base sont :")
def banks_in_database(empty_database: Connection, datatable: list[list[str]]) -> None:
	_header, *lines = datatable
	fetched_list = []
	for name, mode, repeat, maximum, rule_start, start, rule_end, end in empty_database.execute(
		"SELECT internal_name, mode::text, no_repeat, max_duration, crossfade_start_rule::text, crossfade_start,"
		' crossfade_end_rule::text, crossfade_end FROM banks ORDER BY internal_name COLLATE "C"'
	).fetchall():
		repetition = "non"
		if repeat:
			repetition = "oui"
		fetched_list.append(
			(
				str(name),
				str(mode),
				repetition,
				str((maximum) or ("")),
				_crossfade(str(rule_start), start),
				_crossfade(str(rule_end), end),
			)
		)
	expected_list = []
	for line in lines:
		value_list = []
		for value in line:
			value_list.append(value.strip())
		expected_list.append(tuple(value_list))
	assert fetched_list == expected_list, fetched_list


@then(parsers.parse("la banque « {name} » en base a pour durée maximale « {maximum} », sans durée minimale"))
def maximal_duration(empty_database: Connection, name: str, maximum: str) -> None:
	line = empty_database.execute(
		"SELECT min_duration, max_duration FROM banks WHERE internal_name = %s", (name,)
	).fetchone()
	assert line is not None
	assert (line[0], str(line[1])) == (None, maximum)


@then(parsers.parse("le fichier de configuration contient la ligne « {line} »"))
def contains_line(interface: Context, line: str) -> None:
	assert line in configuration_file(interface).read_text(encoding="utf-8").splitlines()


@then(parsers.parse("le fichier de configuration contient encore « {text} »"))
def contains_still(interface: Context, text: str) -> None:
	assert text in configuration_file(interface).read_text(encoding="utf-8")


@then("le fichier de configuration n'a pas changé")
def unchanged(interface: Context) -> None:
	assert configuration_file(interface).read_bytes() == interface.initial_configuration


# ─── Vraie fenêtre ─────────────────────────────────────────


@pytest.fixture
def parent(qtbot: QtBot) -> Iterator[QWidget]:
	widget = QWidget()
	qtbot.addWidget(widget)
	yield widget


@pytest.fixture
def opened() -> dict[str, object]:
	return {}


def the_window(opened: dict[str, object]) -> SuggestionsWindow:
	window = opened["fenetre"]
	assert isinstance(window, SuggestionsWindow)
	return window


SERVICES = {
	"sans service de diffusion": ABSENT,
	"service de diffusion à l'arrêt": ServiceState(installed=True, active="inactive"),
}


@when(
	parsers.re(
		r"la fenêtre des suggestions s'ouvre sur (?:le fil musical et la banque « (?P<bank>[^»]+) », avec les"
		r"|(?P<only_list>les seules)) cartes son de la sortie « (?P<output>[^»]+) », (?P<service>.+)"
	)
)
def open_(
	opened: dict[str, object], parent: QWidget, bank: str | None, only_list: str | None, output: str, service: str
) -> None:
	"""La pré-écoute de la configuration des tests ; l'antenne à renseigner."""
	audio = Audio(output, None, "preecoute-factice")  # type: ignore[arg-type]
	gaps = Shortfalls(False, (), audio)
	if only_list is None:
		assert bank is not None
		gaps = Shortfalls(True, (bank,), audio)
	opened["fenetre"] = SuggestionsWindow(gaps, parent, SERVICES[service])


@then(parsers.parse("elle s'intitule « {title} »"))
def title(opened: dict[str, object], title: str) -> None:
	assert the_window(opened).windowTitle() == title


@then(parsers.re(r"elle propose, cochés, (?P<items>«.+)"))
def ticked_list(opened: dict[str, object], items: str) -> None:
	list_ = the_window(opened).ui.items
	lines = []
	for rank in range(list_.count()):
		lines.append(list_.item(rank))
	line_list = []
	for line in lines:
		line_list.append(line.text())
	assert line_list == re.findall(r"« ((?:[^«»]|« [^»]+ »)+) »", items)
	every_one = True
	for line in lines:
		if line.checkState() != Qt.CheckState.Checked:
			every_one = False
			break
	assert every_one


@then("elle montre les cartes son en tête, avant ce qui est à créer")
def cards_in_head(opened: dict[str, object]) -> None:
	window = the_window(opened)
	arrangement = window.layout()
	assert arrangement is not None
	assert arrangement.indexOf(window.ui.sound_cards_group) == 0
	assert arrangement.indexOf(window.ui.sound_cards_group) < arrangement.indexOf(window.ui.items)
	assert window.ui.sound_cards_group.isVisibleTo(window)


@then("elle ne propose rien à créer")
def nothing_to_create(opened: dict[str, object]) -> None:
	window = the_window(opened)
	assert not window.ui.items.isVisibleTo(window)
	assert not window.ui.explanation.isVisibleTo(window)


def _cards(opened: dict[str, object]) -> SoundCards:
	cards = the_window(opened).cards
	assert cards is not None
	return cards


@then(parsers.re(r"son choix de l'antenne propose (?P<names>«.+)"))
def on_air_choice(opened: dict[str, object], names: str) -> None:
	choice = _cards(opened).ui.on_air
	rank_list = []
	for rank in range(choice.count()):
		rank_list.append(choice.itemText(rank))
	assert rank_list == NAME.findall(names)


@then(parsers.parse("dans son choix de l'antenne, « {text} » est inactive"))
def inactive_line(opened: dict[str, object], text: str) -> None:
	choice = _cards(opened).ui.on_air
	model = choice.model()
	assert isinstance(model, QStandardItemModel)
	assert not model.item(choice.findText(text)).isEnabled()


@then(parsers.re(r"son bouton « (?P<text>Créer|Enregistrer) » est (?P<state>actif|inactif)"))
def ok_button(opened: dict[str, object], text: str, state: str) -> None:
	button = the_window(opened).ui.buttons.button(QDialogButtonBox.StandardButton.Ok)
	assert (button.text(), button.isEnabled()) == (text, state == "actif")


@when(parsers.parse("j'y décoche « {text} »"))
def untick(opened: dict[str, object], text: str) -> None:
	list_ = the_window(opened).ui.items
	rank_list = []
	for rank in range(list_.count()):
		if list_.item(rank).text() == text:
			rank_list.append(list_.item(rank))
	(line,) = rank_list
	line.setCheckState(Qt.CheckState.Unchecked)


@when(parsers.re(r"j'y choisis pour (?P<role>l'antenne|la pré-écoute) « (?P<name>[^»]+) »"))
def choose_card(opened: dict[str, object], role: str, name: str) -> None:
	ui = _cards(opened).ui
	choice = {"l'antenne": ui.on_air, "la pré-écoute": ui.preview}[role]
	index = choice.findText(name)
	assert index >= 0, name
	choice.setCurrentIndex(index)


@when("j'y coche « Ne plus proposer au lancement »")
def tick_more(opened: dict[str, object]) -> None:
	the_window(opened).ui.more_offer.setChecked(True)


@when(parsers.re(r"j'y clique sur « (?:Créer|Enregistrer) »"))
def click_create(opened: dict[str, object]) -> None:
	window = the_window(opened)
	window.ui.buttons.button(QDialogButtonBox.StandardButton.Ok).click()
	opened["reponse"] = window.response()


@then(
	parsers.re(
		r"elle a donné : (?:la banque « (?P<bank>[^»]+) », )?la sortie « (?P<output>[^»]+) »,"
		r" l'antenne « (?P<on_air>[^»]+) », la pré-écoute « (?P<preview>[^»]+) »(?P<more>, ne plus proposer)?"
	)
)
def gives(
	opened: dict[str, object],
	bank: str | None,
	output: str,
	on_air: str,
	preview: str,
	more: str | None,
) -> None:
	assert the_window(opened).result() == SuggestionsWindow.DialogCode.Accepted
	banks: tuple[str, ...] = ()
	if bank is not None:
		banks = (bank,)
	assert opened["reponse"] == Response(
		create=True,
		background_programming=False,
		banks=banks,
		output=output,  # type: ignore[arg-type]
		on_air=on_air,
		preview=preview,
		more_offer=more is not None,
	)


@then(parsers.re(r"la barre d'état (?P<reports>signale|ne signale pas) « Périphérique de l'antenne à renseigner »"))
def reported_on_air(interface: Context, reports: str) -> None:
	opened = window(interface)
	assert opened.to_fill_in_on_air.isVisibleTo(opened) == (reports == "signale")
