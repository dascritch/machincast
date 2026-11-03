"""Scénarios de la session sautée annoncée par la fiche d'un événement
(https://github.com/dascritch/machincast/issues/295).

Les étapes de la fenêtre, de ses fiches, des sessions sautées et de la socket d'état sont dans
tests/interface_steps.py.
"""

from datetime import date, datetime

from PySide6.QtCore import QDateTime
from pytest_bdd import parsers, scenarios, then, when

from machincast.interface.event_card import ORANGE, EventCard
from tests.interface_steps import Connection, Context, opened_card

scenarios("event_card_skipped_session.feature")


def event_card(interface: Context) -> EventCard:
	card = opened_card(interface)
	assert isinstance(card, EventCard), card
	return card


@when(parsers.parse("je règle le début de la fiche de l'événement au « {start} »"))
def set_start(interface: Context, start: str) -> None:
	instant = datetime.fromisoformat(start).astimezone()
	event_card(interface).ui.start.setDateTime(QDateTime.fromSecsSinceEpoch(int(instant.timestamp())))


@when(parsers.parse("la session du {day} de « {name} » est rétablie en base"))
def restored_in_database(empty_database: Connection, day: str, name: str) -> None:
	"""Comme depuis le calendrier, ou depuis une autre fiche."""
	empty_database.execute(
		"DELETE FROM event_skips WHERE day = %s AND event_id = (SELECT id FROM events WHERE internal_name = %s)",
		(date.fromisoformat(day), name),
	)


@then(parsers.parse("la fiche annonce « {text} »"))
def announces(interface: Context, text: str) -> None:
	card = event_card(interface)
	assert card.skipped_session.isVisibleTo(card)
	assert card.session_text.text() == text


@then("la fiche n'annonce aucune session sautée")
def no_announced(interface: Context) -> None:
	card = event_card(interface)
	assert not card.skipped_session.isVisibleTo(card), card.session_text.text()


@then("l'annonce est sous l'erreur de la fiche, sur un liseret orange de 4 pixels")
def under_error(interface: Context) -> None:
	card = event_card(interface)
	arrangement = card.layout()
	assert arrangement is not None
	assert arrangement.indexOf(card.skipped_session) == arrangement.indexOf(card.error) + 1 == 1
	assert f"border: 4px solid {ORANGE}" in card.skipped_session.styleSheet()


@then(
	parsers.re(
		r"le bouton « Rétablir » de l'annonce est (?P<state>actif|inactif)(?:, avec l'infobulle « (?P<bubble>.+) »)?$"
	)
)
def button_reinstate(interface: Context, state: str, bubble: str | None) -> None:
	button = event_card(interface).reinstate_session
	assert button.isEnabled() is (state == "actif")
	if bubble is not None:
		assert button.toolTip() == bubble


@then(parsers.re(r"les sessions sautées de « (?P<name>[^»]+) » en base sont (?P<days>aucune|«.+)"))
def skipped_in_database(empty_database: Connection, name: str, days: str) -> None:
	lines = empty_database.execute(
		"SELECT s.day FROM event_skips s JOIN events e ON e.id = s.event_id WHERE e.internal_name = %s ORDER BY s.day",
		(name,),
	).fetchall()
	expected_list: list[date] = []
	if days != "aucune":
		expected_list = [date.fromisoformat(day) for day in days.strip("« »").split(" », « ")]
	assert [day for (day,) in lines] == expected_list


@then(parsers.parse("la fiche est modifiée, avec le nom interne « {name} »"))
def modified_with(interface: Context, name: str) -> None:
	card = event_card(interface)
	assert card.modified
	assert card.ui.internal_name.text() == name
