"""Étapes partagées des scénarios de l'indexeur : fichiers sonores, sonores en base, passage de l'indexeur.

Chargé comme greffon pytest par tests/conftest.py, pour servir à verification.feature
(https://github.com/dascritch/machincast/issues/7) comme à tags.feature (https://github.com/dascritch/machincast/issues/8).
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, then, when

from machincast.base import Role, connecter
from machincast.indexation.decodage import DecodeurIndisponible, Verification, verifier_fichier
from machincast.indexation.verification import Bilan, texte_bilan, verifier_sonores
from tests.base_test import parametres_base_test
from tests.sons import copie_de_test, corrompre

Connexion = psycopg.Connection[tuple[object, ...]]
DECIMAL = r"\d+(?:,\d+)?"


def nombre(texte: str) -> float:
	"""« 12,5 » → 12.5 : les scénarios écrivent les nombres à la française."""
	return float(texte.replace(",", "."))


@dataclass
class Execution:
	bilan: Bilan
	erreurs: str


# ─── Fichiers ──────────────────────────────────────────────


@given(parsers.re(r"un fichier (?P<format_sonore>\w+) sain"), target_fixture="fichier")
def fichier_sain(tmp_path: Path, format_sonore: str) -> Path:
	return copie_de_test(format_sonore, tmp_path)


@given(parsers.re(r"un fichier (?P<format_sonore>\w+) tagué"), target_fixture="fichier")
def fichier_tague(tmp_path: Path, format_sonore: str) -> Path:
	return copie_de_test(format_sonore, tmp_path, "tags")


@when("je vérifie ce fichier", target_fixture="resultat")
def verifier(fichier: Path) -> Verification | DecodeurIndisponible:
	try:
		return verifier_fichier(fichier)
	except DecodeurIndisponible as erreur:
		return erreur


# ─── Sonores en base ───────────────────────────────────────


def inserer_sonore(
	base: Connexion, emplacement: str, etat: str, champs_edites: list[str] | None = None, duree: float | None = None
) -> int:
	ligne = base.execute(
		"INSERT INTO sonores (type, emplacement, etat, champs_edites, duree)"
		" VALUES ('fichier', %s, %s, %s, %s) RETURNING id",
		(emplacement, etat, champs_edites or [], None if duree is None else timedelta(seconds=duree)),
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


@given("un fichier mp3 endommagé", target_fixture="fichier")
def fichier_endommage(tmp_path: Path) -> Path:
	fichier = copie_de_test("mp3", tmp_path)
	corrompre(fichier, 1000, 1 / 3)
	return fichier


@given(parsers.parse("un sonore à l'état « {etat} » pour ce fichier"), target_fixture="sonore")
def sonore_dans_etat(base_vide: Connexion, fichier: Path, etat: str) -> int:
	return inserer_sonore(base_vide, str(fichier), etat)


@given(
	parsers.re(
		r"un sonore à l'état « actif » pour ce fichier, dont la durée a été saisie à la main"
		rf" à (?P<secondes>{DECIMAL}) secondes"
	),
	target_fixture="sonore",
)
def sonore_duree_editee(base_vide: Connexion, fichier: Path, secondes: str) -> int:
	return inserer_sonore(base_vide, str(fichier), "actif", ["duree"], nombre(secondes))


@given(parsers.parse("un deuxième fichier {format_sonore} sain, dont le sonore est à l'état « {etat} »"))
def deuxieme_sonore(base_vide: Connexion, tmp_path: Path, format_sonore: str, etat: str) -> None:
	repertoire = tmp_path / "deuxieme"
	repertoire.mkdir()
	inserer_sonore(base_vide, str(copie_de_test(format_sonore, repertoire)), etat)


@given("un fichier introuvable", target_fixture="fichier")
def fichier_introuvable(tmp_path: Path) -> Path:
	return tmp_path / "disparu.flac"


@given("un stream enregistré", target_fixture="stream")
def stream(base_vide: Connexion) -> tuple[int, object]:
	ligne = base_vide.execute(
		"INSERT INTO sonores (type, url_stream) VALUES ('stream', 'https://flux.exemple/direct')"
		" RETURNING id, modifie_le"
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0])), ligne[1]


def indexer(base_vide: Connexion, caplog: pytest.LogCaptureFixture, audit_complet: bool) -> Execution:
	# Le compte qui lance les tests endosse déjà le rôle de l'indexation (vérifié par base_vide).
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"), connecter(*parametres_base_test(), Role.INDEXATION) as c:
		bilan = verifier_sonores(c, audit_complet=audit_complet)
	# Les anomalies et les erreurs vont sur la sortie d'erreur : niveau WARNING et au-delà.
	anomalies = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
	return Execution(bilan, "\n".join(anomalies))


@when("l'indexeur fait un audit complet", target_fixture="execution")
def audit_complet(base_vide: Connexion, caplog: pytest.LogCaptureFixture) -> Execution:
	return indexer(base_vide, caplog, audit_complet=True)


@when("l'indexeur fait une indexation rapide", target_fixture="execution")
def indexation_rapide(base_vide: Connexion, caplog: pytest.LogCaptureFixture) -> Execution:
	return indexer(base_vide, caplog, audit_complet=False)


def lire_sonore(base: Connexion, sonore: int) -> tuple[object, ...]:
	ligne = base.execute(
		"SELECT etat::text, duree, fichier_modifie_le, fichier_taille, modifie_le FROM sonores WHERE id = %s",
		(sonore,),
	).fetchone()
	assert ligne is not None
	return ligne


@then(parsers.parse("le sonore est à l'état « {etat} »"))
def sonore_etat(base_vide: Connexion, sonore: int, etat: str) -> None:
	assert lire_sonore(base_vide, sonore)[0] == etat


@then(parsers.re(rf"sa durée en base est de (?P<attendue>{DECIMAL}) secondes? à (?P<marge>{DECIMAL}) seconde près"))
def duree_en_base(base_vide: Connexion, sonore: int, attendue: str, marge: str) -> None:
	duree = lire_sonore(base_vide, sonore)[1]
	assert isinstance(duree, timedelta), duree
	assert abs(duree.total_seconds() - nombre(attendue)) <= nombre(marge), duree


@then("la date de modification et la taille du fichier sont enregistrées")
def date_et_taille(base_vide: Connexion, sonore: int, fichier: Path) -> None:
	_, _, modifie_le, taille, _ = lire_sonore(base_vide, sonore)
	etat = fichier.stat()
	assert taille == etat.st_size
	assert modifie_le == datetime.fromtimestamp(etat.st_mtime, tz=UTC)


@then("rien n'est signalé sur la sortie d'erreur")
def rien_signale(execution: Execution) -> None:
	assert execution.erreurs == ""


@then(parsers.parse("la sortie d'erreur signale ce fichier comme « {verdict} », avec « {consequence} »"))
def erreur_signalee(execution: Execution, fichier: Path, verdict: str, consequence: str) -> None:
	lignes = [ligne for ligne in execution.erreurs.splitlines() if ligne.startswith(f"{fichier} : ")]
	assert len(lignes) == 1, execution.erreurs
	assert f" : {verdict} : " in lignes[0] and lignes[0].endswith(f" ; {consequence}"), lignes[0]


@then(parsers.parse("le bilan indique « {texte} »"))
def bilan_indique(execution: Execution, texte: str) -> None:
	assert texte_bilan(execution.bilan) == texte


@then("le stream n'a pas été modifié")
def stream_intact(base_vide: Connexion, stream: tuple[int, object]) -> None:
	etat, duree, modifie_le_fichier, taille, modifie_le = lire_sonore(base_vide, stream[0])
	assert (etat, duree, modifie_le_fichier, taille) == ("actif", None, None, None)
	assert modifie_le == stream[1]


def lire_tags_en_base(base: Connexion, sonore: int) -> tuple[object, object, object]:
	ligne = base.execute(
		"SELECT artiste, titre, metadonnees_musicales FROM sonores WHERE id = %s", (sonore,)
	).fetchone()
	assert ligne is not None
	return ligne[0], ligne[1], ligne[2]


@then(parsers.parse("en base, l'artiste est « {artiste} » et le titre « {titre} »"))
def artiste_et_titre_en_base(base_vide: Connexion, sonore: int, artiste: str, titre: str) -> None:
	assert lire_tags_en_base(base_vide, sonore)[:2] == (artiste, titre)
