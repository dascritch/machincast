"""Programmes de MachinCast en cours, pour install.sh (https://github.com/dascritch/machincast/issues/254).

	python3 -m machincast.programs list   --state FICHIER   une ligne par programme en cours ; leur état, enregistré
	python3 -m machincast.programs restart --state FICHIER   relance ceux du compte, dit ce qui reste à rouvrir

Une mise à jour, et surtout ses migrations de la base, ne doit pas se faire sous un programme qui s'en sert.
install.sh liste donc, avant de toucher au venv, les programmes de MachinCast qui tournent, sous tous les comptes du
poste : Machin player (le service de diffusion, une diffusion d'essai, une simulation), Machin indexer et
Machin interface, lancés par bin/Machin, par leur exécutable du venv (Machin_player…) ou par python -m. Il les arrête
si l'administrateur l'accepte, puis, à la fin, relance le service lui-même et demande ici de relancer les autres.

Ce module n'emploie que la bibliothèque standard : install.sh le lance avec le python3 du système, le venv pouvant
manquer ou changer pendant l'installation. Il lit /proc : la ligne de commande, le propriétaire, le groupe de contrôle
(le service de diffusion est celui de l'unité machincast.service) et le répertoire de chaque processus.

« lister » écrit, séparés par des tabulations : le pid, « yes » si le programme est du compte qui installe, « yes »
s'il est le service de diffusion (« no » sinon), et ce qu'install.sh en affiche. L'état enregistré est en JSON : ni
install.sh ni la relance n'évaluent la ligne de commande d'un autre programme.

« relancer » relance, pour le seul compte qui installe, et depuis son répertoire : la diffusion d'essai dans un
terminal (konsole, sinon x-terminal-emulator), l'interface dans la session graphique, détachées d'install.sh, avec
leurs arguments, par bin/Machin. La simulation, que lance l'interface, se relance depuis son onglet ; une indexation
interrompue se relance à la main ; les programmes des autres comptes, par leur compte.
"""

import argparse
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from machincast.i18n import _
from machincast.service import UNIT

PROC = Path("/proc")
MACHIN = Path(__file__).resolve().parents[2] / "bin" / "Machin"
"""Le wrapper du répertoire de MachinCast, qui relance chaque programme."""
NAMES = ("player", "indexer", "interface")
"""Les programmes, sous leur nom de commande du wrapper (https://github.com/dascritch/machincast/issues/356)."""
EXECUTABLE = re.compile(r"Machin_(player|indexer|interface)")
MODULE = re.compile(r"machincast\.(player|indexer|interface)")
MODULE_PROGRAM = {"player": "player", "indexer": "indexer", "interface": "interface"}
"""Le programme que lance python -m sur chaque module."""
TERMINALS = ("konsole", "x-terminal-emulator")
GRAPHIC_SESSION = ("WAYLAND_DISPLAY", "DISPLAY")


@dataclass(frozen=True)
class Program:
	pid: int
	account: str
	name: str
	"""player, indexer ou interface."""
	arguments: tuple[str, ...]
	service: bool
	"""Machin player, lancé par l'unité du service de diffusion."""
	directory: str
	"""Répertoire où il a été lancé : ses chemins relatifs s'y lisent ; vide pour un autre compte."""

	@property
	def kind(self) -> str:
		if self.name == "indexer":
			return "indexation"
		if self.name != "player":
			return self.name
		if self.service:
			return _("broadcast service")
		if "--simulation" in self.arguments:
			return "simulation"
		return _("trial broadcast")

	@property
	def command(self) -> str:
		"""Comme il se lance par bin/Machin."""
		return " ".join(["Machin", self.name, *self.arguments])

	@property
	def label(self) -> str:
		return _("{command} ({kind}), account {account}").format(
			command=self.command, kind=self.kind, account=self.account
		)


def recognise(line: Sequence[str]) -> tuple[str, tuple[str, ...]] | None:
	"""Le programme d'une ligne de commande, et ses arguments ; None pour tout autre processus. L'exécutable du venv
	est lancé tel quel, ou par son python ; le module, par python -m."""
	if not line:
		return None
	python = Path(line[0]).name.startswith("python")
	for rank in (0, 1):
		if (rank < len(line)) and ((rank == 0) or (python)):
			found = EXECUTABLE.fullmatch(Path(line[rank]).name)
			if found is not None:
				return found.group(1), tuple(line[rank + 1 :])
	if python:
		for rank in range(1, len(line) - 1):
			if line[rank] == "-m":
				found = MODULE.fullmatch(line[rank + 1])
				if found is None:
					return None
				return MODULE_PROGRAM[found.group(1)], tuple(line[rank + 2 :])
	return None


def _account(uid: int) -> str:
	try:
		return pwd.getpwuid(uid).pw_name
	except KeyError:
		return str(uid)


def _read(process: Path, accounts: Callable[[int], str]) -> Program | None:
	"""Un processus disparu entre-temps, ou illisible, n'est pas un programme en cours."""
	try:
		line = [part for part in process.joinpath("cmdline").read_bytes().decode().split("\0") if part]
		recognised = recognise(line)
		if recognised is None:
			return None
		status = process.joinpath("status").read_text()
		cgroup = process.joinpath("cgroup").read_text()
	except (OSError, UnicodeDecodeError):
		return None
	# Le répertoire ne se lit que pour son propre compte : celui d'un autre compte reste inconnu.
	try:
		directory = str(process.joinpath("cwd").readlink())
	except OSError:
		directory = ""
	uid = re.search(r"^Uid:\s+(\d+)", status, re.MULTILINE)
	if uid is None:
		return None
	name, arguments = recognised
	return Program(
		pid=int(process.name),
		account=accounts(int(uid.group(1))),
		name=name,
		arguments=arguments,
		service=f"/{UNIT}" in cgroup,
		directory=directory,
	)


