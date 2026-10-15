"""Étapes de la boucle de diffusion de Machin lecture (https://github.com/dascritch/machincast/issues/88)."""

import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.hasard import creer_hasard
from machincast.horloge import HorlogeFixe
from machincast.lecture.diffusion import Diffusion, installer_arret
from machincast.lecture.moteur import MoteurAudio
from tests.base_test import CONFIGURATION_TEST, configuration_test, parametres_base_test
from tests.sons import copie_de_test

scenarios("diffusion.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
PAS_REEL = 0.05


@dataclass
class Contexte:
	horloge: HorlogeFixe | None = None
	diffusion: Diffusion | None = None
	moteur: MoteurAudio | None = None
	connexion: Connexion | None = None
	arret: threading.Event | None = None
	resultat: subprocess.CompletedProcess[str] | None = None
	fichiers: dict[str, Path] = field(default_factory=dict)


@pytest.fixture
def contexte() -> Iterator[Contexte]:
	contexte = Contexte()
	yield contexte
	if contexte.moteur is not None:
		contexte.moteur.fermer()
	if contexte.connexion is not None:
		contexte.connexion.close()


def secondes(texte: str) -> float:
	return float(texte.replace(",", "."))


def heure(texte: str) -> datetime:
	return datetime.fromisoformat(texte).astimezone()


def horloge(contexte: Contexte) -> HorlogeFixe:
	assert contexte.horloge is not None
	return contexte.horloge


def diffusion(contexte: Contexte) -> Diffusion:
	assert contexte.diffusion is not None
	return contexte.diffusion


def sonore(base: Connexion, nom: str) -> int:
	ligne = base.execute("SELECT id FROM sonores WHERE titre = %s", (nom,)).fetchone()
	assert ligne is not None, f"sonore {nom} inconnu"
	return int(str(ligne[0]))


def creer_sonore(contexte: Contexte, base: Connexion, repertoire: Path, nom: str) -> int:
	dossier = repertoire / nom
	dossier.mkdir()
	fichier = copie_de_test("flac", dossier)
	contexte.fichiers[nom] = fichier
	etat = fichier.stat()
	ligne = base.execute(
		"INSERT INTO sonores (type, emplacement, etat, titre, duree, fichier_modifie_le, fichier_taille)"
		" VALUES ('fichier', %s, 'actif', %s, '1 s', %s, %s) RETURNING id",
		(str(fichier), nom, datetime.fromtimestamp(etat.st_mtime, tz=UTC), etat.st_size),
	).fetchone()
	assert ligne is not None
	return int(str(ligne[0]))


def evenement(
	contexte: Contexte,
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
		identifiant = int(str(existant[0])) if existant else creer_sonore(contexte, base, repertoire, nom_sonore)
		base.execute(
			"INSERT INTO evenements_elements (evenement_id, position, sonore_id) VALUES (%s, %s, %s)",
			(cree[0], position, identifiant),
		)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("l'horloge du binaire au « {instant} »"))
def horloge_au(contexte: Contexte, instant: str) -> None:
	contexte.horloge = HorlogeFixe(heure(instant))


@given(parsers.re(r"le fil musical permanent « (?P<nom>[^»]+) », avec les sonores (?P<liste>.+)"))
def fil(contexte: Contexte, base_vide: Connexion, tmp_path: Path, nom: str, liste: str) -> None:
	noms = [n.strip(" «»") for n in liste.split(",")]
	evenement(contexte, base_vide, tmp_path, nom, "fil_musical", None, None, noms)


@given(
	parsers.re(
		r"le fil musical permanent « (?P<nom>[^»]+) », avec la banque séquentielle « (?P<banque>[^»]+) »"
		r" des sonores (?P<liste>.+)"
	)
)
def fil_avec_banque(
	contexte: Contexte, base_vide: Connexion, tmp_path: Path, nom: str, banque: str, liste: str
) -> None:
	creee = base_vide.execute(
		"INSERT INTO banques (nom_interne, mode) VALUES (%s, 'sequentiel') RETURNING id", (banque,)
	).fetchone()
	assert creee is not None
	for position, nom_sonore in enumerate((n.strip(" «»") for n in liste.split(",")), start=1):
		base_vide.execute(
			"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, %s)",
			(creee[0], creer_sonore(contexte, base_vide, tmp_path, nom_sonore), position),
		)
	evenement_cree = base_vide.execute(
		"INSERT INTO evenements (nom_interne, priorite) VALUES (%s, 'fil_musical') RETURNING id", (nom,)
	).fetchone()
	assert evenement_cree is not None
	base_vide.execute(
		"INSERT INTO evenements_elements (evenement_id, position, banque_id) VALUES (%s, 1, %s)",
		(evenement_cree[0], creee[0]),
	)


@given(parsers.parse("l'émission « {nom} » de {debut} à {fin}, avec le sonore « {nom_sonore} »"))
def emission(
	contexte: Contexte, base_vide: Connexion, tmp_path: Path, nom: str, debut: str, fin: str, nom_sonore: str
) -> None:
	evenement(
		contexte,
		base_vide,
		tmp_path,
		nom,
		"emission",
		heure(f"2026-10-14 {debut}"),
		heure(f"2026-10-14 {fin}"),
		[nom_sonore],
	)


@given(parsers.parse("le fichier du sonore « {nom} » a été supprimé"))
def fichier_supprime(contexte: Contexte, nom: str) -> None:
	contexte.fichiers[nom].unlink()


@given(parsers.parse("le sonore « {nom} » est à l'état « {etat} »"))
def etat(base_vide: Connexion, nom: str, etat: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = %s WHERE id = %s", (etat, sonore(base_vide, nom)))


@given(parsers.parse("chaque sonore a {duree} seconde de crossfade de début et de fin"))
def crossfades(base_vide: Connexion, duree: str) -> None:
	valeur = timedelta(seconds=secondes(duree))
	base_vide.execute("UPDATE sonores SET crossfade_debut = %s, crossfade_fin = %s", (valeur, valeur))


@given(parsers.parse("chaque sonore a {duree} seconde de crossfade de fin, et aucun de début"))
def crossfade_de_fin(base_vide: Connexion, duree: str) -> None:
	base_vide.execute("UPDATE sonores SET crossfade_fin = %s", (timedelta(seconds=secondes(duree)),))


@given("l'arrêt de la diffusion branché sur les signaux")
def arret_branche(contexte: Contexte) -> Iterator[None]:
	anciens = {numero: signal.getsignal(numero) for numero in (signal.SIGTERM, signal.SIGINT)}
	contexte.arret = installer_arret()
	yield
	for numero, ancien in anciens.items():
		signal.signal(numero, ancien)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.re(r"la diffusion démarre (?P<rythme>au plus vite|en temps réel)"))
def demarrer(contexte: Contexte, base_vide: Connexion, rythme: str) -> None:
	contexte.connexion = connecter(*parametres_base_test(), Role.LECTURE)
	contexte.moteur = MoteurAudio(configuration_test().audio, temps_reel=rythme == "en temps réel")
	contexte.diffusion = Diffusion(contexte.connexion, contexte.moteur, horloge(contexte), creer_hasard(0))
	contexte.diffusion.demarrer()


@when(parsers.re(r"la diffusion tourne (?P<nombre>\d+) pas d(?:'une|e (?P<duree>[\d,]+)) seconde"))
def tourner(contexte: Contexte, nombre: str, duree: str | None) -> None:
	ecart = 1.0 if duree is None else secondes(duree)
	rythme_reel = contexte.moteur is not None and contexte.moteur.temps_reel
	for _ in range(int(nombre)):
		diffusion(contexte).pas()
		# En temps réel, la pause suit l'horloge ; au plus vite, la voie finit pendant une courte pause réelle.
		if rythme_reel:
			time.sleep(ecart)
		else:
			attendre_la_fin_des_voies(contexte)
		horloge(contexte).avancer(timedelta(seconds=ecart))


def attendre_la_fin_des_voies(contexte: Contexte, delai: float = 5.0) -> None:
	assert contexte.moteur is not None
	limite = time.monotonic() + delai
	while any(v.etat == "en cours" for v in contexte.moteur.voies_en_cours()) and time.monotonic() < limite:
		time.sleep(PAS_REEL / 5)
		for voie in contexte.moteur.voies_en_cours():
			voie.traiter()


@when(parsers.parse("la diffusion tourne pendant {duree} seconde en temps réel"))
def tourner_en_temps_reel(contexte: Contexte, duree: str) -> None:
	fin = time.monotonic() + secondes(duree)
	precedent = time.monotonic()
	while time.monotonic() < fin:
		diffusion(contexte).pas()
		time.sleep(PAS_REEL)
		maintenant = time.monotonic()
		horloge(contexte).avancer(timedelta(seconds=maintenant - precedent))
		precedent = maintenant


@when(parsers.parse("l'horloge du binaire passe au « {instant} »"))
def horloge_passe(contexte: Contexte, instant: str) -> None:
	horloge(contexte).avancer(heure(instant) - horloge(contexte).maintenant())


@when(parsers.parse("le sonore « {nom} » redevient actif"))
def redevient_actif(base_vide: Connexion, nom: str) -> None:
	base_vide.execute("UPDATE sonores SET etat = 'actif' WHERE id = %s", (sonore(base_vide, nom),))


@when("la diffusion s'arrête")
def arreter(contexte: Contexte) -> None:
	diffusion(contexte).arreter()


@when("le processus reçoit SIGTERM")
def sigterm() -> None:
	# raise_signal le délivre au fil principal, aussitôt : jamais à un fil de GStreamer, ni après la restauration
	# des gestionnaires d'origine, qui arrêterait pytest.
	signal.raise_signal(signal.SIGTERM)


@when("je lance Machin_lecture avec une configuration dont la socket n'existe pas")
def lancer_sans_base(contexte: Contexte, tmp_path: Path) -> None:
	configuration = tmp_path / "sans-base.toml"
	texte = CONFIGURATION_TEST.read_text(encoding="utf-8")
	configuration.write_text(
		texte.replace('socket = "/var/run/postgresql"', f'socket = "{tmp_path / "aucune-socket"}"'), encoding="utf-8"
	)
	chemin = shutil.which("Machin_lecture") or str(Path(sys.executable).parent / "Machin_lecture")
	contexte.resultat = subprocess.run(
		[chemin, "--config", str(configuration)], capture_output=True, text=True, timeout=60
	)


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


@then("l'arrêt de la diffusion est demandé")
def arret_demande(contexte: Contexte) -> None:
	assert contexte.arret is not None and contexte.arret.wait(2)


@then("il s'arrête avec le code 1, en signalant la base de données injoignable")
def code_un(contexte: Contexte) -> None:
	assert contexte.resultat is not None
	assert contexte.resultat.returncode == 1, contexte.resultat.stderr
	assert "base de données injoignable" in contexte.resultat.stderr
