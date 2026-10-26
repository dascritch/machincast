"""Onglets ouverts à la demande (https://github.com/dascritch/machincast/issues/180).

Les étapes de la fenêtre, de ses menus et de ses onglets sont dans tests/etapes_interface.py.
"""

import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QWidget
from pytest_bdd import scenarios, then, when

from machincast.interface.fenetre import ONGLETS
from tests.etapes_interface import Contexte, fenetre

scenarios("onglets_a_la_demande.feature")


# ─── Libération (https://github.com/dascritch/machincast/issues/262) ───


@pytest.fixture
def listes_de_la_fenetre() -> list[QWidget]:
	return []


@when("la fenêtre de l'interface se ferme, et se libère")
def liberer(interface: Contexte, listes_de_la_fenetre: list[QWidget], request: pytest.FixtureRequest) -> None:
	"""Comme pytest-qt en fin de scénario, puis la suppression aussitôt faite ; la fenêtre, déjà libérée, est retirée
	de celles que pytest-qt fermera."""
	ouverte = fenetre(interface)
	listes_de_la_fenetre.extend(ouverte.listes)
	ouverte.close()
	ouverte.deleteLater()
	QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
	assert not shiboken6.isValid(ouverte)
	request.node.qt_widgets = [(ref, avant) for ref, avant in request.node.qt_widgets if ref() is not ouverte]
	interface.fenetre = None


@then("aucune liste de la fenêtre ne lui survit")
def listes_liberees(listes_de_la_fenetre: list[QWidget]) -> None:
	assert len(listes_de_la_fenetre) == len(ONGLETS)
	survivantes = [liste for liste in listes_de_la_fenetre if shiboken6.isValid(liste)]
	assert survivantes == [], [liste.source.genre for liste in survivantes]
