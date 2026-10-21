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
  garde le tri qu'elle a à l'ouverture.
"""

import logging
import os
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QObject, QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QMenu, QTableView, QTreeView

journal = logging.getLogger(__name__)

FICHIER: Path | None = None
"""Le fichier des réglages des vues ; None : celui du compte, sous $XDG_CONFIG_HOME. Les tests le remplacent."""
NOM_DU_FICHIER = Path("machincast") / "vues.ini"
RETABLIR = "Rétablir les colonnes"
PROPRIETE = "vue"
"""Propriété de l'en-tête qui porte le nom de sa vue."""


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
