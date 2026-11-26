"""Les pages, les routes d'API et les fichiers statiques que les plugins ajoutent à Machin webserver
(https://github.com/dascritch/machincast/issues/588, ticket enfant de https://github.com/dascritch/machincast/issues/348).

Au démarrage, le serveur demande à chaque plugin chargé abonné au point POINT son Extension
(machincast.plugins.points) :

- ses pages, sous /plugins/<nom>/<chemin>, en GET, pour une session valide du rôle qu'elles demandent : leur corps
  HTML, dans le gabarit « Machin webserver », dont le bandeau gagne celles qui ont un libellé (navigation) ;
- ses routes d'API, sous /api/v1/plugins/<nom>/<chemin>, en GET ou en POST, en JSON, pour une session valide, en
  cookie ou en « Authorization: Bearer », du rôle qu'elles demandent ; un rôle insuffisant reçoit 403 ;
- ses fichiers statiques, sous /plugins/<nom>/static/<fichier>, ceux d'un seul répertoire, aux types de STATIC ;
- ses sections de l'accueil (HomeSection) : leur HTML, sous l'antenne en direct, pour une session du rôle qu'elles
  demandent, avec leurs feuilles de style et leurs scripts, sans page ni entrée au bandeau
  (https://github.com/dascritch/machincast/issues/512).

Pages et routes passent par la même application (machincast.webserver.app) : mêmes en-têtes de sécurité, même
politique de contenu, même refus d'un formulaire d'un autre site. Leurs fonctions reçoivent un Tools : la session, la
base au rôle machincast_webserver, l'état de l'antenne, et les demandes à Machin player, au nom du compte de la session
(machincast.webserver.live.ask, https://github.com/dascritch/machincast/issues/593).
"""

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
from typing import Any

from machincast.clock import SystemClock
from machincast.i18n import _
from machincast.webserver import agenda, live, openapi, rendering, template
from machincast.webserver.api import answer, error
from machincast.webserver.app import Request, Response, Route, redirect
from machincast.webserver.portal import Connect, Portal
from machincast.webserver.queries import Connection
from machincast.webserver.sessions import Session

log = logging.getLogger(__name__)

POINT = "intranet.extensions"
CONSULT = "consult"
ACTIONS = "actions"
ROLES = (CONSULT, ACTIONS)
"""Les rôles des comptes de l'intranet : « actions » peut tout ce que peut « consult »."""
PATH = re.compile(r"^(?:[a-z0-9_-]+(?:/[a-z0-9_-]+)*)?$")
"""Le chemin d'une page ou d'une route, sous le préfixe du plugin : vide pour sa page d'accueil."""
FILE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]*$")
STATIC = {
	".css": "text/css; charset=utf-8",
	".js": "text/javascript; charset=utf-8",
	".svg": "image/svg+xml",
	".png": "image/png",
	".woff2": "font/woff2",
	".json": "application/json",
}
"""Les fichiers statiques servis, par extension, et leur type."""


@dataclass
class Tools:
	"""Ce qu'une page ou une route d'un plugin reçoit du serveur."""

	session: Session
	connect: Connect
	state_socket: Path

	async def database[T](self, action: Callable[[Connection], T]) -> T:
		"""Une action sur la base, au rôle machincast_webserver, dans un fil à part."""

		def run() -> T:
			with self.connect() as connection:
				return action(connection)

		return await asyncio.to_thread(run)

	async def state(self) -> dict[str, Any]:
		"""Le dernier état publié par Machin player."""
		return await asyncio.to_thread(live.read_state, self.state_socket)

	async def agenda(self, first: date) -> list[dict[str, Any]]:
		"""L'agenda de la semaine de first, une seule couche d'événements à venir, à reprendre à un autre usage ;
		machincast.webserver.agenda.render l'écrit en grille horaire (https://github.com/dascritch/machincast/issues/599)."""
		now = SystemClock().now()
		return await self.database(lambda connection: agenda.week(connection, first, now))

	def render(self, template_: str, /, **context: Any) -> str:
		"""Un gabarit Jinja2, celui du plugin, dans son templates/, ou un de l'intranet
		(machincast.webserver.rendering, https://github.com/dascritch/machincast/issues/597)."""
		return rendering.render(template_, **context)

	async def ask(self, request: dict[str, Any]) -> live.Answer:
		"""Une demande à Machin player, au nom du compte de la session, et sa réponse."""
		return await asyncio.to_thread(live.ask, self.state_socket, request, self.session.user)


