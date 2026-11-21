"""Les sonores des répertoires personnels, à l'installation du service (https://github.com/dascritch/machincast/issues/381).

Le service de diffusion ne lit jamais un répertoire personnel (machincast.access.personal_home) : ni MachinCast ni
install.sh n'en changent les droits. Les répertoires de banque et les fichiers ajoutés qui y sont, d'après la base de
production, ne passeraient pas à l'antenne. install.sh --service les liste, puis, au choix de l'administrateur :

- les déplace dans le répertoire d'accueil des sonores, /home/machincast (machincast.access.welcome), à son compte et au
  groupe machincast, que le service lit : un répertoire de banque y garde son nom, un fichier ajouté va dans
  « fichiers » ; un nom déjà pris reçoit un suffixe, « -2 », « -3 »… Les emplacements de la base suivent, en une seule
  transaction ; si elle échoue, les fichiers reviennent à leur place. C'est la seule exception à
  https://github.com/dascritch/machincast/issues/96, acceptée explicitement, à chaque fois ;
- ou les retire de la base : les sonores y sont supprimés, comme depuis l'interface, et les répertoires retirés de
  leur banque ; aucun fichier n'est touché ;
- ou les laisse : le service ne les jouera pas, et le dit dans le log.

Seuls les chemins du compte qui installe se déplacent : celui d'un autre compte est signalé, à déplacer par lui.
Les requêtes se font avec le compte de MachinCast, propriétaire de la base, sans endosser de rôle, comme la purge.
"""

import errno
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast import access, admin_queries
from machincast.i18n import _

FILES = "fichiers"
"""Le sous-répertoire du répertoire d'accueil où vont les fichiers ajoutés hors d'une banque."""

log = logging.getLogger("machincast.personal")


@dataclass(frozen=True)
class Found:
	"""Ce que la base a dans des répertoires personnels : les répertoires des banques actives, les fichiers des
	sonores actifs hors de ces répertoires."""

	directories: list[Path]
	files: list[Path]

	def empty(self) -> bool:
		return (self.directories == []) and (self.files == [])


@dataclass(frozen=True)
class Move:
	source: Path
	target: Path


def _inside(path: Path, directory: Path) -> bool:
	return (path == directory) or (directory in path.parents)


def _closed(path: Path, account: access.Account | None) -> bool:
	"""Vrai si le service ne lit pas le chemin, ou ce qu'il contient ; toujours vrai sans compte du service."""
	if account is None:
		return True
	if path.is_dir():
		return access.unreadable_inside(path, account) != []
	return not access.readable(path, account)


def find(connection: psycopg.Connection[TupleRow]) -> Found:
	"""Ce que la base a dans des répertoires personnels, et que le service ne lit pas : ce qu'il lit déjà, ouvert par
	l'administrateur du poste, reste en place."""
	account = access.service_account()
	directories: list[Path] = []
	for (directory,) in admin_queries.bank_directories(connection):
		path = Path(str(directory))
		if (access.personal_home(path) is not None) and (_closed(path, account)):
			directories.append(path)
	files: list[Path] = []
	for (location,) in admin_queries.files(connection):
		path = Path(str(location))
		if (access.personal_home(path) is not None) and (not _in_any(path, directories)) and (_closed(path, account)):
			files.append(path)
	return Found(directories, files)


def _in_any(path: Path, directories: list[Path]) -> bool:
	for directory in directories:
		if _inside(path, directory):
			return True
	return False


def _free(target: Path, taken: set[Path]) -> Path:
	"""Le premier nom libre : celui du fichier, puis avec « -2 », « -3 »… avant son extension."""
	candidate = target
	number = 1
	while (candidate.exists()) or (candidate in taken):
		number += 1
		candidate = target.with_name(f"{target.stem}-{number}{target.suffix}")
	taken.add(candidate)
	return candidate


def plan(found: Found, welcome: Path) -> list[Move]:
	"""Les déplacements : chaque répertoire de banque qui n'est pas dans un autre, et chaque fichier ajouté."""
	moves: list[Move] = []
	taken: set[Path] = set()
	tops: list[Path] = []
	for directory in found.directories:
		if not _in_any(directory, tops):
			tops.append(directory)
	for directory in tops:
		moves.append(Move(directory, _free(welcome / directory.name, taken)))
	for file in found.files:
		moves.append(Move(file, _free(welcome / FILES / file.name, taken)))
	return moves


def foreign(moves: list[Move]) -> list[Path]:
	"""Les sources qui ne sont pas au compte qui installe, ou absentes : elles ne se déplacent pas."""
	found = []
	uid = os.getuid()
	for move in moves:
		try:
			owner = move.source.lstat().st_uid
		except OSError:
			found.append(move.source)
		else:
			if owner != uid:
				found.append(move.source)
	return found


def _rename(source: Path, target: Path) -> None:
	target.parent.mkdir(parents=True, exist_ok=True)
	try:
		# sonore déplacé avec accord : hors d'un répertoire personnel, vers le répertoire d'accueil, ou de retour
		os.rename(source, target)
	except OSError as error:
		if error.errno != errno.EXDEV:
			raise
		# sonore déplacé avec accord : sur un autre système de fichiers, copie, puis retrait de la source, comme mv
		shutil.move(str(source), str(target))


def move(connection: psycopg.Connection[TupleRow], moves: list[Move]) -> None:
	"""Déplace, puis met à jour les emplacements de la base, en une transaction ; si elle échoue, chaque fichier
	revient à sa place."""
	done: list[Move] = []
	try:
		for item in moves:
			_rename(item.source, item.target)
			done.append(item)
			log.info(_("{source} moved to {target}").format(source=item.source, target=item.target))
		with connection.transaction():
			for item in done:
				admin_queries.relocate(connection, str(item.source), str(item.target))
	except BaseException:
		for item in reversed(done):
			_rename(item.target, item.source)
		raise


def forget(connection: psycopg.Connection[TupleRow], found: Found) -> None:
	"""Retire de la base ce qui est dans des répertoires personnels, sans toucher aucun fichier."""
	with connection.transaction():
		for directory in found.directories:
			admin_queries.forget_directory(connection, str(directory))
		for file in found.files:
			admin_queries.forget_file(connection, str(file))
