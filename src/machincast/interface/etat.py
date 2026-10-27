"""État du binaire lecture, lu par sa socket d'état (https://github.com/dascritch/machincast/issues/23, spec § 5.4).

À la connexion, le binaire lecture envoie son dernier état, puis chaque nouvel état, une ligne JSON par état
(machincast.lecture.etat). Dans l'autre sens, l'interface n'envoie que des demandes d'interruption manuelle (envoyer,
https://github.com/dascritch/machincast/issues/104). Sans socket, ou quand elle se ferme, le binaire lecture est
considéré à l'arrêt, et ClientEtat retente la connexion toutes les RELANCE millisecondes. Un message illisible est
signalé dans le journal et ignoré.
"""

import json
import logging
import socket
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QLocalSocket

from machincast.conversion import booleen_ou_rien, entier_ou_rien, texte_ou_rien

journal = logging.getLogger(__name__)

TAILLE_MAXIMALE = 65536
"""Octets au plus d'une ligne de la socket d'état : un message, même avec de longs chemins, en fait bien moins."""
RELANCE = 1000
"""Délai entre deux tentatives de connexion à la socket d'état, en millisecondes."""


@dataclass(frozen=True)
class SonoreAffiche:
	"""Le sonore en cours ou le prochain, tel que la socket d'état le décrit."""

	sonore: int
	stream: bool
	artiste: str | None
	titre: str | None
	evenement: str | None
	emplacement: str | None
	"""Chemin du fichier, ou adresse du stream."""
	debut: datetime | None
	"""Début du passage en cours, ou début estimé du prochain."""
	duree: float | None
	"""En secondes ; None pour un stream."""
	fin_estimee: datetime | None
	progression: float | None
	"""De 0 à 1, pour le sonore en cours ; None pour un stream."""
	sain: bool | None
	"""Pour le prochain sonore ; None pour un stream, qui n'est pas testé."""
	position: float | None = None
	"""Secondes jouées, pour le sonore en cours."""
	evenement_id: int | None = None
	evenement_priorite: str | None = None
	"""« special », « emission », « fil_musical » ou « secours » (https://github.com/dascritch/machincast/issues/228)."""
	evenement_debut: datetime | None = None
	"""Début de l'occurrence de l'événement, en heure murale ; None pour un fil musical permanent
	(https://github.com/dascritch/machincast/issues/144)."""
	evenement_fin: datetime | None = None
	"""Fin de l'occurrence ; None pour une occurrence sans fin."""
	sequence: str | None = None
	sequence_id: int | None = None
	banque: str | None = None
	banque_id: int | None = None
	texte_public: str | None = None
	"""Ce que la page publique affiche du sonore en cours, masquage appliqué."""
	coupe_par: str | None = None
	"""L'événement qui coupera le sonore en cours, à sa fin estimée (https://github.com/dascritch/machincast/issues/169)."""


@dataclass(frozen=True)
class EvenementSuivant:
	"""L'événement suivant, que Machin lecture avancerait à la demande
	(https://github.com/dascritch/machincast/issues/257). Début et fin en heure murale du poste."""

	id: int
	nom: str
	priorite: str
	debut: datetime
	fin: datetime | None


@dataclass(frozen=True)
class EtatLecture:
	etat: str
	"""« diffusion », « silence » ou « arret »."""
	en_cours: SonoreAffiche | None = None
	prochain: SonoreAffiche | None = None
	a_venir: tuple[SonoreAffiche, ...] = ()
	"""Les sonores prévus après le prochain, dans l'ordre (https://github.com/dascritch/machincast/issues/228)."""
	evenement_suivant: EvenementSuivant | None = None


ARRET = EtatLecture("arret")
"""Le binaire lecture ne publie pas : socket absente, fermée, ou dernier message avant l'arrêt."""


def _instant(valeur: object) -> datetime | None:
	if valeur is None:
		return None
	return datetime.fromisoformat(str(valeur))


def _nombre(valeur: object) -> float | None:
	if valeur is None:
		return None
	return float(str(valeur))


def _sonore(champs: dict[str, Any] | None, debut: str) -> SonoreAffiche | None:
	if champs is None:
		return None
	sain = champs.get("sain")
	return SonoreAffiche(
		sonore=int(champs["sonore"]),
		stream=champs["type"] == "stream",
		artiste=texte_ou_rien(champs.get("artiste")),
		titre=texte_ou_rien(champs.get("titre")),
		evenement=texte_ou_rien(champs.get("evenement")),
		emplacement=texte_ou_rien(champs.get("emplacement")),
		debut=_instant(champs.get(debut)),
		duree=_nombre(champs.get("duree")),
		fin_estimee=_instant(champs.get("fin_estimee")),
		progression=_nombre(champs.get("progression")),
		sain=booleen_ou_rien(sain),
		position=_nombre(champs.get("position")),
		evenement_id=entier_ou_rien(champs.get("evenement_id")),
		evenement_priorite=texte_ou_rien(champs.get("evenement_priorite")),
		evenement_debut=_instant(champs.get("evenement_debut")),
		evenement_fin=_instant(champs.get("evenement_fin")),
		sequence=texte_ou_rien(champs.get("sequence")),
		sequence_id=entier_ou_rien(champs.get("sequence_id")),
		banque=texte_ou_rien(champs.get("banque")),
		banque_id=entier_ou_rien(champs.get("banque_id")),
		texte_public=texte_ou_rien(champs.get("texte_public")),
		coupe_par=texte_ou_rien(champs.get("coupe_par")),
	)


