"""Socket d'état du binaire lecture (https://github.com/dascritch/machincast/issues/20, spec § 5.4 et § 4.6).

Le binaire publie son état sur une socket Unix, lue par l'interface. À chaque client qui se connecte, il envoie le
dernier état, puis chaque nouvel état : une ligne JSON par état, en UTF-8, avec le numéro de version du format
(VERSION). La diffusion publie à chaque changement, et au moins toutes les MINIMAL_PUBLICATION secondes pour la
progression. Le format est décrit champ par champ dans la spécification, § 5.4.

La socket est réservée au compte qui diffuse : son répertoire est en 0700, la socket en 0600. Une socket déjà
ouverte par un autre Machin player refuse la seconde diffusion (BusyStateSocket) ; une socket laissée par un
binaire arrêté brutalement est remplacée.

Chaque client a son fil : un client lent ou qui se déconnecte ne bloque jamais la diffusion.

Dans l'autre sens, un client peut envoyer des demandes, une ligne JSON par demande
(https://github.com/dascritch/machincast/issues/104) : {"command": "interrupt", "item": E}, où E est
« sound », « sequence » ou « event » (INTERRUPTIONS) ; {"command": "reread_grid"}, après un changement de la
grille qui doit valoir aussitôt, comme une session sautée (https://github.com/dascritch/machincast/issues/273) ;
{"command": "advance", "event": N}, pour que l'événement suivant annoncé, d'identifiant N, commence aussitôt
(https://github.com/dascritch/machincast/issues/257) ; {"command": "cut_by_fallback", "event": N}, pour
couper l'antenne par l'événement de secours N, et {"command": "cut_by_feed", "feed": N}, par le stream qui
suit le feed N (https://github.com/dascritch/machincast/issues/323). Un fil
par client les lit, et les garde jusqu'au pas suivant
de la diffusion (demandes). Une demande illisible, inconnue, ou plus longue que MAXIMAL_SIZE, est ignorée et
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

from machincast.i18n import _
from machincast.protection import check_writing

log = logging.getLogger(__name__)

VERSION = 3
"""Version du format des messages : elle change quand un champ change de sens ou disparaît."""
MINIMAL_PUBLICATION = 1.0
"""Intervalle maximal entre deux messages, en secondes, pour suivre la progression."""
CLIENTS_WAITING = 1.0
"""Délai laissé aux clients pour recevoir le dernier message, à la fermeture."""
INTERRUPT = "interrupt"
REREAD_GRID = "reread_grid"
ADVANCE = "advance"
"""Avancer l'événement suivant, nommé par son identifiant (https://github.com/dascritch/machincast/issues/257)."""
CUT_BY_FALLBACK = "cut_by_fallback"
CUT_BY_FEED = "cut_by_feed"
"""Couper l'antenne par un événement de secours, ou par un feed (https://github.com/dascritch/machincast/issues/323)."""
INTERRUPTIONS = ("sound", "sequence", "event")
"""Ce qu'une demande peut interrompre (https://github.com/dascritch/machincast/issues/104)."""
MAXIMAL_SIZE = 4096
"""Octets d'une demande, au plus : au-delà, ce qui a été reçu est ignoré."""
IGNORED_REQUEST = _("request ignored on the state socket")


@dataclass(frozen=True)
class Request:
	"""Une demande d'un client de la socket d'état : interrompre un élément de l'antenne, ou relire la grille."""

	item: str = ""
	"""Pour une interruption : « sonore », « sequence » ou « evenement »."""
	command: str = INTERRUPT
	event: int | None = None
	"""Pour une avance : l'identifiant de l'événement suivant attendu ; pour une coupure par le secours, celui du
	secours."""
	feed: int | None = None
	"""Pour une coupure par un feed : son identifiant."""


def interruption_request(item: str) -> str:
	"""La ligne qu'un client envoie pour demander l'interruption de l'élément."""
	return json.dumps({"command": INTERRUPT, "item": item}) + "\n"


def request_reread_grid() -> str:
	"""La ligne qu'un client envoie après un changement de la grille qui doit valoir aussitôt."""
	return json.dumps({"command": REREAD_GRID}) + "\n"


def advance_request(event: int) -> str:
	"""La ligne qu'un client envoie pour avancer l'événement suivant, qu'il a lu dans l'état publié
	(https://github.com/dascritch/machincast/issues/257)."""
	return json.dumps({"command": ADVANCE, "event": event}) + "\n"


