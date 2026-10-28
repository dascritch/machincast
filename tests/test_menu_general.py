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
from machincast.interface import colonnes, version
from tests.etapes_interface import Contexte

scenarios("menu_general.feature")


def git(depot: Path, instant: str, *commande: str) -> None:
	"""Une commande git, à la date donnée, sous un nom d'essai."""
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
	subprocess.run(["git", "-C", str(depot), *commande], check=True, env=environnement)


@given(parsers.parse("MachinCast installé depuis un dépôt git dont le dernier commit date du « {instant} »"))
def depot_git(interface: Contexte, instant: str, depot: Path | None = None) -> None:
	if depot is None:
		depot = interface.repertoire / "machincast"
	depot.mkdir(parents=True)
	git(depot, instant, "init", "-q")
	git(depot, instant, "commit", "-q", "--allow-empty", "-m", "Essai")
	interface.monkeypatch.setattr(version, "DEPOT", depot)


# ─── Releases (https://github.com/dascritch/machincast/issues/208) ───


def depot(interface: Contexte) -> Path:
	return interface.repertoire / "machincast"


@given("ce commit porte le tag de la version de MachinCast")
def tag(interface: Contexte) -> None:
	git(depot(interface), "2026-10-28 15:00:00+00:00", "tag", f"v{__version__}")


@given(parsers.parse("{nombre:d} commits le suivent, le dernier daté du « {instant} »"))
def commits_suivants(interface: Contexte, nombre: int, instant: str) -> None:
	for _ in range(nombre):
		git(depot(interface), instant, "commit", "-q", "--allow-empty", "-m", "Suite")


@given(
	parsers.re(
		r"les nouveautés (?P<quelle>de la version de MachinCast|de la version précédente|d'une autre version), publiée"
		r" le (?P<jour>[\d-]+) : « (?P<texte>[^»]+) »"
	)
)
def nouveautes(nouveautes_du_test: Path, quelle: str, jour: str, texte: str) -> None:
	"""Les sections s'ajoutent à la fin : la plus récente d'abord."""
	numero = {
		"de la version de MachinCast": __version__,
		"de la version précédente": "0.0.1",
		"d'une autre version": "0.0.2",
	}
	ancien = ""
	if nouveautes_du_test.exists():
		ancien = nouveautes_du_test.read_text(encoding="utf-8")
	section = f"## {numero[quelle]} — {jour}\n\n{texte}\n\n"
	nouveautes_du_test.write_text(f"{ancien}{section}", encoding="utf-8")


@given("les nouveautés de la version précédente déjà vues")
def precedentes_vues() -> None:
	colonnes.reglages().setValue(version.CLE_DES_NOUVEAUTES, "0.0.1")


def avec_le_commit(interface: Contexte, texte: str) -> str:
	texte = texte.replace("<version>", __version__)
	if "<commit>" in texte:
		commit = subprocess.run(
			["git", "-C", str(depot(interface)), "log", "-1", "--format=%h"], capture_output=True, text=True, check=True
		).stdout.strip()
		texte = texte.replace("<commit>", commit)
	return texte


@then(parsers.parse("la fenêtre de version a montré les nouveautés de la version de MachinCast : « {texte} »"))
def nouveautes_de_la_version(interface: Contexte, texte: str) -> None:
	(montrees,) = interface.nouveautes_de_la_version
	assert isinstance(montrees, version.Nouveautes)
	assert (montrees.version, montrees.texte) == (__version__, texte)


@then("la fenêtre de version n'a montré aucune nouveauté")
def version_sans_nouveautes(interface: Contexte) -> None:
	assert interface.nouveautes_de_la_version == [None]


@then("aucune nouveauté n'a été montrée au lancement")
def aucune_au_lancement(interface: Contexte) -> None:
	assert interface.nouveautes_montrees == []


@then(parsers.parse("les nouveautés de la version de MachinCast ont été montrées au lancement : « {texte} »"))
def montrees_au_lancement(interface: Contexte, texte: str) -> None:
	(montrees,) = interface.nouveautes_montrees
	assert isinstance(montrees, version.Nouveautes)
	assert (montrees.version, montrees.texte) == (__version__, texte)


@then("les nouveautés n'ont été montrées qu'une fois au lancement")
def une_seule_fois(interface: Contexte) -> None:
	assert len(interface.nouveautes_montrees) == 1, interface.nouveautes_montrees


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
	# Au commit d'une release, la fenêtre donne sa date de publication et le commit : la date ne se lit plus.
	(texte,) = interface.versions
	commit = subprocess.run(
		["git", "-C", str(depot), "log", "-1", "--format=%h"], capture_output=True, text=True, check=True
	).stdout.strip()
	assert texte.startswith(f"MachinCast {__version__}, "), texte
	assert (f"dernière modification le {sortie}." in texte) or (f"commit {commit}." in texte), texte


@then(parsers.parse("la fenêtre de version a dit « {texte} »"))
def fenetre_de_version(interface: Contexte, texte: str) -> None:
	assert interface.versions == [avec_le_commit(interface, texte)]
