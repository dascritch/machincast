"""Étapes partagées des scénarios de la fenêtre de l'interface : onglets, listes et fiches
(https://github.com/dascritch/machincast/issues/26, https://github.com/dascritch/machincast/issues/31,
https://github.com/dascritch/machincast/issues/112).

Chargé comme greffon pytest par tests/conftest.py. La fenêtre s'affiche hors de l'écran du poste
(QT_QPA_PLATFORM=offscreen, réglé par tests/conftest.py). Elle lit la base de test, avec le rôle de l'interface. Le
fixture « interface » tient la fenêtre et ce que le scénario en observe. À l'ouverture de la fenêtre, les fenêtres de
dialogue (machincast.interface.dialogs) sont remplacées par les réponses du scénario, qui note chaque question
posée : aucune fenêtre modale n'attend un clic.
"""

import dataclasses
import json
import re
import shutil
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
import shiboken6
import tomlkit
from PySide6.QtCore import QCoreApplication, QEvent, QMimeData, QModelIndex, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import (
	QAction,
	QDragEnterEvent,
	QDragLeaveEvent,
	QDragMoveEvent,
	QDropEvent,
	QIcon,
	QImage,
	QKeySequence,
)
from PySide6.QtWidgets import (
	QAbstractButton,
	QAbstractItemView,
	QApplication,
	QGroupBox,
	QLabel,
	QLineEdit,
	QListView,
	QMenu,
	QPushButton,
	QTabBar,
	QTabWidget,
	QWidget,
)
from pytest_bdd import given, parsers, then, when
from pytestqt.qtbot import QtBot

from machincast import __version__, audio
from machincast.audio import Device
from machincast.clock import FixedClock
from machincast.configuration import RETENTION, AudioOutput, Crossfades, DeadAirSettings, Interface, load
from machincast.database import Role, open_connection
from machincast.interface import dialogs, version
from machincast.interface.card import DELETE, REPORTED, Card
from machincast.interface.dialogs import Closing, Removal
from machincast.interface.lists import ANOMALY_COLUMN, IDENTIFIER, List
from machincast.interface.preferences import Settings
from machincast.interface.suggestions import Response, Shortfalls
from machincast.interface.window import MainWindow
from machincast.player.state import REREAD_GRID, Request, StateSocket
from machincast.service import ABSENT, ServiceState
from tests.database_fixtures import configuration_test, sample_database_parameters
from tests.sounds import SOUND_FILES

Connection = psycopg.Connection[tuple[object, ...]]
NAME = re.compile(r"« ([^»]+) »")
MODES = {"séquentielle": "sequential", "aléatoire": "random"}


ON_AIR_INDICATOR = re.compile(r"^(?:🟩|🟥) ")
"""Le témoin du service devant le titre de l'onglet Antenne (https://github.com/dascritch/machincast/issues/322)."""


def tab_title(tabs: QTabWidget, index: int) -> str:
	"""Le titre d'un onglet, sans le témoin du service devant celui de l'onglet Antenne."""
	return ON_AIR_INDICATOR.sub("", tabs.tabText(index))


@dataclass
class Context:
	directory: Path
	monkeypatch: pytest.MonkeyPatch
	clock: FixedClock | None = None
	window: MainWindow | None = None
	connection: Connection | None = None
	requests: list[tuple[str, int]] = field(default_factory=list)
	"""Écrans de détail demandés : genre et identifiant."""
	offered_list: list[str] = field(default_factory=list)
	"""Les noms de fichier proposés par le sélecteur d'export d'un tableau (https://github.com/dascritch/machincast/issues/329)."""
	questions: list[str] = field(default_factory=list)
	action_buttons: list[str | None] = field(default_factory=list)
	"""Le bouton qui confirme chaque action groupée, s'il n'est pas son titre (https://github.com/dascritch/machincast/issues/294)."""
	"""Questions posées par les fenêtres de dialogue, dans l'ordre."""
	closing: Closing = Closing.ABANDON
	"""Réponse à la question de fermeture d'une fiche modifiée."""
	removal: Removal = Removal.CANCEL
	maintenance: bool = True
	chosen_backups: Path | None = None
	"""L'emplacement des sauvegardes choisi dans la confirmation de la maintenance ; None : celui proposé."""
	"""Réponse à la confirmation de la maintenance de la base (https://github.com/dascritch/machincast/issues/127)."""
	"""Réponse à l'avertissement de réintégration d'un sonore retiré."""
	deletion: bool = False
	"""Réponse à la question de suppression : True pour supprimer."""
	creation: bool = False
	"""Réponse à la question de création d'un événement depuis le calendrier : True pour créer."""
	refresh_after_check: bool = True
	"""Réponse à la question après la vérification complète d'un sonore : True pour rafraîchir sa fiche
	(https://github.com/dascritch/machincast/issues/190)."""
	action: bool = True
	"""Réponse à la confirmation d'une action sur une sélection : True pour la faire
	(https://github.com/dascritch/machincast/issues/114)."""
	offered_banks: list[list[int] | None] = field(default_factory=list)
	"""Banques que chaque choix de banques a proposées ; None : toutes."""
	audio: dict[str, object] = field(default_factory=dict)
	"""Ce qui remplace la section [audio] de la configuration des tests : sortie, périphériques."""
	audio_settings: tuple[str, str, AudioOutput | None] | None = None
	"""Périphériques de l'antenne et de la pré-écoute que donnera la fenêtre des préférences ; None : inchangés."""
	shown_audio: list[tuple[str | None, str]] = field(default_factory=list)
	"""Périphériques de l'antenne et de la pré-écoute montrés par la fenêtre des préférences."""
	chosen_directories: list[str | None] = field(default_factory=list)
	"""Répertoires que donneront les choix suivants, None pour un choix abandonné."""
	chosen_sounds: list[int] = field(default_factory=list)
	"""Sonores que donnera le prochain choix."""
	chosen_banks: list[int] = field(default_factory=list)
	"""Banques que donnera le prochain choix."""
	chosen_sequences: list[int] = field(default_factory=list)
	chosen_feeds: list[int] = field(default_factory=list)
	"""Séquences que donnera le prochain choix."""
	remarks: list[str] = field(default_factory=list)
	"""Remarques des choix de sonores ou de banques ouverts."""
	opened_folders: list[Path] = field(default_factory=list)
	"""Dossiers ouverts dans le navigateur de fichiers."""
	closed_list: list[QWidget] = field(default_factory=list)
	"""Écrans des onglets que le scénario a fermés."""
	files: dict[Path, bytes] = field(default_factory=dict)
	"""Fichiers créés par le scénario, avec leur contenu."""
	drops: list[tuple[bool, Qt.DropAction]] = field(default_factory=list)
	"""Dépôts de fichiers : acceptés ou non, et l'action retenue."""
	chosen_files: list[Path] = field(default_factory=list)
	"""Fichiers que donnera le prochain choix de fichiers ; aucun pour un choix abandonné."""
	announcements: list[str] = field(default_factory=list)
	"""Messages de la barre d'état, dans l'ordre."""
	opened_pages: list[str] = field(default_factory=list)
	"""Adresses ouvertes dans le navigateur web du poste."""
	versions: list[str] = field(default_factory=list)
	"""Textes montrés par la fenêtre de version."""
	version_news: list[object] = field(default_factory=list)
	"""Les nouveautés montrées par la fenêtre de version, None sans elles (https://github.com/dascritch/machincast/issues/208)."""
	shown_news: list[object] = field(default_factory=list)
	"""Les nouveautés montrées au lancement."""
	configuration: Path | None = None
	"""Fichier de configuration de la fenêtre : une copie de celui des tests, dans le répertoire du scénario."""
	adjusted_preferences: Crossfades | None = None
	"""Ce que donnera la fenêtre des préférences ; None : elle est abandonnée."""
	shown_preferences: list[Crossfades] = field(default_factory=list)
	"""Les réglages que la fenêtre des préférences a montrés, à chaque ouverture."""
	rule_threshold: float | None = None
	"""Le seuil de silence que donnera la fenêtre des préférences (https://github.com/dascritch/machincast/issues/146) ;
	None : celui qu'elle a montré."""
	shown_thresholds: list[float] = field(default_factory=list)
	"""Les seuils de silence que la fenêtre des préférences a montrés, à chaque ouverture."""
	rule_dead_air: DeadAirSettings | None = None
	"""Le blanc dans un sonore que donnera la fenêtre des préférences
	(https://github.com/dascritch/machincast/issues/122) ; None : celui qu'elle a montré."""
	shown_dead_airs: list[DeadAirSettings] = field(default_factory=list)
	"""Les blancs dans un sonore que la fenêtre des préférences a montrés, à chaque ouverture."""
	adjusted_retention: int | None = None
	"""La durée de péremption, en jours, que donnera la fenêtre des préférences
	(https://github.com/dascritch/machincast/issues/268) ; None : celle qu'elle a montrée."""
	shown_retentions: list[int] = field(default_factory=list)
	chosen_days: list[date | None] = field(default_factory=list)
	"""Ce que donneront les prochains choix d'un jour, None pour un choix abandonné
	(https://github.com/dascritch/machincast/issues/273)."""
	day_choice: list[tuple[str, date]] = field(default_factory=list)
	"""Le texte et le premier jour possible de chaque choix d'un jour."""
	active_suggestions: bool = False
	"""Les scénarios n'ont pas de suggestions au lancement, sauf ceux qui les activent
	(https://github.com/dascritch/machincast/issues/119) : sans elles, le fil musical est recréé comme avant."""
	response_to_suggestions: Callable[[Shortfalls], Response] = lambda _gaps: Response(create=False)
	"""Ce que donnera la fenêtre des suggestions, d'après ce qu'elle propose : « Plus tard » par défaut."""
	done_suggestions: list[Shortfalls] = field(default_factory=list)
	"""Ce que la fenêtre des suggestions a proposé, à chaque lancement."""
	response_duration: float = 0.0
	"""Temps qu'a pris la dernière action mesurée, en secondes (https://github.com/dascritch/machincast/issues/194)."""
	adjusted_clipping: bool | None = None
	"""Le voyant « Saturation » que donnera la fenêtre des préférences ; None : inchangé
	(https://github.com/dascritch/machincast/issues/191)."""
	shown_clippings: list[bool] = field(default_factory=list)
	"""Le voyant « Saturation » montré par la fenêtre des préférences, à chaque ouverture."""
	adjusted_icon: tuple[Path | None] | None = None
	"""L'icône que donnera la fenêtre des préférences, None dans le tuple pour celle de MachinCast ; None : inchangée
	(https://github.com/dascritch/machincast/issues/111)."""
	shown_icons: list[Path | None] = field(default_factory=list)
	"""L'icône montrée par la fenêtre des préférences, à chaque ouverture."""
	initial_configuration: bytes = b""
	"""Le fichier de configuration à l'ouverture de la fenêtre."""

	def path_in(self, text: str) -> str:
		"""Chaque « …/ » du texte désigne le répertoire temporaire du scénario."""
		return text.replace("…/", f"{self.directory}/")

	def path(self, text: str) -> str:
		"""Un chemin qui commence par « …/ » est dans le répertoire temporaire du scénario."""
		if text.startswith("…/"):
			return f"{self.directory}/{text.removeprefix('…/')}"
		return text


