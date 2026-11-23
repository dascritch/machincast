"""Le gabarit « Machin intranet » (https://github.com/dascritch/machincast/issues/541).

Minimaliste : en haut, le nom de la radio, l'état de la diffusion, les liens vers les pages de l'intranet et « Se
déconnecter » ; dessous, la page. Sa feuille de style et son script sont servis par l'intranet lui-même
(/static/), la Content-Security-Policy n'acceptant aucune ressource d'ailleurs, ni script dans la page.

Le gabarit et les pages sont des fichiers Jinja2, surchargeables par un plugin (machincast.intranet.rendering,
https://github.com/dascritch/machincast/issues/597) : layout.html.jinja, le bandeau dans banner.html.jinja.
"""

from collections.abc import Sequence
from importlib import resources
from typing import Any

from machincast.i18n import _
from machincast.intranet import rendering
from machincast.intranet.app import HTML, TITLE, Request, Response

STATES = {"playing": _("Broadcasting"), "dead_air": _("Dead air on air"), "stopped": _("Stopped")}
"""L'état de la diffusion, comme l'écrit l'onglet Antenne de l'interface."""
NAVIGATION = (("/", _("Home")), ("/calendar", _("Calendar")), ("/documentation", _("Documentation")))
"""Les pages de l'intranet, dans l'ordre du bandeau."""
STATIC = {"intranet.css": "text/css; charset=utf-8", "intranet.js": "text/javascript; charset=utf-8"}
"""Les seuls fichiers servis sous /static/, et leur type."""


def framed(
	name: str,
	title: str,
	*,
	radio: str,
	state: str,
	user: str,
	current: str,
	navigation: Sequence[tuple[str, str]] = (),
	status: int = 200,
	head: str = "",
	**context: Any,
) -> Response:
	"""Le gabarit name, une page qui étend layout.html.jinja : le bandeau, la radio, l'état de la diffusion, la
	navigation, celle des plugins après celle de l'intranet (https://github.com/dascritch/machincast/issues/588), la page
	en cours marquée ; head ajoute ses feuilles de style et ses scripts, ceux d'un plugin."""
	links = [*NAVIGATION, *navigation]
	text = rendering.render(
		name,
		title=title,
		machin=TITLE,
		radio=radio,
		state=state,
		states=STATES,
		user=user,
		current=current,
		navigation=links,
		head=rendering.html(head),
		**context,
	)
	return Response(status, text.encode("utf-8"), HTML)


def layout(
	title: str,
	body: str,
	*,
	radio: str,
	state: str,
	user: str,
	current: str,
	navigation: Sequence[tuple[str, str]] = (),
	status: int = 200,
	head: str = "",
) -> Response:
	"""Une page de l'intranet, son corps déjà écrit en HTML, dans le gabarit."""
	return framed(
		"layout.html.jinja",
		title,
		radio=radio,
		state=state,
		user=user,
		current=current,
		navigation=navigation,
		status=status,
		head=head,
		body=rendering.html(body),
	)


async def static(request: Request) -> Response:
	"""Un fichier de /static/, parmi ceux de STATIC ; 404 sinon."""
	name = request.path.removeprefix("/static/")
	if name not in STATIC:
		return Response(404, b"", "text/plain; charset=utf-8")
	content = resources.files("machincast.intranet").joinpath("static", name).read_bytes()
	return Response(200, content, STATIC[name])
