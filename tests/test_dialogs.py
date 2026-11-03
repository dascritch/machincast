"""Scénarios des fenêtres de dialogue des fiches (https://github.com/dascritch/machincast/issues/31,
https://github.com/dascritch/machincast/issues/112, https://github.com/dascritch/machincast/issues/32).

Les vraies fenêtres s'ouvrent, hors de l'écran du poste : un minuteur y clique une fois la fenêtre modale ouverte. Le
sélecteur de répertoires et le navigateur de fichiers du poste sont remplacés.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
	QApplication,
	QCalendarWidget,
	QDialogButtonBox,
	QFileDialog,
	QLabel,
	QMessageBox,
	QWidget,
)
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.database import Role, open_connection
from machincast.interface import dialogs
from machincast.interface.choice import Choice
from tests.database_fixtures import sample_database_parameters
from tests.interface_steps import NAME, Connection, identifier
from tests.modals import when_modal

scenarios("dialogs.feature")


@dataclass
class Dialog:
	parent: QWidget
	text: str = ""
	precision: str = ""
	"""Le texte qui suit celui de la question."""
	title: str = ""
	actions: list[str] = field(default_factory=list)
	menus: list[object] = field(default_factory=list)
	"""Le menu du clic droit sur la première ligne d'un choix ; None sans menu."""
	buttons: list[str] = field(default_factory=list)
	response: object = None
	addresses: list[QUrl] = field(default_factory=list)
	departure: str = ""
	"""Le répertoire où le sélecteur de répertoires s'est ouvert."""


@pytest.fixture
def dialog(qtbot: QtBot) -> Iterator[Dialog]:
	parent = QWidget()
	qtbot.addWidget(parent)
	yield Dialog(parent)


def answer(dialog: Dialog, qtbot: QtBot, gesture: str) -> None:
	def make(modal: QWidget) -> None:
		assert isinstance(modal, QMessageBox), modal
		dialog.text = modal.text()
		dialog.precision = modal.informativeText()
		dialog.buttons = [button.text() for button in modal.buttons()]
		keys = {"tape Échap": Qt.Key.Key_Escape, "tape Entrée": Qt.Key.Key_Return}
		if gesture in keys:
			qtbot.keyClick(modal, keys[gesture])
			return
		(name,) = NAME.findall(gesture)
		(button,) = [button for button in modal.buttons() if button.text() == name]
		button.click()

	when_modal(make)


@when(parsers.parse("la question de fermeture de « {title} » s'ouvre, et que j'y {gesture}"))
def closing(dialog: Dialog, qtbot: QtBot, title: str, gesture: str) -> None:
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.confirm_closing(dialog.parent, title)


@when(parsers.parse("la question de rafraîchissement de « {title} » s'ouvre, et que j'y {gesture}"))
def refresh(dialog: Dialog, qtbot: QtBot, title: str, gesture: str) -> None:
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.confirm_closing(dialog.parent, title, "rafraîchir la fiche")


@when(parsers.parse("la question d'arrêt de « {title} » s'ouvre, et que j'y {gesture}"))
def stop(dialog: Dialog, qtbot: QtBot, title: str, gesture: str) -> None:
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.confirm_indexing_stop(dialog.parent, title)


@when(parsers.parse("l'avertissement de réintégration « {text} » s'ouvre, et que j'y {gesture}"))
def removal(dialog: Dialog, qtbot: QtBot, text: str, gesture: str) -> None:
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.confirm_removal(dialog.parent, text)


@when(parsers.parse("la question de suppression « {title} » s'ouvre, et que j'y {gesture}"))
def deletion(dialog: Dialog, qtbot: QtBot, title: str, gesture: str) -> None:
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.confirm_deletion(dialog.parent, title, "Supprimer le sonore « Spot » ?")


@when(
	parsers.parse("la confirmation de la maintenance, sauvegardes dans « {directory} », s'ouvre, et que j'y {gesture}")
)
def maintenance(dialog: Dialog, qtbot: QtBot, directory: str, gesture: str) -> None:
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.confirm_maintenance(dialog.parent, Path(directory))


@when(
	parsers.re(
		r"la confirmation de la maintenance, sauvegardes dans « (?P<directory>[^»]+) », s'ouvre, que j'y choisis"
		r" l'emplacement, que le sélecteur de répertoires donne « ?(?P<selector>[^»]*?) ?», puis que j'y clique sur"
		r" « (?P<button>[^»]+) »"
	)
)
def maintenance_elsewhere(
	dialog: Dialog, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, directory: str, selector: str, button: str
) -> None:
	"""Deux gestes : « Choisir l'emplacement… », qui ouvre le sélecteur, puis le bouton, dans la question rouverte."""

	def choose(_parent: QWidget, title: str, departure: str) -> str | None:
		dialog.title = title
		dialog.departure = departure
		return (selector) or (None)

	monkeypatch.setattr(dialogs, "choose_directory", choose)

	def choose_location(modal: QWidget) -> None:
		assert isinstance(modal, QMessageBox), modal
		(choice,) = [b for b in modal.buttons() if b.text() == dialogs.CHOOSE_LOCATION]
		choice.click()
		answer(dialog, qtbot, f"clique sur « {button} »")

	when_modal(choose_location)
	dialog.response = dialogs.confirm_maintenance(dialog.parent, Path(directory))


