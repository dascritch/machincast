"""Captures d'écran du guide utilisateur (https://github.com/dascritch/machincast/issues/128).

« bin/Machin dev-screenshots [REPERTOIRE] » lance ce module, depuis le répertoire de MachinCast, avec le Python du
venv : il remplit la base de TEST d'une démonstration, « Radio Exemple », ouvre l'interface hors de l'écran
(QT_QPA_PLATFORM=offscreen), à une heure fixe, le mercredi 21 octobre 2026 à 09:41:30, et enregistre chaque écran de
CAPTURES en PNG, dans doc/fr/captures par défaut. La base de production n'est jamais ouverte : la connexion est celle
des tests (tests.sample_database), sur la base de test de la configuration des tests. Ses fichiers sonores sont des
copies
d'un fichier de test, dans DEMONSTRATION, un répertoire temporaire propre à ce module. L'état de la diffusion vient
d'une socket d'état publiée ici même ; aucun Machin player ne tourne.

Les captures sont reproductibles : même heure, mêmes données, même style de Qt (Fusion). Refaire les captures après
un changement d'écran, puis les relire avant de les livrer avec le ticket.
"""

import dataclasses
import functools
import logging
import math
import os
import shutil
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["TZ"] = "Europe/Paris"
time.tzset()

import psycopg  # noqa: E402
import pytest  # noqa: E402
from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtWidgets import QApplication, QGroupBox, QWidget  # noqa: E402

from machincast import audio as audio_outputs  # noqa: E402
from machincast.clock import FixedClock  # noqa: E402
from machincast.configuration import Crossfades, Metadata  # noqa: E402
from machincast.database import Role, open_connection  # noqa: E402
from machincast.interface import columns, expandable  # noqa: E402
from machincast.interface.calendar import Calendar  # noqa: E402
from machincast.interface.event_card import EventCard  # noqa: E402
from machincast.interface.preferences import PreferencesWindow, Settings  # noqa: E402
from machincast.interface.preview import PreviewWindow  # noqa: E402
from machincast.interface.search import SearchScreen  # noqa: E402
from machincast.interface.simulation import SimulationScreen, report  # noqa: E402
from machincast.interface.sound_card import SoundCard  # noqa: E402
from machincast.interface.suggestions import Shortfalls, SuggestionsWindow  # noqa: E402
from machincast.interface.window import MainWindow  # noqa: E402
from machincast.player.simulation import simulate  # noqa: E402
from machincast.player.state import StateSocket  # noqa: E402
from tests.database_fixtures import (  # noqa: E402
	configuration_test,
	purge_database,
	reset_database,  # noqa: E402
	sample_connection,
	sample_database_parameters,
)
from tests.sounds import SOUND_FILES, generate_silences  # noqa: E402

log = logging.getLogger("machincast.screenshots")

Connection = psycopg.Connection[tuple[object, ...]]
ROOT = Path(__file__).resolve().parents[1]
GUIDE_SCREENSHOTS = ROOT / "doc" / "fr" / "captures"
DEMONSTRATION = Path(tempfile.gettempdir()) / "machincast-demonstration"
"""Les fichiers sonores de la démonstration : des copies d'un fichier de test, jamais un fichier de l'utilisateur."""
NOW = datetime.fromisoformat("2026-10-21T09:41:30").astimezone()
HISTORY_START = datetime.fromisoformat("2026-10-19T00:00:00").astimezone()
WIDTH, HEIGHT = 1280, 800
WAITING = 5.0
"""Secondes qu'un écran a pour se remplir."""
DEVICES = (
	audio_outputs.Device("antenne", "Carte son de l'antenne"),
	audio_outputs.Device("casque", "Casque de la régie"),
)
"""Les périphériques de sortie que montre la démonstration, à la place de ceux du poste."""
WEEK = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
OPENED_LIST = WEEK[:5]

SCREENSHOTS = (
	"accueil",
	"pour-bien-demarrer",
	"menu-diffusion",
	"liste-evenements",
	"liste-sonores",
	"menu-colonnes",
	"fiche-evenement",
	"fiche-sequence",
	"fiche-banque",
	"fiche-sonore",
	"fiche-erreur",
	"calendrier",
	"simulation",
	"recherche",
	"onglet-airplay",
	"incidents",
	"preferences",
	"preferences-audio",
	"preecoute",
	"preecoute-fichier",
)
"""Les captures, par nom de fichier sans extension, dans l'ordre où elles sont prises."""


