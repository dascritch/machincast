"""Socket d'état du binaire lecture (https://github.com/dascritch/machincast/issues/20, spec § 5.4 et § 4.6).

Le binaire publie son état sur une socket Unix, lue par l'interface. À chaque client qui se connecte, il envoie le
dernier état, puis chaque nouvel état : une ligne JSON par état, en UTF-8, avec le numéro de version du format
(VERSION). La diffusion publie à chaque changement, et au moins toutes les MINIMAL_PUBLICATION secondes pour la
progression. Le format est décrit champ par champ dans la spécification, § 5.4.

La socket est réservée au compte qui diffuse : son répertoire est en 0700, la socket en 0600 ; avec le service,
au groupe du service, 0660, dans son répertoire d'exécution. Une seconde socket, au même protocole, est réservée au
serveur intranet, dont chaque demande nomme le compte de l'API qui la fait
(https://github.com/dascritch/machincast/issues/549). Une socket déjà
ouverte par un autre Machin player refuse la seconde diffusion (BusyStateSocket) ; une socket laissée par un
binaire arrêté brutalement est remplacée.

Chaque client a son fil : un client lent ou qui se déconnecte ne bloque jamais la diffusion.

Dans l'autre sens, un client peut envoyer des demandes, une ligne JSON par demande
(https://github.com/dascritch/machincast/issues/104) : {"command": "interrupt", "item": E}, où E est
« sound », « sequence » ou « event », ou, pour revenir au début du sonore ou de l'événement à l'antenne,
« restart_sound » ou « restart_event » (INTERRUPTIONS, https://github.com/dascritch/machincast/issues/366), ou
« restart_sequence », pour recommencer la séquence à l'antenne (https://github.com/dascritch/machincast/issues/530) ; {"command": "insert",
"sequence": N} ou {"command": "insert", "bank": N}, pour jouer après le sonore en cours la séquence N, ou un sonore
de la banque N (https://github.com/dascritch/machincast/issues/530) ; {"command": "reread_grid"}, après un changement de la
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

import dataclasses
import functools
import json
import logging
import os
import queue
import re
import socket
import stat
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import TupleRow

from machincast import service
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
INSERT = "insert"
"""Jouer après le sonore en cours une séquence, ou un sonore d'une banque (https://github.com/dascritch/machincast/issues/530)."""
"""Couper l'antenne par un événement de secours, ou par un feed (https://github.com/dascritch/machincast/issues/323)."""
INTERRUPTIONS = ("sound", "sequence", "event", "restart_sound", "restart_event", "restart_sequence")
"""Ce qu'une demande peut interrompre (https://github.com/dascritch/machincast/issues/104) ; revenir au début du sonore
ou de l'événement à l'antenne (https://github.com/dascritch/machincast/issues/366)."""
MAXIMAL_SIZE = 4096
"""Octets d'une demande, au plus : au-delà, ce qui a été reçu est ignoré."""
INTERFACE = "interface"
INTRANET = "intranet"
"""D'où vient une demande : de la socket d'état, que lisent l'interface et le compte de MachinCast, ou de celle de
l'intranet, que seul le serveur intranet joint (https://github.com/dascritch/machincast/issues/549)."""
USER = "user"
"""Le champ du compte de l'API qui fait la demande, sur la socket de l'intranet seulement."""
USER_NAME = re.compile(r"^[A-Za-z0-9._-]{1,255}$")
"""Un nom de compte de l'API, comme api_users.name l'accepte."""
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
	sequence: int | None = None
	bank: int | None = None
	"""Pour une insertion : la séquence, ou la banque, à jouer après le sonore en cours."""
	origin: str = INTERFACE
	"""La socket qui l'a reçue : INTERFACE ou INTRANET (https://github.com/dascritch/machincast/issues/549)."""
	user: str | None = None
	"""Le compte de l'API qui la fait, pour une demande de l'intranet : le serveur intranet le tient de la session."""


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


def insertion_request(*, sequence: int | None = None, bank: int | None = None) -> str:
	"""La ligne qu'un client envoie pour jouer, après le sonore en cours, cette séquence ou un sonore de cette banque
	(https://github.com/dascritch/machincast/issues/530)."""
	if sequence is not None:
		return json.dumps({"command": INSERT, "sequence": sequence}) + "\n"
	return json.dumps({"command": INSERT, "bank": bank}) + "\n"


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


