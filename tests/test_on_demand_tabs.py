"""Onglets ouverts à la demande (https://github.com/dascritch/machincast/issues/180).

Les étapes de la fenêtre, de ses menus et de ses onglets sont dans tests/interface_steps.py.
"""

import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QWidget
from pytest_bdd import scenarios, then, when

from machincast.interface.window import TABS
from tests.interface_steps import Context, window

scenarios("on_demand_tabs.feature")


# ─── Libération (https://github.com/dascritch/machincast/issues/262) ───


@pytest.fixture
def window_lists() -> list[QWidget]:
	return []


@when("la fenêtre de l'interface se ferme, et se libère")
def release(interface: Context, window_lists: list[QWidget], request: pytest.FixtureRequest) -> None:
	"""Comme pytest-qt en fin de scénario, puis la suppression aussitôt faite ; la fenêtre, déjà libérée, est retirée
	de celles que pytest-qt fermera."""
	opened = window(interface)
	window_lists.extend(opened.lists)
	opened.close()
	opened.deleteLater()
	QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
	assert not shiboken6.isValid(opened)
	request.node.qt_widgets = [(ref, before) for ref, before in request.node.qt_widgets if ref() is not opened]
	interface.window = None


@then("aucune liste de la fenêtre ne lui survit")
def released_lists(window_lists: list[QWidget]) -> None:
	assert len(window_lists) == len(TABS)
	surviving = [list_ for list_ in window_lists if shiboken6.isValid(list_)]
	assert surviving == [], [list_.source.category for list_ in surviving]