def _evenement_suivant(champs: dict[str, Any] | None) -> EvenementSuivant | None:
	if champs is None:
		return None
	debut = _instant(champs["debut"])
	if debut is None:
		raise ValueError("un événement suivant a un début")
	return EvenementSuivant(
		id=int(champs["id"]),
		nom=str(champs["nom"]),
		priorite=str(champs["priorite"]),
		debut=debut,
		fin=_instant(champs.get("fin")),
	)


def lire_message(ligne: str) -> EtatLecture:
	"""Un message de la socket d'état ; ValueError s'il est illisible."""
	try:
		message = json.loads(ligne)
		a_venir = [_sonore(champs, "debut_estime") for champs in (message.get("a_venir")) or ([])]
		return EtatLecture(
			str(message["etat"]),
			_sonore(message.get("en_cours"), "debut"),
			_sonore(message.get("prochain"), "debut_estime"),
			tuple(sonore for sonore in a_venir if sonore is not None),
			_evenement_suivant(message.get("evenement_suivant")),
		)
	except (KeyError, TypeError, AttributeError) as erreur:
		raise ValueError(f"message incomplet : {erreur}") from erreur


class ClientEtat(QObject):
	"""Client de la socket d'état, dans la boucle d'événements de Qt : aucun fil, aucune attente."""

	etat_recu = Signal(object)
	"""Chaque EtatLecture reçu, et ARRET quand la socket manque ou se ferme."""

	def __init__(self, chemin: Path, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.chemin = chemin
		self._tampon = b""
		self._socket = QLocalSocket(self)
		self._socket.readyRead.connect(self._lire)
		self._socket.disconnected.connect(self._perdue)
		self._socket.errorOccurred.connect(self._perdue)
		self._relance = QTimer(self)
		self._relance.setSingleShot(True)
		self._relance.setInterval(RELANCE)
		self._relance.timeout.connect(self.connecter)

	def connecter(self) -> None:
		self._tampon = b""
		self._socket.abort()
		self._socket.connectToServer(str(self.chemin))

	def pid_du_lecteur(self) -> int | None:
		"""Le processus du Machin lecture qui répond sur la socket, lu par SO_PEERCRED ; None sans connexion."""
		if self._socket.state() != QLocalSocket.LocalSocketState.ConnectedState:
			return None
		# fromfd travaille sur une copie du descripteur : la fermer laisse la connexion de Qt ouverte.
		with socket.fromfd(int(self._socket.socketDescriptor()), socket.AF_UNIX, socket.SOCK_STREAM) as copie:
			identite = copie.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
		pid, _uid, _gid = struct.unpack("3i", identite)
		return int(pid)

	def envoyer(self, ligne: str) -> bool:
		"""Envoie une ligne au binaire lecture ; False sans connexion."""
		if self._socket.state() != QLocalSocket.LocalSocketState.ConnectedState:
			return False
		self._socket.write(ligne.encode())
		self._socket.flush()
		return True

	def fermer(self) -> None:
		self._relance.stop()
		self._socket.abort()

	def _perdue(self, *_: object) -> None:
		self.etat_recu.emit(ARRET)
		if not self._relance.isActive():
			self._relance.start()

	def tampon_en_attente(self) -> bytes:
		"""Ce qui a été reçu après la dernière fin de ligne."""
		return self._tampon

	def _lire(self) -> None:
		self._tampon += bytes(self._socket.readAll().data())
		*lignes, self._tampon = self._tampon.split(b"\n")
		if len(self._tampon) > TAILLE_MAXIMALE:
			# Une ligne sans fin ne fait pas grossir la mémoire de l'interface
			# (https://github.com/dascritch/machincast/issues/187).
			journal.warning(f"socket d'état {self.chemin} : message trop long ignoré, plus de {TAILLE_MAXIMALE} octets")
			self._tampon = b""
		for ligne in lignes:
			try:
				etat = lire_message(ligne.decode())
			except ValueError as erreur:
				journal.warning(f"socket d'état {self.chemin} : message illisible ignoré : {erreur}")
				continue
			self.etat_recu.emit(etat)
