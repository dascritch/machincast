"""Le pilotage de la diffusion depuis la fenêtre de Machin_interface (https://github.com/dascritch/machincast/issues/440).

BroadcastControl suit l'état du service de diffusion et le pilote : démarrer, arrêter, redémarrer (machincast.interface.control,
https://github.com/dascritch/machincast/issues/25), ou lancer ou arrêter la diffusion d'essai sans service ; il redémarre
la diffusion après des paramètres du service changés, et les rétablit si elle ne redémarre pas
(https://github.com/dascritch/machincast/issues/389). Il propose les interruptions de l'antenne, par le secours, par un
feed, du sonore en cours, et l'avance de l'événement suivant (https://github.com/dascritch/machincast/issues/323), et
demande à Machin player de relire la grille. Les entrées de menu, la barre d'état et l'onglet Antenne restent à la
fenêtre, qu'il met à jour.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMenu

from machincast import access, created_files, service
from machincast.i18n import _
from machincast.interface import control, dialogs, interruption, preferences
from machincast.interface.state import STOP, PlaybackState
from machincast.interface.tab_manager import ON_AIR
from machincast.player.state import (
	advance_request,
	cutoff_request_by_fallback,
	cutoff_request_by_feed,
	insertion_request,
	interruption_request,
	request_reread_grid,
)

INCOMPLETE_SERVICE, INSTALLED_SERVICE = "🟩", "🟥"
"""Le témoin du service de diffusion, devant le titre de l'onglet Antenne : pas complètement installé, ou installé."""
WITHOUT_SERVICE_START = _("Without a service: Machin player in a terminal window")
WITHOUT_TRIAL = _("No trial broadcast running")
TRIAL_HALT = _("Without a service: stops the Machin player launched by hand, like Ctrl-C")
ALREADY_RUNNING = _("The trial broadcast is already running")
SETTINGS_RESTORED = _(
	"Broadcast not restarted: the former broadcast service settings are back, in the configuration file and in the "
	"interface."
)

if TYPE_CHECKING:
	from machincast.interface.window import MainWindow


