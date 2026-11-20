"""Scénarios de la fenêtre « Espace disque » (https://github.com/dascritch/machincast/issues/533).

Les répertoires des banques sont dans le répertoire du scénario ; le compte du service n'existe pas : c'est le compte
des tests qui lit, comme Machin player lancé à la main.
"""

import shutil
from pathlib import Path

import pytest
from PySide6.QtWidgets import QTreeWidgetItem
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import access
from machincast.interface import display
from machincast.interface.disk_space import DIRECTORY, USED, DiskSpaceWindow, mount_point
from tests.interface_steps import Context, window

scenarios("disk_space.feature")


@pytest.fixture(autouse=True)
def without_service(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(access, "service_account", lambda name=None: None)


@given(parsers.re(r"le répertoire « (?P<directory>[^»]+) » contient des fichiers de (?P<sizes>[\d et]+) octets"))
def files(interface: Context, directory: str, sizes: str) -> None:
	folder = Path(interface.path(directory))
	folder.mkdir(parents=True, exist_ok=True)
	for rank, size in enumerate(sizes.split(" et ")):
		(folder / f"fichier-{rank}.bin").write_bytes(b"0" * int(size))


def _opened(interface: Context) -> DiskSpaceWindow:
	opened = window(interface).disk_space
	assert opened is not None
	return opened


def _lines(interface: Context) -> list[QTreeWidgetItem]:
	table = _opened(interface).directories
	found = []
	for rank in range(table.topLevelItemCount()):
		line = table.topLevelItem(rank)
		assert line is not None
		found.append(line)
	return found


@then("la fenêtre « Espace disque » montre bientôt les répertoires :")
def shown_directories(interface: Context, qtbot: QtBot, datatable: list[list[str]]) -> None:
	_header, *rows = datatable
	expected = []
	for directory, bank, used in rows:
		expected.append([interface.path(directory.strip()), bank.strip(), used.strip()])

	def counted() -> bool:
		done = True
		for line in _lines(interface):
			if line.text(USED) == "comptage…":
				done = False
		return done

	qtbot.waitUntil(counted, timeout=5000)
	shown = []
	for line in _lines(interface):
		shown.append([line.text(DIRECTORY), line.text(1), line.text(USED)])
	assert shown == expected


@then("chaque répertoire qui existe a l'espace libre de son point de montage")
def free_spaces(interface: Context) -> None:
	for line in _lines(interface):
		if Path(line.text(DIRECTORY)).exists():
			assert line.text(3).endswith(("o", "ko", "Mo", "Go", "To")), line.text(3)


@then(
	"la fenêtre « Espace disque » montre le point de montage du répertoire du scénario, une seule fois, avec son espace"
	" libre et sa taille"
)
def shown_mount(interface: Context) -> None:
	table = _opened(interface).mounts
	expected = str(mount_point(Path(interface.path("…/musique"))))
	found = []
	for rank in range(table.topLevelItemCount()):
		line = table.topLevelItem(rank)
		assert line is not None
		if line.text(0) == expected:
			found.append(line)
	assert len(found) == 1, expected
	assert found[0].text(2) == display.size(shutil.disk_usage(expected).total)
	assert found[0].text(1) != ""


@when(parsers.parse("je double-clique sur le répertoire « {directory} » de la fenêtre « Espace disque »"))
def double_click(interface: Context, directory: str) -> None:
	for line in _lines(interface):
		if line.text(DIRECTORY) == interface.path(directory):
			_opened(interface).directories.itemDoubleClicked.emit(line, DIRECTORY)
			return
	raise AssertionError(directory)
