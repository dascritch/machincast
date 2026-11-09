"""Rapports de crash des binaires (https://github.com/dascritch/machincast/issues/342).

Un plantage d'un binaire de MachinCast laisse un fichier horodaté dans crash-dump/, à la racine du dépôt du code
(DIRECTORY, ou celui de la variable d'environnement MACHINCAST_CRASH_DUMP), ou, s'il n'est pas accessible en écriture,
dans /tmp/machincast/crash-dump (FALLBACK) : de quoi reproduire les conditions du plantage. Il se nomme « <binaire>-<démarrage>-<pid>.txt », le démarrage en heure du poste
(« Machin_player-2026-11-09T14-03-12-4242.txt ») : le pid et l'heure de démarrage sont aussi ceux de la ligne
« start » du log, et le plantage probable que note le lancement suivant donne son chemin (machincast.runs).

Il contient :

- le binaire, sa version, son pid, ses options, l'heure de son démarrage et celle du plantage ;
- la pile Python, causes enchaînées comprises ;
- les détails d'une erreur venue d'ailleurs que du code de MachinCast : PostgreSQL (SQLSTATE, messages, détail,
  indice, contexte), GLib et GStreamer (domaine, code, message), le système (errno, fichier), un programme lancé (code,
  sortie d'erreur) ;
- les versions de Python, de MachinCast, de psycopg et de libpq, de PyGObject et de GStreamer, de PySide6 et de Qt,
  pour celles qui sont chargées ;
- ce que chaque binaire y ajoute (provide, note) : le fichier en cours d'analyse pour Machin indexer, les cartes son
  et la sortie de « wpctl status » pour Machin interface et Machin player, l'onglet affiché et le sonore en
  pré-écoute, les sonores précédent, en cours et à venir de l'antenne.

Trois sortes de plantage :

- une exception qui remonte jusqu'à cli.launch : le rapport s'écrit aussitôt. Une exception qui n'arrête pas le
  binaire, celle d'un fil ou celle qu'une fonction appelée par Qt laisse passer, n'est pas un plantage : le journal la
  montre, sans rapport ;
- un signal fatal (SIGSEGV, SIGABRT, SIGBUS, SIGFPE, SIGILL), souvent dans GStreamer ou Qt : faulthandler écrit la
  pile de chaque fil dans un rapport en cours, ouvert dès le démarrage (« .<binaire>-<démarrage>-<pid>.en-cours »),
  qui ne reçoit rien d'autre que son en-tête ;
- un arrêt sans un mot (kill -9, manque de mémoire, coupure de courant) : le rapport en cours reste seul.

Un lancement qui se termine normalement efface son rapport en cours. Ceux qu'ont laissés les processus qui ne tournent
plus sont achevés (finish_leftovers, https://github.com/dascritch/machincast/issues/413) : par bin/Machin, dès que le
binaire meurt d'un signal (python -m machincast.crash), sinon par le lancement suivant du même binaire. Ce qui n'était
qu'en mémoire est perdu ; l'achèvement retrouve ce qui reste : les versions, les cartes son du fichier de
configuration, la sortie de « wpctl status », et les dernières lignes du journal de ce pid (journalctl), qui nomment le
sonore à l'antenne, l'onglet affiché ou le sonore en pré-écoute. Le module signal n'a pas sa place ici : il ne
s'exécute qu'entre deux instructions Python, jamais pendant un appel bloqué ou planté.
"""

import contextlib
import faulthandler
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TextIO

from machincast import __version__
from machincast.clock import SystemClock
from machincast.configuration import PROJECT_DIRECTORY, Audio, InvalidConfiguration, load
from machincast.i18n import _

log = logging.getLogger(__name__)

DIRECTORY = PROJECT_DIRECTORY / "crash-dump"
"""Le répertoire des rapports, dans le dépôt du code."""
FALLBACK = Path(tempfile.gettempdir()) / "machincast" / "crash-dump"
"""Celui des rapports quand le dépôt n'est pas accessible en écriture : /tmp/machincast/crash-dump, vidé au
redémarrage du poste."""
PENDING = ".en-cours"
"""Le suffixe d'un rapport en cours, que le lancement efface s'il se termine normalement."""
WPCTL = "wpctl"
WPCTL_DELAY = 5
"""Secondes laissées à « wpctl status », qui interroge PipeWire."""

Provider = Callable[[], str]


ENVIRONMENT = "MACHINCAST_CRASH_DUMP"
"""Variable d'environnement qui désigne un autre répertoire des rapports : celui d'un scénario, pour les binaires
qu'il lance."""


