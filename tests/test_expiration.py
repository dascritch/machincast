"""Étapes de l'expiration automatique des sonores (https://github.com/dascritch/machincast/issues/18).

Les étapes de la diffusion viennent de tests/etapes_diffusion.py.
"""

import uuid
from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.lecture.expiration import expirer
from tests.base_test import parametres_base_test
from tests.etapes_diffusion import Connexion, heure, sonore

scenarios("expiration.feature")


@dataclass
class Avant:
	lignes: dict[str, dict[str, object]] = field(default_factory=dict)


@pytest.fixture
def avant() -> Avant:
	return Avant()


def ligne_du_sonore(base: Connexion, nom: str) -> dict[str, object]:
	ligne = base.execute("SELECT to_jsonb(s) FROM sounds s WHERE title = %s", (nom,)).fetchone()
	assert (ligne is not None) and (isinstance(ligne[0], dict))
	return dict(ligne[0])


def jouer(base: Connexion, nom: str, nombre: int, evenement: object = None, banque: object = None) -> None:
	for _ in range(nombre):
		base.execute(
			"INSERT INTO airplay (play_id, line_type, sound_id, event_id, bank_id) VALUES (%s, 'start', %s, %s, %s)",
			(uuid.uuid4(), sonore(base, nom), evenement, banque),
		)


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("le sonore actif « {nom} » avec un maximum de {maximum:d} lectures"))
def sonore_avec_maximum(base_vide: Connexion, nom: str, maximum: int) -> None:
	base_vide.execute(
		"INSERT INTO sounds (type, location, state, title, max_plays) VALUES ('file', %s, 'active', %s, %s)",
		(f"/annonces/{nom}.flac", nom, maximum),
	)


@given(parsers.re(r"le sonore « (?P<nom>[^»]+) » a un maximum de (?P<maximum>\d+) lectures?"))
def maximum_du_sonore(base_vide: Connexion, nom: str, maximum: str) -> None:
	base_vide.execute("UPDATE sounds SET max_plays = %s WHERE id = %s", (int(maximum), sonore(base_vide, nom)))


@given(parsers.parse("le sonore actif « {nom} » diffusable jusqu'au « {fin} »"))
def sonore_avec_fin(base_vide: Connexion, nom: str, fin: str) -> None:
	base_vide.execute(
		"INSERT INTO sounds (type, location, state, title, broadcast_end) VALUES ('file', %s, 'active', %s, %s)",
		(f"/annonces/{nom}.flac", nom, heure(fin)),
	)


@given(parsers.parse("le sonore « {nom} » est à l'état « {etat} »"))
def etat_du_sonore(base_vide: Connexion, nom: str, etat: str) -> None:
	base_vide.execute("UPDATE sounds SET state = %s WHERE id = %s", (etat, sonore(base_vide, nom)))


@given(parsers.re(r"« (?P<nom>[^»]+) » a été joué (?P<nombre>\d+) fois$"))
def joue(base_vide: Connexion, nom: str, nombre: str) -> None:
	jouer(base_vide, nom, int(nombre))


@given(parsers.parse("« {nom} » a été joué {nombre:d} fois dans l'émission « {emission} »"))
def joue_dans_une_emission(base_vide: Connexion, nom: str, nombre: int, emission: str) -> None:
	cree = base_vide.execute(
		"INSERT INTO events (internal_name, priority, starts_at) VALUES (%s, 'show', '2026-10-01 08:00') RETURNING id",
		(emission,),
	).fetchone()
	assert cree is not None
	jouer(base_vide, nom, nombre, evenement=cree[0])


@given(parsers.parse("« {nom} » a été joué {nombre:d} fois via la banque « {banque} »"))
def joue_via_une_banque(base_vide: Connexion, nom: str, nombre: int, banque: str) -> None:
	creee = base_vide.execute(
		"INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential') RETURNING id", (banque,)
	).fetchone()
	assert creee is not None
	jouer(base_vide, nom, nombre, banque=creee[0])


@given(parsers.parse("« {nom} » a été joué {nombre:d} fois sans événement ni banque"))
def joue_sans_rien(base_vide: Connexion, nom: str, nombre: int) -> None:
	jouer(base_vide, nom, nombre)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse("le binaire lecture vérifie les expirations au « {instant} »"))
def verifier(base_vide: Connexion, avant: Avant, instant: str) -> None:
	for (titre,) in base_vide.execute("SELECT title FROM sounds").fetchall():
		avant.lignes.setdefault(str(titre), ligne_du_sonore(base_vide, str(titre)))
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		expirer(connexion, heure(instant))


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.parse("le sonore « {nom} » est à l'état « {etat} »"))
def etat_attendu(base_vide: Connexion, nom: str, etat: str) -> None:
	assert ligne_du_sonore(base_vide, nom)["state"] == etat


@then(parsers.parse("le log contient {nombre:d} info « {nature} », pour ce sonore, qui mentionne « {mention} »"))
def ligne_du_log(base_vide: Connexion, nombre: int, nature: str, mention: str) -> None:
	lignes = base_vide.execute("SELECT level::text, message, sound_id FROM log WHERE kind = %s", (nature,)).fetchall()
	assert len(lignes) == nombre, lignes
	identifiants = {int(str(i)) for (i,) in base_vide.execute("SELECT id FROM sounds").fetchall()}
	for niveau, message, sonore_id in lignes:
		assert (niveau == "info") and (mention in str(message)) and (sonore_id in identifiants), lignes


@then("le log est vide")
def log_vide(base_vide: Connexion) -> None:
	assert base_vide.execute("SELECT level, kind, message FROM log").fetchall() == []


@then(parsers.parse("seules les colonnes state et modified_at du sonore « {nom} » ont changé"))
def seul_l_etat(base_vide: Connexion, avant: Avant, nom: str) -> None:
	apres = ligne_du_sonore(base_vide, nom)
	changees = {cle for cle in apres if apres[cle] != avant.lignes[nom][cle]}
	assert changees == {"state", "modified_at"}, changees
