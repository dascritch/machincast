"""La liste des fichiers créés par MachinCast (https://github.com/dascritch/machincast/issues/652).

	python3 -m machincast.created_files --list LISTE add FICHIER…      inscrit les fichiers, existants ou à venir
	python3 -m machincast.created_files --list LISTE forget FICHIER…   les retire de la liste
	python3 -m machincast.created_files --list LISTE adopt FICHIER…    inscrit ceux qui existent, et les écrit
	python3 -m machincast.created_files --list LISTE check FICHIER…    code 1 si l'un existe hors de la liste

La liste, fichiers-machincast.txt, est à côté du fichier de configuration : un chemin absolu par ligne, triés, sans
doublon. Elle dit les fichiers que MachinCast a créés, les seuls qu'il modifie, remplace ou efface, et ceux à
sauvegarder pour une reprise d'activité : la configuration et les réglages (machincast.toml, vues.ini, unités et
règles installées, raccourcis), et les données (sorties, exports, rapports, sauvegardes de la base). N'y sont pas : les
logs, les fichiers d'exécution (sockets, PID, rapports de plantage, fichiers temporaires), le venv et le dépôt.

Avant d'écrire, de remplacer ou d'effacer un de ces fichiers, MachinCast appelle check : un fichier qui existe hors de
la liste est refusé (NotCreatedByMachinCast), jamais touché. Un fichier qui n'existe pas encore se crée, puis
s'inscrit (record) ; effacé, il quitte la liste (forget). Les binaires tiennent la liste de leur configuration
(use, dans machincast.cli.launch) ; sans configuration chargée, il n'y a pas de liste, et rien n'est vérifié.

Plusieurs comptes l'écrivent, avec le service installé : celui de MachinCast et celui du service, par son groupe, au
mode que tmpfiles lui donne (machincast.installation.tmpfiles). Elle se réécrit donc en place, jamais remplacée, sous
un verrou (flock).

Ce module n'emploie que la bibliothèque standard, et machincast.i18n : install.sh le lance avec le python3 du système.
"""

import argparse
import fcntl
import os
import sys
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import IO

from machincast.i18n import _

NAME = "fichiers-machincast.txt"
"""Le nom de la liste, dans le répertoire du fichier de configuration."""

LIST: Path | None = None
"""La liste en cours, celle de la configuration chargée ; None sans configuration."""
CONFIGURATION: Path | None = None
"""La configuration chargée, toujours permise."""
ENVIRONMENT = "MACHINCAST_CREATED_FILES"
"""La liste qu'imposent les tests, à eux et aux binaires qu'ils lancent : jamais à côté d'une configuration du dépôt."""


class NotCreatedByMachinCast(PermissionError):
	"""Un fichier qui existe, mais que MachinCast n'a pas créé : il ne le modifie, ne le remplace ni ne l'efface."""


def beside(configuration: Path) -> Path:
	"""La liste d'un fichier de configuration."""
	return absolute(configuration).parent / NAME


def use(configuration: Path | None) -> None:
	"""La liste de cette configuration devient celle en cours ; None : plus de liste. La configuration elle-même est
	permise : désignée à MachinCast, elle est la sienne, qu'install.sh l'ait créée ou qu'on l'ait copiée du modèle ;
	elle s'inscrit à sa première écriture."""
	# La liste du processus, comme le fichier des vues (columns.FILE).
	global LIST, CONFIGURATION
	LIST = None
	CONFIGURATION = None
	if configuration is not None:
		LIST = beside(configuration)
		forced = os.environ.get(ENVIRONMENT, "")
		if forced != "":
			LIST = Path(forced)
		CONFIGURATION = absolute(configuration)


def absolute(path: Path) -> Path:
	"""Le chemin absolu, sans résoudre les liens : celui qu'on sauvegarde, comme on l'a écrit."""
	return Path(os.path.abspath(path))


@contextmanager
def _locked(listing: Path) -> Iterator[IO[str]]:
	"""La liste, ouverte en lecture et écriture, créée au besoin, sous un verrou exclusif."""
	listing.parent.mkdir(parents=True, exist_ok=True)
	with listing.open("a+", encoding="utf-8") as file:
		fcntl.flock(file, fcntl.LOCK_EX)
		try:
			file.seek(0)
			yield file
		finally:
			fcntl.flock(file, fcntl.LOCK_UN)


