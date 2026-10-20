"""Journal d'une indexation lancée depuis l'interface (https://github.com/dascritch/machincast/issues/120).

Une fenêtre à part, qui montre ligne par ligne ce que Machin indexation écrirait dans le terminal, au fil de
l'indexation (machincast.interface.indexation) : chaque sonore indexé avec son statut, les anomalies, puis le bilan.
Elle s'ouvre au lancement de l'indexation, et se vide à chaque nouveau lancement ; à la fin, elle conclut par le bilan
et le nombre d'anomalies. Elle se ferme d'elle-même avec la fenêtre de l'interface.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QWidget

from machincast.interface.ui.journal_indexation import Ui_FenetreJournal


class FenetreJournal(QWidget):
	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent, Qt.WindowType.Window)
		self.ui = Ui_FenetreJournal()
		self.ui.setupUi(self)
		self.ui.journal.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
		self.ui.fermer.clicked.connect(self.close)
		self.anomalies: list[str] = []
		"""Les lignes d'anomalie et d'erreur de l'indexation en cours."""

	def commencer(self, titre: str) -> None:
		"""Une nouvelle indexation : le journal se vide, et la fenêtre s'ouvre au premier plan."""
		self.setWindowTitle(titre)
		self.ui.journal.clear()
		self.anomalies = []
		self.ui.conclusion.setText(f"{titre} en cours…")
		self.show()
		self.raise_()

	def ajouter(self, texte: str, anomalie: bool) -> None:
		self.ui.journal.appendPlainText(texte)
		if anomalie:
			self.anomalies.append(texte)

	def conclure(self, bilan: str) -> None:
		texte = bilan
		nombre = len(self.anomalies)
		if nombre == 1:
			texte = f"{bilan} 1 anomalie, dans le journal ci-dessus."
		elif nombre > 1:
			texte = f"{bilan} {nombre} anomalies, dans le journal ci-dessus."
		self.ui.conclusion.setText(texte)

	def lignes(self) -> list[str]:
		return self.ui.journal.toPlainText().splitlines()
