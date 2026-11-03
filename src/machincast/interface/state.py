"""État du binaire lecture, lu par sa socket d'état (https://github.com/dascritch/machincast/issues/23, spec § 5.4).

À la connexion, le binaire lecture envoie son dernier état, puis chaque nouvel état, une ligne JSON par état
(machincast.player.state). Dans l'autre sens, l'interface n'envoie que des demandes d'interruption manuelle (envoyer,
https://github.com/dascritch/machincast/issues/104). Sans socket, ou quand elle se ferme, le binaire lecture est
considéré à l'arrêt, et StateClient retente la connexion toutes les RELANCE millisecondes. Un message illisible est
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

from machincast.conversion import boolean_or_none, integer_or_none, text_or_none

log = logging.getLogger(__name__)

MAXIMAL_SIZE = 65536
"""Octets au plus d'une ligne de la socket d'état : un message, même avec de longs chemins, en fait bien moins."""
RESTARTED = 1000
"""Délai entre deux tentatives de connexion à la socket d'état, en millisecondes."""


@dataclass(frozen=True)
class DisplayedSound:
	"""Le sonore en cours ou le prochain, tel que la socket d'état le décrit."""

	sound: int
	stream: bool
	artist: str | None
	title: str | None
	event: str | None
	location: str | None
	"""Chemin du fichier, ou adresse du stream."""
	start: datetime | None
	"""Début du passage en cours, ou début estimé du prochain."""
	duration: float | None
	"""En secondes ; None pour un stream."""
	estimated_end: datetime | None
	progress: float | None
	"""De 0 à 1, pour le sonore en cours ; None pour un stream."""
	healthy: bool | None
	"""Pour le prochain sonore ; None pour un stream, qui n'est pas testé."""
	position: float | None = None
	"""Secondes jouées, pour le sonore en cours."""
	id_event: int | None = None
	priority_event: str | None = None
	"""« special », « emission », « fil_musical » ou « secours » (https://github.com/dascritch/machincast/issues/228)."""
	start_event: datetime | None = None
	"""Début de l'occurrence de l'événement, en heure murale ; None pour un fil musical permanent
	(https://github.com/dascritch/machincast/issues/144)."""
	end_event: datetime | None = None
	"""Fin de l'occurrence ; None pour une occurrence sans fin."""
	sequence: str | None = None
	sequence_id: int | None = None
	bank: str | None = None
	id_bank: int | None = None
	public_text: str | None = None
	"""Ce que la page publique affiche du sonore en cours, masquage appliqué."""
	cut_by: str | None = None
	"""L'événement qui coupera le sonore en cours, à sa fin estimée (https://github.com/dascritch/machincast/issues/169)."""


@dataclass(frozen=True)
class FollowingEvent:
	"""L'événement suivant, que Machin player avancerait à la demande
	(https://github.com/dascritch/machincast/issues/257). Début et fin en heure murale du poste."""

	id: int
	name: str
	priority: str
	start: datetime
	end: datetime | None


@dataclass(frozen=True)
class PlaybackState:
	state: str
	"""« diffusion », « blanc » ou « arret »."""
	ongoing: DisplayedSound | None = None
	next_: DisplayedSound | None = None
	upcoming: tuple[DisplayedSound, ...] = ()
	"""Les sonores prévus après le prochain, dans l'ordre (https://github.com/dascritch/machincast/issues/228)."""
	following_event: FollowingEvent | None = None


STOP = PlaybackState("stopped")
"""Le binaire lecture ne publie pas : socket absente, fermée, ou dernier message avant l'arrêt."""


def _instant(value: object) -> datetime | None:
	if value is None:
		return None
	return datetime.fromisoformat(str(value))


def _count(value: object) -> float | None:
	if value is None:
		return None
	return float(str(value))


def _sound(fields: dict[str, Any] | None, start: str) -> DisplayedSound | None:
	if fields is None:
		return None
	healthy = fields.get("healthy")
	return DisplayedSound(
		sound=int(fields["sound_id"]),
		stream=fields["type"] == "stream",
		artist=text_or_none(fields.get("artist")),
		title=text_or_none(fields.get("title")),
		event=text_or_none(fields.get("event")),
		location=text_or_none(fields.get("location")),
		start=_instant(fields.get(start)),
		duration=_count(fields.get("duration")),
		estimated_end=_instant(fields.get("estimated_end")),
		progress=_count(fields.get("progress")),
		healthy=boolean_or_none(healthy),
		position=_count(fields.get("position")),
		id_event=integer_or_none(fields.get("event_id")),
		priority_event=text_or_none(fields.get("event_priority")),
		start_event=_instant(fields.get("event_start")),
		end_event=_instant(fields.get("event_end")),
		sequence=text_or_none(fields.get("sequence")),
		sequence_id=integer_or_none(fields.get("sequence_id")),
		bank=text_or_none(fields.get("bank")),
		id_bank=integer_or_none(fields.get("bank_id")),
		public_text=text_or_none(fields.get("public_text")),
		cut_by=text_or_none(fields.get("cut_by")),
	)


