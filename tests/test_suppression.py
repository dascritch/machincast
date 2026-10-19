"""Scénarios de la suppression d'un élément depuis sa fiche (https://github.com/dascritch/machincast/issues/33).

Les étapes de la fenêtre, des listes, des fiches et des fenêtres de dialogue sont dans tests/etapes_interface.py ;
celles-ci suppriment, et lisent la base de test et le répertoire du scénario.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from tests.etapes_interface import NOM, Connexion, Contexte, fiche_ouverte, identifiant

scenarios("suppression.feature")

TABLES = {
	"le sonore": ("sonores", "titre"),
	"la banque": ("banques", "nom_interne"),
	"la séquence": ("sequences", "nom_interne"),
	"l'événement": ("evenements", "nom_interne"),
}
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


def bouton_supprimer(interface: Contexte) -> QPushButton:
	(bouton,) = [
		bouton for bouton in fiche_ouverte(interface).findChildren(QPushButton) if bouton.text() == "Supprimer…"
	]
	return bouton


def questions_de_suppression(interface: Contexte) -> list[str]:
	return [question for question in interface.questions if question.startswith("suppression : ")]


def lignes_attendues(interface: Contexte, datatable: list[list[str]]) -> str:
	_entete, *lignes = datatable
	return "\n".join(ligne[0].strip().replace("…/", f"{interface.repertoire}/") for ligne in lignes)


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


@when(parsers.re(r"je supprime l'élément de la fiche, en répondant « (?P<reponse>Supprimer|Annuler) »"))
def supprimer(interface: Contexte, qtbot: QtBot, reponse: str) -> None:
	interface.suppression = reponse == "Supprimer"
	qtbot.mouseClick(bouton_supprimer(interface), Qt.MouseButton.LeftButton)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("la question de suppression, intitulée « {titre} », a dit :"))
def question(interface: Contexte, titre: str, datatable: list[list[str]]) -> None:
	assert questions_de_suppression(interface) == [f"suppression : {titre}\n{lignes_attendues(interface, datatable)}"]


@then("la dernière question de suppression a dit :")
def derniere_question(interface: Contexte, datatable: list[list[str]]) -> None:
	_titre, texte = questions_de_suppression(interface)[-1].split("\n", 1)
	assert texte == lignes_attendues(interface, datatable)


@then("la fiche signale une suppression impossible")
def suppression_impossible(interface: Contexte) -> None:
	assert fiche_ouverte(interface).message.text().startswith("Suppression impossible : ")


@then("seule la question de suppression a été posée")
def seule_question(interface: Contexte) -> None:
	assert len(interface.questions) == 1, interface.questions
	assert interface.questions == questions_de_suppression(interface)


@then(
	parsers.re(
		r"(?P<genre>le sonore|la banque|la séquence|l'événement) « (?P<nom>[^»]+) »"
		r" (?P<etat>n'est plus|est toujours) en base"
	)
)
def en_base(base_vide: Connexion, genre: str, nom: str, etat: str) -> None:
	table, colonne = TABLES[genre]
	lignes = base_vide.execute(f"SELECT id FROM {table} WHERE {colonne} = %s", (nom,)).fetchall()  # noqa: S608
	assert len(lignes) == {"n'est plus": 0, "est toujours": 1}[etat], lignes


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
