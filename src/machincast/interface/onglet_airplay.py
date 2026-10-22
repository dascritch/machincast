"""Onglet Airplay (https://github.com/dascritch/machincast/issues/244, spec § 8.1).

L'historique de diffusion, dans un onglet à part, fermé au lancement, que le menu « Affichage » ouvre
(FenetrePrincipale._ouvrir_airplay). Il montre les passages des dernières heures, du plus récent au plus ancien, avec
les colonnes de l'airplay de l'accueil (EcranParDefaut.COLONNES_AIRPLAY). Le nombre d'heures se règle en haut de
l'onglet, de 1 à HEURES_AU_PLUS ; il est retenu pour le compte, dans les réglages des vues
(machincast.interface.colonnes). Comme dans l'accueil, un double-clic demande la fiche du sonore, de l'événement, de
la séquence ou de la banque (ouverte), et le clic droit sur une ligne propose « Pré-écoute… » de son sonore
(preecoute_demandee).

« Exporter… » enregistre ce que l'onglet montre, relu en base, en CSV, en HTML ou en M3U
(machincast.interface.export_airplay), selon le filtre choisi dans le sélecteur de fichier (dialogues.choisir_export).
Le nom reçoit l'extension du format s'il ne l'a pas déjà : un export ne remplace jamais un fichier sonore
(https://github.com/dascritch/machincast/issues/96, machincast.protection). La barre d'état de la fenêtre dit où
l'export est enregistré (annonce).

L'onglet se relit à son ouverture, à chaque réglage, et quand l'accueil voit un nouveau sonore (actualiser) : jamais en
boucle.
"""

import logging
from datetime import timedelta

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
	QAbstractItemView,
	QHBoxLayout,
	QLabel,
	QMenu,
	QPushButton,
	QSpinBox,
	QTableView,
	QVBoxLayout,
	QWidget,
)

from machincast.configuration import Metadonnees
from machincast.horloge import Horloge
from machincast.interface import affichage, colonnes, dialogues
from machincast.interface.airplay import HEURES, lire_airplay
from machincast.interface.colonnes import Colonnes
from machincast.interface.ecran_par_defaut import ELEMENT, EcranParDefaut, cellules_du_passage, elements_du_passage
from machincast.interface.export_airplay import FORMATS, en_csv, en_html, en_m3u
from machincast.interface.simulation import avec_extension
from machincast.lecture.sorties import lire_passages
from machincast.protection import verifier_ecriture

journal = logging.getLogger(__name__)

HEURES_AU_PLUS = 24 * 31
"""Le plus grand nombre d'heures que l'onglet propose : un mois."""
REGLAGE_DES_HEURES = "onglet-airplay/heures"
"""Dans les réglages des vues du compte : le nombre d'heures montré."""
SANS_METADONNEES = Metadonnees(masquer=False, texte_public="")


def heures_retenues() -> int:
	valeur = colonnes.reglages().value(REGLAGE_DES_HEURES)
	try:
		heures = int(str(valeur))
	except ValueError:
		return HEURES
	return min(HEURES_AU_PLUS, max(1, heures))


