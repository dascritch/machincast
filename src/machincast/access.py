"""Lecture des sonores par le service de diffusion : Machin grant-read (https://github.com/dascritch/machincast/issues/381).

Le service de diffusion tourne sous son propre compte, machincast (machincast.service.ACCOUNT) : il lit les sonores
des banques et les fichiers ajoutés. Ce module dit si le compte du service peut lire un fichier ou un répertoire, et
le lui permet, hors des arborescences sensibles :

- arborescences sensibles (sensitive_tree) : les répertoires personnels (personal_home : /home, sauf le répertoire
  d'accueil des sonores, /home/machincast, et le répertoire personnel de tout compte humain, /root compris), et les
  arborescences du système (SYSTEM_TREES : /etc, /bin, /sbin, /usr, /media, /mnt…). MachinCast n'y change jamais
  aucun droit ; le service n'y lit que ce que les droits en place lui laissent lire, et jamais un répertoire
  personnel. Le répertoire d'accueil des sonores, /opt, /srv et /var (LIBRARY_TREES) peuvent recevoir une discothèque :
  leur racine ne change jamais et doit déjà se traverser, et les répertoires du système de /var (VAR_SYSTEM : lib,
  log, cache…) restent sensibles ; ailleurs en dessous, la lecture se donne ;
- lire : les répertoires parents se traversent (x), le fichier se lit (r), un répertoire se lit et se traverse (rx).
  Les droits se calculent comme le noyau, d'après le propriétaire, le groupe, les autres, et les ACL POSIX
  (attribut system.posix_acl_access) : entrée nommée du compte, groupes du compte, masque ;
- donner la lecture : par des ACL (setfacl, paquet acl), sans changer ni le propriétaire, ni les droits du groupe et
  des autres, ni le contenu d'aucun fichier (https://github.com/dascritch/machincast/issues/96) : u:machincast:x sur
  les répertoires parents qui ne se traversent pas, u:machincast:rX sur la cible, récursivement pour un répertoire,
  avec l'ACL par défaut d:u:machincast:rX, que reçoivent les fichiers qui s'y ajoutent. Un changement qui toucherait
  une arborescence sensible est refusé, et rien n'est changé. setfacl ne change que les fichiers dont le compte qui le
  lance est propriétaire : un autre répertoire est signalé, avec la commande qu'un administrateur lance.

	Machin grant-read [CHEMIN…]

donne au service la lecture de ces chemins ; sans chemin, celle des répertoires des banques et des fichiers ajoutés de
la base de production.

Le code de sortie est 0 quand le service lit tout, 1 sinon, ou sans compte du service.
"""

import argparse
import grp
import logging
import os
import pwd
import shlex
import stat
import struct
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from machincast import service
from machincast.cli import launch
from machincast.configuration import Configuration
from machincast.database import Role, open_connection
from machincast.i18n import _
from machincast.maintenance import stay_open

EXECUTABLE = "Machin_grant-read"
DESCRIPTION = _("Lets the broadcast service read the sound files.")
FAILURE_CODE = 1
TOOL = "setfacl"
DELAY = 600
"""Secondes laissées à setfacl : un répertoire de banque peut compter des milliers de fichiers."""
ACL_ATTRIBUTE = "system.posix_acl_access"
_HEADER = struct.Struct("<I")
_ENTRY = struct.Struct("<HHI")
USER_OBJ, USER, GROUP_OBJ, GROUP, MASK, OTHER = 0x01, 0x02, 0x04, 0x08, 0x10, 0x20
READ, EXECUTE = 4, 1

log = logging.getLogger("machincast.access")

WELCOME = Path("/home/machincast")
"""Le répertoire d'accueil des sonores, créé par install.sh --service, au compte de MachinCast et au groupe machincast
(mode 2750) : le service le lit sans qu'aucun droit ne change."""
WELCOME_ENVIRONMENT = "MACHINCAST_WELCOME"
PERSONAL_ENVIRONMENT = "MACHINCAST_PERSONAL_HOMES"
"""Des répertoires personnels de plus, séparés par « : » : les scénarios en simulent, sans en retirer aucun."""
HOMES = Path("/home")
SYSTEM_TREES = (
	Path("/bin"),
	Path("/boot"),
	Path("/dev"),
	Path("/etc"),
	Path("/home"),
	Path("/lib"),
	Path("/lib32"),
	Path("/lib64"),
	Path("/libx32"),
	Path("/lost+found"),
	Path("/media"),
	Path("/mnt"),
	Path("/opt"),
	Path("/proc"),
	Path("/root"),
	Path("/run"),
	Path("/sbin"),
	Path("/snap"),
	Path("/srv"),
	Path("/sys"),
	Path("/usr"),
	Path("/var"),
)
"""Les arborescences du système, et celle des répertoires personnels : MachinCast n'y change jamais de droits."""
HUMAN_UID = 1000


