"""Mesure des blocages de GStreamer, format par format (https://github.com/dascritch/machincast/issues/284).

Les contournements de https://github.com/dascritch/machincast/issues/280 (décodage repris au démarrage) et de
https://github.com/dascritch/machincast/issues/281 (voie bloquée remplacée) ont été écrits pour des défauts de
GStreamer 1.24 sur l'AIFF. Ce script les mesure à nouveau, sans le code de MachinCast, pour décider de chaque
contournement à chaque mise à jour de GStreamer :

	python -m tests.mesures_gstreamer                  # 1 000 essais par pipeline et par format
	python -m tests.mesures_gstreamer -n 200 -j 4      # 200 essais, quatre à la fois, pour mesurer sous charge
	python -m tests.mesures_gstreamer --pipelines decodebin3 --formats aiff
	python -m tests.mesures_gstreamer --synchrone --pipelines playbin playbin3 --formats aiff

Chaque essai décode l'un des fichiers de test tests/fichiers-sonores/sain.* aussi vite que possible :

- decodebin, queue-decodebin, decodebin3 : filesrc ! [queue !] decodebin[3] ! audioconvert ! fakesink, comme la
  vérification de l'indexation. Bloqué au démarrage : aucun son décodé en 2,5 secondes (decodage.DELAI_DEMARRAGE) ;
- playbin, playbin3 : le lecteur d'une voie de l'antenne, sur un fakesink, au plus vite, ou en temps réel avec
  --synchrone, comme à l'antenne. Bloqué au démarrage : pas d'état PLAYING en 3 secondes (moteur.DELAI_DE_GARDE).

Bloqué en cours : du son décodé, puis plus de fin en 10 secondes, pour un fichier d'une seconde. Chaque pipeline
est aussi lancé sur un tube nommé dont la lecture se bloque après son début, comme un partage réseau qui ne répond
plus : il doit rendre la main (état NULL) en moins de 5 secondes, une fois le tube fermé. Les essais tournent dans des
processus à part : un essai qui ne rend jamais la main est compté, et son processus remplacé. Le bilan donne le poste,
la version de GStreamer, et un tableau Markdown.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FICHIERS_SONORES = Path(__file__).parent / "fichiers-sonores"
FORMATS = ("aiff", "flac", "mp3", "ogg", "m4a", "aac", "wav")
PIPELINES = ("decodebin", "queue-decodebin", "decodebin3", "playbin", "playbin3")
DEMARRAGE_DECODAGE = 2.5
"""Comme decodage.DELAI_DEMARRAGE."""
DEMARRAGE_LECTURE = 3.0
"""Comme moteur.DELAI_DE_GARDE."""
FIN = 10.0
RENDRE_LA_MAIN = 5.0
DELAI_DU_TRAVAILLEUR = DEMARRAGE_LECTURE + FIN + RENDRE_LA_MAIN + 5
"""Au-delà, l'essai ne rend plus la main : son processus est remplacé."""
SYNCHRONE = "MACHINCAST_MESURE_SYNCHRONE"
"""Avec --synchrone, transmis aux processus des essais : playbin suit l'horloge, comme à l'antenne."""
VERDICTS = ("sain", "bloqué au démarrage", "bloqué en cours", "erreur", "ne rend pas la main")


def _gst():  # type: ignore[no-untyped-def]
	import gi

	gi.require_version("Gst", "1.0")
	from gi.repository import Gst

	Gst.init(None)
	return Gst


def _construire(gst, pipeline: str, emplacement: Path):  # type: ignore[no-untyped-def]
	"""Le pipeline, et le pad dont les tampons disent que du son est décodé."""
	if pipeline.startswith("playbin"):
		lecteur = gst.ElementFactory.make(pipeline, None)
		puits = gst.ElementFactory.make("fakesink", None)
		puits.set_property("sync", os.environ.get(SYNCHRONE) == "1")
		lecteur.set_property("audio-sink", puits)
		lecteur.set_property("video-sink", gst.ElementFactory.make("fakesink", None))
		lecteur.set_property("uri", emplacement.absolute().as_uri())
		return lecteur, puits.get_static_pad("sink")
	decodeur = "decodebin3" if (pipeline == "decodebin3") else "decodebin"
	file = "queue ! " if (pipeline == "queue-decodebin") else ""
	description = f'filesrc location="{emplacement}" ! {file}{decodeur} ! audioconvert ! fakesink name=puits sync=false'
	lecteur = gst.parse_launch(description)
	return lecteur, lecteur.get_by_name("puits").get_static_pad("sink")


