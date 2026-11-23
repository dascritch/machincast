"""Les requêtes SQL de la vérification des plugins (https://github.com/dascritch/machincast/issues/585)."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]


def missing_tables(connection: Connection, tables: list[str]) -> list[str]:
	"""Les tables de la liste qui ne sont pas dans le schéma public ; il ne faut aucun droit sur elles."""
	rows = connection.execute(
		"SELECT name FROM unnest(%s::text[]) AS name WHERE to_regclass('public.' || quote_ident(name)) IS NULL"
		" ORDER BY name",
		(tables,),
	).fetchall()
	missing = []
	for (name,) in rows:
		missing.append(str(name))
	return missing
