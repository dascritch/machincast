"""Choix des cartes son de l'antenne et de la pré-écoute (https://github.com/dascritch/machincast/issues/339,
spec § 8.10 et § 8.11).

Le bloc SoundCards sert à la page « Audio » des préférences (machincast.interface.preferences) et à la fenêtre « Pour
bien démarrer » (machincast.interface.suggestions). Il choisit :

- le type de sortie (audio.output) : PipeWire, PulseAudio ou ALSA ; la sortie factice des essais n'est proposée que si
  elle est déjà configurée. Un autre type relit les cartes du poste : l'antenne reste à renseigner, sauf sur la sortie
  factice ; la pré-écoute garde sa carte si elle y est ;
- la carte son de l'antenne (audio.device) et celle de la pré-écoute (audio.preview), chacune parmi les
  périphériques du poste (machincast.audio.devices), la carte configurée en tête, et l'entrée « Sortie factice »
  (configuration.DUMMY). La carte choisie pour l'une est grisée dans l'autre, sortie factice comprise.

Le service de diffusion (machincast.service.ServiceState), lu par la fenêtre qui ouvre le bloc :

- installé, l'antenne ne prend pas la sortie factice : seule une installation provisoire, sans service, le peut ;
- en marche, le type de sortie, la carte de l'antenne et son bouton « Tester » sont grisés, avec une infobulle qui dit
  d'arrêter la diffusion.

« Tester » joue le son de test (sample_sound) sur la carte de sa ligne : 2 secondes de sinusoïde à 1000 Hz, à -3 dB,
présenté au serveur audio comme « MachinCast interface », flux « Son de test ». Le pipeline change d'état par son
pilote (machincast.interface.states.Pilot), jamais dans le fil de l'interface, et son bus est relevé par un minuteur
de Qt. Pendant le son, les deux boutons « Tester » sont grisés ; le bloc dit le son en cours, puis s'il a été joué. Un
bloc caché arrête son son de test.
"""

import time
from collections.abc import Callable

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PySide6.QtCore import QTimer, Signal  # noqa: E402
from PySide6.QtGui import QHideEvent, QStandardItemModel  # noqa: E402
from PySide6.QtWidgets import QComboBox, QPushButton, QWidget  # noqa: E402

from machincast import audio as audio_outputs  # noqa: E402
from machincast.audio import Presentation, UnavailableAudioOutput  # noqa: E402
from machincast.configuration import DUMMY, AudioOutput  # noqa: E402
from machincast.interface import states  # noqa: E402
from machincast.interface.ui.sound_cards import Ui_SoundCards  # noqa: E402
from machincast.service import ABSENT, ServiceState  # noqa: E402

TYPES: tuple[tuple[AudioOutput, str], ...] = (("pipewire", "PipeWire"), ("pulseaudio", "PulseAudio"), ("alsa", "ALSA"))
"""Les types de sortie proposés."""
DUMMY_TYPE: tuple[AudioOutput, str] = ("dummy", "Factice, aucun son")
"""La sortie factice des essais : proposée seulement si elle est déjà configurée."""
DUMMY_OUTPUT = "Sortie factice"
TO_FILL_IN = "(à renseigner)"
"""L'antenne, tant qu'elle n'a pas de carte : Machin player refuse alors de diffuser."""
DUMMY_REFUSED = (
	"Seulement sans service de diffusion installé : l'antenne d'un poste dédié joue toujours sur une carte son."
)
RUNNING_BROADCAST = "Arrêter la diffusion pour choisir la carte son de l'antenne."
WITHOUT_CARD = "Choisir d'abord une carte son."
WITHOUT_SOUND = "La sortie factice ne joue aucun son."
TEST = "Jouer 2 secondes de son de test sur cette carte : une sinusoïde à 1000 Hz, à -3 dB"

FREQUENCY = 1000
"""Hertz."""
LEVEL = -3.0
"""Décibels pleine échelle."""
TEST_SOUND_DURATION = 2.0
"""Secondes ; les scénarios la raccourcissent."""
RATE = 48000
SAMPLES_PER_BUFFER = 4800
"""Un dixième de seconde par tampon."""
MARGIN = 5.0
"""Secondes au-delà de la durée du son au bout desquelles un son de test qui ne finit pas est abandonné."""
READING = 50
"""Millisecondes entre deux relèves du bus du son de test."""
TEST_SOUND = Presentation("MachinCast interface", "Son de test")

output_factory: Callable[..., Gst.Element] = audio_outputs.create_output
"""La sortie du son de test ; les scénarios la remplacent par une sortie factice."""


