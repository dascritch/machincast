"""Scénarios de la pré-écoute d'un sonore (https://github.com/dascritch/machincast/issues/116,
https://github.com/dascritch/machincast/issues/29).

Les étapes de la fenêtre et des fiches sont dans tests/etapes_interface.py, celles du serveur de flux local dans
tests/etapes_diffusion.py. La pré-écoute joue sur la sortie factice des tests, en temps réel : ses positions et son
VU-mètre avancent comme sur un vrai périphérique. Les périphériques du poste sont remplacés par ceux du scénario.
"""

import shutil
import tomllib
from datetime import timedelta
from pathlib import Path

import psycopg
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QApplication
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.preecoute import FenetrePreecoute
from tests.etapes_interface import NOM, Contexte, fenetre, fichier_de_configuration
from tests.sons import FICHIERS_SONORES

scenarios("preecoute.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
DELAI = 5000
"""Millisecondes laissées à GStreamer pour ce qui arrive « bientôt »."""


def fenetre_de_preecoute(interface: Contexte) -> FenetrePreecoute:
	ouverte = fenetre(interface).preecoute
	assert ouverte is not None, "aucune fenêtre de pré-écoute"
	return ouverte


# ─── Étant donné ───────────────────────────────────────────


def inserer(base: Connexion, interface: Contexte, titre: str, artiste: str | None, fichier: str) -> None:
	copie = interface.repertoire / fichier
	shutil.copyfile(FICHIERS_SONORES / fichier, copie)
	base.execute(
		"INSERT INTO sonores (type, emplacement, artiste, titre, etat, duree)"
		" VALUES ('fichier', %s, %s, %s, 'actif', %s)",
		(str(copie), artiste, titre, timedelta(seconds=1)),
	)


@given(parsers.parse("le sonore « {titre} » de « {artiste} », pour une copie du fichier de test « {fichier} »"))
def sonore_avec_artiste(interface: Contexte, base_vide: Connexion, titre: str, artiste: str, fichier: str) -> None:
	inserer(base_vide, interface, titre, artiste, fichier)


@given(parsers.re(r"le sonore « (?P<titre>[^»]+) », pour une copie du fichier de test « (?P<fichier>[^»]+) »"))
def sonore(interface: Contexte, base_vide: Connexion, titre: str, fichier: str) -> None:
	inserer(base_vide, interface, titre, None, fichier)


@given(parsers.parse("le fichier du sonore « {titre} » supprimé"))
def fichier_supprime(base_vide: Connexion, titre: str) -> None:
	ligne = base_vide.execute("SELECT emplacement FROM sonores WHERE titre = %s", (titre,)).fetchone()
	assert ligne is not None
	# Une copie de test, dans le répertoire temporaire du scénario.
	Path(str(ligne[0])).unlink()


@given(parsers.parse("le périphérique de l'antenne « {identifiant} »"))
def antenne(interface: Contexte, identifiant: str) -> None:
	interface.audio["peripherique"] = identifiant


# ─── Quand ─────────────────────────────────────────────────


@when("je lance la pré-écoute")
def lancer(interface: Contexte, qtbot: QtBot) -> None:
	bouton = fenetre_de_preecoute(interface).ui.lecture
	assert (bouton.text(), bouton.toolTip()) == ("⏵", "Lecture")
	qtbot.mouseClick(bouton, Qt.MouseButton.LeftButton)


@when("je mets la pré-écoute en pause")
def pause(interface: Contexte, qtbot: QtBot) -> None:
	bouton = fenetre_de_preecoute(interface).ui.lecture
	qtbot.waitUntil(lambda: (bouton.text(), bouton.toolTip()) == ("⏸", "Pause"), timeout=DELAI)
	qtbot.mouseClick(bouton, Qt.MouseButton.LeftButton)


@when("j'arrête la pré-écoute")
def arreter(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fenetre_de_preecoute(interface).ui.arret, Qt.MouseButton.LeftButton)


@when(parsers.parse("je place la position de la pré-écoute à {pourcentage:d} %"))
def placer(interface: Contexte, pourcentage: int) -> None:
	barre = fenetre_de_preecoute(interface).ui.position
	# Comme à la souris : la barre est tenue, déplacée, puis relâchée.
	barre.setSliderDown(True)
	barre.setValue(round(barre.maximum() * pourcentage / 100))
	barre.sliderReleased.emit()
	barre.setSliderDown(False)


@when("je ferme la fenêtre de pré-écoute")
def fermer(interface: Contexte) -> None:
	fenetre_de_preecoute(interface).close()


@when(parsers.parse("je choisis la sortie « {nom} » pour la pré-écoute"))
def choisir_la_sortie(interface: Contexte, nom: str) -> None:
	choix = fenetre_de_preecoute(interface).ui.sortie
	indice = choix.findText(nom)
	assert indice >= 0, nom
	choix.setCurrentIndex(indice)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("la fenêtre de pré-écoute est ouverte, titrée « {titre} »"))
