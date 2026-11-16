"""Étapes partagées des scénarios de l'interface : Barre de menus et questions posées par les fenêtres de dialogue.

Chargé comme greffon pytest par tests/conftest.py (https://github.com/dascritch/machincast/issues/444 : découpé de
tests/interface_steps.py, par domaine).
"""

import re
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import (
	QIcon,
	QImage,
	QKeySequence,
)
from PySide6.QtWidgets import (
	QWidget,
)
from pytest_bdd import given, parsers, then, when
from pytestqt.qtbot import QtBot

from machincast import __version__, audio
from machincast.audio import Device
from machincast.configuration import AudioOutput
from tests.interface_steps import (
	NAME,
	TABLES,
	WAITING,
	Connection,
	Context,
	actions,
	deletion_button,
	deletion_questions,
	expected_lines,
	list_,
	menus,
	named_menu,
	window,
)

# ─── Barre de menus ────────────────────────────────────────


@when(parsers.parse("j'ouvre le menu « {menu} »"))
def open_menu(interface: Context, menu: str) -> None:
	"""L'ouverture du menu, qui relit ce qu'il montre (aboutToShow)."""
	named_menu(interface, menu).aboutToShow.emit()


@when(parsers.parse("j'appuie sur « {keys} »"))
def press(interface: Context, qtbot: QtBot, keys: str) -> None:
	"""Les touches vont au widget qui a le focus dans la fenêtre, activée ; à la fenêtre, si aucun ne l'a."""
	with qtbot.waitActive(window(interface)):
		window(interface).activateWindow()
	target: QWidget = window(interface)
	focus = window(interface).focusWidget()
	if focus is not None:
		target = focus
	combination = QKeySequence(keys)[0]
	qtbot.keyClick(target, combination.key(), combination.keyboardModifiers())


@then(parsers.re(r"la barre de menus a les menus (?P<titles>«.+)"))
def menu_bar(interface: Context, titles: str) -> None:
	under_menu_list = []
	for under_menu in menus(interface):
		under_menu_list.append(under_menu.title().replace("&", ""))
	assert under_menu_list == NAME.findall(titles)


@then(parsers.parse("le menu « {menu} » a les entrées :"))
def menu_entries(interface: Context, menu: str, datatable: list[list[str]]) -> None:
	"""Un séparateur s'écrit « — ». Une infobulle s'affiche au survol de son entrée, même inactive."""
	headers, *rows = datatable
	header_list = []
	for header in headers:
		header_list.append(header.strip())
	assert header_list == ["entrée", "état", "raccourci", "infobulle"]
	fetched_list = []

	def menu_action(action) -> None:
		if action.isSeparator():
			fetched_list.append(["—", "", "", ""])
			return
		tooltip = ""
		if action.toolTip() != action.text().replace("&", ""):
			tooltip = action.toolTip()
		state = "inactive"
		if action.isEnabled():
			state = "active"
		fetched_list.append([action.text(), state, action.shortcut().toString(), tooltip])

	for action in actions(interface, menu):
		menu_action(action)
	expected_list = []
	for row in rows:
		value_list = []
		for value in row:
			value_list.append(value.strip())
		expected_list.append(value_list)
	assert fetched_list == expected_list
	found = False
	for row in expected_list:
		if row[3] != "":
			found = True
			break
	if found:
		assert named_menu(interface, menu).toolTipsVisible()


@then(parsers.re(r"le menu « (?P<menu>[^»]+) » (?:ne )?propose (?:plus que )?(?P<titles>«.+»)(?:, qui [^«»]+)?$"))
def offered_menu(interface: Context, menu: str, titles: str) -> None:
	active_list = []
	for action in actions(interface, menu):
		if (action.isEnabled()) and (not action.isSeparator()):
			active_list.append(action)
	action_list = []
	for action in active_list:
		action_list.append(action.text())
	assert action_list == NAME.findall(titles)


@then(parsers.parse("le menu « {menu} » ne propose plus rien"))
def inactive_menu(interface: Context, menu: str) -> None:
	active_list = []
	for action in actions(interface, menu):
		if (action.isEnabled()) and (not action.isSeparator()):
			active_list.append(action)
	assert active_list == []


@then(parsers.parse("le navigateur web a ouvert « {address} »"))
def opened_page(interface: Context, address: str) -> None:
	"""« <version> » : le numéro de version de MachinCast (https://github.com/dascritch/machincast/issues/208)."""
	assert interface.opened_pages == [address.replace("<version>", __version__)]


def wait_check(interface: Context, qtbot: QtBot) -> None:
	checker = window(interface).checker
	qtbot.waitUntil(lambda: not checker.ongoing(), timeout=WAITING)


@when(parsers.re(r"j'ajoute les fichiers (?P<paths>aucun|«.+)"))
def add_files(interface: Context, qtbot: QtBot, paths: str) -> None:
	"""Depuis la liste des sonores ouverte, par le sélecteur de fichiers."""
	path_list = []
	for path in NAME.findall(paths):
		path_list.append(Path(interface.path(path)))
	interface.chosen_files = path_list
	qtbot.mouseClick(list_(interface).ui.add_files, Qt.MouseButton.LeftButton)