@then(parsers.parse("le sélecteur de répertoires s'est ouvert sur « {departure} »"))
def opened_on(dialog: Dialog, departure: str) -> None:
	assert dialog.departure == departure, dialog.departure
	assert dialog.title == "Emplacement de la sauvegarde de la base", dialog.title


@when(parsers.re(r"la confirmation de l'action « (?P<title>[^»]+) » s'ouvre, et que j'y (?P<gesture>.+)"))
def action(dialog: Dialog, qtbot: QtBot, title: str, gesture: str) -> None:
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.confirm_action(
		dialog.parent, title, "Désactiver 2 sonores ? Un sonore en aperçu reste en aperçu."
	)


@when(parsers.parse("la confirmation de l'action « {title} », au bouton « {button} », s'ouvre, et que j'y {gesture}"))
def action_to_button(dialog: Dialog, qtbot: QtBot, title: str, button: str, gesture: str) -> None:
	"""https://github.com/dascritch/machincast/issues/294"""
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.confirm_action(dialog.parent, title, "Ajouter 2 sonores ?", button)


@when(parsers.parse("la question après la vérification s'ouvre, et que j'y {gesture}"))
def after_check(dialog: Dialog, qtbot: QtBot, gesture: str) -> None:
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.offer_refresh(dialog.parent, "Vérification terminée : Neige, actif.")


@when(parsers.parse("la question de création s'ouvre, et que j'y {gesture}"))
def creation(dialog: Dialog, qtbot: QtBot, gesture: str) -> None:
	answer(dialog, qtbot, gesture)
	dialog.response = dialogs.confirm_creation(
		dialog.parent, "Créer un événement le dimanche 25 octobre 2026 de 13:00 à 14:00 ?"
	)


@when(parsers.parse("le choix d'un jour à partir du « {minimum} » s'ouvre, et que j'y {gesture}"))
def day_choice(dialog: Dialog, qtbot: QtBot, minimum: str, gesture: str) -> None:
	def make(modal: QWidget) -> None:
		(calendar,) = modal.findChildren(QCalendarWidget)
		(text,) = modal.findChildren(QLabel)
		dialog.text = text.text()
		chosen = re.search(r"choisis le « ([^»]+) »", gesture)
		if chosen is not None:
			day = date.fromisoformat(chosen.group(1))
			calendar.setSelectedDate(QDate(day.year, day.month, day.day))
		if gesture.endswith("clique sur OK"):
			(buttons,) = modal.findChildren(QDialogButtonBox)
			buttons.button(QDialogButtonBox.StandardButton.Ok).click()
			return
		key = Qt.Key.Key_Return
		if gesture.endswith("tape Échap"):
			key = Qt.Key.Key_Escape
		qtbot.keyClick((QApplication.focusWidget()) or (modal), key)

	when_modal(make)
	day = dialogs.choose_day(
		dialog.parent,
		"Sauter des sessions",
		"Sauter les sessions de « Matinale » à partir du jeudi 22 octobre, jusqu'au :",
		date.fromisoformat(minimum),
	)
	dialog.response = str(day)


@then(parsers.parse("le choix d'un jour a dit « {text} »"))
def day_says(dialog: Dialog, text: str) -> None:
	assert dialog.text == text


@when(parsers.re(r"le sélecteur de répertoires du poste donne « ?(?P<selector>[^»]*?) ?»"))
def selector(dialog: Dialog, monkeypatch: pytest.MonkeyPatch, selector: str) -> None:
	def choose(_parent: QWidget, _title: str, _departure: str = "") -> str:
		return selector

	monkeypatch.setattr(QFileDialog, "getExistingDirectory", choose)
	dialog.response = dialogs.choose_directory(dialog.parent)


