"""Mesure des blocages de GStreamer, format par format (https://github.com/dascritch/machincast/issues/284).

Les contournements de https://github.com/dascritch/machincast/issues/280 (décodage repris au démarrage) et de
https://github.com/dascritch/machincast/issues/281 (voie bloquée remplacée) ont été écrits pour des défauts de
GStreamer 1.24 sur l'AIFF. Ce script les mesure à nouveau, sans le code de MachinCast, pour décider de chaque
contournement à chaque mise à jour de GStreamer :

	python -m tests.gstreamer_measures                  # 1 000 essais par pipeline et par format
	python -m tests.gstreamer_measures -n 200 -j 4      # 200 essais, quatre à la fois, pour mesurer sous charge
	python -m tests.gstreamer_measures --pipelines decodebin3 --formats aiff
	python -m tests.gstreamer_measures --synchronous --pipelines playbin playbin3 --formats aiff

Chaque essai décode l'un des fichiers de test tests/fichiers-sonores/sain.* aussi vite que possible :

- decodebin, queue-decodebin, decodebin3 : filesrc ! [queue !] decodebin[3] ! audioconvert ! fakesink, comme la
  vérification de l'indexation. Bloqué au démarrage : aucun son décodé en 2,5 secondes (decoding.STARTUP_DELAY) ;
- playbin, playbin3 : le lecteur d'une voie de l'antenne, sur un fakesink, au plus vite, ou en temps réel avec
  --synchronous, comme à l'antenne. Bloqué au démarrage : pas d'état PLAYING en 3 secondes,
  plus strict que engine.GUARD_DELAY.

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

SOUND_FILES = Path(__file__).parent / "fichiers-sonores"
FORMATS = ("aiff", "flac", "mp3", "ogg", "m4a", "aac", "wav")
PIPELINES = ("decodebin", "queue-decodebin", "decodebin3", "playbin", "playbin3")
DECODING_STARTUP = 2.5
"""Comme decodage.DELAI_DEMARRAGE."""
PLAYBACK_STARTUP = 3.0
"""Comme moteur.DELAI_DE_GARDE."""
END = 10.0
YIELD_CONTROL = 5.0
WORKER_DELAY = PLAYBACK_STARTUP + END + YIELD_CONTROL + 5
"""Au-delà, l'essai ne rend plus la main : son processus est remplacé."""
SYNCHRONOUS = "MACHINCAST_MESURE_SYNCHRONE"
"""Avec --synchronous, transmis aux processus des essais : playbin suit l'horloge, comme à l'antenne."""
VERDICTS = ("sain", "bloqué au démarrage", "bloqué en cours", "erreur", "ne rend pas la main")


def _gst():  # type: ignore[no-untyped-def]
	import gi

	gi.require_version("Gst", "1.0")
	from gi.repository import Gst

	Gst.init(None)
	return Gst


def _build(gst, pipeline: str, location: Path):  # type: ignore[no-untyped-def]
	"""Le pipeline, et le pad dont les tampons disent que du son est décodé."""
	if pipeline.startswith("playbin"):
		player = gst.ElementFactory.make(pipeline, None)
		sink = gst.ElementFactory.make("fakesink", None)
		sink.set_property("sync", os.environ.get(SYNCHRONOUS) == "1")
		player.set_property("audio-sink", sink)
		player.set_property("video-sink", gst.ElementFactory.make("fakesink", None))
		player.set_property("uri", location.absolute().as_uri())
		return player, sink.get_static_pad("sink")
	decoder = "decodebin"
	if pipeline == "decodebin3":
		decoder = "decodebin3"
	file = ""
	if pipeline == "queue-decodebin":
		file = "queue ! "
	description = f'filesrc location="{location}" ! {file}{decoder} ! audioconvert ! fakesink name=puits sync=false'
	player = gst.parse_launch(description)
	return player, player.get_by_name("puits").get_static_pad("sink")


