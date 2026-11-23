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
	"interface.event_card": (
		"asked by Machin interface when the card of an event opens, with “card”, “connection” and “parent”: the "
		"plugin answers a machincast.interface.event_card.CardSection, its section of the card, saved with the event "
		"(https://github.com/dascritch/machincast/issues/611)"
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
	"interface.plugin_window": (
		"asked by Machin interface, of one plugin, when its window opens from the menu “Plugins”, with “parent”, the "
		"window: the plugin answers a QWidget, its settings, shown under its name, version and description "
		"(https://github.com/dascritch/machincast/issues/587)"
	),
}
"""Les points du cœur, et ce qu'ils disent : chaque ticket qui en ajoute un le décrit ici, avec ses données
(https://github.com/dascritch/machincast/issues/348)."""
CLOSING = 5.0
"""Secondes laissées aux notifications en cours, à la fermeture d'un binaire."""
FAILED = N_("plugin “{plugin}” failed at the extension point “{point}”: {error}")


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
	try:
		subscription.function(data)
	except Exception as error:
		_failed(subscription, point, error)
