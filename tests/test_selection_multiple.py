"""Scénarios de la sélection multiple dans les listes des sonores et des banques
(https://github.com/dascritch/machincast/issues/114).

Les étapes de la fenêtre, des listes et des éléments en base sont dans tests/etapes_interface.py ; les fenêtres de
dialogue y sont remplacées par les réponses du scénario.
"""

import re

import psycopg
from PySide6.QtCore import QItemSelection, QItemSelectionModel, QModelIndex
from PySide6.QtWidgets import QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.interface.fiche_banque import COLONNE_ETAT, FicheBanque
from machincast.interface.listes import Liste
from tests.etapes_interface import NOM, Contexte, fenetre, identifiant, liste

scenarios("selection_multiple.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
MASQUAGES = {"masqués": True, "affichés": False, "hérité": None}
"""Valeurs de banques.masquer_metadonnees, par leur nom dans les scénarios."""


def index_de(ouverte: Liste, nom: str) -> QModelIndex:
	"""La première cellule de la ligne dont une cellule porte ce nom."""
	modele = ouverte.table.model()
	trouvees = [
		modele.index(rangee, 0)
		for rangee in range(modele.rowCount())
		if any(modele.index(rangee, colonne).data() == nom for colonne in range(modele.columnCount()))
	]
	assert len(trouvees) == 1, nom
	return trouvees[0]


def menu(ouverte: Liste, index: QModelIndex) -> list[str]:
	choix = ouverte.menu_de_la_ligne(index)
	assert choix is not None
	# Les séparateurs ne sont pas des entrées.
	return [action.text() for action in choix.actions() if not action.isSeparator()]


def declencher(ouverte: Liste, index: QModelIndex, texte: str) -> None:
	choix = ouverte.menu_de_la_ligne(index)
	assert choix is not None
	(action,) = [action for action in choix.actions() if action.text() == texte]
	action.trigger()


def sonores_par_titre(base: Connexion, titres: str) -> list[int]:
	return [identifiant(base, "sonores", "titre", titre) for titre in NOM.findall(titres)]


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.re(r"les banques choisies (?P<noms>aucune|«.+)"))
def banques_choisies(interface: Contexte, base_vide: Connexion, noms: str) -> None:
	interface.banques_choisies = [identifiant(base_vide, "banques", "nom_interne", nom) for nom in NOM.findall(noms)]


@given("les confirmations d'action refusées")
def confirmations_refusees(interface: Contexte) -> None:
	interface.action = False


@given(
	parsers.re(
		r"le masquage « (?P<premier>[^»]+) » de la banque « (?P<banque>[^»]+) » et « (?P<second>[^»]+) »"
		r" de la banque « (?P<autre>[^»]+) »"
	)
)
def masquages(base_vide: Connexion, premier: str, banque: str, second: str, autre: str) -> None:
	for valeur, nom in ((premier, banque), (second, autre)):
		base_vide.execute(
			"UPDATE banques SET masquer_metadonnees = %s WHERE nom_interne = %s", (MASQUAGES[valeur], nom)
		)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"je sélectionne les lignes (?P<noms>«.+) de la liste"))
def selectionner(interface: Contexte, noms: str) -> None:
	ouverte = liste(interface)
	selection = QItemSelection()
	for nom in NOM.findall(noms):
		index = index_de(ouverte, nom)
		selection.select(index, index)
	ouverte.table.selectionModel().select(
		selection, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows
	)


@when(parsers.parse("je choisis « {texte} » au clic droit sur la sélection"))
def agir_sur_la_selection(interface: Contexte, texte: str) -> None:
	ouverte = liste(interface)
	(premiere, *_autres) = sorted(ouverte.table.selectionModel().selectedRows(), key=lambda index: index.row())
	declencher(ouverte, premiere, texte)


@when(parsers.parse("je choisis « {texte} » au clic droit sur la ligne « {nom} »"))
def agir_sur_la_ligne(interface: Contexte, texte: str, nom: str) -> None:
	ouverte = liste(interface)
	declencher(ouverte, index_de(ouverte, nom), texte)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"le clic droit sur la sélection propose (?P<textes>«.+)"))
