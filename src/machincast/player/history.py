"""Historique de diffusion, en base ou en mémoire (https://github.com/dascritch/machincast/issues/21).

Tout ce que le binaire lecture lit dans l'airplay pour décider (compteurs de lectures, cycles des banques, position
dans les listes), et tout ce qu'il y écrit (passages, log, expirations), passe par un Historique :

- HistoryInDatabase (IN_DATABASE), pour la diffusion : il lit et écrit la base, par machincast.player.saving et
  machincast.player.expiry ;
- SimulatedHistory (machincast.player.simulation), pour la simulation : il lit la base sans jamais y écrire, et tient
  en mémoire les passages, le log et les expirations simulés, dont ses lectures tiennent compte ;
- HistoryInPlayback et PlannedHistory, pour anticiper une décision ou prévoir les sonores à venir : ils lisent
  l'historique de la diffusion sans jamais y écrire, le second en y ajoutant des passages prévus.

Les deux donnent les mêmes réponses pour un même historique : la logique de lecture est la même en diffusion et en
simulation.
"""

import uuid
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import integer_or_none
from machincast.i18n import N_
from machincast.player import saving
from machincast.player.expiry import Expiry, expire
from machincast.player.saving import Play

Connection = psycopg.Connection[TupleRow]


@dataclass(frozen=True)
class LastPlay:
	"""Le passage le plus récent de tout l'historique, et la banque qui l'a fourni."""

	id: uuid.UUID
	bank: int | None
	"""None pour un sonore placé directement dans un événement."""
	start: datetime | None = None
	event: int | None = None
	item: int | None = None
	"""Élément de la liste de l'événement qui l'a fait jouer."""
	item_sequence: int | None = None
	"""Élément de la séquence qui l'a fait jouer (https://github.com/dascritch/machincast/issues/99)."""


class History(Protocol):
	def plays(self, connection: Connection, sounds: Collection[int]) -> dict[int, int]:
		"""Passages de chaque sonore (lignes de début), sur tout l'historique, quelle que soit la banque."""
		...

	def played_via_bank(self, connection: Connection, bank: int) -> list[int]:
		"""Sonores joués via la banque, du passage le plus récent au plus ancien."""
		...

	def last_item(self, connection: Connection, event: int, since: datetime | None) -> int | None:
		"""Élément de l'événement joué en dernier, depuis cet instant s'il est donné."""
		...

	def last_play(self, connection: Connection) -> LastPlay | None:
		"""Passage le plus récent, tous événements confondus ; None si l'historique est vide."""
		...

	def begin_play(
		self,
		connection: Connection,
		sound: int,
		bank: int | None,
		event: int | None,
		item: int | None,
		instant: datetime,
		sequence: int | None = None,
		item_sequence: int | None = None,
		lender: int | None = None,
	) -> Play: ...

	def finish_play(
		self,
		connection: Connection,
		play: Play,
		instant: datetime,
		cut: bool = False,
		error: str | None = None,
		kind: str = N_("interrupted playback"),
	) -> None: ...

	def record(
		self,
		connection: Connection,
		level: str,
		kind: str,
		message: str,
		instant: datetime | None = None,
		sound: int | None = None,
		bank: int | None = None,
		event: int | None = None,
	) -> None: ...

	def expire(self, connection: Connection, instant: datetime, sound: int | None = None) -> list[Expiry]: ...


@dataclass(frozen=True)
class HistoryInPlayback:
	"""Un historique qui lit celui qu'il enveloppe, sans jamais rien écrire : pour anticiper une décision sans en
	laisser de trace (https://github.com/dascritch/machincast/issues/169)."""

	source: History

	def plays(self, connection: Connection, sounds: Collection[int]) -> dict[int, int]:
		return self.source.plays(connection, sounds)

	def played_via_bank(self, connection: Connection, bank: int) -> list[int]:
		return self.source.played_via_bank(connection, bank)

	def last_item(self, connection: Connection, event: int, since: datetime | None) -> int | None:
		return self.source.last_item(connection, event, since)

	def last_play(self, connection: Connection) -> LastPlay | None:
		return self.source.last_play(connection)

	def begin_play(
		self,
		connection: Connection,
		sound: int,
		bank: int | None,
		event: int | None,
		item: int | None,
		instant: datetime,
		sequence: int | None = None,
		item_sequence: int | None = None,
		lender: int | None = None,
	) -> Play:
		raise AssertionError("une anticipation ne commence aucun passage")

	def finish_play(
		self,
		connection: Connection,
		play: Play,
		instant: datetime,
		cut: bool = False,
		error: str | None = None,
		kind: str = N_("interrupted playback"),
	) -> None:
		raise AssertionError("une anticipation ne termine aucun passage")

	def record(
		self,
		connection: Connection,
		level: str,
		kind: str,
		message: str,
		instant: datetime | None = None,
		sound: int | None = None,
		bank: int | None = None,
		event: int | None = None,
	) -> None:
		"""Rien n'est consigné : ce sera fait quand la décision sera prise pour de bon."""

	def expire(self, connection: Connection, instant: datetime, sound: int | None = None) -> list[Expiry]:
		return []


