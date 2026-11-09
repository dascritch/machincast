"""Fenêtre de Machin_interface (https://github.com/dascritch/machincast/issues/26).

Un onglet par écran : l'onglet Antenne (écran par défaut, ouvert au lancement), le calendrier de la grille, onglet fixe
(https://github.com/dascritch/machincast/issues/307), puis une liste par type d'élément, dans
l'ordre de la recherche (spec § 8.2) : événements, séquences, banques, sonores, feeds. Les listes des sonores
et des feeds ne s'ouvrent qu'à la demande, par le menu « Affichage », à leur place parmi les autres, et se
ferment (https://github.com/dascritch/machincast/issues/180) ; les autres onglets fixes ne se ferment pas. Une liste
fermée est gardée : rouverte, elle retrouve son filtre et son tri. Une liste se relit chaque fois que son onglet
s'ouvre. Ouvrir une ligne demande l'écran de détail de l'élément (requested_detail).

L'écran de détail d'un élément est sa fiche, dans un onglet qui se ferme : événement
(machincast.interface.event_card, https://github.com/dascritch/machincast/issues/32), séquence
(machincast.interface.sequence_card, https://github.com/dascritch/machincast/issues/112), banque
(machincast.interface.bank_card, https://github.com/dascritch/machincast/issues/31) ou sonore
(machincast.interface.sound_card, https://github.com/dascritch/machincast/issues/28). Une fiche déjà ouverte
revient au premier plan. Un élément cité par une fiche s'ouvre comme une ligne de liste. Une fiche modifiée demande
quoi faire de ses modifications avant de se fermer, avec son onglet ou avec la fenêtre.

Le dernier onglet fixe est l'écran des incidents du log (machincast.interface.incidents,
https://github.com/dascritch/machincast/issues/35), qui se relit aussi à l'ouverture de son onglet.

Les onglets ouverts sont retenus d'un lancement à l'autre (https://github.com/dascritch/machincast/issues/321) : à la
fermeture, les réglages des vues du compte (machincast.interface.columns) gardent les onglets ouverts dans leur ordre,
fiches comprises, et l'onglet actif, chacun par sa clé (tab_key) ; au lancement, la fenêtre les rouvre
(reopen_tabs). Une fiche dont l'élément n'est plus en base, ou est supprimé, est oubliée, sans question ; une
fiche pas encore enregistrée, ou celle d'un élément supprimé, n'est pas retenue.

La barre de menus a cinq menus (https://github.com/dascritch/machincast/issues/117) : « Fichier », pour quitter (Alt+Q,
comme la fermeture de la fenêtre) ; « Affichage », pour ouvrir les listes des sonores et des feeds, dans des onglets
qui se ferment, ramener au premier plan le calendrier de la grille, « Grille horaire » (machincast.interface.calendar,
https://github.com/dascritch/machincast/issues/36), et pour rafraîchir les onglets (F5,
https://github.com/dascritch/machincast/issues/148) ; « Diffusion », qui lance ou arrête l'écoute de l'antenne (Alt+P,
https://github.com/dascritch/machincast/issues/256), et démarre, arrête ou redémarre le service de
diffusion (machincast.interface.control, https://github.com/dascritch/machincast/issues/25) selon son état, relu à
l'ouverture du menu ; sans le service, la barre d'état dit que l'installation n'est pas définitive, et le menu pilote
une diffusion d'essai ; « Maintenance », qui lance l'indexation rapide ou l'audit complet
(https://github.com/dascritch/machincast/issues/38) dans un processus à part, avec la fenêtre de son journal
(machincast.interface.indexer, https://github.com/dascritch/machincast/issues/120) : fermer l'interface ne l'arrête
pas ; « Aide », pour lire la documentation, signaler un problème et connaître la version (machincast.interface.version).
Une fonction pas encore écrite a son entrée, inactive, dont l'infobulle donne le ticket.

Les fichiers ajoutés depuis la liste des sonores entrent en base (machincast.interface.adding), puis l'indexeur les
vérifie en tâche de fond (machincast.interface.check, https://github.com/dascritch/machincast/issues/30) ; la
barre d'état annonce l'un et l'autre.
"""

import dataclasses
import logging
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QEvent, QObject, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMenu, QTabBar, QWidget

from machincast import service, shortcut
from machincast.clock import Clock
from machincast.configuration import (
	RETENTION,
	Audio,
	Crossfades,
	DeadAirSettings,
	Interface,
	InvalidConfiguration,
	Metadata,
	Silences,
	load,
)
from machincast.i18n import _
from machincast.interface import (
	columns,
	control,
	dialogs,
	display,
	groups,
	icons,
	indexer,
	interruption,
	preferences,
	suggestions,
	version,
)
from machincast.interface.adding import add_files
from machincast.interface.airplay_tab import WITHOUT_METADATA, AirplayScreen
from machincast.interface.application import identify
from machincast.interface.background_programming import guarantee
from machincast.interface.bank_card import BankCard
from machincast.interface.calendar import ONE_HOUR, Calendar, long_date
from machincast.interface.card import Card, Refreshed
from machincast.interface.check import Checker, FullCheck
from machincast.interface.default_screen import DefaultScreen
from machincast.interface.event_card import EventCard
from machincast.interface.feed_card import FeedCard
from machincast.interface.incidents import IncidentScreen
from machincast.interface.indexer import FINISHED, LAUNCHED, TITLES
from machincast.interface.lists import BANKS, EVENTS, FEEDS, SEQUENCES, SOUNDS, List
from machincast.interface.preview import PreviewWindow
from machincast.interface.search import SearchScreen
from machincast.interface.sequence_card import SequenceCard
from machincast.interface.simulation import SimulationScreen
from machincast.interface.sound_card import SoundCard
from machincast.interface.state import STOP, PlaybackState
from machincast.interface.ui.main_window import Ui_MainWindow
from machincast.player.state import (
	advance_request,
	cutoff_request_by_fallback,
	cutoff_request_by_feed,
	interruption_request,
	request_reread_grid,
)

log = logging.getLogger(__name__)

TABS = (
	(_("Events"), EVENTS),
	(_("Sequences"), SEQUENCES),
	(_("Banks"), BANKS),
	(_("Sounds"), SOUNDS),
	(_("Feeds"), FEEDS),
)
ON_DEMAND = frozenset({"sound", "feed"})
"""Les listes qui ne s'ouvrent pas au lancement, mais par le menu « Affichage », et qui se ferment
(https://github.com/dascritch/machincast/issues/180), par leur genre."""
OLD_TAB_KEYS = {
	"antenne": "on_air",
	"calendrier": "calendar",
	"recherche": "search",
	"liste:Événements": "list:event",
	"liste:Séquences": "list:sequence",
	"liste:Banques": "list:bank",
	"liste:Sonores": "list:sound",
	"liste:Feeds": "list:feed",
}
"""Les clés des onglets retenus avant https://github.com/dascritch/machincast/issues/368, en français, et leur clé
anglaise : les onglets retenus par une version d'avant se rouvrent."""
OLD_CATEGORIES = {"sonore": "sound", "banque": "bank", "séquence": "sequence", "événement": "event"}
"""Les genres des fiches retenues avant https://github.com/dascritch/machincast/issues/368 : « fiche:banque:12 »."""


def current_tab_key(key: str) -> str:
	"""La clé d'un onglet retenu, celle d'une version d'avant traduite : « fiche:banque:12 » devient
	« card:bank:12 »."""
	if key.startswith("fiche:"):
		category, _separator, identifier = key.removeprefix("fiche:").partition(":")
		return f"card:{OLD_CATEGORIES.get(category, category)}:{identifier}"
	return OLD_TAB_KEYS.get(key, key)


