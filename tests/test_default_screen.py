"""Étapes de l'écran par défaut de l'interface (https://github.com/dascritch/machincast/issues/23).

L'écran s'affiche hors de l'écran du poste (QT_QPA_PLATFORM=offscreen, réglé par tests/conftest.py). La socket d'état
est un vrai serveur du binaire lecture (machincast.player.state.StateSocket), qui publie les états du scénario.
"""

import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QGroupBox, QLabel, QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

import machincast.interface.__main__ as module_interface
import machincast.interface.application as module_application
import machincast.interface.default_screen as screen_module
import machincast.interface.error as error_module
from machincast.clock import FixedClock
from machincast.configuration import PROJECT_DIRECTORY
from machincast.database import Role, open_connection
from machincast.interface import expandable
from machincast.interface.application import translate
from machincast.interface.default_screen import DefaultScreen
from machincast.interface.error import UnreachableDatabaseWindow
from machincast.interface.timeline import HEIGHT, Timeline
from machincast.player.state import StateSocket
from tests.categories import AIRPLAY_KEYS as KEYS
from tests.categories import HATCHINGS, SCENARIO
from tests.database_fixtures import CONFIGURATION_TEST, sample_database_parameters
from tests.interface_steps import insert_play, open_in
from tests.sounds import SOUND_FILES
from tests.stream import StreamServer

scenarios("default_screen.feature")

Connection = psycopg.Connection[tuple[object, ...]]
DAY = "2026-10-16"
WAITING = 3000
"""Délai laissé à l'écran pour recevoir un état, en millisecondes."""


@dataclass
class Context:
	directory: Path
	clock: FixedClock | None = None
	socket: StateSocket | None = None
	ongoing: dict[str, Any] | None = None
	next_: dict[str, Any] | None = None
	upcoming: list[dict[str, Any]] = field(default_factory=list)
	"""Les sonores à venir après le prochain (https://github.com/dascritch/machincast/issues/228)."""
	screen: DefaultScreen | None = None
	connection: Connection | None = None
	plays: list[datetime] = field(default_factory=list)
	"""Instants où l'écran a lu l'airplay."""
	cards: list[tuple[str, int, str]] = field(default_factory=list)
	"""Fiches que l'écran a demandées (ouverte) : genre, identifiant et nom."""
	process: subprocess.CompletedProcess[str] | None = None
	windows: list[UnreachableDatabaseWindow] = field(default_factory=list)
	"""Fenêtres d'erreur montrées par Machin interface lancé dans le test."""
	code: int | None = None
	in_database: dict[str, tuple[int, str]] = field(default_factory=dict)
	"""Sonores en base du scénario, par titre : identifiant et emplacement
	(https://github.com/dascritch/machincast/issues/230)."""
	banks: dict[str, int] = field(default_factory=dict)
	next_shape: object = None
	"""La forme d'onde de la frise du prochain sonore, retenue pour la retrouver quand il passe à l'antenne."""
	requested_positions: list[float] = field(default_factory=list)
	fetched_plans: list[int] = field(default_factory=list)
	"""Sonores dont l'écran a lu le plan en base."""
	error_output: str = ""
	opened_list: list[str] = field(default_factory=list)
	"""Documents ouverts par le bouton de la fenêtre d'erreur."""
	display: bool | None = None
	click: str | None = None
	"""Bouton que le technicien choisit dans la fenêtre d'erreur."""
	previewed_list: list[int] = field(default_factory=list)
	"""Sonores dont l'écran a demandé la pré-écoute."""

	@property
	def path(self) -> Path:
		return self.directory / "run" / "lecture.sock"


@pytest.fixture
def context(tmp_path: Path) -> Iterator[Context]:
	context = Context(tmp_path)
	yield context
	if context.screen is not None:
		context.screen.close()
	if context.socket is not None:
		context.socket.shut_down()
	if context.connection is not None:
		context.connection.close()


def hour(text: str) -> datetime:
	return datetime.fromisoformat(text).astimezone()


def hour_or_none(text: str) -> datetime | None:
	if text == "":
		return None
	return hour(text)


def a(schedule: str) -> datetime:
	return hour(f"{DAY} {schedule}")


def seconds(text: str) -> float:
	return float(text.replace(",", "."))


def screen(context: Context) -> DefaultScreen:
	assert context.screen is not None
	return context.screen


def socket(context: Context) -> StateSocket:
	assert context.socket is not None
	return context.socket


def publish(context: Context, state: str = "playing") -> None:
	assert context.clock is not None
	socket(context).publish(
		{
			"timestamp": context.clock.now().isoformat(),
			"state": state,
			"current": context.ongoing if state == "playing" else None,
			"next": context.next_,
			"upcoming": context.upcoming if state == "playing" else [],
		}
	)


def location(title: str) -> str:
	"""Chemin d'un fichier, sans espace : un long titre donne un long chemin, que rien ne coupe."""
	return f"/srv/musique/{title.replace(' ', '_')}.flac"


def address(title: str) -> str:
	return f"https://flux.exemple/{title.replace(' ', '_')}"


def wait(qtbot: QtBot, condition: Callable[[], bool]) -> None:
	qtbot.waitUntil(condition, timeout=WAITING)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'horloge de l'interface au « {instant} »"))
def clock(context: Context, instant: str) -> None:
	context.clock = FixedClock(hour(instant))


@given("la socket d'état du binaire lecture ouverte")
@when("la socket d'état du binaire lecture s'ouvre ensuite")
def open_socket(context: Context) -> None:
	context.socket = StateSocket(context.path)
	context.socket.open_()


@given(
	parsers.re(
		r"le binaire lecture diffuse « (?P<title>[^»]+) » de « (?P<artist>[^»]+) » dans « (?P<event>[^»]+) »,"
		r" commencé à (?P<start>[\d:]+), de (?P<duration>[\d,]+) secondes, joué depuis (?P<position>[\d,]+) secondes"
	)
)
@when(
	parsers.re(
		r"le binaire lecture diffuse « (?P<title>[^»]+) » de « (?P<artist>[^»]+) » dans « (?P<event>[^»]+) »,"
		r" commencé à (?P<start>[\d:]+), de (?P<duration>[\d,]+) secondes, joué depuis (?P<position>[\d,]+) secondes"
	)
)
def broadcasts(context: Context, title: str, artist: str, event: str, start: str, duration: str, position: str) -> None:
	begins = a(start)
	length = seconds(duration)
	context.ongoing = {
		"sound_id": 12,
		"type": "file",
		"artist": artist,
		"title": title,
		"event": event,
		"start": begins.isoformat(),
		"duration": length,
		"estimated_end": (begins + timedelta(seconds=length)).isoformat(),
		"location": location(title),
		"position": seconds(position),
		"progress": round(min(1.0, seconds(position) / ((length) or (1.0))), 3),
	}
	publish(context)


