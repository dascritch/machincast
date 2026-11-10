"""Étapes des scénarios du schéma initial de la base de données."""

import gc
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import psycopg
import pytest
from psycopg import sql
from pytest_bdd import given, parsers, scenarios, then, when

from machincast.database import (
	TABLES,
	TYPES,
	apply_migrations,
	cancel_migrations,
	url_yoyo,
)
from tests.database_fixtures import (
	PURGE_ORDER,
	purge_database,
	sample_database_parameters,
)

scenarios("schema.feature")

# Sépare « col = val, col = val » sur les virgules suivies d'un nom de colonne et d'un signe égal,
# pour ne pas couper les valeurs qui contiennent elles-mêmes des virgules ('{1,2,3}').
SEPARATOR = re.compile(r",\s*(?=\w+\s*=)")
REFERENCE = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


@dataclass
class Context:
	connection: psycopg.Connection[tuple[object, ...]]
	references: dict[str, int] = field(default_factory=dict)
	error: psycopg.Error | None = None
	modified_at: datetime | None = None
	modified: tuple[str, str] = ("sounds", "sonore")
	"""Table et référence dont la date de modification est suivie."""
	connections_before: int = 0
	connections_after: int = 0
	applied: int | None = None
	"""Migrations appliquées par la dernière application (https://github.com/dascritch/machincast/issues/314)."""
	refusal: str | None = None
	before: list[str] = field(default_factory=list)


@pytest.fixture
def context(empty_database: psycopg.Connection[tuple[object, ...]]) -> Context:
	return Context(connection=empty_database)


def run_insertion(
	context: Context, table: str, values: dict[str, str], return_: str = ""
) -> psycopg.Cursor[tuple[object, ...]]:
	# Les valeurs sont des littéraux SQL écrits dans les scénarios : elles sont insérées telles quelles.
	columns = []
	for column in values:
		columns.append(sql.Identifier(column))
	literals = []
	for literal in values.values():
		literals.append(sql.SQL(literal))
	query = sql.SQL("INSERT INTO {} ({}) VALUES ({})" + return_).format(
		sql.Identifier(table),
		sql.SQL(", ").join(columns),
		sql.SQL(", ").join(literals),
	)
	return context.connection.execute(query)


def insert(context: Context, table: str, values: dict[str, str]) -> int:
	"""Insère une ligne et renvoie son identifiant."""
	line = run_insertion(context, table, values, " RETURNING id").fetchone()
	assert line is not None
	return int(str(line[0]))


def analyse(context: Context, values: str) -> dict[str, str]:
	# Remplace {banque}, {sonore}… par les identifiants de référence, sans toucher aux tableaux '{1,2,3}'.
	values = REFERENCE.sub(lambda m: str(context.references.get(m.group(1), m.group(0))), values)
	pairs = []
	for p in SEPARATOR.split(values.strip().strip(",")):
		if p.strip():
			pairs.append(p.split("=", 1))
	analyse = {}
	for key, value in pairs:
		analyse[key.strip()] = value.strip()
	return analyse


# ─── Étant donné ───────────────────────────────────────────


@given("une base de test vide où les migrations sont appliquées")
def migrated_database(context: Context) -> None:
	"""La fixture empty_database fournit déjà une base migrée et purgée."""


@given("les éléments de référence en base")
def references(context: Context) -> None:
	r = context.references
	r["feed"] = insert(context, "feeds", {"name": "'Studio mobile'", "url": "'https://flux.exemple'"})
	r["banque"] = insert(context, "banks", {"internal_name": "'Jingles'", "mode": "'random'"})
	r["sonore"] = insert(
		context,
		"sounds",
		{"type": "'file'", "location": "'/jingles/reference.flac'", "title": "'Titre de référence'"},
	)
	r["evenement"] = insert(context, "events", {"internal_name": "'Fil'", "priority": "'background_programming'"})
	r["sequence"] = insert(context, "sequences", {"internal_name": "'Passage publicitaire'"})


@then("la banque de référence n'est pas marquée « ne pas répéter »")
def reference_without_marked(context: Context) -> None:
	line = context.connection.execute(
		"SELECT no_repeat FROM banks WHERE id = %s", (context.references["banque"],)
	).fetchone()
	assert line == (False,)


