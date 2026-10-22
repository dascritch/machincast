"""Scénarios de l'onglet Airplay (https://github.com/dascritch/machincast/issues/244).

Les passages sont écrits dans l'airplay de la base de test (tests/etapes_interface.py). Le sélecteur de fichier de
l'export est remplacé par le choix du scénario ; les exports s'écrivent dans le répertoire temporaire du scénario.
"""

import csv
import re
from pathlib import Path

import psycopg
import pytest
from PySide6.QtWidgets import QWidget
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import dialogues
from machincast.interface.onglet_airplay import EcranAirplay
from tests.etapes_interface import NOM, Contexte, fenetre, ouvrir_dans

scenarios("onglet_airplay.feature")

Connexion = psycopg.Connection[tuple[object, ...]]


@pytest.fixture
def suivi() -> dict[str, str]:
	"""Ce que le scénario note en chemin : le nom proposé pour l'export."""
	return {}


def ecran(interface: Contexte) -> EcranAirplay:
	onglets = fenetre(interface).ui.onglets
	ecrans = [onglets.widget(indice) for indice in range(onglets.count())]
	(trouve,) = [ecran for ecran in ecrans if isinstance(ecran, EcranAirplay)]
	return trouve


def exports(interface: Contexte) -> Path:
	repertoire = interface.repertoire / "exports"
	repertoire.mkdir(exist_ok=True)
	return repertoire


def emplacement(base: Connexion, titre: str) -> str:
	ligne = base.execute("SELECT emplacement FROM sonores WHERE titre = %s", (titre,)).fetchone()
	assert ligne is not None
	return str(ligne[0])


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je règle l'onglet Airplay sur (?P<heures>\d+) heures?"))
def regler(interface: Contexte, heures: str) -> None:
	ecran(interface).heures.setValue(int(heures))


@when(parsers.parse("j'ouvre dans l'onglet Airplay la cellule « {texte} »"))
def ouvrir_cellule(interface: Contexte, qtbot: QtBot, texte: str) -> None:
	ouvrir_dans(qtbot, ecran(interface).table, texte)


@when(parsers.parse("j'exporte l'onglet Airplay sous « {nom} », avec le filtre « {filtre} »"))
def exporter(interface: Contexte, suivi: dict[str, str], nom: str, filtre: str) -> None:
	def choisir(_parent: QWidget, propose: str, filtres: list[str], _titre: str = "") -> tuple[Path, str]:
		assert filtre in filtres, filtres
		suivi["propose"] = propose
		return exports(interface) / nom, filtre

	interface.monkeypatch.setattr(dialogues, "choisir_export", choisir)
	ecran(interface).exporter.click()


@when("j'abandonne l'export de l'onglet Airplay")
def abandonner(interface: Contexte) -> None:
	def choisir(_parent: QWidget, _propose: str, _filtres: list[str], _titre: str = "") -> None:
		return None

	interface.monkeypatch.setattr(dialogues, "choisir_export", choisir)
	ecran(interface).exporter.click()


@when("l'accueil relit son airplay, pour un nouveau sonore")
def accueil_relu(interface: Contexte) -> None:
	fenetre(interface).accueil.actualiser_airplay()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("l'onglet Airplay montre les {heures:d} dernières heures"))
def heures_montrees(interface: Contexte, heures: int) -> None:
	assert ecran(interface).heures.value() == heures


def table(interface: Contexte) -> list[dict[str, str]]:
	ouvert = ecran(interface)
	modele = ouvert.modele
	return [
		{cle: modele.item(rangee, colonne).text() for colonne, (cle, _) in enumerate(ouvert.COLONNES)}
		for rangee in range(modele.rowCount())
	]


@then("la table de l'onglet Airplay montre :")
def table_attendue(interface: Contexte, datatable: list[list[str]]) -> None:
	entetes, *lignes = datatable
	attendues = [dict(zip(entetes, (v.strip() for v in valeurs), strict=True)) for valeurs in lignes]
	assert table(interface) == attendues, table(interface)


@then(parsers.re(r"la table de l'onglet Airplay a (?P<nombre>\d+) lignes?"))
def lignes(interface: Contexte, nombre: str) -> None:
	assert ecran(interface).modele.rowCount() == int(nombre), table(interface)


@then(parsers.parse("le clic droit sur la ligne « {titre} » de l'onglet Airplay propose « {entree} »"))
def menu(interface: Contexte, titre: str, entree: str) -> None:
	ouvert = ecran(interface)
	modele = ouvert.modele
	(rangee,) = [
		rangee
		for rangee in range(modele.rowCount())
		if any(modele.index(rangee, colonne).data() == titre for colonne in range(modele.columnCount()))
	]
	menu_de_la_ligne = ouvert.menu_de_la_ligne(modele.index(rangee, 0))
	assert menu_de_la_ligne is not None
	assert entree in [action.text() for action in menu_de_la_ligne.actions()]
	assert not menu_de_la_ligne.actions()[0].icon().isNull()