def _essai(gst, pipeline: str, emplacement: Path) -> str:  # type: ignore[no-untyped-def]
	lecteur, entree = _construire(gst, pipeline, emplacement)
	tampons = [0]

	def sonde(_pad, _info):  # type: ignore[no-untyped-def]
		tampons[0] += 1
		return gst.PadProbeReturn.OK

	entree.add_probe(gst.PadProbeType.BUFFER, sonde)
	bus = lecteur.get_bus()
	lecteur.set_state(gst.State.PLAYING)
	debut = time.monotonic()
	verdict = "bloqué en cours"
	pas = gst.SECOND // 20
	types = gst.MessageType.EOS | gst.MessageType.ERROR
	while time.monotonic() - debut < FIN:
		message = bus.timed_pop_filtered(pas, types)
		if message is not None:
			verdict = "sain" if (message.type == gst.MessageType.EOS) else "erreur"
			break
		ecoule = time.monotonic() - debut
		if pipeline.startswith("playbin"):
			_retour, etat, _attente = lecteur.get_state(0)
			if (etat != gst.State.PLAYING) and (ecoule >= DEMARRAGE_LECTURE):
				verdict = "bloqué au démarrage"
				break
		elif (tampons[0] == 0) and (ecoule >= DEMARRAGE_DECODAGE):
			verdict = "bloqué au démarrage"
			break
	lecteur.set_state(gst.State.NULL)
	return verdict


