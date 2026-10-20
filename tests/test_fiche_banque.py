"""Scénarios de la fiche d'une banque (https://github.com/dascritch/machincast/issues/31).

Les étapes de la fenêtre, des listes et des fenêtres de dialogue sont dans tests/etapes_interface.py ; celles-ci
manipulent la fiche, le choix des sonores, et lisent la base de test.
"""

from collections.abc import Iterator
from datetime import timedelta

import pytest
from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QDialog, QDoubleSpinBox, QTreeWidgetItem, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.base import Role, connecter
from machincast.interface.choix import Choix
from machincast.interface.fiche_banque import SONORE, FicheBanque
from machincast.interface.listes import SONORES
from tests.base_test import parametres_base_test
from tests.etapes_interface import (
	NOM,
	Connexion,
	Contexte,
	fenetre,
	glisser,
	identifiant,
	ouvrir_dans,
	taper,
)

scenarios("fiche_banque.feature")

MASQUAGES = {"hérité du sonore": None, "masqués": True, "affichés": False}
MODES = {"séquentielle": "sequentiel", "aléatoire": "aleatoire"}


@pytest.fixture
def choix() -> Iterator[list[Choix]]:
	"""Le choix des sonores ouvert par le scénario, hors de la fenêtre."""
	ouverts: list[Choix] = []
	yield ouverts
	for ouvert in ouverts:
		ouvert.liste.connexion.close()


def fiche(interface: Contexte) -> FicheBanque:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, FicheBanque), ouverte
	return ouverte


def sonore(interface: Contexte, base: Connexion, titre: str) -> QTreeWidgetItem:
	"""La ligne du sonore dans la liste de la fiche, sélectionnée."""
	numero = identifiant(base, "sonores", "titre", titre)
	liste = fiche(interface).ui.sonores
	for rangee in range(liste.topLevelItemCount()):
		ligne = liste.topLevelItem(rangee)
		if ligne.data(0, SONORE) == numero:
			liste.setCurrentItem(ligne)
			return ligne
	raise AssertionError(f"« {titre} » absent de la fiche")


def cliquer(qtbot: QtBot, bouton: QWidget) -> None:
	qtbot.mouseClick(bouton, Qt.MouseButton.LeftButton)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.re(r"les sonores sans titre (?P<emplacements>.+) sont dans la banque « (?P<nom>[^»]+) »"))
def sans_titre(base_vide: Connexion, emplacements: str, nom: str) -> None:
	"""Rangés en fin de liste, par leur emplacement : chemin du fichier ou adresse du stream."""
	banque = identifiant(base_vide, "banques", "nom_interne", nom)
	for emplacement in NOM.findall(emplacements):
		base_vide.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position)"
			" SELECT %s, s.id, (SELECT COALESCE(MAX(position), 0) + 1 FROM banques_sonores WHERE banque_id = %s)"
			" FROM sonores s WHERE %s IN (s.emplacement, s.url_stream)",
			(banque, banque, emplacement),
		)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je (?P<action>coche|décoche) « ne pas répéter »"))
def cocher(interface: Contexte, action: str) -> None:
	fiche(interface).ui.ne_pas_repeter.setChecked(action == "coche")


@when(parsers.parse("j'ajoute le répertoire « {repertoire} »"))
def ajouter_repertoire(interface: Contexte, qtbot: QtBot, repertoire: str) -> None:
	interface.repertoires_choisis.append(repertoire)
	cliquer(qtbot, fiche(interface).ui.ajouter_repertoire)


@when("je renonce à choisir un répertoire")
def renoncer(interface: Contexte, qtbot: QtBot) -> None:
	interface.repertoires_choisis.append(None)
	cliquer(qtbot, fiche(interface).ui.ajouter_repertoire)


@when(parsers.parse("je retire le répertoire « {repertoire} »"))
def retirer_repertoire(interface: Contexte, qtbot: QtBot, repertoire: str) -> None:
	ui = fiche(interface).ui
	trouves = ui.repertoires.findItems(repertoire, Qt.MatchFlag.MatchExactly)
	assert len(trouves) == 1, trouves
	ui.repertoires.setCurrentItem(trouves[0])
	cliquer(qtbot, ui.retirer_repertoire)


