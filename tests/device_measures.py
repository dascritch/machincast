"""Mesure des arrêts net de la liste des périphériques audio (https://github.com/dascritch/machincast/issues/289,
https://github.com/dascritch/machincast/issues/305).

Avec GStreamer 1.28, Gst.DeviceMonitor.stop() tue parfois le processus (abort() dans GLib), ou ne rend jamais la
main. Ce script compare, sans le code de MachinCast, des façons de lister les périphériques de sortie audio, pour
choisir celle de machincast.audio, et la vérifier à chaque mise à jour de GStreamer :

	python -m tests.device_measures                      # 20 processus, 50 listes chacun, chaque façon
	python -m tests.device_measures -n 40 -r 100 --ways moniteur sondage
	python -m tests.device_measures --switch              # pendant que des sorties vont et viennent

Avec --switch, pendant la mesure, une sortie nulle « bascule » apparaît puis disparaît, et devient la sortie par
défaut, toutes les BASCULE secondes, par pactl (paquet pulseaudio-utils) : comme une sortie HDMI quand l'écran se met
en veille, ou au verrouillage de la session. Il faut PipeWire ou PulseAudio, avec pipewire-pulse pour PipeWire.

Façons :

- moniteur : un Gst.DeviceMonitor par liste, filtré sur Audio/Sink, démarré, lu, puis arrêté : celle de MachinCast
  jusqu'à https://github.com/dascritch/machincast/issues/289 ;
- moniteur-attendu : la même, qui attend le message DEVICE_MONITOR_STARTED avant de lire et d'arrêter : celle de
  MachinCast depuis https://github.com/dascritch/machincast/issues/289 ;
- moniteur-sans-arret : la première, sans stop() ;
- moniteur-unique : un seul moniteur, démarré une fois, lu à chaque liste, jamais arrêté : celle de MachinCast depuis
  https://github.com/dascritch/machincast/issues/305 ;
- sondage : sans moniteur, chaque fournisseur de périphériques audio est sondé (Gst.DeviceProvider.get_devices,
  sans start ni stop).

Chaque processus fait ses listes, puis sort normalement ; un processus tué par un signal, ou qui ne rend pas la main en
DELAI secondes, est compté. Le bilan donne le poste, la version de GStreamer, les serveurs audio qui tournent, et un
tableau Markdown.
"""

import argparse
import platform
import subprocess
import sys
import threading
import time
from collections import Counter

WAYS = ("moniteur", "moniteur-attendu", "moniteur-sans-arret", "moniteur-unique", "sondage")
CLASS = "Audio/Sink"
DELAY = 60.0
"""Secondes laissées à un processus pour toutes ses listes."""
SWITCH = 0.2
"""Secondes entre deux changements de sortie, avec --switch."""


def _gst():  # type: ignore[no-untyped-def]
	import gi

	gi.require_version("Gst", "1.0")
	from gi.repository import Gst

	Gst.init(None)
	return Gst


def _monitor(Gst, halt: bool, wait: bool = False):  # type: ignore[no-untyped-def]
	monitor = Gst.DeviceMonitor.new()
	monitor.add_filter(CLASS, None)
	if not monitor.start():
		return []
	started = getattr(Gst.MessageType, "DEVICE_MONITOR_STARTED", None)
	if (wait) and (started is not None):
		monitor.get_bus().timed_pop_filtered(5 * Gst.SECOND, started)
	appliances = list(monitor.get_devices())
	if halt:
		monitor.stop()
	return appliances


def _probe(Gst):  # type: ignore[no-untyped-def]
	appliances = []

	def handle_factory(factory) -> None:
		nonlocal appliances
		provider = factory.get()
		if provider is None:
			return
		appliance_list = []
		for appliance in provider.get_devices():
			if appliance.has_classes(CLASS):
				appliance_list.append(appliance)
		appliances += appliance_list

	for factory in Gst.DeviceProviderFactory.list_get_device_providers(Gst.Rank.MARGINAL):
		handle_factory(factory)
	return appliances


