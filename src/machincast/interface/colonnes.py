"""Colonnes des tableaux de l'interface (https://github.com/dascritch/machincast/issues/207).

Chaque tableau, QTableView ou QTreeView, est une vue, nommée par sa clé : « liste-sonores », « recherche »,
« fiche-banque-sonores »… Colonnes s'y attache, et :

- ajuste les colonnes à leur contenu (resizeColumnToContents) à chaque lecture du tableau : modèle remis à zéro,
  lignes ajoutées ou réordonnées. C'est un ajustement ponctuel, et non le mode ResizeToContents de Qt, qui ignore le
  contenu quand l'en-tête vertical est masqué, et interdit d'élargir une colonne à la main. Qt ne mesure que les
  lignes visibles du tableau : un tableau caché, dans un onglet pas encore ouvert, est ajusté quand il se montre ou
  change de taille. Une fois une colonne
  élargie à la main, l'ajustement s'arrête pour la vue, jusqu'à « Rétablir les colonnes » ;
- laisse déplacer une colonne en glissant son titre (setSectionsMovable) ;
- propose au clic droit sur les titres le menu des colonnes (menu) : une entrée à cocher par colonne, dans l'ordre
  affiché, la dernière colonne montrée restant inactive, puis « Rétablir les colonnes », qui remet l'ordre et les
  colonnes d'origine, oublie les largeurs et réajuste ;
- garde la disposition de la vue (QHeaderView.saveState : ordre, colonnes cachées, largeurs) dans les réglages du
  compte, fichier(), un fichier .ini hors du machincast.toml du poste : chacun garde ses vues. Une disposition gardée
  pour d'autres colonnes, d'une version précédente, est oubliée. L'indicateur de tri n'est pas repris : chaque vue
  garde le tri qu'elle a à l'ouverture ;
- propose au clic droit dans le tableau « Exporter ce tableau… » (https://github.com/dascritch/machincast/issues/329),
  après les entrées de sa ligne, s'il en a (menu_des_lignes) : un sélecteur de fichier (choisir_le_fichier), puis le
  tableau tel qu'il est affiché, en CSV (en_csv) : les colonnes montrées, dans leur ordre, et les lignes que garde le
  filtre, dans l'ordre du tri. La barre d'état de la fenêtre dit où il est enregistré, ou pourquoi il ne l'est pas. Un
  export ne remplace jamais un fichier sonore (https://github.com/dascritch/machincast/issues/96).
"""

import csv
import io
import logging
import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QObject, QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
	QAbstractItemView,
	QFileDialog,
	QHeaderView,
	QMainWindow,
	QMenu,
	QTableView,
	QTreeView,
	QWidget,
)

from machincast.protection import verifier_ecriture

journal = logging.getLogger(__name__)

FICHIER: Path | None = None
"""Le fichier des réglages des vues ; None : celui du compte, sous $XDG_CONFIG_HOME. Les tests le remplacent."""
NOM_DU_FICHIER = Path("machincast") / "vues.ini"
RETABLIR = "Rétablir les colonnes"
PROPRIETE = "vue"
"""Propriété de l'en-tête qui porte le nom de sa vue."""
EXPORTER = "Exporter ce tableau…"
FILTRE_CSV = "Tableur CSV (*.csv)"
SEPARATEUR = ";"
"""Séparateur du CSV, comme ceux de la diffusion et de l'airplay."""
DUREE_DE_L_ANNONCE = 10000
"""Millisecondes pendant lesquelles la barre d'état dit ce que l'export a donné."""


def choisir_le_fichier(parent: QWidget, propose: str) -> Path | None:
	"""Le fichier où exporter le tableau, en .csv ; None si le choix est abandonné. Les tests le remplacent."""
	chemin, _filtre = QFileDialog.getSaveFileName(parent, "Exporter ce tableau", str(Path.home() / propose), FILTRE_CSV)
	if chemin == "":
		return None
	return Path(chemin)


def fichier() -> Path:
	"""Les réglages des vues du compte : $XDG_CONFIG_HOME/machincast/vues.ini, ou ~/.config/machincast/vues.ini."""
	if FICHIER is not None:
		return FICHIER
	racine = Path.home() / ".config"
	configuration = os.environ.get("XDG_CONFIG_HOME", "")
	if configuration != "":
		racine = Path(configuration)
	return racine / NOM_DU_FICHIER


def reglages() -> QSettings:
	return QSettings(str(fichier()), QSettings.Format.IniFormat)


def entete(vue: QAbstractItemView) -> QHeaderView:
	if isinstance(vue, QTreeView):
		return vue.header()
	assert isinstance(vue, QTableView)
	return vue.horizontalHeader()


