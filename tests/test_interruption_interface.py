"""Scénarios de l'interruption de l'antenne depuis l'interface (https://github.com/dascritch/machincast/issues/104).

Une vraie socket d'état (machincast.player.state.StateSocket), là où l'interface la cherche, publie l'état d'un Machin
lecture imaginaire et reçoit les demandes de l'interface. Les étapes de la fenêtre sont dans tests/interface_steps.py.
"""

import time

from PySide6.QtGui import QAction
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QMenu
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import interruption
from machincast.interface.state import read_message
from machincast.player.state import ADVANCE, CUT_BY_FALLBACK, CUT_BY_FEED, Request
from tests.interface_steps import Connection, Context, Player, identifier, list_, publish, window

scenarios("interruption_interface.feature")

WAITING = 5000
"""Millisecondes qu'un état ou une demande a pour arriver."""


def entries(interface: Context) -> dict[str, QAction]:
	return window(interface).interruptions


# ─── Étant donné ───────────────────────────────────────────


@given(
	parsers.re(
		r"Machin player diffuse « (?P<title>[^»]+) »(?:, de la séquence « (?P<sequence>[^»]+) »)?,"
		r" dans (?P<feed>le fil musical )?« (?P<event>[^»]+) »(?:, au nom de « (?P<lender>[^»]+) »)?"
	)
)
def broadcasts(
	player: Player, title: str, sequence: str | None, feed: str | None, event: str, lender: str | None
) -> None:
	"""Un événement sans précision est une émission ; au nom d'une autre, elle lui prête son nom
	(https://github.com/dascritch/machincast/issues/399)."""
	if feed is None:
		priority = "show"
	else:
		priority = "background_programming"
	if lender is None:
		lender_identifier = None
	else:
		lender_identifier = 9
	ongoing = {
		"sound_id": 12,
		"type": "file",
		"artist": None,
		"title": title,
		"event": event,
		"event_priority": priority,
		"sequence": sequence,
		"location": "/srv/musique/minuit.flac",
		"start": "2026-10-21T08:59:00+02:00",
		"duration": 214.0,
		"estimated_end": "2026-10-21T09:02:34+02:00",
		"position": 60.0,
		"progress": 0.28,
		"lender": lender,
		"lender_id": lender_identifier,
	}
	publish(player, "playing", ongoing)


FOLLOWING_EVENT = 7
"""L'identifiant de l'événement suivant annoncé."""


def displayed_sound(title: str, event: str, start: str) -> dict[str, object]:
	sound_identifier = 13
	if start == "debut":
		sound_identifier = 12
	return {
		"sound_id": sound_identifier,
		"type": "file",
		"artist": None,
		"title": title,
		"event": event,
		"event_priority": "show",
		"location": f"/srv/musique/{title}.flac",
		start: "2026-10-21T08:59:00+02:00",
		"duration": 214.0,
		"estimated_end": "2026-10-21T09:02:34+02:00",
	}


def following(name: str | None, start: str | None, end: str | None) -> dict[str, object] | None:
	if name is None:
		return None
	return {"id": FOLLOWING_EVENT, "name": name, "priority": "show", "start": start, "end": end}


ANNOUNCEMENT = (
	r"(?:, et annonce l'événement suivant « (?P<name>[^»]+) », du « (?P<start>[^»]+) » au « (?P<end>[^»]+) »)?"
)


@given(
	parsers.re(
		r"Machin player diffuse « (?P<title>[^»]+) », dans « (?P<event>[^»]+) », avant « (?P<next_>[^»]+) »"
		+ ANNOUNCEMENT
	)
)
def broadcasts_before(
	player: Player,
	title: str,
	event: str,
	next_: str,
	name: str | None,
	start: str | None,
	end: str | None,
) -> None:
	"""https://github.com/dascritch/machincast/issues/257 : le sonore en cours, le prochain, et l'événement suivant."""
	ongoing = displayed_sound(title, event, "start") | {"position": 60.0, "progress": 0.28}
	publish(
		player,
		"playing",
		ongoing,
		next_=displayed_sound(next_, event, "estimated_start"),
		following_event=following(name, start, end),
	)


@given(parsers.re(r"Machin player laisse un blanc" + ANNOUNCEMENT))
def in_dead_air_before(player: Player, name: str | None, start: str | None, end: str | None) -> None:
	publish(player, "dead_air", following_event=following(name, start, end))


@given("Machin player laisse un blanc")
@when("Machin player passe à un blanc")
def in_dead_air(player: Player) -> None:
	publish(player, "dead_air")


@given("Machin player s'est arrêté")
def stops(player: Player) -> None:
	publish(player, "stopped")


# ─── Quand ─────────────────────────────────────────────────


