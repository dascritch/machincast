"""Mode simulation de Machin player (https://github.com/dascritch/machincast/issues/21, spec § 5.5).

La simulation rejoue la diffusion entre deux instants, avec la même logique que la diffusion réelle
(machincast.player.broadcast), pour vérifier une grille avant sa mise à l'antenne :

- aucune écriture en base : toute la simulation se fait dans une seule transaction en lecture seule et en lecture
  répétable (read_only) ; PostgreSQL refuse donc toute écriture, et l'état de départ est figé à son ouverture ;
- l'état de départ (positions dans les listes, cycles aléatoires, compteurs de lectures) est lu dans l'airplay, puis
  tenu en mémoire avec les passages, le log et les expirations simulés (SimulatedHistory) ;
- aucune sortie sonore : les voies sont simulées (SimulatedEngine), et la diffusion avance d'échéance en échéance à
  l'horloge de la simulation (fin d'un sonore, début de son crossfade de fin, début ou fin d'un événement) ;
- un stream n'est pas contacté : on suppose qu'il tient jusqu'à la fin de son événement, ou jusqu'à une coupure ;
- une graine rend le hasard reproductible ;
- seules des sorties .csv, .pls et .html sont produites, pour toute la période, nommées par défaut « simulation »
  suivi des dates de début et de fin (default_name), dans le répertoire des sorties de la configuration. L'artiste
  et le titre y sont masqués comme sur la page publique ; l'emplacement de chaque fichier permet de vérifier ce qui
  est joué.
"""

import html
import logging
import uuid
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.clock import FixedClock
from machincast.configuration import Crossfades, Metadata
from machincast.conversion import boolean_or_none, integer_or_none, text_or_none
from machincast.i18n import N_, _, current, logged, ngettext
from machincast.player.broadcast import Broadcast
from machincast.player.engine import DeadAir, PlaybackTrack, TrackState
from machincast.player.expiry import KIND as EXPIRED_SOUND
from machincast.player.expiry import Expiry, _cause
from machincast.player.grid import next_change, read_grid
from machincast.player.history import IN_DATABASE, LastPlay
from machincast.player.outputs import CSV_COLUMNS, Line, csv_line, first_public_name, hides, playlist
from machincast.player.saving import LEVELS, Play
from machincast.randomness import create_randomness

log = logging.getLogger(__name__)

Connection = psycopg.Connection[TupleRow]

WAITING_IN_DEAD_AIR = timedelta(minutes=1)
"""Pendant un blanc, la simulation réessaie à cet intervalle : un sonore peut redevenir jouable."""


class InvalidPeriod(ValueError):
	"""La fin de la simulation ne suit pas son début."""


def default_name(start: datetime, end: datetime) -> str:
	"""« simulation » suivi des dates de début et de fin, à la minute, en heure du poste."""
	return f"simulation-{start.astimezone():%Y-%m-%dT%H%M}-{end.astimezone():%Y-%m-%dT%H%M}"


@contextmanager
def read_only(connection: Connection) -> Iterator[None]:
	"""Une seule transaction, en lecture seule et en lecture répétable, toujours annulée à la fin.

	Les transactions ouvertes à l'intérieur deviennent des points de sauvegarde de celle-ci : PostgreSQL y refuse toute
	écriture (ReadOnlySqlTransaction).
	"""
	with connection.transaction() as transaction:
		connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
		yield
		raise psycopg.Rollback(transaction)


# ─── Voies simulées ────────────────────────────────────────


