"""Export et réimportation de la base : Machin backup-db et Machin restore-db
(https://github.com/dascritch/machincast/issues/347), pour un plan de reprise d'activité.

	Machin backup-db [--backups REPERTOIRE]
	Machin restore-db FICHIER

backup-db sauvegarde la base de production de la configuration, comme la première étape de Machin maintenance-db :
pg_dump de la version du serveur, au format personnalisé de PostgreSQL, dans un fichier daté du répertoire des
sauvegardes (backup.directory, le répertoire personnel du compte par défaut ; --backups pour un autre).

restore-db réimporte une telle sauvegarde, sur ce poste ou sur un autre, dans une base de production vide, comme
install.sh vient de la créer ; une base qui n'est pas vide n'est jamais écrasée. Il vérifie d'abord le fichier : une
sauvegarde de MachinCast, qui a ses tables et le registre de ses migrations, d'une version qui n'est pas plus récente
que celle installée (aucune migration inconnue). pg_restore la réimporte en une seule transaction : un échec laisse la
base vide. Les objets reviennent au compte qui réimporte (--no-owner), avec les droits des rôles de MachinCast, que
le serveur doit déjà avoir. Puis les migrations qui manquent à une sauvegarde plus ancienne sont appliquées.

Codes de sortie : 0 si tout s'est bien passé, 1 sinon, 2 pour une configuration invalide.
"""

import argparse
import logging
import subprocess
from collections.abc import Sequence
from pathlib import Path

import psycopg
from yoyo import read_migrations

from machincast.cli import launch
from machincast.configuration import Configuration
from machincast.database import MIGRATION_DIRECTORY
from machincast.i18n import _
from machincast.maintenance import BACKUP_DELAY, BackupFailure, back_up, server_version, tool, update_schema

BACKUP_EXECUTABLE = "Machin_backup-db"
BACKUP_DESCRIPTION = _("Backs up the MachinCast database into a dated file.")
RESTORE_EXECUTABLE = "Machin_restore-db"
RESTORE_DESCRIPTION = _("Restores a MachinCast backup into a new, empty database.")
FAILURE_CODE = 1
MIGRATIONS = "_yoyo_migration"
"""La table où yoyo note les migrations appliquées : une sauvegarde de MachinCast l'a, avec ses tables."""
TABLES = (MIGRATIONS, "sounds", "events")
"""Les tables qu'une sauvegarde de MachinCast contient forcément."""

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
log = logging.getLogger("machincast.backup")


class Refusal(Exception):
	"""La sauvegarde ne se réimporte pas : la base reste telle quelle."""


def backup_options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument(
		"--backups",
		type=Path,
		metavar="REPERTOIRE",
		help=_("directory of the backup; by default backup.directory of the configuration"),
	)


def run_backup(configuration: Configuration, options: argparse.Namespace) -> int:
	"""Sauvegarde la base de production ; le code de sortie, nul si elle est faite."""
	directory = Path((options.backups) or (configuration.backup.directory)).expanduser()
	try:
		back_up(configuration, directory)
	except BackupFailure as error:
		log.error(_("backup impossible: {error}").format(error=error))
		return FAILURE_CODE
	return 0


def restore_options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument("file", type=Path, metavar="FICHIER", help=_("backup made by Machin backup-db"))


def _program(name: str, configuration: Configuration) -> str:
	command = tool(name, server_version(configuration.database))
	if command is None:
		raise Refusal(_("{name} not found, install postgresql-client").format(name=name))
	return command


def _read(command: list[str]) -> subprocess.CompletedProcess[str]:
	try:
		return subprocess.run(
			command,
			capture_output=True,
			text=True,
			timeout=BACKUP_DELAY,
			stdin=subprocess.DEVNULL,
			check=False,
		)
	except (OSError, subprocess.SubprocessError) as error:
		raise Refusal(str(error)) from error


