"""Le gain de chaque sonore, dans Machin player, et la vérification de son ajustement manuel, dans Machin indexer
(https://github.com/dascritch/machincast/issues/43).

- Au point « player.sound_gain » (https://github.com/dascritch/machincast/issues/643) : le gain du sonore, d'après
  sa mesure et son ajustement manuel, borné par le plafond de crête (machincast_loudness_normalization.rule).
- Au point « indexer.sound_detailed » : un audit complet vient de mesurer le sonore, par exemple après une mise à jour
  de son fichier. Si son ajustement manuel le ferait dépasser le plafond, il est ramené à la plus forte valeur
  permise, et une ligne « incident » le dit dans le log.
"""

import logging
from collections.abc import Callable, Mapping
from typing import Any

import psycopg

from machincast.i18n import decimal
from machincast_loudness_normalization import queries
from machincast_loudness_normalization.rule import Current, applied, automatic, headroom, manual, measure, tenth_below
from machincast_loudness_normalization.texts import t

log = logging.getLogger(__name__)


def signed(value: float) -> str:
	"""« +2,5 », « −0,7 », au dixième, avec la virgule de la langue."""
	return decimal(f"{value:+.1f}").replace("-", "−")


def sound_gain(current: Current) -> Callable[[Mapping[str, Any]], float | None]:
	def answer(data: Mapping[str, Any]) -> float | None:
		settings = current.settings
		properties = data.get("properties")
		if (settings is None) or (not isinstance(properties, dict)):
			return None
		return applied(settings, measure(properties), manual(properties))

	return answer


def detailed(current: Current, connect: Callable[[], queries.Connection]) -> Callable[[Mapping[str, Any]], None]:
	"""Dans le fil des plugins de Machin indexer : sa propre connexion, au rôle de l'indexation."""

	def check(data: Mapping[str, Any]) -> None:
		settings = current.settings
		measured = data.get("loudness")
		if (settings is None) or (not isinstance(measured, dict)):
			return
		sound = int(data["sound"])
		try:
			with connect() as connection, connection.transaction():
				found = queries.properties(connection, sound)
				adjustment = manual(found)
				now = measure(found)
				limit = headroom(settings, now)
				if (adjustment == 0) or (limit is None) or (now.peak is None) or (adjustment <= limit):
					return
				lowered = tenth_below(limit)
				queries.write_manual(connection, sound, lowered)
				message = t(
					"“{location}”: its peak of {peak} dBFS would exceed the ceiling of {ceiling} dBFS with a gain of"
					" {gain} dB: manual adjustment brought from {before} to {after} dB"
				).format(
					location=data.get("location"),
					peak=signed(now.peak),
					ceiling=signed(settings.ceiling),
					gain=signed(automatic(settings, now) + adjustment),
					before=signed(adjustment),
					after=signed(lowered),
				)
				queries.record_incident(connection, t("level adjusted"), message, sound)
		except psycopg.Error as error:
			log.error(t("loudness_normalization: {error}").format(error=error))

	return check
