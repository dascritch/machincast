"""Conversion des valeurs lues en base, ou dans un message, qui peuvent être absentes
(https://github.com/dascritch/machincast/issues/187).

Une valeur absente, None ou NULL en base, reste absente ; les autres sont converties. Ces fonctions remplacent celles
que plusieurs modules réécrivaient à l'identique.
"""

from collections.abc import Collection
from datetime import timedelta


def text_or_none(value: object) -> str | None:
	if value is None:
		return None
	return str(value)


def integer_or_none(value: object) -> int | None:
	if value is None:
		return None
	return int(str(value))


def boolean_or_none(value: object) -> bool | None:
	if value is None:
		return None
	return bool(value)


def duration_or_none(value: object) -> timedelta | None:
	"""Une durée, et rien pour toute autre valeur."""
	if isinstance(value, timedelta):
		return value
	return None


def list_or_none(identifiers: Collection[int] | None) -> list[int] | None:
	"""Une collection d'identifiants en liste, pour un tableau PostgreSQL ; rien reste rien, c'est-à-dire tous."""
	if identifiers is None:
		return None
	return list(identifiers)
