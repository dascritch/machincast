"""Écran de simulation (https://github.com/dascritch/machincast/issues/37, spec § 8.7).

L'onglet « Simulation » (SimulationScreen), qui se ferme, s'ouvre par « Affichage → Ouvrir l'onglet Simulation »
(machincast.interface.window). On y règle le début et la fin de la période, d'abord de l'heure qu'il est, à la
minute, à un jour plus tard. « Simuler » lance Machin player --simulation (simulation_command), par le Python de
l'interface et avec sa configuration, dans un processus à part (QProcess) : l'interface reste utilisable, et la
simulation garde le rôle de la lecture en base, où elle n'écrit rien (spec § 5.5). Ses sorties vont dans un répertoire
temporaire, propre à l'onglet et effacé à sa fermeture : jamais dans les sorties de la configuration.

À la fin du processus, la table montre les passages de son CSV, avec l'artiste et le titre masqués comme sur la page
publique ; la liste, les alertes et incidents qu'il a signalés sur sa sortie d'erreur (« simulation : … »). Un échec
donne la dernière ligne de sa sortie d'erreur. « Exporter… » enregistre l'une des trois sorties, .csv, .pls ou .html,
selon le filtre choisi dans le sélecteur de fichier (dialogs.choose_export) ; le nom reçoit l'extension du format
s'il ne l'a pas déjà : un export ne peut donc jamais remplacer un fichier sonore
(https://github.com/dascritch/machincast/issues/96, machincast.protection).
"""

import csv
import logging
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, QDateTime, QProcess, QTime, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
	QAbstractItemView,
	QDateTimeEdit,
	QHBoxLayout,
	QLabel,
	QListWidget,
	QPushButton,
	QTableView,
	QVBoxLayout,
	QWidget,
)

from machincast.clock import Clock
from machincast.i18n import _, counted
from machincast.interface import dialogs
from machincast.interface.columns import Columns
from machincast.log import TIMESTAMP
from machincast.player.simulation import default_name
from machincast.protection import check_writing

log = logging.getLogger(__name__)

PERIOD = timedelta(days=1)
"""Durée de la période proposée à l'ouverture de l'onglet."""
NAME = "simulation"
"""Nom des sorties dans le répertoire temporaire de l'onglet."""
DATE_FORMAT = "yyyy-MM-dd HH:mm"
COLUMNS = (_("Start"), _("End"), _("Artist"), _("Title"), _("Location"), _("Event"), _("Sequence"), _("Bank"))
FIELDS = ("debut", "fin", "artiste", "titre", "emplacement", "evenement", "sequence", "banque")
"""Les colonnes du CSV de la simulation montrées dans la table, dans l'ordre de COLONNES."""
FORMATS = {
	_("CSV spreadsheet (*.csv)"): ".csv",
	_("PLS playlist (*.pls)"): ".pls",
	_("HTML page (*.html)"): ".html",
}
"""Filtres du sélecteur d'export, et l'extension de la sortie que chacun enregistre."""
ANOMALY_PREFIX = _("simulation: ")
PROMPTS = _("Set the period, then click on “Simulate”.")
ONGOING = _("Simulation running…")
INVALID_PERIOD = _("The end must follow the start.")


def simulation_command(configuration: Path | None) -> list[str]:
	"""Machin player, lancé par le Python de l'interface, avec la même configuration qu'elle."""
	command = [sys.executable, "-m", "machincast.player"]
	if configuration is not None:
		command += ["--config", str(configuration.expanduser().absolute())]
	return command


def with_extension(path: Path, extension: str) -> Path:
	"""Le chemin, avec l'extension du format exporté s'il ne l'a pas déjà : « grille » devient « grid.pls »,
	« matinale.flac » devient « matinale.flac.csv »."""
	if path.suffix.lower() == extension:
		return path
	return path.with_name(f"{path.name}{extension}")


