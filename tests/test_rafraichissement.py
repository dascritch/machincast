"""Scénarios du rafraîchissement des onglets de l'interface (https://github.com/dascritch/machincast/issues/148).

Le rafraîchissement à l'ouverture d'un onglet : https://github.com/dascritch/machincast/issues/241. Les étapes de la
fenêtre, de sa barre de menus, des fiches et des fenêtres de dialogue sont dans
tests/etapes_interface.py. Ce qu'un autre poste ou la diffusion change, le scénario l'écrit directement en base.
"""

import uuid
from datetime import datetime, time

from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from tests.etapes_interface import Connexion, Contexte, fenetre, identifiant, ouvrir_dans

scenarios("rafraichissement.feature")

TITRE = 4
"""Colonne du titre, dans la table de l'airplay de l'accueil."""


@when(parsers.parse("un autre poste ajoute la banque « {nom} »"))
def ajouter_banque(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("INSERT INTO banques (nom_interne, mode) VALUES (%s, 'sequentiel')", (nom,))


@when(parsers.parse("un autre poste renomme la banque « {nom} » en « {nouveau} »"))
def renommer_banque(base_vide: Connexion, nom: str, nouveau: str) -> None:
	base_vide.execute("UPDATE banques SET nom_interne = %s WHERE nom_interne = %s", (nouveau, nom))


@when(parsers.parse("un autre poste efface la banque « {nom} »"))
def effacer_banque(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("DELETE FROM banques WHERE nom_interne = %s", (nom,))


@when(parsers.parse("la diffusion note dans l'airplay le passage de « {titre} » à {heure}"))
def noter_passage(interface: Contexte, base_vide: Connexion, titre: str, heure: str) -> None:
	assert interface.horloge is not None
	debut = datetime.combine(interface.horloge.maintenant().date(), time.fromisoformat(heure))
	base_vide.execute(
		"INSERT INTO airplay (passage_id, type_ligne, horodatage, sonore_id, evenement_id, titre)"
		" VALUES (%s, 'debut', %s, %s, %s, %s)",
		(
			uuid.uuid4(),
			debut.astimezone(),
			identifiant(base_vide, "sonores", "titre", titre),
			identifiant(base_vide, "evenements", "nom_interne", "Continue"),
			titre,
		),
	)


@then("l'airplay de l'accueil ne montre rien")
def airplay_vide(interface: Contexte) -> None:
	assert fenetre(interface).accueil.modele_airplay.rowCount() == 0


@then(parsers.parse("l'airplay de l'accueil montre « {titre} »"))
def airplay(interface: Contexte, titre: str) -> None:
	modele = fenetre(interface).accueil.modele_airplay
	assert [modele.item(ligne, TITRE).text() for ligne in range(modele.rowCount())] == [titre]


@when(parsers.parse("je double-clique sur « {titre} » dans l'airplay de l'accueil"))
def ouvrir_depuis_l_airplay(interface: Contexte, qtbot: QtBot, titre: str) -> None:
	ouvrir_dans(qtbot, fenetre(interface).accueil.ui.table_airplay, titre)


@then(parsers.parse("le nom interne de la fiche est « {nom} »"))
def nom_interne(interface: Contexte, nom: str) -> None:
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert fiche.ui.nom_interne.text() == nom  # type: ignore[attr-defined]
