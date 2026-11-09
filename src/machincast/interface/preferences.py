"""Préférences de l'interface (https://github.com/dascritch/machincast/issues/145, spec § 8.11).

« Préférences… », dans le menu « Fichier », ouvre PreferencesWindow. Sa page « Crossfades », la première
(https://github.com/dascritch/machincast/issues/234), règle les crossfades : leur granularité (à la seconde ou au
dixième de seconde), leur durée maximale, leurs durées par défaut, celles d'un sonore sans crossfade paramétré que sa
banque ne règle pas (machincast.player.broadcast.crossfade), et la position des fondus par rapport aux silences
détectés d'un sonore joué sans eux (crossfades.fade_in_position et fade_out_position, machincast.player.fades). Une
frise de démonstration (machincast.interface.timeline) montre où tombent les fondus, sur un sonore inventé, et suit les
réglages. Elle règle aussi le seuil de silence (silences.threshold, https://github.com/dascritch/machincast/issues/146),
que l'audit complet prend à son prochain passage, à côté des fondus qu'il place
(https://github.com/dascritch/machincast/issues/324). Sa page « Audio » règle, par le bloc des cartes son
(machincast.interface.sound_cards, https://github.com/dascritch/machincast/issues/339), le type de sortie (audio.output)
et les cartes son de l'antenne (audio.device), que Machin player prend à son prochain démarrage, et de la pré-écoute
(audio.preview, https://github.com/dascritch/machincast/issues/116) : chacune est grisée dans l'autre choix, et se teste
; service de diffusion en marche, celle de l'antenne ne se choisit pas ; elle règle aussi le blanc dans un sonore
(section [dead_air], https://github.com/dascritch/machincast/issues/122) : sa durée, son niveau, et le passage au
secours, que Machin player prend à son prochain démarrage. La page « Base » règle la durée de péremption
(database.retention, https://github.com/dascritch/machincast/issues/268), que Machin purge prend à son prochain passage,
et que suit la fiche d'un élément supprimé. La page « Interface » règle l'onglet Antenne, et choisit l'icône de
l'application (interface.icon, https://github.com/dascritch/machincast/issues/111) : une image lisible, ou celle de
MachinCast ; la fenêtre principale la donne aussitôt à ses fenêtres et aux raccourcis déjà installés
(machincast.shortcut.rewrite).

- Les préférences s'enregistrent dans la section [crossfades] du fichier de configuration (ecrire), qui garde ses
  commentaires et ses autres sections : tomlkit le réécrit tel qu'il l'a lu, sauf les clés réglées. Une durée par
  défaut retirée en disparaît.
- Les préférences de la session (crossfades, definir) valent pour les fiches ouvertes ensuite ; Machin player prend
  les durées par défaut à son prochain démarrage.
- Les champs de crossfade des fiches les suivent (regler) : un pas d'une seconde ou d'un dixième, et la durée
  maximale, sauf pour une valeur déjà plus longue, qui reste telle quelle.
"""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import tomlkit
from PySide6.QtCore import QLocale
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QVBoxLayout, QWidget

from machincast.configuration import (
	MINIMUM_TABLE_ROWS,
	RETENTION,
	SILENCE_THRESHOLD,
	TABLE_ROWS,
	AudioOutput,
	Crossfades,
	DeadAirSettings,
	Granularity,
)
from machincast.i18n import _
from machincast.interface.application import ICON, readable
from machincast.interface.sound_cards import SoundCards
from machincast.interface.timeline import Plan, Timeline, demonstration_shape
from machincast.interface.ui.preferences import Ui_PreferencesWindow
from machincast.player.fades import LABELS, POSITIONS, Position
from machincast.service import ABSENT, ServiceState