def welcome() -> Path:
	return Path((os.environ.get(WELCOME_ENVIRONMENT)) or (str(WELCOME)))


def _real(path: Path) -> Path:
	"""Le chemin absolu, liens symboliques résolus : un lien vers un répertoire personnel y mène."""
	return Path(os.path.realpath(path))


def _homes() -> list[Path]:
	"""Les répertoires personnels : /home et ses répertoires, celui de root, ceux des comptes humains."""
	found = [HOMES, Path("/root")]
	for entry in pwd.getpwall():
		if (entry.pw_uid >= HUMAN_UID) and (entry.pw_dir not in ("", "/", "/nonexistent")):
			found.append(Path(entry.pw_dir))
	for extra in os.environ.get(PERSONAL_ENVIRONMENT, "").split(":"):
		if extra:
			found.append(Path(extra))
	return found


def personal_home(path: Path) -> Path | None:
	"""Le répertoire personnel où est le chemin, liens résolus ; None hors de tout répertoire personnel, et dans le
	répertoire d'accueil des sonores."""
	real = _real(path)
	reception = _real(welcome())
	if (real == reception) or (reception in real.parents):
		return None
	for home in _homes():
		home = _real(home)
		if ((real == home) or (home in real.parents)) and (home == HOMES) and (real != HOMES):
			# Le répertoire personnel lui-même, /home/<compte>, plutôt que /home.
			return HOMES / real.relative_to(HOMES).parts[0]
		if (real == home) or (home in real.parents):
			return home
	return None


LIBRARY_TREES = (Path("/opt"), Path("/srv"), Path("/var"))
"""Les arborescences du système qui peuvent recevoir une discothèque, avec le répertoire d'accueil des sonores : leur
racine ne change jamais, et doit déjà se traverser ; en dessous, Machin grant-read peut donner la lecture."""
VAR_SYSTEM = (
	"backups",
	"cache",
	"crash",
	"lib",
	"lock",
	"log",
	"mail",
	"run",
	"snap",
	"spool",
	"tmp",
)
"""Les répertoires de /var qui sont au système, eux et tout ce qu'ils contiennent : jamais une discothèque."""


def _library_tree(real: Path) -> tuple[bool, Path | None]:
	"""Pour un chemin d'une arborescence de discothèque : vrai, et l'arborescence sensible qu'il touche (la racine de
	l'arborescence, ou un répertoire du système de /var), None en dessous ; faux ailleurs."""
	for tree in (_real(welcome()), *LIBRARY_TREES):
		if real == tree:
			return True, tree
		if tree in real.parents:
			top = tree / real.relative_to(tree).parts[0]
			if (tree == Path("/var")) and (top.name in VAR_SYSTEM):
				return True, top
			return True, None
	return False, None


def sensitive_tree(path: Path) -> Path | None:
	"""L'arborescence sensible où est le chemin, liens résolus : où MachinCast ne change jamais de droits. La racine
	« / » elle-même en est une. Sous /home/machincast, /opt, /srv et /var (hors de ses répertoires du système), seule la
	racine l'est ; None ailleurs."""
	real = _real(path)
	home = personal_home(real)
	if home is not None:
		return home
	library, tree = _library_tree(real)
	if library:
		return tree
	if real == Path("/"):
		return real
	for tree in SYSTEM_TREES:
		if (real == tree) or (tree in real.parents):
			return tree
	return None


@dataclass(frozen=True)
class Account:
	"""Un compte, tel que le noyau l'éprouve : son uid et tous ses groupes."""

	name: str
	uid: int
	groups: frozenset[int]


def service_account(name: str | None = None) -> Account | None:
	"""Le compte du service de diffusion ; None tant que install.sh --service ne l'a pas créé."""
	if name is None:
		name = service.account()
	try:
		entry = pwd.getpwnam(name)
	except KeyError:
		return None
	groups = {entry.pw_gid}
	for group in grp.getgrall():
		if name in group.gr_mem:
			groups.add(group.gr_gid)
	return Account(name, entry.pw_uid, frozenset(groups))