@dataclass(frozen=True)
class Sound:
	artist: str | None
	title: str
	duration: int
	"""En secondes."""
	folder: str
	state: str = "active"
	metadata: str = "{}"


SOUNDS = {
	"cafe": Sound(
		"Les Gaufres",
		"Café à minuit",
		214,
		"lourde",
		metadata='{"album": "Nuits courtes", "year": "2019", "genre": "Chanson", "label": "Disques du Canal"}',
	),
	"toulouse": Sound(
		"Nina Lune", "Toulouse sous la pluie", 242, "lourde", metadata='{"year": "2022", "genre": "Pop"}'
	),
	"brique": Sound("Orchestre du Canal", "Brique rose", 228, "lourde", metadata='{"genre": "Jazz"}'),
	"nuit": Sound("Café Noir", "Nuit blanche", 200, "normale", metadata='{"genre": "Rock"}'),
	"garonne": Sound("Les Pavés", "Garonne", 255, "normale"),
	"vinyles": Sound("Sœurs Volantes", "Vieux vinyles", 310, "rare"),
	"nocturne": Sound("Brume", "Nocturne n° 3", 400, "nuit"),
	"identifiant": Sound("Radio Exemple", "Identifiant", 8, "habillage"),
	"matin": Sound("Radio Exemple", "Jingle du matin", 6, "habillage"),
	"pub-debut": Sound("Radio Exemple", "Début de publicité", 5, "habillage"),
	"boulangerie": Sound(None, "Spot de la boulangerie du port", 30, "publicite"),
	"librairie": Sound(None, "Spot de la librairie des Carmes", 30, "publicite"),
	"abime": Sound("Les Gaufres", "Démo abîmée", 180, "normale", "corrupt"),
	"nouveau": Sound(None, "nouvel-arrivage", 190, "lourde", "preview"),
}
BANKS = {
	"identifiant": ("Identifiant station", None, "random", True, ["identifiant"], None),
	"lourde": ("Musique rotation lourde", None, "random", False, ["cafe", "toulouse", "brique"], "lourde"),
	"normale": ("Musique rotation normale", None, "random", False, ["nuit", "garonne", "abime"], "normale"),
	"rare": ("Musique rotation rare", None, "random", False, ["vinyles"], "rare"),
	"nuit": ("Musique rotation de nuit", "La nuit de Radio Exemple", "random", False, ["nocturne"], "nuit"),
	"publicite": ("Publicité", None, "sequential", True, ["boulangerie", "librairie"], None),
}
"""Nom interne, nom public, mode, « ne pas répéter », sonores et dossier indexé de chaque banque."""


@dataclass
class Demonstration:
	"""Les identifiants en base de la démonstration."""

	sounds: dict[str, int]
	banks: dict[str, int]
	events: dict[str, int]
	sequence: int
	plays: list[tuple[datetime, datetime, str, str | None, str]]
	"""Début, fin, sonore, banque et événement de chaque passage de l'historique, le dernier en cours."""


def _un(connection: Connection, query: str, parameters: tuple[object, ...]) -> int:
	line = connection.execute(query, parameters).fetchone()  # type: ignore[arg-type]
	assert line is not None
	return int(str(line[0]))


def _location(key: str) -> Path:
	sound = SOUNDS[key]
	name = sound.title
	if sound.artist is not None:
		name = f"{sound.artist} - {sound.title}"
	return DEMONSTRATION / sound.folder / f"{name}.flac"


BREATHING = Sound("Brume", "Respiration", 40, "nuit")
"""Le sonore de la capture de la frise de la pré-écoute (https://github.com/dascritch/machincast/issues/224) : un
fichier généré, avec ses silences, hors de toute banque."""


