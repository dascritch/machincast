"""Étapes d'installation appelées par install.sh (https://github.com/dascritch/machincast/issues/40).

	python -m machincast.installation databases   --config machincast.toml   socket, base de production, base de test
	python -m machincast.installation migrate     --config machincast.toml   schéma appliqué aux deux bases
	python -m machincast.installation check       --config machincast.toml   GStreamer, greffons, sortie audio
	python -m machincast.installation unit        --config machincast.toml   unité systemd du service de lecture
	python -m machincast.installation pipewire-unit, wireplumber-unit         le PipeWire du service et son WirePlumber
	python -m machincast.installation wireplumber-service, wireplumber-desktop   leur configuration, et celle du bureau
	python -m machincast.installation tmpfiles, logrotate                      répertoires du service, rotation des logs
	python -m machincast.installation rule        --config machincast.toml   règle polkit qui le pilote, et protège le poste
	python -m machincast.installation logind, system-conf                      touches d'alimentation, Ctrl+Alt+Suppr
	python -m machincast.installation tasks-unit, tasks-timer                 tâches régulières : Machin tasks
	python -m machincast.installation indexing-unit, indexing-timer           indexation rapide, toutes les heures
	python -m machincast.installation intranet-unit                           serveur intranet, éteint par défaut
	python -m machincast.installation shortcut    --config machincast.toml   raccourci de l'interface (.desktop)
	python -m machincast.installation devices     --config machincast.toml   périphériques de sortie du poste
	python -m machincast.installation on-air      --config machincast.toml   antenne utilisable par le service
	python -m machincast.installation plugins     --config machincast.toml   install.sh des plugins activés

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
from psycopg.rows import TupleRow

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast import access, crash, personal, power_save, service  # noqa: E402
from machincast import audio as audio_outputs  # noqa: E402
from machincast import log as log_directory  # noqa: E402
from machincast import plugins as plugin_registry  # noqa: E402
from machincast import shortcut as write_shortcut  # noqa: E402
from machincast.audio import PLUGINS, TRIAL, Plugin, UnavailableAudioOutput, create_output  # noqa: E402
from machincast.cli import launch  # noqa: E402
from machincast.configuration import PROJECT_DIRECTORY, Audio, AudioOutput, Configuration  # noqa: E402
from machincast.database import apply_migrations, url_yoyo  # noqa: E402
from machincast.i18n import _  # noqa: E402
from machincast.indexer.indexer import ONGOING_CODE  # noqa: E402
from machincast.service import INDEXING_UNIT, TASKS_UNIT, UNIT  # noqa: E402

EXECUTABLE = "machincast.installation"
DESCRIPTION = _("MachinCast installation steps, called by install.sh.")
FAILURE_CODE = 1
TASKS_STATE = "machincast-tasks"
"""Le répertoire d'état des tâches régulières, /var/lib/machincast-tasks, que systemd crée au compte de MachinCast :
machincast.schedule y note le dernier passage de la tâche quotidienne."""
TASKS_CHECK = "*:0/15"
"""Tous les quarts d'heure, Machin tasks lance ce qui est dû : la tâche quotidienne ne passe que due
(machincast.schedule). Changer cette périodicité ne change pas les tâches."""

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
	"""Paquet Ubuntu qui fournit les éléments, parmi les prérequis de AGENTS.md."""


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


def plugin_installers(configuration: Configuration) -> list[Path]:
	"""L'install.sh de chaque plugin activé qui en a un, dans l'ordre de [plugins] enabled : install.sh les lance,
	après la base et ses rôles (https://github.com/dascritch/machincast/issues/587), pour créer leurs tables."""
	found_list = {}
	for found in plugin_registry.discover(plugin_registry.directory(configuration)):
		found_list[found.name] = found
	scripts = []
	for name in configuration.plugins.enabled:
		enabled = found_list.get(name)
		if (enabled is not None) and (plugin_registry.install_script(enabled).is_file()):
			scripts.append(plugin_registry.install_script(enabled))
	return scripts


def _plugins(configuration: Configuration) -> int:
	# Données lues par install.sh, un install.sh par ligne : ce n'est pas un message, d'où l'écriture directe.
	for script in plugin_installers(configuration):
		sys.stdout.write(f"{script}\n")
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
	"sound card in Machin interface, File → Broadcast service settings…, Audio page, then run ./install.sh "
	"--service again"
)

