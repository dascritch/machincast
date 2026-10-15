"""Étapes des scénarios du socle de test (https://github.com/dascritch/machincast/issues/5)."""

import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from _pytest.capture import CaptureResult
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.audio import Greffon, SortieAudioIndisponible, creer_sortie, jouer_son_de_test
from machincast.configuration import ConfigurationInvalide, SortieAudio, charger
from machincast.hasard import creer_hasard
from machincast.horloge import HorlogeFixe, HorlogeSysteme
from machincast.journal import configurer as configurer_journal
from tests.base_test import CONFIGURATION_TEST, configuration_test, purger_base

RACINE = Path(__file__).resolve().parents[1]

scenarios("socle.feature")


@dataclass
class Contexte:
	connexion: psycopg.Connection[tuple[object, ...]] | None = None
	chemin: Path | None = None
	erreur: Exception | None = None
	horloge: HorlogeFixe | None = None
	hasards: list[random.Random] = field(default_factory=list)
	element: object = None
	capture: "CaptureResult[str] | None" = None


@pytest.fixture
def contexte() -> Contexte:
	return Contexte()


# ─── Configuration et base de test ─────────────────────────


@then(parsers.parse('la configuration de test désigne la base "{nom}"'))
def base_designee(nom: str) -> None:
	assert configuration_test().base.test == nom


@then(parsers.parse('la sortie audio des tests est "{sortie}"'))
def sortie_des_tests(sortie: str) -> None:
	assert configuration_test().audio.sortie == sortie


@then("la base de production de la configuration de test n'est pas celle du modèle de configuration")
def production_hors_tests() -> None:
	# Un binaire lancé avec la configuration de test ne doit pas pouvoir atteindre la vraie base de production
	# (https://github.com/dascritch/machincast/issues/7).
	modele = charger(RACINE / "machincast.exemple.toml")
	assert configuration_test().base.production != modele.base.production


@given("une configuration de test dont la base de test porte le nom de la base de production")
def configuration_dangereuse(contexte: Contexte, tmp_path: Path) -> None:
	base = configuration_test().base
	texte = CONFIGURATION_TEST.read_text(encoding="utf-8").replace(
		f'test = "{base.test}"', f'test = "{base.production}"'
	)
	contexte.chemin = tmp_path / "configuration-dangereuse.toml"
	contexte.chemin.write_text(texte, encoding="utf-8")


@when("je charge cette configuration")
def charger_configuration(contexte: Contexte) -> None:
	try:
		charger(contexte.chemin)
	except ConfigurationInvalide as erreur:
		contexte.erreur = erreur


@then(parsers.parse('le chargement échoue avec un message qui mentionne "{texte}"'))
def echec(contexte: Contexte, texte: str) -> None:
	assert contexte.erreur is not None, "le chargement aurait dû échouer"
	assert texte in str(contexte.erreur)


@given("une base de test vide")
def base(contexte: Contexte, base_vide: psycopg.Connection[tuple[object, ...]]) -> None:
	contexte.connexion = base_vide


