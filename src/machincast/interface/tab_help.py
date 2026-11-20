"""L'aide propre à l'onglet affiché (https://github.com/dascritch/machincast/issues/534).

Chaque genre d'onglet a sa page d'aide, en Markdown, dans doc/fr/utilisateur/aide : l'Antenne, chaque liste, chaque
fiche, la grille horaire, la simulation, l'airplay, la recherche et les incidents. Elle s'ouvre par « Aide sur … »
du menu « Aide », sur GitHub, à la version du code installé (machincast.interface.version.documentation), avec son
image annotée.

Chaque élément de l'écran y est une ligne numérotée, « 1. **Nom** (`nom_qt`) : ce qu'il fait. », le numéro étant
celui de l'image annotée, et nom_qt le nom de l'objet Qt du widget, ou son attribut dans l'écran. L'aide
contextuelle, F1, reprend ces lignes en infobulles : survoler un élément décrit montre son aide, cliquer dessus la
garde ouverte, sans agir. F1 de nouveau la désactive.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QHelpEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QToolTip, QWhatsThis, QWidget

from machincast.i18n import _

PAGES = Path(__file__).resolve().parents[3] / "doc" / "fr" / "utilisateur" / "aide"
"""Les pages d'aide, dans le dépôt de MachinCast installé."""
FOLDER = "doc/fr/utilisateur/aide"
"""Les pages d'aide, dans le dépôt de MachinCast sur GitHub."""
SHORTCUT = "F1"
CONTEXTUAL = _("Contextual help")
DISABLE_CONTEXTUAL = _("Disable contextual help")
ACTIVE = _("Contextual help: hover or click an element of the tab to read its help; F1 to leave it.")
ENTRY = re.compile(r"^\d+\. \*\*(?P<name>[^*]+)\*\* \(`(?P<widget>\w+)`\) : (?P<text>.+)$")
"""Une ligne d'une page d'aide : « 1. **Nom** (`nom_qt`) : ce qu'il fait. »"""


@dataclass(frozen=True)
class Kind:
	"""Un genre d'onglet : l'entrée du menu « Aide », et le nom de sa page, sans .md."""

	label: str
	page: str


KINDS = {
	"on_air": Kind(_("Help on the On air tab"), "antenne"),
	"list:sound": Kind(_("Help on the list of sounds"), "liste-sonores"),
	"list:bank": Kind(_("Help on the list of banks"), "liste-banques"),
	"list:sequence": Kind(_("Help on the list of sequences"), "liste-sequences"),
	"list:event": Kind(_("Help on the list of events"), "liste-evenements"),
	"list:feed": Kind(_("Help on the list of feeds"), "liste-feeds"),
	"card:sound": Kind(_("Help on the card of a sound"), "fiche-sonore"),
	"card:bank": Kind(_("Help on the card of a bank"), "fiche-banque"),
	"card:sequence": Kind(_("Help on the card of a sequence"), "fiche-sequence"),
	"card:event": Kind(_("Help on the card of an event"), "fiche-evenement"),
	"card:feed": Kind(_("Help on the card of a feed"), "fiche-feed"),
	"calendar": Kind(_("Help on the schedule"), "grille"),
	"simulation": Kind(_("Help on the simulation"), "simulation"),
	"airplay": Kind(_("Help on the Airplay tab"), "airplay"),
	"api": Kind(_("Help on the API tab"), "api"),
	"search": Kind(_("Help on the search"), "recherche"),
	"incidents": Kind(_("Help on the Incidents tab"), "incidents"),
}
"""Chaque genre d'onglet, par la clé de son onglet, sans ce qui distingue deux onglets du même genre."""
WITHOUT_HELP = _("Help on this tab")


def kind_of(key: str | None, category: str | None = None) -> str | None:
	"""Le genre d'un onglet, d'après sa clé (machincast.interface.tab_manager.TabManager.tab_key), ou, pour une
	fiche, d'après son genre d'élément, qu'elle soit enregistrée ou non."""
	if category is not None:
		return f"card:{category}"
	if key is None:
		return None
	if key.startswith("search:"):
		return "search"
	if key in KINDS:
		return key
	return None


def label(kind: str | None) -> str:
	"""L'entrée du menu « Aide » pour ce genre d'onglet."""
	if kind is None:
		return WITHOUT_HELP
	return KINDS[kind].label


