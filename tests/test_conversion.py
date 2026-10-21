"""Scénarios des conversions partagées (https://github.com/dascritch/machincast/issues/187)."""

import re
from datetime import timedelta

from pytest_bdd import parsers, scenarios, then

from machincast import conversion

scenarios("conversion.feature")


def valeur(texte: str) -> object:
	"""La valeur que décrit le scénario : « rien », « le texte « … » », « le nombre 12 »…"""
	if texte == "rien":
		return None
	if texte in ("vrai", "faux"):
		return texte == "vrai"
	if (trouve := re.fullmatch(r"le texte « ?(.*?) ?»", texte)) is not None:
		return trouve.group(1)
	if (trouve := re.fullmatch(r"(?:le nombre|l'entier) (\d+)", texte)) is not None:
		return int(trouve.group(1))
	if (trouve := re.fullmatch(r"la durée de (\d+) s", texte)) is not None:
		return timedelta(seconds=int(trouve.group(1)))
	if (trouve := re.fullmatch(r"(?:l'ensemble|la liste) (.+)", texte)) is not None:
		nombres = [int(nombre) for nombre in trouve.group(1).split(", ")]
		if texte.startswith("l'ensemble"):
			return set(nombres)
		return nombres
	raise AssertionError(texte)


@then(parsers.re(r"(?P<nom>\w+) de (?P<entree>.+) donne (?P<sortie>.+)"))
def convertir(nom: str, entree: str, sortie: str) -> None:
	resultat = getattr(conversion, nom)(valeur(entree))
	if isinstance(resultat, list):
		resultat = sorted(resultat)
	attendu = valeur(sortie)
	assert (resultat, type(resultat)) == (attendu, type(attendu))
