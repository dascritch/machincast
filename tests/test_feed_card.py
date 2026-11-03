"""Scénarios des feeds de streams : leur liste et leur fiche (https://github.com/dascritch/machincast/issues/34).

Les étapes de la fenêtre, des listes, des fiches, de la suppression et des fenêtres de dialogue sont dans
tests/interface_steps.py ; le serveur de flux local, dans tests/broadcast_steps.py.
"""

from PySide6.QtCore import Qt
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.feed_card import FeedCard
from tests.interface_steps import NAME, Connection, Context, open_in, type_, window
from tests.stream import StreamServer

scenarios("feed_card.feature")


def card(interface: Context) -> FeedCard:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, FeedCard), opened
	return opened


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le flux « {stream} » du serveur local est avare"))
def sparing(server: StreamServer, stream: str) -> None:
	server.sparing_list.add(stream)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je saisis (?:le nom|(?P<address>l'adresse)) du feed « (?P<text>[^»]*) »"))
def enter(interface: Context, qtbot: QtBot, address: str | None, text: str) -> None:
	ui = card(interface).ui
	field = ui.name
	if address is not None:
		field = ui.url
	type_(qtbot, field, text)


@when(parsers.parse("je saisis l'adresse du flux « {stream} » du serveur local dans la fiche du feed"))
def local_address(interface: Context, qtbot: QtBot, server: StreamServer, stream: str) -> None:
	type_(qtbot, card(interface).ui.url, server.address(stream))


@when("je teste le flux du feed")
def launch_trial(interface: Context, qtbot: QtBot) -> None:
	qtbot.mouseClick(card(interface).ui.test, Qt.MouseButton.LeftButton)


@when(parsers.parse("le serveur de flux local a bientôt {count:d} connexion"))
@then(parsers.parse("le serveur de flux local a bientôt {count:d} connexion"))
def connections(server: StreamServer, qtbot: QtBot, count: int) -> None:
	qtbot.waitUntil(lambda: server.connections == count, timeout=5000)


@then("le serveur de flux local n'a bientôt plus de connexion")
def more_connection(server: StreamServer, qtbot: QtBot) -> None:
	qtbot.waitUntil(lambda: server.connections == 0, timeout=5000)


@when(parsers.parse("j'ouvre le stream « {title} » du feed"))
def open_stream(interface: Context, qtbot: QtBot, title: str) -> None:
	open_in(qtbot, card(interface).ui.streams, title)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"la fiche du feed montre le nom « (?P<name>[^»]*) » et l'adresse « (?P<url>[^»]*) »"))
def fields(interface: Context, name: str, url: str) -> None:
	ui = card(interface).ui
	assert (ui.name.text(), ui.url.text()) == (name.strip(), url.strip())


@then(parsers.re(r"la fiche du feed montre les streams (?P<titles>aucun|«.+)"))
def streams(interface: Context, titles: str) -> None:
	list_ = card(interface).ui.streams
	assert [list_.item(row).text() for row in range(list_.count())] == NAME.findall(titles)


@then(parsers.parse("le feed « {name} » est en base, à l'adresse « {url} »"))
def in_database(empty_database: Connection, name: str, url: str) -> None:
	lines = empty_database.execute("SELECT url FROM feeds WHERE name = %s", (name,)).fetchall()
	assert lines == [(url,)]


@then(parsers.parse("le stream « {title} » joue l'adresse « {url} »"))
def played_address(empty_database: Connection, title: str, url: str) -> None:
	lines = empty_database.execute(
		"SELECT COALESCE(s.stream_url, m.url) FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.title = %s",
		(title,),
	).fetchall()
	assert lines == [(url,)]


@then(parsers.parse("le test du flux du feed dit bientôt « {verdict} »"))
def verdict(interface: Context, qtbot: QtBot, verdict: str) -> None:
	ui = card(interface).ui
	qtbot.waitUntil(lambda: ui.trial_result.text() == verdict, timeout=15000)


@then("le test du flux du feed dit bientôt qu'il ne répond pas")
def silent(interface: Context, qtbot: QtBot) -> None:
	ui = card(interface).ui
	qtbot.waitUntil(lambda: ui.trial_result.text().startswith("Le flux ne répond pas : "), timeout=15000)
	assert ui.test.isEnabled()
