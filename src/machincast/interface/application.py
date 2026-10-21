"""Application Qt de Machin_interface (https://github.com/dascritch/machincast/issues/23).

Les textes propres à Qt (boutons des fenêtres de dialogue, comme « Afficher les détails… ») sont en français, quelle
que soit la langue du poste : la traduction de Qt livrée avec PySide6 est chargée à la création de l'application.

Ses fenêtres portent l'icône de MachinCast, et elle se réclame du raccourci machincast.desktop, qu'install.sh met dans
le menu des applications : sous Wayland, la barre des tâches y trouve son nom et son icône
(https://github.com/dascritch/machincast/issues/62).
"""

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

TRADUCTION = "qtbase_fr"
ICONE = Path(__file__).with_name("machincast.svg")
RACCOURCI = "machincast"
"""Nom du raccourci de l'interface, sans .desktop, tel qu'install.sh l'installe."""


def traduire(application: QCoreApplication) -> bool:
	"""Charge la traduction française de Qt ; False si elle est introuvable, l'anglais reste alors."""
	traducteur = QTranslator(application)
	if not traducteur.load(TRADUCTION, QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
		return False
	return application.installTranslator(traducteur)


def application(nom: str) -> QApplication:
	"""L'application Qt, créée au besoin, traduite en français."""
	existante = QApplication.instance()
	if isinstance(existante, QApplication):
		identifier(existante)
		return existante
	creee = QApplication([nom])
	creee.setApplicationName("MachinCast")
	identifier(creee)
	traduire(creee)
	return creee


def identifier(application: QApplication) -> None:
	"""L'icône de MachinCast pour ses fenêtres, et le nom de son raccourci pour la barre des tâches."""
	application.setDesktopFileName(RACCOURCI)
	application.setWindowIcon(QIcon(str(ICONE)))