def _trial(gst, pipeline: str, location: Path) -> str:  # type: ignore[no-untyped-def]
	player, entry = _build(gst, pipeline, location)
	buffers = [0]

	def probe(_pad, _info):  # type: ignore[no-untyped-def]
		buffers[0] += 1
		return gst.PadProbeReturn.OK

	entry.add_probe(gst.PadProbeType.BUFFER, probe)
	bus = player.get_bus()
	player.set_state(gst.State.PLAYING)
	start = time.monotonic()
	verdict = "bloqué en cours"
	step = gst.SECOND // 20
	types = gst.MessageType.EOS | gst.MessageType.ERROR
	while time.monotonic() - start < END:
		message = bus.timed_pop_filtered(step, types)
		if message is not None:
			verdict = "erreur"
			if message.type == gst.MessageType.EOS:
				verdict = "sain"
			break
		elapsed = time.monotonic() - start
		if pipeline.startswith("playbin"):
			_return, state, _waiting = player.get_state(0)
			if (state != gst.State.PLAYING) and (elapsed >= PLAYBACK_STARTUP):
				verdict = "bloqué au démarrage"
				break
		else:
			if (buffers[0] == 0) and (elapsed >= DECODING_STARTUP):
				verdict = "bloqué au démarrage"
				break
	player.set_state(gst.State.NULL)
	return verdict