def _acl(path: Path) -> list[tuple[int, int, int]]:
	"""Les entrées de l'ACL d'accès : étiquette, droits, identifiant ; aucune sans ACL."""
	try:
		value = os.getxattr(path, ACL_ATTRIBUTE)
	except OSError:
		return []
	entries = []
	for offset in range(_HEADER.size, len(value) - _ENTRY.size + 1, _ENTRY.size):
		entries.append(_ENTRY.unpack_from(value, offset))
	return entries


def _rights(path: Path, account: Account) -> int:
	"""Les droits du compte sur le chemin, en bits rwx, comme le noyau les accorde."""
	state = path.stat()
	if account.uid == 0:
		return 7
	mode = stat.S_IMODE(state.st_mode)
	if state.st_uid == account.uid:
		return (mode >> 6) & 7
	entries = _acl(path)
	mask = 7
	group_rights = (mode >> 3) & 7
	for tag, rights, _identifier in entries:
		if tag == MASK:
			mask = rights
		if tag == GROUP_OBJ:
			group_rights = rights
	for tag, rights, identifier in entries:
		if (tag == USER) and (identifier == account.uid):
			return rights & mask
	matched = state.st_gid in account.groups
	granted = 0
	if matched:
		granted = group_rights
	for tag, rights, identifier in entries:
		if (tag == GROUP) and (identifier in account.groups):
			matched = True
			granted |= rights
	if matched:
		return granted & mask
	return mode & 7


def _allows(path: Path, account: Account, wanted: int) -> bool:
	try:
		return (_rights(path, account) & wanted) == wanted
	except OSError:
		return False


def blocking(path: Path, account: Account) -> list[Path]:
	"""Ce qui empêche le compte de lire le chemin : les répertoires parents qu'il ne traverse pas, puis le chemin
	lui-même s'il ne le lit pas ; rien s'il le lit."""
	path = Path(os.path.abspath(path))
	found = []
	for parent in reversed(path.parents):
		if not _allows(parent, account, EXECUTE):
			found.append(parent)
	wanted = READ
	if path.is_dir():
		wanted = READ | EXECUTE
	if not _allows(path, account, wanted):
		found.append(path)
	return found


def readable(path: Path, account: Account) -> bool:
	return not blocking(path, account)


def unreadable_inside(directory: Path, account: Account) -> list[Path]:
	"""Les fichiers et répertoires d'un répertoire que le compte ne lit pas, le répertoire compris."""
	found = blocking(directory, account)
	if found:
		return found
	for root, directories, files in os.walk(directory):
		for name in directories + files:
			item = Path(root) / name
			wanted = READ
			if item.is_dir():
				wanted = READ | EXECUTE
			if not _allows(item, account, wanted):
				found.append(item)
	return found


@dataclass(frozen=True)
class Grant:
	"""Ce que la lecture donnée a fait, et ce qu'elle n'a pas pu faire."""

	changed: list[Path]
	problems: list[str]


def _setfacl(arguments: list[str]) -> str | None:
	"""setfacl ; son erreur, ou None."""
	try:
		result = subprocess.run(
			[TOOL, *arguments], capture_output=True, text=True, timeout=DELAY, check=False, stdin=subprocess.DEVNULL
		)
	except FileNotFoundError:
		return _("setfacl not found; install the acl package")
	except subprocess.TimeoutExpired:
		return _("setfacl does not answer")
	if result.returncode != 0:
		return result.stderr.strip()
	return None