@pytest.fixture
def interface(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Context]:
	# monkeypatch est demandé ici, avant qtbot : la fenêtre se ferme en fin de scénario, dialogues encore remplacés.
	interface = Context(tmp_path, monkeypatch)
	yield interface
	if interface.window is not None:
		interface.window.close()
	if interface.connection is not None:
		interface.connection.close()
	# pytest-qt a fermé la fenêtre et demandé sa suppression (deleteLater), qui n'est faite que dans une boucle
	# d'événements : elle se fait ici, avec celle de ce que la fenêtre emporte. Sinon, les fenêtres des scénarios qui
	# n'attendent rien s'accumulent, et le premier scénario qui attend les supprime toutes, au détriment de son délai
	# (https://github.com/dascritch/machincast/issues/262).
	QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


CHANGE_QUESTIONS = {"fermer la fiche": "fermeture", "rafraîchir la fiche": "rafraîchissement"}
"""La question sur les modifications d'une fiche, selon ce qui l'a posée."""


def replace_dialogs(interface: Context) -> None:
	"""Les fenêtres de dialogue donnent les réponses du scénario, et notent les questions posées."""
	monkeypatch = interface.monkeypatch

	def closing(_parent: QWidget, title: str, before: str = "fermer la fiche") -> Closing:
		interface.questions.append(f"{CHANGE_QUESTIONS[before]} : {title}")
		return interface.closing

	def removal(_parent: QWidget, warning: str) -> Removal:
		interface.questions.append(f"retrait : {warning}")
		return interface.removal

	def deletion(_parent: QWidget, title: str, text: str) -> bool:
		interface.questions.append(f"suppression : {title}\n{text}")
		return interface.deletion

	def creation(_parent: QWidget, text: str) -> bool:
		interface.questions.append(f"création : {text}")
		return interface.creation

	def directory(_parent: QWidget, *_title_and_departure: str) -> str | None:
		return interface.chosen_directories.pop(0)

	def sounds(_parent: QWidget, _connection: Connection, remark: str = "") -> list[int]:
		interface.remarks.append(remark)
		return interface.chosen_sounds

	def banks(_parent: QWidget, _connection: Connection, remark: str = "", among: list[int] | None = None) -> list[int]:
		interface.remarks.append(remark)
		interface.offered_banks.append(among)
		return interface.chosen_banks

	def action(_parent: QWidget, title: str, text: str, button: str | None = None) -> bool:
		interface.questions.append(f"action : {title}\n{text}")
		interface.action_buttons.append(button)
		return interface.action

	monkeypatch.setattr(dialogs, "confirm_closing", closing)
	monkeypatch.setattr(dialogs, "confirm_removal", removal)
	monkeypatch.setattr(dialogs, "confirm_deletion", deletion)
	monkeypatch.setattr(dialogs, "confirm_creation", creation)
	monkeypatch.setattr(dialogs, "confirm_action", action)

	def maintenance(_parent: QWidget, backups: Path) -> Path | None:
		interface.questions.append(f"maintenance : {backups}")
		if not interface.maintenance:
			return None
		return (interface.chosen_backups) or (backups)

	monkeypatch.setattr(dialogs, "confirm_maintenance", maintenance)

	def after_check(_parent: QWidget, text: str) -> bool:
		interface.questions.append(f"après vérification : {text} Rafraîchir la fiche ?")
		return interface.refresh_after_check

	monkeypatch.setattr(dialogs, "offer_refresh", after_check)
	monkeypatch.setattr(dialogs, "choose_directory", directory)
	monkeypatch.setattr(dialogs, "choose_files", lambda _parent: interface.chosen_files)
	monkeypatch.setattr(dialogs, "choose_sounds", sounds)

	def sequences(_parent: QWidget, _connection: Connection, remark: str = "") -> list[int]:
		interface.remarks.append(remark)
		return interface.chosen_sequences

	def feeds(_parent: QWidget, _connection: Connection, remark: str = "") -> list[int]:
		interface.remarks.append(remark)
		return interface.chosen_feeds

	monkeypatch.setattr(dialogs, "choose_banks", banks)
	monkeypatch.setattr(dialogs, "choose_sequences", sequences)
	monkeypatch.setattr(dialogs, "choose_feeds", feeds)
	monkeypatch.setattr(dialogs, "open_folder", interface.opened_folders.append)
	monkeypatch.setattr(dialogs, "open_page", interface.opened_pages.append)

	def show_version(_parent: QWidget, text: str, news: version.News | None) -> None:
		interface.versions.append(text)
		interface.version_news.append(news)

	monkeypatch.setattr(dialogs, "show_version", show_version)
	monkeypatch.setattr(dialogs, "show_news", lambda _parent, news: interface.shown_news.append(news))

	def day(_parent: QWidget, _title: str, text: str, minimum: date) -> date | None:
		interface.day_choice.append((text, minimum))
		return interface.chosen_days.pop(0)

	monkeypatch.setattr(dialogs, "choose_day", day)

	def preferences(
		_parent: QWidget, shown_list: Settings, _output: AudioOutput, _service: ServiceState = ABSENT
	) -> Settings | None:
		"""Les crossfades et les périphériques du scénario ; ceux qu'il ne règle pas restent ceux montrés."""
		interface.shown_preferences.append(shown_list.crossfades)
		interface.shown_audio.append((shown_list.on_air, shown_list.preview))
		interface.shown_thresholds.append(shown_list.silence_threshold)
		interface.shown_dead_airs.append(shown_list.dead_air)
		interface.shown_retentions.append(shown_list.retention)
		interface.shown_clippings.append(shown_list.clipping)
		interface.shown_icons.append(shown_list.icon)
		if (
			(interface.adjusted_preferences is None)
			and (interface.audio_settings is None)
			and (interface.rule_threshold is None)
			and (interface.rule_dead_air is None)
			and (interface.adjusted_retention is None)
			and (interface.adjusted_clipping is None)
			and (interface.adjusted_icon is None)
		):
			return None
		on_air, preview, output = (interface.audio_settings) or ((shown_list.on_air, shown_list.preview, None))
		threshold = shown_list.silence_threshold
		if interface.rule_threshold is not None:
			threshold = interface.rule_threshold
		clipping = shown_list.clipping
		if interface.adjusted_clipping is not None:
			clipping = interface.adjusted_clipping
		icon = shown_list.icon
		if interface.adjusted_icon is not None:
			icon = interface.adjusted_icon[0]
		retention = shown_list.retention
		if interface.adjusted_retention is not None:
			retention = interface.adjusted_retention
		return Settings(
			(interface.adjusted_preferences) or (shown_list.crossfades),
			on_air,
			preview,
			threshold,
			clipping,
			shown_list.suggestions,
			icon,
			retention,
			(interface.rule_dead_air) or (shown_list.dead_air),
			output,
		)

	monkeypatch.setattr(dialogs, "set_preferences", preferences)

	def suggest(_parent: QWidget, gaps: Shortfalls, _service: ServiceState = ABSENT) -> Response:
		interface.done_suggestions.append(gaps)
		return interface.response_to_suggestions(gaps)

	monkeypatch.setattr(dialogs, "suggest", suggest)


