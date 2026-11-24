"""La cible et le plafond propres à une banque, dans sa fiche, dans Machin interface
(https://github.com/dascritch/machincast/issues/43), par le point « interface.bank_card »
(https://github.com/dascritch/machincast/issues/591).

L'encart « Niveau » : « Sonie visée propre à la banque » et « Plafond de crête propre à la banque », chacun avec sa
case et son curseur ; décochée, la banque suit le réglage du plugin, que son curseur montre, grisé. Cochés, ils
remplacent ceux du plugin pour les sonores que la banque fournit, et s'enregistrent avec elle, dans sa colonne
properties, sous la clé du plugin ; sans l'un ni l'autre, la clé en part.
"""

from PySide6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QVBoxLayout, QWidget

from machincast.interface.card import CardSection
from machincast_loudness_normalization import queries
from machincast_loudness_normalization.rule import (
	HIGHEST_CEILING,
	HIGHEST_TARGET,
	LOWEST_CEILING,
	LOWEST_TARGET,
	Current,
	Settings,
	bank_values,
)
from machincast_loudness_normalization.slider import LevelSlider
from machincast_loudness_normalization.texts import t


class BankLevelSection(CardSection):
	def __init__(self, connection: queries.Connection, current: Current, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("loudness_normalization")
		self.connection = connection
		self.current = current
		self._loading = False
		group = QGroupBox(t("Level"), self)
		group.setObjectName("loudness_normalization_group")
		self.has_target = QCheckBox(t("Target loudness of its own"), group)
		self.has_target.setObjectName("has_target")
		self.target = LevelSlider(LOWEST_TARGET, HIGHEST_TARGET, t(" LUFS"), group)
		self.target.setObjectName("target")
		self.has_ceiling = QCheckBox(t("Peak ceiling of its own"), group)
		self.has_ceiling.setObjectName("has_ceiling")
		self.ceiling = LevelSlider(LOWEST_CEILING, HIGHEST_CEILING, t(" dBFS"), group)
		self.ceiling.setObjectName("ceiling")
		for box in (self.has_target, self.has_ceiling):
			box.setToolTip(t("Ticked, it replaces the setting of the plugin for the sounds that this bank provides"))
		form = QFormLayout(group)
		form.addRow(self.has_target, self.target)
		form.addRow(self.has_ceiling, self.ceiling)
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(group)
		for box, slider in ((self.has_target, self.target), (self.has_ceiling, self.ceiling)):
			box.toggled.connect(slider.setEnabled)
			box.toggled.connect(self._changed)
			slider.valueChanged.connect(self._changed)

	def _changed(self) -> None:
		if not self._loading:
			self.changed.emit()

	def read(self, identifier: int | None) -> None:
		self._loading = True
		general = (self.current.settings) or (Settings())
		target, ceiling = None, None
		if identifier is not None:
			target, ceiling = bank_values(queries.bank_properties(self.connection, identifier))
		self.has_target.setChecked(target is not None)
		self.target.setEnabled(target is not None)
		if target is None:
			target_shown = general.target
		else:
			target_shown = target
		self.target.setValue(target_shown)
		self.has_ceiling.setChecked(ceiling is not None)
		self.ceiling.setEnabled(ceiling is not None)
		if ceiling is None:
			ceiling_shown = general.ceiling
		else:
			ceiling_shown = ceiling
		self.ceiling.setValue(ceiling_shown)
		self._loading = False

	def write(self, identifier: int) -> None:
		target = None
		if self.has_target.isChecked():
			target = self.target.value()
		ceiling = None
		if self.has_ceiling.isChecked():
			ceiling = self.ceiling.value()
		queries.write_bank_values(self.connection, identifier, target, ceiling)
