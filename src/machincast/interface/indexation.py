"""Indexation lancée depuis l'interface (https://github.com/dascritch/machincast/issues/38, spec § 6 et § 8.11).

Le menu « Maintenance » de la fenêtre lance l'indexation rapide ou l'audit complet, comme Machin indexation : avec son
code (machincast.indexation.indexeur.indexer) et son rôle en base, dans un fil à part, pour que l'interface reste
utilisable. Une seule indexation tourne à la fois. Chaque ligne que l'indexeur écrirait dans le terminal s'annonce
aussitôt (ligne), pour le journal de l'indexation (machincast.interface.journal_indexation,
https://github.com/dascritch/machincast/issues/120) ; sa fin s'annonce avec son bilan (termine). Un décodeur absent ou
une base injoignable l'interrompt, et les sonores déjà vérifiés le restent. Fermer la fenêtre attend la fin de
l'indexation en cours (arreter).
"""

import logging
import threading
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QObject, Signal, SignalInstance

from machincast.base import Role, connecter
from machincast.indexation.__main__ import EXECUTABLE
from machincast.indexation.decodage import DecodeurIndisponible, Verification, verifier_fichier
from machincast.indexation.indexeur import indexer
from machincast.indexation.verification import texte_bilan

JOURNAL_DE_L_INDEXEUR = "machincast.indexation"
"""Le journal où l'indexeur écrit ses lignes : une par sonore indexé, ses anomalies, son bilan."""

TITRES = {False: "Indexation rapide", True: "Audit complet"}
"""Nom de chaque mode, selon audit_complet ; c'est aussi le titre de son journal et de son action de menu."""
TERMINE = {False: "terminée", True: "terminé"}


class _Lignes(logging.Handler):
	"""Relaie les lignes que l'indexeur journalise, dans le fil de l'indexation seulement."""

	def __init__(self, fil: int, relayer: SignalInstance) -> None:
		super().__init__()
		self.fil = fil
		self.relayer = relayer

	def emit(self, enregistrement: logging.LogRecord) -> None:
		if enregistrement.thread == self.fil:
			anomalie = enregistrement.levelno >= logging.WARNING
			self.relayer.emit(f"{EXECUTABLE} : {enregistrement.getMessage()}", anomalie)


class Indexation(QObject):
	ligne = Signal(str, bool)
	"""Une ligne de la sortie de l'indexeur, comme dans le terminal, et si c'est une anomalie (ou une erreur)."""
	termine = Signal(str)
	"""Une indexation est finie : son bilan. Émis dans le fil de l'interface, comme ligne."""
	_ligne = Signal(str, bool)
	_finie = Signal(str)

	def __init__(self, connexion: psycopg.Connection[TupleRow], parent: QObject | None = None) -> None:
		"""connexion : celle de l'interface, dont l'indexation reprend le socket et la base."""
		super().__init__(parent)
		self.socket = Path(str(connexion.info.host))
		self.base = connexion.info.dbname
		self._fil: threading.Thread | None = None
		self._ligne.connect(self._relayer)
		self._finie.connect(self._annoncer)
		# Les lignes de chaque sonore sont des informations : sans ce niveau, elles ne seraient pas écrites.
		logging.getLogger(JOURNAL_DE_L_INDEXEUR).setLevel(logging.INFO)

	def lancer(self, audit_complet: bool) -> None:
		"""Lance l'indexation en tâche de fond ; une seule à la fois, la fenêtre y veille."""
		self._fil = threading.Thread(target=self._indexer, args=(audit_complet,), name="indexation", daemon=True)
		self._fil.start()

	def en_cours(self) -> bool:
		"""Une indexation a été lancée, et sa fin n'est pas encore annoncée."""
		return self._fil is not None

	def arreter(self) -> None:
		"""Attend la fin de l'indexation en cours, avant que la fenêtre se ferme."""
		if self._fil is not None:
			self._fil.join()
		self._fil = None

	def _relayer(self, texte: str, anomalie: bool) -> None:
		self.ligne.emit(texte, anomalie)

	def _annoncer(self, bilan: str) -> None:
		self._fil = None
		self.termine.emit(bilan)

	def _indexer(self, audit_complet: bool) -> None:
		indexeur = logging.getLogger(JOURNAL_DE_L_INDEXEUR)
		lignes = _Lignes(threading.get_ident(), self._ligne)
		indexeur.addHandler(lignes)
		try:
			with connecter(self.socket, self.base, Role.INDEXATION) as connexion:
				bilan = indexer(connexion, audit_complet, _verifier_fichier)
			# Le bilan, comme Machin indexation l'écrit à la fin.
			indexeur.info(texte_bilan(bilan))
			mode, _deux_points, detail = texte_bilan(bilan).partition(" : ")
			texte = f"{mode.capitalize()} {TERMINE[audit_complet]} : {detail}."
		except (DecodeurIndisponible, psycopg.Error) as erreur:
			indexeur.error(f"indexation impossible : {erreur}")
			texte = f"Indexation impossible : {erreur} ; les sonores déjà vérifiés le restent."
		finally:
			indexeur.removeHandler(lignes)
		self._finie.emit(texte)


def _verifier_fichier(chemin: Path) -> Verification:
	"""Le décodage de l'indexeur, appelé par son nom : les scénarios le remplacent."""
	return verifier_fichier(chemin)
