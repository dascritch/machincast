"""Interruption manuelle de l'antenne depuis l'interface (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228, spec § 8.11), et clic droit sur le prochain sonore de l'onglet
Antenne (https://github.com/dascritch/machincast/issues/257) : y sauter, ou avancer l'événement suivant
(offer_to_next).

Le menu « Diffusion » propose de revenir au début du sonore ou de l'événement à l'antenne (RESTARTS,
https://github.com/dascritch/machincast/issues/366), puis de sauter au sonore suivant, de sauter après la séquence en
cours, ou de couper l'événement par le fil musical (ENTRIES). Chaque entrée suit l'état que Machin player publie sur sa socket d'état
(proposer) : elle n'est active que si son élément est à l'antenne, et, pour l'événement, hors du fil musical ; son
infobulle le nomme, ou dit pourquoi elle est inactive. Choisie, elle envoie la demande sur la
socket (StateClient.send), aussitôt, sans question : Machin player la traite à son pas suivant
(machincast.player.broadcast.Broadcast.interrupt). La barre d'état l'annonce (ANNONCES).

Coupures (https://github.com/dascritch/machincast/issues/323) : « ⏭ Couper par le secours », dans le menu « Diffusion »
et au clic droit sur le prochain sonore, inactive sans événement de secours ou sans rien à l'antenne ; avec plusieurs
secours, un sous-menu les nomme (fill_fallback). Au clic droit sur un feed, « ⏭ Couper l'événement par ce feed »,
ou, dans le fil musical, « ⏭ Couper le fil musical par ce feed », inactive sans stream actif qui suive le feed
(offer_feed). Le secours, ou le stream du feed, tient l'antenne jusqu'à la fin prévue de l'événement coupé, ou,
sous le fil musical, jusqu'à l'événement suivant (machincast.player.rundown.Scheduler.cut_by).

Regroupement (https://github.com/dascritch/machincast/issues/530) : dans le menu « Diffusion » et au clic droit sur le
sonore en cours ou le prochain sonore de l'onglet Antenne, ces actions vont dans quatre sous-menus, chacun avec son
icône au lieu d'un emoji (OnAirMenu) : « Recommencer » ce sonore, cette séquence ou cet événement ; « Sauter » au sonore
suivant ou après cette séquence ; « Insérer après ce sonore » une séquence ou un sonore d'une banque, choisis dans les
sous-menus des séquences et des banques ; « Couper » cet événement par un fil musical, ou par un secours.
"""

import logging
import traceback
from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget
from shiboken6 import isValid

from machincast.i18n import _
from machincast.interface import display, icons
from machincast.interface.calendar import day_and_month
from machincast.interface.queries import banks as banks_queries
from machincast.interface.queries import events as events_queries
from machincast.interface.queries import feeds as feeds_queries
from machincast.interface.queries import sequences as sequences_queries
from machincast.interface.state import FollowingEvent, PlaybackState

log = logging.getLogger(__name__)

