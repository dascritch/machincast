"""Le cartouchier dans Machin intranet (https://github.com/dascritch/machincast/issues/512), par le point
« intranet.extensions » (https://github.com/dascritch/machincast/issues/588).

- Les boutons du compte, sous l'antenne en direct de l'accueil, sans page à part ni entrée au bandeau
  (HomeSection) ; pour un compte « consulter », grisés, et la section le dit ; sans bouton, rien.
- GET /api/v1/plugins/cartwall/buttons : les boutons du compte, et pourquoi chacun ne peut pas servir maintenant, une
  banque « ne pas répéter » qui a donné le sonore à l'antenne, une cible supprimée ; le script de la page les relit pour
  les griser.
- POST /api/v1/plugins/cartwall/press, {"button": <identifiant>}, pour un compte « actions API » : la demande du bouton
  à Machin player, au nom du compte, qui la consigne avec lui ; la réponse dit si elle est faite, ou pourquoi elle est
  refusée. Un compte n'appuie que sur ses propres boutons.
"""

import json
from html import escape
from pathlib import Path
from typing import Any

from machincast.intranet.app import Request
from machincast.intranet.extensions import ACTIONS, Endpoint, Extension, HomeSection, Tools
from machincast_cartwall import queries
from machincast_cartwall.buttons import Button, as_json, request
from machincast_cartwall.texts import t

STATIC = Path(__file__).resolve().parents[2] / "static"


def _button(button: Button, *, active: bool) -> str:
	"""Un bouton : sa couleur, que le script pose (la politique de contenu refuse un style dans la page), et, s'il ne
	peut pas servir, grisé, avec sa raison en infobulle."""
	disabled = ""
	title = ""
	if (button.unusable is not None) or (not active):
		disabled = " disabled"
	if button.unusable is not None:
		title = f' title="{escape(button.unusable)}"'
	return (
		f'<button type="button" class="carte" data-bouton="{button.id}" data-couleur="{escape(button.colour)}"'
		f"{title}{disabled}>{escape(button.label)}</button>"
	)


def _buttons(buttons: list[Button], *, active: bool) -> str:
	lines = []
	for button in buttons:
		lines.append(_button(button, active=active))
	notice = ""
	if not active:
		notice = t("This account only consults: its buttons are for the accounts that can act on the antenna.")
	paragraph = ""
	if notice != "":
		paragraph = f'<p class="discret">{escape(notice)}</p>\n'
	return (
		f'<section id="cartouchier" data-actif="{int(active)}">\n<h2>{escape(t("Cartwall"))}</h2>\n{paragraph}'
		f'<div class="cartes">{"".join(lines)}</div>\n<p id="cartouchier-etat" role="status"></p>\n</section>'
	)


async def section(tools: Tools, request_: Request) -> str:
	"""Les boutons du compte, sous l'accueil."""
	buttons = await tools.database(lambda connection: queries.buttons_of(connection, tools.session.user))
	if buttons == []:
		# Un compte sans bouton garde l'accueil tel quel.
		return ""
	return _buttons(buttons, active=tools.session.role == ACTIONS)


async def listed(tools: Tools, request_: Request) -> tuple[int, Any]:
	buttons = await tools.database(lambda connection: queries.buttons_of(connection, tools.session.user))
	found = []
	for button in buttons:
		found.append(as_json(button))
	return 200, {"buttons": found}


def _asked(body: bytes) -> int | None:
	"""L'identifiant du bouton demandé ; None si le corps ne le donne pas."""
	try:
		value = json.loads(body.decode())
	except (UnicodeDecodeError, json.JSONDecodeError):
		return None
	if not isinstance(value, dict):
		return None
	button = value.get("button")
	if (not isinstance(button, int)) or (isinstance(button, bool)):
		return None
	return button


async def press(tools: Tools, request_: Request) -> tuple[int, Any]:
	"""Appuie sur un bouton du compte : 200 si Machin player l'a fait, 409 s'il l'a refusé, avec sa raison."""
	asked = _asked(request_.body)
	if asked is None:
		return 400, {"error": t('A button is asked: {"button": <identifier>}.')}
	button = await tools.database(lambda connection: queries.button_of(connection, tools.session.user, asked))
	if button is None:
		return 404, {"error": t("Unknown button.")}
	if button.unusable is not None:
		return 409, {"done": False, "reason": button.unusable}
	sent = request(button, await tools.state())
	if sent is None:
		return 409, {"done": False, "reason": t("no next event")}
	answer = await tools.ask(sent)
	if not answer.done:
		return 409, {"done": False, "reason": answer.reason}
	return 200, {"done": True}


def extension() -> Extension:
	"""Ce que le cartouchier ajoute à l'intranet."""
	return Extension(
		home=(HomeSection(section, assets=("cartwall.css", "cartwall.js")),),
		endpoints=(Endpoint("GET", "buttons", listed), Endpoint("POST", "press", press, role=ACTIONS)),
		static=STATIC,
	)
