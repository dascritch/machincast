"""Vérification immédiate des fichiers ajoutés par l'interface (https://github.com/dascritch/machincast/issues/30).

Un fichier ajouté entre en base à l'état aperçu (machincast.interface.adding) ; l'indexeur le décode aussitôt, en tâche
de fond, avec son propre code (machincast.indexer.check.check_sounds) et son rôle en base : l'interface
reste utilisable pendant ce temps. Les vérifications demandées passent l'une après l'autre ; chacune se conclut par
une annonce (termine), avec l'état de chaque sonore. Si l'indexeur ne sait pas décoder un format, ou si la base est
injoignable, les sonores restent en aperçu : la prochaine indexation les reprendra.

Fermer la fenêtre attend la fin de la vérification en cours (arreter).

La vérification complète d'un sonore, demandée depuis sa fiche (FullCheck,
https://github.com/dascritch/machincast/issues/190), est l'audit complet de son seul fichier, comme
Machin indexer --full-audit --sound N : décodé en entier, ses silences mesurés au seuil de la configuration.
"""

import logging
import threading
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QObject, Signal

from machincast.database import Role, open_connection
from machincast.i18n import _
from machincast.indexer.check import check_sounds, threshold_text
from machincast.indexer.decoding import Check, UnavailableDecoder, check_file
from machincast.interface import display
from machincast.interface.lists import STATES

log = logging.getLogger(__name__)

AFTER_FAILURE = _("the next indexing will take up the files in preview again.")


class Checker(QObject):
	finished = Signal(str)
	"""Une vérification est finie : ce qu'en dit la barre d'état. Émis dans le fil de l'interface."""
	_finished = Signal(str)
	"""Émis par le fil de la vérification ; termine le relaie dans le fil de l'interface."""

	def __init__(self, connection: psycopg.Connection[TupleRow], parent: QObject | None = None) -> None:
		"""connexion : celle de l'interface, dont la vérification reprend le socket et la base."""
		super().__init__(parent)
		self.socket = Path(str(connection.info.host))
		self.database = connection.info.dbname
		self._waiting: list[list[int]] = []
		self._lock = threading.Lock()
		self._feed: threading.Thread | None = None
		self._announce_remaining = 0
		"""Vérifications demandées dont la fin n'est pas encore annoncée ; tenu dans le fil de l'interface."""
		self._finished.connect(self._announce)

	def check(self, identifiers: list[int]) -> None:
		"""Demande la vérification de ces sonores, après celles déjà demandées."""
		if identifiers == []:
			return
		self._announce_remaining += 1
		with self._lock:
			self._waiting.append(identifiers)
			if (self._feed is not None) and (self._feed.is_alive()):
				return
			self._feed = threading.Thread(target=self._work, name="check", daemon=True)
			self._feed.start()

	def ongoing(self) -> bool:
		"""Une vérification demandée n'a pas encore annoncé sa fin."""
		return self._announce_remaining > 0

	def _announce(self, text: str) -> None:
		self._announce_remaining -= 1
		self.finished.emit(text)

	def halt(self) -> None:
		"""Attend la fin des vérifications demandées ; la fenêtre se ferme, leur fin ne s'annonce plus."""
		feed = self._feed
		if feed is not None:
			feed.join()
		self._announce_remaining = 0

	def _work(self) -> None:
		while True:
			with self._lock:
				if self._waiting == []:
					return
				identifiers = self._waiting.pop(0)
			self._finished.emit(self._check(identifiers))

	def _check(self, identifiers: list[int]) -> str:
		try:
			with open_connection(self.socket, self.database, Role.INDEXING) as connection:
				check_sounds(connection, _check_file, identifiers=identifiers)
				with connection.transaction():
					lines = connection.execute(
						"SELECT artist, title, location, state::text FROM sounds WHERE id = ANY(%s) ORDER BY id",
						(identifiers,),
					).fetchall()
		except (UnavailableDecoder, psycopg.Error) as error:
			log.error(_("check of the added files impossible: {error}").format(error=error))
			return _("Check impossible: {error}; {after_failure}").format(error=error, after_failure=AFTER_FAILURE)
		states = []
		for artist, title, location, state in lines:
			states.append(f"{display.sound_name(artist, title, location, None)}, {STATES.get(str(state), str(state))}")
		return _("Check finished: {list}.").format(list=_("; ").join(states))


