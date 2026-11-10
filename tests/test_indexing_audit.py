"""Scénarios du document d'audit de l'indexation (https://github.com/dascritch/machincast/issues/11).

Les étapes des fichiers, des sonores et du lancement de Machin indexer sont dans tests/indexing_steps.py ; le
répertoire et l'heure des documents sont fixés par tests/conftest.py (audit_directory).
"""

import html
import logging
import re
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then

from machincast.indexer import audit
from tests.indexing_steps import Connection, read_csv

scenarios("indexing_audit.feature")

NAME = r"« ([^»]+) »"


def in_scenario(text: str, tmp_path: Path) -> str:
	"""Un « …/ » désigne le répertoire du scénario."""
	return text.replace("…/", f"{tmp_path}/")


@given("un répertoire d'audit où l'on ne peut pas écrire")
def impossible_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	# Un fichier à la place du répertoire : même root ne peut pas y écrire.
	stub = tmp_path / "pas-un-repertoire"
	stub.write_text("")
	monkeypatch.setattr(audit, "DIRECTORY", stub)


@then(parsers.parse("le document d'audit « {name} » contient :"))
def csv_content(audit_directory: Path, tmp_path: Path, name: str, datatable: list[list[str]]) -> None:
	expected = []
	for row in datatable:
		value_list = []
		for value in row:
			value_list.append(in_scenario(value.strip(), tmp_path))
		expected.append(value_list)
	assert read_csv(audit_directory, name) == expected


@then(parsers.parse("la page d'audit « {name} » s'intitule « {title} »"))
def html_title(audit_directory: Path, name: str, title: str) -> None:
	page = (audit_directory / name).read_text(encoding="utf-8")
	assert f"<title>{html.escape(title)}</title>" in page
	assert f"<h1>{html.escape(title)}</h1>" in page


@then(parsers.re(r"la page d'audit « (?P<name>[^»]+) » montre (?P<texts>«.+)"))
def html_texts(audit_directory: Path, tmp_path: Path, name: str, texts: str) -> None:
	page = (audit_directory / name).read_text(encoding="utf-8")
	for text in re.findall(NAME, texts):
		assert html.escape(in_scenario(text, tmp_path)) in page, text


@then("l'annonce du document d'audit suit le bilan")
def announces_after_report(launching: tuple[int, list[str]]) -> None:
	_code, messages = launching
	assert messages[-2].startswith("indexation rapide : "), messages
	assert messages[-1].startswith("document d'audit : "), messages


@then(parsers.parse("la sortie d'erreur de Machin indexer mentionne « {text} »"))
def error(caplog: pytest.LogCaptureFixture, text: str) -> None:
	found = False
	for r in caplog.records:
		if (r.levelno >= logging.WARNING) and (text in r.getMessage()):
			found = True
			break
	assert found, caplog.text


@then("le log de la base est vide")
def empty_log(empty_database: Connection) -> None:
	assert empty_database.execute("SELECT count(*) FROM log").fetchone() == (0,)
