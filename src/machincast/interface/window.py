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

import contextlib
import dataclasses
import logging
from datetime import datetime, time
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget

from machincast import access, crash, shortcut
from machincast.clock import Clock
from machincast.configuration import (
	DAILY,
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
	broadcast_status,
	columns,
	control,
	dialogs,
	disk_space,
	display,
	groups,
	icons,
	indexer,
	indexing_status,
	installation_notes,
	interruption,
	key_hints,
	preferences,
	service_access,
	suggestions,
	tab_help,
	table_menu,
	version,
)
from machincast.interface.adding import add_files
from machincast.interface.airplay_tab import WITHOUT_METADATA, AirplayScreen
from machincast.interface.api_tab import ApiScreen
from machincast.interface.application import identify
from machincast.interface.background_programming import guarantee
from machincast.interface.bank_card import BankCard
from machincast.interface.broadcast_control import (
	INCOMPLETE_SERVICE,
	INSTALLED_SERVICE,
	BroadcastControl,
)
from machincast.interface.calendar import ONE_HOUR, Calendar, long_date
from machincast.interface.card import Card, Refreshed
from machincast.interface.check import Checker, FullCheck
from machincast.interface.default_screen import DefaultScreen
from machincast.interface.event_card import EventCard
from machincast.interface.feed_card import FeedCard
from machincast.interface.incidents import IncidentScreen
from machincast.interface.indexer import FINISHED, LAUNCHED, TITLES
from machincast.interface.lists import BANKS, EVENTS, FEEDS, SEQUENCES, SOUNDS, List, Source
from machincast.interface.preview import PreviewWindow
from machincast.interface.queries import cards as cards_queries
from machincast.interface.screen_saver import ScreenSaver
from machincast.interface.search import SearchScreen
from machincast.interface.sequence_card import SequenceCard
from machincast.interface.simulation import SimulationScreen
from machincast.interface.sound_card import SoundCard
from machincast.interface.state import STOP, PlaybackState
from machincast.interface.tab_manager import ON_AIR, ON_DEMAND, TabManager
from machincast.interface.ui.main_window import Ui_MainWindow

log = logging.getLogger(__name__)

TABS = (
	(_("Events"), EVENTS),
	(_("Sequences"), SEQUENCES),
	(_("Banks"), BANKS),
	(_("Sounds"), SOUNDS),
	(_("Feeds"), FEEDS),
)


def _by_category(cards: tuple[type[Card], ...]) -> dict[str, type[Card]]:
	cards_by_category = {}
	for card in cards:
		cards_by_category[card.category] = card
	return cards_by_category


CARDS = _by_category((EventCard, SequenceCard, BankCard, SoundCard, FeedCard))
"""Écrans de détail : les fiches, par genre."""
INDEXING_TRACKING = 1000
"""Millisecondes entre deux regards sur le processus de l'indexation lancée depuis le menu."""
TICKETS = "https://github.com/dascritch/machincast/issues"
"""Les tickets de MachinCast, qu'ouvre « Signaler un problème… » ; comme dans pyproject.toml."""
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
STOPPED_BROADCAST = _("🔇 Broadcast stopped")
WITHOUT_SERVICE = _("Non-final installation: broadcast without a service")
"""Ce que montre la barre d'état tant que le service n'est pas installé (https://github.com/dascritch/machincast/issues/25)."""
INSTALL_SERVICE = _(
	"The broadcast does not start with the computer, and does not restart by itself after a "
	"crash. On a computer dedicated to the on-air output, install the service: ./install.sh "
	"--service (INSTALL.md, Broadcast service)."
)
TO_FILL_IN_ON_AIR = _("On-air device to fill in")
SET_ON_AIR = _(
	"Machin player refuses to broadcast without it: choose it in File → Broadcast service settings…, Audio "
	"page, or give it in audio.device of the configuration file."
)
RESTARTING_FOR_SETTINGS = _("Broadcast service settings saved: restarting the broadcast, which takes them…")
LISTENING = {
	False: (_("On-air monitor"), _("Listen to the on-air output on the pre-listen output, at once")),
	True: (_("Stop the on-air monitor"), _("Stop listening to the on-air output on the pre-listen output")),
}
"""L'entrée d'écoute de l'antenne du menu « Diffusion », et son infobulle, selon que l'antenne s'écoute
(https://github.com/dascritch/machincast/issues/256). « Moniteur de l'antenne » depuis
https://github.com/dascritch/machincast/issues/531, aussi le bouton sous le voyant de l'onglet Antenne."""

