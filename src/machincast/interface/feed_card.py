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
- Un feed d'entrée audio (https://github.com/dascritch/machincast/issues/623), d'adresse « input: » suivie du
  périphérique, que seuls les Paramètres du service donnent, montre son périphérique, sans adresse,
  ni mémoire tampon, ni test du flux ; son nom se change dans les Paramètres du service
  (machincast.interface.input_feeds). Une entrée retirée de ces paramètres garde son feed, et la fiche le signale.
- Les streams qui le suivent sont montrés ; ouvrir l'un d'eux ouvre sa fiche. Un feed qu'un stream suit ne se
  supprime pas (machincast.interface.deletion) : la base le refuserait aussi.
"""

from collections.abc import Sequence
from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QWidget

from machincast.audio import INPUT_ADDRESS, input_device
from machincast.clock import Clock
from machincast.conformation import conform
from machincast.i18n import _
from machincast.interface.card import Card, Connection, Refusal
from machincast.interface.queries import feeds as queries
from machincast.interface.stream_trial import StreamTrial, trial_result
from machincast.interface.ui.feed_card import Ui_FeedCard

DEFAULT_BUFFER = 2
"""Secondes de mémoire tampon d'un nouveau feed, comme la valeur par défaut de feeds.buffer_duration."""
SOUND = Qt.ItemDataRole.UserRole
"""Rôle qui porte l'identifiant d'un stream, dans la liste des streams."""
INPUT_CAPTION = _("Audio input:")
NAMED_IN_SETTINGS = _("The name of an audio input changes in File → Broadcast service settings…, Audio page.")
RESERVED_ADDRESS = _(
	"An address starting with “{prefix}” is reserved for the audio inputs of the broadcast service settings."
)
RETIRED = _("Audio input removed from the broadcast service settings: its streams no longer play anything.")


class FeedCard(Card):
	category = "feed"
	CLOSES_AFTER_SAVE = True

	def __init__(
		self, connection: Connection, identifier: int | None, clock: Clock, parent: QWidget | None = None
	) -> None:
		super().__init__(connection, identifier, clock, parent)
		self.ui = Ui_FeedCard()
		self.ui.setupUi(self)
		self.plug(self.ui.save, self.ui.cancel, self.ui.delete, self.ui.message)
		self._name = ""
		self.device: str | None = None
		"""Le périphérique d'un feed d'entrée audio ; None pour un feed d'adresse."""
		self.configured: tuple[str, ...] | None = None
		"""Les périphériques des entrées des Paramètres du service, quand la fenêtre les donne (show_inputs)."""
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
				line = queries.read_feed(self.connection, self.identifier)
				assert line is not None, f"feed {self.identifier} absent"
				marks = line
				streams = queries.streams(self.connection, self.identifier, str(marks[1]))
		name, url, buffer = marks
		self._name = str(name)
		self.device = input_device(url)
		self.ui.name.setText(self._name)
		self.ui.url.setText((self.device) or (str(url)))
		self._show_kind()
		if isinstance(buffer, timedelta):
			self.ui.buffer.setValue(round(buffer.total_seconds()))
		self._show_buffer()
		self.ui.streams.clear()
		for identifier, title in streams:
			item = QListWidgetItem(str(title))
			item.setData(SOUND, int(str(identifier)))
			self.ui.streams.addItem(item)

	def _show_kind(self) -> None:
		"""Un feed d'entrée audio : son périphérique à la place de l'adresse, sans mémoire tampon ni test."""
		of_input = self.device is not None
		for widget in (
			self.ui.buffer_caption,
			self.ui.buffer,
			self.ui.buffer_value,
			self.ui.buffer_explanation,
			self.ui.test,
			self.ui.trial_result,
		):
			widget.setVisible(not of_input)
		self.ui.name.setReadOnly(of_input)
		self.ui.url.setReadOnly(of_input)
		if of_input:
			self.ui.url_caption.setText(INPUT_CAPTION)
			self.ui.name.setToolTip(NAMED_IN_SETTINGS)
		self._show_retirement()

	def show_inputs(self, devices: Sequence[str]) -> None:
		"""Les périphériques des entrées des Paramètres du service : une entrée qui n'y est plus est signalée."""
		self.configured = tuple(devices)
		self._show_retirement()

	def _show_retirement(self) -> None:
		retired = (self.device is not None) and (self.configured is not None) and (self.device not in self.configured)
		if retired:
			self.warn(RETIRED)
		else:
			self.warn("")

	def _write(self) -> int:
		if (self.device is not None) and (self.identifier is not None):
			# Son nom se change dans les Paramètres du service ; rien d'autre ne s'y règle.
			return self.identifier
		name = conform(self.ui.name.text())
		url = self.ui.url.text().strip()
		if name == "":
			raise Refusal(_("The name is required."), self.ui.name)
		if queries.name_taken(self.connection, name, self.identifier):
			raise Refusal(_("Another feed is already called “{name}”.").format(name=name), self.ui.name)
		if url == "":
			raise Refusal(_("The address is required."), self.ui.url)
		if input_device(url) is not None:
			raise Refusal(RESERVED_ADDRESS.format(prefix=INPUT_ADDRESS), self.ui.url)
		buffer = timedelta(seconds=self.ui.buffer.value())
		if self.identifier is None:
			return queries.insert(self.connection, name, url, buffer)
		queries.update(self.connection, self.identifier, name, url, buffer)
		return self.identifier

	def _show_buffer(self) -> None:
		self.ui.buffer_value.setText(_("{seconds} s").format(seconds=self.ui.buffer.value()))

	def _test(self) -> None:
		self.ui.test.setEnabled(False)
		self.ui.trial_result.setText(_("Stream test running…"))
		self.trial.launch(self.ui.url.text().strip())

	def _finished_trial(self, answers: bool, detail: str) -> None:  # noqa: FBT001  # signal de Qt : le booléen arrive par sa position
		self.ui.trial_result.setText(trial_result(answers=answers, detail=detail))
		self.ui.test.setEnabled(True)

	def _open_stream(self, item: QListWidgetItem) -> None:
		self.requested_opening.emit("sound", int(item.data(SOUND)), item.text())
