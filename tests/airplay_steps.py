"""Étapes partagées des scénarios de l'interface : Airplay (https://github.com/dascritch/machincast/issues/244).

Chargé comme greffon pytest par tests/conftest.py (https://github.com/dascritch/machincast/issues/444 : découpé de
tests/interface_steps.py, par domaine).
"""

import uuid
from datetime import datetime

import pytest
import tomlkit
from pytest_bdd import given, parsers, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import preferences
from tests.interface_steps import TABLES, Connection, Context, configuration_file, window
from tests.waiting import settle

# ─── Airplay (https://github.com/dascritch/machincast/issues/244) ───

AIRPLAY_DAY = "2026-10-16"
"""Le jour des passages des scénarios de l'airplay, quand seule leur heure est donnée."""


def hour(text: str) -> datetime:
	return datetime.fromisoformat(text).astimezone()


def hour_or_none(text: str) -> datetime | None:
	if text == "":
		return None
	return hour(text)


def a(schedule: str) -> datetime:
	return hour(f"{AIRPLAY_DAY} {schedule}")


def reference(database: Connection, table: str, name: str) -> int | None:
	"""Identifiant de l'entrée de ce nom interne, créée au besoin ; None pour un nom vide."""
	if not name:
		return None
	values = {
		"events": ", priority) VALUES (%s, 'background_programming')",
		"banks": ", mode) VALUES (%s, 'sequential')",
	}
	line = database.execute(f"SELECT id FROM {table} WHERE internal_name = %s", (name,)).fetchone()
	if line is None:
		remainder = values.get(table, ") VALUES (%s)")
		line = database.execute(f"INSERT INTO {table} (internal_name{remainder} RETURNING id", (name,)).fetchone()
	assert line is not None
	return int(str(line[0]))


def insert_play(
	database: Connection,
	start: datetime,
	end: datetime | None,
	artist: str,
	title: str,
	event: str,
	sequence: str = "",
	bank: str = "",
	without_incident: str = "",
) -> None:
	location = f"/musique/{uuid.uuid4()}.flac"
	line = database.execute(
		"INSERT INTO sounds (type, location, artist, title) VALUES ('file', %s, %s, %s) RETURNING id",
		(location, (artist) or (None), title),
	).fetchone()
	assert line is not None
	references = (
		line[0],
		reference(database, "events", event),
		reference(database, "sequences", sequence),
		reference(database, "banks", bank),
	)
	play = uuid.uuid4()
	columns = "play_id, line_type, logged_at, sound_id, event_id, sequence_id, bank_id, artist, title, location"
	database.execute(
		f"INSERT INTO airplay ({columns}) VALUES (%s, 'start', %s, %s, %s, %s, %s, %s, %s, %s)",
		(play, start, *references, (artist) or (None), title, location),
	)
	if end is not None:
		database.execute(
			f"INSERT INTO airplay ({columns}, played_duration, without_incident)"
			" VALUES (%s, 'end', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
			(play, end, *references, (artist) or (None), title, location, end - start, without_incident == "oui"),
		)


@given("les passages dans l'airplay :")
def plays(empty_database: Connection, datatable: list[list[str]]) -> None:
	headers, *lines = datatable
	for values in lines:
		cells = []
		for v in values:
			cells.append(v.strip())
		line = dict(zip(headers, cells, strict=True))
		insert_play(
			empty_database,
			hour(line["starts_at"]),
			hour_or_none(line["ends_at"]),
			line["artist"],
			line["title"],
			line["event"],
			line["sequence"],
			line["bank"],
			line["without_incident"],
		)


@given("le masquage de tous les sonores et de tous les événements")
def hide(empty_database: Connection) -> None:
	empty_database.execute("UPDATE sounds SET hide_metadata = true")
	empty_database.execute("UPDATE events SET hide_metadata = true")


@when(parsers.parse("le passage de « {title} » commence dans l'airplay à {start}"))
def new_play(empty_database: Connection, title: str, start: str) -> None:
	insert_play(empty_database, a(start), None, "Radio", title, "Fil de jour")


