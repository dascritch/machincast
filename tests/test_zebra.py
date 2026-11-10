"""Scénarios des tableaux en zebra (https://github.com/dascritch/machincast/issues/412).

Les étapes de la fenêtre, des fiches, des menus et des éléments en base sont dans tests/interface_steps.py.
"""

from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QAbstractItemView, QApplication, QComboBox, QCompleter, QHeaderView
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import application, zebra
from tests.interface_steps import Context, window

scenarios("zebra.feature")

SCREENS = Path(__file__).resolve().parent.parent / "src" / "machincast" / "interface" / "ui"
VIEWS = ("QTableView", "QTableWidget", "QTreeView", "QTreeWidget", "QListView", "QListWidget")
ROLE = QPalette.ColorRole.AlternateBase


def _number(text: str) -> float:
	return float(text.replace(",", "."))


@pytest.fixture
def origin_palette(qapp: QApplication) -> Iterator[None]:
	origin = QPalette(qapp.palette())
	yield
	qapp.setPalette(origin)


def _theme(qapp: QApplication, base: str, text: str, alternate: str | None = None) -> None:
	palette = QPalette(qapp.palette())
	for group in zebra.GROUPS:
		palette.setColor(group, QPalette.ColorRole.Base, QColor(base))
		palette.setColor(group, QPalette.ColorRole.Text, QColor(text))
		if alternate is not None:
			palette.setColor(group, ROLE, QColor(alternate))
	qapp.setPalette(palette)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le thème de l'application, au fond {base}, au texte {text} et au fond alterné {alternate}"))
def theme(qapp: QApplication, origin_palette: None, base: str, text: str, alternate: str) -> None:
	_theme(qapp, base, text, alternate)


# ─── Quand ─────────────────────────────────────────────────


@when("l'application de l'interface se crée")
def create(qapp: QApplication) -> None:
	assert application.application("Machin_interface") is qapp


@when(parsers.parse("le thème de l'application passe au fond {base} et au texte {text}"))
def change(qapp: QApplication, base: str, text: str) -> None:
	_theme(qapp, base, text)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le fond alterné de {base} et {text} contraste de {low} à {high} avec le fond"))
def faint(base: str, text: str, low: str, high: str) -> None:
	ratio = zebra.contrast(zebra.alternate(QColor(base), QColor(text)), QColor(base))
	assert _number(low) <= ratio <= _number(high), ratio


@then(parsers.parse("le texte contraste d'au moins {minimum} avec le fond alterné de {base} et {text}"))
def readable(base: str, text: str, minimum: str) -> None:
	ratio = zebra.contrast(zebra.alternate(QColor(base), QColor(text)), QColor(text))
	assert ratio >= _number(minimum), ratio


@then(parsers.parse("le fond alterné de {base} et {text} est {expected}"))
def unchanged(base: str, text: str, expected: str) -> None:
	assert zebra.alternate(QColor(base), QColor(text)).name() == expected


@then(parsers.parse("le fond alterné de l'application est celui de {base} et {text}"))
def follows(qapp: QApplication, qtbot: QtBot, base: str, text: str) -> None:
	expected = zebra.alternate(QColor(base), QColor(text))

	def posed() -> None:
		for group in zebra.GROUPS:
			assert qapp.palette().color(group, ROLE) == expected

	qtbot.waitUntil(posed)
	assert qapp.palette().color(QPalette.ColorRole.Base) == QColor(base)


def _in_popup(view: QAbstractItemView) -> bool:
	"""La liste déroulante d'une liste à choix, ou d'une complétion : une liste, pas un tableau."""
	parent = view.parent()
	while parent is not None:
		if isinstance(parent, (QComboBox, QCompleter)):
			return True
		parent = parent.parent()
	completer_list = []
	for completer in view.window().findChildren(QCompleter):
		completer_list.append(completer.popup())
	return view in completer_list


@then("chaque tableau de la fenêtre alterne ses lignes")
def window_views(interface: Context) -> None:
	views = []
	plain = []
	for view in window(interface).findChildren(QAbstractItemView):
		if (not isinstance(view, QHeaderView)) and (not _in_popup(view)):
			views.append(view)
			if not view.alternatingRowColors():
				plain.append((view.objectName()) or (type(view).__name__))
	assert len(views) >= 10, views
	assert plain == []


@then("chaque tableau des écrans .ui alterne ses lignes")
def screen_views() -> None:
	plain = []
	found = 0
	for screen in sorted(SCREENS.glob("*.ui")):
		for widget in ElementTree.parse(screen).iter("widget"):
			if widget.get("class") in VIEWS:
				found += 1
				zebra_list = []
				for item in widget.findall("property"):
					if (item.get("name") == "alternatingRowColors") and (item.findtext("bool") == "true"):
						zebra_list.append(item)
				if zebra_list == []:
					plain.append(f"{screen.name} : {widget.get('name')}")
	assert found >= 10
	assert plain == []
