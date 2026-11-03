"""Maintenance de la base de données : Machin maintenance-db (https://github.com/dascritch/machincast/issues/127).

Sur la base de production de la configuration, trois étapes, dans l'ordre :

1. sauvegarde : pg_dump, au format personnalisé de PostgreSQL, dans un fichier daté du répertoire des sauvegardes
   (--backups, par défaut « sauvegardes » à côté du fichier de configuration), lisible par pg_restore. Une
   sauvegarde qui échoue arrête tout : rien n'est modifié sans sauvegarde ;
2. schéma : les migrations manquantes sont appliquées, puis chaque rôle de MachinCast doit être endossable par le
   compte ; un rôle qui ne l'est pas est signalé avec les commandes, à lancer par un administrateur, qui l'autorisent ;
3. optimisation : VACUUM (ANALYZE), qui récupère la place des lignes effacées et met à jour les statistiques ;
   la diffusion peut continuer pendant ce temps.

Le compte de MachinCast est propriétaire de la base et de ses tables : il fait tout cela sans endosser de rôle, et
sans droit particulier sur le serveur. Avec --keep-open, la maintenance finie ne rend la main qu'à la fermeture
de son terminal (fin de l'entrée standard, ou Ctrl-C) : la fenêtre ouverte par l'interface reste lisible, Entrée n'y
fait rien. Le code de sortie est 0 si tout s'est bien passé,
1 sinon.
"""

import argparse
import getpass
import logging
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import psycopg

from machincast.cli import launch
from machincast.clock import Clock, SystemClock
from machincast.configuration import Configuration
from machincast.database import OutdatedSchema, Role, apply_migrations, url_yoyo
from machincast.protection import check_writing

EXECUTABLE = "Machin_maintenance-db"
DESCRIPTION = "Sauvegarde, vérifie et optimise la base de données de MachinCast."
FAILURE_CODE = 1
BACKUPS = "sauvegardes"
"""Répertoire des sauvegardes, à côté du fichier de configuration, sauf --backups."""
BACKUP_DELAY = 3600
"""Secondes laissées à pg_dump : une grosse base, sur un disque lent, prend du temps."""
ROLES: tuple[str, ...] = tuple(role.value for role in Role)
"""Les rôles que le compte doit pouvoir endosser."""
CLOCK: Clock = SystemClock()
"""L'heure qui date les sauvegardes ; les scénarios la fixent."""
END = "Maintenance finie : cette fenêtre reste ouverte, la fermer quand vous voulez."

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
log = logging.getLogger("machincast.maintenance")


class BackupFailure(Exception):
	"""La sauvegarde n'a pas pu être faite : la maintenance s'arrête."""


def default_backups(configuration_file: Path) -> Path:
	"""Le répertoire des sauvegardes sans --backups : « sauvegardes », à côté du fichier de configuration."""
	return configuration_file.parent / BACKUPS


def account() -> str:
	"""Le compte qui lance la maintenance, celui de MachinCast."""
	return getpass.getuser()


def back_up(configuration: Configuration, directory: Path) -> Path:
	"""pg_dump de la base de production dans un nouveau fichier daté ; lève BackupFailure."""
	database = configuration.database
	command = shutil.which("pg_dump")
	if command is None:
		raise BackupFailure("pg_dump introuvable, installer postgresql-client")
	timestamp = f"{CLOCK.now().astimezone():%Y-%m-%dT%H-%M-%S}"
	file = directory / f"{database.production}-{timestamp}.dump"
	log.info(f"sauvegarde de la base {database.production} dans {file}")
	check_writing(file)
	if file.exists():
		raise BackupFailure(f"{file} existe déjà, relancer dans une seconde")
	try:
		directory.mkdir(parents=True, exist_ok=True)
		result = subprocess.run(
			[command, "--format=custom", f"--file={file}", f"--host={database.socket}", database.production],
			capture_output=True,
			text=True,
			timeout=BACKUP_DELAY,
			stdin=subprocess.DEVNULL,
		)
	except (OSError, subprocess.SubprocessError) as error:
		raise BackupFailure(str(error)) from error
	if result.returncode != 0:
		raise BackupFailure(result.stderr.strip())
	size = file.stat().st_size / 1_000_000
	log.info(f"sauvegarde faite : {size:.1f} Mo".replace(".", ","))
	return file


