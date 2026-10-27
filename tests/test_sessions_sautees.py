"""Scénarios des sessions sautées, à la diffusion (https://github.com/dascritch/machincast/issues/273).

La diffusion tourne sur le moteur simulé, qui suit l'horloge du binaire. Les étapes partagées de la diffusion sont dans
tests/etapes_diffusion.py ; une demande arrive par une vraie socket d'état, comme dans test_interruption.py.
"""

from datetime import date

import psycopg
from pytest_bdd import given, parsers, scenarios

from machincast.lecture.grille import JOURS

scenarios("sessions_sautees.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


@given(parsers.re(r"l'émission « (?P<nom>[^»]+) » revient (?P<jours>chaque .+)"))
def recurrence(base_vide: Connexion, nom: str, jours: str) -> None:
	noms = [jour.strip() for jour in jours.replace("chaque", "").split(" et ")]
	assert all(jour in JOURS for jour in noms), noms
	base_vide.execute("UPDATE evenements SET jours_recurrence = %s WHERE nom_interne = %s", (noms, nom))


@given(parsers.parse("la session du {jour} de l'événement « {nom} » est rétablie"))
def retablir(base_vide: Connexion, jour: str, nom: str) -> None:
	base_vide.execute(
		"DELETE FROM evenements_sauts"
		" WHERE jour = %s AND evenement_id = (SELECT id FROM evenements WHERE nom_interne = %s)",
		(date.fromisoformat(jour), nom),
	)