def ouverte(interface: Contexte, titre: str) -> None:
	ouverte = fenetre_de_preecoute(interface)
	assert ouverte.isVisible()
	assert ouverte.windowTitle() == titre
	assert ouverte.isWindow()


@then(parsers.parse("il n'y a qu'une fenêtre de pré-écoute, titrée « {titre} »"))
def une_seule(interface: Contexte, titre: str) -> None:
	ouvertes = [w for w in QApplication.topLevelWidgets() if (isinstance(w, FenetrePreecoute)) and (w.isVisible())]
	assert len(ouvertes) == 1
	assert ouvertes[0].windowTitle() == titre


@then(parsers.parse("la pré-écoute montre la source « {source} »"))
def source(interface: Contexte, source: str) -> None:
	assert fenetre_de_preecoute(interface).ui.source.text() == interface.chemin(source)


@when(parsers.re(r"la pré-écoute est (?P<bientot>bientôt )?« (?P<etat>[^»]+) »(?:, à « (?P<temps>[^»]+) »)?"))
@then(parsers.re(r"la pré-écoute est (?P<bientot>bientôt )?« (?P<etat>[^»]+) »(?:, à « (?P<temps>[^»]+) »)?"))
def etat(interface: Contexte, qtbot: QtBot, bientot: str | None, etat: str, temps: str | None) -> None:
	ui = fenetre_de_preecoute(interface).ui

	def atteint() -> bool:
		return (ui.etat.text() == etat) and ((temps is None) or (ui.temps.text() == temps))

	if bientot is not None:
		qtbot.waitUntil(atteint, timeout=DELAI)
	assert atteint(), (ui.etat.text(), ui.temps.text(), ui.message.text())


@then(parsers.parse("la sortie de la pré-écoute est « {identifiant} »"))
def sortie(interface: Contexte, identifiant: str) -> None:
	ouverte = fenetre_de_preecoute(interface)
	assert ouverte.ui.sortie.currentData() == identifiant
	assert ouverte.lecteur.peripherique == identifiant


@then(parsers.re(r"les commandes de la pré-écoute sont : (?P<commandes>.+)"))
def commandes(interface: Contexte, commandes: str) -> None:
	ui = fenetre_de_preecoute(interface).ui
	lues = []
	assert (ui.arret.text(), ui.arret.toolTip()) == ("⏹", "Arrêt")
	for nom, bouton in ((ui.lecture.toolTip().lower(), ui.lecture), ("arrêt", ui.arret), ("position", ui.position)):
		etat_du_bouton = "inactif"
		if bouton.isEnabled():
			etat_du_bouton = "actif"
		lues.append(f"{nom} {etat_du_bouton}")
	attendues = [c.replace("active", "actif").replace("inactive", "inactif") for c in commandes.split(", ")]
	assert lues == attendues


@when("le VU-mètre de la pré-écoute montre bientôt du son")
@then("le VU-mètre de la pré-écoute montre bientôt du son")
def du_son(interface: Contexte, qtbot: QtBot) -> None:
	vumetre = fenetre_de_preecoute(interface).vumetre
	qtbot.waitUntil(lambda: any(niveau > vumetre.PLANCHER for niveau in vumetre.niveaux), timeout=DELAI)


@then("le VU-mètre de la pré-écoute est au silence")
def au_silence(interface: Contexte) -> None:
	assert fenetre_de_preecoute(interface).vumetre.niveaux == []


@then("la pré-écoute montre bientôt les informations :")
def informations(interface: Contexte, qtbot: QtBot, datatable: list[list[str]]) -> None:
	ui = fenetre_de_preecoute(interface).ui
	champs = {"Format": ui.format, "Échantillonnage": ui.echantillonnage, "Canaux": ui.canaux}
	attendues = [(nom.strip(), valeur.strip()) for nom, valeur in datatable[1:]]

	def lues() -> list[tuple[str, str]]:
		return [(nom, champs[nom].text()) for nom, _valeur in attendues]

	qtbot.waitUntil(lambda: lues() == attendues, timeout=DELAI)