@given("un deuxième sonore en base")
def sound_second(context: Context) -> None:
	context.references["sonore2"] = insert(
		context, "sounds", {"type": "'file'", "location": "'/jingles/deuxieme.flac'"}
	)


@given("un événement de secours en base")
def fallback_event(context: Context) -> None:
	context.references["secours"] = insert(
		context, "events", {"internal_name": "'Secours du direct'", "priority": "'fallback'"}
	)


@given("un stream secouru par cet événement")
def rescued_stream(context: Context) -> None:
	context.references["stream"] = insert(
		context,
		"sounds",
		{
			"type": "'stream'",
			"stream_url": "'https://flux.exemple/direct'",
			"fallback_event_id": str(context.references["secours"]),
		},
	)


@when("je passe l'événement de secours en émission")
def fallback_in_show(context: Context) -> None:
	try:
		context.connection.execute(
			"UPDATE events SET priority = 'show', starts_at = '2026-10-19 18:00' WHERE id = %s",
			(context.references["secours"],),
		)
	except psycopg.Error as error:
		context.error = error


FALLBACK_COLUMNS = {
	"secours de fin de liste": "end_fallback_event_id",
	"secours d'un stream tombé": "stream_fallback_event_id",
}
"""Les secours d'un événement (https://github.com/dascritch/machincast/issues/350)."""


@given(parsers.parse("une émission dont le {fallback} est cet événement"))
def rescued_show(context: Context, fallback: str) -> None:
	values = {
		"internal_name": "'Journal'",
		"priority": "'show'",
		"starts_at": "'2026-10-19 18:00'",
		"ends_at": "'2026-10-19 19:00'",
		FALLBACK_COLUMNS[fallback]: str(context.references["secours"]),
	}
	if fallback == "secours de fin de liste":
		values["end_of_list"] = "'fallback'"
	context.references["emission"] = insert(context, "events", values)


@then(parsers.parse("l'émission n'a plus de {fallback}"))
def show_without_fallback(context: Context, fallback: str) -> None:
	line = context.connection.execute(
		f"SELECT {FALLBACK_COLUMNS[fallback]} FROM events WHERE id = %s",  # noqa: S608
		(context.references["emission"],),
	).fetchone()
	assert line == (None,)


@when("je supprime l'événement de secours")
def delete_fallback(context: Context) -> None:
	context.connection.execute("DELETE FROM events WHERE id = %s", (context.references["secours"],))


@then("le stream n'a plus d'événement de secours")
def stream_without_fallback(context: Context) -> None:
	line = context.connection.execute(
		"SELECT fallback_event_id FROM sounds WHERE id = %s", (context.references["stream"],)
	).fetchone()
	assert line == (None,)


@given("une deuxième banque en base")
def bank_second(context: Context) -> None:
	context.references["banque2"] = insert(
		context, "banks", {"internal_name": "'Habillages hors saison'", "mode": "'sequential'"}
	)


@given("un passage du sonore de référence dans l'airplay")
def play(context: Context) -> None:
	insert(
		context,
		"airplay",
		{
			"play_id": "gen_random_uuid()",
			"line_type": "'start'",
			"sound_id": str(context.references["sonore"]),
			"location": "'/jingles/reference.flac'",
			"title": "'Titre de référence'",
		},
	)


# ─── Quand ─────────────────────────────────────────────────


@when(parsers.parse('j\'enregistre dans "{table}" : {values}'))
def save(context: Context, table: str, values: str) -> None:
	try:
		run_insertion(context, table, analyse(context, values))
	except psycopg.Error as error:
		context.error = error


@when(parsers.parse('j\'enregistre dans "{table}" :'))
def save_empty(context: Context, table: str) -> None:
	save(context, table, "")


@when("j'annule toutes les migrations")
def cancel(context: Context) -> None:
	cancel_migrations(url_yoyo(*sample_database_parameters()))


def opened_connections(context: Context) -> int:
	"""Connexions du compte courant à la base de test, celle du scénario comprise."""
	line = context.connection.execute(
		"SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND usename = current_user"
	).fetchone()
	assert (line is not None) and (isinstance(line[0], int))
	return line[0]


