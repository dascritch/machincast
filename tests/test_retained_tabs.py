"""Scénarios des onglets retenus d'un lancement à l'autre (https://github.com/dascritch/machincast/issues/321).

Chaque test a son propre fichier de réglages des vues (tests/conftest.py, view_settings) : jamais celui du compte.
Les étapes de la fenêtre, des onglets et des éléments en base sont dans tests/interface_steps.py.
"""

from pytest_bdd import given, parsers, scenarios, when

from machincast.interface import columns
from machincast.interface.window import ACTIVE_TAB_KEY, TAB_KEY
from tests.interface_steps import Connection

scenarios("retained_tabs.feature")


@when(parsers.parse("le sonore « {title} » est supprimé en base, depuis un autre poste"))
def deleted(empty_database: Connection, title: str) -> None:
	empty_database.execute("UPDATE sounds SET deleted_at = now() WHERE title = %s", (title,))


@given(
	parsers.parse(
		"les onglets retenus par une version d'avant, aux clés françaises, la fiche de la banque « {name} » active"
	)
)
def old_tabs(empty_database: Connection, name: str) -> None:
	"""Les clés d'avant https://github.com/dascritch/machincast/issues/368 : « antenne », « fiche:banque:12 »."""
	line = empty_database.execute("SELECT id FROM banks WHERE internal_name = %s", (name,)).fetchone()
	assert line is not None, name
	card = f"fiche:banque:{line[0]}"
	settings = columns.settings()
	settings.setValue(TAB_KEY, ["antenne", "calendrier", "liste:Feeds", "incidents", card])
	settings.setValue(ACTIVE_TAB_KEY, card)
