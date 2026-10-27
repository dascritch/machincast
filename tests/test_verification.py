"""Étapes des scénarios de vérification des fichiers (https://github.com/dascritch/machincast/issues/7)."""

import os
import resource
import shutil
import subprocess
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import gi
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.indexation import decodage
from machincast.indexation.decodage import DecodeurIndisponible, EtatFichier, Verification, verifier_fichier
from tests.base_test import chemin_configuration_test
from tests.etapes_indexation import DECIMAL, nombre
from tests.sons import copie_de_test, corrompre, tronquer

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("verification.feature")

# ─── Fichiers ──────────────────────────────────────────────


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
def fichier_bloque(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
	"""Tube nommé : un écrivain y verse la première moitié d'un WAV, puis le garde ouvert, sans rien y écrire, jusqu'à
	ce que la vérification abandonne le décodage. Fermé après un délai fixe, la fin du fichier pourrait arriver avant
	que le blocage ne soit constaté, sur un poste chargé (https://github.com/dascritch/machincast/issues/280). Le
	décodage abandonné arrête son pipeline, dont la lecture du tube attend : le tube se ferme juste avant."""
	donnees = copie_de_test("wav", tmp_path).read_bytes()
	debut = donnees[: len(donnees) // 2]
	tube = tmp_path / "bloque.wav"
	os.mkfifo(tube)
	abandonne = threading.Event()
	vraie_liberation = decodage._Decodage.liberer

	def liberer(decodage_en_cours: decodage._Decodage) -> None:
		abandonne.set()
		ecrivain.join(timeout=10)
		vraie_liberation(decodage_en_cours)

	monkeypatch.setattr(decodage._Decodage, "liberer", liberer)

	def alimenter() -> None:
		with tube.open("wb") as tube_ouvert:  # attend que le décodeur ouvre le tube
			tube_ouvert.write(debut)
			tube_ouvert.flush()
			abandonne.wait(timeout=60)

	ecrivain = threading.Thread(target=alimenter, daemon=True)
	ecrivain.start()
	yield tube
	abandonne.set()
	ecrivain.join(timeout=10)


@dataclass
class Tentatives:
	nombre: int = 0


@given(
	parsers.re(r"un décodage qui ne démarre (?:pas aux (?P<echecs>\d+) premières tentatives|jamais)"),
	target_fixture="tentatives",
)
def demarrage_bloque(monkeypatch: pytest.MonkeyPatch, echecs: str | None) -> Tentatives:
	"""Simule un démarrage bloqué : un disque réseau en veille, ou le blocage de decodebin qui a fait écarter l'AIFF
	(https://github.com/dascritch/machincast/issues/280, https://github.com/dascritch/machincast/issues/284)."""
	tentatives = Tentatives()
	vraie_tentative = decodage._tentative

	def tentative(
		chemin: Path, delai_demarrage: timedelta, delai_sans_progression: timedelta, seuil_blancs: float | None = None
	) -> Verification | None:
		tentatives.nombre += 1
		if (echecs is None) or (tentatives.nombre <= int(echecs)):
			return None
		return vraie_tentative(chemin, delai_demarrage, delai_sans_progression)

	monkeypatch.setattr(decodage, "_tentative", tentative)
	return tentatives


@then(parsers.parse("le décodage a été tenté {nombre:d} fois"))
def tente(tentatives: Tentatives, nombre: int) -> None:
	assert tentatives.nombre == nombre


@given("le décodeur GStreamer du Vorbis désactivé")
def vorbis_desactive() -> Iterator[None]:
	"""Simule un paquet absent : decodebin ignore les éléments de rang NONE.

	Plusieurs paquets savent décoder le Vorbis (vorbisdec de plugins-base, avdec_vorbis de libav) : tous sont écartés.
	"""
	Gst.init(None)
	vorbis = Gst.Caps.from_string("audio/x-vorbis")
	assert vorbis is not None
	fabriques = [
		fabrique
		for fabrique in Gst.ElementFactory.list_get_elements(Gst.ELEMENT_FACTORY_TYPE_DECODER, Gst.Rank.MARGINAL)
		if fabrique.can_sink_any_caps(vorbis)
	]
	assert fabriques, "aucun décodeur Vorbis : installer gstreamer1.0-plugins-base"
	rangs = [(fabrique, fabrique.get_rank()) for fabrique in fabriques]
	for fabrique in fabriques:
		fabrique.set_rank(Gst.Rank.NONE)
	yield
	for fabrique, rang in rangs:
		fabrique.set_rank(rang)


def descripteurs_ouverts() -> int:
	return len(os.listdir("/proc/self/fd"))


@dataclass
class Limite:
	"""Descripteurs ouverts avant les vérifications."""

	ouverts: int = 0


@pytest.fixture
def limite() -> Iterator[Limite]:
	"""La limite de descripteurs du processus, rétablie en fin de scénario."""
	souple, dure = resource.getrlimit(resource.RLIMIT_NOFILE)
	yield Limite()
	resource.setrlimit(resource.RLIMIT_NOFILE, (souple, dure))


@given(parsers.parse("un processus limité à {marge:d} descripteurs de fichier de plus que ceux déjà ouverts"))
def limiter(limite: Limite, fichier: Path, marge: int) -> None:
	# Un premier décodage ouvre ce que GStreamer garde pour toute la durée du processus (registre, horloge).
	assert verifier_fichier(fichier).etat == EtatFichier.SAIN
	limite.ouverts = descripteurs_ouverts()
	_souple, dure = resource.getrlimit(resource.RLIMIT_NOFILE)
	resource.setrlimit(resource.RLIMIT_NOFILE, (limite.ouverts + marge, dure))


@when(parsers.parse("je vérifie ce fichier {fois:d} fois de suite"), target_fixture="resultats")
def verifier_plusieurs_fois(fichier: Path, fois: int) -> list[Verification]:
	return [verifier_fichier(fichier) for _ in range(fois)]


@then("le fichier est sain à chaque vérification")
def toujours_sain(resultats: list[Verification]) -> None:
	assert [resultat.probleme for resultat in resultats if resultat.etat != EtatFichier.SAIN] == []


@then("autant de descripteurs de fichier sont ouverts qu'avant les vérifications")
def sans_fuite(limite: Limite) -> None:
	assert descripteurs_ouverts() == limite.ouverts


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
	assert (resultat.probleme is not None) and (resultat.probleme.startswith(verdict))


@then(parsers.parse("le problème signalé mentionne « {texte} »"))
def probleme_mentionne(resultat: Verification, texte: str) -> None:
	assert (resultat.probleme is not None) and (texte in resultat.probleme), resultat.probleme


@then("la vérification s'arrête en signalant un décodeur absent et le paquet à installer")
def decodeur_absent(resultat: Verification | DecodeurIndisponible) -> None:
	assert isinstance(resultat, DecodeurIndisponible), resultat
	assert "gstreamer1.0-plugins-bad" in str(resultat)


# ─── Exécutable ────────────────────────────────────────────


@when(
	parsers.parse('je lance "{executable}" avec une configuration dont la socket PostgreSQL n\'existe pas'),
	target_fixture="commande",
)
def lancer_sans_base(tmp_path: Path, executable: str) -> subprocess.CompletedProcess[str]:
	configuration = tmp_path / "sans-base.toml"
	texte = chemin_configuration_test().read_text(encoding="utf-8")
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
