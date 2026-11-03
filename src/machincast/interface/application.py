"""Application Qt de Machin_interface (https://github.com/dascritch/machincast/issues/23).

Les textes propres à Qt (boutons des fenêtres de dialogue, comme « Afficher les détails… ») sont en français, quelle
que soit la langue du poste : la traduction de Qt livrée avec PySide6 est chargée à la création de l'application.

Ses fenêtres portent l'icône de MachinCast, ou celle choisie dans les préférences
(https://github.com/dascritch/machincast/issues/111), et elle se réclame du raccourci machincast.desktop, qu'install.sh
met dans le menu des applications : sous Wayland, la barre des tâches y trouve son nom et son icône
(https://github.com/dascritch/machincast/issues/62).
"""

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator
from PySide6.QtGui import QIcon, QImageReader
from PySide6.QtWidgets import QApplication

from machincast import shortcut

TRANSLATION = "qtbase_fr"
ICON = shortcut.ICON
SHORTCUT = "machincast"
"""Nom du raccourci de l'interface, sans .desktop, tel qu'install.sh l'installe (machincast.shortcut.NAME)."""


def translate(application: QCoreApplication) -> bool:
	"""Charge la traduction française de Qt ; False si elle est introuvable, l'anglais reste alors."""
	translator = QTranslator(application)
	if not translator.load(TRANSLATION, QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
		return False
	return application.installTranslator(translator)


def application(name: str) -> QApplication:
	"""L'application Qt, créée au besoin, traduite en français."""
	existing = QApplication.instance()
	if isinstance(existing, QApplication):
		identify(existing)
		return existing
	created = QApplication([name])
	created.setApplicationName("MachinCast")
	identify(created)
	translate(created)
	return created


def readable(image: Path) -> bool:
	"""L'image existe, et Qt sait la lire."""
	return (image.is_file()) and (QImageReader(str(image)).canRead())


def identify(application: QApplication, icon: Path | None = None) -> bool:
	"""L'icône choisie, ou celle de MachinCast, pour ses fenêtres, et le nom de son raccourci pour la barre des
	tâches ; False si l'icône choisie est illisible ou introuvable, celle de MachinCast la remplace alors."""
	application.setDesktopFileName(SHORTCUT)
	image = ICON
	socket_jack = (icon is None) or (readable(icon))
	if (icon is not None) and (socket_jack):
		image = icon
	application.setWindowIcon(QIcon(str(image)))
	return socket_jack
