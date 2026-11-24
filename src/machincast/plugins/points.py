"""Les points d'extension, où les plugins s'accrochent (https://github.com/dascritch/machincast/issues/585).

Un point a un nom : ceux du cœur sont dans CORE, chacun décrit ; un plugin peut déclarer les siens, préfixés de son nom
(« cartwall.button »), pour les plugins qui le demandent. Un plugin s'abonne à un point déclaré ; le cœur, ou le
plugin qui l'a déclaré, l'appelle avec ses données, de deux façons :

- notify : prévenir, sans attendre. Chaque abonné est appelé dans un fil à part (un seul fil pour tous, dans l'ordre
  des appels), pour que la diffusion, l'indexation ou l'interface ne l'attendent jamais ;
- collect : demander, et attendre les réponses de chaque abonné, dans l'ordre de chargement des plugins, par exemple
  les pages qu'il ajoute à l'intranet.

L'exception d'un abonné est consignée, avec le plugin et le point ; elle n'arrête ni l'appelant ni les autres abonnés.
"""

import logging
import threading
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from machincast.i18n import N_, _

log = logging.getLogger(__name__)

Subscriber = Callable[[Mapping[str, Any]], object]

CORE: dict[str, str] = {
	"intranet.extensions": (
		"asked by Machin intranet when it starts, without data: the plugin answers its pages, API routes and static "
		"files, a machincast.intranet.extensions.Extension (https://github.com/dascritch/machincast/issues/588)"
	),
	"grid.substitutions": (
		"asked each time a binary reads the grid, without data: the plugin answers a "
		"machincast.shared.grid.Substitution, the events that an event plays, off the grid, and the one that plays "
		"each of its occurrences (https://github.com/dascritch/machincast/issues/608)"
	),
	"grid.event_colour": (
		"asked when a binary colours an event, in the calendar of Machin interface and of Machin intranet and in the "
		"airplay tables, with “event”, its identifier, or None for the colour of a priority, and “priority”, or None "
		"when unknown: the plugin answers a colour “#rrggbb”, or None to keep that of MachinCast "
		"(https://github.com/dascritch/machincast/issues/635)"
	),
	"interface.event_card": (
		"asked by Machin interface when the card of an event opens, with “card”, “connection” and “parent”: the "
		"plugin answers a machincast.interface.card.CardSection, its section of the card, saved with the event; "
		"its grid_widget goes under the days of the recurrence, and it may replace the play list "
		"(https://github.com/dascritch/machincast/issues/611)"
	),
	"interface.menu": (
		"asked by Machin interface when its window opens, with “window”, “connection” and “parent”: the plugin "
		"answers a QMenu or a QAction, or a list of them, put in the menu bar before the menu “Help” "
		"(https://github.com/dascritch/machincast/issues/591)"
	),
	"interface.context_menu": (
		"asked by Machin interface when the context menu of a line of a list opens, with “menu”, “category”, "
		"“identifiers” (the selection, or the clicked line), “clicked” and “parent”: the plugin adds its entries "
		"to the menu (https://github.com/dascritch/machincast/issues/591)"
	),
	"player.before_choice": (
		"asked by Machin player before each sound chosen in the list of the active event, forecast of the coming "
		"sounds included, with “instant”, “connection”, “event”, “priority”, the candidate “sound”, its “bank”, "
		"“sequence” and “duration”, “last_play”, a function giving the start of the last play of a collection of "
		"banks, planned plays included, and “forecast”: the plugin answers the identifier of a bank, one of whose "
		"playable sounds plays before the candidate, or None (https://github.com/dascritch/machincast/issues/640)"
	),
	"player.service_start": (
		"notified by Machin player when its broadcast starts, with “instant” "
		"(https://github.com/dascritch/machincast/issues/589)"
	),
	"player.service_stop": (
		"notified by Machin player when its broadcast stops, with “instant” and “error”, None for a stop asked for "
		"(https://github.com/dascritch/machincast/issues/589)"
	),
	"player.event_start": (
		"notified by Machin player when an event goes on air, with “instant”, “event”, “name”, “public_name”, "
		"“priority”, “start” and “end” of the occurrence, and “playing”, the event it plays when it lends its name "
		"(https://github.com/dascritch/machincast/issues/589)"
	),
	"player.event_stop": (
		"notified by Machin player when the event on air ends, with the data of its start and the “instant” of its "
		"end (https://github.com/dascritch/machincast/issues/589)"
	),
	"player.sequence_start": (
		"notified by Machin player when a sequence starts, with “instant”, “sequence”, “name”, “public_name”, "
		"“event” and “event_name” (https://github.com/dascritch/machincast/issues/589)"
	),
	"player.sequence_stop": (
		"notified by Machin player when the sequence on air ends, with the data of its start and the “instant” of "
		"its end (https://github.com/dascritch/machincast/issues/589)"
	),
	"player.sound_start": (
		"notified by Machin player when a sound starts, with “instant”, “play”, “sound”, “artist”, “title”, "
		"“location”, “stream”, “duration” and “start_position” in seconds, “event”, “lender”, “sequence” and “bank” "
		"(https://github.com/dascritch/machincast/issues/589)"
	),
	"player.sound_stop": (
		"notified by Machin player when a sound ends, with the data of its start, “instant”, “start”, “played” and "
		"“end_position” in seconds, “cut” and “error” (https://github.com/dascritch/machincast/issues/589)"
	),
	"indexer.sound_spotted": (
		"notified by Machin indexer when it registers a new file, in preview, with “sound”, “location”, “bank” and "
		"“bank_name”, the bank whose directory it was found in (https://github.com/dascritch/machincast/issues/590)"
	),
	"indexer.sound_detailed": (
		"notified by Machin indexer when it has written what it found of a sound, with “sound”, “location”, "
		"“previous_state”, “state”, “duration” in seconds, “artist”, “title”, “metadata”, “file_type”, "
		"“detected_start” and “detected_end” in seconds, “audited”, “problem” and “loudness”, the integrated loudness "
		"and the peak measured by a full audit, or None (https://github.com/dascritch/machincast/issues/590, "
		"https://github.com/dascritch/machincast/issues/642)"
	),
	"log_incident": (
		"notified in each binary for each serious incident: an entry of level “incident” of the log, or an error of "
		"the journal of the binary, with “executable”, “instant”, “level”, “kind”, “message”, “references” (“sound”, "
		"“bank”, “event”) and “origin”; a plugin failing to warn creates no incident in turn "
		"(https://github.com/dascritch/machincast/issues/592)"
	),
	"interface.plugin_window": (
		"asked by Machin interface, of one plugin, when its window opens from the menu “Plugins”, with “parent”, the "
		"window: the plugin answers a QWidget, its settings, shown under its name, version and description "
		"(https://github.com/dascritch/machincast/issues/587)"
	),
}
"""Les points du cœur, et ce qu'ils disent : chaque ticket qui en ajoute un le décrit ici, avec ses données
(https://github.com/dascritch/machincast/issues/348)."""
CARD_CATEGORIES = {"bank": "a bank", "sequence": "a sequence", "sound": "a sound", "feed": "a feed"}
"""Les fiches de l'interface, autres que celle d'un événement, et ce qu'elles montrent."""
for _category, _shown in CARD_CATEGORIES.items():
	CORE[f"interface.{_category}_card"] = (
		f"asked by Machin interface when the card of {_shown} opens, with “card”, “connection” and “parent”: the "
		"plugin answers a machincast.interface.card.CardSection, its section of the card, above its buttons, saved "
		"with it (https://github.com/dascritch/machincast/issues/591)"
	)
