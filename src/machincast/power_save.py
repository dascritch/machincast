"""Les cartes son du poste d'antenne ne s'endorment jamais (https://github.com/dascritch/machincast/issues/499).

	python -m machincast.power_save enable|disable|wake [--root RACINE]

Deux réglages du système : l'option power_save=0 du module snd_hda_intel, les cartes son intégrées, et une règle udev
qui laisse éveillés les périphériques USB, cartes son USB comprises ; le poste est dédié à l'antenne. enable les
installe et les applique aussitôt ; wake les applique seulement, une fois installés par install.sh --service ;
disable les retire, et l'économie d'énergie revient au prochain redémarrage. Lancé en administrateur : par sudo depuis
install.sh, par pkexec depuis le menu « Maintenance » de l'interface. Aucun fichier sonore n'est touché.

Codes de sortie : 0 si les réglages sont faits ; 1 s'ils n'ont pas pu l'être.
"""

import argparse
import logging
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from machincast import created_files
from machincast import log as journal
from machincast.i18n import _

ROOT = Path("/")
"""La racine du système : une autre dans les scénarios."""
MODPROBE = Path("/etc/modprobe.d/machincast.conf")
USB_RULE = Path("/etc/udev/rules.d/50-machincast-usb.rules")
HDA_PARAMETER = Path("/sys/module/snd_hda_intel/parameters/power_save")
"""L'économie d'énergie de snd_hda_intel chargé : au bout de combien de secondes de silence la carte s'endort."""
UDEVADM_DELAY = 30
"""Secondes laissées à udevadm."""
EXECUTABLE = "machincast.power_save"

# Nom explicite : lancé par son script, ce module garde le journal « machincast ».
log = logging.getLogger("machincast.power_save")


def modprobe() -> str:
	"""Le réglage de snd_hda_intel : jamais d'économie d'énergie."""
	return """# The MachinCast on-air computer: the integrated sound cards never go to power saving
# (https://github.com/dascritch/machincast/issues/499).
# Installed by install.sh --service, or Maintenance menu of Machin interface; do not edit here.
options snd_hda_intel power_save=0
"""


def usb_rule() -> str:
	"""La règle udev : les périphériques USB, cartes son USB comprises, restent éveillés."""
	return """# The MachinCast on-air computer: USB devices, USB sound cards included, never autosuspend
# (https://github.com/dascritch/machincast/issues/499).
# Installed by install.sh --service, or Maintenance menu of Machin interface; do not edit here.
ACTION=="add|change", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on"
"""


SETTINGS: tuple[tuple[Path, Callable[[], str]], ...] = ((MODPROBE, modprobe), (USB_RULE, usb_rule))
"""Les fichiers des réglages, et ce qu'ils contiennent."""


def _in(root: Path, path: Path) -> Path:
	return root / path.relative_to("/")


def enabled(root: Path | None = None) -> bool:
	"""Les deux réglages sont installés, tels que MachinCast les rédige."""
	if root is None:
		root = ROOT
	for path, text in SETTINGS:
		file = _in(root, path)
		if (not file.is_file()) or (file.read_text(encoding="utf-8") != text()):
			return False
	return True


def _udevadm(*arguments: str) -> None:
	subprocess.run(["udevadm", *arguments], check=True, timeout=UDEVADM_DELAY)


def wake(root: Path) -> list[str]:
	"""Applique les réglages installés, sans attendre le redémarrage ; les messages à dire."""
	said = []
	parameter = _in(root, HDA_PARAMETER)
	if parameter.exists():
		parameter.write_text("0\n", encoding="utf-8")
	else:
		said.append(_("snd_hda_intel is not loaded: its setting will apply when it loads"))
	_udevadm("control", "--reload")
	_udevadm("trigger", "--subsystem-match=usb", "--action=change")
	said.append(_("sound cards always awake"))
	return said


def enable(root: Path) -> list[str]:
	"""Installe les deux réglages, puis les applique."""
	for path, text in SETTINGS:
		file = _in(root, path)
		file.parent.mkdir(parents=True, exist_ok=True)
		created_files.write_text(file, text())
	return wake(root)


def disable(root: Path) -> list[str]:
	"""Retire les deux réglages : l'économie d'énergie revient au prochain redémarrage."""
	for path, _text in SETTINGS:
		# Un réglage qu'il a lui-même écrit, dans /etc (SETTINGS), et seulement s'il est dans la liste.
		created_files.delete(_in(root, path))
	_udevadm("control", "--reload")
	return [_("settings removed: the power saving of the sound cards comes back at the next restart")]


ACTIONS: dict[str, Callable[[Path], list[str]]] = {"enable": enable, "disable": disable, "wake": wake}


def main(arguments: Sequence[str] | None = None) -> int:
	"""Lancé en administrateur, par sudo ou pkexec, sans configuration : ses messages vont sur ses sorties, et dans
	son journal s'il s'écrit."""
	journal.configure(EXECUTABLE)
	analyser = argparse.ArgumentParser(
		prog="python -m machincast.power_save",
		description=_("Keeps the sound cards of the on-air computer out of power saving."),
	)
	analyser.add_argument("action", choices=list(ACTIONS))
	analyser.add_argument("--root", type=Path, default=ROOT, help=_("root of the system, / by default"))
	analyser.add_argument(
		"--list", type=Path, default=None, dest="listing", help=_("list of the files created by MachinCast")
	)
	options = analyser.parse_args(arguments)
	created_files.LIST = options.listing
	try:
		said = ACTIONS[options.action](options.root)
	except (OSError, subprocess.SubprocessError) as error:
		log.error(_("sound cards not set: {error}").format(error=error))
		return 1
	for line in said:
		log.info(line)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
