"""Les entrées audio, dans les Paramètres du service, page « Audio » (https://github.com/dascritch/machincast/issues/622,
ticket enfant de https://github.com/dascritch/machincast/issues/513).

- AudioInputs : le bloc « Entrées audio » ; ajouter une entrée de carte son du poste (machincast.audio.input_devices),
  hors de l'antenne et de la pré-écoute, la nommer, la retirer. Un nom vide, ou pris par une autre entrée, empêche
  d'enregistrer, et le bloc dit pourquoi. Une entrée de la configuration que le poste ne voit plus reste, « introuvable ».
- InputLevel, InputPreview (https://github.com/dascritch/machincast/issues/624) : chaque entrée a son VU-mètre, qui
  montre sa modulation tant que le bloc est affiché (machincast.interface.monitor.InputMonitor) ; une entrée
  introuvable le dit à sa place. « Pré-écoute » écoute l'entrée choisie sur la sortie de pré-écoute, jamais à
  l'antenne. Service installé, l'un et l'autre l'écoutent par le PipeWire du service, comme le moniteur de l'antenne.
- InputReservation : le service installé, des entrées changées se réservent aussitôt au PipeWire du service, sans
  relancer install.sh --service : pkexec lance python -m machincast.input_reservation, avec l'authentification d'un
  administrateur, qui réécrit le fragment WirePlumber des sessions du poste et relance le WirePlumber du service ;
  puis l'interface relance celui de sa session (systemctl --user restart wireplumber.service), qui les lâche.
"""

import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PySide6.QtCore import QObject, QProcess, Qt, QTimer, Signal  # noqa: E402
from PySide6.QtGui import QHideEvent, QShowEvent  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
	QAbstractItemView,
	QComboBox,
	QGroupBox,
	QHBoxLayout,
	QHeaderView,
	QLabel,
	QPushButton,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)
from shiboken6 import isValid  # noqa: E402

from machincast import audio  # noqa: E402
from machincast.configuration import DUMMY, Audio, AudioInput, AudioOutput  # noqa: E402
from machincast.i18n import _  # noqa: E402
from machincast.interface import intents, states  # noqa: E402
from machincast.interface.monitor import InputMonitor, Unavailable, input_source  # noqa: E402
from machincast.interface.vu_meter import VuMeter  # noqa: E402

TITLE = _("Audio inputs")
EXPLANATION = _(
	"The sound card inputs that MachinCast can put on air, like a stream: a production studio, for instance. Each one"
	" becomes a feed, with its stream, under its name. With the broadcast service, they are reserved for it as soon as"
	" they are saved."
)
NAME = 0
DEVICE = 1
LEVEL = 2
"""Les colonnes du tableau des entrées."""
DEVICE_ROLE = Qt.ItemDataRole.UserRole
"""Le rôle qui porte, sur la cellule du nom, le périphérique de l'entrée."""
NOT_FOUND = _("{device} (not found)")
EMPTY_NAME = _("Each audio input needs a name.")
SAME_NAME = _("Two audio inputs are named “{name}”.")
NOTHING_TO_ADD = _("No other sound card input on this computer")
PRE_LISTEN = _("🎧 Pre-listen")
STOP_PRE_LISTEN = _("⏹ Stop the pre-listen")
PRE_LISTEN_TIP = _("Listens to the chosen input on the pre-listen output, never on air.")
WITHOUT_PRE_LISTEN = _("The pre-listen output is the dummy output: nothing to hear.")
PRE_LISTEN_READING = 100
"""Millisecondes entre deux relèves du bus de la pré-écoute."""

RESERVED = _("Audio inputs reserved for the broadcast service.")
REFUSED = _("Audio inputs not reserved: authentication refused.")
FAILED = _("Audio inputs not reserved: {error}")
WITHOUT_PKEXEC = _("Audio inputs not reserved: pkexec missing, install the pkexec package.")
SESSION_NOT_RESTARTED = _(
	"Audio inputs reserved for the broadcast service; the WirePlumber of this session did not restart: {error}"
)
REFUSED_CODES = (126, 127)
"""Les codes de pkexec : authentification refusée ou annulée, ou autorisation impossible à demander."""


