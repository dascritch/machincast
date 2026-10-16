"""Fenêtre de Machin_interface (https://github.com/dascritch/machincast/issues/26).

Un onglet par écran : l'accueil (écran par défaut, ouvert au lancement), puis une liste par type d'élément, dans
l'ordre de la recherche (spec § 8.2) : événements, séquences, banques, sonores. Une liste se relit chaque fois que son
onglet s'ouvre. Ouvrir une ligne demande l'écran de détail de l'élément (detail_demande) ; tant que ces écrans
n'existent pas, la barre d'état l'annonce, avec son ticket.
"""

from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QWidget

from machincast.horloge import Horloge
from machincast.interface.ecran_par_defaut import EcranParDefaut
from machincast.interface.listes import BANQUES, EVENEMENTS, SEQUENCES, SONORES, Liste
from machincast.interface.ui.fenetre_principale import Ui_FenetrePrincipale

ONGLETS = (("Événements", EVENEMENTS), ("Séquences", SEQUENCES), ("Banques", BANQUES), ("Sonores", SONORES))
DETAILS = {
	"sonore": ("du sonore", "https://github.com/dascritch/machincast/issues/28"),
	"banque": ("de la banque", "https://github.com/dascritch/machincast/issues/31"),
	"séquence": ("de la séquence", None),
	"événement": ("de l'événement", "https://github.com/dascritch/machincast/issues/32"),
}
"""Écrans de détail encore à venir, avec leur ticket."""


class FenetrePrincipale(QMainWindow):
	detail_demande = Signal(str, int)
	"""Écran de détail demandé : genre et identifiant de l'élément."""

	def __init__(
		self,
		connexion: psycopg.Connection[TupleRow],
		socket_etat: Path,
		horloge: Horloge,
		parent: QWidget | None = None,
	) -> None:
		super().__init__(parent)
		self.ui = Ui_FenetrePrincipale()
		self.ui.setupUi(self)
		self.accueil = EcranParDefaut(connexion, socket_etat, horloge)
		self.ui.onglets.addTab(self.accueil, "Accueil")
		self.listes: list[Liste] = []
		for titre, source in ONGLETS:
			liste = Liste(source, connexion)
			liste.ouverte.connect(self._ouvrir)
			self.listes.append(liste)
			self.ui.onglets.addTab(liste, titre)
		self.ui.onglets.setCurrentIndex(0)
		self.ui.onglets.currentChanged.connect(self._onglet_ouvert)

	def closeEvent(self, evenement: QCloseEvent) -> None:
		self.accueil.close()
		super().closeEvent(evenement)

	def _onglet_ouvert(self, indice: int) -> None:
		ouvert = self.ui.onglets.widget(indice)
		if isinstance(ouvert, Liste):
			ouvert.actualiser()

	def _ouvrir(self, genre: str, identifiant: int, nom: str) -> None:
		self.detail_demande.emit(genre, identifiant)
		article, ticket = DETAILS[genre]
		message = f"Écran de détails {article} « {nom} » : à venir"
		if ticket is not None:
			message = f"{message}, {ticket}"
		self.ui.barre_d_etat.showMessage(message)