def update_schema(configuration: Configuration) -> None:
	"""Les migrations manquantes ; aucune si le schéma est à jour."""
	database = configuration.database
	count = apply_migrations(url_yoyo(database.socket, database.production), database.production)
	if count == 0:
		log.info(f"schéma de la base {database.production} à jour")
		return
	plural = "s" if count > 1 else ""
	log.info(f"schéma de la base {database.production} : {count} migration{plural} appliquée{plural}")


def check_roles(connection: psycopg.Connection[tuple[object, ...]]) -> bool:
	"""Chaque rôle de MachinCast existe, et le compte peut l'endosser ; sinon, ce qu'un administrateur doit faire."""
	in_order = True
	for role in ROLES:
		line = connection.execute(
			"SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s)"
			" AND pg_has_role(current_user, (SELECT oid FROM pg_roles WHERE rolname = %s), 'SET')",
			(role, role),
		).fetchone()
		if (line is not None) and (line[0] is True):
			continue
		in_order = False
		log.error(
			f"rôle {role} : absent du serveur, ou non endossable par le compte ; à faire par un administrateur :"
			f' sudo -u postgres psql -c "CREATE ROLE {role} NOLOGIN" ;'
			f' sudo -u postgres psql -c "GRANT {role} TO {account()} WITH INHERIT FALSE, SET TRUE"'
		)
	if in_order:
		log.info(f"rôles {', '.join(ROLES)} endossables par le compte")
	return in_order


def optimise(connection: psycopg.Connection[tuple[object, ...]], name: str) -> None:
	"""VACUUM ne s'exécute pas dans une transaction : la connexion est en autocommit."""
	connection.execute("VACUUM (ANALYZE)")
	log.info(f"base {name} optimisée (VACUUM ANALYZE)")


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
		help=f"répertoire des sauvegardes ; par défaut « {BACKUPS} », à côté du fichier de configuration",
	)
	analyser.add_argument(
		"--keep-open",
		action="store_true",
		help="garde le terminal ouvert à la fin, jusqu'à sa fermeture : pour la fenêtre qu'ouvre l'interface",
	)


def stay_open() -> None:
	"""Jusqu'à la fermeture du terminal : la fin de l'entrée standard, ou Ctrl-C. Fermer la fenêtre envoie SIGHUP,
	qui arrête aussi le programme."""
	sys.stdout.write(f"{END}\n")
	sys.stdout.flush()
	try:
		sys.stdin.read()
	except KeyboardInterrupt:
		sys.stdout.write("\n")


def run(configuration: Configuration, options: argparse.Namespace) -> int:
	directory = (options.backups) or (default_backups(configuration.path))
	code = FAILURE_CODE
	try:
		if maintain(configuration, Path(directory).expanduser()):
			log.info("maintenance terminée")
			code = 0
		else:
			log.info("maintenance terminée, avec des anomalies")
	except BackupFailure as error:
		log.error(f"sauvegarde impossible : {error} ; maintenance arrêtée, rien n'a été modifié")
	except OutdatedSchema as error:
		log.error(f"schéma impossible à mettre à jour : {error} ; la sauvegarde est faite, rien d'autre")
	except psycopg.OperationalError as error:
		log.error(f"base de données injoignable ({configuration.database.production}) : {error}")
	except psycopg.Error as error:
		log.error(f"erreur de base de données : {error}")
	if options.keep_open:
		stay_open()
	return code


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, run, own_options)
