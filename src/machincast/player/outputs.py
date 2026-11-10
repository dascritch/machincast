"""Masquage des métadonnées et modules de sortie (https://github.com/dascritch/machincast/issues/19, spec § 4.8, § 5.3).

Sorties privées, qui disent tout :

- journal du binaire : chaque passage qui commence, en information sur la sortie standard ; les alertes et incidents
  du log vont sur la sortie d'erreur (machincast.player.saving.record) ;
- CSV : un fichier par jour, nommé avec la date du jour (outputs.csv « airplay.csv » donne « airplay-2026-10-15.csv »),
  une ligne par passage terminé, séparateur « ; », UTF-8 avec BOM ; jamais réécrit ;
- .pls : les PLAYLIST derniers fichiers joués, streams compris, du plus ancien au plus récent ; réécrit à chaque
  passage.

Sortie publique, avec le masquage :

- HTML : page statique, réécrite à chaque passage, qui montre le sonore à l'antenne puis les PRECEDENTS précédents,
  sans JavaScript, rafraîchie toutes les RAFRAICHISSEMENT secondes. L'emplacement d'un fichier n'y paraît jamais.

Masquage : la valeur retenue est celle du premier niveau renseigné, événement, séquence, banque, sonore, puis la
configuration (metadata.hide). L'événement d'un passage est celui qui lui prête son nom, s'il y en a un
(airplay.lender_event_id, https://github.com/dascritch/machincast/issues/399) : son nom, son nom public et son masquage
valent, sur toutes les sorties. Pour le passage en cours, c'est l'événement qui prête son nom à cet instant
(Outputs.lend) : la page publique change dès qu'un prêt commence ou cesse, sans attendre le passage suivant. Masqués, l'artiste et le titre laissent la place au premier nom public renseigné,
celui de l'événement, de la séquence puis de la banque (https://github.com/dascritch/machincast/issues/99), sinon au
texte public de la configuration. Les indicateurs sont lus en base au moment d'écrire la page.

Une sortie qui ne peut pas être écrite est signalée une fois dans le log (alerte « sortie inaccessible »), sans arrêter
la diffusion ; elle est de nouveau signalée si elle redevient inaccessible après avoir été écrite.
"""

import csv
import functools
import html
import io
import logging
import os
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.configuration import Configuration, Metadata
from machincast.configuration import Outputs as Paths
from machincast.conversion import boolean_or_none, text_or_none
from machincast.i18n import N_, _, current, logged
from machincast.player.saving import Play, record
from machincast.protection import check_writing

log = logging.getLogger(__name__)

PREVIOUS_LIST = 20
"""Passages précédents montrés par la page publique, sous le sonore à l'antenne."""
PLAYLIST = 100
"""Fichiers de la playlist .pls."""
REFRESH = 30
"""Délai de rafraîchissement de la page publique, en secondes."""
CSV_COLUMNS = (
	"start",
	"end",
	"duration",
	"artist",
	"title",
	"location",
	"event",
	"sequence",
	"bank",
	"without_incident",
)
"""L'en-tête du CSV de l'airplay et de la simulation : un format de données, en anglais, qui ne dépend pas de la langue
(https://github.com/dascritch/machincast/issues/367)."""
YES_NO = {True: "yes", False: "no"}
"""Les valeurs de without_incident dans les CSV."""
INACCESSIBLE_OUTPUT = N_("inaccessible output")


@dataclass(frozen=True)
class Line:
	"""Un passage de l'airplay, avec ce qu'il faut pour l'écrire sur chaque sortie."""

	start: datetime
	end: datetime | None
	duration: timedelta | None
	without_incident: bool | None
	artist: str | None
	title: str | None
	location: str | None
	event: str | None
	public_name: str | None
	"""Premier nom public renseigné : celui de l'événement, de la séquence, puis de la banque
	(https://github.com/dascritch/machincast/issues/99)."""
	sequence: str | None
	bank: str | None
	hidings: tuple[bool | None, bool | None, bool | None, bool | None]
	"""Masquage de l'événement, de la séquence, de la banque et du sonore ; None : non renseigné."""


