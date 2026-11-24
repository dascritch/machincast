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

SOUND_GAIN est demandé, lui (https://github.com/dascritch/machincast/issues/643) : avant de jouer un fichier, la
diffusion demande aux plugins son gain, en dB (sound_gain) ; sans plugin, ou sans réponse, il joue tel quel. Un gain
est borné à MAXIMUM_GAIN, ce que l'élément volume de GStreamer permet.

SOUND_EFFECTS aussi (https://github.com/dascritch/machincast/issues/644) : avant de jouer un sonore, fichier ou stream,
la diffusion demande aux plugins ses effets, une description d'éléments GStreamer (sound_effects), par exemple un
compresseur LV2 ; celles de plusieurs plugins s'enchaînent, dans leur ordre de chargement.
"""

import math
from datetime import datetime, timedelta
from typing import Any

import psycopg
from psycopg.rows import TupleRow

from machincast.player import queries
from machincast.player.broadcast_types import Parameters
from machincast.player.rundown import Choice
from machincast.player.saving import Play
from machincast.plugins.points import Points
from machincast.shared.grid import Occurrence

SERVICE_START = "player.service_start"
SERVICE_STOP = "player.service_stop"
EVENT_START = "player.event_start"
EVENT_STOP = "player.event_stop"
SEQUENCE_START = "player.sequence_start"
SEQUENCE_STOP = "player.sequence_stop"
SOUND_START = "player.sound_start"
SOUND_STOP = "player.sound_stop"
SOUND_GAIN = "player.sound_gain"
SOUND_EFFECTS = "player.sound_effects"
MAXIMUM_GAIN = 20.0
"""Le plus grand gain, en dB : un volume de 10, le maximum de l'élément volume de GStreamer."""

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


def _sound_data(connection: Connection, choice: Choice) -> dict[str, Any]:
	"""Ce que les points SOUND_GAIN et SOUND_EFFECTS donnent du sonore : la connexion, le sonore, sa banque, son
	événement et ses properties."""
	with connection.transaction():
		line = queries.sound_properties(connection, choice.sound)
	properties: dict[str, Any] = {}
	if (line is not None) and (isinstance(line[0], dict)):
		properties = line[0]
	return {
		"connection": connection,
		"sound": choice.sound,
		"bank": choice.bank,
		"event": choice.occurrence.event.id,
		"properties": properties,
	}


def sound_gain(connection: Connection, points: Points | None, choice: Choice) -> float:
	"""Le gain du fichier choisi, en dB, que répond le premier plugin abonné à SOUND_GAIN ; 0 sans réponse. Le plugin
	reçoit la connexion de la diffusion, le sonore, sa banque, son événement et ses properties, la mesure de son niveau
	comprise (https://github.com/dascritch/machincast/issues/642)."""
	if (points is None) or (points.subscribers(SOUND_GAIN) == []):
		return 0.0
	for _plugin, answer in points.collect(SOUND_GAIN, _sound_data(connection, choice)):
		if (isinstance(answer, (int, float))) and (not isinstance(answer, bool)) and (math.isfinite(answer)):
			return min(float(answer), MAXIMUM_GAIN)
	return 0.0


def sound_effects(connection: Connection, points: Points | None, choice: Choice, *, stream: bool) -> str | None:
	"""Les effets du sonore choisi, les descriptions d'éléments GStreamer répondues par les plugins abonnés à
	SOUND_EFFECTS, enchaînées dans leur ordre de chargement ; None sans réponse. Le plugin reçoit, en plus des données de
	sound_gain, stream : vrai pour un stream."""
	if (points is None) or (points.subscribers(SOUND_EFFECTS) == []):
		return None
	data = _sound_data(connection, choice)
	data["stream"] = stream
	found = []
	for _plugin, answer in points.collect(SOUND_EFFECTS, data):
		if (isinstance(answer, str)) and (answer.strip() != ""):
			found.append(answer.strip())
	if found == []:
		return None
	return " ! ".join(found)
