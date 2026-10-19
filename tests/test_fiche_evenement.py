"""Scénarios de la fiche d'un événement (https://github.com/dascritch/machincast/issues/32).

Les étapes de la fenêtre, des listes, des fiches et des fenêtres de dialogue sont dans tests/etapes_interface.py ;
celles-ci manipulent la fiche de l'événement, et lisent la base de test.
"""

import re
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import QAbstractButton, QComboBox, QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface.fiche_evenement import FicheEvenement
from tests.etapes_interface import NOM, Connexion, Contexte, fenetre, glisser, ouvrir_dans

scenarios("fiche_evenement.feature")

DATE = "dd/MM/yyyy HH:mm"
EN_BASE = re.compile(r"(le sonore|la banque|la séquence|le fichier) « ([^»]+) »")


def fiche(interface: Contexte) -> FicheEvenement:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, FicheEvenement), ouverte
	return ouverte


def lignes(interface: Contexte) -> list[QTreeWidgetItem]:
	return fiche(interface).elements.lignes()


def choisir(interface: Contexte, nom: str) -> None:
	"""Rend courante la seule ligne de l'élément."""
	trouvees = [ligne for ligne in lignes(interface) if ligne.text(1) == nom]
	assert len(trouvees) == 1, f"« {nom} » : {len(trouvees)} lignes"
	fiche(interface).ui.elements.setCurrentItem(trouvees[0])


def choisir_texte(choix: QComboBox, texte: str) -> None:
	indice = choix.findText(texte, Qt.MatchFlag.MatchFixedString)
	assert indice >= 0, f"« {texte} » absent : {[choix.itemText(i) for i in range(choix.count())]}"
	choix.setCurrentIndex(indice)


def si_coche(case: QAbstractButton, lire: Callable[[], str]) -> Callable[[], str]:
	"""Ce que montre un champ qui ne compte que si sa case est cochée : rien sinon."""

	def lecture() -> str:
		if not case.isChecked():
			return ""
		return lire()

	return lecture


def montre(evenement: FicheEvenement) -> dict[str, Callable[[], str]]:
	"""Ce que la fiche montre, par nom de champ à l'écran."""
	ui = evenement.ui
	return {
		"Nom interne": ui.nom_interne.text,
		"Nom public": ui.nom_public.text,
		"Priorité": lambda: ui.priorite.currentText().casefold(),
		"Artiste et titre": lambda: ui.masquage.currentText().casefold(),
		"Début": si_coche(ui.a_debut, ui.debut.text),
		"Fin": si_coche(ui.a_fin, ui.fin.text),
		"Jours": lambda: ", ".join(jour.text() for jour in evenement.jours if jour.isChecked()),
	}


def cases(evenement: FicheEvenement) -> dict[str, QAbstractButton]:
	ui = evenement.ui
	return {"Début": ui.a_debut, "Fin": ui.a_fin} | {jour.text(): jour for jour in evenement.jours}


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("« {nom} » qui vient de passer dans l'événement « {evenement} »"))
def passage(base_vide: Connexion, nom: str, evenement: str) -> None:
	"""Le début d'un passage dans l'historique de diffusion, joué par la ligne de la banque ou du sonore dans la liste
	de l'événement."""
	base_vide.execute(
		"INSERT INTO airplay (passage_id, type_ligne, evenement_id, element_id, banque_id)"
		" SELECT gen_random_uuid(), 'debut', ev.id, e.id, e.banque_id FROM evenements_elements e"
		" JOIN evenements ev ON ev.id = e.evenement_id LEFT JOIN banques b ON b.id = e.banque_id"
		" LEFT JOIN sonores s ON s.id = e.sonore_id WHERE ev.nom_interne = %s AND %s IN (b.nom_interne, s.titre)",
		(evenement, nom),
	)


# ─── Quand ─────────────────────────────────────────────────


