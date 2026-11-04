"""Fenêtres de dialogue des fiches (https://github.com/dascritch/machincast/issues/31).

Chaque question est une fonction de ce module, appelée par son nom (dialogs.confirm_closing(…)) : les scénarios
la remplacent par la réponse attendue, et aucune fenêtre modale n'attend un clic pendant les tests.
"""

import dataclasses
from datetime import date
from enum import StrEnum
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
	QCalendarWidget,
	QDialog,
	QDialogButtonBox,
	QFileDialog,
	QLabel,
	QMessageBox,
	QVBoxLayout,
	QWidget,
)

from machincast.configuration import ICON_EXTENSIONS, AudioOutput
from machincast.i18n import _, short_date
from machincast.interface import intents
from machincast.interface.choice import Choice
from machincast.interface.intents import label
from machincast.interface.lists import BANKS, FEEDS, SEQUENCES, SOUNDS
from machincast.interface.preferences import PreferencesWindow, Settings
from machincast.interface.suggestions import Response, Shortfalls, SuggestionsWindow
from machincast.interface.version import News
from machincast.protection import INDEXED_EXTENSIONS
from machincast.service import ABSENT, ServiceState


class Closing(StrEnum):
	"""Ce que devient une fiche modifiée qui se ferme."""

	SAVE = _("Save")
	ABANDON = _("Abandon")
	CANCEL = _("Cancel")


class Removal(StrEnum):
	"""Ce que devient un sonore retiré d'une banque, quand la prochaine indexation l'y remettra."""

	REMOVE = _("{remove} Remove anyway").format(remove=intents.REMOVE)
	OPEN_FOLDER = _("Open the folder")
	CANCEL = _("Cancel")


CHOOSE_LOCATION = _("Choose the location…")
"""Le bouton de la confirmation de la maintenance qui ouvre le sélecteur de répertoires."""


