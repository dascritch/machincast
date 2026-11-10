"""Étapes d'installation appelées par install.sh (https://github.com/dascritch/machincast/issues/40).

	python -m machincast.installation databases   --config machincast.toml   socket, base de production, base de test
	python -m machincast.installation migrate     --config machincast.toml   schéma appliqué aux deux bases
	python -m machincast.installation check       --config machincast.toml   GStreamer, greffons, sortie audio
	python -m machincast.installation unit        --config machincast.toml   unité systemd du service de lecture
	python -m machincast.installation pipewire-unit, wireplumber-unit         le PipeWire du service et son WirePlumber
	python -m machincast.installation wireplumber-service, wireplumber-desktop   leur configuration, et celle du bureau
	python -m machincast.installation tmpfiles, logrotate                      répertoires du service, rotation des logs
	python -m machincast.installation rule        --config machincast.toml   règle polkit qui le pilote
	python -m machincast.installation purge-unit  --config machincast.toml   unité systemd de la purge
	python -m machincast.installation purge-timer --config machincast.toml   son minuteur, chaque jour à midi
	python -m machincast.installation shortcut    --config machincast.toml   raccourci de l'interface (.desktop)
	python -m machincast.installation devices     --config machincast.toml   périphériques de sortie du poste
	python -m machincast.installation on-air      --config machincast.toml   antenne utilisable par le service

devices n'est pas appelé par install.sh : il aide à trouver les identifiants à recopier dans audio.device
et audio.preview (https://github.com/dascritch/machincast/issues/116). on-air l'est par install.sh --service, avant
d'installer le service : il refuse une antenne sur la sortie factice (https://github.com/dascritch/machincast/issues/339).

install.sh enchaîne les commandes système (apt, sudo, psql, liens) ; ce module porte ce qui se teste : la lecture
de la configuration, les migrations, la vérification de la version et des greffons GStreamer
(https://github.com/dascritch/machincast/issues/284), et le texte de l'unité systemd et de la règle polkit du service
de lecture (https://github.com/dascritch/machincast/issues/22), et ceux de l'unité et du minuteur de la purge
quotidienne (https://github.com/dascritch/machincast/issues/268), qu'install.sh --service installe, et celui du
raccourci de l'interface, qu'install.sh met dans le menu des applications du compte et, sur demande, sur son bureau
(https://github.com/dascritch/machincast/issues/62). Le service tourne sous son propre compte, machincast, avec son
PipeWire (https://github.com/dascritch/machincast/issues/381).
"""

import argparse
import grp
import logging
import os
import pwd
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import gi
import psycopg

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast import audio as audio_outputs  # noqa: E402
from machincast import crash, service  # noqa: E402
from machincast import log as log_directory  # noqa: E402
from machincast import shortcut as write_shortcut  # noqa: E402
from machincast.audio import PLUGINS, TRIAL, Plugin, UnavailableAudioOutput, create_output  # noqa: E402
from machincast.cli import launch  # noqa: E402
from machincast.configuration import PROJECT_DIRECTORY, Audio, AudioOutput, Configuration  # noqa: E402
from machincast.database import apply_migrations, url_yoyo  # noqa: E402
from machincast.i18n import _  # noqa: E402
from machincast.service import UNIT  # noqa: E402

EXECUTABLE = "machincast.installation"
DESCRIPTION = _("MachinCast installation steps, called by install.sh.")
FAILURE_CODE = 1
PURGE_UNIT = "machincast-purge.service"
"""L'unité de la purge, Machin purge : les mêmes noms dans install.sh."""
PURGE_TIMER = "machincast-purge.timer"
PURGE_HOUR = "*-*-* 12:00:00"
"""Chaque jour à midi : en journée, quand le poste de l'antenne est allumé."""

# Nom explicite : lancé par python -m, ce module s'appelle __main__, hors du journal « machincast ».
log = logging.getLogger("machincast.installation")


@dataclass(frozen=True)
class Requirement:
	"""Un élément GStreamer d'un type donné doit savoir lire ces capacités."""

	item_type: int
	capabilities: str
	package: str | None = None
	"""Paquet qui fournit l'élément, quand ce n'est pas celui du format."""


