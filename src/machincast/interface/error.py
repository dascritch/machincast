"""Fenêtre d'erreur de Machin_interface sans base de données (https://github.com/dascritch/machincast/issues/23).

Sans base, l'interface n'a rien à montrer : une fenêtre dit pourquoi elle n'est pas utilisable, renvoie au document
INSTALL.md du répertoire de MachinCast, et propose de l'ouvrir. L'erreur de PostgreSQL est dans les détails.
"""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QWidget

from machincast.i18n import _


class UnreachableDatabaseWindow(QMessageBox):
	def __init__(
		self, database: str, socket: Path, error: str, installation: Path, parent: QWidget | None = None
	) -> None:
		super().__init__(parent)
		self.installation = installation
		self.setIcon(QMessageBox.Icon.Critical)
		self.setWindowTitle(_("MachinCast: database unreachable"))
		self.setText(
			_(
				"The MachinCast interface cannot be used: it does not reach its database “{database}” "
				"through the socket {socket}. Without a database, it has neither the programming nor the "
				"broadcast history to show."
			).format(database=database, socket=socket)
		)
		self.setInformativeText(
			_(
				"Check that PostgreSQL is started, that the database exists and that this account can "
				"connect to it, following the document {installation}, section “Troubleshooting”."
			).format(installation=installation)
		)
		self.setDetailedText(error)
		self.installation_button = self.addButton(_("Open INSTALL.md"), QMessageBox.ButtonRole.ActionRole)
		self.setDefaultButton(self.addButton(_("Close"), QMessageBox.ButtonRole.RejectRole))

	def display(self) -> None:
		self.exec()
		self.remainder()

	def remainder(self) -> None:
		"""Après la fenêtre : ouvre INSTALL.md si son bouton a été choisi."""
		if self.clickedButton() is self.installation_button:
			QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.installation)))