def page(kind: str) -> Path:
	"""La page d'aide de ce genre d'onglet, dans le dépôt installé."""
	return PAGES / f"{KINDS[kind].page}.md"


def address(kind: str, documentation: str) -> str:
	"""L'adresse de la page d'aide, à la même version que celle de la documentation donnée."""
	base = documentation.split("/doc/", 1)[0]
	return f"{base}/{FOLDER}/{KINDS[kind].page}.md"


@dataclass(frozen=True)
class Entry:
	"""Un élément décrit par une page d'aide."""

	number: int
	name: str
	widget: str
	text: str


def entries(text: str) -> list[Entry]:
	"""Les éléments décrits par le texte d'une page d'aide, dans l'ordre de leur numéro."""
	found: list[Entry] = []
	for line in text.splitlines():
		match = ENTRY.match(line)
		if match is not None:
			found.append(Entry(len(found) + 1, match["name"], match["widget"], match["text"]))
	return found


def read(kind: str) -> list[Entry]:
	"""Les éléments décrits par la page d'aide de ce genre d'onglet ; aucun sans la page."""
	try:
		return entries(page(kind).read_text(encoding="utf-8"))
	except OSError:
		return []


def rich_text(entry: Entry) -> str:
	"""L'aide d'un élément, en texte riche de Qt : son nom en gras, et son texte sans la syntaxe de Markdown."""
	text = entry.text.replace("&", "&amp;").replace("<kbd>", "").replace("</kbd>", "")
	text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
	text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
	text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
	return f"<b>{entry.name}</b><br>{text}"


def widget_of(screen: QWidget, name: str) -> QWidget | None:
	"""Le widget d'un écran : par son nom d'objet Qt, ou par son attribut, dans l'écran ou dans son interface ui."""
	found = screen.findChild(QWidget, name)
	if found is not None:
		return found
	for owner in (screen, getattr(screen, "ui", None)):
		candidate = getattr(owner, name, None)
		if isinstance(candidate, QWidget):
			return candidate
	return None


def described(screen: QWidget, kind: str) -> dict[QWidget, Entry]:
	"""Les widgets de l'écran que décrit la page d'aide de son genre."""
	found: dict[QWidget, Entry] = {}
	for entry in read(kind):
		widget = widget_of(screen, entry.widget)
		if widget is not None:
			found[widget] = entry
	return found


class ContextualHelp(QObject):
	"""L'aide contextuelle : tant qu'elle est active, les éléments décrits de l'écran donnent leur aide au survol, et
	la gardent ouverte au clic, sans agir."""

	def __init__(self, parent: QObject) -> None:
		super().__init__(parent)
		self.active = False
		self.widgets: dict[QWidget, Entry] = {}
		self.shown: Entry | None = None
		"""L'aide montrée en dernier, pour les scénarios."""
		application = QApplication.instance()
		if application is not None:
			application.installEventFilter(self)

	def follow(self, screen: QWidget | None, kind: str | None) -> None:
		"""L'écran affiché, et son genre : ses éléments décrits."""
		self.widgets = {}
		if (screen is not None) and (kind is not None):
			self.widgets = described(screen, kind)

	def toggle(self) -> bool:
		"""Active ou désactive l'aide contextuelle ; dit si elle est active."""
		self.active = not self.active
		if not self.active:
			QWhatsThis.hideText()
			QToolTip.hideText()
		return self.active

	def entry_of(self, widget: QObject | None) -> tuple[QWidget, Entry] | None:
		"""L'élément décrit qui contient ce widget, s'il y en a un."""
		while isinstance(widget, QWidget):
			if widget in self.widgets:
				return widget, self.widgets[widget]
			widget = widget.parentWidget()
		return None

	def eventFilter(self, object_: QObject, event: QEvent) -> bool:
		"""Active, le survol d'un élément décrit montre son aide, et le clic la garde ouverte, sans le transmettre."""
		if not self.active:
			return False
		kind = event.type()
		if kind not in (QEvent.Type.ToolTip, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
			return False
		found = self.entry_of(object_)
		if found is None:
			return False
		widget, entry = found
		self.shown = entry
		if (kind == QEvent.Type.ToolTip) and (isinstance(event, QHelpEvent)):
			QToolTip.showText(event.globalPos(), rich_text(entry), widget)
			return True
		if isinstance(event, QMouseEvent):
			QWhatsThis.showText(event.globalPosition().toPoint(), rich_text(entry), widget)
		return True