def hides(hidings: tuple[bool | None, ...], default: bool) -> bool:
	"""Premier niveau renseigné, dans l'ordre événement, séquence, banque, sonore ; sinon la valeur de la
	configuration."""
	first = default
	for value in hidings:
		if value is not None:
			first = value
			break
	return first


def first_public_name(*names: object) -> str | None:
	"""Premier nom public renseigné, dans l'ordre donné : événement, séquence, banque."""
	first = None
	for name in names:
		if name:
			first = str(name)
			break
	return first


def artist_and_title(line: Line) -> str:
	part_list = []
	for part in (line.artist, line.title):
		if part:
			part_list.append(part)
	return " – ".join(part_list)


def public_text(line: Line, metadata: Metadata) -> str:
	"""Ce que la sortie publique affiche du passage : l'artiste et le titre, sauf s'ils sont masqués."""
	if not hides(line.hidings, metadata.hide):
		visible = artist_and_title(line)
		if visible:
			return visible
	return (line.public_name) or (metadata.public_text)


def csv_path(model: Path, day: datetime) -> Path:
	"""CSV du jour : la date au format ISO 8601 entre le nom et l'extension du chemin de la configuration."""
	return model.with_name(f"{model.stem}-{day:%Y-%m-%d}{model.suffix}")


def _duration(duration: timedelta | None) -> str:
	if duration is None:
		return ""
	seconds = round(duration.total_seconds())
	return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _hour(instant: datetime | None) -> str:
	if instant is None:
		return ""
	return f"{instant.astimezone():%Y-%m-%d %H:%M:%S}"


def read_plays(
	connection: psycopg.Connection[TupleRow],
	count: int | None,
	play: uuid.UUID | None = None,
	since: datetime | None = None,
	ongoing_lender: tuple[int | None] | None = None,
) -> list[Line]:
	"""Les derniers passages, du plus récent au plus ancien, ou un seul ; nombre None : tous, depuis cet instant s'il
	est donné. La connexion a le rôle de la lecture, ou celui de l'interface pour l'export de son onglet Airplay
	(https://github.com/dascritch/machincast/issues/244).

	L'événement d'un passage est celui qui lui prête son nom, sinon le sien. ongoing_lender : pour un passage encore
	en cours, l'événement qui prête son nom à cet instant, ou (None,) sans prêt, à la place de celui qu'il avait à son
	début (https://github.com/dascritch/machincast/issues/399)."""
	override = ongoing_lender is not None
	if ongoing_lender is None:
		lender = None
	else:
		lender = ongoing_lender[0]
	with connection.transaction():
		lines = connection.execute(
			"SELECT d.logged_at, f.logged_at, f.played_duration, f.without_incident, d.artist, d.title, d.location,"
			" e.internal_name, e.public_name, q.public_name, b.public_name, q.internal_name, b.internal_name,"
			" e.hide_metadata, q.hide_metadata, b.hide_metadata, s.hide_metadata"
			" FROM airplay d"
			" LEFT JOIN airplay f ON f.play_id = d.play_id AND f.line_type = 'end'"
			" LEFT JOIN events e ON e.id = CASE WHEN %s AND f.play_id IS NULL THEN COALESCE(%s::bigint, d.event_id)"
			" ELSE COALESCE(d.lender_event_id, d.event_id) END"
			" LEFT JOIN sequences q ON q.id = d.sequence_id"
			" LEFT JOIN banks b ON b.id = d.bank_id"
			" LEFT JOIN sounds s ON s.id = d.sound_id"
			" WHERE d.line_type = 'start' AND (%s::uuid IS NULL OR d.play_id = %s::uuid)"
			" AND (%s::timestamptz IS NULL OR d.logged_at >= %s::timestamptz)"
			" ORDER BY d.logged_at DESC, d.id DESC LIMIT %s",
			(override, lender, play, play, since, since, count),
		).fetchall()
	plays = []
	for (
		start,
		end,
		duration,
		without_incident,
		artist,
		title,
		location,
		event,
		e_public_name,
		q_public_name,
		b_public_name,
		sequence,
		bank,
		e_mask,
		q_mask,
		b_mask,
		s_mask,
	) in lines:
		if isinstance(end, datetime):
			known_end = end
		else:
			known_end = None
		if isinstance(duration, timedelta):
			known_duration = duration
		else:
			known_duration = None
		plays.append(
			Line(
				start=start,
				end=known_end,
				duration=known_duration,
				without_incident=boolean_or_none(without_incident),
				artist=text_or_none(artist),
				title=text_or_none(title),
				location=text_or_none(location),
				event=text_or_none(event),
				public_name=first_public_name(e_public_name, q_public_name, b_public_name),
				sequence=text_or_none(sequence),
				bank=text_or_none(bank),
				hidings=(
					boolean_or_none(e_mask),
					boolean_or_none(q_mask),
					boolean_or_none(b_mask),
					boolean_or_none(s_mask),
				),
			)
		)
	return plays


