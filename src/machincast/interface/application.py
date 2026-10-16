"""Application Qt de Machin_interface (https://github.com/dascritch/machincast/issues/23).

Les textes propres à Qt (boutons des fenêtres de dialogue, comme « Afficher les détails… ») sont en français, quelle
que soit la langue du poste : la traduction de Qt livrée avec PySide6 est chargée à la création de l'application.
"""

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator
from PySide6.QtWidgets import QApplication

TRADUCTION = "qtbase_fr"


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
		return existante
	creee = QApplication([nom])
	creee.setApplicationName("MachinCast")
	traduire(creee)
	return creee
