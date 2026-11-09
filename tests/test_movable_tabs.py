"""Scénarios des onglets déplaçables (https://github.com/dascritch/machincast/issues/405)."""

from pytest_bdd import parsers, scenarios, then, when

from tests.interface_steps import Context, tab_title, window

scenarios("movable_tabs.feature")


@when(parsers.parse("je déplace l'onglet « {title} » à la place {place:d}"))
def move(interface: Context, title: str, place: int) -> None:
	"""Comme la souris : la barre des onglets le déplace, et le signale (tabMoved)."""
	tabs = window(interface).ui.tabs
	(index,) = [index for index in range(tabs.count()) if tab_title(tabs, index) == title]
	tabs.tabBar().moveTab(index, place - 1)


@then("les onglets sont déplaçables")
def movable(interface: Context) -> None:
	assert window(interface).ui.tabs.isMovable()


@then(parsers.parse("l'onglet « {title} » a pour infobulle « {text} »"))
def tooltip(interface: Context, title: str, text: str) -> None:
	tabs = window(interface).ui.tabs
	(index,) = [index for index in range(tabs.count()) if tab_title(tabs, index) == title]
	assert tabs.tabToolTip(index) == text