class AudioInputs(QGroupBox):
	"""Le bloc « Entrées audio » ; changed à chaque changement."""

	changed = Signal()

	def __init__(
		self,
		output: AudioOutput,
		inputs: Sequence[AudioInput],
		excluded: Sequence[str | None],
		parent: QWidget | None = None,
		*,
		preview: str | None = None,
	) -> None:
		"""excluded : les périphériques de l'antenne et de la pré-écoute, qui ne sont pas des entrées ; preview : le
		périphérique de pré-écoute, où s'écoute une entrée."""
		super().__init__(TITLE, parent)
		self.setObjectName("audio_inputs")
		self.output = output
		self.listening = Audio(output=output, device=None, preview=(preview) or (DUMMY))
		"""Ce que le VU-mètre et la pré-écoute d'une entrée écoutent."""
		self.preview_player = InputPreview(self.listening, self)
		self.preview_player.stopped.connect(self._preview_stopped)
		self.excluded = set()
		for taken in excluded:
			if taken is not None:
				self.excluded.add(taken)
		explanation = QLabel(EXPLANATION, self)
		explanation.setWordWrap(True)
		self.table = QTableWidget(0, 3, self)
		self.table.setObjectName("inputs_table")
		self.table.setHorizontalHeaderLabels([_("Name"), _("Input"), _("Level")])
		self.table.verticalHeader().hide()
		self.table.horizontalHeader().setSectionResizeMode(NAME, QHeaderView.ResizeMode.Stretch)
		self.table.horizontalHeader().setSectionResizeMode(DEVICE, QHeaderView.ResizeMode.Stretch)
		self.table.horizontalHeader().setSectionResizeMode(LEVEL, QHeaderView.ResizeMode.Stretch)
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.choice = QComboBox(self)
		self.choice.setObjectName("input_choice")
		self.add = QPushButton(intents.label(intents.ADD, _("Add this input")), self)
		self.add.setObjectName("add_input")
		self.remove = QPushButton(intents.label(intents.REMOVE, _("Remove the input")), self)
		self.remove.setObjectName("remove_input")
		self.pre_listen = QPushButton(PRE_LISTEN, self)
		self.pre_listen.setObjectName("pre_listen_input")
		self.pre_listen.setCheckable(True)
		self.pre_listen.setToolTip(PRE_LISTEN_TIP)
		self.error = QLabel(self)
		self.error.setObjectName("inputs_error")
		self.error.setWordWrap(True)
		self.error.setStyleSheet("color: palette(highlight);")
		actions = QHBoxLayout()
		actions.addWidget(self.choice, 1)
		actions.addWidget(self.add)
		actions.addWidget(self.remove)
		actions.addWidget(self.pre_listen)
		arrangement = QVBoxLayout(self)
		arrangement.addWidget(explanation)
		arrangement.addWidget(self.table)
		arrangement.addLayout(actions)
		arrangement.addWidget(self.error)
		self.names: dict[str, str] = {}
		"""Ce que le poste montre de chaque entrée qu'il voit, par périphérique."""
		for seen in audio.input_devices(output):
			self.names[seen.identifier] = seen.name
		for audio_input in inputs:
			self._append(audio_input.device, audio_input.name)
		self.add.clicked.connect(self._add)
		self.remove.clicked.connect(self._remove)
		self.pre_listen.toggled.connect(self._pre_listen)
		self.table.itemChanged.connect(self._changed)
		self.table.itemSelectionChanged.connect(self._offer)
		self._offer()
		self._check()

	def _append(self, device: str, name: str) -> None:
		row = self.table.rowCount()
		self.table.insertRow(row)
		named = QTableWidgetItem(name)
		named.setData(DEVICE_ROLE, device)
		shown = QTableWidgetItem(self.names.get(device, NOT_FOUND.format(device=device)))
		shown.setFlags(shown.flags() & ~Qt.ItemFlag.ItemIsEditable)
		shown.setToolTip(device)
		self.table.blockSignals(True)
		self.table.setItem(row, NAME, named)
		self.table.setItem(row, DEVICE, shown)
		self.table.blockSignals(False)
		level = InputLevel(self.listening, device, self.table)
		self.table.setCellWidget(row, LEVEL, level)
		if self.isVisible():
			level.monitor.start()

	def levels(self) -> list["InputLevel"]:
		"""Les VU-mètres des entrées, dans l'ordre du tableau."""
		found = []
		for row in range(self.table.rowCount()):
			level = self.table.cellWidget(row, LEVEL)
			assert isinstance(level, InputLevel)
			found.append(level)
		return found

	def showEvent(self, event: QShowEvent) -> None:
		"""Les VU-mètres écoutent leur entrée tant que le bloc est affiché."""
		super().showEvent(event)
		for level in self.levels():
			if not level.monitor.active():
				level.monitor.start()

	def hideEvent(self, event: QHideEvent) -> None:
		super().hideEvent(event)
		self.halt()

	def halt(self) -> None:
		"""Les VU-mètres et la pré-écoute s'arrêtent : la fenêtre se ferme. Le bloc peut se cacher en étant détruit,
		son tableau déjà parti."""
		if (not isValid(self.table)) or (not isValid(self.preview_player)):
			return
		self.preview_player.halt()
		for level in self.levels():
			level.monitor.halt()
		self.pre_listen.setChecked(False)

	def devices(self) -> list[str]:
		"""Les périphériques des entrées, dans l'ordre du tableau."""
		found = []
		for row in range(self.table.rowCount()):
			cell = self.table.item(row, NAME)
			assert cell is not None
			found.append(str(cell.data(DEVICE_ROLE)))
		return found

	def _offer(self) -> None:
		"""Les entrées du poste qu'on peut encore ajouter ; « Retirer » pour une ligne choisie."""
		self.choice.clear()
		taken = set(self.devices()) | self.excluded
		for device, name in self.names.items():
			if device not in taken:
				self.choice.addItem(name, device)
				self.choice.setItemData(self.choice.count() - 1, device, Qt.ItemDataRole.ToolTipRole)
		if self.choice.count() == 0:
			self.choice.addItem(NOTHING_TO_ADD)
			self.choice.setEnabled(False)
			self.add.setEnabled(False)
		else:
			self.choice.setEnabled(True)
			self.add.setEnabled(True)
		self.remove.setEnabled(self.table.currentRow() >= 0)
		heard = self.listening.preview != DUMMY
		self.pre_listen.setEnabled(((self.table.currentRow() >= 0) and (heard)) or (self.pre_listen.isChecked()))
		self.pre_listen.setToolTip(PRE_LISTEN_TIP)
		if not heard:
			self.pre_listen.setToolTip(WITHOUT_PRE_LISTEN)

	def _add(self) -> None:
		device = self.choice.currentData()
		if device is None:
			return
		self._append(str(device), self.choice.currentText())
		self.table.setCurrentCell(self.table.rowCount() - 1, NAME)
		self._changed()

	def _remove(self) -> None:
		row = self.table.currentRow()
		if row < 0:
			return
		level = self.table.cellWidget(row, LEVEL)
		if isinstance(level, InputLevel):
			level.monitor.halt()
		self.table.removeRow(row)
		self._changed()

	def _pre_listen(self, chosen: bool) -> None:  # noqa: FBT001  # signal de Qt : le booléen arrive par sa position
		"""L'entrée choisie, sur la sortie de pré-écoute ; décoché, la pré-écoute s'arrête."""
		self.error.setVisible(False)
		if not chosen:
			self.preview_player.halt()
			self.pre_listen.setText(PRE_LISTEN)
			self._check()
			return
		devices = self.devices()
		row = self.table.currentRow()
		if (row < 0) or (row >= len(devices)):
			self.pre_listen.setChecked(False)
			return
		problem = self.preview_player.play(devices[row])
		if problem is not None:
			self.pre_listen.setChecked(False)
			self.error.setText(problem)
			self.error.setVisible(True)
			return
		self.pre_listen.setText(STOP_PRE_LISTEN)

	def _preview_stopped(self, problem: str) -> None:
		self.pre_listen.setChecked(False)
		if problem != "":
			self.error.setText(problem)
			self.error.setVisible(True)

	def _changed(self) -> None:
		self._offer()
		self._check()
		self.changed.emit()

	def _check(self) -> None:
		self.error.setText((self.problem()) or (""))
		self.error.setVisible(self.problem() is not None)

	def problem(self) -> str | None:
		"""Ce qui empêche d'enregistrer les entrées : un nom vide, ou pris deux fois ; None sinon."""
		seen: list[str] = []
		for audio_input in self.chosen():
			if audio_input.name == "":
				return EMPTY_NAME
			if audio_input.name in seen:
				return SAME_NAME.format(name=audio_input.name)
			seen.append(audio_input.name)
		return None

	def valid(self) -> bool:
		return self.problem() is None

	def chosen(self) -> tuple[AudioInput, ...]:
		"""Les entrées telles que le bloc les montre, les noms sans les espaces qui les entourent."""
		found = []
		for row in range(self.table.rowCount()):
			cell = self.table.item(row, NAME)
			assert cell is not None
			found.append(AudioInput(device=str(cell.data(DEVICE_ROLE)), name=cell.text().strip()))
		return tuple(found)


