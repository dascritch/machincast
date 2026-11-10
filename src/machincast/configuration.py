"""Lecture et validation du fichier de configuration TOML de MachinCast.

Le modèle documenté clé par clé est `machincast.exemple.toml`, à la racine du dépôt.
"""

import logging
import os
import tomllib
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, cast

from machincast.database import SHORT_TEXT_LENGTH
from machincast.i18n import _
from machincast.player.fades import DEFAULT_ENTRY, DEFAULT_OUTPUT, POSITIONS, Position
from machincast.protection import is_sound_file

log = logging.getLogger(__name__)

FILE_NAME = "machincast.toml"

PROJECT_DIRECTORY = Path(__file__).resolve().parents[2]
"""Répertoire de MachinCast : dépôt local ou release décompressée, où se trouve machincast.toml.

Déduit de l'emplacement de ce module (src/machincast/), installé en mode éditable par install.sh : le même
répertoire que celui du wrapper Machin, qui appelle les binaires de son .venv
(https://github.com/dascritch/machincast/issues/76).
"""


def default_file() -> Path:
	"""Fichier lu quand aucun n'est passé avec --config, quel que soit le répertoire courant."""
	return PROJECT_DIRECTORY / FILE_NAME


AudioOutput = Literal["alsa", "pulseaudio", "pipewire", "dummy"]
AUDIO_OUTPUTS: tuple[AudioOutput, ...] = ("alsa", "pulseaudio", "pipewire", "dummy")
"""« factice » ne joue aucun son : pour les tests et les essais."""


class InvalidConfiguration(Exception):
	"""Le fichier de configuration est absent, mal formé ou incomplet."""


RETENTION = 60
"""Durée de péremption par défaut, en jours (https://github.com/dascritch/machincast/issues/268)."""


@dataclass(frozen=True)
class Database:
	socket: Path
	"""Répertoire de la socket Unix de PostgreSQL."""
	production: str
	test: str
	retention: int = RETENTION
	"""Jours au-delà desquels Machin purge efface de la base l'airplay, le log et les éléments supprimés
	(https://github.com/dascritch/machincast/issues/268)."""


DUMMY = "dummy"
"""L'entrée « sortie factice », que prennent audio.device et audio.preview
(https://github.com/dascritch/machincast/issues/339) : l'antenne ne joue aucun son, la pré-écoute est désactivée."""


@dataclass(frozen=True)
class Audio:
	output: AudioOutput
	device: str | None
	"""Périphérique d'antenne ; None tant qu'il n'est pas renseigné ; FACTICE pour l'entrée « sortie factice »."""
	preview: str
	"""Périphérique de pré-écoute ; FACTICE pour l'entrée « sortie factice », qui désactive la pré-écoute."""

	def on_air(self) -> tuple[AudioOutput, str | None]:
		"""La sortie et le périphérique où joue l'antenne : la sortie factice, sans périphérique, sur l'entrée « sortie
		factice »."""
		if self.device == DUMMY:
			return "dummy", None
		return self.output, self.device

	def dummy_on_air(self) -> bool:
		"""L'antenne ne joue aucun son : sortie factice, ou entrée « sortie factice »."""
		return self.on_air()[0] == "dummy"

	def to_fill_in_on_air(self) -> bool:
		"""Sur une vraie sortie, sans périphérique d'antenne, Machin player refuse de diffuser."""
		return (not self.dummy_on_air()) and (self.device is None)

	def disabled_preview(self) -> bool:
		"""Pré-écoute sur l'entrée « sortie factice » : ses boutons et ses menus sont grisés dans l'interface."""
		return self.preview == DUMMY


@dataclass(frozen=True)
class Outputs:
	csv: Path
	pls: Path
	html: Path


@dataclass(frozen=True)
class Metadata:
	hide: bool
	"""Masquage par défaut de l'artiste et du titre sur les sorties publiques."""
	public_text: str
	"""Texte public affiché à la place de l'artiste et du titre masqués, quand l'événement n'a pas de nom public."""


