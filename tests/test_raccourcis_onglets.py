"""Scénarios des raccourcis des onglets (https://github.com/dascritch/machincast/issues/192,
https://github.com/dascritch/machincast/issues/318).

Les étapes de la fenêtre et des fiches sont dans tests/etapes_interface.py.
"""

from PySide6.QtCore import Qt
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.listes import Liste
from tests.etapes_interface import NOM, Contexte, fenetre

scenarios("raccourcis_onglets.feature")


def infobulles(interface: Contexte) -> dict[str, str]:
	onglets = fenetre(interface).ui.onglets
	return {onglets.tabText(indice): onglets.tabToolTip(indice) for indice in range(onglets.count())}


@then(parsers.re(r"les onglets ont pour infobulles (?P<textes>«.+)"))
def toutes_les_infobulles(interface: Contexte, textes: str) -> None:
	assert list(infobulles(interface).values()) == NOM.findall(textes)


@then(parsers.parse("l'onglet « {titre} » a pour infobulle « {texte} »"))
def infobulle(interface: Contexte, titre: str, texte: str) -> None:
	assert infobulles(interface)[titre] == texte


@then(parsers.parse("l'onglet « {titre} » n'a pas d'infobulle"))
def sans_infobulle(interface: Contexte, titre: str) -> None:
	assert infobulles(interface)[titre] == ""


# ─── Onglet précédent, suivant, premier et dernier (https://github.com/dascritch/machincast/issues/318) ───


def ecran(interface: Contexte, titre: str) -> Liste:
	onglets = fenetre(interface).ui.onglets
	(trouve,) = [onglets.widget(indice) for indice in range(onglets.count()) if onglets.tabText(indice) == titre]
	assert isinstance(trouve, Liste), trouve
	return trouve


@when(parsers.parse("je donne le focus au tableau de l'onglet « {titre} »"))
def focus_au_tableau(interface: Contexte, qtbot: QtBot, titre: str) -> None:
	table = ecran(interface, titre).ui.table
	table.setFocus()
	qtbot.waitUntil(table.hasFocus)


@when("je clique sur l'horloge de l'accueil")
def cliquer_l_horloge(interface: Contexte, qtbot: QtBot) -> None:
	qtbot.mouseClick(fenetre(interface).accueil.ui.heure, Qt.MouseButton.LeftButton)


@when(parsers.parse("je saisis « {texte} » dans le filtre de l'onglet « {titre} », le curseur à la fin"))
def saisir_le_filtre(interface: Contexte, qtbot: QtBot, texte: str, titre: str) -> None:
	filtre = ecran(interface, titre).ui.filtre
	filtre.setFocus()
	qtbot.waitUntil(filtre.hasFocus)
	filtre.clear()
	qtbot.keyClicks(filtre, texte)
	assert filtre.cursorPosition() == len(texte)
