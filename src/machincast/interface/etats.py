"""États des pipelines de GStreamer de l'interface, hors de son fil (https://github.com/dascritch/machincast/issues/259).

Lancer, mettre en pause ou arrêter un pipeline ouvre ou ferme son périphérique audio : le serveur audio du poste peut
tarder à répondre, ou ne plus répondre, par exemple au retour d'un écran verrouillé. Demandé dans le fil de
l'interface, ce changement d'état la figeait. Chaque pipeline a donc son Pilote : un fil qui fait ses changements
d'état, un à un, dans l'ordre demandé ; l'interface les demande sans les attendre. Un pipeline arrêté (eteindre) l'est
par son fil, qui s'achève ensuite ; un pipeline qui ne répond plus n'immobilise que son fil.

Ce module est le seul de l'interface à appeler set_state (peripheriques_bloques.feature).
"""

import logging
import queue
import threading

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

journal = logging.getLogger(__name__)

FIN = None
"""Ce qui suit la dernière demande d'un pilote : son fil s'achève."""


class Pilote:
	"""Les changements d'état d'un pipeline, faits par son propre fil, dans l'ordre où ils sont demandés."""

	def __init__(self, pipeline: Gst.Element) -> None:
		self._demandes: queue.SimpleQueue[Gst.State | None] = queue.SimpleQueue()
		self._echec = threading.Event()
		self._eteint = False
		self._en_attente = 0
		"""Demandes pas encore faites."""
		self._faites = threading.Condition()
		fil = threading.Thread(target=self._changer, args=(pipeline,), name=f"etats-{pipeline.get_name()}", daemon=True)
		fil.start()

	def vers(self, etat: Gst.State) -> None:
		"""Demande l'état, sans l'attendre ; rien après eteindre."""
		if not self._eteint:
			self._demander(etat)

	def eteindre(self) -> None:
		"""Demande l'arrêt du pipeline, qui libère son périphérique, sans l'attendre ; le pilote ne sert plus."""
		if not self._eteint:
			self._eteint = True
			self._demander(Gst.State.NULL)
			self._demandes.put(FIN)

	def attendre(self, delai: float) -> bool:
		"""Attend, delai secondes au plus, que les demandes soient faites ; vrai si elles le sont. Pour ce qui doit
		suivre un changement d'état, comme un déplacement dans le fichier : jamais sans délai."""
		with self._faites:
			return self._faites.wait_for(lambda: self._en_attente == 0, delai)

	def a_echoue(self) -> bool:
		"""Un changement d'état demandé a échoué : le pipeline ne peut pas jouer."""
		return self._echec.is_set()

	def _demander(self, etat: Gst.State) -> None:
		with self._faites:
			self._en_attente += 1
		self._demandes.put(etat)

	def _changer(self, pipeline: Gst.Element) -> None:
		while (etat := self._demandes.get()) is not FIN:
			if pipeline.set_state(etat) == Gst.StateChangeReturn.FAILURE:
				journal.warning(f"pipeline {pipeline.get_name()} : passage à l'état {etat.value_nick} impossible")
				self._echec.set()
			with self._faites:
				self._en_attente -= 1
				self._faites.notify_all()