def without_garbage_collector(context: Context, migration: Callable[[str], None]) -> None:
	"""Lance la migration ramasse-miettes suspendu, et note les connexions ouvertes avant et après."""
	context.connections_before = opened_connections(context)
	gc.disable()
	try:
		migration(url_yoyo(*sample_database_parameters()))
		# Une connexion fermée quitte pg_stat_activity peu après : quelques instants pour s'en assurer.
		limit = time.monotonic() + 2
		while ((after := opened_connections(context)) > context.connections_before) and (time.monotonic() < limit):
			time.sleep(0.05)
		context.connections_after = after
	finally:
		gc.enable()


@when("j'applique les migrations, ramasse-miettes suspendu")
def apply_without_garbage_collector(context: Context) -> None:
	without_garbage_collector(context, apply_migrations)


@when("j'annule toutes les migrations, ramasse-miettes suspendu")
def cancel_without_garbage_collector(context: Context) -> None:
	without_garbage_collector(context, cancel_migrations)


@then("aucune connexion supplémentaire à la base de test ne reste ouverte")
def no_remaining_connection(context: Context) -> None:
	assert context.connections_after == context.connections_before, (
		context.connections_before,
		context.connections_after,
	)


@when("je modifie le titre du sonore de référence")
def modify_title(context: Context) -> None:
	identifier = context.references["sonore"]
	line = context.connection.execute("SELECT modified_at FROM sounds WHERE id = %s", (identifier,)).fetchone()
	assert (line is not None) and (isinstance(line[0], datetime))
	context.modified_at = line[0]
	context.connection.execute("UPDATE sounds SET title = 'Nouveau titre' WHERE id = %s", (identifier,))


@given("un élément de l'événement de référence, joué dans l'airplay")
def played_item(context: Context) -> None:
	r = context.references
	r["element"] = insert(
		context,
		"event_items",
		{"event_id": str(r["evenement"]), "position": "1", "sound_id": str(r["sonore"])},
	)
	insert(
		context,
		"airplay",
		{
			"play_id": "gen_random_uuid()",
			"line_type": "'start'",
			"sound_id": str(r["sonore"]),
			"event_id": str(r["evenement"]),
			"event_item_id": str(r["element"]),
		},
	)


@given("un élément de la séquence de référence, joué dans l'airplay")
def played_sequence_item(context: Context) -> None:
	r = context.references
	r["element_de_sequence"] = insert(
		context,
		"sequence_items",
		{"sequence_id": str(r["sequence"]), "position": "1", "sound_id": str(r["sonore"])},
	)
	run_insertion(
		context,
		"airplay",
		{
			"play_id": "gen_random_uuid()",
			"line_type": "'start'",
			"sound_id": str(r["sonore"]),
			"sequence_id": str(r["sequence"]),
			"sequence_item_id": str(r["element_de_sequence"]),
		},
	)


@when("je modifie le nom public de la séquence de référence")
def modify_sequence(context: Context) -> None:
	identifier = context.references["sequence"]
	line = context.connection.execute("SELECT modified_at FROM sequences WHERE id = %s", (identifier,)).fetchone()
	assert (line is not None) and (isinstance(line[0], datetime))
	context.modified_at = line[0]
	context.modified = ("sequences", "sequence")
	context.connection.execute("UPDATE sequences SET public_name = 'Vous écoutez' WHERE id = %s", (identifier,))


@when("je supprime la séquence de référence")
def delete_sequence(context: Context) -> None:
	context.connection.execute("DELETE FROM sequences WHERE id = %s", (context.references["sequence"],))


@then("la ligne d'airplay existe toujours, sans référence à la séquence ni à son élément")
def airplay_without_sequence(context: Context) -> None:
	lines = context.connection.execute("SELECT sequence_id, sequence_item_id, sound_id FROM airplay").fetchall()
	assert lines == [(None, None, context.references["sonore"])]


@when("je supprime l'événement de référence")
def delete_event(context: Context) -> None:
	context.connection.execute("DELETE FROM events WHERE id = %s", (context.references["evenement"],))


@then("aucune session n'est sautée en base")
def no_skipped_session(context: Context) -> None:
	assert context.connection.execute("SELECT count(*) FROM event_skips").fetchone() == (0,)