class Colonnes(QObject):
	"""Les colonnes d'une vue : ajustées, déplaçables, à montrer ou cacher, gardées dans les réglages du compte."""

	def __init__(self, vue: QAbstractItemView, nom: str) -> None:
		super().__init__(vue)
		self.vue = vue
		self.nom = nom
		self.entete = entete(vue)
		self.reglees = False
		"""Une colonne a été élargie à la main : l'ajustement au contenu s'arrête."""
		self._ajustement = False
		self._chargement = False
		self._glisse = False
		"""Le bouton de la souris est enfoncé sur les titres : un redimensionnement vient de l'utilisateur. Qt
		redimensionne aussi les colonnes de lui-même, en posant le tableau ou en étirant la dernière colonne."""
		self._ajuster_bientot = QTimer(self)
		self._ajuster_bientot.setSingleShot(True)
		self._ajuster_bientot.setInterval(0)
		self._ajuster_bientot.timeout.connect(self.ajuster)
		self.menu_des_lignes: Callable[[QPoint], QMenu | None] | None = None
		"""Le menu de la ligne sous le clic droit, à la position du clic dans le tableau, que le tableau propose ;
		« Exporter ce tableau… » le complète."""
		vue.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		vue.customContextMenuRequested.connect(self._montrer_le_menu_du_tableau)
		self.entete.setProperty(PROPRIETE, nom)
		self.entete.setSectionsMovable(True)
		self.entete.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.entete.customContextMenuRequested.connect(self._montrer_le_menu)
		self._origine = QByteArray(self.entete.saveState())
		self.restaurer()
		self.entete.sectionMoved.connect(lambda *_: self.enregistrer())
		self.entete.sectionResized.connect(self._redimensionnee)
		modele = vue.model()
		for signal in (modele.modelReset, modele.rowsInserted, modele.layoutChanged):
			signal.connect(lambda *_: self._ajuster_bientot.start())
		vue.installEventFilter(self)
		# Gardé ici : pendant la destruction du tableau, l'en-tête peut disparaître avant ses derniers événements.
		self._titres = self.entete.viewport()
		self._titres.installEventFilter(self)
		self._ajuster_bientot.start()

	def eventFilter(self, objet: QObject, evenement: QEvent) -> bool:
		"""Un tableau qui se montre, ou change de taille, a de nouvelles lignes visibles à mesurer."""
		if objet is self._titres:
			if evenement.type() == QEvent.Type.MouseButtonPress:
				self._glisse = True
			elif evenement.type() == QEvent.Type.MouseButtonRelease:
				self._glisse = False
			return False
		if evenement.type() in (QEvent.Type.Show, QEvent.Type.Resize):
			self._ajuster_bientot.start()
		return False

	def titres(self) -> list[str]:
		"""Les titres des colonnes, dans l'ordre du modèle."""
		modele = self.vue.model()
		return [str(modele.headerData(colonne, Qt.Orientation.Horizontal)) for colonne in range(modele.columnCount())]

	def montrees(self) -> list[str]:
		"""Les titres des colonnes montrées, dans l'ordre affiché."""
		titres = self.titres()
		ordre = [self.entete.logicalIndex(rang) for rang in range(self.entete.count())]
		return [titres[colonne] for colonne in ordre if not self.entete.isSectionHidden(colonne)]

	def ajuster(self) -> None:
		"""Les colonnes à la largeur de leur contenu, tant qu'aucune n'a été élargie à la main."""
		if self.reglees:
			return
		vue = self.vue
		assert isinstance(vue, (QTableView, QTreeView))
		# Colonne par colonne : resizeColumnsToContents rétrécirait aussi la dernière, quand elle s'étire jusqu'au bord.
		self._ajustement = True
		try:
			for colonne in range(self.entete.count()):
				vue.resizeColumnToContents(colonne)
		finally:
			self._ajustement = False

	def montrer(self, colonne: int, visible: bool) -> None:
		self.entete.setSectionHidden(colonne, not visible)
		self.enregistrer()

	def retablir(self) -> None:
		"""L'ordre et les colonnes d'origine, les largeurs ajustées au contenu ; la disposition gardée est oubliée."""
		self._chargement = True
		try:
			self.entete.restoreState(self._origine)
		finally:
			self._chargement = False
		self.reglees = False
		reglages().remove(self.nom)
		self.ajuster()

	def menu(self) -> QMenu:
		"""Le menu des colonnes : une entrée à cocher par colonne, dans l'ordre affiché, puis « Rétablir les
		colonnes »."""
		menu = QMenu(self.vue)
		titres = self.titres()
		montrees = len(self.montrees())
		for rang in range(self.entete.count()):
			colonne = self.entete.logicalIndex(rang)
			action = QAction(titres[colonne], menu)
			action.setCheckable(True)
			visible = not self.entete.isSectionHidden(colonne)
			action.setChecked(visible)
			# La dernière colonne montrée ne se cache pas : la vue resterait vide.
			action.setEnabled((not visible) or (montrees > 1))
			action.toggled.connect(lambda coche, colonne=colonne: self.montrer(colonne, coche))
			menu.addAction(action)
		menu.addSeparator()
		menu.addAction(RETABLIR).triggered.connect(self.retablir)
		return menu

	def _montrer_le_menu(self, position: QPoint) -> None:
		self.menu().popup(self.entete.mapToGlobal(position))

	def menu_du_tableau(self, position: QPoint) -> QMenu:
		"""Le menu du clic droit à cette position du tableau : celui de sa ligne, s'il en a, puis « Exporter ce
		tableau… »."""
		menu = None
		if self.menu_des_lignes is not None:
			menu = self.menu_des_lignes(position)
		if menu is None:
			menu = QMenu(self.vue)
		elif menu.actions() != []:
			menu.addSeparator()
		menu.addAction(EXPORTER).triggered.connect(self.exporter)
		return menu

	def _montrer_le_menu_du_tableau(self, position: QPoint) -> None:
		menu = self.menu_du_tableau(position)
		menu.exec(self.vue.viewport().mapToGlobal(position))
		menu.deleteLater()

	def en_csv(self) -> str:
		"""Le tableau tel qu'il est affiché : les titres et les cellules des colonnes montrées, dans l'ordre affiché,
		et les lignes montrées, dans l'ordre du tri ; seules les lignes de premier niveau d'un arbre."""
		modele = self.vue.model()
		titres = self.titres()
		ordre = [self.entete.logicalIndex(rang) for rang in range(self.entete.count())]
		colonnes = [colonne for colonne in ordre if not self.entete.isSectionHidden(colonne)]
		sortie = io.StringIO()
		ecrivain = csv.writer(sortie, delimiter=SEPARATEUR, lineterminator="\n")
		ecrivain.writerow([titres[colonne] for colonne in colonnes])
		for rangee in range(modele.rowCount()):
			if (isinstance(self.vue, QTableView)) and (self.vue.isRowHidden(rangee)):
				continue
			cellules = [modele.index(rangee, colonne).data() for colonne in colonnes]
			ecrivain.writerow([str((cellule) or ("")) for cellule in cellules])
		return sortie.getvalue()

	def exporter(self) -> None:
		"""« Exporter ce tableau… » : le fichier choisi reçoit le tableau en CSV, en UTF-8 avec BOM pour les
		tableurs, avec l'extension .csv s'il ne l'a pas."""
		chemin = choisir_le_fichier(self.vue, f"{self.nom}.csv")
		if chemin is None:
			return
		if chemin.suffix.lower() != ".csv":
			chemin = chemin.with_name(f"{chemin.name}.csv")
		try:
			verifier_ecriture(chemin)
			chemin.write_text(self.en_csv(), encoding="utf-8-sig", newline="")
		except OSError as erreur:
			journal.error(f"export du tableau {self.nom} impossible : {erreur}")
			self._annoncer(f"Export impossible : {erreur}")
			return
		self._annoncer(f"Tableau exporté dans {chemin}.")

	def _annoncer(self, texte: str) -> None:
		fenetre = self.vue.window()
		if isinstance(fenetre, QMainWindow):
			fenetre.statusBar().showMessage(texte, DUREE_DE_L_ANNONCE)

	def _redimensionnee(self, _colonne: int, _avant: int, _apres: int) -> None:
		if (self._ajustement) or (self._chargement) or (not self._glisse):
			return
		self.reglees = True
		self.enregistrer()

	def enregistrer(self) -> None:
		if self._chargement:
			return
		memoire = reglages()
		memoire.beginGroup(self.nom)
		memoire.setValue("colonnes", self.titres())
		memoire.setValue("disposition", self.entete.saveState())
		memoire.setValue("largeurs", self.reglees)
		memoire.endGroup()

	def restaurer(self) -> None:
		"""La disposition gardée, si elle est celle de ces colonnes ; le tri de la vue reste le sien."""
		memoire = reglages()
		memoire.beginGroup(self.nom)
		colonnes = memoire.value("colonnes")
		disposition = memoire.value("disposition")
		largeurs = memoire.value("largeurs")
		memoire.endGroup()
		if (not isinstance(disposition, QByteArray)) or (_liste(colonnes) != self.titres()):
			return
		self._chargement = True
		try:
			if not self.entete.restoreState(disposition):
				journal.warning(f"disposition des colonnes de la vue {self.nom} illisible : oubliée")
				return
		finally:
			self._chargement = False
		self.reglees = str(largeurs).lower() == "true"


def _liste(valeur: object) -> list[str]:
	"""Une liste lue dans les réglages : QSettings rend une seule valeur, sans liste, pour une liste d'un élément."""
	if isinstance(valeur, list):
		return [str(element) for element in valeur]
	if valeur is None:
		return []
	return [str(valeur)]
