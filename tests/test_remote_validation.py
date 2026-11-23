"""Scénarios de la validation au pupitre des connexions à distance, et des sessions des comptes
(https://github.com/dascritch/machincast/issues/539)."""

from datetime import timedelta

import pytest
from PySide6.QtWidgets import QPushButton
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import api_tab
from machincast.interface.remote_connections import RemoteConnections
from machincast.intranet import sessions
from tests.interface_steps import NAME, Connection, Context, window
from tests.intranet_steps import screen

scenarios("remote_validation.feature")


@pytest.fixture(autouse=True)
def noted_tokens(interface: Context) -> None:
	"""Le jeton d'une session générée, noté au lieu d'être montré."""
	interface.shown_tokens = []  # type: ignore[attr-defined]

	def note(_parent: object, name: str, value: str) -> None:
		interface.shown_tokens.append((name, value))  # type: ignore[attr-defined]

	interface.monkeypatch.setattr(api_tab, "show_token", note)


def banner(interface: Context) -> RemoteConnections:
	return window(interface).remote_connections


@given(
	parsers.re(
		r"une connexion à valider de « (?P<name>[^»]+) », depuis « (?P<address>[^»]+) », navigateur"
		r" « (?P<agent>[^»]+) », (?:code « (?P<code>\d{6}) »|sans code)(?P<late>, délai passé)?"
	)
)
def pending(
	empty_database: Connection, name: str, address: str, agent: str, code: str | None, late: str | None
) -> None:
	delay = "20 minutes"
	if late is not None:
		delay = "-1 second"
	empty_database.execute(
		"INSERT INTO api_sessions (user_id, token_hash, code, user_agent, source_ip, validate_before)"
		" SELECT id, %s, %s, %s, %s, clock_timestamp() + %s::interval FROM api_users WHERE name = %s",
		(sessions.fingerprint(f"jeton-{name}"), code, agent, address, delay, name),
	)


@when("le bandeau des connexions à distance se relit")
def reread(interface: Context) -> None:
	banner(interface).refresh()


@when("je refuse la connexion à distance")
def refuse(interface: Context) -> None:
	shown = banner(interface)
	(button,) = shown.findChildren(QPushButton, "refuse_remote_connection")
	button.click()


@when("j'accepte la connexion à distance")
def accept(interface: Context) -> None:
	(button,) = banner(interface).findChildren(QPushButton, "accept_remote_connection")
	button.click()


@given(parsers.parse("la connexion à valider de « {name} » est acceptée au pupitre"))
def accepted(empty_database: Connection, name: str) -> None:
	empty_database.execute(
		"UPDATE api_sessions SET accepted_at = clock_timestamp() WHERE token_hash = %s",
		(sessions.fingerprint(f"jeton-{name}"),),
	)


@then(
	parsers.re(
		r"le bandeau des connexions à distance montre 1 connexion demandée, qui nomme (?P<names>.+), et dit"
		r" « (?P<said>[^»]+) »"
	)
)
def requested_saying(interface: Context, qtbot: QtBot, names: str, said: str) -> None:
	qtbot.waitUntil(lambda: (banner(interface).texts() != []) and (said in banner(interface).texts()[0]), timeout=5000)
	(text,) = banner(interface).texts()
	for name in NAME.findall(names):
		assert name in text, text


@then(
	parsers.re(r"le bandeau des connexions à distance montre 1 connexion demandée, qui nomme (?P<names>.+), sans code")
)
def requested(interface: Context, names: str) -> None:
	assert not banner(interface).isHidden()
	(text,) = banner(interface).texts()
	for name in NAME.findall(names):
		assert name in text, text
	assert "042" not in text, text


def _buttons(interface: Context) -> list[str]:
	found = []
	for name in ("accept_remote_connection", "refuse_remote_connection"):
		if banner(interface).findChildren(QPushButton, name) != []:
			found.append(name)
	return found


@then("le bandeau propose d'accepter et de refuser la connexion")
def both_buttons(interface: Context) -> None:
	assert _buttons(interface) == ["accept_remote_connection", "refuse_remote_connection"]


