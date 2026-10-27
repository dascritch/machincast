"""Scénarios « release » d'un flux HTTP/2 qui gèle (https://github.com/dascritch/machincast/issues/278).

Lancés à part : pytest -m release. Un serveur hypercorn sert, en TLS, un flux AAC au rythme du temps réel, puis plus
rien, sa connexion ouverte. La voie de Machin lecture (machincast.lecture.moteur.Voie) le lit sur la sortie de la
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

from tests.sons import FICHIERS_SONORES

hypercorn = pytest.importorskip("hypercorn", reason='hypercorn manque : pip install --editable ".[dev]"')
from hypercorn.asyncio import serve  # noqa: E402
from hypercorn.config import Config  # noqa: E402

scenarios("flux_http2.feature")

GEL = 3.0
"""Secondes de son avant le gel."""
SON = (FICHIERS_SONORES / "sain.aac").read_bytes()
"""Une seconde de son."""
RACINE = Path(__file__).parent.parent
LECTEUR = """
import json, os, sys, time
from machincast.lecture import moteur
if sys.argv[2] == "HTTP/2":
	# Posée par l'import de machincast : libsoup force HTTP/1.1 dès qu'elle existe, quelle que soit sa valeur.
	del os.environ["SOUP_FORCE_HTTP1"]
from tests.base_test import configuration_test
vraie = moteur._regler_source
def regler(lecteur, source):
	vraie(lecteur, source)
	source.set_property("ssl-strict", False)
moteur._regler_source = regler
voie = moteur.Voie(sys.argv[1], configuration_test().audio, None)
voie.demarrer()
limite = time.monotonic() + float(sys.argv[3])
gelee = False
while (time.monotonic() < limite) and (voie.etat == "en cours"):
	voie.traiter()
	gelee = voie.gelee()
	time.sleep(0.1)
print(json.dumps({"etat": voie.etat, "erreur": voie.erreur, "gelee": gelee, "fin": time.time()}), flush=True)
os._exit(0)
"""
"""La voie, lue jusqu'à son erreur ou jusqu'à la durée donnée, puis ce qu'elle est devenue, en JSON."""


@dataclass
class Serveur:
	adresse: str
	versions: list[str] = field(default_factory=list)
	gele_le: float | None = None
	"""Heure du gel, à l'horloge du système."""


@dataclass
class Lecture:
	resultat: dict[str, Any] = field(default_factory=dict)
	"""Ce que la voie est devenue : etat, erreur, gelee, et l'heure de la fin, à l'horloge du système."""


@pytest.fixture
def lecture() -> Lecture:
	return Lecture()


def port_libre() -> int:
	with socket.socket() as essai:
		essai.bind(("127.0.0.1", 0))
		return int(essai.getsockname()[1])


@given(
	"un serveur de flux HTTP/2 local, chiffré, dont le flux AAC gèle au bout de 3 secondes", target_fixture="serveur"
)
def serveur_http2(tmp_path: Path) -> Iterator[Serveur]:
	cle, certificat = tmp_path / "cle.pem", tmp_path / "certificat.pem"
	subprocess.run(
		["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=127.0.0.1", "-days", "1"]
		+ ["-keyout", str(cle), "-out", str(certificat)],
		check=True,
		capture_output=True,
	)
	port = port_libre()
	serveur = Serveur(f"https://127.0.0.1:{port}/inter.aac")
	arret = threading.Event()

	async def application(portee: dict[str, Any], _recevoir: Any, envoyer: Any) -> None:
		if portee["type"] != "http":
			return
		serveur.versions.append(str(portee["http_version"]))
		await envoyer({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"audio/aac")]})
		debut, envoye = time.monotonic(), 0.0
		while time.monotonic() - debut < GEL:
			if envoye > time.monotonic() - debut + 1.5:
				await asyncio.sleep(0.05)
				continue
			await envoyer({"type": "http.response.body", "body": SON, "more_body": True})
			envoye += 1.0
		serveur.gele_le = time.time()
		while not arret.is_set():
			await asyncio.sleep(0.1)

	config = Config()
	config.bind = [f"127.0.0.1:{port}"]
	config.certfile, config.keyfile = str(certificat), str(cle)
	config.alpn_protocols = ["h2", "http/1.1"]
	config.loglevel = "ERROR"

	async def arreter() -> None:
		while not arret.is_set():
			await asyncio.sleep(0.05)

	fil = threading.Thread(
		target=lambda: asyncio.run(serve(application, config, shutdown_trigger=arreter)), daemon=True
	)
	fil.start()
	limite = time.monotonic() + 10
	while time.monotonic() < limite:
		with socket.socket() as essai:
			if essai.connect_ex(("127.0.0.1", port)) == 0:
				break
		time.sleep(0.05)
	yield serveur
	arret.set()
	fil.join(timeout=5)


@when(
	parsers.re(
		r"une voie de Machin lecture lit ce flux, en (?P<version>HTTP/1\.1|HTTP/2),"
		r" jusqu'à (?P<secondes>\d+) secondes après le gel"
	)
)
def lire(serveur: Serveur, lecture: Lecture, version: str, secondes: str) -> None:
	duree = GEL + int(secondes) + 2
	commande = [sys.executable, "-c", LECTEUR, serveur.adresse, version, str(duree)]
	sortie = subprocess.run(commande, capture_output=True, text=True, timeout=duree + 30, cwd=RACINE, check=True)
	lecture.resultat = json.loads(sortie.stdout.strip().splitlines()[-1])


@then(parsers.re(r"le serveur a servi le flux en HTTP/(?P<version>1\.1|2)"))
def version_servie(serveur: Serveur, version: str) -> None:
	assert serveur.versions != [], "aucune requête reçue"
	assert set(serveur.versions) == {version}, serveur.versions


@then(parsers.parse("la voie est en erreur au plus {secondes:d} secondes après le gel"))
def en_erreur(serveur: Serveur, lecture: Lecture, secondes: int) -> None:
	resultat = lecture.resultat
	assert (resultat["etat"] == "en erreur") and (serveur.gele_le is not None), resultat
	assert resultat["fin"] - serveur.gele_le <= secondes + 1, resultat


@then("la voie est toujours en cours, sans erreur")
def toujours_en_cours(lecture: Lecture) -> None:
	assert (lecture.resultat["etat"] == "en cours") and (lecture.resultat["erreur"] is None), lecture.resultat


@then("la voie est gelée")
def gelee(lecture: Lecture) -> None:
	assert lecture.resultat["gelee"], lecture.resultat