def directory() -> Path:
	"""Le répertoire de ENVIRONMENT, sinon DIRECTORY, ou FALLBACK s'il ne peut pas être créé ou écrit."""
	chosen = os.environ.get(ENVIRONMENT)
	candidates = [DIRECTORY, FALLBACK]
	if chosen:
		candidates = [Path(chosen), FALLBACK]
	for candidate in candidates:
		try:
			candidate.mkdir(parents=True, exist_ok=True)
		except OSError:
			continue
		if os.access(candidate, os.W_OK):
			return candidate
	return FALLBACK


def name(program: str, started: datetime, pid: int) -> str:
	"""« Machin_player-2026-11-09T14-03-12-4242.txt »."""
	return f"{program}-{started.astimezone():%Y-%m-%dT%H-%M-%S}-{pid}.txt"


def pending_name(program: str, started: datetime, pid: int) -> str:
	return f".{name(program, started, pid).removesuffix('.txt')}{PENDING}"


@dataclass
class Watch:
	"""Le lancement surveillé : ce que ses rapports diront de lui."""

	program: str
	arguments: Sequence[str]
	started: datetime
	pid: int
	place: Path
	notes: dict[str, str] = field(default_factory=dict)
	"""Ce que le binaire a noté : le fichier en cours d'analyse, par exemple."""
	providers: dict[str, Provider] = field(default_factory=dict)
	"""Ce que le binaire donne au moment du rapport : la sortie de « wpctl status », les sonores de l'antenne…"""
	pending: TextIO | None = None
	written: list[Path] = field(default_factory=list)
	"""Les rapports écrits pendant le lancement."""

	@property
	def pending_path(self) -> Path:
		return self.place / pending_name(self.program, self.started, self.pid)

	@property
	def report_path(self) -> Path:
		return self.place / name(self.program, self.started, self.pid)


_watch: Watch | None = None
_lock = threading.Lock()


def current() -> Watch | None:
	return _watch


def note(key: str, value: str | None) -> None:
	"""Une information du binaire, pour ses rapports ; None l'efface. Sans surveillance, rien."""
	watch = _watch
	if watch is None:
		return
	if value is None:
		watch.notes.pop(key, None)
		return
	watch.notes[key] = value


def provide(key: str, provider: Provider | None) -> None:
	"""Une information que le binaire donnera au moment du rapport ; None la retire."""
	watch = _watch
	if watch is None:
		return
	if provider is None:
		watch.providers.pop(key, None)
		return
	watch.providers[key] = provider


def wpctl_status() -> str:
	"""La sortie de « wpctl status » : les cartes son, les nœuds et les liens de PipeWire."""
	program = shutil.which(WPCTL)
	if program is None:
		return _("wpctl not found")
	try:
		result = subprocess.run(
			[program, "status"], capture_output=True, text=True, timeout=WPCTL_DELAY, stdin=subprocess.DEVNULL
		)
	except (OSError, subprocess.SubprocessError) as error:
		return _("wpctl status impossible: {error}").format(error=error)
	return f"{result.stdout}{result.stderr}".rstrip()


JOURNALCTL = "journalctl"
JOURNAL_LINES = 40
"""Les dernières lignes du journal d'un processus qu'un rapport achevé reprend."""
WITH_SOUND_CARDS = {"Machin_player": False, "Machin_interface": True}
"""Les binaires qui jouent du son, et s'ils ont une pré-écoute."""


def sound_cards(audio: Audio, preview: bool) -> str:
	"""La sortie et le périphérique de l'antenne et, avec preview, ceux de la pré-écoute."""
	output, device = audio.on_air()
	lines = [_("On air: output {output}, device {device}").format(output=output, device=device)]
	if preview:
		lines.append(
			_("Pre-listen: output {output}, device {device}").format(output=audio.output, device=audio.preview)
		)
	return "\n".join(lines)


def journal(pid: int) -> str:
	"""Les JOURNAL_LINES dernières lignes du journal systemd de ce processus, s'il y écrivait : celui d'un service ou
	d'un lancement par le raccourci du bureau ; rien pour un lancement dans un terminal."""
	program = shutil.which(JOURNALCTL)
	if program is None:
		return _("journalctl not found")
	command = [program, f"_PID={pid}", "--no-pager", "--output=short-iso", f"--lines={JOURNAL_LINES}"]
	try:
		result = subprocess.run(command, capture_output=True, text=True, timeout=WPCTL_DELAY, stdin=subprocess.DEVNULL)
	except (OSError, subprocess.SubprocessError) as error:
		return _("journalctl impossible: {error}").format(error=error)
	lines = [line for line in result.stdout.splitlines() if not line.startswith("-- ")]
	return ("\n".join(lines)) or (_("no line in the journal for this process"))