@given(
	parsers.re(
		r"(?P<category>le sonore|la banque|la séquence|l'événement) « (?P<name>[^»]+) » est supprimée? depuis"
		r" l'interface"
	)
)
@when(
	parsers.re(
		r"(?P<category>le sonore|la banque|la séquence|l'événement) « (?P<name>[^»]+) » est supprimée? depuis"
		r" l'interface"
	)
)
def deleted_since_interface(empty_database: Connection, category: str, name: str) -> None:
	"""Comme « Supprimer… » de sa fiche, sans ses retraits des listes
	(https://github.com/dascritch/machincast/issues/267)."""
	table, column = TABLES[category]
	modified = empty_database.execute(
		f"UPDATE {table} SET deleted_at = clock_timestamp() WHERE {column} = %s RETURNING id",
		(name,),
	).fetchall()
	assert len(modified) == 1, modified


@then(parsers.parse("le fichier « {path} » a {count:d} sonores en base, dont {deleted_list:d} supprimé"))
def file_sounds(interface: Context, empty_database: Connection, path: str, count: int, deleted_list: int) -> None:
	lines = empty_database.execute(
		"SELECT deleted_at IS NOT NULL FROM sounds WHERE location = %s", (interface.path(path),)
	).fetchall()
	total = 0
	for (deleted,) in lines:
		if deleted:
			total += 1
	assert (len(lines), total) == (count, deleted_list), lines


@given(parsers.parse("les préférences seront réglées avec la durée de péremption de {days:d} jours"))
def adjusted_retention(interface: Context, days: int) -> None:
	interface.adjusted_retention = days


@given(parsers.parse("les fiches chargent leurs tableaux par {rows:d} lignes"))
def table_rows(monkeypatch: pytest.MonkeyPatch, rows: int) -> None:
	"""Quelle que soit la configuration que la fenêtre lit à son ouverture (https://github.com/dascritch/machincast/issues/383)."""
	monkeypatch.setattr(preferences, "table_rows", lambda: rows)


@given(parsers.parse("je note les versions en base des éléments de la séquence « {name} »"))
@when(parsers.parse("je note les versions en base des éléments de la séquence « {name} »"))
def note_versions(interface: Context, empty_database: Connection, name: str) -> None:
	"""xmin change à chaque UPDATE d'une ligne : une liste réécrite change de versions."""
	interface.versions = _versions(empty_database, name)


@then(parsers.parse("les éléments de la séquence « {name} » n'ont pas été réécrits en base"))
def not_rewritten(interface: Context, empty_database: Connection, name: str) -> None:
	assert _versions(empty_database, name) == interface.versions


def _versions(connection: Connection, name: str) -> list[str]:
	versions = []
	for (xmin,) in connection.execute(
		"SELECT e.xmin::text FROM sequence_items e JOIN sequences q ON q.id = e.sequence_id"
		" WHERE q.internal_name = %s ORDER BY e.position",
		(name,),
	):
		versions.append(str(xmin))
	return versions


@then(parsers.parse("la liste des éléments de la fiche a pour titre « {title} »"))
def items_title(interface: Context, title: str) -> None:
	opened = window(interface).ui.tabs.currentWidget()
	assert opened.ui.item_group.title() == title  # type: ignore[attr-defined]


@when("je descends au bas de la liste des éléments de la fiche")
def items_to_bottom(interface: Context, qtbot: QtBot) -> None:
	opened = window(interface).ui.tabs.currentWidget()
	bar = opened.ui.items.verticalScrollBar()  # type: ignore[attr-defined]
	bar.setValue(bar.maximum())
	settle(qtbot)


@given(parsers.parse("les préférences seront réglées avec {rows:d} lignes chargées à la fois"))
def adjusted_table_rows(interface: Context, rows: int) -> None:
	interface.adjusted_table_rows = rows


@given(parsers.parse("la durée de péremption du fichier de configuration de l'interface est de {days:d} jours"))
def file_retention(interface: Context, days: int) -> None:
	"""https://github.com/dascritch/machincast/issues/268"""
	path = configuration_file(interface)
	document = tomlkit.parse(path.read_text(encoding="utf-8"))
	database = document["database"]
	assert isinstance(database, tomlkit.items.Table)
	database["retention"] = days
	path.write_text(tomlkit.dumps(document), encoding="utf-8")
