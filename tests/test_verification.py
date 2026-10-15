"""Étapes des scénarios de vérification des fichiers (https://github.com/dascritch/machincast/issues/7)."""

import logging
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import gi
import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, autoriser_utilisateur, connecter
from machincast.indexation import decodage
from machincast.indexation.decodage import DecodeurIndisponible, EtatFichier, Verification, verifier_fichier
from machincast.indexation.verification import Bilan, texte_bilan, verifier_sonores
from tests.base_test import CONFIGURATION_TEST, parametres_base_test
from tests.sons import copie_de_test, corrompre, tronquer

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("verification.feature")

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


@given(parsers.parse('un fichier "{nom}" qui contient du texte'), target_fixture="fichier")
def fichier_texte(tmp_path: Path, nom: str) -> Path:
	chemin = tmp_path / nom
	chemin.write_text("Ceci n'est pas un son.\n" * 200, encoding="utf-8")
	return chemin


@given(parsers.parse('un fichier "{nom}" vide'), target_fixture="fichier")
def fichier_vide(tmp_path: Path, nom: str) -> Path:
	chemin = tmp_path / nom
	chemin.touch()
	return chemin


@given("ce fichier tronqué de moitié")
def fichier_tronque(fichier: Path) -> None:
	tronquer(fichier, 0.5)


@given(parsers.parse("{octets:d} octets corrompus au tiers de ce fichier"))
def fichier_corrompu(fichier: Path, octets: int) -> None:
	corrompre(fichier, octets, 1 / 3)


