"""Scénarios des colonnes des tableaux de l'interface (https://github.com/dascritch/machincast/issues/207).

Chaque test a son propre fichier de réglages des vues (tests/conftest.py, reglages_des_vues) : jamais celui du compte.
Les étapes de la fenêtre, des onglets et des éléments en base sont dans tests/etapes_interface.py.
"""

import psycopg
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QAction, QMouseEvent, QStandardItemModel
from PySide6.QtWidgets import (
	QAbstractItemView,
	QApplication,
	QCalendarWidget,
	QGroupBox,
	QTableView,
	QTreeView,
	QWidget,
)
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import colonnes as module_colonnes
from machincast.interface.colonnes import RETABLIR, Colonnes
from machincast.interface.recherche import EcranRecherche
from tests.etapes_interface import NOM, Contexte, choisir_dans_le_menu, fenetre, onglet

scenarios("colonnes.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ATTENTE = 3000
"""Millisecondes qu'un ajustement a pour se faire : il attend la fin de la lecture du tableau."""
VUES = {
	"liste-evenements",
	"liste-sequences",
	"liste-banques",
	"liste-sonores",
	"liste-marques-pages",
	"recherche",
	"incidents",
	"accueil-airplay",
	"accueil-a-venir",
	"simulation",
	"fiche-banque-sonores",
	"fiche-sequence-elements",
	"fiche-evenement-elements",
	"fiche-sonore-relations",
	"fiche-sonore-passages",
}
"""Les vues de l'interface, une par tableau."""


def toutes(ecran: QWidget) -> list[Colonnes]:
	return [colonnes for vue in ecran.findChildren(QAbstractItemView) for colonnes in vue.findChildren(Colonnes)]


def de_l_onglet(interface: Contexte, titre: str) -> Colonnes:
	onglets = fenetre(interface).ui.onglets
	ecran = onglets.widget(onglet(interface, titre))
	(trouvees,) = toutes(ecran)
	return trouvees


def de_la_fiche(interface: Contexte, groupe: str) -> Colonnes:
	"""Les colonnes du tableau de la fiche ouverte qui est dans l'encart de ce titre."""
	fiche = fenetre(interface).ui.onglets.currentWidget()
	assert fiche is not None

	def dans(colonnes: Colonnes) -> bool:
		parent = colonnes.vue.parentWidget()
		while parent is not None:
			if (isinstance(parent, QGroupBox)) and (groupe in parent.title()):
				return True
			parent = parent.parentWidget()
		return False

	(trouvees,) = [colonnes for colonnes in toutes(fiche) if dans(colonnes)]
	return trouvees


def colonnes_de(interface: Contexte, lieu: str) -> Colonnes:
	"""« l'onglet « Sonores » » ou « du tableau « Sonores » de la fiche »."""
	nom = NOM.findall(lieu)[0]
	if lieu.startswith("du tableau"):
		return de_la_fiche(interface, nom)
	return de_l_onglet(interface, nom)


def indice(colonnes: Colonnes, titre: str) -> int:
	return colonnes.titres().index(titre)


def largeur(colonnes: Colonnes, titre: str) -> int:
	return colonnes.entete.sectionSize(indice(colonnes, titre))


def entree(colonnes: Colonnes, texte: str) -> QAction:
	(action,) = [action for action in colonnes.menu().actions() if action.text() == texte]
	return action


LIEU = r"(?P<lieu>de l'onglet « [^»]+ »|du tableau « [^»]+ » de la fiche)"


# ─── Étant donné ───────────────────────────────────────────


@given(
	parsers.re(
		r"une disposition de la vue « (?P<vue>[^»]+) », sa dernière colonne en premier,"
		r" gardée pour les colonnes (?P<titres>«.+)"
	)
)
def disposition_ancienne(vue: str, titres: str) -> None:
	"""Une disposition valable, mais gardée pour d'autres titres de colonnes que ceux de la vue."""
	anciens = NOM.findall(titres)
	modele = QStandardItemModel(0, len(anciens))
	modele.setHorizontalHeaderLabels(anciens)
	tableau = QTableView()
	tableau.setModel(modele)
	tableau.horizontalHeader().moveSection(len(anciens) - 1, 0)
	reglages = QSettings(str(module_colonnes.fichier()), QSettings.Format.IniFormat)
	reglages.beginGroup(vue)
	reglages.setValue("colonnes", anciens)
	reglages.setValue("disposition", tableau.horizontalHeader().saveState())
	reglages.endGroup()
	reglages.sync()
	tableau.deleteLater()


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(rf"j'élargis la colonne « (?P<titre>[^»]+) » {LIEU} à (?P<pixels>\d+) pixels"))
def elargir(interface: Contexte, qtbot: QtBot, titre: str, lieu: str, pixels: str) -> None:
	"""À la souris, comme l'utilisateur : la bordure droite du titre glisse jusqu'à la largeur voulue."""
	colonnes = colonnes_de(interface, lieu)
	qtbot.wait(50)
	entete = colonnes.entete
	colonne = indice(colonnes, titre)
	bord = entete.sectionViewportPosition(colonne) + entete.sectionSize(colonne) - 1
	hauteur = entete.height() // 2
	cible = bord + int(pixels) - entete.sectionSize(colonne)
	ecran = entete.viewport()
	for genre, x, boutons in (
		(QEvent.Type.MouseButtonPress, bord, Qt.MouseButton.LeftButton),
		(QEvent.Type.MouseMove, cible, Qt.MouseButton.LeftButton),
		(QEvent.Type.MouseButtonRelease, cible, Qt.MouseButton.NoButton),
	):
		position = QPointF(x, hauteur)
		evenement = QMouseEvent(
			genre,
			position,
			ecran.mapToGlobal(position),
			Qt.MouseButton.LeftButton,
			boutons,
			Qt.KeyboardModifier.NoModifier,
		)
		QApplication.sendEvent(ecran, evenement)
	assert entete.sectionSize(colonne) == int(pixels), entete.sectionSize(colonne)


