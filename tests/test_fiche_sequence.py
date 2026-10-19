"""Scénarios de la fiche d'une séquence (https://github.com/dascritch/machincast/issues/112).

Les étapes de la fenêtre, des listes, des fiches et des fenêtres de dialogue sont dans tests/etapes_interface.py ;
celles-ci manipulent la fiche de la séquence, et lisent la base de test.
"""

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.fiche_sequence import FicheSequence
from tests.etapes_interface import NOM, Connexion, Contexte, fenetre, glisser, ouvrir_dans

scenarios("fiche_sequence.feature")

MASQUAGES = {"selon la banque ou le sonore": None, "masqués": True, "affichés": False}
EN_BASE = re.compile(r"(le sonore|la banque|le fichier) « ([^»]+) »")


def fiche(interface: Contexte) -> FicheSequence:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, FicheSequence), ouverte
	return ouverte


def lignes(interface: Contexte) -> list[QTreeWidgetItem]:
	liste = fiche(interface).ui.elements
	trouvees = [liste.topLevelItem(rangee) for rangee in range(liste.topLevelItemCount())]
	return [ligne for ligne in trouvees if ligne is not None]


def choisir(interface: Contexte, nom: str) -> None:
	"""Rend courante la seule ligne de l'élément."""
	trouvees = [ligne for ligne in lignes(interface) if ligne.text(1) == nom]
	assert len(trouvees) == 1, f"« {nom} » : {len(trouvees)} lignes"
	fiche(interface).ui.elements.setCurrentItem(trouvees[0])


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("« {titre} » qui vient de passer dans la séquence « {nom} »"))
def passage(base_vide: Connexion, titre: str, nom: str) -> None:
	"""Le début d'un passage dans l'historique de diffusion, joué par la ligne du sonore dans la séquence."""
	base_vide.execute(
		"INSERT INTO airplay (passage_id, type_ligne, sonore_id, sequence_id, sequence_element_id, emplacement, titre)"
		" SELECT gen_random_uuid(), 'debut', s.id, q.id, e.id, s.emplacement, s.titre FROM sequences_elements e"
		" JOIN sequences q ON q.id = e.sequence_id JOIN sonores s ON s.id = e.sonore_id"
		" WHERE q.nom_interne = %s AND s.titre = %s",
		(nom, titre),
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("je choisis l'élément « {nom} »"))
def choisir_element(interface: Contexte, nom: str) -> None:
	choisir(interface, nom)


@when(parsers.parse("je choisis l'élément n° {numero:d}"))
def choisir_numero(interface: Contexte, numero: int) -> None:
	fiche(interface).ui.elements.setCurrentItem(lignes(interface)[numero - 1])


