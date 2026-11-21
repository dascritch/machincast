"""Le processus de Machin intranet, que l'interface retrouve pour l'arrêter
(https://github.com/dascritch/machincast/issues/544).

Tant qu'il sert, Machin intranet note son PID dans son répertoire d'état, et l'efface en s'arrêtant. Lancé à la main
ou par l'interface, sans le service, ce répertoire est celui du compte : l'interface, sous le même compte, y lit le
PID de celui qu'elle doit arrêter. Un PID resté d'un arrêt brutal, ou repris par un autre programme, ne compte pas :
seul compte un processus du même compte, lancé comme Machin intranet, et démarré avant l'écriture du fichier
(https://github.com/dascritch/machincast/issues/550).
Sans dépendance à Hypercorn ni à Qt : l'interface l'importe.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

PID_FILE = "machincast-intranet.pid"


def state_directory() -> Path:
	"""Le répertoire d'état : celui que systemd donne à l'unité, ou celui du compte."""
	given = os.environ.get("STATE_DIRECTORY", "").split(":")[0]
	if given != "":
		return Path(given)
	base = os.environ.get("XDG_STATE_HOME", "")
	if base == "":
		base = str(Path.home() / ".local" / "state")
	return Path(base) / "machincast" / "intranet"


@contextmanager
def recorded(directory: Path | None = None) -> Iterator[Path]:
	"""Le PID de ce processus, noté le temps du bloc."""
	path = ((directory) or (state_directory())) / PID_FILE
	path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
	path.write_text(f"{os.getpid()}\n", encoding="utf-8")
	try:
		yield path
	finally:
		path.unlink(missing_ok=True)  # fichier de MachinCast : le PID de Machin intranet


EXECUTABLE = "Machin_intranet"
MODULE = "machincast.intranet"
TOLERANCE = 2.0
"""Secondes entre le démarrage du processus, arrondi au tic d'horloge, et l'écriture de son PID."""


def arguments(pid: int) -> list[str]:
	"""Les arguments du processus, un par élément ; aucun s'il n'existe pas."""
	try:
		command = Path(f"/proc/{pid}/cmdline").read_bytes()
	except OSError:
		return []
	found = []
	for argument in command.split(b"\0"):
		if argument != b"":
			found.append(argument.decode("utf-8", "replace"))
	return found


def runs_intranet(given: list[str]) -> bool:
	"""Ces arguments sont ceux de Machin intranet : son exécutable, ou python -m machincast.intranet, élément par
	élément, jamais par sous-chaîne (https://github.com/dascritch/machincast/issues/550)."""
	for index, argument in enumerate(given):
		if Path(argument).name == EXECUTABLE:
			return True
		if (argument == "-m") and (given[index + 1 : index + 2] == [MODULE]):
			return True
	return False


def started_at(pid: int) -> float | None:
	"""L'heure de démarrage du processus, en secondes depuis l'époque : starttime de /proc/<pid>/stat, en tics
	depuis le démarrage du poste, plus btime de /proc/stat ; None si elle ne se lit pas."""
	try:
		stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
		system = Path("/proc/stat").read_text(encoding="utf-8")
	except OSError:
		return None
	# Le nom du programme, entre parenthèses, peut contenir des espaces : les champs se comptent après lui.
	fields = stat.rpartition(")")[2].split()
	boot = None
	for line in system.splitlines():
		if line.startswith("btime "):
			boot = int(line.split()[1])
	if (boot is None) or (len(fields) < 20):
		return None
	return boot + (int(fields[19]) / os.sysconf("SC_CLK_TCK"))


def _is_intranet(pid: int, path: Path) -> bool:
	"""Le processus existe, au même compte, c'est Machin intranet, et il a démarré avant l'écriture du fichier de
	son PID : un PID resté d'un arrêt brutal, puis réattribué, ne compte pas."""
	try:
		owner = Path(f"/proc/{pid}").stat().st_uid
		written = path.stat().st_mtime
	except OSError:
		return False
	if owner != os.getuid():
		return False
	if not runs_intranet(arguments(pid)):
		return False
	start = started_at(pid)
	return (start is not None) and (start <= written + TOLERANCE)


def running_pid(directory: Path | None = None) -> int | None:
	"""Le PID du Machin intranet qui sert, d'après son répertoire d'état ; None s'il ne tourne pas."""
	path = ((directory) or (state_directory())) / PID_FILE
	try:
		text = path.read_text(encoding="utf-8").strip()
	except OSError:
		return None
	if (not text.isascii()) or (not text.isdigit()):
		return None
	pid = int(text)
	if not _is_intranet(pid, path):
		return None
	return pid