@dataclass(frozen=True)
class Player:
	state_socket: Path
	"""Socket Unix d'état du binaire lecture, lue par l'interface (https://github.com/dascritch/machincast/issues/20)."""


def default_state_socket() -> Path:
	"""Dans le répertoire d'exécution du compte ($XDG_RUNTIME_DIR, sinon /run/user/<uid>) : privé, effacé au
	redémarrage du poste."""
	directory = (os.environ.get("XDG_RUNTIME_DIR")) or (f"/run/user/{os.getuid()}")
	return Path(directory) / "machincast" / "lecture.sock"


Granularity = Literal["second", "tenth"]
GRANULARITIES: tuple[Granularity, ...] = ("second", "tenth")
CROSSFADES_MAXIMUM = timedelta(seconds=10)
"""Le crossfade le plus long que l'interface propose, sans réglage : 10 s
(https://github.com/dascritch/machincast/issues/223)."""


@dataclass(frozen=True)
class Crossfades:
	"""Réglages des crossfades (https://github.com/dascritch/machincast/issues/145), section [crossfades]."""

	start: timedelta | None = None
	"""Crossfade de début d'un sonore sans crossfade paramétré, que sa banque ne règle pas ; None : 0 seconde."""
	end: timedelta | None = None
	"""Crossfade de fin, de même."""
	maximum: timedelta = CROSSFADES_MAXIMUM
	"""Durée la plus longue que l'interface propose pour un crossfade."""
	granularity: Granularity = "tenth"
	"""Pas des crossfades dans l'interface : à la seconde ou au dixième de seconde."""
	entry: Position = DEFAULT_ENTRY
	"""Où le fade-in se place par rapport au début détecté d'un sonore joué sans ses silences
	(https://github.com/dascritch/machincast/issues/234)."""
	output: Position = DEFAULT_OUTPUT
	"""Où le fade-out se place par rapport à sa fin détectée, de même."""


SILENCE_THRESHOLD = -40.0
"""Seuil de silence par défaut, en dB crête : 0 dB est la pleine échelle (https://github.com/dascritch/machincast/issues/146)."""
MINIMUM_SILENCE_THRESHOLD = -100.0
"""Seuil de silence le plus bas accepté, compris ; le plus haut est 0 dB, exclu."""


@dataclass(frozen=True)
class Silences:
	"""Détection de silence (https://github.com/dascritch/machincast/issues/146), section [silences]."""

	threshold: float = SILENCE_THRESHOLD
	"""Niveau crête, en dB, sous lequel le début et la fin d'un sonore sont un silence : l'audit complet mesure les
	silences à ce seuil."""


DEAD_AIR_DURATION = timedelta(seconds=10)
"""Durée d'un blanc dans un sonore, par défaut (https://github.com/dascritch/machincast/issues/122)."""
DEAD_AIR_DURATIONS = (timedelta(seconds=1), timedelta(seconds=300))
"""Durées d'un blanc acceptées, bornes comprises."""
DEAD_AIR_THRESHOLD = -90.0
"""Niveau crête d'un blanc dans un sonore, par défaut, en dB."""


@dataclass(frozen=True)
class DeadAirSettings:
	"""Blanc dans un sonore, à l'antenne (https://github.com/dascritch/machincast/issues/122), section [dead_air].
	À ne pas confondre avec un silence, qui borne un fichier (Silences, https://github.com/dascritch/machincast/issues/291)."""

	duration: timedelta = DEAD_AIR_DURATION
	"""Le sonore qui joue reste au moins cette durée sous le seuil : c'est un blanc."""
	threshold: float = DEAD_AIR_THRESHOLD
	"""Niveau crête, en dB, sous lequel le sonore ne donne plus de son."""
	fallback: bool = False
	"""Un blanc fait passer au sonore suivant, ou au secours d'un stream ; sinon, il est seulement noté."""


