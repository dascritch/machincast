"""L'antenne en direct, pour l'API de l'intranet (https://github.com/dascritch/machincast/issues/540).

- Les sonores : celui en cours, et les 5 suivants, prochain compris, viennent de la socket d'état de Machin player
  (spec § 5.4), avec leur séquence, leur banque et leur événement, leur durée, et leur début et leur fin prévus ; les 5
  derniers diffusés, de l'airplay.
- Les événements : le précédent, celui en cours et le suivant, avec leurs heures de début et de fin, viennent de la
  grille (machincast.shared.grid.plan), sur la semaine d'avant et la semaine d'après ; un événement avancé ou terminé
  à la main, que seul Machin player connaît, ne l'est pas ici.

Le serveur intranet tourne sous le compte de MachinCast, qui lit la socket d'état du service de diffusion. Sans
Machin player, l'état est « stopped », sans sonore à venir.
"""

import json
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from machincast.intranet import queries
from machincast.intranet.queries import Connection
from machincast.shared.grid import Planned, plan, read_grid, wall_hour

FOLLOWING = 5
"""Sonores à venir, le prochain compris."""
HORIZON = timedelta(days=7)
"""Jusqu'où chercher, avant et après maintenant, l'événement précédent et le suivant."""
TIMEOUT = 1.0
"""Secondes pour lire le dernier état de Machin player."""
MAXIMUM_LINE = 1024 * 1024
STOPPED: dict[str, Any] = {"state": "stopped", "current": None, "next": None, "upcoming": []}


def read_state(path: Path, timeout: float = TIMEOUT) -> dict[str, Any]:
	"""Le dernier état que publie Machin player sur sa socket ; STOPPED sans lui."""
	received = b""
	try:
		with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
			client.settimeout(timeout)
			client.connect(str(path))
			while (b"\n" not in received) and (len(received) < MAXIMUM_LINE):
				chunk = client.recv(65536)
				if chunk == b"":
					break
				received += chunk
		state = json.loads(received.split(b"\n", 1)[0])
	except (OSError, ValueError):
		return dict(STOPPED)
	if not isinstance(state, dict):
		return dict(STOPPED)
	return state


def _segments(planned: list[Planned]) -> list[tuple[datetime, datetime, Planned]]:
	"""Chaque moment où une occurrence est à l'antenne, dans l'ordre."""
	found = []
	for one in planned:
		for begins, ends in one.plays:
			found.append((begins, ends, one))
	found.sort(key=lambda segment: segment[0])
	return found


def _event(segment: tuple[datetime, datetime, Planned] | None, now: datetime) -> dict[str, Any] | None:
	"""Un événement et ses heures ; None pour celle qui sort de la période cherchée : un fil musical à l'antenne
	depuis plus d'une semaine, ou qui le restera plus d'une semaine."""
	if segment is None:
		return None
	begins, ends, one = segment
	event = one.occurrence.event
	start: datetime | None = begins
	end: datetime | None = ends
	if begins <= now - HORIZON:
		start = None
	if ends >= now + HORIZON:
		end = None
	return {"id": event.id, "name": event.name, "priority": str(event.priority), "start": start, "end": end}


def events(connection: Connection, instant: datetime) -> dict[str, dict[str, Any] | None]:
	"""L'événement précédent, celui en cours et le suivant, d'après la grille, en heure murale du poste."""
	with connection.transaction():
		grid = read_grid(connection)
	now = wall_hour(instant)
	segments = _segments(plan(grid, now - HORIZON, now + HORIZON))
	current = None
	previous = None
	following = None
	for segment in segments:
		begins, ends, _one = segment
		if begins <= now < ends:
			current = segment
		if ends <= now:
			previous = segment
		if (begins > now) and (following is None):
			following = segment
	if (current is not None) and (previous is not None) and (previous[2] is current[2]):
		previous = None
	return {"previous": _event(previous, now), "current": _event(current, now), "next": _event(following, now)}


SOUND_FIELDS = (
	"sound_id",
	"type",
	"artist",
	"title",
	"location",
	"duration",
	"estimated_start",
	"start",
	"estimated_end",
	"event",
	"event_id",
	"event_start",
	"event_end",
	"sequence",
	"sequence_id",
	"bank",
	"bank_id",
)


def _sound(published: Any) -> dict[str, Any] | None:
	if not isinstance(published, dict):
		return None
	kept = {}
	for name in SOUND_FIELDS:
		if name in published:
			kept[name] = published[name]
	return kept


def live(connection: Connection, state_socket: Path, instant: datetime) -> dict[str, Any]:
	"""L'antenne : l'heure, l'état, le texte public, le sonore en cours et sa position, les 5 suivants, les 5
	derniers, et les événements précédent, en cours et suivant."""
	state = read_state(state_socket)
	current = state.get("current")
	current_sound = _sound(current)
	public_text = None
	if isinstance(current, dict):
		public_text = current.get("public_text")
		if current_sound is not None:
			current_sound["position"] = current.get("position")
	following = []
	if state.get("next") is not None:
		following.append(_sound(state.get("next")))
	upcoming = state.get("upcoming")
	if isinstance(upcoming, list):
		for planned in upcoming:
			following.append(_sound(planned))
	return {
		"time": instant,
		"state": state.get("state", "stopped"),
		"public_text": public_text,
		"current": current_sound,
		"next": following[:FOLLOWING],
		"previous": queries.previous_plays(connection),
		"events": events(connection, instant),
	}