def configuration_file(interface: Context) -> Path:
	"""La copie du fichier de configuration des tests dans le répertoire du scénario, créée au besoin."""
	if interface.configuration is None:
		interface.configuration = interface.directory / "machincast.toml"
		shutil.copyfile(configuration_test().path, interface.configuration)
	return interface.configuration


def window(interface: Context) -> MainWindow:
	assert interface.window is not None
	return interface.window


def list_(interface: Context) -> List:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, List), opened
	return opened


def lines(interface: Context) -> list[dict[str, str]]:
	"""Les lignes affichées, après filtre et tri, par titre de colonne."""
	model = list_(interface).table.model()
	titles = [
		str(model.headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole))
		for column in range(model.columnCount())
	]
	return [
		{title: str((model.index(row, column).data()) or ("")) for column, title in enumerate(titles)}
		for row in range(model.rowCount())
	]


def opened_card(interface: Context) -> Card:
	opened = window(interface).ui.tabs.currentWidget()
	assert isinstance(opened, Card), opened
	return opened


def tab(interface: Context, title: str) -> int:
	tabs = window(interface).ui.tabs
	titles = [tab_title(tabs, index) for index in range(tabs.count())]
	assert title in titles, titles
	return titles.index(title)


def closing_button(bar: QTabBar, index: int) -> QWidget | None:
	"""Le bouton de fermeture d'un onglet, à gauche ou à droite selon le style."""
	for side in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
		button = bar.tabButton(index, side)
		if button is not None:
			return button
	return None


def type_(qtbot: QtBot, field: QLineEdit, text: str) -> None:
	"""Vide le champ, puis y tape le texte."""
	field.clear()
	for letter in text:
		# QTest ne sait taper que l'ASCII : une lettre accentuée s'insère comme le ferait une méthode de saisie.
		if letter.isascii():
			qtbot.keyClicks(field, letter)
		else:
			field.insert(letter)


def open_in(qtbot: QtBot, table: QAbstractItemView, name: str) -> None:
	"""Double-clic sur la ligne d'une table dont une cellule est le nom."""
	model = table.model()
	columns = 1
	if not isinstance(table, QListView):
		# Le modèle d'une liste n'a qu'une colonne, et ne dit pas son nombre.
		columns = model.columnCount()
	found: QModelIndex | None = None
	for row in range(model.rowCount()):
		for column in range(columns):
			if model.index(row, column).data() == name:
				found = model.index(row, column)
	assert found is not None, f"aucune ligne « {name} »"
	table.scrollTo(found)
	centre = table.visualRect(found).center()
	qtbot.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)
	qtbot.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=centre)


def slide(interface: Context, list_: QAbstractItemView, what: str, drop_in: bool, relocation: bool) -> None:
	"""Un glisser venu du navigateur de fichiers, qui propose la copie, le déplacement et le lien. Maj est enfoncée :
	le navigateur propose le déplacement, que la fiche doit changer en copie. « un texte » glisse du texte, sans
	fichier ; un chemin en https:// est une adresse web. Le dépôt est noté dans interface.drops."""
	target = list_.viewport()
	data = QMimeData()
	if what == "un texte":
		data.setText("Café à minuit")
	else:
		addresses = []
		for path in NAME.findall(what):
			address = QUrl(path)
			if not path.startswith("https://"):
				address = QUrl.fromLocalFile(interface.path(path))
			addresses.append(address)
		data.setUrls(addresses)
	actions = Qt.DropAction.CopyAction | Qt.DropAction.MoveAction | Qt.DropAction.LinkAction
	if relocation:
		actions = Qt.DropAction.MoveAction
	centre = target.rect().center()
	button, keys = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier
	QApplication.sendEvent(target, QDragEnterEvent(centre, actions, data, button, keys))
	QApplication.sendEvent(target, QDragMoveEvent(centre, actions, data, button, keys))
	if not drop_in:
		QApplication.sendEvent(target, QDragLeaveEvent())
		return
	drop = QDropEvent(QPointF(centre), actions, data, button, keys)
	assert drop.proposedAction() == Qt.DropAction.MoveAction
	QApplication.sendEvent(target, drop)
	interface.drops.append((drop.isAccepted(), drop.dropAction()))


def duration_or_none(seconds: str) -> timedelta | None:
	"""Une durée en secondes ; aucune pour une cellule vide."""
	if seconds == "":
		return None
	return timedelta(seconds=int(seconds))


def date_or_none(text: str) -> datetime | None:
	"""« 2026-10-12 20:00 » en heure du poste ; aucune pour une cellule vide."""
	if text == "":
		return None
	return datetime.fromisoformat(text).astimezone()


def identifier(database: Connection, table: str, column: str, value: str) -> int:
	line = database.execute(f"SELECT id FROM {table} WHERE {column} = %s", (value,)).fetchone()  # noqa: S608
	assert line is not None, f"{value} absent de {table}"
	return int(str(line[0]))


def deletion_button(interface: Context) -> QPushButton:
	(button,) = [button for button in opened_card(interface).findChildren(QPushButton) if button.text() == DELETE]
	return button


def deletion_questions(interface: Context) -> list[str]:
	return [question for question in interface.questions if question.startswith("suppression : ")]


def expected_lines(interface: Context, datatable: list[list[str]]) -> str:
	_header, *lines = datatable
	return "\n".join(line[0].strip().replace("…/", f"{interface.directory}/") for line in lines)


TABLES = {
	"le sonore": ("sounds", "title"),
	"la banque": ("banks", "internal_name"),
	"la séquence": ("sequences", "internal_name"),
	"l'événement": ("events", "internal_name"),
	"le feed": ("feeds", "name"),
}
"""Table et colonne du nom de chaque genre d'élément, pour le retrouver en base."""


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'horloge de l'interface au « {instant} »"))
def clock(interface: Context, instant: str) -> None:
	interface.clock = FixedClock(datetime.fromisoformat(instant).astimezone())


@given("les sonores :")
def sounds(interface: Context, empty_database: Connection, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	for values in rows:
		line = dict(zip(headers, (v.strip() for v in values), strict=True))
		line["location"] = interface.path(line["location"])
		stream = line["type"] == "stream"
		empty_database.execute(
			"INSERT INTO sounds (type, location, stream_url, artist, title, state, duration)"
			" VALUES (%s, %s, %s, %s, %s, %s, %s)",
			(
				line["type"],
				None if stream else line["location"],
				line["location"] if stream else None,
				(line["artist"]) or (None),
				(line["title"]) or (None),
				line["state"],
				duration_or_none(line["duration"]),
			),
		)


@given(parsers.re(r"les dossiers (?P<paths>.+) du scénario"))
def scenario_folders(interface: Context, paths: str) -> None:
	for path in NAME.findall(paths):
		Path(interface.path(path)).mkdir(parents=True)


@given(parsers.re(r"les fichiers (?P<paths>.+) du scénario"))
def scenario_files(interface: Context, paths: str) -> None:
	for path in NAME.findall(paths):
		file = Path(interface.path(path))
		file.parent.mkdir(parents=True, exist_ok=True)
		interface.files[file] = f"contenu de {file.name}".encode()
		file.write_bytes(interface.files[file])


@given(
	parsers.re(
		r"la banque « (?P<name>[^»]+) », (?P<mode>séquentielle|aléatoire),"
		r" (?:de nom public « (?P<public_name>[^»]+) »|sans nom public)"
		r"(?P<marked>, marquée « ne pas répéter »)?, avec (?P<list_>.+)"
	)
)
def bank(
	empty_database: Connection, name: str, mode: str, public_name: str | None, marked: str | None, list_: str
) -> None:
	created = empty_database.execute(
		"INSERT INTO banks (internal_name, public_name, mode, no_repeat) VALUES (%s, %s, %s, %s) RETURNING id",
		(name, public_name, MODES[mode], marked is not None),
	).fetchone()
	assert created is not None
	for position, title in enumerate(NAME.findall(list_), start=1):
		empty_database.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
			(created[0], identifier(empty_database, "sounds", "title", title), position),
		)


@given(parsers.re(r"les répertoires (?P<list_>.+) de la banque « (?P<name>[^»]+) »"))
def directories(interface: Context, empty_database: Connection, list_: str, name: str) -> None:
	bank = identifier(empty_database, "banks", "internal_name", name)
	for directory in NAME.findall(list_):
		empty_database.execute(
			"INSERT INTO bank_directories (bank_id, directory) VALUES (%s, %s)",
			(bank, interface.path(directory)),
		)


ITEM = re.compile(r"(le sonore|la banque|la séquence) « ([^»]+) »")
ITEMS = r"(?:le sonore|la banque|la séquence) « [^»]+ »(?:, (?:le sonore|la banque|la séquence) « [^»]+ »)*"
"""Une liste d'éléments : « le sonore « Jingle », la banque « Publicité », la séquence « Passage pub » »."""
REFERENCES = {
	"le sonore": ("sounds", "title", "sound_id"),
	"la banque": ("banks", "internal_name", "bank_id"),
	"la séquence": ("sequences", "internal_name", "sequence_id"),
}
"""Table, colonne du nom et colonne de la liste de chaque genre d'élément."""