def _lines(file: IO[str]) -> set[str]:
	found = set()
	for line in file.read().splitlines():
		if line.strip() != "":
			found.add(line.strip())
	return found


def _rewrite(file: IO[str], lines: set[str]) -> None:
	"""Réécrite en place : le fichier garde son propriétaire, son groupe et son mode."""
	file.seek(0)
	file.truncate()
	for line in sorted(lines):
		file.write(line + "\n")
	file.flush()


def listed(path: Path, listing: Path | None = None) -> bool:
	"""Le fichier est-il dans la liste ? Sans liste, tout est permis."""
	listing = (listing) or (LIST)
	if listing is None:
		return True
	if not listing.exists():
		return False
	with listing.open(encoding="utf-8") as file:
		# Partagé : jamais lue pendant qu'un autre compte la réécrit, vidée puis remplie.
		fcntl.flock(file, fcntl.LOCK_SH)
		try:
			return str(absolute(path)) in _lines(file)
		finally:
			fcntl.flock(file, fcntl.LOCK_UN)


def check(path: Path, listing: Path | None = None) -> None:
	"""À appeler avant de modifier, remplacer ou effacer un fichier : refuse celui qui existe hors de la liste."""
	listing = (listing) or (LIST)
	if (listing is None) or (not path.exists()) or (absolute(path) == CONFIGURATION) or (listed(path, listing)):
		return
	raise NotCreatedByMachinCast(
		_("{path}: not created by MachinCast, it is not in {listing}: MachinCast does not touch it").format(
			path=absolute(path), listing=listing
		)
	)


def record(paths: Iterable[Path], listing: Path | None = None) -> None:
	"""Inscrit les fichiers créés par MachinCast."""
	listing = (listing) or (LIST)
	if listing is None:
		return
	with _locked(listing) as file:
		lines = _lines(file)
		before = len(lines)
		for path in paths:
			lines.add(str(absolute(path)))
		if len(lines) != before:
			_rewrite(file, lines)


def forget(paths: Iterable[Path], listing: Path | None = None) -> None:
	"""Retire de la liste des fichiers que MachinCast a effacés."""
	listing = (listing) or (LIST)
	if (listing is None) or (not listing.exists()):
		return
	with _locked(listing) as file:
		lines = _lines(file)
		before = len(lines)
		for path in paths:
			lines.discard(str(absolute(path)))
		if len(lines) != before:
			_rewrite(file, lines)


def adopt(paths: Iterable[Path], listing: Path) -> list[Path]:
	"""Inscrit les fichiers qui existent déjà, créés par une version d'avant la liste ; renvoie ceux qui n'y étaient
	pas."""
	adopted = []
	for path in paths:
		if (path.is_file()) and (not listed(path, listing)):
			adopted.append(absolute(path))
	record(adopted, listing)
	return adopted


def write_text(path: Path, text: str, *, encoding: str = "utf-8", newline: str | None = None) -> None:
	"""Écrit un fichier de MachinCast : refusé s'il existe hors de la liste, inscrit ensuite."""
	check(path)
	path.write_text(text, encoding=encoding, newline=newline)
	record([path])


def delete(path: Path) -> None:
	"""Efface un fichier de MachinCast : refusé s'il existe hors de la liste, retiré de la liste ensuite."""
	check(path)
	# fichier de MachinCast : inscrit dans la liste des fichiers créés, que check vient de vérifier.
	path.unlink(missing_ok=True)
	forget([path])


def main(arguments: Sequence[str] | None = None) -> int:
	analyser = argparse.ArgumentParser(prog="machincast.created_files", description=__doc__)
	analyser.add_argument("--list", type=Path, required=True, dest="listing")
	analyser.add_argument("action", choices=("add", "forget", "adopt", "check"))
	analyser.add_argument("files", type=Path, nargs="*")
	options = analyser.parse_args(arguments)
	if options.action == "add":
		record(options.files, options.listing)
	if options.action == "forget":
		forget(options.files, options.listing)
	if options.action == "adopt":
		for path in adopt(options.files, options.listing):
			sys.stdout.write(f"{path}\n")
	if options.action == "check":
		for path in options.files:
			try:
				check(path, options.listing)
			except NotCreatedByMachinCast as error:
				sys.stderr.write(f"{error}\n")
				return 1
	return 0


if __name__ == "__main__":
	sys.exit(main())