def ongoing(proc: Path = PROC, accounts: Callable[[int], str] = _account) -> list[Program]:
	"""Les programmes de MachinCast en cours, sous tous les comptes, par pid ; jamais ce processus-ci."""
	found_list = []
	for process in proc.iterdir():
		if (not process.name.isdigit()) or (int(process.name) == os.getpid()):
			continue
		program = _read(process, accounts)
		if program is not None:
			found_list.append(program)
	return sorted(found_list, key=lambda program: program.pid)


def _yes(true: bool) -> str:
	"""« yes » ou « no », pour install.sh (https://github.com/dascritch/machincast/issues/368)."""
	if true:
		return "yes"
	return "no"


def list_items(programs: list[Program], current_account: str) -> str:
	"""Les lignes pour install.sh : pid, du compte, service, et ce qu'il en affiche."""
	return "".join(f"{p.pid}\t{_yes(p.account == current_account)}\t{_yes(p.service)}\t{p.label}\n" for p in programs)


def save(programs: list[Program], state: Path) -> None:
	state.write_text(json.dumps([asdict(program) for program in programs], ensure_ascii=False))


def reread(state: Path) -> list[Program]:
	return [Program(**{**values, "arguments": tuple(values["arguments"])}) for values in json.loads(state.read_text())]


Launch = Callable[[list[str], str], None]
"""Lance une commande, détachée, depuis un répertoire."""


def launch_detached(command: list[str], directory: str) -> None:
	"""Détachée d'install.sh : elle survit à son terminal. Un répertoire disparu depuis laisse le répertoire courant."""
	if not Path(directory).is_dir():
		directory = os.getcwd()
	subprocess.Popen(  # noqa: S603 : la commande est bin/Machin, et les arguments, ceux du programme arrêté
		command,
		cwd=directory,
		start_new_session=True,
		stdin=subprocess.DEVNULL,
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
	)


def _terminal(find: Callable[[str], str | None]) -> str | None:
	for terminal in TERMINALS:
		path = find(terminal)
		if path is not None:
			return path
	return None


def restart(
	programs: list[Program],
	current_account: str,
	environment: Mapping[str, str],
	launch: Launch = launch_detached,
	find: Callable[[str], str | None] = shutil.which,
	simulation: bool = False,
) -> list[str]:
	"""Relance la diffusion d'essai et l'interface du compte ; ce qu'il faut en dire, ligne par ligne. Le service de
	diffusion n'y est pas : install.sh le relance lui-même."""
	restarted_list: list[str] = []
	rest: list[str] = []
	graphic = any(environment.get(variable) for variable in GRAPHIC_SESSION)
	terminal = _terminal(find)
	prefix = ""
	if simulation:
		prefix = "[simulation] "
	for program in programs:
		command = [str(MACHIN), program.name, *program.arguments]
		if program.service:
			continue
		if program.account != current_account:
			rest.append(
				_("to reopen by the account {account}: {command}").format(
					account=program.account, command=program.command
				)
			)
		elif program.kind == "simulation":
			rest.append(_("simulation interrupted: launch it again from the Simulation tab of the interface"))
		elif program.name == "indexer":
			rest.append(_("indexing interrupted: launch again {command}").format(command=program.command))
		elif not graphic:
			ou = _("a terminal")
			if program.name == "interface":
				ou = _("the graphical session")
			rest.append(_("to reopen in {ou}: {command}").format(ou=ou, command=program.command))
		elif program.name == "interface":
			if not simulation:
				launch(command, program.directory)
			restarted_list.append(_("{prefix}relaunched: {command}").format(prefix=prefix, command=program.command))
		elif terminal is None:
			rest.append(_("to reopen in a terminal: {command}").format(command=program.command))
		else:
			if not simulation:
				launch([terminal, "-e", *command], program.directory)
			restarted_list.append(
				_("{prefix}relaunched in a terminal: {command}").format(prefix=prefix, command=program.command)
			)
	return restarted_list + rest


def main(arguments: Sequence[str] | None = None) -> int:
	analyser = argparse.ArgumentParser(prog="machincast.programs", description=__doc__.splitlines()[0])
	analyser.add_argument("action", choices=("list", "restart"))
	analyser.add_argument("--state", type=Path, required=True, help=_("state of the running programs, in JSON"))
	analyser.add_argument("--proc", type=Path, default=PROC, help=argparse.SUPPRESS)
	analyser.add_argument(
		"--simulation", action="store_true", help=_("tells what would be relaunched, without launching anything")
	)
	options = analyser.parse_args(arguments)
	current_account = _account(os.getuid())
	if options.action == "list":
		programs = ongoing(options.proc)
		save(programs, options.state)
		sys.stdout.write(list_items(programs, current_account))
		return 0
	for message in restart(reread(options.state), current_account, os.environ, simulation=options.simulation):
		sys.stdout.write(f"{message}\n")
	return 0


if __name__ == "__main__":
	sys.exit(main())
