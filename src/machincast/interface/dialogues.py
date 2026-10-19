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
from machincast.interface.listes import BANQUES, SEQUENCES, SONORES
from machincast.protection import EXTENSIONS_SONORES


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


def confirmer_fermeture(parent: QWidget, titre: str, avant: str = "fermer la fiche") -> Fermeture:
	"""Demande quoi faire des modifications d'une fiche, avant de la fermer ou de la rafraîchir : Entrée enregistre,
	Échap annule la fermeture ou le rafraîchissement de la fiche."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle(titre)
	question.setText(f"« {titre} » a des modifications qui ne sont pas enregistrées.")
	question.setInformativeText(f"Les enregistrer avant de {avant} ?")
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


def confirmer_suppression(parent: QWidget, titre: str, texte: str) -> bool:
	"""Demande la confirmation d'une suppression : Entrée et Échap gardent l'élément."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Warning)
	question.setWindowTitle(titre)
	question.setText(texte)
	supprimer = question.addButton("Supprimer", QMessageBox.ButtonRole.DestructiveRole)
	annuler = question.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(annuler)
	question.exec()
	return question.clickedButton() is supprimer


def montrer_rapport(parent: QWidget, titre: str, texte: str, anomalies: list[str]) -> None:
	"""Le rapport d'une indexation ; ses anomalies, fichier par fichier, dans les détails."""
	rapport = QMessageBox(parent)
	rapport.setIcon(QMessageBox.Icon.Information)
	rapport.setWindowTitle(titre)
	rapport.setText(texte)
	if anomalies != []:
		rapport.setIcon(QMessageBox.Icon.Warning)
		pluriel = "s" * (len(anomalies) > 1)
		rapport.setInformativeText(f"{len(anomalies)} anomalie{pluriel} : voir les détails.")
		rapport.setDetailedText("\n".join(anomalies))
	rapport.exec()


def choisir_fichiers(parent: QWidget) -> list[Path]:
	"""Les fichiers choisis dans le sélecteur du poste, plusieurs à la fois ; aucun si le choix est abandonné."""
	motifs = " ".join(f"*{extension}" for extension in sorted(EXTENSIONS_SONORES))
	choisis, _filtre = QFileDialog.getOpenFileNames(
		parent, "Ajouter des fichiers sonores", "", f"Fichiers sonores ({motifs});;Tous les fichiers (*)"
	)
	return [Path(chemin) for chemin in choisis]


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


def choisir_sequences(parent: QWidget, connexion: psycopg.Connection[TupleRow], remarque: str = "") -> list[int]:
	"""Les séquences choisies dans la liste des séquences en base ; aucune si le choix est abandonné."""
	return _choisir(Choix(SEQUENCES, connexion, remarque, parent))


def _choisir(choix: Choix) -> list[int]:
	if choix.exec() != QDialog.DialogCode.Accepted:
		return []
	return choix.selection()


def montrer_version(parent: QWidget, texte: str) -> None:
	"""La version de MachinCast, et la date de sa dernière modification."""
	QMessageBox.information(parent, "Version de MachinCast", texte)


def ouvrir_page(adresse: str) -> None:
	"""Ouvre la page dans le navigateur web du poste."""
	QDesktopServices.openUrl(QUrl(adresse))


def ouvrir_dossier(dossier: Path) -> None:
	"""Ouvre le dossier dans le navigateur de fichiers du poste."""
	QDesktopServices.openUrl(QUrl.fromLocalFile(str(dossier)))
