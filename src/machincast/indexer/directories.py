"""Parcours récursif des répertoires des banques (https://github.com/dascritch/machincast/issues/9, spec § 6.2).

Chaque fichier sonore trouvé dans l'un des répertoires d'une banque (table bank_directories) est enregistré
dans sonores s'il ne l'est pas encore, à l'état apercu et sans être décodé
(https://github.com/dascritch/machincast/issues/69), puis rattaché à la banque en fin de liste. La vérification
qui suit le décode dans le même passage.

- Formats de la spec : mp3, m4a et aac, ogg, flac, wav, quelle que soit la casse de l'extension. L'AIFF (.aiff, .aif)
  est ignoré, comme une extension inconnue : GStreamer en bloque parfois le démarrage
  (https://github.com/dascritch/machincast/issues/284).
- Les fichiers et répertoires cachés (nom commençant par un point) sont ignorés : ce sont des fichiers de
  service, comme les « ._*.mp3 » qu'écrit macOS sur un disque partagé.
- Les sous-répertoires sont parcourus dans l'ordre de leur nom, sans suivre les liens symboliques vers d'autres
  répertoires, qui pourraient former une boucle ; un répertoire de banque qui est lui-même un lien est suivi.
- Un fichier déjà indexé n'est jamais dupliqué, même trouvé par plusieurs banques : l'emplacement est unique.
- Un sonore trouvé dans le répertoire d'une banque y est rattaché s'il n'y est pas, même retiré à la main, sauf si sa
  durée est connue et sort des durées de la banque (https://github.com/dascritch/machincast/issues/195).
- Un sonore de durée encore inconnue, trouvé dans le répertoire d'une banque qui a des durées, attend la vérification :
  attach_in_waiting ne l'y rattache qu'ensuite, s'il est dans ses durées ou que sa durée reste inconnue. Un sonore
  qui sort des durées d'une banque ne passe donc jamais par elle, et rien ne le dit, ni ligne ni compte : seule la
  fiche de la banque signale ses durées (https://github.com/dascritch/machincast/issues/210). Un nouveau sonore est
  annoncé avec la première banque qui le garde, ou seul s'il n'en a aucune.
- Après la vérification, remove_outside_durations retire de chaque banque les sonores de durée connue qui sortent de ses
  durées, qu'ils viennent de ses répertoires ou qu'ils aient été ajoutés à la main.
- Un répertoire introuvable ou illisible est signalé en anomalie ; les autres banques sont indexées.

Chaque fichier est enregistré dans sa propre transaction, pour qu'une interruption garde le travail fait.
"""

import logging
import os
import threading
from collections.abc import Collection, Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import list_or_none
from machincast.indexer.check import Report, SoundState
from machincast.protection import INDEXED_EXTENSIONS

log = logging.getLogger(__name__)

EXTENSIONS = INDEXED_EXTENSIONS
"""Extensions des formats de la spec § 6.2, en minuscules (machincast.protection)."""


def _cache(name: str) -> bool:
	return name.startswith(".")


OUTSIDE_DURATIONS = (
	"s.duration IS NOT NULL AND ((b.min_duration IS NOT NULL AND s.duration < b.min_duration)"
	" OR (b.max_duration IS NOT NULL AND s.duration > b.max_duration))"
)
"""Condition SQL : le sonore s, de durée connue, sort des durées de la banque b, bornes comprises dans les durées
(https://github.com/dascritch/machincast/issues/147, https://github.com/dascritch/machincast/issues/195)."""


def sound_files(directory: Path) -> Iterator[Path]:
	"""Fichiers sonores du répertoire et de ses sous-répertoires, dans l'ordre de leur chemin."""

	def flag(error: OSError) -> None:
		log.warning(f"{error.filename} : répertoire illisible ({error.strerror}) ; ignoré")

	for current, under_directories, files in os.walk(directory, onerror=flag):
		# Trié en place : os.walk descend ensuite dans cet ordre, et saute les répertoires cachés retirés.
		under_directories[:] = sorted(name for name in under_directories if not _cache(name))
		for name in sorted(files):
			path = Path(current) / name
			if (not _cache(name)) and (path.suffix.lower() in EXTENSIONS) and (path.is_file()):
				yield path