@given(
	parsers.re(
		r"le binaire lecture diffuse le stream « (?P<title>[^»]+) » dans « (?P<event>[^»]+) »,"
		r" commencé à (?P<start>[\d:]+), joué depuis (?P<position>[\d,]+) secondes"
		r"(?:, jusqu'à la fin de son événement à (?P<end>[\d:]+))?"
	)
)
def broadcasts_stream(context: Context, title: str, event: str, start: str, position: str, end: str | None) -> None:
	estimated_end = None
	if end is not None:
		estimated_end = a(end).isoformat()
	context.ongoing = {
		"sound_id": 7,
		"type": "stream",
		"artist": None,
		"title": title,
		"event": event,
		"start": a(start).isoformat(),
		"duration": None,
		"estimated_end": estimated_end,
		"location": address(title),
		"position": seconds(position),
		"progress": None,
	}
	publish(context)


@given(
	parsers.re(
		r"le prochain sonore est « (?P<title>[^»]+) » dans « (?P<event>[^»]+) », estimé de (?P<start>[\d:]+)"
		r" à (?P<end>[\d:]+), de (?P<duration>[\d,]+) secondes, sain : (?P<healthy>oui|non)"
	)
)
def next_(context: Context, title: str, event: str, start: str, end: str, duration: str, healthy: str) -> None:
	context.next_ = {
		"sound_id": 31,
		"type": "file",
		"artist": None,
		"title": title,
		"event": event,
		"estimated_start": a(start).isoformat(),
		"duration": seconds(duration),
		"estimated_end": a(end).isoformat(),
		"location": location(title),
		"healthy": healthy == "oui",
	}
	publish(context)


@given("les sonores à venir après le prochain sont :")
def upcoming_sounds(context: Context, datatable: list[list[str]]) -> None:
	"""Chaque sonore à venir a ses identifiants : 41, 42… pour les sonores, 51… pour les événements, 61… pour les
	séquences et 71… pour les banques, selon son rang."""
	headers, *rows = datatable
	context.upcoming = []
	for rank, values in enumerate(rows, start=1):
		line = dict(zip(headers, (value.strip() for value in values), strict=True))
		context.upcoming.append(
			{
				"sound_id": 40 + rank,
				"type": "file",
				"artist": (line["artist"]) or (None),
				"title": line["title"],
				"event": line["event"],
				"event_id": 50 + rank,
				"sequence": (line["sequence"]) or (None),
				"sequence_id": (60 + rank) if line["sequence"] else None,
				"bank": (line["bank"]) or (None),
				"bank_id": (70 + rank) if line["bank"] else None,
				"estimated_start": a(line["start"]).isoformat(),
				"duration": seconds(line["duration"]),
				"estimated_end": a(line["end"]).isoformat(),
				"location": location(line["title"]),
				"healthy": line["healthy"] == "oui",
			}
		)
	publish(context)


@given(parsers.parse("le prochain sonore est le stream du flux « {stream} » dans « {event} »"))
def next_stream(context: Context, server: StreamServer, stream: str, event: str) -> None:
	context.next_ = {
		"sound_id": 8,
		"type": "stream",
		"artist": None,
		"title": "Direct studio",
		"event": event,
		"estimated_start": None,
		"duration": None,
		"estimated_end": None,
		"location": server.address(stream),
		"healthy": None,
	}
	publish(context)


@given(parsers.re(r"le (?P<which>sonore en cours|prochain sonore) a pour contexte :"))
def sound_context(context: Context, which: str, datatable: list[list[str]]) -> None:
	"""Les champs de contexte de la socket d'état (spec § 5.4) : identifiants en nombres, heures murales, textes."""
	sound = context.ongoing if which == "sonore en cours" else context.next_
	assert sound is not None
	_headers, *rows = datatable
	for field_name, value in ((field_name.strip(), value.strip()) for field_name, value in rows):
		lu: object = (value) or (None)
		if (field_name.endswith("_id")) and (value != ""):
			lu = int(value)
		if (field_name in ("event_start", "event_end")) and (value != ""):
			lu = datetime.fromisoformat(value).isoformat()
		sound[field_name] = lu
	publish(context)


@given(parsers.re(r"le sonore en cours sera coupé à (?P<instant>[\d:]+) par l'événement « (?P<event>[^»]+) »"))
def cutoff(context: Context, instant: str, event: str) -> None:
	"""La coupure annoncée par la socket (https://github.com/dascritch/machincast/issues/169) : la fin estimée devient
	celle de la coupure."""
	assert context.ongoing is not None
	context.ongoing |= {"estimated_end": a(instant).isoformat(), "cut_by": event, "cut_by_id": 8}
	publish(context)


@given(parsers.parse("le prochain sonore est le stream « {title} » dans « {event} », de début inconnu"))
def next_stream_entry(context: Context, title: str, event: str) -> None:
	context.next_ = {
		"sound_id": 8,
		"type": "stream",
		"artist": None,
		"title": title,
		"event": event,
		"estimated_start": None,
		"duration": None,
		"estimated_end": None,
		"location": address(title),
		"healthy": None,
	}
	publish(context)


@given(
	parsers.parse(
		"le binaire lecture diffuse un sonore sans artiste ni titre dans « {event} », commencé à {start},"
		" de {duration:d} secondes"
	)
)
def broadcasts_without_title(context: Context, event: str, start: str, duration: int) -> None:
	begins = a(start)
	context.ongoing = {
		"sound_id": 13,
		"type": "file",
		"artist": None,
		"title": None,
		"event": event,
		"start": begins.isoformat(),
		"duration": duration,
		"estimated_end": (begins + timedelta(seconds=duration)).isoformat(),
		"location": None,
		"position": 0,
		"progress": 0,
	}
	publish(context)


@given("le binaire lecture laisse un blanc")
@when("le binaire lecture laisse un blanc")
def in_dead_air(context: Context) -> None:
	context.ongoing = None
	context.next_ = None
	publish(context, "dead_air")


# ─── Quand ─────────────────────────────────────────────────


