"""Écran des incidents (https://github.com/dascritch/machincast/issues/35, spec § 8.6).

Les entrées du log que Machin lecture a notées, du plus récent au plus ancien : par défaut les alertes et les
incidents, les informations sur demande ; seules les LIMITE plus récentes sont lues. Chaque entrée donne son horaire,
son niveau, sa nature, son message, et ce qu'elle concerne : sonore, banque, événement, quand c'est renseigné. Un
double-clic sur l'un d'eux demande sa fiche (ouverte) ; un élément supprimé depuis laisse sa cellule vide, l'entrée
garde son message. Comme une liste (machincast.interface.listes), l'écran se relit à l'ouverture de son onglet, et se
filtre sans tenir compte des majuscules ni des accents.

L'indexeur n'écrit pas dans le log : ses anomalies n'y figurent pas.
"""

import logging
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QHeaderView, QTableView, QWidget

from machincast.interface import affichage
from machincast.interface.listes import FiltreSansAccents
from machincast.interface.ui.incidents import Ui_EcranIncidents

journal = logging.getLogger(__name__)

LIMITE = 500
"""Nombre d'entrées lues au plus, les plus récentes."""
COLONNES = ("Horaire", "Niveau", "Nature", "Message", "Sonore", "Banque", "Événement")
LIENS = {4: "sonore", 5: "banque", 6: "événement"}
"""Colonnes qui désignent un élément, et son genre."""
ELEMENT = Qt.ItemDataRole.UserRole
"""Rôle qui porte l'identifiant de l'élément d'une cellule de lien."""


class EcranIncidents(QWidget):
	ouverte = Signal(str, int, str)
	"""Élément ouvert depuis une entrée : genre, identifiant et nom."""

	def __init__(self, connexion: psycopg.Connection[TupleRow], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.connexion = connexion
		self.ui = Ui_EcranIncidents()
		self.ui.setupUi(self)
		self.modele = QStandardItemModel(0, len(COLONNES), self)
		self.modele.setHorizontalHeaderLabels(list(COLONNES))
		self.proxy = FiltreSansAccents(self)
		self.proxy.setSourceModel(self.modele)
		self.table.setModel(self.proxy)
		self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		self._limite_atteinte = False
		self.ui.filtre.textChanged.connect(self._filtrer)
		self.ui.informations.toggled.connect(self.actualiser)
		self.table.activated.connect(self._ouvrir)
		self._compter()

	@property
	def table(self) -> QTableView:
		return self.ui.table

	def actualiser(self) -> None:
		"""Relit le log ; une base injoignable laisse l'écran tel qu'il était."""
		niveaux = ["alerte", "incident"]
		if self.ui.informations.isChecked():
			niveaux.append("info")
		try:
			with self.connexion.transaction():
				rangees = self.connexion.execute(
					"SELECT l.horodatage, l.niveau::text, l.nature, l.message, s.id, s.artiste, s.titre, s.emplacement,"
					" COALESCE(s.url_stream, m.url), b.id, b.nom_interne, e.id, e.nom_interne FROM log l"
					" LEFT JOIN sonores s ON s.id = l.sonore_id"
					" LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id"
					" LEFT JOIN banques b ON b.id = l.banque_id LEFT JOIN evenements e ON e.id = l.evenement_id"
					" WHERE l.niveau::text = ANY(%s) ORDER BY l.horodatage DESC, l.id DESC LIMIT %s",
					(niveaux, LIMITE),
				).fetchall()
		except psycopg.Error as erreur:
			journal.error(f"écran des incidents illisible : {erreur}")
			return
		self.modele.setRowCount(0)
		for horodatage, niveau, nature, message, *references in rangees:
			sonore, artiste, titre, emplacement, adresse, banque, nom_banque, evenement, nom_evenement = references
			assert isinstance(horodatage, datetime)
			cellules = [
				QStandardItem(f"{horodatage.astimezone():%Y-%m-%d %H:%M:%S}"),
				QStandardItem(str(niveau)),
				QStandardItem(str(nature)),
				QStandardItem(str(message)),
				_lien(sonore, affichage.nom_du_sonore(artiste, titre, emplacement, adresse)),
				_lien(banque, str(nom_banque)),
				_lien(evenement, str(nom_evenement)),
			]
			self.modele.appendRow(cellules)
		self._limite_atteinte = len(rangees) == LIMITE
		self._compter()

	def _filtrer(self, texte: str) -> None:
		self.proxy.filtrer(texte)
		self._compter()

	def _compter(self) -> None:
		total = self.modele.rowCount()
		visibles = self.proxy.rowCount()
		texte = f"{total} {_entrees(total)}"
		if total == 0:
			texte = "aucune entrée"
		elif self.ui.filtre.text() != "":
			texte = f"{visibles} {_entrees(visibles)} sur {total}"
		elif self._limite_atteinte:
			texte = f"{texte}, les plus récentes"
		self.ui.compte.setText(texte)

	def _ouvrir(self, index: QModelIndex) -> None:
		"""Un double-clic sur un lien demande la fiche de son élément ; ailleurs, il ne fait rien."""
		# Seule une cellule de lien porte un élément.
		identifiant = index.data(ELEMENT)
		if identifiant is not None:
			self.ouverte.emit(LIENS[index.column()], int(identifiant), str(index.data()))


def _lien(identifiant: object, nom: str) -> QStandardItem:
	"""La cellule d'un élément ; vide quand l'entrée n'en désigne pas, ou plus."""
	if identifiant is None:
		return QStandardItem("")
	cellule = QStandardItem(nom)
	cellule.setData(int(str(identifiant)), ELEMENT)
	return cellule


def _entrees(nombre: int) -> str:
	if nombre > 1:
		return "entrées"
	return "entrée"
