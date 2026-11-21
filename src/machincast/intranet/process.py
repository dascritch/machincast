"""Le processus de Machin intranet, que l'interface retrouve pour l'arrêter
(https://github.com/dascritch/machincast/issues/544).

Tant qu'il sert, Machin intranet note son PID dans son répertoire d'état, et l'efface en s'arrêtant. Lancé à la main
ou par l'interface, sans le service, ce répertoire est celui du compte : l'interface, sous le même compte, y lit le
PID de celui qu'elle doit arrêter. Un PID resté d'un arrêt brutal, ou repris par un autre programme, ne compte pas.
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


def _is_intranet(pid: int) -> bool:
	"""Le processus existe, et c'est Machin intranet."""
	try:
		command = Path(f"/proc/{pid}/cmdline").read_bytes()
	except OSError:
		return False
	return b"intranet" in command


def running_pid(directory: Path | None = None) -> int | None:
	"""Le PID du Machin intranet qui sert, d'après son répertoire d'état ; None s'il ne tourne pas."""
	path = ((directory) or (state_directory())) / PID_FILE
	try:
		text = path.read_text(encoding="utf-8").strip()
	except OSError:
		return None
	if not text.isdigit():
		return None
	pid = int(text)
	if not _is_intranet(pid):
		return None
	return pid
