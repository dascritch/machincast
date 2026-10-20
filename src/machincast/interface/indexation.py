"""Indexation lancée depuis l'interface (https://github.com/dascritch/machincast/issues/38, spec § 6 et § 8.11).

Le menu « Maintenance » de la fenêtre lance l'indexation rapide ou l'audit complet dans un processus à part,
détaché de l'interface : Machin indexation avec --fenetre, qui montre son journal dans sa propre fenêtre
(machincast.interface.journal_indexation, https://github.com/dascritch/machincast/issues/120). Fermer l'interface
ne l'arrête pas, et ne l'attend pas. L'interface suit seulement si le processus tourne encore (processus_actif).

Dans ce processus, Indexation fait tourner l'indexeur (machincast.indexation.indexeur.indexer) avec son rôle en base,
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

from machincast.base import Role, connecter
from machincast.indexation.__main__ import EXECUTABLE
from machincast.indexation.decodage import DecodeurIndisponible, Verification, verifier_fichier
from machincast.indexation.indexeur import IndexationEnCours, indexer
from machincast.indexation.verification import texte_bilan

JOURNAL_DE_L_INDEXEUR = "machincast.indexation"
"""Le journal où l'indexeur écrit ses lignes : une par sonore indexé, ses anomalies, son bilan."""

TITRES = {False: "Indexation rapide", True: "Audit complet"}
"""Nom de chaque mode, selon audit_complet ; c'est aussi le titre de son journal et de son action de menu."""
TERMINE = {False: "terminée", True: "terminé"}
LANCE = {False: "lancée", True: "lancé"}


def commande_indexation(configuration: Path | None) -> list[str]:
	"""Machin indexation, lancé par le Python de l'interface, avec la même configuration qu'elle."""
	commande = [sys.executable, "-m", "machincast.indexation"]
	if configuration is not None:
		commande += ["--config", str(configuration.expanduser().absolute())]
	return commande


def lancer_detachee(commande: list[str]) -> int | None:
	"""Lance la commande dans un processus détaché, qui survit à l'interface ; son numéro, ou None en cas d'échec."""
	programme, *arguments = commande
	lancee, numero = QProcess.startDetached(programme, arguments)
	if not lancee:
		return None
	return int(numero)


def processus_actif(numero: int) -> bool:
	"""Le processus tourne-t-il encore ? Détaché, il n'est pas l'enfant de l'interface : rien à attendre de lui.

	Un numéro qu'un processus d'un autre compte a repris (PermissionError) n'est plus celui de l'indexation.
	"""
	try:
		os.kill(numero, 0)
	except OSError:
		return False
	return True


class _Lignes(logging.Handler):
	"""Relaie les lignes que l'indexeur journalise, formées comme dans le terminal."""

	def __init__(self, relayer: SignalInstance) -> None:
		super().__init__()
		self.relayer = relayer

	def emit(self, enregistrement: logging.LogRecord) -> None:
		anomalie = enregistrement.levelno >= logging.WARNING
		self.relayer.emit(f"{EXECUTABLE} : {enregistrement.getMessage()}", anomalie)


class Indexation(QObject):
	ligne = Signal(str, bool)
	"""Une ligne de la sortie de l'indexeur, comme dans le terminal, et si c'est une anomalie (ou une erreur)."""
	termine = Signal(str)
	"""L'indexation est finie : son bilan. Émis dans le fil de la fenêtre, comme ligne."""
	_ligne = Signal(str, bool)
	_finie = Signal(str)

	def __init__(self, socket: Path, base: str, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.socket = socket
		self.base = base
		self._fil: threading.Thread | None = None
		self._arret = threading.Event()
		self._ligne.connect(self.ligne.emit)
		self._finie.connect(self._annoncer)
		# Les lignes de chaque sonore sont des informations : sans ce niveau, elles ne seraient pas écrites.
		logging.getLogger(JOURNAL_DE_L_INDEXEUR).setLevel(logging.INFO)

	def lancer(self, audit_complet: bool) -> None:
		self._fil = threading.Thread(target=self._indexer, args=(audit_complet,), name="indexation", daemon=True)
		self._fil.start()

	def en_cours(self) -> bool:
		"""L'indexation a été lancée, et sa fin n'est pas encore annoncée."""
		return self._fil is not None

	def arreter(self) -> None:
		"""Arrête l'indexation après le fichier en cours, et attend qu'elle le soit."""
		self._arret.set()
		if self._fil is not None:
			self._fil.join()
		self._fil = None

	def _annoncer(self, bilan: str) -> None:
		self._fil = None
		self.termine.emit(bilan)

	def _indexer(self, audit_complet: bool) -> None:
		indexeur = logging.getLogger(JOURNAL_DE_L_INDEXEUR)
		lignes = _Lignes(self._ligne)
		indexeur.addHandler(lignes)
		try:
			with connecter(self.socket, self.base, Role.INDEXATION) as connexion:
				bilan = indexer(connexion, audit_complet, _verifier_fichier, self._arret)
			# Le bilan, comme Machin indexation l'écrit à la fin.
			indexeur.info(texte_bilan(bilan))
			mode, _deux_points, detail = texte_bilan(bilan).partition(" : ")
			texte = f"{mode.capitalize()} {TERMINE[audit_complet]} : {detail}."
		except (DecodeurIndisponible, IndexationEnCours, psycopg.Error) as erreur:
			indexeur.error(f"indexation impossible : {erreur}")
			texte = f"Indexation impossible : {erreur} ; les sonores déjà vérifiés le restent."
		finally:
			indexeur.removeHandler(lignes)
		self._finie.emit(texte)


def _verifier_fichier(chemin: Path) -> Verification:
	"""Le décodage de l'indexeur, appelé par son nom : les scénarios le remplacent."""
	return verifier_fichier(chemin)
