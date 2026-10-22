"""Scénarios des fenêtres de dialogue des fiches (https://github.com/dascritch/machincast/issues/31,
https://github.com/dascritch/machincast/issues/112, https://github.com/dascritch/machincast/issues/32).

Les vraies fenêtres s'ouvrent, hors de l'écran du poste : un minuteur y clique une fois la fenêtre modale ouverte. Le
sélecteur de répertoires et le navigateur de fichiers du poste sont remplacés.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialogButtonBox, QFileDialog, QMessageBox, QWidget
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.base import Role, connecter
from machincast.interface import dialogues
from machincast.interface.choix import Choix
from tests.base_test import parametres_base_test
from tests.etapes_interface import NOM, Connexion, identifiant
from tests.modales import quand_modale

scenarios("dialogues.feature")


@dataclass
class Dialogue:
	parent: QWidget
	texte: str = ""
	precision: str = ""
	"""Le texte qui suit celui de la question."""
	titre: str = ""
	actions: list[str] = field(default_factory=list)
	menus: list[object] = field(default_factory=list)
	"""Le menu du clic droit sur la première ligne d'un choix ; None sans menu."""
	boutons: list[str] = field(default_factory=list)
	reponse: object = None
	adresses: list[QUrl] = field(default_factory=list)


@pytest.fixture
def dialogue(qtbot: QtBot) -> Iterator[Dialogue]:
	parent = QWidget()
	qtbot.addWidget(parent)
	yield Dialogue(parent)


def repondre(dialogue: Dialogue, qtbot: QtBot, geste: str) -> None:
	def faire(modale: QWidget) -> None:
		assert isinstance(modale, QMessageBox), modale
		dialogue.texte = modale.text()
		dialogue.precision = modale.informativeText()
		dialogue.boutons = [bouton.text() for bouton in modale.buttons()]
		touches = {"tape Échap": Qt.Key.Key_Escape, "tape Entrée": Qt.Key.Key_Return}
		if geste in touches:
			qtbot.keyClick(modale, touches[geste])
			return
		(nom,) = NOM.findall(geste)
		(bouton,) = [bouton for bouton in modale.buttons() if bouton.text() == nom]
		bouton.click()

	quand_modale(faire)


@when(parsers.parse("la question de fermeture de « {titre} » s'ouvre, et que j'y {geste}"))
def fermeture(dialogue: Dialogue, qtbot: QtBot, titre: str, geste: str) -> None:
	repondre(dialogue, qtbot, geste)
	dialogue.reponse = dialogues.confirmer_fermeture(dialogue.parent, titre)


@when(parsers.parse("la question de rafraîchissement de « {titre} » s'ouvre, et que j'y {geste}"))
def rafraichissement(dialogue: Dialogue, qtbot: QtBot, titre: str, geste: str) -> None:
	repondre(dialogue, qtbot, geste)
	dialogue.reponse = dialogues.confirmer_fermeture(dialogue.parent, titre, "rafraîchir la fiche")


@when(parsers.parse("la question d'arrêt de « {titre} » s'ouvre, et que j'y {geste}"))
def arret(dialogue: Dialogue, qtbot: QtBot, titre: str, geste: str) -> None:
	repondre(dialogue, qtbot, geste)
	dialogue.reponse = dialogues.confirmer_arret_indexation(dialogue.parent, titre)


@when(parsers.parse("l'avertissement de réintégration « {texte} » s'ouvre, et que j'y {geste}"))
def retrait(dialogue: Dialogue, qtbot: QtBot, texte: str, geste: str) -> None:
	repondre(dialogue, qtbot, geste)
	dialogue.reponse = dialogues.confirmer_retrait(dialogue.parent, texte)


@when(parsers.parse("la question de suppression « {titre} » s'ouvre, et que j'y {geste}"))
def suppression(dialogue: Dialogue, qtbot: QtBot, titre: str, geste: str) -> None:
	repondre(dialogue, qtbot, geste)
	dialogue.reponse = dialogues.confirmer_suppression(
		dialogue.parent, titre, "Supprimer de la base le sonore « Spot » ?"
	)