for _category, _shown in {"event": "an event", **CARD_CATEGORIES}.items():
	CORE[f"interface.load_{_category}"] = (
		f"notified by Machin interface when the card of {_shown} has read it, with “category”, “identifier” (None "
		"for a new one) and “copy” (https://github.com/dascritch/machincast/issues/591)"
	)
	CORE[f"interface.presave_{_category}"] = (
		f"asked by Machin interface when the card of {_shown} is written, before the saving is committed, with "
		"“category”, “identifier”, “row” (its line, in JSON), “card” and “connection”: a reason, a non-empty "
		"string, refuses the saving (https://github.com/dascritch/machincast/issues/591)"
	)
	CORE[f"interface.save_{_category}"] = (
		f"notified by Machin interface when {_shown} is saved, with “category”, “identifier” and “row” "
		"(https://github.com/dascritch/machincast/issues/591)"
	)

CLOSING = 5.0
"""Secondes laissées aux notifications en cours, à la fermeture d'un binaire."""
FAILED = N_("plugin “{plugin}” failed at the extension point “{point}”: {error}")


_calling = threading.local()
"""Le point dont le fil des plugins appelle un abonné, le temps de l'appel."""


def calling() -> str | None:
	"""Le point dont un abonné est en train d'être appelé dans ce fil ; None hors d'un appel notifié."""
	point: str | None = getattr(_calling, "point", None)
	return point


