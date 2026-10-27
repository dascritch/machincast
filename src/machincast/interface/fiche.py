"""Ce qui est commun aux fiches : banque, sonore, séquence (https://github.com/dascritch/machincast/issues/31,
https://github.com/dascritch/machincast/issues/28, https://github.com/dascritch/machincast/issues/112).

Une fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.fenetre). Ses modifications restent dans la fiche
jusqu'à « Enregistrer », qui les écrit en base en une seule transaction, puis relit la fiche ; « Annuler » relit la
fiche sans rien écrire. Les deux boutons ne servent qu'à une fiche modifiée. Une fiche modifiée qui se ferme demande
quoi faire de ses modifications (machincast.interface.dialogues).

Une fiche concrète décrit son genre et son titre, lit l'élément en base (_lire) et l'y écrit (_ecrire). Un refus
(Refus) laisse la fiche modifiée, avec son message.

Erreurs (https://github.com/dascritch/machincast/issues/270) : un refus, un enregistrement, une suppression ou une
restauration impossible s'affiche en haut de la fiche, sur un liseret rouge de 4 pixels (erreur, LISERET), et le
libellé de chaque champ en cause, que nomme le refus, est précédé de ⚠️ (SIGNALE) ; jusqu'au prochain enregistrement,
à « Annuler », ou à la relecture de la fiche. Le message du bas (message) ne dit plus que ce qui informe : fichiers
ignorés d'un dépôt, élément supprimé, copie dont l'original a disparu.

Le rafraîchissement des onglets (https://github.com/dascritch/machincast/issues/148) relit la fiche ; une fiche modifiée
demande d'abord quoi faire de ses modifications, et la fiche d'un élément effacé de la base est à fermer.

« Supprimer… » supprime l'élément, après une confirmation qui dit où il figure
(machincast.interface.suppression, https://github.com/dascritch/machincast/issues/33) : jamais un fichier ni un
répertoire. Une fiche qui n'est pas encore enregistrée n'a rien à supprimer. La fiche d'un élément supprimé, rouverte
depuis l'historique, dit quand il l'a été ; ses champs ne se modifient pas, et « Restaurer » prend la place de
« Supprimer… » (https://github.com/dascritch/machincast/issues/267).

« Dupliquer » (https://github.com/dascritch/machincast/issues/130), pour un élément enregistré et une fiche non
modifiée, demande une copie (duplication_demandee) : une nouvelle fiche, qui lit l'élément copié (modele) au lieu
d'être vide, sous un nom interne suivi de « (copie) » (nom_de_copie). Elle est modifiée dès sa lecture : rien n'entre
en base avant « Enregistrer », et l'original n'est jamais écrit. « Annuler » et le rafraîchissement relisent
l'original ; s'il a été effacé entre-temps, la copie reste telle quelle. Ce que chaque fiche copie est dit dans son
module.
"""

import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
	QAbstractButton,
	QAbstractItemView,
	QAbstractSlider,
	QAbstractSpinBox,
	QBoxLayout,
	QComboBox,
	QFormLayout,
	QGroupBox,
	QLabel,
	QLineEdit,
	QPlainTextEdit,
	QPushButton,
	QTextEdit,
	QWidget,
)

from machincast.horloge import Horloge
from machincast.interface import dialogues, preferences, suppression
from machincast.interface.dialogues import Fermeture
from machincast.protection import est_fichier_sonore

journal = logging.getLogger(__name__)

SAISIES = (
	QLineEdit,
	QAbstractSpinBox,
	QComboBox,
	QAbstractButton,
	QAbstractItemView,
	QAbstractSlider,
	QTextEdit,
	QPlainTextEdit,
)
"""Ce qui se modifie dans une fiche, et que la fiche d'un élément supprimé fige."""
SUPPRIMER = "Supprimer…"
RESTAURER = "Restaurer"
SIGNALE = "⚠️ "
"""Ce qui précède le libellé d'un champ en cause dans l'erreur de la fiche (https://github.com/dascritch/machincast/issues/270)."""
ROUGE = "#d32f2f"
"""Rouge du liseret de l'erreur : lisible sur un fond clair comme sur un fond sombre."""
LISERET = f"QLabel#erreur_de_la_fiche {{ border: 4px solid {ROUGE}; padding: 6px; }}"

Connexion = psycopg.Connection[TupleRow]
LONGUEUR_DES_NOMS = 255
"""Longueur maximale d'un nom interne en base (varchar)."""


