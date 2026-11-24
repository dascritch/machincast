"""Les réglages de la normalisation du niveau, dans la fenêtre du plugin, menu « Plugins » de Machin interface
(https://github.com/dascritch/machincast/issues/43, point « interface.plugin_window »,
https://github.com/dascritch/machincast/issues/587).

La sonie visée, en LUFS, et le plafond de crête, en dBFS. « Enregistrer » les écrit dans la section
[plugins.loudness_normalization] du fichier de configuration, qui garde ses commentaires et ses autres sections : la
fiche d'un sonore les prend aussitôt, Machin player et Machin indexer à leur prochain démarrage.
"""

from pathlib import Path
from typing import Any

import tomlkit
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from machincast.configuration import Configuration
from machincast_loudness_normalization.rule import (
	HIGHEST_CEILING,
	HIGHEST_TARGET,
	KEY,
	LOWEST_CEILING,
	LOWEST_TARGET,
	Current,
	Settings,
	as_section,
	read_settings,
)
from machincast_loudness_normalization.texts import t


def write_section(path: Path, section: dict[str, Any]) -> None:
	"""La section [plugins.loudness_normalization] du fichier, remplacée ; le reste du fichier reste tel quel."""
	document = tomlkit.parse(path.read_text(encoding="utf-8"))
	if "plugins" not in document:
		document.add("plugins", tomlkit.table())
	plugins = document["plugins"]
	assert isinstance(plugins, tomlkit.items.Table)
	table = tomlkit.table()
	for key, value in section.items():
		table[key] = value
	plugins[KEY] = table
	path.write_text(tomlkit.dumps(document), encoding="utf-8")


class LevelSettings(QWidget):
	def __init__(self, configuration: Configuration, current: Current, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName(KEY)
		self.path = configuration.path
		self.current = current
		self.message = QLabel(
			t(
				"The loudness of each sound is brought to the target by the gain of Machin player, never beyond the peak"
				" ceiling. Machin player and Machin indexer take these settings at their next start."
			),
			self,
		)
		self.message.setObjectName("message")
		self.message.setWordWrap(True)
		self.target = self._spin("target", LOWEST_TARGET, HIGHEST_TARGET, t(" LUFS"))
		self.ceiling = self._spin("ceiling", LOWEST_CEILING, HIGHEST_CEILING, t(" dBFS"))
		settings = (current.settings) or (Settings())
		self.target.setValue(settings.target)
		self.ceiling.setValue(settings.ceiling)
		self.save_button = QPushButton(t("Save"), self)
		self.save_button.setObjectName("save")
		self.save_button.clicked.connect(self.save)
		layout = QVBoxLayout(self)
		layout.addWidget(self.message)
		form = QFormLayout()
		form.addRow(t("Target loudness"), self.target)
		form.addRow(t("Peak ceiling"), self.ceiling)
		layout.addLayout(form)
		end = QHBoxLayout()
		end.addStretch()
		end.addWidget(self.save_button)
		layout.addLayout(end)

	def _spin(self, name: str, lowest: float, highest: float, suffix: str) -> QDoubleSpinBox:
		spin = QDoubleSpinBox(self)
		spin.setObjectName(name)
		spin.setDecimals(1)
		spin.setSingleStep(0.5)
		spin.setRange(lowest, highest)
		spin.setSuffix(suffix)
		return spin

	def save(self) -> bool:
		found = read_settings({"target": self.target.value(), "ceiling": self.ceiling.value()})
		if isinstance(found, str):
			self.message.setText(found)
			return False
		try:
			write_section(self.path, as_section(found))
		except (OSError, ValueError) as error:
			self.message.setText(t("The settings cannot be saved: {error}").format(error=error))
			return False
		self.current.settings = found
		self.message.setText(t("Saved. Restart the broadcast and the indexing for them to take these settings."))
		return True