@given(
	parsers.re(
		r"la séquence « (?P<name>[^»]+) », (?:de nom public « (?P<public_name>[^»]+) »|sans nom public),"
		rf" avec (?P<items>{ITEMS}|rien)"
	)
)
def sequence(empty_database: Connection, name: str, public_name: str | None, items: str) -> None:
	"""Chaque sonore par son titre, chaque banque par son nom, dans l'ordre."""
	created = empty_database.execute(
		"INSERT INTO sequences (internal_name, public_name) VALUES (%s, %s) RETURNING id", (name, public_name)
	).fetchone()
	assert created is not None
	for position, (category, item) in enumerate(ITEM.findall(items), start=1):
		table, column, reference = REFERENCES[category]
		empty_database.execute(
			f"INSERT INTO sequence_items (sequence_id, position, {reference}) VALUES (%s, %s, %s)",  # noqa: S608
			(created[0], position, identifier(empty_database, table, column, item)),
		)


@given(parsers.re(rf"l'événement « (?P<event>[^»]+) » joue (?P<items>{ITEMS})"))
def playing_event(empty_database: Connection, event: str, items: str) -> None:
	"""Les éléments s'ajoutent en fin de la liste de l'événement, dans l'ordre."""
	number = identifier(empty_database, "events", "internal_name", event)
	for category, item in ITEM.findall(items):
		table, column, reference = REFERENCES[category]
		empty_database.execute(
			f"INSERT INTO event_items (event_id, position, {reference})"  # noqa: S608
			" SELECT %s, COALESCE(MAX(position), 0) + 1, %s FROM event_items WHERE event_id = %s",
			(number, identifier(empty_database, table, column, item), number),
		)


@given(parsers.parse("le stream « {title} » a pour événement de secours « {fallback} »"))
def rescued_stream(empty_database: Connection, title: str, fallback: str) -> None:
	empty_database.execute(
		"UPDATE sounds SET fallback_event_id = %s WHERE title = %s",
		(identifier(empty_database, "events", "internal_name", fallback), title),
	)


@given(parsers.re(r"les feeds (?P<marks>.+)"))
def feeds(empty_database: Connection, marks: str) -> None:
	names = NAME.findall(marks)
	for name, url in zip(names[::2], names[1::2], strict=True):
		empty_database.execute("INSERT INTO feeds (name, url) VALUES (%s, %s)", (name, url))


@given(parsers.re(r"(?:les streams|le stream) (?P<titles>.+) (?:suivent|suit) le feed « (?P<marks>[^»]+) »"))
def follow(empty_database: Connection, titles: str, marks: str) -> None:
	for title in NAME.findall(titles):
		empty_database.execute(
			"UPDATE sounds SET stream_url = NULL, feed_id = %s WHERE title = %s",
			(identifier(empty_database, "feeds", "name", marks), title),
		)


def _minutes(text: str | None) -> timedelta | None:
	"""« 2:00 » : deux minutes ; None sans texte."""
	if text is None:
		return None
	minutes, seconds = text.split(":")
	return timedelta(minutes=int(minutes), seconds=int(seconds))


@given(
	parsers.re(
		r"la banque « (?P<name>[^»]+) » veut des sonores"
		r" (?:de (?P<de>[\d:]+) à (?P<a>[\d:]+)"
		r"|d'au moins (?P<at_least>[\d:]+)(?: et d'au plus (?P<then_at_most>[\d:]+))?"
		r"|d'au plus (?P<at_most>[\d:]+))$"
	)
)
def bank_durations(
	empty_database: Connection,
	name: str,
	de: str | None,
	a: str | None,
	at_least: str | None,
	then_at_most: str | None,
	at_most: str | None,
) -> None:
	"""Les durées minimale et maximale des sonores de la banque (https://github.com/dascritch/machincast/issues/147)."""
	minimum = _minutes((de) or (at_least))
	maximum = _minutes((a) or (then_at_most) or (at_most))
	empty_database.execute(
		"UPDATE banks SET min_duration = %s, max_duration = %s WHERE internal_name = %s", (minimum, maximum, name)
	)


@when(parsers.parse("le feed « {name} » est effacé de la base"))
def erase_feed(empty_database: Connection, name: str) -> None:
	empty_database.execute("DELETE FROM feeds WHERE name = %s", (name,))


@given(parsers.parse("le fichier de test « {source} » copié en « {path} »"))
def copies(interface: Context, source: str, path: str) -> None:
	file = Path(interface.path(path))
	file.parent.mkdir(parents=True, exist_ok=True)
	shutil.copyfile(SOUND_FILES / source, file)
	interface.files[file] = file.read_bytes()


@given(parsers.parse("le fichier « {path} », qui n'est pas un son"))
def fake_sound(interface: Context, path: str) -> None:
	file = Path(interface.path(path))
	file.parent.mkdir(parents=True, exist_ok=True)
	interface.files[file] = b"Ceci n'est pas un son."
	file.write_bytes(interface.files[file])


