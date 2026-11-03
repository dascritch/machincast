"""Dépôt de fichiers et de dossiers glissés depuis le navigateur de fichiers du poste
(https://github.com/dascritch/machincast/issues/31).

Un filtre d'événements posé sur la zone d'une liste (son viewport) : il accepte les chemins locaux glissés depuis une
autre application, et les donne par le signal deposes. Les autres glisser-déposer, comme le déplacement d'une ligne
dans sa liste, lui passent à travers.

Un dépôt est toujours une **copie** : accepté comme un déplacement, il laisserait le navigateur de fichiers supprimer
l'original. Un glisser qui ne propose pas la copie est refusé (https://github.com/dascritch/machincast/issues/96).
"""

from pathlib import Path

from PySide6.QtCore import QEvent, QMimeData, QObject, Qt, Signal
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QAbstractItemView


def local_paths(data: QMimeData) -> list[Path]:
	"""Les fichiers et dossiers locaux d'un glisser, dans l'ordre ; aucun pour un glisser venu d'une liste."""
	return [Path(address.toLocalFile()) for address in data.urls() if address.isLocalFile()]


class FileDrop(QObject):
	dropped = Signal(list)
	"""Chemins déposés (list[Path]), dans l'ordre du glisser."""

	def __init__(self, list_: QAbstractItemView) -> None:
		super().__init__(list_)
		self.list_ = list_
		list_.viewport().installEventFilter(self)
		self.accept()

	def accept(self) -> None:
		"""La liste et sa zone acceptent les dépôts ; à rappeler après un changement de mode de glisser-déposer."""
		self.list_.setAcceptDrops(True)

	def eventFilter(self, object_: QObject, event: QEvent) -> bool:
		# Le glisser qui entre, qui passe et qui se dépose ; la sortie d'un glisser n'est pas un QDropEvent.
		if not isinstance(event, QDropEvent):
			return False
		paths = local_paths(event.mimeData())
		if paths == []:
			return False
		if not (event.possibleActions() & Qt.DropAction.CopyAction):
			# Refusé : un QDropEvent naît ignoré.
			return True
		event.setDropAction(Qt.DropAction.CopyAction)
		event.accept()
		if event.type() == QEvent.Type.Drop:
			self.dropped.emit(paths)
		return True
