"""Ce que Machin player dit aux plugins de ce qu'il joue (https://github.com/dascritch/machincast/issues/589).

La diffusion (machincast.player.broadcast) prévient les plugins abonnés à ses points d'extension
(machincast.plugins.points.CORE), sans les attendre : notify les appelle dans le fil des plugins, et consigne
l'erreur de l'un d'eux sans arrêter l'antenne. En simulation, la diffusion n'a pas de points : aucun n'est appelé.

Les données sont faites pour être sérialisées telles quelles : heures en ISO 8601, durées et positions en secondes,
identifiants en entiers.

- SERVICE_START, SERVICE_STOP : le démarrage et l'arrêt de la diffusion, avec l'instant ; l'arrêt sur une erreur la
  donne (error).
- EVENT_START, EVENT_STOP : l'événement à l'antenne qui change (event_data) ; celui qui prête son nom à un autre
  l'est sous son propre nom, avec l'événement qu'il fait jouer (playing).
- SEQUENCE_START, SEQUENCE_STOP : la séquence qui commence ou finit (sequence_data).
- SOUND_START, SOUND_STOP : le passage d'un sonore (sound_data, stopped_sound), avec ses positions réelles dans le
  fichier.
"""

from datetime import datetime, timedelta
from typing import Any

import psycopg
from psycopg.rows import TupleRow

from machincast.player import queries
from machincast.player.broadcast_types import Parameters
from machincast.player.saving import Play
from machincast.shared.grid import Occurrence

SERVICE_START = "player.service_start"
SERVICE_STOP = "player.service_stop"
EVENT_START = "player.event_start"
EVENT_STOP = "player.event_stop"
SEQUENCE_START = "player.sequence_start"
SEQUENCE_STOP = "player.sequence_stop"
SOUND_START = "player.sound_start"
SOUND_STOP = "player.sound_stop"

Connection = psycopg.Connection[TupleRow]


def iso(instant: datetime | None) -> str | None:
	"""L'instant en ISO 8601, avec son décalage ; une heure murale, sans fuseau, est celle du poste."""
	if instant is None:
		return None
	if instant.tzinfo is None:
		return instant.astimezone().isoformat()
	return instant.isoformat()


def seconds(duration: timedelta | None) -> float | None:
	if duration is None:
		return None
	return duration.total_seconds()


def event_data(connection: Connection, occurrence: Occurrence, instant: datetime) -> dict[str, Any]:
	"""L'occurrence à l'antenne : l'événement, ses noms, sa priorité, et les heures de début et de fin de
	l'occurrence ; None pour un fil musical permanent, ou sans fin."""
	with connection.transaction():
		found = queries.event_public_name(connection, occurrence.event.id)
	public_name = None
	if (found is not None) and (found[0] is not None):
		public_name = str(found[0])
	return {
		"instant": iso(instant),
		"event": occurrence.event.id,
		"name": occurrence.event.name,
		"public_name": public_name,
		"priority": occurrence.event.priority.value,
		"start": iso(occurrence.start),
		"end": iso(occurrence.end),
	}


def sequence_data(connection: Connection, sequence: int, occurrence: Occurrence, instant: datetime) -> dict[str, Any]:
	"""La séquence, ses noms, et l'événement qui la fait jouer."""
	with connection.transaction():
		found = queries.sequence_names(connection, sequence)
	name, public_name = str(sequence), None
	if found is not None:
		name = str(found[0])
		if found[1] is not None:
			public_name = str(found[1])
	return {
		"instant": iso(instant),
		"sequence": sequence,
		"name": name,
		"public_name": public_name,
		"event": occurrence.event.id,
		"event_name": occurrence.event.name,
	}


def sound_data(play: Play, parameters: Parameters, instant: datetime) -> dict[str, Any]:
	"""Le passage qui commence : le sonore, ses noms, sa durée jouée, et sa position de départ dans le fichier
	(start_position, 0 sans rognage ; None pour un stream, qui n'en a pas)."""
	start_position: float | None = 0.0
	if parameters.offset is not None:
		start_position = parameters.offset.total_seconds()
	if parameters.stream:
		start_position = None
	return {
		"instant": iso(instant),
		"play": str(play.id),
		"sound": play.sound,
		"artist": parameters.artist,
		"title": parameters.title,
		"location": parameters.location,
		"stream": parameters.stream,
		"duration": seconds(parameters.duration),
		"start_position": start_position,
		"event": play.event,
		"lender": play.lender,
		"sequence": play.sequence,
		"bank": play.bank,
	}


def stopped_sound(
	started: dict[str, Any], start: datetime, instant: datetime, *, cut: bool, error: str | None
) -> dict[str, Any]:
	"""La fin du passage : ce qui a été dit de son début, l'instant, le temps joué, et la position de fin réelle dans
	le fichier (end_position : celle de départ, plus le temps joué ; None pour un stream)."""
	played = (instant - start).total_seconds()
	end_position = None
	if started["start_position"] is not None:
		end_position = float(started["start_position"]) + played
	return {
		**started,
		"instant": iso(instant),
		"start": iso(start),
		"played": played,
		"end_position": end_position,
		"cut": cut,
		"error": error,
	}
