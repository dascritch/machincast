"""Scénarios des emoji d'intention des boutons et des menus (https://github.com/dascritch/machincast/issues/294).

Les étapes de la fenêtre et de ses fiches sont dans tests/interface_steps.py ; les menus contextuels et les questions
sont vérifiés par leurs propres scénarios (selection_multiple, dialogues).
"""

from PySide6.QtWidgets import QPushButton
from pytest_bdd import parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.interface import groups
from machincast.interface.intents import without_intent
from tests.interface_steps import NAME, TABLES, Connection, Context, identifier, opened_card, window

scenarios("intents.feature")

CATEGORIES = {
	"le sonore": "sound",
	"la banque": "bank",
	"la séquence": "sequence",
	"l'événement": "event",
	"le feed": "feed",
}
VERBS = ("Ajouter", "Retirer", "Supprimer")


@when(parsers.re(r"j'ouvre la fiche de (?P<category>.+) « (?P<name>[^»]+) » par son identifiant"))
def open_by_identifier(interface: Context, empty_database: Connection, qtbot: QtBot, category: str, name: str) -> None:
	table, column = TABLES[category]
	window(interface)._open(CATEGORIES[category], identifier(empty_database, table, column, name), name)


@then(parsers.re(r"les boutons de la fiche qui ajoutent, retirent ou suppriment sont (?P<buttons>«.+)"))
def mark_buttons(interface: Context, buttons: str) -> None:
	texts = []
	for button in opened_card(interface).findChildren(QPushButton):
		texts.append(button.text())
	text_list = []
	for text in texts:
		if without_intent(text).startswith(VERBS):
			text_list.append(text)
	assert text_list == NAME.findall(buttons)


@then(
	parsers.re(r"l'action groupée « (?P<key>[^»]+) » s'intitule « (?P<title>[^»]+) », au bouton « (?P<button>[^»]+) »")
)
def grouped_action(key: str, title: str, button: str) -> None:
	action_list = []
	for candidate in groups.SOUNDS:
		if candidate.key == key:
			action_list.append(candidate)
	(action,) = action_list
	assert (action.title, action.button) == (title, button)