def grant(path: Path, account: Account) -> Grant:
	"""Donne au compte la lecture du chemin : la traversée de ses répertoires parents qui en manquent, et la lecture du
	chemin, récursive pour un répertoire, avec l'ACL par défaut des fichiers qui s'y ajouteront."""
	path = _real(path)
	changed: list[Path] = []
	problems: list[str] = []
	crossings = []
	for parent in reversed(path.parents):
		if not _allows(parent, account, EXECUTE):
			crossings.append(parent)
	# Rien ne change dans une arborescence sensible : un seul refus, et aucun droit modifié.
	for target in [*crossings, path]:
		tree = sensitive_tree(target)
		if tree is not None:
			problems.append(
				_("{path}: refused, it is in {tree}, where MachinCast never changes any right").format(
					path=target, tree=tree
				)
			)
	if problems != []:
		problems.append(
			_(
				"put the sound files in {welcome}, which the broadcast service reads, or below /opt, /srv or /var, whose "
				"root it already crosses"
			).format(welcome=welcome())
		)
		return Grant(changed, problems)
	uid = os.getuid()
	for parent in crossings:
		_grant_traversal(parent, account, uid, changed, problems)
	entry = f"u:{account.name}:rX"
	arguments = [f"--modify={entry}", str(path)]
	if path.is_dir():
		arguments = ["--recursive", f"--modify={entry},d:{entry}", str(path)]
	error = _setfacl(arguments)
	if error is not None:
		problems.append(_("{path}: {error}").format(path=path, error=error))
		problems.append(_administrator(arguments))
	else:
		changed.append(path)
	return Grant(changed, problems)


def _grant_traversal(parent: Path, account: Account, uid: int, changed: list[Path], problems: list[str]) -> None:
	"""La traversée d'un répertoire parent qui en manque : par setfacl s'il est au compte, sinon un administrateur."""
	arguments = [f"--modify=u:{account.name}:x", str(parent)]
	if parent.stat().st_uid != uid:
		problems.append(
			_("{path}: {account} cannot cross it, and it belongs to another account").format(
				path=parent, account=account.name
			)
		)
		problems.append(_administrator(arguments))
		return
	error = _setfacl(arguments)
	if error is not None:
		problems.append(_("{path}: {error}").format(path=parent, error=error))
		return
	changed.append(parent)


def _administrator(arguments: list[str]) -> str:
	return _("an administrator can run: sudo {command}").format(command=shlex.join([TOOL, *arguments]))


def database_paths(configuration: Configuration) -> list[Path]:
	"""Les répertoires des banques, et les fichiers ajoutés hors de ces répertoires, de la base de production."""
	database = configuration.database
	with open_connection(database.socket, database.production, Role.INTERFACE) as connection:
		directories = connection.execute(
			"SELECT DISTINCT d.directory FROM bank_directories d JOIN banks b ON b.id = d.bank_id"
			" WHERE b.deleted_at IS NULL ORDER BY 1"
		).fetchall()
		files = connection.execute(
			"SELECT location FROM sounds s WHERE s.deleted_at IS NULL AND s.location IS NOT NULL AND NOT EXISTS ("
			" SELECT 1 FROM bank_directories d WHERE s.location LIKE d.directory || '/%%') ORDER BY 1"
		).fetchall()
	paths = []
	for (directory,) in directories:
		paths.append(Path(str(directory)))
	for (location,) in files:
		paths.append(Path(str(location)))
	return paths


def _options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument(
		"paths",
		nargs="*",
		type=Path,
		metavar=_("PATH"),
		help=_("files or directories; by default, the bank directories and the added files of the database"),
	)
	analyser.add_argument(
		"--keep-open",
		action="store_true",
		help=_("keeps the terminal open at the end, until it is closed: for the window that the interface opens"),
	)


def _run(configuration: Configuration, options: argparse.Namespace) -> int:
	account = service_account()
	if account is None:
		log.error(_("no {account} account: the broadcast service is not installed").format(account=service.account()))
		return FAILURE_CODE
	paths: list[Path] = options.paths
	if not paths:
		paths = database_paths(configuration)
	failed = False
	for path in paths:
		if not path.exists():
			log.warning(_("{path}: not found").format(path=path))
			failed = True
		else:
			failed = (not _grant_path(path, account)) or (failed)
	return int(failed)


def _grant_path(path: Path, account: Account) -> bool:
	"""Vrai si le service lit le chemin, déjà ou une fois la lecture donnée."""
	already = readable(path, account)
	if path.is_dir():
		already = not unreadable_inside(path, account)
	if already:
		log.info(_("{path}: already readable by {account}").format(path=path, account=account.name))
		return True
	result = grant(path, account)
	for problem in result.problems:
		log.warning(problem)
	if result.problems:
		return False
	log.info(_("{path}: readable by {account}").format(path=path, account=account.name))
	return True


def _after(options: argparse.Namespace) -> None:
	if options.keep_open:
		stay_open()


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, _run, _options, then=_after)


if __name__ == "__main__":
	raise SystemExit(main())
