"""Les requêtes SQL des programmes d'administration, toutes ici (https://github.com/dascritch/machincast/issues/583).

Machin purge, Machin maintenance-db, Machin restore-db, Machin grant-read et le déplacement des sonores personnels
d'install.sh --service (machincast.purge, machincast.maintenance, machincast.backup, machincast.access,
machincast.personal). Ce sont les opérations du propriétaire de la base, hors des rôles des binaires de l'antenne, sauf
Machin grant-read, au rôle de l'interface (doc/fr/regles/base-de-donnees.md, « Droits »). Chaque fonction prend la
connexion et ses paramètres, et rend ses lignes, ou ce que la requête a changé ; l'appelant ouvre la transaction.
"""

from datetime import date, datetime

import psycopg

Connection = psycopg.Connection[tuple[object, ...]]

# ─── Machin purge (machincast.purge, https://github.com/dascritch/machincast/issues/268) ───

PLAYS = """
	WITH erased AS (
		DELETE FROM airplay WHERE play_id IN (
			SELECT play_id FROM airplay GROUP BY play_id HAVING max(logged_at) < %s
		) RETURNING play_id
	) SELECT count(DISTINCT play_id) FROM erased
"""
"""Efface les passages entiers, début et fin, finis avant la limite ; leur nombre."""


def erase_plays(connection: Connection, limit: datetime) -> int:
	counted = connection.execute(PLAYS, (limit,)).fetchone()
	assert counted is not None
	return int(str(counted[0]))


def erase_log(connection: Connection, limit: datetime) -> int:
	"""Les lignes du log d'avant la limite ; leur nombre."""
	return connection.execute("DELETE FROM log WHERE logged_at < %s", (limit,)).rowcount


def erase_deleted(connection: Connection, table: str, column: str, limit: datetime) -> int:
	"""Les éléments d'une table, supprimés avant la limite ; leur nombre."""
	return connection.execute(f"DELETE FROM {table} WHERE {column} < %s", (limit,)).rowcount


def erase_skips(connection: Connection, day: date) -> None:
	"""Les sessions sautées d'avant ce jour, qui ne comptent plus pour rien."""
	connection.execute("DELETE FROM event_skips WHERE day < %s", (day,))


def log_purge(connection: Connection, message: str) -> None:
	connection.execute("INSERT INTO log (level, kind, message) VALUES ('info', 'purge', %s)", (message,))


# ─── Machin maintenance-db (machincast.maintenance, https://github.com/dascritch/machincast/issues/127) ───


def server_version(connection: Connection) -> int | None:
	"""Le numéro de version du serveur, server_version_num."""
	line = connection.execute("SHOW server_version_num").fetchone()
	if line is None:
		return None
	return int(str(line[0]))


def role_assumable(connection: Connection, role: str) -> bool:
	"""Le rôle existe, et le compte peut l'endosser."""
	line = connection.execute(
		"SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s)"
		" AND pg_has_role(current_user, (SELECT oid FROM pg_roles WHERE rolname = %s), 'SET')",
		(role, role),
	).fetchone()
	return (line is not None) and (line[0] is True)


def vacuum(connection: Connection) -> None:
	"""VACUUM ne s'exécute pas dans une transaction : la connexion est en autocommit."""
	connection.execute("VACUUM (ANALYZE)")


# ─── Machin restore-db (machincast.backup, https://github.com/dascritch/machincast/issues/347) ───


def public_relations(connection: Connection) -> int | None:
	"""Les tables, séquences et vues du schéma public."""
	line = connection.execute(
		"SELECT count(*) FROM pg_class JOIN pg_namespace ON pg_namespace.oid = relnamespace WHERE nspname = 'public'"
	).fetchone()
	if line is None:
		return None
	return int(str(line[0]))


# ─── Machin grant-read et les sonores personnels (machincast.access, machincast.personal) ───


def bank_directories(connection: Connection) -> list[tuple[object, ...]]:
	"""Les répertoires des banques qui ne sont pas supprimées, une fois chacun."""
	return connection.execute(
		"SELECT DISTINCT d.directory FROM bank_directories d JOIN banks b ON b.id = d.bank_id"
		" WHERE b.deleted_at IS NULL ORDER BY 1"
	).fetchall()


def files_outside_directories(connection: Connection) -> list[tuple[object, ...]]:
	"""Les fichiers des sonores non supprimés hors des répertoires des banques."""
	return connection.execute(
		"SELECT location FROM sounds s WHERE s.deleted_at IS NULL AND s.location IS NOT NULL AND NOT EXISTS ("
		" SELECT 1 FROM bank_directories d WHERE s.location LIKE d.directory || '/%%') ORDER BY 1"
	).fetchall()


def files(connection: Connection) -> list[tuple[object, ...]]:
	"""Les fichiers des sonores non supprimés."""
	return connection.execute(
		"SELECT location FROM sounds WHERE deleted_at IS NULL AND location IS NOT NULL ORDER BY 1"
	).fetchall()


RELOCATE = (
	"UPDATE {table} SET {column} = %s || substr({column}, length(%s) + 1)"
	" WHERE {column} = %s OR left({column}, length(%s) + 1) = %s || '/'"
)
"""Un emplacement, et tout ce qui est dessous, déplacé ailleurs."""
RELOCATED = (("bank_directories", "directory"), ("sounds", "location"))


def relocate(connection: Connection, old: str, new: str) -> None:
	"""Les répertoires des banques et les fichiers des sonores à cet emplacement, ou dessous, vont au nouveau."""
	for table, column in RELOCATED:
		connection.execute(RELOCATE.format(table=table, column=column), (new, old, old, old, old))


def forget_directory(connection: Connection, directory: str) -> None:
	"""Les sonores de ce répertoire sont supprimés, et le répertoire n'est plus celui d'aucune banque ; aucun fichier
	n'est touché."""
	connection.execute(
		"UPDATE sounds SET deleted_at = now() WHERE deleted_at IS NULL"
		" AND (location = %s OR left(location, length(%s) + 1) = %s || '/')",
		(directory, directory, directory),
	)
	connection.execute("DELETE FROM bank_directories WHERE directory = %s", (directory,))


def forget_file(connection: Connection, file: str) -> None:
	"""Le sonore de ce fichier est supprimé ; le fichier n'est pas touché."""
	connection.execute("UPDATE sounds SET deleted_at = now() WHERE deleted_at IS NULL AND location = %s", (file,))