TABLE_ROWS = 1000
"""Les lignes qu'un tableau de fiche charge d'un coup, par défaut ; la suite se charge en descendant (https://github.com/dascritch/machincast/issues/383)."""
MINIMUM_TABLE_ROWS = 100


@dataclass(frozen=True)
class Interface:
	"""Réglages de l'interface graphique (https://github.com/dascritch/machincast/issues/191), section [interface]."""

	clipping: bool = True
	"""Le voyant « Saturation » de la colonne Antenne, dans l'onglet du même nom est affiché."""
	suggestions: bool = True
	"""Au lancement, l'interface propose de créer ce qui manque pour démarrer
	(https://github.com/dascritch/machincast/issues/119)."""
	icon: Path | None = None
	"""L'image choisie pour icône de l'application, ses fenêtres et ses raccourcis ; None : celle de MachinCast
	(https://github.com/dascritch/machincast/issues/111)."""
	table_rows: int = TABLE_ROWS
	"""Les lignes qu'un tableau de fiche charge d'un coup (https://github.com/dascritch/machincast/issues/383)."""


ICON_EXTENSIONS = frozenset({".svg", ".png", ".jpg", ".jpeg"})
"""Les images acceptées pour icône, quelle que soit la casse de l'extension."""


@dataclass(frozen=True)
class Configuration:
	path: Path
	database: Database
	audio: Audio
	outputs: Outputs
	metadata: Metadata
	player: Player
	crossfades: Crossfades = field(default_factory=Crossfades)
	silences: Silences = field(default_factory=Silences)
	dead_air: DeadAirSettings = field(default_factory=DeadAirSettings)
	interface: Interface = field(default_factory=Interface)


# Clés connues, par section, en anglais (https://github.com/dascritch/machincast/issues/357). Toute autre clé est
# refusée, pour détecter les fautes de frappe.
KEYS: dict[str, frozenset[str]] = {
	"database": frozenset({"socket", "production", "test", "retention"}),
	"audio": frozenset({"output", "device", "preview"}),
	"outputs": frozenset({"csv", "pls", "html"}),
	"metadata": frozenset({"hide", "public_text"}),
	"player": frozenset({"state_socket"}),
	"crossfades": frozenset({"granularity", "maximum", "start", "end", "fade_in_position", "fade_out_position"}),
	"silences": frozenset({"threshold"}),
	"dead_air": frozenset({"duration", "threshold", "fallback"}),
	"interface": frozenset({"clipping", "suggestions", "icon", "table_rows"}),
}


OLD_SECTIONS = {
	"base": "database",
	"sorties": "outputs",
	"metadonnees": "metadata",
	"lecture": "player",
	"blanc_antenne": "dead_air",
	"blancs": "silences",
}
"""Les anciens noms français des sections, refusés en nommant leur nom anglais : pas de compatibilité, les
installations se refont de zéro (https://github.com/dascritch/machincast/issues/357)."""


