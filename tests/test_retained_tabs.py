"""Scénarios des onglets retenus d'un lancement à l'autre (https://github.com/dascritch/machincast/issues/321).

Chaque test a son propre fichier de réglages des vues (tests/conftest.py, view_settings) : jamais celui du compte.
Les étapes de la fenêtre, des onglets et des éléments en base sont dans tests/interface_steps.py.
"""

from pytest_bdd import parsers, scenarios, when

from tests.interface_steps import Connection

scenarios("retained_tabs.feature")


@when(parsers.parse("le sonore « {title} » est supprimé en base, depuis un autre poste"))
def deleted(empty_database: Connection, title: str) -> None:
	empty_database.execute("UPDATE sounds SET deleted_at = now() WHERE title = %s", (title,))
