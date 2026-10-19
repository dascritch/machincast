"""Étapes du chevauchement de deux événements de même priorité (https://github.com/dascritch/machincast/issues/32)."""

from datetime import datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then

from machincast.lecture.grille import JAMAIS, JOURS, Evenement, Priorite, chevauchement

scenarios("chevauchements.feature")


def heure_ou_rien(texte: str) -> datetime | None:
	"""« 2026-10-14 21:30 » en heure du poste, avec fuseau ; aucune heure pour une cellule vide."""
	if texte == "":
		return None
	return datetime.fromisoformat(texte).astimezone()


@pytest.fixture
def evenements() -> list[Evenement]:
	return []


@given("les événements à comparer :")
def a_comparer(evenements: list[Evenement], datatable: list[list[str]]) -> None:
	entetes, *lignes = datatable
	for numero, valeurs in enumerate(lignes, start=1):
		ligne = dict(zip((entete.strip() for entete in entetes), (valeur.strip() for valeur in valeurs), strict=True))
		evenements.append(
			Evenement(
				id=numero,
				nom=ligne["nom"],
				priorite=Priorite(ligne["priorité"]),
				debut=heure_ou_rien(ligne["début"]),
				fin=heure_ou_rien(ligne["fin"]),
				jours=frozenset(JOURS.index(jour.strip()) for jour in ligne["jours"].split(",") if jour.strip()),
				modifie_le=JAMAIS,
			)
		)


@then(parsers.re(r"« (?P<nom>[^»]+) » chevauche (?:rien|« (?P<autre>[^»]+) » le « (?P<instant>[^»]+) »)"))
def chevauche(evenements: list[Evenement], nom: str, autre: str | None, instant: str | None) -> None:
	(place,) = [evenement for evenement in evenements if evenement.nom == nom]
	trouve = chevauchement(place, [evenement for evenement in evenements if evenement is not place])
	obtenu = None
	if trouve is not None:
		obtenu = (trouve[0].nom, f"{trouve[1]:%Y-%m-%d %H:%M}")
	attendu = None
	if autre is not None:
		attendu = (autre, instant)
	assert obtenu == attendu