@when(parsers.re(rf"je glisse la colonne « (?P<titre>[^»]+) » {LIEU} en première place"))
def glisser(interface: Contexte, titre: str, lieu: str) -> None:
	colonnes = colonnes_de(interface, lieu)
	entete = colonnes.entete
	entete.moveSection(entete.visualIndex(indice(colonnes, titre)), 0)


@when(parsers.re(rf"je (?P<geste>coche|décoche) « (?P<titre>[^»]+) » dans le menu des colonnes {LIEU}"))
def cocher(interface: Contexte, geste: str, titre: str, lieu: str) -> None:
	action = entree(colonnes_de(interface, lieu), titre)
	assert action.isEnabled()
	assert action.isChecked() == (geste == "décoche")
	action.trigger()


@when(parsers.re(rf"je choisis « {RETABLIR} » dans le menu des colonnes {LIEU}"))
def retablir(interface: Contexte, lieu: str) -> None:
	entree(colonnes_de(interface, lieu), RETABLIR).trigger()


@when(parsers.parse("je tape « {texte} » dans le champ de recherche"))
def taper(interface: Contexte, texte: str) -> None:
	(recherche,) = fenetre(interface).findChildren(EcranRecherche)
	recherche.champ.setText(texte)


@when(parsers.parse("le sonore « {titre} » est ajouté à la banque « {banque} » en base"))
def ajouter_a_la_banque(base_vide: Connexion, titre: str, banque: str) -> None:
	ligne = base_vide.execute(
		"INSERT INTO sonores (type, emplacement, titre) VALUES ('fichier', %s, %s) RETURNING id",
		(f"/srv/{titre}.flac", titre),
	).fetchone()
	assert ligne is not None
	base_vide.execute(
		"INSERT INTO banques_sonores (banque_id, sonore_id, position)"
		" SELECT id, %s, 99 FROM banques WHERE nom_interne = %s",
		(ligne[0], banque),
	)


@when("j'ouvre chaque onglet et la fiche de chaque genre")
def tout_ouvrir(interface: Contexte, qtbot: QtBot) -> None:
	ouverte = fenetre(interface)
	for entree_du_menu in (
		"Ouvrir l'onglet Sonores",
		"Ouvrir l'onglet Marques-pages",
		"Ouvrir l'onglet Simulation",
		"Rechercher…",
	):
		choisir_dans_le_menu(interface, entree_du_menu, "Affichage")
	for genre in ("banque", "séquence", "événement", "sonore"):
		ouverte._ouvrir_fiche(genre, None)
	qtbot.wait(50)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(rf"la colonne « (?P<titre>[^»]+) » {LIEU} montre « (?P<texte>[^»]+) » en entier"))
def en_entier(interface: Contexte, qtbot: QtBot, titre: str, lieu: str, texte: str) -> None:
	colonnes = colonnes_de(interface, lieu)
	necessaire = colonnes.vue.fontMetrics().horizontalAdvance(texte)
	qtbot.waitUntil(lambda: largeur(colonnes, titre) >= necessaire, timeout=ATTENTE)


