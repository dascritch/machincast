"""Les raccourcis en surimpression (https://github.com/dascritch/machincast/issues/529).

Maintenir Ctrl, ou Alt, seule, une seconde (HOLD_DELAY) montre par-dessus la fenêtre les raccourcis qui commencent
par cette touche : sur chaque bouton qui en a un, visible (son raccourci de Qt, ou ceux qu'on lui attache par
attach, comme Ctrl+S et Ctrl+Entrée sur « Enregistrer » d'une fiche), et, dans un encart en bas à droite, ceux des
menus. Relâcher la touche, en presser une autre, ou quitter la fenêtre les cache.

Ce qui est montré se calcule à part de son affichage (hints, menu_hints), pour que les scénarios le vérifient.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QKeyEvent, QKeySequence
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QMainWindow, QMenu, QWidget

HOLD_DELAY = 1000
"""Millisecondes d'appui sur Ctrl ou Alt avant les raccourcis ; les scénarios le raccourcissent."""
SAVE = "Ctrl+S"
SAVE_AND_CLOSE = "Ctrl+Return"
CANCEL_AND_CLOSE = "Ctrl+Esc"
"""Annule les modifications de la fiche ouverte, et la ferme."""
PROPERTY = "machincast_raccourcis"
"""Propriété d'un widget qui porte les raccourcis qu'on lui attache."""
STYLE = (
	"QLabel { background: #fff59d; color: #212121; border: 1px solid #616161; border-radius: 3px; padding: 1px 4px; }"
)
"""Une étiquette lisible sur n'importe quel thème, comme celles d'un clavier."""
MODIFIERS = {
	Qt.Key.Key_Control: Qt.KeyboardModifier.ControlModifier,
	Qt.Key.Key_Alt: Qt.KeyboardModifier.AltModifier,
}
PORTABLE_NAMES = {Qt.KeyboardModifier.ControlModifier: "Ctrl", Qt.KeyboardModifier.AltModifier: "Alt"}
"""Le nom d'une touche de modification dans l'écriture portable d'un raccourci, « Ctrl+Shift+T »."""


@dataclass(frozen=True)
class Hint:
	"""Un raccourci à montrer : sur ce widget, ou, sans widget, dans l'encart des menus, avec le nom de l'entrée."""

	text: str
	target: QWidget | None = None
	entry: str = ""


def attach(widget: QWidget, *keys: str) -> None:
	"""Ces raccourcis, tenus ailleurs (QShortcut de la fenêtre), s'affichent sur ce widget."""
	widget.setProperty(PROPERTY, list(keys))


def _text(keys: QKeySequence) -> str:
	return keys.toString(QKeySequence.SequenceFormat.NativeText)


def _starts_with(keys: QKeySequence, modifier: Qt.KeyboardModifier) -> bool:
	if keys.isEmpty():
		return False
	first = keys.toString(QKeySequence.SequenceFormat.PortableText).split(", ")[0]
	return PORTABLE_NAMES[modifier] in first.split("+")[:-1]


def _keys_of(widget: QWidget) -> list[QKeySequence]:
	found = []
	attached = widget.property(PROPERTY)
	if isinstance(attached, list):
		for keys in attached:
			found.append(QKeySequence(str(keys)))
	if isinstance(widget, QAbstractButton):
		found.append(widget.shortcut())
	return found


def hints(window: QWidget, modifier: Qt.KeyboardModifier) -> list[Hint]:
	"""Les raccourcis des widgets visibles de la fenêtre qui commencent par cette touche, un par widget, ses
	raccourcis séparés par « · »."""
	hint_list = []
	for widget in window.findChildren(QWidget):
		texts = []
		for keys in _keys_of(widget):
			if _starts_with(keys, modifier):
				texts.append(_text(keys))
		if (texts != []) and (widget.isVisible()):
			hint_list.append(Hint(" · ".join(texts), widget))
	return hint_list


