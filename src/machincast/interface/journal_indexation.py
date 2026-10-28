"""Journal d'une indexation lancée depuis l'interface (https://github.com/dascritch/machincast/issues/120).

La fenêtre de Machin indexation --fenetre, dans un processus à part de l'interface (machincast.interface.indexation) :
elle montre ligne par ligne ce que Machin indexation écrirait dans le terminal, au fil de l'indexation, chaque sonore
indexé avec son statut, les anomalies, puis le bilan. À la fin, elle conclut par le bilan et le nombre d'anomalies.

La fermer pendant l'indexation demande s'il faut l'arrêter : elle s'arrête alors après le fichier en cours, et le
travail fait est gardé ; sinon, la fenêtre reste ouverte. Une fois l'indexation finie, elle se ferme sans question,
et le processus s'arrête.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFontDatabase
from PySide6.QtWidgets import QWidget

from machincast.configuration import SEUIL_DE_SILENCE
from machincast.indexation.__main__ import EXECUTABLE
from machincast.interface import dialogues
from machincast.interface.application import application
from machincast.interface.indexation import TITRES, Indexation
from machincast.interface.ui.journal_indexation import Ui_FenetreJournal


class FenetreJournal(QWidget):
	def __init__(
		self,
		socket: Path,
		base: str,
		audit_complet: bool,
		parent: QWidget | None = None,
		seuil_silences: float = SEUIL_DE_SILENCE,
	) -> None:
		super().__init__(parent, Qt.WindowType.Window)
		self.ui = Ui_FenetreJournal()
		self.ui.setupUi(self)
		self.ui.journal.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
		self.ui.fermer.clicked.connect(self.close)
		self.audit_complet = audit_complet
		self.setWindowTitle(TITRES[audit_complet])
		self.anomalies: list[str] = []
		"""Les lignes d'anomalie et d'erreur de l'indexation."""
		self.indexation = Indexation(socket, base, self, seuil_silences)
		self.indexation.ligne.connect(self.ajouter)
		self.indexation.termine.connect(self.conclure)

	def lancer(self) -> None:
		"""Ouvre la fenêtre, puis lance l'indexation."""
		self.ui.conclusion.setText(f"{self.windowTitle()} en cours…")
		self.show()
		self.indexation.lancer(self.audit_complet)

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

	def closeEvent(self, evenement: QCloseEvent) -> None:
		"""Pendant l'indexation, demande s'il faut l'arrêter ; sinon, la fenêtre reste ouverte."""
		if self.indexation.en_cours():
			if not dialogues.confirmer_arret_indexation(self, self.windowTitle()):
				evenement.ignore()
				return
			self.indexation.arreter()
		super().closeEvent(evenement)


def lancer_fenetre(
	socket: Path, base: str, audit_complet: bool, seuil_silences: float = SEUIL_DE_SILENCE, forcer: bool = False
) -> int:
	"""Machin indexation --fenetre : la fenêtre du journal, jusqu'à sa fermeture ; forcer, avec --forcer."""
	qt = application(EXECUTABLE)
	fenetre = FenetreJournal(socket, base, audit_complet, seuil_silences=seuil_silences)
	fenetre.indexation.forcer = forcer
	fenetre.lancer()
	return qt.exec()
