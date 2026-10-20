"""État du binaire lecture, lu par sa socket d'état (https://github.com/dascritch/machincast/issues/23, spec § 5.4).

L'interface ne fait que lire : à la connexion, le binaire lecture envoie son dernier état, puis chaque nouvel état,
une ligne JSON par état (machincast.lecture.etat). Sans socket, ou quand elle se ferme, le binaire lecture est
considéré à l'arrêt, et ClientEtat retente la connexion toutes les RELANCE millisecondes. Un message illisible est
signalé dans le journal et ignoré.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QLocalSocket

journal = logging.getLogger(__name__)

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
class EtatLecture:
	etat: str
	"""« diffusion », « silence » ou « arret »."""
	en_cours: SonoreAffiche | None = None
	prochain: SonoreAffiche | None = None


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


def _entier(valeur: object) -> int | None:
	if valeur is None:
		return None
	return int(str(valeur))


def _texte(valeur: object) -> str | None:
	if valeur is None:
		return None
	return str(valeur)


def _sonore(champs: dict[str, Any] | None, debut: str) -> SonoreAffiche | None:
	if champs is None:
		return None
	sain = champs.get("sain")
	return SonoreAffiche(
		sonore=int(champs["sonore"]),
		stream=champs["type"] == "stream",
		artiste=_texte(champs.get("artiste")),
		titre=_texte(champs.get("titre")),
		evenement=_texte(champs.get("evenement")),
		emplacement=_texte(champs.get("emplacement")),
		debut=_instant(champs.get(debut)),
		duree=_nombre(champs.get("duree")),
		fin_estimee=_instant(champs.get("fin_estimee")),
		progression=_nombre(champs.get("progression")),
		sain=None if sain is None else bool(sain),
		position=_nombre(champs.get("position")),
		evenement_id=_entier(champs.get("evenement_id")),
		evenement_debut=_instant(champs.get("evenement_debut")),
		evenement_fin=_instant(champs.get("evenement_fin")),
		sequence=_texte(champs.get("sequence")),
		sequence_id=_entier(champs.get("sequence_id")),
		banque=_texte(champs.get("banque")),
		banque_id=_entier(champs.get("banque_id")),
		texte_public=_texte(champs.get("texte_public")),
		coupe_par=_texte(champs.get("coupe_par")),
	)


def lire_message(ligne: str) -> EtatLecture:
	"""Un message de la socket d'état ; ValueError s'il est illisible."""
	try:
		message = json.loads(ligne)
		return EtatLecture(
			str(message["etat"]),
			_sonore(message.get("en_cours"), "debut"),
			_sonore(message.get("prochain"), "debut_estime"),
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

	def fermer(self) -> None:
		self._relance.stop()
		self._socket.abort()

	def _perdue(self, *_: object) -> None:
		self.etat_recu.emit(ARRET)
		if not self._relance.isActive():
			self._relance.start()

	def _lire(self) -> None:
		self._tampon += bytes(self._socket.readAll().data())
		*lignes, self._tampon = self._tampon.split(b"\n")
		for ligne in lignes:
			try:
				etat = lire_message(ligne.decode())
			except ValueError as erreur:
				journal.warning(f"socket d'état {self.chemin} : message illisible ignoré : {erreur}")
				continue
			self.etat_recu.emit(etat)
