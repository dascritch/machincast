"""Encarts dépliables (https://github.com/dascritch/machincast/issues/190).

Un encart (QGroupBox) devient dépliable : son contenu passe dans un conteneur intérieur, qu'un clic sur le titre, ou
Espace et Entrée quand l'encart a le focus, montre ou cache. Le titre commence par « ▾ » déplié, « ▸ » replié. Ce
que la fiche cache ou montre dans l'encart, selon le sonore, n'est pas touché : seul le conteneur l'est. Une fonction
retenir, facultative, apprend chaque dépliage ou repliage fait à la main, pour que d'autres fiches s'en souviennent
(https://github.com/dascritch/machincast/issues/223) ; retain_in en donne une qui les garde dans les réglages des
vues du compte (machincast.interface.columns), et retenus les y relit.
"""

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

from machincast.i18n import _
from machincast.interface import columns

EXPANDED, COLLAPSED = "▾", "▸"
CONTENT = "expandable_content"
"""Nom du conteneur intérieur d'un encart dépliable."""
TITLE = "titre_depliable"
"""Propriété de l'encart qui garde son titre, sans flèche."""
TITLE_MARGIN = 6
"""Pixels sous le texte du titre où un clic compte encore pour le titre."""
FREE_HEIGHT = 16777215
"""La hauteur maximale d'un widget de Qt (QWIDGETSIZE_MAX) : celle d'un encart déplié."""


Retain = Callable[[QGroupBox, bool], None]
"""Ce qui retient un encart déplié (True) ou replié (False) à la main."""


def retained(key: str) -> set[str]:
	"""Les noms des encarts gardés sous cette clé des réglages des vues du compte."""
	value = columns.settings().value(key)
	if isinstance(value, str):
		return {value}
	if isinstance(value, list):
		retained = set()
		for name in value:
			retained.add(str(name))
		return retained
	return set()


def retain_in(key: str, expanded_list: bool = True) -> Retain:
	"""Garde sous cette clé les noms des encarts dépliés, ou, deplies faux, ceux des encarts repliés."""

	def retain(group: QGroupBox, expanded: bool) -> None:
		names = retained(key)
		if expanded is expanded_list:
			names.add(group.objectName())
		else:
			names.discard(group.objectName())
		columns.settings().setValue(key, sorted(names))

	return retain


def make_expandable(group: QGroupBox, expanded: bool = False, retain: Retain | None = None) -> None:
	content = QWidget(group)
	content.setObjectName(CONTENT)
	arrangement = group.layout()
	if arrangement is not None:
		# La disposition de l'encart, et ses champs, passent dans le conteneur.
		content.setLayout(arrangement)
	external = QVBoxLayout(group)
	external.setContentsMargins(0, 0, 0, 0)
	external.addWidget(content)
	group.setProperty(TITLE, group.title())
	group.setFocusPolicy(Qt.FocusPolicy.TabFocus)
	group.setToolTip(_("Click on the title to expand or collapse"))
	group.installEventFilter(_Title(group, retain))
	display(group, expanded)


def _content(group: QGroupBox) -> QWidget:
	content = group.findChild(QWidget, CONTENT)
	assert content is not None, "encart non dépliable"
	return content


def is_collapsed(group: QGroupBox) -> bool:
	"""Un encart qui n'est pas dépliable n'est jamais replié."""
	content = group.findChild(QWidget, CONTENT)
	return (content is not None) and (content.isHidden())


def display(group: QGroupBox, expanded: bool) -> None:
	"""Replié, l'encart n'a plus de cadre : il ne reste que son titre."""
	_content(group).setVisible(expanded)
	group.setFlat(not expanded)
	height = FREE_HEIGHT
	if not expanded:
		height = group.fontMetrics().height() + TITLE_MARGIN
	group.setMaximumHeight(height)
	arrow = COLLAPSED
	if expanded:
		arrow = EXPANDED
	group.setTitle(f"{arrow} {group.property(TITLE)}")


def switch(group: QGroupBox) -> None:
	display(group, is_collapsed(group))


class _Title(QObject):
	"""Le clic sur le titre de l'encart, ou Espace et Entrée, le déplie ou le replie."""

	def __init__(self, group: QGroupBox, retain: Retain | None) -> None:
		super().__init__(group)
		self.group = group
		self.retain = retain

	def _switch(self) -> None:
		switch(self.group)
		if self.retain is not None:
			self.retain(self.group, not is_collapsed(self.group))

	def eventFilter(self, _object: QObject, event: QEvent) -> bool:
		if event.type() == QEvent.Type.MouseButtonPress:
			assert isinstance(event, QMouseEvent)
			height = self.group.fontMetrics().height() + TITLE_MARGIN
			if (event.button() == Qt.MouseButton.LeftButton) and (event.position().y() <= height):
				self._switch()
				return True
		if event.type() == QEvent.Type.KeyPress:
			assert isinstance(event, QKeyEvent)
			if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
				self._switch()
				return True
		return False
