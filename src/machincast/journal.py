"""Messages des exécutables, par la bibliothèque logging (revue de https://github.com/dascritch/machincast/pull/65).

Le code n'appelle jamais print : il obtient un journal par logging.getLogger(__name__), sous « machincast ».
Les informations (INFO) vont sur la sortie standard ; les anomalies (WARNING) et les erreurs (ERROR) sur la
sortie d'erreur. Chaque ligne commence par le nom de l'exécutable, par exemple « Machin_indexation : ».
"""

import logging
import sys

JOURNAL = "machincast"


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
	"""Prépare le journal « machincast » pour un exécutable ; sans effet cumulatif si appelé plusieurs fois."""
	journal = logging.getLogger(JOURNAL)
	for ancien in [gestionnaire for gestionnaire in journal.handlers if isinstance(gestionnaire, _Sorties)]:
		journal.removeHandler(ancien)
	gestionnaire = _Sorties()
	gestionnaire.setFormatter(logging.Formatter(f"{executable} : %(message)s"))
	journal.addHandler(gestionnaire)
	journal.setLevel(logging.INFO)
	return journal