@when(
	parsers.parse("la confirmation de la maintenance, sauvegardes dans « {repertoire} », s'ouvre, et que j'y {geste}")
)
def maintenance(dialogue: Dialogue, qtbot: QtBot, repertoire: str, geste: str) -> None:
	repondre(dialogue, qtbot, geste)
	dialogue.reponse = dialogues.confirmer_maintenance(dialogue.parent, Path(repertoire))


@when(parsers.parse("la confirmation de l'action « {titre} » s'ouvre, et que j'y {geste}"))
def action(dialogue: Dialogue, qtbot: QtBot, titre: str, geste: str) -> None:
	repondre(dialogue, qtbot, geste)
	dialogue.reponse = dialogues.confirmer_action(
		dialogue.parent, titre, "Désactiver 2 sonores ? Un sonore en aperçu reste en aperçu."
	)


@when(parsers.parse("la question après la vérification s'ouvre, et que j'y {geste}"))
def apres_verification(dialogue: Dialogue, qtbot: QtBot, geste: str) -> None:
	repondre(dialogue, qtbot, geste)
	dialogue.reponse = dialogues.proposer_rafraichissement(dialogue.parent, "Vérification terminée : Neige, actif.")


@when(parsers.parse("la question de création s'ouvre, et que j'y {geste}"))
def creation(dialogue: Dialogue, qtbot: QtBot, geste: str) -> None:
	repondre(dialogue, qtbot, geste)
	dialogue.reponse = dialogues.confirmer_creation(
		dialogue.parent, "Créer un événement le dimanche 25 octobre 2026 de 13:00 à 14:00 ?"
	)


@when(parsers.re(r"le sélecteur de répertoires du poste donne « ?(?P<selecteur>[^»]*?) ?»"))
def selecteur(dialogue: Dialogue, monkeypatch: pytest.MonkeyPatch, selecteur: str) -> None:
	def choisir(_parent: QWidget, _titre: str) -> str:
		return selecteur

	monkeypatch.setattr(QFileDialog, "getExistingDirectory", choisir)
	dialogue.reponse = dialogues.choisir_repertoire(dialogue.parent)


@when(
	parsers.re(
		r"le choix des (?P<genre>sonores|banques|séquences|marques-pages) s'ouvre,"
		r" avec la remarque « ?(?P<remarque>[^»]*?) ?»,"
		r" et que j'y sélectionne tout, puis clique sur « (?P<bouton>[^»]+) »"
	)
)
def choix(dialogue: Dialogue, base_vide: Connexion, genre: str, remarque: str, bouton: str) -> None:
	def faire(modale: QWidget) -> None:
		assert isinstance(modale, Choix), modale
		dialogue.titre = modale.windowTitle()
		boutons = (modale.liste.ui.nouveau, modale.liste.ui.ajouter_fichiers)
		dialogue.actions = [bouton.text() for bouton in boutons if not bouton.isHidden()]
		dialogue.actions += ["dépôt"] * modale.liste.table.acceptDrops()
		dialogue.menus = [modale.liste.menu_de_la_ligne(modale.liste.proxy.index(0, 0))]
		dialogue.texte = modale.ui.explication.text()
		modale.liste.table.selectAll()
		# « Annuler » est la traduction de Qt (qtbase_fr), que les tests ne chargent pas : le bouton se trouve par son
		# rôle.
		standards = {"Ajouter": QDialogButtonBox.StandardButton.Ok, "Annuler": QDialogButtonBox.StandardButton.Cancel}
		assert modale.ui.boutons.button(QDialogButtonBox.StandardButton.Ok).text() == "Ajouter"
		modale.ui.boutons.button(standards[bouton]).click()

	quand_modale(faire)
	choisir = {
		"sonores": dialogues.choisir_sonores,
		"banques": dialogues.choisir_banques,
		"séquences": dialogues.choisir_sequences,
		"marques-pages": dialogues.choisir_marques_pages,
	}[genre]
	connexion = connecter(*parametres_base_test(), Role.INTERFACE)
	try:
		dialogue.reponse = choisir(dialogue.parent, connexion, remarque)
	finally:
		connexion.close()