RESTART_MENU = _("Restart")
RESTARTS = {
	"restart_sound": _("this sound"),
	"restart_sequence": _("this sequence"),
	"restart_event": _("this event"),
}
"""Revenir au début du sonore, de la séquence ou de l'événement à l'antenne, pour un début raté
(https://github.com/dascritch/machincast/issues/366, https://github.com/dascritch/machincast/issues/530)."""
SKIP_MENU = _("Skip")
SKIPS = {"sound": _("to the next sound"), "sequence": _("after this sequence")}
INSERT_MENU = _("Insert after this sound")
INSERT_SEQUENCE = _("a sequence")
INSERT_BANK = _("a sound from a bank")
NO_SEQUENCE_TO_INSERT = _("No sequence")
NO_BANK_TO_INSERT = _("No bank")
CUT_MENU = _("Cut")
CUTS = {"event": _("this event by the background programming")}
BY_FALLBACK = _("by a fallback")
"""« Couper » « par un secours » ; avec plusieurs secours, son sous-menu les nomme."""
ENTRIES = {
	"sound": SKIPS["sound"],
	"sequence": SKIPS["sequence"],
	"event": CUTS["event"],
}
"""L'entrée de chaque élément qui s'interrompt, dans son sous-menu."""
ANNOUNCEMENTS = {
	"sound": _("Skip to the next sound requested."),
	"sequence": _("Skip after the sequence requested."),
	"event": _("Cut of the event by the background programming requested."),
	"restart_sound": _("Back to the start of the sound requested."),
	"restart_event": _("Restart of the event requested."),
	"restart_sequence": _("Restart of the sequence requested."),
}
ON_AIR_NOTHING = _("Nothing on air")
NO_SEQUENCE = _("No sequence on air")
NO_BEGINNING = _("A stream has no beginning")
ALREADY_BACKGROUND_PROGRAMMING = _("The background programming is already on air")
WITHOUT_PLAYBACK = _("Interruption impossible: Machin player does not answer on its state socket.")
SKIP_TO_SOUND = _("Skip to this sound")
ADVANCE_FOLLOWING_EVENT = _("Advance the next event")
NO_NEXT_SOUND = _("No next sound")
NO_FOLLOWING_EVENT = _("No next event within seven days")
WITHOUT_BROADCAST = _("Machin player is not broadcasting")
ADVANCE_WITHOUT_PLAYBACK = _("Advance impossible: Machin player does not answer on its state socket.")


@dataclass(frozen=True)
class Proposal:
	active: bool
	tooltip: str
	"""Ce que l'entrée interrompt, ou pourquoi elle est inactive."""


def _named(name: str | None) -> Proposal:
	return Proposal(True, _("“{name}”").format(name=name))


def offer(state: PlaybackState) -> dict[str, Proposal]:
	"""Pour chaque élément, l'entrée de son interruption, ou de son retour au début, selon l'état de Machin player."""
	ongoing = state.ongoing
	# Machin player ne publie un sonore en cours qu'en diffusion : ni pendant un blanc, ni à l'arrêt.
	if ongoing is None:
		offer = {}
		for item in (*RESTARTS, *ENTRIES):
			offer[item] = Proposal(False, ON_AIR_NOTHING)
		return offer
	sound = _named((ongoing.title) or (ongoing.location))
	sequence = Proposal(False, NO_SEQUENCE)
	if ongoing.sequence is not None:
		sequence = _named(ongoing.sequence)
	# L'événement à l'antenne : celui qui prête son nom au fil musical, s'il y en a un
	# (https://github.com/dascritch/machincast/issues/399).
	on_air = Proposal(False, ON_AIR_NOTHING)
	if ongoing.event is not None:
		on_air = _named(ongoing.event)
	if ongoing.lender is not None:
		on_air = _named(ongoing.lender)
	# Le couper : rien dans le fil musical, sauf quand il joue au nom d'une émission, qu'il coupe alors.
	event = on_air
	if (ongoing.priority_event == "background_programming") and (ongoing.lender is None):
		event = Proposal(False, ALREADY_BACKGROUND_PROGRAMMING)
	restart_sound = sound
	if ongoing.stream:
		restart_sound = Proposal(False, NO_BEGINNING)
	return {
		"restart_sound": restart_sound,
		"restart_sequence": sequence,
		"restart_event": on_air,
		"sound": sound,
		"sequence": sequence,
		"event": event,
	}


@dataclass(frozen=True)
class NextEntry:
	"""Une entrée du clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257)."""

	text: str
	proposal: Proposal


def advances(following: FollowingEvent) -> str:
	"""« Avancer « Journal », prévu le mercredi 21 octobre à 12:00 »."""
	return _("Advance “{name}”, planned on {day_and_month} at {start:%H:%M}").format(
		name=following.name, day_and_month=day_and_month(following.start.date()), start=following.start
	)


