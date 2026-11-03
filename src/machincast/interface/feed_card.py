"""Fiche d'un feed de stream (https://github.com/dascritch/machincast/issues/34, spec § 8.13).

Un feed est une adresse de flux réutilisable, souvent en ligne par intermittence : plusieurs streams peuvent le
suivre, et jouent son adresse (machincast.player.broadcast). La fiche s'ouvre dans un onglet de la fenêtre
(machincast.interface.window), depuis la liste des feeds, ou vide pour un nouveau feed.
Enregistrement, annulation et fermeture : machincast.interface.card.

- Le nom est obligatoire, propre au feed ; l'adresse est obligatoire. Les deux sont enregistrés sans les
  espaces qui les entourent. Une nouvelle adresse vaut pour tous les streams qui le suivent.
- Le test du flux (machincast.interface.stream_trial) porte sur l'adresse saisie, même pas encore enregistrée ; il
  s'arrête à la fermeture de la fiche.
- Les streams qui le suivent sont montrés ; ouvrir l'un d'eux ouvre sa fiche. Un feed qu'un stream suit ne se
  supprime pas (machincast.interface.deletion) : la base le refuserait aussi.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QWidget

from machincast.clock import Clock
from machincast.conformation import conform
from machincast.interface.card import Card, Connection, Refusal
from machincast.interface.stream_trial import StreamTrial, trial_result
from machincast.interface.ui.feed_card import Ui_FeedCard

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
		self.ui.test.clicked.connect(self._test)
		self.ui.streams.itemActivated.connect(self._open_stream)
		self.load()

	def title(self) -> str:
		if self.identifier is None:
			return "Nouveau feed"
		return f"Feed : {self._name}"

	def shut_down(self) -> None:
		self.trial.halt()

	def _read(self) -> None:
		marks: tuple[object, ...] = ("", "")
		streams: list[tuple[object, ...]] = []
		with self.connection.transaction():
			if self.identifier is not None:
				line = self.connection.execute(
					"SELECT name, url FROM feeds WHERE id = %s", (self.identifier,)
				).fetchone()
				assert line is not None, f"feed {self.identifier} absent"
				marks = line
				streams = self.connection.execute(
					"SELECT id, COALESCE(title, %s) FROM sounds WHERE feed_id = %s AND deleted_at IS NULL"
					" ORDER BY 2, id",
					(str(marks[1]), self.identifier),
				).fetchall()
		name, url = marks
		self._name = str(name)
		self.ui.name.setText(self._name)
		self.ui.url.setText(str(url))
		self.ui.streams.clear()
		for identifier, title in streams:
			item = QListWidgetItem(str(title))
			item.setData(SOUND, int(str(identifier)))
			self.ui.streams.addItem(item)

	def _write(self) -> int:
		name = conform(self.ui.name.text())
		url = self.ui.url.text().strip()
		if name == "":
			raise Refusal("Le nom est obligatoire.", self.ui.name)
		taken = self.connection.execute(
			"SELECT 1 FROM feeds WHERE name = %s AND id IS DISTINCT FROM %s", (name, self.identifier)
		).fetchone()
		if taken is not None:
			raise Refusal(f"Un autre feed s'appelle déjà « {name} ».", self.ui.name)
		if url == "":
			raise Refusal("L'adresse est obligatoire.", self.ui.url)
		if self.identifier is None:
			created = self.connection.execute(
				"INSERT INTO feeds (name, url) VALUES (%s, %s) RETURNING id", (name, url)
			).fetchone()
			assert created is not None
			return int(str(created[0]))
		self.connection.execute("UPDATE feeds SET name = %s, url = %s WHERE id = %s", (name, url, self.identifier))
		return self.identifier

	def _test(self) -> None:
		self.ui.test.setEnabled(False)
		self.ui.trial_result.setText("Test du flux en cours…")
		self.trial.launch(self.ui.url.text().strip())

	def _finished_trial(self, answers: bool, detail: str) -> None:
		self.ui.trial_result.setText(trial_result(answers, detail))
		self.ui.test.setEnabled(True)

	def _open_stream(self, item: QListWidgetItem) -> None:
		self.requested_opening.emit("sonore", int(item.data(SOUND)), item.text())
