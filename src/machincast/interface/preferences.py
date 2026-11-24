"""Préférences de l'interface (https://github.com/dascritch/machincast/issues/145, spec § 8.11).

« Préférences… », dans le menu « Fichier », ouvre PreferencesWindow. Sa page « Crossfades », la première
(https://github.com/dascritch/machincast/issues/234), règle les crossfades : leur granularité (à la seconde ou au
dixième de seconde), leur durée maximale, leurs durées par défaut, celles d'un sonore sans crossfade paramétré que sa
banque ne règle pas (machincast.shared.fades.crossfade), et la position des fondus par rapport aux silences
détectés d'un sonore joué sans eux (crossfades.fade_in_position et fade_out_position, machincast.shared.fades). Une
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

import dataclasses
import html
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import time, timedelta
from pathlib import Path
from typing import Literal

import tomlkit
from PySide6.QtCore import QLocale, QTime
from PySide6.QtGui import QIcon, QStandardItemModel
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QLabel, QVBoxLayout, QWidget

from machincast import notes as notes_module
from machincast import service as service_module
from machincast.clock import Clock, SystemClock
from machincast.configuration import (
	DAILY,
	MINIMUM_TABLE_ROWS,
	RETENTION,
	SILENCE_THRESHOLD,
	TABLE_ROWS,
	AudioInput,
	AudioOutput,
	Crossfades,
	DeadAirSettings,
	FirstLogin,
	Granularity,
	Intranet,
	InvalidConfiguration,
	SecondFactor,
	load,
)
from machincast.i18n import _, pgettext
from machincast.interface import intranet_switch
from machincast.interface.application import ICON, readable
from machincast.interface.audio_inputs import AudioInputs
from machincast.interface.plugins_page import Offered, PluginsPage
from machincast.interface.power_save_switch import PowerSaveSwitch
from machincast.interface.sound_cards import SoundCards
from machincast.interface.timeline import Plan, Timeline, demonstration_shape
from machincast.interface.ui.preferences import Ui_PreferencesWindow
from machincast.intranet import network
from machincast.protection import check_writing
from machincast.service import ABSENT, ServiceState
from machincast.shared.fades import LABELS, POSITIONS, Position

FRENCH = QLocale(QLocale.Language.French, QLocale.Country.France)
"""Les durées s'écrivent avec une virgule."""
GRANULARITIES: tuple[tuple[Granularity, str], ...] = (
	("tenth", _("To the tenth of a second")),
	("second", _("To the second")),
)
STEPS: dict[Granularity, tuple[int, float]] = {"tenth": (1, 0.1), "second": (0, 1.0)}
"""Pour chaque granularité : les décimales et le pas d'un champ de crossfade."""

Kind = Literal["interface", "service"]
"""Les deux fenêtres (https://github.com/dascritch/machincast/issues/389) : les préférences de l'interface, qui valent
aussitôt et ne touchent pas la diffusion, et les paramètres du service, que Machin player ne prend qu'à son
redémarrage."""
INTERFACE: Kind = "interface"
SERVICE: Kind = "service"
TITLES: dict[Kind, str] = {
	INTERFACE: _("Interface preferences"),
	SERVICE: _("Broadcast service settings"),
}
ENTRIES: dict[Kind, str] = {
	INTERFACE: _("Interface preferences…"),
	SERVICE: _("Broadcast service settings…"),
}
"""Les entrées du menu « Fichier »."""
SERVICE_EXPLANATION = _(
	"Machin player takes these settings when it restarts: OK saves them, then restarts the broadcast, with the "
	"password of an administrator if the broadcast service runs; refused, the former settings come back."
)
INTERFACE_AUDIO_EXPLANATION = _(
	"The pre-listen applies at once, on a card of the output type of the broadcast service settings; it can never use "
	"the on-air card. “Test” plays 2 seconds of test sound on it."
)

DEFAULT_ICON = _("MachinCast icon")
"""Ce que montre la page « Interface » quand aucune image n'est choisie."""
PREVIEW_SIZE = 48


