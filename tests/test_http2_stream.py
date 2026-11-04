"""Scénarios « release » d'un flux HTTP/2 qui gèle (https://github.com/dascritch/machincast/issues/278).

Lancés à part : pytest -m release. Un serveur hypercorn sert, en TLS, un flux AAC au rythme du temps réel, puis plus
rien, sa connexion ouverte. La voie de Machin player (machincast.player.engine.Track) le lit sur la sortie de la
configuration de test, dans un processus à part : libsoup ne choisit HTTP/2 que dans un processus où SOUP_FORCE_HTTP1
n'a jamais existé avant sa première session. Le certificat, fait pour le scénario, est accepté (ssl-strict).
"""

import asyncio
import json
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.sounds import SOUND_FILES

hypercorn = pytest.importorskip("hypercorn", reason='hypercorn manque : pip install --editable ".[dev]"')
from hypercorn.asyncio import serve  # noqa: E402
from hypercorn.config import Config  # noqa: E402

scenarios("http2_stream.feature")

FREEZE = 3.0
"""Secondes de son avant le gel."""
SOUND = (SOUND_FILES / "sain.aac").read_bytes()
"""Une seconde de son."""
ROOT = Path(__file__).parent.parent
PLAYER = """
import json, os, sys, time
from machincast.player import engine
if sys.argv[2] == "HTTP/2":
	# Posée par l'import de machincast : libsoup force HTTP/1.1 dès qu'elle existe, quelle que soit sa valeur.
	del os.environ["SOUP_FORCE_HTTP1"]
from tests.database_fixtures import configuration_test
true_set_source = engine._set_source
def set_source(player, source):
	true_set_source(player, source)
	source.set_property("ssl-strict", False)
engine._set_source = set_source
track = engine.Track(sys.argv[1], configuration_test().audio, None)
track.start()
limit = time.monotonic() + float(sys.argv[3])
frozen = False
while (time.monotonic() < limit) and (track.state == "playing"):
	track.handle()
	frozen = track.frozen()
	time.sleep(0.1)
print(json.dumps({"state": track.state, "error": track.error, "frozen": frozen, "end": time.time()}), flush=True)
os._exit(0)
"""
"""La voie, lue jusqu'à son erreur ou jusqu'à la durée donnée, puis ce qu'elle est devenue, en JSON."""


@dataclass
class Server:
	address: str
	versions: list[str] = field(default_factory=list)
	frozen_at: float | None = None
	"""Heure du gel, à l'horloge du système."""


@dataclass
class Playback:
	result: dict[str, Any] = field(default_factory=dict)
	"""Ce que la voie est devenue : etat, erreur, gelee, et l'heure de la fin, à l'horloge du système."""


@pytest.fixture
def playback() -> Playback:
	return Playback()


def free_port() -> int:
	with socket.socket() as trial:
		trial.bind(("127.0.0.1", 0))
		return int(trial.getsockname()[1])


@given("un serveur de flux HTTP/2 local, chiffré, dont le flux AAC gèle au bout de 3 secondes", target_fixture="server")
def http2_server(tmp_path: Path) -> Iterator[Server]:
	key, certificate = tmp_path / "cle.pem", tmp_path / "certificat.pem"
	subprocess.run(
		["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=127.0.0.1", "-days", "1"]
		+ ["-keyout", str(key), "-out", str(certificate)],
		check=True,
		capture_output=True,
	)
	port = free_port()
	server = Server(f"https://127.0.0.1:{port}/inter.aac")
	stop = threading.Event()

	async def application(scope: dict[str, Any], _receive: Any, send: Any) -> None:
		if scope["type"] != "http":
			return
		server.versions.append(str(scope["http_version"]))
		await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"audio/aac")]})
		start, sent = time.monotonic(), 0.0
		while time.monotonic() - start < FREEZE:
			if sent > time.monotonic() - start + 1.5:
				await asyncio.sleep(0.05)
				continue
			await send({"type": "http.response.body", "body": SOUND, "more_body": True})
			sent += 1.0
		server.frozen_at = time.time()
		while not stop.is_set():
			await asyncio.sleep(0.1)

	config = Config()
	config.bind = [f"127.0.0.1:{port}"]
	config.certfile, config.keyfile = str(certificate), str(key)
	config.alpn_protocols = ["h2", "http/1.1"]
	config.loglevel = "ERROR"

	async def halt() -> None:
		while not stop.is_set():
			await asyncio.sleep(0.05)

	feed = threading.Thread(target=lambda: asyncio.run(serve(application, config, shutdown_trigger=halt)), daemon=True)
	feed.start()
	limit = time.monotonic() + 10
	while time.monotonic() < limit:
		with socket.socket() as trial:
			if trial.connect_ex(("127.0.0.1", port)) == 0:
				break
		time.sleep(0.05)
	yield server
	stop.set()
	feed.join(timeout=5)


@when(
	parsers.re(
		r"une voie de Machin player lit ce flux, en (?P<version>HTTP/1\.1|HTTP/2),"
		r" jusqu'à (?P<seconds>\d+) secondes après le gel"
	)
)
def read(server: Server, playback: Playback, version: str, seconds: str) -> None:
	duration = FREEZE + int(seconds) + 2
	command = [sys.executable, "-c", PLAYER, server.address, version, str(duration)]
	output = subprocess.run(command, capture_output=True, text=True, timeout=duration + 30, cwd=ROOT, check=True)
	playback.result = json.loads(output.stdout.strip().splitlines()[-1])


@then(parsers.re(r"le serveur a servi le flux en HTTP/(?P<version>1\.1|2)"))
def served_version(server: Server, version: str) -> None:
	assert server.versions != [], "aucune requête reçue"
	assert set(server.versions) == {version}, server.versions


@then(parsers.parse("la voie est en erreur au plus {seconds:d} secondes après le gel"))
def in_error(server: Server, playback: Playback, seconds: int) -> None:
	result = playback.result
	assert (result["state"] == "error") and (server.frozen_at is not None), result
	assert result["end"] - server.frozen_at <= seconds + 1, result


@then("la voie est toujours en cours, sans erreur")
def always_ongoing(playback: Playback) -> None:
	assert (playback.result["state"] == "playing") and (playback.result["error"] is None), playback.result


@then("la voie est gelée")
def frozen(playback: Playback) -> None:
	assert playback.result["frozen"], playback.result