@when("l'écran par défaut s'ouvre")
def open_(context: Context, empty_database: Connection, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
	assert context.clock is not None
	read = screen_module.read_airplay

	def read_and_count(connection: Any, *others: Any, **named_list: Any) -> Any:
		assert context.clock is not None
		context.plays.append(context.clock.now())
		return read(connection, *others, **named_list)

	monkeypatch.setattr(screen_module, "read_airplay", read_and_count)
	read_plan = screen_module.read_plan

	def read_plan_and_count(connection: Any, sound: int, *others: Any) -> Any:
		context.fetched_plans.append(sound)
		return read_plan(connection, sound, *others)

	monkeypatch.setattr(screen_module, "read_plan", read_plan_and_count)
	context.connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	context.screen = DefaultScreen(context.connection, context.path, context.clock)
	context.screen.opened.connect(
		lambda category, number, name: context.cards.append((SCENARIO.get(category, category), number, name))
	)
	context.screen.requested_preview.connect(context.previewed_list.append)
	qtbot.addWidget(context.screen)
	context.screen.show()


@when(parsers.parse("l'écran par défaut s'ouvre, large de {width:d} pixels"))
def open_wide(
	context: Context, empty_database: Connection, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, width: int
) -> None:
	open_(context, empty_database, qtbot, monkeypatch)
	screen(context).resize(width, 760)


@when(parsers.re(r"le sonore en cours est bientôt « (?P<text>[^»]+) »"))
def wait_ongoing(context: Context, qtbot: QtBot, text: str) -> None:
	wait(qtbot, lambda: screen(context).ui.ongoing_title.text() == text)


@when(parsers.parse("l'horloge de l'interface avance de {count:d} secondes"))
def advance(context: Context, count: int) -> None:
	assert context.clock is not None
	context.clock.advance(timedelta(seconds=count))


@when("le binaire lecture s'arrête")
def stop(context: Context) -> None:
	context.ongoing = None
	context.next_ = None
	publish(context, "stopped")
	socket(context).shut_down()
	context.socket = None


@when("l'état du binaire lecture est bientôt « En diffusion »")
def wait_broadcast(context: Context, qtbot: QtBot) -> None:
	wait(qtbot, lambda: screen(context).ui.playback_state.text() == "En diffusion")


@when("la socket d'état se ferme sans dernier état")
def abrupt_closing(context: Context) -> None:
	socket(context).shut_down()
	context.socket = None


def send_raw(context: Context, text: str) -> None:
	"""Envoie ce texte tel quel aux clients : le serveur, lui, n'envoie que des lignes JSON complètes."""
	server = socket(context)
	with server._condition:
		server._message = text
		server._number += 1
		server._condition.notify_all()


def dead_air_line() -> str:
	return json.dumps({"version": 2, "state": "dead_air", "current": None, "next": None}) + "\n"


@when("un message illisible arrive sur la socket d'état, suivi dans le même envoi d'un état de blanc")
def unreadable(context: Context) -> None:
	send_raw(context, "{ pas du JSON\n" + dead_air_line())


@when("un état de blanc arrive sur la socket d'état en deux envois")
def in_sendings_two(context: Context, qtbot: QtBot) -> None:
	line = dead_air_line()
	half = len(line) // 2
	send_raw(context, line[:half])
	qtbot.wait(300)
	send_raw(context, line[half:])


def configuration_without_database(context: Context) -> Path:
	configuration = context.directory / "sans-base.toml"
	text = CONFIGURATION_TEST.read_text(encoding="utf-8")
	configuration.write_text(
		text.replace('socket = "/var/run/postgresql"', f'socket = "{context.directory / "aucune-socket"}"'),
		encoding="utf-8",
	)
	return configuration


@given("un affichage graphique disponible")
def available_display(context: Context, monkeypatch: pytest.MonkeyPatch, qtbot: QtBot) -> None:
	"""La fenêtre d'erreur est créée, mais pas montrée : le test lit ce qu'elle aurait montré."""

	def display(window: UnreachableDatabaseWindow) -> int:
		if window not in context.windows:
			context.windows.append(window)
		if context.click is not None:
			assert window.installation_button.text() == context.click
			window.installation_button.click()
		return 0

	monkeypatch.setattr(module_interface, "available_display", lambda: True)
	monkeypatch.setattr(UnreachableDatabaseWindow, "exec", display)
	monkeypatch.setattr(
		error_module.QDesktopServices, "openUrl", lambda url: context.opened_list.append(url.toString())
	)


@given("la traduction française de Qt chargée")
def translation(qapp: Any) -> Iterator[None]:
	assert translate(qapp)
	yield
	for translator in qapp.findChildren(module_application.QTranslator):
		qapp.removeTranslator(translator)
		translator.deleteLater()


@given("un compte qui ne peut pas endosser le rôle de l'interface")
def without_right(monkeypatch: pytest.MonkeyPatch) -> None:
	def refuse(*_: object) -> None:
		raise psycopg.errors.InsufficientPrivilege('permission denied to set role "machincast_interface"')

	monkeypatch.setattr(module_interface, "open_connection", refuse)


@when("Machin interface démarre avec une socket PostgreSQL inexistante")
def start(context: Context, capsys: pytest.CaptureFixture[str]) -> None:
	context.code = module_interface.main(["--config", str(configuration_without_database(context))])
	context.error_output = capsys.readouterr().err


@when(parsers.parse("je clique sur « {button} » dans la fenêtre d'erreur"))
def click(context: Context, button: str) -> None:
	context.click = button
	error_window(context).display()


@when(parsers.parse("l'environnement graphique est {environment}"))
def environment(context: Context, environment: str) -> None:
	variables = {}
	if environment != "vide":
		variables = dict(pair.strip().split("=", 1) for pair in environment.split(","))
	context.display = module_interface.available_display(variables)


@when("l'application Qt de l'interface est créée dans un processus neuf")
def new_application(context: Context) -> None:
	program = (
		"from PySide6.QtCore import QCoreApplication\n"
		"from machincast.interface.application import application\n"
		"application('essai')\n"
		"print(QCoreApplication.translate('QMessageBox', 'Show Details...'))\n"
	)
	context.process = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True, timeout=60)


@then(parsers.parse("Qt y traduit « {english} » par « {french} »"))
def translates(context: Context, english: str, french: str) -> None:
	assert context.process is not None
	process = context.process
	assert process.stdout.strip() == french, (english, process.stdout, process.stderr)


@when("je lance Machin_interface avec une socket PostgreSQL inexistante")
def launch(context: Context) -> None:
	configuration = configuration_without_database(context)
	executable = (shutil.which("Machin_interface")) or (str(Path(sys.executable).parent / "Machin_interface"))
	context.process = subprocess.run(
		[executable, "--config", str(configuration)], capture_output=True, text=True, timeout=60
	)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"l'écran affiche (?P<soon>bientôt )?l'heure « (?P<text>[^»]+) »"))
def displayed_hour(context: Context, qtbot: QtBot, soon: str | None, text: str) -> None:
	if soon:
		wait(qtbot, lambda: screen(context).ui.hour.text() == text)
	assert screen(context).ui.hour.text() == text


