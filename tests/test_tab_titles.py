"""Scénarios des titres des onglets et du menu « Onglets » (https://github.com/dascritch/machincast/issues/398)."""

from PySide6.QtGui import QAction
from pytest_bdd import parsers, scenarios, then, when

from tests.interface_steps import ON_AIR_INDICATOR, Context, named_menu, window

scenarios("tab_titles.feature")


def _tab_entries(interface: Context) -> list[QAction]:
	"""Les entrées du menu, telles qu'il les montre à son ouverture."""
	menu = named_menu(interface, "Onglets")
	menu.aboutToShow.emit()
	# Une entrée par onglet, cochable ; « Fermer tous les onglets fermables », à la fin, ne l'est pas.
	return [action for action in menu.actions() if action.isCheckable()]


def _title(action: QAction) -> str:
	"""Le titre, sans le raccourci qu'affiche le menu après une tabulation, ni le témoin de l'onglet Antenne."""
	title, _separator, _shortcut = action.text().partition("\t")
	return ON_AIR_INDICATOR.sub("", title.replace("&&", "&"))


@then(parsers.parse("l'onglet ouvert affiche « {text} »"))
def displayed(interface: Context, text: str) -> None:
	tabs = window(interface).ui.tabs
	assert tabs.tabText(tabs.currentIndex()) == text


@then(parsers.re(r"l'infobulle de l'onglet ouvert est « (?P<first>[^»]+) »(?:, puis « (?P<second>[^»]+) »)?"))
def tooltip(interface: Context, first: str, second: str | None) -> None:
	tabs = window(interface).ui.tabs
	if second is None:
		expected = first
	else:
		expected = f"{first}\n{second}"
	assert tabs.tabToolTip(tabs.currentIndex()) == expected


@then(parsers.parse("le menu « Onglets » liste :"))
def listed(interface: Context, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	fetched = [
		[
			_title(action),
			action.text().partition("\t")[2],
			"oui" if action.isChecked() else "non",
		]
		for action in _tab_entries(interface)
	]
	assert fetched == [[value.strip() for value in row] for row in rows]


@when(parsers.parse("je choisis l'onglet « {title} » dans le menu « Onglets »"))
def choose(interface: Context, title: str) -> None:
	(action,) = [action for action in _tab_entries(interface) if _title(action) == title]
	action.trigger()