def work(way: str, repetitions: int) -> None:
	"""Dans un processus à part : les listes, puis une sortie normale."""
	Gst = _gst()
	unique = None
	for _ in range(repetitions):
		match way:
			case "moniteur":
				_monitor(Gst, halt=True)
			case "moniteur-attendu":
				_monitor(Gst, halt=True, wait=True)
			case "moniteur-sans-arret":
				_monitor(Gst, halt=False)
			case "moniteur-unique":
				if unique is None:
					unique = Gst.DeviceMonitor.new()
					unique.add_filter(CLASS, None)
					unique.start()
				list(unique.get_devices())
			case _:
				_probe(Gst)
	print(len(_probe(Gst)))


def _servers() -> str:
	run = []
	for server in ("pipewire", "pulseaudio"):
		if subprocess.run(["pgrep", "-x", server], capture_output=True).returncode == 0:
			run.append(server)
	return (", ".join(run)) or ("aucun")


def main() -> None:
	parts = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parts.add_argument("-n", "--processus", type=int, default=20)
	parts.add_argument("-r", "--repetitions", type=int, default=50)
	parts.add_argument("--ways", nargs="+", choices=WAYS, default=list(WAYS))
	parts.add_argument("--switch", action="store_true", help="des sorties vont et viennent pendant la mesure")
	parts.add_argument("--worker", choices=WAYS, help=argparse.SUPPRESS)
	options = parts.parse_args()
	if options.worker is not None:
		work(options.worker, options.repetitions)
		return
	Gst = _gst()
	print(f"Poste : {platform.freedesktop_os_release().get('PRETTY_NAME', '?')}, Python {platform.python_version()}")
	print(f"GStreamer : {Gst.version_string()} ; serveurs audio : {_servers()}")
	if not options.switch:
		switch = ""
	else:
		switch = ", pendant que des sorties vont et viennent"
	print(f"{options.process} processus de {options.repetitions} listes par façon{switch}\n")
	stop = threading.Event()
	if options.switch:
		threading.Thread(target=_switch, args=(stop,), daemon=True).start()
	print("| Façon | Sortis normalement | Tués par un signal | Sans réponse |")
	print("| --- | --- | --- | --- |")
	for way in options.ways:
		report: Counter[str] = Counter()

		def handle_item(_, report, way) -> None:
			command = [sys.executable, "-m", "tests.device_measures", "--worker", way]
			command += ["-r", str(options.repetitions)]
			try:
				finished = subprocess.run(command, capture_output=True, timeout=DELAY)
			except subprocess.TimeoutExpired:
				report["sans réponse"] += 1
				return
			chosen = "signal"
			if finished.returncode == 0:
				chosen = "normal"
			report[chosen] += 1

		for _ in range(options.process):
			handle_item(_, report, way)
		print(f"| {way} | {report['normal']} | {report['signal']} | {report['sans réponse']} |", flush=True)
	stop.set()


def _switch(stop: threading.Event) -> None:
	"""Une sortie nulle qui apparaît, devient la sortie par défaut, puis disparaît, jusqu'à la fin de la mesure."""
	default = subprocess.run(["pactl", "get-default-sink"], capture_output=True, text=True).stdout.strip()
	while not stop.is_set():
		module = subprocess.run(
			["pactl", "load-module", "module-null-sink", "sink_name=bascule"], capture_output=True, text=True
		).stdout.strip()
		subprocess.run(["pactl", "set-default-sink", "bascule"], capture_output=True)
		time.sleep(SWITCH)
		if default:
			subprocess.run(["pactl", "set-default-sink", default], capture_output=True)
		if module:
			subprocess.run(["pactl", "unload-module", module], capture_output=True)
		time.sleep(SWITCH)


if __name__ == "__main__":
	main()
