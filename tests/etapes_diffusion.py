"""Étapes partagées des scénarios de la diffusion (https://github.com/dascritch/machincast/issues/88).

Chargé comme greffon pytest par tests/conftest.py : la boucle de diffusion
(https://github.com/dascritch/machincast/issues/88) et les streams (https://github.com/dascritch/machincast/issues/16)
s'en servent. Le banc tient l'horloge, le moteur sur la sortie factice et la diffusion, connectée avec le rôle de
la lecture.
"""

import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, then, when

from machincast.base import Role, connecter
from machincast.hasard import creer_hasard
from machincast.horloge import HorlogeFixe
from machincast.lecture.diffusion import Diffusion
from machincast.lecture.moteur import MoteurAudio
from tests.base_test import configuration_test, parametres_base_test
from tests.sons import copie_de_test

Connexion = psycopg.Connection[tuple[object, ...]]
PAS_REEL = 0.05
DELAI_RECONNEXION_TEST = timedelta(seconds=0.2)
"""Délai entre deux tentatives de reconnexion d'un stream, raccourci pour les scénarios."""


@dataclass
class Banc:
	horloge: HorlogeFixe | None = None
	diffusion: Diffusion | None = None
	moteur: MoteurAudio | None = None
	connexion: Connexion | None = None
	fichiers: dict[str, Path] = field(default_factory=dict)


@pytest.fixture
def banc() -> Iterator[Banc]:
	banc = Banc()
	yield banc
	if banc.moteur is not None:
		banc.moteur.fermer()
	if banc.connexion is not None:
		banc.connexion.close()


def secondes(texte: str) -> float:
	return float(texte.replace(",", "."))


def heure(texte: str) -> datetime:
	return datetime.fromisoformat(texte).astimezone()


def horloge(banc: Banc) -> HorlogeFixe:
	assert banc.horloge is not None
	return banc.horloge


def diffusion(banc: Banc) -> Diffusion:
	assert banc.diffusion is not None
	return banc.diffusion


def sonore(base: Connexion, nom: str) -> int:
	ligne = base.execute("SELECT id FROM sonores WHERE titre = %s", (nom,)).fetchone()
	assert ligne is not None, f"sonore {nom} inconnu"
	return int(str(ligne[0]))


def creer_sonore(banc: Banc, base: Connexion, repertoire: Path, nom: str) -> int:
	dossier = repertoire / nom
	dossier.mkdir()
	fichier = copie_de_test("flac", dossier)
	banc.fichiers[nom] = fichier
	etat = fichier.stat()
	ligne = base.execute(
		"INSERT INTO sonores (type, emplacement, etat, titre, duree, fichier_modifie_le, fichier_taille)"
		" VALUES ('fichier', %s, 'actif', %s, '1 s', %s, %s) RETURNING id",
		(str(fichier), nom, datetime.fromtimestamp(etat.st_mtime, tz=UTC), etat.st_size),
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


def evenement(
	banc: Banc,
	base: Connexion,
	repertoire: Path,
	nom: str,
	priorite: str,
	debut: datetime | None,
	fin: datetime | None,
	sonores: list[str],
) -> None:
	cree = base.execute(
		"INSERT INTO evenements (nom_interne, priorite, debut, fin) VALUES (%s, %s, %s, %s) RETURNING id",
		(nom, priorite, debut, fin),
	).fetchone()
	assert cree is not None
	for position, nom_sonore in enumerate(sonores, start=1):
		existant = base.execute("SELECT id FROM sonores WHERE titre = %s", (nom_sonore,)).fetchone()
		identifiant = int(str(existant[0])) if existant else creer_sonore(banc, base, repertoire, nom_sonore)
		base.execute(
			"INSERT INTO evenements_elements (evenement_id, position, sonore_id) VALUES (%s, %s, %s)",
			(cree[0], position, identifiant),
		)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'horloge du binaire au « {instant} »"))
def horloge_au(banc: Banc, instant: str) -> None:
	banc.horloge = HorlogeFixe(heure(instant))


@given(parsers.re(r"le fil musical permanent « (?P<nom>[^»]+) », avec les sonores (?P<liste>.+)"))
def fil(banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, liste: str) -> None:
	noms = [n.strip(" «»") for n in liste.split(",")]
	evenement(banc, base_vide, tmp_path, nom, "fil_musical", None, None, noms)


@given(
	parsers.re(
		r"le fil musical permanent « (?P<nom>[^»]+) », avec la banque séquentielle « (?P<banque>[^»]+) »"
		r" des sonores (?P<liste>.+)"
	)
)
def fil_avec_banque(banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, banque: str, liste: str) -> None:
	creee = base_vide.execute(
		"INSERT INTO banques (nom_interne, mode) VALUES (%s, 'sequentiel') RETURNING id", (banque,)
	).fetchone()
	assert creee is not None
	for position, nom_sonore in enumerate((n.strip(" «»") for n in liste.split(",")), start=1):
		base_vide.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
			(creee[0], creer_sonore(banc, base_vide, tmp_path, nom_sonore), position),
		)
	evenement_cree = base_vide.execute(
		"INSERT INTO evenements (nom_interne, priorite) VALUES (%s, 'fil_musical') RETURNING id", (nom,)
	).fetchone()
	assert evenement_cree is not None
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, banque_id) VALUES (%s, 1, %s)",
		(evenement_cree[0], creee[0]),
	)


