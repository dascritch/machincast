"""Les onglets de la fenêtre de Machin_interface (https://github.com/dascritch/machincast/issues/440).

TabManager tient les onglets : la clé de chacun d'un lancement à l'autre (tab_key) et les onglets retenus à la
fermeture, rouverts au lancement (https://github.com/dascritch/machincast/issues/321) ; leur ordre, que l'utilisateur
peut changer (https://github.com/dascritch/machincast/issues/405) ; leur titre, coupé au besoin, et l'infobulle de
leur raccourci (https://github.com/dascritch/machincast/issues/398) ; les raccourcis Maj+F1 à Maj+F12, Ctrl+PageUp,
Ctrl+PageDown, Ctrl+Home et Ctrl+End (https://github.com/dascritch/machincast/issues/192,
https://github.com/dascritch/machincast/issues/318) ; le menu « Onglets » ; Ctrl+W, Ctrl+S, Ctrl+Entrée, et les onglets
fermés, que Ctrl+Maj+T et le menu « Affichage » rouvrent (https://github.com/dascritch/machincast/issues/428). Ce que
la fenêtre sait seule, ouvrir un écran d'après sa clé, fermer ou retirer une fiche, lui est donné à la construction.
"""

import logging
from collections.abc import Callable

import psycopg
from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QAction, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QTabBar, QTabWidget, QWidget

from machincast.i18n import _
from machincast.interface import columns, icons, key_hints
from machincast.interface.airplay_tab import AirplayScreen
from machincast.interface.api_tab import ApiScreen
from machincast.interface.calendar import Calendar
from machincast.interface.card import Card
from machincast.interface.lists import List
from machincast.interface.search import SearchScreen
from machincast.interface.simulation import SimulationScreen

log = logging.getLogger(__name__)

ON_AIR = _("On air")
"""Le titre de l'onglet de l'écran par défaut, l'onglet Antenne."""
ON_DEMAND = frozenset({"sound", "feed"})
"""Les listes qui ne s'ouvrent pas au lancement, mais par le menu « Affichage », et qui se ferment
(https://github.com/dascritch/machincast/issues/180), par leur genre."""


OLD_TAB_KEYS = {
	"antenne": "on_air",
	"calendrier": "calendar",
	"recherche": "search:",
	"search": "search:",
	"liste:Événements": "list:event",
	"liste:Séquences": "list:sequence",
	"liste:Banques": "list:bank",
	"liste:Sonores": "list:sound",
	"liste:Feeds": "list:feed",
}
"""Les clés des onglets retenus avant https://github.com/dascritch/machincast/issues/368, en français, et leur clé
anglaise : les onglets retenus par une version d'avant se rouvrent. Une recherche, « search » avant
https://github.com/dascritch/machincast/issues/502, est « search: » suivi de son texte."""


OLD_CATEGORIES = {"sonore": "sound", "banque": "bank", "séquence": "sequence", "événement": "event"}
"""Les genres des fiches retenues avant https://github.com/dascritch/machincast/issues/368 : « fiche:banque:12 »."""


def current_tab_key(key: str) -> str:
	"""La clé d'un onglet retenu, celle d'une version d'avant traduite : « fiche:banque:12 » devient
	« card:bank:12 »."""
	if key.startswith("fiche:"):
		category, _separator, identifier = key.removeprefix("fiche:").partition(":")
		return f"card:{OLD_CATEGORIES.get(category, category)}:{identifier}"
	return OLD_TAB_KEYS.get(key, key)


TAB_KEY = "onglets/ouverts"


ACTIVE_TAB_KEY = "onglets/actif"
"""Les onglets ouverts, et l'onglet actif, dans les réglages des vues du compte
(https://github.com/dascritch/machincast/issues/321)."""


TAB_SHORTCUTS = 12
"""Les onglets qui ont un raccourci, Maj+F1 à Maj+F12 (https://github.com/dascritch/machincast/issues/192)."""


CLOSE_ALL = _("Close all closable tabs")
"""La dernière entrée du menu « Onglets » (https://github.com/dascritch/machincast/issues/405)."""


