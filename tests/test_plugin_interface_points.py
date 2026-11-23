"""Scénarios des points d'extension des fiches et des menus de l'interface
(https://github.com/dascritch/machincast/issues/591).

Les plugins sont imités par des abonnés aux points des plugins chargés (machincast.plugins.active), que
tests/conftest.py remet à vide après chaque scénario ; les notifications sont attendues (Points.close) avant d'être
lues.
"""

import json
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QBoxLayout, QLineEdit, QMenu, QVBoxLayout, QWidget
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import plugins
from machincast.interface.card import Card, CardSection
from machincast.interface.lists import IDENTIFIER, List
from tests.interface_steps import Connection, Context, open_tab, opened_card, window
from tests.plugin_steps import Recorder

scenarios("plugin_interface_points.feature")


class Remark(CardSection):
	"""La section du plugin « remarque » : une remarque, rangée sous son nom dans les propriétés de la banque."""

	def __init__(self, connection: Connection, parent: QWidget | None) -> None:
		super().__init__(parent)
		self.connection = connection
		self.setObjectName("remarque")
		self.text = QLineEdit(self)
		QVBoxLayout(self).addWidget(self.text)
		self.text.textChanged.connect(self.changed)

	def read(self, identifier: int | None) -> None:
		found = self.connection.execute("SELECT properties ->> 'remarque' FROM banks WHERE id = %s", (identifier,))
		line = found.fetchone()
		text = ""
		if (line is not None) and (line[0] is not None):
			text = str(line[0])
		self.text.setText(text)

	def write(self, identifier: int) -> None:
		self.connection.execute(
			"UPDATE banks SET properties = properties || jsonb_build_object('remarque', %s::text) WHERE id = %s",
			(self.text.text(), identifier),
		)


def _section(interface: Context) -> Remark:
	found = opened_card(interface).findChild(Remark, "remarque")
	assert isinstance(found, Remark)
	return found


def _bank(database: Connection, name: str) -> int | None:
	line = database.execute("SELECT id FROM banks WHERE internal_name = %s", (name,)).fetchone()
	if line is None:
		return None
	return int(str(line[0]))


@given("le plugin « remarque », qui ajoute sa section à la fiche d'une banque")
def remark_plugin() -> None:
	def section(data: Mapping[str, Any]) -> CardSection:
		return Remark(data["connection"], data["parent"])

	plugins.active().points.subscribe("remarque", "interface.bank_card", section)


@given(parsers.parse("la banque « {name} » a pour propriétés « {properties} »"))
def properties_set(empty_database: Connection, name: str, properties: str) -> None:
	empty_database.execute("UPDATE banks SET properties = %s::jsonb WHERE internal_name = %s", (properties, name))


@given(parsers.parse("un plugin abonné à « {first} » et à « {second} »"))
def subscribed(recorder: Recorder, first: str, second: str) -> None:
	recorder.subscribe(plugins.active().points, "témoin", [first, second])


@given(parsers.parse("un plugin qui refuse, à « {point} », un nom interne sans majuscule : « {reason} »"))
def refusing(point: str, reason: str) -> None:
	def check(data: Mapping[str, Any]) -> str | None:
		name = str(data["row"]["internal_name"])
		if name[0].isupper():
			return None
		return reason

	plugins.active().points.subscribe("majuscule", point, check)


@given(parsers.parse("un plugin qui ajoute le menu « {title} » à la barre de menus"))
def menu_plugin(title: str) -> None:
	def menu(data: Mapping[str, Any]) -> QMenu:
		return QMenu(title, data["parent"])

	plugins.active().points.subscribe("outils", "interface.menu", menu)


@given(parsers.parse("un plugin qui ajoute l'entrée « {entry} » au clic droit sur une ligne"))
def context_plugin(recorder: Recorder, entry: str) -> None:
	def add(data: Mapping[str, Any]) -> None:
		action = data["menu"].addAction(entry)
		exported = {"category": data["category"], "identifiers": data["identifiers"]}
		action.triggered.connect(lambda: recorder.received.append(("export", exported)))

	plugins.active().points.subscribe("export", "interface.context_menu", add)


@when(parsers.parse("je saisis « {text} » dans la section du plugin « remarque »"))
def enter(interface: Context, text: str) -> None:
	_section(interface).text.setText(text)


@when(parsers.parse("je choisis « {entry} » au clic droit sur la ligne « {name} » de l'onglet « {tab} »"))
def right_click(interface: Context, entry: str, name: str, tab: str) -> None:
	open_tab(interface, tab)
	list_ = window(interface).ui.tabs.currentWidget()
	assert isinstance(list_, List)
	found = list_.proxy.match(list_.proxy.index(0, 0), IDENTIFIER + 1, name, -1, Qt.MatchFlag.MatchExactly)
	assert len(found) == 1, name
	menu = list_.line_menu(found[0])
	assert menu is not None
	chosen = []
	for action in menu.actions():
		if action.text() == entry:
			chosen.append(action)
	(action,) = chosen
	action.trigger()


@then(parsers.parse("la fiche a la section du plugin « remarque », au-dessus de ses boutons, qui montre « {text} »"))
def section_shown(interface: Context, text: str) -> None:
	card = opened_card(interface)
	section = _section(interface)
	assert section.text.text() == text
	arrangement = card.layout()
	assert isinstance(arrangement, QBoxLayout)
	assert arrangement.indexOf(section) == arrangement.count() - 2


@then("la fiche n'est pas modifiée")
def unmodified(interface: Context) -> None:
	assert not opened_card(interface).modified


@then("la fiche est modifiée")
def modified(interface: Context) -> None:
	assert opened_card(interface).modified


@then(parsers.parse("la banque « {name} » a pour propriétés « {properties} »"))
def properties_read(empty_database: Connection, name: str, properties: str) -> None:
	found = empty_database.execute("SELECT properties FROM banks WHERE internal_name = %s", (name,)).fetchone()
	assert found is not None
	assert found[0] == json.loads(properties)


@then(parsers.parse("le plugin a été prévenu de « interface.load_bank » pour la banque « {name} »"))
def loaded(empty_database: Connection, recorder: Recorder, name: str) -> None:
	plugins.active().points.close()
	assert recorder.of("interface.load_bank") == [
		{"category": "bank", "identifier": _bank(empty_database, name), "copy": False}
	]


@then(parsers.parse("le plugin a été prévenu de « interface.save_bank » pour la banque « {name} », avec sa ligne"))
def saved(empty_database: Connection, recorder: Recorder, name: str) -> None:
	plugins.active().points.close()
	(data,) = recorder.of("interface.save_bank")
	assert (data["category"], data["identifier"]) == ("bank", _bank(empty_database, name))
	assert (data["row"]["internal_name"], data["row"]["id"]) == (name, data["identifier"])


@then(parsers.parse("la fiche signale « {text} »"))
def card_says(interface: Context, text: str) -> None:
	card = opened_card(interface)
	assert isinstance(card, Card)
	assert card.error.text() == text


@then(parsers.parse("la banque « {name} » est toujours en base sous ce nom"))
@then(parsers.parse("la banque « {name} » est en base"))
def in_database(empty_database: Connection, name: str) -> None:
	assert _bank(empty_database, name) is not None


@then(parsers.parse("le plugin a exporté la banque « {name} »"))
def exported(empty_database: Connection, recorder: Recorder, name: str) -> None:
	assert recorder.received == [("export", {"category": "bank", "identifiers": [_bank(empty_database, name)]})]
