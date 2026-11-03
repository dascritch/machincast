"""Scénarios du menu général de l'interface (https://github.com/dascritch/machincast/issues/117).

Les étapes de la fenêtre, de sa barre de menus et des fenêtres de dialogue sont dans tests/interface_steps.py. La
date de la dernière modification se lit dans un vrai dépôt git, créé dans le répertoire du scénario.
"""

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QLabel, QMessageBox
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast import __version__
from machincast.interface import columns, dialogs, version
from tests.interface_steps import Context

scenarios("menu_general.feature")


def git(drop: Path, instant: str, *command: str) -> None:
	"""Une commande git, à la date donnée, sous un nom d'essai."""
	date = datetime.fromisoformat(instant).isoformat()
	environment = {
		**os.environ,
		"GIT_AUTHOR_DATE": date,
		"GIT_COMMITTER_DATE": date,
		"GIT_AUTHOR_NAME": "Essai",
		"GIT_AUTHOR_EMAIL": "essai@exemple.invalid",
		"GIT_COMMITTER_NAME": "Essai",
		"GIT_COMMITTER_EMAIL": "essai@exemple.invalid",
	}
	subprocess.run(["git", "-C", str(drop), *command], check=True, env=environment)


@given(parsers.parse("MachinCast installé depuis un dépôt git dont le dernier commit date du « {instant} »"))
def git_drop(interface: Context, instant: str, drop: Path | None = None) -> None:
	if drop is None:
		drop = interface.directory / "machincast"
	drop.mkdir(parents=True)
	git(drop, instant, "init", "-q")
	git(drop, instant, "commit", "-q", "--allow-empty", "-m", "Essai")
	interface.monkeypatch.setattr(version, "DROP", drop)


# ─── Releases (https://github.com/dascritch/machincast/issues/208) ───


def drop(interface: Context) -> Path:
	return interface.directory / "machincast"


@given("ce commit porte le tag de la version de MachinCast")
def tag(interface: Context) -> None:
	git(drop(interface), "2026-10-28 15:00:00+00:00", "tag", f"v{__version__}")


@given(parsers.parse("{count:d} commits le suivent, le dernier daté du « {instant} »"))
def following_commits(interface: Context, count: int, instant: str) -> None:
	for _ in range(count):
		git(drop(interface), instant, "commit", "-q", "--allow-empty", "-m", "Suite")


@given(
	parsers.re(
		r"les nouveautés (?P<which>de la version de MachinCast|de la version précédente|d'une autre version), publiée"
		r" le (?P<day>[\d-]+) : « (?P<text>[^»]+) »"
	)
)
def news(sample_news: Path, which: str, day: str, text: str) -> None:
	"""Les sections s'ajoutent à la fin : la plus récente d'abord."""
	number = {
		"de la version de MachinCast": __version__,
		"de la version précédente": "0.0.1",
		"d'une autre version": "0.0.2",
	}
	old = ""
	if sample_news.exists():
		old = sample_news.read_text(encoding="utf-8")
	section = f"## {number[which]} — {day}\n\n{text}\n\n"
	sample_news.write_text(f"{old}{section}", encoding="utf-8")


@given("les nouveautés de la version précédente déjà vues")
def previous_views() -> None:
	columns.settings().setValue(version.NEWS_KEY, "0.0.1")


def with_commit(interface: Context, text: str) -> str:
	text = text.replace("<version>", __version__)
	if "<commit>" in text:
		commit = subprocess.run(
			["git", "-C", str(drop(interface)), "log", "-1", "--format=%h"], capture_output=True, text=True, check=True
		).stdout.strip()
		text = text.replace("<commit>", commit)
	return text


@then(parsers.parse("la fenêtre de version a montré les nouveautés de la version de MachinCast : « {text} »"))
def version_news(interface: Context, text: str) -> None:
	(shown_list,) = interface.version_news
	assert isinstance(shown_list, version.News)
	assert (shown_list.version, shown_list.text) == (__version__, text)


@then("la fenêtre de version n'a montré aucune nouveauté")
def version_without_news(interface: Context) -> None:
	assert interface.version_news == [None]


