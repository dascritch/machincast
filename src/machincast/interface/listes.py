"""Listes filtrables des sonores, des banques, des séquences et des événements
(https://github.com/dascritch/machincast/issues/26, spec § 8.2).

Chaque liste est un onglet de la fenêtre (machincast.interface.fenetre). Elle se lit en base avec le rôle de
l'interface, chaque fois que son onglet s'ouvre : jamais en boucle. Le filtre garde les lignes dont une colonne contient
le texte tapé, sans tenir compte des majuscules ni des accents. Ouvrir une ligne (double-clic ou Entrée) demande
l'écran de détail de l'élément (signal ouverte). Une liste peut avoir un bouton qui crée un élément
(signal creation_demandee) : « Nouvelle banque » (https://github.com/dascritch/machincast/issues/31). Une ligne en
anomalie, une séquence ou un événement vide, a l'icône d'avertissement, une infobulle qui l'explique, et le compte les
dénombre (https://github.com/dascritch/machincast/issues/138, https://github.com/dascritch/machincast/issues/140).
Le clic droit sur une ligne d'événement, de séquence ou de banque propose « Dupliquer » (signal duplication_demandee,
https://github.com/dascritch/machincast/issues/130). Les listes des sonores et des banques sélectionnent plusieurs
lignes (Ctrl, Maj) ; leur clic droit propose les actions sur la sélection, ou sur la seule ligne cliquée hors de la
sélection (signal action_demandee, machincast.interface.groupes, https://github.com/dascritch/machincast/issues/114).
"""

import logging
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QPoint, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QLabel, QLineEdit, QMenu, QTableView, QWidget

from machincast.interface import affichage, groupes
from machincast.interface.colonnes import Colonnes
from machincast.interface.depot import DepotDeFichiers
from machincast.interface.ui.liste import Ui_Liste

journal = logging.getLogger(__name__)

Connexion = psycopg.Connection[TupleRow]
IDENTIFIANT = Qt.ItemDataRole.UserRole
"""Rôle qui porte, sur la première cellule d'une ligne, l'identifiant de l'élément en base."""
ETATS = {
	"apercu": "aperçu",
	"actif": "actif",
	"desactive": "désactivé",
	"expire": "expiré",
	"errone": "erroné",
	"non_supporte": "non supporté",
	"supprime": "supprimé",
}
PRIORITES = {"special": "spécial", "emission": "émission", "fil_musical": "fil musical", "secours": "secours"}
MODES = {"sequentiel": "séquentielle", "aleatoire": "aléatoire"}
SEQUENCE_VIDE = "Séquence vide : elle ne joue rien, et un événement qui l'appelle passe à son élément suivant."
_RELAIS = "Événement vide : il ne joue rien, et l'événement de priorité inférieure prend le relais pendant sa plage."
EVENEMENT_VIDE = {
	"special": _RELAIS,
	"emission": _RELAIS,
	"fil_musical": (
		"Événement vide : il ne joue rien, et la diffusion se tait, avec une alerte, quand il est à l'antenne."
	),
	"secours": "Événement vide : il ne joue rien, et l'événement de priorité inférieure remplace le stream tombé.",
}
"""Ce que fait la diffusion d'un événement vide, selon sa priorité (spec § 4.2,
https://github.com/dascritch/machincast/issues/140)."""


@dataclass(frozen=True)
class Ligne:
	identifiant: int
	nom: str
	"""Nom de l'élément, pour l'annoncer."""
	cellules: list[str]
	anomalie: str = ""
	"""Ce qui ne va pas, en une phrase, pour l'infobulle de la ligne ; rien pour une ligne saine."""


@dataclass(frozen=True)
class Source:
	"""Un type d'élément : ses colonnes, sa lecture en base, et les mots pour le compter."""

	genre: str
	colonnes: tuple[str, ...]
	lire: Callable[[Connexion], list[Ligne]]
	singulier: str
	pluriel: str
	aucun: str
	nouveau: str = ""
	"""Texte du bouton qui crée un élément de ce type ; aucun bouton sans texte."""
	fichiers: str = ""
	"""Texte du bouton qui ajoute des fichiers, qui se déposent aussi sur la liste ; ni bouton ni dépôt sans texte."""
	duplicable: bool = False
	"""Le clic droit sur une ligne propose « Dupliquer »."""


def _texte(valeur: object) -> str:
	if valeur is None:
		return ""
	return str(valeur)


def _date(valeur: object) -> str:
	if not isinstance(valeur, datetime):
		return ""
	return f"{valeur.astimezone():%Y-%m-%d %H:%M}"


