"""Serveur de flux HTTP local, pour les scénarios des streams (https://github.com/dascritch/machincast/issues/16).

Chaque flux, à l'adresse http://127.0.0.1:<port>/<nom>, envoie sans fin le MP3 de test, au rythme du temps réel,
comme un serveur Icecast : une courte avance au départ, puis une seconde de son par seconde. Le lecteur n'a donc
qu'une fraction de seconde de son d'avance, et voit vite le flux tomber. Le premier envoi est le MP3 tagué
(tests/sons.py) : ses tags ne doivent jamais remplacer les métadonnées de la base.

Un flux hors ligne ferme les connexions en cours et répond 503 aux nouvelles.
"""

import contextlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import BinaryIO

from tests.sons import FICHIERS_SONORES

TAGUE = (FICHIERS_SONORES / "tags.mp3").read_bytes()
SAIN = (FICHIERS_SONORES / "sain.mp3").read_bytes()
"""Une seconde de son : envoyé en boucle, à raison d'une copie par seconde."""
TRANCHES_PAR_SECONDE = 10
AVANCE_INITIALE = 1.5
"""Secondes de son envoyées d'un coup à la connexion."""


class ServeurDeFlux:
	def __init__(self) -> None:
		self.en_ligne: dict[str, bool] = {}
		serveur = self

		class Gestionnaire(BaseHTTPRequestHandler):
			protocol_version = "HTTP/1.0"

			def do_GET(self) -> None:
				nom = self.path.strip("/")
				if not serveur.en_ligne.get(nom, False):
					self.send_error(503, "flux hors ligne")
					return
				self.send_response(200)
				self.send_header("Content-Type", "audio/mpeg")
				self.end_headers()
				# Le lecteur peut fermer la connexion à tout moment.
				with contextlib.suppress(BrokenPipeError, ConnectionResetError):
					serveur.envoyer(nom, self.wfile)  # type: ignore[arg-type]

			def log_message(self, format: str, *args: object) -> None:
				"""Pas de journal des requêtes."""

		self._serveur = ThreadingHTTPServer(("127.0.0.1", 0), Gestionnaire)
		self._serveur.daemon_threads = True
		self._fil = threading.Thread(target=self._serveur.serve_forever, daemon=True)
		self._fil.start()

	def adresse(self, nom: str) -> str:
		return f"http://127.0.0.1:{self._serveur.server_address[1]}/{nom}"

	def envoyer(self, nom: str, sortie: BinaryIO) -> None:
		sortie.write(TAGUE)
		tranche = max(1, len(SAIN) // TRANCHES_PAR_SECONDE)
		envoye = float(len(TAGUE)) / len(SAIN)
		debut = time.monotonic() - AVANCE_INITIALE
		position = 0
		while self.en_ligne.get(nom, False):
			# Pas plus de son que le temps écoulé, avance initiale comprise.
			if envoye > time.monotonic() - debut:
				time.sleep(1 / TRANCHES_PAR_SECONDE / 2)
				continue
			morceau = SAIN[position : position + tranche]
			sortie.write(morceau)
			sortie.flush()
			envoye += len(morceau) / len(SAIN)
			position = (position + tranche) % len(SAIN)

	def fermer(self) -> None:
		for nom in self.en_ligne:
			self.en_ligne[nom] = False
		self._serveur.shutdown()
		self._serveur.server_close()