@dataclass(frozen=True)
class SoundFormat:
	requirements: tuple[Requirement, ...]
	package: str
	"""Paquet Ubuntu qui fournit les éléments, parmi les prérequis de CLAUDE.md."""


_DECODER = Gst.ELEMENT_FACTORY_TYPE_DECODER
_DEMUXER = Gst.ELEMENT_FACTORY_TYPE_DEMUXER
_ANALYSER = Gst.ELEMENT_FACTORY_TYPE_PARSER

FORMATS: dict[str, SoundFormat] = {
	"mp3": SoundFormat(
		(Requirement(_DECODER, "audio/mpeg, mpegversion=(int)1, layer=(int)3"),), "gstreamer1.0-plugins-good"
	),
	"m4a": SoundFormat(
		(Requirement(_DEMUXER, "audio/x-m4a"), Requirement(_DECODER, "audio/mpeg, mpegversion=(int)4")),
		"gstreamer1.0-plugins-bad",
	),
	# AAC brut en trames ADTS (.aac) : aacparse (plugins-good) découpe les trames, le décodeur est celui du M4A.
	"aac": SoundFormat(
		(
			Requirement(
				_ANALYSER, "audio/mpeg, mpegversion=(int)4, stream-format=(string)adts", "gstreamer1.0-plugins-good"
			),
			Requirement(_DECODER, "audio/mpeg, mpegversion=(int)4"),
		),
		"gstreamer1.0-plugins-bad",
	),
	"ogg": SoundFormat(
		(Requirement(_DEMUXER, "application/ogg"), Requirement(_DECODER, "audio/x-vorbis")),
		"gstreamer1.0-plugins-base",
	),
	"flac": SoundFormat((Requirement(_DECODER, "audio/x-flac"),), "gstreamer1.0-plugins-good"),
	"wav": SoundFormat((Requirement(_DEMUXER, "audio/x-wav"),), "gstreamer1.0-plugins-good"),
}
"""Formats de la spec § 6.2, et ce que decodebin doit trouver pour les décoder."""


@dataclass(frozen=True)
class Shortfall:
	item: str
	"""Format sonore, protocole de stream ou sortie audio qui ne peut pas fonctionner."""
	package: str


def _satisfied(requirement: Requirement) -> bool:
	"""Vrai si un élément utilisable par decodebin (rang au moins MARGINAL) lit ces capacités."""
	capabilities = Gst.Caps.from_string(requirement.capabilities)
	assert capabilities is not None
	factories = Gst.ElementFactory.list_get_elements(requirement.item_type, Gst.Rank.MARGINAL)
	for factory in factories:
		if factory.can_sink_any_caps(capabilities):
			return True
	return False


def check_decoders() -> list[Shortfall]:
	"""Formats de la spec qu'aucun décodeur GStreamer installé ne sait lire, avec le paquet à installer.

	Le paquet nommé est celui du premier élément manquant.
	"""
	Gst.init(None)
	gaps = []
	for name, sound_format in FORMATS.items():
		absent = None
		for e in sound_format.requirements:
			if not _satisfied(e):
				absent = e
				break
		if absent is not None:
			gaps.append(Shortfall(name, (absent.package) or (sound_format.package)))
	return gaps


STREAM_PROTOCOLS = {"http": "gstreamer1.0-plugins-good", "https": "gstreamer1.0-plugins-good"}
"""Protocoles des streams (https://github.com/dascritch/machincast/issues/16), et le paquet de leur source
(souphttpsrc)."""


def check_streams() -> list[Shortfall]:
	"""Protocoles de stream qu'aucune source GStreamer installée ne sait lire, avec le paquet à installer."""
	Gst.init(None)
	sources = []
	for f in Gst.ElementFactory.list_get_elements(Gst.ELEMENT_FACTORY_TYPE_SRC, Gst.Rank.MARGINAL):
		if f.get_uri_type() == Gst.URIType.SRC:
			sources.append(f)
	fetched_list = set()
	for f in sources:
		for protocol in (f.get_uri_protocols()) or ([]):
			fetched_list.add(protocol)
	check_streams = []
	for p, package in STREAM_PROTOCOLS.items():
		if p not in fetched_list:
			check_streams.append(Shortfall(_("stream {p}").format(p=p), package))
	return check_streams