def lire_sonores(connexion: Connexion) -> list[Ligne]:
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT s.id, s.artiste, s.titre, s.type::text, s.etat::text, s.audit_demande, s.duree,"
			" COALESCE(s.emplacement, s.url_stream, m.url)"
			" FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id"
			" ORDER BY s.artiste NULLS LAST, s.titre, s.id"
		).fetchall()
	lignes = []
	for identifiant, artiste, titre, type_sonore, etat, audit_demande, duree, emplacement in rangees:
		texte_duree = ""
		if type_sonore == "stream":
			texte_duree = affichage.duree(None)
		elif isinstance(duree, timedelta):
			texte_duree = affichage.duree(duree)
		texte_etat = ETATS.get(str(etat), str(etat))
		if audit_demande is True:
			# https://github.com/dascritch/machincast/issues/114
			texte_etat = f"{texte_etat}, audit demandé"
		# Les durées d'une banque ne se signalent que dans sa fiche, et parmi les relations du sonore, jamais ici
		# (https://github.com/dascritch/machincast/issues/210).
		cellules = [_texte(artiste), _texte(titre), str(type_sonore), texte_etat, texte_duree, _texte(emplacement)]
		lignes.append(Ligne(int(str(identifiant)), (_texte(titre)) or (_texte(emplacement)), cellules))
	return lignes


def lire_banques(connexion: Connexion) -> list[Ligne]:
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT b.id, b.nom_interne, b.nom_public, b.mode::text, b.ne_pas_repeter,"
			" (SELECT min(r.repertoire) FROM banques_repertoires r WHERE r.banque_id = b.id)"
			" FROM banques b ORDER BY b.nom_interne, b.id"
		).fetchall()
	lignes = []
	for identifiant, nom, nom_public, mode, marquee, repertoire in rangees:
		cellules = [str(nom), _texte(nom_public), MODES.get(str(mode), str(mode))]
		cellules += [affichage.oui_non(bool(marquee)), _texte(repertoire)]
		lignes.append(Ligne(int(str(identifiant)), str(nom), cellules))
	return lignes


def lire_sequences(connexion: Connexion) -> list[Ligne]:
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT q.id, q.nom_interne, q.nom_public,"
			" NOT EXISTS (SELECT 1 FROM sequences_elements e WHERE e.sequence_id = q.id)"
			" FROM sequences q ORDER BY q.nom_interne, q.id"
		).fetchall()
	lignes = []
	for identifiant, nom, nom_public, vide in rangees:
		cellules = [str(nom), _texte(nom_public), ""]
		anomalie = ""
		if vide:
			cellules[2] = "séquence vide"
			anomalie = SEQUENCE_VIDE
		lignes.append(Ligne(int(str(identifiant)), str(nom), cellules, anomalie))
	return lignes


def lire_marques_pages(connexion: Connexion) -> list[Ligne]:
	"""Par nom, avec le nombre de streams qui suivent chacun (https://github.com/dascritch/machincast/issues/34)."""
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT m.id, m.nom, m.url, (SELECT count(*) FROM sonores s WHERE s.marque_page_id = m.id)"
			" FROM marques_pages_streams m ORDER BY m.nom, m.id"
		).fetchall()
	return [
		Ligne(int(str(identifiant)), str(nom), [str(nom), str(url), str(streams)])
		for identifiant, nom, url, streams in rangees
	]


def lire_evenements(connexion: Connexion) -> list[Ligne]:
	"""Du plus prioritaire au moins prioritaire, puis par nom."""
	with connexion.transaction():
		rangees = connexion.execute(
			"SELECT e.id, e.nom_interne, e.nom_public, e.priorite::text, e.debut, e.fin, e.jours_recurrence::text[],"
			" NOT EXISTS (SELECT 1 FROM evenements_elements x WHERE x.evenement_id = e.id)"
			# e.priorite : l'ordre du type énuméré, pas celui du texte de la colonne affichée.
			" FROM evenements e ORDER BY e.priorite DESC, e.nom_interne, e.id"
		).fetchall()
	lignes = []
	for identifiant, nom, nom_public, priorite, debut, fin, jours, vide in rangees:
		recurrence = ""
		if isinstance(jours, list):
			recurrence = ", ".join(str(jour) for jour in jours)
		cellules = [str(nom), _texte(nom_public), PRIORITES.get(str(priorite), str(priorite)), _date(debut), _date(fin)]
		cellules += [recurrence, ""]
		anomalie = ""
		if vide:
			cellules[-1] = "événement vide"
			anomalie = EVENEMENT_VIDE[str(priorite)]
		lignes.append(Ligne(int(str(identifiant)), str(nom), cellules, anomalie))
	return lignes