def _actions(menu: QMenu) -> Iterable[QAction]:
	for action in menu.actions():
		under = action.menu()
		if isinstance(under, QMenu):
			yield from _actions(under)
		else:
			yield action


def menu_hints(window: QMainWindow, modifier: Qt.KeyboardModifier) -> list[Hint]:
	"""Les entrées actives des menus de la fenêtre dont le raccourci commence par cette touche."""
	hint_list = []
	for menu in window.menuBar().findChildren(QMenu):
		if menu.parent() is window.menuBar():
			for action in _actions(menu):
				if (action.isEnabled()) and (_starts_with(action.shortcut(), modifier)):
					hint_list.append(Hint(_text(action.shortcut()), None, action.text().replace("&", "")))
	return hint_list


class KeyHints(QObject):
	"""Le guet de Ctrl et d'Alt sur l'application, et les étiquettes qu'il pose sur la fenêtre."""

	def __init__(self, window: QMainWindow) -> None:
		super().__init__(window)
		self.window = window
		self.held: Qt.KeyboardModifier | None = None
		self.labels: list[QLabel] = []
		self.shown: list[Hint] = []
		"""Ce qui est montré, pour les scénarios."""
		self._timer = QTimer(self)
		self._timer.setSingleShot(True)
		self._timer.timeout.connect(self.show)
		application = QApplication.instance()
		if application is not None:
			application.installEventFilter(self)

	def eventFilter(self, object_: QObject, event: QEvent) -> bool:
		"""Ctrl ou Alt pressée seule lance l'attente ; toute autre touche, son relâchement, ou la fenêtre quittée,
		cachent tout."""
		kind = event.type()
		# Une touche prise par un raccourci n'arrive qu'en ShortcutOverride : elle compte aussi.
		if (kind in (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride)) and (isinstance(event, QKeyEvent)):
			self._pressed(event)
			return False
		repeated = (isinstance(event, QKeyEvent)) and (event.isAutoRepeat())
		leaving = kind in (QEvent.Type.KeyRelease, QEvent.Type.ApplicationDeactivate, QEvent.Type.WindowDeactivate)
		if (leaving) and (not repeated):
			self.hide()
		return False

	def _pressed(self, event: QKeyEvent) -> None:
		if event.isAutoRepeat():
			return
		modifier = MODIFIERS.get(Qt.Key(event.key()))
		if (modifier is None) or (not self.window.isActiveWindow()):
			self.hide()
			return
		self.held = modifier
		self._timer.start(HOLD_DELAY)

	def show(self) -> None:
		"""Les étiquettes des raccourcis de la touche tenue, et l'encart de ceux des menus."""
		self.hide_labels()
		if self.held is None:
			return
		self.shown = hints(self.window, self.held)
		for hint in self.shown:
			assert hint.target is not None
			self._label(hint.text, hint.target.mapTo(self.window, QPoint(0, 0)))
		on_menus = menu_hints(self.window, self.held)
		if on_menus != []:
			lines = []
			for hint in on_menus:
				lines.append(f"{hint.text}  {hint.entry}")
			panel = self._label("\n".join(lines), QPoint(0, 0))
			panel.adjustSize()
			panel.move(self.window.width() - panel.width() - 8, self.window.height() - panel.height() - 8)
			self.shown = self.shown + on_menus

	def _label(self, text: str, position: QPoint) -> QLabel:
		label = QLabel(text, self.window)
		label.setStyleSheet(STYLE)
		label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
		label.adjustSize()
		label.move(position)
		label.show()
		label.raise_()
		self.labels.append(label)
		return label

	def waiting(self) -> bool:
		"""Vrai pendant l'attente de la touche tenue."""
		return self._timer.isActive()

	def hide(self) -> None:
		"""Plus de touche tenue : rien n'est montré."""
		self._timer.stop()
		self.held = None
		self.hide_labels()

	def hide_labels(self) -> None:
		for label in self.labels:
			label.deleteLater()
		self.labels = []
		self.shown = []