def fichiers_sonores(chemins: list[Path]) -> tuple[list[str], list[Path]]:
	"""Les fichiers sonores d'un dépôt, sous leur forme normale et dans l'ordre ; puis ce qui n'en est pas."""
	sonores = [chemin for chemin in chemins if (chemin.is_file()) and (est_fichier_sonore(chemin))]
	return [os.path.normpath(chemin) for chemin in sonores], [chemin for chemin in chemins if chemin not in sonores]


def nom_de_copie(connexion: Connexion, table: str, nom: str) -> str:
	"""« Nom (copie) », ou « Nom (copie 2) », « Nom (copie 3) »… s'il est pris dans la table ; le nom est raccourci
	pour que la copie tienne en base. À appeler dans une transaction."""
	numero = 1
	while True:
		suffixe = " (copie)"
		if numero > 1:
			suffixe = f" (copie {numero})"
		candidat = f"{nom[: LONGUEUR_DES_NOMS - len(suffixe)]}{suffixe}"
		pris = connexion.execute(
			f"SELECT 1 FROM {table} WHERE nom_interne = %s AND supprime_le IS NULL",  # noqa: S608
			(candidat,),
		).fetchone()
		if pris is None:
			return candidat
		numero += 1


class Rafraichie(Enum):
	"""Ce qu'est devenue une fiche rafraîchie."""

	RELUE = "relue"
	LAISSEE = "laissée telle quelle"
	"""Ses modifications sont gardées : la réponse « Annuler », ou un enregistrement refusé."""
	EFFACEE = "effacée"
	"""Son élément n'est plus en base : la fiche est à fermer, ses modifications perdues."""


class Refus(Exception):
	"""La fiche n'est pas enregistrée : le message dit pourquoi, et les champs en cause sont nommés, dans l'ordre de la
	fiche (https://github.com/dascritch/machincast/issues/270)."""

	def __init__(self, message: str, *champs: QWidget) -> None:
		super().__init__(message)
		self.champs = champs