def _returns_main(pipeline: str) -> str:
	"""Comme le scénario du fichier dont la lecture se bloque (test_check.py) : un écrivain verse la moitié
	d'un WAV dans un tube nommé, puis le garde ouvert sans rien y écrire. Une fois le son décodé immobile pendant
	2 secondes, l'écrivain ferme le tube, puis le pipeline passe à l'état NULL : le temps qu'il met à rendre la main."""
	gst = _gst()
	data = (SOUND_FILES / "sain.wav").read_bytes()
	with tempfile.TemporaryDirectory() as folder:
		pipe = Path(folder) / "tube.wav"
		os.mkfifo(pipe)
		abandon = threading.Event()
		writer = threading.Thread(target=_feed, args=(pipe, data[: len(data) // 2], abandon), daemon=True)
		writer.start()
		player, entry = _build(gst, pipeline, pipe)
		buffers = [0]

		def probe(_pad, _info):  # type: ignore[no-untyped-def]
			buffers[0] += 1
			return gst.PadProbeReturn.OK

		entry.add_probe(gst.PadProbeType.BUFFER, probe)
		player.set_state(gst.State.PLAYING)
		last, still = -1, time.monotonic()
		while time.monotonic() - still < 2:
			time.sleep(0.05)
			if buffers[0] != last:
				last, still = buffers[0], time.monotonic()
		abandon.set()
		writer.join(timeout=5)
		finished = threading.Event()
		departure = time.monotonic()
		threading.Thread(target=lambda: (player.set_state(gst.State.NULL), finished.set()), daemon=True).start()
		if finished.wait(YIELD_CONTROL):
			return f"{buffers[0]} tampons décodés, rend la main en {time.monotonic() - departure:.2f} s"
		return f"{buffers[0]} tampons décodés, ne rend pas la main en {YIELD_CONTROL:.0f} s"


def _feed(pipe: Path, start: bytes, abandon: threading.Event) -> None:
	with open(pipe, "wb") as opened:
		opened.write(start)
		opened.flush()
		abandon.wait(timeout=60)


def worker(pipeline: str, format_: str, trials: int) -> None:
	"""Les essais, un verdict JSON par ligne, sur la sortie standard."""
	gst = _gst()
	location = SOUND_FILES / f"sain.{format_}"
	for _ in range(trials):
		print(json.dumps(_trial(gst, pipeline, location)), flush=True)


def _read(process: subprocess.Popen[str], lines: list[str]) -> None:
	lines.extend((process.stdout) or ([]))


def _measure(pipeline: str, format_: str, trials: int) -> Counter[str]:
	"""Les verdicts de tous les essais, dans des processus remplacés quand un essai ne rend plus la main."""
	verdicts: Counter[str] = Counter()
	while verdicts.total() < trials:
		rest = trials - verdicts.total()
		command = [sys.executable, "-m", "tests.gstreamer_measures", "--worker", pipeline, format_, str(rest)]
		process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True, cwd=Path(__file__).parent.parent)
		lines: list[str] = []
		playback = threading.Thread(target=_read, args=(process, lines), daemon=True)
		playback.start()
		seen_list = 0
		last = time.monotonic()
		while process.poll() is None:
			time.sleep(0.05)
			if len(lines) > seen_list:
				seen_list, last = len(lines), time.monotonic()
			else:
				if time.monotonic() - last > WORKER_DELAY:
					process.kill()
					verdicts["ne rend pas la main"] += 1
					break
		process.wait()
		playback.join(timeout=5)
		line_list = []
		for line in lines:
			line_list.append(json.loads(line))
		verdicts.update(line_list)
		if (process.returncode not in (0, -9)) and (not lines):
			verdicts["erreur"] += rest
	return verdicts


def _pipe(pipeline: str) -> str:
	"""_rend_la_main dans un processus à part, qui ne peut pas se finir tant que le pipeline ne rend pas la main."""
	command = [sys.executable, "-m", "tests.gstreamer_measures", "--pipe", pipeline]
	try:
		output = subprocess.run(
			command, capture_output=True, text=True, timeout=YIELD_CONTROL + 10, cwd=Path(__file__).parent.parent
		)
	except subprocess.TimeoutExpired:
		return f"ne rend pas la main en {YIELD_CONTROL:.0f} s"
	return (output.stdout.strip()) or (f"erreur : {output.stderr.strip()}")


def _versions() -> str:
	gst = _gst()
	system = platform.freedesktop_os_release().get("PRETTY_NAME", platform.platform())
	return f"{system}, {gst.version_string()}, Python {platform.python_version()}"


def main(arguments: list[str] | None = None) -> int:
	analysis = argparse.ArgumentParser(description="Mesure des blocages de GStreamer, format par format.")
	analysis.add_argument("-n", "--essais", type=int, default=1000, help="essais par pipeline et par format")
	analysis.add_argument("-j", "--parallel", type=int, default=1, help="mesures menées à la fois, pour la charge")
	analysis.add_argument("--pipelines", nargs="+", choices=PIPELINES, default=list(PIPELINES))
	analysis.add_argument("--formats", nargs="+", choices=FORMATS, default=list(FORMATS))
	analysis.add_argument(
		"--synchronous", action="store_true", help="playbin et playbin3 jouent en temps réel, comme à l'antenne"
	)
	analysis.add_argument("--worker", nargs=3, help=argparse.SUPPRESS)
	analysis.add_argument("--pipe", help=argparse.SUPPRESS)
	options = analysis.parse_args(arguments)
	if options.pipe is not None:
		print(_returns_main(options.pipe), flush=True)
		os._exit(0)
	if options.worker is not None:
		pipeline, format_, trials = options.worker
		worker(pipeline, format_, int(trials))
		return 0
	print(f"Poste : {_versions()}")
	if options.synchronous:
		os.environ[SYNCHRONOUS] = "1"
	rhythm = "au plus vite"
	if options.synchronous:
		rhythm = "playbin en temps réel"
	print(f"{options.trials} essais par pipeline et par format, {options.parallel} à la fois, {rhythm}\n")
	measures = []
	for measured_pipeline in options.pipelines:
		for measured_format in options.formats:
			measures.append((measured_pipeline, measured_format))
	departure = time.monotonic()
	with ThreadPoolExecutor(options.parallel) as runner:
		results = list(runner.map(lambda measure: _measure(*measure, options.trials), measures))
	print(f"| pipeline | format | {' | '.join(VERDICTS)} |")
	print(f"| --- | --- |{' --- |' * len(VERDICTS)}")
	for (pipeline, format_), verdicts in zip(measures, results, strict=True):
		cells = []
		for verdict in VERDICTS:
			cells.append(str(verdicts[verdict]))
		print(f"| {pipeline} | {format_} | {' | '.join(cells)} |")
	print("\nTube nommé dont la lecture se bloque après son début :")
	for pipeline in options.pipelines:
		print(f"- {pipeline} : {_pipe(pipeline)}")
	print(f"\nDurée : {time.monotonic() - departure:.0f} s")
	return 0


if __name__ == "__main__":
	sys.exit(main())
