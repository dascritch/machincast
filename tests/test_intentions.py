"""Scénarios des emoji d'intention des boutons et des menus (https://github.com/dascritch/machincast/issues/294).

Les étapes de la fenêtre et de ses fiches sont dans tests/etapes_interface.py ; les menus contextuels et les questions
sont vérifiés par leurs propres scénarios (selection_multiple, dialogues).
"""

from PySide6.QtWidgets import QPushButton
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import groupes
from machincast.interface.intentions import sans_intention
from tests.etapes_interface import NOM, TABLES, Connexion, Contexte, fenetre, fiche_ouverte, identifiant

scenarios("intentions.feature")

GENRES = {
	"le sonore": "sonore",
	"la banque": "banque",
	"la séquence": "séquence",
	"l'événement": "événement",
	"le feed": "feed",
}
VERBES = ("Ajouter", "Retirer", "Supprimer")


@when(parsers.re(r"j'ouvre la fiche de (?P<genre>.+) « (?P<nom>[^»]+) » par son identifiant"))
def ouvrir_par_identifiant(interface: Contexte, base_vide: Connexion, qtbot: QtBot, genre: str, nom: str) -> None:
	table, colonne = TABLES[genre]
	fenetre(interface)._ouvrir(GENRES[genre], identifiant(base_vide, table, colonne, nom), nom)


@then(parsers.re(r"les boutons de la fiche qui ajoutent, retirent ou suppriment sont (?P<boutons>«.+)"))
def boutons_marques(interface: Contexte, boutons: str) -> None:
	textes = [bouton.text() for bouton in fiche_ouverte(interface).findChildren(QPushButton)]
	assert [texte for texte in textes if sans_intention(texte).startswith(VERBES)] == NOM.findall(boutons)


@then(
	parsers.re(r"l'action groupée « (?P<cle>[^»]+) » s'intitule « (?P<titre>[^»]+) », au bouton « (?P<bouton>[^»]+) »")
)
def action_groupee(cle: str, titre: str, bouton: str) -> None:
	(action,) = [action for action in groupes.SONORES if action.cle == cle]
	assert (action.titre, action.bouton) == (titre, bouton)
