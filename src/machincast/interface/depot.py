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


def chemins_locaux(donnees: QMimeData) -> list[Path]:
	"""Les fichiers et dossiers locaux d'un glisser, dans l'ordre ; aucun pour un glisser venu d'une liste."""
	return [Path(adresse.toLocalFile()) for adresse in donnees.urls() if adresse.isLocalFile()]


class DepotDeFichiers(QObject):
	deposes = Signal(list)
	"""Chemins déposés (list[Path]), dans l'ordre du glisser."""

	def __init__(self, liste: QAbstractItemView) -> None:
		super().__init__(liste)
		self.liste = liste
		liste.viewport().installEventFilter(self)
		self.accepter()

	def accepter(self) -> None:
		"""La liste et sa zone acceptent les dépôts ; à rappeler après un changement de mode de glisser-déposer."""
		self.liste.setAcceptDrops(True)

	def eventFilter(self, objet: QObject, evenement: QEvent) -> bool:
		# Le glisser qui entre, qui passe et qui se dépose ; la sortie d'un glisser n'est pas un QDropEvent.
		if not isinstance(evenement, QDropEvent):
			return False
		chemins = chemins_locaux(evenement.mimeData())
		if chemins == []:
			return False
		if not (evenement.possibleActions() & Qt.DropAction.CopyAction):
			# Refusé : un QDropEvent naît ignoré.
			return True
		evenement.setDropAction(Qt.DropAction.CopyAction)
		evenement.accept()
		if evenement.type() == QEvent.Type.Drop:
			self.deposes.emit(chemins)
		return True