class SimulatedTrack:
	"""Une voie sans son : sa position suit l'horloge de la simulation."""

	def __init__(self, clock: FixedClock, duration: timedelta | None) -> None:
		self.clock = clock
		self.start = clock.now()
		self.duration = duration
		self.state: TrackState = "en cours"
		self.error: str | None = None
		self.planned_stop: timedelta | None = None

	def position(self) -> timedelta:
		elapsed = self.clock.now() - self.start
		if self.duration is None:
			return elapsed
		return min(elapsed, self.duration)

	def blocked(self) -> bool:
		"""Une voie simulée démarre toujours."""
		return False

	def frozen(self) -> bool:
		"""Une voie simulée avance toujours."""
		return False

	def dead_air(self) -> DeadAir | None:
		"""Une voie simulée n'a pas de son, ni donc de blanc (https://github.com/dascritch/machincast/issues/122)."""
		return None

	def heard(self) -> bool:
		return True

	def planned_end(self) -> datetime | None:
		if self.planned_stop is not None:
			return self.start + self.planned_stop
		return None if self.duration is None else self.start + self.duration

	def handle(self) -> None:
		end = self.planned_end()
		if (self.state == "en cours") and (end is not None) and (self.clock.now() >= end):
			self.state = "finie"

	def cut(self) -> None:
		if self.state == "en cours":
			self.state = "coupée"

	def shut_down(self) -> None:
		pass

	def fade(self, target: float, duration: timedelta) -> None:
		pass

	def switch_off(self, duration: timedelta) -> None:
		self.planned_stop = self.position() + max(duration, timedelta(0))
		self.handle()

	def delete_output_fade(self) -> None:
		pass

	def volume_to(self, instant: timedelta) -> float:
		return 1.0


class SimulatedEngine:
	"""Moteur sans sortie audio : aucune voie GStreamer n'est créée."""

	def __init__(self, clock: FixedClock) -> None:
		self.clock = clock
		self._tracks: list[SimulatedTrack] = []

	def play(
		self,
		path: Path | str,
		duration: timedelta | None,
		start_crossfade: timedelta = timedelta(0),
		end_crossfade: timedelta = timedelta(0),
		silent: bool = False,
		offset: timedelta | None = None,
		departure: float = 0.0,
		arrival: float = 0.0,
	) -> PlaybackTrack:
		"""La durée d'un sonore rogné est déjà sans ses silences : le décalage ne change rien à la voie simulée."""
		track = SimulatedTrack(self.clock, duration)
		self._tracks.append(track)
		return track

	def handle_messages(self) -> None:
		for track in self._tracks:
			track.handle()
		self._tracks = [track for track in self._tracks if track.state == "en cours"]

	def cut(self) -> None:
		for track in self._tracks:
			track.cut()
		self._tracks = []

	def shut_down(self) -> None:
		self._tracks = []

	def deadlines(self) -> list[datetime]:
		"""Fins prévues des voies en cours."""
		return [end for track in self._tracks if (end := track.planned_end()) is not None]


# ─── Historique en mémoire ─────────────────────────────────


@dataclass
class SimulatedPlay:
	play: Play
	artist: str | None
	title: str | None
	location: str | None
	end: datetime | None = None
	without_incident: bool | None = None


