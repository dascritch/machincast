"""Étapes partagées des scénarios de l'interface : Machin indexer imité (https://github.com/dascritch/machincast/issues/401).

Chargé comme greffon pytest par tests/conftest.py (https://github.com/dascritch/machincast/issues/444 : découpé de
tests/interface_steps.py, par domaine).
"""

from pytest_bdd import parsers, then
from pytestqt.qtbot import QtBot

from tests.interface_steps import LAUNCHED_INDEXERS, NAME, WAITING, Context, configuration_file, window
from tests.waiting import quiet

# ─── Machin indexer imité (https://github.com/dascritch/machincast/issues/401) ───


def _launched_indexers(interface: Context) -> list[str]:
	file = interface.directory / LAUNCHED_INDEXERS
	if not file.exists():
		return []
	return file.read_text().splitlines()


@then(parsers.re(r"Machin indexer a été lancé une fois, avec (?P<options>«.+)"))
def launched_once(interface: Context, qtbot: QtBot, options: str) -> None:
	expected = " ".join(NAME.findall(options))
	qtbot.waitUntil(lambda: _launched_indexers(interface) != [], timeout=WAITING)
	# Un deuxième lancement aurait eu le temps de s'annoncer.
	quiet(qtbot, 500, reason="un deuxième lancement de Machin indexer")
	assert _launched_indexers(interface) == [expected]


@then("Machin indexer n'a pas été lancé")
def not_launched(interface: Context, qtbot: QtBot) -> None:
	quiet(qtbot, 500, reason="un lancement de Machin indexer")
	assert _launched_indexers(interface) == []
	assert interface.window is not None
	assert interface.window.launched_indexings == {}


@then("il n'y a pas de fenêtre de pré-écoute")
def without_preview(interface: Context) -> None:
	assert window(interface).preview is None


@then(parsers.parse("le fichier de configuration contient la ligne « {line} »"))
def contains_line(interface: Context, line: str) -> None:
	assert line in configuration_file(interface).read_text(encoding="utf-8").splitlines()
