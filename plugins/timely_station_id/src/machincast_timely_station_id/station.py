"""La réponse du station ID régulier au point « player.before_choice »
(https://github.com/dascritch/machincast/issues/460, https://github.com/dascritch/machincast/issues/640).

Dans un événement coché, avant chaque sonore choisi dans sa liste : si la règle (machincast_timely_station_id.rule)
le demande, d'après le dernier passage de la banque des station ID ou d'une banque qui annonce aussi la station, prévus compris, la
banque des station ID ; sinon rien. Un candidat fourni par l'une de ces banques passe tel quel : il est lui-même un
station ID. Une banque introuvable est consignée une fois.
"""

import logging
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

import psycopg

from machincast_timely_station_id import queries
from machincast_timely_station_id.rule import Current, due
from machincast_timely_station_id.texts import t

log = logging.getLogger(__name__)


class Station:
	def __init__(self, current: Current) -> None:
		self.current = current
		self.missing: set[str] = set()
		"""Les banques introuvables déjà consignées."""

	def answer(self, data: Mapping[str, Any]) -> int | None:
		settings = self.current.settings
		if settings is None:
			return None
		connection: queries.Connection = data["connection"]
		try:
			with connection.transaction():
				if not queries.chosen(connection, int(data["event"])):
					return None
				identifiers = queries.banks(connection, settings.banks())
		except psycopg.Error as error:
			log.error("timely_station_id: %s", error)
			return None
		self._note_missing(settings.banks(), identifiers)
		station = identifiers.get(settings.bank)
		if station is None:
			return None
		known = list(identifiers.values())
		if data.get("bank") in known:
			return None
		last = data["last_play"](known)
		elapsed = None
		instant = data["instant"]
		if (isinstance(last, datetime)) and (isinstance(instant, datetime)):
			elapsed = instant - last
		duration = data.get("duration")
		if not isinstance(duration, timedelta):
			duration = None
		if due(settings, elapsed, duration):
			return station
		return None

	def _note_missing(self, names: tuple[str, ...], identifiers: dict[str, int]) -> None:
		for name in names:
			if (name not in identifiers) and (name not in self.missing):
				self.missing.add(name)
				log.warning(t("timely_station_id: no bank “{name}”").format(name=name))