@given("les événements :")
def events(empty_database: Connection, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	for values in rows:
		line = dict(zip(headers, (v.strip() for v in values), strict=True))
		empty_database.execute(
			"INSERT INTO events (internal_name, public_name, priority, starts_at, ends_at, recurrence_days)"
			" VALUES (%s, %s, %s, %s, %s, %s::weekday[])",
			(
				line["name"],
				(line["public_name"]) or (None),
				line["priority"],
				date_or_none(line["starts_at"]),
				date_or_none(line["ends_at"]),
				[day.strip() for day in line["days"].split(",") if day.strip()],
			),
		)


HISTORY_CATEGORIES = {
	"du sonore": "le sonore",
	"de la banque": "la banque",
	"de la séquence": "la séquence",
	"de l'événement": "l'événement",
}
HISTORY_CARDS = {
	"le sonore": "sonore",
	"la banque": "banque",
	"la séquence": "séquence",
	"l'événement": "événement",
}


@when(
	parsers.re(
		r"j'ouvre depuis l'historique la fiche (?P<de>du sonore|de la banque|de la séquence|de l'événement)"
		r" « (?P<name>[^»]+) »"
	)
)
def open_since_history(interface: Context, empty_database: Connection, qtbot: QtBot, de: str, name: str) -> None:
	"""Comme un double-clic sur sa cellule de l'airplay, des incidents ou du calendrier : par son identifiant, l'élément
	supprimé d'abord, quand un autre a repris son nom."""
	category = HISTORY_CATEGORIES[de]
	table, column = TABLES[category]
	line = empty_database.execute(
		f"SELECT id FROM {table} WHERE {column} = %s ORDER BY deleted_at IS NULL, id",  # noqa: S608
		(name,),
	).fetchone()
	assert line is not None, name
	window(interface)._open(HISTORY_CARDS[category], int(str(line[0])), name)


@given(parsers.parse("la session du {day} de l'événement « {name} » est sautée"))
@when(parsers.parse("la session du {day} de l'événement « {name} » est sautée"))
def skipped_session(empty_database: Connection, day: str, name: str) -> None:
	"""Comme depuis le calendrier (https://github.com/dascritch/machincast/issues/273), pour l'interface comme pour la
	diffusion."""
	empty_database.execute(
		"INSERT INTO event_skips (event_id, day) SELECT id, %s FROM events WHERE internal_name = %s",
		(date.fromisoformat(day), name),
	)


# ─── Quand ─────────────────────────────────────────────────


@when("la fenêtre de l'interface s'ouvre")
def open_(interface: Context, empty_database: Connection, qtbot: QtBot) -> None:
	open_window(interface, qtbot)


@when("la fenêtre de l'interface se ferme, puis s'ouvre de nouveau")
def reopen(interface: Context, qtbot: QtBot) -> None:
	window(interface).close()
	open_window(interface, qtbot)


def open_window(interface: Context, qtbot: QtBot, with_configuration: bool = True) -> None:
	"""La fenêtre de l'interface, sur une copie du fichier de configuration des tests ; sans lui, elle ne peut pas
	enregistrer ses préférences."""
	assert interface.clock is not None
	replace_dialogs(interface)
	interface.connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	path: Path | None = None
	crossfades = None
	silences = None
	dead_air = None
	retention = RETENTION
	interface_settings = None
	audio = configuration_test().audio
	if with_configuration:
		path = configuration_file(interface)
		interface.initial_configuration = path.read_bytes()
		crossfades = load(path).crossfades
		silences = load(path).silences
		dead_air = load(path).dead_air
		retention = load(path).database.retention
		interface_settings = load(path).interface
		audio = load(path).audio
	if not interface.active_suggestions:
		interface_settings = dataclasses.replace((interface_settings) or (Interface()), suggestions=False)
	audio = dataclasses.replace(audio, **interface.audio)  # type: ignore[arg-type]
	interface.window = MainWindow(
		interface.connection,
		interface.directory / "lecture.sock",
		interface.clock,
		configuration=path,
		crossfades=crossfades,
		audio=audio,
		silences=silences,
		interface=interface_settings,
		retention=retention,
		dead_air=dead_air,
	)
	interface.window.requested_detail.connect(lambda category, number: interface.requests.append((category, number)))

	def announce(text: str) -> None:
		# Effacer la barre d'état n'annonce rien.
		if text != "":
			interface.announcements.append(text)

	# Ce que la fenêtre annonce en s'ouvrant, avant que l'étape l'écoute.
	announce(interface.window.statusBar().currentMessage())
	interface.window.statusBar().messageChanged.connect(announce)

	def abandon(_window: QWidget) -> None:
		# À la fin du scénario, la fenêtre se ferme en abandonnant les modifications de ses fiches.
		interface.closing = Closing.ABANDON

	qtbot.addWidget(interface.window, before_close_func=abandon)
	interface.window.show()
	qtbot.waitExposed(interface.window)
	# Comme Machin_interface, une fois la fenêtre montrée (https://github.com/dascritch/machincast/issues/119).
	interface.window.offer_to_launching()


@when("la base devient injoignable pour l'interface")
def unreachable_database(interface: Context) -> None:
	assert interface.connection is not None
	interface.connection.close()


ON_DEMAND = {"Sonores": "Ouvrir l'onglet Sonores", "Feeds": "Ouvrir l'onglet Feeds"}
"""Les listes qui ne s'ouvrent pas au lancement, et l'entrée du menu « Affichage » qui les ouvre
(https://github.com/dascritch/machincast/issues/180)."""


@when(parsers.parse("j'ouvre l'onglet « {title} »"))
def open_tab(interface: Context, title: str) -> None:
	"""Une liste ouverte à la demande, pas encore ouverte, s'ouvre par le menu « Affichage », comme le ferait
	l'utilisateur (https://github.com/dascritch/machincast/issues/180)."""
	tabs = window(interface).ui.tabs
	titles = [tab_title(tabs, index) for index in range(tabs.count())]
	if (title in ON_DEMAND) and (title not in titles):
		choose_in_menu(interface, ON_DEMAND[title], "Affichage")
		return
	tabs.setCurrentIndex(tab(interface, title))


@when(parsers.parse("j'ouvre la fiche de la banque « {name} »"))
def open_bank_card(interface: Context, qtbot: QtBot, name: str) -> None:
	open_tab(interface, "Banques")
	open_line(interface, qtbot, name)


@when(parsers.parse("j'ouvre la fiche de la séquence « {name} »"))
def open_sequence_card(interface: Context, qtbot: QtBot, name: str) -> None:
	open_tab(interface, "Séquences")
	open_line(interface, qtbot, name)


@when(parsers.parse("j'ouvre la fiche de l'événement « {name} »"))
def open_event_card(interface: Context, qtbot: QtBot, name: str) -> None:
	open_tab(interface, "Événements")
	open_line(interface, qtbot, name)


@when(parsers.parse("j'ouvre la fiche du sonore « {name} »"))
def open_sound_card(interface: Context, qtbot: QtBot, name: str) -> None:
	"""Par son titre, ou son emplacement pour un sonore sans titre."""
	open_tab(interface, "Sonores")
	open_line(interface, qtbot, name)


@when(parsers.parse("je clique sur « {text} »"))
def click_on(interface: Context, qtbot: QtBot, text: str) -> None:
	opened = window(interface).ui.tabs.currentWidget()
	buttons = [button for button in opened.findChildren(QPushButton) if button.text() == text]
	assert len(buttons) == 1, f"bouton « {text} » : {len(buttons)} trouvés"
	qtbot.mouseClick(buttons[0], Qt.MouseButton.LeftButton)


@when(parsers.re(r"je saisis le (?P<field>nom interne|nom public) « (?P<text>[^»]*) »"))
def enter_name(interface: Context, qtbot: QtBot, field: str, text: str) -> None:
	ui = opened_card(interface).ui  # type: ignore[attr-defined]
	fields = {"nom interne": ui.internal_name, "nom public": ui.public_name}
	type_(qtbot, fields[field], text)


@when(parsers.re(r"je choisis (?:le|la) (?P<field>mode|masquage|priorité) « (?P<text>[^»]+) »"))
def choose_in_card(interface: Context, field: str, text: str) -> None:
	ui = opened_card(interface).ui  # type: ignore[attr-defined]
	list_ = getattr(ui, {"priorité": "priority", "masquage": "hiding"}.get(field, field))
	index = list_.findText(text, Qt.MatchFlag.MatchFixedString)
	assert index >= 0, f"« {text} » absent du choix du {field}"
	list_.setCurrentIndex(index)


@when("j'enregistre la fiche")
def save(interface: Context, qtbot: QtBot) -> None:
	qtbot.mouseClick(opened_card(interface).button_save, Qt.MouseButton.LeftButton)


@when("j'annule les modifications de la fiche")
def cancel(interface: Context, qtbot: QtBot) -> None:
	qtbot.mouseClick(opened_card(interface).button_cancel, Qt.MouseButton.LeftButton)


@given(parsers.parse("le sonore « {title} » est effacé de la base"))
@when(parsers.parse("le sonore « {title} » est effacé de la base"))
def erase(empty_database: Connection, title: str) -> None:
	empty_database.execute("DELETE FROM sounds WHERE title = %s", (title,))


@when(parsers.re(r"la banque « (?P<name>[^»]+) » (?P<state>est|n'est plus) marquée « ne pas répéter » en base"))
def mark(empty_database: Connection, name: str, state: str) -> None:
	empty_database.execute("UPDATE banks SET no_repeat = %s WHERE internal_name = %s", (state == "est", name))


@when(parsers.re(r"la (?P<category>banque|séquence) « (?P<name>[^»]+) » est effacée de la base"))
def erase_bank(empty_database: Connection, category: str, name: str) -> None:
	table = {"banque": "banks", "séquence": "sequences"}[category]
	empty_database.execute(f"DELETE FROM {table} WHERE internal_name = %s", (name,))  # noqa: S608


@when(parsers.re(r"j'ajoute les feeds (?P<names>aucun|« [^»]+ »(?:, « [^»]+ »)*)"))
def add_feeds(interface: Context, qtbot: QtBot, empty_database: Connection, names: str) -> None:
	"""Le choix donnera ces feeds, par leur nom ; « aucun » : le choix est abandonné
	(https://github.com/dascritch/machincast/issues/167)."""
	ui = opened_card(interface).ui  # type: ignore[attr-defined]
	interface.chosen_feeds = [identifier(empty_database, "feeds", "name", name) for name in NAME.findall(names)]
	qtbot.mouseClick(ui.add_feeds, Qt.MouseButton.LeftButton)


@then(parsers.parse("le stream « {title} » est en base, actif, et suit le feed « {marks} »"))
def feed_stream(empty_database: Connection, title: str, marks: str) -> None:
	line = empty_database.execute(
		"SELECT s.type::text, s.state::text, s.stream_url, m.name FROM sounds s"
		" JOIN feeds m ON m.id = s.feed_id WHERE s.title = %s",
		(title,),
	).fetchall()
	assert line == [("stream", "active", None, marks)], line


@then(parsers.re(r"(?P<count>\d+) streams? (?:suit|suivent) le feed « (?P<marks>[^»]+) »"))
def stream_count(empty_database: Connection, count: str, marks: str) -> None:
	line = empty_database.execute(
		"SELECT count(*) FROM sounds s JOIN feeds m ON m.id = s.feed_id WHERE m.name = %s",
		(marks,),
	).fetchone()
	assert line is not None
	assert int(str(line[0])) == int(count)


@when(parsers.re(r"j'ajoute les (?P<category>sonores|banques|séquences) (?P<names>aucun|« [^»]+ »(?:, « [^»]+ »)*)"))
def add_items(interface: Context, qtbot: QtBot, empty_database: Connection, category: str, names: str) -> None:
	"""Le choix donnera ces sonores, par leur titre, ou ces banques ou ces séquences, par leur nom ; « aucun » : le
	choix est abandonné."""
	ui = opened_card(interface).ui  # type: ignore[attr-defined]
	if category == "sonores":
		interface.chosen_sounds = [identifier(empty_database, "sounds", "title", name) for name in NAME.findall(names)]
	elif category == "banques":
		interface.chosen_banks = [
			identifier(empty_database, "banks", "internal_name", name) for name in NAME.findall(names)
		]
	else:
		interface.chosen_sequences = [
			identifier(empty_database, "sequences", "internal_name", name) for name in NAME.findall(names)
		]
	button = {"sonores": "add_sounds", "banques": "add_banks", "séquences": "add_sequences"}[category]
	qtbot.mouseClick(getattr(ui, button), Qt.MouseButton.LeftButton)


@when(parsers.parse("je ferme l'onglet « {title} »"))
def close_tab(interface: Context, qtbot: QtBot, title: str) -> None:
	tabs = window(interface).ui.tabs
	index = tab(interface, title)
	button = closing_button(tabs.tabBar(), index)
	assert button is not None, f"l'onglet « {title} » n'a pas de bouton de fermeture"
	interface.closed_list.append(tabs.widget(index))
	qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


@when("je ferme la fenêtre de l'interface")
def close_window(interface: Context) -> None:
	window(interface).close()


@when(parsers.re(r"je réponds « (?P<response>[^»]+) » à la question de (?:fermeture|rafraîchissement)"))
def answer_closing(interface: Context, response: str) -> None:
	interface.closing = Closing(response)


@when(parsers.parse("je réponds « {response} » à l'avertissement de réintégration"))
def answer_removal(interface: Context, response: str) -> None:
	interface.removal = Removal(response)


@when(parsers.parse("le sonore « {title} » est ajouté en base"))
def add(empty_database: Connection, title: str) -> None:
	empty_database.execute(
		"INSERT INTO sounds (type, location, title) VALUES ('file', %s, %s)", (f"/srv/{title}.flac", title)
	)


@when(parsers.parse("je tape « {text} » dans le filtre de la liste"))
def apply_filter(interface: Context, qtbot: QtBot, text: str) -> None:
	type_(qtbot, list_(interface).filter_, text)


@when(parsers.parse("je clique sur le titre de la colonne « {title} »"))
def sort(interface: Context, qtbot: QtBot, title: str) -> None:
	table = list_(interface).table
	header = table.horizontalHeader()
	model = table.model()
	titles = [str(model.headerData(column, Qt.Orientation.Horizontal)) for column in range(model.columnCount())]
	column = titles.index(title)
	position = QPoint(header.sectionViewportPosition(column) + header.sectionSize(column) // 2, header.height() // 2)
	qtbot.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=position)


@when(parsers.parse("j'ouvre la ligne « {name} »"))
def open_line(interface: Context, qtbot: QtBot, name: str) -> None:
	open_in(qtbot, list_(interface).table, name)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"la fenêtre a les onglets (?P<titles>.+)"))