SONORES = Source(
	"sonore",
	("Artiste", "Titre", "Type", "État", "Durée", "Emplacement"),
	lire_sonores,
	"sonore",
	"sonores",
	"aucun sonore",
	"Nouveau stream",
	"Ajouter des fichiers…",
)
BANQUES = Source(
	"banque",
	("Nom", "Nom public", "Mode", "Ne pas répéter", "Répertoire"),
	lire_banques,
	"banque",
	"banques",
	"aucune banque",
	"Nouvelle banque",
	duplicable=True,
)
SEQUENCES = Source(
	"séquence",
	("Nom", "Nom public", "Anomalie"),
	lire_sequences,
	"séquence",
	"séquences",
	"aucune séquence",
	"Nouvelle séquence",
	duplicable=True,
)
EVENEMENTS = Source(
	"événement",
	("Nom", "Nom public", "Priorité", "Début", "Fin", "Récurrence", "Anomalie"),
	lire_evenements,
	"événement",
	"événements",
	"aucun événement",
	"Nouvel événement",
	duplicable=True,
)
MARQUES_PAGES = Source(
	"marque-page",
	("Nom", "Adresse", "Streams"),
	lire_marques_pages,
	"marque-page",
	"marques-pages",
	"aucun marque-page",
	"Nouveau marque-page",
)


def nom_de_vue(texte: str) -> str:
	"""« marques-pages », « evenements » : sans accents, ni majuscules, ni espaces."""
	return sans_accents(texte).replace(" ", "-")


def sans_accents(texte: str) -> str:
	"""Le texte en minuscules, sans accents ni cédilles : « Été » donne « ete »."""
	decompose = unicodedata.normalize("NFKD", texte.casefold())
	return "".join(lettre for lettre in decompose if not unicodedata.combining(lettre))


class FiltreSansAccents(QSortFilterProxyModel):
	"""Garde les lignes dont une colonne contient le texte, sans tenir compte des majuscules ni des accents."""

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._texte = ""

	def filtrer(self, texte: str) -> None:
		self.beginFilterChange()
		self._texte = sans_accents(texte)
		self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

	def filterAcceptsRow(self, rangee: int, parent: QModelIndex | QPersistentModelIndex) -> bool:
		modele = self.sourceModel()
		for colonne in range(modele.columnCount()):
			valeur = modele.index(rangee, colonne, parent).data()
			if self._texte in sans_accents(str((valeur) or (""))):
				return True
		return False