SOUND_CARDS = _("Sound cards")
WPCTL_STATUS = "wpctl status"
PRELISTENED = _("Pre-listened sound")
SHOWN_TAB = _("Tab shown")
"""Les rubriques des rapports de crash de Machin interface (https://github.com/dascritch/machincast/issues/342)."""
ADDITION_TO_BANKS = _("The chosen sounds are added at the end of each bank.")
"""Remarque du choix des banques où ajouter des sonores (https://github.com/dascritch/machincast/issues/114)."""
BANK_REMOVAL = _("Only the banks containing one of the chosen sounds are offered.")
"""Remarque du choix des banques d'où retirer des sonores."""


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
		daily: time = DAILY,
		station: str = "",
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
		self.station = station
		"""Le nom de la radio, metadata.public_text, dans le titre de la fenêtre
		(https://github.com/dascritch/machincast/issues/495)."""
		self.audio = audio
		"""Sortie de l'antenne et périphérique de pré-écoute (https://github.com/dascritch/machincast/issues/116)."""
		self.preview: PreviewWindow | None = None
		self.disk_space: disk_space.DiskSpaceWindow | None = None
		"""La fenêtre de pré-écoute, une seule pour toute l'interface, créée à sa première demande."""
		# Pour un rapport de crash (https://github.com/dascritch/machincast/issues/342).
		crash.provide(SOUND_CARDS, self._sound_cards)
		crash.provide(WPCTL_STATUS, crash.wpctl_status)
		crash.provide(PRELISTENED, self._prelistened)
		crash.provide(SHOWN_TAB, self._shown_tab)
		preferences.define((crossfades) or (Crossfades()))
		preferences.define_retention(retention)
		self.daily = daily
		"""L'heure de la tâche quotidienne, que règlent les paramètres du service
		(https://github.com/dascritch/machincast/issues/455)."""
		preferences.define_table_rows(((interface) or (Interface())).table_rows)
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
		# Déplaçables, l'onglet Antenne toujours le premier (https://github.com/dascritch/machincast/issues/405).
		self.ui.tabs.setMovable(True)
		self.broadcast = BroadcastControl(self)
		self.tab_manager = TabManager(self, self.ui.tabs, self._reopen, self._close, self._remove)
		# Ctrl ou Alt tenue une seconde : les raccourcis en surimpression (https://github.com/dascritch/machincast/issues/529).
		self.key_hints = key_hints.KeyHints(self)
		self.home = DefaultScreen(connection, state_socket, clock, audio=audio)
		self.home.show_clipping(poster=self.clipping)
		# Le moniteur de l'antenne n'a ni lecture ni pause : il écoute aussitôt (https://github.com/dascritch/machincast/issues/531).
		self.home.requested_listening.connect(lambda: self._listen_on_air(launch=True))
		self.tab_manager.add_fixed(self.home, ON_AIR, "on_air")
		# La grille d'antenne, onglet fixe juste après l'onglet Antenne (https://github.com/dascritch/machincast/issues/307).
		self.calendar = Calendar(connection, clock)
		self.calendar.opened.connect(self._open)
		self.calendar.requested_creation.connect(self._create_event)
		self.calendar.announces.connect(self.ui.state_bar.showMessage)
		self.calendar.modified_grid.connect(self.broadcast.modified_grid)
		self.tab_manager.add_fixed(self.calendar, _("Calendar"), "calendar")
		self.home.opened.connect(self._open)
		# Le VU-mètre en pause pendant la veille de la session (https://github.com/dascritch/machincast/issues/346).
		self.screen_saver = ScreenSaver(self)
		self.screen_saver.changed.connect(self._screen_saver_changed)
		self.home.requested_preview.connect(self._preview)
		# Le clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257).
		self.home.requested_skip.connect(lambda: self.broadcast.interrupt("sound"))
		self.home.requested_advance.connect(self.broadcast.advance)
		# Les coupures, depuis le prochain sonore (https://github.com/dascritch/machincast/issues/323).
		self.home.requested_interruption.connect(self.broadcast.interrupt)
		self.home.requested_fallback.connect(self.broadcast.cut_by_fallback)
		self.home.requested_insertion.connect(self.broadcast.insert)
		# Le bouton « Moniteur de l'antenne », sous le voyant, comme l'entrée du menu « Diffusion »
		# (https://github.com/dascritch/machincast/issues/531).
		self.home.ui.monitor.setIcon(icons.icon("preview"))
		self.home.ui.monitor.clicked.connect(self._switch_listening)
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
		self.home.client.received_state.connect(self.broadcast.playback_state)
		self.home.client.received_state.connect(
			lambda state: self.stopped_broadcast.setVisible(state.state == "stopped")
		)
		self.home.client.received_state.connect(self._follow_public_text)
		self.home.client.received_state.connect(lambda _state: self.show_status())
		self.home.unavailable_action.connect(self.ui.state_bar.showMessage)
		self.home.announce_unavailable()
		self._public_text: str | None = None
		"""Le texte public du sonore en cours, titre de l'écoute de l'antenne."""
		self.home.client.received_state.connect(self.broadcast.offer_interruptions)
		self.broadcast.offer_interruptions(STOP)
		self.broadcast.reread_fallback()
		self.broadcast.reread_service()
		self._fetched_just: Card | None = None
		"""La fiche qui vient de s'ouvrir, et de se lire : son passage au premier plan ne la relit pas."""

		def create_list(source: Source, title: str) -> None:
			list_ = List(source, connection)
			list_.opened.connect(self._open)
			list_.requested_creation.connect(lambda category: self._open_card(category, None))
			list_.requested_duplication.connect(self._duplicate)
			list_.requested_preview.connect(self._preview)
			if source.category == "feed":
				# https://github.com/dascritch/machincast/issues/323
				list_.item_menu = self.broadcast.feed_menu
			list_.requested_action.connect(lambda key, items, list_=list_: self._act(list_, key, items))
			list_.requested_addition.connect(lambda list_=list_: self._add_files(list_, dialogs.choose_files(self)))
			list_.dropped_files.connect(lambda paths, list_=list_: self._add_files(list_, paths))
			self.tab_manager.lists.append(list_)
			self.tab_manager.titles[list_] = title
			self.tab_manager.keys[list_] = source.category
			if source.category not in ON_DEMAND:
				self.tab_manager.add_fixed(list_, title)
				return
			# Sans onglet jusqu'à ce qu'on la demande, elle appartient à la fenêtre, cachée : elle ne lui survit pas
			# (https://github.com/dascritch/machincast/issues/262).
			list_.setParent(self)
			list_.hide()

		for title, source in TABS:
			create_list(source, title)
		self.incidents = IncidentScreen(connection)
		self.incidents.opened.connect(self._open)
		self.tab_manager.add_fixed(self.incidents, _("Incidents"), "incidents")
		self.ui.tabs.setCurrentIndex(0)
		self.ui.tabs.currentChanged.connect(self._opened_tab)
		self.ui.tabs.currentChanged.connect(self._follow_help)
		self.ui.tabs.tabCloseRequested.connect(self._close)
		self.ui.tabs.tabBar().tabMoved.connect(self.tab_manager.moved_tab)
		self.tab_manager.create_shortcuts()
		self.tab_manager.reopen_tabs()
		self.tab_manager.appending = False
		self._follow_help()
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
		"""Fichier, Affichage, Onglets, Diffusion, Maintenance, Aide ; une fonction à venir a son entrée, inactive, avec
		son ticket."""
		file = self.menuBar().addMenu(_("&File"))
		# La page « Interface » : https://github.com/dascritch/machincast/issues/145 ; l'icône viendra avec
		# https://github.com/dascritch/machincast/issues/111.
		# Deux fenêtres : ce qui vaut aussitôt dans l'interface, et ce que Machin player prend à son redémarrage
		# (https://github.com/dascritch/machincast/issues/389).
		for kind in (preferences.INTERFACE, preferences.SERVICE):
			settings = file.addAction(preferences.ENTRIES[kind])
			settings.triggered.connect(lambda _ticked=False, chosen=kind: self._preferences(chosen))
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
		# Le signal donne son booléen « coché » : il ne doit pas tenir lieu du texte d'une recherche rouverte.
		look_up.triggered.connect(lambda _ticked=False: self._open_search())

		def add_open_action(source: Source, title: str) -> None:
			if source.category not in ON_DEMAND:
				return
			open_ = display_menu.addAction(
				icons.icon_of(source.category), _("Open the {title} tab").format(title=title)
			)
			open_.triggered.connect(lambda _ticked=False, title=title: self.tab_manager.open_list(title))

		for title, source in TABS:
			add_open_action(source, title)
		grid = display_menu.addAction(icons.icon("grid"), _("Open the Time grid tab"))
		grid.triggered.connect(self._open_calendar)
		simulation = display_menu.addAction(icons.icon("simulation"), _("Open the Simulation tab"))
		simulation.triggered.connect(self._open_simulation)
		airplay = display_menu.addAction(icons.icon("airplay"), _("Open the Airplay tab"))
		airplay.triggered.connect(self._open_airplay)
		# Les comptes de l'intranet et de l'API (https://github.com/dascritch/machincast/issues/537).
		api = display_menu.addAction(icons.icon("api"), _("Open the API tab"))
		api.triggered.connect(self._open_api)
		self.preview_action = display_menu.addAction(icons.icon("preview"), _("Pre-listen…"))
		self.preview_action.triggered.connect(lambda: self._preview(None))
		display_menu.addSeparator()
		# Les onglets fermés, à rouvrir (https://github.com/dascritch/machincast/issues/428).
		self.tab_manager.add_reopening(display_menu)
		# En bas du menu (https://github.com/dascritch/machincast/issues/322).
		# F5 relit les onglets, sans entrée de menu (https://github.com/dascritch/machincast/issues/532).
		QShortcut(QKeySequence("F5"), self).activated.connect(self.refresh)
		# https://github.com/dascritch/machincast/issues/398 : relu à chaque ouverture.
		self.tabs_menu = self.menuBar().addMenu(_("&Tabs"))
		self.tabs_menu.aboutToShow.connect(lambda: self.tab_manager.list_tabs(self.tabs_menu))
		# https://github.com/dascritch/machincast/issues/528 : le tableau de l'onglet affiché.
		self.table_menu = table_menu.TableMenu(self.menuBar().addMenu(_("Ta&ble")), self.ui.tabs)
		self.broadcast_menu = self.menuBar().addMenu(_("&Broadcast"))
		self.broadcast_menu.aboutToShow.connect(self.broadcast.reread_service)
		# L'écoute de l'antenne, lancée aussitôt, en tête du menu (https://github.com/dascritch/machincast/issues/245) ;
		# pendant l'écoute, elle l'arrête, et Alt+P fait l'un ou l'autre (https://github.com/dascritch/machincast/issues/256).
		self.listen = self.broadcast_menu.addAction(icons.icon("preview"), "")
		self.listen.setShortcut(QKeySequence("Alt+P"))
		self.listen.triggered.connect(self._switch_listening)
		self._show_listening(False)
		self.broadcast_menu.addSeparator()
		# Démarrer ou arrêter : seule l'entrée qui sert est montrée (https://github.com/dascritch/machincast/issues/530).
		self.controlled_list: dict[str, QAction] = {}
		for verb, (entry, _success, _failure) in control.VERBS.items():
			action = self.broadcast_menu.addAction(icons.icon(verb), entry)
			action.triggered.connect(lambda _ticked=False, verb=verb: self.broadcast.run(verb))
			self.controlled_list[verb] = action
		self.broadcast_menu.addSeparator()
		# Recommencer, Sauter, Insérer après ce sonore, Couper (https://github.com/dascritch/machincast/issues/530) ; la
		# coupure par le secours est relue à l'ouverture du menu, et quand la grille change
		# (https://github.com/dascritch/machincast/issues/323).
		self.on_air_menu = interruption.OnAirMenu(
			self.broadcast_menu,
			self.connection,
			interruption.Requests(self.broadcast.interrupt, self.broadcast.cut_by_fallback, self.broadcast.insert),
			self,
		)
		self.interruptions = self.on_air_menu.actions
		self.cutoff_by_fallback = self.on_air_menu.fallback
		self.broadcast_menu.aboutToShow.connect(self.broadcast.reread_fallback)
		maintenance = self.menuBar().addMenu(_("&Maintenance"))
		_upcoming(
			maintenance.addAction(_("Output monitor…")), "ticket 85"
		)  # https://github.com/dascritch/machincast/issues/85
		maintenance.addSeparator()
		self.indexings: dict[bool, QAction] = {}
		"""L'action de chaque mode, selon full_audit : grisée tant que son indexation tourne."""
		for full_audit in (False, True):
			action = maintenance.addAction(TITLES[full_audit])
			action.triggered.connect(lambda _ticked=False, audit=full_audit: self._index(full_audit=audit))
			self.indexings[full_audit] = action
		# Où en sont les indexations (https://github.com/dascritch/machincast/issues/392).
		self.indexing_status = maintenance.addAction(_("Indexing status…"))
		self.indexing_status.triggered.connect(self._show_indexing_status)
		self.status_window: indexing_status.StatusWindow | None = None
		maintenance.addSeparator()
		# Grisée pendant toute indexation lancée d'ici : ses migrations attendraient la base
		# (https://github.com/dascritch/machincast/issues/127).
		self.database_maintenance = maintenance.addAction(control.MAINTENANCE)
		self.database_maintenance.triggered.connect(self._maintain_database)
		# L'export de la base, pour un plan de reprise d'activité (https://github.com/dascritch/machincast/issues/347).
		self.export = maintenance.addAction(control.EXPORT)
		self.export.triggered.connect(self._export_database)
		self.exporting = control.Export(self)
		self.exporting.finished.connect(self._exported_database)
		# La lecture des sonores par le service de diffusion (https://github.com/dascritch/machincast/issues/381).
		self.grant_read = maintenance.addAction(control.GRANT_READ)
		self.grant_read.triggered.connect(self.broadcast.grant_read_files)
		maintenance.aboutToShow.connect(self.broadcast.reread_grant_read)
		self.broadcast.reread_grant_read()
		# Où déposer des sonores, et ce qu'occupe chaque banque (https://github.com/dascritch/machincast/issues/533).
		maintenance.addAction(disk_space.TITLE + "…").triggered.connect(self.show_disk_space)
		help_ = self.menuBar().addMenu(_("&Help"))
		# L'aide de l'onglet affiché, en page et en infobulles (https://github.com/dascritch/machincast/issues/534).
		self.tab_help = help_.addAction(tab_help.label(None))
		self.tab_help.triggered.connect(self._open_tab_help)
		self.contextual_help = tab_help.ContextualHelp(self)
		self.contextual = help_.addAction(tab_help.CONTEXTUAL)
		self.contextual.setShortcut(QKeySequence(tab_help.SHORTCUT))
		self.contextual.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
		self.contextual.triggered.connect(self._toggle_contextual_help)
		help_.addSeparator()
		help_.addAction(_("Documentation")).triggered.connect(lambda: dialogs.open_page(version.documentation()))
		# Le document de l'équipe et son lien (https://github.com/dascritch/machincast/issues/451).
		help_.addAction(installation_notes.NOTES).triggered.connect(self._open_notes)
		self.team_link = help_.addAction(installation_notes.TEAM_LINK)
		self.team_link.triggered.connect(lambda: installation_notes.open_team_link(self.configuration))
		self._show_team_link()
		help_.addAction(_("Report a problem…")).triggered.connect(lambda: dialogs.open_page(TICKETS))
		help_.addAction(_("Version")).triggered.connect(
			lambda: dialogs.show_version(self, version.text(), version.of_the_version())
		)
		for menu in (file, display_menu, self.tabs_menu, self.broadcast_menu, maintenance, help_):
			menu.setToolTipsVisible(True)

	def _help_kind(self) -> str | None:
		"""Le genre de l'onglet affiché, pour son aide."""
		screen = self.ui.tabs.currentWidget()
		category = None
		if isinstance(screen, Card):
			category = screen.category
		return tab_help.kind_of(self.tab_manager.tab_key(screen), category)

	def _follow_help(self) -> None:
		"""« Aide sur … » nomme le genre de l'onglet affiché, et l'aide contextuelle suit ses éléments."""
		kind = self._help_kind()
		self.tab_help.setText(tab_help.label(kind))
		self.tab_help.setEnabled(kind is not None)
		self.contextual_help.follow(self.ui.tabs.currentWidget(), kind)

	def _open_tab_help(self) -> None:
		kind = self._help_kind()
		if kind is not None:
			dialogs.open_page(tab_help.address(kind, version.documentation()))

	def _toggle_contextual_help(self) -> None:
		"""F1 : l'aide contextuelle s'active, et l'entrée propose de la désactiver ; ou l'inverse."""
		if self.contextual_help.toggle():
			self.contextual.setText(tab_help.DISABLE_CONTEXTUAL)
			self.ui.state_bar.showMessage(tab_help.ACTIVE)
			return
		self.contextual.setText(tab_help.CONTEXTUAL)
		self.ui.state_bar.clearMessage()

	def _open_notes(self) -> None:
		self.statusBar().showMessage(installation_notes.open_notes(self.configuration))

	def _show_team_link(self) -> None:
		"""« Lien de l'équipe… » est inactive sans adresse, et son infobulle dit où la donner."""
		active = installation_notes.settings(self.configuration).team_link is not None
		self.team_link.setEnabled(active)
		tooltip = ""
		if not active:
			tooltip = installation_notes.WITHOUT_TEAM_LINK
		self.team_link.setToolTip(tooltip)

	def _show_news(self) -> None:
		"""Une seule fois par version, et par compte : la version vue est retenue dans les réglages des vues."""
		news = version.of_the_version()
		settings = columns.settings()
		if (news is None) or (settings.value(version.NEWS_KEY) == news.version):
			return
		dialogs.show_news(self, news)
		settings.setValue(version.NEWS_KEY, news.version)

	def show_disk_space(self) -> None:
		"""La fenêtre « Espace disque », une à la fois, relue à chaque ouverture."""
		if self.disk_space is not None:
			self.disk_space.close()
		self.disk_space = disk_space.DiskSpaceWindow(self.connection, self, access.service_account())
		self.disk_space.show()

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
		cards = []
		for index in range(tabs.count()):
			if isinstance(card := tabs.widget(index), Card):
				cards.append(card)
		return cards

	def _sound_cards(self) -> str:
		"""Les périphériques de l'antenne et de la pré-écoute, tels que le fichier de configuration les donne alors."""
		audio = self.audio
		if self.configuration is not None:
			with contextlib.suppress(InvalidConfiguration, OSError):
				audio = load(self.configuration).audio
		return crash.sound_cards(audio, preview=True)

	def _shown_tab(self) -> str:
		"""Le titre complet de l'onglet au premier plan."""
		index = self.ui.tabs.currentIndex()
		if index < 0:
			return "—"
		return self.tab_manager.full_title(index)

	def _prelistened(self) -> str:
		"""Le fichier ou le stream de la pré-écoute, s'il y en a un."""
		if self.preview is None:
			source = None
		else:
			source = self.preview.player.source
		if source is None:
			return "—"
		return f"{source.title} : {source.address}"

	def closeEvent(self, event: QCloseEvent) -> None:
		"""Ferme la fenêtre, sauf si une fiche refuse de se fermer ; les onglets ouverts sont retenus et les écrans arrêtés."""
		for card in self.cards():
			if not card.can_close():
				event.ignore()
				return
		self.tab_manager.retain_tabs()
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
		for key in (SOUND_CARDS, WPCTL_STATUS, PRELISTENED, SHOWN_TAB):
			crash.provide(key, None)
		if self.preview is not None:
			self.preview.close()
		super().closeEvent(event)

	def _reopen(self, key: str) -> None:
		"""Rouvre un onglet retenu ; un onglet fixe l'est déjà, une clé inconnue est ignorée."""
		category, _separator, rest = key.partition(":")
		match category:
			case _ if (category == "list") and (rest in ON_DEMAND):
				self.tab_manager.open_list(rest)
			case "search":
				self._open_search(rest)
			case "simulation":
				self._open_simulation()
			case "airplay":
				self._open_airplay()
			case "api":
				self._open_api()
			case "card":
				card_type, _separator, identifier = rest.partition(":")
				if (card_type in CARD_TABLES) and (identifier.isdigit()):
					if self._in_database(card_type, int(identifier)):
						self._open_card(card_type, int(identifier))
					else:
						log.info(
							_(
								"card {card_type} {identifier} forgotten: the element is no longer in the database"
							).format(card_type=card_type, identifier=identifier)
						)

	def _in_database(self, category: str, identifier: int) -> bool:
		"""L'élément est en base, et n'est pas supprimé."""
		table = CARD_TABLES[category]
		with self.connection.transaction():
			return cards_queries.exists(self.connection, table, identifier, not_deleted=table in DELETABLE)

	def _open_card(self, category: str, identifier: int | None) -> None:
		"""Ouvre la fiche d'un élément, ou ramène au premier plan celle déjà ouverte ; None pour un nouvel élément."""
		for opened in self.cards():
			if (identifier is not None) and (opened.category == category) and (opened.identifier == identifier):
				self.ui.tabs.setCurrentWidget(opened)
				return
		card = CARDS[category](self.connection, identifier, self.clock)
		card.changed_title.connect(lambda title: self._rename(card, title))
		card.requested_opening.connect(self._open)
		card.deleted.connect(lambda: self._remove(card, remembered=False))
		# « Enregistrer » a réussi : l'onglet se ferme (https://github.com/dascritch/machincast/issues/382).
		card.finished.connect(lambda: self._remove(card))
		card.requested_duplication.connect(self._duplicate)
		card.requested_preview.connect(self._preview)
		if isinstance(card, SoundCard):
			card.requested_check.connect(lambda sound, force, card=card: self._check_fully(card, sound, force=force))
		if category == "event":
			card.deleted.connect(self._guarantee_background_programming)
			card.saved.connect(self._guarantee_background_programming)
		if isinstance(card, EventCard):
			# Une session rétablie depuis la fiche (https://github.com/dascritch/machincast/issues/295), comme depuis le
			# calendrier : la barre d'état l'annonce, et Machin player relit la grille.
			card.restored_session.connect(self.ui.state_bar.showMessage)
			card.restored_session.connect(self.broadcast.modified_grid)
		# Une fiche enregistrée, supprimée ou restaurée vaut aussitôt à l'antenne
		# (https://github.com/dascritch/machincast/issues/266) : Machin player relit la grille, et ne recalcule que si
		# ce qui règle l'antenne a changé. Un sonore ou une banque supprimé quitte les listes des événements.
		card.saved.connect(self.broadcast.modified_grid)
		card.deleted.connect(self.broadcast.modified_grid)
		self.tab_manager.add_tab(card, card.title())
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

	def _check_fully(self, card: SoundCard, sound: int, *, force: bool = False) -> None:
		"""L'audit complet du sonore, au seuil de silence de la configuration ; sa fiche attend. force : même un fichier
		déjà audité est relu (https://github.com/dascritch/machincast/issues/388)."""
		card.wait_check()
		self.full_check.launch(sound, self.silence_threshold, force=force)

	def _full_finished_check(self, sound: int, text: str) -> None:
		"""La barre d'état le dit ; la fiche du sonore, encore ouverte, propose de se rafraîchir."""
		self.ui.state_bar.showMessage(text)
		for card in self.cards():
			if (isinstance(card, SoundCard)) and (card.identifier == sound):
				card.finished_check(text)

	def _rename(self, card: QWidget, title: str) -> None:
		self.tab_manager.title_tab(self.ui.tabs.indexOf(card), title)

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

	def _show_listening(self, ongoing: bool) -> None:  # noqa: FBT001  # signal de Qt : le booléen arrive par sa position
		text, tooltip = LISTENING[ongoing]
		self.listen.setText(text)
		display.set_preview(self.listen, active=True, tooltip=tooltip)
		self.home.ui.monitor.setText(text)
		display.set_preview(self.home.ui.monitor, active=True, tooltip=tooltip)

	def _follow_preview(self) -> None:
		"""Sur l'entrée « Sortie factice » de la pré-écoute, ses boutons et ses entrées de menu sont grisés, partout
		(https://github.com/dascritch/machincast/issues/339) : ceux de la fenêtre, de l'onglet Antenne et des fiches de
		sonores ouvertes ; les menus contextuels le sont à leur ouverture."""
		display.disable_preview(disabled=self.audio.disabled_preview())
		display.set_preview(self.preview_action, active=True, tooltip=self.preview_action.text())
		ongoing = (self.preview is not None) and (self.preview.on_air_listening())
		self._show_listening(ongoing)
		self.home.follow_preview()
		tabs = self.ui.tabs
		for index in range(tabs.count()):
			screen = tabs.widget(index)
			if isinstance(screen, SoundCard):
				screen.follow_preview()

	def _listen_on_air(self, launch: bool = False) -> None:  # noqa: FBT001, FBT002  # signal de Qt : le booléen arrive par sa position
		"""Clic sur le VU-mètre de l'onglet Antenne : l'antenne dans la fenêtre de pré-écoute
		(https://github.com/dascritch/machincast/issues/24) ; par le bouton « Pré-écoute » de la fenêtre, lancée
		aussitôt (https://github.com/dascritch/machincast/issues/223)."""
		self._preview(None)
		# Désactivée, la pré-écoute ne s'ouvre pas (https://github.com/dascritch/machincast/issues/339).
		if self.preview is None:
			return
		self.preview.listen_on_air(self._public_text, launch=launch)

	def _follow_public_text(self, state: PlaybackState) -> None:
		self._public_text = None
		if state.ongoing is not None:
			self._public_text = state.ongoing.public_text
		if self.preview is not None:
			self.preview.follow_on_air(self._public_text)

	def _open_calendar(self) -> None:
		"""Le calendrier, onglet fixe, revient au premier plan (https://github.com/dascritch/machincast/issues/307)."""
		self.ui.tabs.setCurrentWidget(self.calendar)

	def _open_search(self, text: str | None = None) -> None:
		"""Ctrl+F : un nouvel onglet de recherche, le curseur dans son champ ; sur une recherche encore vide, le curseur
		y va seulement (https://github.com/dascritch/machincast/issues/502). Une recherche rouverte, fermée ou retenue
		au lancement, reprend son texte."""
		tabs = self.ui.tabs
		current = tabs.currentWidget()
		if (text is None) and (isinstance(current, SearchScreen)) and (current.field.text().strip() == ""):
			current.focus()
			return
		search = SearchScreen(self.connection)
		search.opened.connect(self._open)
		search.field.textChanged.connect(lambda _text: self._title_search(search))
		self.tab_manager.add_tab(search, search.title())
		if text is not None:
			search.field.setText(text)
		tabs.setCurrentWidget(search)
		search.focus()

	def _title_search(self, search: SearchScreen) -> None:
		"""L'onglet d'une recherche est titré de son texte, au fil de la frappe."""
		index = self.ui.tabs.indexOf(search)
		if index >= 0:
			self.tab_manager.title_tab(index, search.title())

	def _open_simulation(self) -> None:
		"""Un seul onglet de simulation (https://github.com/dascritch/machincast/issues/37) : celui qui est ouvert
		revient au premier plan, avec son résultat."""
		tabs = self.ui.tabs
		opened_list = []
		for index in range(tabs.count()):
			opened_list.append(tabs.widget(index))
		simulation = None
		for screen in opened_list:
			if isinstance(screen, SimulationScreen):
				simulation = screen
				break
		if simulation is None:
			simulation = SimulationScreen(self.clock, self.configuration)
			self.tab_manager.add_tab(simulation, _("Simulation"))
		tabs.setCurrentWidget(simulation)

	def _open_airplay(self) -> None:
		"""Un seul onglet Airplay (https://github.com/dascritch/machincast/issues/244) : celui qui est ouvert revient au
		premier plan. Il se relit quand l'onglet Antenne voit un nouveau sonore."""
		tabs = self.ui.tabs
		opened_list = []
		for index in range(tabs.count()):
			opened_list.append(tabs.widget(index))
		airplay = None
		for screen in opened_list:
			if isinstance(screen, AirplayScreen):
				airplay = screen
				break
		if airplay is None:
			airplay = AirplayScreen(self.connection, self.clock, self._metadata())
			airplay.opened.connect(self._open)
			airplay.requested_preview.connect(self._preview)
			airplay.announces.connect(self.ui.state_bar.showMessage)
			self.home.reread_airplay.connect(airplay.refresh)
			self.tab_manager.add_tab(airplay, _("Airplay"))
		tabs.setCurrentWidget(airplay)

	def _open_api(self) -> None:
		"""Un seul onglet « API » : celui qui est ouvert revient au premier plan."""
		tabs = self.ui.tabs
		api = None
		for index in range(tabs.count()):
			screen = tabs.widget(index)
			if isinstance(screen, ApiScreen):
				api = screen
		if api is None:
			api = ApiScreen(self.connection)
			api.announces.connect(self.ui.state_bar.showMessage)
			self.tab_manager.add_tab(api, _("API"))
		tabs.setCurrentWidget(api)

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
		if isinstance(card, (SearchScreen, SimulationScreen, AirplayScreen, ApiScreen)):
			if isinstance(card, AirplayScreen):
				self.home.reread_airplay.disconnect(card.refresh)
			if isinstance(card, SimulationScreen):
				card.shut_down()
			self.tab_manager.remove_tab(index)
			card.deleteLater()
			return
		if isinstance(card, List):
			# Une liste à la demande est gardée : rouverte, elle retrouve son filtre et son tri.
			self.tab_manager.remove_tab(index)
			return
		assert isinstance(card, Card), card
		if card.can_close():
			self._remove(card)

	def _remove(self, card: Card, *, remembered: bool = True) -> None:
		"""Ferme l'onglet de la fiche, sans rien lui demander ; celle d'un élément supprimé n'est pas à rouvrir."""
		self.tab_manager.remove_tab(self.ui.tabs.indexOf(card), remembered=remembered)
		card.shut_down()
		card.deleteLater()

	def _act(self, list_: List, key: str, items: list[int]) -> None:
		"""Une action sur la sélection d'une liste (https://github.com/dascritch/machincast/issues/114) : le choix des
		banques s'il en faut, la confirmation, puis l'action en une transaction ; la liste se relit et la barre d'état
		annonce ce qui a changé. Un choix abandonné, ou une confirmation refusée, ne change rien."""
		action = groups.action(list_.source.category, key)
		banks: list[int] = []
		try:
			match action.choice:
				case "toutes":
					banks = dialogs.choose_banks(self, self.connection, ADDITION_TO_BANKS)
				case "leurs":
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
		# Le service de diffusion, sous son propre compte, doit pouvoir les lire ; jamais dans un répertoire
		# personnel (https://github.com/dascritch/machincast/issues/381).
		screening = service_access.screen(self, paths)
		paths = screening.accepted
		if paths == []:
			self.ui.state_bar.showMessage(screening.text())
			return
		try:
			adding = add_files(self.connection, paths)
		except psycopg.Error as error:
			log.error(_("addition of files impossible: {error}").format(error=error))
			self.ui.state_bar.showMessage(_("Addition impossible: {error}").format(error=error))
			return
		self.ui.state_bar.showMessage(" ".join([adding.text(), *screening.messages]))
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
		response = dialogs.suggest(self, gaps, self.broadcast.service)
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

	def _export_database(self) -> None:
		"""Machin backup-db dans le répertoire des sauvegardes de la configuration, sans terminal ; l'entrée est inactive
		jusqu'à sa fin, que la barre d'état annonce (https://github.com/dascritch/machincast/issues/347)."""
		self.export.setEnabled(False)
		directory = control.maintenance_backups(self.configuration)
		self.statusBar().showMessage(self.exporting.start(self.configuration, directory))

	def _exported_database(self, text: str) -> None:
		self.export.setEnabled(True)
		self.statusBar().showMessage(text)

	def _show_indexing_status(self) -> None:
		"""Une seule fenêtre de statut : la rouvrir la ramène au premier plan."""
		if self.status_window is None:
			self.status_window = indexing_status.StatusWindow(self.connection, self)
		self.status_window.open_()

	def _index(self, *, full_audit: bool) -> bool:
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
		def follow_full_audit(*, full_audit: bool, number: int) -> None:
			if indexer.active_process(number):
				return
			del self.launched_indexings[full_audit]
			self.indexings[full_audit].setEnabled(True)
			self.ui.state_bar.showMessage(
				_("{title} {finished}; F5 refreshes the tabs and shows its changes.").format(
					title=TITLES[full_audit], finished=FINISHED[full_audit]
				)
			)

		for full_audit, number in list(self.launched_indexings.items()):
			follow_full_audit(full_audit=full_audit, number=number)
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
		# Dans le journal, que l'achèvement d'un rapport de crash reprend
		# (https://github.com/dascritch/machincast/issues/413).
		if index >= 0:
			log.info(_("tab shown: {title}").format(title=self.tab_manager.full_title(index)))
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

	def _preferences(self, kind: preferences.Kind = preferences.SERVICE) -> None:
		"""Les préférences réglées s'enregistrent dans le fichier de configuration, puis valent pour les fiches
		ouvertes ensuite ; un fichier qui ne s'écrit pas les laisse inchangées, et la barre d'état le dit. Un seuil de
		silence changé relance l'audit complet (https://github.com/dascritch/machincast/issues/401). kind : la fenêtre
		des préférences de l'interface, ou celle des paramètres du service ; des paramètres du service changés
		redémarrent la diffusion, et reviennent si elle ne redémarre pas
		(https://github.com/dascritch/machincast/issues/389)."""
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
			output=audio.output,
			table_rows=preferences.table_rows(),
			daily=self.daily,
			backup_directory=control.maintenance_backups(self.configuration),
			notes=installation_notes.settings(self.configuration).notes,
			team_link=installation_notes.settings(self.configuration).team_link,
		)
		# L'état du service, lu à l'ouverture : en marche, la carte de l'antenne ne se choisit pas
		# (https://github.com/dascritch/machincast/issues/339).
		self.broadcast.reread_service()
		settings = dialogs.set_preferences(
			self, shown_list, audio.output, self.broadcast.service, kind, configuration=self.configuration
		)
		if settings is None:
			return
		try:
			former = self.configuration.read_text(encoding="utf-8")
			preferences.write(self.configuration, settings)
		except OSError as error:
			self.statusBar().showMessage(
				_("Preferences not saved in {configuration}: {error}").format(
					configuration=self.configuration, error=error
				)
			)
			return
		text = self.apply_preferences(settings)
		if not preferences.service_changed(shown_list, settings):
			self.statusBar().showMessage(text)
			return
		self.broadcast.reread_service()
		if (self.broadcast.service.installed) and (self.broadcast.service.running):
			# Le redémarrage demande le mot de passe d'un administrateur : refusé, les paramètres reviennent.
			self.broadcast.restoring = (former, shown_list)
			self.statusBar().showMessage(RESTARTING_FOR_SETTINGS)
			self.broadcast.control.control("restart")
			return
		self.statusBar().showMessage(text)

	def apply_preferences(self, settings: preferences.Settings) -> str:
		"""Les réglages valent dans l'interface ; ce qu'en dit la barre d'état."""
		assert self.configuration is not None
		audio = self.audio
		preferences.define(settings.crossfades)
		preferences.define_retention(settings.retention)
		self._show_team_link()
		preferences.define_table_rows(settings.table_rows)
		self.daily = settings.daily
		new_threshold = settings.silence_threshold != self.silence_threshold
		self.silence_threshold = settings.silence_threshold
		self.dead_air = settings.dead_air
		self.clipping = settings.clipping
		self.suggestions = settings.suggestions
		self.home.show_clipping(poster=self.clipping)
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
		return (
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
		if self._index(full_audit=True):
			return _("Silence threshold changed: full audit launched, in its own window.")
		return _("Silence threshold changed: full audit impossible, Machin indexer could not be launched.")

	def show_status(self) -> None:
		"""Le statut coloré de la diffusion, sur l'onglet Antenne, et le titre de la fenêtre, selon le service et l'état
		de la diffusion (https://github.com/dascritch/machincast/issues/495)."""
		installed = self.broadcast.service.installed
		broadcasting = self.home.state.state == "playing"
		self.home.ui.playback_state.setStyleSheet(
			broadcast_status.style(installed=installed, broadcasting=broadcasting)
		)
		indicator = broadcast_status.NOT_BROADCASTING
		# Un blanc à l'antenne garde le témoin de couleur : la diffusion tourne, sans rien à jouer.
		if self.home.state.state in broadcast_status.ON_AIR_STATES:
			indicator = INCOMPLETE_SERVICE
			if installed:
				indicator = INSTALLED_SERVICE
		self.setWindowTitle(broadcast_status.window_title(indicator, self.station))

	def _flag_on_air(self) -> None:
		"""Sans périphérique d'antenne, sur une vraie sortie, Machin player refuse de diffuser : la barre d'état le
		dit."""
		self.to_fill_in_on_air.setVisible(self.audio.to_fill_in_on_air())

	def _screen_saver_changed(self) -> None:
		"""La veille de la session ferme le port de monitoring de l'antenne ; son retour le rouvre
		(https://github.com/dascritch/machincast/issues/346)."""
		if self.screen_saver.asleep:
			self.home.monitor.pause()
		else:
			self.home.monitor.resume()

	def _open(self, category: str, identifier: int, _name: str) -> None:
		self.requested_detail.emit(category, identifier)
		self._open_card(category, identifier)


def _upcoming(action: QAction, tickets: str) -> None:
	"""Une infobulle ne porte pas de lien : elle nomme le ticket par son numéro, sans « # »."""
	action.setEnabled(False)
	action.setToolTip(_("Upcoming: {tickets} on GitHub").format(tickets=tickets))


def _titles(titles: list[str]) -> str:
	title_list = []
	for title in titles:
		title_list.append(_("“{title}”").format(title=title))
	return ", ".join(title_list)
