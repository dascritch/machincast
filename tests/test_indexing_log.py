"""Scénarios du journal de l'indexation, la fenêtre de Machin indexer --window
(https://github.com/dascritch/machincast/issues/120).

La fenêtre s'ouvre ici dans le processus des tests, sur la base de test. Les étapes des fichiers, des sonores et des
banques sont dans tests/interface_steps.py. L'indexation décode vraiment les fichiers de test ; ses scénarios peuvent
la faire attendre, ou lui retirer ses décodeurs, en remplaçant le décodage de l'indexeur.
"""

import logging
import os
import shutil
import subprocess
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.indexer.decoding import Check, UnavailableDecoder, check_file
from machincast.interface import dialogs, indexer
from machincast.interface.indexing_log import LogWindow
from tests.database_fixtures import sample_configuration_path, sample_database_parameters
from tests.interface_steps import NAME, WAITING, Connection, Context
from tests.timestamp import without_timestamp

scenarios("indexing_log.feature")


@dataclass
class Log:
	window: LogWindow | None = None
	halt: bool = False
	"""La réponse à la question d'arrêt de l'indexation."""
	questions: list[str] = field(default_factory=list)


@pytest.fixture
def tracking(monkeypatch: pytest.MonkeyPatch) -> Iterator[Log]:
	"""La fenêtre du scénario, et la question d'arrêt remplacée par la réponse du scénario."""
	tracking = Log()

	def question(_parent: QWidget, title: str) -> bool:
		tracking.questions.append(title)
		return tracking.halt

	monkeypatch.setattr(dialogs, "confirm_indexing_stop", question)
	yield tracking
	if tracking.window is not None:
		tracking.window.indexer.halt()


def log(tracking: Log) -> LogWindow:
	assert tracking.window is not None
	return tracking.window


@pytest.fixture
def resumption() -> threading.Event:
	"""Ce qu'attend une indexation qui attend."""
	return threading.Event()


@pytest.fixture
def in_waiting() -> threading.Event:
	"""Une indexation qui attend en est à son premier décodage."""
	return threading.Event()


# ─── Étant donné ───────────────────────────────────────────


@given("une indexation qui attend")
def indexing_who_waiting(
	monkeypatch: pytest.MonkeyPatch, resumption: threading.Event, in_waiting: threading.Event
) -> None:
	def decode(path: Path) -> Check:
		in_waiting.set()
		assert resumption.wait(WAITING / 1000), "l'indexation attendue n'a jamais repris"
		return check_file(path)

	monkeypatch.setattr(indexer, "check_file", decode)


@given("un indexeur qui ne sait pas décoder les fichiers")
def without_decoder(monkeypatch: pytest.MonkeyPatch) -> None:
	def decode(_path: Path) -> Check:
		raise UnavailableDecoder("aucun décodeur pour ce format")

	monkeypatch.setattr(indexer, "check_file", decode)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le journal « {title} » de l'indexation s'ouvre"))
def open_(tracking: Log, empty_database: Connection, qtbot: QtBot, title: str) -> None:
	socket, database = sample_database_parameters()
	full_audit = {"Indexation rapide": False, "Audit complet": True}[title]
	tracking.window = LogWindow(socket, database, full_audit)
	qtbot.addWidget(tracking.window)
	tracking.window.launch()


@when("l'indexation se termine")
def finish(tracking: Log, qtbot: QtBot) -> None:
	qtbot.waitUntil(lambda: not log(tracking).indexer.ongoing(), timeout=WAITING)


@when("l'indexation en est à son premier décodage")
def first_decoding(in_waiting: threading.Event) -> None:
	assert in_waiting.wait(WAITING / 1000), "l'indexation n'a jamais commencé à décoder"


@when("l'indexation attendue reprend, et se termine")
def resume(tracking: Log, qtbot: QtBot, resumption: threading.Event) -> None:
	resumption.set()
	finish(tracking, qtbot)


@when("je ferme le journal de l'indexation")
def shut_down(tracking: Log, qtbot: QtBot) -> None:
	qtbot.mouseClick(log(tracking).ui.shut_down, Qt.MouseButton.LeftButton)


@when(parsers.parse("je ferme le journal de l'indexation, en répondant « {response} »"))
def close_in_answering(tracking: Log, qtbot: QtBot, response: str) -> None:
	tracking.halt = response == "Arrêter"
	shut_down(tracking, qtbot)


@when(
	parsers.parse(
		"je ferme le journal de l'indexation, en répondant « {response} », pendant que l'indexation attendue reprend"
	)
)
def close_during(tracking: Log, qtbot: QtBot, resumption: threading.Event, response: str) -> None:
	threading.Timer(0.3, resumption.set).start()
	close_in_answering(tracking, qtbot, response)


