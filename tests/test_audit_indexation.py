"""Scénarios du document d'audit de l'indexation (https://github.com/dascritch/machincast/issues/11).

Les étapes des fichiers, des sonores et du lancement de Machin indexation sont dans tests/etapes_indexation.py ; le
répertoire et l'heure des documents sont fixés par tests/conftest.py (repertoire_d_audit).
"""

import csv
import html
import logging
import re
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then

from machincast.indexation import audit
from tests.etapes_indexation import Connexion

scenarios("audit_indexation.feature")

NOM = r"« ([^»]+) »"


def dans_le_scenario(texte: str, tmp_path: Path) -> str:
	"""Un « …/ » désigne le répertoire du scénario."""
	return texte.replace("…/", f"{tmp_path}/")


def lire_csv(repertoire: Path, nom: str) -> list[list[str]]:
	with (repertoire / nom).open(encoding="utf-8-sig", newline="") as fichier:
		return list(csv.reader(fichier, delimiter=";"))


@given("un répertoire d'audit où l'on ne peut pas écrire")
def repertoire_impossible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	# Un fichier à la place du répertoire : même root ne peut pas y écrire.
	bouchon = tmp_path / "pas-un-repertoire"
	bouchon.write_text("")
	monkeypatch.setattr(audit, "REPERTOIRE", bouchon)


@then(parsers.parse("le document d'audit « {nom} » contient :"))
def contenu_csv(repertoire_d_audit: Path, tmp_path: Path, nom: str, datatable: list[list[str]]) -> None:
	attendu = [[dans_le_scenario(valeur.strip(), tmp_path) for valeur in rangee] for rangee in datatable]
	assert lire_csv(repertoire_d_audit, nom) == attendu


@then(parsers.parse("le document d'audit « {nom} » signale ce fichier, « {verdict} », avec « {consequence} »"))
def anomalie_csv(repertoire_d_audit: Path, fichier: Path, nom: str, verdict: str, consequence: str) -> None:
	_entete, anomalie, _bilan = lire_csv(repertoire_d_audit, nom)
	_date, chemin, lu, probleme, suite = anomalie
	assert (chemin, lu, suite) == (str(fichier), verdict, consequence)
	assert (probleme != "") and (not probleme.startswith(verdict)), probleme


@then(parsers.parse("la page d'audit « {nom} » s'intitule « {titre} »"))
def titre_html(repertoire_d_audit: Path, nom: str, titre: str) -> None:
	page = (repertoire_d_audit / nom).read_text(encoding="utf-8")
	assert f"<title>{html.escape(titre)}</title>" in page
	assert f"<h1>{html.escape(titre)}</h1>" in page


@then(parsers.re(r"la page d'audit « (?P<nom>[^»]+) » montre (?P<textes>«.+)"))
def textes_html(repertoire_d_audit: Path, tmp_path: Path, nom: str, textes: str) -> None:
	page = (repertoire_d_audit / nom).read_text(encoding="utf-8")
	for texte in re.findall(NOM, textes):
		assert html.escape(dans_le_scenario(texte, tmp_path)) in page, texte


@then("l'annonce du document d'audit suit le bilan")
def annonce_apres_bilan(lancement: tuple[int, list[str]]) -> None:
	_code, messages = lancement
	assert messages[-2].startswith("indexation rapide : "), messages
	assert messages[-1].startswith("document d'audit : "), messages


@then(parsers.parse("la sortie d'erreur de Machin indexation mentionne « {texte} »"))
def erreur(caplog: pytest.LogCaptureFixture, texte: str) -> None:
	assert any((r.levelno >= logging.WARNING) and (texte in r.getMessage()) for r in caplog.records), caplog.text


@then("le log de la base est vide")
def log_vide(base_vide: Connexion) -> None:
	assert base_vide.execute("SELECT count(*) FROM log").fetchone() == (0,)