@given(
	parsers.re(
		r"(?P<genre>l'émission|le spécial) « (?P<nom>[^»]+) » de (?P<debut>[\d:]+) à (?P<fin>[\d:]+),"
		r" avec le sonore « (?P<nom_sonore>[^»]+) »"
	)
)
def emission(
	banc: Banc, base_vide: Connexion, tmp_path: Path, genre: str, nom: str, debut: str, fin: str, nom_sonore: str
) -> None:
	evenement(
		banc,
		base_vide,
		tmp_path,
		nom,
		"emission" if genre == "l'émission" else "special",
		heure(f"2026-10-14 {debut}"),
		heure(f"2026-10-14 {fin}"),
		[nom_sonore],
	)


@given(parsers.parse("chaque sonore a {duree} seconde de crossfade de début et de fin"))
def crossfades(base_vide: Connexion, duree: str) -> None:
	valeur = timedelta(seconds=secondes(duree))
	base_vide.execute("UPDATE sonores SET crossfade_debut = %s, crossfade_fin = %s", (valeur, valeur))


@given(parsers.parse("chaque sonore a {duree} seconde de crossfade de fin, et aucun de début"))
def crossfade_de_fin(base_vide: Connexion, duree: str) -> None:
	base_vide.execute("UPDATE sonores SET crossfade_fin = %s", (timedelta(seconds=secondes(duree)),))


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"la diffusion démarre (?P<rythme>au plus vite|en temps réel)"))
def demarrer(banc: Banc, base_vide: Connexion, rythme: str) -> None:
	banc.connexion = connecter(*parametres_base_test(), Role.LECTURE)
	banc.moteur = MoteurAudio(configuration_test().audio, temps_reel=rythme == "en temps réel")
	banc.diffusion = Diffusion(
		banc.connexion, banc.moteur, horloge(banc), creer_hasard(0), delai_reconnexion=DELAI_RECONNEXION_TEST
	)
	banc.diffusion.demarrer()


@when(parsers.re(r"la diffusion tourne (?P<nombre>\d+) pas d(?:'une|e (?P<duree>[\d,]+)) seconde"))
def tourner(banc: Banc, nombre: str, duree: str | None) -> None:
	ecart = 1.0 if duree is None else secondes(duree)
	rythme_reel = banc.moteur is not None and banc.moteur.temps_reel
	for _ in range(int(nombre)):
		diffusion(banc).pas()
		# En temps réel, la pause suit l'horloge ; au plus vite, la voie finit pendant une courte pause réelle.
		if rythme_reel:
			time.sleep(ecart)
		else:
			attendre_la_fin_des_voies(banc)
		horloge(banc).avancer(timedelta(seconds=ecart))


def attendre_la_fin_des_voies(banc: Banc, delai: float = 5.0) -> None:
	assert banc.moteur is not None
	limite = time.monotonic() + delai
	while any(v.etat == "en cours" for v in banc.moteur.voies_en_cours()) and time.monotonic() < limite:
		time.sleep(PAS_REEL / 5)
		for voie in banc.moteur.voies_en_cours():
			voie.traiter()


@when(parsers.parse("la diffusion tourne pendant {duree} seconde en temps réel"))
def tourner_en_temps_reel(banc: Banc, duree: str) -> None:
	fin = time.monotonic() + secondes(duree)
	precedent = time.monotonic()
	while time.monotonic() < fin:
		diffusion(banc).pas()
		time.sleep(PAS_REEL)
		maintenant = time.monotonic()
		horloge(banc).avancer(timedelta(seconds=maintenant - precedent))
		precedent = maintenant


@when(parsers.parse("l'horloge du binaire passe au « {instant} »"))
def horloge_passe(banc: Banc, instant: str) -> None:
	horloge(banc).avancer(heure(instant) - horloge(banc).maintenant())


