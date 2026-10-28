"""Étapes partagées de la fenêtre de pré-écoute (https://github.com/dascritch/machincast/issues/116).

Chargé comme greffon pytest par tests/conftest.py : la pré-écoute d'un sonore (test_preecoute.py), l'écoute de
l'antenne depuis le VU-mètre (test_vumetre.py, https://github.com/dascritch/machincast/issues/24) et les périphériques
audio qui ne répondent plus (test_peripheriques_bloques.py, https://github.com/dascritch/machincast/issues/259) s'en
servent.
"""

import shutil
from datetime import timedelta

import psycopg
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from pytest_bdd import given, parsers, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import moniteur
from machincast.interface.ecran_par_defaut import EcranParDefaut
from machincast.interface.preecoute import FenetrePreecoute
from tests.etapes_interface import Contexte, fenetre, identifiant
from tests.sons import FICHIERS_SONORES

Connexion = psycopg.Connection[tuple[object, ...]]

DELAI = 5000
"""Millisecondes laissées à GStreamer pour ce qui arrive « bientôt »."""
SIGNAUX = {
	"sinusoïde à -10 dB": "audiotestsrc is-live=true wave=sine volume=0.316",
	"blanc": "audiotestsrc is-live=true wave=silence",
	"carré à 0 dB": "audiotestsrc is-live=true wave=square volume=1.0",
	"introuvable": "elementintrouvable",
	"bref": "audiotestsrc is-live=true num-buffers=10 wave=sine",
}
"""Les signaux de test du port de monitoring de la sortie factice."""


def fenetre_de_preecoute(interface: Contexte) -> FenetrePreecoute:
	ouverte = fenetre(interface).preecoute
	assert ouverte is not None, "aucune fenêtre de pré-écoute"
	return ouverte


def accueil(interface: Contexte) -> EcranParDefaut:
	return fenetre(interface).accueil


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


# ─── Port de monitoring de l'antenne (https://github.com/dascritch/machincast/issues/24) ───


@given(parsers.parse("le signal de test « {signal} » sur l'antenne factice"))
def signal_de_test(monkeypatch: pytest.MonkeyPatch, signal: str) -> None:
	monkeypatch.setattr(moniteur, "SIGNAL_FACTICE", SIGNAUX[signal])


@given("un nouvel essai du port de monitoring après une demi-seconde")
def reessai_court(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(moniteur, "REESSAI", 500)


@then(parsers.parse("le VU-mètre de l'antenne est bientôt indisponible, avec une erreur qui commence par « {debut} »"))
def indisponible_bientot(interface: Contexte, qtbot: QtBot, debut: str) -> None:
	etiquette = accueil(interface).ui.etat_moniteur
	qtbot.waitUntil(lambda: etiquette.text().startswith(debut), timeout=DELAI)


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


@when("je ferme la fenêtre de pré-écoute")
def fermer(interface: Contexte) -> None:
	fenetre_de_preecoute(interface).close()


@then(parsers.parse("la pré-écoute lit par l'élément GStreamer « {fabrique} »"))
def lecteur_de_la_preecoute(interface: Contexte, fabrique: str) -> None:
	"""https://github.com/dascritch/machincast/issues/284 : playbin3, qui ne se bloque pas au démarrage d'un AIFF."""
	pipeline = fenetre_de_preecoute(interface).lecteur._pipeline
	assert pipeline is not None
	usine = pipeline.get_factory()
	assert (usine is not None) and (usine.get_name() == fabrique)


@then(parsers.parse("la fenêtre de pré-écoute est ouverte, titrée « {titre} »"))
def ouverte(interface: Contexte, titre: str) -> None:
	ouverte = fenetre_de_preecoute(interface)
	assert ouverte.isVisible()
	assert ouverte.windowTitle() == titre
	assert ouverte.isWindow()


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


@then(parsers.re(r"les commandes de la pré-écoute sont : (?P<commandes>.+)"))
def commandes(interface: Contexte, commandes: str) -> None:
	ui = fenetre_de_preecoute(interface).ui
	ouverte = fenetre_de_preecoute(interface)
	lues = []
	assert (ui.arret.text(), ui.arret.toolTip()) == ("⏹", "Arrêt")
	for nom, actif in (
		(ui.lecture.toolTip().lower(), ui.lecture.isEnabled()),
		("arrêt", ui.arret.isEnabled()),
		# La position se règle sur la frise, que seul un fichier a (https://github.com/dascritch/machincast/issues/224).
		("position", (ui.zone_frise.isVisibleTo(ouverte)) and (ouverte.frise.isEnabled())),
	):
		etat_du_bouton = "inactif"
		if actif:
			etat_du_bouton = "actif"
		lues.append(f"{nom} {etat_du_bouton}")
	attendues = [c.replace("active", "actif").replace("inactive", "inactif") for c in commandes.split(", ")]
	assert lues == attendues


@when("le VU-mètre de la pré-écoute montre bientôt du son")
@then("le VU-mètre de la pré-écoute montre bientôt du son")
def du_son(interface: Contexte, qtbot: QtBot) -> None:
	vumetre = fenetre_de_preecoute(interface).vumetre
	qtbot.waitUntil(lambda: any(niveau > vumetre.PLANCHER for niveau in vumetre.niveaux), timeout=DELAI)


@then(parsers.parse("la pré-écoute signale bientôt « {debut} »"))
def signale_bientot(interface: Contexte, qtbot: QtBot, debut: str) -> None:
	message = fenetre_de_preecoute(interface).ui.message
	qtbot.waitUntil(lambda: message.text().startswith(debut), timeout=DELAI)


@then(parsers.parse("la pré-écoute signale « {texte} »"))
def signale(interface: Contexte, texte: str) -> None:
	attendu = texte.replace("…/", f"{interface.repertoire}/")
	assert fenetre_de_preecoute(interface).ui.message.text() == attendu


@then(parsers.parse("la fenêtre de pré-écoute est bientôt titrée « {titre} »"))
def bientot_titree(interface: Contexte, qtbot: QtBot, titre: str) -> None:
	qtbot.waitUntil(lambda: fenetre_de_preecoute(interface).windowTitle() == titre, timeout=DELAI)


@then(parsers.parse("la fenêtre de pré-écoute reste titrée « {titre} »"))
def reste_titree(interface: Contexte, qtbot: QtBot, titre: str) -> None:
	"""Le temps qu'un état publié arrive à l'interface."""
	qtbot.wait(500)
	assert fenetre_de_preecoute(interface).windowTitle() == titre


@when(parsers.parse("je demande la pré-écoute du sonore « {titre} »"))
def demander(interface: Contexte, base_vide: Connexion, titre: str) -> None:
	fenetre(interface)._preecouter(identifiant(base_vide, "sonores", "titre", titre))


@then("la fenêtre n'a pas de bouton « Pré-écoute » sous ses onglets")
def sans_bouton(interface: Contexte) -> None:
	"""https://github.com/dascritch/machincast/issues/245 : l'entrée du menu « Diffusion » remplace le bouton."""
	ouverte = fenetre(interface)
	hors_des_onglets = [
		bouton for bouton in ouverte.findChildren(QPushButton) if not ouverte.ui.onglets.isAncestorOf(bouton)
	]
	assert [bouton.text() for bouton in hors_des_onglets if "Pré-écoute" in bouton.text()] == []
