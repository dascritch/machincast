"""Serveur de flux HTTP local, pour les scénarios des streams (https://github.com/dascritch/machincast/issues/16).

Chaque flux, à l'adresse http://127.0.0.1:<port>/<nom>, envoie sans fin le MP3 de test, au rythme du temps réel,
comme un serveur Icecast : une courte avance au départ, puis une seconde de son par seconde. Le lecteur n'a donc
qu'une fraction de seconde de son d'avance, et voit vite le flux tomber. Le premier envoi est le MP3 tagué
(tests/sons.py) : ses tags ne doivent jamais remplacer les métadonnées de la base.

Un flux hors ligne ferme les connexions en cours et répond 503 aux nouvelles. Un flux avare n'envoie qu'une demi-seconde
de son, puis garde la connexion ouverte sans rien envoyer. Un flux gelé n'envoie plus rien sur ses connexions, sans les
fermer, comme un réseau coupé (https://github.com/dascritch/machincast/issues/278) : une connexion gelée le reste, même
le flux dégelé ; seules les connexions ouvertes ensuite reçoivent du son. Un flux muet envoie du silence numérique
(muet.mp3) au même rythme, sur les mêmes connexions, comme un studio qui ne transmet plus rien
(https://github.com/dascritch/machincast/issues/122) ; il retrouve son son sans nouvelle connexion. Le serveur compte
ses connexions en cours, et toutes celles qu'il a reçues.
"""

import contextlib
import select
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import BinaryIO

from tests.sounds import SOUND_FILES

TAGGED = (SOUND_FILES / "tags.mp3").read_bytes()
HEALTHY = (SOUND_FILES / "sain.mp3").read_bytes()
"""Une seconde de son : envoyé en boucle, à raison d'une copie par seconde."""
SILENT = (SOUND_FILES / "muet.mp3").read_bytes()
"""Une seconde de silence numérique, envoyée de même par un flux muet."""
SLICES_PER_SECOND = 10
INITIAL_ADVANCE = 1.5
"""Secondes de son envoyées d'un coup à la connexion."""


class StreamServer:
	def __init__(self) -> None:
		self.in_line: dict[str, bool] = {}
		self.sparing_list: set[str] = set()
		self.frozen_list: set[str] = set()
		self.silent_list: set[str] = set()
		self.connections = 0
		"""Connexions en cours d'envoi."""
		self.received_list = 0
		"""Connexions reçues depuis le démarrage du serveur."""
		self._lock = threading.Lock()
		server = self

		class Handler(BaseHTTPRequestHandler):
			protocol_version = "HTTP/1.0"

			def do_GET(self) -> None:
				name = self.path.strip("/")
				if not server.in_line.get(name, False):
					self.send_error(503, "flux hors ligne")
					return
				self.send_response(200)
				self.send_header("Content-Type", "audio/mpeg")
				self.end_headers()
				server.count(1)
				try:
					# Le lecteur peut fermer la connexion à tout moment.
					with contextlib.suppress(BrokenPipeError, ConnectionResetError):
						if name in server.sparing_list:
							server.send_little(name, self.connection, self.wfile)  # type: ignore[arg-type]
						else:
							server.send(name, self.wfile)  # type: ignore[arg-type]
				finally:
					server.count(-1)

			def log_message(self, format: str, *args: object) -> None:
				"""Pas de journal des requêtes."""

		self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
		self._server.daemon_threads = True
		# Arrêté à chaque fin de scénario : serve_forever ne voit la demande d'arrêt qu'à son prochain tour, toutes les
		# 0,5 seconde par défaut (https://github.com/dascritch/machincast/issues/280).
		self._feed = threading.Thread(target=self._server.serve_forever, args=(0.02,), daemon=True)
		self._feed.start()

	def address(self, name: str) -> str:
		return f"http://127.0.0.1:{self._server.server_address[1]}/{name}"

	def count(self, gap: int) -> None:
		with self._lock:
			self.connections += gap
			self.received_list += max(gap, 0)

	def send_little(self, name: str, connection: socket.socket, output: BinaryIO) -> None:
		"""Une demi-seconde de son, puis rien, jusqu'à ce que le lecteur ferme la connexion."""
		output.write(HEALTHY[: len(HEALTHY) // 2])
		output.flush()
		while self.in_line.get(name, False):
			readable, _, _ = select.select([connection], [], [], 0.1)
			if (readable != []) and (connection.recv(1024) == b""):
				return

	def send(self, name: str, output: BinaryIO) -> None:
		if name in self.frozen_list:
			self._freeze(name)
			return
		output.write(TAGGED)
		sent = float(len(TAGGED)) / len(HEALTHY)
		start = time.monotonic() - INITIAL_ADVANCE
		position = 0
		data = HEALTHY
		while self.in_line.get(name, False):
			if name in self.frozen_list:
				self._freeze(name)
				return
			# Pas plus de son que le temps écoulé, avance initiale comprise.
			if sent > time.monotonic() - start:
				time.sleep(1 / SLICES_PER_SECOND / 2)
				continue
			# Muet ou de nouveau sonore, le flux repart du début d'un fichier : d'une trame MP3 entière.
			following_list = SILENT if name in self.silent_list else HEALTHY
			if following_list is not data:
				data, position = following_list, 0
			slice_ = max(1, len(data) // SLICES_PER_SECOND)
			piece = data[position : position + slice_]
			output.write(piece)
			output.flush()
			sent += len(piece) / len(data)
			position = (position + slice_) % len(data)

	def _freeze(self, name: str) -> None:
		"""Plus rien sur cette connexion, qui reste ouverte tant que le flux est en ligne, même dégelé."""
		while self.in_line.get(name, False):
			time.sleep(0.05)

	def shut_down(self) -> None:
		for name in self.in_line:
			self.in_line[name] = False
		self._server.shutdown()
		self._server.server_close()
