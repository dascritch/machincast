"""Encarts dépliables (https://github.com/dascritch/machincast/issues/190).

Un encart (QGroupBox) devient dépliable : son contenu passe dans un conteneur intérieur, qu'un clic sur le titre, ou
Espace et Entrée quand l'encart a le focus, montre ou cache. Le titre commence par « ▾ » déplié, « ▸ » replié. Ce
que la fiche cache ou montre dans l'encart, selon le sonore, n'est pas touché : seul le conteneur l'est.
"""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

DEPLIE, REPLIE = "▾", "▸"
CONTENU = "contenu_depliable"
"""Nom du conteneur intérieur d'un encart dépliable."""
TITRE = "titre_depliable"
"""Propriété de l'encart qui garde son titre, sans flèche."""
MARGE_DU_TITRE = 6
"""Pixels sous le texte du titre où un clic compte encore pour le titre."""
HAUTEUR_LIBRE = 16777215
"""La hauteur maximale d'un widget de Qt (QWIDGETSIZE_MAX) : celle d'un encart déplié."""


def rendre_depliable(groupe: QGroupBox, deplie: bool = False) -> None:
	contenu = QWidget(groupe)
	contenu.setObjectName(CONTENU)
	disposition = groupe.layout()
	if disposition is not None:
		# La disposition de l'encart, et ses champs, passent dans le conteneur.
		contenu.setLayout(disposition)
	exterieure = QVBoxLayout(groupe)
	exterieure.setContentsMargins(0, 0, 0, 0)
	exterieure.addWidget(contenu)
	groupe.setProperty(TITRE, groupe.title())
	groupe.setFocusPolicy(Qt.FocusPolicy.TabFocus)
	groupe.setToolTip("Cliquer sur le titre pour déplier ou replier")
	groupe.installEventFilter(_Titre(groupe))
	montrer(groupe, deplie)


def _contenu(groupe: QGroupBox) -> QWidget:
	contenu = groupe.findChild(QWidget, CONTENU)
	assert contenu is not None, "encart non dépliable"
	return contenu


def est_replie(groupe: QGroupBox) -> bool:
	"""Un encart qui n'est pas dépliable n'est jamais replié."""
	contenu = groupe.findChild(QWidget, CONTENU)
	return (contenu is not None) and (contenu.isHidden())


def montrer(groupe: QGroupBox, deplie: bool) -> None:
	"""Replié, l'encart n'a plus de cadre : il ne reste que son titre."""
	_contenu(groupe).setVisible(deplie)
	groupe.setFlat(not deplie)
	hauteur = HAUTEUR_LIBRE
	if not deplie:
		hauteur = groupe.fontMetrics().height() + MARGE_DU_TITRE
	groupe.setMaximumHeight(hauteur)
	fleche = REPLIE
	if deplie:
		fleche = DEPLIE
	groupe.setTitle(f"{fleche} {groupe.property(TITRE)}")


def basculer(groupe: QGroupBox) -> None:
	montrer(groupe, est_replie(groupe))


class _Titre(QObject):
	"""Le clic sur le titre de l'encart, ou Espace et Entrée, le déplie ou le replie."""

	def __init__(self, groupe: QGroupBox) -> None:
		super().__init__(groupe)
		self.groupe = groupe

	def eventFilter(self, _objet: QObject, evenement: QEvent) -> bool:
		if evenement.type() == QEvent.Type.MouseButtonPress:
			assert isinstance(evenement, QMouseEvent)
			hauteur = self.groupe.fontMetrics().height() + MARGE_DU_TITRE
			if (evenement.button() == Qt.MouseButton.LeftButton) and (evenement.position().y() <= hauteur):
				basculer(self.groupe)
				return True
		if evenement.type() == QEvent.Type.KeyPress:
			assert isinstance(evenement, QKeyEvent)
			if evenement.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
				basculer(self.groupe)
				return True
		return False