@when(parsers.parse("le sonore « {nom} » redevient actif"))
def redevient_actif(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = 'actif' WHERE id = %s", (sonore(base_vide, nom),))


@when("la diffusion s'arrête")
def arreter(banc: Banc) -> None:
	diffusion(banc).arreter()


# ─── Alors ─────────────────────────────────────────────────


def passages(base: Connexion) -> list[tuple[str, datetime, datetime | None, bool | None]]:
	lignes = base.execute(
		"SELECT d.titre, d.horodatage, f.horodatage, f.sans_incident FROM airplay d"
		" LEFT JOIN airplay f ON f.passage_id = d.passage_id AND f.type_ligne = 'fin'"
		" WHERE d.type_ligne = 'debut' ORDER BY d.horodatage, d.id"
	).fetchall()
	return [(str(t), d, f, s) for t, d, f, s in lignes]  # type: ignore[misc]


def passage(base: Connexion, nom: str) -> tuple[str, datetime, datetime | None, bool | None]:
	return next(p for p in passages(base) if p[0] == nom)


def log(base: Connexion) -> list[tuple[str, str]]:
	return [(str(n), str(t)) for n, t in base.execute("SELECT niveau::text, nature FROM log ORDER BY id").fetchall()]


@then(parsers.re(r"l'airplay montre les passages (?P<liste>.+)"))
def airplay(base_vide: Connexion, liste: str) -> None:
	assert [p[0] for p in passages(base_vide)] == [n.strip(" «»") for n in liste.split(",")], passages(base_vide)


@then("chaque passage a sa ligne de fin, sans incident")
def lignes_de_fin(base_vide: Connexion) -> None:
	lignes = passages(base_vide)
	assert lignes and all(fin is not None and sans_incident for _, _, fin, sans_incident in lignes), lignes


@then(parsers.parse("le log commence par « {niveau} » « {nature} » et finit par « {niveau_fin} » « {nature_fin} »"))
def bornes_du_log(base_vide: Connexion, niveau: str, nature: str, niveau_fin: str, nature_fin: str) -> None:
	lignes = log(base_vide)
	assert lignes[0] == (niveau, nature) and lignes[-1] == (niveau_fin, nature_fin), lignes


@then(parsers.parse("le log finit par « {niveau} » « {nature} »"))
def fin_du_log(base_vide: Connexion, niveau: str, nature: str) -> None:
	assert log(base_vide)[-1] == (niveau, nature)


@then(parsers.re(r"le log contient (?P<nombre>\d+) (?P<niveau>info|alerte|incident) « (?P<nature>[^»]+) »"))
def lignes_du_log(base_vide: Connexion, nombre: str, niveau: str, nature: str) -> None:
	assert log(base_vide).count((niveau, nature)) == int(nombre), log(base_vide)


@then(parsers.parse("le passage « {nom} » a été coupé net au « {instant} »"))
def coupe_net(base_vide: Connexion, nom: str, instant: str) -> None:
	assert passage(base_vide, nom)[2] == heure(instant)


@then(
	parsers.re(
		r"le passage « (?P<suivant>[^»]+) » a commencé (?P<quand>avant|après) la fin du passage « (?P<nom>[^»]+) »"
	)
)
def chevauchement(base_vide: Connexion, suivant: str, quand: str, nom: str) -> None:
	fin = passage(base_vide, nom)[2]
	debut = passage(base_vide, suivant)[1]
	assert fin is not None
	assert (debut < fin) if quand == "avant" else (debut >= fin), (debut, fin)


@given(parsers.re(r"le sonore « (?P<nom>[^»]+) » a (?P<duree>[\d,]+) seconde de crossfade de (?P<cote>début|fin)"))
def crossfade_du_sonore(base_vide: Connexion, nom: str, duree: str, cote: str) -> None:
	colonne = "crossfade_debut" if cote == "début" else "crossfade_fin"
	base_vide.execute(
		f"UPDATE sonores SET {colonne} = %s WHERE id = %s",
		(timedelta(seconds=secondes(duree)), sonore(base_vide, nom)),
	)


@given(parsers.re(r"l'événement de secours « (?P<nom>[^»]+) », avec les sonores (?P<liste>.+)"))
def evenement_de_secours(banc: Banc, base_vide: Connexion, tmp_path: Path, nom: str, liste: str) -> None:
	evenement(banc, base_vide, tmp_path, nom, "secours", None, None, [n.strip(" «»") for n in liste.split(",")])


@given(parsers.parse("le fil musical « {nom} » est supprimé"))
def fil_supprime(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("DELETE FROM evenements WHERE nom_interne = %s", (nom,))


def sonores_de(base: Connexion, evenement: str) -> set[str]:
	lignes = base.execute(
		"SELECT s.titre FROM evenements e JOIN evenements_elements ee ON ee.evenement_id = e.id"
		" JOIN sonores s ON s.id = ee.sonore_id WHERE e.nom_interne = %s",
		(evenement,),
	).fetchall()
	return {str(ligne[0]) for ligne in lignes}


@then("l'airplay ne montre aucun passage")
def aucun_passage(base_vide: Connexion) -> None:
	assert passages(base_vide) == []
