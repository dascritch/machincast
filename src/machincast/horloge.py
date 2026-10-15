"""Horloge injectable (https://github.com/dascritch/machincast/issues/5).

Tout code qui dépend de l'heure reçoit une Horloge au lieu d'appeler datetime.now() : les tests lui
passent une HorlogeFixe, qu'ils font avancer à volonté. Les heures sont toujours munies d'un fuseau.
"""

import os
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class Horloge(Protocol):
	def maintenant(self) -> datetime:
		"""Heure courante, avec fuseau."""
		...


class HorlogeSysteme:
	"""Heure réelle, dans le fuseau local de la machine."""

	def maintenant(self) -> datetime:
		return datetime.now().astimezone()


class HorlogeFixe:
	"""Heure choisie par le test ; elle ne change que par avancer()."""

	def __init__(self, instant: datetime) -> None:
		if instant.tzinfo is None:
			raise ValueError(f"heure sans fuseau : {instant.isoformat()}")
		self._instant = instant

	def maintenant(self) -> datetime:
		return self._instant

	def avancer(self, duree: timedelta) -> None:
		self._instant += duree


def fuseau_local() -> tzinfo:
	"""Fuseau horaire du système, avec ses changements d'heure : la variable TZ, sinon /etc/localtime.

	Un datetime.now().astimezone() n'a qu'un décalage fixe : il ne suffit pas pour calculer une récurrence qui
	traverse un changement d'heure (https://github.com/dascritch/machincast/issues/12).
	"""
	nom = os.environ.get("TZ", "").removeprefix(":")
	if nom:
		try:
			return ZoneInfo(nom)
		except (ZoneInfoNotFoundError, ValueError):
			pass
	try:
		with open("/etc/localtime", "rb") as fichier:
			return ZoneInfo.from_file(fichier, key="localtime")
	except OSError:
		return UTC