@then(parsers.re(r"l'état du binaire lecture est (?P<soon>bientôt )?« (?P<text>[^»]+) »"))
def displayed_state(context: Context, qtbot: QtBot, soon: str | None, text: str) -> None:
	if soon:
		wait(qtbot, lambda: screen(context).ui.playback_state.text() == text)
	assert screen(context).ui.playback_state.text() == text


@then(parsers.re(r"le sonore en cours est (?P<soon>bientôt )?« (?P<text>[^»]+) »"))
def ongoing_displayed(context: Context, qtbot: QtBot, soon: str | None, text: str) -> None:
	if soon:
		wait(qtbot, lambda: screen(context).ui.ongoing_title.text() == text)
	assert screen(context).ui.ongoing_title.text() == text


@when(parsers.re(r"le prochain sonore est (?P<soon>bientôt )?« (?P<text>[^»]+) »"))
@then(parsers.re(r"le prochain sonore est (?P<soon>bientôt )?« (?P<text>[^»]+) »"))
def next_displayed(context: Context, qtbot: QtBot, soon: str | None, text: str) -> None:
	if soon:
		wait(qtbot, lambda: screen(context).ui.next_title.text() == text)
	assert screen(context).ui.next_title.text() == text


@then(
	parsers.re(
		r"le (?P<which>sonore en cours|prochain sonore) a pour événement « (?P<event>[^»]+) »"
		r" et pour horaire « (?P<schedule>.+) »$"
	)
)
def event_and_schedule(context: Context, which: str, event: str, schedule: str) -> None:
	ui = screen(context).ui
	fields = {"sonore en cours": "ongoing", "prochain sonore": "next"}[which]
	obtained_list = (getattr(ui, f"{fields}_event").text(), getattr(ui, f"{fields}_schedule").text())
	assert obtained_list == (event, schedule)


@then(
	parsers.re(
		r"le (?P<which>sonore en cours|prochain sonore) a pour séquence « (?P<sequence>[^»]+) »"
		r" et pour banque « (?P<bank>[^»]+) »"
	)
)
def sequence_and_bank(context: Context, which: str, sequence: str, bank: str) -> None:
	ui = screen(context).ui
	fields = {"sonore en cours": "ongoing", "prochain sonore": "next"}[which]
	obtained_list = (getattr(ui, f"{fields}_sequence").text(), getattr(ui, f"{fields}_bank").text())
	assert obtained_list == (sequence, bank)


@then(parsers.parse("le sonore en cours n'a pas d'intitulé « {heading} »"))
def without_heading(context: Context, heading: str) -> None:
	texts = [caption.text() for caption in screen(context).ui.ongoing_frame.findChildren(QLabel)]
	assert heading not in texts, texts


@then(parsers.re(r"le bandeau montre (?P<soon>bientôt )?le texte public « (?P<text>.+) »$"))
def public_text(context: Context, qtbot: QtBot, soon: str | None, text: str) -> None:
	caption = screen(context).ui.public_text
	if soon:
		wait(qtbot, lambda: caption.text() == text)
	assert caption.text() == text


@then(parsers.re(r"l'événement à l'antenne est (?P<soon>bientôt )?« (?P<text>[^»]+) »"))
def on_air_event(context: Context, qtbot: QtBot, soon: str | None, text: str) -> None:
	caption = screen(context).ui.on_air_event
	if soon:
		wait(qtbot, lambda: caption.text() == text)
	assert caption.text() == text


@when(parsers.parse("je clique sur le bouton « {name} » de l'onglet Antenne"))
def click_button(context: Context, qtbot: QtBot, name: str) -> None:
	button = getattr(screen(context).ui, name)
	assert button.isEnabled(), name
	qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


@then("l'onglet Antenne a demandé les fiches :")
def requested_cards(context: Context, datatable: list[list[str]]) -> None:
	_headers, *rows = datatable
	expected_list = [(category.strip(), int(number), name.strip()) for category, number, name in rows]
	assert context.cards == expected_list


@then("les boutons de fiche de l'onglet Antenne sont inactifs")
def inactive_buttons(context: Context) -> None:
	ui = screen(context).ui
	buttons = [
		getattr(ui, f"open_{which}_{category}")
		for which in ("ongoing", "next")
		for category in ("sound", "event", "sequence", "bank")
	]
	assert [button.isEnabled() for button in buttons] == [False] * 8


@then(
	parsers.re(
		r"les boutons de séquence et de banque de l'onglet Antenne sont, pour le sonore en cours puis le prochain :"
		r" (?P<states>.+)"
	)
)
def bank_sequence_states(context: Context, states: str) -> None:
	ui = screen(context).ui
	obtained_list = []
	for which in ("ongoing", "next"):
		for category in ("sequence", "bank"):
			obtained_list.append("actif" if getattr(ui, f"open_{which}_{category}").isEnabled() else "inactif")
	assert obtained_list == states.split(", ")


@then(
	parsers.re(
		r"les boutons de fiche de l'onglet Antenne sont, dans l'ordre sonore en cours, son événement, prochain sonore,"
		r" son événement : (?P<states>.+)"
	)
)
def button_states(context: Context, states: str) -> None:
	ui = screen(context).ui
	buttons = (ui.open_ongoing_sound, ui.open_ongoing_event, ui.open_next_sound)
	obtained_list = ["actif" if button.isEnabled() else "inactif" for button in (*buttons, ui.open_next_event)]
	assert obtained_list == states.split(", ")


@given(parsers.parse("le sonore « {title} » est effacé de la base"))
def erase_sound(empty_database: Connection, title: str) -> None:
	empty_database.execute("DELETE FROM sounds WHERE title = %s", (title,))


@when(parsers.parse("j'ouvre dans l'airplay la cellule de la colonne « {column} »"))
def open_column(context: Context, qtbot: QtBot, column: str) -> None:
	"""Double-clic sur la première ligne de l'airplay, dans cette colonne, même vide."""
	table_airplay = screen(context).ui.table_airplay
	titles = [title for _name, title in screen(context).AIRPLAY_COLUMNS]
	index = table_airplay.model().index(0, titles.index(column))
	table_airplay.scrollTo(index)
	position = table_airplay.visualRect(index).center()
	qtbot.mouseClick(table_airplay.viewport(), Qt.MouseButton.LeftButton, pos=position)
	qtbot.mouseDClick(table_airplay.viewport(), Qt.MouseButton.LeftButton, pos=position)


@then("l'onglet Antenne n'a demandé aucune fiche")
def no_card(context: Context) -> None:
	assert context.cards == []


@when(parsers.parse("j'ouvre dans l'airplay la cellule « {text} »"))
def open_cell(context: Context, qtbot: QtBot, text: str) -> None:
	open_in(qtbot, screen(context).ui.table_airplay, text)


