"""Vérification immédiate des fichiers ajoutés par l'interface (https://github.com/dascritch/machincast/issues/30).

Un fichier ajouté entre en base à l'état aperçu (machincast.interface.ajout) ; l'indexeur le décode aussitôt, en tâche
de fond, avec son propre code (machincast.indexation.verification.verifier_sonores) et son rôle en base : l'interface
reste utilisable pendant ce temps. Les vérifications demandées passent l'une après l'autre ; chacune se conclut par
une annonce (termine), avec l'état de chaque sonore. Si l'indexeur ne sait pas décoder un format, ou si la base est
injoignable, les sonores restent en aperçu : la prochaine indexation les reprendra.

Fermer la fenêtre attend la fin de la vérification en cours (arreter).
"""

import logging
import threading
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QObject, Signal

from machincast.base import Role, connecter
from machincast.indexation.decodage import DecodeurIndisponible, Verification, verifier_fichier
from machincast.indexation.verification import verifier_sonores
from machincast.interface import affichage
from machincast.interface.listes import ETATS

journal = logging.getLogger(__name__)

APRES_ECHEC = "la prochaine indexation reprendra les fichiers en aperçu."


class Verificateur(QObject):
	termine = Signal(str)
	"""Une vérification est finie : ce qu'en dit la barre d'état. Émis dans le fil de l'interface."""
	_finie = Signal(str)
	"""Émis par le fil de la vérification ; termine le relaie dans le fil de l'interface."""

	def __init__(self, connexion: psycopg.Connection[TupleRow], parent: QObject | None = None) -> None:
		"""connexion : celle de l'interface, dont la vérification reprend le socket et la base."""
		super().__init__(parent)
		self.socket = Path(str(connexion.info.host))
		self.base = connexion.info.dbname
		self._attente: list[list[int]] = []
		self._verrou = threading.Lock()
		self._fil: threading.Thread | None = None
		self._annoncer_restant = 0
		"""Vérifications demandées dont la fin n'est pas encore annoncée ; tenu dans le fil de l'interface."""
		self._finie.connect(self._annoncer)

	def verifier(self, identifiants: list[int]) -> None:
		"""Demande la vérification de ces sonores, après celles déjà demandées."""
		if identifiants == []:
			return
		self._annoncer_restant += 1
		with self._verrou:
			self._attente.append(identifiants)
			if (self._fil is not None) and (self._fil.is_alive()):
				return
			self._fil = threading.Thread(target=self._travailler, name="vérification", daemon=True)
			self._fil.start()

	def en_cours(self) -> bool:
		"""Une vérification demandée n'a pas encore annoncé sa fin."""
		return self._annoncer_restant > 0

	def _annoncer(self, texte: str) -> None:
		self._annoncer_restant -= 1
		self.termine.emit(texte)

	def arreter(self) -> None:
		"""Attend la fin des vérifications demandées ; la fenêtre se ferme, leur fin ne s'annonce plus."""
		fil = self._fil
		if fil is not None:
			fil.join()
		self._annoncer_restant = 0

	def _travailler(self) -> None:
		while True:
			with self._verrou:
				if self._attente == []:
					return
				identifiants = self._attente.pop(0)
			self._finie.emit(self._verifier(identifiants))

	def _verifier(self, identifiants: list[int]) -> str:
		try:
			with connecter(self.socket, self.base, Role.INDEXATION) as connexion:
				verifier_sonores(connexion, _verifier_fichier, identifiants=identifiants)
				with connexion.transaction():
					lignes = connexion.execute(
						"SELECT artiste, titre, emplacement, etat::text FROM sonores WHERE id = ANY(%s) ORDER BY id",
						(identifiants,),
					).fetchall()
		except (DecodeurIndisponible, psycopg.Error) as erreur:
			journal.error(f"vérification des fichiers ajoutés impossible : {erreur}")
			return f"Vérification impossible : {erreur} ; {APRES_ECHEC}"
		etats = [
			f"{affichage.nom_du_sonore(artiste, titre, emplacement, None)}, {ETATS.get(str(etat), str(etat))}"
			for artiste, titre, emplacement, etat in lignes
		]
		return f"Vérification terminée : {' ; '.join(etats)}."


def _verifier_fichier(chemin: Path) -> Verification:
	"""Le décodage de l'indexeur, appelé par son nom : les scénarios le remplacent."""
	return verifier_fichier(chemin)
