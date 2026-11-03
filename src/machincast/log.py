"""Messages des exécutables, par la bibliothèque logging (revue de https://github.com/dascritch/machincast/pull/65).

Le code n'appelle jamais print : il obtient un journal par logging.getLogger(__name__), sous « machincast ».
Les informations (INFO) vont sur la sortie standard ; les anomalies (WARNING) et les erreurs (ERROR) sur la
sortie d'erreur. Chaque ligne commence par l'heure de son message, en ISO 8601, à la seconde, avec le décalage horaire
du poste, par exemple « 2026-10-23T07:55:19+02:00 à l'antenne : … » ; elle remplace le nom de l'exécutable, qui la
précédait (https://github.com/dascritch/machincast/issues/253).
"""

import logging
import re
import sys
from datetime import datetime

LOG = "machincast"


TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2} ")
"""Début d'une ligne de message : son horodatage, suivi d'une espace."""


def line(saving: logging.LogRecord) -> str:
	"""Le message, précédé de son heure, comme sur les sorties de l'exécutable."""
	hour = datetime.fromtimestamp(saving.created).astimezone().isoformat(timespec="seconds")
	return f"{hour} {saving.getMessage()}"


class _Timestamped(logging.Formatter):
	def format(self, record: logging.LogRecord) -> str:
		return line(record)


class _Outputs(logging.Handler):
	"""Écrit chaque message sur la sortie standard ou la sortie d'erreur en cours, selon son niveau.

	Les sorties sont lues à chaque message, et non à la création : un test peut les remplacer.
	"""

	def emit(self, saving: logging.LogRecord) -> None:
		try:
			output = sys.stdout if saving.levelno < logging.WARNING else sys.stderr
			output.write(self.format(saving) + "\n")
			output.flush()
		except Exception:
			self.handleError(saving)


def configure(executable: str) -> logging.Logger:
	"""Prépare le journal « machincast » pour un exécutable ; sans effet cumulatif si appelé plusieurs fois. Le nom de
	l'exécutable ne figure plus dans ses lignes, que son horodatage ouvre ; il reste celui de son journal."""
	log = logging.getLogger(LOG)
	for old in [handler for handler in log.handlers if isinstance(handler, _Outputs)]:
		log.removeHandler(old)
	handler = _Outputs()
	handler.set_name(executable)
	handler.setFormatter(_Timestamped())
	log.addHandler(handler)
	log.setLevel(logging.INFO)
	return log
