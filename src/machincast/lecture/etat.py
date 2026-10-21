"""Socket d'état du binaire lecture (https://github.com/dascritch/machincast/issues/20, spec § 5.4 et § 4.6).

Le binaire publie son état sur une socket Unix, lue par l'interface. À chaque client qui se connecte, il envoie le
dernier état, puis chaque nouvel état : une ligne JSON par état, en UTF-8, avec le numéro de version du format
(VERSION). La diffusion publie à chaque changement, et au moins toutes les PUBLICATION_MINIMALE secondes pour la
progression. Le format est décrit champ par champ dans la spécification, § 5.4.

La socket est réservée au compte qui diffuse : son répertoire est en 0700, la socket en 0600. Une socket déjà
ouverte par un autre Machin lecture refuse la seconde diffusion (SocketEtatOccupee) ; une socket laissée par un
binaire arrêté brutalement est remplacée.

Chaque client a son fil : un client lent ou qui se déconnecte ne bloque jamais la diffusion.

Dans l'autre sens, un client peut envoyer des demandes, une ligne JSON par demande
(https://github.com/dascritch/machincast/issues/104) : {"commande": "interrompre", "element": E}, où E est
« sonore », « sequence » ou « evenement » (INTERRUPTIONS). Un fil par client les lit, et les garde jusqu'au pas suivant
de la diffusion (demandes). Une demande illisible, inconnue, ou plus longue que TAILLE_MAXIMALE, est ignorée et
signalée dans le journal du binaire. Seul le compte qui diffuse peut ouvrir la socket : il n'y a rien d'autre à
vérifier.
"""

import functools
import json
import logging
import os
import queue
import socket
import stat
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import TupleRow

from machincast.protection import verifier_ecriture

journal = logging.getLogger(__name__)

VERSION = 1
"""Version du format des messages : elle change quand un champ change de sens ou disparaît."""
PUBLICATION_MINIMALE = 1.0
"""Intervalle maximal entre deux messages, en secondes, pour suivre la progression."""
ATTENTE_DES_CLIENTS = 1.0
"""Délai laissé aux clients pour recevoir le dernier message, à la fermeture."""
INTERROMPRE = "interrompre"
INTERRUPTIONS = ("sonore", "sequence", "evenement")
"""Ce qu'une demande peut interrompre (https://github.com/dascritch/machincast/issues/104)."""
TAILLE_MAXIMALE = 4096
"""Octets d'une demande, au plus : au-delà, ce qui a été reçu est ignoré."""
DEMANDE_IGNOREE = "demande ignorée sur la socket d'état"


@dataclass(frozen=True)
class Demande:
	"""Une demande d'un client de la socket d'état : interrompre un élément de l'antenne."""

	element: str
	"""« sonore », « sequence » ou « evenement »."""


def demande_d_interruption(element: str) -> str:
	"""La ligne qu'un client envoie pour demander l'interruption de l'élément."""
	return json.dumps({"commande": INTERROMPRE, "element": element}) + "\n"


def lire_demande(ligne: bytes) -> Demande:
	"""Une demande reçue ; ValueError si elle est illisible ou inconnue."""
	try:
		message = json.loads(ligne.decode())
	except (UnicodeDecodeError, json.JSONDecodeError) as erreur:
		raise ValueError(f"illisible : {erreur}") from erreur
	if not isinstance(message, dict):
		raise ValueError("une demande est un objet JSON")
	commande = message.get("commande")
	element = message.get("element")
	if commande != INTERROMPRE:
		raise ValueError(f"commande inconnue : {commande}")
	if element not in INTERRUPTIONS:
		raise ValueError(f"rien à interrompre de tel : {element}")
	return Demande(str(element))


class SocketEtatOccupee(Exception):
	"""Un autre Machin lecture diffuse déjà sur cette socket."""


def est_sain(connexion: psycopg.Connection[TupleRow], sonore: int) -> bool | None:
	"""Indicateur « sain » (spec § 4.6) : fichier présent, actif, lisible, dernière lecture sans incident.

	None pour un stream, qui n'est pas testé automatiquement.
	"""
	with connexion.transaction():
		ligne = connexion.execute(
			"SELECT s.type::text, s.etat::text, s.emplacement,"
			" (SELECT f.sans_incident FROM airplay f WHERE f.sonore_id = s.id AND f.type_ligne = 'fin'"
			" ORDER BY f.horodatage DESC, f.id DESC LIMIT 1)"
			" FROM sonores s WHERE s.id = %s",
			(sonore,),
		).fetchone()
	if ligne is None:
		return False
	type_sonore, etat, emplacement, derniere = ligne
	if type_sonore == "stream":
		return None
	if (etat != "actif") or (emplacement is None) or (derniere is False):
		return False
	chemin = Path(str(emplacement))
	return (chemin.is_file()) and (os.access(chemin, os.R_OK))


def instant(valeur: datetime | None) -> str | None:
	if valeur is None:
		return None
	return valeur.isoformat()


