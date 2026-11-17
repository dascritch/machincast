"""Aide → « Votre installation… » et « Lien de l'équipe… » (https://github.com/dascritch/machincast/issues/451).

« Votre installation… » ouvre le document de l'équipe (machincast.notes), créé depuis son modèle s'il manque, dans
l'éditeur de texte du poste : kwrite, sinon Gnome Text Editor, détaché de l'interface ; sans l'un ni l'autre, le
programme que le bureau associe au fichier. « Lien de l'équipe… » ouvre interface.team_link dans le navigateur ; sans
adresse, l'entrée est inactive, et son infobulle dit où la donner.
"""

import shutil
from pathlib import Path

from PySide6.QtCore import QProcess, QUrl

from machincast import notes
from machincast.configuration import Interface, InvalidConfiguration, load
from machincast.i18n import _
from machincast.interface import dialogs

EDITORS = ("kwrite", "gnome-text-editor")
"""Les éditeurs de texte essayés, dans l'ordre : celui de KDE, puis celui de GNOME."""
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
	opened = False
	for editor in EDITORS:
		program = shutil.which(editor)
		if (not opened) and (program is not None):
			opened, _pid = QProcess.startDetached(program, [str(path)])
	if not opened:
		dialogs.open_page(QUrl.fromLocalFile(str(path)).toString())
	if created:
		return _("Your installation: {path}, created from the template.").format(path=path)
	return _("Your installation: {path}.").format(path=path)


def open_team_link(configuration: Path | None) -> None:
	address = settings(configuration).team_link
	if address is not None:
		dialogs.open_page(address)