def advance_announcement(name: str) -> str:
	return _("Advance of the event “{name}” requested.").format(name=name)


def _until(following: FollowingEvent) -> str:
	if following.end is None:
		return _("It starts at once, above the grid, until the end of its list")
	end = f"{following.end:%H:%M}"
	if following.end.date() != following.start.date():
		end = f"{day_and_month(following.end.date())}, {end}"
	return _("It starts at once, above the grid, until its end, at {end}").format(end=end)


def offer_to_next(state: PlaybackState) -> dict[str, NextEntry]:
	"""Sauter au prochain sonore (« sound »), et avancer l'événement suivant (« advance »), selon l'état de Machin
	lecture : il faut un sonore à l'antenne et un prochain sonore pour y sauter ; un événement suivant annoncé pour
	l'avancer. À l'arrêt, rien ne se demande."""
	if state.state == "stopped":
		return {
			"sound": NextEntry(SKIP_TO_SOUND, Proposal(False, WITHOUT_BROADCAST)),
			"advance": NextEntry(ADVANCE_FOLLOWING_EVENT, Proposal(False, WITHOUT_BROADCAST)),
		}
	sound = NextEntry(SKIP_TO_SOUND, Proposal(False, NO_NEXT_SOUND))
	if (state.ongoing is not None) and (state.next_ is not None):
		next_ = (state.next_.title) or (state.next_.location)
		ongoing = (state.ongoing.title) or (state.ongoing.location)
		tooltip = _("“{next}”, at once: “{ongoing}” stops").format(next=next_, ongoing=ongoing)
		sound = NextEntry(SKIP_TO_SOUND, Proposal(True, tooltip))
	advance = NextEntry(ADVANCE_FOLLOWING_EVENT, Proposal(False, NO_FOLLOWING_EVENT))
	following = state.following_event
	if following is not None:
		advance = NextEntry(advances(following), Proposal(True, _until(following)))
	return {"sound": sound, "advance": advance}


# ─── Coupures par le secours et par un feed (https://github.com/dascritch/machincast/issues/323) ───

CUT_BY_FALLBACK = BY_FALLBACK
"""L'entrée « par un secours » du sous-menu « Couper » ; avec plusieurs secours, son sous-menu."""
NO_FALLBACK = _("No fallback event")
UNTIL_END = _(
	"The fallback plays until the planned end of the cut event; under the background programming, until the next event"
)
CUT_EVENT_BY_FEED = _("Cut the event by this feed")
CUT_BACKGROUND_PROGRAMMING_BY_FEED = _("Cut the background programming by this feed")
NO_STREAM = _("No active stream follows this feed")
FEED_UNTIL_END = _(
	"The feed's stream plays until the planned end of the cut event; under the background "
	"programming, until the next event. If it drops, the background programming takes over"
)
CUTOFF_WITHOUT_PLAYBACK = _("Cutoff impossible: Machin player does not answer on its state socket.")


@dataclass(frozen=True)
class Fallback:
	"""Un événement de secours, que l'interface propose pour couper l'antenne."""

	identifier: int
	name: str


def read_fallback(connection: psycopg.Connection[TupleRow]) -> list[Fallback]:
	"""Les événements de secours en base, non supprimés, par nom ; aucun si la base est injoignable."""
	try:
		with connection.transaction():
			lines = events_queries.fallback_events(connection)
	except psycopg.Error as error:
		log.error(_("unreadable fallback events: {error}").format(error=error))
		return []
	fallback = []
	for identifier, name in lines:
		fallback.append(Fallback(int(str(identifier)), str(name)))
	return fallback


