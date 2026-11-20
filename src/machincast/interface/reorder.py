"""Monter et descendre les lignes choisies d'une liste à l'ordre réglable (https://github.com/dascritch/machincast/issues/527).

La liste des éléments d'un événement ou d'une séquence (machincast.interface.items) et celle des sonores d'une banque
séquentielle (machincast.interface.bank_card) se réordonnent par « ↥ Monter » et « ↧ Descendre » : toutes les lignes
choisies bougent ensemble, d'un rang, en gardant leur ordre, et restent choisies. Un bloc déjà au bord ne bouge plus.
"""

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

UP = -1
DOWN = 1


def chosen_rows(tree: QTreeWidget) -> list[int]:
	"""Les rangs des lignes choisies, dans l'ordre de la liste."""
	rows = []
	for line in tree.selectedItems():
		rows.append(tree.indexOfTopLevelItem(line))
	rows.sort()
	return rows


def can_move(tree: QTreeWidget, offset: int) -> bool:
	"""Vrai si des lignes sont choisies, et qu'aucune n'est déjà au bord vers lequel elles iraient."""
	rows = chosen_rows(tree)
	if rows == []:
		return False
	if offset == UP:
		return rows[0] > 0
	return rows[-1] < tree.topLevelItemCount() - 1


def move(tree: QTreeWidget, offset: int) -> None:
	"""Les lignes choisies bougent d'un rang, vers le haut (UP) ou le bas (DOWN), et restent choisies."""
	if not can_move(tree, offset):
		return
	rows = chosen_rows(tree)
	if offset == DOWN:
		rows.reverse()
	moved: list[QTreeWidgetItem] = []
	for row in rows:
		line = tree.takeTopLevelItem(row)
		assert line is not None
		tree.insertTopLevelItem(row + offset, line)
		moved.append(line)
	tree.clearSelection()
	for line in moved:
		line.setSelected(True)
	# Rendue courante sans toucher au choix, la dernière ligne déplacée met à jour les boutons (currentItemChanged).
	tree.setCurrentItem(moved[-1], 0, QItemSelectionModel.SelectionFlag.NoUpdate)
	tree.itemSelectionChanged.emit()
