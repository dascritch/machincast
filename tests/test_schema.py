"""Étapes des scénarios du schéma initial de la base de données."""

import gc
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

import psycopg
import pytest
from psycopg import sql
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import TABLES, TYPES, annuler_migrations, appliquer_migrations, url_yoyo
from tests.base_test import parametres_base_test

scenarios("schema.feature")

# Sépare « col = val, col = val » sur les virgules suivies d'un nom de colonne et d'un signe égal,
# pour ne pas couper les valeurs qui contiennent elles-mêmes des virgules ('{1,2,3}').
SEPARATEUR = re.compile(r",\s*(?=\w+\s*=)")
REFERENCE = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


@dataclass
class Contexte:
	connexion: psycopg.Connection[tuple[object, ...]]
	references: dict[str, int] = field(default_factory=dict)
	erreur: psycopg.Error | None = None
	modifie_le: datetime | None = None
	connexions_avant: int = 0
	connexions_apres: int = 0


@pytest.fixture
def contexte(base_vide: psycopg.Connection[tuple[object, ...]]) -> Contexte:
	return Contexte(connexion=base_vide)


def executer_insertion(
	contexte: Contexte, table: str, valeurs: dict[str, str], retour: str = ""
) -> psycopg.Cursor[tuple[object, ...]]:
	# Les valeurs sont des littéraux SQL écrits dans les scénarios : elles sont insérées telles quelles.
	requete = sql.SQL("INSERT INTO {} ({}) VALUES ({})" + retour).format(
		sql.Identifier(table),
		sql.SQL(", ").join(sql.Identifier(c) for c in valeurs),
		sql.SQL(", ").join(sql.SQL(v) for v in valeurs.values()),
	)
	return contexte.connexion.execute(requete)


def inserer(contexte: Contexte, table: str, valeurs: dict[str, str]) -> int:
	"""Insère une ligne et renvoie son identifiant."""
	ligne = executer_insertion(contexte, table, valeurs, " RETURNING id").fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


def analyser(contexte: Contexte, valeurs: str) -> dict[str, str]:
	# Remplace {banque}, {sonore}… par les identifiants de référence, sans toucher aux tableaux '{1,2,3}'.
	valeurs = REFERENCE.sub(lambda m: str(contexte.references.get(m.group(1), m.group(0))), valeurs)
	paires = [p.split("=", 1) for p in SEPARATEUR.split(valeurs.strip().strip(",")) if p.strip()]
	return {cle.strip(): valeur.strip() for cle, valeur in paires}


# ─── Étant donné ───────────────────────────────────────────


@given("une base de test vide où les migrations sont appliquées")
def base_migree(contexte: Contexte) -> None:
	"""La fixture base_vide fournit déjà une base migrée et purgée."""


@given("les éléments de référence en base")
def references(contexte: Contexte) -> None:
	r = contexte.references
	r["marque_page"] = inserer(
		contexte, "marques_pages_streams", {"nom": "'Studio mobile'", "url": "'https://flux.exemple'"}
	)
	r["banque"] = inserer(contexte, "banques", {"nom_interne": "'Jingles'", "mode": "'aleatoire'"})
	r["sonore"] = inserer(
		contexte,
		"sonores",
		{"type": "'fichier'", "emplacement": "'/jingles/reference.flac'", "titre": "'Titre de référence'"},
	)
	r["evenement"] = inserer(contexte, "evenements", {"nom_interne": "'Fil'", "priorite": "'fil_musical'"})


@given("un deuxième sonore en base")
def deuxieme_sonore(contexte: Contexte) -> None:
	contexte.references["sonore2"] = inserer(
		contexte, "sonores", {"type": "'fichier'", "emplacement": "'/jingles/deuxieme.flac'"}
	)


@given("un événement de secours en base")
def evenement_de_secours(contexte: Contexte) -> None:
	contexte.references["secours"] = inserer(
		contexte, "evenements", {"nom_interne": "'Secours du direct'", "priorite": "'secours'"}
	)


@given("un stream secouru par cet événement")
def stream_secouru(contexte: Contexte) -> None:
	contexte.references["stream"] = inserer(
		contexte,
		"sonores",
		{
			"type": "'stream'",
			"url_stream": "'https://flux.exemple/direct'",
			"secours_evenement_id": str(contexte.references["secours"]),
		},
	)


