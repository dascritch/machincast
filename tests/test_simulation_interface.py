"""Scénarios de l'écran de simulation (https://github.com/dascritch/machincast/issues/37).

Machin lecture simule ici sur la base de test, par tests/simulation_de_test.py : la base de production de la
configuration des tests est volontairement inexistante. Les étapes de la fenêtre, des onglets et des éléments en base
sont dans tests/etapes_interface.py.
"""

import os
import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import psycopg
import pytest
from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import dialogues, simulation
from machincast.interface.simulation import COLONNES, EcranSimulation
from tests.etapes_interface import NOM, Contexte, fenetre

scenarios("simulation_interface.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
SIMULATEUR = Path(__file__).parent / "simulation_de_test.py"
COMMANDE_SIMULATION = simulation.commande_simulation
DUREE_MAXIMALE = 60_000
"""Millisecondes qu'une simulation a pour finir."""


@pytest.fixture
def suivi() -> dict[str, object]:
	"""Ce que les étapes notent en passant : le répertoire temporaire de l'onglet, ce que le sélecteur a proposé."""
	return {}


def ecran(interface: Contexte) -> EcranSimulation:
	onglets = fenetre(interface).ui.onglets
	(trouve,) = [
		widget for indice in range(onglets.count()) if isinstance(widget := onglets.widget(indice), EcranSimulation)
	]
	return trouve


def exports(interface: Contexte) -> Path:
	return interface.repertoire / "exports"


def regle(texte: str) -> QDateTime:
	moment = datetime.fromisoformat(texte)
	return QDateTime(QDate(moment.year, moment.month, moment.day), QTime(moment.hour, moment.minute))


def montre(edition: QDateTime) -> str:
	return str(edition.toString("yyyy-MM-dd HH:mm"))


def simulateur(interface: Contexte, *options: str) -> None:
	def commande(configuration: Path | None) -> list[str]:
		assert configuration is not None
		return [sys.executable, str(SIMULATEUR), *options, "--config", str(configuration)]

	interface.monkeypatch.setattr(simulation, "commande_simulation", commande)


# ─── Étant donné ───────────────────────────────────────────


@given("un Machin lecture qui simule sur la base de test")
def sur_la_base_de_test(interface: Contexte) -> None:
	simulateur(interface)


@given("un Machin lecture qui simule sans base joignable")
def sans_base(interface: Contexte) -> None:
	simulateur(interface, "--sans-base")


@given("un Machin lecture qui échoue après avoir simulé")
def qui_echoue(interface: Contexte) -> None:
	simulateur(interface, "--echoue")


@given(parsers.parse("le sonore « {titre} » est à l'état « {etat} » en base"))
@when(parsers.parse("le sonore « {titre} » est à l'état « {etat} » en base"))
def etat_du_sonore(base_vide: Connexion, titre: str, etat: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = %s WHERE titre = %s", (etat, titre))


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je règle la simulation du « {debut} » au « {fin} »"))
def regler(interface: Contexte, debut: str, fin: str) -> None:
	ouvert = ecran(interface)
	ouvert.debut.setDateTime(regle(debut))
	ouvert.fin.setDateTime(regle(fin))


@when("Machin lecture attend avant de simuler")
def attend(interface: Contexte, fin_de_l_attente: Path) -> None:
	simulateur(interface, "--attend", str(fin_de_l_attente))


@pytest.fixture
def fin_de_l_attente(interface: Contexte) -> Iterator[Path]:
	"""Le fichier qui termine l'attente du Machin lecture factice ; il est créé en fin de scénario."""
	fin = interface.repertoire / "fin-de-l-attente"
	yield fin
	fin.touch()


@when("je lance la simulation")
def lancer(interface: Contexte, qtbot: QtBot, suivi: dict[str, object]) -> None:
	ouvert = ecran(interface)
	suivi["temporaire"] = ouvert.temporaire
	ouvert.simuler.click()
	qtbot.waitUntil(lambda: not ouvert.en_cours(), timeout=DUREE_MAXIMALE)


@when("je lance la simulation, sans attendre sa fin")
def lancer_sans_attendre(interface: Contexte, qtbot: QtBot, suivi: dict[str, object]) -> None:
	ouvert = ecran(interface)
	suivi["temporaire"] = ouvert.temporaire
	ouvert.simuler.click()
	processus = ouvert.processus
	assert processus is not None
	qtbot.waitUntil(lambda: processus.processId() > 0, timeout=DUREE_MAXIMALE)
	suivi["pid"] = processus.processId()


@when(parsers.parse("j'exporte la simulation sous « {nom} », avec le filtre « {filtre} »"))
def exporter(interface: Contexte, suivi: dict[str, object], nom: str, filtre: str) -> None:
	exports(interface).mkdir(exist_ok=True)

	def choisir(_parent: QWidget, propose: str, filtres: list[str]) -> tuple[Path, str]:
		assert filtre in filtres
		suivi["propose"] = propose
		return exports(interface) / nom, filtre

	interface.monkeypatch.setattr(dialogues, "choisir_export", choisir)
	ecran(interface).exporter.click()


@when("j'abandonne l'export de la simulation")
def abandonner(interface: Contexte) -> None:
	def choisir(_parent: QWidget, _propose: str, _filtres: list[str]) -> None:
		return None

	interface.monkeypatch.setattr(dialogues, "choisir_export", choisir)
	ecran(interface).exporter.click()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("la simulation est réglée du « {debut} » au « {fin} »"))
def reglee(interface: Contexte, debut: str, fin: str) -> None:
	ouvert = ecran(interface)
	assert (montre(ouvert.debut.dateTime()), montre(ouvert.fin.dateTime())) == (debut, fin)


@then(parsers.parse("le compte de la simulation est « {texte} »"))
def compte(interface: Contexte, texte: str) -> None:
	assert ecran(interface).compte.text() == texte


@then(parsers.parse("le compte de la simulation commence par « {debut} »"))
def compte_commence(interface: Contexte, debut: str) -> None:
	texte = ecran(interface).compte.text()
	assert texte.startswith(debut), texte


@then(parsers.re(r"le bouton « (?P<bouton>Simuler|Exporter…) » de la simulation est (?P<etat>actif|inactif)"))
def bouton(interface: Contexte, bouton: str, etat: str) -> None:
	ouvert = ecran(interface)
	boutons = {"Simuler": ouvert.simuler, "Exporter…": ouvert.exporter}
	assert boutons[bouton].isEnabled() == (etat == "actif")


@then("la simulation montre les passages :")
def passages(interface: Contexte, datatable: list[list[str]]) -> None:
	entetes, *rangees = datatable
	modele = ecran(interface).modele
	assert [str(modele.horizontalHeaderItem(colonne).text()) for colonne in range(modele.columnCount())] == [
		entete.strip() for entete in entetes
	]
	attendues = [[valeur.strip() for valeur in rangee] for rangee in rangees]
	emplacement = COLONNES.index("Emplacement")
	for rangee in attendues:
		rangee[emplacement] = interface.chemin(rangee[emplacement])
	assert ecran(interface).lignes() == attendues


@then("la simulation montre aucun passage")
def aucun_passage(interface: Contexte) -> None:
	assert ecran(interface).lignes() == []


@then(parsers.parse("la simulation montre les titres {titres}"))
def titres(interface: Contexte, titres: str) -> None:
	assert [ligne[3] for ligne in ecran(interface).lignes()] == NOM.findall(titres)


@then("la simulation ne signale rien")
def ne_signale_rien(interface: Contexte) -> None:
	anomalies = ecran(interface).anomalies
	assert (anomalies.count() == 0) and (anomalies.isHidden())


@then(parsers.parse("la simulation signale « {texte} »"))
def signale(interface: Contexte, texte: str) -> None:
	anomalies = ecran(interface).anomalies
	assert not anomalies.isHidden()
	assert [anomalies.item(rangee).text() for rangee in range(anomalies.count())] == [texte]


@then("l'airplay de la base est vide")
def airplay_vide(base_vide: Connexion) -> None:
	ligne = base_vide.execute("SELECT count(*) FROM airplay").fetchone()
	assert ligne == (0,)


@then("aucune simulation n'a été lancée")
def aucune_lancee(interface: Contexte) -> None:
	assert ecran(interface).lancees == 0


@then(parsers.parse("{nombre:d} simulations ont été lancées"))
def lancees(interface: Contexte, nombre: int) -> None:
	assert ecran(interface).lancees == nombre


@then("le Machin lecture de la simulation est arrêté")
def arrete(suivi: dict[str, object]) -> None:
	pid = suivi["pid"]
	assert isinstance(pid, int)
	with pytest.raises(ProcessLookupError):
		os.kill(pid, 0)


@then(parsers.parse("la commande de simulation pour « {chemin} » est Machin lecture --config « {attendu} »"))
def commande(chemin: str, attendu: str) -> None:
	assert COMMANDE_SIMULATION(Path(chemin)) == [sys.executable, "-m", "machincast.lecture", "--config", attendu]
	assert COMMANDE_SIMULATION(None) == [sys.executable, "-m", "machincast.lecture"]


@then(parsers.parse("le sélecteur d'export a proposé « {nom} »"))
def propose(suivi: dict[str, object], nom: str) -> None:
	assert suivi["propose"] == nom


@then(parsers.parse("le fichier « {fichier} » exporté est la sortie {extension} de la simulation"))
def exporte(interface: Contexte, fichier: str, extension: str) -> None:
	(seul,) = list(exports(interface).iterdir())
	assert seul.name == fichier
	assert seul.read_bytes() == (ecran(interface).temporaire / f"simulation{extension}").read_bytes()


@then(parsers.parse("la barre d'état a annoncé l'export de la simulation dans « {fichier} »"))
def annonce_export(interface: Contexte, fichier: str) -> None:
	assert f"Simulation exportée dans {exports(interface) / fichier}." in interface.annonces


@then("aucun fichier n'a été exporté")
def rien_exporte(interface: Contexte) -> None:
	assert (not exports(interface).exists()) or (not list(exports(interface).iterdir()))


@then("le répertoire temporaire de la simulation n'existe plus")
def temporaire_efface(suivi: dict[str, object]) -> None:
	temporaire = suivi["temporaire"]
	assert isinstance(temporaire, Path)
	assert not temporaire.exists()