def breathing_pieces(duration: float = 40.0, seed: float = 0.0) -> tuple[tuple[float, float], ...]:
	"""Une seconde de silence, une montée, un thème qui respire, une extinction, puis une seconde et demie de silence :
	des morceaux, chacun à son amplitude, sur toute la durée. graine : décale le souffle, pour que deux sonores
	générés ne se ressemblent pas."""
	pieces = [(1.0, 0.0)]
	body = duration - 3.0
	step = max(0.1, body / 400)
	for index in range(round(body / step)):
		instant = index * step
		envelope = min(1.0, instant / 3.0, (body - instant) / 6.0)
		rhythm = instant * 40.0 / body
		breath = 0.55 + 0.3 * math.sin(rhythm * 1.3 + seed) + 0.15 * math.sin(rhythm * 7.1 + 2 * seed)
		pieces.append((step, max(0.0, min(0.95, envelope * breath))))
	pieces += [(0.5, 0.004), (1.5, 0.0)]
	return tuple(pieces)


def fill(connection: Connection) -> Demonstration:
	"""La démonstration, dans la base de test vide."""
	# fichier de MachinCast : les copies de fichier de test de la démonstration précédente.
	shutil.rmtree(DEMONSTRATION, ignore_errors=True)
	sounds = {}
	for key, sound in SOUNDS.items():
		path = _location(key)
		path.parent.mkdir(parents=True, exist_ok=True)
		shutil.copyfile(SOUND_FILES / "sain.flac", path)
		checks = None
		if sound.state == "active":
			checks = NOW - timedelta(days=2)
		sounds[key] = _un(
			connection,
			"INSERT INTO sounds (type, location, artist, title, state, duration, music_metadata, mime_type,"
			" checked_at) VALUES ('file', %s, %s, %s, %s, %s, %s, 'audio/flac', %s) RETURNING id",
			(
				str(path),
				sound.artist,
				sound.title,
				sound.state,
				timedelta(seconds=sound.duration),
				sound.metadata,
				checks,
			),
		)
	breathing = DEMONSTRATION / BREATHING.folder / f"{BREATHING.artist} - {BREATHING.title}.flac"
	generate_silences(breathing, breathing_pieces())
	# Ses silences, retirés à l'antenne, et ses crossfades, tels qu'un audit complet et sa fiche les auraient posés.
	sounds["respiration"] = _un(
		connection,
		"INSERT INTO sounds (type, location, artist, title, state, duration, mime_type, checked_at, detected_start,"
		" detected_end, silence_detection, crossfade_start, crossfade_end, audited_at, audit_threshold)"
		" VALUES ('file', %s, %s, %s, 'active', %s, 'audio/flac', %s, %s, %s, true, %s, %s, %s, -40) RETURNING id",
		(
			str(breathing),
			BREATHING.artist,
			BREATHING.title,
			timedelta(seconds=BREATHING.duration),
			NOW - timedelta(days=2),
			timedelta(seconds=1.0),
			timedelta(seconds=2.0),
			timedelta(seconds=2.0),
			timedelta(seconds=4.0),
			NOW - timedelta(days=2),
		),
	)
	marks = _un(
		connection,
		"INSERT INTO feeds (name, url) VALUES ('Studio mobile', 'https://flux.radio-exemple.test/mobile') RETURNING id",
		(),
	)
	banks = {}
	for key, (name, public_name, mode, no_repeat, members, folder) in BANKS.items():
		banks[key] = _un(
			connection,
			"INSERT INTO banks (internal_name, public_name, mode, no_repeat, crossfade_end_rule, crossfade_end)"
			" VALUES (%s, %s, %s, %s, 'default', '2 s') RETURNING id",
			(name, public_name, mode, no_repeat),
		)
		for position, member in enumerate(members, start=1):
			connection.execute(
				"INSERT INTO bank_sounds (bank_id, sound_id, position) VALUES (%s, %s, %s)",
				(banks[key], sounds[member], position),
			)
		if folder is not None:
			connection.execute(
				"INSERT INTO bank_directories (bank_id, directory) VALUES (%s, %s)",
				(banks[key], str(DEMONSTRATION / folder)),
			)
	sequence = _un(
		connection,
		"INSERT INTO sequences (internal_name, public_name) VALUES ('Passage pub', 'Les partenaires de Radio Exemple')"
		" RETURNING id",
		(),
	)
	for position, (column, value) in enumerate(
		(
			("sound_id", sounds["pub-debut"]),
			("bank_id", banks["publicite"]),
			("bank_id", banks["publicite"]),
			("bank_id", banks["identifiant"]),
		),
		start=1,
	):
		connection.execute(
			f"INSERT INTO sequence_items (sequence_id, position, {column}) VALUES (%s, %s, %s)",  # noqa: S608
			(sequence, position, value),
		)
	events = _events(connection, sounds, banks, sequence)
	stream = _un(
		connection,
		"INSERT INTO sounds (type, feed_id, title, state, fallback_event_id)"
		" VALUES ('stream', %s, 'Studio mobile', 'active', %s) RETURNING id",
		(marks, events["secours"]),
	)
	connection.execute(
		"INSERT INTO event_items (event_id, position, sound_id) VALUES (%s, 1, %s)",
		(events["marche"], stream),
	)
	plays = _history(connection, sounds, banks, events)
	_incidents(connection, sounds, events)
	return Demonstration(sounds, banks, events, sequence, plays)