def menu_de_la_selection(interface: Contexte, textes: str) -> None:
	ouverte = liste(interface)
	(premiere, *_autres) = sorted(ouverte.table.selectionModel().selectedRows(), key=lambda index: index.row())
	assert menu(ouverte, premiere) == NOM.findall(textes)


@then(parsers.parse("la dernière question, intitulée « {titre} », a dit « {texte} »"))
def derniere_question(interface: Contexte, titre: str, texte: str) -> None:
	assert interface.questions[-1] == f"action : {titre}\n{texte}", interface.questions


@then(parsers.re(r"les sonores (?P<titres>«.+) sont à l'état « (?P<etat>[^»]+) » en base"))
@then(parsers.re(r"le sonore (?P<titres>« [^»]+ ») est à l'état « (?P<etat>[^»]+) » en base"))
def etats_en_base(base_vide: Connexion, titres: str, etat: str) -> None:
	for sonore in sonores_par_titre(base_vide, titres):
		assert base_vide.execute("SELECT etat::text FROM sonores WHERE id = %s", (sonore,)).fetchone() == (etat,)


@then(parsers.re(r"la liste montre l'état « (?P<etat>[^»]+) » pour (?P<titres>«.+)"))
def etats_montres(interface: Contexte, etat: str, titres: str) -> None:
	ouverte = liste(interface)
	modele = ouverte.table.model()
	colonne = list(ouverte.source.colonnes).index("État")
	for titre in NOM.findall(titres):
		assert modele.index(index_de(ouverte, titre).row(), colonne).data() == etat, titre


@then(parsers.re(r"les sonores de la banque « (?P<nom>[^»]+) » sont, dans l'ordre, (?P<titres>aucun|«.+)"))
def sonores_de_la_banque(base_vide: Connexion, nom: str, titres: str) -> None:
	lus = base_vide.execute(
		"SELECT s.titre, bs.position FROM banques_sonores bs JOIN sonores s ON s.id = bs.sonore_id"
		" JOIN banques b ON b.id = bs.banque_id WHERE b.nom_interne = %s ORDER BY bs.position",
		(nom,),
	).fetchall()
	assert [str(titre) for titre, _position in lus] == NOM.findall(titres)
	# Les positions se suivent, sans trou.
	assert [int(str(position)) for _titre, position in lus] == list(range(1, len(lus) + 1))


@then(parsers.re(r"le choix des banques a proposé (?P<noms>«.+)"))
def banques_proposees(interface: Contexte, base_vide: Connexion, noms: str) -> None:
	(proposees,) = interface.banques_proposees
	assert proposees is not None
	assert proposees == [identifiant(base_vide, "banques", "nom_interne", nom) for nom in NOM.findall(noms)]


@then(parsers.re(r"l'audit complet est demandé pour les sonores (?P<titres>«.+), et pas pour « (?P<autre>[^»]+) »"))
def audits_demandes(base_vide: Connexion, titres: str, autre: str) -> None:
	marques = [
		str(titre)
		for (titre,) in base_vide.execute('SELECT titre FROM sonores WHERE audit_demande ORDER BY titre COLLATE "C"')
	]
	assert marques == sorted(NOM.findall(titres))
	assert autre not in marques


@then(
	parsers.re(
		r"le masquage des banques (?P<noms>«.+) est « (?P<masquage>[^»]+) » en base,"
		r" et celui de « (?P<autre>[^»]+) » « (?P<masquage_autre>[^»]+) »"
	)
)
def masquages_en_base(base_vide: Connexion, noms: str, masquage: str, autre: str, masquage_autre: str) -> None:
	for nom, attendu in [(nom, masquage) for nom in NOM.findall(noms)] + [(autre, masquage_autre)]:
		lu = base_vide.execute("SELECT masquer_metadonnees FROM banques WHERE nom_interne = %s", (nom,)).fetchone()
		assert lu == (MASQUAGES[attendu],), nom