@when("je saisis dans la fiche de l'événement :")
def saisir(interface: Contexte, datatable: list[list[str]]) -> None:
	"""Une date vide décoche sa case ; les jours se donnent tous, ceux qui manquent sont décochés."""
	evenement = fiche(interface)
	ui = evenement.ui
	_entetes, *rangees = datatable
	for champ, brut in ((champ.strip(), brut.strip()) for champ, brut in rangees):
		if champ in ("Priorité", "Artiste et titre"):
			choisir_texte({"Priorité": ui.priorite, "Artiste et titre": ui.masquage}[champ], brut)
		elif champ in ("Début", "Fin"):
			case, date = {"Début": (ui.a_debut, ui.debut), "Fin": (ui.a_fin, ui.fin)}[champ]
			if brut != "":
				date.setDateTime(QDateTime.fromString(brut, DATE))
			case.setChecked(brut != "")
		else:
			assert champ == "Jours", champ
			coches = {jour.strip() for jour in brut.split(",") if jour.strip()}
			for jour in evenement.jours:
				jour.setChecked(jour.text() in coches)


@when(parsers.re(r"je (?P<geste>coche|décoche) « (?P<case>[^»]+) » dans la fiche de l'événement"))
def cocher(interface: Contexte, geste: str, case: str) -> None:
	bouton = cases(fiche(interface))[case]
	assert bouton.isChecked() == (geste == "décoche"), f"« {case} » est déjà dans cet état"
	# Un clic au centre d'une case élargie par sa colonne tombe à côté de son texte : click() la coche comme un clic.
	bouton.click()


@when(parsers.parse("je saisis la fin « {texte} » dans la fiche de l'événement"))
def saisir_fin(interface: Contexte, texte: str) -> None:
	ui = fiche(interface).ui
	ui.fin.setDateTime(QDateTime.fromString(texte, DATE))
	ui.a_fin.setChecked(True)


@when(parsers.parse("je choisis l'élément « {nom} » de l'événement"))
def choisir_element(interface: Contexte, nom: str) -> None:
	choisir(interface, nom)


@when(parsers.parse("je choisis l'élément n° {numero:d} de l'événement"))
def choisir_numero(interface: Contexte, numero: int) -> None:
	fiche(interface).ui.elements.setCurrentItem(lignes(interface)[numero - 1])


@when(parsers.re(r"je retire les éléments (?P<noms>.+)"))
def retirer(interface: Contexte, qtbot: QtBot, noms: str) -> None:
	for nom in NOM.findall(noms):
		choisir(interface, nom)
		qtbot.mouseClick(fiche(interface).ui.retirer_element, Qt.MouseButton.LeftButton)


@when(parsers.re(r"je dépose sur les éléments de l'événement (?P<quoi>.+)"))
def deposer(interface: Contexte, quoi: str) -> None:
	glisser(interface, fiche(interface).ui.elements, quoi, True, False)


@when(parsers.parse("j'ouvre l'élément « {nom} » de l'événement"))
def ouvrir_element(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_dans(qtbot, fiche(interface).ui.elements, nom)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"la priorité se choisit parmi (?P<priorites>.+)"))
def priorites(interface: Contexte, priorites: str) -> None:
	choix = fiche(interface).ui.priorite
	assert [choix.itemText(indice).casefold() for indice in range(choix.count())] == NOM.findall(priorites)