TAB_TITLE = 40
"""Longueur maximale du titre affiché d'un onglet ; au-delà, il est coupé, et son infobulle le donne en entier
(https://github.com/dascritch/machincast/issues/398)."""


def short_title(title: str) -> str:
	"""Le titre tel que l'onglet l'affiche : au plus TAB_TITLE caractères, « … » compris."""
	if len(title) <= TAB_TITLE:
		return title
	return f"{title[: TAB_TITLE - 1].rstrip()}…"


def screen_category(screen: QWidget) -> str:
	"""Le genre que montre un onglet, pour son icône (https://github.com/dascritch/machincast/issues/215) ; rien pour
	l'onglet Antenne, les incidents et la recherche."""
	if isinstance(screen, List):
		return screen.source.category
	if isinstance(screen, Card):
		return screen.category
	if isinstance(screen, Calendar):
		return "grid"
	if isinstance(screen, SimulationScreen):
		return "simulation"
	if isinstance(screen, AirplayScreen):
		return "airplay"
	if isinstance(screen, ApiScreen):
		return "api"
	return ""


LEFT_TAB, RIGHT_TAB, FIRST_TAB, LAST_TAB = "Ctrl+PgUp", "Ctrl+PgDown", "Ctrl+Home", "Ctrl+End"
"""Les raccourcis de l'onglet de gauche, de droite, du premier et du dernier
(https://github.com/dascritch/machincast/issues/318)."""


def _shortcut_texts(shortcuts: tuple[str, ...]) -> frozenset[str]:
	"""Les raccourcis, écrits comme Qt les écrit."""
	texts = set()
	for keys in shortcuts:
		texts.add(QKeySequence(keys).toString())
	return frozenset(texts)


TAB_KEYS = _shortcut_texts((LEFT_TAB, RIGHT_TAB, FIRST_TAB, LAST_TAB))


CLOSE_TAB, SAVE_TAB, REOPEN_TAB = "Ctrl+W", key_hints.SAVE, "Ctrl+Shift+T"
SAVE_AND_CLOSE_TAB = (key_hints.SAVE_AND_CLOSE, "Ctrl+Enter")
"""Les raccourcis qui ferment l'onglet ouvert, l'enregistrent, l'enregistrent puis le ferment (les deux touches
Entrée, du clavier principal et du pavé numérique), et rouvrent le dernier fermé
(https://github.com/dascritch/machincast/issues/428)."""


RECENTLY_CLOSED = 5
"""Les onglets fermés que le sous-menu « Onglets fermés récemment » propose de rouvrir, le plus récent en tête."""


REOPEN = _("Reopen the closed tab")
CLOSED_TABS = _("Recently closed tabs")
"""L'entrée de Ctrl+Maj+T et le sous-menu des onglets fermés, dans le menu « Affichage »."""


class TabKey(QObject):
	"""Les raccourcis des onglets l'emportent sur le widget de la fenêtre qui a le focus : un champ d'une ligne réclame
	Ctrl+Home et Ctrl+End sans rien en faire, un tableau irait à sa première ou à sa dernière ligne, et la barre
	d'onglets de Qt boucle d'un bout à l'autre (https://github.com/dascritch/machincast/issues/318). Le widget ne reçoit
	pas la demande de la touche, qui va au raccourci ; dans une autre fenêtre, sans ces raccourcis, la touche lui
	arrive quand même, comme une touche ordinaire. La fenêtre principale n'a pas de texte multiligne."""

	def eventFilter(self, object_: QObject, event: QEvent) -> bool:
		if (event.type() != QEvent.Type.ShortcutOverride) or (not isinstance(event, QKeyEvent)):
			return False
		return QKeySequence(event.keyCombination()).toString() in TAB_KEYS


def _shortcut_text(index: int) -> str:
	"""Le raccourci de l'onglet de ce rang, tel que l'écrit l'infobulle : Maj+F1 à Maj+F12."""
	return f"Maj+F{index + 1}"