class UnknownPoint(Exception):
	"""Un abonnement à un point que ni le cœur ni aucun plugin chargé ne déclare : une faute de frappe, ou un plugin
	demandé qui manque."""


@dataclass(frozen=True)
class _Subscription:
	plugin: str
	function: Subscriber


class Points:
	"""Le registre des points d'extension d'un binaire."""

	def __init__(self) -> None:
		self._declared: dict[str, str] = dict(CORE)
		self._subscriptions: dict[str, list[_Subscription]] = {}
		self._executor: ThreadPoolExecutor | None = None
		self._lock = threading.Lock()

	def declare(self, plugin: str, point: str, description: str) -> None:
		"""Un point d'un plugin, préfixé de son nom."""
		if not point.startswith(f"{plugin}."):
			raise ValueError(
				_("the extension point “{point}” of the plugin “{plugin}” starts with “{plugin}.”").format(
					point=point, plugin=plugin
				)
			)
		self._declared[point] = description

	def declared(self) -> dict[str, str]:
		return dict(self._declared)

	def subscribe(self, plugin: str, point: str, function: Subscriber) -> None:
		if point not in self._declared:
			raise UnknownPoint(_("unknown extension point “{point}”").format(point=point))
		self._subscriptions.setdefault(point, []).append(_Subscription(plugin, function))

	def subscribers(self, point: str) -> list[str]:
		"""Les plugins abonnés au point, dans l'ordre de leur chargement."""
		names = []
		for subscription in self._subscriptions.get(point, []):
			names.append(subscription.plugin)
		return names

	def collect(self, point: str, data: Mapping[str, Any] | None = None) -> list[tuple[str, object]]:
		"""La réponse de chaque abonné, avec son plugin ; celui qui échoue n'en donne pas."""
		given: Mapping[str, Any] = (data) or ({})
		answers = []
		for subscription in self._subscriptions.get(point, []):
			try:
				answers.append((subscription.plugin, subscription.function(given)))
			except Exception as error:
				_failed(subscription, point, error)
		return answers

	def collect_from(self, plugin: str, point: str, data: Mapping[str, Any] | None = None) -> list[object]:
		"""Les réponses d'un seul plugin abonné au point, comme collect : celui dont s'ouvre la fenêtre, par exemple."""
		given: Mapping[str, Any] = (data) or ({})
		answers = []
		for subscription in self._subscriptions.get(point, []):
			if subscription.plugin == plugin:
				try:
					answers.append(subscription.function(given))
				except Exception as error:
					_failed(subscription, point, error)
		return answers

	def notify(self, point: str, data: Mapping[str, Any] | None = None) -> None:
		"""Prévient chaque abonné, dans le fil des plugins : rendue aussitôt."""
		subscriptions = self._subscriptions.get(point, [])
		if subscriptions == []:
			return
		given: Mapping[str, Any] = dict((data) or ({}))
		with self._lock:
			if self._executor is None:
				self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="plugins")
			executor = self._executor
		for subscription in subscriptions:
			executor.submit(_call, subscription, point, given)

	def close(self) -> None:
		"""Attend les notifications en cours, CLOSING secondes au plus, à la fermeture du binaire."""
		with self._lock:
			executor, self._executor = self._executor, None
		if executor is None:
			return
		finished = threading.Event()
		executor.submit(finished.set)
		finished.wait(CLOSING)
		executor.shutdown(wait=False, cancel_futures=True)


def _failed(subscription: _Subscription, point: str, error: Exception) -> None:
	log.error(_(FAILED).format(plugin=subscription.plugin, point=point, error=error), exc_info=error)


def _call(subscription: _Subscription, point: str, data: Mapping[str, Any]) -> None:
	_calling.point = point
	try:
		subscription.function(data)
	except Exception as error:
		_failed(subscription, point, error)
	finally:
		_calling.point = None
