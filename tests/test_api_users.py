"""Scénarios des comptes de l'intranet et de l'API, dans l'onglet « API »
(https://github.com/dascritch/machincast/issues/537)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import api_tab
from machincast.interface.api_tab import Account, ApiScreen, ApiUserDialog
from machincast.shared import passwords
from tests.interface_steps import NAME, Connection, Context, window

scenarios("api_users.feature")

ROLES = {"consulter": "consult", "actions API": "actions"}
STATES = {"actif": False, "désactivé": True}


def screen(interface: Context) -> ApiScreen:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, ApiScreen)
	return opened


@given("les comptes de l'intranet :")
def accounts(empty_database: Connection, datatable: list[list[str]]) -> None:
	for name, password, role, state in datatable[1:]:
		empty_database.execute(
			"INSERT INTO api_users (name, password_hash, role, disabled_at) VALUES (%s, %s, %s,"
			" CASE WHEN %s THEN clock_timestamp() END)",
			(name, passwords.digest(password), ROLES[role], STATES[state]),
		)


def _answer(interface: Context, account: Account | None) -> None:
	interface.monkeypatch.setattr(api_tab, "ask_account", lambda _parent, _connection, _name: account)


@when(parsers.parse("je crée le compte « {name} », mot de passe « {password} », rôle « {role} »"))
def create(interface: Context, name: str, password: str, role: str) -> None:
	_answer(interface, Account(name, password, ROLES[role]))
	screen(interface).ui.new_user.click()


@when(parsers.parse("je choisis le compte « {name} » dans l'onglet API"))
def choose(interface: Context, name: str) -> None:
	users = screen(interface).ui.users
	found = users.findItems(name, Qt.MatchFlag.MatchExactly, 0)
	assert len(found) == 1, name
	users.setCurrentItem(found[0])


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