def offer_fallback(state: PlaybackState, fallback: list[Fallback]) -> Proposal:
	"""Couper par le secours : il faut un événement de secours, et un sonore à l'antenne."""
	if fallback == []:
		return Proposal(False, NO_FALLBACK)
	if state.ongoing is None:
		return Proposal(False, ON_AIR_NOTHING)
	if len(fallback) == 1:
		return Proposal(
			True,
			_(
				"“{name}” plays until the planned end of the cut event; under the background programming, until the "
				"next event"
			).format(name=fallback[0].name),
		)
	return Proposal(True, UNTIL_END)


def fill_fallback(
	action: QAction, state: PlaybackState, fallback: list[Fallback], ask: Callable[[Fallback], None]
) -> None:
	"""L'entrée « ⏭ Couper par le secours » : avec un seul secours, elle porte ce secours (data), et coupe par lui une
	fois reliée à ask_fallback ; avec plusieurs, son sous-menu les nomme, chacun coupant par lui."""
	proposal = offer_fallback(state, fallback)
	action.setText(BY_FALLBACK)
	action.setEnabled(proposal.active)
	action.setToolTip(proposal.tooltip)
	old = action.menu()
	# Sans sous-menu : PySide6 ne déclare pas None, que Qt accepte pour retirer le menu de l'action.
	action.setMenu(None)  # type: ignore[arg-type]
	if isinstance(old, QMenu):
		old.deleteLater()
	action.setData(None)
	if len(fallback) == 1:
		action.setData(fallback[0])
	else:
		if len(fallback) > 1:
			under_menu = QMenu(BY_FALLBACK)
			under_menu.setToolTipsVisible(True)
			for un in fallback:
				entry = under_menu.addAction(_("“{name}”").format(name=un.name))
				entry.setToolTip(UNTIL_END)
				entry.triggered.connect(lambda _ticked=False, un=un: ask(un))
			action.setMenu(under_menu)


def ask_fallback(action: QAction, ask: Callable[[Fallback], None]) -> None:
	"""L'entrée choisie coupe par le secours qu'elle porte ; avec un sous-menu, ce sont ses entrées qui coupent."""
	fallback = action.data()
	if isinstance(fallback, Fallback):
		ask(fallback)


def fallback_announcement(name: str) -> str:
	return _("Cut by the fallback “{name}” requested.").format(name=name)


def offer_feed(state: PlaybackState, *, active_stream: bool) -> NextEntry:
	"""Couper par un feed, au clic droit sur sa ligne : l'événement à l'antenne, ou le fil musical. Il faut un sonore à
	l'antenne, et un stream actif qui suive le feed."""
	ongoing = state.ongoing
	text = CUT_EVENT_BY_FEED
	if (ongoing is not None) and (ongoing.priority_event == "background_programming"):
		text = CUT_BACKGROUND_PROGRAMMING_BY_FEED
	if ongoing is None:
		return NextEntry(text, Proposal(False, ON_AIR_NOTHING))
	if not active_stream:
		return NextEntry(text, Proposal(False, NO_STREAM))
	return NextEntry(text, Proposal(True, FEED_UNTIL_END))


def feed_announcement(name: str) -> str:
	return _("Cut by the feed “{name}” requested.").format(name=name)


def feed_stream(connection: psycopg.Connection[TupleRow], feed: int) -> tuple[int | None, bool]:
	"""Le stream qui suit le feed, un actif d'abord, le plus ancien ; et s'il est actif. Aucun si la base est
	injoignable."""
	try:
		with connection.transaction():
			line = feeds_queries.active_stream(connection, feed)
	except psycopg.Error as error:
		log.error(_("unreadable stream of feed {feed}: {error}").format(feed=feed, error=error))
		return None, False
	if line is None:
		return None, False
	return int(str(line[0])), line[1] is True