def cutoff_request_by_fallback(event: int) -> str:
	"""La ligne qu'un client envoie pour couper l'antenne par cet événement de secours
	(https://github.com/dascritch/machincast/issues/323)."""
	return json.dumps({"command": CUT_BY_FALLBACK, "event": event}) + "\n"


def cutoff_request_by_feed(feed: int) -> str:
	"""La ligne qu'un client envoie pour couper l'antenne par le stream qui suit ce feed."""
	return json.dumps({"command": CUT_BY_FEED, "feed": feed}) + "\n"


def _identifier(message: dict[str, Any], key: str) -> int:
	"""L'identifiant que nomme la demande, et rien d'autre que sa commande ; ValueError sinon."""
	value = message.get(key)
	# Un booléen est un entier pour Python : il n'est pas un identifiant.
	if (set(message) != {"command", key}) or (not isinstance(value, int)) or (isinstance(value, bool)):
		raise ValueError(
			_("the request “{message}” names an identifier, “{key}”, and nothing else").format(
				message=message.get("command"), key=key
			)
		)
	return value


def read_request(line: bytes) -> Request:
	"""Une demande reçue ; ValueError si elle est illisible ou inconnue."""
	try:
		message = json.loads(line.decode())
	except (UnicodeDecodeError, json.JSONDecodeError) as error:
		raise ValueError(_("unreadable: {error}").format(error=error)) from error
	if not isinstance(message, dict):
		raise ValueError(_("a request is a JSON object"))
	command = message.get("command")
	item = message.get("item")
	if (command == REREAD_GRID) and (set(message) == {"command"}):
		return Request(command=REREAD_GRID)
	if command == ADVANCE:
		event = message.get("event")
		# Un booléen est un entier pour Python : il n'est pas un identifiant.
		if (set(message) != {"command", "event"}) or (not isinstance(event, int)) or (isinstance(event, bool)):
			raise ValueError(_("an advance names the identifier of the next event, and nothing else"))
		return Request(command=ADVANCE, event=event)
	if command == CUT_BY_FALLBACK:
		return Request(command=CUT_BY_FALLBACK, event=_identifier(message, "event"))
	if command == CUT_BY_FEED:
		return Request(command=CUT_BY_FEED, feed=_identifier(message, "feed"))
	if command != INTERRUPT:
		raise ValueError(_("unknown command: {command}").format(command=command))
	if item not in INTERRUPTIONS:
		raise ValueError(_("nothing of that kind to interrupt: {item}").format(item=item))
	return Request(str(item))


class BusyStateSocket(Exception):
	"""Un autre Machin player diffuse déjà sur cette socket."""


def is_healthy(connection: psycopg.Connection[TupleRow], sound: int) -> bool | None:
	"""Indicateur « sain » (spec § 4.6) : fichier présent, actif, lisible, dernière lecture sans incident.

	None pour un stream, qui n'est pas testé automatiquement.
	"""
	with connection.transaction():
		line = connection.execute(
			"SELECT s.type::text, s.state::text, s.location,"
			" (SELECT f.without_incident FROM airplay f WHERE f.sound_id = s.id AND f.line_type = 'end'"
			" ORDER BY f.logged_at DESC, f.id DESC LIMIT 1)"
			" FROM sounds s WHERE s.id = %s",
			(sound,),
		).fetchone()
	if line is None:
		return False
	sound_type, state, location, last = line
	if sound_type == "stream":
		return None
	if (state != "active") or (location is None) or (last is False):
		return False
	path = Path(str(location))
	return (path.is_file()) and (os.access(path, os.R_OK))


def instant(value: datetime | None) -> str | None:
	if value is None:
		return None
	return value.isoformat()


