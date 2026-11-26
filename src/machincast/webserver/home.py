"""L'accueil de « Machin webserver », en direct (https://github.com/dascritch/machincast/issues/541).

Dans l'ordre : l'heure, le texte public en cours, l'événement en cours (début, fin, temps restant), l'événement
suivant (début, fin), le sonore en cours (durée, temps restant), le sonore suivant (durée, attente avant son début),
puis les derniers sonores diffusés, écrits par live.html.jinja (https://github.com/dascritch/machincast/issues/597) ; l'événement en cours et le suivant côte à côte, le sonore en cours et le suivant
aussi (https://github.com/dascritch/machincast/issues/579). Le serveur écrit la page telle qu'est l'antenne à son
chargement ; son script (static/intranet.js) la relit sur /api/v1/live et tient les décomptes, à la seconde. Durées et
décomptes s'écrivent HH:MM:SS.

Sans session, l'accueil mène à la mire ; une session à valider, à la page de validation.
"""

from datetime import datetime
from typing import Any

from machincast.webserver import rendering

EMPTY = "—"


def _moment(value: Any) -> datetime | None:
	"""Une date de la grille ou de la socket d'état, en datetime avec son décalage, l'heure du poste sans lui ; None
	sans elle."""
	found = None
	if isinstance(value, datetime):
		found = value
	if isinstance(value, str):
		try:
			found = datetime.fromisoformat(value)
		except ValueError:
			return None
	if found is None:
		return None
	return found.astimezone()


def hour(value: Any, *, seconds: bool = False) -> str:
	"""Une heure, à la minute, ou à la seconde ; EMPTY sans elle."""
	found = _moment(value)
	if found is None:
		return EMPTY
	if seconds:
		return f"{found.hour:02d}:{found.minute:02d}:{found.second:02d}"
	return f"{found.hour:02d}:{found.minute:02d}"


def duration(value: Any) -> str:
	"""Une durée en secondes, en HH:MM:SS, sans les fractions de seconde, les heures au-delà de 24 comprises : « 26:03:04 » ;
	« 00:00:00 » pour une durée écoulée ; EMPTY sans elle (https://github.com/dascritch/machincast/issues/579)."""
	if (not isinstance(value, (int, float))) or (isinstance(value, bool)):
		return EMPTY
	hours, rest = divmod(int(max(0.0, float(value))), 3600)
	minutes, seconds = divmod(rest, 60)
	return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def remaining(limit: Any, now: datetime) -> str:
	"""Le temps jusqu'à limit."""
	found = _moment(limit)
	if found is None:
		return EMPTY
	return duration((found - now).total_seconds())


def name(sound: dict[str, Any] | None) -> str:
	"""Un sonore : « artiste – titre », ou son emplacement."""
	if sound is None:
		return EMPTY
	parts = []
	for part in (sound.get("artist"), sound.get("title")):
		if part:
			parts.append(str(part))
	if parts != []:
		return " – ".join(parts)
	return str((sound.get("location")) or (EMPTY))


def _countdown(limit: Any, now: datetime) -> dict[str, str]:
	"""Un décompte : sa limite, que le script tient à jour d'après data-limite, et son texte."""
	value = ""
	found = _moment(limit)
	if found is not None:
		value = found.isoformat()
	return {"limit": value, "text": remaining(limit, now)}


def _airplay(plays: list[dict[str, Any]]) -> list[dict[str, str]]:
	lines = []
	for play in plays:
		lines.append({"hour": hour(play.get("start")), "name": name(play)})
	return lines


def live_context(direct: dict[str, Any], now: datetime) -> dict[str, Any]:
	"""Ce que live.html.jinja montre de l'antenne à now : chaque valeur déjà écrite, heure, durée ou décompte."""
	events = (direct.get("events")) or ({})
	current_event = (events.get("current")) or ({})
	next_event = (events.get("next")) or ({})
	current = direct.get("current")
	following = (direct.get("next")) or ([])
	upcoming = None
	if following != []:
		upcoming = following[0]
	upcoming_fields = (upcoming) or ({})
	current_fields = (current) or ({})
	return {
		"hour": hour(now, seconds=True),
		"public_text": (direct.get("public_text")) or (EMPTY),
		"event": {
			"name": (current_event.get("name")) or (EMPTY),
			"start": hour(current_event.get("start")),
			"end": hour(current_event.get("end")),
			"remaining": _countdown(current_event.get("end"), now),
		},
		"next_event": {
			"name": (next_event.get("name")) or (EMPTY),
			"start": hour(next_event.get("start")),
			"end": hour(next_event.get("end")),
		},
		"sound": {
			"name": name(current),
			"duration": duration(current_fields.get("duration")),
			"remaining": _countdown(current_fields.get("estimated_end"), now),
		},
		"next_sound": {
			"name": name(upcoming),
			"duration": duration(upcoming_fields.get("duration")),
			"starts_in": _countdown(upcoming_fields.get("estimated_start"), now),
		},
		"airplay": _airplay((direct.get("previous")) or ([])),
	}


def body(direct: dict[str, Any], now: datetime) -> str:
	"""L'antenne en direct, telle qu'elle est à now (live.html.jinja)."""
	return rendering.render("live.html.jinja", live=live_context(direct, now))
