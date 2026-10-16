"""Fenêtre de Machin_interface (https://github.com/dascritch/machincast/issues/26).

Un onglet par écran : l'accueil (écran par défaut, ouvert au lancement), puis une liste par type d'élément, dans
l'ordre de la recherche (spec § 8.2) : événements, séquences, banques, sonores. Ces onglets ne se ferment pas. Une liste
se relit chaque fois que son onglet s'ouvre. Ouvrir une ligne demande l'écran de détail de l'élément (detail_demande).

L'écran de détail d'une banque est sa fiche (machincast.interface.fiche_banque,
https://github.com/dascritch/machincast/issues/31), dans un onglet qui se ferme ; une fiche déjà ouverte revient au
premier plan. Une fiche modifiée demande quoi faire de ses modifications avant de se fermer, avec son onglet ou avec la
fenêtre. Tant que les autres écrans de détail n'existent pas, la barre d'état les annonce, avec leur ticket.
"""

from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QTabBar, QWidget

from machincast.horloge import Horloge
from machincast.interface.ecran_par_defaut import EcranParDefaut
from machincast.interface.fiche_banque import FicheBanque
from machincast.interface.listes import BANQUES, EVENEMENTS, SEQUENCES, SONORES, Liste
from machincast.interface.ui.fenetre_principale import Ui_FenetrePrincipale

ONGLETS = (("Événements", EVENEMENTS), ("Séquences", SEQUENCES), ("Banques", BANQUES), ("Sonores", SONORES))
DETAILS = {
	"sonore": ("du sonore", "https://github.com/dascritch/machincast/issues/28"),
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
		self.connexion = connexion
		self.ui = Ui_FenetrePrincipale()
		self.ui.setupUi(self)
		self.ui.onglets.setTabsClosable(True)
		self.accueil = EcranParDefaut(connexion, socket_etat, horloge)
		self._ajouter_fixe(self.accueil, "Accueil")
		self.listes: list[Liste] = []
		for titre, source in ONGLETS:
			liste = Liste(source, connexion)
			liste.ouverte.connect(self._ouvrir)
			liste.creation_demandee.connect(lambda _genre: self._ouvrir_fiche(None))
			self.listes.append(liste)
			self._ajouter_fixe(liste, titre)
		self.ui.onglets.setCurrentIndex(0)
		self.ui.onglets.currentChanged.connect(self._onglet_ouvert)
		self.ui.onglets.tabCloseRequested.connect(self._fermer)

	def fiches(self) -> list[FicheBanque]:
		onglets = self.ui.onglets
		return [fiche for indice in range(onglets.count()) if isinstance(fiche := onglets.widget(indice), FicheBanque)]

	def closeEvent(self, evenement: QCloseEvent) -> None:
		for fiche in self.fiches():
			if not fiche.peut_fermer():
				evenement.ignore()
				return
		self.accueil.close()
		super().closeEvent(evenement)

	def _ajouter_fixe(self, ecran: QWidget, titre: str) -> None:
		"""Un onglet sans bouton de fermeture."""
		indice = self.ui.onglets.addTab(ecran, titre)
		for cote in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
			self.ui.onglets.tabBar().setTabButton(indice, cote, None)

	def _ouvrir_fiche(self, identifiant: int | None) -> None:
		"""Ouvre la fiche d'une banque, ou ramène au premier plan celle déjà ouverte ; None pour une nouvelle."""
		for ouverte in self.fiches():
			if (identifiant is not None) and (ouverte.identifiant == identifiant):
				self.ui.onglets.setCurrentWidget(ouverte)
				return
		fiche = FicheBanque(self.connexion, identifiant)
		fiche.titre_change.connect(lambda titre: self._renommer(fiche, titre))
		self.ui.onglets.addTab(fiche, fiche.titre())
		self.ui.onglets.setCurrentWidget(fiche)

	def _renommer(self, fiche: QWidget, titre: str) -> None:
		self.ui.onglets.setTabText(self.ui.onglets.indexOf(fiche), titre)

	def _fermer(self, indice: int) -> None:
		fiche = self.ui.onglets.widget(indice)
		assert isinstance(fiche, FicheBanque), fiche
		if fiche.peut_fermer():
			self.ui.onglets.removeTab(indice)
			fiche.deleteLater()

	def _onglet_ouvert(self, indice: int) -> None:
		ouvert = self.ui.onglets.widget(indice)
		if isinstance(ouvert, Liste):
			ouvert.actualiser()

	def _ouvrir(self, genre: str, identifiant: int, nom: str) -> None:
		self.detail_demande.emit(genre, identifiant)
		if genre == "banque":
			self._ouvrir_fiche(identifiant)
			return
		article, ticket = DETAILS[genre]
		message = f"Écran de détails {article} « {nom} » : à venir"
		if ticket is not None:
			message = f"{message}, {ticket}"
		self.ui.barre_d_etat.showMessage(message)
