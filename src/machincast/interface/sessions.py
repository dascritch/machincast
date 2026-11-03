"""Sessions sautées d'un événement (https://github.com/dascritch/machincast/issues/273), communes au calendrier et à la
fiche d'un événement (https://github.com/dascritch/machincast/issues/295).

Une session sautée se note en base par le jour où elle commence (event_skips). Elle se rétablit tant qu'elle n'a
pas commencé, et qu'aucun événement de même priorité n'a pris sa place (chevauchee). Le jour seul compte : une session
sautée le reste quand l'heure de l'événement change, et la fiche de l'événement l'annonce (next_skipped).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import TupleRow

from machincast.player.grid import NEVER, Event, overlap, read_grid, sessions, wall_hour

Connection = psycopg.Connection[TupleRow]
ONE_DAY = timedelta(days=1)


@dataclass(frozen=True)
class Session:
	"""Une session d'un événement, en heure murale du poste ; sans fin, elle dure jusqu'au bout de sa liste."""

	event: Event
	start: datetime
	end: datetime | None


def past(session: Session, now: datetime) -> bool:
	"""Finie ; une session sans fin l'est le lendemain de son début."""
	moment = wall_hour(now)
	if session.end is None:
		return session.start.date() < moment.date()
	return session.end <= moment


def started(session: Session, now: datetime) -> bool:
	return session.start <= wall_hour(now)


def next_skipped(event: Event, now: datetime) -> Session | None:
	"""La première session sautée de l'événement qui n'est pas encore passée : en cours, ou à venir. Un saut dont le
	jour n'a plus de session, après un changement des jours de l'événement, ne compte pas."""
	for day in sorted(event.skipped_list):
		for start, end in sessions(event, day, day + ONE_DAY):
			session = Session(event, start, end)
			if not past(session, now):
				return session
	return None


def overlapped(connection: Connection, session: Session, now: datetime) -> tuple[Event, datetime] | None:
	"""L'événement de même priorité qui a pris la place de la session, et le premier instant commun ; None si elle
	peut revenir. À appeler dans une transaction."""
	only = Event(
		id=session.event.id,
		name=session.event.name,
		priority=session.event.priority,
		start=session.start,
		end=session.end,
		days=frozenset(),
		modified_at=NEVER,
	)
	others = [other for other in read_grid(connection) if other.id != session.event.id]
	return overlap(only, others, since=wall_hour(now))


def reinstate(connection: Connection, session: Session) -> None:
	"""La session joue de nouveau. À appeler dans une transaction."""
	connection.execute(
		"DELETE FROM event_skips WHERE event_id = %s AND day = %s",
		(session.event.id, session.start.date()),
	)