class Fiche(QWidget):
	titre_change = Signal(str)
	"""Le titre de l'onglet de la fiche a changé : à la lecture, et après un enregistrement."""
	enregistree = Signal(int)
	"""L'élément est enregistré : son identifiant en base."""
	ouverture_demandee = Signal(str, int, str)
	"""Un élément cité par la fiche est à ouvrir : son genre, son identifiant et son nom."""
	supprimee = Signal()
	"""L'élément n'est plus en base : la fiche est à fermer, sans rien demander."""
	duplication_demandee = Signal(str, int)
	preecoute_demandee = Signal(int)
	"""Un sonore est à pré-écouter : depuis le bouton de la fiche d'un sonore, ou le menu contextuel d'une ligne de
	sonore d'une banque, d'une séquence ou d'un événement (https://github.com/dascritch/machincast/issues/226)."""
	"""« Dupliquer » cliqué : le genre et l'identifiant de l'élément à copier dans une nouvelle fiche."""

	genre = ""
	"""Genre de l'élément, celui des listes et de detail_demande : « banque », « sonore », « séquence »."""
	bouton_enregistrer: QPushButton
	bouton_annuler: QPushButton
	bouton_supprimer: QPushButton
	message: QLabel
	"""Ce que la fiche a ignoré, ou ce qui informe ; une erreur va en haut (erreur)."""
	erreur: QLabel
	"""L'erreur, en haut de la fiche, sur un liseret rouge ; cachée sans erreur."""
	bouton_dupliquer: QPushButton | None = None
	"""Seules les fiches d'un événement, d'une séquence et d'une banque en ont un."""

	def __init__(
		self, connexion: Connexion, identifiant: int | None, horloge: Horloge, parent: QWidget | None = None
	) -> None:
		super().__init__(parent)
		self.connexion = connexion
		self.identifiant = identifiant
		self.horloge = horloge
		self.modifiee = False
		self.modele: int | None = None
		"""L'élément que copie une nouvelle fiche, jusqu'à son enregistrement ; None sinon."""
		self.supprime_le: datetime | None = None
		"""L'élément est supprimé, depuis cet instant (https://github.com/dascritch/machincast/issues/267)."""
		self._figes: list[QWidget] = []
		"""Ce que la fiche d'un élément supprimé a figé."""
		self._signales: list[tuple[QLabel | QAbstractButton | QGroupBox, str]] = []
		"""Les libellés précédés de ⚠️, avec leur texte d'origine."""

	def brancher(
		self,
		enregistrer: QPushButton,
		annuler: QPushButton,
		supprimer: QPushButton,
		message: QLabel,
		dupliquer: QPushButton | None = None,
	) -> None:
		"""Les boutons et le message de la fiche ; à appeler une fois son écran construit, avant charger()."""
		self.bouton_enregistrer = enregistrer
		self.bouton_annuler = annuler
		self.bouton_supprimer = supprimer
		self.message = message
		self.bouton_dupliquer = dupliquer
		self.erreur = QLabel(self)
		self.erreur.setObjectName("erreur_de_la_fiche")
		self.erreur.setWordWrap(True)
		self.erreur.setStyleSheet(LISERET)
		self.erreur.setAccessibleName("Erreur")
		self.erreur.hide()
		disposition = self.layout()
		assert isinstance(disposition, QBoxLayout)
		disposition.insertWidget(0, self.erreur)
		enregistrer.clicked.connect(self.enregistrer)
		annuler.clicked.connect(self.charger)
		supprimer.clicked.connect(self._supprimer_ou_restaurer)
		if dupliquer is not None:
			dupliquer.clicked.connect(self._dupliquer)

	def copier(self, modele: int) -> None:
		"""La fiche, nouvelle, devient la copie de cet élément ; rien n'est enregistré."""
		self.modele = modele
		self.charger()

	def est_une_copie(self) -> bool:
		"""Jusqu'à son enregistrement, qui oublie l'élément copié."""
		return self.modele is not None

	def lu(self) -> int | None:
		"""L'élément que la fiche lit en base : le sien, ou celui qu'elle copie ; None pour une fiche vide."""
		if self.identifiant is not None:
			return self.identifiant
		return self.modele

	def titre(self) -> str:
		raise NotImplementedError

	def charger(self) -> None:
		"""Lit l'élément en base et le montre ; la fiche n'est plus modifiée, même si la lecture a changé ses champs.
		Une copie reste modifiée : elle n'est pas en base. Une copie dont l'original a été effacé reste telle quelle."""
		if (self.est_une_copie()) and (not self._en_base(self.modele)):
			self.message.setText("L'original n'est plus en base : la copie reste telle quelle.")
			return
		self._lire()
		self._marquer(self.est_une_copie())
		self.bouton_supprimer.setEnabled(self.identifiant is not None)
		self.message.clear()
		self.effacer_l_erreur()
		self._montrer_la_suppression()
		self.titre_change.emit(self.titre())

	def _montrer_la_suppression(self) -> None:
		"""La fiche d'un élément supprimé le dit, et se fige ; restauré, elle se modifie de nouveau."""
		self.supprime_le = None
		if self.identifiant is not None:
			with self.connexion.transaction():
				self.supprime_le = suppression.supprime_le(self.connexion, self.genre, self.identifiant)
		if self.supprime_le is None:
			for saisie in self._figes:
				saisie.setEnabled(True)
			self._figes = []
			self.bouton_supprimer.setText(SUPPRIMER)
			return
		for saisie in self.findChildren(QWidget):
			if (isinstance(saisie, SAISIES)) and (saisie is not self.bouton_supprimer) and (saisie.isEnabled()):
				saisie.setEnabled(False)
				self._figes.append(saisie)
		self.bouton_supprimer.setText(RESTAURER)
		self.message.setText(suppression.marque(self.genre, self.supprime_le, preferences.peremption()))

	def enregistrer(self) -> bool:
		"""Écrit la fiche en base, puis la relit ; une fiche refusée n'est pas enregistrée, et dit pourquoi."""
		try:
			with self.connexion.transaction():
				identifiant = self._ecrire()
		except Refus as refus:
			self.signaler_l_erreur(str(refus), refus.champs)
			return False
		except psycopg.Error as erreur:
			journal.error(f"{self.titre()} : enregistrement impossible : {erreur}")
			self.signaler_l_erreur(f"Enregistrement impossible : {erreur}")
			return False
		self.identifiant = identifiant
		self.modele = None
		self.charger()
		self.enregistree.emit(identifiant)
		return True

	def _supprimer_ou_restaurer(self) -> None:
		if self.supprime_le is None:
			self.supprimer()
		else:
			self.restaurer()

	def restaurer(self) -> None:
		"""L'élément supprimé est remis en service ; la fiche dit pourquoi elle ne le peut pas."""
		if self.identifiant is None:
			return
		try:
			with self.connexion.transaction():
				suppression.restaurer(self.connexion, self.genre, self.identifiant)
		except suppression.Empechee as empechee:
			self.signaler_l_erreur(str(empechee))
			return
		except psycopg.Error as erreur:
			journal.error(f"{self.titre()} : restauration impossible : {erreur}")
			self.signaler_l_erreur(f"Restauration impossible : {erreur}")
			return
		self.charger()
		self.enregistree.emit(self.identifiant)

	def supprimer(self) -> None:
		"""Supprime l'élément, après confirmation ; un élément déjà effacé de la base ferme simplement la fiche."""
		if self.identifiant is None:
			return
		try:
			with self.connexion.transaction():
				question = suppression.question(self.connexion, self.genre, self.identifiant)
		except suppression.Empechee as empechee:
			self.signaler_l_erreur(str(empechee))
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
					suppression.supprimer(self.connexion, self.genre, self.identifiant, self.horloge.maintenant())
		except psycopg.Error as erreur:
			self._signaler_suppression_impossible(erreur)
			return
		self.supprimee.emit()

	def _signaler_suppression_impossible(self, erreur: psycopg.Error) -> None:
		journal.error(f"{self.titre()} : suppression impossible : {erreur}")
		self.signaler_l_erreur(f"Suppression impossible : {erreur}")

	def signaler_l_erreur(self, texte: str, champs: tuple[QWidget, ...] = ()) -> None:
		"""L'erreur en haut de la fiche, et ⚠️ devant le libellé de chaque champ en cause."""
		self.effacer_l_erreur()
		self.erreur.setText(texte)
		self.erreur.show()
		for champ in champs:
			libelle = self._libelle(champ)
			if (libelle is None) or (any(signale is libelle for signale, _texte in self._signales)):
				continue
			if isinstance(libelle, QGroupBox):
				self._signales.append((libelle, libelle.title()))
				libelle.setTitle(f"{SIGNALE}{libelle.title()}")
			else:
				self._signales.append((libelle, libelle.text()))
				libelle.setText(f"{SIGNALE}{libelle.text()}")

	def effacer_l_erreur(self) -> None:
		"""Plus d'erreur : le liseret se cache, et les champs signalés retrouvent leur libellé."""
		self.erreur.clear()
		self.erreur.hide()
		for libelle, texte in self._signales:
			if isinstance(libelle, QGroupBox):
				libelle.setTitle(texte)
			else:
				libelle.setText(texte)
		self._signales = []

	def _libelle(self, champ: QWidget) -> QLabel | QAbstractButton | QGroupBox | None:
		"""Le libellé d'un champ : celui de sa ligne de formulaire, ou l'étiquette dont il est le compagnon ; une case
		à cocher, un bouton ou un groupe est son propre libellé."""
		for formulaire in self.findChildren(QFormLayout):
			etiquette = formulaire.labelForField(champ)
			if isinstance(etiquette, QLabel):
				return etiquette
		for etiquette in self.findChildren(QLabel):
			if etiquette.buddy() is champ:
				return etiquette
		if isinstance(champ, (QAbstractButton, QGroupBox)):
			return champ
		return None

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
		if (self.identifiant is not None) and (not self._en_base(self.identifiant)):
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

	def _en_base(self, identifiant: int | None) -> bool:
		table = suppression.GENRES[self.genre].table
		with self.connexion.transaction():
			ligne = self.connexion.execute(f"SELECT 1 FROM {table} WHERE id = %s", (identifiant,)).fetchone()  # noqa: S608
		return ligne is not None

	def nom_de_la_copie(self, nom: str) -> str:
		"""Le nom interne d'une copie de l'élément nommé ainsi."""
		table = suppression.GENRES[self.genre].table
		with self.connexion.transaction():
			return nom_de_copie(self.connexion, table, nom)

	def _dupliquer(self) -> None:
		# Le bouton n'est actif que pour un élément enregistré, et une fiche non modifiée (_marquer).
		if self.identifiant is not None:
			self.duplication_demandee.emit(self.genre, self.identifiant)

	def enregistrer_fichier(self, fichier: str) -> int:
		"""Dans la transaction d'« Enregistrer » : un fichier déposé devient un sonore à l'état aperçu, que Machin
		indexation décodera ; s'il a été enregistré entre-temps, le sonore est repris."""
		ligne = self.connexion.execute(
			"SELECT id FROM sonores WHERE emplacement = %s AND supprime_le IS NULL", (fichier,)
		).fetchone()
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
		if self.bouton_dupliquer is not None:
			self.bouton_dupliquer.setEnabled((self.identifiant is not None) and (not modifiee))
