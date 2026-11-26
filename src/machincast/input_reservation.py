"""Les entrées audio réservées au service de diffusion, aussitôt (https://github.com/dascritch/machincast/issues/622).

	python -m machincast.input_reservation --config CONFIGURATION [--root RACINE]

Le service installé, ses entrées audio, audio.inputs de sa configuration, sont au PipeWire du service, comme la carte
de l'antenne : le fragment WirePlumber des sessions du poste les désactive (machincast.installation.wireplumber_desktop),
deux PipeWire n'ouvrant pas la même carte en même temps. Les Paramètres du service le réécrivent dès que les entrées
changent, sans relancer install.sh --service : cette commande, lancée par pkexec avec l'authentification d'un
administrateur, réécrit le fragment, puis relance le WirePlumber du service, qui les prend. L'interface relance
ensuite celui de sa session, qui les lâche. Aucun fichier sonore n'est touché.

Codes de sortie : 0 si les entrées sont réservées ; 1 si elles n'ont pas pu l'être ; 2 pour une configuration
invalide.
"""

import argparse
import logging
import subprocess
from collections.abc import Sequence
from pathlib import Path

from machincast import created_files
from machincast import log as journal
from machincast.configuration import InvalidConfiguration, load
from machincast.i18n import _
from machincast.installation import WIREPLUMBER_FRAGMENT, WIREPLUMBER_UNIT, wireplumber_desktop

ROOT = Path("/")
"""La racine du système : une autre dans les scénarios."""
DESKTOP_FRAGMENT = Path("/etc/wireplumber/wireplumber.conf.d") / WIREPLUMBER_FRAGMENT
"""Le fragment WirePlumber des sessions du poste, celui qu'install.sh --service installe (FICHIER_WIREPLUMBER_BUREAU)."""
SYSTEMCTL_DELAY = 30
"""Secondes laissées à systemctl."""
EXECUTABLE = "machincast.input_reservation"

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
log = logging.getLogger("machincast.input_reservation")


def reserve(configuration: Path, root: Path) -> list[str]:
	"""Réécrit le fragment des sessions du poste avec les entrées de cette configuration, puis relance le WirePlumber
	du service ; les messages à dire. Lève InvalidConfiguration, OSError ou SubprocessError."""
	audio = load(configuration).audio
	created_files.use(configuration)
	fragment = root / DESKTOP_FRAGMENT.relative_to("/")
	fragment.parent.mkdir(parents=True, exist_ok=True)
	created_files.write_text(fragment, wireplumber_desktop(audio))
	subprocess.run(["systemctl", "restart", WIREPLUMBER_UNIT], check=True, timeout=SYSTEMCTL_DELAY)
	if not audio.inputs:
		return [_("no audio input reserved for the broadcast service")]
	names = []
	for audio_input in audio.inputs:
		names.append(audio_input.name)
	return [_("audio inputs reserved for the broadcast service: {names}").format(names=", ".join(names))]


def main(arguments: Sequence[str] | None = None) -> int:
	"""Lancé en administrateur, par pkexec : ses messages vont sur ses sorties, et dans son journal s'il s'écrit."""
	journal.configure(EXECUTABLE)
	analyser = argparse.ArgumentParser(
		prog="python -m machincast.input_reservation",
		description=_("Reserves the audio inputs of the configuration for the broadcast service."),
	)
	analyser.add_argument("--config", type=Path, required=True, help=_("configuration of the broadcast service"))
	analyser.add_argument("--root", type=Path, default=ROOT, help=_("root of the system, / by default"))
	options = analyser.parse_args(arguments)
	try:
		said = reserve(options.config, options.root)
	except InvalidConfiguration as error:
		log.error(_("audio inputs not reserved: {error}").format(error=error))
		return 2
	except (OSError, subprocess.SubprocessError) as error:
		log.error(_("audio inputs not reserved: {error}").format(error=error))
		return 1
	for line in said:
		log.info(line)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
