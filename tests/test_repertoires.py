"""Étapes de l'indexation récursive des répertoires de banques (https://github.com/dascritch/machincast/issues/9)."""

import argparse
import dataclasses
import logging
import re
import shutil
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.indexation.__main__ import executer
from tests.base_test import configuration_test
from tests.etapes_indexation import Execution
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
	assert (ligne is not None) and (ligne[0] == int(nombre))


@then(
	parsers.parse(
		"la sortie d'erreur signale le répertoire « {repertoire} » comme introuvable, pour la banque « {nom} »"
	)
)
def repertoire_signale(execution: Execution, racine: Path, repertoire: str, nom: str) -> None:
	lignes = [ligne for ligne in execution.erreurs.splitlines() if str(racine / repertoire) in ligne]
	assert lignes, execution.erreurs
	assert ("introuvable" in lignes[0]) and (nom in lignes[0]), lignes[0]


@then("la sortie standard montre, ligne par ligne :")
def sortie_standard(execution: Execution, racine: Path, datatable: list[list[str]]) -> None:
	"""Un chemin qui commence par « …/ » est dans le répertoire du scénario."""
	_entete, *lignes = datatable
	assert execution.informations == [ligne.strip().replace("…/", f"{racine}/") for (ligne,) in lignes]


@then(parsers.parse("la sortie d'erreur signale « {chemin} », avec « {consequence} »"))
def erreur_signalee(execution: Execution, racine: Path, chemin: str, consequence: str) -> None:
	(ligne,) = execution.erreurs.splitlines()
	assert ligne.startswith(f"{chemin.replace('…/', f'{racine}/')} : "), ligne
	assert ligne.endswith(f" ; {consequence}"), ligne


@when("Machin indexation est lancé sur la base de test", target_fixture="lancement")
def lancer_sur_la_base_de_test(caplog: pytest.LogCaptureFixture) -> tuple[int, list[str]]:
	"""Son action, avec une configuration dont la base de production est la base de test."""
	configuration = configuration_test()
	sur_la_base_de_test = dataclasses.replace(
		configuration, base=dataclasses.replace(configuration.base, production=configuration.base.test)
	)
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"):
		code = executer(sur_la_base_de_test, argparse.Namespace(audit_complet=False, fenetre=False))
	return code, [enregistrement.getMessage() for enregistrement in caplog.records]


@then(parsers.parse("Machin indexation se termine avec le code {code:d}, en signalant « {texte} »"))
def lancement_termine(lancement: tuple[int, list[str]], code: int, texte: str) -> None:
	obtenu, messages = lancement
	assert (obtenu, messages[-1]) == (code, texte), messages


@then("le verrou de l'indexation a été rendu dès la fin de l'indexation")
def verrou_rendu(execution: Execution) -> None:
	assert execution.verrou_rendu


@given(parsers.parse("« {relatif} » déplacé en « {destination} »"))
def deplacer(racine: Path, relatif: str, destination: str) -> None:
	"""Un déplacement hors de MachinCast, comme le ferait le navigateur de fichiers."""
	cible = racine / destination
	cible.parent.mkdir(parents=True, exist_ok=True)
	shutil.move(racine / relatif, cible)
