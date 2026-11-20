"""L'API REST de l'intranet, version 1, en lecture seulement (https://github.com/dascritch/machincast/issues/540).

Sous /api/v1, en GET seulement, pour une session valide, quel que soit le rôle du compte : son jeton en cookie, ou en
« Authorization: Bearer » (machincast.intranet.portal). Sans session valide, 401 ; une autre méthode, 405 ; un
élément inconnu, 404. Les réponses sont en JSON, en UTF-8 : dates en ISO 8601, durées en secondes.

- /api/v1/live : l'antenne en direct (machincast.intranet.live) ;
- /api/v1/calendar : les occurrences des événements des jours [from, to[, ?from=<date>&to=<date>, la semaine en
  cours par défaut, en JSON, ou en HTML hCalendar avec ?format=html (machincast.intranet.calendar) ;
- /api/v1/incidents : les incidents seulement, les plus récents en tête ;
- /api/v1/events, /sequences, /banks, /sounds : une page de la liste, ?after=<id>&limit=<n> ; la réponse donne
  `next`, l'identifiant à passer en after pour la page suivante, ou null ;
- /api/v1/events/<id>, et de même pour les autres : la fiche d'un élément, ses éléments ou ses sonores compris.

Un nouveau chemin d'une version publiée garde les autres tels quels ; un changement de sens ou de forme ouvre
/api/v2.
"""

import asyncio
import json
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from machincast.clock import Clock, SystemClock
from machincast.i18n import _
from machincast.intranet import calendar, live, queries
from machincast.intranet.app import JSON, Request, Response, Route, page
from machincast.intranet.portal import Connect, Portal
from machincast.intranet.queries import Connection

PREFIX = "/api/v1/"
CARD = re.compile(r"(?P<kind>events|sequences|banks|sounds)(?:/(?P<identifier>\d{1,18}))?")


def _plain(value: Any) -> Any:
	"""Ce que JSON ne sait pas écrire : dates en ISO 8601, durées en secondes, adresses et chemins en texte."""
	if isinstance(value, (datetime, date)):
		return value.isoformat()
	if isinstance(value, timedelta):
		return value.total_seconds()
	if isinstance(value, Decimal):
		return float(value)
	if isinstance(value, (IPv4Address, IPv6Address, Path)):
		return str(value)
	raise TypeError(type(value).__name__)


def dumps(value: Any) -> bytes:
	return json.dumps(value, ensure_ascii=False, default=_plain, sort_keys=True).encode("utf-8")


def answer(status: int, value: Any, headers: list[tuple[str, str]] | None = None) -> Response:
	return Response(status, dumps(value), JSON, (headers) or ([]))


def error(status: int, message: str) -> Response:
	headers = []
	if status == 401:
		headers.append(("www-authenticate", 'Bearer realm="MachinCast"'))
	return answer(status, {"error": message}, headers)


def _number(given: dict[str, list[str]], name: str, default: int, maximum: int) -> int | None:
	"""Un paramètre entier, de 0 à maximum ; None, illisible."""
	values = given.get(name)
	if values is None:
		return default
	if not values[0].isdigit():
		return None
	number = int(values[0])
	if number > maximum:
		return None
	return number


class ApiV1:
	"""Les routes de /api/v1."""

	def __init__(self, portal: Portal, connect: Connect, state_socket: Path, clock: Clock | None = None) -> None:
		self.portal = portal
		self.connect = connect
		self.state_socket = state_socket
		self.clock = (clock) or (SystemClock())

	def routes(self) -> dict[tuple[str, str], Route]:
		return {("GET", f"{PREFIX}*"): self.respond}

	async def _database[T](self, action: Callable[[Connection], T]) -> T:
		def run() -> T:
			with self.connect() as connection:
				return action(connection)

		return await asyncio.to_thread(run)

	async def respond(self, request: Request) -> Response:
		"""Une session valide d'abord, puis le chemin demandé."""
		if await self.portal.valid(request) is None:
			return error(401, _("A valid session is required."))
		path = request.path[len(PREFIX) :].rstrip("/")
		if path == "live":
			instant = self.clock.now()
			return answer(
				200, await self._database(lambda connection: live.live(connection, self.state_socket, instant))
			)
		if path == "calendar":
			return await self._calendar(request)
		if path == "incidents":
			return answer(200, {"incidents": await self._database(queries.incidents)})
		matched = CARD.fullmatch(path)
		if matched is None:
			return error(404, _("Unknown path of the API."))
		kind = matched["kind"]
		if matched["identifier"] is not None:
			return await self._card(kind, int(matched["identifier"]))
		return await self._page(kind, request)

	async def _calendar(self, request: Request) -> Response:
		"""Le calendrier des jours [from, to[, en JSON, ou en HTML hCalendar avec ?format=html."""
		chosen = calendar.period(request.query, self.clock.now().astimezone().date())
		if chosen is None:
			return error(
				400,
				_("from and to are dates, from before to, at most {maximum} days apart.").format(
					maximum=calendar.MAXIMUM_DAYS
				),
			)
		first, last = chosen
		found = await self._database(lambda connection: calendar.entries(connection, first, last))
		if parse_qs(request.query).get("format") == ["html"]:
			return page(_("Calendar"), calendar.hcalendar(found))
		return answer(200, {"from": first, "to": last, "events": found})

	async def _card(self, kind: str, identifier: int) -> Response:
		found = await self._database(lambda connection: queries.card(connection, kind, identifier))
		if found is None:
			return error(404, _("No such element."))
		return answer(200, found)

	async def _page(self, kind: str, request: Request) -> Response:
		given = parse_qs(request.query)
		after = _number(given, "after", 0, 2**62)
		limit = _number(given, "limit", queries.DEFAULT_LIMIT, queries.MAXIMUM_LIMIT)
		if (after is None) or (limit is None) or (limit == 0):
			return error(
				400,
				_("after is an identifier, and limit a number from 1 to {maximum}.").format(
					maximum=queries.MAXIMUM_LIMIT
				),
			)
		# Une ligne de plus que demandé dit s'il y a une page suivante.
		rows = await self._database(lambda connection: queries.page(connection, kind, after, limit + 1))
		following = None
		if len(rows) > limit:
			rows = rows[:limit]
			following = rows[-1]["id"]
		return answer(200, {kind: rows, "next": following})