@then(parsers.re(rf"la colonne « (?P<titre>[^»]+) » {LIEU} (?P<verdict>fait|ne fait pas) (?P<pixels>\d+) pixels"))
def fait(interface: Contexte, qtbot: QtBot, titre: str, lieu: str, verdict: str, pixels: str) -> None:
	qtbot.wait(100)
	colonnes = colonnes_de(interface, lieu)
	assert (largeur(colonnes, titre) == int(pixels)) == (verdict == "fait"), largeur(colonnes, titre)


@then(parsers.re(rf"la dernière colonne {LIEU} s'étire jusqu'au bord du tableau"))
def etiree(interface: Contexte, qtbot: QtBot, lieu: str) -> None:
	colonnes = colonnes_de(interface, lieu)
	entete = colonnes.entete
	derniere = entete.logicalIndex(entete.count() - 1)

	def jusqu_au_bord() -> bool:
		return entete.sectionViewportPosition(derniere) + entete.sectionSize(derniere) == entete.viewport().width()

	qtbot.waitUntil(jusqu_au_bord, timeout=ATTENTE)


@then(parsers.re(rf"les colonnes {LIEU} sont (?P<titres>«.+)"))
def montrees(interface: Contexte, lieu: str, titres: str) -> None:
	assert colonnes_de(interface, lieu).montrees() == NOM.findall(titres)


@then(parsers.re(rf"le menu des colonnes {LIEU} propose :"))
def menu(interface: Contexte, lieu: str, datatable: list[list[str]]) -> None:
	_, *lignes = datatable

	def ligne(action: QAction) -> list[str]:
		if action.isSeparator():
			return ["—", ""]
		if not action.isCheckable():
			return [action.text(), ""]
		if action.isChecked():
			return [action.text(), "coché"]
		return [action.text(), "décoché"]

	obtenues = [ligne(action) for action in colonnes_de(interface, lieu).menu().actions()]
	assert obtenues == [[valeur.strip() for valeur in ligne] for ligne in lignes]


@then(parsers.re(rf"l'entrée « (?P<titre>[^»]+) » du menu des colonnes {LIEU} est inactive"))
def inactive(interface: Contexte, titre: str, lieu: str) -> None:
	assert not entree(colonnes_de(interface, lieu), titre).isEnabled()


@then(parsers.parse("les réglages du compte gardent la vue « {vue} »"))
def gardee(vue: str) -> None:
	reglages = QSettings(str(module_colonnes.fichier()), QSettings.Format.IniFormat)
	assert vue in reglages.childGroups(), reglages.childGroups()


@then("le fichier de configuration n'a pas changé")
def configuration_intacte(interface: Contexte) -> None:
	chemin = fenetre(interface).configuration
	assert chemin is not None
	assert chemin.read_bytes() == interface.configuration_initiale


@then("chaque tableau de l'interface a des colonnes déplaçables, de largeur libre, avec le menu des colonnes de sa vue")
def tous_les_tableaux(interface: Contexte) -> None:
	ouverte = fenetre(interface)
	vues = [
		vue
		for vue in ouverte.findChildren(QAbstractItemView)
		if (isinstance(vue, (QTableView, QTreeView))) and (not _dans_un_calendrier(vue))
	]
	noms = set()
	for vue in vues:
		(colonnes,) = vue.findChildren(Colonnes)
		entete = colonnes.entete
		assert entete.sectionsMovable(), colonnes.nom
		# La dernière colonne affichée peut s'étirer jusqu'au bord du tableau ; les autres sont de largeur libre.
		derniere = entete.logicalIndex(entete.count() - 1)
		libres = [colonne for colonne in range(entete.count()) if colonne != derniere]
		assert all(entete.sectionResizeMode(colonne) == entete.ResizeMode.Interactive for colonne in libres), (
			colonnes.nom
		)
		assert entete.property(module_colonnes.PROPRIETE) == colonnes.nom
		noms.add(colonnes.nom)
	assert noms == VUES, sorted(noms ^ VUES)


def _dans_un_calendrier(vue: QWidget) -> bool:
	"""Le tableau des jours d'un sélecteur de date n'est pas un tableau de l'interface."""
	parent = vue.parentWidget()
	while parent is not None:
		if isinstance(parent, QCalendarWidget):
			return True
		parent = parent.parentWidget()
	return False
