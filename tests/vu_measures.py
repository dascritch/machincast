"""Mesure du rythme du VU-mètre de l'antenne, avant, pendant et après l'écoute de l'antenne sur la pré-écoute
(https://github.com/dascritch/machincast/issues/627).

Sur le poste, avec sa configuration, ce script ouvre le moniteur de l'antenne de l'onglet Antenne
(machincast.interface.monitor.Monitor), puis écoute l'antenne sur la pré-écoute, comme la fenêtre de pré-écoute
(machincast.interface.preview.Player), l'arrête, et recommence :

	python -m tests.vu_measures                         # la configuration de machincast.toml
	python -m tests.vu_measures --config <fichier> --ecoutes 3 --duree 5
	python -m tests.vu_measures --temoin                # les mêmes phases, sans aucune écoute : le témoin

Pour chaque phase, il donne :

- les relevés de level reçus par seconde par le moniteur, et ceux qui en apportent de nouveaux niveaux : 20 attendus,
  un toutes les 50 ms ;
- le retard moyen et le pire retard d'un minuteur de 50 ms de Qt : une boucle de l'interface encombrée ;
- les fils du processus, et les nœuds PipeWire de MachinCast que liste pw-cli, quand il existe : ce qui n'est pas
  libéré ;
- l'état du moniteur : ouvert, ou la raison de son indisponibilité.

Avec --temoin, les phases d'écoute se passent sans écoute : un rythme qui baisse quand même vient du moniteur seul.

Rien n'est écrit, ni en base, ni dans la configuration ; rien ne joue à l'antenne.
"""

import argparse
import shutil
import subprocess
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

Gst.init(None)

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from machincast.configuration import Audio, load  # noqa: E402
from machincast.interface.monitor import Monitor  # noqa: E402
from machincast.interface.preview import Player, Source  # noqa: E402

TICK = 50
"""Millisecondes du minuteur de Qt dont le retard est mesuré, comme celui du moniteur."""


class Counted(Monitor):
	"""Le moniteur de l'antenne, qui compte ses relevés."""

	def __init__(self, audio: Audio) -> None:
		super().__init__(audio)
		self.readings = 0
		self.changes = 0
		self._previous: list[float] = []

	def note(self, levels: list[float], peaks: list[float]) -> None:
		self.readings += 1
		if levels != self._previous:
			self.changes += 1
		self._previous = list(levels)
		super().note(levels, peaks)


def wait(seconds: float) -> None:
	loop = QEventLoop()
	QTimer.singleShot(round(seconds * 1000), loop.quit)
	loop.exec()


def pipewire_nodes() -> str:
	"""Les nœuds PipeWire de MachinCast, de la session : « — » sans pw-cli."""
	if shutil.which("pw-cli") is None:
		return "—"
	listed = subprocess.run(["pw-cli", "ls", "Node"], capture_output=True, text=True, timeout=10, check=False).stdout
	found = 0
	for line in listed.splitlines():
		if "MachinCast" in line:
			found += 1
	return str(found)


def measure(label: str, monitor: Counted, seconds: float) -> None:
	"""Une phase : les relevés du moniteur et le retard d'un minuteur de Qt, pendant `seconds` secondes."""
	monitor.readings = monitor.changes = 0
	delays: list[float] = []
	expected = [time.monotonic() + TICK / 1000]

	def tick() -> None:
		now = time.monotonic()
		delays.append(max(0.0, now - expected[0]) * 1000)
		expected[0] = now + TICK / 1000

	timer = QTimer()
	timer.setInterval(TICK)
	timer.timeout.connect(tick)
	timer.start()
	start = time.monotonic()
	wait(seconds)
	timer.stop()
	elapsed = time.monotonic() - start
	average = 0.0
	if delays:
		average = sum(delays) / len(delays)
	print(
		f"| {label} | {monitor.readings / elapsed:.1f} | {monitor.changes / elapsed:.1f} | {average:.1f} |"
		f" {max(delays, default=0.0):.0f} | {threading.active_count()} | {pipewire_nodes()} |"
		f" {(monitor.unavailable) or ('ouvert')} |",
		flush=True,
	)


def listen(audio: Audio, monitor: Counted, listening: int, seconds: float) -> None:
	"""Une écoute de l'antenne sur la pré-écoute, comme la fenêtre de pré-écoute, puis son arrêt : mesurés tous deux."""
	player = Player(audio.output, audio.preview)
	player.load(Source("Antenne", "Antenne", True, None, audio))
	player.read()
	reading = QTimer()
	reading.setInterval(TICK)
	reading.timeout.connect(player.read_off)
	reading.start()
	measure(f"pendant l'écoute {listening}", monitor, seconds)
	reading.stop()
	player.halt()
	measure(f"après l'écoute {listening}", monitor, seconds)


def main() -> None:
	analyser = argparse.ArgumentParser(prog="python -m tests.vu_measures", description=__doc__.splitlines()[0])
	analyser.add_argument("--config", type=Path, default=None, help="configuration, machincast.toml par défaut")
	analyser.add_argument("--ecoutes", type=int, default=3, help="écoutes de l'antenne, 3 par défaut")
	analyser.add_argument("--duree", type=float, default=5.0, help="secondes de chaque phase, 5 par défaut")
	analyser.add_argument("--temoin", action="store_true", help="les mêmes phases, sans écouter l'antenne")
	options = analyser.parse_args()
	_application = QApplication([])
	audio = load(options.config).audio
	monitor = Counted(audio)
	monitor.start()
	wait(2)
	print(f"{Gst.version_string()}, sortie {audio.output}, antenne {audio.device}, pré-écoute {audio.preview}")
	print(
		"| phase | relevés/s | nouveaux/s | retard moyen (ms) | pire retard (ms) | fils | nœuds MachinCast | moniteur |"
	)
	print("| --- | --- | --- | --- | --- | --- | --- | --- |")
	measure("avant", monitor, options.duree)
	for listening in range(1, options.ecoutes + 1):
		if options.temoin:
			measure(f"témoin {listening}, sans écoute", monitor, options.duree)
			measure(f"témoin {listening}, après", monitor, options.duree)
		else:
			listen(audio, monitor, listening, options.duree)
	if monitor.unavailable is not None:
		print(f"Moniteur indisponible : {monitor.unavailable}")
	monitor.halt()


if __name__ == "__main__":
	main()