@then("le débit de la pré-écoute est bientôt donné en kbit/s")
def debit(interface: Contexte, qtbot: QtBot) -> None:
	champ = fenetre_de_preecoute(interface).ui.debit
	qtbot.waitUntil(lambda: champ.text().endswith(" kbit/s"), timeout=DELAI)


@then("la pré-écoute donne bientôt des secondes pré-décodées")
def predecode(interface: Contexte, qtbot: QtBot) -> None:
	champ = fenetre_de_preecoute(interface).ui.predecode
	qtbot.waitUntil(lambda: (champ.text().endswith(" s")) and (champ.text() != "0,0 s"), timeout=DELAI)


@then(parsers.parse("la position de la pré-écoute est bientôt entre {minimum} et {maximum} seconde"))
def position(interface: Contexte, qtbot: QtBot, minimum: str, maximum: str) -> None:
	lecteur = fenetre_de_preecoute(interface).lecteur
	bas, haut = float(minimum.replace(",", ".")), float(maximum.replace(",", "."))
	qtbot.waitUntil(lambda: bas <= ((lecteur.position()) or (0.0)) <= haut, timeout=DELAI)


@then("la pré-écoute ne joue plus rien")
def plus_rien(interface: Contexte) -> None:
	assert not fenetre_de_preecoute(interface).lecteur.actif()


@then(parsers.parse("la pré-écoute signale bientôt « {debut} »"))
def signale_bientot(interface: Contexte, qtbot: QtBot, debut: str) -> None:
	message = fenetre_de_preecoute(interface).ui.message
	qtbot.waitUntil(lambda: message.text().startswith(debut), timeout=DELAI)


@then(parsers.parse("la pré-écoute signale « {texte} »"))
def signale(interface: Contexte, texte: str) -> None:
	attendu = texte.replace("…/", f"{interface.repertoire}/")
	assert fenetre_de_preecoute(interface).ui.message.text() == attendu


@then(parsers.re(r"la pré-écoute propose les sorties (?P<noms>«.+)"))
def sorties_proposees(interface: Contexte, noms: str) -> None:
	choix = fenetre_de_preecoute(interface).ui.sortie
	assert [choix.itemText(indice) for indice in range(choix.count())] == NOM.findall(noms)


@then(parsers.parse("le fichier de configuration a pour pré-écoute « {identifiant} », avec ses commentaires"))
def configuration_ecrite(interface: Contexte, identifiant: str) -> None:
	chemin = fichier_de_configuration(interface)
	texte = chemin.read_text(encoding="utf-8")
	assert tomllib.loads(texte)["audio"]["preecoute"] == identifiant
	initiale = interface.configuration_initiale.decode("utf-8")
	commentaires = [ligne for ligne in initiale.splitlines() if ligne.startswith("#")]
	assert commentaires == [ligne for ligne in texte.splitlines() if ligne.startswith("#")]


@then("le bouton « Pré-écoute… » de la fiche est inactif")
def bouton_inactif(interface: Contexte) -> None:
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert not fiche.ui.preecouter.isEnabled()


@when(parsers.parse("je force la sortie « {nom} » pour la pré-écoute"))
def forcer_la_sortie(interface: Contexte, nom: str) -> None:
	"""Une ligne grisée ne se choisit pas à la souris : le programme la choisit, comme le ferait au pire le clavier."""
	choix = fenetre_de_preecoute(interface).ui.sortie
	indice = choix.findText(nom)
	assert indice >= 0, nom
	choix.setCurrentIndex(indice)


@then("la pré-écoute propose les sorties :")
def sorties_et_etats(interface: Contexte, datatable: list[list[str]]) -> None:
	choix = fenetre_de_preecoute(interface).ui.sortie
	modele = choix.model()
	assert isinstance(modele, QStandardItemModel)
	lues = []
	for indice in range(choix.count()):
		etat_de_la_ligne = "inactive"
		if modele.item(indice).isEnabled():
			etat_de_la_ligne = "active"
		lues.append([choix.itemText(indice), etat_de_la_ligne])
	assert lues == [[cellule.strip() for cellule in rangee] for rangee in datatable[1:]]


@then(parsers.parse("le fichier de configuration a toujours pour pré-écoute « {identifiant} »"))
def configuration_intacte(interface: Contexte, identifiant: str) -> None:
	chemin = fichier_de_configuration(interface)
	assert tomllib.loads(chemin.read_text(encoding="utf-8"))["audio"]["preecoute"] == identifiant
	assert chemin.read_bytes() == interface.configuration_initiale
