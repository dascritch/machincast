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

JOURNAL = "machincast"


HORODATAGE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2} ")
"""Début d'une ligne de message : son horodatage, suivi d'une espace."""


def ligne(enregistrement: logging.LogRecord) -> str:
	"""Le message, précédé de son heure, comme sur les sorties de l'exécutable."""
	heure = datetime.fromtimestamp(enregistrement.created).astimezone().isoformat(timespec="seconds")
	return f"{heure} {enregistrement.getMessage()}"


class _Horodate(logging.Formatter):
	def format(self, record: logging.LogRecord) -> str:
		return ligne(record)


class _Sorties(logging.Handler):
	"""Écrit chaque message sur la sortie standard ou la sortie d'erreur en cours, selon son niveau.

	Les sorties sont lues à chaque message, et non à la création : un test peut les remplacer.
	"""

	def emit(self, enregistrement: logging.LogRecord) -> None:
		try:
			sortie = sys.stdout if enregistrement.levelno < logging.WARNING else sys.stderr
			sortie.write(self.format(enregistrement) + "\n")
			sortie.flush()
		except Exception:
			self.handleError(enregistrement)


def configurer(executable: str) -> logging.Logger:
	"""Prépare le journal « machincast » pour un exécutable ; sans effet cumulatif si appelé plusieurs fois. Le nom de
	l'exécutable ne figure plus dans ses lignes, que son horodatage ouvre ; il reste celui de son journal."""
	journal = logging.getLogger(JOURNAL)
	for ancien in [gestionnaire for gestionnaire in journal.handlers if isinstance(gestionnaire, _Sorties)]:
		journal.removeHandler(ancien)
	gestionnaire = _Sorties()
	gestionnaire.set_name(executable)
	gestionnaire.setFormatter(_Horodate())
	journal.addHandler(gestionnaire)
	journal.setLevel(logging.INFO)
	return journal
