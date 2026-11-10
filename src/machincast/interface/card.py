"""Ce qui est commun aux fiches : banque, sonore, séquence (https://github.com/dascritch/machincast/issues/31,
https://github.com/dascritch/machincast/issues/28, https://github.com/dascritch/machincast/issues/112).

Une fiche s'ouvre dans un onglet de la fenêtre (machincast.interface.window). Ses modifications restent dans la fiche
jusqu'à « Enregistrer », qui les écrit en base en une seule transaction, puis relit la fiche ; « Annuler » relit la
fiche sans rien écrire. Les deux boutons ne servent qu'à une fiche modifiée. Une fiche modifiée qui se ferme demande
quoi faire de ses modifications (machincast.interface.dialogs).

Une fiche concrète décrit son genre et son titre, lit l'élément en base (_lire) et l'y écrit (_ecrire). Un refus
(Refus) laisse la fiche modifiée, avec son message.

Avertissement (https://github.com/dascritch/machincast/issues/328) : ce qui ne refuse rien, mais que la diffusion ne
jouera pas comme prévu, une liste vide par exemple, s'affiche en haut de la fiche, sous l'erreur, sur un liseret orange
(avertir, WARNING_OUTLINE).

Erreurs (https://github.com/dascritch/machincast/issues/270) : un refus, un enregistrement, une suppression ou une
restauration impossible s'affiche en haut de la fiche, sur un liseret rouge de 4 pixels (erreur, LISERET), et le
libellé de chaque champ en cause, que nomme le refus, est précédé de ⚠️ (SIGNALE) ; jusqu'au prochain enregistrement,
à « Annuler », ou à la relecture de la fiche. Le message du bas (message) ne dit plus que ce qui informe : fichiers
ignorés d'un dépôt, élément supprimé, copie dont l'original a disparu.

Le rafraîchissement des onglets (https://github.com/dascritch/machincast/issues/148) relit la fiche ; une fiche modifiée
demande d'abord quoi faire de ses modifications, et la fiche d'un élément effacé de la base est à fermer.

« Supprimer… » supprime l'élément, après une confirmation qui dit où il figure
(machincast.interface.deletion, https://github.com/dascritch/machincast/issues/33) : jamais un fichier ni un
répertoire. Une fiche qui n'est pas encore enregistrée n'a rien à supprimer. La fiche d'un élément supprimé, rouverte
depuis l'historique, dit quand il l'a été ; ses champs ne se modifient pas, et « Restaurer » prend la place de
« Supprimer… » (https://github.com/dascritch/machincast/issues/267).

« Dupliquer » (https://github.com/dascritch/machincast/issues/130), pour un élément enregistré et une fiche non
modifiée, demande une copie (requested_duplication) : une nouvelle fiche, qui lit l'élément copié (modele) au lieu
d'être vide, sous un nom interne suivi de « (copie) » (copy_name). Elle est modifiée dès sa lecture : rien n'entre
en base avant « Enregistrer », et l'original n'est jamais écrit. « Annuler » et le rafraîchissement relisent
l'original ; s'il a été effacé entre-temps, la copie reste telle quelle. Ce que chaque fiche copie est dit dans son
module.

Pendant l'enregistrement, toute la fiche est grisée, pour montrer que l'application y travaille ; elle se dégrise à la
fin, réussie ou refusée (https://github.com/dascritch/machincast/issues/382). Réussi par « Enregistrer », l'enregistrement
d'une banque, d'un événement, d'une séquence ou d'un sonore ferme son onglet (CLOSES_AFTER_SAVE, finished) ; refusé, la
fiche reste ouverte, et dit pourquoi.
"""

import logging
import os
from collections.abc import Sequence
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

from machincast.clock import Clock
from machincast.i18n import _
from machincast.interface import deletion, dialogs, intents, preferences
from machincast.interface.dialogs import Closing
from machincast.protection import is_sound_file

log = logging.getLogger(__name__)