@dataclass(frozen=True)
class Waiting:
	"""Un sonore de durée encore inconnue, trouvé dans le répertoire d'une banque qui a des durées."""

	bank: int
	name: str
	sound: int
	location: str


@dataclass
class Scan:
	"""Ce que le parcours laisse à attach_in_waiting, une fois les sonores vérifiés."""

	waits: list[Waiting] = field(default_factory=list)
	unannounced: dict[int, str] = field(default_factory=dict)
	"""Les nouveaux sonores qu'aucune banque n'a encore gardés, avec leur emplacement."""


def _attach(connection: psycopg.Connection[TupleRow], bank: int, sound: int) -> bool:
	"""Rattache le sonore à la fin de la banque, s'il n'y est pas et qu'il ne sort pas de ses durées."""
	return (
		connection.execute(
			"INSERT INTO bank_sounds (bank_id, sound_id, position)"
			" SELECT %s, %s, (SELECT COALESCE(MAX(position), 0) + 1 FROM bank_sounds WHERE bank_id = %s)"
			f" WHERE NOT EXISTS (SELECT 1 FROM sounds s, banks b WHERE s.id = %s AND b.id = %s AND {OUTSIDE_DURATIONS})"
			" ON CONFLICT (bank_id, sound_id) DO NOTHING",
			(bank, sound, bank, sound, bank),
		).rowcount
		> 0
	)


def _announce(report: Report, scan: Scan, sound: int, name: str, location: str) -> None:
	"""Une ligne par rattachement ; la première banque d'un nouveau sonore l'annonce avec lui, sans compter de
	rattachement."""
	if scan.unannounced.pop(sound, None) is not None:
		log.info(f"{location} : nouveau sonore, ajouté à la banque {name}")
		return
	report.attached_list += 1
	log.info(f"{location} : rattaché à la banque {name}")


def _save(
	connection: psycopg.Connection[TupleRow], bank: int, name: str, location: str, report: Report, scan: Scan
) -> None:
	"""Enregistre le fichier comme nouveau sonore s'il ne l'est pas, et le rattache à la banque, ou le met en attente
	de sa vérification ; une ligne dit chaque rattachement."""
	with connection.transaction():
		line = connection.execute(
			"SELECT s.id, s.duration IS NULL AND (b.min_duration IS NOT NULL OR b.max_duration IS NOT NULL)"
			" FROM sounds s, banks b WHERE s.location = %s AND s.deleted_at IS NULL AND b.id = %s",
			(location, bank),
		).fetchone()
		if line is None:
			line = connection.execute(
				"INSERT INTO sounds (type, location, state, indexed_at)"
				" VALUES ('file', %s, %s, clock_timestamp())"
				" RETURNING id, EXISTS (SELECT 1 FROM banks WHERE id = %s"
				" AND (min_duration IS NOT NULL OR max_duration IS NOT NULL))",
				(location, SoundState.PREVIEW.value, bank),
			).fetchone()
			assert line is not None
			report.new_list += 1
			scan.unannounced[int(str(line[0]))] = location
		sound, in_waiting = int(str(line[0])), line[1] is True
		# Un sonore de durée connue, hors des durées de la banque, n'y est pas rattaché ; un sonore de durée encore
		# inconnue attend sa vérification, si la banque a des durées
		# (https://github.com/dascritch/machincast/issues/195, https://github.com/dascritch/machincast/issues/210).
		attached = False
		if in_waiting:
			scan.waits.append(Waiting(bank, name, sound, location))
		else:
			attached = _attach(connection, bank, sound)
	if attached:
		_announce(report, scan, sound, name, location)


def attach_in_waiting(connection: psycopg.Connection[TupleRow], report: Report, scan: Scan) -> None:
	"""Après la vérification, rattache les sonores en attente aux banques dont ils sont dans les durées, ou dont leur
	durée reste inconnue ; annonce les nouveaux sonores qu'aucune banque n'a gardés. Un sonore hors des durées d'une
	banque n'y entre pas, sans ligne ni compte (https://github.com/dascritch/machincast/issues/210)."""
	for waiting in scan.waits:
		with connection.transaction():
			attached = _attach(connection, waiting.bank, waiting.sound)
		if attached:
			_announce(report, scan, waiting.sound, waiting.name, waiting.location)
	for location in scan.unannounced.values():
		log.info(f"{location} : nouveau sonore")


