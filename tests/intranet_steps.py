"""Étapes partagées des scénarios de l'intranet et de ses comptes (https://github.com/dascritch/machincast/issues/537).

Chargé comme greffon pytest par tests/conftest.py.
"""

from PySide6.QtCore import Qt
from pytest_bdd import given, parsers, when

from machincast.interface.api_tab import ApiScreen
from machincast.shared import passwords
from tests.interface_steps import Connection, Context, window

ROLES = {"consulter": "consult", "actions API": "actions"}
STATES = {"actif": False, "désactivé": True}


@given("les comptes de l'intranet :")
def accounts(empty_database: Connection, datatable: list[list[str]]) -> None:
	for name, password, role, state in datatable[1:]:
		empty_database.execute(
			"INSERT INTO api_users (name, password_hash, role, disabled_at) VALUES (%s, %s, %s,"
			" CASE WHEN %s THEN clock_timestamp() END)",
			(name.strip(), passwords.digest(password.strip()), ROLES[role.strip()], STATES[state.strip()]),
		)


def screen(interface: Context) -> ApiScreen:
	"""L'onglet « API », ouvert au premier plan."""
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, ApiScreen)
	return opened


@when(parsers.parse("je choisis le compte « {name} » dans l'onglet API"))
def choose(interface: Context, name: str) -> None:
	users = screen(interface).ui.users
	found = users.findItems(name, Qt.MatchFlag.MatchExactly, 0)
	assert len(found) == 1, name
	users.setCurrentItem(found[0])
