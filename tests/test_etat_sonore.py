"""Étapes des scénarios de l'état d'un sonore (https://github.com/dascritch/machincast/issues/66)."""

import psycopg
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("etat_sonore.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


@given("une base de test vide où les migrations sont appliquées")
def base_migree(base_vide: Connexion) -> None:
	"""base_vide applique déjà toutes les migrations."""


@when("j'enregistre un sonore sans préciser son état", target_fixture="sonore")
def enregistrer(base_vide: Connexion) -> int:
	ligne = base_vide.execute(
		"INSERT INTO sonores (type, emplacement) VALUES ('fichier', '/a.flac') RETURNING id"
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


@then(parsers.parse('le type "{nom}" a pour valeurs, dans l\'ordre : {valeurs}'))
def valeurs_du_type(base_vide: Connexion, nom: str, valeurs: str) -> None:
	lignes = base_vide.execute(
		"SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid = enumtypid"
		" WHERE typname = %s ORDER BY enumsortorder",
		(nom,),
	).fetchall()
	assert [ligne[0] for ligne in lignes] == [valeur.strip() for valeur in valeurs.split(",")]


@then(parsers.parse("son état est « {etat} »"))
def etat_du_sonore(base_vide: Connexion, sonore: int, etat: str) -> None:
	ligne = base_vide.execute("SELECT etat::text FROM sonores WHERE id = %s", (sonore,)).fetchone()
	assert ligne == (etat,)


@then(parsers.parse("un sonore à l'état « {etat} » est refusé"))
def etat_refuse(base_vide: Connexion, etat: str) -> None:
	try:
		base_vide.execute("INSERT INTO sonores (type, emplacement, etat) VALUES ('fichier', '/x.flac', %s)", (etat,))
	except psycopg.errors.InvalidTextRepresentation:
		return
	raise AssertionError(f"l'état « {etat} » aurait dû être refusé")