@when("l'interface a reçu l'état de Machin player")
def received_state(interface: Context, player: Player, qtbot: QtBot) -> None:
	"""Les entrées montrent ce que propose le dernier état publié."""
	expected_list = interruption.offer(read_message(player.published))

	def up_to_date() -> bool:
		every_one = True
		for item, action in entries(interface).items():
			if not (
				(action.isEnabled() == expected_list[item].active) and (action.toolTip() == expected_list[item].tooltip)
			):
				every_one = False
				break
		return every_one

	qtbot.waitUntil(up_to_date, timeout=WAITING)


@when("l'onglet Antenne a reçu l'état de Machin player")
def up_to_date_home(interface: Context, player: Player, qtbot: QtBot) -> None:
	expected = read_message(player.published)
	qtbot.waitUntil(lambda: window(interface).home.state == expected, timeout=WAITING)


def next_actions(interface: Context) -> list[QAction]:
	menu = window(interface).home.next_menu()
	assert menu is not None
	next_actions = []
	for action in menu.actions():
		if not action.isSeparator():
			next_actions.append(action)
	return next_actions


@when(parsers.parse("je choisis « {entry} » au clic droit sur le prochain sonore"))
def choose_to_next(interface: Context, entry: str) -> None:
	action_list = []
	for candidate in next_actions(interface):
		if candidate.text() == entry:
			action_list.append(candidate)
	(action,) = action_list
	action.trigger()


@when(parsers.parse("Machin player ferme sa socket d'état, juste avant que je choisisse « {entry} »"))
def closed_socket_before_choice(interface: Context, player: Player, qtbot: QtBot, entry: str) -> None:
	"""Le choix arrive avant que l'interface ait vu la socket se fermer : l'entrée est encore active."""
	assert player.socket is not None
	player.socket.shut_down()
	player.socket = None
	client = window(interface).home.client
	qtbot.waitUntil(lambda: client._socket.state() != QLocalSocket.LocalSocketState.ConnectedState, timeout=WAITING)
	action_list = []
	for candidate in entries(interface).values():
		if candidate.text() == entry:
			action_list.append(candidate)
	(action,) = action_list
	action.setEnabled(True)
	action.trigger()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("les interruptions du menu « {menu} » sont :"))
def interruptions(interface: Context, menu: str, datatable: list[list[str]]) -> None:
	_, *lines = datatable
	assert menu == "Diffusion"
	broadcast_menu = window(interface).broadcast_menu
	obtained_list = []
	for action in broadcast_menu.actions():
		if action in entries(interface).values():
			state = "inactive"
			if action.isEnabled():
				state = "active"
			obtained_list.append([action.text(), state, action.toolTip()])
	line_list = []
	for line in lines:
		value_list = []
		for value in line:
			value_list.append(value.strip())
		line_list.append(value_list)
	assert obtained_list == line_list


@then("le clic droit sur le prochain sonore propose :")
def next_menu(interface: Context, datatable: list[list[str]]) -> None:
	_, *lines = datatable
	obtained_list = []
	for action in next_actions(interface):
		state = "inactive"
		if action.isEnabled():
			state = "active"
		obtained_list.append([action.text(), state, action.toolTip()])
	# Qt donne à une action sans infobulle son texte pour infobulle : une cellule vide l'accepte.
	expected_list = []
	for line in lines:
		value_list = []
		for value in line:
			value_list.append(value.strip())
		expected_list.append(value_list)
	for obtained, expected in zip(obtained_list, expected_list, strict=False):
		if expected[2] == "":
			obtained[2] = ""
	assert obtained_list == expected_list


@then(parsers.parse("Machin player a reçu la demande d'avancer l'événement n°{event:d}"))
def advances_received(player: Player, qtbot: QtBot, event: int) -> None:
	socket = player.socket
	assert socket is not None

	def received() -> bool:
		player.received_list += socket.requests()
		return player.received_list != []

	qtbot.waitUntil(received, timeout=WAITING)
	time.sleep(0.1)
	player.received_list += socket.requests()
	assert player.received_list == [Request(command=ADVANCE, event=event)]


@then("aucune interruption n'est active")
def no_active(interface: Context) -> None:
	found = False
	for action in entries(interface).values():
		if action.isEnabled():
			found = True
			break
	assert not found


@then(parsers.parse("Machin player a reçu la demande d'interrompre « {item} »"))
def asks_received(player: Player, qtbot: QtBot, item: str) -> None:
	socket = player.socket
	assert socket is not None

	def received() -> bool:
		player.received_list += socket.requests()
		return player.received_list != []

	qtbot.waitUntil(received, timeout=WAITING)
	time.sleep(0.1)
	player.received_list += socket.requests()
	assert player.received_list == [Request(item)]


# ─── Coupures par le secours et par un feed (https://github.com/dascritch/machincast/issues/323) ───


def _entries(text: str) -> list[str]:
	"""« « A » », « « B » » : les entrées, qui peuvent porter elles-mêmes des guillemets."""
	return text.removeprefix("« ").removesuffix(" »").split(" », « ")


