"""Choix d'éléments déjà en base, sonores ou banques, pour les ajouter à une fiche
(https://github.com/dascritch/machincast/issues/31, https://github.com/dascritch/machincast/issues/112).

La liste filtrable de ces éléments (machincast.interface.listes), où plusieurs lignes se sélectionnent à la fois ;
ouvrir une ligne (double-clic ou Entrée) la choisit et valide. L'ajout de nouveaux fichiers est l'affaire de
https://github.com/dascritch/machincast/issues/30.
"""

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QWidget

from machincast.interface.listes import IDENTIFIANT, Liste, Source
from machincast.interface.ui.choix import Ui_Choix


class Choix(QDialog):
	def __init__(
		self,
		source: Source,
		connexion: psycopg.Connection[TupleRow],
		remarque: str = "",
		parent: QWidget | None = None,
	) -> None:
		"""remarque : ce que la fiche fait d'un élément qu'elle a déjà, à la suite de l'explication."""
		super().__init__(parent)
		self.ui = Ui_Choix()
		self.ui.setupUi(self)
		self.setWindowTitle(f"Ajouter des {source.pluriel}")
		explication = f"Choisir parmi les {source.pluriel} déjà en base (Ctrl ou Maj pour en prendre plusieurs)."
		self.ui.explication.setText(f"{explication} {remarque}".strip())
		self.liste = Liste(source, connexion, self)
		self.liste.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		self.ui.disposition.insertWidget(1, self.liste)
		self.ui.boutons.button(QDialogButtonBox.StandardButton.Ok).setText("Ajouter")
		self.ui.boutons.accepted.connect(self.accept)
		self.ui.boutons.rejected.connect(self.reject)
		self.liste.ouverte.connect(self.accept)
		self.liste.actualiser()

	def selection(self) -> list[int]:
		"""Les éléments sélectionnés, dans l'ordre de la liste affichée."""
		rangees = sorted(index.row() for index in self.liste.table.selectionModel().selectedRows())
		modele = self.liste.table.model()
		return [int(modele.index(rangee, 0).data(IDENTIFIANT)) for rangee in rangees]