@when(parsers.re(r"j'ajoute les sonores (?P<titres>.+), en effaçant « (?P<efface>[^»]+) » de la base pendant le choix"))
def ajouter_sonores_effaces(interface: Contexte, qtbot: QtBot, base_vide: Connexion, titres: str, efface: str) -> None:
	interface.sonores_choisis = [identifiant(base_vide, "sonores", "titre", titre) for titre in NOM.findall(titres)]
	base_vide.execute("DELETE FROM sonores WHERE titre = %s", (efface,))
	cliquer(qtbot, fiche(interface).ui.ajouter_sonores)


@when(parsers.parse("je choisis le sonore « {titre} »"))
def choisir_sonore(interface: Contexte, base_vide: Connexion, titre: str) -> None:
	sonore(interface, base_vide, titre)


@when(parsers.parse("je choisis le répertoire « {repertoire} »"))
def choisir_repertoire(interface: Contexte, repertoire: str) -> None:
	liste = fiche(interface).ui.repertoires
	trouves = liste.findItems(repertoire, Qt.MatchFlag.MatchExactly)
	assert len(trouves) == 1, trouves
	liste.setCurrentItem(trouves[0])


@when(parsers.re(r"je (?P<sens>monte|descends) le sonore « (?P<titre>[^»]+) »"))
def deplacer(interface: Contexte, qtbot: QtBot, base_vide: Connexion, sens: str, titre: str) -> None:
	sonore(interface, base_vide, titre)
	ui = fiche(interface).ui
	cliquer(qtbot, {"monte": ui.monter, "descends": ui.descendre}[sens])


@when(parsers.parse("je retire le sonore « {titre} »"))
def retirer_sonore(interface: Contexte, qtbot: QtBot, base_vide: Connexion, titre: str) -> None:
	sonore(interface, base_vide, titre)
	cliquer(qtbot, fiche(interface).ui.retirer_sonore)


@when(parsers.parse("l'indexation rattache le sonore « {titre} » à la banque « {nom} »"))
def rattacher(base_vide: Connexion, titre: str, nom: str) -> None:
	# La requête de machincast.indexation.repertoires : en fin de liste.
	banque = identifiant(base_vide, "banques", "nom_interne", nom)
	base_vide.execute(
		"INSERT INTO banques_sonores (banque_id, sonore_id, position)"
		" SELECT %s, %s, COALESCE(MAX(position), 0) + 1 FROM banques_sonores WHERE banque_id = %s",
		(banque, identifiant(base_vide, "sonores", "titre", titre), banque),
	)


@when(
	parsers.re(
		r"je (?P<geste>dépose|glisse sans les déposer) sur les (?P<liste>répertoires|sonores) de la fiche"
		r" (?P<quoi>.+?)(?P<deplacement>, en ne proposant que le déplacement)?"
	)
)
def deposer(interface: Contexte, geste: str, liste: str, quoi: str, deplacement: str | None) -> None:
	ui = fiche(interface).ui
	cible = {"répertoires": ui.repertoires, "sonores": ui.sonores}[liste]
	glisser(interface, cible, quoi, geste == "dépose", deplacement is not None)


