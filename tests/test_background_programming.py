"""Scénarios du fil musical garanti (https://github.com/dascritch/machincast/issues/39).

Les étapes de la fenêtre, des listes, des fiches et de la suppression sont dans tests/interface_steps.py.
"""

from pytest_bdd import parsers, scenarios, then, when

from tests.interface_steps import NAME, Connection

scenarios("background_programming.feature")


@when("la base perd son dernier fil musical")
def lose(empty_database: Connection) -> None:
	empty_database.execute("DELETE FROM events WHERE priority = 'background_programming'")


@then(parsers.parse("le fil musical « {name} » est en base, permanent et sans élément"))
def permanent(empty_database: Connection, name: str) -> None:
	lines = empty_database.execute(
		"SELECT e.priority::text, e.starts_at, e.ends_at, e.recurrence_days::text[], e.public_name, e.hide_metadata,"
		" (SELECT count(*) FROM event_items x WHERE x.event_id = e.id) FROM events e"
		" WHERE e.internal_name = %s",
		(name,),
	).fetchall()
	assert lines == [("background_programming", None, None, [], None, None, 0)]


@then(parsers.re(r"les fils musicaux en base sont (?P<names>aucun|«.+)"))
def feeds(empty_database: Connection, names: str) -> None:
	lines = empty_database.execute(
		"SELECT internal_name FROM events WHERE priority = 'background_programming' AND deleted_at IS NULL"
		" ORDER BY internal_name"
	).fetchall()
	name_list = []
	for (name,) in lines:
		name_list.append(str(name))
	assert name_list == NAME.findall(names)
