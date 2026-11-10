"""Le niveau et la sourdine de la carte de l'antenne, dans le PipeWire du service (https://github.com/dascritch/machincast/issues/381).

En mode service, la carte de l'antenne est au PipeWire du service de diffusion, caché aux sessions du poste : le
réglage du son de la session ne la voit plus. L'interface la règle comme le ferait le compte machincast, par wpctl,
le client de WirePlumber, joint au PipeWire du service par sa socket (PIPEWIRE_REMOTE), que le compte de MachinCast
atteint par le groupe machincast :

- le nœud de la carte se trouve par son nom (node.name, audio.device), dans la sortie de pw-dump ;
- wpctl get-volume en lit le niveau (0 à 1) et la sourdine (« [MUTED] ») ;
- wpctl set-volume et set-mute les changent aussitôt, sans rien écrire dans la configuration.

Sans PipeWire du service joignable, ou sans le nœud, lève Unavailable, avec la raison.
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass

from machincast import service
from machincast.i18n import _

DUMP = "pw-dump"
CONTROL = "wpctl"
DELAY = 10
"""Secondes laissées à pw-dump et wpctl."""
_VOLUME = re.compile(r"Volume:\s*(?P<volume>[0-9.]+)(?P<muted>\s*\[MUTED\])?")


class Unavailable(Exception):
	"""Le niveau de la carte de l'antenne ne se lit ni ne se règle."""


@dataclass(frozen=True)
class Level:
	volume: float
	"""De 0 à 1 : 1 est le niveau nominal de la carte."""
	muted: bool


def _environment() -> dict[str, str]:
	"""L'environnement d'un client du PipeWire du service : sa socket, jamais celle de la session."""
	socket = service.pipewire_socket()
	if socket is None:
		raise Unavailable(_("the PipeWire of the broadcast service is not running"))
	environment = dict(os.environ)
	environment.pop("PIPEWIRE_RUNTIME_DIR", None)
	environment["PIPEWIRE_REMOTE"] = str(socket)
	return environment


def _run(arguments: list[str]) -> str:
	try:
		result = subprocess.run(
			arguments,
			env=_environment(),
			capture_output=True,
			text=True,
			timeout=DELAY,
			check=False,
			stdin=subprocess.DEVNULL,
		)
	except FileNotFoundError:
		raise Unavailable(_("{program} not found").format(program=arguments[0])) from None
	except subprocess.TimeoutExpired:
		raise Unavailable(_("{program} does not answer").format(program=arguments[0])) from None
	if result.returncode != 0:
		raise Unavailable((result.stderr.strip()) or (_("{program} failed").format(program=arguments[0])))
	return result.stdout


def node(name: str) -> int:
	"""L'identifiant du nœud de la carte, d'après son nom."""
	try:
		objects = json.loads(_run([DUMP]))
	except json.JSONDecodeError as error:
		raise Unavailable(str(error)) from None
	for item in objects:
		properties = item.get("info", {}).get("props", {})
		if (item.get("type") == "PipeWire:Interface:Node") and (properties.get("node.name") == name):
			return int(item["id"])
	raise Unavailable(_("no on-air card {name} in the PipeWire of the broadcast service").format(name=name))


def level(name: str) -> Level:
	match = _VOLUME.search(_run([CONTROL, "get-volume", str(node(name))]))
	if match is None:
		raise Unavailable(_("level of {name} unreadable").format(name=name))
	return Level(float(match.group("volume")), match.group("muted") is not None)


def set_volume(name: str, volume: float) -> None:
	_run([CONTROL, "set-volume", str(node(name)), f"{max(0.0, min(volume, 1.0)):.2f}"])


def set_muted(name: str, muted: bool) -> None:
	_run([CONTROL, "set-mute", str(node(name)), str(int(muted))])
