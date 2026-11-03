"""Enregistrement de l'airplay et du log (https://github.com/dascritch/machincast/issues/17, spec § 3.1 et § 5.2).

Le binaire lecture n'écrit que par ce module, et seulement des insertions : ses droits PostgreSQL ne lui
permettent ni de modifier ni de supprimer une ligne d'airplay ou de log, ni de lire le log (pas de RETURNING).

- Airplay : deux lignes par passage, reliées par play_id. Chacune recopie l'emplacement (pour un stream, son
  adresse directe ou celle de son feed), l'artiste et le titre du sonore au moment du passage, et référence
  le sonore, la banque qui l'a fourni (aucune pour un sonore placé directement dans l'événement), l'événement et
  l'élément de sa liste, et, pour un sonore joué par une séquence, la séquence et son élément
  (https://github.com/dascritch/machincast/issues/99). La ligne de fin donne la durée effectivement diffusée et
  l'indicateur without_incident.
- Log : chaque opération, normale (info) ou non (alerte, incident), avec sa nature, un message et ses références.
  Une coupure nette est une opération normale ; une lecture interrompue par une erreur est un incident, que
  l'appelant peut nommer plus précisément (flux tombé d'un stream).

Les alertes et incidents du log sont aussi écrits dans le journal du binaire, sur sa sortie d'erreur
(https://github.com/dascritch/machincast/issues/19).

Les heures viennent de l'horloge du binaire (machincast.clock), pour que la simulation et les tests soient
reproductibles.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import psycopg
from psycopg.rows import TupleRow

from machincast.i18n import N_, _, logged

Level = Literal["info", "warning", "incident"]
LEVELS = {"info": _("info"), "warning": _("warning"), "incident": _("incident")}
"""Les niveaux du log à l'écran et dans les messages, par leur valeur en base
(https://github.com/dascritch/machincast/issues/358)."""

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Play:
	id: uuid.UUID
	sound: int
	bank: int | None
	event: int | None
	item: int | None
	start: datetime
	sequence: int | None = None
	"""Séquence qui a fait jouer le sonore (https://github.com/dascritch/machincast/issues/99)."""
	item_sequence: int | None = None
	"""Élément de cette séquence."""


def record(
	connection: psycopg.Connection[TupleRow],
	level: str,
	kind: str,
	message: str,
	instant: datetime | None = None,
	sound: int | None = None,
	bank: int | None = None,
	event: int | None = None,
) -> None:
	"""Ajoute une ligne au log ; sans instant, l'heure du serveur PostgreSQL. Jamais de RETURNING : la lecture
	n'a pas le droit de lire le log."""
	if level != "info":
		# Sortie privée stderr (https://github.com/dascritch/machincast/issues/19) : alertes et incidents.
		log.warning(
			_("{level}: {kind}: {message}").format(
				level=LEVELS.get(level, level), kind=logged(kind), message=logged(message)
			)
		)
	with connection.transaction():
		connection.execute(
			"INSERT INTO log (logged_at, level, kind, message, sound_id, bank_id, event_id)"
			" VALUES (COALESCE(%s, clock_timestamp()), %s, %s, %s, %s, %s, %s)",
			(instant, level, kind, message, sound, bank, event),
		)


def _start(connection: psycopg.Connection[TupleRow], play: Play) -> None:
	connection.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, bank_id, event_id, event_item_id,"
		" sequence_id, sequence_item_id, location, artist, title)"
		" SELECT %s, 'start', %s, s.id, %s, %s, %s, %s, %s, COALESCE(s.location, s.stream_url, m.url), s.artist,"
		" s.title FROM sounds s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
		(
			play.id,
			play.start,
			play.bank,
			play.event,
			play.item,
			play.sequence,
			play.item_sequence,
			play.sound,
		),
	)


def _end(connection: psycopg.Connection[TupleRow], play: Play, instant: datetime, without_incident: bool) -> None:
	# La ligne de fin recopie la ligne de début : l'artiste et le titre restent ceux du moment du passage.
	connection.execute(
		"INSERT INTO airplay (play_id, line_type, logged_at, sound_id, bank_id, event_id, event_item_id,"
		" sequence_id, sequence_item_id, location, artist, title, played_duration, without_incident)"
		" SELECT play_id, 'end', %s, sound_id, bank_id, event_id, event_item_id, sequence_id,"
		" sequence_item_id, location, artist, title, %s, %s FROM airplay"
		" WHERE play_id = %s AND line_type = 'start'",
		(instant, instant - play.start, without_incident, play.id),
	)


def begin_play(
	connection: psycopg.Connection[TupleRow],
	sound: int,
	bank: int | None,
	event: int | None,
	item: int | None,
	instant: datetime,
	sequence: int | None = None,
	item_sequence: int | None = None,
) -> Play:
	"""Ligne de début d'un passage ; l'artiste et le titre sont recopiés tels qu'ils sont à cet instant."""
	play = Play(uuid.uuid4(), sound, bank, event, item, instant, sequence, item_sequence)
	with connection.transaction():
		_start(connection, play)
	return play


def finish_play(
	connection: psycopg.Connection[TupleRow],
	play: Play,
	instant: datetime,
	cut: bool = False,
	error: str | None = None,
	kind: str = N_("interrupted playback"),
) -> None:
	"""Ligne de fin d'un passage, avec la durée diffusée ; une coupure ou une erreur est aussi consignée au log,
	l'erreur en incident de la nature donnée."""
	with connection.transaction():
		_end(connection, play, instant, error is None)
		references = {"sound": play.sound, "bank": play.bank, "event": play.event}
		if error is not None:
			record(connection, "incident", kind, error, instant, **references)
		elif cut:
			record(connection, "info", N_("clean cut"), N_("start of an event"), instant, **references)