FRENCH = QLocale(QLocale.Language.French, QLocale.Country.France)
"""Les durées s'écrivent avec une virgule."""
GRANULARITIES: tuple[tuple[Granularity, str], ...] = (
	("tenth", _("To the tenth of a second")),
	("second", _("To the second")),
)
STEPS: dict[Granularity, tuple[int, float]] = {"tenth": (1, 0.1), "second": (0, 1.0)}
"""Pour chaque granularité : les décimales et le pas d'un champ de crossfade."""

DEFAULT_ICON = _("MachinCast icon")
"""Ce que montre la page « Interface » quand aucune image n'est choisie."""
PREVIEW_SIZE = 48


@dataclass(frozen=True)
class Settings:
	"""Ce que règle la fenêtre des préférences."""

	crossfades: Crossfades
	on_air: str | None
	"""audio.device ; None tant qu'il n'est pas renseigné."""
	preview: str
	"""audio.preview."""
	silence_threshold: float = SILENCE_THRESHOLD
	"""silences.threshold, en dB crête (https://github.com/dascritch/machincast/issues/146)."""
	clipping: bool = True
	"""interface.clipping : le voyant « Saturation » de l'onglet Antenne est affiché
	(https://github.com/dascritch/machincast/issues/191)."""
	suggestions: bool = True
	"""interface.suggestions : au lancement, l'interface propose ce qui manque pour démarrer
	(https://github.com/dascritch/machincast/issues/119)."""
	icon: Path | None = None
	"""interface.icon : l'image choisie pour icône de l'application ; None : celle de MachinCast
	(https://github.com/dascritch/machincast/issues/111)."""
	retention: int = RETENTION
	"""database.retention, en jours : au-delà, Machin purge efface de la base
	(https://github.com/dascritch/machincast/issues/268)."""
	dead_air: DeadAirSettings = DeadAirSettings()
	"""La section [dead_air] : blanc dans un sonore, à l'antenne
	(https://github.com/dascritch/machincast/issues/122)."""
	output: AudioOutput | None = None
	"""audio.output, le type de sortie choisi (https://github.com/dascritch/machincast/issues/339) ; None : inchangé."""
	table_rows: int = TABLE_ROWS
	"""interface.table_rows : les lignes qu'un tableau de fiche charge d'un coup (https://github.com/dascritch/machincast/issues/383)."""


_current_list = Crossfades()
_retention = RETENTION
_table_rows = TABLE_ROWS


DEMONSTRATION = (30.0, 3.0, 4.0)
"""Le sonore de la frise de démonstration (https://github.com/dascritch/machincast/issues/234) : sa durée, et ses
silences détectés au début et à la fin, en secondes ; il est joué sans eux."""


def crossfades() -> Crossfades:
	"""Les préférences de la session, que suivent les fiches qui s'ouvrent."""
	return _current_list


def define(settings: Crossfades) -> None:
	global _current_list  # noqa: PLW0603 : les préférences de la session, une seule par interface
	_current_list = settings


def retention() -> int:
	"""La durée de péremption de la session, en jours : la fiche d'un élément supprimé dit quand il sera effacé."""
	return _retention


def define_retention(days: int) -> None:
	global _retention  # noqa: PLW0603 : les préférences de la session, une seule par interface
	_retention = days


def table_rows() -> int:
	"""Les lignes qu'un tableau de fiche charge d'un coup, dans la session (https://github.com/dascritch/machincast/issues/383)."""
	return _table_rows


def define_table_rows(rows: int) -> None:
	global _table_rows  # noqa: PLW0603 : les préférences de la session, une seule par interface
	_table_rows = rows


def set_(field: QDoubleSpinBox, granularity: Granularity, maximum: timedelta) -> None:
	"""Le pas, les décimales et la durée maximale d'un champ de crossfade."""
	decimals, step = STEPS[granularity]
	field.setLocale(FRENCH)
	field.setDecimals(decimals)
	field.setSingleStep(step)
	field.setMaximum(maximum.total_seconds())


def set_according_to_preferences(field: QDoubleSpinBox) -> None:
	settings = crossfades()
	set_(field, settings.granularity, settings.maximum)


