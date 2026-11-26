"""Scénarios des comptes de l'intranet et de l'API, dans l'onglet « API »
(https://github.com/dascritch/machincast/issues/537)."""

import re

from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QTreeWidgetItem, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import api_tab
from machincast.interface.api_tab import Account, ApiUserDialog
from machincast.shared import passwords
from machincast.webserver import sessions
from tests.interface_steps import NAME, Connection, Context, window
from tests.intranet_steps import ROLES, screen

scenarios("api_users.feature")


def _answer(interface: Context, account: Account | None) -> None:
	interface.monkeypatch.setattr(api_tab, "ask_account", lambda _parent, _connection, _name: account)


@when(parsers.parse("je crée le compte « {name} », mot de passe « {password} », rôle « {role} »"))
def create(interface: Context, name: str, password: str, role: str) -> None:
	_answer(interface, Account(name, password, ROLES[role]))
	screen(interface).ui.new_user.click()


@when(parsers.parse("je donne au compte le rôle « {role} »"))
def give_role(interface: Context, role: str) -> None:
	choice = screen(interface).ui.role
	index = choice.findData(ROLES[role])
	choice.setCurrentIndex(index)
	choice.activated.emit(index)


@when(parsers.parse("je change le mot de passe du compte pour « {password} »"))
def change_password(interface: Context, password: str) -> None:
	opened = screen(interface)
	_answer(interface, Account(opened.ui.users.currentItem().text(0), password, ""))  # type: ignore[union-attr]
	opened.ui.change_password.click()


@when(parsers.re(r"je supprime le compte, en répondant « (?P<response>❌ Supprimer|Annuler) »"))
def delete(interface: Context, response: str) -> None:
	interface.deletion = response == "❌ Supprimer"
	screen(interface).ui.delete.click()


@when(
	parsers.re(
		r"je saisis dans la fenêtre d'un nouveau compte « (?P<name>[^»]*) », « (?P<password>[^»]*) »,"
		r" confirmé par « (?P<confirmation>[^»]*) », puis OK"
	)
)
def fill(interface: Context, qtbot: QtBot, name: str, password: str, confirmation: str) -> None:
	assert interface.connection is not None
	dialog = ApiUserDialog(window(interface), interface.connection, None)
	qtbot.addWidget(dialog)
	dialog.ui.name.setText(name)
	dialog.ui.password.setText(password)
	dialog.ui.confirmation.setText(confirmation)
	dialog.show()
	dialog.ui.buttons.button(QDialogButtonBox.StandardButton.Ok).click()
	QApplication.processEvents()
	interface.dialog = dialog  # type: ignore[attr-defined]


@then(parsers.parse("la fenêtre du compte reste ouverte, et dit « {text} »"))
def refused(interface: Context, text: str) -> None:
	dialog = interface.dialog  # type: ignore[attr-defined]
	assert dialog.isVisible()
	assert dialog.result() != QDialog.DialogCode.Accepted
	assert dialog.ui.refusal.text() == text


@then("la fenêtre du compte est acceptée")
def accepted(interface: Context) -> None:
	dialog = interface.dialog  # type: ignore[attr-defined]
	assert dialog.result() == QDialog.DialogCode.Accepted


@then("les comptes de l'onglet API sont :")
def shown(interface: Context, datatable: list[list[str]]) -> None:
	users = screen(interface).ui.users
	lines = []
	for index in range(users.topLevelItemCount()):
		line = users.topLevelItem(index)
		assert line is not None
		lines.append([line.text(0), line.text(1), line.text(2)])
	expected = []
	for line in datatable[1:]:
		cells = []
		for cell in line:
			cells.append(cell.strip())
		expected.append(cells)
	assert lines == expected


@then(parsers.parse("le compte « {name} » est choisi dans l'onglet API"))
def chosen(interface: Context, name: str) -> None:
	line = screen(interface).ui.users.currentItem()
	assert line is not None
	assert line.text(0) == name


@then(parsers.re(r"les boutons (?P<names>.+) de l'onglet API sont grisés"))
def greyed(interface: Context, names: str) -> None:
	ui = screen(interface).ui
	buttons: dict[str, QWidget] = {}
	for button in (ui.new_user, ui.change_password, ui.disable, ui.delete):
		buttons[button.text()] = button
	for name in NAME.findall(names):
		assert not buttons[name].isEnabled(), name
	assert not ui.role.isEnabled()
	assert ui.new_user.isEnabled()


@then(parsers.parse("la base garde, pour « {name} », l'empreinte de « {password} », jamais le mot de passe lui-même"))
def fingerprint(empty_database: Connection, name: str, password: str) -> None:
	row = empty_database.execute("SELECT password_hash FROM api_users WHERE name = %s", (name,)).fetchone()
	assert row is not None
	stored = str(row[0])
	assert password not in stored
	assert passwords.matches(password, stored)
	assert not passwords.matches(password + "!", stored)