@when("la vérification des fichiers ajoutés se termine")
def finished_check(interface: Context, qtbot: QtBot) -> None:
	wait_check(interface, qtbot)


@then(parsers.parse("la barre d'état a annoncé « {text} »"))
def announces(interface: Context, text: str) -> None:
	assert interface.path_in(text) in interface.announcements, interface.announcements


@then("la barre d'état n'a rien annoncé")
def announced_nothing(interface: Context) -> None:
	assert interface.announcements == []


@when(parsers.re(r"je supprime l'élément de la fiche, en répondant « (?P<response>❌ Supprimer|Annuler) »"))
def delete(interface: Context, qtbot: QtBot, response: str) -> None:
	interface.deletion = response == "❌ Supprimer"
	qtbot.mouseClick(deletion_button(interface), Qt.MouseButton.LeftButton)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("la question de suppression, intitulée « {title} », a dit :"))
def question(interface: Context, title: str, datatable: list[list[str]]) -> None:
	assert deletion_questions(interface) == [f"suppression : {title}\n{expected_lines(interface, datatable)}"]


@then("la dernière question de suppression a dit :")
def last_question(interface: Context, datatable: list[list[str]]) -> None:
	_title, text = deletion_questions(interface)[-1].split("\n", 1)
	assert text == expected_lines(interface, datatable)


@then(
	parsers.re(
		r"(?P<category>le sonore|la banque|la séquence|l'événement|le feed) « (?P<name>[^»]+) »"
		r" (?P<state>n'est plus|est toujours|est marquée? « supprimée? ») en base"
	)
)
def in_database(empty_database: Connection, category: str, name: str, state: str) -> None:
	"""« Toujours en base » : pas supprimé ; « marqué « supprimé » » : supprimé, en attendant sa péremption
	(https://github.com/dascritch/machincast/issues/267). Un feed n'est jamais marqué : il quitte la base."""
	table, column = TABLES[category]
	marks = "NULL"
	if category != "le feed":
		marks = "deleted_at"
	lines = empty_database.execute(
		f"SELECT {marks} FROM {table} WHERE {column} = %s",
		(name,),
	).fetchall()
	match state:
		case "n'est plus":
			assert lines == [], lines
		case "est toujours":
			line_list = []
			for line in lines:
				line_list.append(line[0])
			assert line_list == [None], lines
		case _:
			assert (len(lines) == 1) and (lines[0][0] is not None), lines


@given("les périphériques audio du poste :")
def station_devices(monkeypatch: pytest.MonkeyPatch, datatable: list[list[str]]) -> None:
	"""Ceux que donnerait le fournisseur de périphériques de GStreamer, pour la pré-écoute et les préférences."""
	found_list = []
	for device_identifier, name in datatable[1:]:
		found_list.append(Device(device_identifier.strip(), name.strip()))

	def list_items(_output: AudioOutput) -> list[Device]:
		return found_list

	monkeypatch.setattr(audio, "devices", list_items)


CONFIGURATION_AUDIO = (
	r"(?:sortie « (?P<output>[^»]+) », )?"
	r"(?:sans périphérique d'antenne|avec le périphérique d'antenne « (?P<on_air>[^»]+) »)"
	r"(?: et de pré-écoute « (?P<preview>[^»]+) »)?"
)


@given(parsers.re(r"la configuration audio (?P<settings>.+)"))
def configuration_audio(interface: Context, settings: str) -> None:
	"""« sortie « pipewire », sans périphérique d'antenne » ou « avec le périphérique d'antenne « x » », suivi ou non
	de « et de pré-écoute « y » »."""
	found = re.fullmatch(CONFIGURATION_AUDIO, settings)
	assert found is not None, settings
	if found["output"] is not None:
		interface.audio["output"] = found["output"]
	interface.audio["device"] = found["on_air"]
	if found["preview"] is not None:
		interface.audio["preview"] = found["preview"]


@given(
	parsers.re(
		r"les préférences régleront (?:la sortie « (?P<output>[^»]+) », )?l'antenne « (?P<on_air>[^»]+) »"
		r" et la pré-écoute « (?P<preview>[^»]+) »"
	)
)
def rule_audio(interface: Context, output: str | None, on_air: str, preview: str) -> None:
	"""Avec la sortie, le type de sortie du bloc des cartes son (https://github.com/dascritch/machincast/issues/339)."""
	interface.audio_settings = (on_air, preview, output)  # type: ignore[assignment]


def same_icon(one: QIcon, other: QIcon, size: int = 24) -> bool:
	"""Deux icônes dessinent la même image, à cette taille ; une icône nulle n'est la même que nulle autre."""
	if (one.isNull()) or (other.isNull()):
		return False
	format_ = QImage.Format.Format_ARGB32
	return one.pixmap(size).toImage().convertToFormat(format_) == other.pixmap(size).toImage().convertToFormat(format_)