@when(parsers.parse("j'ouvre le sonore « {nom} » de la banque"))
def ouvrir_sonore(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	ouvrir_dans(qtbot, fiche(interface).ui.sonores, nom)


@when(parsers.parse("je choisis le sonore « {nom} » de la banque, puis j'appuie sur Entrée"))
def ouvrir_sonore_au_clavier(interface: Contexte, qtbot: QtBot, nom: str) -> None:
	sonores = fiche(interface).ui.sonores
	(ligne,) = sonores.findItems(nom, Qt.MatchFlag.MatchExactly, 0)
	sonores.setCurrentItem(ligne)
	sonores.setFocus()
	qtbot.keyClick(sonores, Qt.Key.Key_Return)


@when(parsers.parse("l'indexation enregistre le fichier « {chemin} »"))
def indexer_fichier(interface: Contexte, base_vide: Connexion, chemin: str) -> None:
	base_vide.execute(
		"INSERT INTO sonores (type, emplacement, etat, indexe_le) VALUES ('fichier', %s, 'apercu', clock_timestamp())",
		(interface.chemin(chemin),),
	)


@when("j'ouvre le choix des sonores")
def ouvrir_choix(choix: list[Choix], base_vide: Connexion, qtbot: QtBot) -> None:
	ouvert = Choix(SONORES, connecter(*parametres_base_test(), Role.INTERFACE))
	choix.append(ouvert)
	qtbot.addWidget(ouvert)
	ouvert.show()
	qtbot.waitExposed(ouvert)


@when(parsers.parse("je tape « {texte} » dans le filtre du choix des sonores"))
def filtrer_choix(choix: list[Choix], qtbot: QtBot, texte: str) -> None:
	taper(qtbot, choix[0].liste.filtre, texte)


@when("je sélectionne toutes les lignes du choix des sonores")
def tout_selectionner(choix: list[Choix]) -> None:
	choix[0].liste.table.selectAll()


@when(parsers.re(r"je sélectionne les lignes (?P<titres>.+) du choix des sonores"))
def selectionner(choix: list[Choix], titres: str) -> None:
	table = choix[0].liste.table
	modele = table.model()
	for titre in NOM.findall(titres):
		rangees = [rangee for rangee in range(modele.rowCount()) if modele.index(rangee, 1).data() == titre]
		assert len(rangees) == 1, titre
		table.selectionModel().select(
			modele.index(rangees[0], 0),
			QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
		)


@when(parsers.parse("j'ouvre la ligne « {nom} » du choix des sonores"))
def ouvrir_ligne_choix(choix: list[Choix], qtbot: QtBot, nom: str) -> None:
	ouvrir_dans(qtbot, choix[0].liste.table, nom)


# ─── Alors ─────────────────────────────────────────────────


@then(
	parsers.re(
		r"la fiche montre le nom interne « (?P<nom>[^»]*) », le nom public « (?P<nom_public>[^»]*) »,"
		r" le mode « (?P<mode>[^»]+) », le masquage « (?P<masquage>[^»]+) »"
		r" et « ne pas répéter » (?P<case>coché|décoché)"
	)
)
def champs(interface: Contexte, nom: str, nom_public: str, mode: str, masquage: str, case: str) -> None:
	ui = fiche(interface).ui
	montres = (ui.nom_interne.text(), ui.nom_public.text(), ui.mode.currentText().casefold())
	montres += (ui.masquage.currentText().casefold(), ui.ne_pas_repeter.isChecked())
	assert montres == (nom.strip(), nom_public.strip(), mode, masquage, case == "coché")


@then(parsers.re(r"la fiche montre les répertoires (?P<repertoires>.+)"))
def repertoires_montres(interface: Contexte, repertoires: str) -> None:
	liste = fiche(interface).ui.repertoires
	attendus = [interface.chemin(repertoire) for repertoire in NOM.findall(repertoires)]
	assert [liste.item(rangee).text() for rangee in range(liste.count())] == attendus


@then("la fiche montre les sonores :")
def sonores_en_table(interface: Contexte, datatable: list[list[str]]) -> None:
	liste = fiche(interface).ui.sonores
	entetes, *rangees = datatable
	titres = [liste.headerItem().text(colonne) for colonne in range(liste.columnCount())]
	assert titres == [entete.strip() for entete in entetes]
	montrees = []
	for rangee in range(liste.topLevelItemCount()):
		ligne = liste.topLevelItem(rangee)
		assert ligne is not None
		montrees.append([ligne.text(colonne) for colonne in range(liste.columnCount())])
	assert montrees == [[interface.chemin(valeur.strip()) for valeur in valeurs] for valeurs in rangees]


@then(parsers.re(r"les boutons de ligne actifs de la fiche sont (?P<boutons>.+)"))
def boutons_de_ligne(interface: Contexte, boutons: str) -> None:
	ui = fiche(interface).ui
	actifs = [
		bouton.text()
		for bouton in (ui.retirer_repertoire, ui.retirer_sonore, ui.monter, ui.descendre)
		if bouton.isEnabled()
	]
	assert actifs == NOM.findall(boutons)


@then(parsers.re(r"la fiche montre les sonores (?P<sonores>«.+)"))
def sonores_montres(interface: Contexte, sonores: str) -> None:
	liste = fiche(interface).ui.sonores
	montres = [liste.topLevelItem(rangee).text(0) for rangee in range(liste.topLevelItemCount())]
	assert montres == NOM.findall(sonores)


@then("aucune ligne de sonore de la fiche n'accepte qu'on y dépose une autre")
def aucun_depot(interface: Contexte) -> None:
	liste = fiche(interface).ui.sonores
	lignes = [liste.topLevelItem(rangee) for rangee in range(liste.topLevelItemCount())]
	assert lignes != []
	assert all(not (ligne.flags() & Qt.ItemFlag.ItemIsDropEnabled) for ligne in lignes)
	assert all(ligne.flags() & Qt.ItemFlag.ItemIsDragEnabled for ligne in lignes)


@then(parsers.re(r"les sonores de la fiche (?P<verdict>peuvent|ne peuvent pas) se réordonner"))
def reordonnable(interface: Contexte, verdict: str) -> None:
	ui = fiche(interface).ui
	peuvent = verdict == "peuvent"
	interne = ui.sonores.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
	assert (interne, ui.sonores.dragEnabled(), ui.monter.isEnabled(), ui.descendre.isEnabled()) == (peuvent,) * 4


@then(
	parsers.re(
		r"l'avertissement de réintégration nomme « (?P<sonore>[^»]+) », le répertoire « (?P<repertoire>[^»]+) »"
		r" et la prochaine indexation"
	)
)
def avertissement(interface: Contexte, sonore: str, repertoire: str) -> None:
	assert len(interface.questions) == 1, interface.questions
	question = interface.questions[0]
	assert question.startswith("retrait : "), question
	assert f"« {sonore} »" in question, question
	assert repertoire in question, question
	assert "prochaine indexation" in question, question


@then(
	parsers.re(
		r"la banque « (?P<nom>[^»]+) » est en base : (?:nom public « (?P<nom_public>[^»]+) »|sans nom public),"
		r" (?P<mode>séquentielle|aléatoire), masquage « (?P<masquage>[^»]+) »,"
		r" (?P<repeter>avec|sans) « ne pas répéter »"
	)
)
def banque_en_base(
	base_vide: Connexion, nom: str, nom_public: str | None, mode: str, masquage: str, repeter: str
) -> None:
	lignes = base_vide.execute(
		"SELECT nom_public, mode::text, masquer_metadonnees, ne_pas_repeter FROM banques WHERE nom_interne = %s",
		(nom,),
	).fetchall()
	assert lignes == [(nom_public, MODES[mode], MASQUAGES[masquage], repeter == "avec")]


@then(parsers.re(r"les répertoires de la banque « (?P<nom>[^»]+) » sont (?P<repertoires>.+) en base"))
def repertoires_en_base(interface: Contexte, base_vide: Connexion, nom: str, repertoires: str) -> None:
	lignes = base_vide.execute(
		"SELECT r.repertoire FROM banques_repertoires r JOIN banques b ON b.id = r.banque_id"
		" WHERE b.nom_interne = %s ORDER BY r.repertoire",
		(nom,),
	).fetchall()
	assert [str(ligne[0]) for ligne in lignes] == [
		interface.chemin(repertoire) for repertoire in NOM.findall(repertoires)
	]


@then(parsers.re(r"les sonores de la banque « (?P<nom>[^»]+) » sont, dans l'ordre, (?P<titres>.+)"))
def sonores_en_base(interface: Contexte, base_vide: Connexion, nom: str, titres: str) -> None:
	"""Chaque sonore par son titre, ou « le fichier « …/chemin » » pour un sonore sans titre."""
	lignes = base_vide.execute(
		"SELECT bs.position, COALESCE(s.titre, s.emplacement) FROM banques_sonores bs"
		" JOIN banques b ON b.id = bs.banque_id JOIN sonores s ON s.id = bs.sonore_id"
		" WHERE b.nom_interne = %s ORDER BY bs.position",
		(nom,),
	).fetchall()
	attendus = [interface.chemin(titre) for titre in NOM.findall(titres)]
	assert lignes == list(enumerate(attendus, start=1))


@then(parsers.parse("le sonore « {titre} » est toujours en base"))
def toujours_en_base(base_vide: Connexion, titre: str) -> None:
	identifiant(base_vide, "sonores", "titre", titre)


@then(parsers.re(r"le choix des sonores donne (?P<titres>.+)"))
def choisis(choix: list[Choix], base_vide: Connexion, titres: str) -> None:
	attendus = [identifiant(base_vide, "sonores", "titre", titre) for titre in NOM.findall(titres)]
	assert choix[0].selection() == attendus


@then("les répertoires et les sonores de la fiche acceptent les dépôts")
def acceptent(interface: Contexte) -> None:
	ui = fiche(interface).ui
	listes = (ui.repertoires, ui.repertoires.viewport(), ui.sonores, ui.sonores.viewport())
	assert [liste.acceptDrops() for liste in listes] == [True] * 4


@then(parsers.parse("le fichier « {chemin} » n'est pas en base"))
def fichier_absent(interface: Contexte, base_vide: Connexion, chemin: str) -> None:
	lignes = base_vide.execute("SELECT id FROM sonores WHERE emplacement = %s", (interface.chemin(chemin),)).fetchall()
	assert lignes == []


@then("le choix des sonores est validé")
def valide(choix: list[Choix]) -> None:
	assert choix[0].result() == QDialog.DialogCode.Accepted


# ─── Crossfades (https://github.com/dascritch/machincast/issues/143) ─────


def _crossfade(interface: Contexte, cote: str) -> tuple[QComboBox, QDoubleSpinBox]:
	ui = fiche(interface).ui
	suffixe = {"début": "debut", "fin": "fin"}[cote]
	return getattr(ui, f"regle_crossfade_{suffixe}"), getattr(ui, f"crossfade_{suffixe}")


@when(parsers.re(r"je choisis pour le crossfade de (?P<cote>début|fin) la règle « (?P<regle>[^»]+) »"))
def choisir_regle(interface: Contexte, cote: str, regle: str) -> None:
	liste, _duree = _crossfade(interface, cote)
	rang = liste.findText(regle)
	assert rang >= 0, regle
	liste.setCurrentIndex(rang)


@when(parsers.re(r"je saisis (?P<duree>[\d,]+) seconde de crossfade de (?P<cote>début|fin) dans la fiche"))
def saisir_crossfade(interface: Contexte, duree: str, cote: str) -> None:
	_liste, champ = _crossfade(interface, cote)
	assert champ.isEnabled(), cote
	champ.setValue(float(duree.replace(",", ".")))


@then("la fiche montre les crossfades :")
def crossfades_montres(interface: Contexte, datatable: list[list[str]]) -> None:
	_entetes, *rangees = datatable
	montres = []
	for cote, *_valeurs in rangees:
		liste, champ = _crossfade(interface, cote.strip())
		modifiable = "oui" if champ.isEnabled() else "non"
		montres.append([cote.strip(), liste.currentText(), champ.text(), modifiable])
	assert montres == [[valeur.strip() for valeur in rangee] for rangee in rangees]


@then(parsers.re(r"le crossfade de début se règle parmi (?P<regles>.+)"))
def regles_proposees(interface: Contexte, regles: str) -> None:
	liste, _champ = _crossfade(interface, "début")
	assert [liste.itemText(rang) for rang in range(liste.count())] == NOM.findall(regles)


@then(
	parsers.re(
		r"la banque « (?P<nom>[^»]+) » a en base les crossfades « (?P<regle_debut>[^»]+) » (?P<debut>[\d,]+) secondes?"
		r" au début, et « (?P<regle_fin>[^»]+) » (?P<fin>[\d,]+) secondes? à la fin"
	)
)
def crossfades_en_base(base_vide: Connexion, nom: str, regle_debut: str, debut: str, regle_fin: str, fin: str) -> None:
	lignes = base_vide.execute(
		"SELECT crossfade_debut_regle::text, crossfade_debut, crossfade_fin_regle::text, crossfade_fin"
		" FROM banques WHERE nom_interne = %s",
		(nom,),
	).fetchall()
	secondes = [timedelta(seconds=float(valeur.replace(",", "."))) for valeur in (debut, fin)]
	assert lignes == [(regle_debut, secondes[0], regle_fin, secondes[1])]
