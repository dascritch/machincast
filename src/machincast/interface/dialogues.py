"""Fenêtres de dialogue des fiches (https://github.com/dascritch/machincast/issues/31).

Chaque question est une fonction de ce module, appelée par son nom (dialogues.confirmer_fermeture(…)) : les scénarios
la remplacent par la réponse attendue, et aucune fenêtre modale n'attend un clic pendant les tests.
"""

import dataclasses
from enum import StrEnum
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from machincast.configuration import EXTENSIONS_D_ICONE, SortieAudio
from machincast.interface.choix import Choix
from machincast.interface.listes import BANQUES, MARQUES_PAGES, SEQUENCES, SONORES
from machincast.interface.preferences import FenetrePreferences, Reglages
from machincast.interface.suggestions import FenetreSuggestions, Manques, Reponse
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


def confirmer_arret_indexation(parent: QWidget, titre: str) -> bool:
	"""Arrêter l'indexation en cours ? Entrée et Échap la laissent continuer."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle(titre)
	question.setText(f"L'indexation est en cours : « {titre} ».")
	question.setInformativeText(
		"L'arrêter ? Elle s'arrête après le fichier en cours ; le travail fait est gardé, la prochaine indexation"
		" reprendra le reste."
	)
	arreter = question.addButton("Arrêter", QMessageBox.ButtonRole.DestructiveRole)
	continuer = question.addButton("Continuer", QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(continuer)
	question.exec()
	return question.clickedButton() is arreter


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


def proposer_rafraichissement(parent: QWidget, texte: str) -> bool:
	"""Après la vérification complète d'un sonore (https://github.com/dascritch/machincast/issues/190) : rafraîchir sa
	fiche ? Entrée rafraîchit, Échap laisse la fiche telle quelle."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle("Vérification complète")
	question.setText(f"{texte} Rafraîchir la fiche ?")
	rafraichir = question.addButton("Rafraîchir", QMessageBox.ButtonRole.AcceptRole)
	question.addButton("Plus tard", QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(rafraichir)
	question.exec()
	return question.clickedButton() is rafraichir


def confirmer_creation(parent: QWidget, texte: str) -> bool:
	"""Créer un événement depuis le calendrier ? Rien n'est enregistré avant sa fiche : Entrée crée, Échap annule."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle("Nouvel événement")
	question.setText(texte)
	creer = question.addButton("Créer", QMessageBox.ButtonRole.AcceptRole)
	question.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(creer)
	question.exec()
	return question.clickedButton() is creer


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


def confirmer_action(parent: QWidget, titre: str, texte: str) -> bool:
	"""Une action sur plusieurs éléments à la fois (https://github.com/dascritch/machincast/issues/114) : Entrée la
	fait, Échap l'annule."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle(titre)
	question.setText(texte)
	faire = question.addButton(titre, QMessageBox.ButtonRole.AcceptRole)
	question.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(faire)
	question.exec()
	return question.clickedButton() is faire


def confirmer_maintenance(parent: QWidget, sauvegardes: Path) -> bool:
	"""Lancer la maintenance de la base, qui écrit une sauvegarde dans sauvegardes ? Entrée et Échap l'annulent : elle
	ne se lance que par son bouton (https://github.com/dascritch/machincast/issues/127)."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle("Maintenance de la base de données")
	question.setText("Êtes-vous sûr de vouloir lancer cette opération ?")
	question.setInformativeText(f"Une sauvegarde de la base sera enregistrée à l'emplacement {sauvegardes}.")
	lancer = question.addButton("Lancer la maintenance", QMessageBox.ButtonRole.AcceptRole)
	annuler = question.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(annuler)
	question.exec()
	return question.clickedButton() is lancer


def choisir_fichiers(parent: QWidget) -> list[Path]:
	"""Les fichiers choisis dans le sélecteur du poste, plusieurs à la fois ; aucun si le choix est abandonné."""
	motifs = " ".join(f"*{extension}" for extension in sorted(EXTENSIONS_SONORES))
	choisis, _filtre = QFileDialog.getOpenFileNames(
		parent, "Ajouter des fichiers sonores", "", f"Fichiers sonores ({motifs});;Tous les fichiers (*)"
	)
	return [Path(chemin) for chemin in choisis]


def choisir_icone(parent: QWidget) -> Path | None:
	"""L'image choisie pour icône de l'application (https://github.com/dascritch/machincast/issues/111) ; None si le
	choix est abandonné."""
	motifs = " ".join(f"*{extension}" for extension in sorted(EXTENSIONS_D_ICONE))
	chemin, _filtre = QFileDialog.getOpenFileName(parent, "Icône de l'application", "", f"Images ({motifs})")
	if chemin == "":
		return None
	return Path(chemin)


def choisir_export(parent: QWidget, propose: str, filtres: list[str]) -> tuple[Path, str] | None:
	"""Le fichier où exporter, et le filtre choisi, qui en donne le format ; None si le choix est abandonné."""
	chemin, filtre = QFileDialog.getSaveFileName(
		parent, "Exporter la simulation", str(Path.home() / propose), ";;".join(filtres)
	)
	if chemin == "":
		return None
	return Path(chemin), filtre


def choisir_repertoire(parent: QWidget) -> str | None:
	"""Un répertoire choisi dans le sélecteur du poste, ou None si le choix est abandonné."""
	repertoire = QFileDialog.getExistingDirectory(parent, "Répertoire indexé de la banque")
	if repertoire == "":
		return None
	return repertoire


def choisir_sonores(parent: QWidget, connexion: psycopg.Connection[TupleRow], remarque: str = "") -> list[int]:
	"""Les sonores choisis dans la liste des sonores en base ; aucun si le choix est abandonné."""
	return _choisir(Choix(SONORES, connexion, remarque, parent))


def choisir_banques(
	parent: QWidget, connexion: psycopg.Connection[TupleRow], remarque: str = "", parmi: list[int] | None = None
) -> list[int]:
	"""Les banques choisies dans la liste des banques en base, ou parmi celles-ci seulement ; aucune si le choix est
	abandonné."""
	source = BANQUES
	if parmi is not None:
		proposees = set(parmi)
		source = dataclasses.replace(
			BANQUES, lire=lambda lue: [ligne for ligne in BANQUES.lire(lue) if ligne.identifiant in proposees]
		)
	return _choisir(Choix(source, connexion, remarque, parent))


def choisir_sequences(parent: QWidget, connexion: psycopg.Connection[TupleRow], remarque: str = "") -> list[int]:
	"""Les séquences choisies dans la liste des séquences en base ; aucune si le choix est abandonné."""
	return _choisir(Choix(SEQUENCES, connexion, remarque, parent))


def choisir_marques_pages(parent: QWidget, connexion: psycopg.Connection[TupleRow], remarque: str = "") -> list[int]:
	"""Les marques-pages choisis dans la liste des marques-pages en base ; aucun si le choix est abandonné
	(https://github.com/dascritch/machincast/issues/167)."""
	return _choisir(Choix(MARQUES_PAGES, connexion, remarque, parent))


def _choisir(choix: Choix) -> list[int]:
	if choix.exec() != QDialog.DialogCode.Accepted:
		return []
	return choix.selection()


def regler_preferences(parent: QWidget, reglages: Reglages, sortie: SortieAudio) -> Reglages | None:
	"""Les préférences réglées dans leur fenêtre ; None si elle est abandonnée
	(https://github.com/dascritch/machincast/issues/145)."""
	fenetre = FenetrePreferences(reglages, sortie, parent)
	if fenetre.exec() != QDialog.DialogCode.Accepted:
		return None
	return fenetre.reglages()


def suggerer(parent: QWidget, manques: Manques) -> Reponse:
	"""La fenêtre modale des suggestions au lancement (https://github.com/dascritch/machincast/issues/119) : ce qu'il
	faut créer, ou rien sur « Plus tard »."""
	fenetre = FenetreSuggestions(manques, parent)
	fenetre.exec()
	return fenetre.reponse()


def montrer_version(parent: QWidget, texte: str) -> None:
	"""La version de MachinCast, et la date de sa dernière modification."""
	QMessageBox.information(parent, "Version de MachinCast", texte)


def ouvrir_page(adresse: str) -> None:
	"""Ouvre la page dans le navigateur web du poste."""
	QDesktopServices.openUrl(QUrl(adresse))


def ouvrir_dossier(dossier: Path) -> None:
	"""Ouvre le dossier dans le navigateur de fichiers du poste."""
	QDesktopServices.openUrl(QUrl.fromLocalFile(str(dossier)))
