"""Les attentes des tests (https://github.com/dascritch/machincast/issues/444).

Un test attend une condition, jamais une durée : `settle` laisse l'application traiter ses événements en attente
(mise en page, signaux) et, si on la lui donne, attend la condition. Seule l'attente d'une absence (« aucune seconde
demande n'est arrivée », « le titre ne change pas ») n'a pas de condition à guetter : `quiet` la nomme, et dit ce
qu'elle laisse arriver. Un scénario de base.feature refuse toute autre attente à durée fixe dans tests/.
"""

import time
from collections.abc import Callable

from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

SETTLING = 5000
"""Millisecondes qu'une condition a pour devenir vraie."""


def settle(qtbot: QtBot, condition: Callable[[], bool] | None = None) -> None:
	"""Traite les événements en attente, puis attend la condition si elle est donnée."""
	QApplication.processEvents()
	if condition is not None:
		qtbot.waitUntil(condition, timeout=SETTLING)


def quiet(qtbot: QtBot | None, milliseconds: int, *, reason: str) -> None:
	"""Attend l'absence d'un événement : la durée est celle qu'aurait eue l'événement pour arriver, `reason` dit
	lequel. Sans qtbot, dans un scénario sans boucle Qt, la durée s'écoule seulement."""
	assert reason, "une attente d'absence dit ce qu'elle laisse arriver"
	if qtbot is None:
		time.sleep(milliseconds / 1000)
	else:
		qtbot.wait(milliseconds)