def _load_libraries() -> None:
	"""Charge les bibliothèques des binaires, pour que versions() les donne à l'achèvement d'un rapport."""
	for module in ("psycopg", "PySide6.QtCore"):
		with contextlib.suppress(Exception):
			__import__(module)
	with contextlib.suppress(Exception):
		from machincast import audio  # noqa: F401 : charge GStreamer
	with contextlib.suppress(Exception):
		from gi.repository import Gst

		Gst.init(None)


def completion(program: str, pid: int, configuration: Path | None) -> list[str]:
	"""Ce qu'un rapport en cours, achevé après la mort de son processus, reçoit encore : les versions, les cartes son du
	fichier de configuration et « wpctl status » pour les binaires qui jouent du son, puis les dernières lignes du
	journal de ce pid."""
	_load_libraries()
	lines = ["", _("Versions, when the report was finished"), *(f"  {line}" for line in versions())]
	sections: list[tuple[str, str]] = []
	if program in WITH_SOUND_CARDS:
		try:
			cards = sound_cards(load(configuration).audio, WITH_SOUND_CARDS[program])
		except (InvalidConfiguration, OSError) as error:
			cards = _("unreadable configuration: {error}").format(error=error)
		sections += [(_("Sound cards, from the configuration file"), cards), ("wpctl status", wpctl_status())]
	sections.append((_("Last lines of the journal of pid {pid}").format(pid=pid), journal(pid)))
	for key, value in sections:
		lines += ["", key, *(f"  {line}" for line in value.splitlines())]
	return lines


def versions() -> list[str]:
	"""Les versions de Python, de MachinCast et des bibliothèques chargées."""
	lines = [
		f"Python {platform.python_version()} ({sys.executable})",
		f"MachinCast {__version__}",
		f"{platform.platform()}",
	]
	psycopg = sys.modules.get("psycopg")
	if psycopg is not None:
		lines.append(f"psycopg {psycopg.__version__}, libpq {_libpq(psycopg)}")
	gi = sys.modules.get("gi")
	if gi is not None:
		lines.append(f"PyGObject {getattr(gi, '__version__', '?')}")
	gst = sys.modules.get("gi.repository.Gst")
	if gst is not None:
		try:
			lines.append(str(gst.version_string()))
		except Exception as error:  # noqa: BLE001 : un rapport ne doit pas planter
			lines.append(f"GStreamer ? ({error})")
	pyside = sys.modules.get("PySide6")
	if pyside is not None:
		qt = sys.modules.get("PySide6.QtCore")
		qt_version = "?"
		if qt is not None:
			qt_version = qt.qVersion()
		lines.append(f"PySide6 {pyside.__version__}, Qt {qt_version}")
	return lines


def _libpq(psycopg: object) -> str:
	"""« 16.4 » pour 160004."""
	try:
		number = int(psycopg.pq.version())  # type: ignore[attr-defined]
	except Exception:  # noqa: BLE001 : un rapport ne doit pas planter
		return "?"
	return f"{number // 10000}.{number % 10000}"


def _chain(error: BaseException) -> list[BaseException]:
	"""L'erreur et ses causes, la plus récente d'abord."""
	found: list[BaseException] = []
	while (error is not None) and (error not in found):
		found.append(error)
		error = (error.__cause__) or (error.__context__)  # type: ignore[assignment]
	return found


def external(error: BaseException) -> list[str]:
	"""Ce que PostgreSQL, GLib et GStreamer, le système ou un programme lancé ont rendu, pour chaque erreur de la
	chaîne."""
	lines: list[str] = []
	for item in _chain(error):
		kind = f"{type(item).__module__}.{type(item).__qualname__}"
		module = type(item).__module__
		if module.startswith("psycopg"):
			diag = getattr(item, "diag", None)
			lines.append(f"PostgreSQL ({kind}) : SQLSTATE {getattr(item, 'sqlstate', None)}")
			if diag is not None:
				for attribute in (
					"severity",
					"message_primary",
					"message_detail",
					"message_hint",
					"context",
					"schema_name",
					"table_name",
					"column_name",
					"constraint_name",
					"statement_position",
				):
					value = getattr(diag, attribute, None)
					if value:
						lines.append(f"  {attribute} : {value}")
			lines.append(f"  {item}")
		elif (hasattr(item, "domain")) and (hasattr(item, "code")) and (module.startswith("gi")):
			lines.append(
				f"GLib ({kind}) : domain {getattr(item, 'domain', '?')}, code {getattr(item, 'code', '?')},"
				f" message {getattr(item, 'message', item)}"
			)
		elif isinstance(item, subprocess.CalledProcessError):
			lines.append(f"{kind} : {item.cmd} → code {item.returncode}")
			if item.stderr:
				lines.append(f"  {item.stderr}")
		elif isinstance(item, OSError):
			lines.append(f"{kind} : errno {item.errno} ({item.strerror}), file {item.filename}")
	return lines


