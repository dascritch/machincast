"""Indexation lancée depuis l'interface (https://github.com/dascritch/machincast/issues/38, spec § 6 et § 8.11).

Le menu « Maintenance » de la fenêtre lance l'indexation rapide ou l'audit complet dans un processus à part,
détaché de l'interface : Machin indexer avec --window, qui montre son journal dans sa propre fenêtre
(machincast.interface.indexing_log, https://github.com/dascritch/machincast/issues/120). Fermer l'interface
ne l'arrête pas, et ne l'attend pas. L'interface suit seulement si le processus tourne encore (active_process).

Dans ce processus, Indexation fait tourner l'indexeur (machincast.indexer.indexer.index) avec son rôle en base,
dans un fil à part, pour que la fenêtre reste utilisable. Chaque ligne que l'indexeur écrirait dans le terminal
s'annonce aussitôt (ligne), sa fin avec son bilan (termine). Un décodeur absent, une base injoignable ou une autre
indexation en cours l'interrompt, et les sonores déjà vérifiés le restent. arreter() l'arrête après le fichier en
cours.
"""

import logging
import os
import sys
import threading
from pathlib import Path

import psycopg
from PySide6.QtCore import QObject, QProcess, Signal, SignalInstance

from machincast import log
from machincast.configuration import SILENCE_THRESHOLD
from machincast.database import Role, open_connection
from machincast.i18n import _, pgettext
from machincast.indexer import audit
from machincast.indexer.check import report_detail, report_text
from machincast.indexer.decoding import Check, UnavailableDecoder, check_file
from machincast.indexer.indexer import OngoingIndexing, index

INDEXER_LOG = "machincast.indexer"
"""Le journal où l'indexeur écrit ses lignes : une par sonore indexé, ses anomalies, son bilan."""

TITLES = {False: _("Quick indexing"), True: _("Full audit")}
"""Nom de chaque mode, selon audit_complet ; c'est aussi le titre de son journal et de son action de menu."""
FINISHED = {False: pgettext("quick indexing", "finished"), True: pgettext("full audit", "finished")}
LAUNCHED = {False: pgettext("quick indexing", "launched"), True: pgettext("full audit", "launched")}
"""Accordés au nom de chaque mode, qui les précède."""


def indexing_command(configuration: Path | None) -> list[str]:
	"""Machin indexer, lancé par le Python de l'interface, avec la même configuration qu'elle."""
	command = [sys.executable, "-m", "machincast.indexer"]
	if configuration is not None:
		command += ["--config", str(configuration.expanduser().absolute())]
	return command


def launch_detached(command: list[str]) -> int | None:
	"""Lance la commande dans un processus détaché, qui survit à l'interface ; son numéro, ou None en cas d'échec."""
	program, *arguments = command
	launched, number = QProcess.startDetached(program, arguments)
	if not launched:
		return None
	return int(number)


def active_process(number: int) -> bool:
	"""Le processus tourne-t-il encore ? Détaché, il n'est pas l'enfant de l'interface : rien à attendre de lui.

	Un numéro qu'un processus d'un autre compte a repris (PermissionError) n'est plus celui de l'indexation.
	"""
	try:
		os.kill(number, 0)
	except OSError:
		return False
	return True


class _Lines(logging.Handler):
	"""Relaie les lignes que l'indexeur journalise, formées comme dans le terminal."""

	def __init__(self, relay: SignalInstance) -> None:
		super().__init__()
		self.relay = relay

	def emit(self, saving: logging.LogRecord) -> None:
		anomaly = saving.levelno >= logging.WARNING
		self.relay.emit(log.line(saving), anomaly)


class Indexing(QObject):
	line = Signal(str, bool)
	"""Une ligne de la sortie de l'indexeur, comme dans le terminal, et si c'est une anomalie (ou une erreur)."""
	finished = Signal(str)
	"""L'indexation est finie : son bilan. Émis dans le fil de la fenêtre, comme ligne."""
	_line = Signal(str, bool)
	_finished = Signal(str)

	def __init__(
		self, socket: Path, database: str, parent: QObject | None = None, silence_threshold: float = SILENCE_THRESHOLD
	) -> None:
		super().__init__(parent)
		self.socket = socket
		self.database = database
		self.silence_threshold = silence_threshold
		"""Seuil de silence de l'audit complet (https://github.com/dascritch/machincast/issues/146)."""
		self.force = False
		"""L'audit complet décode aussi les sonores déjà audités et inchangés : Machin indexer --force
		(https://github.com/dascritch/machincast/issues/206) ; jamais depuis le menu de l'interface."""
		self._feed: threading.Thread | None = None
		self._stop = threading.Event()
		self._line.connect(self.line.emit)
		self._finished.connect(self._announce)
		# Les lignes de chaque sonore sont des informations : sans ce niveau, elles ne seraient pas écrites.
		logging.getLogger(INDEXER_LOG).setLevel(logging.INFO)

	def launch(self, full_audit: bool) -> None:
		self._feed = threading.Thread(target=self._index, args=(full_audit,), name="indexation", daemon=True)
		self._feed.start()

	def ongoing(self) -> bool:
		"""L'indexation a été lancée, et sa fin n'est pas encore annoncée."""
		return self._feed is not None

	def halt(self) -> None:
		"""Arrête l'indexation après le fichier en cours, et attend qu'elle le soit."""
		self._stop.set()
		if self._feed is not None:
			self._feed.join()
		self._feed = None

	def _announce(self, report: str) -> None:
		self._feed = None
		self.finished.emit(report)

	def _index(self, full_audit: bool) -> None:
		indexer = logging.getLogger(INDEXER_LOG)
		lines = _Lines(self._line)
		indexer.addHandler(lines)
		start = audit.CLOCK.now()
		try:
			with open_connection(self.socket, self.database, Role.INDEXING) as connection:
				report = index(
					connection, full_audit, _check_file, self._stop, self.silence_threshold, force=self.force
				)
			# Le bilan, puis le document d'audit, comme Machin indexer les écrit à la fin.
			indexer.info(report_text(report))
			audit.produce(report.anomalies, report_text(report), start)
			text = _("{mode} {finished}: {detail}.").format(
				mode=TITLES[full_audit], finished=FINISHED[full_audit], detail=report_detail(report)
			)
		except (UnavailableDecoder, OngoingIndexing, psycopg.Error) as error:
			indexer.error(_("indexing impossible: {error}").format(error=error))
			text = _("Indexing impossible: {error}; the sounds already checked stay so.").format(error=error)
		finally:
			indexer.removeHandler(lines)
		self._finished.emit(text)


def _check_file(path: Path, *, silence_threshold: float | None = None) -> Check:
	"""Le décodage de l'indexeur, appelé par son nom : les scénarios le remplacent."""
	if silence_threshold is None:
		return check_file(path)
	return check_file(path, silence_threshold=silence_threshold)