def enregistrer_banque(contexte: Contexte, nom: str) -> int:
	assert contexte.connexion is not None
	ligne = contexte.connexion.execute(
		"INSERT INTO banques (nom_interne, mode) VALUES (%s, 'aleatoire') RETURNING id", (nom,)
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


@when("j'enregistre deux banques")
def deux_banques(contexte: Contexte) -> None:
	enregistrer_banque(contexte, "Jingles")
	enregistrer_banque(contexte, "Habillages")


@when("la base de test est purgée")
def purger(contexte: Contexte) -> None:
	assert contexte.connexion is not None
	purger_base(contexte.connexion)


@then("la base ne contient plus aucune banque")
def plus_de_banque(contexte: Contexte) -> None:
	assert contexte.connexion is not None
	assert contexte.connexion.execute("SELECT count(*) FROM banques").fetchone() == (0,)


@then(parsers.parse("la prochaine banque enregistrée reçoit l'identifiant {identifiant:d}"))
def identifiant_remis(contexte: Contexte, identifiant: int) -> None:
	assert enregistrer_banque(contexte, "Nouvelle") == identifiant


# ─── Horloge ───────────────────────────────────────────────


@given(parsers.parse('une horloge fixée au "{instant}"'))
def horloge_fixe(contexte: Contexte, instant: str) -> None:
	contexte.horloge = HorlogeFixe(datetime.fromisoformat(instant))


@when(parsers.parse("l'horloge avance de {secondes:d} secondes"))
def avancer(contexte: Contexte, secondes: int) -> None:
	assert contexte.horloge is not None
	contexte.horloge.avancer(timedelta(seconds=secondes))


@then(parsers.parse('l\'horloge indique "{instant}"'))
def indique(contexte: Contexte, instant: str) -> None:
	assert contexte.horloge is not None
	assert contexte.horloge.maintenant() == datetime.fromisoformat(instant)


@then(parsers.parse('une horloge fixée au "{instant}" est refusée'))
def sans_fuseau(instant: str) -> None:
	with pytest.raises(ValueError, match="fuseau"):
		HorlogeFixe(datetime.fromisoformat(instant))


@then("l'horloge système donne une heure avec fuseau, proche de l'heure réelle")
def horloge_systeme() -> None:
	instant = HorlogeSysteme().maintenant()
	assert instant.tzinfo is not None
	assert abs(instant - datetime.now().astimezone()) < timedelta(seconds=5)


# ─── Hasard ────────────────────────────────────────────────


@given(parsers.parse("deux générateurs de hasard créés avec la graine {graine:d}"))
def deux_generateurs(contexte: Contexte, graine: int) -> None:
	contexte.hasards = [creer_hasard(graine), creer_hasard(graine)]


@given(parsers.parse("un générateur créé avec la graine {premiere:d} et un autre avec la graine {seconde:d}"))
def generateurs_differents(contexte: Contexte, premiere: int, seconde: int) -> None:
	contexte.hasards = [creer_hasard(premiere), creer_hasard(seconde)]


def tirages(hasard: random.Random, nombre: int, parmi: int) -> list[int]:
	return [hasard.choice(range(parmi)) for _ in range(nombre)]


@then(parsers.parse("ils tirent les mêmes {nombre:d} sonores parmi {parmi:d}"))
def memes_tirages(contexte: Contexte, nombre: int, parmi: int) -> None:
	premier, second = contexte.hasards
	assert tirages(premier, nombre, parmi) == tirages(second, nombre, parmi)


@then(parsers.parse("leurs {nombre:d} tirages parmi {parmi:d} diffèrent"))
def tirages_differents(contexte: Contexte, nombre: int, parmi: int) -> None:
	premier, second = contexte.hasards
	assert tirages(premier, nombre, parmi) != tirages(second, nombre, parmi)


# ─── Sortie audio ──────────────────────────────────────────


@when(parsers.parse('je crée la sortie audio "{sortie}" sur le périphérique "{peripherique}"'))
def creer_avec_peripherique(contexte: Contexte, sortie: str, peripherique: str) -> None:
	contexte.element = creer_sortie(sortie, peripherique)  # type: ignore[arg-type]


@when(parsers.parse('je crée la sortie audio "{sortie}" sans périphérique'))
def creer_sans_peripherique(contexte: Contexte, sortie: str) -> None:
	contexte.element = creer_sortie(sortie, None)  # type: ignore[arg-type]


@then(parsers.parse('l\'élément GStreamer est un "{fabrique}"'))
def element_cree(contexte: Contexte, fabrique: str) -> None:
	assert contexte.element.get_factory().get_name() == fabrique  # type: ignore[attr-defined]


@then(parsers.parse('son périphérique est "{peripherique}"'))
def peripherique_regle(contexte: Contexte, peripherique: str) -> None:
	element = contexte.element
	nom = "target-object" if element.get_factory().get_name() == "pipewiresink" else "device"  # type: ignore[attr-defined]
	assert element.get_property(nom) == peripherique  # type: ignore[attr-defined]


@when("je joue un son de test d'une demi-seconde sur la sortie factice", target_fixture="resultat")
def jouer() -> bool:
	return jouer_son_de_test(creer_sortie("factice", None), duree=timedelta(milliseconds=500))


@then("la lecture se termine sans erreur")
def lecture_terminee(resultat: bool) -> None:
	assert resultat is True


@when(parsers.parse("je crée une sortie dont le greffon GStreamer « {fabrique} » n'est pas installé"))
def greffon_manquant(contexte: Contexte, fabrique: str) -> None:
	greffons: dict[SortieAudio, Greffon] = {
		"factice": Greffon(fabrique=fabrique, propriete=None, paquet="gstreamer1.0-inexistant")
	}
	try:
		creer_sortie("factice", None, greffons)
	except SortieAudioIndisponible as erreur:
		contexte.erreur = erreur


@then("la création échoue en nommant le paquet à installer")
def paquet_nomme(contexte: Contexte) -> None:
	assert contexte.erreur is not None, "la création aurait dû échouer"
	assert "gstreamer1.0-inexistant" in str(contexte.erreur)


# ─── Garde-fous ────────────────────────────────────────────

SOURCES = RACINE / "src" / "machincast"
MODULES_DEDIES = {"horloge.py", "hasard.py"}
# Appels qui lisent l'heure réelle ou un hasard non injecté.
INTERDITS = re.compile(
	r"\b(datetime\.now|datetime\.today|datetime\.utcnow|date\.today|time\.time|time\.monotonic|random\.(?!Random\b)\w+)\s*\("
	r"|^\s*(from random import|import random)\b",
	re.MULTILINE,
)


@then("aucun fichier de src/ ne lit l'heure ni le hasard en dehors de machincast.horloge et machincast.hasard")
def garde_fou() -> None:
	fautes = [
		f"{chemin.relative_to(SOURCES)} : {m.group(0).strip()}"
		for chemin in sorted(SOURCES.rglob("*.py"))
		if chemin.name not in MODULES_DEDIES
		for m in INTERDITS.finditer(chemin.read_text(encoding="utf-8"))
	]
	assert not fautes, "utiliser machincast.horloge ou machincast.hasard :\n" + "\n".join(fautes)


# Les messages des exécutables passent par logging et machincast.journal, jamais par print
# (revue de https://github.com/dascritch/machincast/pull/65).
PRINT = re.compile(r"(?<![\w.])print\s*\(")


@then("aucun fichier de src/ n'appelle print")
def sans_print() -> None:
	fautes = [
		f"{chemin.relative_to(SOURCES)}:{numero}"
		for chemin in sorted(SOURCES.rglob("*.py"))
		for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), start=1)
		if PRINT.search(ligne.split("#", 1)[0])
	]
	assert not fautes, "utiliser logging (machincast.journal) au lieu de print :\n" + "\n".join(fautes)


@given(parsers.parse('les messages configurés pour l\'exécutable "{executable}"'))
def messages_configures(executable: str, capsys: pytest.CaptureFixture[str]) -> None:
	# capsys est demandé dès ici : sa capture doit commencer avant l'émission des messages.
	capsys.readouterr()
	configurer_journal(executable)


@when(parsers.parse("le code émet une information « {information} » et une anomalie « {anomalie} »"))
def emettre(information: str, anomalie: str) -> None:
	journal = logging.getLogger("machincast.essai")
	journal.info(information)
	journal.warning(anomalie)


@then(parsers.parse("la sortie standard contient seulement « {texte} »"))
def sortie_standard(capsys: pytest.CaptureFixture[str], contexte: Contexte, texte: str) -> None:
	capture = capsys.readouterr()
	contexte.capture = capture
	assert capture.out == texte + "\n"


@then(parsers.parse("la sortie d'erreur contient seulement « {texte} »"))
def sortie_erreur(contexte: Contexte, texte: str) -> None:
	assert contexte.capture is not None
	assert contexte.capture.err == texte + "\n"