@dataclass
class SimulatedHistory:
	"""L'airplay et le log de la base, lus sans y écrire, plus les passages, le log et les expirations simulés."""

	simulated_plays: list[SimulatedPlay] = field(default_factory=list)
	log: list[tuple[str, str, str]] = field(default_factory=list)
	"""Lignes de log simulées : niveau, nature, message."""
	expired_list: set[int] = field(default_factory=set)
	"""Sonores expirés pendant la simulation, consignés une seule fois. Ils ne sont déjà plus jouables : leur maximum
	de lectures, compté avec les passages simulés, ou leur fin de période est atteint."""

	def plays(self, connection: Connection, sounds: Collection[int]) -> dict[int, int]:
		counts = IN_DATABASE.plays(connection, sounds)
		for simulated in self.simulated_plays:
			if simulated.play.sound in counts:
				counts[simulated.play.sound] += 1
		return counts

	def played_via_bank(self, connection: Connection, bank: int) -> list[int]:
		simulated_list = [s.play.sound for s in reversed(self.simulated_plays) if s.play.bank == bank]
		return simulated_list + IN_DATABASE.played_via_bank(connection, bank)

	def last_item(self, connection: Connection, event: int, since: datetime | None) -> int | None:
		for simulated in reversed(self.simulated_plays):
			play = simulated.play
			if (play.event == event) and ((since is None) or (play.start >= since)):
				return play.item
		return IN_DATABASE.last_item(connection, event, since)

	def last_play(self, connection: Connection) -> LastPlay | None:
		if self.simulated_plays:
			play = self.simulated_plays[-1].play
			return LastPlay(play.id, play.bank, play.start, play.event, play.item, play.item_sequence)
		return IN_DATABASE.last_play(connection)

	def begin_play(
		self,
		connection: Connection,
		sound: int,
		bank: int | None,
		event: int | None,
		item: int | None,
		instant: datetime,
		sequence: int | None = None,
		item_sequence: int | None = None,
	) -> Play:
		line = connection.execute(
			"SELECT s.artist, s.title, COALESCE(s.location, s.stream_url, m.url) FROM sounds s"
			" LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
			(sound,),
		).fetchone()
		artist, title, location = line if line is not None else (None, None, None)
		play = Play(uuid.uuid4(), sound, bank, event, item, instant, sequence, item_sequence)
		self.simulated_plays.append(
			SimulatedPlay(
				play,
				text_or_none(artist),
				text_or_none(title),
				text_or_none(location),
			)
		)
		return play

	def finish_play(
		self,
		connection: Connection,
		play: Play,
		instant: datetime,
		cut: bool = False,
		error: str | None = None,
		kind: str = N_("interrupted playback"),
	) -> None:
		for simulated in self.simulated_plays:
			if simulated.play.id == play.id:
				simulated.end, simulated.without_incident = instant, error is None
		references = {"sound": play.sound, "bank": play.bank, "event": play.event}
		if error is not None:
			self.record(connection, "incident", kind, error, instant, **references)
		elif cut:
			self.record(connection, "info", N_("clean cut"), N_("start of an event"), instant, **references)

	def record(
		self,
		connection: Connection,
		level: str,
		kind: str,
		message: str,
		instant: datetime | None = None,
		sound: int | None = None,
		bank: int | None = None,
		event: int | None = None,
	) -> None:
		if level != "info":
			text = _("simulation: {level}: {kind}: {message}").format(
				level=LEVELS.get(level, level), kind=logged(kind), message=logged(message)
			)
			if instant is not None:
				text = _("simulation: {moment}: {level}: {kind}: {message}").format(
					moment=f"{instant.astimezone():%Y-%m-%d %H:%M:%S}",
					level=LEVELS.get(level, level),
					kind=logged(kind),
					message=logged(message),
				)
			log.warning(text)
		self.log.append((level, kind, message))

	def expire(self, connection: Connection, instant: datetime, sound: int | None = None) -> list[Expiry]:
		lines = connection.execute(
			"SELECT id, max_plays, broadcast_end, COALESCE(title, location, stream_url) FROM sounds"
			" WHERE state = 'active' AND (%s::bigint IS NULL OR id = %s::bigint)"
			" AND (broadcast_end <= %s OR max_plays IS NOT NULL)",
			(sound, sound, instant),
		).fetchall()
		candidates = {int(str(i)): (m, f, n) for i, m, f, n in lines if int(str(i)) not in self.expired_list}
		play_counts = self.plays(connection, list(candidates))
		expiries = []
		for identifier, (maximum, end, name) in candidates.items():
			limit = integer_or_none(maximum)
			broadcast_end = end if isinstance(end, datetime) else None
			if ((limit is not None) and (play_counts[identifier] >= limit)) or (
				(broadcast_end is not None) and (broadcast_end <= instant)
			):
				expiry = Expiry(identifier, _cause(limit, play_counts[identifier], broadcast_end, instant))
				self.expired_list.add(identifier)
				self.record(
					connection,
					"info",
					EXPIRED_SOUND,
					N_("{name}: {cause}").format(name=name, cause=expiry.cause),
					instant,
					identifier,
				)
				expiries.append(expiry)
		return expiries

	def lines(self, connection: Connection) -> list[Line]:
		"""Passages simulés, dans l'ordre où ils commencent, avec leur événement, leur banque et le masquage de chaque
		niveau, comme machincast.player.outputs.read_plays pour l'airplay."""
		events = {
			identifier: (name, public_name, hides)
			for identifier, name, public_name, hides in connection.execute(
				"SELECT id, internal_name, public_name, hide_metadata FROM events WHERE id = ANY(%s)",
				([s.play.event for s in self.simulated_plays],),
			).fetchall()
		}
		sequences = {
			identifier: (name, public_name, hides)
			for identifier, name, public_name, hides in connection.execute(
				"SELECT id, internal_name, public_name, hide_metadata FROM sequences WHERE id = ANY(%s)",
				([s.play.sequence for s in self.simulated_plays],),
			).fetchall()
		}
		banks = {
			identifier: (name, public_name, hides)
			for identifier, name, public_name, hides in connection.execute(
				"SELECT id, internal_name, public_name, hide_metadata FROM banks WHERE id = ANY(%s)",
				([s.play.bank for s in self.simulated_plays],),
			).fetchall()
		}
		sounds: dict[object, object] = dict(
			connection.execute(
				"SELECT id, hide_metadata FROM sounds WHERE id = ANY(%s)",
				([s.play.sound for s in self.simulated_plays],),
			).fetchall()
		)
		result = []
		for simulated in sorted(self.simulated_plays, key=lambda s: s.play.start):
			play = simulated.play
			event = events.get(play.event, (None, None, None))
			sequence = sequences.get(play.sequence, (None, None, None))
			bank = banks.get(play.bank, (None, None, None))
			result.append(
				Line(
					start=play.start,
					end=simulated.end,
					duration=None if simulated.end is None else simulated.end - play.start,
					without_incident=simulated.without_incident,
					artist=simulated.artist,
					title=simulated.title,
					location=simulated.location,
					event=text_or_none(event[0]),
					public_name=first_public_name(event[1], sequence[1], bank[1]),
					sequence=text_or_none(sequence[0]),
					bank=text_or_none(bank[0]),
					hidings=(
						boolean_or_none(event[2]),
						boolean_or_none(sequence[2]),
						boolean_or_none(bank[2]),
						boolean_or_none(sounds.get(play.sound)),
					),
				)
			)
		return result