class _Player:
	"""Lit les valeurs d'un document TOML en produisant des messages d'erreur explicites."""

	def __init__(self, path: Path, document: dict[str, Any]) -> None:
		self.path = path
		self.document = document

	def error(self, message: str) -> InvalidConfiguration:
		return InvalidConfiguration(_("{path}: {message}").format(path=self.path, message=message))

	def check_keys(self) -> None:
		for section, content in self.document.items():
			if section in OLD_SECTIONS:
				raise self.error(
					_(
						"unknown section [{section}]: its name is now [{old_sections}], and its keys are in "
						"English, as in machincast.exemple.toml "
						"(https://github.com/dascritch/machincast/issues/357)"
					).format(section=section, old_sections=OLD_SECTIONS[section])
				)
			if section not in KEYS:
				raise self.error(_("unknown section [{section}]").format(section=section))
			if not isinstance(content, dict):
				raise self.error(_("[{section}] must be a section").format(section=section))
			for key in content:
				if key not in KEYS[section]:
					raise self.error(_("unknown key {section}.{key}").format(section=section, key=key))

	def _value(self, section: str, key: str, mandatory: bool) -> object:
		content = self.document.get(section, {})
		if key not in content:
			if mandatory:
				raise self.error(_("missing key {section}.{key}").format(section=section, key=key))
			return None
		return cast(object, content[key])

	def text(self, section: str, key: str) -> str:
		value = self._value(section, key, mandatory=True)
		if not isinstance(value, str):
			raise self.error(
				_("key {section}.{key}: text expected, {describe} found").format(
					section=section, key=key, describe=_describe(value)
				)
			)
		if not value.strip():
			raise self.error(_("key {section}.{key}: the value cannot be empty").format(section=section, key=key))
		return value

	def short_text(self, section: str, key: str) -> str:
		"""Texte affiché au public : limité à SHORT_TEXT_LENGTH caractères, comme les textes en base."""
		value = self.text(section, key)
		if len(value) > SHORT_TEXT_LENGTH:
			raise self.error(
				_("key {section}.{key}: {short_text_length} characters at most, {count} found").format(
					section=section, key=key, short_text_length=SHORT_TEXT_LENGTH, count=len(value)
				)
			)
		return value

	def optional_text(self, section: str, key: str) -> str | None:
		value = self._value(section, key, mandatory=False)
		if value is None:
			return None
		if not isinstance(value, str):
			raise self.error(
				_("key {section}.{key}: text expected, {describe} found").format(
					section=section, key=key, describe=_describe(value)
				)
			)
		return (value) or (None)

	def optional_path(self, section: str, key: str) -> Path | None:
		"""Comme file_path, ou None si la clé est absente."""
		if self.optional_text(section, key) is None:
			return None
		return self.file_path(section, key)

	def icon(self) -> Path | None:
		"""interface.icon : une image SVG, PNG ou JPEG ; elle peut manquer sur le poste, l'interface prend alors
		l'icône de MachinCast."""
		path = self.optional_path("interface", "icon")
		if (path is not None) and (path.suffix.lower() not in ICON_EXTENSIONS):
			raise self.error(
				_("key interface.icon: SVG, PNG or JPEG image expected, “{name}” found").format(name=path.name)
			)
		return path

	def boolean(self, section: str, key: str) -> bool:
		value = self._value(section, key, mandatory=True)
		if not isinstance(value, bool):
			raise self.error(
				_("key {section}.{key}: boolean expected (true or false), {describe} found").format(
					section=section, key=key, describe=_describe(value)
				)
			)
		return value

	def optional_boolean(self, section: str, key: str, default: bool) -> bool:
		value = self._value(section, key, mandatory=False)
		if value is None:
			return default
		if not isinstance(value, bool):
			raise self.error(
				_("key {section}.{key}: boolean expected (true or false), {describe} found").format(
					section=section, key=key, describe=_describe(value)
				)
			)
		return value

	def days(self, section: str, key: str, default: int) -> int:
		"""Un nombre entier de jours, 1 au moins ; defaut sans la clé."""
		value = self.document.get(section, {}).get(key, default)
		if (isinstance(value, bool)) or (not isinstance(value, int)) or (value < 1):
			raise self.error(
				_("key {section}.{key}: “{value}” is not a whole number of days, at least 1").format(
					section=section, key=key, value=value
				)
			)
		return value

	def rows(self, section: str, key: str, default: int) -> int:
		"""Un nombre entier de lignes, MINIMUM_TABLE_ROWS au moins ; defaut sans la clé."""
		value = self.document.get(section, {}).get(key, default)
		if (isinstance(value, bool)) or (not isinstance(value, int)) or (value < MINIMUM_TABLE_ROWS):
			raise self.error(
				_("key {section}.{key}: “{value}” is not a whole number of rows, at least {minimum}").format(
					section=section, key=key, value=value, minimum=MINIMUM_TABLE_ROWS
				)
			)
		return value

	def optional_count(self, section: str, key: str) -> float | None:
		value = self._value(section, key, mandatory=False)
		if value is None:
			return None
		if (isinstance(value, bool)) or (not isinstance(value, (int, float))):
			raise self.error(
				_("key {section}.{key}: number expected, {describe} found").format(
					section=section, key=key, describe=_describe(value)
				)
			)
		return float(value)

	def crossfades(self) -> Crossfades:
		"""La section [crossfades], facultative, comme toutes ses clés."""
		fetched = (self.optional_text("crossfades", "granularity")) or ("tenth")
		granularity = fetched
		if granularity not in GRANULARITIES:
			raise self.error(
				_("key crossfades.granularity: unknown “{fetched}”, possible values: {list}").format(
					fetched=fetched, list=", ".join(GRANULARITIES)
				)
			)
		maximum = CROSSFADES_MAXIMUM
		seconds = self.optional_count("crossfades", "maximum")
		if seconds is not None:
			if seconds <= 0:
				raise self.error(_("key crossfades.maximum: a strictly positive number of seconds is expected"))
			maximum = timedelta(seconds=seconds)
		durations: list[timedelta | None] = []
		for key in ("start", "end"):
			duration = self.optional_count("crossfades", key)
			if duration is None:
				durations.append(None)
				continue
			if duration < 0:
				raise self.error(
					_("key crossfades.{key}: a positive or zero number of seconds is expected").format(key=key)
				)
			if timedelta(seconds=duration) > maximum:
				raise self.error(
					_("key crossfades.{key}: at most crossfades.maximum, {maximum:g} s").format(
						key=key, maximum=maximum.total_seconds()
					)
				)
			durations.append(timedelta(seconds=duration))
		positions: list[Position] = []
		for key, default in (("fade_in_position", DEFAULT_ENTRY), ("fade_out_position", DEFAULT_OUTPUT)):
			fetched = (self.optional_text("crossfades", key)) or (default)
			position = fetched
			if position not in POSITIONS:
				raise self.error(
					_("key crossfades.{key}: unknown “{fetched}”, possible values: {list}").format(
						key=key, fetched=fetched, list=", ".join(POSITIONS)
					)
				)
			positions.append(position)
		return Crossfades(durations[0], durations[1], maximum, granularity, positions[0], positions[1])

	def silences(self) -> Silences:
		"""La section [silences], facultative, comme sa clé."""
		threshold = self.optional_count("silences", "threshold")
		if threshold is None:
			return Silences()
		if not (MINIMUM_SILENCE_THRESHOLD <= threshold < 0):
			raise self.error(
				_(
					"key silences.threshold: a number of dB from {minimum_silence_threshold:g} dB included to "
					"0 dB excluded is expected, {threshold:g} found"
				).format(minimum_silence_threshold=MINIMUM_SILENCE_THRESHOLD, threshold=threshold)
			)
		return Silences(threshold)

	def dead_air(self) -> DeadAirSettings:
		"""La section [dead_air], facultative, comme ses clés (https://github.com/dascritch/machincast/issues/122)."""
		duration = DEAD_AIR_DURATION
		seconds = self.optional_count("dead_air", "duration")
		if seconds is not None:
			bound_list = []
			for bound in DEAD_AIR_DURATIONS:
				bound_list.append(bound.total_seconds())
			minimum, maximum = bound_list
			if not (minimum <= seconds <= maximum):
				raise self.error(
					_(
						"key dead_air.duration: a number of seconds, from {minimum:g} to {maximum:g} seconds "
						"included, is expected, {seconds:g} found"
					).format(minimum=minimum, maximum=maximum, seconds=seconds)
				)
			duration = timedelta(seconds=seconds)
		threshold = self.optional_count("dead_air", "threshold")
		if threshold is None:
			threshold = DEAD_AIR_THRESHOLD
		else:
			if not (MINIMUM_SILENCE_THRESHOLD <= threshold < 0):
				raise self.error(
					_(
						"key dead_air.threshold: a number of dB from {minimum_silence_threshold:g} dB included to "
						"0 dB excluded is expected, {threshold:g} found"
					).format(minimum_silence_threshold=MINIMUM_SILENCE_THRESHOLD, threshold=threshold)
				)
		return DeadAirSettings(duration, threshold, self.optional_boolean("dead_air", "fallback", False))

	def file_path(self, section: str, key: str) -> Path:
		"""Chemin absolu tel quel ; chemin relatif résolu depuis le répertoire du fichier de configuration."""
		path = Path(self.text(section, key)).expanduser()
		if path.is_absolute():
			return path
		return self.path.parent / path