TIMERS_MISSING = _(
	"The timers of the tasks are not installed: ./install.sh --service installs them, except with --no-timers. "
	"Without them, this hour is not used."
)
"""Ce que dit la page « Tâches » sans les minuteurs d'install.sh --service (https://github.com/dascritch/machincast/issues/455)."""


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
	daily: time = DAILY
	"""schedule.daily : l'heure de la tâche quotidienne, purge puis audit complet
	(https://github.com/dascritch/machincast/issues/455)."""
	backup_directory: Path = dataclasses.field(default_factory=Path.home)
	notes: Path | None = None
	"""interface.notes : le document « Votre installation » ; None : celui du Bureau
	(https://github.com/dascritch/machincast/issues/451)."""
	team_link: str | None = None
	"""interface.team_link : l'adresse web de l'équipe ; None : aucune."""
	intranet: Intranet = Intranet()
	"""La section [intranet] : le serveur intranet, éteint par défaut
	(https://github.com/dascritch/machincast/issues/538)."""
	plugins: tuple[str, ...] = ()
	"""plugins.enabled : les plugins activés, dans l'ordre (https://github.com/dascritch/machincast/issues/587)."""
	inputs: tuple[AudioInput, ...] = ()
	"""audio.inputs : les entrées audio, dans l'ordre (https://github.com/dascritch/machincast/issues/622)."""
	"""backup.directory : où l'export et la maintenance écrivent leur sauvegarde
	(https://github.com/dascritch/machincast/issues/347)."""


def service_changed(before: Settings, after: Settings) -> bool:
	"""Vrai si un réglage que Machin player ne prend qu'à son redémarrage a changé : les durées et les positions des
	crossfades, le type de sortie, la carte de l'antenne, le blanc dans un sonore
	(https://github.com/dascritch/machincast/issues/389), les plugins activés
	(https://github.com/dascritch/machincast/issues/587)."""
	first, second = before.crossfades, after.crossfades
	crossfades = (first.start, first.end, first.maximum, first.entry, first.output) != (
		second.start,
		second.end,
		second.maximum,
		second.entry,
		second.output,
	)
	output = (after.output is not None) and (after.output != before.output)
	return (
		(crossfades)
		or (output)
		or (after.on_air != before.on_air)
		or (after.dead_air != before.dead_air)
		or (after.plugins != before.plugins)
	)


CLOCK: Clock = SystemClock()
"""L'heure qui date la copie de machincast.toml (https://github.com/dascritch/machincast/issues/347)."""

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
	global _current_list
	_current_list = settings


def retention() -> int:
	"""La durée de péremption de la session, en jours : la fiche d'un élément supprimé dit quand il sera effacé."""
	return _retention


def define_retention(days: int) -> None:
	global _retention
	_retention = days


def table_rows() -> int:
	"""Les lignes qu'un tableau de fiche charge d'un coup, dans la session (https://github.com/dascritch/machincast/issues/383)."""
	return _table_rows


def define_table_rows(rows: int) -> None:
	global _table_rows
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


def _write_daily(document: tomlkit.TOMLDocument, daily: time) -> None:
	"""schedule.daily, « HH:MM » : l'heure par défaut ne s'écrit pas dans un fichier qui ne la donne pas
	(https://github.com/dascritch/machincast/issues/455)."""
	section = document.get("schedule")
	if (section is None) and (daily == DAILY):
		return
	if section is None:
		document.add("schedule", tomlkit.table())
		section = document["schedule"]
	assert isinstance(section, tomlkit.items.Table)
	section["daily"] = daily.isoformat(timespec="minutes")


def address_list(addresses: Sequence[str]) -> str:
	"""Les adresses de l'intranet et de son API à donner aux autres postes, en liste à puces, chacune en lien
	(https://github.com/dascritch/machincast/issues/604)."""
	items = []
	for address in addresses:
		written = html.escape(address)
		items.append(f'<li><a href="{written}">{written}</a></li>')
	introduction = html.escape(
		_("Addresses to give to the other computers, for the intranet and its API:"), quote=False
	)
	return f"<p>{introduction}</p><ul>{''.join(items)}</ul>"