class EcranAirplay(QWidget):
	ouverte = Signal(str, int, str)
	"""Fiche demandée : genre, identifiant et nom de l'élément."""
	preecoute_demandee = Signal(int)
	"""« Pré-écoute… » choisi au clic droit sur une ligne : son sonore."""
	annonce = Signal(str)
	"""Ce que la barre d'état de la fenêtre dit d'un export."""
	COLONNES = EcranParDefaut.COLONNES_AIRPLAY

	def __init__(
		self,
		connexion: psycopg.Connection[TupleRow],
		horloge: Horloge,
		metadonnees: Metadonnees = SANS_METADONNEES,
		parent: QWidget | None = None,
	) -> None:
		"""metadonnees : le masquage et le texte public de la configuration, pour le texte public des exports."""
		super().__init__(parent)
		self.connexion = connexion
		self.horloge = horloge
		self.metadonnees = metadonnees
		self.heures = QSpinBox(self)
		self.heures.setObjectName("heures")
		self.heures.setRange(1, HEURES_AU_PLUS)
		self.heures.setSuffix(" h")
		self.heures.setValue(heures_retenues())
		self.heures.setToolTip(
			"Les passages commencés depuis ce nombre d'heures ; retenu pour les prochaines ouvertures"
		)
		etiquette = QLabel("&Dernières heures", self)
		etiquette.setBuddy(self.heures)
		self.exporter = QPushButton("&Exporter…", self)
		self.exporter.setToolTip("Enregistrer ce que l'onglet montre, en CSV, en HTML ou en M3U")
		self.table = QTableView(self)
		self.table.setObjectName("table_airplay")
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setAlternatingRowColors(True)
		self.table.verticalHeader().setVisible(False)
		self.table.horizontalHeader().setStretchLastSection(True)
		self.table.setToolTip("Double-clic sur un sonore, un événement, une séquence ou une banque : ouvrir sa fiche")
		self.modele = QStandardItemModel(0, len(self.COLONNES), self)
		self.modele.setHorizontalHeaderLabels([titre for _, titre in self.COLONNES])
		self.table.setModel(self.modele)
		self.colonnes = Colonnes(self.table, "onglet-airplay")
		haut = QHBoxLayout()
		haut.addWidget(etiquette)
		haut.addWidget(self.heures)
		haut.addStretch(1)
		haut.addWidget(self.exporter)
		disposition = QVBoxLayout(self)
		disposition.addLayout(haut)
		disposition.addWidget(self.table, 1)
		self.heures.valueChanged.connect(self._regler)
		self.exporter.clicked.connect(self._exporter)
		self.table.activated.connect(self._ouvrir_cellule)
		self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.table.customContextMenuRequested.connect(self._menu)
		self.actualiser()

	def actualiser(self) -> None:
		"""Relit les passages ; une base injoignable laisse la table telle qu'elle était."""
		try:
			passages = lire_airplay(self.connexion, self.horloge.maintenant() - timedelta(hours=self.heures.value()))
		except psycopg.Error as erreur:
			journal.error(f"airplay illisible : {erreur}")
			return
		self.modele.setRowCount(0)
		for passage in passages:
			cellules = [QStandardItem(texte) for texte in cellules_du_passage(passage)]
			for colonne, element in elements_du_passage(passage).items():
				cellules[colonne].setData(element, ELEMENT)
			self.modele.appendRow(cellules)

	def _regler(self, heures: int) -> None:
		colonnes.reglages().setValue(REGLAGE_DES_HEURES, heures)
		self.actualiser()

	def _ouvrir_cellule(self, index: QModelIndex) -> None:
		element = index.data(ELEMENT)
		if element is not None:
			genre, identifiant, nom = element
			self.ouverte.emit(genre, identifiant, nom)

	def menu_de_la_ligne(self, index: QModelIndex) -> QMenu | None:
		"""« Pré-écoute… » du sonore de la ligne ; aucun menu hors d'une ligne, ou pour un sonore supprimé depuis."""
		if not index.isValid():
			return None
		sonore = None
		for colonne in range(self.modele.columnCount()):
			element = self.modele.index(index.row(), colonne).data(ELEMENT)
			if (element is not None) and (element[0] == "sonore"):
				sonore = int(element[1])
		if sonore is None:
			return None
		menu = QMenu(self)
		affichage.proposer_la_preecoute(menu, sonore, self.preecoute_demandee.emit)
		return menu

	def _menu(self, position: QPoint) -> None:
		menu = self.menu_de_la_ligne(self.table.indexAt(position))
		if menu is not None:
			menu.exec(self.table.viewport().mapToGlobal(position))
			menu.deleteLater()

	def _exporter(self) -> None:
		maintenant = self.horloge.maintenant()
		heures = self.heures.value()
		propose = f"airplay-{maintenant.astimezone():%Y-%m-%d-%H%M}-{heures}h.csv"
		choix = dialogues.choisir_export(self, propose, list(FORMATS), "Exporter l'airplay")
		if choix is None:
			return
		chemin, filtre = choix
		extension = FORMATS[filtre]
		destination = avec_extension(chemin, extension)
		try:
			lignes = lire_passages(self.connexion, None, depuis=maintenant - timedelta(hours=heures))
			titre = f"Airplay des {heures} dernières heures, au {maintenant.astimezone():%d/%m/%Y %H:%M}"
			contenus = {
				".csv": lambda: en_csv(lignes, self.metadonnees),
				".html": lambda: en_html(lignes, self.metadonnees, titre, maintenant),
				".m3u": lambda: en_m3u(lignes, self.metadonnees),
			}
			contenu = contenus[extension]()
			verifier_ecriture(destination)
			# Le BOM laisse les tableurs reconnaître l'UTF-8 du CSV.
			encodage = "utf-8-sig" if extension == ".csv" else "utf-8"
			destination.write_text(contenu, encoding=encodage, newline="")
		except (OSError, psycopg.Error) as erreur:
			self.annonce.emit(f"Export impossible : {erreur}")
			return
		self.annonce.emit(f"Airplay exporté dans {destination}.")
