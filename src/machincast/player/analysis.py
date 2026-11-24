"""Analyse du prochain sonore au dernier moment (https://github.com/dascritch/machincast/issues/181).

Au début de chaque sonore, Machin player réserve le suivant, et prévoit les sonores à venir
(machincast.player.broadcast) ; il examine chacun d'eux, et le sonore qui démarre sans avoir été réservé
(https://github.com/dascritch/machincast/issues/646). Si c'est un fichier qui n'a pas eu d'audit complet depuis la
dernière modification de son fichier (sounds.audited_at vide, plus ancien que la date de modification du fichier, ou
fichier changé depuis : machincast.fingerprint.audited_since_modification,
https://github.com/dascritch/machincast/issues/401), même s'il a été vérifié par une indexation rapide, ou un fichier
sain sans mesure de son niveau (https://github.com/dascritch/machincast/issues/642), la diffusion lance
« Machin indexer --full-audit --sound N »
dans un processus à part, sans fenêtre, et ne l'attend jamais : que l'indexeur plante ou n'ait pas fini, le sonore
est joué à son heure. Au plus RUNNING analyses tournent à la fois : un sonore de plus est redemandé au début du sonore
suivant. Ses lignes vont dans le journal de Machin player. Machin indexer --sound ne prend aucun verrou : l'audit se fait même pendant
une indexation rapide ou un audit complet de toute la base. Un même sonore n'est pas redemandé avant RESTARTED. Un stream n'est jamais analysé, comme l'indexeur ne vérifie jamais les streams.
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.fingerprint import audited_since_modification
from machincast.player import queries

RUNNING = 2
"""Les analyses qui tournent à la fois, au plus : au démarrage, la playlist immédiate n'en lance pas une par sonore."""
RESTARTED = timedelta(hours=1)
"""Délai avant de redemander l'analyse d'un même sonore : celle d'avant a peut-être échoué, ou le fichier changé."""


def analysis_command(configuration: Path) -> list[str]:
	"""Machin indexer, lancé par le Python de la lecture, avec sa configuration, en audit complet d'un seul
	sonore : le numéro du sonore s'ajoute à la fin."""
	return [
		sys.executable,
		"-m",
		"machincast.indexer",
		"--config",
		str(configuration.expanduser().absolute()),
		"--full-audit",
		"--sound",
	]


def to_analyse(connection: psycopg.Connection[TupleRow], sound: int) -> bool:
	"""Un fichier sans audit complet depuis sa dernière modification ; la connexion a le rôle de la lecture."""
	line = queries.file_audit(connection, sound)
	# Seul un fichier a un emplacement : la base le garantit (contrainte sounds_file_or_stream).
	if (line is None) or (line[0] is None):
		return False
	location, audited_at, modified_at, size = line
	return not audited_since_modification(Path(str(location)), modified_at, size, audited_at)


class Analyser:
	"""Lance l'analyse d'un sonore, sans l'attendre ; se souvient des sonores demandés."""

	def __init__(self, command: list[str], restarted: timedelta = RESTARTED, running: int = RUNNING) -> None:
		self.command = command
		self.restarted = restarted
		self.running = running
		self._requests: dict[int, datetime] = {}
		self._process: list[subprocess.Popen[bytes]] = []

	def to_ask(self, sound: int, instant: datetime) -> bool:
		"""Pas demandé depuis RELANCE."""
		last = self._requests.get(sound)
		return (last is None) or (instant - last >= self.restarted)

	def busy(self) -> bool:
		"""Assez d'analyses tournent déjà ; les finies sont relevées."""
		self._collect()
		return len(self._process) >= self.running

	def _collect(self) -> None:
		"""Les analyses finies sont relevées, pour ne pas laisser de processus zombie."""
		process_list = []
		for process in self._process:
			if process.poll() is None:
				process_list.append(process)
		self._process = process_list

	def launch(self, sound: int, instant: datetime) -> None:
		"""Lance l'analyse dans sa propre session, sans entrée : un Ctrl-C dans le terminal de la diffusion ne
		l'interrompt pas. Lève OSError si la commande ne peut pas être lancée ; la demande est retenue quand même,
		pour ne pas redire l'échec à chaque sonore."""
		self._collect()
		self._requests[sound] = instant
		self._process.append(
			subprocess.Popen([*self.command, str(sound)], stdin=subprocess.DEVNULL, start_new_session=True)
		)
