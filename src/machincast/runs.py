"""Démarrages et fins des binaires, dans le journal et dans le log de la base
(https://github.com/dascritch/machincast/issues/341).

Machin indexer, Machin maintenance-db et Machin purge notent chacun de leurs lancements, comme Machin player le fait
déjà, pour que l'administrateur y retrouve un plantage ou une fausse manœuvre :

- leur démarrage, ligne « start » du log, au niveau info : « Machin_indexer 0.9.0, pid 1234: --full-audit », le
  binaire, sa version, son pid et ses options ;
- leur fin, ligne « end » : « Machin_indexer, pid 1234: exit code 0 », au niveau info pour le code 0, en incident pour
  tout autre code, comme le 2 d'une option refusée ;
- un plantage probable, en incident, quand le démarrage précédent du même binaire n'a pas noté sa fin et que son
  processus ne tourne plus : arrêté par un signal, tué, ou le poste éteint en cours de route.

Un lancement dont la configuration est illisible ne sait pas quelle base joindre : seul le journal en parle. Une base
injoignable n'empêche pas le binaire de tourner : le journal dit que son démarrage n'a pas pu être noté, et sa fin ne
l'est pas non plus.

Le log garde ces textes en anglais ; l'interface les traduit à l'affichage (machincast.i18n.logged).
"""

import argparse
import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast import __version__
from machincast.configuration import Database
from machincast.database import Role, open_connection
from machincast.i18n import N_, _, logged
from machincast.player.saving import record

log = logging.getLogger(__name__)

START = N_("start")
END = N_("end")
PROBABLE_CRASH = N_("probable crash")
START_MESSAGE = N_("{program} {version}, pid {pid}")
START_WITH_OPTIONS = N_("{program} {version}, pid {pid}: {options}")
END_MESSAGE = N_("{program}, pid {pid}: exit code {code}")
CRASH_MESSAGE = N_("{program}, pid {pid}, started on {start}, did not log its end")
INTERRUPTED_CODE = 130
"""Le code d'un programme arrêté par Ctrl-C, comme le donne le shell."""
PROC_STAT = Path("/proc/stat")


def _always(_options: argparse.Namespace) -> bool:
	return True


@dataclass(frozen=True)
class Recording:
	"""Comment un binaire note ses lancements."""

	role: Role | None
	"""Le rôle qui écrit le log ; None pour le compte propriétaire de la base, comme la purge et la maintenance."""
	when: Callable[[argparse.Namespace], bool] = field(default=_always)
	"""Les lancements à noter, selon leurs options : pas la vérification d'un seul sonore que Machin player demande
	avant chaque sonore."""


def start_text(program: str, pid: int, arguments: Sequence[str]) -> str:
	"""« Machin_indexer 0.9.0, pid 1234: --full-audit »."""
	if arguments:
		return START_WITH_OPTIONS.format(program=program, version=__version__, pid=pid, options=" ".join(arguments))
	return START_MESSAGE.format(program=program, version=__version__, pid=pid)


def boot(path: Path = PROC_STAT) -> datetime:
	"""Le démarrage du poste, d'après le noyau ; le plus ancien instant possible s'il est illisible."""
	try:
		for line in path.read_text(encoding="ascii").splitlines():
			if line.startswith("btime "):
				return datetime.fromtimestamp(int(line.split()[1]), tz=UTC)
	except (OSError, ValueError):
		pass
	return datetime.min.replace(tzinfo=UTC)


def alive(pid: int, since: datetime) -> bool:
	"""Le processus de ce démarrage tourne encore : son pid existe, et le démarrage est d'après celui du poste, sans
	quoi le pid serait celui d'un autre processus."""
	if since < boot():
		return False
	try:
		os.kill(pid, 0)
	except ProcessLookupError:
		return False
	except PermissionError:
		return True
	return True


def _connect(database: Database, role: Role | None) -> psycopg.Connection[TupleRow]:
	if role is None:
		return psycopg.connect(host=str(database.socket), dbname=database.production)
	return open_connection(database.socket, database.production, role)


def _check_previous(connection: psycopg.Connection[TupleRow], program: str) -> None:
	"""Un incident si le démarrage précédent de ce binaire n'a pas de fin et que son processus ne tourne plus."""
	with connection.transaction():
		previous = connection.execute(
			"SELECT started_at, pid, ended FROM machincast_previous_start(%s)", (program,)
		).fetchone()
	if previous is None:
		return
	started_at, previous_pid, finished = previous
	if (finished) or (alive(previous_pid, started_at)):
		return
	message = CRASH_MESSAGE.format(program=program, pid=previous_pid, start=f"{started_at.astimezone():%Y-%m-%d %H:%M}")
	record(connection, "incident", PROBABLE_CRASH, message)


def started(database: Database, program: str, arguments: Sequence[str], role: Role | None) -> bool:
	"""Note le démarrage, dans le journal et dans le log de la base, après un plantage probable du lancement
	précédent ; faux si la base n'a pas pu le noter."""
	pid = os.getpid()
	text = start_text(program, pid, arguments)
	log.info(_("{kind}: {message}").format(kind=_(START), message=logged(text)))
	try:
		with _connect(database, role) as connection:
			_check_previous(connection, program)
			record(connection, "info", START, text)
	except psycopg.Error as error:
		log.warning(_("{program}: start not logged in the database: {error}").format(program=program, error=error))
		return False
	return True


def ended(database: Database, program: str, code: int, role: Role | None) -> None:
	"""Note la fin et son code de sortie ; en incident pour tout autre code que 0."""
	message = END_MESSAGE.format(program=program, pid=os.getpid(), code=code)
	level = "info"
	if code == 0:
		log.info(_("{kind}: {message}").format(kind=_(END), message=logged(message)))
	else:
		# record l'écrit aussi dans le journal, comme toute alerte ou tout incident.
		level = "incident"
	try:
		with _connect(database, role) as connection:
			record(connection, level, END, message)
	except psycopg.Error as error:
		if level != "info":
			# Base injoignable : record n'a rien écrit, pas même au journal.
			log.warning(_("{kind}: {message}").format(kind=_(END), message=logged(message)))
		log.warning(_("{program}: end not logged in the database: {error}").format(program=program, error=error))


def _exit_code(exit: SystemExit) -> int:
	if exit.code is None:
		return 0
	if isinstance(exit.code, int):
		return exit.code
	return 1


def recorded(
	database: Database, program: str, arguments: Sequence[str], role: Role | None, action: Callable[[], int]
) -> int:
	"""Lance l'action entre son démarrage et sa fin, notés ; une exception qui l'interrompt donne le code 1, Ctrl-C le
	code 130, et passe."""
	noted = started(database, program, arguments, role)
	code = 1
	try:
		code = action()
	except KeyboardInterrupt:
		code = INTERRUPTED_CODE
		raise
	except SystemExit as exit:
		code = _exit_code(exit)
		raise
	finally:
		if noted:
			ended(database, program, code, role)
	return code
