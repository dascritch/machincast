"""Le service de diffusion, machincast.service (https://github.com/dascritch/machincast/issues/22).

Installé sur demande par install.sh --service, il fait tourner Machin lecture sous le compte de MachinCast. Ce module
dit seulement son nom et son état, que lit systemctl sans aucun droit particulier ; l'interface le pilote
(machincast.interface.pilotage, https://github.com/dascritch/machincast/issues/25), et machincast.installation rédige
son unité et sa règle polkit.
"""

import subprocess
from dataclasses import dataclass

UNITE = "machincast.service"
"""L'unité systemd du service de lecture, celle que suit « Machin logs » : le même nom dans bin/Machin."""
DELAI = 5
"""Secondes laissées à systemctl pour dire l'état du service."""


@dataclass(frozen=True)
class EtatDuService:
	installe: bool
	actif: str
	"""ActiveState de systemd : « active », « inactive », « failed », « activating »…"""

	@property
	def en_marche(self) -> bool:
		return self.actif == "active"


ABSENT = EtatDuService(installe=False, actif="inactive")


def lire_l_etat() -> EtatDuService:
	"""L'état du service, d'après systemctl ; absent si systemctl manque, échoue ou ne connaît pas l'unité."""
	try:
		sortie = subprocess.run(
			["systemctl", "show", UNITE, "--property=LoadState,ActiveState"],
			capture_output=True,
			text=True,
			timeout=DELAI,
			check=False,
		)
	except (OSError, subprocess.TimeoutExpired):
		return ABSENT
	# Sans systemd, ou sans l'unité, systemctl ne dit rien sur sa sortie standard : le service est absent.
	proprietes = dict(ligne.split("=", 1) for ligne in sortie.stdout.splitlines() if "=" in ligne)
	if proprietes.get("LoadState") != "loaded":
		return ABSENT
	return EtatDuService(installe=True, actif=proprietes.get("ActiveState", "inactive"))
