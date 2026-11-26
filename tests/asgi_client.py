"""Un client ASGI minimal, pour les scénarios de l'intranet sans serveur ni TLS
(https://github.com/dascritch/machincast/issues/539) : la requête passe directement à l'application."""

import asyncio
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from machincast.webserver.app import Intranet


@dataclass
class Answer:
	status: int
	headers: list[tuple[str, str]] = field(default_factory=list)
	body: bytes = b""

	def header(self, name: str) -> str | None:
		for key, value in self.headers:
			if key == name:
				return value
		return None

	def text(self) -> str:
		return self.body.decode("utf-8")


def call(
	application: Intranet,
	method: str,
	path: str,
	*,
	form: dict[str, str] | None = None,
	headers: dict[str, str] | None = None,
	client: str = "10.0.0.31",
	repeated: list[tuple[str, str]] | None = None,
	body: bytes = b"",
) -> Answer:
	"""La réponse de l'application à une requête ; un formulaire part en application/x-www-form-urlencoded ; repeated,
	des en-têtes de plus, envoyés après les autres, même s'ils les répètent, comme HTTP/2 le permet ; body, un corps
	brut, pour une route d'API en JSON."""
	sent = {"host": "studio.radio.lan:8443", "user-agent": "Firefox/140 (scénario)"}
	if form is not None:
		body = urlencode(form).encode()
		sent["content-type"] = "application/x-www-form-urlencoded"
	sent.update((headers) or ({}))
	raw_headers = []
	for name, value in [*sent.items(), *((repeated) or ([]))]:
		raw_headers.append((name.encode("latin-1"), value.encode("latin-1")))
	scope: dict[str, Any] = {
		"type": "http",
		"method": method,
		"path": path.partition("?")[0],
		"query_string": path.partition("?")[2].encode("latin-1"),
		"headers": raw_headers,
		"client": (client, 51234),
	}
	answer = Answer(0)
	received = False

	async def receive() -> dict[str, Any]:
		nonlocal received
		if received:
			return {"type": "http.disconnect"}
		received = True
		return {"type": "http.request", "body": body, "more_body": False}

	async def send(message: dict[str, Any]) -> None:
		if message["type"] == "http.response.start":
			answer.status = message["status"]
			for name, value in message["headers"]:
				answer.headers.append((name.decode("latin-1"), value.decode("latin-1")))
		if message["type"] == "http.response.body":
			answer.body += message.get("body", b"")

	asyncio.run(application(scope, receive, send))
	return answer