@then("l'onglet Antenne a demandé les fiches de l'airplay :")
def airplay_cards(context: Context, empty_database: Connection, datatable: list[list[str]]) -> None:
	"""Chaque fiche par son identifiant en base : le sonore par son titre, les autres par leur nom interne."""
	tables = {"sonore": ("sounds", "title"), "événement": ("events", "internal_name")}
	tables |= {"séquence": ("sequences", "internal_name"), "banque": ("banks", "internal_name")}
	_headers, *rows = datatable
	expected_list = []
	for category, name in ((category.strip(), name.strip()) for category, name in rows):
		table_in_database, column = tables[category]
		line = empty_database.execute(f"SELECT id FROM {table_in_database} WHERE {column} = %s", (name,)).fetchone()  # noqa: S608
		assert line is not None, name
		expected_list.append((category, int(str(line[0])), name))
	assert context.cards == expected_list


@then("le sonore en cours et le prochain sonore ont la même largeur, de part et d'autre de la colonne de l'antenne")
def halves(context: Context, qtbot: QtBot) -> None:
	"""La colonne de l'antenne est entre eux (https://github.com/dascritch/machincast/issues/24) : ils se partagent
	le reste de la largeur."""
	ui = screen(context).ui
	qtbot.wait(100)
	left, column, right = ui.ongoing_frame.width(), ui.on_air_column.width(), ui.next_frame.width()
	assert abs(left - right) <= 1, (left, right)
	space = ui.sounds.spacing()
	available = ui.sounds.geometry().width()
	assert abs((left + column + right + 2 * space) - available) <= 1, (left, column, right, available)
	assert ui.ongoing_frame.geometry().right() < ui.on_air_column.geometry().left()
	assert ui.on_air_column.geometry().right() < ui.next_frame.geometry().left()


@then(parsers.re(r"le (?P<which>sonore en cours|prochain sonore) a pour emplacement « (?P<text>[^»]+) »"))
def displayed_location(context: Context, which: str, text: str) -> None:
	ui = screen(context).ui
	field = ui.ongoing_location if which == "sonore en cours" else ui.next_location
	assert field.text() == text, field.text()
	assert field.isReadOnly()
	# Un long chemin dépasse le champ : l'infobulle le donne en entier.
	assert field.toolTip() == ("" if text == "—" else text), field.toolTip()
	assert field.cursorPosition() == len(text), "la fin du chemin, le nom du fichier, doit rester visible"


@then(parsers.parse("le prochain sonore est sain : « {text} »"))
def healthy(context: Context, text: str) -> None:
	assert screen(context).ui.next_healthy.text() == text


@then(
	parsers.re(
		r"l'avancement du sonore en cours est (?P<soon>bientôt )?à « (?P<text>.+?) »"
		r"(?:, à (?P<value>\d+) %)?$"
	)
)
def progress(context: Context, qtbot: QtBot, soon: str | None, text: str, value: str | None) -> None:
	"""Sur la barre de progression d'un stream, ou sous la frise d'un fichier
	(https://github.com/dascritch/machincast/issues/230) : le texte montré, et la part jouée."""
	opened = screen(context)

	def shows() -> str:
		if opened.ui.ongoing_progress.isVisibleTo(opened):
			return opened.ui.ongoing_progress.text()
		return opened.ongoing_timeline.legend

	if soon:
		wait(qtbot, lambda: shows() == text)
	assert shows() == text
	if value is not None:
		assert opened.ongoing_progress == int(value), opened.ongoing_progress


def table(context: Context) -> list[dict[str, str]]:
	model = screen(context).airplay_model
	columns = screen(context).AIRPLAY_COLUMNS
	return [
		{KEYS.get(key, key): model.item(row, column).text() for column, (key, _) in enumerate(columns)}
		for row in range(model.rowCount())
	]


def upcoming_table(context: Context) -> list[dict[str, str]]:
	model = screen(context).upcoming_model
	columns = screen(context).AIRPLAY_COLUMNS
	return [
		{KEYS.get(key, key): model.item(row, column).text() for column, (key, _) in enumerate(columns)}
		for row in range(model.rowCount())
	]


@then("la table des sonores à venir montre :")
def upcoming_expected_table(context: Context, qtbot: QtBot, datatable: list[list[str]]) -> None:
	headers, *lines = datatable
	expected_list = [dict(zip(headers, (v.strip() for v in values), strict=True)) for values in lines]
	wait(qtbot, lambda: len(upcoming_table(context)) == len(expected_list))
	assert upcoming_table(context) == expected_list, upcoming_table(context)


@then(parsers.re(r"la table des sonores à venir a bientôt (?P<count>\d+) lignes?"))
@when(parsers.re(r"la table des sonores à venir a bientôt (?P<count>\d+) lignes?"))
def upcoming_lines(context: Context, qtbot: QtBot, count: str) -> None:
	wait(qtbot, lambda: screen(context).upcoming_model.rowCount() == int(count))


@then("la table des sonores à venir a les colonnes de l'airplay, dans le même ordre")
def upcoming_columns(context: Context) -> None:
	opened = screen(context)

	def headers(model: QStandardItemModel) -> list[str]:
		return [str(model.headerData(column, Qt.Orientation.Horizontal)) for column in range(model.columnCount())]

	assert headers(opened.upcoming_model) == headers(opened.airplay_model), headers(opened.upcoming_model)


@then("la table des sonores à venir est au-dessus de celle de l'airplay")
def upcoming_to_above(context: Context, qtbot: QtBot) -> None:
	ui = screen(context).ui
	screen(context).show()
	qtbot.wait(50)
	airplay_top = ui.table_airplay.mapTo(screen(context), ui.table_airplay.rect().topLeft()).y()
	upcoming_bottom = ui.upcoming_table.mapTo(screen(context), ui.upcoming_table.rect().bottomLeft()).y()
	assert upcoming_bottom < airplay_top, (upcoming_bottom, airplay_top)


@when(parsers.parse("j'ouvre dans les sonores à venir la cellule « {text} »"))
def open_upcoming(context: Context, qtbot: QtBot, text: str) -> None:
	open_in(qtbot, screen(context).ui.upcoming_table, text)


@when(parsers.parse("je choisis « {entry} » au clic droit sur la ligne « {title} » des sonores à venir"))
def upcoming_menu(context: Context, entry: str, title: str) -> None:
	opened = screen(context)
	model = opened.upcoming_model
	(row,) = [
		row
		for row in range(model.rowCount())
		if any(model.index(row, column).data() == title for column in range(model.columnCount()))
	]
	menu = opened.upcoming_sound_menu(model.index(row, 0))
	assert menu is not None
	(action,) = [action for action in menu.actions() if action.text() == entry]
	action.trigger()


