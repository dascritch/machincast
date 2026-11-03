"""Scénarios des onglets retenus d'un lancement à l'autre (https://github.com/dascritch/machincast/issues/321).

Chaque test a son propre fichier de réglages des vues (tests/conftest.py, reglages_des_vues) : jamais celui du compte.
Les étapes de la fenêtre, des onglets et des éléments en base sont dans tests/etapes_interface.py.
"""

from pytest_bdd import parsers, scenarios, when

from tests.etapes_interface import Connexion

scenarios("onglets_retenus.feature")


@when(parsers.parse("le sonore « {titre} » est supprimé en base, depuis un autre poste"))
def supprime(base_vide: Connexion, titre: str) -> None:
	base_vide.execute("UPDATE sounds SET deleted_at = now() WHERE title = %s", (titre,))
