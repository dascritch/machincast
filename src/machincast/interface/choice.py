"""Choix d'éléments déjà en base, sonores ou banques, pour les ajouter à une fiche
(https://github.com/dascritch/machincast/issues/31, https://github.com/dascritch/machincast/issues/112).

La liste filtrable de ces éléments (machincast.interface.lists), où plusieurs lignes se sélectionnent à la fois ;
ouvrir une ligne (double-clic ou Entrée) la choisit et valide. L'ajout de nouveaux fichiers est l'affaire de
https://github.com/dascritch/machincast/issues/30.
"""

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QWidget

from machincast.interface.intents import ADD, label
from machincast.interface.lists import IDENTIFIER, List, Source, view_name
from machincast.interface.ui.choice import Ui_Choice


class Choice(QDialog):
	def __init__(
		self,
		source: Source,
		connection: psycopg.Connection[TupleRow],
		remark: str = "",
		parent: QWidget | None = None,
	) -> None:
		"""remarque : ce que la fiche fait d'un élément qu'elle a déjà, à la suite de l'explication."""
		super().__init__(parent)
		self.ui = Ui_Choice()
		self.ui.setupUi(self)
		self.setWindowTitle(f"Ajouter des {source.plural}")
		explanation = f"Choisir parmi les {source.plural} déjà en base (Ctrl ou Maj pour en prendre plusieurs)."
		self.ui.explanation.setText(f"{explanation} {remark}".strip())
		self.list_ = List(source, connection, self, actions=False, view=f"choix-{view_name(source.plural)}")
		self.list_.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
		self.ui.arrangement.insertWidget(1, self.list_)
		self.ui.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(label(ADD, "Ajouter"))
		self.ui.buttons.accepted.connect(self.accept)
		self.ui.buttons.rejected.connect(self.reject)
		self.list_.opened.connect(self.accept)
		self.list_.refresh()

	def selection(self) -> list[int]:
		"""Les éléments sélectionnés, dans l'ordre de la liste affichée."""
		rows = sorted(index.row() for index in self.list_.table.selectionModel().selectedRows())
		model = self.list_.table.model()
		return [int(model.index(row, 0).data(IDENTIFIER)) for row in rows]
