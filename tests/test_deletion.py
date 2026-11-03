"""Scénarios de la suppression d'un élément depuis sa fiche (https://github.com/dascritch/machincast/issues/33).

Les étapes de la fenêtre, des listes, des fiches et des fenêtres de dialogue sont dans tests/interface_steps.py ;
celles-ci suppriment, et lisent la base de test et le répertoire du scénario.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QPushButton
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import search
from machincast.interface.choice import Choice
from machincast.interface.lists import SOUNDS
from tests.interface_steps import (
	NAME,
	Connection,
	Context,
	deletion_questions,
	identifier,
	lines,
	opened_card,
)

scenarios("deletion.feature")

NAMES = "COALESCE(s.title, b.internal_name, q.internal_name)"
LISTS = {
	"la banque": (
		"banks",
		f"SELECT {NAMES} FROM bank_sounds e JOIN sounds s ON s.id = e.sound_id"
		" LEFT JOIN banks b ON false LEFT JOIN sequences q ON false WHERE e.bank_id = %s ORDER BY e.position",
	),
	"la séquence": (
		"sequences",
		f"SELECT {NAMES} FROM sequence_items e LEFT JOIN sounds s ON s.id = e.sound_id"
		" LEFT JOIN banks b ON b.id = e.bank_id LEFT JOIN sequences q ON false"
		" WHERE e.sequence_id = %s ORDER BY e.position",
	),
	"l'événement": (
		"events",
		f"SELECT {NAMES} FROM event_items e LEFT JOIN sounds s ON s.id = e.sound_id"
		" LEFT JOIN banks b ON b.id = e.bank_id LEFT JOIN sequences q ON q.id = e.sequence_id"
		" WHERE e.event_id = %s ORDER BY e.position",
	),
}
"""La table de la banque, de la séquence ou de l'événement, et la requête des noms de ses éléments, dans l'ordre."""


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("« {title} » qui est passé à l'antenne pendant « {event} »"))
def play(empty_database: Connection, title: str, event: str) -> None:
	"""Le début d'un passage dans l'historique de diffusion, qui recopie l'emplacement, l'artiste et le titre."""
	empty_database.execute(
		"INSERT INTO airplay (play_id, line_type, sound_id, event_id, location, artist, title)"
		" SELECT gen_random_uuid(), 'start', s.id, %s, s.location, s.artist, s.title FROM sounds s"
		" WHERE s.title = %s",
		(identifier(empty_database, "events", "internal_name", event), title),
	)


# ─── Quand ─────────────────────────────────────────────────


@then("la fiche signale une suppression impossible")
def impossible_deletion(interface: Context) -> None:
	"""En haut de la fiche, comme toute erreur (https://github.com/dascritch/machincast/issues/270)."""
	card = opened_card(interface)
	assert card.error.isVisibleTo(card)
	assert card.error.text().startswith("Suppression impossible : ")


@then("seule la question de suppression a été posée")
def only_question(interface: Context) -> None:
	assert len(interface.questions) == 1, interface.questions
	assert interface.questions == deletion_questions(interface)


@then(
	parsers.re(
		r"la liste en base de (?P<category>la banque|la séquence|l'événement) « (?P<name>[^»]+) » est"
		r" (?P<names>rien|«.+)"
	)
)
def list_in_database(empty_database: Connection, category: str, name: str, names: str) -> None:
	"""Les éléments, dans l'ordre : un sonore par son titre, une banque ou une séquence par son nom."""
	table, query = LISTS[category]
	lines = empty_database.execute(query, (identifier(empty_database, table, "internal_name", name),)).fetchall()
	assert [str(line[0]) for line in lines] == NAME.findall(names)


@then(parsers.parse("l'historique de diffusion garde le passage de « {sound} », à l'emplacement « {location} »"))
def kept_play(interface: Context, empty_database: Connection, sound: str, location: str) -> None:
	lines = empty_database.execute("SELECT artist, title, location FROM airplay").fetchall()
	artist, title = sound.split(" – ")
	assert lines == [(artist, title, interface.path(location))]


@then("les fichiers du scénario sont intacts")
def intact_list(interface: Context) -> None:
	assert interface.files != []
	assert {file: file.read_bytes() for file in interface.files} == interface.files


@then(parsers.parse("le dossier « {folder} » est toujours là"))
def folder_there(interface: Context, folder: str) -> None:
	assert Path(interface.path(folder)).is_dir()


@then(parsers.parse("le stream « {title} » n'a plus d'événement de secours"))
def without_fallback(empty_database: Connection, title: str) -> None:
	lines = empty_database.execute("SELECT fallback_event_id FROM sounds WHERE title = %s", (title,)).fetchall()
	assert lines == [(None,)]


# ─── Suppression différée (https://github.com/dascritch/machincast/issues/267) ───


@when(parsers.parse("une autre banque « {name} » est créée en base"))
def other_bank(empty_database: Connection, name: str) -> None:
	empty_database.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, 'random')", (name,))


@then(parsers.re(r"les champs de la fiche (?P<no>ne )?se modifient(?: pas)?"))
def fields(interface: Context, no: str | None) -> None:
	"""Les champs de saisie ; la case et les boutons de la fiche en lecture seule, sauf « Restaurer »."""
	card = opened_card(interface)
	inputs = [field for field in card.findChildren(QLineEdit) if field.parent() is not None]
	assert inputs != []
	active_list = [field.objectName() for field in inputs if field.isEnabled()]
	if no is None:
		assert active_list != [], "aucun champ modifiable"
	else:
		assert active_list == [], active_list


@then(parsers.re(r"la fiche propose « (?P<yes>[^»]+) », pas « (?P<no>[^»]+) »"))
def offers(interface: Context, yes: str, no: str) -> None:
	texts = {button.text(): button for button in opened_card(interface).findChildren(QPushButton)}
	assert (yes in texts) and (texts[yes].isEnabled()), list(texts)
	assert no not in texts, list(texts)


@then(parsers.re(r"la liste montre les noms (?P<names>.+)"))
def shown_names(interface: Context, names: str) -> None:
	assert [line["Nom"] for line in lines(interface)] == NAME.findall(names), lines(interface)


@then(parsers.parse("la recherche de « {text} » ne trouve rien"))
def empty_search(interface: Context, text: str) -> None:
	assert interface.connection is not None
	found_list, count = search.find(interface.connection, text, 50)
	assert (found_list, count) == ([], 0), found_list


@then(parsers.parse("le choix des sonores d'une banque ne propose pas « {title} »"))
def choice_without(interface: Context, qtbot: QtBot, title: str) -> None:
	assert interface.connection is not None
	choice = Choice(SOUNDS, interface.connection)
	qtbot.addWidget(choice)
	model = choice.list_.table.model()
	column = [model.headerData(c, Qt.Orientation.Horizontal) for c in range(model.columnCount())].index("Titre")
	titles = [model.index(row, column).data() for row in range(model.rowCount())]
	assert titles != []
	assert title not in titles, titles