def _rend_la_main(pipeline: str) -> str:
	"""Comme le scénario du fichier dont la lecture se bloque (test_verification.py) : un écrivain verse la moitié
	d'un WAV dans un tube nommé, puis le garde ouvert sans rien y écrire. Une fois le son décodé immobile pendant
	2 secondes, l'écrivain ferme le tube, puis le pipeline passe à l'état NULL : le temps qu'il met à rendre la main."""
	gst = _gst()
	donnees = (FICHIERS_SONORES / "sain.wav").read_bytes()
	with tempfile.TemporaryDirectory() as dossier:
		tube = Path(dossier) / "tube.wav"
		os.mkfifo(tube)
		abandon = threading.Event()
		ecrivain = threading.Thread(target=_alimenter, args=(tube, donnees[: len(donnees) // 2], abandon), daemon=True)
		ecrivain.start()
		lecteur, entree = _construire(gst, pipeline, tube)
		tampons = [0]

		def sonde(_pad, _info):  # type: ignore[no-untyped-def]
			tampons[0] += 1
			return gst.PadProbeReturn.OK

		entree.add_probe(gst.PadProbeType.BUFFER, sonde)
		lecteur.set_state(gst.State.PLAYING)
		dernier, immobile = -1, time.monotonic()
		while time.monotonic() - immobile < 2:
			time.sleep(0.05)
			if tampons[0] != dernier:
				dernier, immobile = tampons[0], time.monotonic()
		abandon.set()
		ecrivain.join(timeout=5)
		fini = threading.Event()
		depart = time.monotonic()
		threading.Thread(target=lambda: (lecteur.set_state(gst.State.NULL), fini.set()), daemon=True).start()
		if fini.wait(RENDRE_LA_MAIN):
			return f"{tampons[0]} tampons décodés, rend la main en {time.monotonic() - depart:.2f} s"
		return f"{tampons[0]} tampons décodés, ne rend pas la main en {RENDRE_LA_MAIN:.0f} s"


def _alimenter(tube: Path, debut: bytes, abandon: threading.Event) -> None:
	with open(tube, "wb") as ouvert:
		ouvert.write(debut)
		ouvert.flush()
		abandon.wait(timeout=60)


def travailleur(pipeline: str, format_: str, essais: int) -> None:
	"""Les essais, un verdict JSON par ligne, sur la sortie standard."""
	gst = _gst()
	emplacement = FICHIERS_SONORES / f"sain.{format_}"
	for _ in range(essais):
		print(json.dumps(_essai(gst, pipeline, emplacement)), flush=True)


def _lire(processus: subprocess.Popen[str], lignes: list[str]) -> None:
	lignes.extend((processus.stdout) or ([]))


def _mesurer(pipeline: str, format_: str, essais: int) -> Counter[str]:
	"""Les verdicts de tous les essais, dans des processus remplacés quand un essai ne rend plus la main."""
	verdicts: Counter[str] = Counter()
	while verdicts.total() < essais:
		reste = essais - verdicts.total()
		commande = [sys.executable, "-m", "tests.mesures_gstreamer", "--travailleur", pipeline, format_, str(reste)]
		processus = subprocess.Popen(commande, stdout=subprocess.PIPE, text=True, cwd=Path(__file__).parent.parent)
		lignes: list[str] = []
		lecture = threading.Thread(target=_lire, args=(processus, lignes), daemon=True)
		lecture.start()
		vus = 0
		dernier = time.monotonic()
		while processus.poll() is None:
			time.sleep(0.05)
			if len(lignes) > vus:
				vus, dernier = len(lignes), time.monotonic()
			elif time.monotonic() - dernier > DELAI_DU_TRAVAILLEUR:
				processus.kill()
				verdicts["ne rend pas la main"] += 1
				break
		processus.wait()
		lecture.join(timeout=5)
		verdicts.update(json.loads(ligne) for ligne in lignes)
		if (processus.returncode not in (0, -9)) and (not lignes):
			verdicts["erreur"] += reste
	return verdicts


def _tube(pipeline: str) -> str:
	"""_rend_la_main dans un processus à part, qui ne peut pas se finir tant que le pipeline ne rend pas la main."""
	commande = [sys.executable, "-m", "tests.mesures_gstreamer", "--tube", pipeline]
	try:
		sortie = subprocess.run(
			commande, capture_output=True, text=True, timeout=RENDRE_LA_MAIN + 10, cwd=Path(__file__).parent.parent
		)
	except subprocess.TimeoutExpired:
		return f"ne rend pas la main en {RENDRE_LA_MAIN:.0f} s"
	return (sortie.stdout.strip()) or (f"erreur : {sortie.stderr.strip()}")


def _versions() -> str:
	gst = _gst()
	systeme = platform.freedesktop_os_release().get("PRETTY_NAME", platform.platform())
	return f"{systeme}, {gst.version_string()}, Python {platform.python_version()}"


def main(arguments: list[str] | None = None) -> int:
	analyse = argparse.ArgumentParser(description="Mesure des blocages de GStreamer, format par format.")
	analyse.add_argument("-n", "--essais", type=int, default=1000, help="essais par pipeline et par format")
	analyse.add_argument("-j", "--paralleles", type=int, default=1, help="mesures menées à la fois, pour la charge")
	analyse.add_argument("--pipelines", nargs="+", choices=PIPELINES, default=list(PIPELINES))
	analyse.add_argument("--formats", nargs="+", choices=FORMATS, default=list(FORMATS))
	analyse.add_argument(
		"--synchrone", action="store_true", help="playbin et playbin3 jouent en temps réel, comme à l'antenne"
	)
	analyse.add_argument("--travailleur", nargs=3, help=argparse.SUPPRESS)
	analyse.add_argument("--tube", help=argparse.SUPPRESS)
	options = analyse.parse_args(arguments)
	if options.tube is not None:
		print(_rend_la_main(options.tube), flush=True)
		os._exit(0)
	if options.travailleur is not None:
		pipeline, format_, essais = options.travailleur
		travailleur(pipeline, format_, int(essais))
		return 0
	print(f"Poste : {_versions()}")
	if options.synchrone:
		os.environ[SYNCHRONE] = "1"
	rythme = "playbin en temps réel" if options.synchrone else "au plus vite"
	print(f"{options.essais} essais par pipeline et par format, {options.paralleles} à la fois, {rythme}\n")
	mesures = [(pipeline, format_) for pipeline in options.pipelines for format_ in options.formats]
	depart = time.monotonic()
	with ThreadPoolExecutor(options.paralleles) as executeur:
		resultats = list(executeur.map(lambda mesure: _mesurer(*mesure, options.essais), mesures))
	print(f"| pipeline | format | {' | '.join(VERDICTS)} |")
	print(f"| --- | --- |{' --- |' * len(VERDICTS)}")
	for (pipeline, format_), verdicts in zip(mesures, resultats, strict=True):
		print(f"| {pipeline} | {format_} | {' | '.join(str(verdicts[verdict]) for verdict in VERDICTS)} |")
	print("\nTube nommé dont la lecture se bloque après son début :")
	for pipeline in options.pipelines:
		print(f"- {pipeline} : {_tube(pipeline)}")
	print(f"\nDurée : {time.monotonic() - depart:.0f} s")
	return 0


if __name__ == "__main__":
	sys.exit(main())
