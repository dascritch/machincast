"""Scénarios de la position des fondus par rapport aux blancs détectés
(https://github.com/dascritch/machincast/issues/234).

Le placement s'essaie seul (machincast.lecture.fondus.placer) ; la diffusion, par les paramètres de lecture qu'elle lit
en base de test (machincast.lecture.diffusion.lire_parametres), avec le rôle de Machin lecture.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from types import SimpleNamespace
from typing import cast

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.configuration import Crossfades
from machincast.lecture.deroule import Choix
from machincast.lecture.diffusion import Parametres, lire_parametres
from machincast.lecture.fondus import LIBELLES, POSITIONS, Placement, Position, placer
from tests.base_test import parametres_base_test

scenarios("position_des_fondus.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
POSITION = {libelle: position for position, libelle in LIBELLES.items()}
"""Chaque position par ce qu'elle dit, « est en cours »."""


@dataclass
class Essai:
	duree: timedelta = timedelta(0)
	debut: timedelta | None = None
	fin: timedelta | None = None
	sans_blancs: bool = True
	crossfades: tuple[timedelta, timedelta] = (timedelta(0), timedelta(0))
	placement: Placement | None = None
	sonores: dict[str, int] = field(default_factory=dict)
	banques: dict[str, int] = field(default_factory=dict)
	defauts: Crossfades = field(default_factory=Crossfades)
	parametres: Parametres | None = None


@pytest.fixture
def essai() -> Essai:
	return Essai()


def secondes(texte: str) -> float:
	return float(texte.replace(",", ".").removesuffix(" s"))


def blanc(texte: str) -> timedelta | None:
	if texte == "aucun":
		return None
	return timedelta(seconds=secondes(texte))


# ─── Placement ─────────────────────────────────────────────


@given(
	parsers.re(
		r"un fichier de (?P<duree>\d+) secondes, aux blancs détectés de (?P<debut>[\d,]+ s|aucun) au début et"
		r" (?P<fin>[\d,]+ s|aucun) à la fin, (?P<joue>sans|avec) ses blancs"
	)
)
def fichier(essai: Essai, duree: str, debut: str, fin: str, joue: str) -> None:
	essai.duree = timedelta(seconds=int(duree))
	essai.debut, essai.fin = blanc(debut), blanc(fin)
	essai.sans_blancs = joue == "sans"


@given(parsers.parse("des crossfades de {debut:d} secondes au début et {fin:d} à la fin"))
def crossfades(essai: Essai, debut: int, fin: int) -> None:
	essai.crossfades = (timedelta(seconds=debut), timedelta(seconds=fin))


@when(
	parsers.re(
		r"le fade-in (?P<entree>commence|est en cours|se termine) au début détecté, et le fade-out"
		r" (?P<sortie>commence|est en cours|se termine) à la fin détectée"
	)
)
def placer_les_fondus(essai: Essai, entree: str, sortie: str) -> None:
	essai.placement = placer(
		essai.duree, essai.debut, essai.fin, essai.sans_blancs, *essai.crossfades, POSITION[entree], POSITION[sortie]
	)


def _placement(essai: Essai) -> Placement:
	assert essai.placement is not None
	return essai.placement


@then(parsers.parse("la lecture va de {de} à {a} secondes du fichier"))
def lecture(essai: Essai, de: str, a: str) -> None:
	placement = _placement(essai)
	assert placement.debut.total_seconds() == pytest.approx(secondes(de))
	assert (placement.debut + placement.duree).total_seconds() == pytest.approx(secondes(a))
	# Le fichier entier se joue sans décalage : la voie n'a rien à borner.
	entier = (secondes(de) == 0) and (secondes(a) == essai.duree.total_seconds())
	assert (placement.decalage is None) == entier, placement


@then(parsers.parse("le fade-in dure {duree} secondes, depuis le volume {volume}"))
def fade_in(essai: Essai, duree: str, volume: str) -> None:
	placement = _placement(essai)
	assert placement.fondu_entree.total_seconds() == pytest.approx(secondes(duree))
	assert placement.depart == pytest.approx(secondes(volume))


@then(parsers.parse("le fade-out dure {duree} secondes, jusqu'au volume {volume}"))
def fade_out(essai: Essai, duree: str, volume: str) -> None:
	placement = _placement(essai)
	assert placement.fondu_sortie.total_seconds() == pytest.approx(secondes(duree))
	assert placement.arrivee == pytest.approx(secondes(volume))


