"""Le service de diffusion, machincast.service (https://github.com/dascritch/machincast/issues/22).

Installé sur demande par install.sh --service, il fait tourner Machin player sous le compte de MachinCast. Ce module
dit seulement son nom et son état, que lit systemctl sans aucun droit particulier ; l'interface le pilote
(machincast.interface.control, https://github.com/dascritch/machincast/issues/25), et machincast.installation rédige
son unité et sa règle polkit.
"""

import subprocess
from dataclasses import dataclass

UNIT = "machincast.service"
"""L'unité systemd du service de lecture, celle que suit « Machin logs » : le même nom dans bin/Machin."""
DELAY = 5
"""Secondes laissées à systemctl pour dire l'état du service."""


@dataclass(frozen=True)
class ServiceState:
	installed: bool
	active: str
	"""ActiveState de systemd : « active », « inactive », « failed », « activating »…"""

	@property
	def running(self) -> bool:
		return self.active == "active"


ABSENT = ServiceState(installed=False, active="inactive")


def read_state() -> ServiceState:
	"""L'état du service, d'après systemctl ; absent si systemctl manque, échoue ou ne connaît pas l'unité."""
	try:
		output = subprocess.run(
			["systemctl", "show", UNIT, "--property=LoadState,ActiveState"],
			capture_output=True,
			text=True,
			timeout=DELAY,
			check=False,
		)
	except (OSError, subprocess.TimeoutExpired):
		return ABSENT
	# Sans systemd, ou sans l'unité, systemctl ne dit rien sur sa sortie standard : le service est absent.
	properties = dict(line.split("=", 1) for line in output.stdout.splitlines() if "=" in line)
	if properties.get("LoadState") != "loaded":
		return ABSENT
	return ServiceState(installed=True, active=properties.get("ActiveState", "inactive"))