def confirm_closing(parent: QWidget, title: str, before: str = _("close the card")) -> Closing:
	"""Demande quoi faire des modifications d'une fiche, avant de la fermer ou de la rafraîchir : Entrée enregistre,
	Échap annule la fermeture ou le rafraîchissement de la fiche."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle(title)
	question.setText(_("“{title}” has changes that are not saved.").format(title=title))
	question.setInformativeText(_("Save them before you {before}?").format(before=before))
	# Le bouton du rôle AcceptRole répond à Entrée, celui du rôle RejectRole à Échap.
	save = question.addButton(Closing.SAVE.value, QMessageBox.ButtonRole.AcceptRole)
	abandon = question.addButton(Closing.ABANDON.value, QMessageBox.ButtonRole.DestructiveRole)
	question.addButton(Closing.CANCEL.value, QMessageBox.ButtonRole.RejectRole)
	question.exec()
	if question.clickedButton() is save:
		return Closing.SAVE
	if question.clickedButton() is abandon:
		return Closing.ABANDON
	return Closing.CANCEL


def confirm_indexing_stop(parent: QWidget, title: str) -> bool:
	"""Arrêter l'indexation en cours ? Entrée et Échap la laissent continuer."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle(title)
	question.setText(_("The indexing is running: “{title}”.").format(title=title))
	question.setInformativeText(
		_("Stop it? It stops after the current file; the work done is kept, the next indexing will take up the rest.")
	)
	halt = question.addButton(_("Stop"), QMessageBox.ButtonRole.DestructiveRole)
	continue_ = question.addButton(_("Continue"), QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(continue_)
	question.exec()
	return question.clickedButton() is halt


def confirm_removal(parent: QWidget, warning: str) -> Removal:
	"""Prévient qu'un sonore retiré reviendra : Entrée et Échap gardent le sonore."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Warning)
	question.setWindowTitle(_("Remove a sound"))
	question.setText(warning)
	remove = question.addButton(Removal.REMOVE.value, QMessageBox.ButtonRole.DestructiveRole)
	open_ = question.addButton(Removal.OPEN_FOLDER.value, QMessageBox.ButtonRole.ActionRole)
	cancel = question.addButton(Removal.CANCEL.value, QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(cancel)
	question.exec()
	if question.clickedButton() is remove:
		return Removal.REMOVE
	if question.clickedButton() is open_:
		return Removal.OPEN_FOLDER
	return Removal.CANCEL


def offer_refresh(parent: QWidget, text: str) -> bool:
	"""Après la vérification complète d'un sonore (https://github.com/dascritch/machincast/issues/190) : rafraîchir sa
	fiche ? Entrée rafraîchit, Échap laisse la fiche telle quelle."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle(_("Full check"))
	question.setText(_("{text} Refresh the card?").format(text=text))
	refresh = question.addButton(_("Refresh"), QMessageBox.ButtonRole.AcceptRole)
	question.addButton(_("Later"), QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(refresh)
	question.exec()
	return question.clickedButton() is refresh


def confirm_creation(parent: QWidget, text: str) -> bool:
	"""Créer un événement depuis le calendrier ? Rien n'est enregistré avant sa fiche : Entrée crée, Échap annule."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle(_("New event"))
	question.setText(text)
	create = question.addButton(_("Create"), QMessageBox.ButtonRole.AcceptRole)
	question.addButton(_("Cancel"), QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(create)
	question.exec()
	return question.clickedButton() is create


def choose_day(parent: QWidget, title: str, text: str, minimum: date) -> date | None:
	"""Un jour, à partir du minimum, proposé d'abord (https://github.com/dascritch/machincast/issues/273) : Entrée
	valide, Échap abandonne ; None pour un choix abandonné."""
	window = QDialog(parent)
	window.setWindowTitle(title)
	arrangement = QVBoxLayout(window)
	arrangement.addWidget(QLabel(text))
	calendar = QCalendarWidget()
	departure = QDate(minimum.year, minimum.month, minimum.day)
	calendar.setMinimumDate(departure)
	calendar.setSelectedDate(departure)
	calendar.setGridVisible(True)
	arrangement.addWidget(calendar)
	buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
	buttons.accepted.connect(window.accept)
	buttons.rejected.connect(window.reject)
	arrangement.addWidget(buttons)
	calendar.setFocus()
	if window.exec() != QDialog.DialogCode.Accepted:
		return None
	chosen = calendar.selectedDate()
	return date(chosen.year(), chosen.month(), chosen.day())


def confirm_deletion(parent: QWidget, title: str, text: str) -> bool:
	"""Demande la confirmation d'une suppression : Entrée et Échap gardent l'élément."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Warning)
	question.setWindowTitle(title)
	question.setText(text)
	delete = question.addButton(label(intents.DELETE, _("Delete")), QMessageBox.ButtonRole.DestructiveRole)
	cancel = question.addButton(_("Cancel"), QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(cancel)
	question.exec()
	return question.clickedButton() is delete


def confirm_action(parent: QWidget, title: str, text: str, button: str | None = None) -> bool:
	"""Une action sur plusieurs éléments à la fois (https://github.com/dascritch/machincast/issues/114) : Entrée la
	fait, Échap l'annule."""
	question = QMessageBox(parent)
	question.setIcon(QMessageBox.Icon.Question)
	question.setWindowTitle(title)
	question.setText(text)
	make = question.addButton((button) or (title), QMessageBox.ButtonRole.AcceptRole)
	question.addButton(_("Cancel"), QMessageBox.ButtonRole.RejectRole)
	question.setDefaultButton(make)
	question.exec()
	return question.clickedButton() is make


def warn_not_started(parent: QWidget, text: str, journal: list[str]) -> None:
	"""Le service a démarré, mais Machin player s'est arrêté aussitôt
	(https://github.com/dascritch/machincast/issues/376) : une alerte, que la barre d'état seule laisserait passer,
	avec les dernières lignes du journal du service en détails."""
	alert = QMessageBox(parent)
	alert.setIcon(QMessageBox.Icon.Warning)
	alert.setWindowTitle(_("Broadcast not started"))
	alert.setText(text)
	if journal:
		alert.setInformativeText(_("Last lines of the journal of the service:"))
		alert.setDetailedText("\n".join(journal))
	alert.exec()


def confirm_maintenance(parent: QWidget, backups: Path) -> Path | None:
	"""Lancer la maintenance de la base, qui écrit une sauvegarde dans sauvegardes, ou dans un autre répertoire choisi
	depuis la question ? L'emplacement de la sauvegarde, ou None si elle est annulée. Entrée et Échap l'annulent :
	elle ne se lance que par son bouton (https://github.com/dascritch/machincast/issues/127)."""
	while True:
		question = QMessageBox(parent)
		question.setIcon(QMessageBox.Icon.Question)
		question.setWindowTitle(_("Database maintenance"))
		question.setText(_("Are you sure you want to launch this operation?"))
		question.setInformativeText(_("A backup of the database will be saved at {backups}.").format(backups=backups))
		launch = question.addButton(_("Launch the maintenance"), QMessageBox.ButtonRole.AcceptRole)
		choose = question.addButton(CHOOSE_LOCATION, QMessageBox.ButtonRole.ActionRole)
		cancel = question.addButton(_("Cancel"), QMessageBox.ButtonRole.RejectRole)
		question.setDefaultButton(cancel)
		question.exec()
		if question.clickedButton() is launch:
			return backups
		if question.clickedButton() is not choose:
			return None
		# Un choix abandonné garde l'emplacement d'avant ; la question se repose, avec l'emplacement à jour.
		choice = choose_directory(parent, _("Location of the database backup"), str(backups))
		if choice is not None:
			backups = Path(choice)


def choose_files(parent: QWidget) -> list[Path]:
	"""Les fichiers choisis dans le sélecteur du poste, plusieurs à la fois ; aucun si le choix est abandonné."""
	patterns = " ".join(f"*{extension}" for extension in sorted(INDEXED_EXTENSIONS))
	chosen_list, _filter = QFileDialog.getOpenFileNames(
		parent, _("Add sound files"), "", _("Sound files ({patterns});;All files (*)").format(patterns=patterns)
	)
	return [Path(path) for path in chosen_list]


def choose_icon(parent: QWidget) -> Path | None:
	"""L'image choisie pour icône de l'application (https://github.com/dascritch/machincast/issues/111) ; None si le
	choix est abandonné."""
	patterns = " ".join(f"*{extension}" for extension in sorted(ICON_EXTENSIONS))
	path, _filter = QFileDialog.getOpenFileName(
		parent, _("Application icon"), "", _("Images ({patterns})").format(patterns=patterns)
	)
	if path == "":
		return None
	return Path(path)


def choose_export(
	parent: QWidget, offers: str, filters: list[str], title: str = _("Export the simulation")
) -> tuple[Path, str] | None:
	"""Le fichier où exporter, et le filtre choisi, qui en donne le format ; None si le choix est abandonné."""
	path, filter_ = QFileDialog.getSaveFileName(parent, title, str(Path.home() / offers), ";;".join(filters))
	if path == "":
		return None
	return Path(path), filter_


def choose_directory(
	parent: QWidget, title: str = _("Indexed directory of the bank"), departure: str = ""
) -> str | None:
	"""Un répertoire choisi dans le sélecteur du poste, ouvert sur depart, ou None si le choix est abandonné."""
	directory = QFileDialog.getExistingDirectory(parent, title, departure)
	if directory == "":
		return None
	return directory


def choose_sounds(parent: QWidget, connection: psycopg.Connection[TupleRow], remark: str = "") -> list[int]:
	"""Les sonores choisis dans la liste des sonores en base ; aucun si le choix est abandonné."""
	return _choose(Choice(SOUNDS, connection, remark, parent))


def choose_banks(
	parent: QWidget, connection: psycopg.Connection[TupleRow], remark: str = "", among: list[int] | None = None
) -> list[int]:
	"""Les banques choisies dans la liste des banques en base, ou parmi celles-ci seulement ; aucune si le choix est
	abandonné."""
	source = BANKS
	if among is not None:
		offered_list = set(among)
		source = dataclasses.replace(
			BANKS, read=lambda fetched: [line for line in BANKS.read(fetched) if line.identifier in offered_list]
		)
	return _choose(Choice(source, connection, remark, parent))


def choose_sequences(parent: QWidget, connection: psycopg.Connection[TupleRow], remark: str = "") -> list[int]:
	"""Les séquences choisies dans la liste des séquences en base ; aucune si le choix est abandonné."""
	return _choose(Choice(SEQUENCES, connection, remark, parent))


def choose_feeds(parent: QWidget, connection: psycopg.Connection[TupleRow], remark: str = "") -> list[int]:
	"""Les feeds choisis dans la liste des feeds en base ; aucun si le choix est abandonné
	(https://github.com/dascritch/machincast/issues/167)."""
	return _choose(Choice(FEEDS, connection, remark, parent))


def _choose(choice: Choice) -> list[int]:
	if choice.exec() != QDialog.DialogCode.Accepted:
		return []
	return choice.selection()


def set_preferences(
	parent: QWidget, settings: Settings, output: AudioOutput, service: ServiceState = ABSENT
) -> Settings | None:
	"""Les préférences réglées dans leur fenêtre ; None si elle est abandonnée
	(https://github.com/dascritch/machincast/issues/145). Le service de diffusion en marche verrouille la carte de
	l'antenne (https://github.com/dascritch/machincast/issues/339)."""
	window = PreferencesWindow(settings, output, parent, service)
	if window.exec() != QDialog.DialogCode.Accepted:
		return None
	return window.settings()


def suggest(parent: QWidget, gaps: Shortfalls, service: ServiceState = ABSENT) -> Response:
	"""La fenêtre modale des suggestions au lancement (https://github.com/dascritch/machincast/issues/119) : ce qu'il
	faut créer, et les cartes son choisies (https://github.com/dascritch/machincast/issues/339), ou rien sur « Plus
	tard »."""
	window = SuggestionsWindow(gaps, parent, service)
	window.exec()
	return window.response()


VERSION_LINKS = (
	(_("Code"), "https://github.com/dascritch/machincast/"),
	(_("Author: DaScritch"), "https://dascritch.com"),
	(_("For: \\<FMR\\>"), "https://radio-fmr.net"),
)
"""Les liens de la fenêtre de version, en Markdown (https://github.com/dascritch/machincast/issues/332)."""


def version_window(parent: QWidget | None, text: str, news: News | None) -> QMessageBox:
	"""La version de MachinCast, la date de sa publication ou de sa dernière modification, les liens vers le code,
	l'auteur et la radio (https://github.com/dascritch/machincast/issues/332), et les nouveautés de la version
	installée, si elle est publiée (https://github.com/dascritch/machincast/issues/208). Les liens s'ouvrent dans le
	navigateur web."""
	links = " · ".join(f"[{label}]({address})" for label, address in VERSION_LINKS)
	content = f"{text}\n\n{links}"
	if news is not None:
		content = _("{content}\n\n### What's new in version {version}\n\n{text}").format(
			content=content, version=news.version, text=news.text
		)
	window = QMessageBox(QMessageBox.Icon.Information, _("MachinCast version"), "", parent=parent)
	window.setTextFormat(Qt.TextFormat.MarkdownText)
	window.setText(content)
	caption = window.findChild(QLabel, "qt_msgbox_label")
	if caption is not None:
		caption.setOpenExternalLinks(True)
		caption.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
	return window


def show_version(parent: QWidget, text: str, news: News | None) -> None:
	version_window(parent, text, news).exec()


def show_news(parent: QWidget, news: News) -> None:
	"""Les nouveautés de la version, au premier lancement qui la découvre
	(https://github.com/dascritch/machincast/issues/208)."""
	window = QMessageBox(
		QMessageBox.Icon.Information,
		_("What's new in MachinCast {version}").format(version=news.version),
		_("### MachinCast {version}, published on {date}\n\n{text}").format(
			version=news.version, date=short_date(news.published_at), text=news.text
		),
		parent=parent,
	)
	window.setTextFormat(Qt.TextFormat.MarkdownText)
	window.exec()


def open_page(address: str) -> None:
	"""Ouvre la page dans le navigateur web du poste."""
	QDesktopServices.openUrl(QUrl(address))


def open_folder(folder: Path) -> None:
	"""Ouvre le dossier dans le navigateur de fichiers du poste."""
	QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
