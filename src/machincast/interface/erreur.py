"""Fenêtre d'erreur de Machin_interface sans base de données (https://github.com/dascritch/machincast/issues/23).

Sans base, l'interface n'a rien à montrer : une fenêtre dit pourquoi elle n'est pas utilisable, renvoie au document
INSTALL.md du répertoire de MachinCast, et propose de l'ouvrir. L'erreur de PostgreSQL est dans les détails.
"""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QWidget


class FenetreBaseInjoignable(QMessageBox):
	def __init__(self, base: str, socket: Path, erreur: str, installation: Path, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.installation = installation
		self.setIcon(QMessageBox.Icon.Critical)
		self.setWindowTitle("MachinCast : base de données injoignable")
		self.setText(
			f"L'interface de MachinCast n'est pas utilisable : elle n'accède pas à sa base de données « {base} »,"
			f" par la socket {socket}. Sans base, elle n'a ni la programmation, ni l'historique de diffusion à montrer."
		)
		self.setInformativeText(
			"Vérifiez que PostgreSQL est démarré, que la base existe et que ce compte peut s'y connecter, en suivant"
			f" le document {installation}, section « En cas de problème »."
		)
		self.setDetailedText(erreur)
		self.bouton_installation = self.addButton("Ouvrir INSTALL.md", QMessageBox.ButtonRole.ActionRole)
		self.setDefaultButton(self.addButton("Fermer", QMessageBox.ButtonRole.RejectRole))

	def montrer(self) -> None:
		self.exec()
		self.suite()

	def suite(self) -> None:
		"""Après la fenêtre : ouvre INSTALL.md si son bouton a été choisi."""
		if self.clickedButton() is self.bouton_installation:
			QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.installation)))