def _events(connection: Connection, sounds: dict[str, int], banks: dict[str, int], sequence: int) -> dict[str, int]:
	day = datetime.fromisoformat("2026-10-01T00:00").astimezone()

	def create(
		name: str, public_name: str | None, priority: str, start: timedelta | None, end: timedelta | None, days: tuple
	) -> int:
		return _un(
			connection,
			"INSERT INTO events (internal_name, public_name, priority, starts_at, ends_at, recurrence_days)"
			" VALUES (%s, %s, %s, %s, %s, %s::weekday[]) RETURNING id",
			(
				name,
				public_name,
				priority,
				None if start is None else day + start,
				None if end is None else day + end,
				list(days),
			),
		)

	events = {
		"jour": create("Fil de jour", None, "background_programming", None, None, ()),
		"nuit": create("Fil de nuit", None, "background_programming", timedelta(hours=0), timedelta(hours=6), WEEK),
		"matinale": create(
			"Matinale", "La Matinale de Radio Exemple", "show", timedelta(hours=7), timedelta(hours=9), OPENED_LIST
		),
		"journal": create(
			"Le Journal", None, "show", timedelta(hours=12), timedelta(hours=12, minutes=15), OPENED_LIST
		),
		"secours": create("Secours studio", None, "fallback", None, None, ()),
	}
	# La Matinale fait relâche le vendredi : une session sautée (https://github.com/dascritch/machincast/issues/273).
	connection.execute("INSERT INTO event_skips (event_id, day) VALUES (%s, '2026-10-23')", (events["matinale"],))
	saturday = datetime.fromisoformat("2026-10-24T10:00").astimezone()
	events["marche"] = _un(
		connection,
		"INSERT INTO events (internal_name, public_name, priority, starts_at, ends_at)"
		" VALUES ('Direct du marché', 'En direct du marché', 'special', %s, %s) RETURNING id",
		(saturday, saturday + timedelta(hours=2)),
	)
	lists = {
		"jour": [("banque", "identifiant"), ("banque", "lourde"), ("banque", "normale"), ("banque", "lourde")],
		"nuit": [("banque", "identifiant"), ("banque", "nuit")],
		"matinale": [
			("sonore", "matin"),
			("banque", "lourde"),
			("sequence", ""),
			("banque", "normale"),
			("banque", "rare"),
		],
		"journal": [("sonore", "identifiant"), ("banque", "normale")],
		"secours": [("banque", "normale")],
	}
	added_list = {"jour": [("banque", "rare")]}
	for key, items in lists.items():
		for position, (category, value) in enumerate(items + added_list.get(key, []), start=1):
			column, identifier = {
				"banque": ("bank_id", banks.get(value)),
				"sonore": ("sound_id", sounds.get(value)),
				"sequence": ("sequence_id", sequence),
			}[category]
			connection.execute(
				f"INSERT INTO event_items (event_id, position, {column}) VALUES (%s, %s, %s)",  # noqa: S608
				(events[key], position, identifier),
			)
	return events


def _program(instant: datetime) -> str:
	"""L'événement à l'antenne à l'instant, d'après la grille de la démonstration."""
	open_ = instant.weekday() < 5
	hour = instant.hour + instant.minute / 60
	if hour < 6:
		return "nuit"
	if (open_) and (7 <= hour < 9):
		return "matinale"
	if (open_) and (12 <= hour < 12.25):
		return "journal"
	return "jour"


