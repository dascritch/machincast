"""Scénarios de la section qu'un plugin ajoute à la fiche d'un événement
(https://github.com/dascritch/machincast/issues/611).

Le plugin « note » est imité par un abonné au point « interface.event_card » des plugins du binaire
(machincast.plugins.active), que tests/conftest.py remet à vide après chaque scénario.
"""

import json
from typing import Any

from PySide6.QtWidgets import QCheckBox, QLineEdit, QVBoxLayout, QWidget
from pytest_bdd import given, parsers, scenarios, then, when

from machincast import plugins
from machincast.interface.card import Refusal
from machincast.interface.event_card import POINT, CardSection, EventCard
from machincast.plugins.points import CORE
from tests.interface_steps import Connection, Context, window

scenarios("event_card_section.feature")


class Note(CardSection):
	"""La section du plugin « note » : une note, rangée sous son nom dans les propriétés de l'événement."""

	def __init__(self, connection: Connection, parent: QWidget | None) -> None:
		super().__init__(parent)
		self.connection = connection
		self.setObjectName("note")
		self.text = QLineEdit(self)
		self.without_list = QCheckBox("Sans liste", self)
		arrangement = QVBoxLayout(self)
		arrangement.addWidget(self.text)
		arrangement.addWidget(self.without_list)
		self.text.textChanged.connect(self.changed)
		self.without_list.toggled.connect(self.replaces_items)

	def grid_widget(self) -> QWidget | None:
		return self.without_list

	def read(self, identifier: int | None) -> None:
		properties: dict[str, Any] = {}
		if identifier is not None:
			found = self.connection.execute("SELECT properties FROM events WHERE id = %s", (identifier,)).fetchone()
			if found is not None:
				properties = dict(found[0])  # type: ignore[call-overload]
		self.text.setText(str(properties.get("note", {}).get("text", "")))

	def write(self, identifier: int) -> None:
		if self.text.text() == "":
			raise Refusal("Une note est demandée.", self.text)
		self.connection.execute(
			"UPDATE events SET properties = properties || jsonb_build_object('note', jsonb_build_object('text', %s::text))"
			" WHERE id = %s",
			(self.text.text(), identifier),
		)


def _card(interface: Context) -> EventCard:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, EventCard), opened
	return opened


def _section(interface: Context) -> Note:
	found = _card(interface).findChild(Note, "note")
	assert isinstance(found, Note)
	return found


@given(parsers.parse("l'événement « {name} » a pour propriétés « {properties} »"))
def properties_set(empty_database: Connection, name: str, properties: str) -> None:
	empty_database.execute("UPDATE events SET properties = %s::jsonb WHERE internal_name = %s", (properties, name))


@given("le plugin « note », qui ajoute sa section à la fiche d'un événement")
def note_plugin() -> None:
	def section(data: Any) -> CardSection:
		return Note(data["connection"], data["parent"])

	plugins.active().points.subscribe("note", POINT, section)


@then(parsers.parse("la fiche de l'événement a la section du plugin « note », qui montre « {text} »"))
def section_shown(interface: Context, text: str) -> None:
	assert _section(interface).text.text() == text


@then("la fiche de l'événement montre sa liste")
def items_shown(interface: Context) -> None:
	assert not _card(interface).ui.item_group.isHidden()


@then("la fiche de l'événement ne montre plus sa liste")
def items_hidden(interface: Context) -> None:
	assert _card(interface).ui.item_group.isHidden()


@then(
	parsers.parse(
		"la case « {label} » du plugin « note » est sous les jours de la récurrence, au-dessus de l'explication des dates"
	)
)
def under_days(interface: Context, label: str) -> None:
	ui = _card(interface).ui
	box = _section(interface).without_list
	assert box.text() == label
	assert box.parentWidget() is ui.grid_group
	layout = ui.grid_layout
	days_row = -1
	for index in range(layout.count()):
		if layout.itemAt(index).layout() is ui.day_layout:
			days_row = layout.getItemPosition(index)[0]
	box_row = layout.getItemPosition(layout.indexOf(box))[0]
	explanation_row = layout.getItemPosition(layout.indexOf(ui.grid_explanation))[0]
	assert (box_row, explanation_row) == (days_row + 1, days_row + 2)


@then("la fiche n'est pas modifiée")
def unmodified(interface: Context) -> None:
	assert not _card(interface).modified


@then("la fiche est modifiée")
def modified(interface: Context) -> None:
	assert _card(interface).modified


@when(parsers.re(r"je saisis « (?P<text>[^»]*?) ?» dans la section du plugin « note »"))
def enter(interface: Context, text: str) -> None:
	_section(interface).text.setText(text)


@when(parsers.parse("je coche « {label} » dans la section du plugin « note »"))
def tick(interface: Context, label: str) -> None:
	box = _section(interface).without_list
	assert box.text() == label
	box.setChecked(True)


@then(parsers.parse("la fiche signale « {text} »"))
def card_says(interface: Context, text: str) -> None:
	assert _card(interface).error.text() == text


@then(parsers.parse("l'événement « {name} » a pour propriétés « {properties} »"))
def properties_read(empty_database: Connection, name: str, properties: str) -> None:
	found = empty_database.execute("SELECT properties FROM events WHERE internal_name = %s", (name,)).fetchone()
	assert found is not None
	assert found[0] == json.loads(properties)


@then(parsers.parse("le point « {point} » est un point du cœur, qui mène à la CardSection"))
def core_point(point: str) -> None:
	assert point == POINT
	assert "machincast.interface.event_card.CardSection" in CORE[point]
