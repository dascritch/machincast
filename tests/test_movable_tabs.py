"""Scénarios des onglets déplaçables (https://github.com/dascritch/machincast/issues/405)."""

from PySide6.QtGui import QAction
from pytest_bdd import parsers, scenarios, then, when

from tests.interface_steps import Context, named_menu, tab_title, window

scenarios("movable_tabs.feature")


@when(parsers.parse("je déplace l'onglet « {title} » à la place {place:d}"))
def move(interface: Context, title: str, place: int) -> None:
	"""Comme la souris : la barre des onglets le déplace, et le signale (tabMoved)."""
	tabs = window(interface).ui.tabs
	index_list = []
	for rank in range(tabs.count()):
		if tab_title(tabs, rank) == title:
			index_list.append(rank)
	(index,) = index_list
	tabs.tabBar().moveTab(index, place - 1)


@then("les onglets sont déplaçables")
def movable(interface: Context) -> None:
	assert window(interface).ui.tabs.isMovable()


@then(parsers.parse("l'onglet « {title} » a pour infobulle « {text} »"))
def tooltip(interface: Context, title: str, text: str) -> None:
	tabs = window(interface).ui.tabs
	index_list = []
	for rank in range(tabs.count()):
		if tab_title(tabs, rank) == title:
			index_list.append(rank)
	(index,) = index_list
	assert tabs.tabToolTip(index) == text


CLOSE_ALL = "Fermer tous les onglets fermables"


def _close_all(interface: Context) -> QAction:
	"""La dernière entrée du menu, telle qu'il la montre à son ouverture, après un séparateur."""
	menu = named_menu(interface, "Onglets")
	menu.aboutToShow.emit()
	*_, separator, last = menu.actions()
	assert separator.isSeparator()
	assert last.text() == CLOSE_ALL
	return last


@then(
	parsers.re(
		r"le menu « Onglets » finit par un séparateur, puis « Fermer tous les onglets fermables », (?P<state>active|inactive)"
	)
)
def close_all_entry(interface: Context, state: str) -> None:
	assert _close_all(interface).isEnabled() == (state == "active")


@when("je ferme tous les onglets fermables par le menu « Onglets »")
def close_all(interface: Context) -> None:
	_close_all(interface).trigger()
