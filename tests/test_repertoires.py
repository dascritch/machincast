"""Étapes de l'indexation récursive des répertoires de banques (https://github.com/dascritch/machincast/issues/9)."""

import re
import shutil
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then

from tests.etapes_indexation import Execution, indexer
from tests.sons import copie_de_test, corrompre

scenarios("repertoires.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ELEMENT = re.compile(r"« ([^»]+) »")
# Extension du fichier demandé → fichier de test à copier (tests/fichiers-sonores).
FORMATS = {
	"mp3": "mp3",
	"m4a": "m4a",
	"aac": "aac",
	"ogg": "ogg",
	"flac": "flac",
	"wav": "wav",
	"aiff": "aiff",
	"aif": "aiff",
}


@pytest.fixture
def racine(tmp_path: Path) -> Path:
	"""Répertoire temporaire où se trouvent les répertoires des banques du scénario."""
	chemin = tmp_path / "radio"
	chemin.mkdir()
	return chemin


def banque(base: Connexion, nom: str) -> int:
	ligne = base.execute("SELECT id FROM banques WHERE nom_interne = %s", (nom,)).fetchone()
	if ligne is None:
		ligne = base.execute(
			"INSERT INTO banques (nom_interne, mode) VALUES (%s, 'sequentiel') RETURNING id", (nom,)
		).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


@given(parsers.parse("une banque « {nom} » alimentée par le répertoire « {repertoire} »"))
def banque_alimentee(base_vide: Connexion, racine: Path, nom: str, repertoire: str) -> None:
	base_vide.execute(
		"INSERT INTO banques_repertoires (banque_id, repertoire) VALUES (%s, %s)",
		(banque(base_vide, nom), str(racine / repertoire)),
	)


@given(parsers.re(r"le fichier « (?P<relatif>[^»]+) », (?P<etat>sain|endommagé|quelconque)"))
def fichier(tmp_path: Path, racine: Path, relatif: str, etat: str) -> None:
	cible = racine / relatif
	cible.parent.mkdir(parents=True, exist_ok=True)
	if etat == "quelconque":
		cible.write_bytes(b"pas du son")
		return
	extension = cible.suffix.lstrip(".").lower()
	source = copie_de_test(FORMATS[extension] if etat == "sain" else "mp3", tmp_path)
	if etat == "endommagé":
		corrompre(source, 1000, 1 / 3)
	shutil.move(source, cible)


@given("l'indexeur a fait une indexation rapide")
def indexation_prealable(base_vide: Connexion, caplog: pytest.LogCaptureFixture) -> None:
	indexer(base_vide, caplog, audit_complet=False)


@given(parsers.parse("« {relatif} » a été retiré à la main de la banque « {nom} »"))
def retire(base_vide: Connexion, racine: Path, relatif: str, nom: str) -> None:
	base_vide.execute(
		"DELETE FROM banques_sonores WHERE banque_id = %s"
		" AND sonore_id = (SELECT id FROM sonores WHERE emplacement = %s)",
		(banque(base_vide, nom), str(racine / relatif)),
	)


@then(parsers.re(r"la banque « (?P<nom>[^»]+) » contient, dans l'ordre, (?P<liste>.+)"))
def contenu(base_vide: Connexion, racine: Path, nom: str, liste: str) -> None:
	lignes = base_vide.execute(
		"SELECT s.emplacement FROM banques_sonores bs JOIN sonores s ON s.id = bs.sonore_id"
		" WHERE bs.banque_id = %s ORDER BY bs.position",
		(banque(base_vide, nom),),
	).fetchall()
	assert [str(ligne[0]) for ligne in lignes] == [str(racine / relatif) for relatif in ELEMENT.findall(liste)]


@then(parsers.parse("le sonore de « {relatif} » est à l'état « {etat} »"))
def etat_du_sonore(base_vide: Connexion, racine: Path, relatif: str, etat: str) -> None:
	ligne = base_vide.execute(
		"SELECT etat::text FROM sonores WHERE emplacement = %s", (str(racine / relatif),)
	).fetchone()
	assert ligne is not None, f"aucun sonore pour {relatif}"
	assert ligne[0] == etat


@then(parsers.re(r"la base contient (?P<nombre>\d+) sonores?"))
def nombre_de_sonores(base_vide: Connexion, nombre: str) -> None:
	ligne = base_vide.execute("SELECT count(*) FROM sonores").fetchone()
	assert ligne is not None and ligne[0] == int(nombre)


@then(
	parsers.parse(
		"la sortie d'erreur signale le répertoire « {repertoire} » comme introuvable, pour la banque « {nom} »"
	)
)
def repertoire_signale(execution: Execution, racine: Path, repertoire: str, nom: str) -> None:
	lignes = [ligne for ligne in execution.erreurs.splitlines() if str(racine / repertoire) in ligne]
	assert lignes, execution.erreurs
	assert "introuvable" in lignes[0] and nom in lignes[0], lignes[0]
