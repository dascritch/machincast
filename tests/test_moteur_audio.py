"""Étapes du moteur audio GStreamer (https://github.com/dascritch/machincast/issues/15)."""

import os
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.lecture.fichiers import verifier_avant_lecture
from machincast.lecture.moteur import MoteurAudio, Voie, enchainement
from tests.base_test import configuration_test, parametres_base_test
from tests.sons import FICHIERS_SONORES, copie_de_test

scenarios("moteur_audio.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
ATTENTE_MAXIMALE = 10.0


@dataclass
class Contexte:
	moteur: MoteurAudio | None = None
	voies: dict[str, Voie] = field(default_factory=dict)
	voie: Voie | None = None
	sonore: int | None = None
	fichier: Path | None = None
	resultat: Path | None = None


@pytest.fixture
def contexte() -> Iterator[Contexte]:
	contexte = Contexte()
	yield contexte
	if contexte.moteur is not None:
		contexte.moteur.fermer()


def secondes(texte: str) -> timedelta:
	return timedelta(seconds=float(texte.replace(",", ".")))


def moteur(contexte: Contexte) -> MoteurAudio:
	assert contexte.moteur is not None
	return contexte.moteur


# ─── Enveloppe et enchaînement ─────────────────────────────


@given(
	parsers.parse(
		"une voie pour un sonore de {duree} secondes, avec {debut} secondes de crossfade de début et {fin} de fin"
	)
)
def voie_preparee(contexte: Contexte, duree: str, debut: str, fin: str) -> None:
	contexte.voie = Voie(
		FICHIERS_SONORES / "sain.flac",
		configuration_test().audio,
		secondes(duree),
		secondes(debut),
		secondes(fin),
		temps_reel=False,
	)


@then(parsers.parse("à {instant} secondes, son volume est de {volume}"))
def volume(contexte: Contexte, instant: str, volume: str) -> None:
	assert contexte.voie is not None
	assert contexte.voie.volume_a(secondes(instant)) == pytest.approx(float(volume.replace(",", ".")))


@then(
	parsers.parse(
		"un sonore de {duree} secondes, avec {fin} secondes de crossfade de fin,"
		" laisse démarrer le suivant après {apres} secondes"
	)
)
def point_d_enchainement(duree: str, fin: str, apres: str) -> None:
	assert enchainement(secondes(duree), secondes(fin)) == secondes(apres)


# ─── Lecture ───────────────────────────────────────────────


@given(parsers.re(r"un moteur audio sur la sortie de la configuration de test, (?P<rythme>au plus vite|en temps réel)"))
def moteur_de_test(contexte: Contexte, rythme: str) -> None:
	contexte.moteur = MoteurAudio(configuration_test().audio, temps_reel=rythme == "en temps réel")


@when(parsers.parse("il joue le fichier de test « {nom} »"))
def jouer(contexte: Contexte, nom: str) -> None:
	contexte.voies[nom] = moteur(contexte).jouer(FICHIERS_SONORES / nom, timedelta(seconds=1))


@when("il joue un fichier qui contient du texte")
def jouer_texte(contexte: Contexte, tmp_path: Path) -> None:
	faux = tmp_path / "faux.mp3"
	faux.write_text("ceci n'est pas du son", encoding="utf-8")
	contexte.voies["texte"] = moteur(contexte).jouer(faux, timedelta(seconds=1))


@when("j'attends la fin de ses voies")
def attendre(contexte: Contexte) -> None:
	limite = time.monotonic() + ATTENTE_MAXIMALE
	while moteur(contexte).voies_en_cours() and time.monotonic() < limite:
		moteur(contexte).traiter_messages()
		time.sleep(0.01)
	assert not moteur(contexte).voies_en_cours(), "voies toujours en cours"


@when(parsers.parse("{millisecondes:d} millisecondes passent"))
def patienter(contexte: Contexte, millisecondes: int) -> None:
	time.sleep(millisecondes / 1000)
	moteur(contexte).traiter_messages()


@when("il coupe net")
def couper(contexte: Contexte) -> None:
	moteur(contexte).couper()


@then(parsers.parse("la voie de « {nom} » est finie"))
def finie(contexte: Contexte, nom: str) -> None:
	voie = contexte.voies[nom]
	assert voie.etat == "finie", f"{voie.etat} : {voie.erreur}"


@then(parsers.parse("elle a joué sur l'élément GStreamer « {fabrique} »"))
def element_de_sortie(contexte: Contexte, fabrique: str) -> None:
	voie = next(iter(contexte.voies.values()))
	assert voie.fabrique_de_sortie == fabrique


@then(parsers.parse("{nombre:d} voies sont en cours"))
def en_cours(contexte: Contexte, nombre: int) -> None:
	assert len(moteur(contexte).voies_en_cours()) == nombre


@then("aucune voie n'est en cours")
def aucune(contexte: Contexte) -> None:
	assert moteur(contexte).voies_en_cours() == []


@then(parsers.parse("la voie de « {nom} » est coupée avant {millisecondes:d} millisecondes"))
def coupee(contexte: Contexte, nom: str, millisecondes: int) -> None:
	voie = contexte.voies[nom]
	assert voie.etat == "coupée", voie.etat
	assert voie.position_finale is not None and voie.position_finale < timedelta(milliseconds=millisecondes)


@then("la voie du fichier texte est en erreur, avec le motif de GStreamer")
def en_erreur(contexte: Contexte) -> None:
	voie = contexte.voies["texte"]
	assert voie.etat == "en erreur"
	assert voie.erreur


# ─── Vérification avant lecture ────────────────────────────


@given(parsers.parse("un sonore indexé pour le fichier de test « {nom} »"))
def sonore_indexe(contexte: Contexte, base_vide: Connexion, tmp_path: Path, nom: str) -> None:
	fichier = copie_de_test(nom.split(".")[-1], tmp_path)
	etat = fichier.stat()
	ligne = base_vide.execute(
		"INSERT INTO sonores (type, emplacement, etat, fichier_modifie_le, fichier_taille)"
		" VALUES ('fichier', %s, 'actif', %s, %s) RETURNING id",
		(str(fichier), datetime.fromtimestamp(etat.st_mtime, tz=UTC), etat.st_size),
	).fetchone()
	assert ligne is not None
	contexte.sonore, contexte.fichier = int(str(ligne[0])), fichier


@given("la date de modification du fichier a changé")
def date_changee(contexte: Contexte) -> None:
	assert contexte.fichier is not None
	etat = contexte.fichier.stat()
	os.utime(contexte.fichier, (etat.st_atime, etat.st_mtime + 60))


@given("la taille du fichier a changé")
def taille_changee(contexte: Contexte) -> None:
	assert contexte.fichier is not None
	etat = contexte.fichier.stat()
	with contexte.fichier.open("ab") as fichier:
		fichier.write(b"\0" * 16)
	os.utime(contexte.fichier, (etat.st_atime, etat.st_mtime))


@given("le fichier a été supprimé")
def supprime(contexte: Contexte) -> None:
	assert contexte.fichier is not None
	contexte.fichier.unlink()


@when("le binaire lecture vérifie ce fichier avant de le jouer")
def verifier(contexte: Contexte, base_vide: Connexion) -> None:
	assert contexte.sonore is not None
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		contexte.resultat = verifier_avant_lecture(connexion, contexte.sonore)


@then("le fichier est prêt à être joué")
def pret(contexte: Contexte) -> None:
	assert contexte.resultat == contexte.fichier


@then("le fichier n'est pas joué")
def pas_joue(contexte: Contexte) -> None:
	assert contexte.resultat is None


def log(base: Connexion) -> list[tuple[object, ...]]:
	return base.execute("SELECT niveau::text, nature, message, sonore_id FROM log ORDER BY id").fetchall()


@then("le log ne contient rien")
def log_vide(base_vide: Connexion) -> None:
	assert log(base_vide) == []


@then(parsers.parse("le log contient une alerte « {nature} » pour ce sonore, qui mentionne « {mention} »"))
def alerte(contexte: Contexte, base_vide: Connexion, nature: str, mention: str) -> None:
	lignes = log(base_vide)
	assert len(lignes) == 1, lignes
	niveau, trouvee, message, sonore = lignes[0]
	assert (niveau, trouvee, sonore) == ("alerte", nature, contexte.sonore)
	assert mention in str(message), message


@then(parsers.parse("le log contient un incident « {nature} » pour ce sonore"))
def incident(contexte: Contexte, base_vide: Connexion, nature: str) -> None:
	lignes = log(base_vide)
	assert [(n, t, s) for n, t, _, s in lignes] == [("incident", nature, contexte.sonore)], lignes
