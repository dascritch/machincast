"""Mesure des arrêts net de la liste des périphériques audio (https://github.com/dascritch/machincast/issues/289,
https://github.com/dascritch/machincast/issues/305).

Avec GStreamer 1.28, Gst.DeviceMonitor.stop() tue parfois le processus (abort() dans GLib), ou ne rend jamais la
main. Ce script compare, sans le code de MachinCast, des façons de lister les périphériques de sortie audio, pour
choisir celle de machincast.audio, et la vérifier à chaque mise à jour de GStreamer :

	python -m tests.mesures_peripheriques                      # 20 processus, 50 listes chacun, chaque façon
	python -m tests.mesures_peripheriques -n 40 -r 100 --facons moniteur sondage
	python -m tests.mesures_peripheriques --bascule              # pendant que des sorties vont et viennent

Avec --bascule, pendant la mesure, une sortie nulle « bascule » apparaît puis disparaît, et devient la sortie par
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

FACONS = ("moniteur", "moniteur-attendu", "moniteur-sans-arret", "moniteur-unique", "sondage")
CLASSE = "Audio/Sink"
DELAI = 60.0
"""Secondes laissées à un processus pour toutes ses listes."""
BASCULE = 0.2
"""Secondes entre deux changements de sortie, avec --bascule."""


def _gst():  # type: ignore[no-untyped-def]
	import gi

	gi.require_version("Gst", "1.0")
	from gi.repository import Gst

	Gst.init(None)
	return Gst


def _moniteur(Gst, arreter: bool, attendre: bool = False):  # type: ignore[no-untyped-def]
	moniteur = Gst.DeviceMonitor.new()
	moniteur.add_filter(CLASSE, None)
	if not moniteur.start():
		return []
	demarre = getattr(Gst.MessageType, "DEVICE_MONITOR_STARTED", None)
	if (attendre) and (demarre is not None):
		moniteur.get_bus().timed_pop_filtered(5 * Gst.SECOND, demarre)
	appareils = list(moniteur.get_devices())
	if arreter:
		moniteur.stop()
	return appareils


def _sondage(Gst):  # type: ignore[no-untyped-def]
	appareils = []
	for fabrique in Gst.DeviceProviderFactory.list_get_device_providers(Gst.Rank.MARGINAL):
		fournisseur = fabrique.get()
		if fournisseur is None:
			continue
		appareils += [appareil for appareil in fournisseur.get_devices() if appareil.has_classes(CLASSE)]
	return appareils


def travailler(facon: str, repetitions: int) -> None:
	"""Dans un processus à part : les listes, puis une sortie normale."""
	Gst = _gst()
	unique = None
	for _ in range(repetitions):
		if facon == "moniteur":
			_moniteur(Gst, arreter=True)
		elif facon == "moniteur-attendu":
			_moniteur(Gst, arreter=True, attendre=True)
		elif facon == "moniteur-sans-arret":
			_moniteur(Gst, arreter=False)
		elif facon == "moniteur-unique":
			if unique is None:
				unique = Gst.DeviceMonitor.new()
				unique.add_filter(CLASSE, None)
				unique.start()
			list(unique.get_devices())
		else:
			_sondage(Gst)
	print(len(_sondage(Gst)))


def _serveurs() -> str:
	tournent = []
	for serveur in ("pipewire", "pulseaudio"):
		if subprocess.run(["pgrep", "-x", serveur], capture_output=True).returncode == 0:
			tournent.append(serveur)
	return (", ".join(tournent)) or ("aucun")


def main() -> None:
	parties = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parties.add_argument("-n", "--processus", type=int, default=20)
	parties.add_argument("-r", "--repetitions", type=int, default=50)
	parties.add_argument("--facons", nargs="+", choices=FACONS, default=list(FACONS))
	parties.add_argument("--bascule", action="store_true", help="des sorties vont et viennent pendant la mesure")
	parties.add_argument("--travailleur", choices=FACONS, help=argparse.SUPPRESS)
	options = parties.parse_args()
	if options.travailleur is not None:
		travailler(options.travailleur, options.repetitions)
		return
	Gst = _gst()
	print(f"Poste : {platform.freedesktop_os_release().get('PRETTY_NAME', '?')}, Python {platform.python_version()}")
	print(f"GStreamer : {Gst.version_string()} ; serveurs audio : {_serveurs()}")
	bascule = "" if not options.bascule else ", pendant que des sorties vont et viennent"
	print(f"{options.processus} processus de {options.repetitions} listes par façon{bascule}\n")
	arret = threading.Event()
	if options.bascule:
		threading.Thread(target=_basculer, args=(arret,), daemon=True).start()
	print("| Façon | Sortis normalement | Tués par un signal | Sans réponse |")
	print("| --- | --- | --- | --- |")
	for facon in options.facons:
		bilan: Counter[str] = Counter()
		for _ in range(options.processus):
			commande = [sys.executable, "-m", "tests.mesures_peripheriques", "--travailleur", facon]
			commande += ["-r", str(options.repetitions)]
			try:
				fini = subprocess.run(commande, capture_output=True, timeout=DELAI)
			except subprocess.TimeoutExpired:
				bilan["sans réponse"] += 1
				continue
			bilan["normal" if fini.returncode == 0 else "signal"] += 1
		print(f"| {facon} | {bilan['normal']} | {bilan['signal']} | {bilan['sans réponse']} |", flush=True)
	arret.set()


def _basculer(arret: threading.Event) -> None:
	"""Une sortie nulle qui apparaît, devient la sortie par défaut, puis disparaît, jusqu'à la fin de la mesure."""
	defaut = subprocess.run(["pactl", "get-default-sink"], capture_output=True, text=True).stdout.strip()
	while not arret.is_set():
		module = subprocess.run(
			["pactl", "load-module", "module-null-sink", "sink_name=bascule"], capture_output=True, text=True
		).stdout.strip()
		subprocess.run(["pactl", "set-default-sink", "bascule"], capture_output=True)
		time.sleep(BASCULE)
		if defaut:
			subprocess.run(["pactl", "set-default-sink", defaut], capture_output=True)
		if module:
			subprocess.run(["pactl", "unload-module", module], capture_output=True)
		time.sleep(BASCULE)


if __name__ == "__main__":
	main()
