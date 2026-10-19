"""Étapes du choix d'un sonore dans une banque (https://github.com/dascritch/machincast/issues/13)."""

import random
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.hasard import creer_hasard
from machincast.horloge import HorlogeFixe
from machincast.lecture.banques import choisir_sonore, restants
from tests.base_test import parametres_base_test

scenarios("choix_sonore.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ELEMENT = re.compile(r"« ([^»]+) »")
MODES = {"séquentielle": "sequentiel", "aléatoire": "aleatoire"}


@dataclass
class Contexte:
	horloge: HorlogeFixe | None = None
	hasard: random.Random = field(default_factory=lambda: creer_hasard(0))
	joues: list[str] = field(default_factory=list)


@pytest.fixture
def contexte() -> Contexte:
	return Contexte()


def noms(liste: str) -> list[str]:
	return ELEMENT.findall(liste)


def heure(texte: str) -> datetime:
	return datetime.fromisoformat(texte).astimezone()


def sonore(base: Connexion, nom: str) -> int:
	ligne = base.execute("SELECT id FROM sonores WHERE emplacement = %s", (f"/sons/{nom}.flac",)).fetchone()
	if ligne is None:
		ligne = base.execute(
			"INSERT INTO sonores (type, emplacement, etat) VALUES ('fichier', %s, 'actif') RETURNING id",
			(f"/sons/{nom}.flac",),
		).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


def nom_du_sonore(base: Connexion, identifiant: int) -> str:
	ligne = base.execute("SELECT emplacement FROM sonores WHERE id = %s", (identifiant,)).fetchone()
	assert ligne is not None
	return str(ligne[0]).removeprefix("/sons/").removesuffix(".flac")


def banque(base: Connexion, nom: str) -> int:
	ligne = base.execute("SELECT id FROM banques WHERE nom_interne = %s", (nom,)).fetchone()
	assert ligne is not None, f"banque {nom} inconnue"
	return int(str(ligne[0]))


def ajouter(base: Connexion, nom_banque: str, nom_sonore: str) -> None:
	base.execute(
		"INSERT INTO banques_sonores (banque_id, sonore_id, position)"
		" SELECT %s, %s, COALESCE(MAX(position), 0) + 1 FROM banques_sonores WHERE banque_id = %s",
		(banque(base, nom_banque), sonore(base, nom_sonore), banque(base, nom_banque)),
	)


def passage(base: Connexion, nom_sonore: str, nom_banque: str | None) -> None:
	"""Ligne de début d'un passage dans l'airplay : ce qui compte pour le choix."""
	fournie_par = None
	if nom_banque is not None:
		fournie_par = banque(base, nom_banque)
	base.execute(
		"INSERT INTO airplay (passage_id, type_ligne, sonore_id, banque_id) VALUES (%s, 'debut', %s, %s)",
		(uuid.uuid4(), sonore(base, nom_sonore), fournie_par),
	)


def choisir(contexte: Contexte, nom_banque: str) -> int | None:
	assert contexte.horloge is not None
	socket, base_test = parametres_base_test()
	with connecter(socket, base_test, Role.LECTURE) as connexion:
		identifiant = banque_lecture(connexion, nom_banque)
		return choisir_sonore(connexion, identifiant, contexte.horloge.maintenant(), contexte.hasard)


def banque_lecture(connexion: psycopg.Connection[tuple[object, ...]], nom: str) -> int:
	ligne = connexion.execute("SELECT id FROM banques WHERE nom_interne = %s", (nom,)).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


def jouer(contexte: Contexte, base: Connexion, nombre: int, nom_banque: str) -> list[str]:
	joues = []
	for _ in range(nombre):
		choisi = choisir(contexte, nom_banque)
		assert choisi is not None, f"la banque {nom_banque} n'a rien fourni"
		nom = nom_du_sonore(base, choisi)
		passage(base, nom, nom_banque)
		joues.append(nom)
	return joues


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'heure « {texte} »"))
def horloge(contexte: Contexte, texte: str) -> None:
	contexte.horloge = HorlogeFixe(heure(texte))


@given(parsers.re(r"une banque (?P<mode>séquentielle|aléatoire) « (?P<nom>[^»]+) » contenant (?P<liste>.+)"))
def banque_contenant(base_vide: Connexion, mode: str, nom: str, liste: str) -> None:
	base_vide.execute("INSERT INTO banques (nom_interne, mode) VALUES (%s, %s)", (nom, MODES[mode]))
	for nom_sonore in noms(liste):
		ajouter(base_vide, nom, nom_sonore)


@given(parsers.parse("le sonore « {nom_sonore} » ajouté à la banque « {nom_banque} »"))
def ajoute(base_vide: Connexion, nom_sonore: str, nom_banque: str) -> None:
	ajouter(base_vide, nom_banque, nom_sonore)


@given(parsers.parse("« {nom_sonore} » a été joué via la banque « {nom_banque} »"))
def joue_via(base_vide: Connexion, nom_sonore: str, nom_banque: str) -> None:
	passage(base_vide, nom_sonore, nom_banque)


@given(parsers.parse("« {nom_sonore} » a été joué sans banque"))
def joue_sans_banque(base_vide: Connexion, nom_sonore: str) -> None:
	passage(base_vide, nom_sonore, None)


@given(parsers.parse("le hasard créé avec la graine {graine:d}"))
def hasard(contexte: Contexte, graine: int) -> None:
	contexte.hasard = creer_hasard(graine)


@given(parsers.parse("le sonore « {nom} » est à l'état « {etat} »"))
def etat(base_vide: Connexion, nom: str, etat: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = %s WHERE id = %s", (etat, sonore(base_vide, nom)))


@given(parsers.parse("le sonore « {nom} » n'est diffusable qu'à partir du « {debut} »"))
def diffusable_a_partir(base_vide: Connexion, nom: str, debut: str) -> None:
	base_vide.execute("UPDATE sonores SET debut_diffusion = %s WHERE id = %s", (heure(debut), sonore(base_vide, nom)))


@given(parsers.parse("le sonore « {nom} » n'est plus diffusable depuis le « {fin} »"))
def plus_diffusable(base_vide: Connexion, nom: str, fin: str) -> None:
	base_vide.execute("UPDATE sonores SET fin_diffusion = %s WHERE id = %s", (heure(fin), sonore(base_vide, nom)))


@given(parsers.parse("le sonore « {nom} » est diffusable du « {debut} » au « {fin} »"))
def diffusable(base_vide: Connexion, nom: str, debut: str, fin: str) -> None:
	base_vide.execute(
		"UPDATE sonores SET debut_diffusion = %s, fin_diffusion = %s WHERE id = %s",
		(heure(debut), heure(fin), sonore(base_vide, nom)),
	)


@given(parsers.parse("le sonore « {nom} » a atteint son maximum de {maximum:d} lectures"))
def maximum_atteint(base_vide: Connexion, nom: str, maximum: int) -> None:
	lectures(base_vide, nom, maximum, maximum)


@given(parsers.parse("le sonore « {nom} » a été lu {nombre:d} fois sur un maximum de {maximum:d} lectures"))
def lectures(base_vide: Connexion, nom: str, nombre: int, maximum: int) -> None:
	base_vide.execute("UPDATE sonores SET max_lectures = %s WHERE id = %s", (maximum, sonore(base_vide, nom)))
	for _ in range(nombre):
		passage(base_vide, nom, None)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je joue (?P<nombre>\d+) sonores? de la banque « (?P<nom>[^»]+) »"))
def jouer_sonores(contexte: Contexte, base_vide: Connexion, nombre: str, nom: str) -> None:
	contexte.joues = jouer(contexte, base_vide, int(nombre), nom)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("les sonores joués sont {liste}"))
def sonores_joues(contexte: Contexte, liste: str) -> None:
	assert contexte.joues == noms(liste)


@then(parsers.parse("chaque tranche de {taille:d} sonores joués contient {liste}, une fois chacun"))
def tranches(contexte: Contexte, taille: int, liste: str) -> None:
	attendus = sorted(noms(liste))
	for debut in range(0, len(contexte.joues), taille):
		assert sorted(contexte.joues[debut : debut + taille]) == attendus, contexte.joues


def suite(contexte: Contexte, base: Connexion, graine: int, nombre: int, nom_banque: str) -> list[str]:
	base.execute("DELETE FROM airplay")
	contexte.hasard = creer_hasard(graine)
	return jouer(contexte, base, nombre, nom_banque)


@then(parsers.parse("deux tirages de {nombre:d} sonores avec la graine {graine:d} donnent la même suite"))
def meme_suite(contexte: Contexte, base_vide: Connexion, nombre: int, graine: int) -> None:
	premiere = suite(contexte, base_vide, graine, nombre, "Titres")
	assert suite(contexte, base_vide, graine, nombre, "Titres") == premiere


@then(
	parsers.parse(
		"des tirages de {nombre:d} sonores avec les graines {premiere:d} à {derniere:d}"
		" ne donnent pas tous la même suite"
	)
)
def suites_differentes(contexte: Contexte, base_vide: Connexion, nombre: int, premiere: int, derniere: int) -> None:
	suites = {tuple(suite(contexte, base_vide, g, nombre, "Titres")) for g in range(premiere, derniere + 1)}
	assert len(suites) > 1


@then(parsers.parse("les sonores qui restent à jouer dans le cycle de « {nom} » sont {liste}"))
def cycle_restant(contexte: Contexte, base_vide: Connexion, nom: str, liste: str) -> None:
	assert contexte.horloge is not None
	socket, base_test = parametres_base_test()
	with connecter(socket, base_test, Role.LECTURE) as connexion:
		reste = restants(connexion, banque_lecture(connexion, nom), contexte.horloge.maintenant())
	assert sorted(nom_du_sonore(base_vide, s) for s in reste) == sorted(noms(liste))


@then(parsers.parse("la banque « {nom} » ne fournit aucun sonore"))
def aucun(contexte: Contexte, nom: str) -> None:
	assert choisir(contexte, nom) is None
