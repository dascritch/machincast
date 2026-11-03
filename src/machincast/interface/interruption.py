"""Interruption manuelle de l'antenne depuis l'interface (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228, spec § 8.11), et clic droit sur le prochain sonore de l'onglet
Antenne (https://github.com/dascritch/machincast/issues/257) : y sauter, ou avancer l'événement suivant
(offer_to_next).

Le menu « Diffusion » propose de sauter au sonore suivant, de sauter après la séquence en cours, ou de couper
l'événement par le fil musical (ENTREES). Chaque entrée suit l'état que Machin player publie sur sa socket d'état
(proposer) : elle n'est active que si son élément est à l'antenne, et, pour l'événement, hors du fil musical ; son
infobulle le nomme, ou dit pourquoi elle est inactive. Choisie, elle envoie la demande sur la
socket (StateClient.envoyer), aussitôt, sans question : Machin player la traite à son pas suivant
(machincast.player.broadcast.Broadcast.interrupt). La barre d'état l'annonce (ANNONCES).

Coupures (https://github.com/dascritch/machincast/issues/323) : « ⏭ Couper par le secours », dans le menu « Diffusion »
et au clic droit sur le prochain sonore, inactive sans événement de secours ou sans rien à l'antenne ; avec plusieurs
secours, un sous-menu les nomme (fill_fallback). Au clic droit sur un feed, « ⏭ Couper l'événement par ce feed »,
ou, dans le fil musical, « ⏭ Couper le fil musical par ce feed », inactive sans stream actif qui suive le feed
(offer_feed). Le secours, ou le stream du feed, tient l'antenne jusqu'à la fin prévue de l'événement coupé, ou,
sous le fil musical, jusqu'à l'événement suivant (machincast.player.rundown.Scheduler.cut_by).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from machincast.i18n import _
from machincast.interface import display
from machincast.interface.calendar import day_and_month
from machincast.interface.intents import SKIP, label
from machincast.interface.state import FollowingEvent, PlaybackState

log = logging.getLogger(__name__)

ENTRIES = {
	"sound": label(SKIP, _("Skip to the next sound")),
	"sequence": label(SKIP, _("Skip after the sequence")),
	"event": label(SKIP, _("Cut the event by the background programming")),
}
"""Entrée du menu « Diffusion » de chaque élément qui s'interrompt, dans l'ordre du menu."""
ANNOUNCEMENTS = {
	"sound": _("Skip to the next sound requested."),
	"sequence": _("Skip after the sequence requested."),
	"event": _("Cut of the event by the background programming requested."),
}
ON_AIR_NOTHING = _("Nothing on air")
NO_SEQUENCE = _("No sequence on air")
ALREADY_BACKGROUND_PROGRAMMING = _("The background programming is already on air")
WITHOUT_PLAYBACK = _("Interruption impossible: Machin player does not answer on its state socket.")
SKIP_TO_SOUND = label(SKIP, _("Skip to this sound"))
ADVANCE_FOLLOWING_EVENT = label(SKIP, _("Advance the next event"))
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
	"""Pour chaque élément, l'entrée de son interruption, selon l'état de Machin player."""
	ongoing = state.ongoing
	# Machin player ne publie un sonore en cours qu'en diffusion : ni pendant un blanc, ni à l'arrêt.
	if ongoing is None:
		return {item: Proposal(False, ON_AIR_NOTHING) for item in ENTRIES}
	sequence = Proposal(False, NO_SEQUENCE)
	if ongoing.sequence is not None:
		sequence = _named(ongoing.sequence)
	event = Proposal(False, ON_AIR_NOTHING)
	if ongoing.event is not None:
		event = _named(ongoing.event)
	if ongoing.priority_event == "background_programming":
		event = Proposal(False, ALREADY_BACKGROUND_PROGRAMMING)
	return {
		"sound": _named((ongoing.title) or (ongoing.location)),
		"sequence": sequence,
		"event": event,
	}


@dataclass(frozen=True)
class NextEntry:
	"""Une entrée du clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257)."""

	text: str
	proposal: Proposal


def advances(following: FollowingEvent) -> str:
	"""« ⏭ Avancer « Journal », prévu le mercredi 21 octobre à 12:00 »."""
	return _("{skip} Advance “{name}”, planned on {day_and_month} at {start:%H:%M}").format(
		skip=SKIP, name=following.name, day_and_month=day_and_month(following.start.date()), start=following.start
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

CUT_BY_FALLBACK = label(SKIP, _("Cut by the fallback"))
"""L'entrée du menu « Diffusion » et du clic droit sur le prochain sonore ; avec plusieurs secours, son sous-menu."""
NO_FALLBACK = _("No fallback event")
UNTIL_END = _(
	"The fallback plays until the planned end of the cut event; under the background programming, until the next event"
)
CUT_EVENT_BY_FEED = label(SKIP, _("Cut the event by this feed"))
CUT_BACKGROUND_PROGRAMMING_BY_FEED = label(SKIP, _("Cut the background programming by this feed"))
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
			lines = connection.execute(
				"SELECT id, internal_name FROM events WHERE priority = 'fallback' AND deleted_at IS NULL"
				" ORDER BY internal_name, id"
			).fetchall()
	except psycopg.Error as error:
		log.error(_("unreadable fallback events: {error}").format(error=error))
		return []
	return [Fallback(int(str(identifier)), str(name)) for identifier, name in lines]


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
	action.setText(CUT_BY_FALLBACK)
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
	elif len(fallback) > 1:
		under_menu = QMenu(CUT_BY_FALLBACK)
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


def offer_feed(state: PlaybackState, active_stream: bool) -> NextEntry:
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
			line = connection.execute(
				"SELECT id, state = 'active' FROM sounds WHERE feed_id = %s AND type = 'stream' AND deleted_at IS NULL"
				" ORDER BY state = 'active' DESC, id LIMIT 1",
				(feed,),
			).fetchone()
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
	entry = offer_feed(state, active)
	action = menu.addAction(entry.text)
	action.setEnabled(entry.proposal.active)
	action.setToolTip(entry.proposal.tooltip)
	action.triggered.connect(lambda _ticked=False: cut(feed, name))
	menu.setToolTipsVisible(True)