def hide(line: Line, metadata: Metadata) -> Line:
	"""Le passage tel que la page publique le montre : artiste et titre masqués selon les cinq niveaux, remplacés
	par le premier nom public renseigné ou le texte public (machincast.player.outputs). L'emplacement reste : il permet
	de vérifier ce qui est joué."""
	if not hides(line.hidings, metadata.hide):
		return line
	return replace(line, artist=None, title=(line.public_name) or (metadata.public_text))


# ─── Simulation ────────────────────────────────────────────


@dataclass
class Result:
	plays: list[Line] = field(default_factory=list)
	log: list[tuple[str, str, str]] = field(default_factory=list)
	"""Log simulé : niveau, nature, message."""
	files: tuple[Path, Path, Path] | None = None
	"""Sorties écrites : .csv, .pls, .html."""


def _next_deadline(
	connection: Connection, broadcast: Broadcast, engine: SimulatedEngine, instant: datetime, end: datetime
) -> datetime:
	"""Le prochain instant où la diffusion peut changer : fin de voie, début de crossfade de fin, grille, blanc."""
	candidates = [end, *engine.deadlines()]
	current = broadcast.current
	if (current is not None) and (not current.following_requested) and (current.parameters.duration is not None):
		candidates.append(current.play.start + current.parameters.duration - current.parameters.end_crossfade)
	change = next_change(read_grid(connection), instant)
	if change is not None:
		candidates.append(change)
	if (current is None) and (not broadcast.outgoing_list):
		candidates.append(instant + WAITING_IN_DEAD_AIR)
	after = [candidate for candidate in candidates if candidate > instant]
	if not after:
		return end
	return min(after)


