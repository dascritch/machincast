"""Étapes partagées de la fenêtre de pré-écoute (https://github.com/dascritch/machincast/issues/116).

Chargé comme greffon pytest par tests/conftest.py : la pré-écoute d'un sonore (test_preecoute.py) et l'écoute de
l'antenne depuis le VU-mètre (test_vumetre.py, https://github.com/dascritch/machincast/issues/24) s'en servent.
"""

from PySide6.QtCore import Qt
from pytest_bdd import parsers, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.preecoute import FenetrePreecoute
from tests.etapes_interface import Contexte, fenetre

DELAI = 5000
"""Millisecondes laissées à GStreamer pour ce qui arrive « bientôt »."""


def fenetre_de_preecoute(interface: Contexte) -> FenetrePreecoute:
	ouverte = fenetre(interface).preecoute
	assert ouverte is not None, "aucune fenêtre de pré-écoute"
	return ouverte


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


@then(parsers.parse("la pré-écoute signale bientôt « {debut} »"))
def signale_bientot(interface: Contexte, qtbot: QtBot, debut: str) -> None:
	message = fenetre_de_preecoute(interface).ui.message
	qtbot.waitUntil(lambda: message.text().startswith(debut), timeout=DELAI)


@then(parsers.parse("la pré-écoute signale « {texte} »"))
def signale(interface: Contexte, texte: str) -> None:
	attendu = texte.replace("…/", f"{interface.repertoire}/")
	assert fenetre_de_preecoute(interface).ui.message.text() == attendu
