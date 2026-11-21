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
from machincast.interface.queries import events as queries

NAME = _("Background programming")


def guarantee(connection: psycopg.Connection[TupleRow]) -> str | None:
	"""Crée un fil musical permanent et vide s'il n'en existe aucun ; son nom, ou None s'il en existait un."""
	with connection.transaction():
		if queries.background_programming_exists(connection):
			return None
		taken = set()
		for (taken_name,) in queries.names_like(connection, NAME):
			taken.add(str(taken_name))
		name = NAME
		number = 1
		while name in taken:
			number += 1
			name = f"{NAME} {number}"
		queries.insert_background_programming(connection, name)
	return name