def recorded_migrations(restore: str, file: Path) -> list[str]:
	"""Les migrations notées dans la sauvegarde, par leur identifiant ; lève Refusal pour un fichier qui n'est pas une
	sauvegarde de MachinCast."""
	not_backup = _("{file} is not a MachinCast backup: {reason}")
	listed = _read([restore, "--list", str(file)])
	if listed.returncode != 0:
		raise Refusal(not_backup.format(file=file, reason=listed.stderr.strip()))
	for table in TABLES:
		if f"TABLE public {table} " not in listed.stdout:
			raise Refusal(not_backup.format(file=file, reason=_("table {table} missing").format(table=table)))
	data = _read([restore, "--data-only", f"--table={MIGRATIONS}", "--file=-", str(file)])
	if data.returncode != 0:
		raise Refusal(not_backup.format(file=file, reason=data.stderr.strip()))
	return _copied_identifiers(data.stdout)


def _copied_identifiers(script: str) -> list[str]:
	"""Les migration_id du COPY de la table des migrations, dans le script que donne pg_restore."""
	identifiers: list[str] = []
	column = -1
	for line in script.splitlines():
		if line == "\\.":
			column = -1
		if (column >= 0) and (line != "\\."):
			identifiers.append(line.split("\t")[column])
		if line.startswith(f"COPY public.{MIGRATIONS} "):
			columns = line.split("(", 1)[1].split(")", 1)[0].split(", ")
			column = columns.index("migration_id")
	return identifiers


def _known_migrations() -> set[str]:
	known = set()
	for migration in read_migrations(str(MIGRATION_DIRECTORY)):
		known.add(migration.id)
	return known


def _check_empty(configuration: Configuration) -> None:
	"""La base de production ne doit rien contenir : ni table, ni séquence, ni vue dans son schéma public."""
	database = configuration.database
	with psycopg.connect(host=str(database.socket), dbname=database.production) as connection:
		line = connection.execute(
			"SELECT count(*) FROM pg_class JOIN pg_namespace ON pg_namespace.oid = relnamespace"
			" WHERE nspname = 'public'"
		).fetchone()
	if (line is None) or (line[0] != 0):
		raise Refusal(
			_(
				"database {production} is not empty: a backup is only restored into a new database, as install.sh"
				" creates it"
			).format(production=database.production)
		)


def restore(configuration: Configuration, file: Path) -> None:
	"""Vérifie la sauvegarde et la base, réimporte, puis applique les migrations qui manquent ; lève Refusal,
	psycopg.Error."""
	database = configuration.database
	if not file.is_file():
		raise Refusal(_("{file} not found").format(file=file))
	program = _program("pg_restore", configuration)
	unknown = sorted(set(recorded_migrations(program, file)) - _known_migrations())
	if unknown:
		raise Refusal(
			_(
				"{file} comes from a newer version of MachinCast (unknown migrations: {migrations}): update MachinCast"
				" first"
			).format(file=file, migrations=", ".join(unknown))
		)
	_check_empty(configuration)
	log.info(_("restoring {file} into database {production}").format(file=file, production=database.production))
	result = _read(
		[
			program,
			"--no-owner",
			"--single-transaction",
			"--exit-on-error",
			f"--host={database.socket}",
			f"--dbname={database.production}",
			str(file),
		]
	)
	if result.returncode != 0:
		raise Refusal(
			_("restoring failed, database {production} left empty: {error}").format(
				production=database.production, error=result.stderr.strip()
			)
		)
	log.info(_("restoring done"))
	update_schema(configuration)


def run_restore(configuration: Configuration, options: argparse.Namespace) -> int:
	"""Réimporte la sauvegarde ; le code de sortie, nul si elle est réimportée et à jour."""
	try:
		restore(configuration, Path(options.file).expanduser().absolute())
	except Refusal as refusal:
		log.error(str(refusal))
		return FAILURE_CODE
	except psycopg.OperationalError as error:
		log.error(
			_("database unreachable ({production}): {error}").format(
				production=configuration.database.production, error=error
			)
		)
		return FAILURE_CODE
	except psycopg.Error as error:
		log.error(_("database error: {error}").format(error=error))
		return FAILURE_CODE
	return 0


def backup_main(arguments: Sequence[str] | None = None) -> int:
	return launch(BACKUP_EXECUTABLE, BACKUP_DESCRIPTION, arguments, run_backup, backup_options)


def restore_main(arguments: Sequence[str] | None = None) -> int:
	return launch(RESTORE_EXECUTABLE, RESTORE_DESCRIPTION, arguments, run_restore, restore_options)