FIRST_LOGINS: dict[FirstLogin, str] = {
	"none": _("No validation"),
	"desk": _("Validation at the desk"),
	"desk_code": _("Validation at the desk, with a code"),
}
"""La sécurité de la première connexion à l'intranet, dans l'ordre de la page « Intranet »
(https://github.com/dascritch/machincast/issues/600)."""
SECOND_FACTORS: dict[SecondFactor, str] = {
	"none": pgettext("second factor", "None"),
	"totp": _("Authentication app"),
	"desk": _("Validation at the desk"),
}
"""Le second facteur de chaque connexion à l'intranet, dans l'ordre de la page « Intranet »
(https://github.com/dascritch/machincast/issues/601)."""
READ_ONLY = _("Consultation only: an administrator did not allow to set the service.")
"""Le bandeau de la fenêtre en consultation (https://github.com/dascritch/machincast/issues/603)."""
IN_PRODUCTION = _("Impossible in production: the intranet server is installed as a service.")


def _write_intranet(document: tomlkit.TOMLDocument, intranet: Intranet) -> None:
	"""intranet.enabled, port, validation (https://github.com/dascritch/machincast/issues/538) et first_login
	(https://github.com/dascritch/machincast/issues/600) : les valeurs par
	défaut ne s'écrivent pas dans un fichier qui n'a pas la section ; l'adresse d'écoute et le certificat restent
	ceux du fichier."""
	section = document.get("intranet")
	default = Intranet()
	if (section is None) and (
		(intranet.enabled, intranet.port, intranet.validation, intranet.first_login, intranet.second_factor)
		== (
			default.enabled,
			default.port,
			default.validation,
			default.first_login,
			default.second_factor,
		)
	):
		return
	if section is None:
		document.add("intranet", tomlkit.table())
		section = document["intranet"]
	assert isinstance(section, tomlkit.items.Table)
	section["enabled"] = intranet.enabled
	section["port"] = intranet.port
	section["validation"] = intranet.validation
	if (intranet.first_login != default.first_login) or ("first_login" in section):
		section["first_login"] = intranet.first_login
	if (intranet.second_factor != default.second_factor) or ("second_factor" in section):
		section["second_factor"] = intranet.second_factor


def intranet(path: Path) -> Intranet:
	"""La section [intranet] du fichier ; celle par défaut, s'il ne se lit pas."""
	try:
		return load(path).intranet
	except InvalidConfiguration:
		return Intranet()


def intranet_changed(before: Settings, after: Settings) -> bool:
	"""Le serveur intranet est à rallumer ou à éteindre : allumé, éteint, port, durée de validation, sécurité de la
	première connexion ou second facteur changés."""
	first, second = before.intranet, after.intranet
	return (first.enabled, first.port, first.validation, first.first_login, first.second_factor) != (
		second.enabled,
		second.port,
		second.validation,
		second.first_login,
		second.second_factor,
	)


def _write_backup(document: tomlkit.TOMLDocument, directory: Path) -> None:
	"""backup.directory : le répertoire personnel, par défaut, ne s'écrit pas dans un fichier qui ne donne pas la clé
	(https://github.com/dascritch/machincast/issues/347)."""
	section = document.get("backup")
	if (section is None) and (directory == Path.home()):
		return
	if section is None:
		document.add("backup", tomlkit.table())
		section = document["backup"]
	assert isinstance(section, tomlkit.items.Table)
	section["directory"] = str(directory)