def _header(watch: Watch) -> list[str]:
	return [
		_("MachinCast crash report"),
		"",
		_("Program: {program} {version}, pid {pid}").format(program=watch.program, version=__version__, pid=watch.pid),
		_("Options: {options}").format(options=(" ".join(watch.arguments)) or ("—")),
		_("Started: {start}").format(start=f"{watch.started.astimezone().isoformat(timespec='seconds')}"),
	]


def _context(watch: Watch, live: bool) -> list[str]:
	"""Les versions, puis ce que le binaire a noté et, en direct seulement, ce qu'il donne."""
	lines = ["", _("Versions"), *(f"  {line}" for line in versions())]
	for key, value in watch.notes.items():
		lines += ["", key, *(f"  {line}" for line in value.splitlines())]
	if live:
		for key, provider in list(watch.providers.items()):
			try:
				value = provider()
			except Exception as error:  # noqa: BLE001 : un rapport ne doit pas planter
				value = _("not available: {error}").format(error=error)
			lines += ["", key, *(f"  {line}" for line in value.splitlines())]
	return lines


def write_report(error: BaseException, instant: datetime | None = None) -> Path | None:
	"""Le rapport d'un plantage par cette exception, pendant le lancement surveillé ; None sans surveillance, ou s'il
	n'a pas pu s'écrire. Plusieurs plantages du même lancement s'ajoutent au même rapport."""
	watch = _watch
	if watch is None:
		return None
	instant = (instant) or (SystemClock().now())
	lines = [
		*_header(watch),
		_("Crash: {instant}").format(instant=instant.isoformat(timespec="seconds")),
		"",
		_("Python stack"),
		*(line.rstrip("\n") for line in traceback.format_exception(error)),
	]
	details = external(error)
	if details:
		lines += ["", _("Errors outside MachinCast"), *(f"  {line}" for line in details)]
	lines += _context(watch, live=True)
	path = watch.report_path
	with _lock:
		try:
			mode = "a" if path in watch.written else "w"
			with path.open(mode, encoding="utf-8") as file:
				if mode == "a":
					file.write("\n" + "─" * 60 + "\n\n")
				file.write("\n".join(lines) + "\n")
		except OSError as failure:
			log.error(_("crash report impossible to write in {path}: {error}").format(path=path, error=failure))
			return None
		if path not in watch.written:
			watch.written.append(path)
	log.error(_("crash report written: {path}").format(path=path))
	return path


def _start_pending(watch: Watch) -> None:
	"""L'en-tête du rapport en cours, écrit une fois au démarrage : faulthandler écrit à sa suite. Jamais réécrit
	(https://github.com/dascritch/machincast/issues/413)."""
	if watch.pending is None:
		return
	text = "\n".join([*_header(watch), "", _("Fatal signal, if any"), ""]) + "\n"
	try:
		watch.pending.write(text)
		watch.pending.flush()
	except (OSError, ValueError) as error:
		log.warning(_("pending crash report not written: {error}").format(error=error))


def finish_leftovers(program: str, place: Path | None = None, configuration: Path | None = None) -> list[Path]:
	"""Les rapports en cours de ce binaire laissés par des processus qui ne tournent plus deviennent des rapports, avec
	l'heure de leur dernière écriture et ce que completion retrouve encore ; leurs chemins."""
	place = (place) or (directory())
	finished: list[Path] = []
	for pending in sorted(place.glob(f".{program}-*{PENDING}")):
		pid_text = pending.name.removesuffix(PENDING).rsplit("-", 1)[-1]
		if (not pid_text.isdigit()) or (_running(int(pid_text))):
			continue
		target = place / f"{pending.name.removeprefix('.').removesuffix(PENDING)}.txt"
		try:
			last = datetime.fromtimestamp(pending.stat().st_mtime).astimezone()
			text = pending.read_text(encoding="utf-8", errors="replace")
			ending = _(
				"End: unknown, the process stopped without a report (fatal signal, kill -9, out of memory, power cut);"
				" last written {last}"
			).format(last=last.isoformat(timespec="seconds"))
			added = "\n".join(completion(program, int(pid_text), configuration))
			target.write_text(f"{text.rstrip()}\n\n{ending}\n{added}\n", encoding="utf-8")
			pending.unlink()
		except OSError as error:
			log.warning(_("pending crash report {path} not finished: {error}").format(path=pending, error=error))
			continue
		finished.append(target)
	return finished