@then(parsers.parse("l'export proposait le nom « {nom} »"))
def nom_propose(suivi: dict[str, str], nom: str) -> None:
	assert suivi["propose"] == nom


def lire(interface: Contexte, nom: str) -> str:
	return (exports(interface) / nom).read_text(encoding="utf-8-sig")


@then(parsers.parse("l'export « {nom} » a l'en-tête « {entete} »"))
def entete_du_csv(interface: Contexte, nom: str, entete: str) -> None:
	assert lire(interface, nom).splitlines()[0] == entete


@then(parsers.re(r"l'export « (?P<nom>[^»]+) » a (?P<nombre>\d+) passages(?:, le premier « (?P<premier>.+) »)?$"))
def passages_du_csv(interface: Contexte, nom: str, nombre: str, premier: str | None) -> None:
	_entete, *rangees = list(csv.reader(lire(interface, nom).splitlines(), delimiter=";"))
	assert len(rangees) == int(nombre), rangees
	if premier is None:
		return
	attendu = premier.split(";")
	assert len(rangees[0]) == len(attendu), rangees[0]
	for obtenu, valeur in zip(rangees[0], attendu, strict=True):
		# « … » : une valeur quelconque, non vide.
		assert (obtenu == valeur) or ((valeur == "…") and (obtenu != "")), rangees[0]


@then(parsers.parse("l'export « {nom} » est une page HTML de {nombre:d} passages"))
def page(interface: Contexte, nom: str, nombre: int) -> None:
	texte = lire(interface, nom)
	assert texte.startswith("<!DOCTYPE html>")
	assert len(re.findall(r"<tr class=\"passage\">", texte)) == nombre, texte


@then(parsers.re(r"l'export « (?P<nom>[^»]+) » contient (?P<textes>.+) et l'emplacement de « (?P<titre>[^»]+) »"))
def contenu_de_la_page(interface: Contexte, base_vide: Connexion, nom: str, textes: str, titre: str) -> None:
	texte = lire(interface, nom)
	for attendu in [*NOM.findall(textes), emplacement(base_vide, titre)]:
		assert attendu in texte, attendu


@then(
	parsers.parse(
		"dans l'export « {nom} », la ligne de « {titre} » a l'incident « {incident} », celle du « {autre} » aucun"
	)
)
def incidents_de_la_page(interface: Contexte, nom: str, titre: str, incident: str, autre: str) -> None:
	rangees = re.findall(r'<tr class="passage">(.*?)</tr>', lire(interface, nom))
	cellules = {
		re.findall(r"<td>(.*?)</td>", rangee)[4]: re.findall(r"<td>(.*?)</td>", rangee)[-1] for rangee in rangees
	}
	assert (cellules[titre], cellules[autre]) == (incident, ""), cellules


@then(parsers.parse("l'export « {nom} » commence par « {debut} »"))
def debut_du_m3u(interface: Contexte, nom: str, debut: str) -> None:
	assert lire(interface, nom).startswith(f"{debut}\n")


@then(parsers.re(r"l'export « (?P<nom>[^»]+) » donne, dans l'ordre, les emplacements de (?P<titres>.+)"))
def emplacements_du_m3u(interface: Contexte, base_vide: Connexion, nom: str, titres: str) -> None:
	lues = [ligne for ligne in lire(interface, nom).splitlines() if (ligne) and (not ligne.startswith("#"))]
	assert lues == [emplacement(base_vide, titre) for titre in NOM.findall(titres)]


@then(parsers.re(r"l'export « (?P<nom>[^»]+) » contient « (?P<premier>[^»]+) » et « (?P<second>[^»]+) »$"))
def lignes_du_m3u(interface: Contexte, nom: str, premier: str, second: str) -> None:
	lues = lire(interface, nom).splitlines()
	assert (premier in lues) and (second in lues), lues


@then(parsers.parse("il n'y a pas d'export « {nom} »"))
def pas_d_export(interface: Contexte, nom: str) -> None:
	assert not (exports(interface) / nom).exists()


@then("aucun fichier n'a été exporté")
def aucun_export(interface: Contexte) -> None:
	assert list(exports(interface).iterdir()) == []


@then(parsers.parse("la barre d'état annonce un export, « {debut} » suivi de son chemin"))
def annonce(interface: Contexte, debut: str) -> None:
	assert fenetre(interface).ui.barre_d_etat.currentMessage().startswith(debut)