def fill_feed(
	menu: QMenu,
	state: PlaybackState,
	connection: psycopg.Connection[TupleRow],
	feed: int,
	name: str,
	preview: Callable[[int], None],
	cut: Callable[[int, str], None],
) -> None:
	"""Le clic droit sur un feed : « Pré-écoute… » de son stream, puis la coupure de l'antenne par lui."""
	stream, active = feed_stream(connection, feed)
	if stream is not None:
		display.offer_preview(menu, stream, preview)
	entry = offer_feed(state, active_stream=active)
	action = menu.addAction(icons.icon("cut"), entry.text)
	action.setEnabled(entry.proposal.active)
	action.setToolTip(entry.proposal.tooltip)
	action.triggered.connect(lambda _ticked=False: cut(feed, name))
	menu.setToolTipsVisible(True)


# ─── Menus regroupés (https://github.com/dascritch/machincast/issues/530) ───


@dataclass(frozen=True)
class Requests:
	"""Ce que demandent les entrées de l'antenne : une interruption, une coupure par un secours, une insertion."""

	interrupt: Callable[[str], None]
	fallback: Callable[[Fallback], None]
	insert: Callable[[str, int, str], None]
	"""L'insertion d'une séquence (« sequence ») ou d'un sonore d'une banque (« bank ») : son genre, son
	identifiant, son nom."""


def _named_list(connection: psycopg.Connection[TupleRow], category: str) -> list[tuple[int, str]]:
	"""Les séquences ou les banques, par nom ; aucune si la base est injoignable."""
	try:
		with connection.transaction():
			if category == "sequence":
				lines = sequences_queries.named(connection)
			else:
				lines = banks_queries.named(connection)
	except psycopg.Error as error:
		log.error(_("unreadable {category} list: {error}").format(category=category, error=error))
		return []
	named_list = []
	for identifier, name in lines:
		named_list.append((int(str(identifier)), str(name)))
	return named_list


