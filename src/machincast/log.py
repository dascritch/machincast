"""Messages des exécutables, par la bibliothèque logging (revue de https://github.com/dascritch/machincast/pull/65).

Le code n'appelle jamais print : il obtient un journal par logging.getLogger(__name__), sous « machincast ».
Les informations (INFO) vont sur la sortie standard ; les anomalies (WARNING) et les erreurs (ERROR) sur la
sortie d'erreur. Chaque ligne commence par l'heure de son message, en ISO 8601, à la seconde, avec le décalage horaire
du poste, par exemple « 2026-10-23T07:55:19+02:00 à l'antenne : … » ; elle remplace le nom de l'exécutable, qui la
précédait (https://github.com/dascritch/machincast/issues/253).

Les mêmes lignes vont aussi, quand il existe et s'écrit, dans le fichier « <exécutable>.log » de /var/log/machincast
(DIRECTORY, ou celui de la variable d'environnement MACHINCAST_LOG_DIRECTORY), précédées de leur niveau
(https://github.com/dascritch/machincast/issues/381) : les règles usuelles d'administration d'un service. install.sh le
crée, au groupe machincast, que partagent le compte du service et celui du bureau : chacun lit ce que l'autre y écrit.
Le fichier se crée lisible et modifiable par le groupe (FILE_MODE) ; logrotate le fait tourner.
"""

import contextlib
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

LOG = "machincast"
DIRECTORY = Path("/var/log/machincast")
"""Le répertoire des logs et des rapports de crash de MachinCast, qu'install.sh crée."""
ENVIRONMENT = "MACHINCAST_LOG_DIRECTORY"
"""Variable d'environnement qui désigne un autre répertoire des logs : celui d'un scénario."""
FILE_MODE = 0o660
"""Un fichier de log se lit et s'écrit par son compte et le groupe machincast."""


def directory() -> Path:
	"""Le répertoire des logs : celui de ENVIRONMENT, sinon DIRECTORY."""
	from_environment = os.environ.get(ENVIRONMENT)
	if from_environment:
		return Path(from_environment)
	return DIRECTORY


TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2} ")
"""Début d'une ligne de message : son horodatage, suivi d'une espace."""


def line(saving: logging.LogRecord) -> str:
	"""Le message, précédé de son heure, comme sur les sorties de l'exécutable."""
	hour = datetime.fromtimestamp(saving.created).astimezone().isoformat(timespec="seconds")
	return f"{hour} {saving.getMessage()}"


class _Timestamped(logging.Formatter):
	def format(self, record: logging.LogRecord) -> str:
		return line(record)


class _Levelled(logging.Formatter):
	def format(self, record: logging.LogRecord) -> str:
		hour, _space, message = line(record).partition(" ")
		return f"{hour} {record.levelname} {message}"


class _File(logging.FileHandler):
	"""Le fichier de log d'un exécutable, créé lisible et modifiable par le groupe (FILE_MODE)."""

	def _open(self):  # type: ignore[no-untyped-def]
		created = not os.path.exists(self.baseFilename)
		stream = super()._open()
		if created:
			with contextlib.suppress(OSError):
				os.chmod(self.baseFilename, FILE_MODE)
		return stream


def _file_handler(executable: str) -> logging.Handler | None:
	"""Le fichier de log de l'exécutable, dans directory() ; None s'il n'existe pas ou ne s'écrit pas."""
	folder = directory()
	if (not folder.is_dir()) or (not os.access(folder, os.W_OK)):
		return None
	try:
		handler = _File(folder / f"{executable}.log", encoding="utf-8")
	except OSError:
		return None
	handler.setFormatter(_Levelled())
	return handler


class _Outputs(logging.Handler):
	"""Écrit chaque message sur la sortie standard ou la sortie d'erreur en cours, selon son niveau.

	Les sorties sont lues à chaque message, et non à la création : un test peut les remplacer.
	"""

	def emit(self, saving: logging.LogRecord) -> None:
		try:
			if saving.levelno < logging.WARNING:
				output = sys.stdout
			else:
				output = sys.stderr
			output.write(self.format(saving) + "\n")
			output.flush()
		except Exception:
			self.handleError(saving)


def configure(executable: str) -> logging.Logger:
	"""Prépare le journal « machincast » pour un exécutable ; sans effet cumulatif si appelé plusieurs fois. Le nom de
	l'exécutable ne figure plus dans ses lignes, que son horodatage ouvre ; il reste celui de son journal."""
	log = logging.getLogger(LOG)
	handler_list = []
	for old_handler in log.handlers:
		if isinstance(old_handler, (_Outputs, _File)):
			handler_list.append(old_handler)
	for old in handler_list:
		log.removeHandler(old)
		old.close()
	handler = _Outputs()
	handler.set_name(executable)
	handler.setFormatter(_Timestamped())
	log.addHandler(handler)
	file = _file_handler(executable)
	if file is not None:
		log.addHandler(file)
	log.setLevel(logging.INFO)
	return log