def sample_sound(output: AudioOutput, device: str) -> Gst.Pipeline:
	"""Le pipeline du son de test sur la carte ; lève UnavailableAudioOutput si sa sortie ne peut pas être créée."""
	Gst.init(None)
	pipeline = Gst.Pipeline.new("son-de-test")
	source = Gst.ElementFactory.make("audiotestsrc", "source")
	filter_ = Gst.ElementFactory.make("capsfilter", None)
	conversion = Gst.ElementFactory.make("audioconvert", None)
	resampling = Gst.ElementFactory.make("audioresample", None)
	if (source is None) or (filter_ is None) or (conversion is None) or (resampling is None):
		raise UnavailableAudioOutput(
			"audiotestsrc, audioconvert ou audioresample introuvable, installer gstreamer1.0-plugins-base"
		)
	source.set_property("wave", "sine")
	source.set_property("freq", float(FREQUENCY))
	source.set_property("volume", 10 ** (LEVEL / 20))
	source.set_property("samplesperbuffer", SAMPLES_PER_BUFFER)
	source.set_property("num-buffers", max(1, round(TEST_SOUND_DURATION * RATE / SAMPLES_PER_BUFFER)))
	filter_.set_property("caps", Gst.Caps.from_string(f"audio/x-raw,rate={RATE},channels=2"))
	sink = output_factory(output, device, presentation=TEST_SOUND)
	sink.set_name("puits")
	for item in (source, filter_, conversion, resampling, sink):
		pipeline.add(item)
	source.link(filter_)
	filter_.link(conversion)
	conversion.link(resampling)
	resampling.link(sink)
	return pipeline


class SoundCards(QWidget):
	"""Le type de sortie, et les cartes son de l'antenne et de la pré-écoute, chacune avec son bouton « Tester »."""

	changed = Signal()
	"""Un autre choix : la fenêtre revoit si elle peut l'enregistrer (valide)."""

	def __init__(
		self,
		output: AudioOutput,
		on_air: str | None,
		preview: str | None,
		service: ServiceState = ABSENT,
		parent: QWidget | None = None,
		clock: Callable[[], float] = time.monotonic,
	) -> None:
		super().__init__(parent)
		self.ui = Ui_SoundCards()
		self.ui.setupUi(self)
		self.service = service
		self.clock = clock
		"""L'horloge monotone du poste : un son de test qui ne finit pas est abandonné."""
		self._pipeline: Gst.Pipeline | None = None
		self._piloted: states.Pilot | None = None
		self._card = ""
		self._end = 0.0
		self._reading = QTimer(self)
		self._reading.setInterval(READING)
		self._reading.timeout.connect(self._read_off)
		ui = self.ui
		types = list(TYPES)
		if output == "dummy":
			types.append(DUMMY_TYPE)
		for value, text in types:
			ui.output.addItem(text, value)
		ui.output.setCurrentIndex(ui.output.findData(output))
		self._fill_cards(on_air, preview)
		ui.output.currentIndexChanged.connect(self._change_type)
		ui.on_air.currentIndexChanged.connect(self._refresh)
		ui.preview.currentIndexChanged.connect(self._refresh)
		ui.test_on_air.clicked.connect(lambda: self._test(ui.on_air))
		ui.test_preview.clicked.connect(lambda: self._test(ui.preview))
		self._say("")
		self._refresh()

	# ─── Ce qui est choisi ─────────────────────────────────────

	def chosen_output(self) -> AudioOutput:
		output: AudioOutput = self.ui.output.currentData()
		return output

	def chosen_on_air(self) -> str | None:
		data = self.ui.on_air.currentData()
		if data is None:
			return None
		return str(data)

	def chosen_preview(self) -> str | None:
		data = self.ui.preview.currentData()
		if data is None:
			return None
		return str(data)

	def valid(self) -> bool:
		"""Une pré-écoute, sur une autre carte que l'antenne."""
		preview = self.chosen_preview()
		return (preview is not None) and (preview != self.chosen_on_air())

	# ─── Listes ────────────────────────────────────────────────

	def _fill_cards(self, on_air: str | None, preview: str | None) -> None:
		found_list = audio_outputs.devices(self.chosen_output())
		for choice in (self.ui.on_air, self.ui.preview):
			choice.blockSignals(True)
			choice.clear()
		_fill(self.ui.on_air, on_air, found_list)
		_fill(self.ui.preview, preview, found_list)
		for choice in (self.ui.on_air, self.ui.preview):
			choice.blockSignals(False)

	def _change_type(self) -> None:
		"""Les cartes du nouveau type : l'antenne reste à renseigner, sauf sur la sortie factice ; la pré-écoute garde
		la sienne si elle y est, sinon la première autre carte, sinon la sortie factice."""
		on_air = None
		if self.chosen_on_air() == DUMMY:
			on_air = DUMMY
		found_list = [p.identifier for p in audio_outputs.devices(self.chosen_output())]
		preview = self.chosen_preview()
		if (preview != DUMMY) and (preview not in found_list):
			preview = next((card for card in found_list if card != on_air), DUMMY)
		self._fill_cards(on_air, preview)
		self._refresh()

	def _refresh(self) -> None:
		"""Grise ce qui ne peut pas être choisi, et les boutons qui ne peuvent pas servir."""
		ui = self.ui
		on_air, preview = self.chosen_on_air(), self.chosen_preview()
		_grey_out(ui.on_air, preview, refuse_dummy=self.service.installed)
		_grey_out(ui.preview, on_air, refuse_dummy=False)
		locked = (self.service.installed) and (self.service.running)
		for item in (ui.output, ui.on_air):
			item.setEnabled(not locked)
		ui.output.setToolTip("Le serveur audio par lequel passent l'antenne et la pré-écoute")
		ui.on_air.setToolTip("La carte son sur laquelle Machin player diffuse l'antenne")
		if locked:
			for item in (ui.output, ui.on_air):
				item.setToolTip(RUNNING_BROADCAST)
		ongoing = self._pipeline is not None
		_set_button(ui.test_on_air, on_air, ongoing, locked)
		_set_button(ui.test_preview, preview, ongoing, False)
		self.changed.emit()

	# ─── Son de test ───────────────────────────────────────────

	def _test(self, choice: QComboBox) -> None:
		card = choice.currentData()
		if (self._pipeline is not None) or (card is None) or (card == DUMMY):
			return
		self._card = choice.currentText()
		try:
			pipeline = sample_sound(self.chosen_output(), str(card))
		except UnavailableAudioOutput as error:
			self._say(f"Son de test impossible sur « {self._card} » : {error}")
			return
		self._pipeline = pipeline
		self._piloted = states.Pilot(pipeline)
		self._end = self.clock() + TEST_SOUND_DURATION + MARGIN
		self._say(f"Son de test sur « {self._card} »…")
		self._piloted.to(Gst.State.PLAYING)
		self._reading.start()
		self._refresh()

	def _read_off(self) -> None:
		pipeline = self._pipeline
		if pipeline is None:
			return
		if (self._piloted is not None) and (self._piloted.has_failed()):
			self._finish(f"Son de test impossible sur « {self._card} » : la carte ne s'ouvre pas.")
			return
		bus = pipeline.get_bus()
		assert bus is not None
		while (message := bus.pop()) is not None:
			if message.type == Gst.MessageType.EOS:
				self._finish(f"Son de test joué sur « {self._card} ».")
				return
			if message.type == Gst.MessageType.ERROR:
				error, _detail = message.parse_error()
				self._finish(f"Son de test impossible sur « {self._card} » : {error.message}")
				return
		if self.clock() > self._end:
			self._finish(f"Son de test impossible sur « {self._card} » : la carte ne répond pas.")

	def _finish(self, text: str) -> None:
		self.halt()
		self._say(text)

	def halt(self) -> None:
		"""Arrête le son de test en cours, sans l'attendre."""
		self._reading.stop()
		if self._piloted is not None:
			self._piloted.switch_off()
		self._pipeline, self._piloted = None, None
		self._refresh()

	def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802 : nom imposé par Qt
		self.halt()
		super().hideEvent(event)

	def _say(self, text: str) -> None:
		self.ui.trial.setText(text)
		self.ui.trial.setVisible(text != "")

	def text(self) -> str:
		"""Ce que le bloc dit du son de test."""
		return str(self.ui.trial.text())