def tabs(interface: Context, titles: str) -> None:
	tabs = window(interface).ui.tabs
	assert [tab_title(tabs, index) for index in range(tabs.count())] == NAME.findall(titles)


@then(parsers.parse("l'onglet ouvert est « {title} »"))
def opened_tab(interface: Context, title: str) -> None:
	tabs = window(interface).ui.tabs
	assert tab_title(tabs, tabs.currentIndex()) == title


def closable_list(interface: Context) -> list[str]:
	tabs = window(interface).ui.tabs
	return [tab_title(tabs, index) for index in range(tabs.count()) if closing_button(tabs.tabBar(), index) is not None]


@then("aucun onglet n'a de bouton de fermeture")
def no_closable(interface: Context) -> None:
	assert closable_list(interface) == []


@then(parsers.re(r"seuls les onglets (?P<titles>«.+) ont un bouton de fermeture"))
def only_closable_ones(interface: Context, titles: str) -> None:
	assert closable_list(interface) == NAME.findall(titles)


@when("j'efface le filtre de la liste")
def erase_filter(interface: Context) -> None:
	list_(interface).filter_.clear()


@then(parsers.parse("seul l'onglet « {title} » a un bouton de fermeture"))
def only_closable(interface: Context, title: str) -> None:
	tabs = window(interface).ui.tabs
	closable_list = [
		tab_title(tabs, index) for index in range(tabs.count()) if closing_button(tabs.tabBar(), index) is not None
	]
	assert closable_list == [title]


@then(parsers.re(r"la fenêtre de l'interface est (?P<state>fermée|ouverte)"))
def opened_window(interface: Context, state: str) -> None:
	assert window(interface).isVisible() == (state == "ouverte")


@then("la fiche fermée est libérée")
def released(interface: Context) -> None:
	QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
	assert [shiboken6.isValid(closed) for closed in interface.closed_list] == [False]


@then(
	parsers.re(
		r"l'avertissement de réintégration nomme « (?P<sound>[^»]+) », le répertoire « (?P<directory>[^»]+) »"
		r" et la prochaine indexation"
	)
)
def warning(interface: Context, sound: str, directory: str) -> None:
	assert len(interface.questions) == 1, interface.questions
	question = interface.questions[0]
	assert question.startswith("retrait : "), question
	assert f"« {sound} »" in question, question
	assert directory in question, question
	assert "prochaine indexation" in question, question


@then("aucune question n'a été posée")
def no_question(interface: Context) -> None:
	assert interface.questions == []


@then(parsers.re(r"la question de (?P<what>fermeture|rafraîchissement) a nommé « (?P<title>[^»]+) »"))
def closing_question(interface: Context, what: str, title: str) -> None:
	assert interface.questions == [f"{what} : {title}"]


@then(parsers.re(r"le navigateur de fichiers a ouvert (?P<folder>.+)"))
def opened_folder(interface: Context, folder: str) -> None:
	assert interface.opened_folders == [Path(path) for path in NAME.findall(folder)]


def report(card: Card) -> str:
	"""Ce que la fiche signale : son erreur, en haut, sinon son message d'information, en bas
	(https://github.com/dascritch/machincast/issues/270)."""
	if card.error.isVisibleTo(card):
		return card.error.text()
	return card.message.text()


@then(parsers.parse("la fiche signale « {message} »"))
def reports(interface: Context, message: str) -> None:
	assert report(opened_card(interface)) == message


@then("la fiche signale un enregistrement impossible")
def impossible_saving(interface: Context) -> None:
	assert report(opened_card(interface)).startswith("Enregistrement impossible : ")


@then("la fiche ne signale rien")
def reported_nothing(interface: Context) -> None:
	card = opened_card(interface)
	assert (not card.error.isVisibleTo(card)) and (card.message.text() == "")


@then("l'erreur est en haut de la fiche, sur un liseret rouge de 4 pixels")
def error_in_top(interface: Context) -> None:
	"""https://github.com/dascritch/machincast/issues/270 : la première chose de la fiche."""
	card = opened_card(interface)
	arrangement = card.layout()
	assert arrangement is not None
	first = arrangement.itemAt(0)
	assert (first is not None) and (first.widget() is card.error)
	assert card.error.isVisibleTo(card)
	assert card.error.text() != ""
	assert "border: 4px solid #d32f2f" in card.error.styleSheet()


def reported_fields(card: Card) -> list[str]:
	"""Les libellés que précède ⚠️, dans l'ordre de la fiche, sans le signe ni le raccourci clavier."""
	labels = []
	for widget in card.findChildren(QWidget):
		if (isinstance(widget, (QLabel, QAbstractButton))) and (widget is not card.error):
			labels.append(widget.text())
		elif isinstance(widget, QGroupBox):
			labels.append(widget.title())
	return [text.removeprefix(REPORTED).replace("&", "") for text in labels if text.startswith(REPORTED)]


@then(parsers.re(r"les champs signalés par ⚠️ sont (?P<names>«.+)"))
def fields_in_cause(interface: Context, names: str) -> None:
	assert reported_fields(opened_card(interface)) == NAME.findall(names)


@then("aucun champ n'est signalé par ⚠️")
def no_field(interface: Context) -> None:
	assert reported_fields(opened_card(interface)) == []


@then(parsers.parse("la fiche avertit en haut « {text} »"))
def warns_in_top(interface: Context, text: str) -> None:
	"""Sous l'erreur, sur un liseret orange, précédé de ⚠️ (https://github.com/dascritch/machincast/issues/328)."""
	opened = opened_card(interface)
	assert opened.warning.isVisibleTo(opened)
	assert opened.warning.text() == f"⚠️ {text}"
	assert "#ef6c00" in opened.warning.styleSheet()
	# En haut : après l'erreur, et avant les champs de la fiche, dont la première disposition est le formulaire.
	arrangement = opened.layout()
	assert arrangement is not None
	fields = next(rank for rank in range(arrangement.count()) if arrangement.itemAt(rank).layout() is not None)
	assert arrangement.indexOf(opened.error) < arrangement.indexOf(opened.warning) < fields


@then(parsers.re(r"le choix du masquage de la fiche propose (?P<texts>«.+)"))
def offered_hidings(interface: Context, texts: str) -> None:
	choice = opened_card(interface).ui.hiding  # type: ignore[attr-defined]
	assert [choice.itemText(rank) for rank in range(choice.count())] == NAME.findall(texts)


@then("la fiche n'avertit pas en haut")
def n_warns_not_in_top(interface: Context) -> None:
	opened = opened_card(interface)
	assert not opened.warning.isVisibleTo(opened)


@then(parsers.re(r"les boutons « Enregistrer » et « Annuler » de la fiche sont (?P<state>actifs|inactifs)"))
def buttons(interface: Context, state: str) -> None:
	opened = opened_card(interface)
	active_list = (opened.button_save.isEnabled(), opened.button_cancel.isEnabled())
	assert active_list == (state == "actifs", state == "actifs")


@then(parsers.re(r"la fenêtre (?P<verdict>n'a plus|a encore) d'onglet de fiche"))
def card_tab(interface: Context, verdict: str) -> None:
	tabs = window(interface).ui.tabs
	cards = [tabs.widget(index) for index in range(tabs.count())]
	assert any(isinstance(opened, Card) for opened in cards) == (verdict == "a encore")


@then(parsers.re(r"les listes qui proposent de créer un élément sont (?P<buttons>.+)"))
def new_buttons(interface: Context, buttons: str) -> None:
	tabs = window(interface).ui.tabs
	with_ = []
	for index in range(tabs.count()):
		opened = tabs.widget(index)
		if (isinstance(opened, List)) and (not opened.ui.new.isHidden()):
			with_.append(f"{tab_title(tabs, index)} : {opened.ui.new.text()}")
	assert with_ == NAME.findall(buttons)


@then("l'onglet « Antenne » montre l'écran par défaut")
def home(interface: Context) -> None:
	assert window(interface).ui.tabs.widget(0) is window(interface).home