def from_user(line: str, user: str) -> str:
	"""La ligne d'une demande, avec le compte de l'API qui la fait : ce qu'envoie le serveur intranet."""
	return json.dumps({**json.loads(line), USER: user}) + "\n"


def _user(message: dict[str, Any], origin: str) -> str | None:
	"""Le compte de l'API d'une demande, retiré du message : obligatoire de l'intranet, refusé d'ailleurs, où rien ne
	dit qui l'a écrit."""
	if origin != INTRANET:
		if USER in message:
			raise ValueError(_("the user of a request is given only on the socket of the intranet"))
		return None
	user = message.pop(USER, None)
	if (not isinstance(user, str)) or (USER_NAME.fullmatch(user) is None):
		raise ValueError(_("a request of the intranet names the user who makes it"))
	return user


def read_request(line: bytes, origin: str = INTERFACE) -> Request:
	"""Une demande reçue de la socket d'origin ; ValueError si elle est illisible ou inconnue."""
	try:
		message = json.loads(line.decode())
	except (UnicodeDecodeError, json.JSONDecodeError) as error:
		raise ValueError(_("unreadable: {error}").format(error=error)) from error
	if not isinstance(message, dict):
		raise ValueError(_("a request is a JSON object"))
	user = _user(message, origin)
	return dataclasses.replace(_command(message), origin=origin, user=user)