@when("je lance Machin indexer --window sans affichage graphique", target_fixture="command")
def without_display() -> subprocess.CompletedProcess[str]:
	path = shutil.which("Machin_indexer")
	assert path is not None, 'Machin_indexer n\'est pas installé : lancer pip install -e ".[dev]"'
	environment = {
		key: value for key, value in os.environ.items() if key not in ("DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM")
	}
	return subprocess.run(
		[path, "--window", "--config", str(sample_configuration_path())],
		capture_output=True,
		text=True,
		timeout=60,
		env=environment,
	)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le journal « {title} » de l'indexation conclut « {text} »"))
def conclusion(tracking: Log, title: str, text: str) -> None:
	assert (log(tracking).windowTitle(), log(tracking).ui.conclusion.text()) == (title, text)


@then(parsers.parse("le journal « {title} » de l'indexation est ouvert"))
def opened_log(tracking: Log, title: str) -> None:
	assert log(tracking).isVisible()
	assert log(tracking).windowTitle() == title


@then("le journal de l'indexation est fermé")
def closed_log(tracking: Log) -> None:
	assert not log(tracking).isVisible()


@then("aucune question n'a été posée")
def without_question(tracking: Log) -> None:
	assert tracking.questions == []


@then(parsers.parse("la question d'arrêt de l'indexation a nommé « {title} »"))
def stop_question(tracking: Log, title: str) -> None:
	assert tracking.questions == [title]


@then("l'indexation est arrêtée")
def stopped(tracking: Log) -> None:
	assert not log(tracking).indexer.ongoing()


@then("le journal de l'indexeur n'est plus écouté")
def free_log() -> None:
	assert logging.getLogger("machincast.indexer").handlers == []


@then("le journal de l'indexation montre :")
def log_lines(tracking: Log, interface: Context, datatable: list[list[str]]) -> None:
	"""Les lignes, comme dans le terminal ; un chemin qui commence par « …/ » est dans le répertoire du scénario."""
	_header, *lines = datatable
	shown_list = [without_timestamp(line) for line in log(tracking).lines()]
	assert shown_list == [interface.path_in(line.strip()) for (line,) in lines]


@then("le journal de l'indexation ne signale aucune anomalie")
def without_anomaly(tracking: Log) -> None:
	assert log(tracking).anomalies == []


@then(parsers.re(r"le journal de l'indexation signale (?P<count>\d+) anomalies?, sur (?P<paths>«.+)"))
def anomalies(tracking: Log, interface: Context, count: str, paths: str) -> None:
	"""Chaque anomalie suit la ligne qui ouvre l'analyse de son fichier, et le nomme
	(https://github.com/dascritch/machincast/issues/413)."""
	window = log(tracking)
	reported_list = window.anomalies
	assert len(reported_list) == int(count), reported_list
	shown = window.lines()
	for anomaly, path in zip(reported_list, NAME.findall(paths), strict=True):
		place = shown.index(anomaly)
		assert place > 0, shown
		assert without_timestamp(shown[place - 1]) == f"[horodatage] {interface.path(path)} : analyse…", shown


@then(parsers.parse("les sonores de la banque « {name} » en base sont :"))
def bank_sounds(interface: Context, empty_database: Connection, name: str, datatable: list[list[str]]) -> None:
	headers, *rows = datatable
	fetched_list = empty_database.execute(
		"SELECT s.location, s.state::text, s.title FROM sounds s"
		" JOIN bank_sounds bs ON bs.sound_id = s.id JOIN banks b ON b.id = bs.bank_id"
		" WHERE b.internal_name = %s ORDER BY bs.position",
		(name,),
	).fetchall()
	assert [header.strip() for header in headers] == ["location", "state", "title"]
	expected_list = [tuple(interface.path(value.strip()) for value in row) for row in rows]
	assert [tuple(str(value) for value in line) for line in fetched_list] == expected_list


@then(parsers.parse("le sonore « {title} » est à l'état « {expected_state} »"))
def state(empty_database: Connection, title: str, expected_state: str) -> None:
	lu = empty_database.execute("SELECT state::text FROM sounds WHERE title = %s", (title,)).fetchone()
	assert lu is not None, f"sonore « {title} » absent"
	assert lu[0] == expected_state


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def output_code(command: subprocess.CompletedProcess[str], code: int) -> None:
	assert command.returncode == code, command.stderr


@then(parsers.parse("la sortie d'erreur de la commande mentionne « {text} »"))
def command_error(command: subprocess.CompletedProcess[str], text: str) -> None:
	assert text in command.stderr, command.stderr
