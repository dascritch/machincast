"""Scénarios de l'audit complet demandé pour certains sonores (https://github.com/dascritch/machincast/issues/114).

Les étapes des fichiers, des sonores et de l'indexeur sont dans tests/etapes_indexation.py.
"""

import psycopg
from pytest_bdd import given, scenarios, then

scenarios("audit_demande.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


def audit_demande(base: Connexion, sonore: int) -> object:
	ligne = base.execute("SELECT audit_demande FROM sonores WHERE id = %s", (sonore,)).fetchone()
	assert ligne is not None
	return ligne[0]


@given("un audit complet demandé pour ce sonore")
def demander(base_vide: Connexion, sonore: int) -> None:
	base_vide.execute("UPDATE sonores SET audit_demande = true WHERE id = %s", (sonore,))


@then("ce sonore n'a plus d'audit complet demandé")
def plus_demande(base_vide: Connexion, sonore: int) -> None:
	assert audit_demande(base_vide, sonore) is False


@then("ce sonore a toujours un audit complet demandé")
def toujours_demande(base_vide: Connexion, sonore: int) -> None:
	assert audit_demande(base_vide, sonore) is True