def check_output(configuration: Configuration, plugins: dict[AudioOutput, Plugin] = PLUGINS) -> list[Shortfall]:
	"""Crée l'élément de la sortie audio configurée, sans jouer de son : aucun son ne part à l'antenne. Sur l'entrée
	« sortie factice » de l'antenne, la sortie reste à vérifier, pour la pré-écoute."""
	audio = configuration.audio
	try:
		create_output(audio.output, audio.on_air()[1], plugins, presentation=TRIAL)
	except UnavailableAudioOutput:
		return [Shortfall(_("audio output {output}").format(output=audio.output), plugins[audio.output].package)]
	return []


CHECKED_VERSION = (1, 28)
"""Version de GStreamer avec laquelle MachinCast est vérifié, celle d'Ubuntu 26.04 LTS
(https://github.com/dascritch/machincast/issues/284) : la suite de tests et les mesures de tests.gstreamer_measures
y sont faites. Une version plus ancienne fonctionne, sans garantie : ses défauts peuvent être autres."""
CHECKED_DISTRIBUTION = "Ubuntu 26.04 LTS"
COMPONENTS: dict[str, tuple[str | None, str]] = {
	"GStreamer": (None, "libgstreamer1.0-0"),
	_("the GStreamer playback plugin"): ("playback", "gstreamer1.0-plugins-base"),
	_("the GStreamer flac plugin"): ("flac", "gstreamer1.0-plugins-good"),
	_("the GStreamer faad plugin"): ("faad", "gstreamer1.0-plugins-bad"),
}
"""Le cœur de GStreamer, et un greffon de chaque paquet de greffons : celui qui les fournit, à mettre à jour."""


@dataclass(frozen=True)
class Old:
	component: str
	version: str
	package: str


def read_version(plugin: str | None) -> str | None:
	"""La version installée du cœur de GStreamer, ou d'un greffon ; None pour un greffon absent."""
	Gst.init(None)
	if plugin is None:
		major, minor, corrective, _nano = Gst.version()
		return f"{major}.{minor}.{corrective}"
	found = Gst.Registry.get().find_plugin(plugin)
	if found is None:
		return None
	return str(found.get_version())


def _numbers(version: str) -> tuple[int, ...]:
	number_list = []
	for number in version.split(".")[:2]:
		if number.isdigit():
			number_list.append(int(number))
	return tuple(number_list)


def check_versions() -> list[Old]:
	"""Ce qui est plus ancien que la version vérifiée, avec le paquet à mettre à jour. Un greffon absent n'est pas
	signalé ici : check_decoders le signale."""
	old_list = []
	for component, (plugin, package) in COMPONENTS.items():
		version = read_version(plugin)
		if (version is not None) and (_numbers(version) < CHECKED_VERSION):
			old_list.append(Old(component, version, package))
	return old_list


def _databases(configuration: Configuration) -> int:
	# Données lues par install.sh, une valeur par ligne : ce n'est pas un message, d'où l'écriture directe.
	database = configuration.database
	sys.stdout.write(f"{database.socket}\n{database.production}\n{database.test}\n")
	return 0


def _migrate(configuration: Configuration) -> int:
	database = configuration.database
	for name in (database.production, database.test):
		try:
			apply_migrations(url_yoyo(database.socket, name))
		except psycopg.OperationalError as error:
			log.error(
				_("database unreachable ({name} through {socket}): {error}").format(
					name=name, socket=database.socket, error=error
				)
			)
			return FAILURE_CODE
		except psycopg.errors.InsufficientPrivilege as error:
			log.error(
				_(
					"insufficient rights to apply the schema in database {name}, which probably belongs to "
					"another PostgreSQL role: {error}"
				).format(name=name, error=error)
			)
			return FAILURE_CODE
		log.info(_("schema up to date in database {name}").format(name=name))
	return 0


