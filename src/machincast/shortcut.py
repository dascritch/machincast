"""Raccourci de l'interface, machincast.desktop (https://github.com/dascritch/machincast/issues/62).

rediger donne son texte (Desktop Entry Specification 1.5) : Machin interface, lancé depuis le répertoire de MachinCast
(clé Path), avec l'icône de la configuration (interface.icon, https://github.com/dascritch/machincast/issues/111), ou
celle de MachinCast, ICONE, si aucune n'est choisie ou si l'image choisie n'existe plus. install.sh l'installe dans le
menu des applications du compte (menu_folder) et, sur demande, sur son bureau (desktop_folder), par
machincast.installation shortcut.

reecrire est appelé par les préférences de l'interface quand l'icône change : sous Wayland, la barre des tâches et le
menu prennent l'icône du raccourci, et non celle de la fenêtre. Il ne réécrit que les raccourcis déjà installés, en
gardant leurs droits (exécutable sur le bureau, pour Plasma), et n'en crée jamais.

Les tests remplacent MENU_FOLDER et DESKTOP_FOLDER par des dossiers du test : jamais les raccourcis du compte.
"""

import os
import shutil
import subprocess
from pathlib import Path

from machincast.configuration import PROJECT_DIRECTORY

NAME = "machincast.desktop"
"""Le nom du raccourci ; l'interface s'en réclame (setDesktopFileName), sans « .desktop »."""
ICON = Path(__file__).resolve().parent / "interface" / "machincast.png"
"""L'icône de MachinCast, dans le paquet : celle du raccourci et des fenêtres, sauf icône choisie. C'est le logo des
équipes techniques de la radio qui commissionne MachinCast (https://github.com/dascritch/machincast/issues/213)."""
MENU_FOLDER: Path | None = None
"""Le dossier du menu des applications ; None : celui du compte, sous $XDG_DATA_HOME."""
DESKTOP_FOLDER: Path | None = None
"""Le dossier du bureau ; None : celui du compte, que donne xdg-user-dir."""
RESERVED_LIST = frozenset(" \t\n\"'\\><~|&;$*?#()`")
"""Caractères qui imposent de citer un argument de la clé Exec (Desktop Entry Specification, « The Exec key »)."""
PLACES = {"menu": "dans le menu des applications", "bureau": "sur le bureau"}
"""Les lieux d'un raccourci, pour les messages."""


def _argument(text: str) -> str:
	"""Un argument de la clé Exec, cité s'il contient un caractère réservé ; dans les guillemets, « " », « ` », « $ » et
	« \\ » sont précédés d'une barre oblique inversée."""
	if not any(character in RESERVED_LIST for character in text):
		return text
	cites = "".join(f"\\{character}" if character in '"`$\\' else character for character in text)
	return f'"{cites}"'


def _string(text: str) -> str:
	"""Une valeur de type chaîne d'une entrée .desktop : la barre oblique inversée y est doublée."""
	return text.replace("\\", "\\\\")


def usable_icon(icon: Path | None) -> bool:
	"""L'icône choisie existe ; sans icône choisie, c'est celle de MachinCast, toujours là."""
	return (icon is None) or (icon.is_file())


def write(directory: Path = PROJECT_DIRECTORY, icon: Path | None = None) -> str:
	"""Le raccourci de l'interface. StartupWMClass est le nom de l'application, que Qt donne pour classe à ses
	fenêtres sous X11 ; sous Wayland, l'application se réclame du raccourci par son nom, machincast."""
	command = f"{_argument(str(directory / 'bin' / 'Machin'))} interface".replace("%", "%%")
	image = directory / ICON.relative_to(PROJECT_DIRECTORY)
	if (icon is not None) and (usable_icon(icon)):
		image = icon
	return f"""# Raccourci de l'interface de MachinCast (https://github.com/dascritch/machincast/issues/62).
# Installé par install.sh, réécrit par les préférences de l'interface quand son icône change ; ne pas modifier ici.
[Desktop Entry]
Type=Application
Version=1.5
Name=MachinCast
GenericName=Diffusion radio automatisée
Comment=Programmer l'antenne et suivre la diffusion
Exec={_string(command)}
Path={_string(str(directory))}
Icon={_string(str(image))}
Terminal=false
Categories=AudioVideo;Audio;
Keywords=radio;antenne;diffusion;programmation;
StartupNotify=true
StartupWMClass=MachinCast
"""


def menu_folder() -> Path:
	"""$XDG_DATA_HOME/applications, ou ~/.local/share/applications."""
	if MENU_FOLDER is not None:
		return MENU_FOLDER
	data = os.environ.get("XDG_DATA_HOME", "")
	if data == "":
		return Path.home() / ".local" / "share" / "applications"
	return Path(data) / "applications"


def desktop_folder() -> Path | None:
	"""Le bureau du compte, « Bureau » en français, que donne xdg-user-dir ; None sans bureau."""
	if DESKTOP_FOLDER is not None:
		return DESKTOP_FOLDER
	command = shutil.which("xdg-user-dir")
	if command is None:
		return None
	try:
		output = subprocess.run([command, "DESKTOP"], capture_output=True, text=True, timeout=10, check=True).stdout
	except (OSError, subprocess.SubprocessError):
		return None
	folder = Path(output.strip())
	# Sans bureau configuré, xdg-user-dir répond le dossier personnel.
	if (output.strip() == "") or (folder == Path.home()):
		return None
	return folder


def installed_list() -> dict[str, Path]:
	"""Les raccourcis de MachinCast déjà installés, par lieu : « menu », « bureau »."""
	found_list = {"menu": menu_folder() / NAME}
	desktop = desktop_folder()
	if desktop is not None:
		found_list["bureau"] = desktop / NAME
	return {place: path for place, path in found_list.items() if path.is_file()}


def rewrite(icon: Path | None) -> list[str]:
	"""Réécrit les raccourcis déjà installés avec l'icône donnée, en gardant leurs droits ; renvoie leurs lieux,
	« dans le menu des applications », « sur le bureau ». Lève OSError si l'un ne peut pas être écrit."""
	text = write(icon=icon)
	places = []
	for place, path in installed_list().items():
		# Un raccourci de MachinCast, réécrit en place : ses droits restent, exécutable compris.
		path.write_text(text, encoding="utf-8")
		places.append(PLACES[place])
	return places
