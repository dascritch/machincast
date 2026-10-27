"""Scénarios d'un événement modifié pendant la diffusion (https://github.com/dascritch/machincast/issues/266).

La diffusion tourne sur le moteur simulé, qui suit l'horloge du binaire. Les étapes partagées de la diffusion, dont la
demande de relire la grille sur la socket d'état, sont dans tests/etapes_diffusion.py ; les modifications se font en
base, comme les écrirait la fiche de l'événement.
"""

import psycopg
from pytest_bdd import given, parsers, scenarios, when

from tests.etapes_diffusion import heure

scenarios("edition_evenement.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


@when(parsers.parse("l'émission « {nom} » est déplacée de {debut} à {fin}"))
def deplacer(base_vide: Connexion, nom: str, debut: str, fin: str) -> None:
	modifiees = base_vide.execute(
		"UPDATE evenements SET debut = %s, fin = %s WHERE nom_interne = %s",
		(heure(f"2026-10-14 {debut}"), heure(f"2026-10-14 {fin}"), nom),
	).rowcount
	assert modifiees == 1


@when(parsers.parse("l'événement « {nom} » est renommé « {nouveau} », avec un nom public et un masquage"))
def renommer(base_vide: Connexion, nom: str, nouveau: str) -> None:
	"""Ce qui ne règle pas l'antenne ; sa date de modification avance, comme à chaque enregistrement."""
	modifiees = base_vide.execute(
		"UPDATE evenements SET nom_interne = %s, nom_public = 'Le jour', masquer_metadonnees = true"
		" WHERE nom_interne = %s",
		(nouveau, nom),
	).rowcount
	assert modifiees == 1


@when(parsers.parse("l'émission « {nom} » finit à {fin}"))
def finir(base_vide: Connexion, nom: str, fin: str) -> None:
	modifiees = base_vide.execute(
		"UPDATE evenements SET fin = %s WHERE nom_interne = %s", (heure(f"2026-10-14 {fin}"), nom)
	).rowcount
	assert modifiees == 1


@when(parsers.parse("l'événement « {nom} » passe en fil musical"))
def en_fil_musical(base_vide: Connexion, nom: str) -> None:
	modifiees = base_vide.execute(
		"UPDATE evenements SET priorite = 'fil_musical' WHERE nom_interne = %s", (nom,)
	).rowcount
	assert modifiees == 1


@given(parsers.parse("l'émission « {nom} » a eu lieu la veille"))
def la_veille(base_vide: Connexion, nom: str) -> None:
	modifiees = base_vide.execute(
		"UPDATE evenements SET debut = debut - interval '1 day', fin = fin - interval '1 day' WHERE nom_interne = %s",
		(nom,),
	).rowcount
	assert modifiees == 1


@when(parsers.parse("l'événement « {nom} » revient aussi le {jour}"))
def revenir(base_vide: Connexion, nom: str, jour: str) -> None:
	modifiees = base_vide.execute(
		"UPDATE evenements SET jours_recurrence = array_append(jours_recurrence, %s::jour_semaine)"
		" WHERE nom_interne = %s",
		(jour, nom),
	).rowcount
	assert modifiees == 1
