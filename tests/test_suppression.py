"""Scénarios de la suppression d'un élément depuis sa fiche (https://github.com/dascritch/machincast/issues/33).

Les étapes de la fenêtre, des listes, des fiches et des fenêtres de dialogue sont dans tests/etapes_interface.py ;
celles-ci suppriment, et lisent la base de test et le répertoire du scénario.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QPushButton
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import recherche
from machincast.interface.choix import Choix
from machincast.interface.listes import SONORES
from tests.etapes_interface import (
	NOM,
	Connexion,
	Contexte,
	fiche_ouverte,
	identifiant,
	lignes,
	questions_de_suppression,
)

scenarios("suppression.feature")

NOMS = "COALESCE(s.titre, b.nom_interne, q.nom_interne)"
LISTES = {
	"la banque": (
		"banques",
		f"SELECT {NOMS} FROM banques_sonores e JOIN sonores s ON s.id = e.sonore_id"
		" LEFT JOIN banques b ON false LEFT JOIN sequences q ON false WHERE e.banque_id = %s ORDER BY e.position",
	),
	"la séquence": (
		"sequences",
		f"SELECT {NOMS} FROM sequences_elements e LEFT JOIN sonores s ON s.id = e.sonore_id"
		" LEFT JOIN banques b ON b.id = e.banque_id LEFT JOIN sequences q ON false"
		" WHERE e.sequence_id = %s ORDER BY e.position",
	),
	"l'événement": (
		"evenements",
		f"SELECT {NOMS} FROM evenements_elements e LEFT JOIN sonores s ON s.id = e.sonore_id"
		" LEFT JOIN banques b ON b.id = e.banque_id LEFT JOIN sequences q ON q.id = e.sequence_id"
		" WHERE e.evenement_id = %s ORDER BY e.position",
	),
}
"""La table de la banque, de la séquence ou de l'événement, et la requête des noms de ses éléments, dans l'ordre."""


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("« {titre} » qui est passé à l'antenne pendant « {evenement} »"))
def passage(base_vide: Connexion, titre: str, evenement: str) -> None:
	"""Le début d'un passage dans l'historique de diffusion, qui recopie l'emplacement, l'artiste et le titre."""
	base_vide.execute(
		"INSERT INTO airplay (passage_id, type_ligne, sonore_id, evenement_id, emplacement, artiste, titre)"
		" SELECT gen_random_uuid(), 'debut', s.id, %s, s.emplacement, s.artiste, s.titre FROM sonores s"
		" WHERE s.titre = %s",
		(identifiant(base_vide, "evenements", "nom_interne", evenement), titre),
	)


# ─── Quand ─────────────────────────────────────────────────


@then("la fiche signale une suppression impossible")
def suppression_impossible(interface: Contexte) -> None:
	"""En haut de la fiche, comme toute erreur (https://github.com/dascritch/machincast/issues/270)."""
	fiche = fiche_ouverte(interface)
	assert fiche.erreur.isVisibleTo(fiche)
	assert fiche.erreur.text().startswith("Suppression impossible : ")


@then("seule la question de suppression a été posée")
def seule_question(interface: Contexte) -> None:
	assert len(interface.questions) == 1, interface.questions
	assert interface.questions == questions_de_suppression(interface)


@then(
	parsers.re(
		r"la liste en base de (?P<genre>la banque|la séquence|l'événement) « (?P<nom>[^»]+) » est (?P<noms>rien|«.+)"
	)
)
def liste_en_base(base_vide: Connexion, genre: str, nom: str, noms: str) -> None:
	"""Les éléments, dans l'ordre : un sonore par son titre, une banque ou une séquence par son nom."""
	table, requete = LISTES[genre]
	lignes = base_vide.execute(requete, (identifiant(base_vide, table, "nom_interne", nom),)).fetchall()
	assert [str(ligne[0]) for ligne in lignes] == NOM.findall(noms)


@then(parsers.parse("l'historique de diffusion garde le passage de « {sonore} », à l'emplacement « {emplacement} »"))
def passage_garde(interface: Contexte, base_vide: Connexion, sonore: str, emplacement: str) -> None:
	lignes = base_vide.execute("SELECT artiste, titre, emplacement FROM airplay").fetchall()
	artiste, titre = sonore.split(" – ")
	assert lignes == [(artiste, titre, interface.chemin(emplacement))]


@then("les fichiers du scénario sont intacts")
def intacts(interface: Contexte) -> None:
	assert interface.fichiers != []
	assert {fichier: fichier.read_bytes() for fichier in interface.fichiers} == interface.fichiers


@then(parsers.parse("le dossier « {dossier} » est toujours là"))
def dossier_la(interface: Contexte, dossier: str) -> None:
	assert Path(interface.chemin(dossier)).is_dir()


@then(parsers.parse("le stream « {titre} » n'a plus d'événement de secours"))
def sans_secours(base_vide: Connexion, titre: str) -> None:
	lignes = base_vide.execute("SELECT secours_evenement_id FROM sonores WHERE titre = %s", (titre,)).fetchall()
	assert lignes == [(None,)]


# ─── Suppression différée (https://github.com/dascritch/machincast/issues/267) ───


@when(parsers.parse("une autre banque « {nom} » est créée en base"))
def autre_banque(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("INSERT INTO banques (nom_interne, mode) VALUES (%s, 'aleatoire')", (nom,))


@then(parsers.re(r"les champs de la fiche (?P<non>ne )?se modifient(?: pas)?"))
def champs(interface: Contexte, non: str | None) -> None:
	"""Les champs de saisie ; la case et les boutons de la fiche en lecture seule, sauf « Restaurer »."""
	fiche = fiche_ouverte(interface)
	saisies = [champ for champ in fiche.findChildren(QLineEdit) if champ.parent() is not None]
	assert saisies != []
	actifs = [champ.objectName() for champ in saisies if champ.isEnabled()]
	if non is None:
		assert actifs != [], "aucun champ modifiable"
	else:
		assert actifs == [], actifs


@then(parsers.re(r"la fiche propose « (?P<oui>[^»]+) », pas « (?P<non>[^»]+) »"))
def propose(interface: Contexte, oui: str, non: str) -> None:
	textes = {bouton.text(): bouton for bouton in fiche_ouverte(interface).findChildren(QPushButton)}
	assert (oui in textes) and (textes[oui].isEnabled()), list(textes)
	assert non not in textes, list(textes)


@then(parsers.re(r"la liste montre les noms (?P<noms>.+)"))
def noms_affiches(interface: Contexte, noms: str) -> None:
	assert [ligne["Nom"] for ligne in lignes(interface)] == NOM.findall(noms), lignes(interface)


@then(parsers.parse("la recherche de « {texte} » ne trouve rien"))
def recherche_vide(interface: Contexte, texte: str) -> None:
	assert interface.connexion is not None
	trouves, nombre = recherche.chercher(interface.connexion, texte, 50)
	assert (trouves, nombre) == ([], 0), trouves


@then(parsers.parse("le choix des sonores d'une banque ne propose pas « {titre} »"))
def choix_sans(interface: Contexte, qtbot: QtBot, titre: str) -> None:
	assert interface.connexion is not None
	choix = Choix(SONORES, interface.connexion)
	qtbot.addWidget(choix)
	modele = choix.liste.table.model()
	colonne = [modele.headerData(c, Qt.Orientation.Horizontal) for c in range(modele.columnCount())].index("Titre")
	titres = [modele.index(rangee, colonne).data() for rangee in range(modele.rowCount())]
	assert titres != []
	assert titre not in titres, titres
