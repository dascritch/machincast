"""Maintenance de la base de données : Machin maintenance-db (https://github.com/dascritch/machincast/issues/127).

Sur la base de production de la configuration, trois étapes, dans l'ordre :

1. sauvegarde : pg_dump, au format personnalisé de PostgreSQL, dans un fichier daté du répertoire des sauvegardes
   (--backups, par défaut backup.directory de la configuration, le répertoire personnel du compte sans elle,
   https://github.com/dascritch/machincast/issues/347), lisible par pg_restore et par Machin restore-db. Une
   sauvegarde qui échoue arrête tout : rien n'est modifié sans sauvegarde ;
2. schéma : les migrations manquantes du cœur sont appliquées ; celles des plugins, leur install.sh les applique
   (https://github.com/dascritch/machincast/issues/586), puis chaque rôle de MachinCast doit être endossable par le
   compte ; un rôle qui ne l'est pas est signalé avec les commandes, à lancer par un administrateur, qui l'autorisent ;
3. optimisation : VACUUM (ANALYZE), qui récupère la place des lignes effacées et met à jour les statistiques ;
   la diffusion peut continuer pendant ce temps.

Le compte de MachinCast est propriétaire de la base et de ses tables : il fait tout cela sans endosser de rôle, et
sans droit particulier sur le serveur. Avec --keep-open, la maintenance finie ne rend la main qu'à la fermeture
de son terminal (fin de l'entrée standard, ou Ctrl-C) : la fenêtre ouverte par l'interface reste lisible, Entrée n'y
fait rien ; la fin de la maintenance est notée avant (https://github.com/dascritch/machincast/issues/341). Le code de
sortie est 0 si tout s'est bien passé, 1 sinon. Le démarrage et la fin de chaque maintenance sont notés au journal et
au log de la base (machincast.runs) ; la base qui n'a pas encore le schéma de MachinCast ne peut pas noter le
démarrage.
"""

import argparse
import getpass
import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import psycopg

from machincast import admin_queries, created_files
from machincast.cli import launch
from machincast.clock import Clock, SystemClock
from machincast.configuration import Configuration, Database
from machincast.database import Role, apply_migrations, url_yoyo
from machincast.i18n import _, decimal, ngettext
from machincast.protection import check_writing
from machincast.runs import Recording

EXECUTABLE = "Machin_maintenance-db"
DESCRIPTION = _("Backs up, checks and optimises the MachinCast database.")
FAILURE_CODE = 1
RECORDING = Recording(role=None)
"""Le démarrage et la fin de la maintenance, dans le log, par le compte propriétaire de la base
(https://github.com/dascritch/machincast/issues/341)."""
BACKUP_DELAY = 3600
"""Secondes laissées à pg_dump : une grosse base, sur un disque lent, prend du temps."""
BACKUP_UMASK = 0o077
"""Une sauvegarde naît en 0600 : elle contient tout, empreintes des mots de passe de l'intranet comprises."""


def _role_names() -> tuple[str, ...]:
	names = []
	for role in Role:
		names.append(role.value)
	return tuple(names)


ROLES = _role_names()
"""Les rôles que le compte doit pouvoir endosser."""
CLOCK: Clock = SystemClock()
"""L'heure qui date les sauvegardes ; les scénarios la fixent."""
END = _("Maintenance finished: this window stays open, close it whenever you want.")

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
log = logging.getLogger("machincast.maintenance")


POSTGRESQL = Path("/usr/lib/postgresql")
"""Les versions de PostgreSQL installées par les paquets, chacune avec ses programmes."""


class BackupFailure(Exception):
	"""La sauvegarde n'a pas pu être faite : la maintenance s'arrête."""


def account() -> str:
	"""Le compte qui lance la maintenance, celui de MachinCast."""
	return getpass.getuser()


def tool(name: str, version: int | None, root: Path | None = None) -> str | None:
	"""Le programme de PostgreSQL de cette version majeure, comme les paquets Debian et Ubuntu l'installent
	(/usr/lib/postgresql/<version>/bin), sinon celui du PATH (https://github.com/dascritch/machincast/issues/384) :
	le pg_dump du PATH est le plus récent installé, et sa sauvegarde ne se relirait pas avec le pg_restore du serveur,
	plus ancien (« unsupported version (1.16) in file header »)."""
	if version is not None:
		candidate = ((root) or (POSTGRESQL)) / str(version) / "bin" / name
		if os.access(candidate, os.X_OK):
			return str(candidate)
	return shutil.which(name)


def server_version(database: Database) -> int | None:
	"""La version majeure du serveur de la base de production ; None s'il est injoignable."""
	try:
		with psycopg.connect(host=str(database.socket), dbname=database.production) as connection:
			number = admin_queries.server_version(connection)
	except psycopg.Error:
		return None
	if number is None:
		return None
	return number // 10000


