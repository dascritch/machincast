"""Analyse du prochain sonore au dernier moment (https://github.com/dascritch/machincast/issues/181).

Au début de chaque sonore, Machin lecture réserve le suivant (machincast.lecture.diffusion). Si ce prochain sonore
est un fichier jamais vérifié en entier (sonores.verifie_le vide), ou dont le fichier a changé depuis sa dernière
vérification (machincast.empreinte.modifie), la diffusion lance « Machin indexation --audit-complet --sonore N »
dans un processus à part, sans fenêtre, et ne l'attend jamais : que l'indexeur plante ou n'ait pas fini, le sonore
est joué à son heure. Ses lignes vont dans le journal de Machin lecture. Un même sonore n'est pas redemandé avant
RELANCE. Un stream n'est jamais analysé, comme l'indexeur ne vérifie jamais les streams.
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from machincast.empreinte import modifie

RELANCE = timedelta(hours=1)
"""Délai avant de redemander l'analyse d'un même sonore : celle d'avant a peut-être échoué, ou le fichier changé."""


def commande_d_analyse(configuration: Path) -> list[str]:
	"""Machin indexation, lancé par le Python de la lecture, avec sa configuration, en audit complet d'un seul
	sonore : le numéro du sonore s'ajoute à la fin."""
	return [
		sys.executable,
		"-m",
		"machincast.indexation",
		"--config",
		str(configuration.expanduser().absolute()),
		"--audit-complet",
		"--sonore",
	]


def a_analyser(connexion: psycopg.Connection[TupleRow], sonore: int) -> bool:
	"""Un fichier jamais vérifié en entier, ou changé depuis ; la connexion a le rôle de la lecture."""
	ligne = connexion.execute(
		"SELECT emplacement, verifie_le, fichier_modifie_le, fichier_taille FROM sonores WHERE id = %s", (sonore,)
	).fetchone()
	# Seul un fichier a un emplacement : la base le garantit (contrainte sonores_fichier_ou_stream).
	if (ligne is None) or (ligne[0] is None):
		return False
	emplacement, verifie_le, modifie_le, taille = ligne
	if verifie_le is None:
		return True
	return modifie(Path(str(emplacement)), modifie_le, taille)


class Analyseur:
	"""Lance l'analyse d'un sonore, sans l'attendre ; se souvient des sonores demandés."""

	def __init__(self, commande: list[str], relance: timedelta = RELANCE) -> None:
		self.commande = commande
		self.relance = relance
		self._demandes: dict[int, datetime] = {}
		self._processus: list[subprocess.Popen[bytes]] = []

	def a_demander(self, sonore: int, instant: datetime) -> bool:
		"""Pas demandé depuis RELANCE."""
		derniere = self._demandes.get(sonore)
		return (derniere is None) or (instant - derniere >= self.relance)

	def lancer(self, sonore: int, instant: datetime) -> None:
		"""Lance l'analyse dans sa propre session, sans entrée : un Ctrl-C dans le terminal de la diffusion ne
		l'interrompt pas. Lève OSError si la commande ne peut pas être lancée ; la demande est retenue quand même,
		pour ne pas redire l'échec à chaque sonore."""
		# Les analyses finies sont relevées, pour ne pas laisser de processus zombie.
		self._processus = [processus for processus in self._processus if processus.poll() is None]
		self._demandes[sonore] = instant
		self._processus.append(
			subprocess.Popen([*self.commande, str(sonore)], stdin=subprocess.DEVNULL, start_new_session=True)
		)
