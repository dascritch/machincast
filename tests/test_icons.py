"""Scénarios des icônes des genres (https://github.com/dascritch/machincast/issues/215).

Les étapes de la fenêtre, des fiches, des menus et des éléments en base sont dans tests/interface_steps.py.
"""

from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPalette
from PySide6.QtWidgets import QApplication
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import icons
from machincast.interface.search import SearchScreen
from machincast.interface.sound_card import SoundCard
from tests.categories import CATEGORY
from tests.interface_steps import NAME, Context, actions, tab_title, window

scenarios("icons.feature")

SIZE = 24


def image(icon: QIcon, size: int = SIZE) -> QImage:
	return icon.pixmap(size).toImage().convertToFormat(QImage.Format.Format_ARGB32)


ICON_NAMES = CATEGORY | {"grille": "grid", "pré-écoute": "preview"}
"""Le nom d'une icône dans le code, par son mot des scénarios (https://github.com/dascritch/machincast/issues/368)."""


def _icon_name(name: str) -> str:
	return ICON_NAMES.get(name, name)


def _expected(name: str) -> QImage | None:
	"""L'image de l'icône d'un genre, ou None pour « aucune »."""
	if name == "aucune":
		return None
	return image(icons.icon(_icon_name(name)))


def _scope(icon: QIcon | None) -> QImage | None:
	if (icon is None) or (icon.isNull()):
		return None
	return image(icon)


@then(
	parsers.re(
		r"l'icône « (?P<category>[^»]+) », dessinée en (?P<colour>#[0-9a-f]{6}), n'a que cette couleur,"
		r" et se voit à (?P<sizes>.+) pixels"
	)
)
def monochrome(qapp: QApplication, category: str, colour: str, sizes: str) -> None:
	expected = QColor(colour)
	text_list = []
	for text in sizes.replace(" et ", ", ").split(", "):
		text_list.append(int(text))
	for size in text_list:
		drawing = image(icons.icon(_icon_name(category), expected), size)
		assert (drawing.width(), drawing.height()) == (size, size)
		pixels = []
		for x in range(size):
			for y in range(size):
				pixels.append(drawing.pixelColor(x, y))
		# Chaque pixel net est de la couleur demandée ; les bords lissés, presque transparents, perdent un peu de
		# précision, d'où la marge d'arrondi.
		clean_list = []
		for pixel in pixels:
			if pixel.alpha() > 128:
				clean_list.append(pixel)
		gaps = []
		for pixel in clean_list:
			gaps.append(
				max(
					abs(pixel.red() - expected.red()),
					abs(pixel.green() - expected.green()),
					abs(pixel.blue() - expected.blue()),
				)
			)
		assert max(gaps) <= 3, (category, size, max(gaps))
		assert len(clean_list) >= len(pixels) / 10, (category, size)


@then(parsers.re(r"les icônes (?P<names>«.+) sont toutes différentes"))
def different(qapp: QApplication, names: str) -> None:
	images = []
	for name in NAME.findall(names):
		images.append(image(icons.icon(_icon_name(name))))
	differences = []
	for rank, first in enumerate(images):
		for second in images[rank + 1 :]:
			differences.append(first != second)
	assert all(differences)


@pytest.fixture
def origin_palette(qapp: QApplication) -> Iterator[None]:
	origin = QPalette(qapp.palette())
	yield
	qapp.setPalette(origin)


@when(parsers.parse("le thème de l'application écrit en {colour}"))
def theme(qapp: QApplication, origin_palette: None, colour: str) -> None:
	palette = QPalette(qapp.palette())
	palette.setColor(QPalette.ColorRole.WindowText, QColor(colour))
	qapp.setPalette(palette)


@then(parsers.parse("l'icône « {category} » de l'application est dessinée en {colour}"))
def follows_theme(qapp: QApplication, category: str, colour: str) -> None:
	assert image(icons.icon(_icon_name(category))) == image(icons.icon(_icon_name(category), QColor(colour)))


def _tabs(interface: Context) -> dict[str, QIcon]:
	tabs = window(interface).ui.tabs
	index_dict = {}
	for index in range(tabs.count()):
		index_dict[tab_title(tabs, index)] = tabs.tabIcon(index)
	return index_dict


