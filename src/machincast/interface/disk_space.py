"""La fenêtre « Espace disque », du menu « Maintenance » (https://github.com/dascritch/machincast/issues/533).

Elle dit où il reste de la place pour déposer des sonores, et ce que chaque banque occupe :

- les points de montage où le service de diffusion peut lire un sonore (mounts) : ceux du répertoire d'accueil des
  sonores, /home/machincast, et des répertoires des banques, que le compte du service lit, ou, sans service, celui de
  l'interface ; pour chacun, l'espace libre et la taille ;
- un tableau des répertoires indexés par une banque : le répertoire, la banque, le volume qu'il occupe, compté en tâche
  de fond (occupied), et l'espace qui reste sur son point de montage. Un double-clic sur le répertoire l'ouvre dans le
  gestionnaire de fichiers.

Rien n'est écrit, ni en base ni sur le disque : les fichiers ne sont que comptés.
"""

import logging
import os
import shutil
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
	QDialog,
	QDialogButtonBox,
	QLabel,
	QTreeWidget,
	QTreeWidgetItem,
	QVBoxLayout,
	QWidget,
)

from machincast import access
from machincast.i18n import _
from machincast.interface import dialogs, display
from machincast.interface.columns import Columns
from machincast.interface.queries import banks as banks_queries

log = logging.getLogger(__name__)

TITLE = _("Disk space")
MOUNT_COLUMNS = (_("Mount point"), _("Free"), _("Size"))
DIRECTORY_COLUMNS = (_("Directory"), _("Bank"), _("Used"), _("Free"))
COUNTING = _("counting…")
UNREACHABLE = _("unreachable")
NO_MOUNT = _("No mount point where the broadcast service reads a sound.")
DIRECTORY = 0
USED = 2


@dataclass(frozen=True)
class Mount:
	"""Un point de montage, et ce qu'il a de libre et de taille, en octets."""

	path: Path
	free: int
	total: int


def mount_point(path: Path) -> Path:
	"""Le point de montage du chemin : lui-même, ou son plus proche parent qui en est un."""
	current = path
	while not os.path.ismount(current):
		if current.parent == current:
			return current
		current = current.parent
	return current


def _existing(path: Path) -> Path | None:
	"""Le chemin, ou son plus proche parent qui existe ; None si rien n'existe."""
	for candidate in (path, *path.parents):
		if candidate.exists():
			return candidate
	return None


def _readable(path: Path, account: access.Account | None) -> bool:
	"""Lisible par le compte du service, ou, sans service, par le compte de l'interface, qui lance Machin player."""
	if account is not None:
		return access.readable(path, account)
	return os.access(path, os.R_OK | os.X_OK)


def mounts(candidates: list[Path], account: access.Account | None) -> list[Mount]:
	"""Les points de montage, chacun une fois, des chemins que le service lit, dans l'ordre de leur chemin."""
	found: dict[Path, Mount] = {}
	for candidate in candidates:
		existing = _existing(candidate)
		if (existing is not None) and (_readable(existing, account)):
			point = mount_point(existing)
			if point not in found:
				usage = shutil.disk_usage(point)
				found[point] = Mount(point, usage.free, usage.total)
	return sorted(found.values(), key=lambda mount: str(mount.path))


def occupied(directory: Path) -> int | None:
	"""Les octets des fichiers du répertoire et de ses sous-répertoires, sans suivre les liens ; None s'il ne se lit
	pas. Un fichier illisible est passé."""
	if not directory.is_dir():
		return None
	total = 0
	for root, _directories, files in os.walk(directory):
		for name in files:
			total += _file_size(Path(root) / name)
	return total


def _file_size(path: Path) -> int:
	try:
		return path.lstat().st_size
	except OSError:
		return 0


def free_space(directory: Path) -> int | None:
	"""L'espace libre du point de montage du répertoire ; None s'il n'existe ni lui ni un parent."""
	existing = _existing(directory)
	if existing is None:
		return None
	return shutil.disk_usage(existing).free