def public_page(lines: list[Line], metadata: Metadata, instant: datetime) -> str:
	"""Page HTML publique : le sonore à l'antenne, puis les précédents, masquage appliqué."""
	if (lines) and (lines[0].end is None):
		ongoing = lines[0]
	else:
		ongoing = None
	if ongoing is not None:
		previous_list = lines[1:]
	else:
		previous_list = lines
	name = html.escape(metadata.public_text)

	def play(line: Line) -> str:
		text = html.escape(public_text(line, metadata))
		return f'<time datetime="{line.start.isoformat()}">{line.start.astimezone():%H:%M}</time> {text}'

	on_air = name
	if ongoing is not None:
		on_air = play(ongoing)
	line_list = []
	for previous in previous_list[:PREVIOUS_LIST]:
		line_list.append(f"\t\t\t<li>{play(previous)}</li>")
	items = "\n".join(line_list)
	updated = _("Updated at {time}").format(
		time=f'<time datetime="{instant.isoformat()}">{instant.astimezone():%H:%M:%S}</time>'
	)
	return f"""<!DOCTYPE html>
<html lang="{current()}">
<head>
	<meta charset="utf-8">
	<meta http-equiv="refresh" content="{REFRESH}">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{_("{name}: on air").format(name=name)}</title>
	<style>
		body {{ font-family: system-ui, sans-serif; margin: 1rem auto; max-width: 40rem; padding: 0 1rem; }}
		.en-cours p {{ font-size: 1.4rem; }}
		ol {{ list-style: none; padding: 0; }}
		time {{ font-variant-numeric: tabular-nums; margin-right: 0.5rem; opacity: 0.7; }}
	</style>
</head>
<body>
	<h1>{name}</h1>
	<section class="en-cours">
		<h2>{_("On air")}</h2>
		<p>{on_air}</p>
	</section>
	<section>
		<h2>{_("Previously")}</h2>
		<ol class="precedents">
{items}
		</ol>
	</section>
	<footer><p>{updated}</p></footer>
</body>
</html>
"""


def playlist(lines: list[Line]) -> str:
	"""Playlist .pls : du plus ancien au plus récent, sans masquage."""
	played_list = []
	for line in reversed(lines):
		if line.location:
			played_list.append(line)
	entries = []
	for number, line in enumerate(played_list, start=1):
		duration = -1
		if line.duration is not None:
			duration = round(line.duration.total_seconds())
		entries.append(f"File{number}={line.location}")
		entries.append(f"Title{number}={(artist_and_title(line)) or (line.location)}")
		entries.append(f"Length{number}={duration}")
	return "\n".join(["[playlist]", *entries, f"NumberOfEntries={len(played_list)}", "Version=2", ""])


def csv_line(line: Line) -> str:
	buffer = io.StringIO()
	if line.without_incident is None:
		without_incident = ""
	else:
		without_incident = YES_NO[line.without_incident]
	csv.writer(buffer, delimiter=";", lineterminator="\r\n").writerow(
		[
			_hour(line.start),
			_hour(line.end),
			_duration(line.duration),
			(line.artist) or (""),
			(line.title) or (""),
			(line.location) or (""),
			(line.event) or (""),
			(line.sequence) or (""),
			(line.bank) or (""),
			without_incident,
		]
	)
	return buffer.getvalue()


