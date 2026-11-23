"""Le schéma OpenAPI 3.1 de l'API de l'intranet (https://github.com/dascritch/machincast/issues/602).

/api/v1/openapi.json le donne à une session valide, comme le reste de l'API : chaque chemin de /api/v1, ses paramètres
et ses réponses, puis les routes des plugins activés (machincast.intranet.extensions), chacune avec son plugin, en
étiquette, et le rôle qu'elle demande. Le jeton se donne en « Authorization: Bearer », ou dans le cookie de la session.
"""

from typing import Any

from machincast import __version__
from machincast.i18n import _
from machincast.intranet.sessions import COOKIE

VERSION = "3.1.0"
TITLE = "MachinCast API"
JSON_CONTENT = "application/json"
KINDS = ("events", "sequences", "banks", "sounds")
"""Les éléments que l'API liste par pages, et dont elle donne la fiche."""


def _object(description: str) -> dict[str, Any]:
	"""Une réponse JSON, un objet."""
	return {"description": description, "content": {JSON_CONTENT: {"schema": {"type": "object"}}}}


def error(description: str) -> dict[str, Any]:
	"""Une réponse d'erreur : {"error": message}."""
	schema = {
		"type": "object",
		"properties": {"error": {"type": "string"}},
		"required": ["error"],
	}
	return {"description": description, "content": {JSON_CONTENT: {"schema": schema}}}


def _query(name: str, description: str, kind: str) -> dict[str, Any]:
	return {"name": name, "in": "query", "required": False, "description": description, "schema": {"type": kind}}


def _operation(summary: str, ok: str, parameters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
	"""Une opération en GET : son résumé, ses paramètres, sa réponse, et les erreurs de toute l'API."""
	found: dict[str, Any] = {
		"summary": summary,
		"responses": {
			"200": _object(ok),
			"401": error(_("No valid session.")),
		},
	}
	if parameters is not None:
		found["parameters"] = parameters
	return found


def _cards(paths: dict[str, Any]) -> None:
	"""Chaque liste par pages, et la fiche de chacun de ses éléments."""
	for kind in KINDS:
		paths[f"/api/v1/{kind}"] = {
			"get": _operation(
				_("A page of the list of {kind}").format(kind=kind),
				_("The page, and next, the identifier to give as after for the next page, or null."),
				[
					_query("after", _("The identifier after which the page starts."), "integer"),
					_query("limit", _("The number of elements of the page."), "integer"),
				],
			)
		}
		card = _operation(_("The card of one of the {kind}").format(kind=kind), _("The card."))
		card["parameters"] = [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}]
		card["responses"]["404"] = error(_("No such element."))
		paths[f"/api/v1/{kind}/{{id}}"] = {"get": card}


def core_paths() -> dict[str, Any]:
	"""Les chemins de /api/v1."""
	paths: dict[str, Any] = {
		"/api/v1/live": {"get": _operation(_("The live broadcast"), _("The broadcast, now."))},
		"/api/v1/calendar": {
			"get": _operation(
				_("The occurrences of the events of the days [from, to["),
				_("The occurrences, in JSON, or in HTML hCalendar with format=html."),
				[
					_query("from", _("The first day, by default the start of the current week."), "string"),
					_query("to", _("The day after the last one."), "string"),
					_query("format", _("html, for HTML hCalendar."), "string"),
				],
			)
		},
		"/api/v1/incidents": {"get": _operation(_("The incidents, the most recent first"), _("The incidents."))},
		"/api/v1/openapi.json": {"get": _operation(_("This OpenAPI schema"), _("The schema."))},
	}
	paths["/api/v1/calendar"]["get"]["responses"]["400"] = error(_("Unreadable period."))
	_cards(paths)
	return paths


def document(plugin_paths: dict[str, Any]) -> dict[str, Any]:
	"""Le schéma, les routes des plugins après celles de /api/v1."""
	return {
		"openapi": VERSION,
		"info": {"title": TITLE, "version": __version__},
		"paths": {**core_paths(), **plugin_paths},
		"components": {
			"securitySchemes": {
				"bearer": {"type": "http", "scheme": "bearer"},
				"cookie": {"type": "apiKey", "in": "cookie", "name": COOKIE},
			}
		},
		"security": [{"bearer": []}, {"cookie": []}],
	}