def bank_directories(connection: psycopg.Connection[TupleRow]) -> list[tuple[Path, str]]:
	"""Les répertoires des banques, et le nom de leur banque ; aucun si la base est injoignable."""
	try:
		with connection.transaction():
			lines = banks_queries.all_directories(connection)
	except psycopg.Error as error:
		log.error(_("unreadable bank directories: {error}").format(error=error))
		return []
	found = []
	for directory, bank in lines:
		found.append((Path(str(directory)), str(bank)))
	return found


class Counter(QObject):
	"""Compte en tâche de fond ce qu'occupe chaque répertoire, et l'annonce dans le fil de l'interface."""

	measured = Signal(str, object)
	"""Un répertoire compté : son chemin, et ses octets, ou None s'il ne se lit pas."""

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self._stop = threading.Event()
		self.worker: threading.Thread | None = None

	def count(self, directories: list[Path], measure: Callable[[Path], int | None] = occupied) -> None:
		self.worker = threading.Thread(target=self._work, args=(directories, measure), name="disk-space", daemon=True)
		self.worker.start()

	def _work(self, directories: list[Path], measure: Callable[[Path], int | None]) -> None:
		for directory in directories:
			if self._stop.is_set():
				return
			self.measured.emit(str(directory), measure(directory))

	def halt(self) -> None:
		self._stop.set()


class DiskSpaceWindow(QDialog):
	"""Les points de montage, puis les répertoires des banques."""

	def __init__(
		self,
		connection: psycopg.Connection[TupleRow],
		parent: QWidget | None = None,
		account: access.Account | None = None,
	) -> None:
		super().__init__(parent)
		self.setWindowTitle(TITLE)
		self.resize(800, 520)
		arrangement = QVBoxLayout(self)
		directories = bank_directories(connection)
		self.mounts = self._table(MOUNT_COLUMNS, "espace-disque-montages")
		candidates = [access.welcome()]
		for directory, _bank in directories:
			candidates.append(directory)
		found = mounts(candidates, account)
		for mount in found:
			QTreeWidgetItem(self.mounts, [str(mount.path), display.size(mount.free), display.size(mount.total)])
		self.empty = QLabel(NO_MOUNT, self)
		self.empty.setVisible(found == [])
		arrangement.addWidget(self.mounts)
		arrangement.addWidget(self.empty)
		self.directories = self._table(DIRECTORY_COLUMNS, "espace-disque-repertoires")
		for directory, bank in directories:
			free = free_space(directory)
			free_text = UNREACHABLE
			if free is not None:
				free_text = display.size(free)
			QTreeWidgetItem(self.directories, [str(directory), bank, COUNTING, free_text])
		self.directories.itemDoubleClicked.connect(self._open)
		arrangement.addWidget(self.directories, 1)
		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
		buttons.rejected.connect(self.reject)
		arrangement.addWidget(buttons)
		self.counter = Counter(self)
		self.counter.measured.connect(self._show_used, Qt.ConnectionType.QueuedConnection)
		unique: list[Path] = []
		for directory, _bank in directories:
			if directory not in unique:
				unique.append(directory)
		self.counter.count(unique)

	def _table(self, titles: tuple[str, ...], view: str) -> QTreeWidget:
		table = QTreeWidget(self)
		table.setRootIsDecorated(False)
		table.setAlternatingRowColors(True)
		table.setHeaderLabels(list(titles))
		Columns(table, view)
		return table

	def _show_used(self, directory: str, used: object) -> None:
		text = UNREACHABLE
		if isinstance(used, int):
			text = display.size(used)
		for rank in range(self.directories.topLevelItemCount()):
			line = self.directories.topLevelItem(rank)
			if (line is not None) and (line.text(DIRECTORY) == directory):
				line.setText(USED, text)

	def _open(self, line: QTreeWidgetItem, column: int) -> None:
		"""Un double-clic sur le répertoire l'ouvre dans le gestionnaire de fichiers."""
		if column == DIRECTORY:
			dialogs.open_folder(Path(line.text(DIRECTORY)))

	def done(self, result: int) -> None:
		self.counter.halt()
		super().done(result)
