"""Les fixtures et les étapes communes des scénarios du cartouchier (https://github.com/dascritch/machincast/issues/512).

Ils reprennent celles de MachinCast (tests/conftest.py), sur la même base de test, où les migrations du cartouchier
s'appliquent au premier scénario qui la demande, et s'annulent à la fin de la session : les scénarios du cœur ne
voient jamais sa table.
"""

import sys
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from pytest_bdd import given, parsers

ROOT = Path(__file__).resolve().parents[3]
PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PLUGIN / "src"))

from tests.database_fixtures import sample_database_parameters  # noqa: E402

from machincast.database import url_yoyo  # noqa: E402
from machincast.plugins import schema  # noqa: E402

pytest_plugins = ["tests.conftest"]

Connection = psycopg.Connection[tuple[object, ...]]

_applied = False


def _url() -> str:
	return url_yoyo(*sample_database_parameters())


@pytest.fixture
def base(empty_database: Connection) -> Connection:
	"""La base de test vide, avec la table du cartouchier."""
	global _applied
	schema.apply(_url(), PLUGIN)
	_applied = True
	return empty_database


@pytest.fixture(scope="session", autouse=True)
def cartwall_cancelled() -> Iterator[None]:
	"""Les migrations du cartouchier s'annulent à la fin de la session."""
	yield
	if _applied:
		schema.cancel(_url(), PLUGIN)


def identifier(connection: Connection, table: str, column: str, name: str) -> int:
	line = connection.execute(f"SELECT id FROM {table} WHERE {column} = %s", (name,)).fetchone()
	assert line is not None, name
	return int(str(line[0]))


@given(parsers.re(r"la banque « (?P<name>[^»]+) »(?P<marked>, marquée « ne pas répéter »)?$"))
def bank(base: Connection, name: str, marked: str | None) -> None:
	base.execute(
		"INSERT INTO banks (internal_name, mode, no_repeat) VALUES (%s, 'sequential', %s)", (name, marked is not None)
	)


@given(parsers.parse("la séquence « {name} »"))
def sequence(base: Connection, name: str) -> None:
	base.execute("INSERT INTO sequences (internal_name) VALUES (%s)", (name,))


@given(parsers.parse("l'événement de secours « {name} »"))
def fallback(base: Connection, name: str) -> None:
	base.execute("INSERT INTO events (internal_name, priority) VALUES (%s, 'fallback')", (name,))


@given(parsers.parse("le feed « {name} »"))
def feed(base: Connection, name: str) -> None:
	base.execute("INSERT INTO feeds (name, url) VALUES (%s, 'https://flux.radio.lan/studio')", (name,))


TARGETS = {
	"insert_bank": ("bank_id", "banks", "internal_name"),
	"insert_sequence": ("sequence_id", "sequences", "internal_name"),
	"cut_by_fallback": ("event_id", "events", "internal_name"),
	"cut_by_feed": ("feed_id", "feeds", "name"),
}


@given(parsers.parse("les boutons de « {user} » :"))
def buttons(base: Connection, user: str, datatable: list[list[str]]) -> None:
	account = identifier(base, "api_users", "name", user)
	for position, row in enumerate(datatable[1:], start=1):
		label, colour, action, target, blank = (row[0].strip(), row[1].strip(), row[2].strip(), row[3], row[4])
		columns = {"sequence_id": None, "bank_id": None, "event_id": None, "feed_id": None}
		found = TARGETS.get(action)
		if found is not None:
			column, table, name = found
			columns[column] = identifier(base, table, name, target.strip())
		base.execute(
			"INSERT INTO cartwall__buttons (api_user_id, position, label, colour, action, sequence_id, bank_id, event_id,"
			" feed_id, blank) VALUES (%(account)s, %(position)s, %(label)s, %(colour)s, %(action)s, %(sequence_id)s,"
			" %(bank_id)s, %(event_id)s, %(feed_id)s, NULLIF(%(blank)s, ''))",
			{
				**columns,
				"account": account,
				"position": position,
				"label": label,
				"colour": colour,
				"action": action,
				"blank": blank.strip(),
			},
		)


def stored(connection: Connection, user: str) -> list[list[str]]:
	"""Les boutons du compte en base, dans l'ordre, comme les tableaux des scénarios."""
	lines = connection.execute(
		"SELECT b.label, b.colour, b.action, COALESCE(s.internal_name, k.internal_name, e.internal_name, f.name, ''),"
		" COALESCE(b.blank, '') FROM cartwall__buttons b JOIN api_users u ON u.id = b.api_user_id"
		" LEFT JOIN sequences s ON s.id = b.sequence_id LEFT JOIN banks k ON k.id = b.bank_id"
		" LEFT JOIN events e ON e.id = b.event_id LEFT JOIN feeds f ON f.id = b.feed_id"
		" WHERE u.name = %s ORDER BY b.position",
		(user,),
	).fetchall()
	found = []
	for line in lines:
		row = []
		for value in line:
			row.append(str(value))
		found.append(row)
	return found
