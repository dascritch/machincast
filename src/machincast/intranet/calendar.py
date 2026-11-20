"""Le calendrier de l'intranet (https://github.com/dascritch/machincast/issues/542).

Les occurrences des événements d'une période, d'après la grille (machincast.shared.grid.plan), passées comme à
venir, même celles d'un événement supprimé d'avant sa suppression, et même celles qu'un événement de priorité plus
haute couvre (une émission sous un spécial) : `on_air` dit les moments où chacune serait à l'antenne, vide pour une
occurrence couverte entièrement (`covered`) ; une session sautée (`skipped`) ne joue rien.

En JSON, pour /api/v1/calendar, et en HTML hCalendar, pour la page /calendar comme pour
/api/v1/calendar?format=html : chaque occurrence est un `vevent` (`h-event`), son nom en `summary`, ses heures en
`dtstart` et `dtend`, sa priorité en `category`.

Les heures sont celles du poste, avec leur décalage horaire.
"""

from datetime import date, datetime, time, timedelta
from html import escape
from typing import Any
from urllib.parse import parse_qs

from machincast.i18n import _
from machincast.intranet.queries import Connection
from machincast.shared.grid import DAY_NAMES, Planned, Priority, plan, read_grid

ONE_DAY = timedelta(days=1)
WEEK = 7
MAXIMUM_DAYS = 62
"""Jours d'une période au plus, pour l'API."""
PRIORITIES = {
	Priority.BREAKING: _("breaking"),
	Priority.SPECIAL: _("special"),
	Priority.SHOW: _("show"),
	Priority.BACKGROUND_PROGRAMMING: _("background programming"),
	Priority.FALLBACK: _("fallback"),
}


def midnight(day: date) -> datetime:
	"""Minuit au début de day, à l'heure du poste."""
	return datetime.combine(day, time()).astimezone()


def monday(day: date) -> date:
	"""Le lundi de la semaine de day."""
	return day - timedelta(days=day.weekday())


def _date(given: dict[str, list[str]], name: str) -> date | None:
	values = given.get(name)
	if values is None:
		return None
	return date.fromisoformat(values[0])


def period(query: str, today: date) -> tuple[date, date] | None:
	"""Les jours [from, to[ de l'API, la semaine de today par défaut ; None si illisibles, à l'envers, ou plus
	longs que MAXIMUM_DAYS."""
	given = parse_qs(query)
	try:
		first = _date(given, "from")
		last = _date(given, "to")
	except ValueError:
		return None
	if first is None:
		first = monday(today)
	if last is None:
		last = first + timedelta(days=WEEK)
	if (last <= first) or ((last - first).days > MAXIMUM_DAYS):
		return None
	return first, last


def week(query: str, today: date) -> date:
	"""Le lundi de la semaine demandée à la page, ?week=<un jour de la semaine> ; celle de today sinon."""
	given = parse_qs(query)
	try:
		found = _date(given, "week")
	except ValueError:
		found = None
	if found is None:
		found = today
	return monday(found)


def entries(connection: Connection, first: date, last: date) -> list[dict[str, Any]]:
	"""Les occurrences qui touchent les jours [first, last[, dans l'ordre de leur début."""
	with connection.transaction():
		grid = read_grid(connection, deleted_list=True)
	found = []
	for planned in plan(grid, midnight(first), midnight(last)):
		found.append(_entry(planned))
	return found


def _entry(planned: Planned) -> dict[str, Any]:
	event = planned.occurrence.event
	on_air = []
	for begins, ends in planned.plays:
		on_air.append({"start": begins.astimezone(), "end": ends.astimezone()})
	return {
		"id": event.id,
		"name": event.name,
		"priority": str(event.priority),
		"start": planned.start.astimezone(),
		"end": planned.end.astimezone(),
		"on_air": on_air,
		"covered": (on_air == []) and (not planned.skipped),
		"skipped": planned.skipped,
		"deleted": event.deleted_at is not None,
	}


def _hour(moment: datetime) -> str:
	return f"{moment.hour:02d}:{moment.minute:02d}"


def _end_hour(start: datetime, end: datetime) -> str:
	"""La fin, « 24:00 » à minuit le jour d'après le début."""
	if (end.date() > start.date()) and (end.time() == time()):
		return "24:00"
	return _hour(end)


def _remark(entry: dict[str, Any]) -> str:
	remarks = []
	if entry["covered"]:
		remarks.append(_("covered"))
	if entry["skipped"]:
		remarks.append(_("skipped"))
	if entry["deleted"]:
		remarks.append(_("deleted"))
	if remarks == []:
		return ""
	return f' <span class="remarque">({escape(", ".join(remarks))})</span>'


def vevent(entry: dict[str, Any], start: datetime, end: datetime) -> str:
	"""Une occurrence en hCalendar, entre start et end."""
	classes = ["vevent", "h-event", entry["priority"]]
	if entry["covered"]:
		classes.append("couvert")
	if entry["skipped"]:
		classes.append("saute")
	label = PRIORITIES.get(Priority(entry["priority"]), entry["priority"])
	return (
		f'<li class="{" ".join(classes)}">'
		f'<time class="dtstart dt-start" datetime="{start.isoformat()}">{_hour(start)}</time>–'
		f'<time class="dtend dt-end" datetime="{end.isoformat()}">{_end_hour(start, end)}</time> '
		f'<span class="summary p-name">{escape(entry["name"])}</span> '
		f'<span class="category p-category">{escape(label)}</span>{_remark(entry)}</li>'
	)


def hcalendar(found: list[dict[str, Any]]) -> str:
	"""Les occurrences, en une liste hCalendar."""
	lines = []
	for entry in found:
		lines.append(vevent(entry, entry["start"], entry["end"]))
	return f'<ol class="vcalendar">\n{"\n".join(lines)}\n</ol>'


def _day_title(day: date) -> str:
	return f"{DAY_NAMES[day.weekday()]} {day.day:02d}/{day.month:02d}"


def weekly(found: list[dict[str, Any]], first: date) -> str:
	"""La semaine de first, jour par jour : chaque occurrence sous chacun des jours qu'elle touche, à ses heures
	de ce jour."""
	days = []
	for offset in range(WEEK):
		day = first + timedelta(days=offset)
		begins, ends = midnight(day), midnight(day + ONE_DAY)
		lines = []
		for entry in found:
			if (entry["start"] < ends) and (entry["end"] > begins):
				lines.append(vevent(entry, max(entry["start"], begins), min(entry["end"], ends)))
		days.append(
			f'<section class="jour" id="jour-{day.isoformat()}">\n<h2>{escape(_day_title(day))}</h2>\n'
			f'<ol class="vcalendar">\n{"\n".join(lines)}\n</ol>\n</section>'
		)
	return "\n".join(days)
