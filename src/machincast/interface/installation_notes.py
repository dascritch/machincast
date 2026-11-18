"""Aide → « Votre installation… » et « Lien de l'équipe… » (https://github.com/dascritch/machincast/issues/451).

« Votre installation… » ouvre le document de l'équipe (machincast.notes), créé depuis son modèle s'il manque, toujours
dans un éditeur de texte, détaché de l'interface (https://github.com/dascritch/machincast/issues/491) : le premier
présent de EDITORS, sinon l'application que le bureau associe aux fichiers texte, lancée par gio. Jamais celle des
fichiers .md, qui est souvent une visionneuse, comme Okular sous KDE. Sans éditeur, la barre d'état le dit. « Lien de l'équipe… » ouvre interface.team_link dans le navigateur ; sans
adresse, l'entrée est inactive, et son infobulle dit où la donner.
"""

import os
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QProcess

from machincast import notes
from machincast.configuration import Interface, InvalidConfiguration, load
from machincast.i18n import _
from machincast.interface import dialogs

EDITORS = ("kate", "kwrite", "gnome-text-editor", "gedit", "mousepad", "xed", "pluma", "featherpad")
"""Les éditeurs de texte essayés, dans l'ordre : ceux de KDE, de GNOME, puis de Xfce, Cinnamon, MATE et LXQt."""
EDITOR_PATH: str | None = None
"""Les répertoires où chercher les éditeurs : le PATH par défaut ; ceux du scénario dans les tests, jamais les éditeurs
installés sur le poste des tests (https://github.com/dascritch/machincast/issues/508)."""
TEXT_TYPE = "text/plain"
"""Le type dont l'application associée ouvre le document, faute d'éditeur connu : celle des .md n'édite pas toujours."""
XDG_DELAY = 5
"""Secondes laissées à xdg-mime pour répondre."""
NOTES = _("Your installation…")
TEAM_LINK = _("Team link…")
WITHOUT_TEAM_LINK = _("Address to give in File → Interface preferences…, Interface page.")


def settings(configuration: Path | None) -> Interface:
	"""Les réglages de l'interface de sa configuration ; ceux par défaut sans elle, ou si elle ne se lit pas."""
	if configuration is None:
		return Interface()
	try:
		return load(configuration).interface
	except InvalidConfiguration:
		return Interface()


def open_notes(configuration: Path | None) -> str:
	"""Crée le document s'il manque, puis l'ouvre ; ce qu'en dit la barre d'état."""
	path = notes.document(settings(configuration).notes)
	try:
		created = notes.create(path)
	except OSError as error:
		return _("Your installation: {path} not created: {error}.").format(path=path, error=error)
	if not edit(path):
		return _("Your installation: no text editor found; the document is {path}.").format(path=path)
	if created:
		return _("Your installation: {path}, created from the template.").format(path=path)
	return _("Your installation: {path}.").format(path=path)


def edit(path: Path) -> bool:
	"""Ouvre le fichier dans un éditeur de texte, détaché : vrai si l'un d'eux a été lancé."""
	for editor in EDITORS:
		program = shutil.which(editor, path=EDITOR_PATH)
		if program is not None:
			started, _pid = QProcess.startDetached(program, [str(path)])
			if started:
				return True
	desktop = text_application()
	gio = shutil.which("gio")
	if (desktop is None) or (gio is None):
		return False
	started, _pid = QProcess.startDetached(gio, ["launch", str(desktop), str(path)])
	return started


def text_application() -> Path | None:
	"""Le fichier .desktop de l'application que le bureau associe aux fichiers texte (xdg-mime), cherché comme le veut
	la spécification XDG : dans XDG_DATA_HOME, puis dans chaque répertoire de XDG_DATA_DIRS."""
	try:
		result = subprocess.run(
			["xdg-mime", "query", "default", TEXT_TYPE], capture_output=True, text=True, timeout=XDG_DELAY, check=False
		)
	except (OSError, subprocess.SubprocessError):
		return None
	name = result.stdout.strip()
	if (result.returncode != 0) or (not name) or ("/" in name):
		return None
	home = os.environ.get("XDG_DATA_HOME", "")
	if not home:
		home = str(Path.home() / ".local" / "share")
	system = os.environ.get("XDG_DATA_DIRS", "")
	if not system:
		system = "/usr/local/share:/usr/share"
	for directory in [home, *system.split(":")]:
		desktop = Path(directory) / "applications" / name
		if (directory) and (desktop.is_file()):
			return desktop
	return None


def open_team_link(configuration: Path | None) -> None:
	address = settings(configuration).team_link
	if address is not None:
		dialogs.open_page(address)