def _write(path: Path, content: str) -> None:
	"""Remplace le fichier d'un coup : un lecteur ne voit jamais de page à moitié écrite."""
	check_writing(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
	try:
		with os.fdopen(descriptor, "w", encoding="utf-8") as file:
			file.write(content)
		os.chmod(temporary, 0o644)
		os.replace(temporary, path)  # fichier de MachinCast : sortie, jamais un fichier sonore (check_writing)
	except BaseException:
		Path(temporary).unlink(missing_ok=True)  # fichier de MachinCast : fichier temporaire de la sortie
		raise


@dataclass
class Outputs:
	"""Modules de sortie du binaire lecture."""

	paths: Paths
	metadata: Metadata
	_inaccessible_list: set[Path] = field(default_factory=set, init=False, repr=False)
	_lender: tuple[int | None] = field(default=(None,), init=False, repr=False)
	"""L'événement qui prête son nom au passage en cours (https://github.com/dascritch/machincast/issues/399)."""

	@classmethod
	def since(cls, configuration: Configuration) -> "Outputs":
		return cls(configuration.outputs, configuration.metadata)

	def lend(
		self, connection: psycopg.Connection[TupleRow], lender: int | None, instant: datetime | None = None
	) -> None:
		"""L'événement qui prête son nom au passage en cours, ou None ; à l'instant donné, la page publique est réécrite
		aussitôt (https://github.com/dascritch/machincast/issues/399)."""
		self._lender = (lender,)
		if instant is not None:
			self.update(connection, instant)

	def started_play(self, connection: psycopg.Connection[TupleRow], play: Play) -> None:
		"""Annonce le passage dans le journal du binaire, puis met à jour la page publique et la playlist."""
		for line in read_plays(connection, 1, play.id, ongoing_lender=self._lender):
			place = ""
			if line.event:
				place = f" ({line.event})"
			log.info(
				_("on air: {artist_and_title}{place}").format(
					artist_and_title=(artist_and_title(line)) or (line.location), place=place
				)
			)
		self.update(connection, play.start)

	def announce(self, kind: str, message: str) -> None:
		"""Un début ou une fin d'événement ou de séquence, dans le journal du binaire
		(https://github.com/dascritch/machincast/issues/153)."""
		log.info(_("{kind}: {message}").format(kind=logged(kind), message=logged(message)))

	def finished_play(self, connection: psycopg.Connection[TupleRow], play: Play, instant: datetime) -> None:
		"""Ajoute le passage au CSV de son jour, puis met à jour la page publique et la playlist."""
		for line in read_plays(connection, 1, play.id):
			path = csv_path(self.paths.csv, line.start.astimezone())
			self._output(connection, path, instant, functools.partial(self._add, path, line))
		self.update(connection, instant)

	def update(self, connection: psycopg.Connection[TupleRow], instant: datetime) -> None:
		"""Réécrit la page publique et la playlist depuis l'airplay."""
		lines = read_plays(connection, max(PREVIOUS_LIST + 1, PLAYLIST), ongoing_lender=self._lender)
		page = public_page(lines[: PREVIOUS_LIST + 1], self.metadata, instant)
		list_ = playlist(lines[:PLAYLIST])
		self._output(connection, self.paths.html, instant, lambda: _write(self.paths.html, page))
		self._output(connection, self.paths.pls, instant, lambda: _write(self.paths.pls, list_))

	@staticmethod
	def _add(path: Path, line: Line) -> None:
		check_writing(path)
		path.parent.mkdir(parents=True, exist_ok=True)
		new = not path.exists()
		file_encoding = "utf-8"
		if new:
			file_encoding = "utf-8-sig"
		with path.open("a", encoding=file_encoding, newline="") as file:
			if new:
				file.write(";".join(CSV_COLUMNS) + "\r\n")
			file.write(csv_line(line))

	def _output(
		self, connection: psycopg.Connection[TupleRow], path: Path, instant: datetime, write: Callable[[], None]
	) -> None:
		try:
			write()
		except OSError as error:
			if path not in self._inaccessible_list:
				self._inaccessible_list.add(path)
				record(
					connection,
					"warning",
					INACCESSIBLE_OUTPUT,
					N_("{path}: {error}").format(path=path, error=error),
					instant,
				)
		else:
			self._inaccessible_list.discard(path)
