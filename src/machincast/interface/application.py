"""Application Qt de Machin_interface (https://github.com/dascritch/machincast/issues/23).

L'interface parle la langue de la session (https://github.com/dascritch/machincast/issues/360) : ses écrans .ui,
écrits en anglais, se traduisent par le catalogue gettext de MachinCast, et les textes propres à Qt (boutons des
fenêtres de dialogue, comme « Afficher les détails… ») par la traduction de Qt livrée avec PySide6, chargées à la
création de l'application.

Ses fenêtres portent l'icône de MachinCast, ou celle choisie dans les préférences
(https://github.com/dascritch/machincast/issues/111), et elle se réclame du raccourci machincast.desktop, qu'install.sh
met dans le menu des applications : sous Wayland, la barre des tâches y trouve son nom et son icône
(https://github.com/dascritch/machincast/issues/62).

Les lignes de ses tableaux alternent deux fonds, peu contrastés entre eux, recalculés d'après le thème
(machincast.interface.zebra, https://github.com/dascritch/machincast/issues/412).
"""

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator
from PySide6.QtGui import QIcon, QImageReader
from PySide6.QtWidgets import QApplication

from machincast import i18n, shortcut
from machincast.interface import zebra

QT_CATALOG = "qtbase"
"""La traduction de Qt, qtbase_<langue>.qm, dans le répertoire des traductions de PySide6."""
ICON = shortcut.ICON
SHORTCUT = "machincast"
"""Nom du raccourci de l'interface, sans .desktop, tel qu'install.sh l'installe (machincast.shortcut.NAME)."""


class ScreenCatalog(QTranslator):
	"""Les textes des écrans .ui, que pyside6-uic passe à QCoreApplication.translate, traduits par le catalogue gettext
	de MachinCast : un seul catalogue pour le code et les écrans."""

	def translate(  # type: ignore[override]
		self, context: str, source_text: str, disambiguation: str | None = None, n: int = -1
	) -> str | None:
		"""Le commentaire d'un texte du .ui (son attribut comment) est son contexte, msgctxt, dans le catalogue : il
		distingue un même mot anglais aux traductions différentes."""
		# None, une chaîne nulle pour Qt, dit que ce traducteur ne connaît pas le texte : il en essaie un autre, ou le
		# garde. Une chaîne vide serait une traduction, vide, que reçoivent aussi les textes internes de Qt.
		return i18n.known(source_text, (disambiguation) or (None))

	def isEmpty(self) -> bool:  # noqa: N802
		return False


_screens = ScreenCatalog()
"""Sans parent : elle dure autant que le programme, et aucun nettoyage des traducteurs de l'application ne l'emporte."""


def translate_screens(application: QCoreApplication) -> bool:
	"""Installe la traduction des écrans, une fois par application."""
	return application.installTranslator(_screens)


def translate(application: QCoreApplication) -> bool:
	"""Traduit l'application dans la langue de la session : ses écrans, et les textes de Qt. False si la traduction de
	Qt est introuvable : ses textes restent en anglais."""
	translate_screens(application)
	language = i18n.current()
	if language == i18n.SOURCE:
		return True
	translator = QTranslator(application)
	if not translator.load(f"{QT_CATALOG}_{language}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
		return False
	return application.installTranslator(translator)


def application(name: str) -> QApplication:
	"""L'application Qt, créée au besoin, traduite dans la langue de la session."""
	existing = QApplication.instance()
	if isinstance(existing, QApplication):
		identify(existing)
		zebra.install(existing)
		return existing
	created = QApplication([name])
	created.setApplicationName("MachinCast")
	identify(created)
	translate(created)
	zebra.install(created)
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
