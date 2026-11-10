"""Étapes des scénarios de lecture des tags (https://github.com/dascritch/machincast/issues/8).

Les étapes des fichiers, des sonores en base et du passage de l'indexeur sont dans tests/indexing_steps.py.
"""

import json
from pathlib import Path

import gi
import psycopg
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.database import SHORT_TEXT_LENGTH
from machincast.indexer.decoding import Check
from machincast.indexer.tags import Tags, extract
from tests.indexing_steps import read_tags_in_database as read

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

scenarios("tags.feature")

Connection = psycopg.Connection[tuple[object, ...]]
JSON = r"(?P<object_>\{.*\})"


def tags_list(text: str) -> Gst.TagList:
	Gst.init(None)
	list_ = Gst.TagList.new_from_string(text)
	assert list_ is not None, f"tags illisibles : {text}"
	return list_


# ─── Lecture ───────────────────────────────────────────────


@given(parsers.parse("les tags « {text} »"), target_fixture="list_")
def provided_tags(text: str) -> Gst.TagList:
	return tags_list(text)


@given("des tags dont l'artiste et le titre font 300 caractères", target_fixture="list_")
def long_tags() -> Gst.TagList:
	return tags_list(f'taglist, artist=(string)"{"a" * 300}", title=(string)"{"t" * 300}"')


@when("j'extrais ces tags", target_fixture="tags")
def extract_tags(list_: Gst.TagList) -> Tags:
	return extract(list_)


@then(parsers.parse("l'artiste lu est « {artist} » et le titre lu « {title} »"))
def artist_and_fetched_title(result: Check, artist: str, title: str) -> None:
	assert (result.tags.artist, result.tags.title) == (artist, title)


@then(parsers.re(rf"les métadonnées musicales lues sont {JSON}"))
def fetched_metadata(result: Check, object_: str) -> None:
	assert result.tags.metadata == json.loads(object_)


@then("aucun tag n'est lu")
def no_tag(result: Check) -> None:
	assert result.tags == Tags(None, None, {})


@then(parsers.re(r"l'année retenue est (?P<year>\d+|aucune)"))
def retained_year(tags: Tags, year: str) -> None:
	if year == "aucune":
		chosen = None
	else:
		chosen = int(year)
	assert tags.metadata.get("year") == chosen


@then(parsers.re(rf"les métadonnées musicales retenues sont {JSON}"))
def retained_metadata(tags: Tags, object_: str) -> None:
	assert tags.metadata == json.loads(object_)


@then("l'artiste et le titre retenus font 255 caractères")
def truncated_list(tags: Tags) -> None:
	assert (tags.artist is not None) and (tags.title is not None)
	assert len(tags.artist) == len(tags.title) == SHORT_TEXT_LENGTH


@then("aucun artiste ni titre n'est retenu")
def nor_artist_nor_title(tags: Tags) -> None:
	assert (tags.artist, tags.title) == (None, None)


# ─── Enregistrement en base ────────────────────────────────


def insert(database: Connection, file: Path, column: str, value: str, metadata: str) -> int:
	line = database.execute(
		f"INSERT INTO sounds (type, location, {column}, music_metadata) VALUES ('file', %s, %s, %s) RETURNING id",
		(str(file), value, metadata),
	).fetchone()
	assert line is not None
	return int(str(line[0]))


@given(
	parsers.re(rf"pour ce fichier, un sonore d'artiste « (?P<artist>[^»]+) » et de métadonnées {JSON}"),
	target_fixture="sound",
)
def sound_with_artist(empty_database: Connection, file: Path, artist: str, object_: str) -> int:
	return insert(empty_database, file, "artist", artist, object_)


@given(
	parsers.re(rf"pour ce fichier, un sonore de titre « (?P<title>[^»]+) » et de métadonnées {JSON}"),
	target_fixture="sound",
)
def sound_with_title(empty_database: Connection, file: Path, title: str, object_: str) -> int:
	return insert(empty_database, file, "title", title, object_)


@given(parsers.parse("les champs « {first} » et « {second} » de ce sonore édités à la main"))
def edited_fields(empty_database: Connection, sound: int, first: str, second: str) -> None:
	empty_database.execute("UPDATE sounds SET edited_fields = %s WHERE id = %s", ([first, second], sound))


@then(parsers.re(rf"en base, les métadonnées musicales sont {JSON}"))
def metadata_in_database(empty_database: Connection, sound: int, object_: str) -> None:
	assert read(empty_database, sound)[2] == json.loads(object_)


@then("en base, le sonore n'a ni artiste ni titre")
def without_artist_nor_title(empty_database: Connection, sound: int) -> None:
	assert read(empty_database, sound)[:2] == (None, None)


@then(parsers.parse("en base, le titre est toujours « {title} »"))
def unchanged_title(empty_database: Connection, sound: int, title: str) -> None:
	assert read(empty_database, sound)[1] == title