@then("aucune nouveauté n'a été montrée au lancement")
def no_to_launching(interface: Context) -> None:
	assert interface.shown_news == []


@then(parsers.parse("les nouveautés de la version de MachinCast ont été montrées au lancement : « {text} »"))
def shown_to_launching(interface: Context, text: str) -> None:
	(shown_list,) = interface.shown_news
	assert isinstance(shown_list, version.News)
	assert (shown_list.version, shown_list.text) == (__version__, text)


@then("les nouveautés n'ont été montrées qu'une fois au lancement")
def a_only_times(interface: Context) -> None:
	assert len(interface.shown_news) == 1, interface.shown_news


@given("MachinCast installé hors d'un dépôt git")
def outside_drop(interface: Context) -> None:
	interface.monkeypatch.setattr(version, "DROP", interface.directory)


@given("MachinCast installé dans un dossier d'un autre dépôt")
def in_other_drop(interface: Context) -> None:
	"""Le dépôt d'installation n'en est pas un : git trouverait celui du dossier parent."""
	git_drop(interface, "2026-10-18 12:05:00+00:00", interface.directory / "parent")
	installation = interface.directory / "parent" / "machincast"
	installation.mkdir()
	interface.monkeypatch.setattr(version, "DROP", installation)


@given("MachinCast installé depuis un dépôt git illisible")
def unreadable_drop(interface: Context) -> None:
	(interface.directory / ".git").mkdir()
	interface.monkeypatch.setattr(version, "DROP", interface.directory)


@given("MachinCast installé depuis un dépôt git, sans git")
def without_git(interface: Context) -> None:
	git_drop(interface, "2026-10-18 12:05:00+00:00")
	interface.monkeypatch.setenv("PATH", str(interface.directory / "rien"))


@then("la fenêtre de version donne la date du dernier commit du dépôt de MachinCast")
def drop_date(interface: Context) -> None:
	drop = Path(__file__).resolve().parents[1]
	output = subprocess.run(
		["git", "-C", str(drop), "log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%d à %H:%M"],
		capture_output=True,
		text=True,
		check=True,
	).stdout.strip()
	# Au commit d'une release, la fenêtre donne sa date de publication et le commit : la date ne se lit plus.
	(text,) = interface.versions
	commit = subprocess.run(
		["git", "-C", str(drop), "log", "-1", "--format=%h"], capture_output=True, text=True, check=True
	).stdout.strip()
	assert text.startswith(f"MachinCast {__version__}, "), text
	assert (f"dernière modification le {output}." in text) or (f"commit {commit}." in text), text


@then(parsers.parse("la fenêtre de version a dit « {text} »"))
def version_window(interface: Context, text: str) -> None:
	assert interface.versions == [with_commit(interface, text)]


# ─── Liens de la fenêtre de version (https://github.com/dascritch/machincast/issues/332) ───


@when(parsers.parse("je construis la fenêtre de version de « {text} »"), target_fixture="version_window")
def build_version_window(qtbot: QtBot, text: str) -> QMessageBox:
	window = dialogs.version_window(None, text, None)
	qtbot.addWidget(window)
	return window


def caption_of(window: QMessageBox) -> QLabel:
	caption = window.findChild(QLabel, "qt_msgbox_label")
	assert isinstance(caption, QLabel)
	return caption


@then("elle a les liens :")
def links(version_window: QMessageBox, datatable: list[list[str]]) -> None:
	"""Le Markdown est rendu en HTML par la fenêtre : les liens s'y lisent, texte et adresse."""
	_headers, *rows = datatable
	document = QTextDocument()
	document.setMarkdown(caption_of(version_window).text())
	html = document.toHtml()
	for text, address in rows:
		escapes = text.replace("<", "&lt;").replace(">", "&gt;")
		assert re.search(rf'<a href="{re.escape(address)}">(<span[^>]*>)?{re.escape(escapes)}', html), (text, html)


@then("ses liens s'ouvrent dans le navigateur web")
def opened_links(version_window: QMessageBox) -> None:
	assert caption_of(version_window).openExternalLinks()