@then(parsers.parse("la pré-écoute du sonore {sound:d} a été demandée"))
def requested_preview(context: Context, sound: int) -> None:
	assert context.previewed_list == [sound]


@then(
	parsers.re(
		r"l'onglet Antenne propose pour le prochain sonore : pré-écoute (?P<preview>active|inactive),"
		r" test du flux (?P<stream>actif|inactif|caché)"
	)
)
def next_listened(context: Context, preview: str, stream: str) -> None:
	ui = screen(context).ui
	assert ui.preview_next.isEnabled() == (preview == "active")
	assert ui.test_next_stream.isVisibleTo(screen(context)) == (stream != "caché")
	if stream != "caché":
		assert ui.test_next_stream.isEnabled() == (stream == "actif")


@when("je clique sur la frise du prochain sonore")
def click_next_timeline(context: Context, qtbot: QtBot) -> None:
	timeline = screen(context).next_timeline
	wait(qtbot, lambda: timeline.isVisibleTo(screen(context)))
	qtbot.mouseClick(timeline, Qt.MouseButton.LeftButton, pos=timeline.rect().center())


@then(parsers.parse("le test du flux du prochain sonore dit bientôt « {text} »"))
def next_tested_stream(context: Context, qtbot: QtBot, text: str) -> None:
	caption = screen(context).ui.next_stream
	qtbot.waitUntil(lambda: caption.text() != "Test du flux en cours…", timeout=15000)
	assert caption.text() == text


@given(
	parsers.re(
		r"(?P<count>\d+) passages d'une minute dans l'airplay, « (?P<name>[^»]+) 1 » à (?P<start>[\d:]+),"
		r" le dernier en cours"
	)
)
def minute_plays(empty_database: Connection, count: str, name: str, start: str) -> None:
	departure = a(start)
	for rank in range(int(count)):
		begins = departure + timedelta(minutes=rank)
		end = None
		if rank < int(count) - 1:
			end = begins + timedelta(minutes=1)
		insert_play(empty_database, begins, end, "", f"{name} {rank + 1}", "Fil de jour", "", "", "oui")


@then(parsers.parse("la table de l'airplay a {count:d} lignes, de « {first} » à « {last} »"))
def airplay_lines(context: Context, count: int, first: str, last: str) -> None:
	titles = [line["titre"] for line in table(context)]
	assert (len(titles), titles[0], titles[-1]) == (count, first, last), titles


def panel(context: Context, title: str) -> QGroupBox:
	(group,) = [
		group
		for group in (screen(context).ui.upcoming_frame, screen(context).ui.airplay_frame)
		if group.property(expandable.TITLE) == title
	]
	return group


@then(parsers.parse("l'encart de l'airplay de l'onglet Antenne s'intitule « {title} »"))
def airplay_title(context: Context, title: str) -> None:
	assert screen(context).ui.airplay_frame.property(expandable.TITLE) == title


@then(parsers.parse("les encarts « {first} » et « {second} » de l'onglet Antenne sont dépliés"))
def expanded_panel_two(context: Context, first: str, second: str) -> None:
	assert not expandable.is_collapsed(panel(context, first))
	assert not expandable.is_collapsed(panel(context, second))


@then(parsers.re(r"l'encart « (?P<title>[^»]+) » de l'onglet Antenne est (?P<state>déplié|replié)"))
def home_panel(context: Context, title: str, state: str) -> None:
	assert expandable.is_collapsed(panel(context, title)) is (state == "replié")


@when(parsers.parse("je clique sur le titre de l'encart « {title} » de l'onglet Antenne"))
def click_title(context: Context, qtbot: QtBot, title: str) -> None:
	qtbot.mouseClick(panel(context, title), Qt.MouseButton.LeftButton, pos=QPoint(20, 5))