def _command(message: dict[str, Any]) -> Request:
	"""La demande que dit le message, sans son origine."""
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
	if (command == INSERT) and ("sequence" in message):
		return Request(command=INSERT, sequence=_identifier(message, "sequence"))
	if command == INSERT:
		return Request(command=INSERT, bank=_identifier(message, "bank"))
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
	"""Serveur de la socket d'état : un fil pour accepter les clients, un fil par client. Avec intranet, une seconde
	socket au même protocole, pour le seul serveur intranet, dont chaque demande nomme le compte de l'API qui la fait
	(https://github.com/dascritch/machincast/issues/549) ; les clients des deux reçoivent les mêmes états."""

	def __init__(self, path: Path, intranet: Path | None = None) -> None:
		self.path = path
		self.intranet = intranet
		self._servers: list[tuple[socket.socket, Path]] = []
		self._condition = threading.Condition()
		self._message = ""
		self._number = 0
		self._closed = False
		self._sent_list: dict[int, int] = {}
		"""Dernier message envoyé à chaque client, par identifiant de fil."""
		self._feeds: list[threading.Thread] = []
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
		"""Crée la socket, et celle de l'intranet ; lève BusyStateSocket si un autre Machin player l'a déjà ouverte."""
		paths = [(self.path, INTERFACE)]
		if self.intranet is not None:
			paths.append((self.intranet, INTRANET))
		try:
			for path, origin in paths:
				server = self._bind(path)
				self._servers.append((server, path))
				feed = threading.Thread(
					target=self._accept, args=(server, origin), name=f"{origin} socket", daemon=True
				)
				self._feeds.append(feed)
				feed.start()
		except BaseException:
			self._close_servers()
			raise

	def _bind(self, path: Path) -> socket.socket:
		"""Une socket qui écoute à ce chemin, à son mode : celui du groupe dans un répertoire partagé, privée ailleurs."""
		check_writing(path)
		directory = path.parent
		# Dans le répertoire du service, la socket est à son groupe : le compte de MachinCast la lit et y écrit ; le
		# répertoire est à tmpfiles.d (https://github.com/dascritch/machincast/issues/381). De même dans celui du
		# serveur intranet, à son groupe (https://github.com/dascritch/machincast/issues/549). Ailleurs, privée.
		shared = directory in (service.runtime(), service.intranet_runtime())
		mode = 0o600
		if shared:
			mode = 0o660
		else:
			directory.mkdir(mode=0o700, parents=True, exist_ok=True)
			os.chmod(directory, 0o700)
		if (path.exists()) or (path.is_symlink()):
			if self._busy(path):
				raise BusyStateSocket(_("{path}: another Machin player is already broadcasting").format(path=path))
			if not stat.S_ISSOCK(path.lstat().st_mode):
				raise OSError(_("{path} exists and is not a socket").format(path=path))
			path.unlink()  # fichier de MachinCast : socket d'état laissée par un arrêt brutal
		server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		try:
			old = os.umask(0o777 & ~mode)
			try:
				server.bind(str(path))
			finally:
				os.umask(old)
			os.chmod(path, mode)
			server.listen()
			server.settimeout(0.2)
		except BaseException:
			# Une socket qui n'écoute pas ne reste pas ouverte (https://github.com/dascritch/machincast/issues/187).
			server.close()
			raise
		return server

	def _busy(self, path: Path) -> bool:
		with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as trial:
			try:
				trial.connect(str(path))
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
		"""Laisse aux clients le temps de recevoir le dernier message, puis ferme et efface les sockets."""
		if self._servers == []:
			return
		with self._condition:
			self._condition.wait_for(self._all_sent, CLIENTS_WAITING)
			self._closed = True
			self._condition.notify_all()
		for feed in self._feeds:
			feed.join(CLIENTS_WAITING)
		self._close_servers()

	def _close_servers(self) -> None:
		for server, path in self._servers:
			server.close()
			path.unlink(missing_ok=True)  # fichier de MachinCast : socket d'état
		self._servers = []
		self._feeds = []

	def _accept(self, server: socket.socket, origin: str) -> None:
		while not self._closed:
			try:
				client, _ = server.accept()
			except TimeoutError:
				# Le délai d'attente laisse voir la fermeture de la socket.
				pass
			except OSError:
				return
			else:
				threading.Thread(target=self._serve, args=(client, origin), name="state client", daemon=True).start()

	def _all_sent(self) -> bool:
		"""Chaque client a reçu le dernier message."""
		for sent in self._sent_list.values():
			if sent < self._number:
				return False
		return True

	def _to_send(self, sent: int) -> bool:
		return (self._number > sent) or (self._closed)

	def _serve(self, client: socket.socket, origin: str = INTERFACE) -> None:
		key = threading.get_ident()
		sent = 0
		with client:
			client.settimeout(CLIENTS_WAITING)
			threading.Thread(target=self._listen, args=(client, origin), name="client requests", daemon=True).start()
			while True:
				line = None
				with self._condition:
					self._sent_list[key] = sent
					self._condition.notify_all()
					self._condition.wait_for(functools.partial(self._to_send, sent), 0.5)
					if self._number > sent:
						line, sent = self._message, self._number
					else:
						if self._closed:
							break
				if line is not None:
					try:
						client.sendall(line.encode())
					except OSError:
						break
			with self._condition:
				self._sent_list.pop(key, None)
				self._condition.notify_all()

	def _listen(self, client: socket.socket, origin: str = INTERFACE) -> None:
		"""Les demandes du client, jusqu'à sa déconnexion ou la fermeture de la socket."""
		buffer = b""
		while not self._closed:
			try:
				received = client.recv(MAXIMAL_SIZE)
			except TimeoutError:
				# Le délai d'attente laisse voir la fermeture de la socket.
				received = None
			except OSError:
				return
			if received == b"":
				return
			if received is not None:
				buffer = self._receive_lines(buffer + received, origin)

	def _receive_lines(self, buffer: bytes, origin: str = INTERFACE) -> bytes:
		"""Les demandes complètes du tampon sont reçues ; le reste, une demande commencée, est rendu, ou oublié s'il
		est trop long."""
		*lines, rest = buffer.split(b"\n")
		if len(rest) > MAXIMAL_SIZE:
			log.warning(
				_("{ignored_request}: more than {maximal_size} bytes").format(
					ignored_request=IGNORED_REQUEST, maximal_size=MAXIMAL_SIZE
				)
			)
			rest = b""
		for line in lines:
			self._receive(line, origin)
		return rest

	def _receive(self, line: bytes, origin: str = INTERFACE) -> None:
		if line.strip() == b"":
			return
		try:
			self._requests.put(read_request(line, origin))
		except ValueError as error:
			log.warning(_("{ignored_request}: {error}").format(ignored_request=IGNORED_REQUEST, error=error))