@then(parsers.re(r"les listes qui sélectionnent plusieurs lignes sont (?P<onglets>«.+)"))
def listes_multiples(interface: Contexte, onglets: str) -> None:
	ui = fenetre(interface).ui
	multiples = sorted(
		ui.onglets.tabText(rangee)
		for rangee in range(ui.onglets.count())
		if (isinstance(ecran := ui.onglets.widget(rangee), Liste))
		and (ecran.table.selectionMode() == ecran.table.SelectionMode.ExtendedSelection)
	)
	assert multiples == NOM.findall(onglets)


# ─── Fiche d'une banque ────────────────────────────────────

ETAT_DE_SONORE = re.compile(r"« ([^»]+) » ([^,]+)")
"""« Les Gaufres – Café à minuit » actif : le sonore de la fiche et son état affiché."""


def fiche_de_banque(interface: Contexte) -> FicheBanque:
	ouverte = fenetre(interface).ui.onglets.currentWidget()
	assert isinstance(ouverte, FicheBanque), ouverte
	return ouverte


def lignes_de_la_fiche(interface: Contexte) -> list[QTreeWidgetItem]:
	sonores = fiche_de_banque(interface).ui.sonores
	return [ligne for rangee in range(sonores.topLevelItemCount()) if (ligne := sonores.topLevelItem(rangee))]


def ligne_de_la_fiche(interface: Contexte, nom: str) -> QTreeWidgetItem:
	(ligne,) = [ligne for ligne in lignes_de_la_fiche(interface) if ligne.text(0) == nom]
	return ligne


def choisir_au_clic_droit(interface: Contexte, ligne: QTreeWidgetItem, texte: str) -> None:
	menu = fiche_de_banque(interface).menu_des_sonores(ligne)
	assert menu is not None
	(action,) = [action for action in menu.actions() if action.text() == texte]
	action.trigger()


@when(parsers.re(r"je sélectionne les sonores (?P<noms>«.+) de la fiche"))
def selectionner_dans_la_fiche(interface: Contexte, noms: str) -> None:
	sonores = fiche_de_banque(interface).ui.sonores
	sonores.clearSelection()
	choisis = NOM.findall(noms)
	sonores.setCurrentItem(ligne_de_la_fiche(interface, choisis[0]))
	for nom in choisis:
		ligne_de_la_fiche(interface, nom).setSelected(True)


@when(parsers.parse("je choisis « {texte} » au clic droit sur les sonores choisis de la fiche"))
def etat_des_sonores_choisis(interface: Contexte, texte: str) -> None:
	premiere = fiche_de_banque(interface).ui.sonores.selectedItems()[0]
	choisir_au_clic_droit(interface, premiere, texte)


@when(parsers.parse("je choisis « {texte} » au clic droit sur le sonore « {nom} » de la fiche"))
def etat_d_un_sonore(interface: Contexte, texte: str, nom: str) -> None:
	choisir_au_clic_droit(interface, ligne_de_la_fiche(interface, nom), texte)


@then(parsers.re(r"les sonores de la fiche sont, avec leur état, (?P<sonores>aucun|«.+)"))
def etats_de_la_fiche(interface: Contexte, sonores: str) -> None:
	montres = [(ligne.text(0), ligne.text(COLONNE_ETAT)) for ligne in lignes_de_la_fiche(interface)]
	assert montres == ETAT_DE_SONORE.findall(sonores)


@then("seul « Retirer le sonore » sert aux sonores choisis de la fiche")
def seul_retirer(interface: Contexte) -> None:
	ui = fiche_de_banque(interface).ui
	assert [ui.retirer_sonore.isEnabled(), ui.monter.isEnabled(), ui.descendre.isEnabled()] == [True, False, False]


@then(parsers.parse("l'avertissement de réintégration a dit « {texte} »"))
def avertissement(interface: Contexte, texte: str) -> None:
	assert interface.questions == [f"retrait : {texte}"]


@when(parsers.parse("le sonore « {titre} » repasse en aperçu en base"))
def repasse_en_apercu(base_vide: Connexion, titre: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = 'apercu' WHERE titre = %s", (titre,))