Render = Callable[[Tools, Request], Awaitable[str]]
Handle = Callable[[Tools, Request], Awaitable[tuple[int, Any]]]


@dataclass(frozen=True)
class Page:
	path: str
	title: str
	render: Render
	"""Le corps HTML de la page, sans le gabarit."""
	role: str = CONSULT
	navigation: str | None = None
	"""Son libellé dans le bandeau ; sans lui, elle n'y est pas."""
	assets: tuple[str, ...] = ()
	"""Ses feuilles de style (.css) et ses scripts (.js), parmi les fichiers statiques du plugin."""


@dataclass(frozen=True)
class Endpoint:
	method: str
	path: str
	handle: Handle
	"""Le statut et la valeur JSON de la réponse."""
	role: str = CONSULT
	summary: str = ""
	"""Son résumé, dans le schéma OpenAPI de l'API (https://github.com/dascritch/machincast/issues/602)."""


@dataclass(frozen=True)
class HomeSection:
	"""Une section qu'un plugin ajoute à l'accueil, sous l'antenne en direct."""

	render: Render
	"""Son HTML, une <section>, sans le gabarit."""
	role: str = CONSULT
	assets: tuple[str, ...] = ()
	"""Ses feuilles de style (.css) et ses scripts (.js), parmi les fichiers statiques du plugin."""


@dataclass(frozen=True)
class Extension:
	"""Ce qu'un plugin ajoute à l'intranet."""

	pages: tuple[Page, ...] = ()
	endpoints: tuple[Endpoint, ...] = ()
	static: Path | None = None
	home: tuple[HomeSection, ...] = ()


ROLE_NAMES = {CONSULT: _("consult"), "actions": _("API actions")}
"""Les rôles, comme les nomme l'onglet API de l'interface."""


def _operation(name: str, method: str, path: str, endpoint: Endpoint) -> dict[str, Any]:
	"""Une route d'un plugin, dans le schéma OpenAPI (https://github.com/dascritch/machincast/issues/602)."""
	responses: dict[str, Any] = {
		"200": {"description": _("The answer of the plugin."), "content": {"application/json": {"schema": {}}}},
		"401": openapi.error(_("No valid session.")),
	}
	if endpoint.role != CONSULT:
		responses["403"] = openapi.error(_("This account cannot act on the antenna."))
	return {
		"summary": (endpoint.summary) or (f"{method} {path}"),
		"description": _("Route of the plugin “{name}”, for the accounts “{role}”.").format(
			name=name, role=ROLE_NAMES.get(endpoint.role, endpoint.role)
		),
		"tags": [name],
		"x-machincast-role": endpoint.role,
		"responses": responses,
	}


def allowed(session: Session, role: str) -> bool:
	"""Le compte a le rôle demandé : « actions » peut aussi ce que peut « consult »."""
	return (role == CONSULT) or (session.role == role)