def _fill(choice: QComboBox, current: str | None, found_list: list[audio_outputs.Device]) -> None:
	"""La carte configurée d'abord, « (introuvable) » si elle n'est pas sur le poste, « (à renseigner) » s'il n'y en a
	pas ; puis les autres cartes du poste ; puis la sortie factice, si elle n'est pas déjà en tête."""
	if current is None:
		choice.addItem(TO_FILL_IN, None)
	elif current == DUMMY:
		choice.addItem(DUMMY_OUTPUT, DUMMY)
	else:
		name = next((p.name for p in found_list if p.identifier == current), f"{current} (introuvable)")
		choice.addItem(name, current)
	for device in found_list:
		if device.identifier != current:
			choice.addItem(device.name, device.identifier)
	if current != DUMMY:
		choice.addItem(DUMMY_OUTPUT, DUMMY)
	choice.setCurrentIndex(0)


def _grey_out(choice: QComboBox, excluded: object, refuse_dummy: bool) -> None:
	"""La carte de l'autre choix est grisée ; la sortie factice aussi, si elle est refusée."""
	model = choice.model()
	assert isinstance(model, QStandardItemModel)
	for index in range(choice.count()):
		data = choice.itemData(index)
		line = model.item(index)
		refused = (data == DUMMY) and (refuse_dummy)
		line.setEnabled((data != excluded) and (not refused))
		tooltip = ""
		if refused:
			tooltip = DUMMY_REFUSED
		line.setToolTip(tooltip)


def _set_button(button: QPushButton, card: str | None, ongoing: bool, locked: bool) -> None:
	tooltip = TEST
	if locked:
		tooltip = RUNNING_BROADCAST
	elif card is None:
		tooltip = WITHOUT_CARD
	elif card == DUMMY:
		tooltip = WITHOUT_SOUND
	button.setToolTip(tooltip)
	button.setEnabled((tooltip == TEST) and (not ongoing))
