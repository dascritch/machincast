"""Scénarios du menu général de l'interface (https://github.com/dascritch/machincast/issues/117).

Les étapes de la fenêtre, de sa barre de menus et des fenêtres de dialogue sont dans tests/etapes_interface.py. La
date de la dernière modification se lit dans un vrai dépôt git, créé dans le répertoire du scénario.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then

from machincast import __version__
from machincast.interface import version
from tests.etapes_interface import Contexte

scenarios("menu_general.feature")


@given(parsers.parse("MachinCast installé depuis un dépôt git dont le dernier commit date du « {instant} »"))
def depot_git(interface: Contexte, instant: str, depot: Path | None = None) -> None:
	if depot is None:
		depot = interface.repertoire / "machincast"
	depot.mkdir(parents=True)
	date = datetime.fromisoformat(instant).isoformat()
	environnement = {
		**os.environ,
		"GIT_AUTHOR_DATE": date,
		"GIT_COMMITTER_DATE": date,
		"GIT_AUTHOR_NAME": "Essai",
		"GIT_AUTHOR_EMAIL": "essai@exemple.invalid",
		"GIT_COMMITTER_NAME": "Essai",
		"GIT_COMMITTER_EMAIL": "essai@exemple.invalid",
	}
	for commande in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "Essai"]):
		subprocess.run(["git", "-C", str(depot), *commande], check=True, env=environnement)
	interface.monkeypatch.setattr(version, "DEPOT", depot)


@given("MachinCast installé hors d'un dépôt git")
def hors_depot(interface: Contexte) -> None:
	interface.monkeypatch.setattr(version, "DEPOT", interface.repertoire)


@given("MachinCast installé dans un dossier d'un autre dépôt")
def dans_un_autre_depot(interface: Contexte) -> None:
	"""Le dépôt d'installation n'en est pas un : git trouverait celui du dossier parent."""
	depot_git(interface, "2026-10-18 12:05:00+00:00", interface.repertoire / "parent")
	installation = interface.repertoire / "parent" / "machincast"
	installation.mkdir()
	interface.monkeypatch.setattr(version, "DEPOT", installation)


@given("MachinCast installé depuis un dépôt git illisible")
def depot_illisible(interface: Contexte) -> None:
	(interface.repertoire / ".git").mkdir()
	interface.monkeypatch.setattr(version, "DEPOT", interface.repertoire)


@given("MachinCast installé depuis un dépôt git, sans git")
def sans_git(interface: Contexte) -> None:
	depot_git(interface, "2026-10-18 12:05:00+00:00")
	interface.monkeypatch.setenv("PATH", str(interface.repertoire / "rien"))


@then("la fenêtre de version donne la date du dernier commit du dépôt de MachinCast")
def date_du_depot(interface: Contexte) -> None:
	depot = Path(__file__).resolve().parents[1]
	sortie = subprocess.run(
		["git", "-C", str(depot), "log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%d à %H:%M"],
		capture_output=True,
		text=True,
		check=True,
	).stdout.strip()
	assert interface.versions == [f"MachinCast {__version__}, dernière modification le {sortie}."]


@then(parsers.parse("la fenêtre de version a dit « {texte} »"))
def fenetre_de_version(interface: Contexte, texte: str) -> None:
	assert interface.versions == [texte.replace("<version>", __version__)]
