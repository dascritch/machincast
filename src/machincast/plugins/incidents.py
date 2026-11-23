"""log_incident : l'avertissement d'un incident grave, dans chaque binaire
(https://github.com/dascritch/machincast/issues/592).

Les plugins chargés (machincast.plugins.active) abonnés au point « log_incident » sont prévenus, sans être attendus, de
chaque incident sérieux consigné :

- une entrée du log de niveau « incident » (machincast.player.saving.record), avec ce qu'elle concerne ;
- une erreur du journal du binaire, de niveau ERROR ou CRITICAL, quel que soit le module qui la consigne : le
  gestionnaire que load installe sur le journal (install).

Un plugin qui échoue à prévenir ne crée pas d'incident à son tour : ce que le journal consigne pendant qu'un abonné
de log_incident est appelé, son échec compris, n'est pas un incident (machincast.plugins.points.calling).
"""

import logging
from collections.abc import Mapping
from datetime import datetime

POINT = "log_incident"


class _Handler(logging.Handler):
	"""Le journal du binaire : chaque erreur est un incident."""

	def __init__(self) -> None:
		super().__init__(logging.ERROR)

	def emit(self, record: logging.LogRecord) -> None:
		tell(
			record.levelname.lower(),
			record.name,
			record.getMessage(),
			datetime.fromtimestamp(record.created).astimezone(),
		)


_handler = _Handler()


def install() -> None:
	"""Le gestionnaire du journal du binaire, une seule fois ; il ne fait rien tant qu'aucun plugin n'est abonné."""
	root = logging.getLogger()
	if _handler not in root.handlers:
		root.addHandler(_handler)


def tell(
	level: str,
	kind: str,
	message: str,
	instant: datetime | None = None,
	references: Mapping[str, int | None] | None = None,
	origin: str | None = None,
) -> None:
	"""Prévient les plugins abonnés d'un incident ; rien pendant l'appel d'un abonné de log_incident."""
	from machincast import plugins
	from machincast.plugins.points import calling

	if calling() == POINT:
		return
	loaded = plugins.active()
	if loaded.points.subscribers(POINT) == []:
		return
	when = (instant) or (datetime.now().astimezone())
	if when.tzinfo is None:
		when = when.astimezone()
	given: dict[str, int | None] = {"sound": None, "bank": None, "event": None}
	if references is not None:
		given.update(references)
	loaded.points.notify(
		POINT,
		{
			"executable": loaded.executable,
			"instant": when.isoformat(),
			"level": level,
			"kind": kind,
			"message": message,
			"references": given,
			"origin": origin,
		},
	)
