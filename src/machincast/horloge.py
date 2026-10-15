"""Horloge injectable (https://github.com/dascritch/machincast/issues/5).

Tout code qui dépend de l'heure reçoit une Horloge au lieu d'appeler datetime.now() : les tests lui
passent une HorlogeFixe, qu'ils font avancer à volonté. Les heures sont toujours munies d'un fuseau.
"""

from datetime import datetime, timedelta
from typing import Protocol


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
