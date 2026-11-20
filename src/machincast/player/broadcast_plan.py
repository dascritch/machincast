"""Les calculs de la diffusion sur les sonores et les événements (https://github.com/dascritch/machincast/issues/440) :
ce que joue une décision, où tombe une coupure, le crossfade d'un sonore, l'horizon et la fin estimée d'un passage.
machincast.player.broadcast les appelle."""

import logging
import uuid
from datetime import datetime, timedelta

from machincast.i18n import N_
from machincast.player.broadcast_types import CUTOFF_HORIZON, PRIORITIES, Parameters, Playback
from machincast.player.engine import (
	PlaybackTrack,
	overlay,
	sequencing,
)
from machincast.player.rundown import INSERTED, OUTSIDE_LIST, Choice, Cutoff
from machincast.player.saving import Play
from machincast.shared.grid import Occurrence

log = logging.getLogger(__name__)


def _lender_id(choice: Choice) -> int | None:
	"""L'événement au nom de qui le sonore passe (https://github.com/dascritch/machincast/issues/399)."""
	if choice.lender is None:
		return None
	return choice.lender.event.id


def _play_item(choice: Choice) -> int | None:
	"""L'élément de liste qui a fait jouer le sonore ; aucun pour le stream d'un feed qui coupe l'antenne, ni pour un
	sonore inséré à la main (https://github.com/dascritch/machincast/issues/530)."""
	if choice.item.id in (OUTSIDE_LIST, INSERTED):
		return None
	return choice.item.id


def _planned_play(choice: Choice, start: datetime) -> Play:
	line = choice.line
	if line is None:
		sequence = None
	else:
		sequence = line.sequence
	if line is None:
		sequence_item = None
	else:
		sequence_item = line.id
	return Play(
		uuid.uuid4(),
		choice.sound,
		choice.bank,
		choice.occurrence.event.id,
		_play_item(choice),
		start,
		sequence,
		sequence_item,
	)


def _same_cutoff(planned: Cutoff | None, cutoff: Cutoff | None) -> bool:
	if (planned is None) or (cutoff is None):
		return (planned is None) and (cutoff is None)
	return (planned.instant == cutoff.instant) and (planned.occurrence.key == cutoff.occurrence.key)


def _occurrence_end(occurrence: Occurrence) -> datetime | None:
	if occurrence.end is None:
		return None
	return occurrence.end.astimezone()


def _following_instant(
	start: datetime, parameters: Parameters, occurrence: Occurrence, cutoff: Cutoff | None
) -> datetime | None:
	"""Quand le sonore qui commence à debut appellera son suivant : à la coupure, au début de son crossfade de fin, ou,
	pour un stream, à la fin de son événement ; None si on ne le sait pas."""
	if cutoff is not None:
		return cutoff.instant
	if parameters.duration is not None:
		return start + max(timedelta(0), parameters.duration - parameters.end_crossfade)
	if not parameters.stream:
		return None
	return _occurrence_end(occurrence)


def _following_start(
	start: datetime, parameters: Parameters, occurrence: Occurrence, cutoff: Cutoff | None, incoming: Parameters
) -> datetime | None:
	"""Quand démarrera le sonore entrant, après celui qui commence à debut : à la coupure, qui est nette ; au début du
	crossfade de fin s'ils se superposent, sinon à la fin ; pour un stream, à la fin de son événement, où il s'éteint.
	None si on ne le sait pas."""
	if cutoff is not None:
		return cutoff.instant
	if parameters.duration is not None:
		return start + sequencing(parameters.duration, parameters.end_crossfade, incoming.start_crossfade)
	end = None
	if parameters.stream:
		end = _occurrence_end(occurrence)
	if (end is None) or (overlay(parameters.end_crossfade, incoming.start_crossfade)):
		return end
	return end + parameters.end_crossfade


def _continues_sequence(previous: Choice | None, choice: Choice | None) -> bool:
	"""Le passage suit-il le précédent dans la même séquence, un élément plus loin ?"""
	if (previous is None) or (choice is None) or (previous.line is None) or (choice.line is None):
		return False
	return (previous.item.id == choice.item.id) and (choice.line.position > previous.line.position)


def _hour(instant: datetime) -> str:
	"""« 20:00 », ou « 19:59:51 » quand les secondes comptent."""
	if instant.second == 0:
		return f"{instant:%H:%M}"
	return f"{instant:%H:%M:%S}"


def _on_air_event(occurrence: Occurrence) -> str:
	"""« « Journal », émission, de 20:00 à 20:30 » ; « depuis 19:00 » sans fin, « permanent » pour un fil musical."""
	start, end = occurrence.start, occurrence.end
	hours = N_("permanent")
	if (start is not None) and (end is None):
		hours = N_("since {hour}").format(hour=_hour(start))
	if (start is not None) and (end is not None):
		hours = N_("from {hour} to {hour2}").format(hour=_hour(start), hour2=_hour(end))
	return N_("“{name}”, {priorities}, {hours}").format(
		name=occurrence.event.name, priorities=PRIORITIES[occurrence.event.priority], hours=hours
	)


def _horizon(playback: Playback, instant: datetime) -> datetime:
	"""Jusqu'où un événement qui commence coupe le sonore : jusqu'à ce que le suivant soit demandé, au début de son
	crossfade de fin ; pour un stream, jusqu'à la fin de son occurrence, où il s'éteint, ou CUTOFF_HORIZON."""
	return _horizon_of(playback.play.start, playback.parameters, playback.choice.occurrence, instant)


def _horizon_of(start: datetime, parameters: Parameters, occurrence: Occurrence, instant: datetime) -> datetime:
	duration = parameters.duration
	if duration is not None:
		return start + duration - parameters.end_crossfade
	horizon = max(instant, start) + CUTOFF_HORIZON
	end = _occurrence_end(occurrence)
	if end is not None:
		horizon = min(horizon, end)
	return horizon


def _estimated_end(playback: Playback) -> datetime | None:
	"""L'instant de la coupure annoncée, sinon la fin du sonore ; pour un stream, la fin de son événement, où il
	s'éteint (https://github.com/dascritch/machincast/issues/242), None sans elle."""
	if playback.cutoff is not None:
		return playback.cutoff.instant
	if playback.parameters.duration is None:
		if not playback.parameters.stream:
			return None
		return _occurrence_end(playback.choice.occurrence)
	return playback.play.start + playback.parameters.duration


def _seconds(duration: timedelta | None) -> float | None:
	if duration is None:
		return None
	return round(duration.total_seconds(), 3)


def _progress(position: timedelta, duration: timedelta | None) -> float | None:
	"""Part jouée du sonore, de 0 à 1, au millième ; None sans durée connue."""
	if not duration:
		return None
	return round(min(1.0, position / duration), 3)


def _buffer(track: PlaybackTrack, parameters: Parameters) -> dict[str, float] | None:
	"""La mémoire tampon du stream d'un feed, en secondes : ce qu'elle contient, sur sa durée
	(https://github.com/dascritch/machincast/issues/351) ; None sans elle."""
	level = track.buffer_level()
	if (parameters.buffer is None) or (level is None):
		return None
	return {"level": round(level.total_seconds(), 1), "target": round(parameters.buffer.total_seconds(), 1)}


def _without_progress(ongoing: object) -> object:
	if not isinstance(ongoing, dict):
		return ongoing
	without_progress = {}
	for key, value in ongoing.items():
		if key not in ("position", "progression", "buffer"):
			without_progress[key] = value
	return without_progress
