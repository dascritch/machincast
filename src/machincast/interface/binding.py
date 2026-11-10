"""Écoute de l'antenne par un lien de PipeWire (https://github.com/dascritch/machincast/issues/24).

Quand l'antenne et la pré-écoute sont toutes deux sur PipeWire, la pré-écoute de l'antenne ne repasse pas le son par
GStreamer : elle relie, dans le graphe de PipeWire, les ports de monitoring du périphérique de l'antenne
(« <antenne>:monitor_FL ») aux entrées du périphérique de pré-écoute (« <preecoute>:playback_FL »). C'est une simple
copie du flux de sortie, que PipeWire cadence lui-même : rien ne se rejoue, rien ne saccade.

Les liens se font et se défont par pw-link (paquet pipewire-bin). Chaque canal va à l'entrée du même nom ; une entrée
unique (un casque mono) les reçoit tous ; sinon, les canaux vont aux entrées dans l'ordre.
"""

import subprocess

from machincast.i18n import _

COMMAND = "pw-link"
DELAY = 5.0
"""Secondes laissées à pw-link pour répondre."""

Pair = tuple[str, str]
"""Un port de sortie et le port d'entrée qu'il alimente."""


class ImpossibleBinding(Exception):
	"""Les liens ne peuvent pas se faire : le message dit pourquoi."""


def _pw_link(*arguments: str) -> str:
	try:
		result = subprocess.run(
			[COMMAND, *arguments], capture_output=True, text=True, timeout=DELAY, check=False, stdin=subprocess.DEVNULL
		)
	except FileNotFoundError:
		raise ImpossibleBinding(_("pw-link not found; install pipewire-bin.")) from None
	except subprocess.TimeoutExpired:
		raise ImpossibleBinding(_("pw-link does not answer.")) from None
	if result.returncode != 0:
		raise ImpossibleBinding(
			_("pw-link {list}: {stderr}").format(list=" ".join(arguments), stderr=result.stderr.strip())
		)
	return result.stdout


def _ports(option: str) -> list[str]:
	ports = []
	for line in _pw_link(option).splitlines():
		if line.strip():
			ports.append(line.strip())
	return ports


def pairs(on_air: str, preview: str) -> list[Pair]:
	"""Les liens qui copient l'antenne sur la pré-écoute ; lève ImpossibleBinding s'il n'y en a aucun."""
	outputs = []
	for port in _ports("-o"):
		if port.startswith(f"{on_air}:monitor_"):
			outputs.append(port)
	entries = []
	for port in _ports("-i"):
		if port.startswith(f"{preview}:playback_"):
			entries.append(port)
	if (not outputs) or (not entries):
		raise ImpossibleBinding(
			_("PipeWire has no monitoring port for {on_air}, or no input for {preview}.").format(
				on_air=on_air, preview=preview
			)
		)
	if len(entries) == 1:
		pairs = []
		for output in outputs:
			pairs.append((output, entries[0]))
		return pairs
	by_channel = {}
	for entry in entries:
		by_channel[entry.removeprefix(f"{preview}:playback_")] = entry
	found_list = []
	for output in outputs:
		if (channel := output.removeprefix(f"{on_air}:monitor_")) in by_channel:
			found_list.append((output, by_channel[channel]))
	if found_list:
		return found_list
	return list(zip(outputs, entries, strict=False))


def link(links: list[Pair]) -> None:
	"""Un lien qui existe déjà n'est pas une erreur."""
	for output, entry in links:
		try:
			_pw_link(output, entry)
		except ImpossibleBinding as error:
			if "exists" not in str(error):
				raise


def unbind(links: list[Pair]) -> None:
	"""Un lien déjà défait, ou un PipeWire arrêté, n'est pas une erreur."""

	def unlink(entry: str, output: str) -> None:
		try:
			_pw_link("-d", output, entry)
		except ImpossibleBinding:
			return

	for output, entry in links:
		unlink(entry, output)
