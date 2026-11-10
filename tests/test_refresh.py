"""Scénarios du rafraîchissement des onglets de l'interface (https://github.com/dascritch/machincast/issues/148).

Le rafraîchissement à l'ouverture d'un onglet : https://github.com/dascritch/machincast/issues/241. Les étapes de la
fenêtre, de sa barre de menus, des fiches et des fenêtres de dialogue sont dans
tests/interface_steps.py. Ce qu'un autre poste ou la diffusion change, le scénario l'écrit directement en base.
"""

import uuid
from datetime import datetime, time

from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from tests.interface_steps import Connection, Context, identifier, open_in, window

scenarios("refresh.feature")

TITLE = 4
"""Colonne du titre, dans la table de l'airplay de l'onglet Antenne."""


@when(parsers.parse("un autre poste ajoute la banque « {name} »"))
def add_bank(empty_database: Connection, name: str) -> None:
	empty_database.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential')", (name,))


@when(parsers.parse("un autre poste renomme la banque « {name} » en « {new} »"))
def rename_bank(empty_database: Connection, name: str, new: str) -> None:
	empty_database.execute("UPDATE banks SET internal_name = %s WHERE internal_name = %s", (new, name))


@when(parsers.parse("un autre poste efface la banque « {name} »"))
def erase_bank(empty_database: Connection, name: str) -> None:
	empty_database.execute("DELETE FROM banks WHERE internal_name = %s", (name,))


@when(parsers.parse("la diffusion note dans l'airplay le passage de « {title} » à {hour}"))
def note_play(interface: Context, empty_database: Connection, title: str, hour: str) -> None:
	assert interface.clock is not None
	start = datetime.combine(interface.clock.now().date(), time.fromisoformat(hour))
	empty_database.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, event_id, title)"
		" VALUES (%s, 'start', %s, %s, %s, %s)",
		(
			uuid.uuid4(),
			start.astimezone(),
			identifier(empty_database, "sounds", "title", title),
			identifier(empty_database, "events", "internal_name", "Continue"),
			title,
		),
	)


@then("l'airplay de l'onglet Antenne ne montre rien")
def empty_airplay(interface: Context) -> None:
	assert window(interface).home.airplay_model.rowCount() == 0


@then(parsers.parse("l'airplay de l'onglet Antenne montre « {title} »"))
def airplay(interface: Context, title: str) -> None:
	model = window(interface).home.airplay_model
	line_list = []
	for line in range(model.rowCount()):
		line_list.append(model.item(line, TITLE).text())
	assert line_list == [title]


@when(parsers.parse("je double-clique sur « {title} » dans l'airplay de l'onglet Antenne"))
def open_since_airplay(interface: Context, qtbot: QtBot, title: str) -> None:
	open_in(qtbot, window(interface).home.ui.table_airplay, title)


@then(parsers.parse("le nom interne de la fiche est « {name} »"))
def internal_name(interface: Context, name: str) -> None:
	card = window(interface).ui.tabs.currentWidget()
	assert card.ui.internal_name.text() == name  # type: ignore[attr-defined]