@given("un fichier WAV dont la lecture se bloque après son début", target_fixture="fichier")
def fichier_bloque(tmp_path: Path) -> Iterator[Path]:
	"""Tube nommé : un écrivain y verse la première moitié d'un WAV, puis attend 3 secondes avant de le fermer."""
	donnees = copie_de_test("wav", tmp_path).read_bytes()
	debut = donnees[: len(donnees) // 2]
	tube = tmp_path / "bloque.wav"
	os.mkfifo(tube)

	def alimenter() -> None:
		with tube.open("wb") as ecrivain:  # attend que le décodeur ouvre le tube
			ecrivain.write(debut)
			ecrivain.flush()
			time.sleep(3)

	ecrivain = threading.Thread(target=alimenter, daemon=True)
	ecrivain.start()
	yield tube
	ecrivain.join(timeout=10)


@dataclass
class Tentatives:
	nombre: int = 0


@given(
	parsers.re(r"un décodage qui ne démarre (?:pas aux (?P<echecs>\d+) premières tentatives|jamais)"),
	target_fixture="tentatives",
)
def demarrage_bloque(monkeypatch: pytest.MonkeyPatch, echecs: str | None) -> Tentatives:
	"""Simule le blocage de GStreamer au démarrage du pipeline, constaté sur environ 1 % des décodages."""
	tentatives = Tentatives()
	vraie_tentative = decodage._tentative

	def tentative(chemin: Path, delai_demarrage: timedelta, delai_sans_progression: timedelta) -> Verification | None:
		tentatives.nombre += 1
		if echecs is None or tentatives.nombre <= int(echecs):
			return None
		return vraie_tentative(chemin, delai_demarrage, delai_sans_progression)

	monkeypatch.setattr(decodage, "_tentative", tentative)
	return tentatives


@then(parsers.parse("le décodage a été tenté {nombre:d} fois"))
def tente(tentatives: Tentatives, nombre: int) -> None:
	assert tentatives.nombre == nombre


@given("le décodeur GStreamer de l'AIFF désactivé")
def aiff_desactive() -> Iterator[None]:
	"""Simule un paquet absent : decodebin ignore les éléments de rang NONE.

	Plusieurs paquets savent lire l'AIFF (aiffparse de plugins-bad, avdemux_aiff de libav) : tous sont écartés.
	"""
	Gst.init(None)
	aiff = Gst.Caps.from_string("audio/x-aiff")
	assert aiff is not None
	fabriques = [
		fabrique
		for fabrique in Gst.ElementFactory.list_get_elements(Gst.ELEMENT_FACTORY_TYPE_DEMUXER, Gst.Rank.MARGINAL)
		if fabrique.can_sink_any_caps(aiff)
	]
	assert fabriques, "aucun lecteur d'AIFF : installer gstreamer1.0-plugins-bad"
	rangs = [(fabrique, fabrique.get_rank()) for fabrique in fabriques]
	for fabrique in fabriques:
		fabrique.set_rank(Gst.Rank.NONE)
	yield
	for fabrique, rang in rangs:
		fabrique.set_rank(rang)


@when("je vérifie ce fichier", target_fixture="resultat")
def verifier(fichier: Path) -> Verification | DecodeurIndisponible:
	try:
		return verifier_fichier(fichier)
	except DecodeurIndisponible as erreur:
		return erreur


@when(
	parsers.parse("je vérifie ce fichier en abandonnant après {secondes:d} seconde sans progression"),
	target_fixture="resultat",
)
def verifier_avec_delai(fichier: Path, secondes: int) -> Verification:
	return verifier_fichier(fichier, delai_sans_progression=timedelta(seconds=secondes))


@then("le fichier est sain")
def est_sain(resultat: Verification) -> None:
	assert isinstance(resultat, Verification), resultat
	assert resultat.etat is EtatFichier.SAIN, resultat.probleme


@then(parsers.re(rf"sa durée mesurée est de (?P<attendue>{DECIMAL}) secondes? à (?P<marge>{DECIMAL}) seconde près"))
def duree_mesuree(resultat: Verification, attendue: str, marge: str) -> None:
	assert resultat.duree is not None
	assert abs(resultat.duree.total_seconds() - nombre(attendue)) <= nombre(marge), resultat.duree


@then(parsers.parse("le fichier est déclaré {verdict}"))
def est_declare(resultat: Verification, verdict: str) -> None:
	assert isinstance(resultat, Verification), resultat
	assert resultat.etat == verdict, f"{resultat.etat} : {resultat.probleme}"
	assert resultat.probleme is not None and resultat.probleme.startswith(verdict)


@then(parsers.parse("le problème signalé mentionne « {texte} »"))
def probleme_mentionne(resultat: Verification, texte: str) -> None:
	assert resultat.probleme is not None and texte in resultat.probleme, resultat.probleme


@then("la vérification s'arrête en signalant un décodeur absent et le paquet à installer")
def decodeur_absent(resultat: Verification | DecodeurIndisponible) -> None:
	assert isinstance(resultat, DecodeurIndisponible), resultat
	assert "gstreamer1.0-plugins-bad" in str(resultat)


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


@when("l'indexeur vérifie les sonores", target_fixture="execution")
def indexeur_verifie(base_vide: Connexion, caplog: pytest.LogCaptureFixture) -> Execution:
	utilisateur = base_vide.execute("SELECT current_user").fetchone()
	assert utilisateur is not None
	autoriser_utilisateur(base_vide, str(utilisateur[0]), [Role.INDEXATION])
	caplog.clear()
	with caplog.at_level(logging.INFO, logger="machincast"), connecter(*parametres_base_test(), Role.INDEXATION) as c:
		bilan = verifier_sonores(c)
	# Les anomalies et les erreurs vont sur la sortie d'erreur : niveau WARNING et au-delà.
	anomalies = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
	return Execution(bilan, "\n".join(anomalies))


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


# ─── Exécutable ────────────────────────────────────────────


@when(
	parsers.parse('je lance "{executable}" avec une configuration dont la socket PostgreSQL n\'existe pas'),
	target_fixture="commande",
)
def lancer_sans_base(tmp_path: Path, executable: str) -> subprocess.CompletedProcess[str]:
	configuration = tmp_path / "sans-base.toml"
	texte = CONFIGURATION_TEST.read_text(encoding="utf-8")
	configuration.write_text(
		texte.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'), encoding="utf-8"
	)
	chemin = shutil.which(executable)
	assert chemin is not None, f'{executable} n\'est pas installé : lancer pip install -e ".[dev]"'
	return subprocess.run([chemin, "--config", str(configuration)], capture_output=True, text=True, timeout=60)


@then(parsers.parse("la commande se termine avec le code {code:d}"))
def code_de_sortie(commande: subprocess.CompletedProcess[str], code: int) -> None:
	assert commande.returncode == code, commande.stderr


@then(parsers.parse("la sortie d'erreur de la commande mentionne « {texte} »"))
def erreur_commande(commande: subprocess.CompletedProcess[str], texte: str) -> None:
	assert texte in commande.stderr, commande.stderr


@pytest.fixture(autouse=True)
def gstreamer() -> None:
	Gst.init(None)