@then("l'événement de référence n'a plus d'élément")
def event_without_item(context: Context) -> None:
	line = context.connection.execute(
		"SELECT count(*) FROM event_items WHERE event_id = %s", (context.references["evenement"],)
	).fetchone()
	assert line == (0,)


@when("je supprime cet élément de l'événement")
def delete_item(context: Context) -> None:
	context.connection.execute("DELETE FROM event_items WHERE id = %s", (context.references["element"],))


@when("je supprime le sonore de référence")
def delete_sound(context: Context) -> None:
	context.connection.execute("DELETE FROM sounds WHERE id = %s", (context.references["sonore"],))


# ─── Alors ─────────────────────────────────────────────────


def present_tables(context: Context) -> set[str]:
	lines = context.connection.execute(
		"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
	).fetchall()
	present_tables = set()
	for line in lines:
		present_tables.add(str(line[0]))
	return present_tables


@then("la base contient les tables :")
def contains_tables(context: Context, datatable: list[list[str]]) -> None:
	expected_list = set()
	for line in datatable[1:]:
		expected_list.add(line[0])
	assert expected_list == set(TABLES)
	assert expected_list <= present_tables(context)


@then("la base ne contient plus aucune table ni aucun type de MachinCast")
def more_tables(context: Context) -> None:
	assert not set(TABLES) & present_tables(context)
	types = context.connection.execute("SELECT typname FROM pg_type WHERE typname = ANY(%s)", (list(TYPES),)).fetchall()
	assert types == []


@then("la base accepte l'enregistrement")
def accepts(context: Context) -> None:
	assert context.error is None, f"refusé : {context.error}"


@then("la base refuse l'enregistrement")
def refuses(context: Context) -> None:
	assert context.error is not None, "la base aurait dû refuser l'enregistrement"
	# Une contrainte violée, une valeur hors d'un type ENUM ou un texte trop long,
	# et non une faute de syntaxe dans le scénario.
	assert isinstance(
		context.error,
		psycopg.errors.IntegrityError
		| psycopg.errors.InvalidTextRepresentation
		| psycopg.errors.StringDataRightTruncation,
	), repr(context.error)


def compare(context: Context, type_enum: str, first: str, second: str) -> bool:
	query = sql.SQL("SELECT %s::{type} < %s::{type}").format(type=sql.Identifier(type_enum))
	line = context.connection.execute(query, (first, second)).fetchone()
	assert line is not None
	return line[0] is True


@then(parsers.parse('la priorité "{first}" est inférieure à "{second}"'))
def lower_priority(context: Context, first: str, second: str) -> None:
	assert compare(context, "event_priority", first, second)


@then(parsers.parse('le jour "{first}" vient avant "{second}"'))
def day_before(context: Context, first: str, second: str) -> None:
	assert compare(context, "weekday", first, second)


@then("sa date de modification a avancé")
def advanced_date(context: Context) -> None:
	table, reference = context.modified
	line = context.connection.execute(
		sql.SQL("SELECT modified_at FROM {} WHERE id = %s").format(sql.Identifier(table)),
		(context.references[reference],),
	).fetchone()
	assert (line is not None) and (isinstance(line[0], datetime))
	assert (context.modified_at is not None) and (line[0] > context.modified_at)


@then("la ligne d'airplay existe toujours, sans référence à l'élément")
def airplay_without_item(context: Context) -> None:
	lines = context.connection.execute("SELECT event_item_id, event_id FROM airplay").fetchall()
	assert lines == [(None, context.references["evenement"])]


@then("la ligne d'airplay existe toujours, avec son titre recopié et sans référence au sonore")
def kept_airplay(context: Context) -> None:
	lines = context.connection.execute("SELECT sound_id, title FROM airplay").fetchall()
	assert lines == [(None, "Titre de référence")]


# ─── Crossfades facultatifs (https://github.com/dascritch/machincast/issues/145) ─────


@then("les types énumérés de la base sont ceux de machincast.database.TYPES")
def known_types(context: Context) -> None:
	lines = context.connection.execute(
		"SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace"
		" WHERE t.typtype = 'e' AND n.nspname = 'public'"
	).fetchall()
	name_set = set()
	for (name,) in lines:
		name_set.add(str(name))
	assert name_set == set(TYPES)