@when(parsers.parse("je choisis l'élément « {nom} », puis je descends"))
def descendre(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	choisir(interface, nom)
	qtbot.mouseClick(fiche(interface).ui.descendre, Qt.MouseButton.LeftButton)


@when(parsers.re(r"je retire les éléments (?P<noms>.+)"))
def retirer(interface: Contexte, qtbot: QtBot, noms: str) -> None:
	for nom in NOM.findall(noms):
		choisir(interface, nom)
		qtbot.mouseClick(fiche(interface).ui.retirer_element, Qt.MouseButton.LeftButton)


@when(
	parsers.re(
		r"je dépose sur les éléments de la séquence (?P<quoi>.+?)"
		r"(?P<deplacement>, en ne proposant que le déplacement)?"
	)
)
def deposer(interface: Contexte, quoi: str, deplacement: str | None) -> None:
	glisser(interface, fiche(interface).ui.elements, quoi, True, deplacement is not None)


@when(parsers.parse("j'ouvre l'élément « {nom} » de la séquence"))
def ouvrir_element(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_dans(qtbot, fiche(interface).ui.elements, nom)


@when(parsers.parse("j'ouvre l'événement « {nom} » de la séquence"))
def ouvrir_evenement(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_dans(qtbot, fiche(interface).ui.evenements, nom)


# ─── Alors ─────────────────────────────────────────────────


@then(
	parsers.re(
		r"la fiche de la séquence montre le nom interne « (?P<nom>[^»]*) », le nom public « (?P<nom_public>[^»]*) »"
		r" et le masquage « (?P<masquage>[^»]+) »"
	)
)
def champs(interface: Contexte, nom: str, nom_public: str, masquage: str) -> None:
	ui = fiche(interface).ui
	montres = (ui.nom_interne.text(), ui.nom_public.text(), ui.masquage.currentText().casefold())
	assert montres == (nom.strip(), nom_public.strip(), masquage)


@then("la fiche de la séquence montre les éléments :")
def elements_en_table(interface: Contexte, datatable: list[list[str]]) -> None:
	liste = fiche(interface).ui.elements
	entetes, *rangees = datatable
	titres = [liste.headerItem().text(colonne) for colonne in range(liste.columnCount())]
	assert titres == [entete.strip() for entete in entetes]
	montrees = [[ligne.text(colonne) for colonne in range(liste.columnCount())] for ligne in lignes(interface)]
	assert montrees == [[valeur.strip() for valeur in valeurs] for valeurs in rangees]


@then(parsers.re(r"la fiche de la séquence montre les éléments (?P<noms>«.+)"))
def elements_montres(interface: Contexte, noms: str) -> None:
	assert [ligne.text(1) for ligne in lignes(interface)] == NOM.findall(noms)


@then(parsers.re(r"la fiche de la séquence montre les événements (?P<noms>aucun|«.+)"))
def evenements_montres(interface: Contexte, noms: str) -> None:
	liste = fiche(interface).ui.evenements
	assert [liste.item(rangee).text() for rangee in range(liste.count())] == NOM.findall(noms)


@then(parsers.re(r"la fiche de la séquence (?:n')?avertit (?:de rien|« (?P<texte>.+) »)"))
def avertit(interface: Contexte, texte: str | None) -> None:
	assert fiche(interface).ui.avertissement.text() == ((texte) or (""))


@then(parsers.re(r"les boutons de ligne actifs de la séquence sont (?P<boutons>.+)"))
def boutons_de_ligne(interface: Contexte, boutons: str) -> None:
	ui = fiche(interface).ui
	actifs = [bouton.text() for bouton in (ui.retirer_element, ui.monter, ui.descendre) if bouton.isEnabled()]
	assert actifs == NOM.findall(boutons)


@then("les éléments de la séquence se réordonnent par glisser-déposer, sans se déposer les uns dans les autres")
def reordonnable(interface: Contexte) -> None:
	liste = fiche(interface).ui.elements
	assert liste.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
	assert lignes(interface) != []
	assert all(not (ligne.flags() & Qt.ItemFlag.ItemIsDropEnabled) for ligne in lignes(interface))
	assert all(ligne.flags() & Qt.ItemFlag.ItemIsDragEnabled for ligne in lignes(interface))


@then(
	parsers.re(
		r"la séquence « (?P<nom>[^»]+) » est en base : (?:nom public « (?P<nom_public>[^»]+) »|sans nom public),"
		r" masquage « (?P<masquage>[^»]+) »"
	)
)
def sequence_en_base(base_vide: Connexion, nom: str, nom_public: str | None, masquage: str) -> None:
	lignes = base_vide.execute(
		"SELECT nom_public, masquer_metadonnees FROM sequences WHERE nom_interne = %s", (nom,)
	).fetchall()
	assert lignes == [(nom_public, MASQUAGES[masquage])]


@then(
	parsers.re(
		r"l'historique de diffusion désigne, dans la séquence « (?P<nom>[^»]+) », la ligne n° (?P<numero>\d+)"
		r" et aucune ligne"
	)
)
def historique(base_vide: Connexion, nom: str, numero: str) -> None:
	"""Les passages, dans leur ordre : la position de la ligne qui les a joués, aucune pour une ligne retirée."""
	positions = base_vide.execute(
		"SELECT e.position FROM airplay a JOIN sequences q ON q.id = a.sequence_id"
		" LEFT JOIN sequences_elements e ON e.id = a.sequence_element_id WHERE q.nom_interne = %s ORDER BY a.id",
		(nom,),
	).fetchall()
	assert positions == [(int(numero),), (None,)]


@then(parsers.re(r"les éléments de la séquence « (?P<nom>[^»]+) » sont, dans l'ordre, (?P<elements>.+)"))
def elements_en_base(interface: Contexte, base_vide: Connexion, nom: str, elements: str) -> None:
	"""Un sonore par son titre, une banque par son nom, un sonore sans titre par son fichier."""
	lignes = base_vide.execute(
		"SELECT e.position, CASE WHEN e.banque_id IS NOT NULL THEN 'la banque' WHEN s.titre IS NOT NULL"
		" THEN 'le sonore' ELSE 'le fichier' END, COALESCE(b.nom_interne, s.titre, s.emplacement)"
		" FROM sequences_elements e JOIN sequences q ON q.id = e.sequence_id"
		" LEFT JOIN banques b ON b.id = e.banque_id LEFT JOIN sonores s ON s.id = e.sonore_id"
		" WHERE q.nom_interne = %s ORDER BY e.position",
		(nom,),
	).fetchall()
	attendus = [(genre, interface.chemin(element)) for genre, element in EN_BASE.findall(elements)]
	assert lignes == [(position, *attendu) for position, attendu in enumerate(attendus, start=1)]
