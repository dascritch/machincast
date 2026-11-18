"""Le presse-papiers des listes d'éléments et de sonores (https://github.com/dascritch/machincast/issues/129).

Les éléments d'un événement ou d'une séquence (machincast.interface.items), les sonores d'une banque
(machincast.interface.bank_card) et les résultats de la recherche (machincast.interface.search) se copient dans un
même format : une liste d'entrées, chacune avec son genre (« sound », « bank », « sequence », « event »), son
identifiant en base, le fichier d'un sonore pas encore en base, le feed d'un stream à créer, et son nom. Ils passent
aussi en texte, une ligne par entrée, ses colonnes séparées par des tabulations. Ctrl+C et Ctrl+V ne servent que dans la liste qui a le focus. Chaque liste colle ce qu'elle peut contenir,
et laisse le reste de côté, en le disant : un événement copié depuis la recherche n'est l'élément d'aucune liste.
"""

import json
from collections.abc import Callable

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem, QWidget

from machincast.i18n import _

MIME = "application/x-machincast-items"
"""Le format des éléments copiés dans le presse-papiers."""
COPY = _("Copy")
PASTE = _("Paste")


def entry(category: object, item: object, file: object, feed: object, name: str) -> dict[str, object]:
	"""Une entrée copiée."""
	return {"category": category, "item": item, "file": file, "feed": feed, "name": name}


def text(tree: QTreeWidget, line: QTreeWidgetItem) -> str:
	"""Le texte d'une ligne : ses colonnes, séparées par des tabulations."""
	cells = []
	for column in range(tree.columnCount()):
		cells.append(line.text(column))
	return "\t".join(cells)


def put(entries: list[dict[str, object]], lines: list[str]) -> None:
	"""Les entrées vont au presse-papiers, et leur texte avec elles."""
	data = QMimeData()
	data.setData(MIME, json.dumps(entries).encode())
	data.setText("\n".join(lines) + "\n")
	QGuiApplication.clipboard().setMimeData(data)


def copied() -> list[dict[str, object]]:
	"""Les entrées du presse-papiers ; aucune s'il n'en vient pas."""
	data = QGuiApplication.clipboard().mimeData()
	if (data is None) or (not data.hasFormat(MIME)):
		return []
	payload = json.loads(bytes(data.data(MIME).data()).decode())
	assert isinstance(payload, list)
	return payload


def shortcuts(view: QWidget, copy: Callable[[], None], paste: Callable[[], None] | None = None) -> None:
	"""Ctrl+C, et Ctrl+V pour une liste où coller, quand la liste a le focus."""
	bindings: list[tuple[QKeySequence.StandardKey, Callable[[], None]]] = [(QKeySequence.StandardKey.Copy, copy)]
	if paste is not None:
		bindings.append((QKeySequence.StandardKey.Paste, paste))
	for keys, act in bindings:
		shortcut = QShortcut(QKeySequence(keys), view)
		shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
		shortcut.activated.connect(act)


def offer(menu: QMenu, *, chosen: bool, copy: Callable[[], None], paste: Callable[[], None] | None = None) -> None:
	"""« Copier », et « Coller » pour une liste où coller, en fin de menu ; inactifs sans ligne choisie ou sans entrée
	copiée."""
	entry_copy = menu.addAction(COPY)
	entry_copy.setShortcut(QKeySequence(QKeySequence.StandardKey.Copy))
	entry_copy.setEnabled(chosen)
	entry_copy.triggered.connect(copy)
	if paste is None:
		return
	entry_paste = menu.addAction(PASTE)
	entry_paste.setShortcut(QKeySequence(QKeySequence.StandardKey.Paste))
	entry_paste.setEnabled(copied() != [])
	entry_paste.triggered.connect(paste)