CARDS: dict[str, type[Card]] = {
	card.category: card for card in (EventCard, SequenceCard, BankCard, SoundCard, FeedCard)
}
"""Écrans de détail : les fiches, par genre."""
INDEXING_TRACKING = 1000
"""Millisecondes entre deux regards sur le processus de l'indexation lancée depuis le menu."""
TICKETS = "https://github.com/dascritch/machincast/issues"
"""Les tickets de MachinCast, qu'ouvre « Signaler un problème… » ; comme dans pyproject.toml."""
ON_AIR = _("On air")
TAB_KEY = "onglets/ouverts"
ACTIVE_TAB_KEY = "onglets/actif"
"""Les onglets ouverts, et l'onglet actif, dans les réglages des vues du compte
(https://github.com/dascritch/machincast/issues/321)."""
CARD_TABLES = {
	"sound": "sounds",
	"bank": "banks",
	"sequence": "sequences",
	"event": "events",
	"feed": "feeds",
}
DELETABLE = frozenset({"sounds", "banks", "sequences", "events"})
"""Les tables dont un élément peut être supprimé sans être effacé de la base (deleted_at)."""
"""L'onglet de l'écran par défaut, l'onglet Antenne, qui suit l'antenne (https://github.com/dascritch/machincast/issues/322)."""
INCOMPLETE_SERVICE, INSTALLED_SERVICE = "🟩", "🟥"
"""Le témoin du service de diffusion, devant le titre de l'onglet Antenne : pas complètement installé, ou installé."""
STOPPED_BROADCAST = _("🔇 Broadcast stopped")
WITHOUT_SERVICE = _("Non-final installation: broadcast without a service")
"""Ce que montre la barre d'état tant que le service n'est pas installé (https://github.com/dascritch/machincast/issues/25)."""
INSTALL_SERVICE = _(
	"The broadcast does not start with the computer, and does not restart by itself after a "
	"crash. On a computer dedicated to the on-air output, install the service: ./install.sh "
	"--service (INSTALL.md, Broadcast service)."
)
WITHOUT_SERVICE_START = _("Without a service: Machin player in a terminal window")
WITHOUT_TRIAL = _("No trial broadcast running")
TRIAL_HALT = _("Without a service: stops the Machin player launched by hand, like Ctrl-C")
TO_FILL_IN_ON_AIR = _("On-air device to fill in")
SET_ON_AIR = _(
	"Machin player refuses to broadcast without it: choose it in File → Preferences…, Audio "
	"page, or give it in audio.device of the configuration file."
)
ALREADY_RUNNING = _("The trial broadcast is already running")
LISTENING = {
	False: (_("On-air pre-listen"), _("Listen to the on-air output on the pre-listen output, at once")),
	True: (_("Stop the on-air pre-listen"), _("Stop listening to the on-air output on the pre-listen output")),
}
"""L'entrée d'écoute de l'antenne du menu « Diffusion », et son infobulle, selon que l'antenne s'écoute
(https://github.com/dascritch/machincast/issues/256)."""

TAB_SHORTCUTS = 12
"""Les onglets qui ont un raccourci, Maj+F1 à Maj+F12 (https://github.com/dascritch/machincast/issues/192)."""
ADDITION_TO_BANKS = _("The chosen sounds are added at the end of each bank.")
"""Remarque du choix des banques où ajouter des sonores (https://github.com/dascritch/machincast/issues/114)."""
BANK_REMOVAL = _("Only the banks containing one of the chosen sounds are offered.")
"""Remarque du choix des banques d'où retirer des sonores."""


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
	return ""


LEFT_TAB, RIGHT_TAB, FIRST_TAB, LAST_TAB = "Ctrl+PgUp", "Ctrl+PgDown", "Ctrl+Home", "Ctrl+End"
"""Les raccourcis de l'onglet de gauche, de droite, du premier et du dernier
(https://github.com/dascritch/machincast/issues/318)."""
TAB_KEYS = frozenset(QKeySequence(keys).toString() for keys in (LEFT_TAB, RIGHT_TAB, FIRST_TAB, LAST_TAB))


class TabKey(QObject):
	"""Les raccourcis des onglets l'emportent sur le widget de la fenêtre qui a le focus : un champ d'une ligne réclame
	Ctrl+Home et Ctrl+End sans rien en faire, un tableau irait à sa première ou à sa dernière ligne, et la barre
	d'onglets de Qt boucle d'un bout à l'autre (https://github.com/dascritch/machincast/issues/318). Le widget ne reçoit
	pas la demande de la touche, qui va au raccourci ; dans une autre fenêtre, sans ces raccourcis, la touche lui
	arrive quand même, comme une touche ordinaire. La fenêtre principale n'a pas de texte multiligne."""

	def eventFilter(self, object_: QObject, event: QEvent) -> bool:  # noqa: N802 : nom imposé par Qt
		if (event.type() != QEvent.Type.ShortcutOverride) or (not isinstance(event, QKeyEvent)):
			return False
		return QKeySequence(event.keyCombination()).toString() in TAB_KEYS


