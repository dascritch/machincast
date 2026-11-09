"""Fiche d'un feed de stream (https://github.com/dascritch/machincast/issues/34, spec § 8.13).

Un feed est une adresse de flux réutilisable, souvent en ligne par intermittence : plusieurs streams peuvent le
suivre, et jouent son adresse (machincast.player.broadcast). La fiche s'ouvre dans un onglet de la fenêtre
(machincast.interface.window), depuis la liste des feeds, ou vide pour un nouveau feed.
Enregistrement, annulation et fermeture : machincast.interface.card.

- Le nom est obligatoire, propre au feed ; l'adresse est obligatoire. Les deux sont enregistrés sans les
  espaces qui les entourent. Une nouvelle adresse vaut pour tous les streams qui le suivent.
- La mémoire tampon, de 2 à 10 secondes, 2 par défaut (https://github.com/dascritch/machincast/issues/351) : le
  stream attend qu'elle soit pleine pour jouer. Elle vaut pour tous les streams qui suivent le feed, à leur prochain
  démarrage.
- Le test du flux (machincast.interface.stream_trial) porte sur l'adresse saisie, même pas encore enregistrée ; il
  s'arrête à la fermeture de la fiche.
- Les streams qui le suivent sont montrés ; ouvrir l'un d'eux ouvre sa fiche. Un feed qu'un stream suit ne se
  supprime pas (machincast.interface.deletion) : la base le refuserait aussi.
"""

from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QWidget

from machincast.clock import Clock
from machincast.conformation import conform
from machincast.i18n import _
from machincast.interface.card import Card, Connection, Refusal
from machincast.interface.stream_trial import StreamTrial, trial_result
from machincast.interface.ui.feed_card import Ui_FeedCard

DEFAULT_BUFFER = 2
"""Secondes de mémoire tampon d'un nouveau feed, comme la valeur par défaut de feeds.buffer_duration."""
SOUND = Qt.ItemDataRole.UserRole
"""Rôle qui porte l'identifiant d'un stream, dans la liste des streams."""


class FeedCard(Card):
	category = "feed"

	def __init__(
		self, connection: Connection, identifier: int | None, clock: Clock, parent: QWidget | None = None
	) -> None:
		super().__init__(connection, identifier, clock, parent)
		self.ui = Ui_FeedCard()
		self.ui.setupUi(self)
		self.plug(self.ui.save, self.ui.cancel, self.ui.delete, self.ui.message)
		self._name = ""
		self.trial = StreamTrial(self)
		self.trial.finished.connect(self._finished_trial)
		self.ui.name.textChanged.connect(self._modify)
		self.ui.url.textChanged.connect(self._modify)
		self.ui.buffer.valueChanged.connect(self._show_buffer)
		self.ui.buffer.valueChanged.connect(self._modify)
		self.ui.test.clicked.connect(self._test)
		self.ui.streams.itemActivated.connect(self._open_stream)
		self.load()

	def title(self) -> str:
		if self.identifier is None:
			return _("New feed")
		return _("Feed: {name}").format(name=self._name)

	def shut_down(self) -> None:
		self.trial.halt()

	def _read(self) -> None:
		marks: tuple[object, ...] = ("", "", timedelta(seconds=DEFAULT_BUFFER))
		streams: list[tuple[object, ...]] = []
		with self.connection.transaction():
			if self.identifier is not None:
				line = self.connection.execute(
					"SELECT name, url, buffer_duration FROM feeds WHERE id = %s", (self.identifier,)
				).fetchone()
				assert line is not None, f"feed {self.identifier} absent"
				marks = line
				streams = self.connection.execute(
					"SELECT id, COALESCE(title, %s) FROM sounds WHERE feed_id = %s AND deleted_at IS NULL"
					" ORDER BY 2, id",
					(str(marks[1]), self.identifier),
				).fetchall()
		name, url, buffer = marks
		self._name = str(name)
		self.ui.name.setText(self._name)
		self.ui.url.setText(str(url))
		if isinstance(buffer, timedelta):
			self.ui.buffer.setValue(round(buffer.total_seconds()))
		self._show_buffer()
		self.ui.streams.clear()
		for identifier, title in streams:
			item = QListWidgetItem(str(title))
			item.setData(SOUND, int(str(identifier)))
			self.ui.streams.addItem(item)

	def _write(self) -> int:
		name = conform(self.ui.name.text())
		url = self.ui.url.text().strip()
		if name == "":
			raise Refusal(_("The name is required."), self.ui.name)
		taken = self.connection.execute(
			"SELECT 1 FROM feeds WHERE name = %s AND id IS DISTINCT FROM %s", (name, self.identifier)
		).fetchone()
		if taken is not None:
			raise Refusal(_("Another feed is already called “{name}”.").format(name=name), self.ui.name)
		if url == "":
			raise Refusal(_("The address is required."), self.ui.url)
		buffer = timedelta(seconds=self.ui.buffer.value())
		if self.identifier is None:
			created = self.connection.execute(
				"INSERT INTO feeds (name, url, buffer_duration) VALUES (%s, %s, %s) RETURNING id", (name, url, buffer)
			).fetchone()
			assert created is not None
			return int(str(created[0]))
		self.connection.execute(
			"UPDATE feeds SET name = %s, url = %s, buffer_duration = %s WHERE id = %s",
			(name, url, buffer, self.identifier),
		)
		return self.identifier

	def _show_buffer(self) -> None:
		self.ui.buffer_value.setText(_("{seconds} s").format(seconds=self.ui.buffer.value()))

	def _test(self) -> None:
		self.ui.test.setEnabled(False)
		self.ui.trial_result.setText(_("Stream test running…"))
		self.trial.launch(self.ui.url.text().strip())

	def _finished_trial(self, answers: bool, detail: str) -> None:
		self.ui.trial_result.setText(trial_result(answers, detail))
		self.ui.test.setEnabled(True)

	def _open_stream(self, item: QListWidgetItem) -> None:
		self.requested_opening.emit("sound", int(item.data(SOUND)), item.text())