def _check(configuration: Configuration) -> int:
	number_list = []
	for number in CHECKED_VERSION:
		number_list.append(str(number))
	checked = ".".join(number_list)
	for old in check_versions():
		log.warning(
			_(
				"{component} {version}: MachinCast is checked with version {checked} "
				"({checked_distribution}); update {package}"
			).format(
				component=old.component,
				version=old.version,
				checked=checked,
				checked_distribution=CHECKED_DISTRIBUTION,
				package=old.package,
			)
		)
	gaps = check_decoders() + check_streams() + check_output(configuration)
	for missing in gaps:
		log.error(
			_("{item}: GStreamer plugin missing, install {package}").format(item=missing.item, package=missing.package)
		)
	if gaps:
		return FAILURE_CODE
	log.info(_("decoders, stream source and audio output available"))
	return 0


DUMMY_ON_AIR = _(
	"on air on the dummy output: the broadcast service would play no sound; choose another "
	"sound card in Machin interface, File → Preferences…, Audio page, then run ./install.sh "
	"--service again"
)

PULSEAUDIO_ON_AIR = _(
	"on air on the PulseAudio output: the broadcast service plays through its own PipeWire; choose the "
	"PipeWire output in Machin interface, File → Preferences…, Audio page, then run ./install.sh --service again"
)


def _on_air(configuration: Configuration) -> int:
	"""Le service de diffusion d'un poste dédié joue toujours sur une carte son : jamais sur la sortie factice, ni sur
	l'entrée « Sortie factice » de l'antenne (https://github.com/dascritch/machincast/issues/339). Il joue par son
	propre PipeWire, sans serveur PulseAudio (https://github.com/dascritch/machincast/issues/381)."""
	audio = configuration.audio
	if audio.dummy_on_air():
		log.error(DUMMY_ON_AIR)
		return FAILURE_CODE
	if audio.output == "pulseaudio":
		log.error(PULSEAUDIO_ON_AIR)
		return FAILURE_CODE
	output, device = audio.on_air()
	if device is None:
		log.warning(
			_(
				"on air on output {output}, to be filled in: the broadcast service will refuse to start "
				"until audio.device gives it"
			).format(output=output)
		)
		return 0
	log.info(
		_("on air on output {output}, device {device}: the broadcast service can use it").format(
			output=output, device=device
		)
	)
	return 0


@dataclass(frozen=True)
class Account:
	"""Le compte de MachinCast, celui qui l'installe : propriétaire de la base, il lance la purge et pilote le service,
	qui tourne sous le compte du service (SERVICE_ACCOUNT, https://github.com/dascritch/machincast/issues/381)."""

	name: str
	group: str
	uid: int

	@classmethod
	def current(cls) -> "Account":
		entry = pwd.getpwuid(os.getuid())
		return cls(entry.pw_name, grp.getgrgid(entry.pw_gid).gr_name, entry.pw_uid)


SERVICE_ACCOUNT = "machincast"
"""Le compte système du service de diffusion, et son groupe, où install.sh --service ajoute le compte de MachinCast
(https://github.com/dascritch/machincast/issues/381) : les mêmes noms dans install.sh."""
SERVICE_RUNTIME = service.RUNTIME
"""Le répertoire d'exécution du service : la socket de son PipeWire, pipewire-0, et sa socket d'état. Partagé avec le
groupe (2770), recréé à chaque démarrage du poste par tmpfiles.d."""
SERVICE_STATE = Path("/var/lib/machincast")
"""Le répertoire personnel du compte du service : l'état de son WirePlumber."""
SERVICE_WIREPLUMBER = Path("/etc/machincast/wireplumber")
"""La configuration du WirePlumber du service, seule lue avec celle du paquet : pas celle de /etc/wireplumber, qui
cache la carte de l'antenne au bureau."""
PIPEWIRE_UNIT = "machincast-pipewire.service"
WIREPLUMBER_UNIT = "machincast-wireplumber.service"
SERVICE_GROUP_MODE = "2770"
"""Répertoires du service : le compte et son groupe lisent et écrivent, les fichiers créés restent au groupe."""
HEADER = """# Installed by install.sh --service; do not edit here, run install.sh --service again."""


def _service_account() -> str:
	"""Le compte du service, son groupe, et le même environnement pour PipeWire, WirePlumber et Machin player :
	tout ce qu'ils créent est au groupe, que le compte de MachinCast rejoint."""
	return f"""User={SERVICE_ACCOUNT}
Group={SERVICE_ACCOUNT}
# Les cartes son, hors d'une session ouverte : le groupe audio.
SupplementaryGroups=audio
UMask=0007
Environment=HOME={SERVICE_STATE}
Environment=XDG_RUNTIME_DIR={SERVICE_RUNTIME}
Environment=PIPEWIRE_RUNTIME_DIR={SERVICE_RUNTIME}"""


