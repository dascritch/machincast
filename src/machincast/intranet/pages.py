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
from collections.abc import Callable
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any

from machincast import __version__
from machincast.clock import Clock, SystemClock
from machincast.i18n import _

# Sans Qt : machincast.interface.version ne lit que git, pour situer l'installation.
from machincast.interface import version
from machincast.intranet import calendar, home, hour_grid, live, template
from machincast.intranet.app import Request, Response, Route, redirect
from machincast.intranet.portal import Connect, Portal
from machincast.intranet.queries import Connection
from machincast.intranet.sessions import Session

SPECIFICATION = "doc/fr/spec.md#13-intranet-et-api"
"""L'intranet et son API, dans la spécification."""


def guide() -> str:
	"""Le guide de l'antenne de la version installée, sur GitHub."""
	return version.documentation()


def specification(address: str) -> str:
	"""La spécification de l'intranet et de son API, à la même version que le guide d'adresse donnée."""
	return address.replace(version.DOCUMENTATION, SPECIFICATION)


def documentation_body(address: str) -> str:
	"""La page de la documentation : le guide de l'antenne et la spécification de l'API, à la version installée."""
	return "\n".join(
		(
			f"<h1>{escape(_('Documentation'))}</h1>",
			f"<p>{escape(_('MachinCast version {version}.').format(version=__version__))}</p>",
			'<ul class="documentation">',
			f'<li><a id="guide" href="{escape(address)}">{escape(_("Broadcast guide"))}</a></li>',
			f'<li><a id="specification" href="{escape(specification(address))}">'
			f"{escape(_('Intranet and API specification'))}</a></li>",
			"</ul>",
		)
	)


def calendar_body(found: list[dict[str, Any]], first: date, now: datetime) -> str:
	"""La page du calendrier : la semaine de first en grille horaire, telle qu'elle est à now, et les liens vers la
	précédente, celle d'aujourd'hui et la suivante."""
	before = (first - timedelta(days=calendar.WEEK)).isoformat()
	after = (first + timedelta(days=calendar.WEEK)).isoformat()
	last = first + timedelta(days=calendar.WEEK - 1)
	title = _("Week from {first} to {last}").format(
		first=f"{first.day:02d}/{first.month:02d}", last=f"{last.day:02d}/{last.month:02d}/{last.year}"
	)
	return "\n".join(
		(
			f"<h1>{escape(title)}</h1>",
			'<nav class="semaines">',
			f'<a id="precedente" rel="prev" href="/calendar?week={before}">{escape(_("Previous week"))}</a>',
			f'<a id="aujourdhui" href="/calendar">{escape(_("This week"))}</a>',
			f'<a id="suivante" rel="next" href="/calendar?week={after}">{escape(_("Next week"))}</a>',
			"</nav>",
			hour_grid.week(found, first, now),
		)
	)


class Pages:
	"""Les pages de l'intranet, et ce qu'il leur faut : la base, la socket d'état de Machin player, le nom de la
	radio, l'horloge."""

	def __init__(
		self, portal: Portal, connect: Connect, state_socket: Path, radio: str, clock: Clock | None = None
	) -> None:
		self.portal = portal
		self.connect = connect
		self.state_socket = state_socket
		self.radio = radio
		self.clock = (clock) or (SystemClock())

	def routes(self) -> dict[tuple[str, str], Route]:
		return {
			("GET", "/"): self.home,
			("GET", "/calendar"): self.calendar,
			("GET", "/documentation"): self.documentation,
			("GET", "/static/*"): template.static,
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

	async def _framed(self, session: Session, title: str, body: str, current: str) -> Response:
		"""Une page dans le gabarit, l'état de la diffusion lu sur la socket de Machin player."""
		state = await asyncio.to_thread(live.read_state, self.state_socket)
		return template.layout(
			title,
			body,
			radio=self.radio,
			state=str(state.get("state", "stopped")),
			user=session.user,
			current=current,
		)

	async def home(self, request: Request) -> Response:
		"""L'accueil, en direct."""
		found = await self._session(request)
		if isinstance(found, Response):
			return found
		now = self.clock.now()
		direct = await self._database(lambda connection: live.live(connection, self.state_socket, now))
		return template.layout(
			_("Home"),
			home.body(direct, now),
			radio=self.radio,
			state=str(direct.get("state", "stopped")),
			user=found.user,
			current="/",
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
		return await self._framed(found, _("Calendar"), calendar_body(entries, first, now), "/calendar")

	async def documentation(self, request: Request) -> Response:
		"""Les liens vers la documentation de la version installée."""
		found = await self._session(request)
		if isinstance(found, Response):
			return found
		address = await asyncio.to_thread(guide)
		return await self._framed(found, _("Documentation"), documentation_body(address), "/documentation")