def back_up(configuration: Configuration, directory: Path) -> Path:
	"""pg_dump de la version du serveur, sur la base de production, dans un nouveau fichier daté ; lève
	BackupFailure."""
	database = configuration.database
	command = tool("pg_dump", server_version(database))
	if command is None:
		raise BackupFailure(_("pg_dump not found, install postgresql-client"))
	timestamp = f"{CLOCK.now().astimezone():%Y-%m-%dT%H-%M-%S}"
	file = directory / f"{database.production}-{timestamp}.dump"
	log.info(_("backup of database {production} into {file}").format(production=database.production, file=file))
	check_writing(file)
	if file.exists():
		raise BackupFailure(_("{file} already exists, run again in a second").format(file=file))
	try:
		directory.mkdir(parents=True, exist_ok=True)
		result = subprocess.run(
			[command, "--format=custom", f"--file={file}", f"--host={database.socket}", database.production],
			capture_output=True,
			text=True,
			timeout=BACKUP_DELAY,
			stdin=subprocess.DEVNULL,
			check=False,
			# La sauvegarde garde les empreintes des mots de passe de l'intranet : lisible du seul compte
			# (https://github.com/dascritch/machincast/issues/553).
			umask=BACKUP_UMASK,
		)
	except (OSError, subprocess.SubprocessError) as error:
		raise BackupFailure(str(error)) from error
	if result.returncode != 0:
		raise BackupFailure(result.stderr.strip())
	# Une sauvegarde à garder pour une reprise d'activité (https://github.com/dascritch/machincast/issues/652).
	created_files.record([file])
	size = file.stat().st_size / 1_000_000
	log.info(_("backup done: {size} MB").format(size=decimal(f"{size:.1f}")))
	return file


def update_schema(configuration: Configuration) -> None:
	"""Les migrations manquantes du cœur ; aucune si le schéma est à jour. Celles des plugins, leur install.sh les
	applique (https://github.com/dascritch/machincast/issues/587)."""
	database = configuration.database
	count = apply_migrations(url_yoyo(database.socket, database.production))
	if count == 0:
		log.info(_("schema of database {production} up to date").format(production=database.production))
	else:
		log.info(
			ngettext(
				"schema of database {production}: {count} migration applied",
				"schema of database {production}: {count} migrations applied",
				count,
			).format(production=database.production, count=count)
		)


def check_roles(connection: psycopg.Connection[tuple[object, ...]]) -> bool:
	"""Chaque rôle de MachinCast existe, et le compte peut l'endosser ; sinon, ce qu'un administrateur doit faire."""
	in_order = True

	def check_role(role: str) -> None:
		nonlocal in_order
		if admin_queries.role_assumable(connection, role):
			return
		in_order = False
		log.error(
			_(
				"role {role}: missing from the server, or not assumable by the account; to be done by an "
				'administrator: sudo -u postgres psql -c "CREATE ROLE {role} NOLOGIN" ; sudo -u postgres '
				'psql -c "GRANT {role} TO {account} WITH INHERIT FALSE, SET TRUE"'
			).format(role=role, account=account())
		)

	for role in ROLES:
		check_role(role)
	if in_order:
		log.info(_("roles {list} assumable by the account").format(list=", ".join(ROLES)))
	return in_order


def optimise(connection: psycopg.Connection[tuple[object, ...]], name: str) -> None:
	"""Optimise la base ; VACUUM ne s'exécute pas dans une transaction : la connexion est en autocommit."""
	admin_queries.vacuum(connection)
	log.info(_("database {name} optimised (VACUUM ANALYZE)").format(name=name))


def maintain(configuration: Configuration, directory: Path) -> bool:
	"""Les trois étapes ; vrai si tout s'est bien passé. Lève BackupFailure, psycopg.Error."""
	database = configuration.database
	back_up(configuration, directory)
	update_schema(configuration)
	with psycopg.connect(host=str(database.socket), dbname=database.production, autocommit=True) as connection:
		roles = check_roles(connection)
		optimise(connection, database.production)
	return roles


def own_options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument(
		"--backups",
		type=Path,
		metavar="REPERTOIRE",
		help=_("directory of the backup; by default backup.directory of the configuration"),
	)
	analyser.add_argument(
		"--keep-open",
		action="store_true",
		help=_("keeps the terminal open at the end, until it is closed: for the window that the interface opens"),
	)


def stay_open(said: str = END) -> None:
	"""Jusqu'à la fermeture du terminal : la fin de l'entrée standard, ou Ctrl-C. Fermer la fenêtre envoie SIGHUP,
	qui arrête aussi le programme."""
	sys.stdout.write(f"{said}\n")
	sys.stdout.flush()
	try:
		sys.stdin.read()
	except KeyboardInterrupt:
		sys.stdout.write("\n")


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	"""Lance la maintenance de la base, sauvegarde d'abord ; le code de sortie, nul si tout s'est bien passé."""
	directory = (options.backups) or (configuration.backup.directory)
	code = FAILURE_CODE
	try:
		if maintain(configuration, Path(directory).expanduser()):
			log.info(_("maintenance finished"))
			code = 0
		else:
			log.info(_("maintenance finished, with anomalies"))
	except BackupFailure as error:
		log.error(_("backup impossible: {error}; maintenance stopped, nothing was changed").format(error=error))
	except psycopg.OperationalError as error:
		log.error(
			_("database unreachable ({production}): {error}").format(
				production=configuration.database.production, error=error
			)
		)
	except psycopg.Error as error:
		log.error(_("database error: {error}").format(error=error))
	return code


def after(options: argparse.Namespace) -> None:
	"""Après la fin, notée au log : le terminal qu'ouvre l'interface reste ouvert, sans que la maintenance soit encore
	en cours pour le log."""
	if options.keep_open:
		stay_open()


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, own_options, recording=RECORDING, then=after)