@when(
	parsers.re(
		r"le choix des banques s'ouvre, parmi (?P<noms>«.+), et que j'y sélectionne tout, puis clique sur « Ajouter »"
	)
)
def choix_parmi(dialogue: Dialogue, base_vide: Connexion, noms: str) -> None:
	def faire(modale: QWidget) -> None:
		assert isinstance(modale, Choix), modale
		modale.liste.table.selectAll()
		modale.ui.boutons.button(QDialogButtonBox.StandardButton.Ok).click()

	quand_modale(faire)
	parmi = [
		int(str(ligne[0]))
		for nom in NOM.findall(noms)
		if (ligne := base_vide.execute("SELECT id FROM banques WHERE nom_interne = %s", (nom,)).fetchone())
	]
	connexion = connecter(*parametres_base_test(), Role.INTERFACE)
	try:
		dialogue.reponse = dialogues.choisir_banques(dialogue.parent, connexion, "", parmi)
	finally:
		connexion.close()


@when(parsers.parse("j'ouvre le dossier « {dossier} »"))
def ouvrir_dossier(dialogue: Dialogue, monkeypatch: pytest.MonkeyPatch, dossier: str) -> None:
	def ouvrir(adresse: QUrl) -> bool:
		dialogue.adresses.append(adresse)
		return True

	monkeypatch.setattr(QDesktopServices, "openUrl", ouvrir)
	dialogues.ouvrir_dossier(Path(dossier))


@then(parsers.parse("la question a précisé « {texte} »"))
def precision(dialogue: Dialogue, texte: str) -> None:
	assert dialogue.precision == texte


@then(parsers.parse("la question a dit « {texte} »"))
def question(dialogue: Dialogue, texte: str) -> None:
	assert dialogue.texte == texte


@then(parsers.re(r"la question a proposé (?P<boutons>.+)"))
def proposes(dialogue: Dialogue, boutons: str) -> None:
	assert sorted(dialogue.boutons) == sorted(NOM.findall(boutons))


@then(parsers.parse("la réponse est « {reponse} »"))
def reponse(dialogue: Dialogue, reponse: str) -> None:
	assert str(dialogue.reponse) == reponse


@then(parsers.re(r"le répertoire choisi est (?P<choisi>.+)"))
def repertoire(dialogue: Dialogue, choisi: str) -> None:
	attendu = None
	if choisi != "aucun":
		(attendu,) = NOM.findall(choisi)
	assert dialogue.reponse == attendu


@then(parsers.parse("le choix s'est intitulé « {titre} »"))
def intitule(dialogue: Dialogue, titre: str) -> None:
	assert dialogue.titre == titre


@then("le choix n'a proposé ni création ni ajout de fichiers")
def sans_actions(dialogue: Dialogue) -> None:
	assert dialogue.actions == []


@then(parsers.parse("le choix a expliqué « {texte} »"))
def explique(dialogue: Dialogue, texte: str) -> None:
	assert dialogue.texte == texte


@then(parsers.re(r"les (?P<genre>sonores|banques|séquences|marques-pages) choisi(?:e)?s sont (?P<noms>.+)"))
def choisis(dialogue: Dialogue, base_vide: Connexion, genre: str, noms: str) -> None:
	table, colonne = {
		"sonores": ("sonores", "titre"),
		"banques": ("banques", "nom_interne"),
		"séquences": ("sequences", "nom_interne"),
		"marques-pages": ("marques_pages_streams", "nom"),
	}[genre]
	assert dialogue.reponse == [identifiant(base_vide, table, colonne, nom) for nom in NOM.findall(noms)]


@then(parsers.parse("le poste a ouvert l'adresse « {adresse} »"))
def adresse(dialogue: Dialogue, adresse: str) -> None:
	assert [url.toString() for url in dialogue.adresses] == [adresse]


@then("le choix n'a proposé aucune action au clic droit")
def sans_menu(dialogue: Dialogue) -> None:
	assert dialogue.menus == [None]
