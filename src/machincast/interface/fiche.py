"""Ce qui est commun aux fiches : banque, sonore, séquence (https://github.com/dascritch/machincast/issues/31,
https://github.com/dascritch/machincast/issues/28, https://github.com/dascritch/machincast/issues/112).

Une fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.fenetre). Ses modifications restent dans la fiche
jusqu'à « Enregistrer », qui les écrit en base en une seule transaction, puis relit la fiche ; « Annuler » relit la
fiche sans rien écrire. Les deux boutons ne servent qu'à une fiche modifiée. Une fiche modifiée qui se ferme demande
quoi faire de ses modifications (machincast.interface.dialogues).

Une fiche concrète décrit son genre et son titre, lit l'élément en base (_lire) et l'y écrit (_ecrire). Un refus
(Refus) laisse la fiche modifiée, avec son message.

Le rafraîchissement des onglets (https://github.com/dascritch/machincast/issues/148) relit la fiche ; une fiche modifiée
demande d'abord quoi faire de ses modifications, et la fiche d'un élément effacé de la base est à fermer.

« Supprimer… » supprime l'élément de la base, après une confirmation qui dit où il figure
(machincast.interface.suppression, https://github.com/dascritch/machincast/issues/33) : jamais un fichier ni un
répertoire. Une fiche qui n'est pas encore enregistrée n'a rien à supprimer.
"""

import logging
import os
from enum import Enum
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from machincast.horloge import Horloge
from machincast.interface import dialogues, suppression
from machincast.interface.dialogues import Fermeture
from machincast.protection import est_fichier_sonore

journal = logging.getLogger(__name__)

Connexion = psycopg.Connection[TupleRow]


def fichiers_sonores(chemins: list[Path]) -> tuple[list[str], list[Path]]:
	"""Les fichiers sonores d'un dépôt, sous leur forme normale et dans l'ordre ; puis ce qui n'en est pas."""
	sonores = [chemin for chemin in chemins if (chemin.is_file()) and (est_fichier_sonore(chemin))]
	return [os.path.normpath(chemin) for chemin in sonores], [chemin for chemin in chemins if chemin not in sonores]


class Rafraichie(Enum):
	"""Ce qu'est devenue une fiche rafraîchie."""

	RELUE = "relue"
	LAISSEE = "laissée telle quelle"
	"""Ses modifications sont gardées : la réponse « Annuler », ou un enregistrement refusé."""
	EFFACEE = "effacée"
	"""Son élément n'est plus en base : la fiche est à fermer, ses modifications perdues."""


class Refus(Exception):
	"""La fiche n'est pas enregistrée : le message dit pourquoi."""


class Fiche(QWidget):
	titre_change = Signal(str)
	"""Le titre de l'onglet de la fiche a changé : à la lecture, et après un enregistrement."""
	enregistree = Signal(int)
	"""L'élément est enregistré : son identifiant en base."""
	ouverture_demandee = Signal(str, int, str)
	"""Un élément cité par la fiche est à ouvrir : son genre, son identifiant et son nom."""
	supprimee = Signal()
	"""L'élément n'est plus en base : la fiche est à fermer, sans rien demander."""

	genre = ""
	"""Genre de l'élément, celui des listes et de detail_demande : « banque », « sonore », « séquence »."""
	bouton_enregistrer: QPushButton
	bouton_annuler: QPushButton
	bouton_supprimer: QPushButton
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

	def brancher(self, enregistrer: QPushButton, annuler: QPushButton, supprimer: QPushButton, message: QLabel) -> None:
		"""Les boutons et le message de la fiche ; à appeler une fois son écran construit, avant charger()."""
		self.bouton_enregistrer = enregistrer
		self.bouton_annuler = annuler
		self.bouton_supprimer = supprimer
		self.message = message
		enregistrer.clicked.connect(self.enregistrer)
		annuler.clicked.connect(self.charger)
		supprimer.clicked.connect(self.supprimer)

	def titre(self) -> str:
		raise NotImplementedError

	def charger(self) -> None:
		"""Lit l'élément en base et le montre ; la fiche n'est plus modifiée, même si la lecture a changé ses champs."""
		self._lire()
		self._marquer(False)
		self.bouton_supprimer.setEnabled(self.identifiant is not None)
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

	def supprimer(self) -> None:
		"""Supprime l'élément de la base, après confirmation ; un élément déjà effacé ferme simplement la fiche."""
		if self.identifiant is None:
			return
		try:
			with self.connexion.transaction():
				question = suppression.question(self.connexion, self.genre, self.identifiant)
		except suppression.Empechee as empechee:
			self.message.setText(str(empechee))
			return
		except psycopg.Error as erreur:
			self._signaler_suppression_impossible(erreur)
			return
		try:
			if question is not None:
				titre, texte = question
				if not dialogues.confirmer_suppression(self, titre, texte):
					return
				with self.connexion.transaction():
					suppression.supprimer(self.connexion, self.genre, self.identifiant)
		except psycopg.Error as erreur:
			self._signaler_suppression_impossible(erreur)
			return
		self.supprimee.emit()

	def _signaler_suppression_impossible(self, erreur: psycopg.Error) -> None:
		journal.error(f"{self.titre()} : suppression impossible : {erreur}")
		self.message.setText(f"Suppression impossible : {erreur}")

	def peut_fermer(self) -> bool:
		"""Une fiche modifiée demande quoi faire de ses modifications avant de se fermer."""
		if not self.modifiee:
			return True
		reponse = dialogues.confirmer_fermeture(self, self.titre())
		if reponse is Fermeture.ENREGISTRER:
			return self.enregistrer()
		return reponse is Fermeture.ABANDONNER

	def rafraichir(self) -> Rafraichie:
		"""Relit la fiche ; une fiche modifiée demande d'abord quoi faire de ses modifications."""
		if (self.identifiant is not None) and (not self._en_base()):
			return Rafraichie.EFFACEE
		if self.modifiee:
			reponse = dialogues.confirmer_fermeture(self, self.titre(), "rafraîchir la fiche")
			if reponse is Fermeture.ANNULER:
				return Rafraichie.LAISSEE
			if reponse is Fermeture.ENREGISTRER:
				# Enregistrer relit la fiche.
				if self.enregistrer():
					return Rafraichie.RELUE
				return Rafraichie.LAISSEE
		self.charger()
		return Rafraichie.RELUE

	def _en_base(self) -> bool:
		table = suppression.GENRES[self.genre].table
		with self.connexion.transaction():
			ligne = self.connexion.execute(f"SELECT 1 FROM {table} WHERE id = %s", (self.identifiant,)).fetchone()  # noqa: S608
		return ligne is not None

	def enregistrer_fichier(self, fichier: str) -> int:
		"""Dans la transaction d'« Enregistrer » : un fichier déposé devient un sonore à l'état aperçu, que Machin
		indexation décodera ; s'il a été enregistré entre-temps, le sonore est repris."""
		ligne = self.connexion.execute("SELECT id FROM sonores WHERE emplacement = %s", (fichier,)).fetchone()
		if ligne is None:
			ligne = self.connexion.execute(
				"INSERT INTO sonores (type, emplacement, etat) VALUES ('fichier', %s, 'apercu') RETURNING id",
				(fichier,),
			).fetchone()
			assert ligne is not None
		return int(str(ligne[0]))

	def signaler_ignores(self, ignores: list[Path], raison: str, conseil: str = "") -> None:
		"""Ce que la fiche n'a pas pris d'un dépôt, et pourquoi."""
		if ignores != []:
			self.message.setText(f"Ignorés, {raison} : {', '.join(chemin.name for chemin in ignores)}.{conseil}")

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