class OnAirMenu:
	"""Les sous-menus « Recommencer », « Sauter », « Insérer après ce sonore » et « Couper », ajoutés à un menu ; leurs
	entrées suivent l'état de Machin player (offer), comme celles du menu « Diffusion » avant eux.

	Celui du menu « Diffusion » est gardé (watched) : si Qt détruit ses entrées sans que l'interface le demande, le
	journal consigne, une fois, la pile des appels de leur destruction, et elles se recréent à l'état suivant
	(https://github.com/dascritch/machincast/issues/658)."""

	def __init__(
		self,
		menu: QMenu,
		connection: psycopg.Connection[TupleRow],
		requests: Requests,
		parent: QWidget | None = None,
		*,
		watched: bool = False,
	) -> None:
		self.connection = connection
		self.requests = requests
		self.menu = menu
		self.parent = parent
		self.actions: dict[str, QAction] = {}
		self.menus: dict[str, QMenu] = {}
		self.state: PlaybackState | None = None
		self.watched = watched
		"""Vrai tant que la destruction d'une entrée est inattendue : faux pendant leur reconstruction, et à la
		fermeture de la fenêtre."""
		self._reported = False
		self._build()

	def _build(self) -> None:
		menu = self.menu
		parent = self.parent
		restart = self._under(menu, RESTART_MENU, "restart", parent)
		for item, text in RESTARTS.items():
			self._entry(restart, item, text)
		skip = self._under(menu, SKIP_MENU, "skip", parent)
		for item, text in SKIPS.items():
			self._entry(skip, item, text)
		insert = self._under(menu, INSERT_MENU, "insert", parent)
		self.sequences = insert.addMenu(icons.icon("sequence"), INSERT_SEQUENCE)
		self.sequences.aboutToShow.connect(lambda: self._fill_insertions(self.sequences, "sequence"))
		self.banks = insert.addMenu(icons.icon("bank"), INSERT_BANK)
		self.banks.aboutToShow.connect(lambda: self._fill_insertions(self.banks, "bank"))
		cut = self._under(menu, CUT_MENU, "cut", parent)
		self._entry(cut, "event", CUTS["event"])
		self.fallback = cut.addAction(BY_FALLBACK)
		fallback = self.fallback
		fallback.triggered.connect(lambda _ticked=False: ask_fallback(fallback, self.requests.fallback))
		for action in [*self.actions.values(), fallback]:
			action.destroyed.connect(self._lost)

	def _lost(self) -> None:
		"""Une entrée détruite sans que l'interface le demande : la pile des appels dit qui l'a détruite."""
		if (not self.watched) or (self._reported):
			return
		self._reported = True
		log.warning(
			_("entries of the Broadcast menu destroyed, recreated at the next state of Machin player:\n{stack}").format(
				stack="".join(traceback.format_stack())
			)
		)

	def alive(self) -> bool:
		"""Les entrées, leurs sous-menus et la coupure par le secours existent encore pour Qt."""
		every_one = isValid(self.fallback)
		for each in [*self.actions.values(), *self.menus.values(), self.sequences, self.banks]:
			if not isValid(each):
				every_one = False
		return every_one

	def _rebuild(self) -> None:
		"""Les sous-menus, recréés à leur place ; ceux qui restent sont retirés du menu, puis détruits."""
		watched = self.watched
		self.watched = False
		for under in self.menus.values():
			if isValid(under):
				if isValid(self.menu):
					self.menu.removeAction(under.menuAction())
				under.deleteLater()
		self.actions.clear()
		self.menus.clear()
		self._build()
		self.watched = watched
		self._reported = False

	def _under(self, menu: QMenu, title: str, icon: str, parent: QWidget | None) -> QMenu:
		under = QMenu(title, parent)
		under.setIcon(icons.icon(icon))
		under.setToolTipsVisible(True)
		menu.addMenu(under)
		self.menus[icon] = under
		return under

	def _entry(self, menu: QMenu, item: str, text: str) -> None:
		action = menu.addAction(text)
		action.triggered.connect(lambda _ticked=False, item=item: self.requests.interrupt(item))
		self.actions[item] = action

	def offer(self, state: PlaybackState, fallback: list[Fallback]) -> None:
		"""Les entrées suivent ce qui est à l'antenne ; une entrée inactive dit pourquoi dans son infobulle. Insérer
		demande un sonore à l'antenne. Détruites hors de l'interface, elles se recréent d'abord."""
		if not self.alive():
			self._rebuild()
		for item, proposal in offer(state).items():
			action = self.actions[item]
			action.setEnabled(proposal.active)
			action.setToolTip(proposal.tooltip)
		self.state = state
		fill_fallback(self.fallback, state, fallback, self.requests.fallback)
		on_air = state.ongoing is not None
		for under in (self.sequences, self.banks):
			under.setEnabled(on_air)
			under.menuAction().setToolTip("")
			if not on_air:
				under.menuAction().setToolTip(ON_AIR_NOTHING)

	def _fill_insertions(self, menu: QMenu, category: str) -> None:
		"""Les séquences ou les banques, relues à l'ouverture du sous-menu ; chacune s'insère après le sonore en
		cours."""
		menu.clear()
		named_list = _named_list(self.connection, category)
		if named_list == []:
			empty = NO_SEQUENCE_TO_INSERT
			if category == "bank":
				empty = NO_BANK_TO_INSERT
			menu.addAction(empty).setEnabled(False)
			return
		for identifier, name in named_list:
			entry = menu.addAction(_("“{name}”").format(name=name))
			entry.triggered.connect(
				lambda _ticked=False, identifier=identifier, name=name: self.requests.insert(category, identifier, name)
			)


def insertion_announcement(category: str, name: str) -> str:
	"""Ce que la barre d'état annonce d'une insertion demandée."""
	if category == "sequence":
		return _("Insertion of the sequence “{name}” after this sound requested.").format(name=name)
	return _("Insertion of a sound from the bank “{name}” after this sound requested.").format(name=name)


INSERTION_WITHOUT_PLAYBACK = _("Insertion impossible: Machin player does not answer on its state socket.")