class Liste(QWidget):
	ouverte = Signal(str, int, str)
	"""Ligne ouverte : genre, identifiant et nom de l'élément."""
	creation_demandee = Signal(str)
	"""Bouton de création cliqué : genre de l'élément à créer."""
	ajout_demande = Signal()
	"""Bouton d'ajout de fichiers cliqué."""
	fichiers_deposes = Signal(list)
	"""Fichiers déposés sur la liste (list[Path]) : https://github.com/dascritch/machincast/issues/30."""
	duplication_demandee = Signal(str, int)
	"""« Dupliquer » choisi au clic droit sur une ligne : genre et identifiant de l'élément."""
	action_demandee = Signal(str, list)
	"""Une action choisie au clic droit (machincast.interface.groupes) : sa clé, et les éléments (list[int])."""

	def __init__(
		self,
		source: Source,
		connexion: Connexion,
		parent: QWidget | None = None,
		actions: bool = True,
		vue: str | None = None,
	) -> None:
		"""vue : le nom sous lequel ses colonnes sont gardées ; par défaut, « liste- » suivi du pluriel du genre
		({I})."""
		"""actions : les boutons de création et d'ajout, et le dépôt de fichiers ; pas dans un choix d'éléments."""
		super().__init__(parent)
		self.source = source
		self.connexion = connexion
		self.ui = Ui_Liste()
		self.ui.setupUi(self)
		self.modele = QStandardItemModel(0, len(source.colonnes), self)
		self.modele.setHorizontalHeaderLabels(list(source.colonnes))
		self.proxy = FiltreSansAccents(self)
		self.proxy.setSourceModel(self.modele)
		self.proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
		self.table.setModel(self.proxy)
		entete = self.table.horizontalHeader()
		if vue is None:
			vue = f"liste-{nom_de_vue(source.pluriel)}"
		self.colonnes = Colonnes(self.table, vue)
		# Un clic sur un titre de colonne trie la liste ; avant, elle garde l'ordre de la base.
		self.table.setSortingEnabled(True)
		entete.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
		self.filtre.textChanged.connect(self._filtrer)
		self.table.activated.connect(self._ouvrir)
		self.ui.nouveau.setText(source.nouveau)
		self.ui.nouveau.setVisible((actions) and (source.nouveau != ""))
		self.ui.nouveau.clicked.connect(lambda: self.creation_demandee.emit(source.genre))
		self.ui.ajouter_fichiers.setText(source.fichiers)
		self.ui.ajouter_fichiers.setVisible((actions) and (source.fichiers != ""))
		self.ui.ajouter_fichiers.clicked.connect(self.ajout_demande)
		if (actions) and (source.fichiers != ""):
			self.depot = DepotDeFichiers(self.table)
			self.depot.deposes.connect(self.fichiers_deposes)
		self.duplicable = (actions) and (source.duplicable)
		self.actions_groupees: tuple[groupes.Action, ...] = ()
		"""Les actions sur la sélection ; aucune hors des listes des sonores et des banques, ou dans un choix."""
		if actions:
			self.actions_groupees = groupes.ACTIONS.get(source.genre, ())
		if self.actions_groupees != ():
			self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		if (self.duplicable) or (self.actions_groupees != ()):
			self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
			self.table.customContextMenuRequested.connect(self._menu)
		self._compter()

	@property
	def filtre(self) -> QLineEdit:
		return self.ui.filtre

	@property
	def compte(self) -> QLabel:
		return self.ui.compte

	@property
	def table(self) -> QTableView:
		return self.ui.table

	def actualiser(self) -> None:
		"""Relit la liste en base ; une base injoignable laisse la liste telle qu'elle était."""
		try:
			lignes = self.source.lire(self.connexion)
		except psycopg.Error as erreur:
			journal.error(f"liste des {self.source.pluriel} illisible : {erreur}")
			return
		self.modele.setRowCount(0)
		for ligne in lignes:
			cellules = [QStandardItem(texte) for texte in ligne.cellules]
			cellules[0].setData(ligne.identifiant, IDENTIFIANT)
			cellules[0].setData(ligne.nom, IDENTIFIANT + 1)
			if ligne.anomalie:
				cellules[0].setIcon(affichage.icone_d_anomalie(self))
				for cellule in cellules:
					cellule.setToolTip(ligne.anomalie)
			self.modele.appendRow(cellules)
		self._compter()

	def _filtrer(self, texte: str) -> None:
		self.proxy.filtrer(texte)
		self._compter()

	def _compter(self) -> None:
		total = self.modele.rowCount()
		visibles = self.proxy.rowCount()
		if self.filtre.text() != "":
			texte = f"{visibles} {self._mot(visibles)} sur {total}"
		elif total == 0:
			texte = self.source.aucun
		else:
			texte = f"{total} {self._mot(total)}"
		# Les lignes en anomalie parmi celles que montre le filtre.
		anomalies = sum(
			1 for rangee in range(visibles) if self.proxy.index(rangee, 0).data(Qt.ItemDataRole.ToolTipRole)
		)
		if anomalies > 0:
			texte = f"{texte}, dont {anomalies} en anomalie"
		self.compte.setText(texte)

	def _mot(self, nombre: int) -> str:
		if nombre > 1:
			return self.source.pluriel
		return self.source.singulier

	def selection(self) -> list[int]:
		"""Les éléments des lignes sélectionnées, dans l'ordre de la liste affichée."""
		rangees = sorted(index.row() for index in self.table.selectionModel().selectedRows())
		return [self._element(self.proxy.index(rangee, 0)) for rangee in rangees]

	def _element(self, index: QModelIndex) -> int:
		premiere = self.modele.index(self.proxy.mapToSource(index).row(), 0)
		return int(premiere.data(IDENTIFIANT))

	def menu_de_la_ligne(self, index: QModelIndex) -> QMenu | None:
		"""Le menu du clic droit sur cette ligne de la table : sur la sélection si elle en fait partie, sur elle seule
		sinon ; aucun hors d'une ligne, ou pour une liste sans actions. « Dupliquer » ne vaut que pour un élément."""
		if (not index.isValid()) or ((not self.duplicable) and (self.actions_groupees == ())):
			return None
		cliquee = self._element(index)
		elements = self.selection()
		if cliquee not in elements:
			elements = [cliquee]
		menu = QMenu(self)
		if (self.duplicable) and (len(elements) == 1):
			dupliquer = menu.addAction("Dupliquer")
			dupliquer.triggered.connect(lambda: self.duplication_demandee.emit(self.source.genre, cliquee))
		for action in self.actions_groupees:
			entree = menu.addAction(action.texte)
			entree.triggered.connect(lambda _coche=False, cle=action.cle: self.action_demandee.emit(cle, elements))
		return menu

	def _menu(self, position: QPoint) -> None:
		menu = self.menu_de_la_ligne(self.table.indexAt(position))
		if menu is not None:
			menu.exec(self.table.viewport().mapToGlobal(position))
			menu.deleteLater()

	def _ouvrir(self, index: QModelIndex) -> None:
		premiere = self.modele.index(self.proxy.mapToSource(index).row(), 0)
		self.ouverte.emit(self.source.genre, int(premiere.data(IDENTIFIANT)), str(premiere.data(IDENTIFIANT + 1)))
