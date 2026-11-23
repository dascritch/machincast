"""Les pages de « Machin intranet », dans son gabarit, pour une session valide.

- GET / : l'accueil en direct (machincast.intranet.home, https://github.com/dascritch/machincast/issues/541) ;
- GET /calendar : le calendrier de la semaine, ?week=<un jour de la semaine>, avec la semaine précédente et la
  suivante, en grille horaire (machincast.intranet.calendar, https://github.com/dascritch/machincast/issues/542,
  machincast.intranet.hour_grid, https://github.com/dascritch/machincast/issues/580) ;
- GET /documentation : les liens vers la documentation de la version installée
  (https://github.com/dascritch/machincast/issues/542) ;
- GET /static/* : la feuille de style et le script du gabarit, sans session.

Sans session, une page mène à la mire ; une session à valider, à la page de validation.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from machincast import __version__
from machincast.clock import Clock, SystemClock
from machincast.i18n import _

# Sans Qt : machincast.interface.version ne lit que git, pour situer l'installation.
from machincast.interface import version
from machincast.intranet import calendar, home, hour_grid, live, rendering, template
from machincast.intranet.app import Request, Response, Route, redirect
from machincast.intranet.portal import Connect, Portal
from machincast.intranet.queries import Connection
from machincast.intranet.sessions import Session
from machincast.shortcut import ICON

log = logging.getLogger(__name__)

SPECIFICATION = "doc/fr/spec.md#13-intranet-et-api"
"""L'intranet et son API, dans la spécification."""


def guide() -> str:
	"""Le guide de l'antenne de la version installée, sur GitHub."""
	return version.documentation()


def specification(address: str) -> str:
	"""La spécification de l'intranet et de son API, à la même version que le guide d'adresse donnée."""
	return address.replace(version.DOCUMENTATION, SPECIFICATION)


def week_context(found: list[dict[str, Any]], first: date, now: datetime) -> dict[str, Any]:
	"""Ce que calendar.html.jinja montre : la semaine de first en grille horaire, telle qu'elle est à now, et les liens
	vers la précédente, celle d'aujourd'hui et la suivante."""
	last = first + timedelta(days=calendar.WEEK - 1)
	return {
		"week_title": _("Week from {first} to {last}").format(
			first=f"{first.day:02d}/{first.month:02d}", last=f"{last.day:02d}/{last.month:02d}/{last.year}"
		),
		"before": (first - timedelta(days=calendar.WEEK)).isoformat(),
		"after": (first + timedelta(days=calendar.WEEK)).isoformat(),
		"grid": rendering.html(hour_grid.week(found, first, now)),
	}


ICONS = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
"""Les images d'interface.icon, et leur type."""


def icon_response(icon: Path | None) -> Response:
	"""L'icône choisie, si elle se lit, ou celle de MachinCast."""
	for path in (icon, ICON):
		if (path is not None) and (path.suffix.lower() in ICONS):
			try:
				return Response(200, path.read_bytes(), ICONS[path.suffix.lower()])
			except OSError:
				log.info(_("icon {path} unreadable: the one of MachinCast instead").format(path=path))
	return Response(404, b"", "text/plain; charset=utf-8")


HomeSections = Callable[[Session, Request], Awaitable[tuple[str, str]]]
"""Les sections des plugins sous l'accueil : leur HTML, et leur en-tête."""


class Pages:
	"""Les pages de l'intranet, et ce qu'il leur faut : la base, la socket d'état de Machin player, le nom de la
	radio, l'horloge."""

	def __init__(
		self,
		portal: Portal,
		connect: Connect,
		state_socket: Path,
		radio: str,
		clock: Clock | None = None,
		icon: Path | None = None,
	) -> None:
		self.portal = portal
		self.icon = icon
		"""interface.icon, l'icône de l'application choisie dans l'interface : celle de l'intranet
		(https://github.com/dascritch/machincast/issues/598)."""
		self.connect = connect
		self.state_socket = state_socket
		self.radio = radio
		self.clock = (clock) or (SystemClock())
		self.navigation: list[tuple[str, str]] = []
		"""Les pages des plugins dans le bandeau (https://github.com/dascritch/machincast/issues/588)."""
		self.home_sections: HomeSections | None = None
		"""Les sections des plugins sous l'accueil, et leur en-tête
		(machincast.intranet.extensions.Extensions.home, https://github.com/dascritch/machincast/issues/512)."""

	def routes(self) -> dict[tuple[str, str], Route]:
		return {
			("GET", "/"): self.home,
			("GET", "/calendar"): self.calendar,
			("GET", "/documentation"): self.documentation,
			("GET", "/static/*"): template.static,
			("GET", "/favicon"): self.favicon,
		}

	async def _database[T](self, action: Callable[[Connection], T]) -> T:
		def run() -> T:
			with self.connect() as connection:
				return action(connection)

		return await asyncio.to_thread(run)

	async def _session(self, request: Request) -> Session | Response:
		"""La session valide de la requête ; sinon, où aller."""
		found = await self.portal.session(request)
		if found is None:
			return redirect("/login")
		if found.state == "pending":
			return redirect("/validation")
		if found.state != "valid":
			return redirect("/login")
		return found

	async def _framed(self, session: Session, name: str, title: str, current: str, **context: Any) -> Response:
		"""Le gabarit name, une page dans le gabarit, l'état de la diffusion lu sur la socket de Machin player."""
		state = await asyncio.to_thread(live.read_state, self.state_socket)
		return template.framed(
			name,
			title,
			radio=self.radio,
			state=str(state.get("state", "stopped")),
			user=session.user,
			current=current,
			navigation=self.navigation,
			**context,
		)

	async def favicon(self, request: Request) -> Response:
		"""L'icône de l'intranet, sans session : celle de l'application choisie dans l'interface, ou celle de
		MachinCast si aucune ne l'est, ou si elle ne se lit pas (https://github.com/dascritch/machincast/issues/598)."""
		return await asyncio.to_thread(icon_response, self.icon)

	async def home(self, request: Request) -> Response:
		"""L'accueil, en direct."""
		found = await self._session(request)
		if isinstance(found, Response):
			return found
		now = self.clock.now()
		direct = await self._database(lambda connection: live.live(connection, self.state_socket, now))
		sections, head = "", ""
		if self.home_sections is not None:
			sections, head = await self.home_sections(found, request)
		return template.framed(
			"home.html.jinja",
			_("Home"),
			head=head,
			live=home.live_context(direct, now),
			sections=rendering.html(sections),
			radio=self.radio,
			state=str(direct.get("state", "stopped")),
			user=found.user,
			current="/",
			navigation=self.navigation,
		)

	async def calendar(self, request: Request) -> Response:
		"""Le calendrier de la semaine demandée."""
		found = await self._session(request)
		if isinstance(found, Response):
			return found
		now = self.clock.now().astimezone()
		first = calendar.week(request.query, now.date())
		last = first + timedelta(days=calendar.WEEK)
		entries = await self._database(lambda connection: calendar.entries(connection, first, last))
		return await self._framed(
			found, "calendar.html.jinja", _("Calendar"), "/calendar", **week_context(entries, first, now)
		)

	async def documentation(self, request: Request) -> Response:
		"""Les liens vers la documentation de la version installée."""
		found = await self._session(request)
		if isinstance(found, Response):
			return found
		address = await asyncio.to_thread(guide)
		return await self._framed(
			found,
			"documentation.html.jinja",
			_("Documentation"),
			"/documentation",
			version_text=_("MachinCast version {version}.").format(version=__version__),
			guide=address,
			specification=specification(address),
		)
