"""Scénarios du lancement de l'indexation depuis l'interface (https://github.com/dascritch/machincast/issues/38,
https://github.com/dascritch/machincast/issues/120).

Les étapes de la fenêtre, de sa barre de menus et des fenêtres de dialogue sont dans tests/interface_steps.py.
Machin indexer est remplacé par un programme factice, lancé pour de vrai dans un processus détaché : il note ses
options dans un fichier, puis attend qu'un autre fichier apparaisse.
"""

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import indexer
from machincast.interface.window import INDEXING_TRACKING
from tests.interface_steps import NAME, WAITING, Context, window

scenarios("interface_indexing.feature")

INDEXING_COMMAND = indexer.indexing_command
"""La vraie, que le Contexte remplace par celle du programme factice."""

DUMMY = """
import pathlib, sys, time
with pathlib.Path(sys.argv[1]).open("a") as options:
	options.write(" ".join(sys.argv[3:]) + "\\n")
fin = pathlib.Path(sys.argv[2])
while not fin.exists():
	time.sleep(0.05)
"""


@pytest.fixture
def dummy(interface: Context) -> Iterator[tuple[Path, Path]]:
	"""Le fichier des options du programme factice, une ligne par lancement, et celui qui le termine ; il est terminé en
	fin de scénario."""
	options, end = interface.directory / "options-indexation", interface.directory / "fin-indexation"
	yield options, end
	end.touch()


@given("un Machin indexer factice, qui attend")
def dummy_machin(interface: Context, dummy: tuple[Path, Path]) -> None:
	options, end = dummy
	command = [sys.executable, "-c", DUMMY, str(options), str(end)]
	interface.monkeypatch.setattr(indexer, "indexing_command", lambda _configuration: command)


@given("un Machin indexer introuvable")
def not_found_machin(interface: Context) -> None:
	command = [str(interface.directory / "aucun" / "Machin_indexer")]
	interface.monkeypatch.setattr(indexer, "indexing_command", lambda _configuration: command)


@when("l'interface a regardé plusieurs fois si le Machin indexer factice tourne")
def several_views(qtbot: QtBot) -> None:
	qtbot.wait(INDEXING_TRACKING * 2 + 500)


@when("le Machin indexer factice se termine")
def finish(interface: Context, qtbot: QtBot, dummy: tuple[Path, Path]) -> None:
	_options, end = dummy
	end.touch()
	qtbot.waitUntil(lambda: window(interface).launched_indexings == {}, timeout=WAITING)


@then(parsers.re(r"Machin indexer a été lancé avec (?P<options>«.+)"))
def launches_with(qtbot: QtBot, dummy: tuple[Path, Path], options: str) -> None:
	file, _end = dummy
	expected = " ".join(NAME.findall(options))
	# Chaque Machin indexer factice ajoute une ligne, ses options : deux lancés ensemble en ajoutent deux.
	qtbot.waitUntil(lambda: (file.exists()) and (expected in file.read_text().splitlines()), timeout=WAITING)


@then("le Machin indexer factice tourne toujours")
def runs_always(interface: Context, dummy: tuple[Path, Path]) -> None:
	(number,) = window(interface).launched_indexings.values()
	assert indexer.active_process(number)
	assert not dummy[1].exists()


@then(parsers.parse("{count:d} Machin indexer factices tournent"))
def running(interface: Context, count: int) -> None:
	numbers = list(window(interface).launched_indexings.values())
	assert len(numbers) == count
	assert all(indexer.active_process(number) for number in numbers)


@then(parsers.re(r"la commande d'indexation, pour la configuration (?P<configuration>.+), est « (?P<expected>.+) »"))
def command(interface: Context, monkeypatch: pytest.MonkeyPatch, configuration: str, expected: str) -> None:
	monkeypatch.chdir(interface.directory)
	path: Path | None = None
	if configuration != "par défaut":
		(name,) = NAME.findall(configuration)
		path = Path(name)
	expected = interface.path_in(expected).replace("<python>", sys.executable)
	assert INDEXING_COMMAND(path) == expected.split(" ")
