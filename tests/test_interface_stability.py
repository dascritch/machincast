"""Scénarios de la réactivité et de la stabilité de l'interface (https://github.com/dascritch/machincast/issues/305).

Les étapes de la fenêtre, de ses onglets et de ses fiches sont dans tests/interface_steps.py.
"""

import gc
import weakref
from collections.abc import Callable
from types import SimpleNamespace

import psycopg
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.interface.bank_card import BankCard
from tests.interface_steps import Connection, Context, identifier, opened_card, window

scenarios("interface_stability.feature")


@pytest.fixture
def plays() -> SimpleNamespace:
	return SimpleNamespace(count=0, cards=[])


@given(parsers.parse("la banque « {name} », de {count:d} sonores"))
def big_bank(empty_database: Connection, name: str, count: int) -> None:
	empty_database.execute("INSERT INTO banks (internal_name, mode) VALUES (%s, 'random')", (name,))
	bank = identifier(empty_database, "banks", "internal_name", name)
	empty_database.execute(
		"INSERT INTO sounds (type, location, title, artist, duration) SELECT 'file', '/srv/m/' || i || '.flac',"
		" 'Titre ' || i, 'Artiste ' || i, '200 s' FROM generate_series(1, %s) i",
		(count,),
	)
	empty_database.execute(
		"INSERT INTO bank_sounds (bank_id, sound_id, position)"
		" SELECT %s, id, row_number() OVER (ORDER BY id) FROM sounds",
		(bank,),
	)


@given("les lectures des fiches de banque sont comptées")
def count(plays: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
	read: Callable[[BankCard], None] = BankCard._read

	def counted(card: BankCard) -> None:
		plays.count += 1
		read(card)

	monkeypatch.setattr(BankCard, "_read", counted)


@when(parsers.parse("j'ouvre puis ferme {times:d} fois la fiche de la banque « {name} »"))
def open_close(interface: Context, empty_database: Connection, plays: SimpleNamespace, times: int, name: str) -> None:
	main = window(interface)
	bank = identifier(empty_database, "banks", "internal_name", name)
	for _ in range(times):
		main._open("banque", bank, name)
		opened = opened_card(interface)
		plays.cards.append(weakref.ref(opened))
		main._close(main.ui.tabs.indexOf(opened))
		del opened
		QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
		QApplication.processEvents()
	gc.collect()


@then(parsers.parse("la fiche de la banque a été lue {count:d} fois"))
def fetched(plays: SimpleNamespace, count: int) -> None:
	assert plays.count == count


@then(parsers.parse("la fiche montre {count:d} sonores"))
def shown_sounds(interface: Context, count: int) -> None:
	card = opened_card(interface)
	assert isinstance(card, BankCard)
	assert card.ui.sounds.topLevelItemCount() == count


@then("aucune des fiches fermées ne survit")
def released_list(plays: SimpleNamespace) -> None:
	assert plays.cards != []
	assert [reference for reference in plays.cards if reference() is not None] == []


@then("psycopg n'utilise pas son implémentation en Python")
def psycopg_compile() -> None:
	assert psycopg.pq.__impl__ in ("binary", "c"), psycopg.pq.__impl__