@then("la fiche de l'événement montre :")
def montres(interface: Contexte, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	lecteurs = montre(fiche(interface))
	attendus = [(champ.strip(), valeur.strip()) for champ, valeur in rangees]
	assert [(champ, lecteurs[champ]()) for champ, _valeur in attendus] == attendus


@then("la fiche de l'événement montre les éléments :")
def elements_en_table(interface: Contexte, datatable: list[list[str]]) -> None:
	liste = fiche(interface).ui.elements
	entetes, *rangees = datatable
	titres = [liste.headerItem().text(colonne) for colonne in range(liste.columnCount())]
	assert titres == [entete.strip() for entete in entetes]
	montrees = [[ligne.text(colonne) for colonne in range(liste.columnCount())] for ligne in lignes(interface)]
	assert montrees == [[valeur.strip() for valeur in valeurs] for valeurs in rangees]


@then(parsers.re(r"la fiche de l'événement montre les éléments (?P<noms>aucun|«.+)"))
def elements_montres(interface: Contexte, noms: str) -> None:
	assert [ligne.text(1) for ligne in lignes(interface)] == NOM.findall(noms)


@then(parsers.re(r"la fiche de l'événement (?:n')?avertit (?:de rien|« (?P<texte>.+) »)"))
def avertit(interface: Contexte, texte: str | None) -> None:
	assert fiche(interface).ui.avertissement.text() == ((texte) or (""))


@then(parsers.re(r"la grille de la fiche de l'événement se saisit par (?P<quoi>.+)"))
def grille(interface: Contexte, quoi: str) -> None:
	"""Les cases de dates actives, et « les jours » quand tous les jours se cochent ; « rien » sinon."""
	evenement = fiche(interface)
	ui = evenement.ui
	actives = [case.text().replace("&", "") for case in (ui.a_debut, ui.a_fin) if case.isEnabled()]
	if all(jour.isEnabled() for jour in evenement.jours):
		actives.append("les jours")
	else:
		assert not any(jour.isEnabled() for jour in evenement.jours)
	attendues = NOM.findall(quoi)
	if quoi.endswith("les jours"):
		attendues.append("les jours")
	assert actives == attendues
	assert (ui.debut.isEnabled(), ui.fin.isEnabled()) == (ui.a_debut.isChecked(), ui.a_fin.isChecked())


@then(parsers.parse("l'événement « {nom} » a en base :"))
def evenement_en_base(base_vide: Connexion, nom: str, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	attendus = [(champ.strip(), valeur.strip()) for champ, valeur in rangees]
	lus = []
	for champ, _valeur in attendus:
		colonne = {"priorite": "priorite::text", "jours_recurrence": "jours_recurrence::text[]"}.get(champ, champ)
		ligne = base_vide.execute(
			f"SELECT {colonne} FROM evenements WHERE nom_interne = %s",  # noqa: S608
			(nom,),
		).fetchone()
		assert ligne is not None, f"« {nom} » absent de la base"
		valeur = ligne[0]
		if isinstance(valeur, datetime):
			valeur = valeur.astimezone()
		lus.append((champ, str(valeur)))
	assert lus == attendus


@then(parsers.re(r"les éléments de l'événement « (?P<nom>[^»]+) » sont, dans l'ordre, (?P<elements>.+)"))
def elements_en_base(interface: Contexte, base_vide: Connexion, nom: str, elements: str) -> None:
	"""Un sonore par son titre, une banque ou une séquence par son nom, un sonore sans titre par son fichier."""
	lignes_en_base = base_vide.execute(
		"SELECT e.position, CASE WHEN e.banque_id IS NOT NULL THEN 'la banque'"
		" WHEN e.sequence_id IS NOT NULL THEN 'la séquence' WHEN s.titre IS NOT NULL THEN 'le sonore'"
		" ELSE 'le fichier' END, COALESCE(b.nom_interne, q.nom_interne, s.titre, s.emplacement)"
		" FROM evenements_elements e JOIN evenements ev ON ev.id = e.evenement_id"
		" LEFT JOIN banques b ON b.id = e.banque_id LEFT JOIN sequences q ON q.id = e.sequence_id"
		" LEFT JOIN sonores s ON s.id = e.sonore_id WHERE ev.nom_interne = %s ORDER BY e.position",
		(nom,),
	).fetchall()
	attendus = [(genre, interface.chemin(element)) for genre, element in EN_BASE.findall(elements)]
	assert lignes_en_base == [(position, *attendu) for position, attendu in enumerate(attendus, start=1)]


@then(
	parsers.re(
		r"l'historique de diffusion désigne, dans l'événement « (?P<nom>[^»]+) », la ligne n° (?P<numero>\d+)"
		r" et aucune ligne"
	)
)
def historique(base_vide: Connexion, nom: str, numero: str) -> None:
	"""Les passages, dans leur ordre : la position de la ligne qui les a joués, aucune pour une ligne retirée."""
	positions = base_vide.execute(
		"SELECT e.position FROM airplay a JOIN evenements ev ON ev.id = a.evenement_id"
		" LEFT JOIN evenements_elements e ON e.id = a.element_id WHERE ev.nom_interne = %s ORDER BY a.id",
		(nom,),
	).fetchall()
	assert positions == [(int(numero),), (None,)]
