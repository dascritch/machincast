"""Les entrées des menus et de leurs sous-menus, pour les scénarios de l'interface
(https://github.com/dascritch/machincast/issues/530) : découpé de tests/interface_steps.py, qui ne doit pas dépasser
1500 lignes.
"""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

SUBMENU = " › "
"""Sépare un sous-menu de son entrée dans un scénario : « Recommencer › cet événement »
(https://github.com/dascritch/machincast/issues/530)."""


def find_entry(menu: QMenu, path: str) -> QAction:
	"""L'entrée montrée de ce menu, ou d'un de ses sous-menus, chacun ouvert d'abord, comme sous la souris."""
	under = menu
	*submenus, title = path.split(SUBMENU)
	for submenu in submenus:
		under = submenu_of(under, submenu)
	under.aboutToShow.emit()
	titled = []
	for action in under.actions():
		if (action.isVisible()) and (action.text() == title):
			titled.append(action)
	assert len(titled) == 1, f"« {path} » absent du menu « {menu.title()} »"
	return titled[0]


def submenu_of(menu: QMenu, title: str) -> QMenu:
	"""Le sous-menu de ce titre, ouvert comme sous la souris."""
	menu.aboutToShow.emit()
	for action in menu.actions():
		under = action.menu()
		if (isinstance(under, QMenu)) and (action.text() == title):
			under.aboutToShow.emit()
			return under
	raise AssertionError(f"sous-menu « {title} » absent de « {menu.title()} »")
