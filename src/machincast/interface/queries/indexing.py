"""Requête de l'avancement de l'indexation (https://github.com/dascritch/machincast/issues/442)."""

import psycopg
from psycopg.rows import TupleRow

Connection = psycopg.Connection[TupleRow]

QUERY = """
WITH latest AS (
	SELECT max(logged_at) AS started_at FROM log WHERE kind = 'start' AND starts_with(message, %s || ' ')
),
directories AS (
	SELECT r.directory,
		bool_and((r.scanned_at IS NOT NULL) AND (r.scanned_at >= COALESCE((SELECT started_at FROM latest), '-infinity')))
			AS scanned
	FROM bank_directories r JOIN banks b ON b.id = r.bank_id
	WHERE b.deleted_at IS NULL
	GROUP BY r.directory
)
SELECT
	(SELECT started_at FROM latest),
	(SELECT count(*) FROM directories),
	(SELECT count(*) FROM directories WHERE scanned),
	count(*),
	count(*) FILTER (WHERE (checked_at IS NOT NULL) AND (audited_at IS NULL)),
	count(*) FILTER (WHERE audited_at IS NOT NULL)
FROM sounds
WHERE type = 'file' AND deleted_at IS NULL
"""


def status(connection: Connection, executable: str) -> TupleRow:
	"""Début de la dernière indexation, répertoires et leur nombre scanné, fichiers, vérifiés et audités ; dans une
	transaction."""
	line = connection.execute(QUERY, (executable,)).fetchone()
	assert line is not None
	return line
