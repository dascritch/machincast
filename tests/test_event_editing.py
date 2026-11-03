"""Scénarios d'un événement modifié pendant la diffusion (https://github.com/dascritch/machincast/issues/266).

La diffusion tourne sur le moteur simulé, qui suit l'horloge du binaire. Les étapes partagées de la diffusion, dont la
demande de relire la grille sur la socket d'état, sont dans tests/broadcast_steps.py ; les modifications se font en
base, comme les écrirait la fiche de l'événement.
"""

import psycopg
from pytest_bdd import given, parsers, scenarios, when

from machincast.player.grid import DAY_NAMES, DAYS
from tests.broadcast_steps import hour

scenarios("event_editing.feature")

Connection = psycopg.Connection[tuple[object, ...]]


@when(parsers.parse("l'émission « {name} » est déplacée de {start} à {end}"))
def move(empty_database: Connection, name: str, start: str, end: str) -> None:
	modified_list = empty_database.execute(
		"UPDATE events SET starts_at = %s, ends_at = %s WHERE internal_name = %s",
		(hour(f"2026-10-14 {start}"), hour(f"2026-10-14 {end}"), name),
	).rowcount
	assert modified_list == 1


@when(parsers.parse("l'événement « {name} » est renommé « {new} », avec un nom public et un masquage"))
def rename(empty_database: Connection, name: str, new: str) -> None:
	"""Ce qui ne règle pas l'antenne ; sa date de modification avance, comme à chaque enregistrement."""
	modified_list = empty_database.execute(
		"UPDATE events SET internal_name = %s, public_name = 'Le jour', hide_metadata = true WHERE internal_name = %s",
		(new, name),
	).rowcount
	assert modified_list == 1


@when(parsers.parse("l'émission « {name} » finit à {end}"))
def finish(empty_database: Connection, name: str, end: str) -> None:
	modified_list = empty_database.execute(
		"UPDATE events SET ends_at = %s WHERE internal_name = %s", (hour(f"2026-10-14 {end}"), name)
	).rowcount
	assert modified_list == 1


@when(parsers.parse("l'événement « {name} » passe en fil musical"))
def in_background_programming(empty_database: Connection, name: str) -> None:
	modified_list = empty_database.execute(
		"UPDATE events SET priority = 'background_programming' WHERE internal_name = %s", (name,)
	).rowcount
	assert modified_list == 1


@given(parsers.parse("l'émission « {name} » a eu lieu la veille"))
def the_standby(empty_database: Connection, name: str) -> None:
	modified_list = empty_database.execute(
		"UPDATE events SET starts_at = starts_at - interval '1 day', ends_at = ends_at - interval '1 day'"
		" WHERE internal_name = %s",
		(name,),
	).rowcount
	assert modified_list == 1


@when(parsers.parse("l'événement « {name} » revient aussi le {day}"))
def come_back(empty_database: Connection, name: str, day: str) -> None:
	modified_list = empty_database.execute(
		"UPDATE events SET recurrence_days = array_append(recurrence_days, %s::weekday) WHERE internal_name = %s",
		(DAYS[DAY_NAMES.index(day)], name),
	).rowcount
	assert modified_list == 1
