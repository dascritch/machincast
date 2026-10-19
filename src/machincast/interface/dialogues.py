"""Fenêtres de dialogue des fiches (https://github.com/dascritch/machincast/issues/31).

Chaque question est une fonction de ce module, appelée par son nom (dialogues.confirmer_fermeture(…)) : les scénarios
la remplacent par la réponse attendue, et aucune fenêtre modale n'attend un clic pendant les tests.
"""

from enum import StrEnum
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from machincast.interface.choix import Choix
from machincast.interface.listes import BANQUES, SONORES


class Fermeture(StrEnum):
	"""Ce que devient une fiche modifiée qui se ferme."""

	ENREGISTRER = "Enregistrer"
	ABANDONNER = "Abandonner"
	ANNULER = "Annuler"


class Retrait(StrEnum):
	"""Ce que devient un sonore retiré d'une banque, quand la prochaine indexation l'y remettra."""

	RETIRER = "Retirer quand même"
	OUVRIR_DOSSIER = "Ouvrir le dossier"
	ANNULER = "Annuler"


def confirmer_fermeture(parent: QWidget, titre: str) -> Fermeture:
	"""Demande quoi faire des modifications d'une fiche qui se ferme : Entrée enregistre, Échap annule la fermeture."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle(titre)
	question.setText(f"« {titre} » a des modifications qui ne sont pas enregistrées.")
	question.setInformativeText("Les enregistrer avant de fermer la fiche ?")
	# Le bouton du rôle AcceptRole répond à Entrée, celui du rôle RejectRole à Échap.
	enregistrer = question.addButton(Fermeture.ENREGISTRER.value, QMessageBox.ButtonRole.AcceptRole)
	abandonner = question.addButton(Fermeture.ABANDONNER.value, QMessageBox.ButtonRole.DestructiveRole)
	question.addButton(Fermeture.ANNULER.value, QMessageBox.ButtonRole.RejectRole)
	question.exec()
	if question.clickedButton() is enregistrer:
		return Fermeture.ENREGISTRER
	if question.clickedButton() is abandonner:
		return Fermeture.ABANDONNER
	return Fermeture.ANNULER


def confirmer_retrait(parent: QWidget, avertissement: str) -> Retrait:
	"""Prévient qu'un sonore retiré reviendra : Entrée et Échap gardent le sonore."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Warning)
	question.setWindowTitle("Retirer un sonore")
	question.setText(avertissement)
	retirer = question.addButton(Retrait.RETIRER.value, QMessageBox.ButtonRole.DestructiveRole)
	ouvrir = question.addButton(Retrait.OUVRIR_DOSSIER.value, QMessageBox.ButtonRole.ActionRole)
	annuler = question.addButton(Retrait.ANNULER.value, QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(annuler)
	question.exec()
	if question.clickedButton() is retirer:
		return Retrait.RETIRER
	if question.clickedButton() is ouvrir:
		return Retrait.OUVRIR_DOSSIER
	return Retrait.ANNULER


def choisir_repertoire(parent: QWidget) -> str | None:
	"""Un répertoire choisi dans le sélecteur du poste, ou None si le choix est abandonné."""
	repertoire = QFileDialog.getExistingDirectory(parent, "Répertoire indexé de la banque")
	if repertoire == "":
		return None
	return repertoire


def choisir_sonores(parent: QWidget, connexion: psycopg.Connection[TupleRow], remarque: str = "") -> list[int]:
	"""Les sonores choisis dans la liste des sonores en base ; aucun si le choix est abandonné."""
	return _choisir(Choix(SONORES, connexion, remarque, parent))


def choisir_banques(parent: QWidget, connexion: psycopg.Connection[TupleRow], remarque: str = "") -> list[int]:
	"""Les banques choisies dans la liste des banques en base ; aucune si le choix est abandonné."""
	return _choisir(Choix(BANQUES, connexion, remarque, parent))


def _choisir(choix: Choix) -> list[int]:
	if choix.exec() != QDialog.DialogCode.Accepted:
		return []
	return choix.selection()


def ouvrir_dossier(dossier: Path) -> None:
	"""Ouvre le dossier dans le navigateur de fichiers du poste."""
	QDesktopServices.openUrl(QUrl.fromLocalFile(str(dossier)))