def systemd_unit(directory: Path = PROJECT_DIRECTORY) -> str:
	"""L'unité du service de lecture : Machin player, sous le compte du service, relancé après un plantage. Il joue
	par le PipeWire du service, démarré avant lui (https://github.com/dascritch/machincast/issues/381) ; ses messages
	vont dans journald et dans /var/log/machincast."""
	return f"""# MachinCast broadcast service (https://github.com/dascritch/machincast/issues/22).
{HEADER}

[Unit]
Description=MachinCast: on-air broadcast (Machin player)
Wants=network-online.target
Requires={PIPEWIRE_UNIT} {WIREPLUMBER_UNIT}
After=network-online.target postgresql.service sound.target {PIPEWIRE_UNIT} {WIREPLUMBER_UNIT}

[Service]
Type=simple
{_service_account()}
WorkingDirectory={directory}
ExecStart={directory}/bin/Machin player
Restart=on-failure
RestartSec=5
# Code 2 : configuration ou appel invalide, que relancer ne corrige pas (https://github.com/dascritch/machincast/issues/376).
RestartPreventExitStatus=2
KillSignal=SIGTERM
TimeoutStopSec=15
SyslogIdentifier=machincast

[Install]
WantedBy=multi-user.target
"""


def pipewire_unit() -> str:
	"""Le PipeWire du service : le sien, sous son compte, hors de toute session ; sa socket est dans le répertoire
	d'exécution du service, que le groupe lit, pour la pré-écoute et le VU-mètre de l'interface."""
	return f"""# PipeWire of the MachinCast broadcast service (https://github.com/dascritch/machincast/issues/381).
{HEADER}

[Unit]
Description=MachinCast: PipeWire of the broadcast service
After=sound.target systemd-tmpfiles-setup.service

[Service]
Type=simple
{_service_account()}
StateDirectory=machincast
ExecStart=/usr/bin/pipewire
Restart=on-failure
RestartSec=2
SyslogIdentifier=machincast-pipewire

[Install]
WantedBy=multi-user.target
"""


def wireplumber_unit() -> str:
	"""Le WirePlumber du service : il donne au PipeWire du service les cartes son, avec sa seule configuration
	(SERVICE_WIREPLUMBER) et celle du paquet."""
	return f"""# WirePlumber of the MachinCast broadcast service (https://github.com/dascritch/machincast/issues/381).
{HEADER}

[Unit]
Description=MachinCast: WirePlumber of the broadcast service
BindsTo={PIPEWIRE_UNIT}
After={PIPEWIRE_UNIT}

[Service]
Type=simple
{_service_account()}
Environment=WIREPLUMBER_CONFIG_DIR={SERVICE_WIREPLUMBER}:/usr/share/wireplumber
StateDirectory=machincast
ExecStart=/usr/bin/wireplumber
Restart=on-failure
RestartSec=2
SyslogIdentifier=machincast-wireplumber

[Install]
WantedBy={PIPEWIRE_UNIT}
"""


def tmpfiles() -> str:
	"""Les répertoires du service, recréés à chaque démarrage du poste : d'exécution, des logs et des rapports de
	crash, au compte du service et à son groupe."""
	lines = [
		"# Directories of the MachinCast broadcast service (https://github.com/dascritch/machincast/issues/381).",
		HEADER,
	]
	for directory in (SERVICE_RUNTIME, log_directory.DIRECTORY, crash.DIRECTORY):
		lines.append(f"d {directory} {SERVICE_GROUP_MODE} {SERVICE_ACCOUNT} {SERVICE_ACCOUNT} -")
	return "\n".join(lines) + "\n"


