"""Horloge injectable (https://github.com/dascritch/machincast/issues/5).

Tout code qui dépend de l'heure reçoit une Horloge au lieu d'appeler datetime.now() : les tests lui
passent une FixedClock, qu'ils font avancer à volonté. Les heures sont toujours munies d'un fuseau.
"""

from datetime import datetime, timedelta
from typing import Protocol

from machincast.i18n import _


class Clock(Protocol):
	def now(self) -> datetime:
		"""Heure courante, avec fuseau."""
		...


class SystemClock:
	"""Heure réelle, dans le fuseau local de la machine."""

	def now(self) -> datetime:
		return datetime.now().astimezone()


class FixedClock:
	"""Heure choisie par le test ; elle ne change que par avancer()."""

	def __init__(self, instant: datetime) -> None:
		if instant.tzinfo is None:
			raise ValueError(_("time without a time zone: {instant}").format(instant=instant.isoformat()))
		self._instant = instant

	def now(self) -> datetime:
		return self._instant

	def advance(self, duration: timedelta) -> None:
		self._instant += duration