class InputLevel(QWidget):
	"""Le VU-mètre d'une entrée, ou, à sa place, pourquoi elle ne s'écoute pas : une entrée introuvable."""

	def __init__(self, listening: Audio | None, device: str, parent: QWidget | None = None) -> None:
		"""listening : la sortie où s'écoute l'entrée ; None, le VU-mètre est indisponible, comme celui de l'antenne."""
		super().__init__(parent)
		self.setObjectName("input_level")
		self.meter = VuMeter(self)
		self.meter.setMinimumHeight(28)
		self.unavailable = QLabel(self)
		self.unavailable.setObjectName("input_unavailable")
		self.unavailable.setWordWrap(True)
		self.unavailable.hide()
		arrangement = QHBoxLayout(self)
		arrangement.setContentsMargins(2, 2, 2, 2)
		arrangement.addWidget(self.meter)
		arrangement.addWidget(self.unavailable)
		self.monitor = InputMonitor(listening, device, self)
		self.monitor.changed.connect(self._show)

	def _show(self) -> None:
		problem = self.monitor.unavailable
		self.unavailable.setText((problem) or (""))
		self.unavailable.setVisible(problem is not None)
		self.meter.setVisible(problem is None)
		self.meter.display(self.monitor.levels, self.monitor.peaks)


