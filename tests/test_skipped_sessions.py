"""Scénarios des sessions sautées, à la diffusion (https://github.com/dascritch/machincast/issues/273).

La diffusion tourne sur le moteur simulé, qui suit l'horloge du binaire. Les étapes partagées de la diffusion sont dans
tests/broadcast_steps.py ; une demande arrive par une vraie socket d'état, comme dans test_interruption.py.
"""

from datetime import date

import psycopg
from pytest_bdd import given, parsers, scenarios

from machincast.player.grid import DAY_NAMES, DAYS

scenarios("skipped_sessions.feature")

Connection = psycopg.Connection[tuple[object, ...]]


@given(parsers.re(r"l'émission « (?P<name>[^»]+) » revient (?P<days>chaque .+)"))
def recurrence(empty_database: Connection, name: str, days: str) -> None:
	names = []
	for day in days.replace("chaque", "").split(" et "):
		names.append(DAYS[DAY_NAMES.index(day.strip())])
	empty_database.execute("UPDATE events SET recurrence_days = %s WHERE internal_name = %s", (names, name))


@given(parsers.parse("la session du {day} de l'événement « {name} » est rétablie"))
def reinstate(empty_database: Connection, day: str, name: str) -> None:
	empty_database.execute(
		"DELETE FROM event_skips WHERE day = %s AND event_id = (SELECT id FROM events WHERE internal_name = %s)",
		(date.fromisoformat(day), name),
	)
