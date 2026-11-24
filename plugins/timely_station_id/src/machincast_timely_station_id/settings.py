"""Les réglages du station ID régulier, dans la fenêtre du plugin, menu « Plugins » de Machin interface
(https://github.com/dascritch/machincast/issues/460, point « interface.plugin_window »,
https://github.com/dascritch/machincast/issues/587).

La banque des station ID, choisie parmi les banques non supprimées ; les autres identifiants de la station, cochés ; l'écart minimal
et maximal entre deux station ID, en minutes ; le placement. « Enregistrer » vérifie les réglages, puis les écrit dans
la section [plugins.timely_station_id] du fichier de configuration, qui garde ses commentaires et ses autres sections :
la prochaine simulation et la fiche d'un événement les prennent aussitôt, Machin player à son prochain démarrage.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import psycopg
import tomlkit
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QComboBox,
	QFormLayout,
	QHBoxLayout,
	QLabel,
	QListWidget,
	QListWidgetItem,
	QPushButton,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)

from machincast.configuration import Configuration
from machincast.database import Role, open_connection
from machincast_timely_station_id import queries
from machincast_timely_station_id.rule import AFTER, BEFORE, Current, Settings, as_section, read_settings
from machincast_timely_station_id.texts import t

NAME = "timely_station_id"
LONGEST = 120
"""Le plus grand écart réglable, en minutes."""
PLACEMENTS = (
	(BEFORE, "Before the song that would exceed the maximum, once the minimum is past"),
	(AFTER, "After the maximum, without moving any song forward"),
)
DEFAULT = Settings("")

Connect = Callable[[], queries.Connection]


def connector(configuration: Configuration) -> Connect:
	"""La connexion à la base de production, au rôle de l'interface."""

	def connect() -> queries.Connection:
		settings = configuration.database
		return open_connection(settings.socket, settings.production, Role.INTERFACE)

	return connect


def write_section(path: Path, section: dict[str, Any]) -> None:
	"""La section [plugins.timely_station_id] du fichier, remplacée ; le reste du fichier reste tel quel."""
	document = tomlkit.parse(path.read_text(encoding="utf-8"))
	if "plugins" not in document:
		document.add("plugins", tomlkit.table())
	plugins = document["plugins"]
	assert isinstance(plugins, tomlkit.items.Table)
	table = tomlkit.table()
	for key, value in section.items():
		table[key] = value
	plugins[NAME] = table
	path.write_text(tomlkit.dumps(document), encoding="utf-8")


def _minutes(value: int | float) -> int:
	return round(value)


class StationSettings(QWidget):
	def __init__(
		self,
		configuration: Configuration,
		current: Current,
		parent: QWidget | None = None,
		connect: Connect | None = None,
	) -> None:
		super().__init__(parent)
		self.setObjectName(NAME)
		self.path = configuration.path
		self.current = current
		self.open_base = (connect) or (connector(configuration))
		self.message = QLabel(
			t(
				"A station ID at regular intervals, in the events whose box “Regular station ID” is ticked. Machin player"
				" takes these settings at its next start."
			),
			self,
		)
		self.message.setObjectName("message")
		self.message.setWordWrap(True)
		self.bank = QComboBox(self)
		self.bank.setObjectName("bank")
		self.watched = QListWidget(self)
		self.watched.setObjectName("watched")
		self.watched.setToolTip(
			t(
				"These banks also say the name of the radio, for instance a seasonal jingle: a play of one of them counts"
				" as a station ID"
			)
		)
		self.minimum = self._spin("minimum")
		self.maximum = self._spin("maximum")
		self.placement = QComboBox(self)
		self.placement.setObjectName("placement")
		for value, text in PLACEMENTS:
			self.placement.addItem(t(text), value)
		self.save_button = QPushButton(t("Save"), self)
		self.save_button.setObjectName("save")
		self.save_button.clicked.connect(self.save)
		self._layout()
		self._read()

	def _spin(self, name: str) -> QSpinBox:
		spin = QSpinBox(self)
		spin.setObjectName(name)
		spin.setRange(1, LONGEST)
		spin.setSuffix(t(" min"))
		return spin

	def _layout(self) -> None:
		layout = QVBoxLayout(self)
		layout.addWidget(self.message)
		form = QFormLayout()
		form.addRow(t("Bank of the station IDs"), self.bank)
		form.addRow(t("Other identifiers of the station"), self.watched)
		form.addRow(t("Minimum between two station IDs"), self.minimum)
		form.addRow(t("Maximum between two station IDs"), self.maximum)
		form.addRow(t("Placement"), self.placement)
		layout.addLayout(form)
		end = QHBoxLayout()
		end.addStretch()
		end.addWidget(self.save_button)
		layout.addLayout(end)

	def _read(self) -> None:
		"""Les banques de la base, et les réglages en vigueur, sinon ceux par défaut."""
		settings = (self.current.settings) or (DEFAULT)
		names: list[str] = []
		try:
			with self.open_base() as connection:
				names = queries.bank_names(connection)
		except psycopg.Error as error:
			self.message.setText(t("The banks cannot be read: {error}").format(error=error))
		known = list(names)
		for name in settings.banks():
			if (name != "") and (name not in known):
				# Une banque réglée mais introuvable reste proposée, pour se voir et se changer.
				known.append(name)
		self.bank.addItem(t("— choose a bank —"), "")
		for name in known:
			self.bank.addItem(name, name)
		self.bank.setCurrentIndex(max(self.bank.findData(settings.bank), 0))
		for name in known:
			item = QListWidgetItem(name, self.watched)
			item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
			state = Qt.CheckState.Unchecked
			if name in settings.watched:
				state = Qt.CheckState.Checked
			item.setCheckState(state)
		self.minimum.setValue(_minutes(settings.minimum.total_seconds() / 60))
		self.maximum.setValue(_minutes(settings.maximum.total_seconds() / 60))
		self.placement.setCurrentIndex(max(self.placement.findData(settings.placement), 0))

	def section(self) -> dict[str, Any]:
		"""Les réglages de la fenêtre, comme dans machincast.toml."""
		watched = []
		for row in range(self.watched.count()):
			item = self.watched.item(row)
			if (item.checkState() == Qt.CheckState.Checked) and (item.text() != self.bank.currentData()):
				watched.append(item.text())
		section: dict[str, Any] = {"bank": self.bank.currentData()}
		if watched != []:
			section["watched"] = watched
		section["minimum"] = self.minimum.value()
		section["maximum"] = self.maximum.value()
		section["placement"] = self.placement.currentData()
		return section

	def save(self) -> bool:
		found = read_settings(self.section())
		if isinstance(found, str):
			self.message.setText(found)
			return False
		try:
			write_section(self.path, as_section(found))
		except (OSError, ValueError) as error:
			self.message.setText(t("The settings cannot be saved: {error}").format(error=error))
			return False
		self.current.settings = found
		self.message.setText(t("Saved. Restart the broadcast for Machin player to take them."))
		return True
