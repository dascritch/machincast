"""Ce que la fiche d'une émission dit du créneau qu'elle partage (https://github.com/dascritch/machincast/issues/609) :
à la place de l'encadré de sa grille, dont les dates ne comptent plus, l'événement méta qui la fait jouer, son jour,
ses heures, et les autres émissions de son alternance.

« Cette émission partage le créneau « Mercredi soir », le mercredi de 20h à 21h, avec les émissions « Les ahuris » et
« Zôtre ». »
"""

from datetime import datetime

from machincast.i18n import short_date
from machincast.shared import grid
from machincast_alternation.texts import t


def hour(instant: datetime) -> str:
	"""« 20h », ou « 20h30 »."""
	wall = grid.wall_hour(instant)
	if wall.minute == 0:
		return f"{wall.hour}h"
	return f"{wall.hour}h{wall.minute:02d}"


def listed(parts: list[str]) -> str:
	"""« A », « A et B », « A, B et C »."""
	if len(parts) <= 1:
		return "".join(parts)
	return t("{first} and {last}").format(first=", ".join(parts[:-1]), last=parts[-1])


def when(event: grid.Event) -> str:
	"""« le mercredi de 20h à 21h », « le lundi et le mercredi de 20h à 21h », « le 02/12/2026 à partir de 20h »."""
	days = []
	for day in sorted(event.days):
		days.append(t("on {day}").format(day=grid.DAY_NAMES[day].lower()))
	if (not days) and (event.start is not None):
		days.append(t("on {day}").format(day=short_date(grid.wall_hour(event.start).date())))
	hours = ""
	if (event.start is not None) and (event.end is not None):
		hours = t("from {start} to {end}").format(start=hour(event.start), end=hour(event.end))
	if (event.start is not None) and (event.end is None):
		hours = t("from {start} on").format(start=hour(event.start))
	return " ".join([listed(days), hours]).strip()


def text(meta: str, event: grid.Event | None, others: list[str]) -> str:
	"""Le texte de l'encadré : le créneau de l'événement méta, et les autres émissions qui le partagent."""
	slot = t("“{name}”").format(name=meta)
	if event is not None:
		slot = t("“{name}”, {when}").format(name=meta, when=when(event))
	quoted = []
	for name in others:
		quoted.append(t("“{name}”").format(name=name))
	if len(quoted) == 0:
		return t("This show shares the slot {slot}.").format(slot=slot)
	if len(quoted) == 1:
		return t("This show shares the slot {slot}, with the show {others}.").format(slot=slot, others=quoted[0])
	return t("This show shares the slot {slot}, with the shows {others}.").format(slot=slot, others=listed(quoted))