@then(parsers.re(r"le sonore « (?P<location>[^»]+) » a ses crossfades (?P<value>non paramétrés|de 0 seconde)"))
def sound_crossfades(context: Context, location: str, value: str) -> None:
	line = context.connection.execute(
		"SELECT crossfade_start, crossfade_end FROM sounds WHERE location = %s", (location,)
	).fetchone()
	expected = None
	if value == "de 0 seconde":
		expected = timedelta(0)
	assert line == (expected, expected), line


@when("j'applique les migrations")
def apply(context: Context) -> None:
	context.connection.commit()
	try:
		context.applied = apply_migrations(url_yoyo(*sample_database_parameters()))
	except psycopg.Error as error:
		context.refusal = str(error)


def database_migrations(context: Context) -> list[str]:
	lines = context.connection.execute("SELECT migration_id FROM _yoyo_migration ORDER BY migration_id").fetchall()
	database_migrations = []
	for line in lines:
		database_migrations.append(str(line[0]))
	return database_migrations


@then(parsers.re(r"(?P<count>aucune|\d+) migrations? (?:n')?(?:a été appliquée|ont été appliquées)"))
def applied_count(context: Context, count: str) -> None:
	assert context.refusal is None, context.refusal
	if count == "aucune":
		expected = 0
	else:
		expected = int(count)
	assert context.applied == expected


@then(parsers.parse("les migrations appliquées à la base de test sont « {migration} »"))
def applied_migrations(context: Context, migration: str) -> None:
	name_list = []
	for name in migration.split(","):
		name_list.append(name.strip())
	assert database_migrations(context) == name_list


# ─── Détection de silence (https://github.com/dascritch/machincast/issues/146) ───


def _detection(context: Context, table: str, column: str, value: object) -> object:
	query = sql.SQL("SELECT silence_detection FROM {} WHERE {} = %s").format(
		sql.Identifier(table), sql.Identifier(column)
	)
	line = context.connection.execute(query, (value,)).fetchone()
	assert line is not None
	return line[0]


@then("la banque de référence n'active pas la détection de silence")
def reference_bank_without_detection(context: Context) -> None:
	assert _detection(context, "banks", "id", context.references["banque"]) is False


@then("le sonore de référence n'active pas la détection de silence")
def reference_sound_without_detection(context: Context) -> None:
	assert _detection(context, "sounds", "id", context.references["sonore"]) is False


@then("le sonore de référence n'a ni début ni fin détectés")
def reference_sound_without_silences(context: Context) -> None:
	line = context.connection.execute(
		"SELECT detected_start, detected_end FROM sounds WHERE id = %s", (context.references["sonore"],)
	).fetchone()
	assert line == (None, None)


# ─── Audit demandé (https://github.com/dascritch/machincast/issues/114) ───


def _requested_audit(context: Context, column: str, value: object) -> object:
	line = context.connection.execute(
		f"SELECT audit_requested FROM sounds WHERE {column} = %s",  # noqa: S608
		(value,),
	).fetchone()
	assert line is not None
	return line[0]


@then("le sonore de référence n'a pas d'audit complet demandé")
def reference_sound_without_audit(context: Context) -> None:
	assert _requested_audit(context, "id", context.references["sonore"]) is False


@then(parsers.parse("la table « {table} » a {count:d} ligne"))
@then(parsers.parse("la table « {table} » a {count:d} lignes"))
def table_lines(context: Context, table: str, count: int) -> None:
	assert table in TABLES, table
	line = context.connection.execute(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608 : table connue
	assert line == (count,), line


# ─── Purge entre deux scénarios (https://github.com/dascritch/machincast/issues/280) ───


@when("la base est purgée comme entre deux scénarios")
def purge(context: Context) -> None:
	purge_database(context.connection)


@then("la purge connaît chaque table de machincast.database.TABLES")
def full_purge() -> None:
	assert sorted(PURGE_ORDER) == sorted(TABLES)


@then("chaque table de la base est vide")
def empty_tables(context: Context) -> None:
	for table in TABLES:
		line = context.connection.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()
		assert line == (0,), table


@then("un nouveau sonore reçoit l'identifiant 1")
def identifier(context: Context) -> None:
	line = context.connection.execute(
		"INSERT INTO sounds (type, location) VALUES ('file', '/premier.flac') RETURNING id"
	).fetchone()
	assert line == (1,)