def logrotate() -> str:
	"""La rotation des logs de /var/log/machincast : chaque semaine, huit semaines gardées. Les binaires du service et
	du bureau y écrivent ensemble : la copie, puis la troncature, laisse leurs fichiers ouverts valables."""
	return f"""# Logs of MachinCast (https://github.com/dascritch/machincast/issues/381).
{HEADER}
{log_directory.DIRECTORY}/*.log {{
	su {SERVICE_ACCOUNT} {SERVICE_ACCOUNT}
	weekly
	rotate 8
	compress
	delaycompress
	missingok
	notifempty
	copytruncate
}}
"""


WIREPLUMBER_FRAGMENT = "50-machincast.conf"
"""Le même nom pour les deux fragments : celui du service, et celui du bureau, dans /etc/wireplumber."""


def wireplumber_service() -> str:
	"""Le fragment du WirePlumber du service : seulement les cartes son ; ni Bluetooth, ni caméras, qu'un compte sans
	session n'atteint pas."""
	return f"""# WirePlumber of the MachinCast broadcast service (https://github.com/dascritch/machincast/issues/381).
{HEADER}
wireplumber.profiles = {{
	main = {{
		monitor.bluez = disabled
		monitor.bluez-midi = disabled
		monitor.v4l2 = disabled
		monitor.libcamera = disabled
	}}
}}
"""


def wireplumber_desktop(audio: Audio) -> str:
	"""Le fragment du WirePlumber des sessions du poste : la carte de l'antenne y est cachée, elle est au service ; deux
	PipeWire n'ouvrent pas la même carte en même temps. Sans antenne sur une carte PipeWire, il ne cache rien."""
	output, device = audio.on_air()
	head = f"""# MachinCast: the on-air card belongs to the broadcast service (https://github.com/dascritch/machincast/issues/381).
{HEADER}
"""
	if (output != "pipewire") or (device is None) or (audio.dummy_on_air()):
		return head + "# No on-air card to hide.\n"
	name = device.replace("\\", "\\\\").replace('"', '\\"')
	return (
		head
		+ f"""monitor.alsa.rules = [
	{{
		matches = [ {{ node.name = "{name}" }} ]
		actions = {{ update-props = {{ node.disabled = true }} }}
	}}
]
"""
	)


def purge_unit(account: Account, directory: Path = PROJECT_DIRECTORY) -> str:
	"""L'unité de la purge : Machin purge, une fois, sous le compte de MachinCast, propriétaire de la base. Son
	minuteur la lance ; elle n'a pas de section Install. Ses messages vont dans journald."""
	return f"""# MachinCast database purge (https://github.com/dascritch/machincast/issues/268).
# Installed by install.sh --service; do not edit here, run install.sh --service again.

[Unit]
Description=MachinCast: database purge (Machin purge)
After=postgresql.service

[Service]
Type=oneshot
User={account.name}
Group={account.group}
WorkingDirectory={directory}
ExecStart={directory}/bin/Machin purge
SyslogIdentifier=machincast-purge
"""


def purge_timer() -> str:
	"""Le minuteur de la purge : chaque jour à midi ; une purge manquée, poste éteint, se fait à son démarrage."""
	return f"""# Daily purge of the MachinCast database (https://github.com/dascritch/machincast/issues/268).
# Installed by install.sh --service; do not edit here, run install.sh --service again.

[Unit]
Description=MachinCast: daily database purge, at noon

[Timer]
OnCalendar={PURGE_HOUR}
Persistent=true
Unit={PURGE_UNIT}

[Install]
WantedBy=timers.target
"""


def polkit_rule(account: Account) -> str:
	"""La règle polkit du service de lecture : son compte le démarre, l'arrête ou le redémarre, avec
	l'authentification d'un administrateur ; rien d'autre, ni sur une autre unité."""
	return f"""// Control of the MachinCast broadcast service (https://github.com/dascritch/machincast/issues/22).
// Installed by install.sh --service; do not edit here, run install.sh --service again.
polkit.addRule(function (action, subject) {{
	if ((action.id == "org.freedesktop.systemd1.manage-units") && (action.lookup("unit") == "{UNIT}")
		&& (["start", "stop", "restart"].indexOf(action.lookup("verb")) >= 0) && (subject.user == "{account.name}")) {{
		return polkit.Result.AUTH_ADMIN;
	}}
	return polkit.Result.NOT_HANDLED;
}});
"""


ICON = write_shortcut.ICON