def display(field: QDoubleSpinBox, seconds: float) -> None:
	"""Une valeur plus longue que la durée maximale reste telle quelle : le champ s'allonge pour elle."""
	field.setMaximum(max(field.maximum(), seconds))
	field.setValue(seconds)


def _seconds(duration: timedelta) -> int | float:
	"""Un nombre entier de secondes s'écrit sans décimale dans le fichier."""
	return _count(duration.total_seconds())


def _count(value: float) -> int | float:
	"""Un nombre entier s'écrit sans décimale dans le fichier."""
	if value == int(value):
		return int(value)
	return value


def write(path: Path, settings: Settings) -> None:
	"""Écrit les réglages dans les sections [crossfades], [audio], [silences], [dead_air], [interface] et [database] du
	fichier de configuration, sous leurs noms anglais (https://github.com/dascritch/machincast/issues/357) ; le reste du
	fichier reste tel quel, commentaires compris."""
	document = tomlkit.parse(path.read_text(encoding="utf-8"))
	database = document["database"]
	assert isinstance(database, tomlkit.items.Table)
	# La durée par défaut ne s'écrit pas dans une section qui ne la donne pas : [database] reste telle quelle.
	if ("retention" in database) or (settings.retention != RETENTION):
		database["retention"] = settings.retention
	if "crossfades" not in document:
		document.add("crossfades", tomlkit.table())
	section = document["crossfades"]
	assert isinstance(section, tomlkit.items.Table)
	crossfades = settings.crossfades
	section["granularity"] = crossfades.granularity
	section["maximum"] = _seconds(crossfades.maximum)
	section["fade_in_position"] = crossfades.entry
	section["fade_out_position"] = crossfades.output
	write_audio(document, settings.output, settings.on_air, settings.preview)
	for key, duration in (("start", crossfades.start), ("end", crossfades.end)):
		if duration is None:
			if key in section:
				del section[key]
			continue
		section[key] = _seconds(duration)
	if "silences" not in document:
		document.add("silences", tomlkit.table())
	silences = document["silences"]
	assert isinstance(silences, tomlkit.items.Table)
	silences["threshold"] = _count(settings.silence_threshold)
	if "dead_air" not in document:
		document.add("dead_air", tomlkit.table())
	dead_air = document["dead_air"]
	assert isinstance(dead_air, tomlkit.items.Table)
	dead_air["duration"] = _seconds(settings.dead_air.duration)
	dead_air["threshold"] = _count(settings.dead_air.threshold)
	dead_air["fallback"] = settings.dead_air.fallback
	if "interface" not in document:
		document.add("interface", tomlkit.table())
	section_interface = document["interface"]
	assert isinstance(section_interface, tomlkit.items.Table)
	section_interface["clipping"] = settings.clipping
	section_interface["suggestions"] = settings.suggestions
	# Le nombre par défaut ne s'écrit pas dans une section qui ne le donne pas.
	if ("table_rows" in section_interface) or (settings.table_rows != TABLE_ROWS):
		section_interface["table_rows"] = settings.table_rows
	if settings.icon is not None:
		section_interface["icon"] = str(settings.icon)
	elif "icon" in section_interface:
		del section_interface["icon"]
	path.write_text(tomlkit.dumps(document), encoding="utf-8")


def write_audio(
	document: tomlkit.TOMLDocument, output: AudioOutput | None, on_air: str | None, preview: str | None
) -> None:
	"""La section [audio] : audio.output, audio.device et audio.preview, chacun s'il est donné, en valeurs du fichier
	(« dummy » pour la sortie factice) ; partagée par les préférences, les suggestions et la pré-écoute."""
	audio = document["audio"]
	assert isinstance(audio, tomlkit.items.Table)
	if output is not None:
		audio["output"] = output
	if on_air is not None:
		audio["device"] = on_air
	if preview is not None:
		audio["preview"] = preview


