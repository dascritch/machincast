"""Scénarios de l'aide propre à l'onglet affiché (https://github.com/dascritch/machincast/issues/534).

Les pages d'aide sont celles du dépôt : chaque élément qu'elles nomment doit se trouver dans l'onglet de leur genre,
pour que l'aide contextuelle le trouve.
"""

from pathlib import Path

from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.interface import tab_help, version
from machincast.interface.tab_manager import ON_AIR
from tests.interface_steps import Context, tab_title, window

scenarios("tab_help.feature")

CAPTURES = Path(__file__).resolve().parents[1] / "doc" / "fr" / "captures" / "aide"
LISTS = {
	"list:sound": "Sonores",
	"list:bank": "Banques",
	"list:sequence": "Séquences",
	"list:event": "Événements",
	"list:feed": "Feeds",
}


@given("MachinCast installé hors d'un dépôt git")
def outside_drop(interface: Context) -> None:
	interface.monkeypatch.setattr(version, "DROP", interface.directory)


@when(parsers.parse("j'affiche un onglet de genre « {kind} »"))
def show_kind(interface: Context, kind: str) -> None:
	"""L'onglet de ce genre, ouvert comme le ferait l'utilisateur ; une fiche, vide."""
	opened = window(interface)
	if kind.startswith("card:"):
		opened._open_card(kind.removeprefix("card:"), None)
		return
	if kind in LISTS:
		opened.tab_manager.open_list(LISTS[kind])
		return
	openings = {
		"calendar": opened._open_calendar,
		"simulation": opened._open_simulation,
		"airplay": opened._open_airplay,
		"search": opened._open_search,
	}
	if kind in openings:
		openings[kind]()
		return
	tabs = opened.ui.tabs
	titles = {"on_air": ON_AIR, "incidents": "Incidents"}
	for index in range(tabs.count()):
		if tab_title(tabs, index) == titles[kind]:
			tabs.setCurrentIndex(index)


@then(parsers.parse("la page d'aide « {page} » décrit au moins {count:d} éléments, tous dans l'onglet affiché"))
def described(interface: Context, page: str, count: int) -> None:
	path = tab_help.PAGES / f"{page}.md"
	entries = tab_help.entries(path.read_text(encoding="utf-8"))
	assert len(entries) >= count, entries
	screen = window(interface).ui.tabs.currentWidget()
	assert screen is not None
	missing = []
	for entry in entries:
		if tab_help.widget_of(screen, entry.widget) is None:
			missing.append(entry.widget)
	assert missing == [], missing


@then(parsers.parse("l'image annotée de la page d'aide « {page} » existe"))
def annotated(page: str) -> None:
	assert (CAPTURES / f"{page}.png").is_file(), page
	text = (tab_help.PAGES / f"{page}.md").read_text(encoding="utf-8")
	assert f"(../../captures/aide/{page}.png)" in text


@when(parsers.parse("je survole le champ « {name} » de l'onglet affiché"))
def hover(interface: Context, name: str) -> None:
	screen = window(interface).ui.tabs.currentWidget()
	assert screen is not None
	widget = tab_help.widget_of(screen, name)
	assert widget is not None, name
	event = QHelpEvent(QEvent.Type.ToolTip, QPoint(2, 2), widget.mapToGlobal(QPoint(2, 2)))
	QApplication.sendEvent(widget, event)


@then(parsers.parse("l'aide contextuelle a montré « {name} » : « {text} »"))
def shown(interface: Context, name: str, text: str) -> None:
	entry = window(interface).contextual_help.shown
	assert entry is not None
	assert entry.name == name
	assert tab_help.rich_text(entry) == f"<b>{name}</b><br>{text}"


@then("l'aide contextuelle n'a rien montré")
def nothing_shown(interface: Context) -> None:
	assert window(interface).contextual_help.shown is None


def _titles(interface: Context) -> list[str]:
	tabs = window(interface).ui.tabs
	titles = []
	for index in range(tabs.count()):
		titles.append(tab_title(tabs, index))
	return titles


@then(parsers.parse("aucun onglet « {title} » n'est ouvert"))
def not_opened(interface: Context, title: str) -> None:
	assert title not in _titles(interface)


@then(parsers.parse("l'onglet « {title} » est ouvert"))
def opened_tab(interface: Context, title: str) -> None:
	assert title in _titles(interface)