@then("les onglets portent les icônes :")
def tab_icons(interface: Context, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	scopes = _tabs(interface)
	icon_list = []
	for title, _icon in rows:
		icon_list.append(title.strip())
	assert list(scopes) == icon_list
	for title, name in rows:
		assert _scope(scopes[title.strip()]) == _expected(name.strip()), title


@then(parsers.parse("l'onglet « {title} » porte l'icône « {name} »"))
def tab_icon(interface: Context, title: str, name: str) -> None:
	assert _scope(_tabs(interface)[title]) == _expected(name)


@then(parsers.parse("les entrées du menu « {menu} » portent les icônes :"))
def menu_icons(interface: Context, menu: str, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	scopes = {}
	for action in actions(interface, menu):
		if not action.isSeparator():
			scopes[action.text()] = action.icon()
	for entry, name in rows:
		assert _scope(scopes[entry.strip()]) == _expected(name.strip()), entry


@then("les résultats de la recherche portent les icônes :")
def search_icons(interface: Context, qtbot: QtBot, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	(search,) = window(interface).findChildren(SearchScreen)
	model = search.table.model()
	qtbot.waitUntil(lambda: model.rowCount() == len(rows))
	for row, (category, name, icon) in enumerate(rows):
		type_ = model.index(row, 0)
		assert (type_.data(), model.index(row, 1).data()) == (category.strip(), name.strip())
		assert _scope(type_.data(Qt.ItemDataRole.DecorationRole)) == _expected(icon.strip()), category


@then("les relations de la fiche portent les icônes :")
def relation_icons(interface: Context, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	card = window(interface).ui.tabs.currentWidget()
	assert isinstance(card, SoundCard)
	table = card.ui.relations
	assert table.rowCount() == len(rows)
	for row, (category, name, icon) in enumerate(rows):
		category_cell, name_cell = table.item(row, 0), table.item(row, 1)
		assert (category_cell is not None) and (name_cell is not None)
		assert (category_cell.text(), name_cell.text()) == (category.strip(), name.strip())
		assert _scope(category_cell.icon()) == _expected(icon.strip()), category


@when(parsers.parse("je tape « {text} » dans le champ de recherche"))
def type_(interface: Context, text: str) -> None:
	(search,) = window(interface).findChildren(SearchScreen)
	search.field.setText(text)


@then("les boutons de l'onglet Antenne portent les icônes :")
def home_icons(interface: Context, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	ui = window(interface).home.ui
	for name, icon in rows:
		button = getattr(ui, name.strip())
		assert _scope(button.icon()) == _expected(icon.strip()), name


@then(
	parsers.re(
		r"le bouton « (?P<name>[^»]+) » de (?P<ou>la fiche ouverte|l'onglet Antenne|la fenêtre)"
		r" porte l'icône « (?P<icon>[^»]+) »"
	)
)
def button_icon(interface: Context, name: str, ou: str, icon: str) -> None:
	opened = window(interface)
	carrier: object = opened.ui
	if ou == "l'onglet Antenne":
		carrier = opened.home.ui
	if ou == "la fiche ouverte":
		carrier = opened.ui.tabs.currentWidget().ui
	assert _scope(getattr(carrier, name).icon()) == _expected(icon), name


@then("les icônes du thème des écrans sont seulement :")
def theme_icons(datatable: list[list[str]]) -> None:
	"""Chaque iconset theme des fichiers .ui, avec le widget qui le porte."""
	_headers, *rows = datatable
	found_list = []
	for file in sorted((Path(icons.__file__).parent / "ui").glob("*.ui")):
		for widget in ElementTree.parse(file).iter("widget"):
			for property_ in widget.findall("property[@name='icon']"):
				for iconset in property_.iter("iconset"):
					found_list.append([file.name, str(widget.get("name")), str(iconset.get("theme"))])
	row_list = []
	for row in rows:
		cell_list = []
		for cell in row:
			cell_list.append(cell.strip())
		row_list.append(cell_list)
	assert found_list == row_list