def _following_event(fields: dict[str, Any] | None) -> FollowingEvent | None:
	if fields is None:
		return None
	start = _instant(fields["start"])
	if start is None:
		raise ValueError("un événement suivant a un début")
	return FollowingEvent(
		id=int(fields["id"]),
		name=str(fields["name"]),
		priority=str(fields["priority"]),
		start=start,
		end=_instant(fields.get("end")),
	)


def read_message(line: str) -> PlaybackState:
	"""Un message de la socket d'état ; ValueError s'il est illisible."""
	try:
		message = json.loads(line)
		upcoming = [_sound(fields, "estimated_start") for fields in (message.get("upcoming")) or ([])]
		return PlaybackState(
			str(message["state"]),
			_sound(message.get("current"), "start"),
			_sound(message.get("next"), "estimated_start"),
			tuple(sound for sound in upcoming if sound is not None),
			_following_event(message.get("next_event")),
		)
	except (KeyError, TypeError, AttributeError) as error:
		raise ValueError(f"message incomplet : {error}") from error


class StateClient(QObject):
	"""Client de la socket d'état, dans la boucle d'événements de Qt : aucun fil, aucune attente."""

	received_state = Signal(object)
	"""Chaque EtatLecture reçu, et ARRET quand la socket manque ou se ferme."""

	def __init__(self, path: Path, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.path = path
		self._buffer = b""
		self._socket = QLocalSocket(self)
		self._socket.readyRead.connect(self._read)
		self._socket.disconnected.connect(self._lost)
		self._socket.errorOccurred.connect(self._lost)
		self._restarted = QTimer(self)
		self._restarted.setSingleShot(True)
		self._restarted.setInterval(RESTARTED)
		self._restarted.timeout.connect(self.open_connection)

	def open_connection(self) -> None:
		self._buffer = b""
		self._socket.abort()
		self._socket.connectToServer(str(self.path))

	def player_pid(self) -> int | None:
		"""Le processus du Machin player qui répond sur la socket, lu par SO_PEERCRED ; None sans connexion."""
		if self._socket.state() != QLocalSocket.LocalSocketState.ConnectedState:
			return None
		# fromfd travaille sur une copie du descripteur : la fermer laisse la connexion de Qt ouverte.
		with socket.fromfd(int(self._socket.socketDescriptor()), socket.AF_UNIX, socket.SOCK_STREAM) as copies:
			identity = copies.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
		pid, _uid, _gid = struct.unpack("3i", identity)
		return int(pid)

	def send(self, line: str) -> bool:
		"""Envoie une ligne au binaire lecture ; False sans connexion."""
		if self._socket.state() != QLocalSocket.LocalSocketState.ConnectedState:
			return False
		self._socket.write(line.encode())
		self._socket.flush()
		return True

	def shut_down(self) -> None:
		self._restarted.stop()
		self._socket.abort()

	def _lost(self, *_: object) -> None:
		self.received_state.emit(STOP)
		if not self._restarted.isActive():
			self._restarted.start()

	def buffer_in_waiting(self) -> bytes:
		"""Ce qui a été reçu après la dernière fin de ligne."""
		return self._buffer

	def _read(self) -> None:
		self._buffer += bytes(self._socket.readAll().data())
		*lines, self._buffer = self._buffer.split(b"\n")
		if len(self._buffer) > MAXIMAL_SIZE:
			# Une ligne sans fin ne fait pas grossir la mémoire de l'interface
			# (https://github.com/dascritch/machincast/issues/187).
			log.warning(f"socket d'état {self.path} : message trop long ignoré, plus de {MAXIMAL_SIZE} octets")
			self._buffer = b""
		for line in lines:
			try:
				state = read_message(line.decode())
			except ValueError as error:
				log.warning(f"socket d'état {self.path} : message illisible ignoré : {error}")
				continue
			self.received_state.emit(state)
