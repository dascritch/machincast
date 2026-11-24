"""Scénarios de la banque en emoji (https://github.com/dascritch/machincast/issues/505).

Les banques sont en base de test ; le plugin s'abonne au point « interface.bank_card » des plugins du binaire
(machincast.plugins.active), que tests/conftest.py remet à vide après chaque scénario. La fiche de la banque est
ouverte seule, au rôle machincast_interface, à une heure fixe.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import machincast_bank_as_an_emoji
import psycopg
import pytest
from machincast_bank_as_an_emoji import names, picker, section
from machincast_bank_as_an_emoji.section import EmojiSection
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot
from tests.database_fixtures import sample_database_parameters

from conftest import PLUGIN
from machincast import plugins
from machincast.clock import FixedClock
from machincast.database import Role, open_connection
from machincast.interface.bank_card import BankCard

scenarios(str(PLUGIN / "tests" / "features" / "bank_as_an_emoji.feature"))

Connection = psycopg.Connection[tuple[object, ...]]
CLOCK = FixedClock(datetime(2026, 11, 24, 10, tzinfo=ZoneInfo("Europe/Paris")))


@dataclass
class Context:
	card: BankCard | None = None
	connection: Connection | None = None
	points: list[str] = field(default_factory=list)
	launched: list[str] = field(default_factory=list)


@pytest.fixture
def context(qtbot: QtBot) -> Iterator[Context]:
	found = Context()
	yield found
	if found.card is not None:
		found.card.close()
	if found.connection is not None:
		found.connection.close()


def _names(text: str) -> list[str]:
	return re.findall(r"« ([^»]*) »", text)


def _bank(connection: Connection, name: str) -> int:
	found = connection.execute(
		"SELECT id FROM banks WHERE internal_name = %s ORDER BY deleted_at NULLS FIRST", (name,)
	).fetchone()
	assert found is not None, name
	return int(str(found[0]))


def _card(context: Context) -> BankCard:
	assert context.card is not None
	return context.card


def _section(context: Context) -> EmojiSection:
	found = _card(context).findChild(EmojiSection, "bank_as_an_emoji")
	assert isinstance(found, EmojiSection)
	return found


def _strip(text: str) -> str:
	"""Une cellule vide des exemples, « », est une chaîne vide."""
	return text.strip()


# ─── Étant donné ───────────────────────────────────────────


@given(parsers.parse("les banques « {first} » et « {second} »"))
def banks(empty_database: Connection, first: str, second: str) -> None:
	for name in (first, second):
		empty_database.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, 'sequential')", (name,))


@given("le plugin de la banque en emoji, chargé")
def loaded() -> None:
	machincast_bank_as_an_emoji.register(_Plugin("Machin_interface"))  # type: ignore[arg-type]


@given(parsers.re(r"le sélecteur d'emojis de KDE (?P<state>installé|absent)$"))
def kde(context: Context, monkeypatch: pytest.MonkeyPatch, state: str) -> None:
	"""plasma-emojier, installé ou non ; installé, son lancement est seulement noté."""
	program = None
	if state == "installé":
		program = "/usr/bin/plasma-emojier"
	monkeypatch.setattr(section, "emojier", lambda: program)

	class Process:
		@staticmethod
		def startDetached(launched: str, _arguments: list[str]) -> bool:
			context.launched.append(launched)
			return True

	monkeypatch.setattr(picker, "QProcess", Process)
	QGuiApplication.clipboard().setText("avant le choix")


@given(parsers.parse("la banque « {name} » supprimée"))
def deleted(empty_database: Connection, name: str) -> None:
	empty_database.execute("UPDATE banks SET deleted_at = now() WHERE internal_name = %s", (name,))


# ─── Quand ─────────────────────────────────────────────────


def _open(context: Context, qtbot: QtBot, identifier: int | None) -> BankCard:
	socket, database = sample_database_parameters()
	context.connection = open_connection(socket, database, Role.INTERFACE)
	context.card = BankCard(context.connection, identifier, CLOCK)
	qtbot.addWidget(context.card)
	context.card.show()
	return context.card


@when(parsers.parse("j'ouvre la fiche de la banque « {name} »"))
def open_card(empty_database: Connection, context: Context, qtbot: QtBot, name: str) -> None:
	_open(context, qtbot, _bank(empty_database, name)).load()


@when(parsers.parse("j'ouvre la copie de la banque « {name} »"))
def open_copy(empty_database: Connection, context: Context, qtbot: QtBot, name: str) -> None:
	_open(context, qtbot, None).copy(_bank(empty_database, name))


@when("le raccourci du libellé « Nom interne » donne le focus à son champ")
def shortcut(context: Context, qtbot: QtBot) -> None:
	"""Ce que fait le libellé à son raccourci, Alt+N : le focus à son compagnon, le champ de la fiche."""
	card = _card(context)
	qtbot.waitExposed(card)
	card.ui.public_name.setFocus()
	buddy = card.ui.internal_name_caption.buddy()
	assert buddy is card.ui.internal_name
	buddy.setFocus(Qt.FocusReason.ShortcutFocusReason)


@when(parsers.parse("je choisis l'emoji « {emoji} »"))
def choose(context: Context, emoji: str) -> None:
	_section(context).set_emoji(emoji)


@when("je clique sur le bouton de l'emoji")
def click_emoji(context: Context) -> None:
	_section(context).emoji.click()


@when(parsers.re(r"(?:il copie|le presse-papiers reçoit) « (?P<text>[^»]+) »(?: dans le presse-papiers)?$"))
def copied(text: str) -> None:
	QGuiApplication.clipboard().setText(text)


@when("le choix se termine, dix minutes après")
def ended(context: Context) -> None:
	kde = _section(context).kde
	assert kde is not None
	assert kde.timer.interval() == 10 * 60 * 1000
	kde.timer.timeout.emit()


@when(parsers.parse("je choisis « {emoji} » dans la grille"))
def choose_in_grid(context: Context, emoji: str) -> None:
	for button in _section(context).grid.buttons:
		if button.text() == emoji:
			button.click()
			return
	raise AssertionError(emoji)


@when(parsers.parse("je colle « {text} » dans la grille, puis Entrée"))
def paste(context: Context, text: str) -> None:
	pasted = _section(context).grid.pasted
	pasted.setText(text)
	pasted.returnPressed.emit()


@when("je clique sur « Retirer l'emoji »")
def clear(context: Context) -> None:
	_section(context).clear.click()


@when(parsers.re(r"je remplace le nom interne éditable par « ?(?P<name>[^»]*?) ?»$"))
def rename(context: Context, name: str) -> None:
	_section(context).name.setText(name)


@when("j'enregistre la fiche")
def save(context: Context) -> None:
	_card(context).save()


@when("j'annule la fiche")
def cancel(context: Context) -> None:
	_card(context).ui.cancel.click()


@when(parsers.parse("le plugin de la banque en emoji s'enregistre dans « {executable} »"))
def register(context: Context, executable: str) -> None:
	machincast_bank_as_an_emoji.register(_Plugin(executable, context.points))  # type: ignore[arg-type]


class _Plugin:
	"""Un plugin chargé, abonné aux points du binaire, ou qui note seulement ses abonnements."""

	def __init__(self, executable: str, noted: list[str] | None = None) -> None:
		self.context = SimpleNamespace(executable=executable)
		self.noted = noted

	def on(self, point: str, function: Any) -> None:
		if self.noted is not None:
			self.noted.append(point)
			return
		plugins.active().points.subscribe("bank_as_an_emoji", point, function)


# ─── Alors ─────────────────────────────────────────────────


@then(parsers.re(r"le nom interne « (?P<name>[^»]+) » a l'emoji « ?(?P<emoji>[^»]*?) ?» et le nom « (?P<rest>[^»]+) »"))
def split(name: str, emoji: str, rest: str) -> None:
	assert names.split(name) == (_strip(emoji), rest)
	assert names.joined(_strip(emoji), rest) == name


@then(parsers.parse("le bouton de l'emoji montre « {text} »"))
def button(context: Context, text: str) -> None:
	assert _section(context).emoji.text() == text


@then("« Retirer l'emoji » est inactif")
def clear_inactive(context: Context) -> None:
	assert not _section(context).clear.isEnabled()


@then("le sélecteur d'emojis de KDE est lancé")
def launched(context: Context) -> None:
	assert context.launched == ["/usr/bin/plasma-emojier"]


@then("la grille d'emojis s'ouvre")
def grid_open(context: Context) -> None:
	assert _section(context).grid.isVisible()


@then("la grille d'emojis est fermée")
def grid_closed(context: Context) -> None:
	assert not _section(context).grid.isVisible()


@then(parsers.parse("le nom interne éditable est « {name} »"))
def editable(context: Context, name: str) -> None:
	assert _section(context).name.text() == name


@then("le champ du nom interne de la fiche est caché")
def hidden(context: Context) -> None:
	card = _card(context)
	assert card.ui.internal_name.isHidden()
	assert _section(context).name.isVisible()


@then("le bouton de l'emoji est devant le nom interne, dans la ligne « Nom interne »")
def in_row(context: Context) -> None:
	card = _card(context)
	section = _section(context)
	assert card.ui.form.labelForField(section.field) is card.ui.internal_name_caption
	assert section.emoji.x() < section.name.x()


@then(parsers.re(r"la fiche (?P<state>n'est pas modifiée|est modifiée)$"))
def modified(context: Context, state: str) -> None:
	assert _card(context).modified == (state == "est modifiée")


@then("le nom interne éditable a le focus")
def focused(context: Context) -> None:
	assert _card(context).focusWidget() is _section(context).name


@then(parsers.parse("la banque « {name} » est en base, et « {former} » n'y est plus"))
def renamed(empty_database: Connection, name: str, former: str) -> None:
	stored = empty_database.execute("SELECT internal_name FROM banks WHERE deleted_at IS NULL").fetchall()
	assert (name,) in stored, stored
	assert (former,) not in stored, stored


@then(parsers.parse("la banque « {name} » est toujours en base"))
def unchanged(empty_database: Connection, name: str) -> None:
	assert _bank(empty_database, name) > 0


@then(parsers.parse("la fiche dit l'erreur « {text} »"))
def error(context: Context, text: str) -> None:
	assert _card(context).error.text() == text


@then("le bouton de l'emoji et le nom interne éditable sont figés")
def frozen(context: Context) -> None:
	section = _section(context)
	assert not section.emoji.isEnabled()
	assert not section.name.isEnabled()


@then(parsers.parse("il s'abonne seulement à {points}"))
def subscribed(context: Context, points: str) -> None:
	assert context.points == _names(points)