@when("l'écran par défaut se ferme, puis s'ouvre de nouveau")
def reopen_screen(context: Context, empty_database: Connection, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
	screen(context).close()
	open_(context, empty_database, qtbot, monkeypatch)


@then("la table de l'airplay montre :")
def expected_table(context: Context, datatable: list[list[str]]) -> None:
	headers, *lines = datatable
	expected_list = [dict(zip(headers, (v.strip() for v in values), strict=True)) for values in lines]
	assert table(context) == expected_list, table(context)


@then(parsers.re(r"l'airplay a (?P<soon>bientôt )?été lu (?P<count>\d+) fois"))
def plays(context: Context, qtbot: QtBot, soon: str | None, count: str) -> None:
	if soon:
		wait(qtbot, lambda: len(context.plays) == int(count))
	else:
		# Laisse arriver les états publiés : aucun ne doit relire l'airplay.
		qtbot.wait(500)
	assert len(context.plays) == int(count), context.plays


@then(parsers.parse("la première ligne de la table de l'airplay est « {title} »"))
def first_line(context: Context, title: str) -> None:
	assert table(context)[0]["titre"] == title, table(context)


def error_window(context: Context) -> UnreachableDatabaseWindow:
	assert len(context.windows) == 1, context.windows
	return context.windows[0]


@then(parsers.parse("il s'arrête avec le code {code:d}, après une fenêtre d'erreur « {title} »"))
def code_and_window(context: Context, code: int, title: str) -> None:
	assert context.code == code
	assert error_window(context).windowTitle() == title


@then("la fenêtre d'erreur explique que l'interface n'est pas utilisable sans sa base de données")
def explanation(context: Context) -> None:
	text = error_window(context).text()
	assert "n'est pas utilisable" in text, text
	assert "base de données" in text, text


@then("la fenêtre d'erreur invite à lire le document INSTALL.md du répertoire de MachinCast")
def prompt(context: Context) -> None:
	text = error_window(context).informativeText()
	assert str(PROJECT_DIRECTORY / "INSTALL.md") in text, text


@then("la fenêtre d'erreur détaille l'erreur de PostgreSQL")
def details(context: Context) -> None:
	assert "aucune-socket" in error_window(context).detailedText()


@then(parsers.parse("le message « {pattern} » est aussi sur la sortie d'erreur"))
def also_on_output(context: Context, pattern: str) -> None:
	assert pattern in context.error_output, context.error_output


@then(parsers.parse("la fenêtre d'erreur a les boutons « {first} », « {second} » et « {third} »"))
def buttons(context: Context, first: str, second: str, third: str) -> None:
	texts = sorted(button.text() for button in error_window(context).buttons())
	assert texts == sorted([first, second, third]), texts


@then("le document INSTALL.md du répertoire de MachinCast est ouvert")
def opened_installation(context: Context) -> None:
	assert context.opened_list == [f"file://{PROJECT_DIRECTORY / 'INSTALL.md'}"], context.opened_list


@then(parsers.re(r"une fenêtre d'erreur (?P<verdict>peut|ne peut pas) s'ouvrir"))
def display_verdict(context: Context, verdict: str) -> None:
	assert context.display is (verdict == "peut")


@then(parsers.parse("Machin_interface s'arrête avec le code {code:d}, en signalant « {pattern} »"))
def binary_stop(context: Context, code: int, pattern: str) -> None:
	assert context.process is not None
	assert context.process.returncode == code, context.process.stderr
	assert pattern in context.process.stderr, context.process.stderr


@then(parsers.re(r"l'écran n'a aucun intitulé (?P<texts>«.+)"))
def without_heading_to_banner(context: Context, texts: str) -> None:
	"""https://github.com/dascritch/machincast/issues/191"""
	shown_list = {caption.text() for caption in screen(context).findChildren(QLabel)}
	for text in re.findall(r"« ([^»]+) »", texts):
		assert text not in shown_list, text


@then(parsers.re(r"(?P<what>l'état du binaire lecture|l'événement à l'antenne) a pour infobulle « (?P<text>[^»]+) »"))
def banner_tooltip(context: Context, what: str, text: str) -> None:
	ui = screen(context).ui
	caption = {"l'état du binaire lecture": ui.playback_state, "l'événement à l'antenne": ui.on_air_event}[what]
	assert caption.toolTip() == text


@then(parsers.parse("l'heure a pour infobulle « {text} »"))
def hour_tooltip(context: Context, text: str) -> None:
	assert screen(context).ui.hour.toolTip() == text


# ─── Frises (https://github.com/dascritch/machincast/issues/230) ───


@given(
	parsers.re(
		r"le sonore « (?P<title>[^»]+) » en base, pour une copie du fichier de test « (?P<file>[^»]+) », de"
		r" (?P<duration>\d+) secondes, aux silences de (?P<start>[\d,]+) s au début et (?P<end>[\d,]+) s à la fin,"
		r" sans détection de silence, aux crossfades de (?P<cd>[\d,]+) s au début et (?P<cf>[\d,]+) s à la fin"
	)
)
def sound_in_database(
	context: Context,
	empty_database: Connection,
	title: str,
	file: str,
	duration: str,
	start: str,
	end: str,
	cd: str,
	cf: str,
) -> None:
	copies = context.directory / file
	shutil.copyfile(SOUND_FILES / file, copies)
	line = empty_database.execute(
		"INSERT INTO sounds (type, location, title, state, duration, detected_start, detected_end, crossfade_start,"
		" crossfade_end, audited_at, audit_threshold) VALUES ('file', %s, %s, 'active', %s, %s, %s, %s, %s, now(), -40)"
		" RETURNING id",
		(
			str(copies),
			title,
			timedelta(seconds=int(duration)),
			timedelta(seconds=seconds(start)),
			timedelta(seconds=seconds(end)),
			timedelta(seconds=seconds(cd)),
			timedelta(seconds=seconds(cf)),
		),
	).fetchone()
	assert line is not None
	context.in_database[title] = (int(str(line[0])), str(copies))


@given(
	parsers.re(
		r"la banque « (?P<name>[^»]+) » en base, qui retire les silences et impose un crossfade de fin de"
		r" (?P<cf>[\d,]+) s, avec « (?P<title>[^»]+) »"
	)
)
def bank_in_database(context: Context, empty_database: Connection, name: str, cf: str, title: str) -> None:
	line = empty_database.execute(
		"INSERT INTO banks (internal_name, mode, silence_detection, crossfade_end_rule, crossfade_end)"
		" VALUES (%s, 'random', true, 'forced', %s) RETURNING id",
		(name, timedelta(seconds=seconds(cf))),
	).fetchone()
	assert line is not None
	context.banks[name] = int(str(line[0]))
	empty_database.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, 1)",
		(line[0], context.in_database[title][0]),
	)


@given(
	parsers.re(
		r"le binaire lecture diffuse « (?P<title>[^»]+) », (?:de la banque « (?P<bank>[^»]+) »|sans banque),"
		r" commencé à (?P<start>[\d:]+), joué depuis (?P<position>[\d,]+) seconde"
	)
)
@when(
	parsers.re(
		r"le binaire lecture diffuse « (?P<title>[^»]+) », (?:de la banque « (?P<bank>[^»]+) »|sans banque),"
		r" commencé à (?P<start>[\d:]+), joué depuis (?P<position>[\d,]+) seconde"
	)
)
def broadcasts_in_database(context: Context, title: str, bank: str | None, start: str, position: str) -> None:
	"""Un sonore en base ; la durée annoncée par la socket est celle de la partie jouée, sans les silences retirés."""
	identifier, path = context.in_database[title]
	begins = a(start)
	context.ongoing = {
		"sound_id": identifier,
		"type": "file",
		"artist": None,
		"title": title,
		"event": "Fil de nuit",
		"start": begins.isoformat(),
		"duration": 1.0,
		"estimated_end": (begins + timedelta(seconds=1.0)).isoformat(),
		"location": path,
		"position": seconds(position),
		"progress": round(seconds(position), 3),
		"bank": bank,
		"bank_id": context.banks.get((bank) or ("")),
	}
	publish(context)


@given(parsers.parse("le prochain sonore est « {title} » en base, sans banque"))
def next_in_database(context: Context, title: str) -> None:
	identifier, path = context.in_database[title]
	context.next_ = {
		"sound_id": identifier,
		"type": "file",
		"artist": None,
		"title": title,
		"event": "Fil de jour",
		"estimated_start": a("20:03:34").isoformat(),
		"duration": 2.0,
		"estimated_end": a("20:03:36").isoformat(),
		"location": path,
		"healthy": True,
	}
	publish(context)


def _timeline(context: Context, which: str) -> Timeline:
	opened = screen(context)
	if which == "sonore en cours":
		return opened.ongoing_timeline
	return opened.next_timeline


@then(
	parsers.re(
		r"le (?P<which>sonore en cours|prochain sonore) a une frise(?P<without_head>, sans tête de lecture)?"
		r"(?P<without_bar>, sans barre de progression)?$"
	)
)
def has_timeline(context: Context, qtbot: QtBot, which: str, without_head: str | None, without_bar: str | None) -> None:
	opened = screen(context)
	timeline = _timeline(context, which)
	wait(qtbot, lambda: timeline.isVisibleTo(opened))
	if without_bar is not None:
		assert not opened.ui.ongoing_progress.isVisibleTo(opened)
	if without_head is not None:
		assert timeline.head is None