class PreferencesWindow(QDialog):
	"""La fenêtre des préférences : une page « Interface », avec les crossfades, et une page « Audio », avec les
	périphériques."""

	def __init__(
		self, all_: Settings, output: AudioOutput, parent: QWidget | None = None, service: ServiceState = ABSENT
	) -> None:
		super().__init__(parent)
		self.ui = Ui_PreferencesWindow()
		self.ui.setupUi(self)
		ui = self.ui
		settings = all_.crossfades
		self.cards = SoundCards(output, all_.on_air, all_.preview, service, ui.device_group)
		ui.device_layout.addWidget(self.cards)
		self.cards.changed.connect(self._exclude)
		self._exclude()
		for value, text in GRANULARITIES:
			ui.granularity.addItem(text, value)
		ui.granularity.setCurrentIndex(ui.granularity.findData(settings.granularity))
		self._granularity()
		ui.maximum.setValue(settings.maximum.total_seconds())
		self._maximum()
		for box, field, duration in ((ui.has_start, ui.start, settings.start), (ui.has_end, ui.end, settings.end)):
			box.toggled.connect(field.setEnabled)
			box.setChecked(duration is not None)
			if duration is not None:
				field.setValue(duration.total_seconds())
		ui.silence_threshold.setLocale(FRENCH)
		ui.silence_threshold.setValue(all_.silence_threshold)
		ui.dead_air_fallback.setChecked(all_.dead_air.fallback)
		ui.dead_air_duration.setLocale(FRENCH)
		ui.dead_air_duration.setValue(all_.dead_air.duration.total_seconds())
		ui.dead_air_threshold.setLocale(FRENCH)
		ui.dead_air_threshold.setValue(all_.dead_air.threshold)
		ui.retention.setValue(all_.retention)
		ui.clipping.setChecked(all_.clipping)
		ui.suggestions.setChecked(all_.suggestions)
		ui.table_rows.setMinimum(MINIMUM_TABLE_ROWS)
		ui.table_rows.setValue(all_.table_rows)
		self.icon = all_.icon
		self._show_icon()
		self._flag("")
		ui.choose_icon.clicked.connect(self._choose_icon)
		ui.default_icon.clicked.connect(self._come_back_to_default_icon)
		ui.granularity.currentIndexChanged.connect(self._granularity)
		ui.maximum.valueChanged.connect(self._maximum)
		# Les positions des fondus, et leur frise de démonstration (https://github.com/dascritch/machincast/issues/234).
		for choice, current in ((ui.entry_position, settings.entry), (ui.output_position, settings.output)):
			for position in POSITIONS:
				choice.addItem(LABELS[position], position)
			choice.setCurrentIndex(choice.findData(current))
			choice.currentIndexChanged.connect(self._demonstrate)
		self.demonstration = Timeline(ui.place_demonstration, interactive=False)
		arrangement = QVBoxLayout(ui.place_demonstration)
		arrangement.setContentsMargins(0, 0, 0, 0)
		arrangement.addWidget(self.demonstration)
		length, start_silence, end_silence = DEMONSTRATION
		self.demonstration.show_shape(demonstration_shape(length, start_silence, end_silence))
		for field in (ui.start, ui.end):
			field.valueChanged.connect(self._demonstrate)
		self._demonstrate()
		ui.buttons.accepted.connect(self.accept)
		ui.buttons.rejected.connect(self.reject)

	def _show_icon(self) -> None:
		"""L'aperçu et le chemin de l'icône ; « Icône de MachinCast » ne sert que pour une autre icône."""
		ui = self.ui
		image = ICON
		text = DEFAULT_ICON
		if self.icon is not None:
			image = self.icon
			text = str(self.icon)
		ui.preview_icon.setPixmap(QIcon(str(image)).pixmap(PREVIEW_SIZE))
		ui.path_icon.setText(text)
		ui.default_icon.setEnabled(self.icon is not None)

	def _choose_icon(self) -> None:
		"""Une image que Qt ne sait pas lire n'est pas prise : la page le dit."""
		# Importé ici : dialogues ouvre cette fenêtre, et importe donc ce module.
		from machincast.interface import dialogs

		chosen = dialogs.choose_icon(self)
		if chosen is None:
			return
		if not readable(chosen):
			self._flag(_("Unreadable image: {chosen}").format(chosen=chosen))
			return
		self._flag("")
		self.icon = chosen
		self._show_icon()

	def _come_back_to_default_icon(self) -> None:
		self._flag("")
		self.icon = None
		self._show_icon()

	def _flag(self, text: str) -> None:
		"""Ce qui ne va pas avec l'image choisie ; rien, sans place prise sur la page."""
		self.ui.error_icon.setText(text)
		self.ui.error_icon.setVisible(text != "")

	def _chosen(self) -> Granularity:
		granularity: Granularity = self.ui.granularity.currentData()
		return granularity

	def _granularity(self) -> None:
		"""Les champs suivent la granularité choisie ; la durée maximale fait au moins un pas."""
		ui = self.ui
		decimals, step = STEPS[self._chosen()]
		ui.maximum.setLocale(FRENCH)
		ui.maximum.setDecimals(decimals)
		ui.maximum.setSingleStep(step)
		ui.maximum.setMinimum(step)
		for field in (ui.start, ui.end):
			set_(field, self._chosen(), timedelta(seconds=ui.maximum.value()))

	def _maximum(self) -> None:
		"""Une durée par défaut ne dépasse pas la durée maximale."""
		for field in (self.ui.start, self.ui.end):
			set_(field, self._chosen(), timedelta(seconds=self.ui.maximum.value()))

	def _positions(self) -> tuple[Position, Position]:
		entry: Position = self.ui.entry_position.currentData()
		output: Position = self.ui.output_position.currentData()
		return entry, output

	def _demonstrate(self) -> None:
		"""La frise de démonstration : le sonore inventé, avec les durées par défaut saisies, même décochées, et les
		positions choisies."""
		duration, start_silence, end_silence = DEMONSTRATION
		entry, output = self._positions()
		plan = Plan(
			duration,
			start_silence,
			end_silence,
			removed_silences=True,
			start_crossfade=self.ui.start.value(),
			end_crossfade=self.ui.end.value(),
			entry_position=entry,
			output_position=output,
		)
		self.demonstration.display(plan, duration)
		self.ui.demonstration_legend.setText(
			_("Demonstration: a sound of 30 s, with silences of 3 s and 4 s. {summary}").format(summary=plan.summary())
		)

	def _exclude(self) -> None:
		"""« OK » ne donne jamais la même carte à l'antenne et à la pré-écoute (SoundCards grise chacune dans l'autre
		choix)."""
		self.ui.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self.cards.valid())

	def settings(self) -> Settings:
		ui = self.ui
		durations: list[timedelta | None] = []
		for box, field in ((ui.has_start, ui.start), (ui.has_end, ui.end)):
			duration = None
			if box.isChecked():
				duration = timedelta(seconds=field.value())
			durations.append(duration)
		entry, output = self._positions()
		crossfades = Crossfades(
			durations[0], durations[1], timedelta(seconds=ui.maximum.value()), self._chosen(), entry, output
		)
		return Settings(
			crossfades,
			self.cards.chosen_on_air(),
			str(self.cards.chosen_preview()),
			round(ui.silence_threshold.value(), 1),
			ui.clipping.isChecked(),
			ui.suggestions.isChecked(),
			self.icon,
			ui.retention.value(),
			DeadAirSettings(
				timedelta(seconds=round(ui.dead_air_duration.value(), 1)),
				round(ui.dead_air_threshold.value(), 1),
				ui.dead_air_fallback.isChecked(),
			),
			self.cards.chosen_output(),
			ui.table_rows.value(),
		)