ROTATIONS = {
	"jour": ["identifiant", "lourde", "normale", "lourde", "rare"],
	"nuit": ["identifiant", "nuit"],
	"matinale": ["matin", "lourde", "pub-debut", "publicite", "publicite", "identifiant", "normale", "rare"],
	"journal": ["identifiant", "normale"],
}
"""Ce que chaque événement fait passer, en boucle : une banque, ou un sonore placé directement."""


def _history(
	connection: Connection, sounds: dict[str, int], banks: dict[str, int], events: dict[str, int]
) -> list[tuple[datetime, datetime, str, str | None, str]]:
	"""Les passages, du lundi 19 octobre à maintenant, comme les aurait notés Machin player : le dernier est en
	cours."""
	turns = dict.fromkeys(BANKS, 0)
	positions = dict.fromkeys(ROTATIONS, 0)
	playable_list = {
		key: [m for m in members if SOUNDS[m].state == "active"] for key, (*_, members, _d) in BANKS.items()
	}
	plays: list[tuple[datetime, datetime, str, str | None, str]] = []
	instant = HISTORY_START
	while instant <= NOW:
		event = _program(instant)
		rotation = ROTATIONS[event]
		item = rotation[positions[event] % len(rotation)]
		positions[event] += 1
		bank: str | None = None
		sound = item
		if item in BANKS:
			bank = item
			members = playable_list[item]
			sound = members[turns[item] % len(members)]
			turns[item] += 1
		end = instant + timedelta(seconds=SOUNDS[sound].duration)
		plays.append((instant, end, sound, bank, event))
		instant = end
	lines = []
	for start, end, sound, bank, event in plays:
		play = uuid.uuid4()
		common = (
			play,
			sounds[sound],
			None if bank is None else banks[bank],
			events[event],
			str(_location(sound)),
			SOUNDS[sound].artist,
			SOUNDS[sound].title,
		)
		lines.append((*common, "start", start, None, None))
		if end <= NOW:
			lines.append((*common, "end", end, end - start, True))
	with connection.cursor() as slider:
		slider.executemany(
			"INSERT INTO airplay (play_id, sound_id, bank_id, event_id, location, artist, title,"
			" line_type, logged_at, played_duration, without_incident)"
			" VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
			lines,
		)
	return plays


def _incidents(connection: Connection, sounds: dict[str, int], events: dict[str, int]) -> None:
	entries = [
		(
			"2026-10-20T14:12:05",
			"incident",
			"fichier introuvable",
			f"{_location('garonne')} : aucun fichier",
			"garonne",
			"jour",
		),
		(
			"2026-10-20T16:40:12",
			"warning",
			"fichier modifié",
			f"{_location('nuit')} : taille changée",
			"nuit",
			"jour",
		),
		("2026-10-21T03:10:00", "warning", "blanc", "rien à diffuser dans le fil musical", None, "nuit"),
		(
			"2026-10-21T07:00:00",
			"info",
			"début d'événement",
			"« Matinale », émission, de 07:00 à 09:00",
			None,
			"matinale",
		),
		("2026-10-21T08:20:31", "info", "interruption manuelle", "du sonore « Nuit blanche »", "nuit", "matinale"),
		("2026-10-21T09:00:00", "info", "fin d'événement", "« Matinale »", None, "matinale"),
	]
	for timestamp, level, kind, message, sound, event in entries:
		connection.execute(
			"INSERT INTO log (logged_at, level, kind, message, sound_id, event_id) VALUES (%s, %s, %s, %s, %s, %s)",
			(
				datetime.fromisoformat(timestamp).astimezone(),
				level,
				kind,
				message,
				None if sound is None else sounds[sound],
				events[event],
			),
		)


# ─── État de la diffusion ──────────────────────────────────