class StateSocket:
	"""Serveur de la socket d'état : un fil pour accepter les clients, un fil par client."""

	def __init__(self, path: Path) -> None:
		self.path = path
		self._server: socket.socket | None = None
		self._condition = threading.Condition()
		self._message = ""
		self._number = 0
		self._closed = False
		self._sent_list: dict[int, int] = {}
		"""Dernier message envoyé à chaque client, par identifiant de fil."""
		self._feed: threading.Thread | None = None
		self._requests: queue.SimpleQueue[Request] = queue.SimpleQueue()

	def requests(self) -> list[Request]:
		"""Les demandes reçues depuis le dernier appel, dans l'ordre d'arrivée."""
		received_list = []
		while True:
			try:
				received_list.append(self._requests.get_nowait())
			except queue.Empty:
				return received_list

	def open_(self) -> None:
		"""Crée la socket ; lève BusyStateSocket si un autre Machin player l'a déjà ouverte."""
		check_writing(self.path)
		directory = self.path.parent
		directory.mkdir(mode=0o700, parents=True, exist_ok=True)
		os.chmod(directory, 0o700)
		if (self.path.exists()) or (self.path.is_symlink()):
			if self._busy():
				raise BusyStateSocket(_("{path}: another Machin player is already broadcasting").format(path=self.path))
			if not stat.S_ISSOCK(self.path.lstat().st_mode):
				raise OSError(_("{path} exists and is not a socket").format(path=self.path))
			self.path.unlink()  # fichier de MachinCast : socket d'état laissée par un arrêt brutal
		server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		try:
			old = os.umask(0o177)
			try:
				server.bind(str(self.path))
			finally:
				os.umask(old)
			os.chmod(self.path, 0o600)
			server.listen()
			server.settimeout(0.2)
		except BaseException:
			# Une socket qui n'écoute pas ne reste pas ouverte (https://github.com/dascritch/machincast/issues/187).
			server.close()
			raise
		self._server = server
		self._feed = threading.Thread(target=self._accept, name="state socket", daemon=True)
		self._feed.start()

	def _busy(self) -> bool:
		with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as trial:
			try:
				trial.connect(str(self.path))
			except OSError:
				return False
		return True

	def publish(self, message: dict[str, Any]) -> None:
		"""Envoie le message à tous les clients, et à ceux qui se connecteront ensuite."""
		line = json.dumps({"version": VERSION, **message}, ensure_ascii=False) + "\n"
		with self._condition:
			self._message = line
			self._number += 1
			self._condition.notify_all()

	def shut_down(self) -> None:
		"""Laisse aux clients le temps de recevoir le dernier message, puis ferme et efface la socket."""
		if self._server is None:
			return
		with self._condition:
			self._condition.wait_for(
				lambda: all(sent >= self._number for sent in self._sent_list.values()), CLIENTS_WAITING
			)
			self._closed = True
			self._condition.notify_all()
		if self._feed is not None:
			self._feed.join(CLIENTS_WAITING)
		self._server.close()
		self._server = None
		self.path.unlink(missing_ok=True)  # fichier de MachinCast : socket d'état

	def _accept(self) -> None:
		server = self._server
		while (server is not None) and (not self._closed):
			try:
				client, _ = server.accept()
			except TimeoutError:
				continue
			except OSError:
				return
			threading.Thread(target=self._serve, args=(client,), name="state client", daemon=True).start()

	def _to_send(self, sent: int) -> bool:
		return (self._number > sent) or (self._closed)

	def _serve(self, client: socket.socket) -> None:
		key = threading.get_ident()
		sent = 0
		with client:
			client.settimeout(CLIENTS_WAITING)
			threading.Thread(target=self._listen, args=(client,), name="client requests", daemon=True).start()
			while True:
				with self._condition:
					self._sent_list[key] = sent
					self._condition.notify_all()
					self._condition.wait_for(functools.partial(self._to_send, sent), 0.5)
					if self._number <= sent:
						if self._closed:
							break
						continue
					line, sent = self._message, self._number
				try:
					client.sendall(line.encode())
				except OSError:
					break
			with self._condition:
				self._sent_list.pop(key, None)
				self._condition.notify_all()

	def _listen(self, client: socket.socket) -> None:
		"""Les demandes du client, jusqu'à sa déconnexion ou la fermeture de la socket."""
		buffer = b""
		while not self._closed:
			try:
				received = client.recv(MAXIMAL_SIZE)
			except TimeoutError:
				continue
			except OSError:
				return
			if received == b"":
				return
			buffer += received
			*lines, buffer = buffer.split(b"\n")
			if len(buffer) > MAXIMAL_SIZE:
				log.warning(
					_("{ignored_request}: more than {maximal_size} bytes").format(
						ignored_request=IGNORED_REQUEST, maximal_size=MAXIMAL_SIZE
					)
				)
				buffer = b""
			for line in lines:
				self._receive(line)

	def _receive(self, line: bytes) -> None:
		if line.strip() == b"":
			return
		try:
			self._requests.put(read_request(line))
		except ValueError as error:
			log.warning(_("{ignored_request}: {error}").format(ignored_request=IGNORED_REQUEST, error=error))