@when("je passe l'événement de secours en émission")
def secours_en_emission(contexte: Contexte) -> None:
	try:
		contexte.connexion.execute(
			"UPDATE evenements SET priorite = 'emission', debut = '2026-10-19 18:00' WHERE id = %s",
			(contexte.references["secours"],),
		)
	except psycopg.Error as erreur:
		contexte.erreur = erreur


@when("je supprime l'événement de secours")
def supprimer_secours(contexte: Contexte) -> None:
	contexte.connexion.execute("DELETE FROM evenements WHERE id = %s", (contexte.references["secours"],))


@then("le stream n'a plus d'événement de secours")
def stream_sans_secours(contexte: Contexte) -> None:
	ligne = contexte.connexion.execute(
		"SELECT secours_evenement_id FROM sonores WHERE id = %s", (contexte.references["stream"],)
	).fetchone()
	assert ligne == (None,)


@given("une deuxième banque en base")
def deuxieme_banque(contexte: Contexte) -> None:
	contexte.references["banque2"] = inserer(
		contexte, "banques", {"nom_interne": "'Habillages hors saison'", "mode": "'sequentiel'"}
	)


@given("un passage du sonore de référence dans l'airplay")
def passage(contexte: Contexte) -> None:
	inserer(
		contexte,
		"airplay",
		{
			"passage_id": "gen_random_uuid()",
			"type_ligne": "'debut'",
			"sonore_id": str(contexte.references["sonore"]),
			"emplacement": "'/jingles/reference.flac'",
			"titre": "'Titre de référence'",
		},
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse('j\'enregistre dans "{table}" : {valeurs}'))
def enregistrer(contexte: Contexte, table: str, valeurs: str) -> None:
	try:
		executer_insertion(contexte, table, analyser(contexte, valeurs))
	except psycopg.Error as erreur:
		contexte.erreur = erreur


@when(parsers.parse('j\'enregistre dans "{table}" :'))
def enregistrer_vide(contexte: Contexte, table: str) -> None:
	enregistrer(contexte, table, "")


@when("j'annule toutes les migrations")
def annuler(contexte: Contexte) -> None:
	annuler_migrations(url_yoyo(*parametres_base_test()))


def connexions_ouvertes(contexte: Contexte) -> int:
	"""Connexions du compte courant à la base de test, celle du scénario comprise."""
	ligne = contexte.connexion.execute(
		"SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND usename = current_user"
	).fetchone()
	assert ligne is not None and isinstance(ligne[0], int)
	return ligne[0]


def sans_ramasse_miettes(contexte: Contexte, migration: Callable[[str], None]) -> None:
	"""Lance la migration ramasse-miettes suspendu, et note les connexions ouvertes avant et après."""
	contexte.connexions_avant = connexions_ouvertes(contexte)
	gc.disable()
	try:
		migration(url_yoyo(*parametres_base_test()))
		# Une connexion fermée quitte pg_stat_activity peu après : quelques instants pour s'en assurer.
		limite = time.monotonic() + 2
		while (apres := connexions_ouvertes(contexte)) > contexte.connexions_avant and time.monotonic() < limite:
			time.sleep(0.05)
		contexte.connexions_apres = apres
	finally:
		gc.enable()


@when("j'applique les migrations, ramasse-miettes suspendu")
def appliquer_sans_ramasse_miettes(contexte: Contexte) -> None:
	sans_ramasse_miettes(contexte, appliquer_migrations)


@when("j'annule toutes les migrations, ramasse-miettes suspendu")
def annuler_sans_ramasse_miettes(contexte: Contexte) -> None:
	sans_ramasse_miettes(contexte, annuler_migrations)


@then("aucune connexion supplémentaire à la base de test ne reste ouverte")
def aucune_connexion_restante(contexte: Contexte) -> None:
	assert contexte.connexions_apres == contexte.connexions_avant, (
		contexte.connexions_avant,
		contexte.connexions_apres,
	)


@when("je modifie le titre du sonore de référence")
def modifier_titre(contexte: Contexte) -> None:
	identifiant = contexte.references["sonore"]
	ligne = contexte.connexion.execute("SELECT modifie_le FROM sonores WHERE id = %s", (identifiant,)).fetchone()
	assert ligne is not None and isinstance(ligne[0], datetime)
	contexte.modifie_le = ligne[0]
	contexte.connexion.execute("UPDATE sonores SET titre = 'Nouveau titre' WHERE id = %s", (identifiant,))