@when(
	parsers.re(
		r"le choix des (?P<category>sonores|banques|séquences|feeds) s'ouvre,"
		r" avec la remarque « ?(?P<remark>[^»]*?) ?»,"
		r" et que j'y sélectionne tout, puis clique sur « (?P<button>[^»]+) »"
	)
)
def choice(dialog: Dialog, empty_database: Connection, category: str, remark: str, button: str) -> None:
	def make(modal: QWidget) -> None:
		assert isinstance(modal, Choice), modal
		dialog.title = modal.windowTitle()
		buttons = (modal.list_.ui.new, modal.list_.ui.add_files)
		dialog.actions = [button.text() for button in buttons if not button.isHidden()]
		dialog.actions += ["dépôt"] * modal.list_.table.acceptDrops()
		dialog.menus = [modal.list_.line_menu(modal.list_.proxy.index(0, 0))]
		dialog.text = modal.ui.explanation.text()
		modal.list_.table.selectAll()
		# « Annuler » est la traduction de Qt (qtbase_fr), que les tests ne chargent pas : le bouton se trouve par son
		# rôle.
		ok, cancel = QDialogButtonBox.StandardButton.Ok, QDialogButtonBox.StandardButton.Cancel
		standards = {"➕ Ajouter": ok, "Annuler": cancel}
		assert modal.ui.buttons.button(QDialogButtonBox.StandardButton.Ok).text() == "➕ Ajouter"
		modal.ui.buttons.button(standards[button]).click()

	when_modal(make)
	choose = {
		"sonores": dialogs.choose_sounds,
		"banques": dialogs.choose_banks,
		"séquences": dialogs.choose_sequences,
		"feeds": dialogs.choose_feeds,
	}[category]
	connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	try:
		dialog.response = choose(dialog.parent, connection, remark)
	finally:
		connection.close()


@when(
	parsers.re(
		r"le choix des banques s'ouvre, parmi (?P<names>«.+), et que j'y sélectionne tout,"
		r" puis clique sur « ➕ Ajouter »"
	)
)
def choice_among(dialog: Dialog, empty_database: Connection, names: str) -> None:
	def make(modal: QWidget) -> None:
		assert isinstance(modal, Choice), modal
		modal.list_.table.selectAll()
		modal.ui.buttons.button(QDialogButtonBox.StandardButton.Ok).click()

	when_modal(make)
	among = [
		int(str(line[0]))
		for name in NAME.findall(names)
		if (line := empty_database.execute("SELECT id FROM banks WHERE internal_name = %s", (name,)).fetchone())
	]
	connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	try:
		dialog.response = dialogs.choose_banks(dialog.parent, connection, "", among)
	finally:
		connection.close()


@when(parsers.parse("j'ouvre le dossier « {folder} »"))
def open_folder(dialog: Dialog, monkeypatch: pytest.MonkeyPatch, folder: str) -> None:
	def open_(address: QUrl) -> bool:
		dialog.addresses.append(address)
		return True

	monkeypatch.setattr(QDesktopServices, "openUrl", open_)
	dialogs.open_folder(Path(folder))


@then(parsers.parse("la question a précisé « {text} »"))
def precision(dialog: Dialog, text: str) -> None:
	assert dialog.precision == text


@then(parsers.parse("la question a dit « {text} »"))
def question(dialog: Dialog, text: str) -> None:
	assert dialog.text == text


@then(parsers.re(r"la question a proposé (?P<buttons>.+)"))
def offered_list(dialog: Dialog, buttons: str) -> None:
	assert sorted(dialog.buttons) == sorted(NAME.findall(buttons))


@then(parsers.parse("la réponse est « {response} »"))
def response(dialog: Dialog, response: str) -> None:
	assert str(dialog.response) == response


@then(parsers.re(r"le répertoire choisi est (?P<chosen>.+)"))
def directory(dialog: Dialog, chosen: str) -> None:
	expected = None
	if chosen != "aucun":
		(expected,) = NAME.findall(chosen)
	assert dialog.response == expected


@then(parsers.parse("le choix s'est intitulé « {title} »"))
def heading(dialog: Dialog, title: str) -> None:
	assert dialog.title == title


@then("le choix n'a proposé ni création ni ajout de fichiers")
def without_actions(dialog: Dialog) -> None:
	assert dialog.actions == []


@then(parsers.parse("le choix a expliqué « {text} »"))
def explains(dialog: Dialog, text: str) -> None:
	assert dialog.text == text


@then(parsers.re(r"les (?P<category>sonores|banques|séquences|feeds) choisi(?:e)?s sont (?P<names>.+)"))
def chosen_list(dialog: Dialog, empty_database: Connection, category: str, names: str) -> None:
	table, column = {
		"sonores": ("sounds", "title"),
		"banques": ("banks", "internal_name"),
		"séquences": ("sequences", "internal_name"),
		"feeds": ("feeds", "name"),
	}[category]
	assert dialog.response == [identifier(empty_database, table, column, name) for name in NAME.findall(names)]


@then(parsers.parse("le poste a ouvert l'adresse « {address} »"))
def address(dialog: Dialog, address: str) -> None:
	assert [url.toString() for url in dialog.addresses] == [address]


@then("le choix n'a proposé aucune action au clic droit")
def without_menu(dialog: Dialog) -> None:
	assert dialog.menus == [None]
