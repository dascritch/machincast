"""Conversion des valeurs lues en base, ou dans un message, qui peuvent être absentes
(https://github.com/dascritch/machincast/issues/187).

Une valeur absente, None ou NULL en base, reste absente ; les autres sont converties. Ces fonctions remplacent celles
que plusieurs modules réécrivaient à l'identique.
"""

from collections.abc import Collection
from datetime import timedelta


def texte_ou_rien(valeur: object) -> str | None:
	if valeur is None:
		return None
	return str(valeur)


def entier_ou_rien(valeur: object) -> int | None:
	if valeur is None:
		return None
	return int(str(valeur))


def booleen_ou_rien(valeur: object) -> bool | None:
	if valeur is None:
		return None
	return bool(valeur)


def duree_ou_rien(valeur: object) -> timedelta | None:
	"""Une durée, et rien pour toute autre valeur."""
	if isinstance(valeur, timedelta):
		return valeur
	return None


def liste_ou_rien(identifiants: Collection[int] | None) -> list[int] | None:
	"""Une collection d'identifiants en liste, pour un tableau PostgreSQL ; rien reste rien, c'est-à-dire tous."""
	if identifiants is None:
		return None
	return list(identifiants)
