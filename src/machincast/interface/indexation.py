"""Indexation lancée depuis l'interface (https://github.com/dascritch/machincast/issues/38, spec § 6 et § 8.11).

Le menu « Maintenance » de la fenêtre lance l'indexation rapide ou l'audit complet, comme Machin indexation : avec son
code (machincast.indexation.indexeur.indexer) et son rôle en base, dans un fil à part, pour que l'interface reste
utilisable. Une seule indexation tourne à la fois. Sa fin s'annonce (termine) avec le bilan et les anomalies que
l'indexeur a signalées, fichier par fichier ; un décodeur absent ou une base injoignable l'interrompt, et les sonores
déjà vérifiés le restent. Fermer la fenêtre attend la fin de l'indexation en cours (arreter).
"""

import logging
import threading
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QObject, Signal

from machincast.base import Role, connecter
from machincast.indexation.decodage import DecodeurIndisponible, Verification, verifier_fichier
from machincast.indexation.indexeur import indexer
from machincast.indexation.verification import texte_bilan

journal = logging.getLogger(__name__)

TITRES = {False: "Indexation rapide", True: "Audit complet"}
"""Nom de chaque mode, selon audit_complet ; c'est aussi le titre de son rapport et de son action de menu."""
TERMINE = {False: "terminée", True: "terminé"}


class _Anomalies(logging.Handler):
	"""Retient les anomalies que l'indexeur journalise, dans le fil de l'indexation seulement.

	L'indexeur ne journalise que des anomalies (warning) : son bilan, l'interface le compose elle-même.
	"""

	def __init__(self, fil: int) -> None:
		super().__init__()
		self.fil = fil
		self.messages: list[str] = []

	def emit(self, enregistrement: logging.LogRecord) -> None:
		if enregistrement.thread == self.fil:
			self.messages.append(enregistrement.getMessage())


class Indexation(QObject):
	termine = Signal(str, str, list)
	"""Une indexation est finie : son titre, son bilan, ses anomalies (list[str]). Émis dans le fil de l'interface."""
	_finie = Signal(str, str, list)

	def __init__(self, connexion: psycopg.Connection[TupleRow], parent: QObject | None = None) -> None:
		"""connexion : celle de l'interface, dont l'indexation reprend le socket et la base."""
		super().__init__(parent)
		self.socket = Path(str(connexion.info.host))
		self.base = connexion.info.dbname
		self._fil: threading.Thread | None = None
		self._finie.connect(self._annoncer)

	def lancer(self, audit_complet: bool) -> None:
		"""Lance l'indexation en tâche de fond ; une seule à la fois, la fenêtre y veille."""
		self._fil = threading.Thread(target=self._indexer, args=(audit_complet,), name="indexation", daemon=True)
		self._fil.start()

	def en_cours(self) -> bool:
		"""Une indexation a été lancée, et sa fin n'est pas encore annoncée."""
		return self._fil is not None

	def arreter(self) -> None:
		"""Attend la fin de l'indexation en cours ; la fenêtre se ferme, sa fin ne s'annonce plus."""
		if self._fil is not None:
			self._fil.join()
		self._fil = None

	def _annoncer(self, titre: str, bilan: str, anomalies: list[str]) -> None:
		if self._fil is None:
			# Annonce arrivée après arreter : la fenêtre est fermée.
			return
		self._fil = None
		self.termine.emit(titre, bilan, anomalies)

	def _indexer(self, audit_complet: bool) -> None:
		anomalies = _Anomalies(threading.get_ident())
		indexeur = logging.getLogger("machincast.indexation")
		indexeur.addHandler(anomalies)
		try:
			with connecter(self.socket, self.base, Role.INDEXATION) as connexion:
				bilan = indexer(connexion, audit_complet, _verifier_fichier)
			mode, _deux_points, detail = texte_bilan(bilan).partition(" : ")
			texte = f"{mode.capitalize()} {TERMINE[audit_complet]} : {detail}."
		except (DecodeurIndisponible, psycopg.Error) as erreur:
			journal.error(f"indexation impossible : {erreur}")
			texte = f"Indexation impossible : {erreur} ; les sonores déjà vérifiés le restent."
		finally:
			indexeur.removeHandler(anomalies)
		self._finie.emit(TITRES[audit_complet], texte, anomalies.messages)


def _verifier_fichier(chemin: Path) -> Verification:
	"""Le décodage de l'indexeur, appelé par son nom : les scénarios le remplacent."""
	return verifier_fichier(chemin)
