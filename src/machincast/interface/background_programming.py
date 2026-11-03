"""Fil musical garanti (https://github.com/dascritch/machincast/issues/39, spec § 8.10).

Sans événement de priorité fil musical, l'antenne n'a rien à jouer quand aucun autre événement ne la tient.
L'interface le vérifie au lancement, après la suppression d'un événement et après l'enregistrement d'un événement
(machincast.interface.window) : s'il n'en existe aucun, elle crée « Fil musical », permanent (sans début ni fin), et
sans élément, sa liste restant à remplir dans sa fiche. Si ce nom est déjà pris par un autre événement, le fil prend le
premier libre parmi « Fil musical 2 », « Fil musical 3 »…
"""

import psycopg
from psycopg.rows import TupleRow

from machincast.i18n import _

NAME = _("Background programming")


def guarantee(connection: psycopg.Connection[TupleRow]) -> str | None:
	"""Crée un fil musical permanent et vide s'il n'en existe aucun ; son nom, ou None s'il en existait un."""
	with connection.transaction():
		existing = connection.execute(
			"SELECT 1 FROM events WHERE priority = 'background_programming' AND deleted_at IS NULL LIMIT 1"
		).fetchone()
		if existing is not None:
			return None
		taken = {
			str(name)
			for (name,) in connection.execute(
				"SELECT internal_name FROM events WHERE (internal_name = %s OR internal_name LIKE %s || ' %%')"
				" AND deleted_at IS NULL",
				(NAME, NAME),
			)
		}
		name = NAME
		number = 1
		while name in taken:
			number += 1
			name = f"{NAME} {number}"
		connection.execute(
			"INSERT INTO events (internal_name, priority) VALUES (%s, 'background_programming')", (name,)
		)
	return name
