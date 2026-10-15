"""Étapes de la détermination de l'événement actif (https://github.com/dascritch/machincast/issues/12)."""

from dataclasses import dataclass, field
from datetime import datetime

import psycopg
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.base import Role, connecter
from machincast.horloge import HorlogeFixe
from machincast.lecture.grille import Evenement, Priorite, evenement_actif, heure_murale, lire_grille, occurrence
from tests.base_test import parametres_base_test

scenarios("evenement_actif.feature")

Connexion = psycopg.Connection[tuple[object, ...]]
JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


@dataclass
class Contexte:
	evenements: list[Evenement] = field(default_factory=list)
	terminees: set[tuple[int, datetime | None]] = field(default_factory=set)
	horloge: HorlogeFixe | None = None


@pytest.fixture
def contexte() -> Contexte:
	return Contexte()


def heure(contexte: Contexte, texte: str) -> datetime:
	"""« 2026-10-14 21:30 » en heure du poste, ou « 2026-10-25 02:30+01:00 » avec son décalage ; avec fuseau."""
	return datetime.fromisoformat(texte.strip()).astimezone()


def tableau(datatable: list[list[str]]) -> list[dict[str, str]]:
	entetes, *lignes = datatable
	return [dict(zip(entetes, (cellule.strip() for cellule in ligne), strict=True)) for ligne in lignes]


def nomme(contexte: Contexte, nom: str) -> Evenement:
	return next(e for e in contexte.evenements if e.nom == nom)


def actif(contexte: Contexte, instant: datetime) -> str | None:
	resultat = evenement_actif(contexte.evenements, instant, frozenset(contexte.terminees))
	return None if resultat is None else resultat.evenement.nom


@given("aucun événement")
def aucun(contexte: Contexte) -> None:
	contexte.evenements = []


@given(parsers.parse("l'heure « {texte} »"))
def horloge(contexte: Contexte, texte: str) -> None:
	contexte.horloge = HorlogeFixe(heure(contexte, texte))


@given("les événements :")
def evenements(contexte: Contexte, datatable: list[list[str]]) -> None:
	contexte.evenements = [
		Evenement(
			id=numero,
			nom=ligne["nom"],
			priorite=Priorite(ligne["priorité"]),
			debut=heure(contexte, ligne["début"]) if ligne["début"] else None,
			fin=heure(contexte, ligne["fin"]) if ligne["fin"] else None,
			jours=frozenset(JOURS.index(jour.strip()) for jour in ligne["jours"].split(",") if jour.strip()),
			modifie_le=heure(contexte, ligne["modifié"]),
		)
		for numero, ligne in enumerate(tableau(datatable), start=1)
	]


@given("ces événements enregistrés en base")
def en_base(contexte: Contexte, base_vide: Connexion) -> None:
	for e in contexte.evenements:
		base_vide.execute(
			"INSERT INTO evenements (nom_interne, priorite, debut, fin, jours_recurrence, modifie_le)"
			" VALUES (%s, %s, %s, %s, %s::jour_semaine[], %s)",
			(e.nom, e.priorite.value, e.debut, e.fin, [JOURS[j] for j in sorted(e.jours)], e.modifie_le),
		)


@when("le binaire lecture lit la grille en base")
def lire(contexte: Contexte, base_vide: Connexion) -> None:
	with connecter(*parametres_base_test(), Role.LECTURE) as connexion:
		contexte.evenements = lire_grille(connexion)


@when(parsers.parse("l'occurrence de « {nom} » commencée le « {debut} » se termine, sa liste épuisée"))
def terminer(contexte: Contexte, nom: str, debut: str) -> None:
	instant = heure(contexte, debut)
	en_cours = occurrence(nomme(contexte, nom), instant)
	assert en_cours is not None and en_cours.debut == heure_murale(instant), en_cours
	contexte.terminees.add(en_cours.cle)


@then("aucun événement n'est actif")
def aucun_actif(contexte: Contexte) -> None:
	assert contexte.horloge is not None
	assert actif(contexte, contexte.horloge.maintenant()) is None


@then(parsers.parse("l'événement actif est « {nom} » à chacune de ces heures :"))
def actif_partout(contexte: Contexte, nom: str, datatable: list[list[str]]) -> None:
	for ligne in tableau(datatable):
		assert actif(contexte, heure(contexte, ligne["heure"])) == nom, ligne["heure"]


@then("l'événement actif est :")
def actif_selon_heure(contexte: Contexte, datatable: list[list[str]]) -> None:
	ecarts = []
	for ligne in tableau(datatable):
		# La grille ne lit l'heure que par une horloge : une horloge fixe, réglée sur chaque heure du tableau.
		obtenu = actif(contexte, HorlogeFixe(heure(contexte, ligne["heure"])).maintenant())
		if obtenu != ligne["actif"]:
			ecarts.append(f"{ligne['heure']} : {obtenu} au lieu de {ligne['actif']}")
	assert not ecarts, "\n".join(ecarts)