@given("un élément de l'événement de référence, joué dans l'airplay")
def element_joue(contexte: Contexte) -> None:
	r = contexte.references
	r["element"] = inserer(
		contexte,
		"evenements_elements",
		{"evenement_id": str(r["evenement"]), "position": "1", "sonore_id": str(r["sonore"])},
	)
	inserer(
		contexte,
		"airplay",
		{
			"passage_id": "gen_random_uuid()",
			"type_ligne": "'debut'",
			"sonore_id": str(r["sonore"]),
			"evenement_id": str(r["evenement"]),
			"element_id": str(r["element"]),
		},
	)


@when("je supprime cet élément de l'événement")
def supprimer_element(contexte: Contexte) -> None:
	contexte.connexion.execute("DELETE FROM evenements_elements WHERE id = %s", (contexte.references["element"],))


@when("je supprime le sonore de référence")
def supprimer_sonore(contexte: Contexte) -> None:
	contexte.connexion.execute("DELETE FROM sonores WHERE id = %s", (contexte.references["sonore"],))


# ─── Alors ─────────────────────────────────────────────────


def tables_presentes(contexte: Contexte) -> set[str]:
	lignes = contexte.connexion.execute(
		"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
	).fetchall()
	return {str(ligne[0]) for ligne in lignes}


@then("la base contient les tables :")
def contient_tables(contexte: Contexte, datatable: list[list[str]]) -> None:
	attendues = {ligne[0] for ligne in datatable[1:]}
	assert attendues == set(TABLES)
	assert attendues <= tables_presentes(contexte)


@then("la base ne contient plus aucune table ni aucun type de MachinCast")
def plus_de_tables(contexte: Contexte) -> None:
	assert not set(TABLES) & tables_presentes(contexte)
	types = contexte.connexion.execute("SELECT typname FROM pg_type WHERE typname = ANY(%s)", (list(TYPES),)).fetchall()
	assert types == []


@then("la base accepte l'enregistrement")
def accepte(contexte: Contexte) -> None:
	assert contexte.erreur is None, f"refusé : {contexte.erreur}"


@then("la base refuse l'enregistrement")
def refuse(contexte: Contexte) -> None:
	assert contexte.erreur is not None, "la base aurait dû refuser l'enregistrement"
	# Une contrainte violée, une valeur hors d'un type ENUM ou un texte trop long,
	# et non une faute de syntaxe dans le scénario.
	assert isinstance(
		contexte.erreur,
		psycopg.errors.IntegrityError
		| psycopg.errors.InvalidTextRepresentation
		| psycopg.errors.StringDataRightTruncation,
	), repr(contexte.erreur)


def comparer(contexte: Contexte, type_enum: str, premier: str, second: str) -> bool:
	requete = sql.SQL("SELECT %s::{type} < %s::{type}").format(type=sql.Identifier(type_enum))
	ligne = contexte.connexion.execute(requete, (premier, second)).fetchone()
	assert ligne is not None
	return ligne[0] is True


@then(parsers.parse('la priorité "{premiere}" est inférieure à "{seconde}"'))
def priorite_inferieure(contexte: Contexte, premiere: str, seconde: str) -> None:
	assert comparer(contexte, "priorite_evenement", premiere, seconde)


@then(parsers.parse('le jour "{premier}" vient avant "{second}"'))
def jour_avant(contexte: Contexte, premier: str, second: str) -> None:
	assert comparer(contexte, "jour_semaine", premier, second)


@then("sa date de modification a avancé")
def date_avancee(contexte: Contexte) -> None:
	ligne = contexte.connexion.execute(
		"SELECT modifie_le FROM sonores WHERE id = %s", (contexte.references["sonore"],)
	).fetchone()
	assert ligne is not None and isinstance(ligne[0], datetime)
	assert contexte.modifie_le is not None and ligne[0] > contexte.modifie_le


@then("la ligne d'airplay existe toujours, sans référence à l'élément")
def airplay_sans_element(contexte: Contexte) -> None:
	lignes = contexte.connexion.execute("SELECT element_id, evenement_id FROM airplay").fetchall()
	assert lignes == [(None, contexte.references["evenement"])]


@then("la ligne d'airplay existe toujours, avec son titre recopié et sans référence au sonore")
def airplay_conserve(contexte: Contexte) -> None:
	lignes = contexte.connexion.execute("SELECT sonore_id, titre FROM airplay").fetchall()
	assert lignes == [(None, "Titre de référence")]