class SocketEtat:
	"""Serveur de la socket d'état : un fil pour accepter les clients, un fil par client."""

	def __init__(self, chemin: Path) -> None:
		self.chemin = chemin
		self._serveur: socket.socket | None = None
		self._condition = threading.Condition()
		self._message = ""
		self._numero = 0
		self._fermee = False
		self._envoyes: dict[int, int] = {}
		"""Dernier message envoyé à chaque client, par identifiant de fil."""
		self._fil: threading.Thread | None = None
		self._demandes: queue.SimpleQueue[Demande] = queue.SimpleQueue()

	def demandes(self) -> list[Demande]:
		"""Les demandes reçues depuis le dernier appel, dans l'ordre d'arrivée."""
		recues = []
		while True:
			try:
				recues.append(self._demandes.get_nowait())
			except queue.Empty:
				return recues

	def ouvrir(self) -> None:
		"""Crée la socket ; lève SocketEtatOccupee si un autre Machin lecture l'a déjà ouverte."""
		verifier_ecriture(self.chemin)
		repertoire = self.chemin.parent
		repertoire.mkdir(mode=0o700, parents=True, exist_ok=True)
		os.chmod(repertoire, 0o700)
		if (self.chemin.exists()) or (self.chemin.is_symlink()):
			if self._occupee():
				raise SocketEtatOccupee(f"{self.chemin} : un autre Machin lecture diffuse déjà")
			if not stat.S_ISSOCK(self.chemin.lstat().st_mode):
				raise OSError(f"{self.chemin} existe et n'est pas une socket")
			self.chemin.unlink()  # fichier de MachinCast : socket d'état laissée par un arrêt brutal
		serveur = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		try:
			ancien = os.umask(0o177)
			try:
				serveur.bind(str(self.chemin))
			finally:
				os.umask(ancien)
			os.chmod(self.chemin, 0o600)
			serveur.listen()
			serveur.settimeout(0.2)
		except BaseException:
			# Une socket qui n'écoute pas ne reste pas ouverte (https://github.com/dascritch/machincast/issues/187).
			serveur.close()
			raise
		self._serveur = serveur
		self._fil = threading.Thread(target=self._accepter, name="socket d'état", daemon=True)
		self._fil.start()

	def _occupee(self) -> bool:
		with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as essai:
			try:
				essai.connect(str(self.chemin))
			except OSError:
				return False
		return True

	def publier(self, message: dict[str, Any]) -> None:
		"""Envoie le message à tous les clients, et à ceux qui se connecteront ensuite."""
		ligne = json.dumps({"version": VERSION, **message}, ensure_ascii=False) + "\n"
		with self._condition:
			self._message = ligne
			self._numero += 1
			self._condition.notify_all()

	def fermer(self) -> None:
		"""Laisse aux clients le temps de recevoir le dernier message, puis ferme et efface la socket."""
		if self._serveur is None:
			return
		with self._condition:
			self._condition.wait_for(
				lambda: all(envoye >= self._numero for envoye in self._envoyes.values()), ATTENTE_DES_CLIENTS
			)
			self._fermee = True
			self._condition.notify_all()
		if self._fil is not None:
			self._fil.join(ATTENTE_DES_CLIENTS)
		self._serveur.close()
		self._serveur = None
		self.chemin.unlink(missing_ok=True)  # fichier de MachinCast : socket d'état

	def _accepter(self) -> None:
		serveur = self._serveur
		while (serveur is not None) and (not self._fermee):
			try:
				client, _ = serveur.accept()
			except TimeoutError:
				continue
			except OSError:
				return
			threading.Thread(target=self._servir, args=(client,), name="client de l'état", daemon=True).start()

	def _a_envoyer(self, envoye: int) -> bool:
		return (self._numero > envoye) or (self._fermee)

	def _servir(self, client: socket.socket) -> None:
		cle = threading.get_ident()
		envoye = 0
		with client:
			client.settimeout(ATTENTE_DES_CLIENTS)
			threading.Thread(target=self._ecouter, args=(client,), name="demandes d'un client", daemon=True).start()
			while True:
				with self._condition:
					self._envoyes[cle] = envoye
					self._condition.notify_all()
					self._condition.wait_for(functools.partial(self._a_envoyer, envoye), 0.5)
					if self._numero <= envoye:
						if self._fermee:
							break
						continue
					ligne, envoye = self._message, self._numero
				try:
					client.sendall(ligne.encode())
				except OSError:
					break
			with self._condition:
				self._envoyes.pop(cle, None)
				self._condition.notify_all()

	def _ecouter(self, client: socket.socket) -> None:
		"""Les demandes du client, jusqu'à sa déconnexion ou la fermeture de la socket."""
		tampon = b""
		while not self._fermee:
			try:
				recu = client.recv(TAILLE_MAXIMALE)
			except TimeoutError:
				continue
			except OSError:
				return
			if recu == b"":
				return
			tampon += recu
			*lignes, tampon = tampon.split(b"\n")
			if len(tampon) > TAILLE_MAXIMALE:
				journal.warning(f"{DEMANDE_IGNOREE} : plus de {TAILLE_MAXIMALE} octets")
				tampon = b""
			for ligne in lignes:
				self._recevoir(ligne)

	def _recevoir(self, ligne: bytes) -> None:
		if ligne.strip() == b"":
			return
		try:
			self._demandes.put(lire_demande(ligne))
		except ValueError as erreur:
			journal.warning(f"{DEMANDE_IGNOREE} : {erreur}")