PULSEAUDIO_ON_AIR = _(
	"on air on the PulseAudio output: the broadcast service plays through its own PipeWire; choose the "
	"PipeWire output in Machin interface, File → Broadcast service settings…, Audio page, then run ./install.sh --service again"
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


SERVICE_ACCOUNT = service.ACCOUNT
"""Le compte système du service de diffusion, et son groupe, où install.sh --service ajoute le compte de MachinCast
(https://github.com/dascritch/machincast/issues/381) : les mêmes noms dans install.sh."""
SERVICE_RUNTIME = service.RUNTIME
"""Le répertoire d'exécution du service : la socket de son PipeWire, pipewire-0, et sa socket d'état. Partagé avec le
groupe (2770), recréé à chaque démarrage du poste par tmpfiles.d."""
INTRANET_ACCOUNT = service.INTRANET_ACCOUNT
"""Le compte système du serveur intranet, et son groupe (https://github.com/dascritch/machincast/issues/549) : les
mêmes noms dans install.sh."""
INTRANET_RUNTIME = service.INTRANET_RUNTIME
"""Le répertoire de la socket que Machin player réserve au serveur intranet : au compte du service, qui y crée la
socket, et au groupe du serveur intranet, qui la joint (2750)."""
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
	crash, au compte du service et à son groupe ; la socket et le journal du serveur intranet."""
	lines = [
		"# Directories of the MachinCast broadcast service (https://github.com/dascritch/machincast/issues/381).",
		HEADER,
	]
	for directory in (SERVICE_RUNTIME, log_directory.DIRECTORY, crash.DIRECTORY):
		lines.append(f"d {directory} {SERVICE_GROUP_MODE} {SERVICE_ACCOUNT} {SERVICE_ACCOUNT} -")
	# La socket que Machin player réserve au serveur intranet, que seul son groupe joint
	# (https://github.com/dascritch/machincast/issues/549).
	lines.append(f"d {INTRANET_RUNTIME} 2750 {SERVICE_ACCOUNT} {INTRANET_ACCOUNT} -")
	# Le journal du serveur intranet, à son compte et au groupe du service, qui le lit et le fait tourner (logrotate,
	# copytruncate) ; son compte, hors du groupe, ne fait que traverser le répertoire des logs, sans le lister ni lire
	# les autres journaux (https://github.com/dascritch/machincast/issues/578).
	lines.append(f"f {INTRANET_LOG} 0660 {INTRANET_ACCOUNT} {SERVICE_ACCOUNT} -")
	lines.append(f"a+ {log_directory.DIRECTORY} - - - - u:{INTRANET_ACCOUNT}:--x")
	return "\n".join(lines) + "\n"


PROFILE = Path("/etc/profile.d/machincast.sh")
"""Le script que lit chaque nouveau shell de connexion, quand le service est installé
(https://github.com/dascritch/machincast/issues/517) : le même chemin dans install.sh (FICHIER_PROFIL)."""


def profile() -> str:
	"""Le script de session : dans un shell interactif, sur un terminal, la bannière de Machin banner, qui dit aussi si
	Machin player tourne. Statique : le numéro de version, lui, vient de Machin banner, pas du fichier, que install.sh
	ne réécrit donc pas à chaque version."""
	return f"""# Banner of MachinCast at each new shell (https://github.com/dascritch/machincast/issues/517).
{HEADER}
case "$-" in
	*i*)
		if [ -t 1 ] && command -v Machin >/dev/null 2>&1; then
			Machin banner
		fi
		;;
esac
"""


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


def hidden_nodes(audio: Audio) -> list[str]:
	"""Les nœuds que les sessions du poste ne voient pas, sur la sortie PipeWire : la carte de l'antenne, puis les entrées
	audio (https://github.com/dascritch/machincast/issues/622) ; aucun sur une autre sortie."""
	if audio.output != "pipewire":
		return []
	found = []
	output, device = audio.on_air()
	if (output == "pipewire") and (device is not None):
		found.append(device)
	for audio_input in audio.inputs:
		found.append(audio_input.device)
	return found


def wireplumber_desktop(audio: Audio) -> str:
	"""Le fragment du WirePlumber des sessions du poste : la carte de l'antenne et les entrées audio y sont cachées,
	elles sont au service ; deux PipeWire n'ouvrent pas la même carte en même temps. Sans antenne sur une carte
	PipeWire ni entrée, il ne cache rien. Il est réécrit, avec les entrées, par machincast.input_reservation."""
	head = f"""# MachinCast: the on-air card and the audio inputs belong to the broadcast service
# (https://github.com/dascritch/machincast/issues/381, https://github.com/dascritch/machincast/issues/622).
{HEADER}
"""
	nodes = hidden_nodes(audio)
	if not nodes:
		return head + "# No on-air card nor audio input to hide.\n"
	matches = []
	for device in nodes:
		name = device.replace("\\", "\\\\").replace('"', '\\"')
		matches.append(f'{{ node.name = "{name}" }}')
	return (
		head
		+ f"""monitor.alsa.rules = [
	{{
		matches = [ {" ".join(matches)} ]
		actions = {{ update-props = {{ node.disabled = true }} }}
	}}
]
"""
	)


def tasks_unit(account: Account, directory: Path = PROJECT_DIRECTORY) -> str:
	"""L'unité des tâches régulières (https://github.com/dascritch/machincast/issues/455), sous le compte de MachinCast,
	propriétaire de la base : elle lance Machin tasks, qui fait ce qui est dû, aujourd'hui la tâche quotidienne (purge
	puis audit complet). Ce que fait chaque passage est dans le wrapper : ses tâches peuvent changer sans toucher à
	l'unité. Son répertoire d'état garde le dernier passage de chaque tâche. Son minuteur la lance ; elle n'a pas de
	section Install."""
	return f"""# MachinCast regular tasks (https://github.com/dascritch/machincast/issues/455).
# Installed by install.sh --service; do not edit here, run install.sh --service again. The tasks are those of
# Machin tasks; the hour of the daily tasks is set by schedule.daily in machincast.toml, or in the interface: this
# unit does not change.

[Unit]
Description=MachinCast: regular tasks (Machin tasks)
After=postgresql.service

[Service]
Type=oneshot
User={account.name}
Group={account.group}
WorkingDirectory={directory}
StateDirectory={TASKS_STATE}
ExecStart={directory}/bin/Machin tasks
SyslogIdentifier=machincast-tasks
"""


def tasks_timer() -> str:
	"""Le minuteur des tâches régulières : tous les quarts d'heure ; chaque tâche ne passe que quand elle est due."""
	return f"""# MachinCast regular tasks, every quarter of an hour (https://github.com/dascritch/machincast/issues/455).
# Installed by install.sh --service; do not edit here, run install.sh --service again.

[Unit]
Description=MachinCast: regular tasks, every quarter of an hour

[Timer]
OnCalendar={TASKS_CHECK}
Unit={TASKS_UNIT}

[Install]
WantedBy=timers.target
"""


def indexing_unit(account: Account, directory: Path = PROJECT_DIRECTORY) -> str:
	"""L'unité de l'indexation rapide (https://github.com/dascritch/machincast/issues/455), sous le compte de
	MachinCast. Une indexation rapide déjà en cours, lancée depuis l'interface, donne le code 3 : pas un échec. systemd
	ne la relance pas tant que la précédente tourne."""
	return f"""# MachinCast quick indexing (https://github.com/dascritch/machincast/issues/455).
# Installed by install.sh --service; do not edit here, run install.sh --service again.

[Unit]
Description=MachinCast: quick indexing (Machin indexer)
After=postgresql.service

[Service]
Type=oneshot
User={account.name}
Group={account.group}
WorkingDirectory={directory}
ExecStart={directory}/bin/Machin indexer
SuccessExitStatus={ONGOING_CODE}
SyslogIdentifier=machincast-indexing
"""


INTRANET_STATE = "machincast-intranet"
"""Le répertoire d'état du serveur intranet, /var/lib/machincast-intranet : son certificat généré."""
INTRANET_LOG = log_directory.DIRECTORY / "Machin_intranet.log"
"""Le journal du serveur intranet (machincast.intranet.__main__.EXECUTABLE), préparé par tmpfiles à son compte : il ne
peut ni lister ni écrire /var/log/machincast (https://github.com/dascritch/machincast/issues/578)."""
INTRANET_DISABLED = 4
"""Le code de Machin intranet éteint (machincast.intranet.__main__.DISABLED_CODE)."""


INTRANET_HARDENING = (
	"NoNewPrivileges=yes",
	"PrivateTmp=yes",
	"PrivateDevices=yes",
	"ProtectSystem=strict",
	"ProtectHome=yes",
	"ProtectKernelTunables=yes",
	"ProtectKernelModules=yes",
	"ProtectKernelLogs=yes",
	"ProtectControlGroups=yes",
	"ProtectClock=yes",
	"ProtectHostname=yes",
	"ProtectProc=invisible",
	# Dans /proc, seuls les processus : ni /proc/stat, ni /proc/sys, ni les autres réglages du noyau, que le serveur ne
	# lit pas ; ip lit les adresses par netlink (https://github.com/dascritch/machincast/issues/556).
	"ProcSubset=pid",
	"CapabilityBoundingSet=",
	"AmbientCapabilities=",
	"RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK",
	"RestrictNamespaces=yes",
	"RestrictRealtime=yes",
	"RestrictSUIDSGID=yes",
	"LockPersonality=yes",
	"MemoryDenyWriteExecute=yes",
	"SystemCallArchitectures=native",
	"SystemCallFilter=@system-service",
	"SystemCallFilter=~@privileged @resources",
	# ip, qui lit les adresses du poste, lâche ses capacités au démarrage par capset (drop_cap), même sans en avoir :
	# interdit par @privileged, il était tué par SIGSYS (https://github.com/dascritch/machincast/issues/556). capset ne
	# peut que retirer des capacités, et l'unité n'en donne aucune.
	"SystemCallFilter=capset",
	"UMask=0077",
)
"""Ce que le serveur intranet, exposé au réseau, ne peut pas faire (https://github.com/dascritch/machincast/issues/549) :
tout le système en lecture seule, sauf son répertoire d'état ; aucun répertoire personnel ; aucune capacité ; pas
d'autres familles de sockets que Unix, IP et netlink (ip address, pour les adresses du poste) ; mesuré par
systemd-analyze security machincast-intranet."""


def intranet_unit(directory: Path = PROJECT_DIRECTORY) -> str:
	"""L'unité du serveur intranet (https://github.com/dascritch/machincast/issues/538), sous son propre compte,
	machincast-intranet, hors du groupe du service de diffusion, dont le rôle PostgreSQL n'endosse que
	machincast_intranet (https://github.com/dascritch/machincast/issues/549). Elle démarre avec le poste ; Machin intranet
	s'arrête aussitôt, code 4, tant que intranet.enabled n'est pas vrai, sans que systemd le relance. La page
	« Intranet » des paramètres du service la redémarre ou l'arrête, ce que permet la règle polkit. Son répertoire
	d'état garde le certificat généré ; elle ne peut écrire nulle part ailleurs (INTRANET_HARDENING), sauf son journal
	(INTRANET_LOG)."""
	hardening = "\n".join(INTRANET_HARDENING)
	return f"""# MachinCast intranet server (https://github.com/dascritch/machincast/issues/538).
# Installed by install.sh --service; do not edit here, run install.sh --service again. It is switched on by
# intranet.enabled in machincast.toml, or in the interface: this unit does not change.

[Unit]
Description=MachinCast: intranet server, HTTPS only (Machin intranet)
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=exec
User={INTRANET_ACCOUNT}
Group={INTRANET_ACCOUNT}
WorkingDirectory={directory}
StateDirectory={INTRANET_STATE}
StateDirectoryMode=0700
# Son journal, que prépare tmpfiles ; sans lui, l'unité démarre quand même
# (https://github.com/dascritch/machincast/issues/578).
ReadWritePaths=-{INTRANET_LOG}
ExecStart={directory}/bin/Machin intranet
SuccessExitStatus={INTRANET_DISABLED}
RestartPreventExitStatus={INTRANET_DISABLED}
Restart=on-failure
RestartSec=10
{hardening}
SyslogIdentifier=machincast-intranet

[Install]
WantedBy=multi-user.target
"""


def indexing_timer() -> str:
	"""Le minuteur de l'indexation rapide : toutes les heures ; une heure manquée, poste éteint, passe à son démarrage."""
	return f"""# MachinCast quick indexing, every hour (https://github.com/dascritch/machincast/issues/455).
# Installed by install.sh --service; do not edit here, run install.sh --service again.

[Unit]
Description=MachinCast: quick indexing, every hour

[Timer]
OnCalendar=hourly
Persistent=true
Unit={INDEXING_UNIT}

[Install]
WantedBy=timers.target
"""


POWER_ACTIONS = (
	"org.freedesktop.login1.power-off",
	"org.freedesktop.login1.power-off-multiple-sessions",
	"org.freedesktop.login1.power-off-ignore-inhibit",
	"org.freedesktop.login1.reboot",
	"org.freedesktop.login1.reboot-multiple-sessions",
	"org.freedesktop.login1.reboot-ignore-inhibit",
	"org.freedesktop.login1.halt",
	"org.freedesktop.login1.halt-multiple-sessions",
	"org.freedesktop.login1.halt-ignore-inhibit",
	"org.freedesktop.login1.suspend",
	"org.freedesktop.login1.suspend-multiple-sessions",
	"org.freedesktop.login1.suspend-ignore-inhibit",
	"org.freedesktop.login1.hibernate",
	"org.freedesktop.login1.hibernate-multiple-sessions",
	"org.freedesktop.login1.hibernate-ignore-inhibit",
)
"""Les actions de logind qui éteignent, redémarrent, arrêtent ou mettent en veille le poste : une session active les a
sans mot de passe sur Ubuntu, écran de connexion compris (allow_active de org.freedesktop.login1.policy) ; sur un poste
d'antenne, elles demandent l'authentification d'un administrateur (https://github.com/dascritch/machincast/issues/448)."""


ADMINISTRATOR_GROUPS = ("sudo", "admin")
"""Les groupes des administrateurs d'Ubuntu : admin, d'avant 12.04, que polkit reconnaît encore."""


def _administrators() -> str:
	"""La condition, en ES5, d'un compte administrateur."""
	tests = []
	for group in ADMINISTRATOR_GROUPS:
		tests.append(f'subject.isInGroup("{group}")')
	return " || ".join(tests)


def polkit_rule(account: Account) -> str:
	"""La règle polkit du service de lecture : son compte le démarre, l'arrête ou le redémarre, avec son propre mot de
	passe s'il est administrateur, sinon celui d'un administrateur (https://github.com/dascritch/machincast/issues/558),
	et de même le serveur intranet
	(https://github.com/dascritch/machincast/issues/538) ; rien d'autre, ni sur une autre unité. Elle protège aussi le poste :
	l'éteindre, le redémarrer ou le mettre en veille demande l'authentification d'un administrateur, à tout compte
	(https://github.com/dascritch/machincast/issues/448). Elle donne au compte les paramètres du service, dans Machin
	interface, de la même façon (https://github.com/dascritch/machincast/issues/603). Elle est en ES5, comme Duktape, le
	moteur de polkitd."""
	quoted = []
	for action in POWER_ACTIONS:
		quoted.append(f'"{action}"')
	actions = ",\n\t\t".join(quoted)
	return f"""// Control of the MachinCast broadcast service (https://github.com/dascritch/machincast/issues/22).
// Installed by install.sh --service; do not edit here, run install.sh --service again.

// An administrator gives their own password, without choosing among the administrators of the computer; another
// account, the password of an administrator (https://github.com/dascritch/machincast/issues/558).
function byAdministrator(subject) {{
	if ({_administrators()}) {{
		return polkit.Result.AUTH_SELF_KEEP;
	}}
	return polkit.Result.AUTH_ADMIN;
}}

polkit.addRule(function (action, subject) {{
	if ((action.id == "org.freedesktop.systemd1.manage-units")
		&& (["{UNIT}", "{service.INTRANET_UNIT}"].indexOf(action.lookup("unit")) >= 0)
		&& (["start", "stop", "restart"].indexOf(action.lookup("verb")) >= 0) && (subject.user == "{account.name}")) {{
		return byAdministrator(subject);
	}}
	return polkit.Result.NOT_HANDLED;
}});

// The on-air computer: powering off, rebooting, halting or suspending it asks for an administrator's password, from
// any account and from the login screen (https://github.com/dascritch/machincast/issues/448).
polkit.addRule(function (action, subject) {{
	if ([
		{actions}
	].indexOf(action.id) >= 0) {{
		return byAdministrator(subject);
	}}
	return polkit.Result.NOT_HANDLED;
}});

// The settings of the broadcast service, in Machin interface: an administrator's password, their own for an
// administrator (https://github.com/dascritch/machincast/issues/603).
polkit.addRule(function (action, subject) {{
	if ((action.id == "{service.SERVICE_SETTINGS_ACTION}") && (subject.user == "{account.name}")) {{
		return byAdministrator(subject);
	}}
	return polkit.Result.NOT_HANDLED;
}});
"""


POLICY_FILE = Path("/usr/share/polkit-1/actions") / f"{service.SERVICE_SETTINGS_ACTION}.policy"
"""La politique polkit de l'action des paramètres du service (https://github.com/dascritch/machincast/issues/603) : polkit
ne lit les actions que dans ce répertoire ; install.sh --service y installe ce seul fichier, sans toucher aux droits de
l'arborescence."""


def polkit_policy() -> str:
	"""La politique polkit de l'action des paramètres du service : le mot de passe d'un administrateur, gardé quelques
	minutes, pour toute session ; la règle du service le rend propre à un administrateur
	(https://github.com/dascritch/machincast/issues/603)."""
	return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<!-- Installed by install.sh, with its service option (https://github.com/dascritch/machincast/issues/603); do not edit here. -->
<policyconfig>
  <vendor>MachinCast</vendor>
  <vendor_url>https://github.com/dascritch/machincast</vendor_url>
  <action id="{service.SERVICE_SETTINGS_ACTION}">
    <description>Set the MachinCast broadcast service</description>
    <message>Authentication is required to set the MachinCast broadcast service</message>
    <defaults>
      <allow_any>auth_admin_keep</allow_any>
      <allow_inactive>auth_admin_keep</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
  </action>
</policyconfig>
"""


LOGIND_KEYS = (
	"HandlePowerKey",
	"HandlePowerKeyLongPress",
	"HandleRebootKey",
	"HandleRebootKeyLongPress",
	"HandleSuspendKey",
	"HandleSuspendKeyLongPress",
	"HandleHibernateKey",
	"HandleHibernateKeyLongPress",
	"HandleLidSwitch",
	"HandleLidSwitchExternalPower",
	"HandleLidSwitchDocked",
)
"""Ce que logind fait seul, sans polkit, à l'appui d'une touche ou à la fermeture du capot : ignoré sur un poste
d'antenne (https://github.com/dascritch/machincast/issues/448)."""


def logind() -> str:
	"""Le fragment de logind du service : les touches d'alimentation, de redémarrage et de veille, et le capot, ne
	coupent plus l'antenne. Dans une session, le bureau garde la main sur la touche, et passe par logind, donc par la
	règle polkit ; un appui long, que le matériel traite seul, éteint toujours."""
	settings = ""
	for key in LOGIND_KEYS:
		settings += f"{key}=ignore\n"
	return f"""# The MachinCast on-air computer: keys and lid never power off, reboot or suspend it
# (https://github.com/dascritch/machincast/issues/448).
# Installed by install.sh --service; do not edit here, run install.sh --service again.
[Login]
{settings}"""


def system_conf() -> str:
	"""Le fragment de systemd du service : sept Ctrl+Alt+Suppr en deux secondes, en console, ne forcent plus le
	redémarrage ; install.sh --service masque aussi ctrl-alt-del.target, qu'un seul appui lance
	(https://github.com/dascritch/machincast/issues/448)."""
	return """# The MachinCast on-air computer: a burst of Ctrl+Alt+Del on the console never forces a reboot
# (https://github.com/dascritch/machincast/issues/448).
# Installed by install.sh --service; do not edit here, run install.sh --service again.
[Manager]
CtrlAltDelBurstAction=none
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


def _profile(_configuration: Configuration) -> int:
	sys.stdout.write(profile())
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


def _tasks_unit(_configuration: Configuration) -> int:
	sys.stdout.write(tasks_unit(Account.current()))
	return 0


def _tasks_timer(_configuration: Configuration) -> int:
	sys.stdout.write(tasks_timer())
	return 0


def _indexing_unit(_configuration: Configuration) -> int:
	sys.stdout.write(indexing_unit(Account.current()))
	return 0


def _intranet_unit(_configuration: Configuration) -> int:
	sys.stdout.write(intranet_unit())
	return 0


def _indexing_timer(_configuration: Configuration) -> int:
	sys.stdout.write(indexing_timer())
	return 0


def _rule(_configuration: Configuration) -> int:
	sys.stdout.write(polkit_rule(Account.current()))
	return 0


def _policy(_configuration: Configuration) -> int:
	sys.stdout.write(polkit_policy())
	return 0


def _logind(_configuration: Configuration) -> int:
	sys.stdout.write(logind())
	return 0


def _system_conf(_configuration: Configuration) -> int:
	sys.stdout.write(system_conf())
	return 0


def _power_save(_configuration: Configuration) -> int:
	sys.stdout.write(power_save.modprobe())
	return 0


def _usb_power(_configuration: Configuration) -> int:
	sys.stdout.write(power_save.usb_rule())
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


def _owner_connection(configuration: Configuration) -> psycopg.Connection[TupleRow] | None:
	"""La base de production, avec le compte de MachinCast, propriétaire, sans rôle : comme la purge."""
	database = configuration.database
	try:
		return psycopg.connect(host=str(database.socket), dbname=database.production)
	except psycopg.OperationalError as error:
		log.error(
			_("database unreachable ({name} through {socket}): {error}").format(
				name=database.production, socket=database.socket, error=error
			)
		)
		return None


def _personal_sounds(configuration: Configuration) -> int:
	"""Les répertoires de banque et les fichiers ajoutés de la base qui sont dans un répertoire personnel, un par ligne
	(https://github.com/dascritch/machincast/issues/381) ; rien s'il n'y en a pas."""
	connection = _owner_connection(configuration)
	if connection is None:
		return FAILURE_CODE
	with connection:
		found = personal.find(connection)
	for path in [*found.directories, *found.files]:
		sys.stdout.write(f"{path}\n")
	return 0


def _move_personal_sounds(configuration: Configuration) -> int:
	"""Les déplace dans le répertoire d'accueil des sonores, et la base suit ; ceux d'un autre compte restent."""
	connection = _owner_connection(configuration)
	if connection is None:
		return FAILURE_CODE
	with connection:
		moves = personal.plan(personal.find(connection), access.welcome())
		foreign = personal.foreign(moves)
		for path in foreign:
			log.warning(_("{path}: not moved, it belongs to another account, or is missing").format(path=path))
		kept = []
		for item in moves:
			if item.source not in foreign:
				kept.append(item)
		try:
			personal.move(connection, kept)
		except (OSError, psycopg.Error) as error:
			log.error(_("sound files not moved, all are back in place: {error}").format(error=error))
			return FAILURE_CODE
	log.info(_("{count} paths moved to {welcome}").format(count=len(kept), welcome=access.welcome()))
	return int(foreign != [])


def _forget_personal_sounds(configuration: Configuration) -> int:
	"""Les retire de la base, sans toucher aucun fichier."""
	connection = _owner_connection(configuration)
	if connection is None:
		return FAILURE_CODE
	with connection:
		found = personal.find(connection)
		personal.forget(connection, found)
	log.info(
		_("{count} paths removed from the database, no file touched").format(
			count=len(found.directories) + len(found.files)
		)
	)
	return 0


ACTIONS = {
	"check": _check,
	"tasks-timer": _tasks_timer,
	"tasks-unit": _tasks_unit,
	"databases": _databases,
	"devices": _devices,
	"indexing-timer": _indexing_timer,
	"indexing-unit": _indexing_unit,
	"intranet-unit": _intranet_unit,
	"logind": _logind,
	"logrotate": _logrotate,
	"migrate": _migrate,
	"plugins": _plugins,
	"move-personal-sounds": _move_personal_sounds,
	"forget-personal-sounds": _forget_personal_sounds,
	"personal-sounds": _personal_sounds,
	"on-air": _on_air,
	"pipewire-unit": _pipewire_unit,
	"power-save": _power_save,
	"profile": _profile,
	"policy": _policy,
	"rule": _rule,
	"shortcut": _shortcut,
	"system-conf": _system_conf,
	"tmpfiles": _tmpfiles,
	"unit": _unit,
	"usb-power": _usb_power,
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
