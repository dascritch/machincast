"""Le gabarit « Machin intranet » (https://github.com/dascritch/machincast/issues/541).

Minimaliste : en haut, le nom de la radio, l'état de la diffusion, les liens vers les pages de l'intranet et « Se
déconnecter » ; dessous, la page. Sa feuille de style et son script sont servis par l'intranet lui-même
(/static/), la Content-Security-Policy n'acceptant aucune ressource d'ailleurs, ni script dans la page.
"""

from html import escape
from importlib import resources

from machincast.i18n import _
from machincast.intranet.app import TITLE, Request, Response, page

STATES = {"playing": _("Broadcasting"), "dead_air": _("Dead air on air"), "stopped": _("Stopped")}
"""L'état de la diffusion, comme l'écrit l'onglet Antenne de l'interface."""
NAVIGATION: list[tuple[str, str]] = [("/", _("Home"))]
"""Les pages de l'intranet, dans l'ordre du bandeau ; chaque page s'y ajoute."""
STATIC = {"intranet.css": "text/css; charset=utf-8", "intranet.js": "text/javascript; charset=utf-8"}
"""Les seuls fichiers servis sous /static/, et leur type."""
HEAD = """<link rel="stylesheet" href="/static/intranet.css">
<script src="/static/intranet.js" defer></script>
"""


def banner(radio: str, state: str, user: str, current: str) -> str:
	"""Le bandeau : la radio, l'état de la diffusion, la navigation, la page en cours marquée, et la déconnexion."""
	links = []
	for address, label in NAVIGATION:
		marked = ""
		if address == current:
			marked = ' aria-current="page"'
		links.append(f'<a href="{address}"{marked}>{escape(label)}</a>')
	labels = []
	for key, label in STATES.items():
		labels.append(f'data-{key.replace("_", "-")}="{escape(label)}"')
	return f"""<header class="bandeau">
<span class="radio">{escape(radio)}</span>
<span class="machin">{TITLE}</span>
<span id="etat" class="etat {escape(state)}" {" ".join(labels)}>{escape(STATES.get(state, state))}</span>
<nav>{" ".join(links)}</nav>
<span class="discret">{escape(user)}</span>
<form method="post" action="/logout"><button type="submit">{escape(_("Disconnect"))}</button></form>
</header>"""


def layout(title: str, body: str, *, radio: str, state: str, user: str, current: str) -> Response:
	"""Une page de l'intranet, dans le gabarit."""
	return page(
		title,
		f"{banner(radio, state, user, current)}\n<main>\n{body}\n</main>",
		head=HEAD,
	)


async def static(request: Request) -> Response:
	"""Un fichier de /static/, parmi ceux de STATIC ; 404 sinon."""
	name = request.path.removeprefix("/static/")
	if name not in STATIC:
		return Response(404, b"", "text/plain; charset=utf-8")
	content = resources.files("machincast.intranet").joinpath("static", name).read_bytes()
	return Response(200, content, STATIC[name])