INPUTS = (
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
DELETE = intents.label(intents.DELETE, _("Delete…"))
RESTORE = _("Restore")
REPORTED = "⚠️ "
"""Ce qui précède le libellé d'un champ en cause dans l'erreur de la fiche (https://github.com/dascritch/machincast/issues/270)."""
RED = "#d32f2f"
"""Rouge du liseret de l'erreur : lisible sur un fond clair comme sur un fond sombre."""
OUTLINE = f"QLabel#erreur_de_la_fiche {{ border: 4px solid {RED}; padding: 6px; }}"
ORANGE = "#ef6c00"
"""Orange d'un avertissement, qui ne refuse rien : lisible sur un fond clair comme sur un fond sombre."""
WARNING_OUTLINE = f"QLabel#avertissement_de_la_fiche {{ border: 4px solid {ORANGE}; padding: 6px; }}"
WARNED = "⚠️ "
"""Ce qui précède l'avertissement en haut de la fiche (https://github.com/dascritch/machincast/issues/328)."""

Connection = psycopg.Connection[TupleRow]
NAME_LENGTH = 255
"""Longueur maximale d'un nom interne en base (varchar)."""


def rank_of(choices: Sequence[tuple[object, str]], wanted: object) -> int:
	"""Le rang du choix de valeur wanted, parmi des couples (valeur, texte) : celui à montrer dans une liste déroulante
	(https://github.com/dascritch/machincast/issues/340). ValueError pour une valeur qui n'en est pas."""
	for rank, (value, _text) in enumerate(choices):
		if value == wanted:
			return rank
	raise ValueError(wanted)


def sound_files(paths: list[Path]) -> tuple[list[str], list[Path]]:
	"""Les fichiers sonores d'un dépôt, sous leur forme normale et dans l'ordre ; puis ce qui n'en est pas."""
	sounds = []
	for path in paths:
		if (path.is_file()) and (is_sound_file(path)):
			sounds.append(path)
	path_list = []
	for path in sounds:
		path_list.append(os.path.normpath(path))
	others = []
	for path in paths:
		if path not in sounds:
			others.append(path)
	return path_list, others


def copy_name(connection: Connection, table: str, name: str) -> str:
	"""« Nom (copie) », ou « Nom (copie 2) », « Nom (copie 3) »… s'il est pris dans la table ; le nom est raccourci
	pour que la copie tienne en base. À appeler dans une transaction."""
	number = 1
	while True:
		suffix = " (copie)"
		if number > 1:
			suffix = f" (copie {number})"
		candidate = f"{name[: NAME_LENGTH - len(suffix)]}{suffix}"
		taken = connection.execute(
			f"SELECT 1 FROM {table} WHERE internal_name = %s AND deleted_at IS NULL",  # noqa: S608
			(candidate,),
		).fetchone()
		if taken is None:
			return candidate
		number += 1


class Refreshed(Enum):
	"""Ce qu'est devenue une fiche rafraîchie."""

	REREAD = "relue"
	LEFT = _("left as is")
	"""Ses modifications sont gardées : la réponse « Annuler », ou un enregistrement refusé."""
	ERASED = _("erased")
	"""Son élément n'est plus en base : la fiche est à fermer, ses modifications perdues."""


class Refusal(Exception):
	"""La fiche n'est pas enregistrée : le message dit pourquoi, et les champs en cause sont nommés, dans l'ordre de la
	fiche (https://github.com/dascritch/machincast/issues/270)."""

	def __init__(self, message: str, *fields: QWidget) -> None:
		super().__init__(message)
		self.fields = fields


class Card(QWidget):
	changed_title = Signal(str)
	"""Le titre de l'onglet de la fiche a changé : à la lecture, et après un enregistrement."""
	saved = Signal(int)
	"""L'élément est enregistré : son identifiant en base."""
	requested_opening = Signal(str, int, str)
	"""Un élément cité par la fiche est à ouvrir : son genre, son identifiant et son nom."""
	deleted = Signal()
	"""L'élément n'est plus en base : la fiche est à fermer, sans rien demander."""
	requested_duplication = Signal(str, int)
	finished = Signal()
	"""« Enregistrer » a réussi, pour une fiche qui se ferme alors (CLOSES_AFTER_SAVE) : son onglet est à fermer
	(https://github.com/dascritch/machincast/issues/382)."""
	requested_preview = Signal(int)
	"""Un sonore est à pré-écouter : depuis le bouton de la fiche d'un sonore, ou le menu contextuel d'une ligne de
	sonore d'une banque, d'une séquence ou d'un événement (https://github.com/dascritch/machincast/issues/226)."""
	"""« Dupliquer » cliqué : le genre et l'identifiant de l'élément à copier dans une nouvelle fiche."""

	category = ""
	CLOSES_AFTER_SAVE = False
	"""La fiche se ferme après « Enregistrer », s'il réussit : celle d'une banque, d'un événement, d'une séquence ou d'un
	sonore (https://github.com/dascritch/machincast/issues/382)."""
	"""Genre de l'élément, celui des listes et de detail_demande : « banque », « sonore », « séquence »."""
	button_save: QPushButton
	button_cancel: QPushButton
	button_delete: QPushButton
	message: QLabel
	"""Ce que la fiche a ignoré, ou ce qui informe ; une erreur va en haut (erreur)."""
	error: QLabel
	"""L'erreur, en haut de la fiche, sur un liseret rouge ; cachée sans erreur."""
	button_duplicate: QPushButton | None = None
	"""Seules les fiches d'un événement, d'une séquence et d'une banque en ont un."""

	def __init__(
		self, connection: Connection, identifier: int | None, clock: Clock, parent: QWidget | None = None
	) -> None:
		super().__init__(parent)
		self.connection = connection
		self.identifier = identifier
		self.clock = clock
		self.modified = False
		self.model: int | None = None
		"""L'élément que copie une nouvelle fiche, jusqu'à son enregistrement ; None sinon."""
		self.deleted_at: datetime | None = None
		"""L'élément est supprimé, depuis cet instant (https://github.com/dascritch/machincast/issues/267)."""
		self._frozen: list[QWidget] = []
		"""Ce que la fiche d'un élément supprimé a figé."""
		self._reported_list: list[tuple[QLabel | QAbstractButton | QGroupBox, str]] = []
		"""Les libellés précédés de ⚠️, avec leur texte d'origine."""

	def plug(
		self,
		save: QPushButton,
		cancel: QPushButton,
		delete: QPushButton,
		message: QLabel,
		duplicate: QPushButton | None = None,
	) -> None:
		"""Les boutons et le message de la fiche ; à appeler une fois son écran construit, avant charger()."""
		self.button_save = save
		self.button_cancel = cancel
		self.button_delete = delete
		self.message = message
		self.button_duplicate = duplicate
		self.error = QLabel(self)
		self.error.setObjectName("erreur_de_la_fiche")
		self.error.setWordWrap(True)
		self.error.setStyleSheet(OUTLINE)
		self.error.setAccessibleName(_("Error"))
		self.error.hide()
		arrangement = self.layout()
		assert isinstance(arrangement, QBoxLayout)
		arrangement.insertWidget(0, self.error)
		self.warning = QLabel(self)
		self.warning.setObjectName("avertissement_de_la_fiche")
		self.warning.setWordWrap(True)
		self.warning.setStyleSheet(WARNING_OUTLINE)
		self.warning.setAccessibleName(_("Warning"))
		self.warning.hide()
		arrangement.insertWidget(1, self.warning)
		save.clicked.connect(self._save_and_close)
		cancel.clicked.connect(self.load)
		delete.clicked.connect(self._delete_or_restore)
		if duplicate is not None:
			duplicate.clicked.connect(self._duplicate)

	def copy(self, model: int) -> None:
		"""La fiche, nouvelle, devient la copie de cet élément ; rien n'est enregistré."""
		self.model = model
		self.load()

	def is_copy(self) -> bool:
		"""Jusqu'à son enregistrement, qui oublie l'élément copié."""
		return self.model is not None

	def lu(self) -> int | None:
		"""L'élément que la fiche lit en base : le sien, ou celui qu'elle copie ; None pour une fiche vide."""
		if self.identifier is not None:
			return self.identifier
		return self.model

	def title(self) -> str:
		raise NotImplementedError

	def load(self) -> None:
		"""Lit l'élément en base et le montre ; la fiche n'est plus modifiée, même si la lecture a changé ses champs.
		Une copie reste modifiée : elle n'est pas en base. Une copie dont l'original a été effacé reste telle quelle."""
		if (self.is_copy()) and (not self._in_database(self.model)):
			self.message.setText(_("The original is no longer in the database: the copy stays as it is."))
			return
		self._read()
		self._mark(self.is_copy())
		self.button_delete.setEnabled(self.identifier is not None)
		self.message.clear()
		self.erase_error()
		self._show_deletion()
		self.changed_title.emit(self.title())

	def _show_deletion(self) -> None:
		"""La fiche d'un élément supprimé le dit, et se fige ; restauré, elle se modifie de nouveau."""
		self.deleted_at = None
		if self.identifier is not None:
			with self.connection.transaction():
				self.deleted_at = deletion.deleted_at(self.connection, self.category, self.identifier)
		if self.deleted_at is None:
			for input_ in self._frozen:
				input_.setEnabled(True)
			self._frozen = []
			self.button_delete.setText(DELETE)
			return
		for input_ in self.findChildren(QWidget):
			if (isinstance(input_, INPUTS)) and (input_ is not self.button_delete) and (input_.isEnabledTo(self)):
				input_.setEnabled(False)
				self._frozen.append(input_)
		self.button_delete.setText(RESTORE)
		self.message.setText(deletion.marks(self.category, self.deleted_at, preferences.retention()))

	def _save_and_close(self) -> None:
		"""« Enregistrer » : la fiche qui se ferme après un enregistrement réussi le demande."""
		if (self.save()) and (self.CLOSES_AFTER_SAVE):
			self.finished.emit()

	def save(self) -> bool:
		"""Écrit la fiche en base, puis la relit ; une fiche refusée n'est pas enregistrée, et dit pourquoi. Toute la
		fiche est grisée pendant l'enregistrement (https://github.com/dascritch/machincast/issues/382)."""
		self.setEnabled(False)
		# Le gris se dessine avant l'enregistrement, qui tient le fil de l'interface, sans traiter d'autre événement.
		self.repaint()
		try:
			return self._save()
		finally:
			self.setEnabled(True)

	def _save(self) -> bool:
		try:
			with self.connection.transaction():
				identifier = self._write()
		except Refusal as refusal:
			self.flag_error(str(refusal), refusal.fields)
			return False
		except psycopg.Error as error:
			log.error(_("{self_}: saving impossible: {error}").format(self_=self.title(), error=error))
			self.flag_error(_("Saving impossible: {error}").format(error=error))
			return False
		self.identifier = identifier
		self.model = None
		self.load()
		self.saved.emit(identifier)
		return True

	def _delete_or_restore(self) -> None:
		if self.deleted_at is None:
			self.delete()
		else:
			self.restore()

	def restore(self) -> None:
		"""L'élément supprimé est remis en service ; la fiche dit pourquoi elle ne le peut pas."""
		if self.identifier is None:
			return
		try:
			with self.connection.transaction():
				deletion.restore(self.connection, self.category, self.identifier)
		except deletion.Prevented as prevented:
			self.flag_error(str(prevented))
			return
		except psycopg.Error as error:
			log.error(_("{self_}: restoring impossible: {error}").format(self_=self.title(), error=error))
			self.flag_error(_("Restoring impossible: {error}").format(error=error))
			return
		self.load()
		self.saved.emit(self.identifier)

	def delete(self) -> None:
		"""Supprime l'élément, après confirmation ; un élément déjà effacé de la base ferme simplement la fiche."""
		if self.identifier is None:
			return
		try:
			with self.connection.transaction():
				question = deletion.question(self.connection, self.category, self.identifier)
		except deletion.Prevented as prevented:
			self.flag_error(str(prevented))
			return
		except psycopg.Error as error:
			self._flag_impossible_deletion(error)
			return
		try:
			if question is not None:
				title, text = question
				if not dialogs.confirm_deletion(self, title, text):
					return
				with self.connection.transaction():
					deletion.delete(self.connection, self.category, self.identifier, self.clock.now())
		except psycopg.Error as error:
			self._flag_impossible_deletion(error)
			return
		self.deleted.emit()

	def _flag_impossible_deletion(self, error: psycopg.Error) -> None:
		log.error(_("{self_}: deletion impossible: {error}").format(self_=self.title(), error=error))
		self.flag_error(_("Deletion impossible: {error}").format(error=error))

	def _reported(self, label: QWidget) -> bool:
		"""Le libellé signale déjà une erreur."""
		for reports, _text in self._reported_list:
			if reports is label:
				return True
		return False

	def flag_error(self, text: str, fields: tuple[QWidget, ...] = ()) -> None:
		"""L'erreur en haut de la fiche, et ⚠️ devant le libellé de chaque champ en cause."""
		self.erase_error()
		self.error.setText(text)
		self.error.show()

		def flag_field(field: QWidget) -> None:
			label = self._label(field)
			if (label is None) or (self._reported(label)):
				return
			if isinstance(label, QGroupBox):
				self._reported_list.append((label, label.title()))
				label.setTitle(f"{REPORTED}{label.title()}")
			else:
				self._reported_list.append((label, label.text()))
				label.setText(f"{REPORTED}{label.text()}")

		for field in fields:
			flag_field(field)

	def warn(self, text: str) -> None:
		"""L'avertissement en haut de la fiche, sous l'erreur, sur un liseret orange : il ne refuse rien, et la fiche
		s'enregistre (https://github.com/dascritch/machincast/issues/328). Un texte vide le cache."""
		self.warning.setText("")
		if text != "":
			self.warning.setText(f"{WARNED}{text}")
		self.warning.setVisible(text != "")

	def erase_error(self) -> None:
		"""Plus d'erreur : le liseret se cache, et les champs signalés retrouvent leur libellé."""
		self.error.clear()
		self.error.hide()
		for label, text in self._reported_list:
			if isinstance(label, QGroupBox):
				label.setTitle(text)
			else:
				label.setText(text)
		self._reported_list = []

	def _label(self, field: QWidget) -> QLabel | QAbstractButton | QGroupBox | None:
		"""Le libellé d'un champ : celui de sa ligne de formulaire, ou l'étiquette dont il est le compagnon ; une case
		à cocher, un bouton ou un groupe est son propre libellé."""
		for form in self.findChildren(QFormLayout):
			caption = form.labelForField(field)
			if isinstance(caption, QLabel):
				return caption
		for caption in self.findChildren(QLabel):
			if caption.buddy() is field:
				return caption
		if isinstance(field, (QAbstractButton, QGroupBox)):
			return field
		return None

	def can_close(self) -> bool:
		"""Une fiche modifiée demande quoi faire de ses modifications avant de se fermer."""
		if not self.modified:
			return True
		response = dialogs.confirm_closing(self, self.title())
		if response is Closing.SAVE:
			return self.save()
		return response is Closing.ABANDON

	def refresh(self) -> Refreshed:
		"""Relit la fiche ; une fiche modifiée demande d'abord quoi faire de ses modifications."""
		if (self.identifier is not None) and (not self._in_database(self.identifier)):
			return Refreshed.ERASED
		if self.modified:
			response = dialogs.confirm_closing(self, self.title(), _("refresh the card"))
			if response is Closing.CANCEL:
				return Refreshed.LEFT
			if response is Closing.SAVE:
				# Enregistrer relit la fiche.
				if self.save():
					return Refreshed.REREAD
				return Refreshed.LEFT
		self.load()
		return Refreshed.REREAD

	def _in_database(self, identifier: int | None) -> bool:
		table = deletion.CATEGORIES[self.category].table
		with self.connection.transaction():
			line = self.connection.execute(f"SELECT 1 FROM {table} WHERE id = %s", (identifier,)).fetchone()  # noqa: S608
		return line is not None

	def name_of_copy(self, name: str) -> str:
		"""Le nom interne d'une copie de l'élément nommé ainsi."""
		table = deletion.CATEGORIES[self.category].table
		with self.connection.transaction():
			return copy_name(self.connection, table, name)

	def _duplicate(self) -> None:
		# Le bouton n'est actif que pour un élément enregistré, et une fiche non modifiée (_marquer).
		if self.identifier is not None:
			self.requested_duplication.emit(self.category, self.identifier)

	def save_file(self, file: str) -> int:
		"""Dans la transaction d'« Enregistrer » : un fichier déposé devient un sonore à l'état aperçu, que Machin
		indexation décodera ; s'il a été enregistré entre-temps, le sonore est repris."""
		line = self.connection.execute(
			"SELECT id FROM sounds WHERE location = %s AND deleted_at IS NULL", (file,)
		).fetchone()
		if line is None:
			line = self.connection.execute(
				"INSERT INTO sounds (type, location, state) VALUES ('file', %s, 'preview') RETURNING id",
				(file,),
			).fetchone()
			assert line is not None
		return int(str(line[0]))

	def flag_ignored(self, ignored: list[Path], reason: str, advice: str = "") -> None:
		"""Ce que la fiche n'a pas pris d'un dépôt, et pourquoi."""
		if ignored != []:
			path_list = []
			for path in ignored:
				path_list.append(path.name)
			self.message.setText(
				_("Ignored, {reason}: {list}.{advice}").format(reason=reason, list=", ".join(path_list), advice=advice)
			)

	def shut_down(self) -> None:
		"""La fiche va être détruite : elle arrête ce qu'elle a lancé."""

	def _read(self) -> None:
		raise NotImplementedError

	def _write(self) -> int:
		"""Écrit l'élément dans la transaction en cours ; son identifiant. Refus pour une fiche invalide."""
		raise NotImplementedError

	def _modify(self) -> None:
		self._mark(True)

	def _mark(self, modified: bool) -> None:
		self.modified = modified
		self.button_save.setEnabled(modified)
		self.button_cancel.setEnabled(modified)
		if self.button_duplicate is not None:
			self.button_duplicate.setEnabled((self.identifier is not None) and (not modified))
