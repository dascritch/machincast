"""Raccourci de l'interface, machincast.desktop (https://github.com/dascritch/machincast/issues/62).

rediger donne son texte (Desktop Entry Specification 1.5) : Machin interface, lancé depuis le répertoire de MachinCast
(clé Path), avec l'icône de la configuration (interface.icone, https://github.com/dascritch/machincast/issues/111), ou
celle de MachinCast, ICONE, si aucune n'est choisie ou si l'image choisie n'existe plus. install.sh l'installe dans le
menu des applications du compte (dossier_du_menu) et, sur demande, sur son bureau (dossier_du_bureau), par
machincast.installation raccourci.

reecrire est appelé par les préférences de l'interface quand l'icône change : sous Wayland, la barre des tâches et le
menu prennent l'icône du raccourci, et non celle de la fenêtre. Il ne réécrit que les raccourcis déjà installés, en
gardant leurs droits (exécutable sur le bureau, pour Plasma), et n'en crée jamais.

Les tests remplacent DOSSIER_MENU et DOSSIER_BUREAU par des dossiers du test : jamais les raccourcis du compte.
"""

import os
import shutil
import subprocess
from pathlib import Path

from machincast.configuration import REPERTOIRE_PROJET

NOM = "machincast.desktop"
"""Le nom du raccourci ; l'interface s'en réclame (setDesktopFileName), sans « .desktop »."""
ICONE = Path(__file__).resolve().parent / "interface" / "machincast.svg"
"""L'icône de MachinCast, dans le paquet : celle du raccourci et des fenêtres, sauf icône choisie."""
DOSSIER_MENU: Path | None = None
"""Le dossier du menu des applications ; None : celui du compte, sous $XDG_DATA_HOME."""
DOSSIER_BUREAU: Path | None = None
"""Le dossier du bureau ; None : celui du compte, que donne xdg-user-dir."""
RESERVES = frozenset(" \t\n\"'\\><~|&;$*?#()`")
"""Caractères qui imposent de citer un argument de la clé Exec (Desktop Entry Specification, « The Exec key »)."""
LIEUX = {"menu": "dans le menu des applications", "bureau": "sur le bureau"}
"""Les lieux d'un raccourci, pour les messages."""


def _argument(texte: str) -> str:
	"""Un argument de la clé Exec, cité s'il contient un caractère réservé ; dans les guillemets, « " », « ` », « $ » et
	« \\ » sont précédés d'une barre oblique inversée."""
	if not any(caractere in RESERVES for caractere in texte):
		return texte
	cite = "".join(f"\\{caractere}" if caractere in '"`$\\' else caractere for caractere in texte)
	return f'"{cite}"'


def _chaine(texte: str) -> str:
	"""Une valeur de type chaîne d'une entrée .desktop : la barre oblique inversée y est doublée."""
	return texte.replace("\\", "\\\\")


def icone_utilisable(icone: Path | None) -> bool:
	"""L'icône choisie existe ; sans icône choisie, c'est celle de MachinCast, toujours là."""
	return (icone is None) or (icone.is_file())


def rediger(repertoire: Path = REPERTOIRE_PROJET, icone: Path | None = None) -> str:
	"""Le raccourci de l'interface. StartupWMClass est le nom de l'application, que Qt donne pour classe à ses
	fenêtres sous X11 ; sous Wayland, l'application se réclame du raccourci par son nom, machincast."""
	commande = f"{_argument(str(repertoire / 'bin' / 'Machin'))} interface".replace("%", "%%")
	image = repertoire / ICONE.relative_to(REPERTOIRE_PROJET)
	if (icone is not None) and (icone_utilisable(icone)):
		image = icone
	return f"""# Raccourci de l'interface de MachinCast (https://github.com/dascritch/machincast/issues/62).
# Installé par install.sh, réécrit par les préférences de l'interface quand son icône change ; ne pas modifier ici.
[Desktop Entry]
Type=Application
Version=1.5
Name=MachinCast
GenericName=Diffusion radio automatisée
Comment=Programmer l'antenne et suivre la diffusion
Exec={_chaine(commande)}
Path={_chaine(str(repertoire))}
Icon={_chaine(str(image))}
Terminal=false
Categories=AudioVideo;Audio;
Keywords=radio;antenne;diffusion;programmation;
StartupNotify=true
StartupWMClass=MachinCast
"""


def dossier_du_menu() -> Path:
	"""$XDG_DATA_HOME/applications, ou ~/.local/share/applications."""
	if DOSSIER_MENU is not None:
		return DOSSIER_MENU
	donnees = os.environ.get("XDG_DATA_HOME", "")
	if donnees == "":
		return Path.home() / ".local" / "share" / "applications"
	return Path(donnees) / "applications"


def dossier_du_bureau() -> Path | None:
	"""Le bureau du compte, « Bureau » en français, que donne xdg-user-dir ; None sans bureau."""
	if DOSSIER_BUREAU is not None:
		return DOSSIER_BUREAU
	commande = shutil.which("xdg-user-dir")
	if commande is None:
		return None
	try:
		sortie = subprocess.run([commande, "DESKTOP"], capture_output=True, text=True, timeout=10, check=True).stdout
	except (OSError, subprocess.SubprocessError):
		return None
	dossier = Path(sortie.strip())
	# Sans bureau configuré, xdg-user-dir répond le dossier personnel.
	if (sortie.strip() == "") or (dossier == Path.home()):
		return None
	return dossier


def installes() -> dict[str, Path]:
	"""Les raccourcis de MachinCast déjà installés, par lieu : « menu », « bureau »."""
	trouves = {"menu": dossier_du_menu() / NOM}
	bureau = dossier_du_bureau()
	if bureau is not None:
		trouves["bureau"] = bureau / NOM
	return {lieu: chemin for lieu, chemin in trouves.items() if chemin.is_file()}


def reecrire(icone: Path | None) -> list[str]:
	"""Réécrit les raccourcis déjà installés avec l'icône donnée, en gardant leurs droits ; renvoie leurs lieux,
	« dans le menu des applications », « sur le bureau ». Lève OSError si l'un ne peut pas être écrit."""
	texte = rediger(icone=icone)
	lieux = []
	for lieu, chemin in installes().items():
		# Un raccourci de MachinCast, réécrit en place : ses droits restent, exécutable compris.
		chemin.write_text(texte, encoding="utf-8")
		lieux.append(LIEUX[lieu])
	return lieux