class MainWindow(QMainWindow):
	requested_detail = Signal(str, int)
	"""Écran de détail demandé : genre et identifiant de l'élément."""

	def __init__(
		self,
		connection: psycopg.Connection[TupleRow],
		state_socket: Path,
		clock: Clock,
		parent: QWidget | None = None,
		indexing_command: list[str] | None = None,
		configuration: Path | None = None,
		crossfades: Crossfades | None = None,
		*,
		audio: Audio,
		silences: Silences | None = None,
		interface: Interface | None = None,
		retention: int = RETENTION,
		dead_air: DeadAirSettings | None = None,
	) -> None:
		"""indexing_command : Machin indexer, avec la configuration de l'interface
		(indexer.indexing_command). configuration : le fichier où « Préférences… » enregistre les réglages,
		crossfades ceux qu'il donne (https://github.com/dascritch/machincast/issues/145) ; sans fichier, les
		préférences ne s'enregistrent pas. silences : la détection de silence qu'il donne
		(https://github.com/dascritch/machincast/issues/146). interface : ses réglages de l'interface, le voyant
		« Saturation » de l'onglet Antenne (https://github.com/dascritch/machincast/issues/191). dead_air : le
		blanc dans un sonore qu'il donne, pour Machin player (https://github.com/dascritch/machincast/issues/122)."""
		super().__init__(parent)
		self.configuration = configuration
		self.audio = audio
		"""Sortie de l'antenne et périphérique de pré-écoute (https://github.com/dascritch/machincast/issues/116)."""
		self.preview: PreviewWindow | None = None
		"""La fenêtre de pré-écoute, une seule pour toute l'interface, créée à sa première demande."""
		preferences.define((crossfades) or (Crossfades()))
		preferences.define_retention(retention)
		self.silence_threshold = ((silences) or (Silences())).threshold
		self.dead_air = (dead_air) or (DeadAirSettings())
		"""Blanc dans un sonore, que montrent les préférences (https://github.com/dascritch/machincast/issues/122)."""
		self.clipping = ((interface) or (Interface())).clipping
		"""Le voyant « Saturation » de l'onglet Antenne est affiché (https://github.com/dascritch/machincast/issues/191)."""
		self.suggestions = ((interface) or (Interface())).suggestions
		self.icon = ((interface) or (Interface())).icon
		"""L'icône choisie pour l'application ; None : celle de MachinCast
		(https://github.com/dascritch/machincast/issues/111)."""
		"""Au lancement, proposer ce qui manque pour démarrer (https://github.com/dascritch/machincast/issues/119)."""
		"""Seuil de silence du fichier de configuration, que montrent les préférences."""
		self.connection = connection
		self.clock = clock
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)
		self.ui.tabs.setTabsClosable(True)
		self.home = DefaultScreen(connection, state_socket, clock, audio=audio)
		self.home.show_clipping(self.clipping)
		self.home.requested_listening.connect(self._listen_on_air)
		self._add_fixed(self.home, ON_AIR)
		# La grille d'antenne, onglet fixe juste après l'onglet Antenne (https://github.com/dascritch/machincast/issues/307).
		self.calendar = Calendar(connection, clock)
		self.calendar.opened.connect(self._open)
		self.calendar.requested_creation.connect(self._create_event)
		self.calendar.announces.connect(self.ui.state_bar.showMessage)
		self.calendar.modified_grid.connect(self._modified_grid)
		self._add_fixed(self.calendar, _("Calendar"))
		self.home.opened.connect(self._open)
		self.home.requested_preview.connect(self._preview)
		# Le clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257).
		self.home.requested_skip.connect(lambda: self._interrupt("sound"))
		self.home.requested_advance.connect(self._advance)
		# Les coupures, depuis le prochain sonore (https://github.com/dascritch/machincast/issues/323).
		self.home.requested_interruption.connect(self._interrupt)
		self.home.requested_fallback.connect(self._cut_by_fallback)
		self._on_air: PlaybackState = STOP
		"""Le dernier état de Machin player, pour les coupures proposées."""
		self._fallback: list[interruption.Fallback] = []
		"""Les événements de secours, relus à l'ouverture du menu « Diffusion » et quand la grille change."""
		self.checker = Checker(connection, self)
		self.checker.finished.connect(self._finished_check)
		self.full_check = FullCheck(connection, self)
		"""L'audit complet d'un sonore, demandé depuis sa fiche (https://github.com/dascritch/machincast/issues/190)."""
		self.full_check.finished.connect(self._full_finished_check)
		if indexing_command is None:
			indexing_command = indexer.indexing_command(None)
		self.indexing_command = indexing_command
		self.launched_indexings: dict[bool, int] = {}
		"""Numéro du processus de chaque indexation lancée depuis le menu, selon full_audit, tant qu'il tourne : une
		indexation rapide et un audit complet peuvent tourner ensemble
		(https://github.com/dascritch/machincast/issues/401)."""
		self._indexing_tracking = QTimer(self)
		self._indexing_tracking.setInterval(INDEXING_TRACKING)
		self._indexing_tracking.timeout.connect(self._follow_indexing)
		"""Audit complet ou indexation rapide, pour l'indexation lancée."""
		self.control = control.Control(self)
		self.control.finished.connect(self._finished_control)
		self.control.not_started.connect(lambda text, journal: dialogs.warn_not_started(self, text, journal))
		self.service = service.ABSENT
		"""L'état du service de diffusion, relu au lancement, à l'ouverture du menu et après chaque commande."""
		self._requested_stop = False
		"""Sans service : l'arrêt de la diffusion d'essai, demandé depuis le menu, est à annoncer quand il a lieu."""
		self.without_service = QLabel(WITHOUT_SERVICE)
		self.without_service.setToolTip(INSTALL_SERVICE)
		self.ui.state_bar.addPermanentWidget(self.without_service)
		self.to_fill_in_on_air = QLabel(TO_FILL_IN_ON_AIR)
		self.to_fill_in_on_air.setToolTip(SET_ON_AIR)
		self.ui.state_bar.addPermanentWidget(self.to_fill_in_on_air)
		self.stopped_broadcast = QLabel(STOPPED_BROADCAST)
		"""Tant que la diffusion ne tourne pas, la dernière ligne de la fenêtre le dit
		(https://github.com/dascritch/machincast/issues/322)."""
		self.ui.state_bar.addPermanentWidget(self.stopped_broadcast)
		self._flag_on_air()
		self._fill_menus()
		self._follow_preview()
		self.home.client.received_state.connect(self._playback_state)
		self.home.client.received_state.connect(
			lambda state: self.stopped_broadcast.setVisible(state.state == "stopped")
		)
		self.home.client.received_state.connect(self._follow_public_text)
		self._public_text: str | None = None
		"""Le texte public du sonore en cours, titre de l'écoute de l'antenne."""
		self.home.client.received_state.connect(self._offer_interruptions)
		self._offer_interruptions(STOP)
		self._reread_fallback()
		self._reread_service()
		self._fetched_just: Card | None = None
		"""La fiche qui vient de s'ouvrir, et de se lire : son passage au premier plan ne la relit pas."""
		self.lists: list[List] = []
		self._titles: dict[QWidget, str] = {}
		"""Le titre de l'onglet de chaque liste, ouverte ou non."""
		self._keys: dict[QWidget, str] = {}
		"""La clé de l'onglet de chaque liste, dans les réglages : son genre."""
		for title, source in TABS:
			list_ = List(source, connection)
			list_.opened.connect(self._open)
			list_.requested_creation.connect(lambda category: self._open_card(category, None))
			list_.requested_duplication.connect(self._duplicate)
			list_.requested_preview.connect(self._preview)
			if source.category == "feed":
				# https://github.com/dascritch/machincast/issues/323
				list_.item_menu = self._feed_menu
			list_.requested_action.connect(lambda key, items, list_=list_: self._act(list_, key, items))
			list_.requested_addition.connect(lambda list_=list_: self._add_files(list_, dialogs.choose_files(self)))
			list_.dropped_files.connect(lambda paths, list_=list_: self._add_files(list_, paths))
			self.lists.append(list_)
			self._titles[list_] = title
			self._keys[list_] = source.category
			if self._keys[list_] not in ON_DEMAND:
				self._add_fixed(list_, title)
				continue
			# Sans onglet jusqu'à ce qu'on la demande, elle appartient à la fenêtre, cachée : elle ne lui survit pas
			# (https://github.com/dascritch/machincast/issues/262).
			list_.setParent(self)
			list_.hide()
		self.incidents = IncidentScreen(connection)
		self.incidents.opened.connect(self._open)
		self._add_fixed(self.incidents, _("Incidents"))
		self.ui.tabs.setCurrentIndex(0)
		self.ui.tabs.currentChanged.connect(self._opened_tab)
		self.ui.tabs.tabCloseRequested.connect(self._close)
		self._create_shortcuts()
		self.reopen_tabs()
		if not identify(self._application(), self.icon):
			self.statusBar().showMessage(
				_("Icon {icon} unreadable or not found: MachinCast icon instead.").format(icon=self.icon)
			)

	@staticmethod
	def _application() -> QApplication:
		application = QApplication.instance()
		assert isinstance(application, QApplication)
		return application

	def _change_icon(self, icon: Path | None) -> str:
		"""L'icône choisie, pour les fenêtres et les raccourcis déjà installés ; ce qu'en dit la barre d'état."""
		self.icon = icon
		identify(self._application(), icon)
		try:
			places = shortcut.rewrite(icon)
		except OSError as error:
			return _(" Shortcuts not updated: {error}.").format(error=error)
		if not places:
			return ""
		return _(" Icon updated {places}.").format(places=_(" and ").join(places))

	def _fill_menus(self) -> None:
		"""Fichier, Affichage, Diffusion, Maintenance, Aide ; une fonction à venir a son entrée, inactive, avec son
		ticket."""
		file = self.menuBar().addMenu(_("&File"))
		# La page « Interface » : https://github.com/dascritch/machincast/issues/145 ; l'icône viendra avec
		# https://github.com/dascritch/machincast/issues/111.
		settings = file.addAction(_("Preferences…"))
		settings.triggered.connect(self._preferences)
		if self.configuration is None:
			settings.setEnabled(False)
			settings.setToolTip(_("Without a configuration file, the preferences are not saved"))
		file.addSeparator()
		quit_ = file.addAction(_("Quit"))
		quit_.setShortcut(QKeySequence("Alt+Q"))
		quit_.triggered.connect(self.close)
		display_menu = self.menuBar().addMenu(_("&View"))
		look_up = display_menu.addAction(_("Search…"))
		look_up.setShortcut(QKeySequence("Ctrl+F"))
		look_up.triggered.connect(self._open_search)
		for title, source in TABS:
			if source.category not in ON_DEMAND:
				continue
			open_ = display_menu.addAction(
				icons.icon_of(source.category), _("Open the {title} tab").format(title=title)
			)
			open_.triggered.connect(lambda _ticked=False, title=title: self.open_list(title))
		grid = display_menu.addAction(icons.icon("grid"), _("Open the Time grid tab"))
		grid.triggered.connect(self._open_calendar)
		simulation = display_menu.addAction(icons.icon("simulation"), _("Open the Simulation tab"))
		simulation.triggered.connect(self._open_simulation)
		airplay = display_menu.addAction(icons.icon("airplay"), _("Open the Airplay tab"))
		airplay.triggered.connect(self._open_airplay)
		self.preview_action = display_menu.addAction(icons.icon("preview"), _("Pre-listen…"))
		self.preview_action.triggered.connect(lambda: self._preview(None))
		# En bas du menu (https://github.com/dascritch/machincast/issues/322).
		display_menu.addSeparator()
		refresh = display_menu.addAction(_("Refresh the tabs"))
		refresh.setShortcut(QKeySequence("F5"))
		refresh.triggered.connect(self.refresh)
		self.broadcast_menu = self.menuBar().addMenu(_("&Broadcast"))
		self.broadcast_menu.aboutToShow.connect(self._reread_service)
		# L'écoute de l'antenne, lancée aussitôt, en tête du menu (https://github.com/dascritch/machincast/issues/245) ;
		# pendant l'écoute, elle l'arrête, et Alt+P fait l'un ou l'autre (https://github.com/dascritch/machincast/issues/256).
		self.listen = self.broadcast_menu.addAction(icons.icon("preview"), "")
		self.listen.setShortcut(QKeySequence("Alt+P"))
		self.listen.triggered.connect(self._switch_listening)
		self._show_listening(False)
		self.broadcast_menu.addSeparator()
		self.controlled_list: dict[str, QAction] = {}
		for verb, (entry, _success, _failure) in control.VERBS.items():
			action = self.broadcast_menu.addAction(entry)
			action.triggered.connect(lambda _ticked=False, verb=verb: self._control(verb))
			self.controlled_list[verb] = action
		self.broadcast_menu.addSeparator()
		# https://github.com/dascritch/machincast/issues/104
		self.interruptions: dict[str, QAction] = {}
		for item, entry in interruption.ENTRIES.items():
			action = self.broadcast_menu.addAction(entry)
			action.triggered.connect(lambda _ticked=False, item=item: self._interrupt(item))
			self.interruptions[item] = action
		# https://github.com/dascritch/machincast/issues/323 : relu à l'ouverture du menu, et quand la grille change.
		self.cutoff_by_fallback = self.broadcast_menu.addAction(interruption.CUT_BY_FALLBACK)
		fallback = self.cutoff_by_fallback
		fallback.triggered.connect(lambda _ticked=False: interruption.ask_fallback(fallback, self._cut_by_fallback))
		self.broadcast_menu.aboutToShow.connect(self._reread_fallback)
		maintenance = self.menuBar().addMenu(_("&Maintenance"))
		_upcoming(
			maintenance.addAction(_("Output monitor…")), "ticket 85"
		)  # https://github.com/dascritch/machincast/issues/85
		maintenance.addSeparator()
		self.indexings: dict[bool, QAction] = {}
		"""L'action de chaque mode, selon full_audit : grisée tant que son indexation tourne."""
		for full_audit in (False, True):
			action = maintenance.addAction(TITLES[full_audit])
			action.triggered.connect(lambda _ticked=False, audit=full_audit: self._index(audit))
			self.indexings[full_audit] = action
		maintenance.addSeparator()
		# Grisée pendant toute indexation lancée d'ici : ses migrations attendraient la base
		# (https://github.com/dascritch/machincast/issues/127).
		self.database_maintenance = maintenance.addAction(control.MAINTENANCE)
		self.database_maintenance.triggered.connect(self._maintain_database)
		help_ = self.menuBar().addMenu(_("&Help"))
		help_.addAction(_("Documentation")).triggered.connect(lambda: dialogs.open_page(version.documentation()))
		help_.addAction(_("Report a problem…")).triggered.connect(lambda: dialogs.open_page(TICKETS))
		help_.addAction(_("Version")).triggered.connect(
			lambda: dialogs.show_version(self, version.text(), version.of_the_version())
		)
		for menu in (file, display_menu, self.broadcast_menu, maintenance, help_):
			menu.setToolTipsVisible(True)

	def _show_news(self) -> None:
		"""Une seule fois par version, et par compte : la version vue est retenue dans les réglages des vues."""
		news = version.of_the_version()
		settings = columns.settings()
		if (news is None) or (settings.value(version.NEWS_KEY) == news.version):
			return
		dialogs.show_news(self, news)
		settings.setValue(version.NEWS_KEY, news.version)

	def _reread_service(self) -> None:
		self.service = service.read_state()
		self._present_broadcast()

	def _playback_state(self, state: PlaybackState) -> None:
		"""La diffusion d'essai arrêtée depuis le menu : l'annoncer."""
		if (state.state != "stopped") or (not self._requested_stop):
			return
		self._requested_stop = False
		self.ui.state_bar.showMessage(control.STOPPED)

	def _offer_interruptions(self, state: PlaybackState) -> None:
		"""Les interruptions du menu « Diffusion » suivent ce qui est à l'antenne, comme la coupure par le secours, et
		le clic droit sur un feed (https://github.com/dascritch/machincast/issues/323)."""
		for item, proposal in interruption.offer(state).items():
			action = self.interruptions[item]
			action.setEnabled(proposal.active)
			action.setToolTip(proposal.tooltip)
		self._on_air = state
		self._fill_fallback()

	def _reread_fallback(self) -> None:
		self._fallback = interruption.read_fallback(self.connection)
		self._fill_fallback()

	def _fill_fallback(self) -> None:
		interruption.fill_fallback(self.cutoff_by_fallback, self._on_air, self._fallback, self._cut_by_fallback)

	def _cut_by_fallback(self, fallback: interruption.Fallback) -> None:
		"""Demande à Machin player de couper l'antenne par ce secours, sans question."""
		announces = interruption.CUTOFF_WITHOUT_PLAYBACK
		if self.home.client.send(cutoff_request_by_fallback(fallback.identifier)):
			announces = interruption.fallback_announcement(fallback.name)
		self.ui.state_bar.showMessage(announces)

	def _cut_by_feed(self, feed: int, name: str) -> None:
		"""Demande à Machin player de couper l'antenne par le stream de ce feed, sans question."""
		announces = interruption.CUTOFF_WITHOUT_PLAYBACK
		if self.home.client.send(cutoff_request_by_feed(feed)):
			announces = interruption.feed_announcement(name)
		self.ui.state_bar.showMessage(announces)

	def _feed_menu(self, menu: QMenu, feed: int, name: str) -> None:
		interruption.fill_feed(menu, self._on_air, self.connection, feed, name, self._preview, self._cut_by_feed)

	def _modified_grid(self) -> None:
		"""Une session sautée ou rétablie (https://github.com/dascritch/machincast/issues/273), une fiche enregistrée,
		supprimée ou restaurée (https://github.com/dascritch/machincast/issues/266) valent aussitôt à l'antenne :
		Machin player relit la grille, s'il diffuse ; sinon, il la lira à son démarrage. Les événements de secours
		ont pu changer."""
		self.home.client.send(request_reread_grid())
		self._reread_fallback()

	def _interrupt(self, item: str) -> None:
		"""Demande à Machin player d'interrompre l'élément, sans question : l'antenne n'attend pas."""
		announces = interruption.WITHOUT_PLAYBACK
		if self.home.client.send(interruption_request(item)):
			announces = interruption.ANNOUNCEMENTS[item]
		self.ui.state_bar.showMessage(announces)

	def _advance(self, event: int, name: str) -> None:
		"""Demande à Machin player d'avancer l'événement suivant qu'il a annoncé, sans question
		(https://github.com/dascritch/machincast/issues/257)."""
		announces = interruption.ADVANCE_WITHOUT_PLAYBACK
		if self.home.client.send(advance_request(event)):
			announces = interruption.advance_announcement(name)
		self.ui.state_bar.showMessage(announces)

	def _present_broadcast(self) -> None:
		"""Les entrées du menu « Diffusion » selon l'état du service ; sans lui, le signal d'installation à terminer. Le
		titre de l'onglet Antenne en porte le témoin (https://github.com/dascritch/machincast/issues/322)."""
		self.without_service.setVisible(not self.service.installed)
		indicator = INCOMPLETE_SERVICE
		if self.service.installed:
			indicator = INSTALLED_SERVICE
		index = self.ui.tabs.indexOf(self.home)
		self.ui.tabs.setTabText(index, f"{indicator} {ON_AIR}")
		if self.service.installed:
			# En marche : arrêter ; arrêté ou en échec : démarrer.
			allowed = {"start": not self.service.running, "stop": self.service.running}
			for verb, action in self.controlled_list.items():
				action.setText(control.VERBS[verb][0])
				action.setEnabled(allowed[verb])
				action.setToolTip("")
			return
		ongoing = self.home.client.player_pid() is not None
		tooltips = {"start": WITHOUT_SERVICE_START, "stop": WITHOUT_TRIAL}
		if ongoing:
			tooltips = {"start": ALREADY_RUNNING, "stop": TRIAL_HALT}
		for verb, action in self.controlled_list.items():
			action.setText(control.TRIAL[verb])
			action.setEnabled((verb == "start") != ongoing)
			action.setToolTip(tooltips[verb])

	def _control(self, verb: str) -> None:
		if self.service.installed:
			self.control.control(verb)
			return
		if verb == "start":
			self.ui.state_bar.showMessage(control.launch_in_terminal(self.configuration))
			return
		pid = self.home.client.player_pid()
		if pid is None:
			# Le menu relu à son ouverture n'active l'entrée qu'avec une diffusion d'essai : elle vient de s'arrêter.
			return
		text = control.halt_player(pid)
		self.ui.state_bar.showMessage(text)
		self._requested_stop = text == control.REQUESTED_STOP

	def _finished_control(self, text: str) -> None:
		self.ui.state_bar.showMessage(text)
		self._reread_service()

	def refresh(self) -> None:
		"""Relit l'onglet ouvert, l'airplay de l'onglet Antenne et les fiches ; une liste se relit déjà à son
		ouverture."""
		self._opened_tab(self.ui.tabs.currentIndex())
		self.home.refresh_airplay()
		left_list: list[str] = []
		erased_list: list[str] = []
		for card in self.cards():
			title = card.title()
			result = card.refresh()
			if result is Refreshed.LEFT:
				left_list.append(title)
			if result is Refreshed.ERASED:
				erased_list.append(title)
				self._remove(card)
		text = _("Tabs refreshed.")
		if left_list != []:
			text = _("{text} Cards left as they are: {titles}.").format(text=text, titles=_titles(left_list))
		if erased_list != []:
			text = _("{text} Cards closed, their element is no longer in the database: {titles}.").format(
				text=text, titles=_titles(erased_list)
			)
		self.ui.state_bar.showMessage(text)

	def cards(self) -> list[Card]:
		tabs = self.ui.tabs
		return [card for index in range(tabs.count()) if isinstance(card := tabs.widget(index), Card)]

	def closeEvent(self, event: QCloseEvent) -> None:
		for card in self.cards():
			if not card.can_close():
				event.ignore()
				return
		self.retain_tabs()
		for card in self.cards():
			card.shut_down()
		tabs = self.ui.tabs
		for index in range(tabs.count()):
			simulation = tabs.widget(index)
			if isinstance(simulation, SimulationScreen):
				simulation.shut_down()
		self.checker.halt()
		self.full_check.halt()
		self.home.close()
		if self.preview is not None:
			self.preview.close()
		super().closeEvent(event)

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
			return f"list:{self._keys[screen]}"
		for fixed, key in ((self.home, "on_air"), (self.calendar, "calendar"), (self.incidents, "incidents")):
			if screen is fixed:
				return key
		for category, key in (
			(SearchScreen, "search"),
			(SimulationScreen, "simulation"),
			(AirplayScreen, "airplay"),
		):
			if isinstance(screen, category):
				return key
		return None

	def retain_tabs(self) -> None:
		"""Les onglets ouverts, dans leur ordre, et l'onglet actif, dans les réglages des vues du compte."""
		tabs = self.ui.tabs
		keys = [self.tab_key(tabs.widget(index)) for index in range(tabs.count())]
		settings = columns.settings()
		settings.setValue(TAB_KEY, [key for key in keys if key is not None])
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
				self._reopen(current_tab_key(str(key)))
			except psycopg.Error as error:
				log.error(_("tab “{key}” not reopened: {error}").format(key=key, error=error))
		active = current_tab_key(str(settings.value(ACTIVE_TAB_KEY, "on_air")))
		tabs = self.ui.tabs
		found_list = [index for index in range(tabs.count()) if self.tab_key(tabs.widget(index)) == active]
		tabs.setCurrentIndex(next(iter(found_list), 0))

	def _reopen(self, key: str) -> None:
		"""Rouvre un onglet retenu ; un onglet fixe l'est déjà, une clé inconnue est ignorée."""
		category, _separator, rest = key.partition(":")
		if (category == "list") and (rest in ON_DEMAND):
			self.open_list(rest)
		elif category == "search":
			self._open_search()
		elif category == "simulation":
			self._open_simulation()
		elif category == "airplay":
			self._open_airplay()
		elif category == "card":
			card_type, _separator, identifier = rest.partition(":")
			if (card_type in CARD_TABLES) and (identifier.isdigit()):
				if self._in_database(card_type, int(identifier)):
					self._open_card(card_type, int(identifier))
				else:
					log.info(
						_("card {card_type} {identifier} forgotten: the element is no longer in the database").format(
							card_type=card_type, identifier=identifier
						)
					)

	def _in_database(self, category: str, identifier: int) -> bool:
		"""L'élément est en base, et n'est pas supprimé."""
		table = CARD_TABLES[category]
		condition = ""
		if table in DELETABLE:
			condition = " AND deleted_at IS NULL"
		with self.connection.transaction():
			line = self.connection.execute(
				f"SELECT 1 FROM {table} WHERE id = %s{condition}",  # noqa: S608 : table et condition sont des constantes
				(identifier,),
			).fetchone()
		return line is not None

	def _add_fixed(self, screen: QWidget, title: str) -> None:
		"""Un onglet sans bouton de fermeture."""
		index = self._add_tab(screen, title)
		for side in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
			self.ui.tabs.tabBar().setTabButton(index, side, None)

	def _add_tab(self, screen: QWidget, title: str) -> int:
		"""Tout onglet s'ajoute par ici, et se retire par _retirer_onglet : les raccourcis suivent."""
		index = self.ui.tabs.addTab(screen, icons.icon_of(screen_category(screen)), title)
		self._number_tabs()
		return index

	def _remove_tab(self, index: int) -> None:
		self.ui.tabs.removeTab(index)
		self._number_tabs()

	def _create_shortcuts(self) -> None:
		"""Maj+F1 à Maj+F12 : les 12 premiers onglets, selon leur rang
		(https://github.com/dascritch/machincast/issues/192) ; Ctrl+PageUp, Ctrl+PageDown, Ctrl+Home et Ctrl+End :
		l'onglet de gauche, de droite, le premier et le dernier (https://github.com/dascritch/machincast/issues/318)."""
		for rank in range(TAB_SHORTCUTS):
			shortcut = QShortcut(QKeySequence(f"Shift+F{rank + 1}"), self)
			shortcut.activated.connect(lambda rank=rank: self._go_to_tab(rank))
		# Ctrl+PageUp et Ctrl+PageDown à gauche et à droite, sans boucler, comme le ferait Qt ; Ctrl+Home et Ctrl+End au
		# premier et au dernier onglet (https://github.com/dascritch/machincast/issues/318). Raccourcis de la fenêtre,
		# ils valent quel que soit le widget qui a le focus, sauf celui qui se sert de la touche.
		for keys, relocation in (
			(LEFT_TAB, self._left_tab),
			(RIGHT_TAB, self._right_tab),
			(FIRST_TAB, lambda: self._go_to_tab(0)),
			(LAST_TAB, lambda: self._go_to_tab(self.ui.tabs.count() - 1)),
		):
			QShortcut(QKeySequence(keys), self).activated.connect(relocation)
		application = QApplication.instance()
		if application is not None:
			application.installEventFilter(TabKey(self))

	def _left_tab(self) -> None:
		"""Sur le premier onglet, rien : il n'y a pas d'onglet -1."""
		self._go_to_tab(self.ui.tabs.currentIndex() - 1)

	def _right_tab(self) -> None:
		"""Sur le dernier onglet, rien : il n'y a pas d'onglet après lui."""
		self._go_to_tab(self.ui.tabs.currentIndex() + 1)

	def _go_to_tab(self, rank: int) -> None:
		"""Un rang sans onglet ne change rien : Qt ignore l'indice."""
		self.ui.tabs.setCurrentIndex(rank)

	def _number_tabs(self) -> None:
		"""L'infobulle de chaque onglet donne son raccourci ; au-delà des 12 premiers, il n'en a pas."""
		tabs = self.ui.tabs
		for index in range(tabs.count()):
			text = ""
			if index < TAB_SHORTCUTS:
				text = f"Maj+F{index + 1}"
			tabs.setTabToolTip(index, text)

	def _open_card(self, category: str, identifier: int | None) -> None:
		"""Ouvre la fiche d'un élément, ou ramène au premier plan celle déjà ouverte ; None pour un nouvel élément."""
		for opened in self.cards():
			if (identifier is not None) and (opened.category == category) and (opened.identifier == identifier):
				self.ui.tabs.setCurrentWidget(opened)
				return
		card = CARDS[category](self.connection, identifier, self.clock)
		card.changed_title.connect(lambda title: self._rename(card, title))
		card.requested_opening.connect(self._open)
		card.deleted.connect(lambda: self._remove(card))
		card.requested_duplication.connect(self._duplicate)
		card.requested_preview.connect(self._preview)
		if isinstance(card, SoundCard):
			card.requested_check.connect(lambda sound, card=card: self._check_fully(card, sound))
		if category == "event":
			card.deleted.connect(self._guarantee_background_programming)
			card.saved.connect(self._guarantee_background_programming)
		if isinstance(card, EventCard):
			# Une session rétablie depuis la fiche (https://github.com/dascritch/machincast/issues/295), comme depuis le
			# calendrier : la barre d'état l'annonce, et Machin player relit la grille.
			card.restored_session.connect(self.ui.state_bar.showMessage)
			card.restored_session.connect(self._modified_grid)
		# Une fiche enregistrée, supprimée ou restaurée vaut aussitôt à l'antenne
		# (https://github.com/dascritch/machincast/issues/266) : Machin player relit la grille, et ne recalcule que si
		# ce qui règle l'antenne a changé. Un sonore ou une banque supprimé quitte les listes des événements.
		card.saved.connect(self._modified_grid)
		card.deleted.connect(self._modified_grid)
		self._add_tab(card, card.title())
		# Elle vient de se lire : passer au premier plan ne la relit pas (https://github.com/dascritch/machincast/issues/305).
		self._fetched_just = card
		self.ui.tabs.setCurrentWidget(card)
		self._fetched_just = None

	def _duplicate(self, category: str, identifier: int) -> None:
		"""Une nouvelle fiche, copie de l'élément (https://github.com/dascritch/machincast/issues/130) : rien n'est
		enregistré avant « Enregistrer »."""
		self._open_card(category, None)
		card = self.ui.tabs.currentWidget()
		assert isinstance(card, Card)
		card.copy(identifier)

	def _check_fully(self, card: SoundCard, sound: int) -> None:
		"""L'audit complet du sonore, au seuil de silence de la configuration ; sa fiche attend."""
		card.wait_check()
		self.full_check.launch(sound, self.silence_threshold)

	def _full_finished_check(self, sound: int, text: str) -> None:
		"""La barre d'état le dit ; la fiche du sonore, encore ouverte, propose de se rafraîchir."""
		self.ui.state_bar.showMessage(text)
		for card in self.cards():
			if (isinstance(card, SoundCard)) and (card.identifier == sound):
				card.finished_check(text)

	def _rename(self, card: QWidget, title: str) -> None:
		self.ui.tabs.setTabText(self.ui.tabs.indexOf(card), title)

	def _preview(self, sound: int | None) -> None:
		"""La fenêtre de pré-écoute, au premier plan : le sonore demandé y remplace le précédent ; sans sonore, elle
		garde le sien. Elle n'a pas de fenêtre parente (https://github.com/dascritch/machincast/issues/325) : le bureau
		lui donne sa propre entrée dans le gestionnaire des tâches, et ne la garde pas au-dessus de l'interface. Elle se
		ferme avec l'interface (closeEvent), et disparaît avec elle. Désactivée, sur l'entrée « Sortie factice », elle
		ne s'ouvre jamais (https://github.com/dascritch/machincast/issues/339)."""
		if display.disabled_preview():
			return
		if self.preview is None:
			self.preview = PreviewWindow(self.connection, self.audio, self.configuration)
			self.preview.changed_listening.connect(self._show_listening)
			self.destroyed.connect(self.preview.deleteLater)
		if (sound is not None) or (not self.preview.isVisible()):
			self.preview.preview(sound)
		self.preview.show()
		self.preview.raise_()
		self.preview.activateWindow()

	def _switch_listening(self) -> None:
		"""L'entrée d'écoute de l'antenne, ou Alt+P : l'arrête pendant l'écoute, la lance sinon."""
		if (self.preview is not None) and (self.preview.on_air_listening()):
			self.preview.halt()
			return
		self._listen_on_air(launch=True)

	def _show_listening(self, ongoing: bool) -> None:
		text, tooltip = LISTENING[ongoing]
		self.listen.setText(text)
		display.set_preview(self.listen, True, tooltip)

	def _follow_preview(self) -> None:
		"""Sur l'entrée « Sortie factice » de la pré-écoute, ses boutons et ses entrées de menu sont grisés, partout
		(https://github.com/dascritch/machincast/issues/339) : ceux de la fenêtre, de l'onglet Antenne et des fiches de
		sonores ouvertes ; les menus contextuels le sont à leur ouverture."""
		display.disable_preview(self.audio.disabled_preview())
		display.set_preview(self.preview_action, True, self.preview_action.text())
		ongoing = (self.preview is not None) and (self.preview.on_air_listening())
		self._show_listening(ongoing)
		self.home.follow_preview()
		tabs = self.ui.tabs
		for index in range(tabs.count()):
			screen = tabs.widget(index)
			if isinstance(screen, SoundCard):
				screen.follow_preview()

	def _listen_on_air(self, launch: bool = False) -> None:
		"""Clic sur le VU-mètre de l'onglet Antenne : l'antenne dans la fenêtre de pré-écoute
		(https://github.com/dascritch/machincast/issues/24) ; par le bouton « Pré-écoute » de la fenêtre, lancée
		aussitôt (https://github.com/dascritch/machincast/issues/223)."""
		self._preview(None)
		# Désactivée, la pré-écoute ne s'ouvre pas (https://github.com/dascritch/machincast/issues/339).
		if self.preview is None:
			return
		self.preview.listen_on_air(self._public_text, launch)

	def _follow_public_text(self, state: PlaybackState) -> None:
		self._public_text = None
		if state.ongoing is not None:
			self._public_text = state.ongoing.public_text
		if self.preview is not None:
			self.preview.follow_on_air(self._public_text)

	def _open_calendar(self) -> None:
		"""Le calendrier, onglet fixe, revient au premier plan (https://github.com/dascritch/machincast/issues/307)."""
		self.ui.tabs.setCurrentWidget(self.calendar)

	def _open_search(self) -> None:
		"""Un seul onglet de recherche (https://github.com/dascritch/machincast/issues/27) : celui qui est ouvert
		revient au premier plan ; le curseur va dans son champ."""
		tabs = self.ui.tabs
		opened_list = [tabs.widget(index) for index in range(tabs.count())]
		search = next((screen for screen in opened_list if isinstance(screen, SearchScreen)), None)
		if search is None:
			search = SearchScreen(self.connection)
			search.opened.connect(self._open)
			self._add_tab(search, _("Search"))
		tabs.setCurrentWidget(search)
		search.focus()

	def open_list(self, title: str) -> None:
		"""Ouvre une liste à la demande à sa place, après les listes qui la précèdent et avant les incidents, ou la
		ramène au premier plan (https://github.com/dascritch/machincast/issues/180). Elle se désigne par son titre, ou
		par son genre."""
		tabs = self.ui.tabs
		(list_,) = (list_ for list_ in self.lists if title in (self._titles[list_], self._keys[list_]))
		title = self._titles[list_]
		index = tabs.indexOf(list_)
		if index < 0:
			order: list[QWidget] = [self.home, self.calendar, *self.lists]
			rank = order.index(list_)
			place = sum(1 for screen in order[:rank] if tabs.indexOf(screen) >= 0)
			index = tabs.insertTab(place, list_, icons.icon_of(screen_category(list_)), title)
			self._number_tabs()
		tabs.setCurrentIndex(index)

	def _open_simulation(self) -> None:
		"""Un seul onglet de simulation (https://github.com/dascritch/machincast/issues/37) : celui qui est ouvert
		revient au premier plan, avec son résultat."""
		tabs = self.ui.tabs
		opened_list = [tabs.widget(index) for index in range(tabs.count())]
		simulation = next((screen for screen in opened_list if isinstance(screen, SimulationScreen)), None)
		if simulation is None:
			simulation = SimulationScreen(self.clock, self.configuration)
			self._add_tab(simulation, _("Simulation"))
		tabs.setCurrentWidget(simulation)

	def _open_airplay(self) -> None:
		"""Un seul onglet Airplay (https://github.com/dascritch/machincast/issues/244) : celui qui est ouvert revient au
		premier plan. Il se relit quand l'onglet Antenne voit un nouveau sonore."""
		tabs = self.ui.tabs
		opened_list = [tabs.widget(index) for index in range(tabs.count())]
		airplay = next((screen for screen in opened_list if isinstance(screen, AirplayScreen)), None)
		if airplay is None:
			airplay = AirplayScreen(self.connection, self.clock, self._metadata())
			airplay.opened.connect(self._open)
			airplay.requested_preview.connect(self._preview)
			airplay.announces.connect(self.ui.state_bar.showMessage)
			self.home.reread_airplay.connect(airplay.refresh)
			self._add_tab(airplay, _("Airplay"))
		tabs.setCurrentWidget(airplay)

	def _metadata(self) -> Metadata:
		"""Le masquage et le texte public de la configuration, pour le texte public des exports de l'airplay."""
		if self.configuration is None:
			return WITHOUT_METADATA
		try:
			return load(self.configuration).metadata
		except (InvalidConfiguration, OSError) as error:
			log.warning(_("unreadable configuration, exports without hiding: {error}").format(error=error))
			return WITHOUT_METADATA

	def _create_event(self, start: datetime) -> None:
		"""Un nouvel événement, à l'heure cliquée dans le calendrier, s'ouvre dans sa fiche si on le confirme."""
		end = start + ONE_HOUR
		text = _("Create an event on {long_date} from {start:%H:%M} to {end:%H:%M}?").format(
			long_date=long_date(start.date()), start=start, end=end
		)
		if not dialogs.confirm_creation(self, text):
			return
		self._open_card("event", None)
		card = self.ui.tabs.currentWidget()
		assert isinstance(card, EventCard)
		card.plan(start, end)

	def _close(self, index: int) -> None:
		card = self.ui.tabs.widget(index)
		if isinstance(card, Calendar):
			# Onglet fixe (https://github.com/dascritch/machincast/issues/307) : il ne se ferme pas.
			return
		if isinstance(card, (SearchScreen, SimulationScreen, AirplayScreen)):
			if isinstance(card, AirplayScreen):
				self.home.reread_airplay.disconnect(card.refresh)
			if isinstance(card, SimulationScreen):
				card.shut_down()
			self._remove_tab(index)
			card.deleteLater()
			return
		if isinstance(card, List):
			# Une liste à la demande est gardée : rouverte, elle retrouve son filtre et son tri.
			self._remove_tab(index)
			return
		assert isinstance(card, Card), card
		if card.can_close():
			self._remove(card)

	def _remove(self, card: Card) -> None:
		"""Ferme l'onglet de la fiche, sans rien lui demander."""
		self._remove_tab(self.ui.tabs.indexOf(card))
		card.shut_down()
		card.deleteLater()

	def _act(self, list_: List, key: str, items: list[int]) -> None:
		"""Une action sur la sélection d'une liste (https://github.com/dascritch/machincast/issues/114) : le choix des
		banques s'il en faut, la confirmation, puis l'action en une transaction ; la liste se relit et la barre d'état
		annonce ce qui a changé. Un choix abandonné, ou une confirmation refusée, ne change rien."""
		action = groups.action(list_.source.category, key)
		banks: list[int] = []
		try:
			if action.choice == "toutes":
				banks = dialogs.choose_banks(self, self.connection, ADDITION_TO_BANKS)
			elif action.choice == "leurs":
				with self.connection.transaction():
					among = groups.sound_banks(self.connection, items)
				banks = dialogs.choose_banks(self, self.connection, BANK_REMOVAL, among)
			if (action.choice != "") and (banks == []):
				return
			with self.connection.transaction():
				names = groups.bank_names(self.connection, banks)
			if not dialogs.confirm_action(self, action.title, action.question(len(items), names), action.button):
				return
			with self.connection.transaction():
				announces = action.run(self.connection, items, banks)
		except psycopg.Error as error:
			log.error(_("{title}: impossible: {error}").format(title=action.title, error=error))
			self.ui.state_bar.showMessage(_("{title}: impossible: {error}").format(title=action.title, error=error))
			return
		self.ui.state_bar.showMessage(announces)
		list_.refresh()

	def _add_files(self, list_: List, paths: list[Path]) -> None:
		"""Les fichiers entrent en base à l'état aperçu, puis l'indexeur les vérifie, en tâche de fond."""
		if paths == []:
			return
		try:
			adding = add_files(self.connection, paths)
		except psycopg.Error as error:
			log.error(_("addition of files impossible: {error}").format(error=error))
			self.ui.state_bar.showMessage(_("Addition impossible: {error}").format(error=error))
			return
		self.ui.state_bar.showMessage(adding.text())
		list_.refresh()
		self.checker.check(adding.added_list)

	def offer_to_launching(self) -> None:
		"""Une fois la fenêtre montrée : les nouveautés d'une version publiée, si elles n'ont pas encore été montrées
		(https://github.com/dascritch/machincast/issues/208), puis la fenêtre des suggestions, s'il manque de quoi
		démarrer (https://github.com/dascritch/machincast/issues/119) ; sans les suggestions, le fil musical garanti,
		comme avant (spec § 8.10)."""
		self._show_news()
		if not self.suggestions:
			self._guarantee_background_programming()
			return
		try:
			gaps = suggestions.missing_list(self.connection, self.audio)
		except psycopg.Error as error:
			log.error(_("suggestions impossible: {error}").format(error=error))
			return
		if gaps.empty():
			return
		response = dialogs.suggest(self, gaps, self.service)
		if self.configuration is not None:
			try:
				suggestions.save(self.configuration, response)
			except OSError as error:
				self.statusBar().showMessage(
					_("Settings not saved in {configuration}: {error}").format(
						configuration=self.configuration, error=error
					)
				)
				return
		if response.more_offer:
			self.suggestions = False
		if not response.create:
			return
		try:
			text = suggestions.create(self.connection, response)
		except psycopg.Error as error:
			self.statusBar().showMessage(_("Creation impossible: {error}").format(error=error))
			return
		if text is not None:
			self.statusBar().showMessage(text)
		if (response.output is not None) and (response.preview is not None) and (self.configuration is not None):
			self.audio = dataclasses.replace(
				self.audio, output=response.output, device=response.on_air, preview=response.preview
			)
			self._flag_on_air()
			self._follow_preview()
			self.home.change_on_air(self.audio)
			on_air = (response.on_air) or (_("to fill in"))
			self.statusBar().showMessage(
				_(
					"Sound cards: on air {on_air}, pre-listen {preview}; Machin player will take the on-air "
					"output at its next start."
				).format(on_air=on_air, preview=response.preview)
			)

	def _guarantee_background_programming(self) -> None:
		"""Sans fil musical en base, en crée un, permanent et vide, et le dit (spec § 8.10)."""
		try:
			created = guarantee(self.connection)
		except psycopg.Error as error:
			log.error(_("check of the background programming impossible: {error}").format(error=error))
			return
		if created is None:
			return
		text = _(
			"No background programming: “{created}” is created, permanent and without element; its "
			"list is filled in its card."
		).format(created=created)
		log.warning(text)
		self.ui.state_bar.showMessage(text)

	def _maintain_database(self) -> None:
		"""Machin maintenance-db dans un terminal, une fois confirmée, avec l'emplacement de sa sauvegarde, au choix
		(https://github.com/dascritch/machincast/issues/127)."""
		backups = dialogs.confirm_maintenance(self, control.maintenance_backups(self.configuration))
		if backups is None:
			self.statusBar().showMessage(control.ABANDONED_MAINTENANCE)
			return
		self.statusBar().showMessage(control.launch_maintenance(self.configuration, backups))

	def _index(self, full_audit: bool) -> bool:
		"""Lance Machin indexer dans son propre processus, avec sa fenêtre ; le menu ne propose plus ce mode, ni la
		maintenance de la base, tant qu'il tourne. L'autre mode reste proposé
		(https://github.com/dascritch/machincast/issues/401). Vrai s'il est lancé."""
		command = [*self.indexing_command, "--window"]
		if full_audit:
			command.append("--full-audit")
		number = indexer.launch_detached(command)
		if number is None:
			log.error(_("indexing impossible to launch: {list}").format(list=" ".join(command)))
			self.ui.state_bar.showMessage(_("Indexing impossible: Machin indexer could not be launched."))
			return False
		self.launched_indexings[full_audit] = number
		self.indexings[full_audit].setEnabled(False)
		self.database_maintenance.setEnabled(False)
		title = TITLES[full_audit]
		self.ui.state_bar.showMessage(
			_("{title} {launched}, in its own window.").format(title=title, launched=LAUNCHED[full_audit])
		)
		self._indexing_tracking.start()
		return True

	def _follow_indexing(self) -> None:
		for full_audit, number in list(self.launched_indexings.items()):
			if indexer.active_process(number):
				continue
			del self.launched_indexings[full_audit]
			self.indexings[full_audit].setEnabled(True)
			self.ui.state_bar.showMessage(
				_("{title} {finished}; “Refresh the tabs” (F5) shows its changes.").format(
					title=TITLES[full_audit], finished=FINISHED[full_audit]
				)
			)
		if self.launched_indexings == {}:
			self._indexing_tracking.stop()
			self.database_maintenance.setEnabled(True)

	def _finished_check(self, text: str) -> None:
		self.ui.state_bar.showMessage(text)
		opened = self.ui.tabs.currentWidget()
		if isinstance(opened, List):
			opened.refresh()

	def _opened_tab(self, index: int) -> None:
		"""L'onglet qui passe au premier plan se relit, s'il n'est pas en cours d'édition
		(https://github.com/dascritch/machincast/issues/241) : une liste, les incidents, le calendrier, la recherche,
		l'airplay, l'airplay de l'onglet Antenne, et une fiche qui n'est pas modifiée, sans rien demander. Une fiche
		modifiée reste telle quelle ; celle d'un élément effacé de la base se ferme."""
		opened = self.ui.tabs.widget(index)
		if isinstance(opened, (List, IncidentScreen, Calendar, SearchScreen, AirplayScreen)):
			opened.refresh()
		if opened is self.home:
			self.home.refresh_airplay()
		if (not isinstance(opened, Card)) or (opened.modified) or (opened is self._fetched_just):
			return
		title = opened.title()
		if opened.refresh() is Refreshed.ERASED:
			self._remove(opened)
			self.ui.state_bar.showMessage(
				_("Card closed, its element is no longer in the database: “{title}”.").format(title=title)
			)

	def _preferences(self) -> None:
		"""Les préférences réglées s'enregistrent dans le fichier de configuration, puis valent pour les fiches
		ouvertes ensuite ; un fichier qui ne s'écrit pas les laisse inchangées, et la barre d'état le dit. Un seuil de
		silence changé relance l'audit complet (https://github.com/dascritch/machincast/issues/401)."""
		assert self.configuration is not None
		audio = self.audio
		shown_list = preferences.Settings(
			preferences.crossfades(),
			audio.device,
			audio.preview,
			self.silence_threshold,
			self.clipping,
			self.suggestions,
			self.icon,
			preferences.retention(),
			self.dead_air,
		)
		# L'état du service, lu à l'ouverture : en marche, la carte de l'antenne ne se choisit pas
		# (https://github.com/dascritch/machincast/issues/339).
		self._reread_service()
		settings = dialogs.set_preferences(self, shown_list, audio.output, self.service)
		if settings is None:
			return
		try:
			preferences.write(self.configuration, settings)
		except OSError as error:
			self.statusBar().showMessage(
				_("Preferences not saved in {configuration}: {error}").format(
					configuration=self.configuration, error=error
				)
			)
			return
		preferences.define(settings.crossfades)
		preferences.define_retention(settings.retention)
		new_threshold = settings.silence_threshold != self.silence_threshold
		self.silence_threshold = settings.silence_threshold
		self.dead_air = settings.dead_air
		self.clipping = settings.clipping
		self.suggestions = settings.suggestions
		self.home.show_clipping(self.clipping)
		icon = ""
		if settings.icon != self.icon:
			icon = self._change_icon(settings.icon)
		text = _("the default crossfades")
		output = (settings.output) or (audio.output)
		if (settings.on_air != audio.device) or (output != audio.output):
			text = _("the default crossfades and the on-air device")
		self.audio = dataclasses.replace(audio, output=output, device=settings.on_air, preview=settings.preview)
		if self.preview is not None:
			# La pré-écoute repart des nouveaux périphériques à sa prochaine ouverture.
			self.preview.close()
			self.preview.deleteLater()
			self.preview = None
		self._flag_on_air()
		self._follow_preview()
		self.home.change_on_air(self.audio)
		audit = ""
		if new_threshold:
			audit = f" {self._audit_new_threshold()}"
		self.statusBar().showMessage(
			_("Preferences saved in {configuration}; Machin player will take {text} at its next start.{icon}").format(
				configuration=self.configuration, text=text, icon=icon
			)
			+ audit
		)

	def _audit_new_threshold(self) -> str:
		"""Les silences mesurés au seuil précédent ne valent plus : l'audit complet est relancé, avec la configuration
		qui vient d'être enregistrée ; un audit complet lancé d'ici, encore en cours, garde l'ancien seuil
		(https://github.com/dascritch/machincast/issues/401). Ce que la barre d'état en dit."""
		if True in self.launched_indexings:
			return _(
				"Silence threshold changed: the ongoing full audit keeps the former threshold, launch “{title}” again "
				"at its end."
			).format(title=TITLES[True])
		if self._index(True):
			return _("Silence threshold changed: full audit launched, in its own window.")
		return _("Silence threshold changed: full audit impossible, Machin indexer could not be launched.")

	def _flag_on_air(self) -> None:
		"""Sans périphérique d'antenne, sur une vraie sortie, Machin player refuse de diffuser : la barre d'état le
		dit."""
		self.to_fill_in_on_air.setVisible(self.audio.to_fill_in_on_air())

	def _open(self, category: str, identifier: int, _name: str) -> None:
		self.requested_detail.emit(category, identifier)
		self._open_card(category, identifier)


def _upcoming(action: QAction, tickets: str) -> None:
	"""Une infobulle ne porte pas de lien : elle nomme le ticket par son numéro, sans « # »."""
	action.setEnabled(False)
	action.setToolTip(_("Upcoming: {tickets} on GitHub").format(tickets=tickets))


def _titles(titles: list[str]) -> str:
	return ", ".join(_("“{title}”").format(title=title) for title in titles)
