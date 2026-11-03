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
"""Colonne du titre, dans la table de l'airplay de l'onglet Antenne."""


@when(parsers.parse("un autre poste ajoute la banque « {nom} »"))
def ajouter_banque(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential')", (nom,))


@when(parsers.parse("un autre poste renomme la banque « {nom} » en « {nouveau} »"))
def renommer_banque(base_vide: Connexion, nom: str, nouveau: str) -> None:
	base_vide.execute("UPDATE banks SET internal_name = %s WHERE internal_name = %s", (nouveau, nom))


@when(parsers.parse("un autre poste efface la banque « {nom} »"))
def effacer_banque(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("DELETE FROM banks WHERE internal_name = %s", (nom,))


@when(parsers.parse("la diffusion note dans l'airplay le passage de « {titre} » à {heure}"))
def noter_passage(interface: Contexte, base_vide: Connexion, titre: str, heure: str) -> None:
	assert interface.horloge is not None
	debut = datetime.combine(interface.horloge.maintenant().date(), time.fromisoformat(heure))
	base_vide.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, event_id, title)"
		" VALUES (%s, 'start', %s, %s, %s, %s)",
		(
			uuid.uuid4(),
			debut.astimezone(),
			identifiant(base_vide, "sounds", "title", titre),
			identifiant(base_vide, "events", "internal_name", "Continue"),
			titre,
		),
	)


@then("l'airplay de l'onglet Antenne ne montre rien")
def airplay_vide(interface: Contexte) -> None:
	assert fenetre(interface).accueil.modele_airplay.rowCount() == 0


@then(parsers.parse("l'airplay de l'onglet Antenne montre « {titre} »"))
def airplay(interface: Contexte, titre: str) -> None:
	modele = fenetre(interface).accueil.modele_airplay
	assert [modele.item(ligne, TITRE).text() for ligne in range(modele.rowCount())] == [titre]


@when(parsers.parse("je double-clique sur « {titre} » dans l'airplay de l'onglet Antenne"))
def ouvrir_depuis_l_airplay(interface: Contexte, qtbot: QtBot, titre: str) -> None:
	ouvrir_dans(qtbot, fenetre(interface).accueil.ui.table_airplay, titre)


@then(parsers.parse("le nom interne de la fiche est « {nom} »"))
def nom_interne(interface: Contexte, nom: str) -> None:
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert fiche.ui.nom_interne.text() == nom  # type: ignore[attr-defined]
