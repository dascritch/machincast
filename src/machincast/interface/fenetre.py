"""Fenêtre de Machin_interface (https://github.com/dascritch/machincast/issues/26).

Un onglet par écran : l'accueil (écran par défaut, ouvert au lancement), puis une liste par type d'élément, dans
l'ordre de la recherche (spec § 8.2) : événements, séquences, banques, sonores. Ces onglets ne se ferment pas. Une liste
se relit chaque fois que son onglet s'ouvre. Ouvrir une ligne demande l'écran de détail de l'élément (detail_demande).

L'écran de détail d'un élément est sa fiche, dans un onglet qui se ferme : événement
(machincast.interface.fiche_evenement, https://github.com/dascritch/machincast/issues/32), séquence
(machincast.interface.fiche_sequence, https://github.com/dascritch/machincast/issues/112), banque
(machincast.interface.fiche_banque, https://github.com/dascritch/machincast/issues/31) ou sonore
(machincast.interface.fiche_sonore, https://github.com/dascritch/machincast/issues/28). Une fiche déjà ouverte
revient au premier plan. Un élément cité par une fiche s'ouvre comme une ligne de liste. Une fiche modifiée demande
quoi faire de ses modifications avant de se fermer, avec son onglet ou avec la fenêtre.

Les fichiers ajoutés depuis la liste des sonores entrent en base (machincast.interface.ajout), puis l'indexeur les
vérifie en tâche de fond (machincast.interface.verification, https://github.com/dascritch/machincast/issues/30) ; la
barre d'état annonce l'un et l'autre.
"""

import logging
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QTabBar, QWidget

from machincast.horloge import Horloge
from machincast.interface import dialogues
from machincast.interface.ajout import ajouter_fichiers
from machincast.interface.ecran_par_defaut import EcranParDefaut
from machincast.interface.fiche import Fiche
from machincast.interface.fiche_banque import FicheBanque
from machincast.interface.fiche_evenement import FicheEvenement
from machincast.interface.fiche_sequence import FicheSequence
from machincast.interface.fiche_sonore import FicheSonore
from machincast.interface.listes import BANQUES, EVENEMENTS, SEQUENCES, SONORES, Liste
from machincast.interface.ui.fenetre_principale import Ui_FenetrePrincipale
from machincast.interface.verification import Verificateur

journal = logging.getLogger(__name__)

ONGLETS = (("Événements", EVENEMENTS), ("Séquences", SEQUENCES), ("Banques", BANQUES), ("Sonores", SONORES))
FICHES: dict[str, type[Fiche]] = {
	fiche.genre: fiche for fiche in (FicheEvenement, FicheSequence, FicheBanque, FicheSonore)
}
"""Écrans de détail : les fiches, par genre."""


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
		self.horloge = horloge
		self.ui = Ui_FenetrePrincipale()
		self.ui.setupUi(self)
		self.ui.onglets.setTabsClosable(True)
		self.accueil = EcranParDefaut(connexion, socket_etat, horloge)
		self._ajouter_fixe(self.accueil, "Accueil")
		self.verificateur = Verificateur(connexion, self)
		self.verificateur.termine.connect(self._verification_terminee)
		self.listes: list[Liste] = []
		for titre, source in ONGLETS:
			liste = Liste(source, connexion)
			liste.ouverte.connect(self._ouvrir)
			liste.creation_demandee.connect(lambda genre: self._ouvrir_fiche(genre, None))
			liste.ajout_demande.connect(
				lambda liste=liste: self._ajouter_fichiers(liste, dialogues.choisir_fichiers(self))
			)
			liste.fichiers_deposes.connect(lambda chemins, liste=liste: self._ajouter_fichiers(liste, chemins))
			self.listes.append(liste)
			self._ajouter_fixe(liste, titre)
		self.ui.onglets.setCurrentIndex(0)
		self.ui.onglets.currentChanged.connect(self._onglet_ouvert)
		self.ui.onglets.tabCloseRequested.connect(self._fermer)

	def fiches(self) -> list[Fiche]:
		onglets = self.ui.onglets
		return [fiche for indice in range(onglets.count()) if isinstance(fiche := onglets.widget(indice), Fiche)]

	def closeEvent(self, evenement: QCloseEvent) -> None:
		for fiche in self.fiches():
			if not fiche.peut_fermer():
				evenement.ignore()
				return
		for fiche in self.fiches():
			fiche.fermer()
		self.verificateur.arreter()
		self.accueil.close()
		super().closeEvent(evenement)

	def _ajouter_fixe(self, ecran: QWidget, titre: str) -> None:
		"""Un onglet sans bouton de fermeture."""
		indice = self.ui.onglets.addTab(ecran, titre)
		for cote in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
			self.ui.onglets.tabBar().setTabButton(indice, cote, None)

	def _ouvrir_fiche(self, genre: str, identifiant: int | None) -> None:
		"""Ouvre la fiche d'un élément, ou ramène au premier plan celle déjà ouverte ; None pour un nouvel élément."""
		for ouverte in self.fiches():
			if (identifiant is not None) and (ouverte.genre == genre) and (ouverte.identifiant == identifiant):
				self.ui.onglets.setCurrentWidget(ouverte)
				return
		fiche = FICHES[genre](self.connexion, identifiant, self.horloge)
		fiche.titre_change.connect(lambda titre: self._renommer(fiche, titre))
		fiche.ouverture_demandee.connect(self._ouvrir)
		fiche.supprimee.connect(lambda: self._retirer(fiche))
		self.ui.onglets.addTab(fiche, fiche.titre())
		self.ui.onglets.setCurrentWidget(fiche)

	def _renommer(self, fiche: QWidget, titre: str) -> None:
		self.ui.onglets.setTabText(self.ui.onglets.indexOf(fiche), titre)

	def _fermer(self, indice: int) -> None:
		fiche = self.ui.onglets.widget(indice)
		assert isinstance(fiche, Fiche), fiche
		if fiche.peut_fermer():
			self._retirer(fiche)

	def _retirer(self, fiche: Fiche) -> None:
		"""Ferme l'onglet de la fiche, sans rien lui demander."""
		self.ui.onglets.removeTab(self.ui.onglets.indexOf(fiche))
		fiche.fermer()
		fiche.deleteLater()

	def _ajouter_fichiers(self, liste: Liste, chemins: list[Path]) -> None:
		"""Les fichiers entrent en base à l'état aperçu, puis l'indexeur les vérifie, en tâche de fond."""
		if chemins == []:
			return
		try:
			ajout = ajouter_fichiers(self.connexion, chemins)
		except psycopg.Error as erreur:
			journal.error(f"ajout de fichiers impossible : {erreur}")
			self.ui.barre_d_etat.showMessage(f"Ajout impossible : {erreur}")
			return
		self.ui.barre_d_etat.showMessage(ajout.texte())
		liste.actualiser()
		self.verificateur.verifier(ajout.ajoutes)

	def _verification_terminee(self, texte: str) -> None:
		self.ui.barre_d_etat.showMessage(texte)
		ouvert = self.ui.onglets.currentWidget()
		if isinstance(ouvert, Liste):
			ouvert.actualiser()

	def _onglet_ouvert(self, indice: int) -> None:
		ouvert = self.ui.onglets.widget(indice)
		if isinstance(ouvert, Liste):
			ouvert.actualiser()

	def _ouvrir(self, genre: str, identifiant: int, _nom: str) -> None:
		self.detail_demande.emit(genre, identifiant)
		self._ouvrir_fiche(genre, identifiant)
