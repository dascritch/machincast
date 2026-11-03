"""États des pipelines de GStreamer de l'interface, hors de son fil (https://github.com/dascritch/machincast/issues/259).

Lancer, mettre en pause ou arrêter un pipeline ouvre ou ferme son périphérique audio : le serveur audio du poste peut
tarder à répondre, ou ne plus répondre, par exemple au retour d'un écran verrouillé. Demandé dans le fil de
l'interface, ce changement d'état la figeait. Chaque pipeline a donc son Pilote : un fil qui fait ses changements
d'état, un à un, dans l'ordre demandé ; l'interface les demande sans les attendre. Un pipeline arrêté (eteindre) l'est
par son fil, qui s'achève ensuite ; un pipeline qui ne répond plus n'immobilise que son fil.

Ce module est le seul de l'interface à appeler set_state (blocked_devices.feature).
"""

import logging
import queue
import threading

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

log = logging.getLogger(__name__)

END = None
"""Ce qui suit la dernière demande d'un pilote : son fil s'achève."""


class Pilot:
	"""Les changements d'état d'un pipeline, faits par son propre fil, dans l'ordre où ils sont demandés."""

	def __init__(self, pipeline: Gst.Element) -> None:
		self._requests: queue.SimpleQueue[Gst.State | None] = queue.SimpleQueue()
		self._failure = threading.Event()
		self._off = False
		self._in_waiting = 0
		"""Demandes pas encore faites."""
		self._done_list = threading.Condition()
		feed = threading.Thread(target=self._change, args=(pipeline,), name=f"etats-{pipeline.get_name()}", daemon=True)
		feed.start()

	def to(self, state: Gst.State) -> None:
		"""Demande l'état, sans l'attendre ; rien après eteindre."""
		if not self._off:
			self._ask(state)

	def switch_off(self) -> None:
		"""Demande l'arrêt du pipeline, qui libère son périphérique, sans l'attendre ; le pilote ne sert plus."""
		if not self._off:
			self._off = True
			self._ask(Gst.State.NULL)
			self._requests.put(END)

	def wait(self, delay: float) -> bool:
		"""Attend, delai secondes au plus, que les demandes soient faites ; vrai si elles le sont. Pour ce qui doit
		suivre un changement d'état, comme un déplacement dans le fichier : jamais sans délai."""
		with self._done_list:
			return self._done_list.wait_for(lambda: self._in_waiting == 0, delay)

	def has_failed(self) -> bool:
		"""Un changement d'état demandé a échoué : le pipeline ne peut pas jouer."""
		return self._failure.is_set()

	def _ask(self, state: Gst.State) -> None:
		with self._done_list:
			self._in_waiting += 1
		self._requests.put(state)

	def _change(self, pipeline: Gst.Element) -> None:
		while (state := self._requests.get()) is not END:
			if pipeline.set_state(state) == Gst.StateChangeReturn.FAILURE:
				log.warning(f"pipeline {pipeline.get_name()} : passage à l'état {state.value_nick} impossible")
				self._failure.set()
			with self._done_list:
				self._in_waiting -= 1
				self._done_list.notify_all()