def copy_configuration(configuration: Path, directory: Path) -> Path:
	"""Copie le fichier de configuration dans directory, sous un nom daté comme les sauvegardes de la base,
	machincast-AAAA-MM-JJTHH-MM-SS.toml : jamais par-dessus un autre fichier ; lève OSError
	(https://github.com/dascritch/machincast/issues/347)."""
	timestamp = f"{CLOCK.now().astimezone():%Y-%m-%dT%H-%M-%S}"
	copy = directory / f"{configuration.stem}-{timestamp}{configuration.suffix}"
	check_writing(copy)
	with copy.open("xb") as written:
		written.write(configuration.read_bytes())
	return copy


def _write_interface(document: tomlkit.TOMLDocument, settings: Settings) -> None:
	"""La section [interface] : voyant, suggestions, lignes des tableaux, icône, document et lien de l'équipe."""
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
	else:
		if "icon" in section_interface:
			del section_interface["icon"]
	# Le document et le lien de l'équipe (https://github.com/dascritch/machincast/issues/451) : retirés sans valeur.
	for key, value in (("notes", settings.notes), ("team_link", settings.team_link)):
		if value is not None:
			section_interface[key] = str(value)
		if (value is None) and (key in section_interface):
			del section_interface[key]


def _write_plugins(document: tomlkit.TOMLDocument, enabled: tuple[str, ...]) -> None:
	"""plugins.enabled (https://github.com/dascritch/machincast/issues/587) ; les réglages de chaque plugin,
	[plugins.<nom>], restent tels quels. Sans plugin activé, une section absente ne se crée pas."""
	if ("plugins" not in document) and (enabled == ()):
		return
	if "plugins" not in document:
		document.add("plugins", tomlkit.table())
	section = document["plugins"]
	assert isinstance(section, tomlkit.items.Table)
	names = tomlkit.array()
	names.extend(enabled)
	section["enabled"] = names


def plugins_enabled(path: Path) -> tuple[str, ...]:
	"""[plugins] enabled du fichier ; aucun s'il ne se lit pas."""
	try:
		return load(path).plugins.enabled
	except InvalidConfiguration:
		return ()


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
	_write_daily(document, settings.daily)
	_write_backup(document, settings.backup_directory)
	_write_intranet(document, settings.intranet)
	_write_plugins(document, settings.plugins)
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
	write_inputs(document, settings.inputs)

	def write_duration(duration: timedelta | None, key: str) -> None:
		if duration is None:
			if key in section:
				del section[key]
			return
		section[key] = _seconds(duration)

	for key, duration in (("start", crossfades.start), ("end", crossfades.end)):
		write_duration(duration, key)
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
	_write_interface(document, settings)
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


def write_inputs(document: tomlkit.TOMLDocument, inputs: Sequence[AudioInput]) -> None:
	"""audio.inputs, une table en ligne par entrée ; aucune entrée, la clé disparaît
	(https://github.com/dascritch/machincast/issues/622)."""
	audio = document["audio"]
	assert isinstance(audio, tomlkit.items.Table)
	if not inputs:
		if "inputs" in audio:
			del audio["inputs"]
		return
	entries = tomlkit.array()
	for audio_input in inputs:
		entry = tomlkit.inline_table()
		entry.update({"device": audio_input.device, "name": audio_input.name})
		entries.append(entry)
	audio["inputs"] = entries


def inputs_changed(before: Settings, after: Settings) -> bool:
	"""Les entrées audio ont changé : le service installé, elles se réservent aussitôt
	(https://github.com/dascritch/machincast/issues/622)."""
	return before.inputs != after.inputs