@given(parsers.parse("« {name} » a une session valide et une session à valider"))
def two_sessions(empty_database: Connection, name: str) -> None:
	empty_database.execute(
		"INSERT INTO api_sessions (user_id, token_hash, state, validated_at, expires_at)"
		" SELECT id, %s, 'valid', clock_timestamp(), clock_timestamp() + interval '1 hour' FROM api_users"
		" WHERE name = %s",
		(sessions.fingerprint(f"valide-{name}"), name),
	)
	empty_database.execute(
		"INSERT INTO api_sessions (user_id, token_hash, code, validate_before)"
		" SELECT id, %s, '123456', clock_timestamp() + interval '10 minutes' FROM api_users WHERE name = %s",
		(sessions.fingerprint(f"attente-{name}"), name),
	)


def _states(empty_database: Connection, name: str) -> list[str]:
	found = []
	for (state,) in empty_database.execute(
		"SELECT s.state::text FROM api_sessions s JOIN api_users u ON u.id = s.user_id WHERE u.name = %s ORDER BY s.id",
		(name,),
	).fetchall():
		found.append(str(state))
	return found


@then(parsers.parse("les sessions de « {name} » sont toutes invalides"))
def all_invalid(empty_database: Connection, name: str) -> None:
	assert _states(empty_database, name) == ["invalid", "invalid"]


@then(parsers.parse("« {name} » a encore 1 session valide et 1 session à valider"))
def untouched(empty_database: Connection, name: str) -> None:
	assert _states(empty_database, name) == ["valid", "pending"]


# ─── Le second facteur (https://github.com/dascritch/machincast/issues/601) ───


@when(
	parsers.re(
		r"je règle l'application d'authentification du compte, en répondant « (?P<response>Enregistrer|Annuler) »"
	)
)
def set_up_authenticator(interface: Context, response: str) -> None:
	shown: list[tuple[str, str]] = []

	def show(_parent: object, _name: str, secret: str, uri: str) -> bool:
		shown.append((secret, uri))
		return response == "Enregistrer"

	interface.monkeypatch.setattr(api_tab, "show_authenticator", show)
	interface.authenticator = shown  # type: ignore[attr-defined]
	screen(interface).ui.authenticator.click()


@then(parsers.parse("la fenêtre a montré une clé de 32 caractères, en groupes de quatre, et son adresse « {uri} »"))
def authenticator_shown(interface: Context, uri: str) -> None:
	((secret, given),) = interface.authenticator  # type: ignore[attr-defined]
	assert re.fullmatch(r"[A-Z2-7]{32}", secret), secret
	assert api_tab.grouped(secret).split(" ") == re.findall(r".{4}", secret)
	assert given == uri.replace("…", secret)


def _secret(empty_database: Connection, name: str) -> object:
	found = empty_database.execute("SELECT totp_secret FROM api_users WHERE name = %s", (name,)).fetchone()
	assert found is not None
	return found[0]


@then(parsers.parse("la base garde la clé de l'application d'authentification de « {name} »"))
def secret_kept(interface: Context, empty_database: Connection, name: str) -> None:
	((secret, _uri),) = interface.authenticator  # type: ignore[attr-defined]
	assert _secret(empty_database, name) == secret


@then(parsers.parse("la base ne garde pas de clé de l'application d'authentification de « {name} »"))
def no_secret(empty_database: Connection, name: str) -> None:
	assert _secret(empty_database, name) is None


@given(parsers.parse("l'application d'authentification de « {name} » réglée"))
def secret_set(empty_database: Connection, name: str) -> None:
	empty_database.execute(
		"UPDATE api_users SET totp_secret = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP' WHERE name = %s", (name,)
	)


def _line(interface: Context, name: str) -> QTreeWidgetItem:
	users = screen(interface).ui.users
	for index in range(users.topLevelItemCount()):
		line = users.topLevelItem(index)
		if (line is not None) and (line.text(0) == name):
			return line
	raise AssertionError(name)


@then(parsers.parse("l'onglet API dit, pour « {name} », l'application d'authentification « {said} »"))
def authenticator_column(interface: Context, name: str, said: str) -> None:
	assert _line(interface, name).text(4) == said


@then(parsers.parse("l'onglet API dit, pour « {name} », {count:d} navigateurs connus"))
def browsers_column(interface: Context, name: str, count: int) -> None:
	assert _line(interface, name).text(5) == str(count)


@given(parsers.re(r"« (?P<name>[^»]+) » a (?P<count>\d+) navigateurs? connus?"))
def browsers(empty_database: Connection, name: str, count: str) -> None:
	for index in range(int(count)):
		empty_database.execute(
			"INSERT INTO api_browsers (user_id, token_hash) SELECT id, %s FROM api_users WHERE name = %s",
			(sessions.fingerprint(f"navigateur-{name}-{index}"), name),
		)


def _browsers(empty_database: Connection, name: str) -> int:
	found = empty_database.execute(
		"SELECT count(*) FROM api_browsers b JOIN api_users u ON u.id = b.user_id WHERE u.name = %s", (name,)
	).fetchone()
	assert found is not None
	return int(found[0])


@then(parsers.parse("« {name} » n'a plus de navigateur connu"))
def no_browser(empty_database: Connection, name: str) -> None:
	assert _browsers(empty_database, name) == 0


@then(parsers.parse("« {name} » a encore {count:d} navigateur connu"))
def browsers_left(empty_database: Connection, name: str, count: int) -> None:
	assert _browsers(empty_database, name) == count