def index_directories(
	connection: psycopg.Connection[TupleRow], report: Report, stop: threading.Event | None = None
) -> Scan:
	"""Enregistre et rattache à leurs banques les fichiers sonores de leurs répertoires ; complète le bilan. Renvoie les
	rattachements qui attendent la vérification, pour attach_in_waiting.

	arret : une fois posé, le parcours s'arrête avant le fichier suivant.

	La connexion doit avoir endossé le rôle de l'indexation (machincast.database.open_connection).
	"""
	scan = Scan()
	with connection.transaction():
		directories = connection.execute(
			"SELECT b.id, b.internal_name, r.directory FROM bank_directories r JOIN banks b ON b.id = r.bank_id"
			" WHERE b.deleted_at IS NULL ORDER BY b.id, r.directory"
		).fetchall()
	for bank, name, directory in directories:
		path = Path(os.path.normpath(str(directory)))
		if not path.is_absolute():
			log.warning(f"{directory} : répertoire relatif, ignoré pour la banque {name}")
			continue
		if not path.is_dir():
			log.warning(f"{path} : répertoire introuvable, ignoré pour la banque {name}")
			continue
		for file in sound_files(path):
			if (stop is not None) and (stop.is_set()):
				return scan
			_save(connection, int(str(bank)), str(name), str(file), report, scan)
	return scan


def remove_outside_durations(
	connection: psycopg.Connection[TupleRow], report: Report, identifiers: Collection[int] | None = None
) -> None:
	"""Retire de chaque banque les sonores dont la durée en base est connue et sort de ses durées ; complète le bilan
	(https://github.com/dascritch/machincast/issues/195).

	Seule la ligne de bank_sounds disparaît : le sonore reste en base, dans ses autres banques, séquences et
	événements, et son fichier n'est jamais touché. La durée comparée est la durée complète, même saisie à la main.
	identifiants : seuls ces sonores ; tous sans eux. Chaque retrait a sa ligne, désignée par le chemin du fichier.
	"""
	with connection.transaction():
		outside = connection.execute(
			"SELECT bs.bank_id, bs.sound_id, b.internal_name, s.location, s.duration, b.min_duration, b.max_duration"
			" FROM bank_sounds bs JOIN banks b ON b.id = bs.bank_id JOIN sounds s ON s.id = bs.sound_id"
			f" WHERE (%s::bigint[] IS NULL OR s.id = ANY(%s)) AND b.deleted_at IS NULL AND {OUTSIDE_DURATIONS}"
			" ORDER BY b.id, bs.position",
			(list_or_none(identifiers), list_or_none(identifiers)),
		).fetchall()
		for bank, sound, name, location, duration, minimum, maximum in outside:
			connection.execute("DELETE FROM bank_sounds WHERE bank_id = %s AND sound_id = %s", (bank, sound))
			report.removals += 1
			log.info(f"{location} : retiré de la banque {name}, {_outside_durations(duration, minimum, maximum)}")


def _duration(value: object) -> str:
	"""« 3:34 », ou « 1:02:05 » au-delà d'une heure, à la seconde la plus proche : un fichier d'une seconde décodé en
	0,998 seconde dure « 0:01 »."""
	assert isinstance(value, timedelta), value
	hours, rest = divmod(round(value.total_seconds()), 3600)
	minutes, seconds = divmod(rest, 60)
	if hours > 0:
		return f"{hours}:{minutes:02d}:{seconds:02d}"
	return f"{minutes}:{seconds:02d}"


def _outside_durations(duration: object, minimum: object, maximum: object) -> str:
	"""« durée 0:30 plus courte que son minimum, 1:00 », ou « … plus longue que son maximum, 2:00 »."""
	if (isinstance(minimum, timedelta)) and (isinstance(duration, timedelta)) and (duration < minimum):
		return f"durée {_duration(duration)} plus courte que son minimum, {_duration(minimum)}"
	return f"durée {_duration(duration)} plus longue que son maximum, {_duration(maximum)}"