class InputPreview(QObject):
	"""Une entrée écoutée sur la sortie de pré-écoute, jamais à l'antenne ; stopped dit pourquoi elle s'arrête, vide
	pour un arrêt demandé."""

	stopped = Signal(str)

	def __init__(self, listening: Audio, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.listening = listening
		self.device: str | None = None
		self._pipeline: Gst.Pipeline | None = None
		self._piloted: states.Pilot | None = None
		self._reading = QTimer(self)
		self._reading.setInterval(PRE_LISTEN_READING)
		self._reading.timeout.connect(self._read_off)

	def active(self) -> bool:
		return self._pipeline is not None

	def play(self, device: str) -> str | None:
		"""L'entrée sur la sortie de pré-écoute ; ce qui l'empêche, None sinon."""
		self.halt()
		try:
			source = input_source(self.listening, device)
		except Unavailable as error:
			return str(error)
		try:
			output = audio.create_output(self.listening.output, self.listening.preview, presentation=audio.PREVIEW)
		except audio.UnavailableAudioOutput as error:
			return str(error)
		pipeline = Gst.Pipeline.new("pre-ecoute-entree")
		conversion = Gst.ElementFactory.make("audioconvert", None)
		resampling = Gst.ElementFactory.make("audioresample", None)
		assert (conversion is not None) and (resampling is not None)
		for item in (source, conversion, resampling, output):
			pipeline.add(item)
		source.link(conversion)
		conversion.link(resampling)
		resampling.link(output)
		self.device, self._pipeline = device, pipeline
		self._piloted = states.Pilot(pipeline)
		self._piloted.to(Gst.State.PLAYING)
		self._reading.start()
		return None

	def halt(self) -> None:
		self._reading.stop()
		if self._piloted is not None:
			self._piloted.switch_off()
		self._pipeline, self._piloted, self.device = None, None, None

	def _read_off(self) -> None:
		pipeline = self._pipeline
		if pipeline is None:
			return
		bus = pipeline.get_bus()
		assert bus is not None
		message = bus.pop_filtered(Gst.MessageType.ERROR | Gst.MessageType.EOS)
		if message is None:
			return
		problem = _("the input has closed.")
		if message.type == Gst.MessageType.ERROR:
			error, _detail = message.parse_error()
			problem = str(error.message)
		self.halt()
		self.stopped.emit(_("Pre-listen stopped: {problem}").format(problem=problem))


class InputReservation(QObject):
	"""Réserve aussitôt les entrées de la configuration au service, par pkexec ; announced dit ce qu'il en est."""

	announced = Signal(str)

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self.process: QProcess | None = None
		self.root: Path | None = None
		"""Une autre racine du système, dans les scénarios."""

	def start(self, configuration: Path) -> None:
		"""Une seule réservation à la fois : une autre, en cours, prendra la configuration telle qu'elle est écrite."""
		if self.process is not None:
			return
		pkexec = shutil.which("pkexec")
		if pkexec is None:
			self.announced.emit(WITHOUT_PKEXEC)
			return
		arguments = [sys.executable, "-m", "machincast.input_reservation", "--config", str(configuration.absolute())]
		if self.root is not None:
			arguments += ["--root", str(self.root)]
		process = QProcess(self)
		process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
		process.finished.connect(self._reserved)
		self.process = process
		process.start(pkexec, arguments)

	def _reserved(self, code: int, status: QProcess.ExitStatus) -> None:
		process = self.process
		assert process is not None
		output = bytes(process.readAll().data()).decode(errors="replace")
		process.deleteLater()
		if (code != 0) or (status != QProcess.ExitStatus.NormalExit):
			self.process = None
			if code in REFUSED_CODES:
				self.announced.emit(REFUSED)
				return
			self.announced.emit(FAILED.format(error=_last_line(output, code)))
			return
		# Le WirePlumber de la session lâche les entrées qu'il ne doit plus ouvrir.
		session = QProcess(self)
		session.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
		session.finished.connect(self._session_restarted)
		self.process = session
		session.start("systemctl", ["--user", "restart", "wireplumber.service"])

	def _session_restarted(self, code: int, status: QProcess.ExitStatus) -> None:
		process = self.process
		assert process is not None
		self.process = None
		output = bytes(process.readAll().data()).decode(errors="replace")
		process.deleteLater()
		if (code == 0) and (status == QProcess.ExitStatus.NormalExit):
			self.announced.emit(RESERVED)
			return
		self.announced.emit(SESSION_NOT_RESTARTED.format(error=_last_line(output, code)))


def _last_line(output: str, code: int) -> str:
	error = _("exit code {code}").format(code=code)
	for line in output.splitlines():
		if line.strip():
			error = line.strip()
	return error
