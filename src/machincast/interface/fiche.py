"""Ce qui est commun aux fiches : banque, sonore (https://github.com/dascritch/machincast/issues/31,
https://github.com/dascritch/machincast/issues/28).

Une fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.fenetre). Ses modifications restent dans la fiche
jusqu'à « Enregistrer », qui les écrit en base en une seule transaction, puis relit la fiche ; « Annuler » relit la
fiche sans rien écrire. Les deux boutons ne servent qu'à une fiche modifiée. Une fiche modifiée qui se ferme demande
quoi faire de ses modifications (machincast.interface.dialogues).

Une fiche concrète décrit son genre et son titre, lit l'élément en base (_lire) et l'y écrit (_ecrire). Un refus
(Refus) laisse la fiche modifiée, avec son message.
"""

import logging

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from machincast.horloge import Horloge
from machincast.interface import dialogues
from machincast.interface.dialogues import Fermeture

journal = logging.getLogger(__name__)

Connexion = psycopg.Connection[TupleRow]


class Refus(Exception):
	"""La fiche n'est pas enregistrée : le message dit pourquoi."""


class Fiche(QWidget):
	titre_change = Signal(str)
	"""Le titre de l'onglet de la fiche a changé : à la lecture, et après un enregistrement."""
	enregistree = Signal(int)
	"""L'élément est enregistré : son identifiant en base."""

	genre = ""
	"""Genre de l'élément, celui des listes et de detail_demande : « banque », « sonore »."""
	bouton_enregistrer: QPushButton
	bouton_annuler: QPushButton
	message: QLabel
	"""Ce qui empêche l'enregistrement, ou ce que la fiche a ignoré."""

	def __init__(
		self, connexion: Connexion, identifiant: int | None, horloge: Horloge, parent: QWidget | None = None
	) -> None:
		super().__init__(parent)
		self.connexion = connexion
		self.identifiant = identifiant
		self.horloge = horloge
		self.modifiee = False

	def brancher(self, enregistrer: QPushButton, annuler: QPushButton, message: QLabel) -> None:
		"""Les boutons et le message de la fiche ; à appeler une fois son écran construit, avant charger()."""
		self.bouton_enregistrer = enregistrer
		self.bouton_annuler = annuler
		self.message = message
		enregistrer.clicked.connect(self.enregistrer)
		annuler.clicked.connect(self.charger)

	def titre(self) -> str:
		raise NotImplementedError

	def charger(self) -> None:
		"""Lit l'élément en base et le montre ; la fiche n'est plus modifiée, même si la lecture a changé ses champs."""
		self._lire()
		self._marquer(False)
		self.message.clear()
		self.titre_change.emit(self.titre())

	def enregistrer(self) -> bool:
		"""Écrit la fiche en base, puis la relit ; une fiche refusée n'est pas enregistrée, et dit pourquoi."""
		try:
			with self.connexion.transaction():
				identifiant = self._ecrire()
		except Refus as refus:
			self.message.setText(str(refus))
			return False
		except psycopg.Error as erreur:
			journal.error(f"{self.titre()} : enregistrement impossible : {erreur}")
			self.message.setText(f"Enregistrement impossible : {erreur}")
			return False
		self.identifiant = identifiant
		self.charger()
		self.enregistree.emit(identifiant)
		return True

	def peut_fermer(self) -> bool:
		"""Une fiche modifiée demande quoi faire de ses modifications avant de se fermer."""
		if not self.modifiee:
			return True
		reponse = dialogues.confirmer_fermeture(self, self.titre())
		if reponse is Fermeture.ENREGISTRER:
			return self.enregistrer()
		return reponse is Fermeture.ABANDONNER

	def fermer(self) -> None:
		"""La fiche va être détruite : elle arrête ce qu'elle a lancé."""

	def _lire(self) -> None:
		raise NotImplementedError

	def _ecrire(self) -> int:
		"""Écrit l'élément dans la transaction en cours ; son identifiant. Refus pour une fiche invalide."""
		raise NotImplementedError

	def _modifier(self) -> None:
		self._marquer(True)

	def _marquer(self, modifiee: bool) -> None:
		self.modifiee = modifiee
		self.bouton_enregistrer.setEnabled(modifiee)
		self.bouton_annuler.setEnabled(modifiee)
