"""Les textes de la diffusion (https://github.com/dascritch/machincast/issues/440) : ce que l'airplay et le log disent de
ce qui est à l'antenne, et les lignes du rapport de crash de Machin player (crash_text)."""

import logging
from datetime import datetime, timedelta
from typing import Any

from machincast.i18n import N_, _
from machincast.player.broadcast_plan import _lender_id, _seconds
from machincast.player.broadcast_types import Parameters
from machincast.player.engine import (
	DeadAir,
)
from machincast.player.grid import Occurrence
from machincast.player.rundown import Choice, Cutoff
from machincast.player.state import instant as iso

log = logging.getLogger(__name__)


def _display(choice: Choice, parameters: Parameters) -> dict[str, Any]:
	kind = "file"
	if parameters.stream:
		kind = "stream"
	if choice.lender is None:
		event_name = None
	else:
		event_name = choice.lender.event.name
	return {
		"sound_id": choice.sound,
		"type": kind,
		"artist": parameters.artist,
		"title": parameters.title,
		"location": parameters.location,
		"event": choice.occurrence.event.name,
		# https://github.com/dascritch/machincast/issues/399, sans changer la version.
		"lender": event_name,
		"lender_id": _lender_id(choice),
	}


def _announces(
	choice: Choice,
	parameters: Parameters,
	*,
	healthy: bool | None,
	details: dict[str, Any],
	start: datetime | None,
	cutoff: Cutoff | None,
) -> dict[str, Any]:
	"""Ce que la socket d'état dit du prochain sonore, ou d'un sonore à venir."""
	duration = parameters.duration
	end = None
	if (start is not None) and (duration is not None):
		end = start + duration
	if cutoff is not None:
		end = cutoff.instant
	return {
		**_display(choice, parameters),
		**details,
		"estimated_start": iso(start),
		"duration": _seconds(duration),
		"estimated_end": iso(end),
		"healthy": healthy,
	}


def _dead_air_message(dead_air: DeadAir, parameters: Parameters) -> str:
	"""« <fichier> : blanc de 10 s à 1:23,4 du sonore, niveau moyen -95,2 dB » ; un stream compte depuis le début de
	sa lecture (https://github.com/dascritch/machincast/issues/122)."""
	level = N_("digital silence")
	if dead_air.level is not None:
		level = N_("average level {level:.1f} dB").format(level=dead_air.level)
	duration = f"{dead_air.duration.total_seconds():.1f}".removesuffix(".0")
	ou = N_("of the sound")
	if parameters.stream:
		ou = N_("of its playback")
	sound = (parameters.location) or (parameters.address)
	return N_("{sound}: dead air of {duration} s at {timecode} {ou}, {level}").format(
		sound=sound, duration=duration, timecode=_timecode(dead_air.position), ou=ou, level=level
	)


def _timecode(position: timedelta) -> str:
	"""« 1:23.4 », ou « 1:02:03.4 » au-delà d'une heure : minutes, secondes et dixièmes, pour le log, en anglais."""
	tenths = round(position.total_seconds() * 10)
	hours, rest = divmod(tenths, 36000)
	minutes, rest = divmod(rest, 600)
	seconds = f"{rest // 10:02d}.{rest % 10}"
	if hours > 0:
		return f"{hours}:{minutes:02d}:{seconds}"
	return f"{minutes}:{seconds}"


SOUNDS_ON_AIR = _("Sounds on air")
"""La rubrique des rapports de crash de Machin player (https://github.com/dascritch/machincast/issues/342)."""


CRASH_UPCOMING = 5


def _crash_line(label: str, sound: dict[str, Any] | None) -> str:
	"""« À l'antenne : Matinale / Séquence / Banque / Artiste – Titre / /srv/fichier.flac »."""
	if sound is None:
		return f"{label} : —"
	event = str((sound.get("event")) or ("—"))
	if sound.get("lender"):
		event = _("{event}, in the name of “{lender}”").format(event=event, lender=sound["lender"])
	part_list = []
	for part in (sound.get("artist"), sound.get("title")):
		if part:
			part_list.append(str(part))
	title = " – ".join(part_list)
	parts = [
		event,
		(sound.get("sequence")) or ("—"),
		(sound.get("bank")) or ("—"),
		(title) or ("—"),
		(sound.get("location")) or ("—"),
	]
	texts = []
	for part in parts:
		texts.append(str(part))
	return f"{label} : {' / '.join(texts)}"


def crash_text(previous: dict[str, Any] | None, message: dict[str, Any]) -> str:
	"""Les sonores précédent, en cours, et les CRASH_UPCOMING suivants annoncés, une ligne chacun : événement,
	séquence, banque, artiste et titre, fichier."""
	coming = [message.get("next"), *((message.get("upcoming")) or ([]))]
	sound_list = []
	for sound in coming:
		if sound is not None:
			sound_list.append(sound)
	coming = sound_list[:CRASH_UPCOMING]
	lines = [
		_("Event / sequence / bank / sound / file"),
		_crash_line(_("Previous"), previous),
		_crash_line(_("Playing now"), message.get("current")),
	]
	rank_list = []
	for rank, sound in enumerate(coming, 1):
		rank_list.append(_crash_line(_("Next {rank}").format(rank=rank), sound))
	lines += rank_list
	return "\n".join(lines)


def _event_announcement(occurrence: Occurrence | None) -> dict[str, Any] | None:
	"""L'événement suivant, tel que la socket d'état le publie (https://github.com/dascritch/machincast/issues/257)."""
	if occurrence is None:
		return None
	event = occurrence.event
	return {
		"id": event.id,
		"name": event.name,
		"priority": event.priority.value,
		"start": iso(occurrence.start),
		"end": iso(occurrence.end),
	}
