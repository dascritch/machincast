"""Les connexions à distance à valider au pupitre (https://github.com/dascritch/machincast/issues/539).

Une connexion à l'intranet, par nom et mot de passe valides, attend d'être validée : au-dessus des onglets, un
bandeau nomme le compte, l'adresse IP source, le navigateur, l'heure limite et le code à 6 chiffres à donner à la
personne qui se connecte, qui le saisit sur son poste. « Refuser » rend la session invalide. Le bandeau relit les
connexions toutes les POLL millisecondes, et disparaît sans connexion à valider.
"""

import logging
from html import escape

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from machincast.i18n import _
from machincast.interface.queries import api_users as queries

log = logging.getLogger(__name__)

POLL = 3000
"""Millisecondes entre deux lectures des connexions à valider."""
OUTLINE = "QFrame#remote_connections { border: 2px solid #ef6c00; border-radius: 4px; }"
"""Orange, lisible sur un thème clair comme sombre : une action est attendue au pupitre."""
REFUSE = _("Refuse")


def describe(connection: queries.Pending) -> str:
	"""La ligne d'une connexion à valider, en texte riche : le code en gras, chiffres groupés par trois."""
	code = f"{connection.code[:3]} {connection.code[3:]}"
	return _(
		"Remote connection to validate: <b>{user}</b>, from {address}, {browser}, until {limit}. "
		"Code to give: <b>{code}</b>"
	).format(
		user=escape(connection.user),
		address=escape((connection.address) or ("?")),
		browser=escape((connection.user_agent[:80]) or ("?")),
		limit=f"{connection.validate_before.astimezone():%H:%M}",
		code=code,
	)


class RemoteConnections(QFrame):
	"""Le bandeau des connexions à valider."""

	refused = Signal(str)
	"""Ce que vient de refuser le pupitre, pour la barre d'état."""

	def __init__(self, connection: psycopg.Connection[TupleRow], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("remote_connections")
		self.setStyleSheet(OUTLINE)
		self.connection = connection
		self.arrangement = QVBoxLayout(self)
		self.shown: list[queries.Pending] = []
		self.labels: list[QLabel] = []
		self.setVisible(False)
		self.timer = QTimer(self)
		self.timer.setInterval(POLL)
		self.timer.timeout.connect(self.refresh)
		self.timer.start()

	def refresh(self) -> None:
		"""Relit les connexions à valider ; une base injoignable laisse le bandeau tel quel."""
		try:
			with self.connection.transaction():
				found = queries.pending(self.connection)
		except psycopg.Error as error:
			log.debug(_("remote connections unreadable: {error}").format(error=error))
			return
		if found == self.shown:
			return
		self.shown = found
		while self.arrangement.count() > 0:
			item = self.arrangement.takeAt(0)
			widget = None
			if item is not None:
				widget = item.widget()
			if widget is not None:
				widget.deleteLater()
		self.labels = []
		for pending in found:
			self.arrangement.addWidget(self._line(pending))
		self.setVisible(found != [])

	def _line(self, pending: queries.Pending) -> QWidget:
		line = QWidget(self)
		line.setObjectName(f"remote_connection_{pending.identifier}")
		arrangement = QHBoxLayout(line)
		arrangement.setContentsMargins(0, 0, 0, 0)
		said = QLabel(describe(pending), line)
		said.setObjectName("remote_connection_text")
		said.setTextFormat(Qt.TextFormat.RichText)
		said.setWordWrap(True)
		arrangement.addWidget(said, 1)
		self.labels.append(said)
		refuse = QPushButton(REFUSE, line)
		refuse.setObjectName("refuse_remote_connection")
		refuse.clicked.connect(lambda _checked=False, chosen=pending: self.refuse(chosen))
		arrangement.addWidget(refuse)
		return line

	def refuse(self, pending: queries.Pending) -> None:
		with self.connection.transaction():
			queries.invalidate(self.connection, pending.identifier)
		self.refused.emit(_("Remote connection of {user} refused.").format(user=pending.user))
		self.refresh()

	def texts(self) -> list[str]:
		"""Le texte de chaque connexion montrée, pour les scénarios."""
		found = []
		for label in self.labels:
			found.append(label.text())
		return found