def _shows(demonstration: Demonstration, rank: int, start_key: str) -> dict[str, object]:
	start, end, sound, bank, event = demonstration.plays[rank]
	model = SOUNDS[sound]
	text = model.title
	if model.artist is not None:
		text = f"{model.artist} – {model.title}"
	return {
		"sound_id": demonstration.sounds[sound],
		"type": "file",
		"artist": model.artist,
		"title": model.title,
		"location": str(_location(sound)),
		"event": {"jour": "Fil de jour", "nuit": "Fil de nuit", "matinale": "Matinale"}.get(event, event),
		"event_id": demonstration.events[event],
		"event_start": None,
		"event_end": None,
		"sequence": None,
		"sequence_id": None,
		"bank": None if bank is None else BANKS[bank][0],
		"bank_id": None if bank is None else demonstration.banks[bank],
		start_key: start.isoformat(),
		"duration": float(model.duration),
		"estimated_end": end.isoformat(),
		"public_text": text,
		"cut_by": None,
		"cut_by_id": None,
	}


def _finished_shape(card: SoundCard) -> bool:
	return (card.shape is not None) and (card.shape.finished)


def give_relief(connection: Connection, demonstration: Demonstration) -> None:
	"""Les frises de l'onglet Antenne (https://github.com/dascritch/machincast/issues/230) : le sonore en cours et le
	prochain ont un fichier généré à leur durée, à basse fréquence pour l'écrire vite, et leurs silences et
	crossfades, tels qu'un audit complet et leur fiche les auraient posés. De même pour « Café à minuit », dont la
	fiche montre la frise (https://github.com/dascritch/machincast/issues/223)."""
	for key, seed in ((demonstration.plays[-1][2], 0.0), (demonstration.plays[-6][2], 2.0), ("cafe", 4.0)):
		generate_silences(_location(key), breathing_pieces(SOUNDS[key].duration, seed), frequency=4000)
		connection.execute(
			"UPDATE sounds SET detected_start = '1 s', detected_end = '1.5 s', silence_detection = true,"
			" crossfade_start = '2 s', crossfade_end = '4 s', audited_at = %s, audit_threshold = -40 WHERE id = %s",
			(NOW - timedelta(days=2), demonstration.sounds[key]),
		)


def publish(socket: StateSocket, demonstration: Demonstration) -> None:
	"""L'état qu'aurait publié Machin player à MAINTENANT : le dernier passage en cours, le suivant réservé."""
	ongoing = _shows(demonstration, -1, "start")
	start = demonstration.plays[-1][0]
	position = (NOW - start).total_seconds()
	ongoing |= {"position": position, "progress": round(position / float(str(ongoing["duration"])), 3)}
	end = demonstration.plays[-1][1]
	next_ = {
		**_shows(demonstration, -6, "estimated_start"),
		"estimated_start": end.isoformat(),
		"healthy": True,
	}
	next_["estimated_end"] = (end + timedelta(seconds=float(str(next_["duration"])))).isoformat()
	# Les sonores à venir (https://github.com/dascritch/machincast/issues/228) : d'autres passages de la
	# démonstration, enchaînés après le prochain.
	upcoming = []
	following_start = datetime.fromisoformat(str(next_["estimated_end"]))
	for rank in (-2, -3, -4, -5, -7):
		sound = {**_shows(demonstration, rank, "estimated_start"), "healthy": rank != -4}
		sound["estimated_start"] = following_start.isoformat()
		following_start += timedelta(seconds=float(str(sound["duration"])))
		sound["estimated_end"] = following_start.isoformat()
		upcoming.append(sound)
	socket.publish(
		{
			"timestamp": NOW.isoformat(),
			"state": "playing",
			"current": ongoing,
			"next": next_,
			"upcoming": upcoming,
		}
	)


# ─── Captures ──────────────────────────────────────────────


def wait(condition: Callable[[], bool], delay: float = WAITING) -> None:
	limit = time.monotonic() + delay
	while (not condition()) and (time.monotonic() < limit):
		QApplication.processEvents()
		time.sleep(0.02)
	for _ in range(5):
		QApplication.processEvents()


def save(widget: QWidget, path: Path) -> Path:
	wait(lambda: False, 0.2)
	assert widget.grab().save(str(path), "PNG"), path
	log.info(f"capture : {path}")
	return path


def _tab(window: MainWindow, title: str) -> None:
	tabs = window.ui.tabs
	(index,) = [index for index in range(tabs.count()) if tabs.tabText(index) == title]
	tabs.setCurrentIndex(index)


