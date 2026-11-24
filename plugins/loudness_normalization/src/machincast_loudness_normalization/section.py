"""Le niveau d'un sonore, dans sa fiche, dans Machin interface (https://github.com/dascritch/machincast/issues/43), par
le point « interface.sound_card » (https://github.com/dascritch/machincast/issues/591).

La mesure de l'audit complet, sa sonie et sa crête ; l'ajustement manuel, en dB, que la fiche enregistre dans la
colonne properties du sonore, borné pour que la crête ne dépasse jamais le plafond ; le gain que Machin player
appliquera. Sans le plugin, la fiche n'en montre rien, et Machin player joue le sonore tel quel.
"""

from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from machincast.interface.card import CardSection
from machincast_loudness_normalization import queries
from machincast_loudness_normalization.gain import signed
from machincast_loudness_normalization.rule import (
	MANUAL,
	Current,
	Measure,
	applied,
	automatic,
	headroom,
	manual,
	measure,
	tenth_below,
)
from machincast_loudness_normalization.texts import t

STEP = 0.5


class LevelSection(CardSection):
	def __init__(self, connection: queries.Connection, current: Current, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.setObjectName("loudness_normalization")
		self.connection = connection
		self.current = current
		self.measured = Measure()
		self._loading = False
		box = QGroupBox(t("Level"), self)
		self.measure = QLabel(box)
		self.measure.setObjectName("measure")
		self.measure.setWordWrap(True)
		self.adjustment = QDoubleSpinBox(box)
		self.adjustment.setObjectName("manual_adjustment")
		self.adjustment.setDecimals(1)
		self.adjustment.setSingleStep(STEP)
		self.adjustment.setRange(-MANUAL, MANUAL)
		self.adjustment.setSuffix(t(" dB"))
		self.adjustment.setToolTip(
			t(
				"Added to the automatic gain, which brings the loudness to the target; bounded so that the peak never"
				" exceeds the ceiling."
			)
		)
		self.applied = QLabel(box)
		self.applied.setObjectName("applied_gain")
		form = QFormLayout(box)
		form.addRow(self.measure)
		form.addRow(t("Manual adjustment"), self.adjustment)
		form.addRow(self.applied)
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(box)
		self.adjustment.valueChanged.connect(self._changed)

	def _changed(self) -> None:
		self._show_applied()
		if not self._loading:
			self.changed.emit()

	def read(self, identifier: int | None) -> None:
		self._loading = True
		found = {}
		if identifier is not None:
			found = queries.properties(self.connection, identifier)
		self.measured = measure(found)
		self._show_measure()
		self._bound()
		self.adjustment.setValue(manual(found))
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
		"""L'ajustement le plus fort garde la crête sous le plafond."""
		settings = self.current.settings
		highest = MANUAL
		if settings is not None:
			limit = headroom(settings, self.measured)
			if limit is not None:
				highest = max(-MANUAL, min(MANUAL, tenth_below(limit)))
		self.adjustment.setMaximum(highest)

	def _show_applied(self) -> None:
		settings = self.current.settings
		if settings is None:
			self.applied.setText(t("The loudness normalisation is not set: its settings are refused."))
			return
		gain = applied(settings, self.measured, self.adjustment.value())
		self.applied.setText(
			t(
				"Gain applied: {gain} dB (automatic {automatic} dB, target {target} LUFS, ceiling {ceiling} dBFS)"
			).format(
				gain=signed(gain),
				automatic=signed(automatic(settings, self.measured)),
				target=signed(settings.target),
				ceiling=signed(settings.ceiling),
			)
		)

	def write(self, identifier: int) -> None:
		queries.write_manual(self.connection, identifier, round(self.adjustment.value(), 1))


def _shown(value: float | None) -> str:
	if value is None:
		return t("unknown")
	return signed(value)