@then("la liste montre :")
def expected_entries(interface: Context, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	expected_list = [dict(zip(headers, (interface.path(v.strip()) for v in values), strict=True)) for values in rows]
	assert lines(interface) == expected_list, lines(interface)


@then(parsers.re(r"la colonne « (?P<column>[^»]+) » de la liste montre (?P<values>«.+)"))
def displayed_column(interface: Context, column: str, values: str) -> None:
	assert [line[column] for line in lines(interface)] == NAME.findall(values), lines(interface)


@then(parsers.re(r"la liste montre les titres (?P<titles>.+)"))
def shown_titles(interface: Context, titles: str) -> None:
	assert [line["Titre"] for line in lines(interface)] == NAME.findall(titles), lines(interface)


def marked_list(interface: Context) -> list[list[str]]:
	"""Les lignes en anomalie de la liste ouverte, son nom et son infobulle : ⚠️ dans la première colonne, l'infobulle
	sur toutes ses cellules, et aucune icône, ni sur le nom ni ailleurs. Les autres n'ont ni ⚠️ ni infobulle
	(https://github.com/dascritch/machincast/issues/138, https://github.com/dascritch/machincast/issues/327)."""
	model = list_(interface).table.model()
	assert model.headerData(0, Qt.Orientation.Horizontal) == ANOMALY_COLUMN
	found_list = []
	for row in range(model.rowCount()):
		cells = [model.index(row, column) for column in range(model.columnCount())]
		assert {cell.data(Qt.ItemDataRole.DecorationRole) for cell in cells} == {None}
		bubbles = {cell.data(Qt.ItemDataRole.ToolTipRole) for cell in cells}
		if cells[0].data() == ANOMALY_COLUMN:
			assert len(bubbles) == 1, bubbles
			found_list.append([str(cells[0].data(IDENTIFIER + 1)), str(bubbles.pop())])
		else:
			assert (cells[0].data(), bubbles) == ("", {None}), bubbles
	return found_list


@then(parsers.re(r"la liste marque en anomalie les lignes (?P<names>.+), avec l'infobulle « (?P<tooltip>[^»]+) »"))
def anomalies(interface: Context, names: str, tooltip: str) -> None:
	assert marked_list(interface) == [[name, tooltip] for name in NAME.findall(names)]


@then("la liste marque en anomalie les lignes et infobulles :")
def anomalies_and_tooltips(interface: Context, datatable: list[list[str]]) -> None:
	"""Chaque ligne en anomalie a son infobulle, propre à la ligne (https://github.com/dascritch/machincast/issues/140)."""
	_headers, *rows = datatable
	assert marked_list(interface) == [[line.strip(), tooltip.strip()] for line, tooltip in rows]


@then(parsers.parse("la première colonne de la liste est « {title} », avec l'infobulle « {tooltip} »"))
def anomaly_column(interface: Context, title: str, tooltip: str) -> None:
	model = list_(interface).table.model()
	header = (
		model.headerData(0, Qt.Orientation.Horizontal),
		model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole),
	)
	assert header == (title, tooltip)
	assert list_(interface).table.horizontalHeader().visualIndex(0) == 0


@then(parsers.parse("la liste n'a pas de colonne « {title} »"))
def without_column(interface: Context, title: str) -> None:
	model = list_(interface).table.model()
	titles = [model.headerData(column, Qt.Orientation.Horizontal) for column in range(model.columnCount())]
	assert title not in titles


@then(parsers.parse("le compte de la liste est « {text} »"))
def count(interface: Context, text: str) -> None:
	assert list_(interface).count.text() == text


@then(parsers.parse("l'écran de détail de {category} « {name} » est demandé"))
def detail(interface: Context, empty_database: Connection, category: str, name: str) -> None:
	tables = {
		"sonore": ("sounds", "title"),
		"banque": ("banks", "internal_name"),
		"séquence": ("sequences", "internal_name"),
		"événement": ("events", "internal_name"),
		"feed": ("feeds", "name"),
	}
	table, column = tables[category]
	assert interface.requests == [(category, identifier(empty_database, table, column, name))], interface.requests


@then(parsers.re(r"(?:le choix a|les choix ont) précisé « (?P<remark>[^»]+) »"))
def remark(interface: Context, remark: str) -> None:
	"""Chaque choix ouvert par la fiche a donné cette remarque."""
	assert interface.remarks != []
	assert set(interface.remarks) == {remark}


@then("le dépôt est accepté comme une copie")
def copied_drop(interface: Context) -> None:
	assert interface.drops == [(True, Qt.DropAction.CopyAction)]


@then("le dépôt est refusé")
def refused_drop(interface: Context) -> None:
	assert [accepts for accepts, _action in interface.drops] == [False]


@then(parsers.parse("le fichier « {path} » est en base, à l'état aperçu, sans artiste ni titre"))
def file_in_preview(interface: Context, empty_database: Connection, path: str) -> None:
	lines = empty_database.execute(
		"SELECT type::text, state::text, artist, title FROM sounds WHERE location = %s", (interface.path(path),)
	).fetchall()
	assert lines == [("file", "preview", None, None)]


@then("les fichiers déposés sont intacts")
def intact_list(interface: Context) -> None:
	assert {file: file.read_bytes() for file in interface.files} == interface.files


@then(parsers.re(r"le bouton « ❌ Supprimer… » de la fiche est (?P<state>actif|inactif)"))
def button_delete(interface: Context, state: str) -> None:
	assert opened_card(interface).button_delete.isEnabled() == (state == "actif")


@then(parsers.parse("la barre d'état annonce « {text} »"))
def state_bar(interface: Context, text: str) -> None:
	assert window(interface).statusBar().currentMessage() == interface.path_in(text)


# ─── Barre de menus ────────────────────────────────────────


def menus(interface: Context) -> list[QMenu]:
	"""Les menus de la barre de menus, dans l'ordre."""
	bar = window(interface).menuBar()
	found_list = {under_menu.menuAction(): under_menu for under_menu in bar.findChildren(QMenu)}
	return [found_list[action] for action in bar.actions()]


def named_menu(interface: Context, menu: str) -> QMenu:
	found_list = [under_menu for under_menu in menus(interface) if under_menu.title().replace("&", "") == menu]
	assert len(found_list) == 1, f"menu « {menu} » absent"
	return found_list[0]


def actions(interface: Context, menu: str) -> list[QAction]:
	"""Les entrées d'un menu de la barre de menus, séparateurs compris, dans l'ordre."""
	return list(named_menu(interface, menu).actions())


@when(parsers.parse("j'ouvre le menu « {menu} »"))
def open_menu(interface: Context, menu: str) -> None:
	"""L'ouverture du menu, qui relit ce qu'il montre (aboutToShow)."""
	named_menu(interface, menu).aboutToShow.emit()


@when(parsers.parse("je choisis « {title} » dans le menu « {menu} »"))
def choose_in_menu(interface: Context, title: str, menu: str) -> None:
	"""Le menu s'ouvre d'abord, comme sous la souris : il peut relire ce qu'il propose (aboutToShow)."""
	named_menu(interface, menu).aboutToShow.emit()
	chosen_list = [action for action in actions(interface, menu) if action.text() == title]
	assert len(chosen_list) == 1, f"« {title} » absent du menu « {menu} »"
	chosen_list[0].trigger()


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
	assert [under_menu.title().replace("&", "") for under_menu in menus(interface)] == NAME.findall(titles)


@then(parsers.parse("le menu « {menu} » a les entrées :"))
def menu_entries(interface: Context, menu: str, datatable: list[list[str]]) -> None:
	"""Un séparateur s'écrit « — ». Une infobulle s'affiche au survol de son entrée, même inactive."""
	headers, *rows = datatable
	assert [header.strip() for header in headers] == ["entrée", "état", "raccourci", "infobulle"]
	fetched_list = []
	for action in actions(interface, menu):
		if action.isSeparator():
			fetched_list.append(["—", "", "", ""])
			continue
		tooltip = ""
		if action.toolTip() != action.text().replace("&", ""):
			tooltip = action.toolTip()
		state = "inactive"
		if action.isEnabled():
			state = "active"
		fetched_list.append([action.text(), state, action.shortcut().toString(), tooltip])
	expected_list = [[value.strip() for value in row] for row in rows]
	assert fetched_list == expected_list
	if any((row[3] != "") for row in expected_list):
		assert named_menu(interface, menu).toolTipsVisible()


@then(parsers.re(r"le menu « (?P<menu>[^»]+) » propose (?P<titles>«.+)"))
def offered_menu(interface: Context, menu: str, titles: str) -> None:
	active_list = [action for action in actions(interface, menu) if (action.isEnabled()) and (not action.isSeparator())]
	assert [action.text() for action in active_list] == NAME.findall(titles)


@then(parsers.parse("le menu « {menu} » ne propose plus rien"))
def inactive_menu(interface: Context, menu: str) -> None:
	active_list = [action for action in actions(interface, menu) if (action.isEnabled()) and (not action.isSeparator())]
	assert active_list == []


@then(parsers.parse("le navigateur web a ouvert « {address} »"))
def opened_page(interface: Context, address: str) -> None:
	"""« <version> » : le numéro de version de MachinCast (https://github.com/dascritch/machincast/issues/208)."""
	assert interface.opened_pages == [address.replace("<version>", __version__)]


WAITING = 20_000
"""Millisecondes accordées à une vérification ou une indexation : un fichier de test se décode en moins d'1 s."""


def wait_check(interface: Context, qtbot: QtBot) -> None:
	checker = window(interface).checker
	qtbot.waitUntil(lambda: not checker.ongoing(), timeout=WAITING)