def simulate(
	connection: Connection,
	directory: Path,
	start: datetime,
	end: datetime,
	seed: int | None = None,
	name: str | None = None,
	metadata: Metadata | None = None,
	crossfades: Crossfades | None = None,
) -> Result:
	"""Simule la diffusion de debut à fin, puis écrit les sorties de la simulation dans le répertoire.

	La connexion a endossé le rôle de la lecture (machincast.database.open_connection) ; rien n'est écrit en base.
	"""
	if end <= start:
		raise InvalidPeriod(_("the end must follow the start"))
	history = SimulatedHistory()
	clock = FixedClock(start)
	engine = SimulatedEngine(clock)
	with read_only(connection):
		broadcast = Broadcast(
			connection,
			engine,
			clock,
			create_randomness(seed),
			history=history,
			crossfades=(crossfades) or (Crossfades()),
		)
		broadcast.start()
		while clock.now() < end:
			instant = clock.now()
			broadcast.step()
			if (broadcast.current is None) and (not broadcast.outgoing_list) and (broadcast.in_waiting is not None):
				# Le sonore en attente démarre au même instant, sans laisser de blanc.
				broadcast.step()
			clock.advance(_next_deadline(connection, broadcast, engine, instant, end) - instant)
		broadcast.halt()
		lines = history.lines(connection)
	hidden_list = [hide(line, (metadata) or (Metadata(hide=False, public_text=""))) for line in lines]
	files = export(hidden_list, history.log, directory, (name) or (default_name(start, end)), start, end)
	return Result(lines, history.log, files)


# ─── Sorties de la simulation ──────────────────────────────


def _end_hour(end: datetime | None) -> str:
	if end is None:
		return ""
	return f"{end.astimezone():%H:%M:%S}"


def simulation_page(lines: list[Line], log: list[tuple[str, str, str]], start: datetime, end: datetime) -> str:
	period = _("from {start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M}").format(
		start=start.astimezone(), end=end.astimezone()
	)

	def cell(text: str | None) -> str:
		return f"<td>{html.escape((text) or (''))}</td>"

	rows = "\n".join(
		"\t\t\t<tr>"
		+ cell(f"{line.start.astimezone():%Y-%m-%d %H:%M:%S}")
		+ cell(_end_hour(line.end))
		+ cell(line.artist)
		+ cell(line.title)
		+ cell(line.location)
		+ cell(line.event)
		+ cell(line.sequence)
		+ cell(line.bank)
		+ "</tr>"
		for line in lines
	)
	anomalies = "\n".join(
		f'\t\t<li class="{html.escape(level)}">'
		+ html.escape(
			_("{level}: {kind}: {message}").format(
				level=LEVELS.get(level, level), kind=logged(kind), message=logged(message)
			)
		)
		+ "</li>"
		for level, kind, message in log
		if level != "info"
	)
	plays = ngettext(
		"{count} play. Nothing was written to the database.",
		"{count} plays. Nothing was written to the database.",
		len(lines),
	).format(count=len(lines))
	headers = "".join(
		f"<th>{html.escape(header)}</th>"
		for header in (
			_("Start"),
			_("End"),
			_("Artist"),
			_("Title"),
			_("Location"),
			_("Event"),
			_("Sequence"),
			_("Bank"),
		)
	)
	return f"""<!DOCTYPE html>
<html lang="{current()}">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>Simulation {html.escape(period)}</title>
	<style>
		body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
		table {{ border-collapse: collapse; }}
		th, td {{ border-bottom: 1px solid #ccc; padding: 0.2rem 0.6rem; text-align: left; }}
		.incident {{ color: #a00; }}
	</style>
</head>
<body>
	<h1>Simulation {html.escape(period)}</h1>
	<p>{plays}</p>
	<h2>{_("Alerts and incidents")}</h2>
	<ul>
{anomalies}
	</ul>
	<h2>{_("Plays")}</h2>
	<table>
		<thead><tr>{headers}</tr></thead>
		<tbody>
{rows}
		</tbody>
	</table>
</body>
</html>
"""


def export(
	lines: list[Line],
	log: list[tuple[str, str, str]],
	directory: Path,
	name: str,
	start: datetime,
	end: datetime,
) -> tuple[Path, Path, Path]:
	"""CSV, .pls et .html de la simulation, pour toute la période ; un fichier existant est remplacé."""
	directory.mkdir(parents=True, exist_ok=True)
	csv_path, pls_path, html_path = (directory / f"{name}{extension}" for extension in (".csv", ".pls", ".html"))
	with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
		file.write(";".join(CSV_COLUMNS) + "\r\n")
		for line in lines:
			file.write(csv_line(line))
	pls_path.write_text(playlist(list(reversed(lines))), encoding="utf-8")
	html_path.write_text(simulation_page(lines, log, start, end), encoding="utf-8")
	return csv_path, pls_path, html_path