LINK_DELAY = 300
"""Secondes d'écart admises entre le démarrage noté au log et celui du nom du rapport : la surveillance commence juste
avant que le log ne note le démarrage."""


def report_of(program: str, started: datetime, pid: int, place: Path | None = None) -> Path | None:
	"""Le rapport du lancement de ce binaire, avec ce pid, qui a démarré à cet instant, à LINK_DELAY près ; None s'il
	n'y en a pas."""
	place = (place) or (directory())
	best: tuple[float, Path] | None = None
	for path in place.glob(f"{program}-*-{pid}.txt"):
		stamp = path.name.removeprefix(f"{program}-").removesuffix(f"-{pid}.txt")
		try:
			day, _separator, hour = stamp.partition("T")
			instant = datetime.fromisoformat(f"{day}T{hour.replace('-', ':')}").astimezone()
		except ValueError:
			continue
		gap = abs((instant - started).total_seconds())
		if (gap <= LINK_DELAY) and ((best is None) or (gap < best[0])):
			best = (gap, path)
	return None if best is None else best[1]


def _running(pid: int) -> bool:
	try:
		os.kill(pid, 0)
	except ProcessLookupError:
		return False
	except PermissionError:
		return True
	return True


@contextmanager
def watch(
	program: str, arguments: Sequence[str] = (), place: Path | None = None, configuration: Path | None = None
) -> Iterator[Watch]:
	"""Surveille le lancement : rapport en cours ouvert, faulthandler ; une
	exception qui sort du bloc écrit son rapport, puis passe. À la sortie, tout est rendu, et le rapport en cours
	effacé : le lancement s'est terminé."""
	global _watch
	place = (place) or (directory())
	finish_leftovers(program, place, configuration)
	watched = Watch(program, list(arguments), SystemClock().now(), os.getpid(), place)
	try:
		watched.pending = watched.pending_path.open("w", encoding="utf-8")
	except OSError as error:
		log.warning(_("pending crash report impossible to open: {error}").format(error=error))
	previous_watch, _watch = _watch, watched
	enabled = faulthandler.is_enabled()
	if watched.pending is not None:
		_start_pending(watched)
		faulthandler.enable(file=watched.pending, all_threads=True)
	try:
		yield watched
	except (KeyboardInterrupt, SystemExit, GeneratorExit):
		raise
	except BaseException as error:
		write_report(error)
		raise
	finally:
		if watched.pending is not None:
			faulthandler.disable()
			# faulthandler ne dit pas sur quel fichier il écrivait : il reprend la sortie d'erreur d'origine, quand
			# elle a un descripteur (pas sous pytest, qui la capture).
			if (enabled) and (sys.__stderr__ is not None):
				with contextlib.suppress(ValueError, OSError):
					faulthandler.enable(file=sys.__stderr__, all_threads=True)
			watched.pending.close()
			watched.pending_path.unlink(missing_ok=True)
		_watch = previous_watch


def main(arguments: Sequence[str] | None = None) -> int:
	"""« python -m machincast.crash BINAIRE [--config FICHIER] » : achève les rapports en cours que ce binaire a laissés.
	bin/Machin l'appelle quand le binaire meurt d'un signal (https://github.com/dascritch/machincast/issues/413)."""
	import argparse

	from machincast.log import configure as configure_log

	configure_log("Machin")
	analyser = argparse.ArgumentParser(
		prog="python -m machincast.crash", description=_("Finishes the pending crash reports left by a binary.")
	)
	analyser.add_argument("program", metavar=_("BINARY"), help=_("Machin_player, Machin_interface…"))
	analyser.add_argument("--config", type=Path, default=None, metavar=_("FILE"))
	options = analyser.parse_args(arguments)
	for path in finish_leftovers(options.program, configuration=options.config):
		log.error(_("crash report written: {path}").format(path=path))
	return 0


if __name__ == "__main__":
	sys.exit(main())
