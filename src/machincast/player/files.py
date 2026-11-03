"""Vérification d'un fichier avant de le jouer (https://github.com/dascritch/machincast/issues/15, spec § 5.1).

Le binaire lecture compare la date de modification et la taille du fichier avec celles que l'indexeur a
enregistrées. Un écart est consigné dans le log, en alerte : le fichier est quand même joué, et c'est l'indexeur
qui mettra la base à jour. Un fichier introuvable n'est pas joué : incident dans le log.
"""

from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import integer_or_none
from machincast.i18n import N_
from machincast.player.history import IN_DATABASE, History


def check_before_playback(
	connection: psycopg.Connection[TupleRow], sound: int, history: History = IN_DATABASE
) -> Path | None:
	"""Chemin du fichier à jouer, ou None s'il est introuvable ; consigne tout écart dans le log.

	La connexion a endossé le rôle de la lecture (machincast.database.open_connection).
	"""
	with connection.transaction():
		line = connection.execute(
			"SELECT location, file_modified_at, file_size FROM sounds WHERE id = %s", (sound,)
		).fetchone()
		if (line is None) or (line[0] is None):
			return None
		path = Path(str(line[0]))
		modified_at = line[1] if isinstance(line[1], datetime) else None
		size = integer_or_none(line[2])
		try:
			state = path.stat()
		except OSError:
			history.record(
				connection,
				"incident",
				N_("file not found"),
				N_("{path}: no file at this location").format(path=path),
				sound=sound,
			)
			return None
		gaps = []
		on_disk = datetime.fromtimestamp(state.st_mtime, tz=UTC)
		if (modified_at is not None) and (on_disk != modified_at):
			gaps.append(
				N_(
					"modification date {modified_at:%Y-%m-%d %H:%M:%S} in the database, "
					"{on_disk:%Y-%m-%d %H:%M:%S} on the disk"
				).format(modified_at=modified_at.astimezone(), on_disk=on_disk.astimezone())
			)
		if (size is not None) and (state.st_size != size):
			gaps.append(
				N_("size {size} bytes in the database, {st_size} on the disk").format(size=size, st_size=state.st_size)
			)
		if gaps:
			history.record(
				connection,
				"warning",
				N_("modified file"),
				N_("{path}: {list}; the indexer will update the database").format(path=path, list=" ; ".join(gaps)),
				sound=sound,
			)
		return path
