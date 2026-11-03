"""Analyse du prochain sonore au dernier moment (https://github.com/dascritch/machincast/issues/181).

Au début de chaque sonore, Machin player réserve le suivant (machincast.player.broadcast). Si ce prochain sonore
est un fichier jamais vérifié en entier (sounds.checked_at vide), ou dont le fichier a changé depuis sa dernière
vérification (machincast.fingerprint.modified), la diffusion lance « Machin indexer --full-audit --sound N »
dans un processus à part, sans fenêtre, et ne l'attend jamais : que l'indexeur plante ou n'ait pas fini, le sonore
est joué à son heure. Ses lignes vont dans le journal de Machin player. Un même sonore n'est pas redemandé avant
RELANCE. Un stream n'est jamais analysé, comme l'indexeur ne vérifie jamais les streams.
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.fingerprint import modified

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
	"""Un fichier jamais vérifié en entier, ou changé depuis ; la connexion a le rôle de la lecture."""
	line = connection.execute(
		"SELECT location, checked_at, file_modified_at, file_size FROM sounds WHERE id = %s", (sound,)
	).fetchone()
	# Seul un fichier a un emplacement : la base le garantit (contrainte sounds_file_or_stream).
	if (line is None) or (line[0] is None):
		return False
	location, checks_at, modified_at, size = line
	if checks_at is None:
		return True
	return modified(Path(str(location)), modified_at, size)


class Analyser:
	"""Lance l'analyse d'un sonore, sans l'attendre ; se souvient des sonores demandés."""

	def __init__(self, command: list[str], restarted: timedelta = RESTARTED) -> None:
		self.command = command
		self.restarted = restarted
		self._requests: dict[int, datetime] = {}
		self._process: list[subprocess.Popen[bytes]] = []

	def to_ask(self, sound: int, instant: datetime) -> bool:
		"""Pas demandé depuis RELANCE."""
		last = self._requests.get(sound)
		return (last is None) or (instant - last >= self.restarted)

	def launch(self, sound: int, instant: datetime) -> None:
		"""Lance l'analyse dans sa propre session, sans entrée : un Ctrl-C dans le terminal de la diffusion ne
		l'interrompt pas. Lève OSError si la commande ne peut pas être lancée ; la demande est retenue quand même,
		pour ne pas redire l'échec à chaque sonore."""
		# Les analyses finies sont relevées, pour ne pas laisser de processus zombie.
		self._process = [process for process in self._process if process.poll() is None]
		self._requests[sound] = instant
		self._process.append(
			subprocess.Popen([*self.command, str(sound)], stdin=subprocess.DEVNULL, start_new_session=True)
		)
