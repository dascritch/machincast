"""Scénarios du lancement de l'indexation depuis l'interface (https://github.com/dascritch/machincast/issues/38,
https://github.com/dascritch/machincast/issues/120).

Les étapes de la fenêtre, de sa barre de menus et des fenêtres de dialogue sont dans tests/etapes_interface.py.
Machin indexation est remplacé par un programme factice, lancé pour de vrai dans un processus détaché : il note ses
options dans un fichier, puis attend qu'un autre fichier apparaisse.
"""

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import indexation
from machincast.interface.fenetre import SUIVI_INDEXATION
from tests.etapes_interface import ATTENTE, NOM, Contexte, fenetre

scenarios("indexation_interface.feature")

COMMANDE_INDEXATION = indexation.commande_indexation
"""La vraie, que le Contexte remplace par celle du programme factice."""

FACTICE = """
import pathlib, sys, time
pathlib.Path(sys.argv[1]).write_text("\\n".join(sys.argv[3:]))
fin = pathlib.Path(sys.argv[2])
while not fin.exists():
	time.sleep(0.05)
"""


@pytest.fixture
def factice(interface: Contexte) -> Iterator[tuple[Path, Path]]:
	"""Le fichier des options du programme factice, et celui qui le termine ; il est terminé en fin de scénario."""
	options, fin = interface.repertoire / "options-indexation", interface.repertoire / "fin-indexation"
	yield options, fin
	fin.touch()


@given("un Machin indexation factice, qui attend")
def machin_factice(interface: Contexte, factice: tuple[Path, Path]) -> None:
	options, fin = factice
	commande = [sys.executable, "-c", FACTICE, str(options), str(fin)]
	interface.monkeypatch.setattr(indexation, "commande_indexation", lambda _configuration: commande)


@given("un Machin indexation introuvable")
def machin_introuvable(interface: Contexte) -> None:
	commande = [str(interface.repertoire / "aucun" / "Machin_indexation")]
	interface.monkeypatch.setattr(indexation, "commande_indexation", lambda _configuration: commande)


@when("l'interface a regardé plusieurs fois si le Machin indexation factice tourne")
def plusieurs_regards(qtbot: QtBot) -> None:
	qtbot.wait(SUIVI_INDEXATION * 2 + 500)


@when("le Machin indexation factice se termine")
def terminer(interface: Contexte, qtbot: QtBot, factice: tuple[Path, Path]) -> None:
	_options, fin = factice
	fin.touch()
	qtbot.waitUntil(lambda: fenetre(interface).indexation_lancee is None, timeout=ATTENTE)


@then(parsers.re(r"Machin indexation a été lancé avec (?P<options>«.+)"))
def lance_avec(qtbot: QtBot, factice: tuple[Path, Path], options: str) -> None:
	fichier, _fin = factice
	qtbot.waitUntil(fichier.exists, timeout=ATTENTE)
	assert fichier.read_text().splitlines() == NOM.findall(options)


@then("le Machin indexation factice tourne toujours")
def tourne_toujours(interface: Contexte, factice: tuple[Path, Path]) -> None:
	numero = fenetre(interface).indexation_lancee
	assert numero is not None
	assert indexation.processus_actif(numero)
	assert not factice[1].exists()


@then(parsers.re(r"la commande d'indexation, pour la configuration (?P<configuration>.+), est « (?P<attendue>.+) »"))
def commande(interface: Contexte, monkeypatch: pytest.MonkeyPatch, configuration: str, attendue: str) -> None:
	monkeypatch.chdir(interface.repertoire)
	chemin: Path | None = None
	if configuration != "par défaut":
		(nom,) = NOM.findall(configuration)
		chemin = Path(nom)
	attendue = interface.chemin_dans(attendue).replace("<python>", sys.executable)
	assert COMMANDE_INDEXATION(chemin) == attendue.split(" ")
