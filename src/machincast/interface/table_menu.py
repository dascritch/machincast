"""Le menu « Tableau » de la fenêtre (https://github.com/dascritch/machincast/issues/528).

Après « Onglet », il agit sur le tableau de l'onglet affiché, celui que choisit columns.of_widget : copier, couper et
coller ses lignes, comme le clic droit et les touches de la liste (https://github.com/dascritch/machincast/issues/129),
l'exporter, rétablir ses colonnes. Une entrée que ce tableau ne permet pas est inactive : couper et coller ne servent
qu'à une liste éditable, et rien ne sert à un onglet sans tableau. Les touches sont rappelées dans le texte des
entrées, sans être prises par le menu (Qt.ShortcutContext.WidgetShortcut) : elles restent celles de la liste qui a le
focus.
"""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMenu, QTabWidget

from machincast.i18n import _
from machincast.interface import clipboard, columns

COPY = _("Copy lines")
CUT = _("Cut lines")
PASTE = _("Paste lines")
EXPORT = _("Export lines…")
REINSTATE = _("Reset the columns")


class TableMenu:
	"""Le menu « Tableau », relu à chaque ouverture."""

	def __init__(self, menu: QMenu, tabs: QTabWidget) -> None:
		self.menu = menu
		self.tabs = tabs
		menu.aboutToShow.connect(self.fill)
		self.fill()

	def fill(self) -> None:
		"""Les entrées, actives selon le tableau de l'onglet affiché."""
		self.menu.clear()
		table = columns.of_widget(self.tabs.currentWidget())
		handlers = None
		chosen = False
		if table is not None:
			handlers = clipboard.handlers(table.view)
			chosen = table.view.selectionModel().selectedRows() != []
		copy = None
		cut = None
		paste = None
		if handlers is not None:
			copy = handlers.copy
			cut = handlers.cut
			paste = handlers.paste
		self._entry(COPY, QKeySequence.StandardKey.Copy, copy, enabled=chosen)
		self._entry(CUT, QKeySequence.StandardKey.Cut, cut, enabled=chosen)
		self._entry(PASTE, QKeySequence.StandardKey.Paste, paste, enabled=clipboard.copied() != [])
		self.menu.addSeparator()
		export = None
		reinstate = None
		if table is not None:
			export = table.export
			reinstate = table.reinstate
		self._entry(EXPORT, None, export, enabled=True)
		self._entry(REINSTATE, None, reinstate, enabled=True)

	def _entry(
		self,
		text: str,
		keys: QKeySequence.StandardKey | None,
		act: Callable[[], None] | None,
		*,
		enabled: bool,
	) -> None:
		entry = self.menu.addAction(text)
		if keys is not None:
			entry.setShortcut(QKeySequence(keys))
			entry.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
		entry.setEnabled((act is not None) and (enabled))
		if act is not None:
			entry.triggered.connect(act)