@when(parsers.re(r"j'ajoute les fichiers (?P<paths>aucun|«.+)"))
def add_files(interface: Context, qtbot: QtBot, paths: str) -> None:
	"""Depuis la liste des sonores ouverte, par le sélecteur de fichiers."""
	interface.chosen_files = [Path(interface.path(path)) for path in NAME.findall(paths)]
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
		f"SELECT {marks} FROM {table} WHERE {column} = %s",  # noqa: S608
		(name,),
	).fetchall()
	if state == "n'est plus":
		assert lines == [], lines
	elif state == "est toujours":
		assert [line[0] for line in lines] == [None], lines
	else:
		assert (len(lines) == 1) and (lines[0][0] is not None), lines


@given("les périphériques audio du poste :")
def station_devices(monkeypatch: pytest.MonkeyPatch, datatable: list[list[str]]) -> None:
	"""Ceux que donnerait le fournisseur de périphériques de GStreamer, pour la pré-écoute et les préférences."""
	found_list = [Device(identifier.strip(), name.strip()) for identifier, name in datatable[1:]]

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


# ─── Machin player imaginaire, sur la socket d'état (https://github.com/dascritch/machincast/issues/104) ─────


@dataclass
class Player:
	socket: StateSocket | None = None
	published: str = ""
	"""Le dernier état publié, tel que la socket l'envoie."""
	received_list: list[Request] = field(default_factory=list)


@pytest.fixture
def player() -> Iterator[Player]:
	player = Player()
	yield player
	if player.socket is not None:
		player.socket.shut_down()


def publish(
	player: Player, state: str, ongoing: dict[str, object] | None = None, **others: dict[str, object] | None
) -> None:
	"""Un état de Machin player ; autres donne d'autres champs, comme le prochain sonore ou l'événement suivant."""
	assert player.socket is not None
	# Les arguments nommés suivent les noms du code (next_, following_event) ; le message, ceux du protocole.
	keys = {"next_": "next", "following_event": "next_event"}
	message = {"state": state, "current": ongoing, "next": None, **{keys.get(k, k): v for k, v in others.items()}}
	player.published = json.dumps({"version": 3, **message})
	player.socket.publish(message)


@then("Machin player a reçu la demande de relire la grille")
def requested_rereading(player: Player, qtbot: QtBot) -> None:
	"""Après une session sautée (https://github.com/dascritch/machincast/issues/273), ou une fiche enregistrée,
	supprimée ou restaurée (https://github.com/dascritch/machincast/issues/266) : une seule demande."""
	socket = player.socket
	assert socket is not None

	def received() -> bool:
		player.received_list += socket.requests()
		return player.received_list != []

	qtbot.waitUntil(received, timeout=5000)
	# Une seconde demande, envoyée juste après, aurait le temps d'arriver.
	qtbot.wait(100)
	player.received_list += socket.requests()
	assert player.received_list == [Request(command=REREAD_GRID)]


@given("la socket d'état de Machin player ouverte pour l'interface")
def opened_socket(interface: Context, player: Player) -> None:
	player.socket = StateSocket(interface.directory / "lecture.sock")
	player.socket.open_()


@given(parsers.parse("Machin player diffuse un sonore au texte public « {text} »"))
@when(parsers.parse("Machin player diffuse un sonore au texte public « {text} »"))
def broadcasts_to_public_text(player: Player, text: str) -> None:
	"""Le texte public du sonore en cours, ce que la page publique en affiche
	(https://github.com/dascritch/machincast/issues/223)."""
	ongoing = {
		"sound_id": 12,
		"type": "file",
		"artist": None,
		"title": text,
		"event": "Continue",
		"location": "/srv/musique/minuit.flac",
		"start": "2026-10-21T08:59:00+02:00",
		"duration": 214.0,
		"estimated_end": "2026-10-21T09:02:34+02:00",
		"position": 60.0,
		"progress": 0.28,
		"public_text": text,
	}
	publish(player, "playing", ongoing)


# ─── Airplay (https://github.com/dascritch/machincast/issues/244) ───

AIRPLAY_DAY = "2026-10-16"
"""Le jour des passages des scénarios de l'airplay, quand seule leur heure est donnée."""


def hour(text: str) -> datetime:
	return datetime.fromisoformat(text).astimezone()


def hour_or_none(text: str) -> datetime | None:
	if text == "":
		return None
	return hour(text)


def a(schedule: str) -> datetime:
	return hour(f"{AIRPLAY_DAY} {schedule}")


def reference(database: Connection, table: str, name: str) -> int | None:
	"""Identifiant de l'entrée de ce nom interne, créée au besoin ; None pour un nom vide."""
	if not name:
		return None
	values = {
		"events": ", priority) VALUES (%s, 'background_programming')",
		"banks": ", mode) VALUES (%s, 'sequential')",
	}
	line = database.execute(f"SELECT id FROM {table} WHERE internal_name = %s", (name,)).fetchone()  # noqa: S608
	if line is None:
		remainder = values.get(table, ") VALUES (%s)")
		line = database.execute(f"INSERT INTO {table} (internal_name{remainder} RETURNING id", (name,)).fetchone()  # noqa: S608
	assert line is not None
	return int(str(line[0]))


def insert_play(
	database: Connection,
	start: datetime,
	end: datetime | None,
	artist: str,
	title: str,
	event: str,
	sequence: str = "",
	bank: str = "",
	without_incident: str = "",
) -> None:
	location = f"/musique/{uuid.uuid4()}.flac"
	line = database.execute(
		"INSERT INTO sounds (type, location, artist, title) VALUES ('file', %s, %s, %s) RETURNING id",
		(location, (artist) or (None), title),
	).fetchone()
	assert line is not None
	references = (
		line[0],
		reference(database, "events", event),
		reference(database, "sequences", sequence),
		reference(database, "banks", bank),
	)
	play = uuid.uuid4()
	columns = "play_id, line_type, logged_at, sound_id, event_id, sequence_id, bank_id, artist, title, location"
	database.execute(
		f"INSERT INTO airplay ({columns}) VALUES (%s, 'start', %s, %s, %s, %s, %s, %s, %s, %s)",
		(play, start, *references, (artist) or (None), title, location),
	)
	if end is not None:
		database.execute(
			f"INSERT INTO airplay ({columns}, played_duration, without_incident)"
			" VALUES (%s, 'end', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
			(play, end, *references, (artist) or (None), title, location, end - start, without_incident == "oui"),
		)


@given("les passages dans l'airplay :")
def plays(empty_database: Connection, datatable: list[list[str]]) -> None:
	headers, *lines = datatable
	for values in lines:
		line = dict(zip(headers, (v.strip() for v in values), strict=True))
		insert_play(
			empty_database,
			hour(line["starts_at"]),
			hour_or_none(line["ends_at"]),
			line["artist"],
			line["title"],
			line["event"],
			line["sequence"],
			line["bank"],
			line["without_incident"],
		)


@given("le masquage de tous les sonores et de tous les événements")
def hide(empty_database: Connection) -> None:
	empty_database.execute("UPDATE sounds SET hide_metadata = true")
	empty_database.execute("UPDATE events SET hide_metadata = true")


@when(parsers.parse("le passage de « {title} » commence dans l'airplay à {start}"))
def new_play(empty_database: Connection, title: str, start: str) -> None:
	insert_play(empty_database, a(start), None, "Radio", title, "Fil de jour")


@given(
	parsers.re(
		r"(?P<category>le sonore|la banque|la séquence|l'événement) « (?P<name>[^»]+) » est supprimée? depuis"
		r" l'interface"
	)
)
@when(
	parsers.re(
		r"(?P<category>le sonore|la banque|la séquence|l'événement) « (?P<name>[^»]+) » est supprimée? depuis"
		r" l'interface"
	)
)
def deleted_since_interface(empty_database: Connection, category: str, name: str) -> None:
	"""Comme « Supprimer… » de sa fiche, sans ses retraits des listes
	(https://github.com/dascritch/machincast/issues/267)."""
	table, column = TABLES[category]
	modified = empty_database.execute(
		f"UPDATE {table} SET deleted_at = clock_timestamp() WHERE {column} = %s RETURNING id",  # noqa: S608
		(name,),
	).fetchall()
	assert len(modified) == 1, modified


@then(parsers.parse("le fichier « {path} » a {count:d} sonores en base, dont {deleted_list:d} supprimé"))
def file_sounds(interface: Context, empty_database: Connection, path: str, count: int, deleted_list: int) -> None:
	lines = empty_database.execute(
		"SELECT deleted_at IS NOT NULL FROM sounds WHERE location = %s", (interface.path(path),)
	).fetchall()
	assert (len(lines), sum(1 for (deleted,) in lines if deleted)) == (count, deleted_list), lines


@given(parsers.parse("les préférences seront réglées avec la durée de péremption de {days:d} jours"))
def adjusted_retention(interface: Context, days: int) -> None:
	interface.adjusted_retention = days


@given(parsers.parse("la durée de péremption du fichier de configuration de l'interface est de {days:d} jours"))
def file_retention(interface: Context, days: int) -> None:
	"""https://github.com/dascritch/machincast/issues/268"""
	path = configuration_file(interface)
	document = tomlkit.parse(path.read_text(encoding="utf-8"))
	database = document["database"]
	assert isinstance(database, tomlkit.items.Table)
	database["retention"] = days
	path.write_text(tomlkit.dumps(document), encoding="utf-8")