def _screen[T](window: MainWindow, category: type[T]) -> T:
	tabs = window.ui.tabs
	(found,) = [screen for index in range(tabs.count()) if isinstance(screen := tabs.widget(index), category)]
	return found


def _close_tab(window: MainWindow) -> None:
	"""L'onglet capturé se ferme : la barre d'onglets ne déborde pas dans les captures suivantes."""
	window._close(window.ui.tabs.currentIndex())
	wait(lambda: False, 0.1)


def _expand(window: MainWindow, title: str) -> None:
	opened = window.ui.tabs.currentWidget()
	assert opened is not None
	(group,) = [group for group in opened.findChildren(QGroupBox) if group.property(expandable.TITLE) == title]
	expandable.display(group, True)


def produce(directory: Path) -> dict[str, Path]:
	"""Les captures de CAPTURES, dans le répertoire, sur la base de test déjà migrée, qu'elles remplacent."""
	directory.mkdir(parents=True, exist_ok=True)
	application = QApplication.instance()
	if application is None:
		application = QApplication(sys.argv[:1])
	assert isinstance(application, QApplication)
	application.setStyle("Fusion")
	with sample_connection() as owner:
		purge_database(owner)
		demonstration = fill(owner)
		give_relief(owner, demonstration)
	work = Path(tempfile.mkdtemp(prefix="machincast-captures-"))
	configuration = work / "machincast.toml"
	# Les colonnes d'origine, ajustées au contenu : jamais la disposition gardée par le compte qui fait les captures.
	views, columns.FILE = columns.FILE, work / "vues.ini"
	shutil.copyfile(ROOT / "tests" / "configuration-test.toml", configuration)
	socket = StateSocket(work / "lecture.sock")
	socket.open_()
	publish(socket, demonstration)
	clock = FixedClock(NOW)
	connection = open_connection(*sample_database_parameters(), Role.INTERFACE)
	audio = dataclasses.replace(configuration_test().audio, device="antenne", preview="casque")
	devices, audio_outputs.devices = audio_outputs.devices, lambda _output: list(DEVICES)
	window = MainWindow(connection, socket.path, clock, configuration=configuration, audio=audio)
	screenshots: dict[str, Path] = {}

	def take(name: str, widget: QWidget) -> None:
		screenshots[name] = save(widget, directory / f"{name}.png")

	try:
		window.resize(WIDTH, HEIGHT)
		window.show()
		wait(lambda: window.home.ui.playback_state.text() == "En diffusion")
		timelines = (window.home.ongoing_timeline, window.home.next_timeline)
		wait(lambda: all((timeline.shape is not None) and (timeline.shape.finished) for timeline in timelines))
		take("accueil", window)
		gaps = ("Identifiant station", "Musique rotation lourde", "Musique rotation de nuit", "Publicités")
		# Les cartes son en tête, sur PipeWire, tant que l'antenne est à renseigner
		# (https://github.com/dascritch/machincast/issues/339).
		to_choose = dataclasses.replace(audio, output="pipewire", device=None)
		suggestions = SuggestionsWindow(Shortfalls(True, gaps, to_choose), window)
		suggestions.show()
		take("pour-bien-demarrer", suggestions)
		suggestions.close()
		window.broadcast_menu.aboutToShow.emit()
		window.broadcast_menu.popup(window.mapToGlobal(QPoint(200, 30)))
		wait(lambda: window.broadcast_menu.isVisible())
		take("menu-diffusion", window.broadcast_menu)
		window.broadcast_menu.hide()
		_tab(window, "Événements")
		take("liste-evenements", window)
		window.open_list("Sonores")
		take("liste-sonores", window)
		(sounds,) = [list_ for list_ in window.lists if window._titles[list_] == "Sonores"]
		menu = sounds.columns.menu()
		menu.popup(window.mapToGlobal(QPoint(400, 110)))
		wait(lambda: menu.isVisible())
		take("menu-colonnes", menu)
		menu.hide()
		for name, category, identifier in (
			("fiche-evenement", "event", demonstration.events["matinale"]),
			("fiche-sequence", "sequence", demonstration.sequence),
			("fiche-banque", "bank", demonstration.banks["lourde"]),
			("fiche-sonore", "sound", demonstration.sounds["cafe"]),
		):
			window._open(category, identifier, "")
			if category == "sound":
				_expand(window, "Métadonnées")
				card = window.ui.tabs.currentWidget()
				assert isinstance(card, SoundCard)
				wait(functools.partial(_finished_shape, card))
			take(name, window)
			_close_tab(window)
		# Une erreur de fiche, en haut, sur son liseret rouge (https://github.com/dascritch/machincast/issues/270).
		window._open("event", demonstration.events["matinale"], "")
		corrupt = window.ui.tabs.currentWidget()
		assert isinstance(corrupt, EventCard)
		corrupt.ui.internal_name.setText("")
		corrupt.save()
		take("fiche-erreur", window)
		corrupt.load()
		_close_tab(window)
		window._open_calendar()
		wait(lambda: _screen(window, Calendar).isVisible())
		take("calendrier", window)
		_close_tab(window)
		_simulate(window)
		take("simulation", window)
		_close_tab(window)
		window._open_search()
		_screen(window, SearchScreen).field.setText("café")
		take("recherche", window)
		_close_tab(window)
		window._open_airplay()
		take("onglet-airplay", window)
		_close_tab(window)
		_tab(window, "Incidents")
		take("incidents", window)
		# Des crossfades par défaut, pour que la frise de démonstration montre ses fondus
		# (https://github.com/dascritch/machincast/issues/234).
		crossfades = Crossfades(start=timedelta(seconds=2), end=timedelta(seconds=4))
		preferences = PreferencesWindow(Settings(crossfades, audio.device, audio.preview), "pipewire", window)
		preferences.show()
		take("preferences", preferences)
		# La page « Audio », et son bloc des cartes son (https://github.com/dascritch/machincast/issues/339).
		preferences.ui.pages.setCurrentWidget(preferences.ui.page_audio)
		take("preferences-audio", preferences)
		preferences.close()
		preview = PreviewWindow(connection, audio, configuration)
		preview.listen_on_air("Café Noir – Nuit blanche")
		preview.show()
		take("preecoute", preview)
		preview.preview(demonstration.sounds["respiration"])
		wait(lambda: (preview.shape is not None) and (preview.shape.finished))
		preview.player.read()
		preview.player.put_to(14.2)
		preview.player.pause()
		wait(lambda: preview.timeline.head is not None)
		take("preecoute-fichier", preview)
		preview.close()
	finally:
		window.close()
		connection.close()
		socket.shut_down()
		audio_outputs.devices = devices
		columns.FILE = views
		# fichier de MachinCast : le répertoire de travail des captures, sa configuration et sa socket.
		shutil.rmtree(work, ignore_errors=True)
	return screenshots


