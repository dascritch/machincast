"""Scénarios de la pré-écoute depuis le menu contextuel d'une ligne (https://github.com/dascritch/machincast/issues/226).

Les étapes de la fenêtre, des fiches et des listes sont dans tests/etapes_interface.py, celles de la pré-écoute dans
tests/etapes_preecoute.py. Le menu d'une ligne se demande à l'écran qui le construit, comme le ferait le clic droit,
sans l'afficher : un menu ouvert attendrait qu'on le ferme.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

import psycopg
import pytest
from PySide6.QtCore import QItemSelectionModel, QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.interface import affichage, icones
from machincast.interface.fiche_banque import FicheBanque
from machincast.interface.fiche_evenement import FicheEvenement
from machincast.interface.fiche_sequence import FicheSequence
from machincast.interface.listes import Liste
from tests.etapes_interface import Contexte, fenetre, glisser, identifiant, liste, meme_icone

scenarios("menu_preecoute.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
PREECOUTE = "Pré-écoute…"


@dataclass
class Menu:
	ouvert: QMenu | None = None
	demande: bool = False
	"""Un menu a été demandé, même s'il n'y en a pas eu."""
	entrees: list[str] = field(default_factory=list)


@pytest.fixture
def menu() -> Menu:
	return Menu()


def _retenir(menu: Menu, ouvert: QMenu | None) -> None:
	menu.demande = True
	menu.ouvert = ouvert
	menu.entrees = []
	if ouvert is not None:
		menu.entrees = [(action.text()) or ("—") for action in ouvert.actions()]


# ─── Étant donné ───────────────────────────────────────────


def _passage(base: Connexion, interface: Contexte, sonore: int | None, titre: str, heure: str) -> None:
	assert interface.horloge is not None
	jour = interface.horloge.maintenant().date()
	debut = datetime.fromisoformat(f"{jour.isoformat()}T{heure}:00").astimezone()
	base.execute(
		"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, titre) VALUES (%s, 'debut', %s, %s, %s)",
		(uuid.uuid4(), debut, sonore, titre),
	)


@given(parsers.re(r"« (?P<titre>[^»]+) » passé à l'antenne à (?P<heure>\d\d:\d\d)$"))
def passe(interface: Contexte, base_vide: Connexion, titre: str, heure: str) -> None:
	_passage(base_vide, interface, identifiant(base_vide, "sonores", "titre", titre), titre, heure)


@given(parsers.parse("« {titre} » passé à l'antenne à {heure}, son sonore supprimé depuis"))
def passe_puis_supprime(interface: Contexte, base_vide: Connexion, titre: str, heure: str) -> None:
	"""L'airplay garde l'artiste et le titre du passage ; son sonore n'est plus désigné."""
	_passage(base_vide, interface, None, titre, heure)


# ─── Quand ─────────────────────────────────────────────────


def _ligne_de_la_liste(ouverte: Liste, titre: str) -> QModelIndex:
	modele = ouverte.table.model()
	for rangee in range(modele.rowCount()):
		for colonne in range(modele.columnCount()):
			if modele.index(rangee, colonne).data() == titre:
				return modele.index(rangee, 0)
	raise AssertionError(f"aucune ligne « {titre} » dans la liste")


def _ligne_de_l_arbre(arbre: QTreeWidget, titre: str) -> QTreeWidgetItem:
	for rangee in range(arbre.topLevelItemCount()):
		ligne = arbre.topLevelItem(rangee)
		if any(titre in ligne.text(colonne) for colonne in range(arbre.columnCount())):
			return ligne
	raise AssertionError(f"aucune ligne « {titre} »")


@when(parsers.parse("je sélectionne les lignes « {premier} » et « {second} » de la liste"))
def selectionner(interface: Contexte, premier: str, second: str) -> None:
	ouverte = liste(interface)
	selection = ouverte.table.selectionModel()
	selection.clearSelection()
	for titre in (premier, second):
		selection.select(
			_ligne_de_la_liste(ouverte, titre),
			QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
		)


@when(parsers.parse("j'ouvre le menu contextuel de la ligne « {titre} » de la liste"))
def menu_de_la_liste(interface: Contexte, menu: Menu, titre: str) -> None:
	ouverte = liste(interface)
	_retenir(menu, ouverte.menu_de_la_ligne(_ligne_de_la_liste(ouverte, titre)))


@when(parsers.parse("j'ouvre le menu contextuel de la ligne « {titre} » de l'airplay"))
def menu_de_l_airplay(interface: Contexte, menu: Menu, titre: str) -> None:
	accueil = fenetre(interface).accueil
	modele = accueil.modele_airplay
	(rangee,) = [
		rangee
		for rangee in range(modele.rowCount())
		if any(modele.index(rangee, colonne).data() == titre for colonne in range(modele.columnCount()))
	]
	_retenir(menu, accueil.menu_de_l_airplay(modele.index(rangee, 0)))


@when(parsers.parse("j'ouvre le menu contextuel de la ligne « {titre} » des éléments"))
def menu_des_elements(interface: Contexte, menu: Menu, titre: str) -> None:
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(fiche, (FicheSequence, FicheEvenement)), fiche
	elements = fiche.elements
	_retenir(menu, elements.menu_de_la_ligne(_ligne_de_l_arbre(elements.liste, titre)))


@when(parsers.parse("je dépose « {fichier} » sur les sonores de la banque"))
def deposer(interface: Contexte, fichier: str) -> None:
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(fiche, FicheBanque), fiche
	glisser(interface, fiche.ui.sonores, f"« {fichier} »", True, False)


@when(parsers.parse("j'ouvre le menu contextuel de la ligne « {titre} » des sonores de la banque"))
def menu_de_la_banque(interface: Contexte, menu: Menu, titre: str) -> None:
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(fiche, FicheBanque), fiche
	_retenir(menu, fiche.menu_des_sonores(_ligne_de_l_arbre(fiche.ui.sonores, titre)))


@when(parsers.parse("je choisis « {entree} » dans le menu contextuel"))
def choisir(menu: Menu, entree: str) -> None:
	assert menu.ouvert is not None, "aucun menu contextuel"
	(action,) = [action for action in menu.ouvert.actions() if action.text() == entree]
	assert isinstance(action, QAction)
	action.trigger()


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"le menu contextuel commence par « (?P<entree>[^»]+) »(?P<separateur>, puis un séparateur)?"))
def commence_par(menu: Menu, entree: str, separateur: str | None) -> None:
	assert menu.entrees[:1] == [entree], menu.entrees
	if entree == affichage.PREECOUTE:
		# Toute entrée « Pré-écoute… » porte le casque (https://github.com/dascritch/machincast/issues/223).
		assert menu.ouvert is not None
		assert meme_icone(menu.ouvert.actions()[0].icon(), icones.icone("pré-écoute"))
	if separateur is not None:
		assert menu.ouvert is not None
		assert menu.ouvert.actions()[1].isSeparator(), menu.entrees


@then(parsers.parse("le menu contextuel propose toujours « {entree} »"))
def propose_toujours(menu: Menu, entree: str) -> None:
	assert entree in menu.entrees, menu.entrees


@then(parsers.parse("le menu contextuel ne propose pas « {entree} »"))
def ne_propose_pas(menu: Menu, entree: str) -> None:
	assert menu.demande
	assert entree not in menu.entrees, menu.entrees


@then("il n'y a pas de menu contextuel")
def sans_menu(menu: Menu) -> None:
	assert menu.demande
	assert menu.ouvert is None, menu.entrees