@then(
	parsers.re(r"le (?P<which>sonore en cours|prochain sonore) (?:a une barre de progression, sans|n'a pas de) frise")
)
def without_timeline(context: Context, which: str) -> None:
	opened = screen(context)
	assert not _timeline(context, which).isVisibleTo(opened)
	if which == "sonore en cours":
		assert opened.ui.ongoing_progress.isVisibleTo(opened)


@then(parsers.parse("la frise du sonore en cours montre bientôt les zones :"))
def ongoing_areas(context: Context, qtbot: QtBot, datatable: list[list[str]]) -> None:
	timeline = _timeline(context, "sonore en cours")
	wait(qtbot, lambda: timeline.plan is not None)
	assert timeline.plan is not None
	fetched_list = [
		[
			area.name,
			f"{area.start:.2f}".replace(".", ","),
			f"{area.end:.2f}".replace(".", ","),
			HATCHINGS[area.hatching],
			area.tooltip,
		]
		for area in timeline.plan.areas()
	]
	assert fetched_list == [[cell.strip() for cell in row] for row in datatable[1:]]


@then(
	parsers.re(r"la frise du prochain sonore montre bientôt les zones (?P<names>«.+»), ses silences joués à l'antenne")
)
def next_areas(context: Context, qtbot: QtBot, names: str) -> None:
	timeline = _timeline(context, "prochain sonore")
	wait(qtbot, lambda: timeline.plan is not None)
	assert timeline.plan is not None
	areas = timeline.plan.areas()
	assert [area.name for area in areas] == re.findall(r"« ([^»]+) »", names)
	assert {area.hatching for area in areas if area.name.startswith("silence")} == {"pale"}


@then(
	parsers.parse(
		"la tête de lecture de la frise du sonore en cours est à {position} seconde, la position jouée comptée depuis"
		" le début de la lecture"
	)
)
def head(context: Context, qtbot: QtBot, position: str) -> None:
	timeline = _timeline(context, "sonore en cours")
	wait(qtbot, lambda: (timeline.head is not None) and (abs(timeline.head - seconds(position)) < 0.001))


@when(parsers.re(r"la forme d'onde de la frise du (?P<which>sonore en cours|prochain sonore) est bientôt complète"))
@then(parsers.re(r"la forme d'onde de la frise du (?P<which>sonore en cours|prochain sonore) est bientôt complète"))
def full_shape(context: Context, qtbot: QtBot, which: str) -> None:
	timeline = _timeline(context, which)

	def finished() -> bool:
		return (timeline.shape is not None) and (timeline.shape.finished)

	wait(qtbot, finished)
	assert (timeline.shape is not None) and (timeline.shape.error is None), timeline.remark()
	assert max(timeline.shape.amplitudes(0.6, 1.4)) > 0.4
	if which == "prochain sonore":
		context.next_shape = timeline.shape


@then("la frise du sonore en cours dessine bientôt la forme d'onde qu'avait le prochain sonore")
def same_shape(context: Context, qtbot: QtBot) -> None:
	timeline = _timeline(context, "sonore en cours")
	assert context.next_shape is not None
	wait(qtbot, lambda: timeline.shape is context.next_shape)


@when("je clique au milieu de la frise du sonore en cours")
def click_timeline(context: Context, qtbot: QtBot) -> None:
	timeline = _timeline(context, "sonore en cours")
	wait(qtbot, lambda: timeline.isVisibleTo(screen(context)))
	context.requested_positions = []
	timeline.placed.connect(context.requested_positions.append)
	before = timeline.head
	qtbot.mouseClick(timeline, Qt.MouseButton.LeftButton, pos=timeline.rect().center())
	assert timeline.head == before


@then("la frise du sonore en cours n'a demandé aucune position")
def no_position(context: Context) -> None:
	assert context.requested_positions == []


@then(parsers.parse("le plan du sonore « {title} » n'a été lu qu'une fois en base"))
def fetched_times_plan(context: Context, title: str) -> None:
	assert context.fetched_plans.count(context.in_database[title][0]) == 1, context.fetched_plans


def _top(context: Context, widget: QWidget) -> int:
	"""L'ordonnée du haut d'un élément, dans l'écran."""
	return widget.mapTo(screen(context), QPoint(0, 0)).y()


@then("les frises du sonore en cours et du prochain sonore sont au-dessus de leur titre, à la même hauteur")
def timelines_in_head(context: Context, qtbot: QtBot) -> None:
	opened = screen(context)
	ongoing, next_ = opened.ongoing_timeline, opened.next_timeline
	wait(qtbot, lambda: (ongoing.isVisible()) and (next_.isVisible()))
	assert _top(context, ongoing) == _top(context, next_)
	assert _top(context, ongoing) + ongoing.height() <= _top(context, opened.ui.ongoing_title)
	assert _top(context, next_) + next_.height() <= _top(context, opened.ui.next_title)


@then("le temps qui reste au sonore en cours est écrit au milieu de sa frise, sans autre ligne sous elle")
def remains_in_timeline(context: Context) -> None:
	opened = screen(context)
	timeline = opened.ongoing_timeline
	assert timeline.legend.startswith("reste "), timeline.legend
	assert timeline.legend_background() is not None
	assert not hasattr(opened.ui, "en_cours_reste")
	space = opened.ui.ongoing_layout.spacing()
	assert _top(context, timeline) + timeline.height() + space >= _top(context, opened.ui.ongoing_title) - 1


@when("la colonne de l'antenne est plus haute qu'il ne lui faut")
def high_column(context: Context, qtbot: QtBot) -> None:
	"""Les frises font les sonores plus hauts que la colonne de l'antenne ne le demande : il y a de la hauteur à
	prendre. Sans assez de hauteur, l'écran s'allonge, comme sur un poste où les textes sont plus grands."""
	opened = screen(context)
	column = opened.ui.on_air_column
	opened.ui.ongoing_frame.setMinimumHeight(column.sizeHint().height() + 2 * HEIGHT)
	wait(qtbot, lambda: column.height() > column.sizeHint().height() + HEIGHT)


@then("le VU-mètre de l'antenne occupe sa colonne : ses voyants gardent leur hauteur, il prend le reste")
def vu_meter_in_column(context: Context) -> None:
	ui = screen(context).ui
	for light in (ui.clipping_light, ui.dead_air_light, ui.monitor_state):
		# Un texte qui passe à la ligne a la hauteur de ses lignes, à sa largeur.
		expected = light.sizeHint().height()
		if light.hasHeightForWidth():
			expected = light.heightForWidth(light.width())
		assert light.height() == expected, (light.objectName(), light.height(), expected)
	assert ui.on_air_column.height() == ui.ongoing_frame.height()