def _simulate(window: MainWindow) -> None:
	"""La simulation de la fin de la matinée, faite ici sur la base de test, comme l'aurait faite Machin player."""
	window._open_simulation()
	screen = _screen(window, SimulationScreen)
	start, end = NOW.replace(minute=0, second=0), NOW.replace(hour=12, minute=30, second=0)
	screen.start.setDateTime(screen.start.dateTime().fromSecsSinceEpoch(int(start.timestamp())))
	screen.end.setDateTime(screen.end.dateTime().fromSecsSinceEpoch(int(end.timestamp())))
	with open_connection(*sample_database_parameters(), Role.PLAYBACK) as playback:
		result = simulate(
			playback,
			screen.temporary,
			start,
			end,
			seed=1,
			name="simulation",
			metadata=Metadata(hide=False, public_text="Radio Exemple"),
		)
	anomalies = [message for level, _kind, message in result.log if level != "info"]
	plays = screen._read(screen.temporary / "simulation.csv")
	screen.anomalies.addItems(anomalies)
	screen.anomalies.setVisible(bool(anomalies))
	screen.count.setText(report(plays, len(anomalies)))
	screen.period = (start, end)
	screen.export.setEnabled(True)


def main(arguments: list[str]) -> int:
	logging.basicConfig(level=logging.INFO, format="{message}", style="{")
	directory = GUIDE_SCREENSHOTS
	if arguments:
		directory = Path(arguments[0])
	try:
		with sample_connection() as owner:
			reset_database(owner)
	except pytest.skip.Exception as reason:
		log.error(f"captures impossibles : {reason}")
		return 1
	produce(directory)
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
