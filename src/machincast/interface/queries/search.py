"""Requêtes de la recherche globale (https://github.com/dascritch/machincast/issues/442)."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]

ACCENTED = "àâäáãåçéèêëíìîïñóòôöõúùûüýÿÀÂÄÁÃÅÇÉÈÊËÍÌÎÏÑÓÒÔÖÕÚÙÛÜÝ"
WITHOUT_ACCENT = "aaaaaaceeeeiiiinooooouuuuyyaaaaaaceeeeiiiinooooouuuuy"
"""Les lettres accentuées, minuscules et majuscules, que la base ramène à leur lettre de base, dans le même ordre :
avant lower(), qui ne sait pas toujours abaisser une majuscule accentuée, selon la locale de la base."""


def _normalised(column: str) -> str:
	return f"lower(translate(COALESCE({column}, ''), '{ACCENTED}', '{WITHOUT_ACCENT}'))"


def _finds(*columns: str) -> str:
	column_list = []
	for column in columns:
		column_list.append(f"{_normalised(column)} LIKE query.pattern")
	return " OR ".join(column_list)


FOUND_LIST = f"""
	WITH query AS (SELECT %s::text AS pattern)
	SELECT 1 AS rank, 'event' AS category, id, internal_name AS name, public_name, NULL AS state FROM events, query
		WHERE (deleted_at IS NULL) AND ({_finds("internal_name", "public_name")})
	UNION ALL
	SELECT 2, 'sequence', id, internal_name, public_name, NULL FROM sequences, query
		WHERE (deleted_at IS NULL) AND ({_finds("internal_name", "public_name")})
	UNION ALL
	SELECT 3, 'bank', id, internal_name, public_name, NULL FROM banks, query
		WHERE (deleted_at IS NULL) AND ({_finds("internal_name", "public_name")})
	UNION ALL
	SELECT 4, 'sound', id, concat_ws(' – ', artist, title), NULL, state::text FROM sounds, query
		WHERE (deleted_at IS NULL) AND ({_finds("artist", "title")})
"""
"""Les éléments où se trouve le motif, lié une seule fois (query.pattern), avec le rang de leur type (rank) ; jamais un
élément supprimé (https://github.com/dascritch/machincast/issues/267)."""


def found(connection: Connection, pattern: str, limit: int) -> list[TupleRow]:
	"""Les premiers éléments où se trouve le motif : type, identifiant, nom, nom public et état ; dans une transaction."""
	return connection.execute(
		f"SELECT category, id, name, public_name, state FROM ({FOUND_LIST}) t ORDER BY rank, lower(name), id LIMIT %s",
		(pattern, limit),
	).fetchall()


def count(connection: Connection, pattern: str) -> int:
	"""Le nombre total d'éléments où se trouve le motif."""
	line = connection.execute(f"SELECT count(*) FROM ({FOUND_LIST}) t", (pattern,)).fetchone()
	assert line is not None
	return int(str(line[0]))