class TabManager:
	"""Les onglets de la fenêtre : leur ordre, leurs titres, leurs raccourcis et ceux qu'on retient d'un lancement à
	l'autre."""

	def __init__(
		self,
		window: QMainWindow,
		tabs: QTabWidget,
		reopen_screen: Callable[[str], None],
		close_screen: Callable[[int], None],
		remove_card: Callable[[Card], None],
	) -> None:
		"""reopen_screen rouvre l'écran d'une clé retenue, close_screen ferme l'onglet de ce rang, remove_card ferme celui
		d'une fiche sans rien lui demander."""
		self.window = window
		self.tabs = tabs
		self.reopen_screen = reopen_screen
		self.close_screen = close_screen
		self.remove_card = remove_card
		self.appending = True
		"""Vrai pendant la construction de la fenêtre et la réouverture des onglets retenus : un onglet s'ajoute à la fin,
		au lieu de s'ouvrir à droite de l'onglet ouvert."""
		self.last_opened: dict[QWidget, QWidget] = {}
		"""Pour chaque onglet d'origine, le dernier onglet ouvert depuis lui : le suivant se range après lui, comme dans
		Firefox (https://github.com/dascritch/machincast/issues/405)."""
		self.fixed: dict[QWidget, str] = {}
		"""La clé de chaque onglet fixe, l'onglet Antenne, le calendrier et les incidents."""
		self.on_air: QWidget = tabs
		"""L'onglet Antenne, toujours le premier : fixé quand il est ajouté."""
		self.lists: list[List] = []
		self.titles: dict[QWidget, str] = {}
		"""Le titre de l'onglet de chaque liste, ouverte ou non."""
		self.keys: dict[QWidget, str] = {}
		"""La clé de l'onglet de chaque liste, dans les réglages : son genre."""
		self.closed: list[tuple[str, str, str]] = []
		"""Les onglets fermés, à rouvrir, le plus récent en tête : leur clé, leur titre entier et leur genre ; au plus
		RECENTLY_CLOSED, et jamais un onglet ouvert."""
		self.reopen_action: QAction | None = None
		self.closed_menu: QMenu | None = None

	def tab_key(self, screen: QWidget | None) -> str | None:
		"""Ce qui désigne un onglet d'un lancement à l'autre : « antenne », « liste:Feeds », « fiche:banque:12 »… ;
		None pour une fiche pas encore enregistrée, ou celle d'un élément supprimé, et sans onglet."""
		if screen is None:
			return None
		if isinstance(screen, Card):
			if (screen.identifier is None) or (screen.deleted_at is not None):
				return None
			return f"card:{screen.category}:{screen.identifier}"
		if isinstance(screen, List):
			return f"list:{self.keys[screen]}"
		if screen in self.fixed:
			return self.fixed[screen]
		if isinstance(screen, SearchScreen):
			return screen.key()
		for category, key in (
			(SimulationScreen, "simulation"),
			(AirplayScreen, "airplay"),
			(ApiScreen, "api"),
		):
			if isinstance(screen, category):
				return key
		return None

	def retain_tabs(self) -> None:
		"""Les onglets ouverts, dans leur ordre, et l'onglet actif, dans les réglages des vues du compte."""
		tabs = self.tabs
		keys = []
		for index in range(tabs.count()):
			keys.append(self.tab_key(tabs.widget(index)))
		settings = columns.settings()
		key_list = []
		for key in keys:
			if key is not None:
				key_list.append(key)
		settings.setValue(TAB_KEY, key_list)
		settings.setValue(ACTIVE_TAB_KEY, (self.tab_key(tabs.currentWidget())) or ("on_air"))

	def reopen_tabs(self) -> None:
		"""Les onglets retenus à la dernière fermeture, dans leur ordre, puis l'onglet actif ; une fiche dont l'élément
		n'est plus en base, ou est supprimé, est oubliée."""
		settings = columns.settings()
		retained = settings.value(TAB_KEY)
		if retained is None:
			return
		if not isinstance(retained, list):
			retained = [retained]
		for key in retained:
			try:
				self.reopen_screen(current_tab_key(str(key)))
			except psycopg.Error as error:
				log.error(_("tab “{key}” not reopened: {error}").format(key=key, error=error))
		key_list = []
		for key in retained:
			key_list.append(current_tab_key(str(key)))
		self._order_tabs(key_list)
		tabs = self.tabs
		active = current_tab_key(str(settings.value(ACTIVE_TAB_KEY, "on_air")))
		found_list = []
		for index in range(tabs.count()):
			if self.tab_key(tabs.widget(index)) == active:
				found_list.append(index)
		tabs.setCurrentIndex(next(iter(found_list), 0))

	def _order_tabs(self, order: list[str]) -> None:
		"""Les onglets retenus reprennent l'ordre retenu, onglets fixes compris, qui ont pu être déplacés
		(https://github.com/dascritch/machincast/issues/405) : ils échangent leurs places entre eux, et un onglet absent
		de l'ordre retenu, celui d'une version d'avant, garde la sienne. L'onglet Antenne reste le premier."""
		tabs = self.tabs
		screens = []
		for index in range(tabs.count()):
			if (screen := tabs.widget(index)) is not None:
				screens.append(screen)
		# Plusieurs onglets peuvent avoir la même clé, deux recherches du même texte
		# (https://github.com/dascritch/machincast/issues/502) : chacun prend la place suivante de sa clé.
		by_key: dict[str | None, list[QWidget]] = {}
		for keyed in screens:
			by_key.setdefault(self.tab_key(keyed), []).append(keyed)
		key_list = []
		for key in order:
			if by_key.get(key):
				key_list.append(by_key[key].pop(0))
		placed = set(key_list)
		retained = iter(key_list)
		wanted: list[QWidget] = []
		for screen in screens:
			if screen in placed:
				screen = next(retained)
			wanted.append(screen)
		for index, screen in enumerate(wanted):
			tabs.tabBar().moveTab(tabs.indexOf(screen), index)

	def add_fixed(self, screen: QWidget, title: str, key: str | None = None) -> None:
		"""Un onglet sans bouton de fermeture ; key le désigne d'un lancement à l'autre, sauf une liste, qui a celle de son
		genre."""
		if key is not None:
			self.fixed[screen] = key
		if key == "on_air":
			self.on_air = screen
		index = self.add_tab(screen, title)
		for side in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
			self.tabs.tabBar().setTabButton(index, side, None)

	def add_tab(self, screen: QWidget, title: str) -> int:
		"""Tout onglet s'ajoute par ici, et se retire par _remove_tab : les raccourcis suivent. Il s'ouvre à droite de
		l'onglet d'où il est ouvert, l'onglet ouvert à cet instant, après ceux déjà ouverts depuis lui, comme dans
		Firefox (https://github.com/dascritch/machincast/issues/405) ; à la fin, pendant la construction de la fenêtre et
		la réouverture des onglets retenus."""
		tabs = self.tabs
		icon = icons.icon_of(screen_category(screen))
		if self.appending:
			index = tabs.addTab(screen, icon, title)
		else:
			origin = tabs.currentWidget()
			index = tabs.insertTab(self._place_from(origin), screen, icon, title)
			self._note_opening(origin, screen)
		self.title_tab(index, title)
		self._forget(self.tab_key(screen))
		return index

	def _place_from(self, origin: QWidget | None) -> int:
		"""La place d'un onglet ouvert depuis origin : après le dernier onglet ouvert depuis lui, s'il est encore ouvert
		et à sa droite, sinon directement à sa droite. origin retient ce nouvel onglet ; un onglet sans origine va à la
		fin."""
		tabs = self.tabs
		if origin is None:
			return tabs.count()
		place = tabs.indexOf(origin) + 1
		last = self.last_opened.get(origin)
		if (last is not None) and (tabs.indexOf(last) >= place):
			place = tabs.indexOf(last) + 1
		return place

	def _note_opening(self, origin: QWidget | None, screen: QWidget) -> None:
		if origin is not None:
			self.last_opened[origin] = screen

	def moved_tab(self, _from: int, _to: int) -> None:
		"""Un onglet déplacé : l'onglet Antenne revient en tête, Maj+F1 et Ctrl+Home y mènent toujours ; les raccourcis
		et les infobulles suivent le nouvel ordre (https://github.com/dascritch/machincast/issues/405)."""
		bar = self.tabs.tabBar()
		on_air = self.tabs.indexOf(self.on_air)
		if on_air > 0:
			bar.moveTab(on_air, 0)
			return
		self._number_tabs()

	def title_tab(self, index: int, title: str) -> None:
		"""Le titre affiché, coupé à TAB_TITLE caractères ; le titre entier reste dans l'onglet, pour son infobulle et
		le menu « Onglets » (https://github.com/dascritch/machincast/issues/398)."""
		tabs = self.tabs
		tabs.setTabText(index, short_title(title))
		tabs.tabBar().setTabData(index, title)
		self._number_tabs()

	def full_title(self, index: int) -> str:
		"""Le titre entier de l'onglet."""
		title = self.tabs.tabBar().tabData(index)
		if isinstance(title, str):
			return title
		return self.tabs.tabText(index)

	def list_tabs(self, menu: QMenu) -> None:
		"""Le menu « Onglets » : les onglets ouverts, dans leur ordre, avec leur titre entier et leur raccourci ;
		l'onglet ouvert est coché (https://github.com/dascritch/machincast/issues/398). Le raccourci s'affiche après
		une tabulation, sans être celui de l'entrée : Maj+F1 à Maj+F12 restent ceux de la fenêtre."""
		tabs = self.tabs
		menu.clear()
		for index in range(tabs.count()):
			text = self.full_title(index).replace("&", "&&")
			if index < TAB_SHORTCUTS:
				text = f"{text}\t{_shortcut_text(index)}"
			action = menu.addAction(tabs.tabIcon(index), text)
			action.setCheckable(True)
			action.setChecked(index == tabs.currentIndex())
			widget = tabs.widget(index)
			action.triggered.connect(lambda _ticked=False, widget=widget: tabs.setCurrentWidget(widget))
		# Tout à la fin (https://github.com/dascritch/machincast/issues/405).
		menu.addSeparator()
		close_all = menu.addAction(CLOSE_ALL)
		close_all.setEnabled(self._closable() != [])
		close_all.triggered.connect(self.close_closable)

	def _closable(self) -> list[QWidget]:
		"""Les onglets qui se ferment, dans leur ordre : fiches, listes à la demande, recherche, simulation et airplay ;
		jamais les onglets fixes."""
		tabs = self.tabs
		found: list[QWidget] = []
		for index in range(tabs.count()):
			screen = tabs.widget(index)
			closing = isinstance(screen, (Card, SearchScreen, SimulationScreen, AirplayScreen, ApiScreen))
			on_demand = (isinstance(screen, List)) and (self.keys[screen] in ON_DEMAND)
			if (screen is not None) and ((closing) or (on_demand)):
				found.append(screen)
		return found

	def close_closable(self) -> None:
		"""Ferme tous les onglets fermables, de gauche à droite ; une fiche modifiée pose la question de sa fermeture,
		et « Annuler » arrête là : elle et les suivantes restent ouvertes
		(https://github.com/dascritch/machincast/issues/405)."""
		tabs = self.tabs
		for screen in self._closable():
			if isinstance(screen, Card):
				if not screen.can_close():
					return
				self.remove_card(screen)
			else:
				self.close_screen(tabs.indexOf(screen))

	def remove_tab(self, index: int, *, remembered: bool = True) -> None:
		"""Un onglet fermé n'est plus ni l'origine ni le dernier ouvert d'aucun autre. S'il se rouvre, il est retenu parmi
		les onglets fermés, sauf remembered faux : la fiche d'un élément supprimé."""
		screen = self.tabs.widget(index)
		key = self.tab_key(screen)
		if (remembered) and (key is not None) and (screen in self._closable()):
			self._forget(key)
			self.closed.insert(0, (key, self.full_title(index), screen_category(screen)))
			del self.closed[RECENTLY_CLOSED:]
			self._show_closed()
		last_dict = {}
		for origin, last in self.last_opened.items():
			if screen not in (origin, last):
				last_dict[origin] = last
		self.last_opened = last_dict
		self.tabs.removeTab(index)
		self._number_tabs()

	def create_shortcuts(self) -> None:
		"""Maj+F1 à Maj+F12 : les 12 premiers onglets, selon leur rang
		(https://github.com/dascritch/machincast/issues/192) ; Ctrl+PageUp, Ctrl+PageDown, Ctrl+Home et Ctrl+End :
		l'onglet de gauche, de droite, le premier et le dernier (https://github.com/dascritch/machincast/issues/318)."""
		for rank in range(TAB_SHORTCUTS):
			shortcut = QShortcut(QKeySequence(f"Shift+F{rank + 1}"), self.window)
			shortcut.activated.connect(lambda rank=rank: self._go_to_tab(rank))
		# Ctrl+PageUp et Ctrl+PageDown à gauche et à droite, sans boucler, comme le ferait Qt ; Ctrl+Home et Ctrl+End au
		# premier et au dernier onglet (https://github.com/dascritch/machincast/issues/318). Raccourcis de la fenêtre,
		# ils valent quel que soit le widget qui a le focus, sauf celui qui se sert de la touche.
		for keys, relocation in (
			(LEFT_TAB, self._left_tab),
			(RIGHT_TAB, self._right_tab),
			(FIRST_TAB, lambda: self._go_to_tab(0)),
			(LAST_TAB, lambda: self._go_to_tab(self.tabs.count() - 1)),
		):
			QShortcut(QKeySequence(keys), self.window).activated.connect(relocation)
		# Fermer et enregistrer l'onglet ouvert (https://github.com/dascritch/machincast/issues/428).
		QShortcut(QKeySequence(CLOSE_TAB), self.window).activated.connect(self.close_current)
		QShortcut(QKeySequence(SAVE_TAB), self.window).activated.connect(self.save_current)
		for keys in SAVE_AND_CLOSE_TAB:
			QShortcut(QKeySequence(keys), self.window).activated.connect(self.save_and_close_current)
		# https://github.com/dascritch/machincast/issues/529
		QShortcut(QKeySequence(key_hints.CANCEL_AND_CLOSE), self.window).activated.connect(
			self.cancel_and_close_current
		)
		application = QApplication.instance()
		if application is not None:
			application.installEventFilter(TabKey(self.window))

	def close_current(self) -> None:
		"""Ctrl+W : ferme l'onglet ouvert, comme son bouton de fermeture ; un onglet fixe reste ouvert."""
		screen = self.tabs.currentWidget()
		if (screen is not None) and (screen in self._closable()):
			self.close_screen(self.tabs.indexOf(screen))

	def save_current(self) -> None:
		"""Ctrl+S : enregistre la fiche ouverte, qui reste ouverte ; sur une fiche sans modification, ou un autre
		onglet, rien."""
		screen = self.tabs.currentWidget()
		if (isinstance(screen, Card)) and (screen.button_save.isEnabled()):
			screen.save()

	def save_and_close_current(self) -> None:
		"""Ctrl+Entrée : enregistre la fiche ouverte, puis la ferme ; une fiche sans modification se ferme, une fiche
		refusée reste ouverte et dit pourquoi. Sur un autre onglet, rien."""
		screen = self.tabs.currentWidget()
		if not isinstance(screen, Card):
			return
		if (not screen.button_save.isEnabled()) or (screen.save()):
			self.remove_card(screen)

	def cancel_and_close_current(self) -> None:
		"""Ctrl+Échap : ferme la fiche ouverte sans rien enregistrer ni rien demander, ses modifications perdues
		(https://github.com/dascritch/machincast/issues/529). Sur un autre onglet, rien."""
		screen = self.tabs.currentWidget()
		if isinstance(screen, Card):
			self.remove_card(screen)

	def add_reopening(self, menu: QMenu) -> None:
		"""Dans le menu « Affichage » : « Rouvrir l'onglet fermé », Ctrl+Maj+T, et le sous-menu des onglets fermés, relu
		à chaque ouverture ; inactifs tant qu'aucun onglet n'est à rouvrir."""
		self.reopen_action = menu.addAction(REOPEN)
		self.reopen_action.setShortcut(QKeySequence(REOPEN_TAB))
		self.reopen_action.triggered.connect(self.reopen_last)
		self.closed_menu = menu.addMenu(CLOSED_TABS)
		self.closed_menu.aboutToShow.connect(self._list_closed)
		self._show_closed()

	def reopen_last(self) -> None:
		"""Ctrl+Maj+T : rouvre le dernier onglet fermé ; sans onglet fermé, rien."""
		if self.closed:
			self._reopen_closed(self.closed[0][0])

	def _reopen_closed(self, key: str) -> None:
		"""Rouvre un onglet fermé, qui quitte la liste ; la fiche d'un élément supprimé depuis ne se rouvre pas."""
		self._forget(key)
		try:
			self.reopen_screen(key)
		except psycopg.Error as error:
			log.error(_("tab “{key}” not reopened: {error}").format(key=key, error=error))

	def _forget(self, key: str | None) -> None:
		"""Un onglet ouvert, ou rouvert, n'est plus à rouvrir."""
		kept_list = []
		for closed in self.closed:
			if closed[0] != key:
				kept_list.append(closed)
		if len(kept_list) != len(self.closed):
			self.closed = kept_list
			self._show_closed()

	def _show_closed(self) -> None:
		if (self.reopen_action is None) or (self.closed_menu is None):
			return
		self.reopen_action.setEnabled(self.closed != [])
		self.closed_menu.menuAction().setEnabled(self.closed != [])

	def _list_closed(self) -> None:
		"""Le sous-menu des onglets fermés : leur titre entier et leur icône, le plus récent en tête."""
		menu = self.closed_menu
		assert menu is not None
		menu.clear()
		for key, title, category in self.closed:
			action = menu.addAction(icons.icon_of(category), title.replace("&", "&&"))
			action.triggered.connect(lambda _ticked=False, key=key: self._reopen_closed(key))

	def _left_tab(self) -> None:
		"""Sur le premier onglet, rien : il n'y a pas d'onglet -1."""
		self._go_to_tab(self.tabs.currentIndex() - 1)

	def _right_tab(self) -> None:
		"""Sur le dernier onglet, rien : il n'y a pas d'onglet après lui."""
		self._go_to_tab(self.tabs.currentIndex() + 1)

	def _go_to_tab(self, rank: int) -> None:
		"""Un rang sans onglet ne change rien : Qt ignore l'indice."""
		self.tabs.setCurrentIndex(rank)

	def _number_tabs(self) -> None:
		"""L'infobulle de chaque onglet donne son raccourci ; au-delà des 12 premiers, il n'en a pas. Au-dessus, celle
		d'un titre coupé le donne en entier (https://github.com/dascritch/machincast/issues/398)."""
		tabs = self.tabs
		for index in range(tabs.count()):
			lines = []
			title = self.full_title(index)
			if short_title(title) != title:
				lines.append(title)
			if index < TAB_SHORTCUTS:
				lines.append(_shortcut_text(index))
			tabs.setTabToolTip(index, "\n".join(lines))

	def open_list(self, title: str) -> None:
		"""Ouvre une liste à la demande à droite de l'onglet ouvert, comme tout onglet
		(https://github.com/dascritch/machincast/issues/405), ou la ramène au premier plan
		(https://github.com/dascritch/machincast/issues/180). Elle se désigne par son titre, ou par son genre."""
		tabs = self.tabs
		titled = []
		for candidate in self.lists:
			if title in (self.titles[candidate], self.keys[candidate]):
				titled.append(candidate)
		(list_,) = titled
		index = tabs.indexOf(list_)
		if index < 0:
			index = self.add_tab(list_, self.titles[list_])
		tabs.setCurrentIndex(index)