def report(plays: int, anomalies: int) -> str:
	play_text = _("No play")
	if plays > 0:
		play_text = counted("{count} play", "{count} plays", plays)
	anomaly_text = _("no alert nor incident")
	if anomalies > 0:
		anomaly_text = counted("{count} alert or incident", "{count} alerts or incidents", anomalies)
	return _("{play_text}, {anomaly_text}. Nothing was written to the database.").format(
		play_text=play_text, anomaly_text=anomaly_text
	)


def _instant(editing: QDateTimeEdit) -> datetime:
	"""L'instant réglé, en heure du poste."""
	moment = editing.dateTime().toPython()
	assert isinstance(moment, datetime)
	return moment.astimezone()


class SimulationScreen(QWidget):
	finished = Signal()
	"""La simulation lancée s'est terminée, réussie ou non."""

	def __init__(self, clock: Clock, configuration: Path | None, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.configuration = configuration
		self.temporary = Path(tempfile.mkdtemp(prefix="machincast-simulation-"))
		"""Répertoire des sorties de la simulation, effacé à la fermeture de l'onglet."""
		self.process: QProcess | None = None
		self.launched_list = 0
		"""Simulations lancées depuis l'ouverture de l'onglet."""
		self.period: tuple[datetime, datetime] | None = None
		"""Période de la dernière simulation réussie, celle qu'on exporte."""
		arrangement = QVBoxLayout(self)
		setting = QHBoxLayout()
		# Les champs sont à la minute : les secondes de l'horloge tombent.
		start = clock.now().astimezone()
		self.start = self._editing(start)
		self.end = self._editing(start + PERIOD)
		setting.addWidget(QLabel(_("From"), self))
		setting.addWidget(self.start)
		setting.addWidget(QLabel(_("to"), self))
		setting.addWidget(self.end)
		self.simulate = QPushButton(_("Simulate"), self)
		self.simulate.setToolTip(
			_("Machin player simulates the broadcast of the period, without sound and without writing to the database")
		)
		self.simulate.clicked.connect(self.launch)
		setting.addWidget(self.simulate)
		self.export = QPushButton(_("Export…"), self)
		self.export.setToolTip(_("Saves the result as .csv, .pls or .html"))
		self.export.setEnabled(False)
		self.export.clicked.connect(self._export)
		setting.addWidget(self.export)
		setting.addStretch()
		arrangement.addLayout(setting)
		self.count = QLabel(PROMPTS, self)
		self.count.setWordWrap(True)
		arrangement.addWidget(self.count)
		self.model = QStandardItemModel(0, len(COLUMNS), self)
		self.model.setHorizontalHeaderLabels(list(COLUMNS))
		self.table = QTableView(self)
		self.table.setModel(self.model)
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.verticalHeader().hide()
		self.table.horizontalHeader().setStretchLastSection(True)
		self.columns = Columns(self.table, "simulation")
		arrangement.addWidget(self.table, 1)
		self.anomalies = QListWidget(self)
		self.anomalies.setToolTip(_("Alerts and incidents of the simulation"))
		self.anomalies.setMaximumHeight(120)
		self.anomalies.hide()
		arrangement.addWidget(self.anomalies)

	def _editing(self, instant: datetime) -> QDateTimeEdit:
		local = instant.astimezone()
		moment = QDateTime(QDate(local.year, local.month, local.day), QTime(local.hour, local.minute))
		editing = QDateTimeEdit(moment, self)
		editing.setDisplayFormat(DATE_FORMAT)
		editing.setCalendarPopup(True)
		return editing

	def ongoing(self) -> bool:
		return self.process is not None

	def refresh(self) -> None:
		"""Rien à relire : le résultat est celui de la dernière simulation, que seul « Simuler » relance."""

	def launch(self) -> None:
		start, end = _instant(self.start), _instant(self.end)
		if end <= start:
			self.count.setText(INVALID_PERIOD)
			return
		self._empty()
		program, *arguments = simulation_command(self.configuration)
		arguments += [
			"--simulation",
			start.isoformat(timespec="minutes"),
			end.isoformat(timespec="minutes"),
			"--directory",
			str(self.temporary),
			"--name",
			NAME,
		]
		process = QProcess(self)
		process.finished.connect(lambda code, _status: self._finish(process, code, (start, end)))
		process.errorOccurred.connect(lambda error: self._fail(process, error))
		self.process = process
		self.launched_list += 1
		self.simulate.setEnabled(False)
		self.count.setText(ONGOING)
		log.info(
			_("simulation from {start} to {end}").format(
				start=start.isoformat(timespec="minutes"), end=end.isoformat(timespec="minutes")
			)
		)
		process.start(program, arguments)

	def _empty(self) -> None:
		self.period = None
		self.export.setEnabled(False)
		self.model.setRowCount(0)
		self.anomalies.clear()
		self.anomalies.hide()
		for old in self.temporary.glob(f"{NAME}.*"):
			# fichier de MachinCast : une sortie de la simulation précédente, dans le répertoire temporaire de l'onglet.
			old.unlink()

	def _fail(self, process: QProcess, error: QProcess.ProcessError) -> None:
		"""Un programme qui ne démarre pas ne finit jamais : finished n'est pas émis."""
		if error == QProcess.ProcessError.FailedToStart:
			self._end(process)
			self.count.setText(_("Simulation impossible: {errorstring}").format(errorstring=process.errorString()))

	def _end(self, process: QProcess) -> None:
		self.process = None
		self.simulate.setEnabled(True)
		process.deleteLater()
		self.finished.emit()

	def _finish(self, process: QProcess, code: int, period: tuple[datetime, datetime]) -> None:
		errors = bytes(process.readAllStandardError().data()).decode("utf-8", errors="replace").splitlines()
		self._end(process)
		anomalies = [line.split(ANOMALY_PREFIX, 1)[1] for line in errors if ANOMALY_PREFIX in line]
		path = self.temporary / f"{NAME}.csv"
		if (code != 0) or (not path.exists()):
			reason = _("Machin player stopped without saying anything")
			# Chaque message de Machin player commence par son horodatage (machincast.log) ; un message peut tenir
			# sur plusieurs lignes.
			messages = [TIMESTAMP.sub("", line) for line in errors if TIMESTAMP.match(line)]
			if messages:
				reason = messages[-1]
			self.count.setText(_("Simulation impossible: {reason}").format(reason=reason))
			return
		plays = self._read(path)
		self.anomalies.addItems(anomalies)
		self.anomalies.setVisible(bool(anomalies))
		self.count.setText(report(plays, len(anomalies)))
		self.period = period
		self.export.setEnabled(True)

	def _read(self, path: Path) -> int:
		with path.open(encoding="utf-8-sig", newline="") as file:
			for line in csv.DictReader(file, delimiter=";"):
				self.model.appendRow([QStandardItem(line[field]) for field in FIELDS])
		return self.model.rowCount()

	def lines(self) -> list[list[str]]:
		return [
			[str(self.model.item(row, column).text()) for column in range(self.model.columnCount())]
			for row in range(self.model.rowCount())
		]

	def _export(self) -> None:
		assert self.period is not None
		offers = f"{default_name(*self.period)}.csv"
		choice = dialogs.choose_export(self, offers, list(FORMATS))
		if choice is None:
			return
		path, filter_ = choice
		extension = FORMATS[filter_]
		destination = with_extension(path, extension)
		try:
			check_writing(destination)
			shutil.copyfile(self.temporary / f"{NAME}{extension}", destination)
		except OSError as error:
			self._announce(_("Export impossible: {error}").format(error=error))
			return
		self._announce(_("Simulation exported to {destination}.").format(destination=destination))

	def _announce(self, text: str) -> None:
		window = self.window()
		bar = getattr(window, "statusBar", None)
		if bar is not None:
			bar().showMessage(text)

	def shut_down(self) -> None:
		"""Arrête la simulation en cours, puis efface le répertoire temporaire de l'onglet."""
		process = self.process
		if process is not None:
			process.kill()
			process.waitForFinished()
		# fichier de MachinCast : le répertoire temporaire de l'onglet, et les sorties de ses simulations.
		shutil.rmtree(self.temporary, ignore_errors=True)