def _receive(player: Player, qtbot: QtBot) -> list[Request]:
	"""Les demandes reçues jusqu'ici, après en avoir attendu au moins une de plus."""
	socket = player.socket
	assert socket is not None
	already = len(player.received_list)

	def received() -> bool:
		player.received_list += socket.requests()
		return len(player.received_list) > already

	qtbot.waitUntil(received, timeout=WAITING)
	time.sleep(0.1)
	player.received_list += socket.requests()
	return player.received_list


def _feed_menu(interface: Context, name: str) -> QMenu:
	opened = list_(interface)
	model = opened.table.model()
	row_list = []
	for candidate_row in range(model.rowCount()):
		if model.index(candidate_row, 0).data() == name:
			row_list.append(candidate_row)
	(row,) = row_list
	menu = opened.line_menu(model.index(row, 0))
	assert menu is not None
	return menu


@when(parsers.parse("je choisis « {entry} » dans le sous-menu de la coupure par le secours"))
def choose_fallback(interface: Context, entry: str) -> None:
	under_menu = window(interface).cutoff_by_fallback.menu()
	assert under_menu is not None
	action_list = []
	for candidate in under_menu.actions():
		if candidate.text() == entry:
			action_list.append(candidate)
	(action,) = action_list
	action.trigger()


@when(parsers.parse("je choisis « {entry} » au clic droit sur le feed « {name} »"))
def choose_to_feed(interface: Context, entry: str, name: str) -> None:
	action_list = []
	for candidate in _feed_menu(interface, name).actions():
		if candidate.text() == entry:
			action_list.append(candidate)
	(action,) = action_list
	action.trigger()


@then(
	parsers.parse(
		"la coupure par le secours du menu « Diffusion » est active, sans sous-menu, avec l'infobulle « {tooltip} »"
	)
)
def active_fallback(interface: Context, tooltip: str) -> None:
	action = window(interface).cutoff_by_fallback
	assert action in window(interface).broadcast_menu.actions()
	assert (action.text(), action.isEnabled(), action.menu(), action.toolTip()) == (
		interruption.CUT_BY_FALLBACK,
		True,
		None,
		tooltip,
	)


@then(parsers.parse("la coupure par le secours du menu « Diffusion » est inactive, avec l'infobulle « {tooltip} »"))
def inactive_fallback(interface: Context, tooltip: str) -> None:
	action = window(interface).cutoff_by_fallback
	assert (action.isEnabled(), action.toolTip()) == (False, tooltip)


@then(parsers.parse("la coupure par le secours du menu « Diffusion » a le sous-menu {entries}"))
def under_fallback_menu(interface: Context, entries: str) -> None:
	action = window(interface).cutoff_by_fallback
	under_menu = action.menu()
	assert (action.isEnabled()) and (under_menu is not None)
	entry_list = []
	for entry in under_menu.actions():
		entry_list.append(entry.text())
	assert entry_list == _entries(entries)


@then(parsers.parse("Machin player a reçu la demande de couper l'antenne par le secours « {name} »"))
def cutoff_by_received_fallback(empty_database: Connection, player: Player, qtbot: QtBot, name: str) -> None:
	fallback = identifier(empty_database, "events", "internal_name", name)
	assert _receive(player, qtbot) == [Request(command=CUT_BY_FALLBACK, event=fallback)]


@then(parsers.parse("Machin player a reçu la demande de couper l'antenne par le feed « {name} »"))
def cutoff_by_received_feed(empty_database: Connection, player: Player, qtbot: QtBot, name: str) -> None:
	feed = identifier(empty_database, "feeds", "name", name)
	assert _receive(player, qtbot) == [Request(command=CUT_BY_FEED, feed=feed)]


@then(parsers.parse("Machin player a reçu aussi la demande d'interrompre « {item} »"))
def also_received(player: Player, qtbot: QtBot, item: str) -> None:
	assert _receive(player, qtbot)[-1] == Request(item)


@then(parsers.parse("le clic droit sur le feed « {name} » propose :"))
def feed_menu(interface: Context, name: str, datatable: list[list[str]]) -> None:
	_, *lines = datatable
	obtained_list = []

	def feed_action(action) -> None:
		if action.isSeparator():
			return
		state = "inactive"
		if action.isEnabled():
			state = "active"
		obtained_list.append([action.text(), state, action.toolTip()])

	for action in _feed_menu(interface, name).actions():
		feed_action(action)
	expected_list = []
	for line in lines:
		value_list = []
		for value in line:
			value_list.append(value.strip())
		expected_list.append(value_list)
	# Qt donne à une action sans infobulle son texte pour infobulle : une cellule vide l'accepte.
	for obtained, expected in zip(obtained_list, expected_list, strict=False):
		if expected[2] == "":
			obtained[2] = ""
	assert obtained_list == expected_list
