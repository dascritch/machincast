"""L'accueil de « Machin intranet », en direct (https://github.com/dascritch/machincast/issues/541).

Dans l'ordre : l'heure, le texte public en cours, l'événement en cours (début, fin, temps restant), l'événement
suivant (début, fin), le sonore en cours (durée, temps restant), le sonore suivant (durée, attente avant son début),
puis les derniers sonores diffusés. Le serveur écrit la page telle qu'est l'antenne à son chargement ; son script
(static/intranet.js) la relit sur /api/v1/live et tient les décomptes au centième de seconde.

Sans session, l'accueil mène à la mire ; une session à valider, à la page de validation.
"""

from datetime import datetime
from html import escape
from typing import Any

from machincast.i18n import _

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
	"""Une durée en secondes, au centième, à la française : « 12,50 s » ; EMPTY sans elle."""
	if (not isinstance(value, (int, float))) or (isinstance(value, bool)):
		return EMPTY
	return f"{max(0.0, float(value)):.2f}".replace(".", ",") + " s"


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


def _countdown(identifier: str, limit: Any, now: datetime) -> str:
	"""Un décompte, que le script tient à jour d'après data-limite."""
	value = ""
	found = _moment(limit)
	if found is not None:
		value = found.isoformat()
	return (
		f'<span id="{identifier}" class="decompte" data-limite="{escape(value)}">{escape(remaining(limit, now))}</span>'
	)


def _field(label: str, content: str) -> str:
	return f"<dt>{escape(label)}</dt><dd>{content}</dd>"


def _span(identifier: str, text: str) -> str:
	return f'<span id="{identifier}">{escape(text)}</span>'


def _section(identifier: str, title: str, fields: list[str]) -> str:
	return f'<section class="{identifier}">\n<h2>{escape(title)}</h2>\n<dl>{"".join(fields)}</dl>\n</section>'


def _airplay(plays: list[dict[str, Any]]) -> str:
	lines = []
	for play in plays:
		lines.append(f"<li>{escape(hour(play.get('start')))} {escape(name(play))}</li>")
	return f'<section class="airplay">\n<h2>{escape(_("Last sounds on air"))}</h2>\n<ol id="airplay">{"".join(lines)}</ol>\n</section>'


def body(direct: dict[str, Any], now: datetime) -> str:
	"""Les sections de l'accueil, dans l'ordre, telles qu'est l'antenne à now."""
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
	return "\n".join(
		(
			'<div id="direct">',
			f'<p class="heure">{_span("heure", hour(now, seconds=True))}</p>',
			f'<p class="texte-public">{_span("texte-public", (direct.get("public_text")) or (EMPTY))}</p>',
			_section(
				"evenement",
				_("Current event"),
				[
					_field(_("Name"), _span("evenement-nom", (current_event.get("name")) or (EMPTY))),
					_field(_("Start"), _span("evenement-debut", hour(current_event.get("start")))),
					_field(_("End"), _span("evenement-fin", hour(current_event.get("end")))),
					_field(_("Remaining"), _countdown("evenement-reste", current_event.get("end"), now)),
				],
			),
			_section(
				"suivant",
				_("Next event"),
				[
					_field(_("Name"), _span("suivant-nom", (next_event.get("name")) or (EMPTY))),
					_field(_("Start"), _span("suivant-debut", hour(next_event.get("start")))),
					_field(_("End"), _span("suivant-fin", hour(next_event.get("end")))),
				],
			),
			_section(
				"sonore",
				_("Current sound"),
				[
					_field(_("Sound"), _span("sonore-nom", name(current))),
					_field(_("Duration"), _span("sonore-duree", duration(current_fields.get("duration")))),
					_field(_("Remaining"), _countdown("sonore-reste", current_fields.get("estimated_end"), now)),
				],
			),
			_section(
				"prochain",
				_("Next sound"),
				[
					_field(_("Sound"), _span("prochain-nom", name(upcoming))),
					_field(_("Duration"), _span("prochain-duree", duration(upcoming_fields.get("duration")))),
					_field(_("Starts in"), _countdown("prochain-attente", upcoming_fields.get("estimated_start"), now)),
				],
			),
			_airplay((direct.get("previous")) or ([])),
			"</div>",
		)
	)
