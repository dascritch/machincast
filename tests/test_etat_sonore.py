"""Étapes des scénarios de l'état d'un sonore (https://github.com/dascritch/machincast/issues/66)."""

from collections.abc import Callable
from typing import Any

import psycopg
from pytest_bdd import given, parsers, scenarios, then, when
from yoyo import get_backend, read_migrations

from machincast.base import REPERTOIRE_MIGRATIONS, url_yoyo
from tests.base_test import parametres_base_test

scenarios("etat_sonore.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ETATS = ("actif", "desactive", "expire", "errone", "supprime")


def migrations(selection: Callable[[str], bool]) -> tuple[Any, Any]:
	"""Le backend yoyo de la base de test et les migrations dont l'identifiant vérifie la sélection."""
	backend = get_backend(url_yoyo(*parametres_base_test()))
	toutes = read_migrations(str(REPERTOIRE_MIGRATIONS))
	return backend, toutes.filter(lambda migration: selection(migration.id))


@given("une base de test vide où les migrations sont appliquées")
def base_migree(base_vide: Connexion) -> None:
	"""base_vide applique déjà toutes les migrations."""


@given(parsers.parse("une base où seules les migrations antérieures à « {numero} » sont appliquées"))
def base_partielle(base_vide: Connexion, numero: str) -> None:
	"""Schéma recréé avec les seules migrations antérieures ; base_vide réappliquera les autres au scénario suivant."""
	base_vide.execute("DROP SCHEMA public CASCADE")
	base_vide.execute("CREATE SCHEMA public AUTHORIZATION pg_database_owner")
	base_vide.execute("GRANT USAGE ON SCHEMA public TO PUBLIC")
	backend, anterieures = migrations(lambda identifiant: identifiant < numero)
	with backend.lock():
		backend.apply_migrations(backend.to_apply(anterieures))


@given("dans cette base, les sonores :")
def sonores_anciens(base_vide: Connexion, datatable: list[list[str]]) -> None:
	for emplacement, actif, champs_edites in datatable[1:]:
		base_vide.execute(
			"INSERT INTO sonores (type, emplacement, actif, champs_edites) VALUES ('fichier', %s, %s, %s)",
			(emplacement, actif == "true", champs_edites),
		)


@given("un sonore dans chacun des cinq états")
def sonores_par_etat(base_vide: Connexion) -> None:
	for etat in ETATS:
		base_vide.execute(
			"INSERT INTO sonores (type, emplacement, etat) VALUES ('fichier', %s, %s)", (f"/{etat}.flac", etat)
		)


@when("j'applique les migrations restantes")
def appliquer_restantes(base_vide: Connexion) -> None:
	backend, toutes = migrations(lambda identifiant: True)
	with backend.lock():
		backend.apply_migrations(backend.to_apply(toutes))


@when(parsers.parse("j'annule la migration « {numero} »"))
def annuler(base_vide: Connexion, numero: str) -> None:
	# Annuler une migration annule aussi les suivantes, qui peuvent en dépendre.
	backend, selection = migrations(lambda identifiant: identifiant >= numero)
	with backend.lock():
		backend.rollback_migrations(backend.to_rollback(selection))


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


@then(parsers.parse('la table "{table}" n\'a pas de colonne "{colonne}"'))
def sans_colonne(base_vide: Connexion, table: str, colonne: str) -> None:
	ligne = base_vide.execute(
		"SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s", (table, colonne)
	).fetchone()
	assert ligne is None


@then("les sonores sont devenus :")
def sonores_convertis(base_vide: Connexion, datatable: list[list[str]]) -> None:
	lignes = base_vide.execute("SELECT emplacement, etat::text, champs_edites::text FROM sonores ORDER BY emplacement")
	assert [list(ligne) for ligne in lignes.fetchall()] == datatable[1:]


@then(parsers.parse("seul le sonore qui était à l'état « {etat} » est actif"))
def seul_actif(base_vide: Connexion, etat: str) -> None:
	lignes = base_vide.execute("SELECT emplacement FROM sonores WHERE actif ORDER BY emplacement").fetchall()
	assert lignes == [(f"/{etat}.flac",)]


@given(parsers.parse("un sonore à l'état « {premier} » et un sonore à l'état « {second} »"))
def deux_sonores(base_vide: Connexion, premier: str, second: str) -> None:
	for etat in (premier, second):
		base_vide.execute(
			"INSERT INTO sonores (type, emplacement, etat) VALUES ('fichier', %s, %s)", (f"/{etat}.flac", etat)
		)


@then(parsers.parse("les sonores sont aux états « {premier} » et « {second} »"))
def etats_des_sonores(base_vide: Connexion, premier: str, second: str) -> None:
	lignes = base_vide.execute("SELECT etat::text FROM sonores ORDER BY id").fetchall()
	assert [ligne[0] for ligne in lignes] == [premier, second]
