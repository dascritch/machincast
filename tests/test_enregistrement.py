"""Étapes de l'enregistrement de l'airplay et du log (https://github.com/dascritch/machincast/issues/17)."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.lecture.enregistrement import Passage, commencer_passage, consigner, terminer_passage
from tests.base_test import parametres_base_test

scenarios("enregistrement.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
SOURCES_LECTURE = Path(__file__).resolve().parents[1] / "src" / "machincast" / "lecture"


@dataclass
class Contexte:
	ids: dict[str, int] = field(default_factory=dict)
	passage: Passage | None = None


@pytest.fixture
def contexte() -> Contexte:
	return Contexte()


@pytest.fixture
def lecture(base_vide: Connexion) -> Iterator[Connexion]:
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		yield connexion


def heure(texte: str) -> datetime:
	return datetime.fromisoformat(texte).astimezone()


def creer(base: Connexion, requete: str, valeurs: tuple[object, ...]) -> int:
	ligne = base.execute(requete + " RETURNING id", valeurs).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


def evenement(base: Connexion, nom: str) -> int:
	return creer(
		base,
		"INSERT INTO evenements (nom_interne, priorite, debut) VALUES (%s, 'emission', %s)",
		(nom, heure("2026-10-15 20:00:00")),
	)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le sonore « {emplacement} », de l'artiste « {artiste} » et du titre « {titre} »"))
def sonore(contexte: Contexte, base_vide: Connexion, emplacement: str, artiste: str, titre: str) -> None:
	contexte.ids["sonore"] = creer(
		base_vide,
		"INSERT INTO sonores (type, emplacement, etat, artiste, titre) VALUES ('fichier', %s, 'actif', %s, %s)",
		(emplacement, artiste, titre),
	)


@given(parsers.parse("la banque « {nom} » qui le contient"))
def banque(contexte: Contexte, base_vide: Connexion, nom: str) -> None:
	contexte.ids[nom] = creer(base_vide, "INSERT INTO banques (nom_interne, mode) VALUES (%s, 'sequentiel')", (nom,))
	base_vide.execute(
		"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, 1)",
		(contexte.ids[nom], contexte.ids["sonore"]),
	)


@given(parsers.parse("l'émission « {nom} », dont il est le 2e élément, via la banque « {banque_nom} »"))
def emission(contexte: Contexte, base_vide: Connexion, nom: str, banque_nom: str) -> None:
	contexte.ids[nom] = evenement(base_vide, nom)
	creer(
		base_vide,
		"INSERT INTO evenements_elements (evenement_id, position, sonore_id) VALUES (%s, 1, %s)",
		(contexte.ids[nom], contexte.ids["sonore"]),
	)
	contexte.ids["element"] = creer(
		base_vide,
		"INSERT INTO evenements_elements (evenement_id, position, banque_id) VALUES (%s, 2, %s)",
		(contexte.ids[nom], contexte.ids[banque_nom]),
	)


@given(parsers.parse("l'émission « {nom} », dont le sonore est le 1er élément, sans banque"))
def emission_directe(contexte: Contexte, base_vide: Connexion, nom: str) -> None:
	contexte.ids[nom] = evenement(base_vide, nom)
	contexte.ids[f"element {nom}"] = creer(
		base_vide,
		"INSERT INTO evenements_elements (evenement_id, position, sonore_id) VALUES (%s, 1, %s)",
		(contexte.ids[nom], contexte.ids["sonore"]),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le binaire lecture commence ce passage à « {instant} »"))
def commencer(contexte: Contexte, lecture: Connexion, instant: str) -> None:
	i = contexte.ids
	contexte.passage = commencer_passage(lecture, i["sonore"], i["Titres"], i["Magazine"], i["element"], heure(instant))


@when(parsers.parse("le binaire lecture commence le passage de l'émission « {nom} » à « {instant} »"))
def commencer_direct(contexte: Contexte, lecture: Connexion, nom: str, instant: str) -> None:
	i = contexte.ids
	contexte.passage = commencer_passage(lecture, i["sonore"], None, i[nom], i[f"element {nom}"], heure(instant))


@when(parsers.parse("le titre du sonore devient « {titre} »"))
def nouveau_titre(contexte: Contexte, base_vide: Connexion, titre: str) -> None:
	base_vide.execute("UPDATE sonores SET titre = %s WHERE id = %s", (titre, contexte.ids["sonore"]))


@when(parsers.re(r"(?:le binaire lecture termine le passage|le termine) à « (?P<instant>[^»]+) », joué en entier"))
def terminer_entier(contexte: Contexte, lecture: Connexion, instant: str) -> None:
	assert contexte.passage is not None
	terminer_passage(lecture, contexte.passage, heure(instant))


@when(parsers.parse("le termine à « {instant} », coupé net"))
def terminer_coupe(contexte: Contexte, lecture: Connexion, instant: str) -> None:
	assert contexte.passage is not None
	terminer_passage(lecture, contexte.passage, heure(instant), coupe=True)


@when(parsers.parse("le termine à « {instant} », sur l'erreur « {erreur} »"))
def terminer_erreur(contexte: Contexte, lecture: Connexion, instant: str, erreur: str) -> None:
	assert contexte.passage is not None
	terminer_passage(lecture, contexte.passage, heure(instant), erreur=erreur)


@when(parsers.parse("le binaire lecture consigne « {niveau} » « {nature} » : « {message} », à « {instant} »"))
def consigne(lecture: Connexion, niveau: str, nature: str, message: str, instant: str) -> None:
	consigner(lecture, niveau, nature, message, heure(instant))


# ─── Alors ─────────────────────────────────────────────────


def airplay(base: Connexion) -> list[tuple[object, ...]]:
	return base.execute(
		"SELECT passage_id, type_ligne::text, horodatage, emplacement, artiste, titre, sonore_id, banque_id,"
		" evenement_id, element_id, duree_diffusee, sans_incident FROM airplay ORDER BY id"
	).fetchall()


@then(parsers.parse("l'airplay contient {nombre:d} lignes, de début et de fin, avec le même identifiant de passage"))
def deux_lignes(base_vide: Connexion, nombre: int) -> None:
	lignes = airplay(base_vide)
	assert [ligne[1] for ligne in lignes] == ["debut", "fin"][:nombre]
	assert len({ligne[0] for ligne in lignes}) == 1


@then(parsers.parse("la ligne de début est datée de « {debut} », celle de fin de « {fin} »"))
def dates(base_vide: Connexion, debut: str, fin: str) -> None:
	assert [ligne[2] for ligne in airplay(base_vide)] == [heure(debut), heure(fin)]


@then(
	parsers.parse(
		"chaque ligne d'airplay recopie l'emplacement « {emplacement} », l'artiste « {artiste} »"
		" et le titre « {titre} »"
	)
)
def recopie(base_vide: Connexion, emplacement: str, artiste: str, titre: str) -> None:
	lignes = airplay(base_vide)
	assert (lignes) and (all(ligne[3:6] == (emplacement, artiste, titre) for ligne in lignes)), lignes


@then(
	parsers.parse(
		"chaque ligne d'airplay référence le sonore, la banque « {banque_nom} », l'émission « {nom} » et son 2e élément"
	)
)
def references(contexte: Contexte, base_vide: Connexion, banque_nom: str, nom: str) -> None:
	i = contexte.ids
	attendu = (i["sonore"], i[banque_nom], i[nom], i["element"])
	assert all(ligne[6:10] == attendu for ligne in airplay(base_vide))


@then("la ligne de début ne référence aucune banque")
def sans_banque(base_vide: Connexion) -> None:
	assert airplay(base_vide)[0][7] is None


@then(parsers.re(r"la ligne de fin indique (?P<secondes>\d+) secondes diffusées, (?P<issue>sans|avec) incident"))
def ligne_de_fin(base_vide: Connexion, secondes: str, issue: str) -> None:
	fin = airplay(base_vide)[-1]
	assert fin[1] == "fin"
	assert fin[10] == timedelta(seconds=int(secondes))
	assert fin[11] is (issue == "sans")


def log(base: Connexion) -> list[tuple[object, ...]]:
	return base.execute(
		"SELECT niveau::text, nature, message, horodatage, sonore_id, banque_id, evenement_id FROM log ORDER BY id"
	).fetchall()


@then("le log ne contient rien")
def log_vide(base_vide: Connexion) -> None:
	assert log(base_vide) == []


@then(parsers.parse("le log contient une ligne « {niveau} » « {nature} » pour ce sonore, la banque et l'émission"))
def ligne_de_log(contexte: Contexte, base_vide: Connexion, niveau: str, nature: str) -> None:
	i = contexte.ids
	lignes = log(base_vide)
	assert [(n, t, s, b, e) for n, t, _, _, s, b, e in lignes] == [
		(niveau, nature, i["sonore"], i["Titres"], i["Magazine"])
	], lignes


@then(parsers.parse("cette ligne du log mentionne « {texte} »"))
def mention(base_vide: Connexion, texte: str) -> None:
	assert texte in str(log(base_vide)[-1][2])


@then(
	parsers.parse(
		"le log contient une ligne « {niveau} » « {nature} » datée de « {instant} », qui mentionne « {message} »"
	)
)
def ligne_datee(base_vide: Connexion, niveau: str, nature: str, instant: str, message: str) -> None:
	lignes = log(base_vide)
	assert len(lignes) == 1, lignes
	n, t, m, h, *_ = lignes[0]
	assert (n, t, h) == (niveau, nature, heure(instant))
	assert message in str(m)


@then("aucun module du binaire lecture n'écrit dans le log autrement que par machincast.lecture.enregistrement")
def un_seul_journal() -> None:
	fautes = [
		chemin.name
		for chemin in sorted(SOURCES_LECTURE.glob("*.py"))
		if (chemin.name != "enregistrement.py") and ("INSERT INTO log" in chemin.read_text(encoding="utf-8"))
	]
	assert not fautes, fautes