class Extensions:
	"""Les routes des plugins, et leurs entrées dans le bandeau."""

	def __init__(
		self,
		portal: Portal,
		connect: Connect,
		state_socket: Path,
		radio: str,
		found: list[tuple[str, object]],
	) -> None:
		self.portal = portal
		self.connect = connect
		self.state_socket = state_socket
		self.radio = radio
		self.extensions: list[tuple[str, Extension]] = []
		for name, value in found:
			if isinstance(value, Extension):
				self.extensions.append((name, value))
			else:
				log.error(_("plugin “{name}”: an intranet extension is expected").format(name=name))
		self.navigation: list[tuple[str, str]] = []
		for name, extension in self.extensions:
			for each in extension.pages:
				if (each.navigation is not None) and (PATH.match(each.path)):
					self.navigation.append((address(name, each.path), each.navigation))

	async def home(self, session: Session, request: Request) -> tuple[str, str]:
		"""Les sections des plugins sous l'accueil, que le rôle du compte permet, et leurs feuilles de style et
		scripts, pour l'en-tête de la page ; une section en échec est consignée, et laissée."""
		sections = []
		heads = []
		tools = Tools(session, self.connect, self.state_socket)
		for name, extension in self.extensions:
			for section in extension.home:
				rendered = None
				if allowed(session, section.role):
					rendered = await _section(name, section, tools, request)
				# Une section vide n'ajoute rien à l'accueil.
				if (rendered is not None) and (rendered.strip() != ""):
					sections.append(rendered)
					heads.append(_assets(name, section.assets))
		return "\n".join(sections), "".join(heads)

	def routes(self) -> dict[tuple[str, str], Route]:
		found: dict[tuple[str, str], Route] = {}
		for name, extension in self.extensions:
			for each in extension.pages:
				self._add(found, name, ("GET", f"/plugins/{name}/", each.path), self._page(name, each))
			for endpoint in extension.endpoints:
				method = endpoint.method.upper()
				if method in ("GET", "POST"):
					self._add(
						found, name, (method, f"/api/v1/plugins/{name}/", endpoint.path), self._endpoint(endpoint)
					)
			if extension.static is not None:
				found[("GET", f"/plugins/{name}/static/*")] = self._static(name, extension.static)
		return found

	def operations(self) -> dict[str, Any]:
		"""Les routes d'API des plugins, pour le schéma OpenAPI (https://github.com/dascritch/machincast/issues/602) :
		chacune avec son plugin en étiquette, et le rôle qu'elle demande ; une route au chemin invalide n'y est pas."""
		paths: dict[str, Any] = {}
		for name, extension in self.extensions:
			for endpoint in extension.endpoints:
				method = endpoint.method.upper()
				if (method in ("GET", "POST")) and (PATH.match(endpoint.path)):
					path = f"/api/v1/plugins/{name}/{endpoint.path}".rstrip("/")
					paths.setdefault(path, {})[method.lower()] = _operation(name, method, path, endpoint)
		return paths

	def _add(self, found: dict[tuple[str, str], Route], name: str, where: tuple[str, str, str], route: Route) -> None:
		"""Ajoute la route, à son chemin sous le préfixe du plugin, s'il est valide ; sinon, le consigne."""
		method, prefix, path = where
		if not PATH.match(path):
			log.error(
				_("plugin “{name}”: “{path}” is not a path of the intranet").format(name=name, path=prefix + path)
			)
			return
		found[(method, (prefix + path).rstrip("/"))] = route

	async def _session(self, request: Request) -> Session | None:
		return await self.portal.valid(request)

	def _page(self, name: str, page: Page) -> Route:
		async def route(request: Request) -> Response:
			found = await self.portal.session(request)
			if found is None:
				return redirect("/login")
			if found.state == "pending":
				return redirect("/validation")
			if found.state != "valid":
				return redirect("/login")
			tools = Tools(found, self.connect, self.state_socket)
			state = await tools.state()
			frame: dict[str, Any] = {
				"radio": self.radio,
				"state": str(state.get("state", "stopped")),
				"user": found.user,
				"current": request.path,
				"navigation": self.navigation,
				"head": _assets(name, page.assets),
			}
			if not allowed(found, page.role):
				return template.framed("forbidden.html.jinja", page.title, status=403, **frame)
			return template.layout(page.title, await page.render(tools, request), **frame)

		return route

	def _endpoint(self, endpoint: Endpoint) -> Route:
		async def route(request: Request) -> Response:
			found = await self._session(request)
			if found is None:
				return error(401, _("A valid session is required."))
			if not allowed(found, endpoint.role):
				return error(403, _("This account cannot act on the antenna."))
			status, value = await endpoint.handle(Tools(found, self.connect, self.state_socket), request)
			return answer(status, value)

		return route

	def _static(self, name: str, directory: Path) -> Route:
		async def route(request: Request) -> Response:
			file = request.path.removeprefix(f"/plugins/{name}/static/")
			kind = STATIC.get(Path(file).suffix.lower())
			path = directory / file
			if (not FILE.match(file)) or (kind is None) or (not path.is_file()):
				return Response(404, b"", "text/plain; charset=utf-8")
			return Response(200, await asyncio.to_thread(path.read_bytes), kind)

		return route


async def _section(name: str, section: HomeSection, tools: Tools, request: Request) -> str | None:
	"""Le HTML de la section ; None si elle échoue, consigné."""
	try:
		return await section.render(tools, request)
	except Exception as error:
		log.error(
			_("plugin “{name}”: its section of the home page failed: {error}").format(name=name, error=error),
			exc_info=error,
		)
		return None


def address(name: str, path: str) -> str:
	"""L'adresse d'une page d'un plugin."""
	if path == "":
		return f"/plugins/{name}"
	return f"/plugins/{name}/{path}"


def _assets(name: str, files: tuple[str, ...]) -> str:
	"""Les feuilles de style et les scripts d'une page d'un plugin, de ses fichiers statiques."""
	lines = []
	for file in files:
		source = escape(f"/plugins/{name}/static/{file}")
		if file.endswith(".css"):
			lines.append(f'<link rel="stylesheet" href="{source}">\n')
		if file.endswith(".js"):
			lines.append(f'<script src="{source}" defer></script>\n')
	return "".join(lines)
