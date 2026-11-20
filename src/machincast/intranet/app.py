"""L'application web de l'intranet, en ASGI, servie par Hypercorn (https://github.com/dascritch/machincast/issues/538).

Sans framework : des routes par méthode et par chemin, des réponses entières, et les en-têtes de sécurité sur chacune.
Le serveur n'écoute qu'en HTTPS (machincast.intranet.__main__) : Strict-Transport-Security demande au navigateur de ne
jamais revenir en clair. Un formulaire envoyé d'une autre origine est refusé, comme un corps trop gros.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from html import escape
from http.cookies import CookieError, SimpleCookie
from typing import Any
from urllib.parse import parse_qs, urlsplit

from machincast.i18n import _

log = logging.getLogger(__name__)

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]

SECURITY_HEADERS = (
	("strict-transport-security", "max-age=31536000"),
	("x-content-type-options", "nosniff"),
	("x-frame-options", "DENY"),
	("referrer-policy", "no-referrer"),
	("content-security-policy", "default-src 'self'; frame-ancestors 'none'; form-action 'self'"),
	("cache-control", "no-store"),
)
"""Sur chaque réponse : HTTPS seulement, pas de cadre, rien en cache, aucune ressource d'ailleurs."""
HTML = "text/html; charset=utf-8"
TEXT = "text/plain; charset=utf-8"
JSON = "application/json"
TITLE = "Machin intranet"
MAXIMUM_BODY = 64 * 1024
"""Octets d'un corps de requête, au plus : un formulaire de connexion n'en demande pas tant."""


@dataclass
class Request:
	"""Une requête, réduite à ce que lisent les routes."""

	method: str
	path: str
	headers: dict[str, str] = field(default_factory=dict)
	query: str = ""
	client: str = ""
	body: bytes = b""
	too_large: bool = False

	def cookie(self, name: str) -> str | None:
		"""La valeur d'un cookie ; None sans lui, ou d'un en-tête illisible."""
		jar: SimpleCookie = SimpleCookie()
		try:
			jar.load(self.headers.get("cookie", ""))
		except CookieError:
			return None
		if name not in jar:
			return None
		return jar[name].value

	def form(self) -> dict[str, str]:
		"""Les champs d'un formulaire envoyé, chacun par sa première valeur."""
		fields = {}
		for name, values in parse_qs(self.body.decode("utf-8", "replace"), keep_blank_values=True).items():
			fields[name] = values[0]
		return fields

	def same_origin(self) -> bool:
		"""Sans en-tête Origin, ou d'une origine dont l'hôte est celui de la requête."""
		origin = self.headers.get("origin")
		if origin is None:
			return True
		return urlsplit(origin).netloc == self.headers.get("host", self.headers.get(":authority", ""))


@dataclass
class Response:
	status: int
	body: bytes = b""
	content_type: str = TEXT
	headers: list[tuple[str, str]] = field(default_factory=list)


Route = Callable[[Request], Awaitable[Response]]


def page(title: str, body: str, status: int = 200) -> Response:
	"""Une page HTML complète, en français, son titre échappé ; body est déjà du HTML."""
	text_ = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — {TITLE}</title>
</head>
<body>
{body}
</body>
</html>
"""
	return Response(status, text_.encode("utf-8"), HTML)


def text(status: int, message: str) -> Response:
	return Response(status, f"{message}\n".encode(), TEXT)


def redirect(location: str, headers: list[tuple[str, str]] | None = None) -> Response:
	"""303 : le navigateur va à location, par GET."""
	return Response(303, b"", TEXT, [("location", location), *((headers) or ([]))])


class Intranet:
	"""L'application ASGI : chaque route par sa méthode et son chemin ; HEAD comme GET ; 404 pour un autre chemin,
	405 pour une autre méthode."""

	def __init__(self, routes: dict[tuple[str, str], Route] | None = None) -> None:
		self.routes: dict[tuple[str, str], Route] = {}
		if routes is not None:
			self.routes.update(routes)

	async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
		if scope["type"] == "lifespan":
			await self._lifespan(receive, send)
			return
		if scope["type"] != "http":
			return
		request = await self._request(scope, receive)
		response = await self.respond(request)
		await self._send(send, response, head=request.method == "HEAD")

	def methods(self, path: str) -> list[str]:
		found = []
		for method, route_path in self.routes:
			if route_path == path:
				found.append(method)
		return found

	async def respond(self, request: Request) -> Response:
		"""La réponse à une requête ; une route qui plante donne 500, et le note."""
		method = request.method
		if method == "HEAD":
			method = "GET"
		allowed = self.methods(request.path)
		if allowed == []:
			return text(404, _("Not found."))
		if method not in allowed:
			response = text(405, _("Method not allowed."))
			response.headers.append(("allow", ", ".join(allowed)))
			return response
		if request.too_large:
			return text(413, _("Request too large."))
		if (method != "GET") and (not request.same_origin()):
			return text(403, _("Form sent from another site."))
		try:
			return await self.routes[(method, request.path)](request)
		except Exception:
			log.exception(_("intranet: request {path} failed").format(path=request.path))
			return text(500, _("Internal error."))

	async def _lifespan(self, receive: Receive, send: Send) -> None:
		while True:
			message = await receive()
			if message["type"] == "lifespan.startup":
				await send({"type": "lifespan.startup.complete"})
			if message["type"] == "lifespan.shutdown":
				await send({"type": "lifespan.shutdown.complete"})
				return

	async def _request(self, scope: Scope, receive: Receive) -> Request:
		headers = {}
		for name, value in scope.get("headers", []):
			headers[name.decode("latin-1").lower()] = value.decode("latin-1")
		body = b""
		too_large = False
		more = True
		while more:
			message = await receive()
			if not too_large:
				body += message.get("body", b"")
			if len(body) > MAXIMUM_BODY:
				too_large = True
				body = b""
			more = message.get("more_body", False)
		client = (scope.get("client")) or (("", 0))
		return Request(
			method=scope["method"],
			path=scope["path"],
			headers=headers,
			query=scope.get("query_string", b"").decode("latin-1"),
			client=str(client[0]),
			body=body,
			too_large=too_large,
		)

	async def _send(self, send: Send, response: Response, *, head: bool) -> None:
		headers = [
			(b"content-type", response.content_type.encode()),
			(b"content-length", str(len(response.body)).encode()),
		]
		for name, value in (*SECURITY_HEADERS, *response.headers):
			headers.append((name.encode("latin-1"), value.encode("latin-1")))
		await send({"type": "http.response.start", "status": response.status, "headers": headers})
		body = response.body
		if head:
			body = b""
		await send({"type": "http.response.body", "body": body})
