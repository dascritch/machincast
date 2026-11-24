"""Le niveau d'un sonore, dans sa fiche, dans Machin interface (https://github.com/dascritch/machincast/issues/43), par
le point « interface.sound_card » (https://github.com/dascritch/machincast/issues/591).

L'encart « Niveau », dépliable comme les autres encarts de la fiche, se place sous l'encart « Fichier » ; un stream
n'en a pas, comme il n'a pas d'encart « Fichier ». La section elle-même reste cachée. L'encart montre la mesure de
l'audit complet, sa sonie et sa crête ; l'ajustement manuel, en dB, que la fiche enregistre dans la colonne properties
du sonore, borné pour que la crête ne dépasse jamais le plafond, celui du plugin comme celui de chaque banque qui le
contient ; le gain que Machin player appliquera, et celui des banques qui ont leurs propres cible et plafond. Sans le
plugin, la fiche n'en montre rien, et Machin player joue le sonore tel quel.
"""

from PySide6.QtWidgets import QBoxLayout, QCheckBox, QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from machincast.interface import expandable
from machincast.interface.card import CardSection
from machincast.interface.sound_card import EXPANDED_PANELS, SoundCard
from machincast_loudness_normalization import queries
from machincast_loudness_normalization.gain import signed
from machincast_loudness_normalization.rule import (
	MANUAL,
	Current,
	Measure,
	Settings,
	applied,
	automatic,
	bank_values,
	half_below,
	manual,
	measure,
	overridden,
	strictest,
)
from machincast_loudness_normalization.slider import LevelSlider
from machincast_loudness_normalization.texts import t

GROUP = "loudness_normalization_group"
"""Le nom de l'encart « Niveau » : la fiche retient s'il est déplié, comme ses autres encarts."""


class LevelSection(CardSection):
	def __init__(
		self,
		connection: queries.Connection,
		current: Current,
		parent: QWidget | None = None,
		card: SoundCard | None = None,
	) -> None:
		super().__init__(parent)
		self.setObjectName("loudness_normalization")
		self.connection = connection
		self.current = current
		self.measured = Measure()
		self.banks: list[tuple[str, Settings]] = []
		"""Les banques du sonore qui ont leurs propres cible ou plafond, avec leurs réglages."""
		self._loading = False
		self.group = QGroupBox(t("Level"), self)
		self.group.setObjectName(GROUP)
		self.measure = QLabel(self.group)
		self.measure.setObjectName("measure")
		self.measure.setWordWrap(True)
		self.has_adjustment = QCheckBox(t("Manual adjustment"), self.group)
		self.has_adjustment.setObjectName("has_manual_adjustment")
		self.adjustment = LevelSlider(-MANUAL, MANUAL, t(" dB"), self.group, sign=True)
		self.adjustment.setObjectName("manual_adjustment")
		for widget in (self.has_adjustment, self.adjustment):
			widget.setToolTip(
				t(
					"Added to the automatic gain, which brings the loudness to the target; bounded so that the peak"
					" never exceeds the ceiling."
				)
			)
		self.applied = QLabel(self.group)
		self.applied.setObjectName("applied_gain")
		self.applied.setWordWrap(True)
		form = QFormLayout(self.group)
		form.addRow(self.measure)
		form.addRow(self.has_adjustment, self.adjustment)
		form.addRow(self.applied)
		self.in_card = card is not None
		if card is None:
			layout = QVBoxLayout(self)
			layout.setContentsMargins(0, 0, 0, 0)
			layout.addWidget(self.group)
		else:
			self.hide()
			_below_file(card, self.group)
			expandable.make_expandable(
				self.group,
				expanded=GROUP in expandable.retained(EXPANDED_PANELS),
				retain=expandable.retain_in(EXPANDED_PANELS),
			)
		self.adjustment.valueChanged.connect(self._changed)
		self.has_adjustment.toggled.connect(self.adjustment.setEnabled)
		self.has_adjustment.toggled.connect(self._changed)

	def _changed(self) -> None:
		self._show_applied()
		if not self._loading:
			self.changed.emit()

	def read(self, identifier: int | None) -> None:
		self._loading = True
		found = {}
		self.banks = []
		settings = self.current.settings
		stream = False
		if identifier is not None:
			found = queries.properties(self.connection, identifier)
			stream = queries.is_stream(self.connection, identifier)
			for name, properties in queries.banks_of_sound(self.connection, identifier):
				if (settings is not None) and (bank_values(properties) != (None, None)):
					self.banks.append((name, overridden(settings, properties)))
		self.group.setVisible(not stream)
		self.measured = measure(found)
		self._show_measure()
		self._bound()
		adjustment = manual(found)
		self.has_adjustment.setChecked(adjustment != 0)
		self.adjustment.setEnabled(adjustment != 0)
		self.adjustment.setValue(adjustment)
		self._show_applied()
		self._loading = False

	def _show_measure(self) -> None:
		if (self.measured.integrated is None) and (self.measured.peak is None):
			self.measure.setText(t("Not measured yet: the full audit of Machin indexer measures it."))
			return
		self.measure.setText(
			t("Loudness {integrated} LUFS, peak {peak} dBFS").format(
				integrated=_shown(self.measured.integrated), peak=_shown(self.measured.peak)
			)
		)

	def _bound(self) -> None:
		"""L'ajustement le plus fort garde la crête sous le plafond du plugin, et sous celui de chaque banque."""
		settings = self.current.settings
		highest = MANUAL
		if settings is not None:
			variants = [settings]
			for _name, own in self.banks:
				variants.append(own)
			bound = strictest(variants, self.measured)
			if bound is not None:
				highest = max(-MANUAL, min(MANUAL, half_below(bound[1])))
		self.adjustment.setMaximum(highest)

	def chosen(self) -> float:
		"""L'ajustement manuel, en dB ; 0 décoché."""
		if not self.has_adjustment.isChecked():
			return 0.0
		return self.adjustment.value()

	def _show_applied(self) -> None:
		settings = self.current.settings
		if settings is None:
			self.applied.setText(t("The loudness normalisation is not set: its settings are refused."))
			return
		lines = [_gain_line(settings, self.measured, self.chosen())]
		for name, own in self.banks:
			lines.append(
				t("In the bank “{name}”: {gain}").format(name=name, gain=_gain_line(own, self.measured, self.chosen()))
			)
		self.applied.setText("\n".join(lines))

	def write(self, identifier: int) -> None:
		queries.write_manual(self.connection, identifier, round(self.chosen(), 1))


def _below_file(card: SoundCard, group: QGroupBox) -> None:
	"""L'encart, juste sous l'encart « Fichier » de la fiche."""
	file_group = card.ui.file_group
	holder = file_group.parentWidget()
	arrangement = None
	if holder is not None:
		arrangement = holder.layout()
	if not isinstance(arrangement, QBoxLayout):
		raise LookupError(file_group.objectName())
	arrangement.insertWidget(arrangement.indexOf(file_group) + 1, group)


def _gain_line(settings: Settings, measured: Measure, adjustment: float) -> str:
	return t("Gain applied: {gain} dB (automatic {automatic} dB, target {target} LUFS, ceiling {ceiling} dBFS)").format(
		gain=signed(applied(settings, measured, adjustment)),
		automatic=signed(automatic(settings, measured)),
		target=signed(settings.target),
		ceiling=signed(settings.ceiling),
	)


def _shown(value: float | None) -> str:
	if value is None:
		return t("unknown")
	return signed(value)