class BroadcastControl(QObject):
	"""L'état du service de diffusion, ses commandes, et les interruptions de l'antenne."""

	def __init__(self, window: "MainWindow") -> None:
		super().__init__(window)
		self.window = window
		self.control = control.Control(window)
		self.control.finished.connect(self.finished_control)
		self.control.restarted.connect(self.restarted)
		self.control.not_started.connect(lambda text, journal: dialogs.warn_not_started(window, text, journal))
		self.service = service.ABSENT
		"""L'état du service de diffusion, relu au lancement, à l'ouverture du menu et après chaque commande."""
		self.restoring: tuple[str, preferences.Settings] | None = None
		"""Le fichier de configuration et les réglages d'avant des paramètres du service, le temps que la diffusion
		redémarre (https://github.com/dascritch/machincast/issues/389)."""
		self._requested_stop = False
		"""Sans service : l'arrêt de la diffusion d'essai, demandé depuis le menu, est à annoncer quand il a lieu."""
		self._on_air: PlaybackState = STOP
		"""Le dernier état de Machin player, pour les coupures proposées."""
		self._fallback: list[interruption.Fallback] = []
		"""Les événements de secours, relus à l'ouverture du menu « Diffusion » et quand la grille change."""

	def reread_service(self) -> None:
		self.service = service.read_state()
		self.present_broadcast()

	def playback_state(self, state: PlaybackState) -> None:
		"""La diffusion d'essai arrêtée depuis le menu : l'annoncer."""
		if (state.state != "stopped") or (not self._requested_stop):
			return
		self._requested_stop = False
		self.window.ui.state_bar.showMessage(control.STOPPED)

	def offer_interruptions(self, state: PlaybackState) -> None:
		"""Les interruptions du menu « Diffusion » suivent ce qui est à l'antenne, comme la coupure par le secours, et
		le clic droit sur un feed (https://github.com/dascritch/machincast/issues/323)."""
		self._on_air = state
		self.window.on_air_menu.offer(state, self._fallback)

	def reread_fallback(self) -> None:
		self._fallback = interruption.read_fallback(self.window.connection)
		self.fill_fallback()

	def fill_fallback(self) -> None:
		self.window.on_air_menu.offer(self._on_air, self._fallback)

	def cut_by_fallback(self, fallback: interruption.Fallback) -> None:
		"""Demande à Machin player de couper l'antenne par ce secours, sans question."""
		announces = interruption.CUTOFF_WITHOUT_PLAYBACK
		if self.window.home.client.send(cutoff_request_by_fallback(fallback.identifier)):
			announces = interruption.fallback_announcement(fallback.name)
		self.window.ui.state_bar.showMessage(announces)

	def cut_by_feed(self, feed: int, name: str) -> None:
		"""Demande à Machin player de couper l'antenne par le stream de ce feed, sans question."""
		announces = interruption.CUTOFF_WITHOUT_PLAYBACK
		if self.window.home.client.send(cutoff_request_by_feed(feed)):
			announces = interruption.feed_announcement(name)
		self.window.ui.state_bar.showMessage(announces)

	def feed_menu(self, menu: QMenu, feed: int, name: str) -> None:
		interruption.fill_feed(
			menu, self._on_air, self.window.connection, feed, name, self.window._preview, self.cut_by_feed
		)

	def modified_grid(self) -> None:
		"""Une session sautée ou rétablie (https://github.com/dascritch/machincast/issues/273), une fiche enregistrée,
		supprimée ou restaurée (https://github.com/dascritch/machincast/issues/266) valent aussitôt à l'antenne :
		Machin player relit la grille, s'il diffuse ; sinon, il la lira à son démarrage. Les événements de secours
		ont pu changer."""
		self.window.home.client.send(request_reread_grid())
		self.reread_fallback()

	def interrupt(self, item: str) -> None:
		"""Demande à Machin player d'interrompre l'élément, sans question : l'antenne n'attend pas."""
		announces = interruption.WITHOUT_PLAYBACK
		if self.window.home.client.send(interruption_request(item)):
			announces = interruption.ANNOUNCEMENTS[item]
		self.window.ui.state_bar.showMessage(announces)

	def insert(self, category: str, identifier: int, name: str) -> None:
		"""Demande à Machin player de jouer, après le sonore en cours, cette séquence ou un sonore de cette banque, sans
		question (https://github.com/dascritch/machincast/issues/530)."""
		request = insertion_request(bank=identifier)
		if category == "sequence":
			request = insertion_request(sequence=identifier)
		announces = interruption.INSERTION_WITHOUT_PLAYBACK
		if self.window.home.client.send(request):
			announces = interruption.insertion_announcement(category, name)
		self.window.ui.state_bar.showMessage(announces)

	def advance(self, event: int, name: str) -> None:
		"""Demande à Machin player d'avancer l'événement suivant qu'il a annoncé, sans question
		(https://github.com/dascritch/machincast/issues/257)."""
		announces = interruption.ADVANCE_WITHOUT_PLAYBACK
		if self.window.home.client.send(advance_request(event)):
			announces = interruption.advance_announcement(name)
		self.window.ui.state_bar.showMessage(announces)

	def present_broadcast(self) -> None:
		"""Les entrées du menu « Diffusion » selon l'état du service ; sans lui, le signal d'installation à terminer. Le
		titre de l'onglet Antenne en porte le témoin (https://github.com/dascritch/machincast/issues/322)."""
		self.window.without_service.setVisible(not self.service.installed)
		indicator = INCOMPLETE_SERVICE
		if self.service.installed:
			indicator = INSTALLED_SERVICE
		index = self.window.ui.tabs.indexOf(self.window.home)
		self.window.tab_manager.title_tab(index, f"{indicator} {ON_AIR}")
		self.window.show_status()
		if self.service.installed:
			# En marche : arrêter ; arrêté ou en échec : démarrer. Seule l'entrée qui sert est montrée
			# (https://github.com/dascritch/machincast/issues/530).
			allowed = {"start": not self.service.running, "stop": self.service.running}
			for verb, action in self.window.controlled_list.items():
				action.setText(control.VERBS[verb][0])
				action.setEnabled(allowed[verb])
				action.setVisible(allowed[verb])
				action.setToolTip("")
			return
		ongoing = self.window.home.client.player_pid() is not None
		tooltips = {"start": WITHOUT_SERVICE_START, "stop": WITHOUT_TRIAL}
		if ongoing:
			tooltips = {"start": ALREADY_RUNNING, "stop": TRIAL_HALT}
		for verb, action in self.window.controlled_list.items():
			action.setText(control.TRIAL[verb])
			action.setEnabled((verb == "start") != ongoing)
			action.setVisible((verb == "start") != ongoing)
			action.setToolTip(tooltips[verb])

	def run(self, verb: str) -> None:
		if self.service.installed:
			self.control.control(verb)
			return
		if verb == "start":
			self.window.ui.state_bar.showMessage(control.launch_in_terminal(self.window.configuration))
			return
		pid = self.window.home.client.player_pid()
		if pid is None:
			# Le menu relu à son ouverture n'active l'entrée qu'avec une diffusion d'essai : elle vient de s'arrêter.
			return
		text = control.halt_player(pid)
		self.window.ui.state_bar.showMessage(text)
		self._requested_stop = text == control.REQUESTED_STOP

	def finished_control(self, text: str) -> None:
		self.window.ui.state_bar.showMessage(text)
		self.reread_service()

	def restarted(self, success: bool) -> None:  # noqa: FBT001  # signal de Qt : le booléen arrive par sa position
		"""La diffusion redémarrée prend les nouveaux paramètres ; sinon, les précédents reviennent, dans le fichier et
		dans l'interface (https://github.com/dascritch/machincast/issues/389)."""
		restoring = self.restoring
		self.restoring = None
		if (restoring is None) or (success):
			return
		former, previous = restoring
		assert self.window.configuration is not None
		try:
			created_files.write_text(self.window.configuration, former)
		except OSError as error:
			self.window.statusBar().showMessage(
				_(
					"Broadcast not restarted, and the former settings could not be written back in {configuration}: "
					"{error}"
				).format(configuration=self.window.configuration, error=error)
			)
			return
		self.window.apply_preferences(previous)
		self.window.statusBar().showMessage(SETTINGS_RESTORED)

	def reread_grant_read(self) -> None:
		"""Sans compte du service, Machin player lit avec le compte qui le lance : rien à donner."""
		installed = access.service_account() is not None
		self.window.grant_read.setEnabled(installed)
		self.window.grant_read.setToolTip("")
		if not installed:
			self.window.grant_read.setToolTip(control.WITHOUT_SERVICE_ACCOUNT)

	def grant_read_files(self) -> None:
		self.window.ui.state_bar.showMessage(control.launch_grant_read(self.window.configuration))