@dataclass(frozen=True)
class PlannedHistory(HistoryInPlayback):
	"""Un historique qui lit celui qu'il enveloppe, suivi des passages prévus, sans jamais rien écrire : pour prévoir
	les sonores à venir (https://github.com/dascritch/machincast/issues/228). Les passages prévus, du plus ancien au
	plus récent, comptent comme s'ils avaient été joués ; la liste s'allonge au fil de la prévision. Ce que les
	décisions consigneraient est gardé dans consignes, sans heure : la diffusion le consigne quand le sonore prévu
	devient le prochain."""

	planned_list: list[Play] = field(default_factory=list)
	recorded_list: list[dict[str, Any]] = field(default_factory=list)

	def record(
		self,
		connection: Connection,
		level: str,
		kind: str,
		message: str,
		instant: datetime | None = None,
		sound: int | None = None,
		bank: int | None = None,
		event: int | None = None,
	) -> None:
		self.recorded_list.append(
			{
				"level": level,
				"kind": kind,
				"message": message,
				"sound": sound,
				"bank": bank,
				"event": event,
			}
		)

	def plays(self, connection: Connection, sounds: Collection[int]) -> dict[int, int]:
		counts = self.source.plays(connection, sounds)
		for play in self.planned_list:
			if play.sound in counts:
				counts[play.sound] += 1
		return counts

	def played_via_bank(self, connection: Connection, bank: int) -> list[int]:
		planned_list = []
		for play in reversed(self.planned_list):
			if play.bank == bank:
				planned_list.append(play.sound)
		return planned_list + self.source.played_via_bank(connection, bank)

	def last_item(self, connection: Connection, event: int, since: datetime | None) -> int | None:
		for play in reversed(self.planned_list):
			if (play.event == event) and ((since is None) or (play.start >= since)):
				return play.item
		return self.source.last_item(connection, event, since)

	def last_play(self, connection: Connection) -> LastPlay | None:
		if not self.planned_list:
			return self.source.last_play(connection)
		play = self.planned_list[-1]
		return LastPlay(play.id, play.bank, play.start, play.event, play.item, play.item_sequence)


class HistoryInDatabase:
	"""L'airplay et le log de la base, avec les droits de la lecture."""

	def plays(self, connection: Connection, sounds: Collection[int]) -> dict[int, int]:
		lines = connection.execute(
			"SELECT sound_id, count(*) FROM airplay WHERE line_type = 'start' AND sound_id = ANY(%s) GROUP BY sound_id",
			(list(sounds),),
		).fetchall()
		counts = {}
		for sound, count in lines:
			counts[int(str(sound))] = int(str(count))
		plays = {}
		for wanted in sounds:
			plays[wanted] = counts.get(wanted, 0)
		return plays

	def played_via_bank(self, connection: Connection, bank: int) -> list[int]:
		lines = connection.execute(
			"SELECT sound_id FROM airplay WHERE bank_id = %s AND line_type = 'start' AND sound_id IS NOT NULL"
			" ORDER BY logged_at DESC, id DESC",
			(bank,),
		).fetchall()
		played_via_bank = []
		for line in lines:
			played_via_bank.append(int(str(line[0])))
		return played_via_bank

	def last_item(self, connection: Connection, event: int, since: datetime | None) -> int | None:
		line = connection.execute(
			"SELECT event_item_id FROM airplay WHERE event_id = %s AND line_type = 'start'"
			" AND (%s::timestamptz IS NULL OR logged_at >= %s::timestamptz)"
			" ORDER BY logged_at DESC, id DESC LIMIT 1",
			(event, since, since),
		).fetchone()
		if (line is None) or (line[0] is None):
			return None
		return int(str(line[0]))

	def last_play(self, connection: Connection) -> LastPlay | None:
		line = connection.execute(
			"SELECT play_id, bank_id, logged_at, event_id, event_item_id, sequence_item_id FROM airplay"
			" WHERE line_type = 'start' ORDER BY logged_at DESC, id DESC LIMIT 1"
		).fetchone()
		if line is None:
			return None
		play, bank, start, event, item, item_sequence = line
		if isinstance(start, datetime):
			known_start = start
		else:
			known_start = None
		return LastPlay(
			uuid.UUID(str(play)),
			integer_or_none(bank),
			known_start,
			integer_or_none(event),
			integer_or_none(item),
			integer_or_none(item_sequence),
		)

	def begin_play(
		self,
		connection: Connection,
		sound: int,
		bank: int | None,
		event: int | None,
		item: int | None,
		instant: datetime,
		sequence: int | None = None,
		item_sequence: int | None = None,
		lender: int | None = None,
	) -> Play:
		return saving.begin_play(connection, sound, bank, event, item, instant, sequence, item_sequence, lender)

	def finish_play(
		self,
		connection: Connection,
		play: Play,
		instant: datetime,
		cut: bool = False,
		error: str | None = None,
		kind: str = N_("interrupted playback"),
	) -> None:
		saving.finish_play(connection, play, instant, cut=cut, error=error, kind=kind)

	def record(
		self,
		connection: Connection,
		level: str,
		kind: str,
		message: str,
		instant: datetime | None = None,
		sound: int | None = None,
		bank: int | None = None,
		event: int | None = None,
	) -> None:
		saving.record(connection, level, kind, message, instant, sound, bank, event)

	def expire(self, connection: Connection, instant: datetime, sound: int | None = None) -> list[Expiry]:
		return expire(connection, instant, sound)


IN_DATABASE: History = HistoryInDatabase()
"""Historique de la diffusion : la base."""