def sound_states(connection: psycopg.Connection[TupleRow], identifiers: list[int]) -> str:
	"""« Neige, actif ; Café à minuit, erroné » : chaque sonore et son état, après sa vérification."""
	with connection.transaction():
		lines = connection.execute(
			"SELECT artist, title, location, state::text FROM sounds WHERE id = ANY(%s) ORDER BY id",
			(identifiers,),
		).fetchall()
	artist_list = []
	for artist, title, location, state in lines:
		artist_list.append(
			_("{sound}, {state}").format(
				sound=display.sound_name(artist, title, location, None), state=STATES.get(str(state), str(state))
			)
		)
	return _("; ").join(artist_list)


class FullCheck(QObject):
	"""L'audit complet d'un sonore, en tâche de fond ; chaque fin s'annonce (terminee), avec son sonore."""

	finished = Signal(int, str)
	"""Le sonore vérifié, et ce que la vérification en dit. Émis dans le fil de l'interface."""
	_finished = Signal(int, str)

	def __init__(self, connection: psycopg.Connection[TupleRow], parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.socket = Path(str(connection.info.host))
		self.database = connection.info.dbname
		self._feeds: list[threading.Thread] = []
		self._remaining_list = 0
		"""Vérifications lancées dont la fin n'est pas encore annoncée ; tenu dans le fil de l'interface."""
		self._finished.connect(self._announce)

	def launch(self, sound: int, silence_threshold: float) -> None:
		self._remaining_list += 1
		feed = threading.Thread(
			target=lambda: self._finished.emit(sound, self._check(sound, silence_threshold)),
			name="full check",
			daemon=True,
		)
		self._feeds.append(feed)
		feed.start()

	def ongoing(self) -> bool:
		return self._remaining_list > 0

	def halt(self) -> None:
		"""Attend la fin des vérifications lancées ; la fenêtre se ferme, leur fin ne s'annonce plus."""
		for feed in self._feeds:
			feed.join()
		self._remaining_list = 0

	def _announce(self, sound: int, text: str) -> None:
		self._remaining_list -= 1
		self.finished.emit(sound, text)

	def _check(self, sound: int, silence_threshold: float) -> str:
		def check(path: Path, *, silence_threshold: float | None = None) -> Check:
			# Appelé par son nom au moment du décodage : les scénarios le remplacent.
			return _check_full_file(path, silence_threshold=silence_threshold)

		try:
			with open_connection(self.socket, self.database, Role.INDEXING) as connection:
				report = check_sounds(
					connection, check, full_audit=True, identifiers=[sound], silence_threshold=silence_threshold
				)
				states = sound_states(connection, [sound])
		except (UnavailableDecoder, psycopg.Error) as error:
			log.error(_("full check impossible: {error}").format(error=error))
			return _("Check impossible: {error}.").format(error=error)
		if report.already_audited:
			# https://github.com/dascritch/machincast/issues/206
			return _("Already audited at the threshold of {threshold_text} dB, unchanged file: {states}.").format(
				threshold_text=threshold_text(silence_threshold), states=states
			)
		return _("Check finished: {states}.").format(states=states)


def _check_full_file(path: Path, *, silence_threshold: float | None = None) -> Check:
	"""Le décodage de l'audit complet, silences compris."""
	return check_file(path, silence_threshold=silence_threshold)


def _check_file(path: Path, *, silence_threshold: float | None = None) -> Check:
	"""Le décodage de l'indexeur, appelé par son nom : les scénarios le remplacent. La vérification des fichiers
	ajoutés n'est pas un audit complet : elle ne mesure pas les silences (silence_threshold n'est jamais donné)."""
	return check_file(path)
