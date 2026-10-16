"""Choix de sonores déjà en base, pour les ajouter à une banque (https://github.com/dascritch/machincast/issues/31).

La liste filtrable des sonores (machincast.interface.listes), où plusieurs lignes se sélectionnent à la fois ; ouvrir
une ligne (double-clic ou Entrée) la choisit et valide. L'ajout de nouveaux fichiers est l'affaire de
https://github.com/dascritch/machincast/issues/30.
"""

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QWidget

from machincast.interface.listes import IDENTIFIANT, SONORES, Liste
from machincast.interface.ui.choix_sonores import Ui_ChoixSonores


class ChoixSonores(QDialog):
	def __init__(self, connexion: psycopg.Connection[TupleRow], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.ui = Ui_ChoixSonores()
		self.ui.setupUi(self)
		self.liste = Liste(SONORES, connexion, self)
		self.liste.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		self.ui.disposition.insertWidget(1, self.liste)
		self.ui.boutons.button(QDialogButtonBox.StandardButton.Ok).setText("Ajouter")
		self.ui.boutons.accepted.connect(self.accept)
		self.ui.boutons.rejected.connect(self.reject)
		self.liste.ouverte.connect(self.accept)
		self.liste.actualiser()

	def selection(self) -> list[int]:
		"""Les sonores sélectionnés, dans l'ordre de la liste affichée."""
		rangees = sorted(index.row() for index in self.liste.table.selectionModel().selectedRows())
		modele = self.liste.table.model()
		return [int(modele.index(rangee, 0).data(IDENTIFIANT)) for rangee in rangees]
