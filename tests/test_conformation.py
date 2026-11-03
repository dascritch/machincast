"""Scénarios de la conformation des textes (https://github.com/dascritch/machincast/issues/108).

Les étapes de la fenêtre, des fiches et de la base sont dans tests/interface_steps.py. « \\u{a0} » écrit dans un
scénario le caractère U+00A0 : les caractères invisibles ou de contrôle ne se lisent pas dans un tableau Gherkin.
"""

import re

import gi
import psycopg
from PySide6.QtWidgets import QLineEdit
from pytest_bdd import given, parsers, scenarios, then, when
from pytestqt.qtbot import QtBot

from machincast.conformation import conform
from tests.interface_steps import Context, open_line, open_tab, window

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast.indexer.tags import Tags, extract  # noqa: E402

scenarios("conformation.feature")

Connection = psycopg.Connection[tuple[object, ...]]
ESCAPE = re.compile(r"\\u\{([0-9a-fA-F]+)\}")
TABLES = {"banks", "sequences", "events", "feeds", "sounds"}
"""Les tables dont un scénario lit une colonne : chacune n'a qu'une ligne."""


def decode(text: str) -> str:
	"""« \\u{a0} » devient le caractère U+00A0."""
	return ESCAPE.sub(lambda found: chr(int(found.group(1), 16)), text)


# ─── Fonction ──────────────────────────────────────────────


@when(parsers.re(r"je conforme le texte « (?P<text>.*) »"), target_fixture="conforms")
def conform_text(text: str) -> str:
	return conform(decode(text))


@then(parsers.re(r"le texte conformé est « (?P<expected>.*) »"))
def text_conforms(conforms: str, expected: str) -> None:
	assert conforms == expected, ascii(conforms)


# ─── Tags ──────────────────────────────────────────────────


@given("les tags d'un fichier :", target_fixture="tags_list")
def file_tags(datatable: list[list[str]]) -> Gst.TagList:
	Gst.init(None)
	list_ = Gst.TagList.new_empty()
	for tag, value in (row for row in datatable[1:]):
		list_.add_value(Gst.TagMergeMode.APPEND, tag.strip(), decode(value.strip()))
	return list_


@when("l'indexeur extrait ces tags", target_fixture="extract_tags")
def extract_tags(tags_list: Gst.TagList) -> Tags:
	return extract(tags_list)


@then(parsers.parse("l'artiste extrait est « {artist} », le titre « {title} »"))
def artist_and_title(extract_tags: Tags, artist: str, title: str) -> None:
	assert (extract_tags.artist, extract_tags.title) == (artist, title)


@then(parsers.parse("les métadonnées musicales extraites sont « {key} » « {value} », sans genre"))
def metadata(extract_tags: Tags, key: str, value: str) -> None:
	assert extract_tags.metadata == {key: value}


# ─── Fiches ────────────────────────────────────────────────


@when(parsers.parse("j'ouvre la fiche du feed « {name} »"))
def open_feed(interface: Context, qtbot: QtBot, name: str) -> None:
	open_tab(interface, "Feeds")
	open_line(interface, qtbot, name)


@when(parsers.re(r"je saisis « (?P<input_>.*) » dans le champ « (?P<field>\w+) » de la fiche"))
def enter(interface: Context, input_: str, field: str) -> None:
	"""Comme une méthode de saisie : le texte entre tel quel dans le champ."""
	card = window(interface).ui.tabs.currentWidget()
	line = getattr(card.ui, field)
	assert isinstance(line, QLineEdit)
	line.selectAll()
	line.insert(decode(input_))


@then(parsers.re(r"en base, (?P<column>[\w.]+) de (?P<table>\w+) vaut « (?P<expected>.*) »"))
def in_database(empty_database: Connection, column: str, table: str, expected: str) -> None:
	assert table in TABLES
	key = None
	if "." in column:
		column, key = column.split(".")
	lines = empty_database.execute(f"SELECT {column} FROM {table}").fetchall()  # noqa: S608
	assert len(lines) == 1, lines
	value = lines[0][0]
	if (key is not None) and (isinstance(value, dict)):
		value = value.get(key)
	assert ((value) or ("")) == expected, ascii(value)