@then(parsers.parse("la position « {libelle} » s'écrit « {cle} » dans la configuration"))
def cle_de_configuration(libelle: str, cle: str) -> None:
	assert cle in POSITIONS
	assert LIBELLES[cast(Position, cle)] == libelle


# ─── Diffusion ─────────────────────────────────────────────


@given(
	parsers.re(
		r"le sonore « (?P<titre>[^»]+) », de (?P<duree>\d+) secondes, aux blancs détectés de (?P<debut>[\d,]+) s au"
		r" début et (?P<fin>[\d,]+) s à la fin, qui active la détection de blanc, avec des crossfades de"
		r" (?P<cd>\d+) secondes au début et (?P<cf>\d+) à la fin"
	)
)
def sonore(essai: Essai, base_vide: Connexion, titre: str, duree: str, debut: str, fin: str, cd: str, cf: str) -> None:
	ligne = base_vide.execute(
		"INSERT INTO sonores (type, emplacement, titre, etat, duree, debut_detecte, fin_detectee, detection_blancs,"
		" crossfade_debut, crossfade_fin) VALUES ('fichier', %s, %s, 'actif', %s, %s, %s, true, %s, %s) RETURNING id",
		(
			f"/srv/musique/{titre}.flac",
			titre,
			timedelta(seconds=int(duree)),
			timedelta(seconds=secondes(debut)),
			timedelta(seconds=secondes(fin)),
			timedelta(seconds=int(cd)),
			timedelta(seconds=int(cf)),
		),
	).fetchone()
	assert ligne is not None
	essai.sonores[titre] = int(str(ligne[0]))


@given(
	parsers.re(
		r"les positions des fondus de la configuration : fade-in « (?P<entree>[^»]+) », fade-out « (?P<sortie>[^»]+) »"
	)
)
def positions_de_la_configuration(essai: Essai, entree: str, sortie: str) -> None:
	essai.defauts = Crossfades(entree=POSITION[entree], sortie=POSITION[sortie])


@given(
	parsers.re(
		r"la banque « (?P<nom>[^»]+) », avec « (?P<titre>[^»]+) », qui impose un crossfade de fin de"
		r" (?P<duree>[\d,]+) secondes"
	)
)
def banque(essai: Essai, base_vide: Connexion, nom: str, titre: str, duree: str) -> None:
	ligne = base_vide.execute(
		"INSERT INTO banques (nom_interne, mode, crossfade_fin_regle, crossfade_fin)"
		" VALUES (%s, 'aleatoire', 'impose', %s) RETURNING id",
		(nom, timedelta(seconds=secondes(duree))),
	).fetchone()
	assert ligne is not None
	essai.banques[nom] = int(str(ligne[0]))
	base_vide.execute(
		"INSERT INTO banques_sonores (banque_id, sonore_id, position) VALUES (%s, %s, 1)",
		(ligne[0], essai.sonores[titre]),
	)


@when(
	parsers.re(
		r"la diffusion lit les paramètres de « (?P<titre>[^»]+) », (?:de la banque « (?P<nom>[^»]+) »|sans banque)"
	)
)
def lire(essai: Essai, titre: str, nom: str | None) -> None:
	banque_id = None
	if nom is not None:
		banque_id = essai.banques[nom]
	# lire_parametres ne lit du choix que le sonore et sa banque.
	choix = cast(Choix, SimpleNamespace(sonore=essai.sonores[titre], banque=banque_id))
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		essai.parametres = lire_parametres(connexion, choix, essai.defauts)


@then(
	parsers.re(
		r"ses paramètres de lecture : à partir de (?P<decalage>[\d,]+) s du fichier, pendant (?P<duree>[\d,]+) s,"
		r" fade-in de (?P<cd>[\d,]+) s depuis (?P<depart>[\d,]+), fade-out de (?P<cf>[\d,]+) s jusqu'à"
		r" (?P<arrivee>[\d,]+)"
	)
)
def parametres(essai: Essai, decalage: str, duree: str, cd: str, depart: str, cf: str, arrivee: str) -> None:
	lus = essai.parametres
	assert lus is not None
	assert (lus.decalage is not None) and (lus.duree is not None)
	lues = (
		lus.decalage.total_seconds(),
		lus.duree.total_seconds(),
		lus.crossfade_debut.total_seconds(),
		lus.volume_de_depart,
		lus.crossfade_fin.total_seconds(),
		lus.volume_d_arrivee,
	)
	attendues = tuple(secondes(valeur) for valeur in (decalage, duree, cd, depart, cf, arrivee))
	assert lues == pytest.approx(attendues), lues