def _describe(value: object) -> str:
	match value:
		case bool():
			return _("boolean")
		case int() | float():
			return _("number")
		case str():
			return _("text")
		case list():
			return _("list")
		case dict():
			return _("section")
		case _:
			return type(value).__name__


def load(path: Path | None = None) -> Configuration:
	"""Charge et valide la configuration.

	Sans chemin, lit `machincast.toml` dans le répertoire de MachinCast (default_file).
	Lève InvalidConfiguration avec un message qui nomme le fichier et la clé en cause.
	"""
	path = ((path) or (default_file())).expanduser().absolute()
	try:
		with path.open("rb") as file:
			document = tomllib.load(file)
	except FileNotFoundError:
		raise InvalidConfiguration(_("{path}: configuration file not found").format(path=path)) from None
	except tomllib.TOMLDecodeError as error:
		raise InvalidConfiguration(_("{path}: invalid TOML syntax ({error})").format(path=path, error=error)) from None

	reader = _Player(path, document)
	reader.check_keys()

	database = Database(
		socket=Path(reader.text("database", "socket")),
		production=reader.text("database", "production"),
		test=reader.text("database", "test"),
		retention=reader.days("database", "retention", RETENTION),
	)
	if database.test == database.production:
		raise reader.error(_("key database.test: the test database cannot be the production database"))

	fetched = reader.text("audio", "output")
	output = fetched
	if output not in AUDIO_OUTPUTS:
		raise reader.error(
			_("key audio.output: unknown “{fetched}”, possible values: {list}").format(
				fetched=fetched, list=", ".join(AUDIO_OUTPUTS)
			)
		)
	device = reader.optional_text("audio", "device")
	if device is not None:
		device = device
	preview = reader.text("audio", "preview")
	if preview == device:
		raise reader.error(_("key audio.pre-listen: the pre-listen must use another device than the on-air one"))

	outputs = Outputs(
		csv=reader.file_path("outputs", "csv"),
		pls=reader.file_path("outputs", "pls"),
		html=reader.file_path("outputs", "html"),
	)
	player = Player(state_socket=(reader.optional_path("player", "state_socket")) or (default_state_socket()))
	# Un fichier sonore n'est jamais écrit ni remplacé (https://github.com/dascritch/machincast/issues/96).
	for key, value in (
		("outputs.csv", outputs.csv),
		("outputs.pls", outputs.pls),
		("outputs.html", outputs.html),
		("player.state_socket", player.state_socket),
	):
		if is_sound_file(value):
			raise reader.error(
				_(
					"key {key}: “{value}” has the extension of a sound file, and MachinCast never writes to a "
					"sound file"
				).format(key=key, value=value)
			)

	return Configuration(
		path=path,
		database=database,
		audio=Audio(output=output, device=device, preview=preview),
		outputs=outputs,
		metadata=Metadata(
			hide=reader.boolean("metadata", "hide"),
			public_text=reader.short_text("metadata", "public_text"),
		),
		player=player,
		crossfades=reader.crossfades(),
		silences=reader.silences(),
		dead_air=reader.dead_air(),
		interface=Interface(
			clipping=reader.optional_boolean("interface", "clipping", True),
			suggestions=reader.optional_boolean("interface", "suggestions", True),
			icon=reader.icon(),
			table_rows=reader.rows("interface", "table_rows", TABLE_ROWS),
		),
	)
