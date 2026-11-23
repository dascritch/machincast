"""L'agenda de l'intranet : une seule couche d'événements, ceux qui auront lieu
(https://github.com/dascritch/machincast/issues/599, ticket enfant de
https://github.com/dascritch/machincast/issues/596).

Des occurrences du calendrier (machincast.intranet.calendar.entries), l'agenda ne garde que ce qui passera à
l'antenne :

- une occurrence à l'horaire défini : ni un fil musical permanent, ni une occurrence sans fin, ni un secours ;
- seulement les moments où elle est à l'antenne : une émission qu'une spéciale remplace n'apparaît pas, et celle
  qu'une spéciale coupe apparaît avant et après elle, en deux morceaux ; une session sautée, ou un événement
  supprimé, n'apparaît pas ;
- seulement ce qui finit après maintenant : l'en cours, et l'à venir.

Les morceaux ne se chevauchent jamais : une seule couche. L'agenda est un élément réutilisable : items donne ses
morceaux, render son HTML (agenda.html.jinja, en grille horaire, machincast.intranet.hour_grid), que la page
/calendar inclut, et qu'un plugin peut reprendre à un autre usage, un export en PDF par exemple
(machincast.intranet.extensions.Tools.agenda).
"""

from datetime import date, datetime, timedelta
from typing import Any

from machincast.intranet import calendar, hour_grid, rendering
from machincast.intranet.queries import Connection


def items(found: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
	"""Les morceaux de l'agenda, une seule couche, dans l'ordre de leur début : chacun une occurrence du calendrier, à
	l'horaire défini, réduite à un moment où elle est à l'antenne, qui finit après now."""
	layer = []
	for entry in found:
		if (entry["defined"]) and (not entry["skipped"]) and (not entry["deleted"]):
			for piece in entry["on_air"]:
				if piece["end"] > now:
					layer.append(
						{**entry, "start": piece["start"], "end": piece["end"], "on_air": [piece], "covered": False}
					)
	layer.sort(key=lambda item: item["start"])
	return layer


def week(connection: Connection, first: date, now: datetime) -> list[dict[str, Any]]:
	"""Les morceaux de l'agenda de la semaine de first, tels qu'ils sont à now."""
	return items(calendar.entries(connection, first, first + timedelta(days=calendar.WEEK)), now)


def render(layer: list[dict[str, Any]], first: date, now: datetime) -> str:
	"""L'agenda de la semaine de first, en grille horaire (agenda.html.jinja)."""
	return rendering.render("agenda.html.jinja", grid=rendering.html(hour_grid.week(layer, first, now)))