def shortcut(directory: Path = PROJECT_DIRECTORY, icon: Path | None = None) -> str:
	"""Le raccourci de l'interface (machincast.shortcut), avec l'icône choisie s'il y en a une qui existe
	(https://github.com/dascritch/machincast/issues/111)."""
	return write_shortcut.write(directory, icon)


def _unit(_configuration: Configuration) -> int:
	# Le texte de l'unité, qu'install.sh installe : ce n'est pas un message, d'où l'écriture directe.
	sys.stdout.write(systemd_unit())
	return 0


def _pipewire_unit(_configuration: Configuration) -> int:
	sys.stdout.write(pipewire_unit())
	return 0


def _wireplumber_unit(_configuration: Configuration) -> int:
	sys.stdout.write(wireplumber_unit())
	return 0


def _tmpfiles(_configuration: Configuration) -> int:
	sys.stdout.write(tmpfiles())
	return 0


def _logrotate(_configuration: Configuration) -> int:
	sys.stdout.write(logrotate())
	return 0


def _wireplumber_service(_configuration: Configuration) -> int:
	sys.stdout.write(wireplumber_service())
	return 0


def _wireplumber_desktop(configuration: Configuration) -> int:
	sys.stdout.write(wireplumber_desktop(configuration.audio))
	return 0


def _purge_unit(_configuration: Configuration) -> int:
	sys.stdout.write(purge_unit(Account.current()))
	return 0


def _purge_timer(_configuration: Configuration) -> int:
	sys.stdout.write(purge_timer())
	return 0


def _rule(_configuration: Configuration) -> int:
	sys.stdout.write(polkit_rule(Account.current()))
	return 0


def _shortcut(configuration: Configuration) -> int:
	sys.stdout.write(shortcut(icon=configuration.interface.icon))
	return 0


def list_items_devices(configuration: Configuration) -> str:
	"""Les périphériques de sortie de la sortie configurée, un par ligne : identifiant, nom, et leur rôle dans la
	configuration (https://github.com/dascritch/machincast/issues/116). Sans aucun, tout ce que voit GStreamer, pour
	comprendre pourquoi."""
	audio = configuration.audio
	roles = {audio.device: _("on air"), audio.preview: _("pre-listen")}
	found_list = audio_outputs.devices(audio.output)
	lines = []
	for p in found_list:
		lines.append(f"{p.identifier}\t{p.name}\t{roles.get(p.identifier, '')}".rstrip("\t"))
	if found_list:
		return "\n".join(lines) + "\n"
	lines = [_("no “{output}” output device; output devices seen by GStreamer:").format(output=audio.output)]
	for appliance in audio_outputs.appliances():
		name = audio_outputs.identifier(appliance)
		shown = (name) or (_("no identifier"))
		lines.append(f"{audio_outputs.appliance_type(appliance)}\t{appliance.get_display_name()}\t{shown}")
	return "\n".join(lines) + "\n"


def _devices(configuration: Configuration) -> int:
	# Une liste à lire, ou à recopier dans audio.device et audio.preview : écrite telle quelle.
	sys.stdout.write(list_items_devices(configuration))
	return 0


ACTIONS = {
	"check": _check,
	"databases": _databases,
	"devices": _devices,
	"logrotate": _logrotate,
	"migrate": _migrate,
	"on-air": _on_air,
	"pipewire-unit": _pipewire_unit,
	"purge-timer": _purge_timer,
	"purge-unit": _purge_unit,
	"rule": _rule,
	"shortcut": _shortcut,
	"tmpfiles": _tmpfiles,
	"unit": _unit,
	"wireplumber-desktop": _wireplumber_desktop,
	"wireplumber-service": _wireplumber_service,
	"wireplumber-unit": _wireplumber_unit,
}


def _options(analyser: argparse.ArgumentParser) -> None:
	analyser.add_argument("action", choices=sorted(ACTIONS), help=_("installation step to run"))


def _run(configuration: Configuration, options: argparse.Namespace) -> int:
	return ACTIONS[options.action](configuration)


def main(arguments: Sequence[str] | None = None) -> int:
	return launch(EXECUTABLE, DESCRIPTION, arguments, _run, _options)


if __name__ == "__main__":
	raise SystemExit(main())
