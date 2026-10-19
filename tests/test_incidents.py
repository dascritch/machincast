"""Scénarios de l'écran des incidents (https://github.com/dascritch/machincast/issues/35).

Les étapes de la fenêtre, des listes et des fiches sont dans tests/etapes_interface.py ; celles-ci écrivent le log de
la base de test, comme Machin lecture, et lisent l'écran.
"""

from datetime import datetime, timedelta

from PySide6.QtCore import QModelIndex, Qt
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.incidents import EcranIncidents
from tests.etapes_interface import NOM, Connexion, Contexte, fenetre, identifiant, taper

scenarios("incidents.feature")


def ecran(interface: Contexte) -> EcranIncidents:
	ouvert = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouvert, EcranIncidents), ouvert
	return ouvert


def lignes(interface: Contexte) -> list[dict[str, str]]:
	modele = ecran(interface).table.model()
	titres = [str(modele.headerData(colonne, Qt.Orientation.Horizontal)) for colonne in range(modele.columnCount())]
	return [
		{titre: str((modele.index(rangee, colonne).data()) or ("")) for colonne, titre in enumerate(titres)}
		for rangee in range(modele.rowCount())
	]


def noter(base: Connexion, horodatage: str, niveau: str, nature: str, message: str, references: dict[str, str]) -> None:
	"""Une entrée du log, comme l'écrit Machin lecture ; chaque référence par le nom de l'élément."""
	ids = {
		"sonore": ("sonores", "titre"),
		"banque": ("banques", "nom_interne"),
		"evenement": ("evenements", "nom_interne"),
	}
	valeurs = {cle: None for cle in ids}
	for cle, (table, colonne) in ids.items():
		if references.get(cle, "") != "":
			valeurs[cle] = identifiant(base, table, colonne, references[cle])
	base.execute(
		"INSERT INTO log (horodatage, niveau, nature, message, sonore_id, banque_id, evenement_id)"
		" VALUES (%s, %s, %s, %s, %s, %s, %s)",
		(
			datetime.fromisoformat(horodatage).astimezone(),
			niveau,
			nature,
			message,
			valeurs["sonore"],
			valeurs["banque"],
			valeurs["evenement"],
		),
	)


# ─── Étant donné ───────────────────────────────────────────


@given("le log :")
def log(base_vide: Connexion, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	for valeurs in rangees:
		ligne = dict(zip((entete.strip() for entete in entetes), (v.strip() for v in valeurs), strict=True))
		noter(base_vide, ligne["horodatage"], ligne["niveau"], ligne["nature"], ligne["message"], ligne)


@given("le log est vide")
def log_vide(base_vide: Connexion) -> None:
	base_vide.execute("DELETE FROM log")


@given(parsers.parse("{nombre:d} alertes « {nature} » dans le log, une par minute depuis « {debut} »"))
def alertes(base_vide: Connexion, nombre: int, nature: str, debut: str) -> None:
	depart = datetime.fromisoformat(debut)
	for rang in range(nombre):
		noter(base_vide, (depart + timedelta(minutes=rang)).isoformat(), "alerte", nature, f"n° {rang}", {})


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("Machin lecture note l'incident « {nature} » à « {horodatage} »"))
def incident(base_vide: Connexion, nature: str, horodatage: str) -> None:
	noter(base_vide, horodatage, "incident", nature, "", {})


@when(parsers.re(r"je (?P<geste>coche|décoche) « Montrer aussi les informations »"))
def informations(interface: Contexte, geste: str) -> None:
	case = ecran(interface).ui.informations
	assert case.isChecked() == (geste == "décoche")
	case.click()


@when(parsers.parse("je tape « {texte} » dans le filtre des incidents"))
def filtrer(interface: Contexte, qtbot: QtBot, texte: str) -> None:
	taper(qtbot, ecran(interface).ui.filtre, texte)


@when(parsers.parse("j'ouvre la cellule « {cellule} » de l'entrée « {nature} »"))
def ouvrir_cellule(interface: Contexte, qtbot: QtBot, cellule: str, nature: str) -> None:
	table = ecran(interface).table
	modele = table.model()
	trouves = [
		modele.index(rangee, colonne)
		for rangee in range(modele.rowCount())
		for colonne in range(modele.columnCount())
		if (modele.index(rangee, 2).data() == nature) and (modele.index(rangee, colonne).data() == cellule)
	]
	assert len(trouves) == 1, trouves
	index: QModelIndex = trouves[0]
	table.scrollTo(index)
	centre = table.visualRect(index).center()
	qtbot.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)
	qtbot.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)


# ─── Alors ─────────────────────────────────────────────────


@then("la liste des incidents montre :")
def montre(interface: Contexte, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	attendues = [
		dict(zip((e.strip() for e in entetes), (v.strip() for v in valeurs), strict=True)) for valeurs in rangees
	]
	assert lignes(interface) == attendues


@then(parsers.re(r"la liste des incidents montre les natures (?P<natures>.+)"))
def natures(interface: Contexte, natures: str) -> None:
	assert [ligne["Nature"] for ligne in lignes(interface)] == NOM.findall(natures)


@then(parsers.parse("la liste des incidents commence par la nature « {nature} »"))
def premiere(interface: Contexte, nature: str) -> None:
	assert lignes(interface)[0]["Nature"] == nature


@then(parsers.parse("le compte des incidents est « {texte} »"))
def compte(interface: Contexte, texte: str) -> None:
	assert ecran(interface).ui.compte.text() == texte
