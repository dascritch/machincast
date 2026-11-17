"""Économiseur d'écran et verrouillage de la session (https://github.com/dascritch/machincast/issues/346).

Personne ne regarde le VU-mètre pendant que la session est verrouillée ou l'écran éteint, et le serveur audio peut
alors cesser de répondre : l'interface ferme son port de monitoring le temps de la veille, et le rouvre au retour.

La veille se lit sur le bus de session, au signal ActiveChanged de org.freedesktop.ScreenSaver, que KDE émet au
verrouillage de la session comme au démarrage de l'économiseur d'écran, et GNOME de même ; jamais par une
interrogation en boucle. Sans bus de session, ou sans économiseur d'écran, la session n'est jamais en veille.
"""

from PySide6.QtCore import SLOT, QObject, Signal, Slot
from PySide6.QtDBus import QDBusConnection

PATH = "/org/freedesktop/ScreenSaver"
INTERFACE = "org.freedesktop.ScreenSaver"
SIGNAL = "ActiveChanged"


def bus() -> QDBusConnection:
	"""Le bus de session, où l'économiseur d'écran annonce la veille ; les scénarios en donnent un à part."""
	return QDBusConnection.sessionBus()


class ScreenSaver(QObject):
	"""La veille de la session : vraie tant que la session est verrouillée ou l'économiseur d'écran actif."""

	changed = Signal()
	"""La session entre en veille, ou en sort ; `asleep` dit laquelle."""

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.asleep = False
		self._bus = bus()
		self.listening = False
		"""Vrai si le bus de session transmet la veille : sinon, la session n'est jamais en veille."""
		if self._bus.isConnected():
			# Tout émetteur : le nom de l'économiseur d'écran change d'un bureau à l'autre, pas son signal. PySide6 attend
			# la signature du slot telle que SLOT() la rend, une chaîne ; ses stubs annoncent des octets, qui ne
			# connectent rien.
			slot = SLOT("_active_changed(bool)")
			self.listening = self._bus.connect("", PATH, INTERFACE, SIGNAL, self, slot)  # type: ignore[call-overload]

	@Slot(bool)
	def _active_changed(self, active: bool) -> None:  # noqa: FBT001  # argument du signal D-Bus, passé par sa position
		if active != self.asleep:
			self.asleep = active
			self.changed.emit()
