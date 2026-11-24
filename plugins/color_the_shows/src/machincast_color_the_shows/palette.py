"""Ce que le plugin répond au point « grid.event_colour » (https://github.com/dascritch/machincast/issues/635,
https://github.com/dascritch/machincast/issues/628).

Le point est demandé à chaque dessin d'un bloc ou d'une cellule : la palette répond de mémoire. Elle relit les genres,
les couleurs des priorités et le genre de chaque événement au plus tous les LIFETIME secondes, à sa première
réponse qui suit, et aussitôt après un enregistrement dans l'interface (forget). Une base injoignable garde la palette
qu'elle avait.

- Un événement qui a un genre : la couleur de son genre.
- Sinon, la couleur de sa priorité, quand le plugin en a une : gris pour le fil antenne, vert pour les émissions,
  rouge pour les spéciales, par défaut ; aucune pour un imprévu ou un secours, ni sans priorité connue, dans un
  tableau d'airplay.
"""

import logging
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import psycopg

from machincast_color_the_shows import queries

log = logging.getLogger(__name__)

LIFETIME = 30.0
"""Secondes pendant lesquelles la palette répond sans relire la base."""


@dataclass(frozen=True)
class Colours:
	genres: dict[int, tuple[str, str]] = field(default_factory=dict)
	"""Le nom et la couleur de chaque genre."""
	priorities: dict[str, str] = field(default_factory=dict)
	events: dict[int, int] = field(default_factory=dict)
	"""Le genre de chaque événement qui en a un."""


class Palette:
	def __init__(self, connect: Callable[[], queries.Connection], clock: Callable[[], float] = time.monotonic) -> None:
		self.connect = connect
		self.clock = clock
		self.colours = Colours()
		self._read_at: float | None = None
		self._lock = threading.Lock()

	def reload(self) -> None:
		"""Relit la base ; injoignable, la palette garde ce qu'elle avait, et réessaie à sa prochaine réponse."""
		with self._lock:
			self._read_at = self.clock()
			try:
				with self.connect() as connection:
					found = Colours(
						genres=_by_identifier(queries.genres(connection)),
						priorities=queries.priorities(connection),
						events=queries.event_genres(connection),
					)
			except psycopg.Error as error:
				log.error("color_the_shows: colours unreadable: %s", error)
				self._read_at = None
				return
			self.colours = found

	def forget(self) -> None:
		"""La prochaine réponse relit la base : un événement, ou les réglages, viennent d'être enregistrés."""
		self._read_at = None

	def answer(self, data: Mapping[str, Any]) -> str | None:
		"""La couleur de l'événement, ou de la priorité ; None pour laisser celle de MachinCast."""
		if (self._read_at is None) or (self.clock() - self._read_at >= LIFETIME):
			self.reload()
		colours = self.colours
		event = data.get("event")
		if event is not None:
			genre = colours.events.get(int(event))
			if (genre is not None) and (genre in colours.genres):
				return colours.genres[genre][1]
		priority = data.get("priority")
		if priority is None:
			return None
		return colours.priorities.get(str(priority))


def _by_identifier(found: list[tuple[int, str, str]]) -> dict[int, tuple[str, str]]:
	genres = {}
	for identifier, name, colour in found:
		genres[identifier] = (name, colour)
	return genres