@then("le bandeau ne propose plus que de refuser la connexion")
def refuse_only(interface: Context, qtbot: QtBot) -> None:
	qtbot.waitUntil(lambda: _buttons(interface) == ["refuse_remote_connection"], timeout=5000)


@then(parsers.parse("la dernière session de « {name} » est acceptée au pupitre"))
def last_accepted(empty_database: Connection, name: str) -> None:
	found = empty_database.execute(
		"SELECT s.accepted_at IS NOT NULL FROM api_sessions s JOIN api_users u ON u.id = s.user_id"
		" WHERE u.name = %s ORDER BY s.id DESC LIMIT 1",
		(name,),
	).fetchone()
	assert found == (True,)


@then("le bandeau des connexions à distance est caché")
def hidden(interface: Context) -> None:
	assert banner(interface).isHidden()


@given(parsers.parse("la connexion à valider de « {name} » a déjà reçu {count:d} codes faux"))
def wrong_codes(empty_database: Connection, name: str, count: int) -> None:
	empty_database.execute(
		"UPDATE api_sessions SET attempts = %s WHERE token_hash = %s", (count, sessions.fingerprint(f"jeton-{name}"))
	)


@then(
	parsers.re(
		r"le bandeau des connexions à distance montre 1 connexion, qui nomme (?P<names>.+) et le code « (?P<code>[^»]+) »"
	)
)
def shown(interface: Context, names: str, code: str) -> None:
	assert not banner(interface).isHidden()
	(text,) = banner(interface).texts()
	for name in NAME.findall(names):
		assert name in text, text
	assert f"<b>{code}</b>" in text, text


@then(parsers.parse("la dernière session de « {name} » est invalide"))
def last_invalid(empty_database: Connection, name: str) -> None:
	row = empty_database.execute(
		"SELECT s.state::text FROM api_sessions s JOIN api_users u ON u.id = s.user_id WHERE u.name = %s"
		" ORDER BY s.id DESC LIMIT 1",
		(name,),
	).fetchone()
	assert row == ("invalid",)


@when("je choisis la première session de l'onglet API")
def first_session(interface: Context) -> None:
	tree = screen(interface).ui.sessions
	tree.setCurrentItem(tree.topLevelItem(0))


@then("les sessions de l'onglet API sont :")
def sessions_shown(interface: Context, datatable: list[list[str]]) -> None:
	tree = screen(interface).ui.sessions
	lines = []
	for index in range(tree.topLevelItemCount()):
		line = tree.topLevelItem(index)
		assert line is not None
		lines.append([line.text(0), line.text(1), line.text(4), line.text(5)])
	expected = []
	for row in datatable[1:]:
		cells = []
		for cell in row:
			cells.append(cell.strip())
		expected.append(cells)
	assert lines == expected


@then("« Invalider la session » est grisé")
def invalidate_greyed(interface: Context) -> None:
	assert not screen(interface).ui.invalidate_session.isEnabled()


@then(parsers.parse("un jeton a été montré pour « {name} »"))
def token_shown(interface: Context, name: str) -> None:
	shown_list = interface.shown_tokens  # type: ignore[attr-defined]
	assert len(shown_list) == 1
	assert shown_list[0][0] == name


@then(
	parsers.parse(
		"la base garde de ce jeton son empreinte seulement, en session valide de « {name} », générée au pupitre, pour"
		" {hours:d} heures"
	)
)
def token_stored(interface: Context, empty_database: Connection, name: str, hours: int) -> None:
	value = interface.shown_tokens[0][1]  # type: ignore[attr-defined]
	row = empty_database.execute(
		"SELECT u.name, s.state::text, s.origin::text, s.expires_at - s.validated_at FROM api_sessions s"
		" JOIN api_users u ON u.id = s.user_id WHERE s.token_hash = %s",
		(sessions.fingerprint(value),),
	).fetchone()
	assert row == (name, "valid", "interface", timedelta(hours=hours))
	assert empty_database.execute("SELECT count(*) FROM api_sessions WHERE token_hash = %s", (value,)).fetchone() == (
		0,
	)