class PreferencesWindow(QDialog):
	"""La fenêtre des préférences de l'interface, ou celle des paramètres du service, selon kind : les mêmes pages,
	chacune réduite à ce que règle sa fenêtre."""

	def __init__(
		self,
		all_: Settings,
		output: AudioOutput,
		parent: QWidget | None = None,
		service: ServiceState = ABSENT,
		kind: Kind = SERVICE,
		*,
		timers: bool | None = None,
		configuration: Path | None = None,
		offered: Sequence[Offered] = (),
		read_only: bool = False,
	) -> None:
		super().__init__(parent)
		self.ui = Ui_PreferencesWindow()
		self.ui.setupUi(self)
		self.kind = kind
		ui = self.ui
		settings = all_.crossfades
		self.inputs: AudioInputs | None = None
		self.given_inputs = all_.inputs
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
		self._show_daily(all_.daily, timers=timers)
		self.configuration = configuration
		ui.backup_directory.setText(str(all_.backup_directory))
		ui.choose_backup_directory.clicked.connect(self._choose_backup_directory)
		ui.copy_configuration.clicked.connect(self._copy_configuration)
		ui.copy_configuration.setEnabled(configuration is not None)
		ui.copy_result.setVisible(False)
		self._show_notes(all_)
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
		self.intranet = all_.intranet
		ui.intranet_enabled.setChecked(all_.intranet.enabled)
		ui.intranet_port.setValue(all_.intranet.port)
		ui.intranet_validation.setValue(all_.intranet.validation)
		self._offer_first_logins(all_.intranet.first_login)
		for factor, text in SECOND_FACTORS.items():
			ui.intranet_second_factor.addItem(text, factor)
		ui.intranet_second_factor.setCurrentIndex(ui.intranet_second_factor.findData(all_.intranet.second_factor))
		ui.intranet_enabled.toggled.connect(self._show_intranet)
		ui.intranet_port.valueChanged.connect(self._show_intranet)
		self._show_intranet()
		# Les plugins, dans les paramètres du service seulement (https://github.com/dascritch/machincast/issues/587).
		self.enabled_plugins = all_.plugins
		self.plugins_page: PluginsPage | None = None
		if kind == SERVICE:
			self.plugins_page = PluginsPage(offered, all_.plugins)
			ui.pages.addTab(self.plugins_page, _("Plugins"))
		self.power_save: PowerSaveSwitch | None = None
		if kind == SERVICE:
			self._offer_power_save()
		# Les entrées audio, dans les paramètres du service seulement (https://github.com/dascritch/machincast/issues/622).
		if kind == SERVICE:
			self.inputs = AudioInputs(
				output, all_.inputs, (all_.on_air, all_.preview), ui.page_audio, preview=all_.preview
			)
			ui.audio_layout.insertWidget(ui.audio_layout.indexOf(ui.device_group) + 1, self.inputs)
			self.inputs.changed.connect(self._exclude)
		self._keep_only(kind)
		self.read_only_banner: QLabel | None = None
		if read_only:
			self._read_only()

	def _read_only(self) -> None:
		"""En consultation, sans administrateur (https://github.com/dascritch/machincast/issues/603) : chaque page se
		lit sans se régler, ses onglets toujours au choix, et seul « Fermer » reste."""
		ui = self.ui
		self.setWindowTitle(_("{title} (consultation)").format(title=self.windowTitle()))
		banner = QLabel(READ_ONLY, self)
		banner.setWordWrap(True)
		ui.arrangement.insertWidget(0, banner)
		self.read_only_banner = banner
		for index in range(ui.pages.count()):
			page = ui.pages.widget(index)
			if page is not None:
				page.setEnabled(False)
		ui.buttons.setStandardButtons(QDialogButtonBox.StandardButton.Close)

	def _offer_first_logins(self, chosen: FirstLogin) -> None:
		"""La sécurité de la première connexion ; « Aucune validation » grisée en production, le serveur intranet
		installé en service (https://github.com/dascritch/machincast/issues/600)."""
		box = self.ui.intranet_first_login
		for value, text in FIRST_LOGINS.items():
			box.addItem(text, value)
		model = box.model()
		assert isinstance(model, QStandardItemModel)
		item = model.item(0)
		assert item is not None
		if intranet_switch.service_installed():
			item.setEnabled(False)
			item.setToolTip(IN_PRODUCTION)
		box.setCurrentIndex(box.findData(chosen))

	def _second_factor(self) -> SecondFactor:
		chosen = self.ui.intranet_second_factor.currentData()
		for value in SECOND_FACTORS:
			if value == chosen:
				return value
		return self.intranet.second_factor

	def _first_login(self) -> FirstLogin:
		chosen = self.ui.intranet_first_login.currentData()
		for value in FIRST_LOGINS:
			if value == chosen:
				return value
		return self.intranet.first_login

	def _show_intranet(self) -> None:
		"""Port et durée de validation ne servent qu'au serveur allumé ; allumé, les adresses à donner aux postes
		distants (https://github.com/dascritch/machincast/issues/538)."""
		ui = self.ui
		enabled = ui.intranet_enabled.isChecked()
		for widget in (ui.intranet_port, ui.intranet_validation, ui.intranet_first_login, ui.intranet_second_factor):
			widget.setEnabled(enabled)
		ui.intranet_addresses.setVisible(enabled)
		# Sans le service, sous le compte qui le lance, sans cloisonnement (https://github.com/dascritch/machincast/issues/549).
		ui.intranet_test_mode.setText(intranet_switch.TEST_MODE)
		ui.intranet_test_mode.setVisible(not intranet_switch.service_installed())
		# Ce qui tourne vraiment, quel que soit le réglage (https://github.com/dascritch/machincast/issues/558).
		said = intranet_switch.STOPPED
		if intranet_switch.running():
			said = intranet_switch.RUNNING
		ui.intranet_running.setText(said)
		if enabled:
			ui.intranet_addresses.setText(
				address_list(network.to_give(self.intranet.address, ui.intranet_port.value()))
			)

	def _offer_power_save(self) -> None:
		"""« Cartes son toujours éveillées », page « Audio », sous les cartes son : elle agit aussitôt, sans attendre
		« OK », et dit sous elle ce qu'il en est (https://github.com/dascritch/machincast/issues/532)."""
		box = QCheckBox(self.ui.device_group)
		box.setObjectName("power_save")
		self.ui.device_layout.addWidget(box)
		said = QLabel(self.ui.device_group)
		said.setObjectName("power_save_result")
		said.setWordWrap(True)
		said.setVisible(False)
		self.ui.device_layout.addWidget(said)
		self.power_save = PowerSaveSwitch(box, self)
		self.power_save.announced.connect(said.setText)
		self.power_save.announced.connect(lambda _text: said.setVisible(True))

	def _show_daily(self, daily: time, *, timers: bool | None) -> None:
		"""L'heure de la tâche quotidienne, réglable si install.sh --service a installé les minuteurs des tâches ; sinon
		grisée, et la page dit comment les installer (https://github.com/dascritch/machincast/issues/455)."""
		ui = self.ui
		if timers is None:
			timers = service_module.timers_installed()
		ui.daily.setTime(QTime(daily.hour, daily.minute))
		ui.daily.setEnabled(timers)
		ui.timers_missing.setText(TIMERS_MISSING)
		ui.timers_missing.setHidden(timers)

	def _show_notes(self, all_: Settings) -> None:
		"""Le document de l'installation, vide pour celui du Bureau, que montre l'indication du champ ; le lien de
		l'équipe, qui doit être une adresse web pour que « OK » serve (https://github.com/dascritch/machincast/issues/451)."""
		ui = self.ui
		text = ""
		if all_.notes is not None:
			text = str(all_.notes)
		ui.notes.setText(text)
		ui.notes.setPlaceholderText(str(notes_module.document(None)))
		ui.team_link.setText((all_.team_link) or (""))
		ui.choose_notes.clicked.connect(self._choose_notes)
		ui.team_link.textChanged.connect(self._exclude)

	def _choose_notes(self) -> None:
		from machincast.interface import dialogs

		field = self.ui.notes
		chosen = dialogs.choose_document(self, (field.text()) or (field.placeholderText()))
		if chosen is not None:
			field.setText(str(chosen))

	def _team_link(self) -> str | None:
		text = self.ui.team_link.text().strip()
		if text == "":
			return None
		return text

	def _choose_backup_directory(self) -> None:
		"""Le répertoire des sauvegardes, choisi dans le sélecteur, ouvert sur celui saisi ; abandonné, rien ne change."""
		from machincast.interface import dialogs

		field = self.ui.backup_directory
		chosen = dialogs.choose_directory(self, _("Backup directory"), field.text())
		if chosen is not None:
			field.setText(chosen)

	def _copy_configuration(self) -> None:
		"""Copie machincast.toml dans un répertoire choisi, comme une clé USB ; la page dit où, ou pourquoi elle n'a pas
		pu (https://github.com/dascritch/machincast/issues/347)."""
		from machincast.interface import dialogs

		assert self.configuration is not None
		chosen = dialogs.choose_directory(self, _("Where to copy machincast.toml"), self.ui.backup_directory.text())
		if chosen is None:
			return
		try:
			text = _("Copied to {copy}.").format(copy=copy_configuration(self.configuration, Path(chosen)))
		except OSError as error:
			text = _("Copy impossible: {error}").format(error=error)
		self.ui.copy_result.setText(text)
		self.ui.copy_result.setVisible(True)

	def _keep_only(self, kind: Kind) -> None:
		"""Les réglages de cette fenêtre seulement : les autres restent ceux du fichier, et settings() les rend tels
		quels (https://github.com/dascritch/machincast/issues/389)."""
		ui = self.ui
		self.setWindowTitle(TITLES[kind])
		if kind == SERVICE:
			for page in (ui.page_interface, ui.database_page):
				ui.pages.removeTab(ui.pages.indexOf(page))
			ui.crossfades_form.setRowVisible(0, False)
			ui.silence_group.setVisible(False)
			ui.silence_explanation.setVisible(False)
			ui.explanation.setText(SERVICE_EXPLANATION)
			self.cards.keep_rows(on_air=True, preview=False)
			return
		for page in (ui.tasks_page, ui.backup_page, ui.intranet_page):
			ui.pages.removeTab(ui.pages.indexOf(page))
		for row in (1, 2, 3):
			ui.crossfades_form.setRowVisible(row, False)
		ui.position_group.setVisible(False)
		ui.explanation.setVisible(False)
		ui.dead_air_group.setVisible(False)
		ui.pages.setTabText(ui.pages.indexOf(ui.page_crossfades), _("Crossfades and silences"))
		ui.audio_explanation.setText(INTERFACE_AUDIO_EXPLANATION)
		self.cards.keep_rows(on_air=False, preview=True)

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
		link = self.ui.team_link.text().strip()
		link_valid = (link == "") or (link.startswith(("http://", "https://")))
		ok = self.ui.buttons.button(QDialogButtonBox.StandardButton.Ok)
		inputs_valid = (self.inputs is None) or (self.inputs.valid())
		ok.setEnabled((self.cards.valid()) and (link_valid) and (inputs_valid))
		self.ui.team_link.setToolTip("")
		if not link_valid:
			self.ui.team_link.setToolTip(_("A web address, starting with http:// or https://"))

	def settings(self) -> Settings:
		"""Les réglages tels que la fenêtre les montre : crossfades, cartes son, seuil de silence et positions des fondus."""
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
			time(ui.daily.time().hour(), ui.daily.time().minute()),
			Path(ui.backup_directory.text().strip()).expanduser(),
			self._notes(),
			self._team_link(),
			dataclasses.replace(
				self.intranet,
				enabled=ui.intranet_enabled.isChecked(),
				port=ui.intranet_port.value(),
				validation=ui.intranet_validation.value(),
				first_login=self._first_login(),
				second_factor=self._second_factor(),
			),
			self._plugins(),
			self._inputs(),
		)

	def _inputs(self) -> tuple[AudioInput, ...]:
		if self.inputs is None:
			return self.given_inputs
		return self.inputs.chosen()

	def _plugins(self) -> tuple[str, ...]:
		if self.plugins_page is None:
			return self.enabled_plugins
		return self.plugins_page.enabled()

	def _notes(self) -> Path | None:
		text = self.ui.notes.text().strip()
		if text == "":
			return None
		return Path(text).expanduser()
