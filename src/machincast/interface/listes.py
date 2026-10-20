"""Listes filtrables des sonores, des banques, des séquences et des événements
(https://github.com/dascritch/machincast/issues/26, spec § 8.2).

Chaque liste est un onglet de la fenêtre (machincast.interface.fenetre). Elle se lit en base avec le rôle de
l'interface, chaque fois que son onglet s'ouvre : jamais en boucle. Le filtre garde les lignes dont une colonne contient
le texte tapé, sans tenir compte des majuscules ni des accents. Ouvrir une ligne (double-clic ou Entrée) demande
l'écran de détail de l'élément (signal ouverte). Une liste peut avoir un bouton qui crée un élément
(signal creation_demandee) : « Nouvelle banque » (https://github.com/dascritch/machincast/issues/31). Une ligne en
anomalie, une séquence ou un événement vide, a l'icône d'avertissement, une infobulle qui l'explique, et le compte les
dénombre (https://github.com/dascritch/machincast/issues/138, https://github.com/dascritch/machincast/issues/140).
"""

import logging
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QHeaderView, QLabel, QLineEdit, QStyle, QTableView, QWidget

from machincast.interface import affichage
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
			"SELECT s.id, s.artiste, s.titre, s.type::text, s.etat::text, s.duree,"
			" COALESCE(s.emplacement, s.url_stream, m.url)"
			" FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id"
			" ORDER BY s.artiste NULLS LAST, s.titre, s.id"
		).fetchall()
	lignes = []
	for identifiant, artiste, titre, type_sonore, etat, duree, emplacement in rangees:
		texte_duree = ""
		if type_sonore == "stream":
			texte_duree = affichage.duree(None)
		elif isinstance(duree, timedelta):
			texte_duree = affichage.duree(duree)
		cellules = [_texte(artiste), _texte(titre), str(type_sonore), ETATS.get(str(etat), str(etat))]
		cellules += [texte_duree, _texte(emplacement)]
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
)
SEQUENCES = Source(
	"séquence",
	("Nom", "Nom public", "Anomalie"),
	lire_sequences,
	"séquence",
	"séquences",
	"aucune séquence",
	"Nouvelle séquence",
)
EVENEMENTS = Source(
	"événement",
	("Nom", "Nom public", "Priorité", "Début", "Fin", "Récurrence", "Anomalie"),
	lire_evenements,
	"événement",
	"événements",
	"aucun événement",
	"Nouvel événement",
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

	def __init__(
		self, source: Source, connexion: Connexion, parent: QWidget | None = None, actions: bool = True
	) -> None:
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
		entete.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
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
				cellules[0].setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning))
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

	def _ouvrir(self, index: QModelIndex) -> None:
		premiere = self.modele.index(self.proxy.mapToSource(index).row(), 0)
		self.ouverte.emit(self.source.genre, int(premiere.data(IDENTIFIANT)), str(premiere.data(IDENTIFIANT + 1)))
