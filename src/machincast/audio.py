"""Sorties audio GStreamer (https://github.com/dascritch/machincast/issues/5).

La sortie choisie dans la configuration (audio.output) correspond à un élément GStreamer. La sortie
« factice » ne joue aucun son : elle sert aux tests et aux essais.

Une sortie PipeWire sur un périphérique y est verrouillée (VERROU, https://github.com/dascritch/machincast/issues/345) :
sans verrou, WirePlumber relie au périphérique par défaut du poste, souvent celui de la pré-écoute, un flux dont le
périphérique manque ou disparaît, par exemple quand la carte son change de profil à la mise en veille des écrans.
Verrouillé, le flux attend son périphérique, sans son, et WirePlumber le relie à lui dès qu'il revient.
"""

import logging
import socket
from dataclasses import dataclass
from datetime import timedelta

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, GObject, Gst  # noqa: E402

from machincast import service  # noqa: E402
from machincast.configuration import AudioOutput  # noqa: E402
from machincast.i18n import _  # noqa: E402

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Plugin:
	factory: str
	"""Nom de la fabrique d'éléments GStreamer."""
	property_: str | None
	"""Propriété qui désigne le périphérique ; None si la sortie n'en a pas."""
	package: str
	"""Paquet Ubuntu qui fournit le greffon."""


PLAYER = "playbin3"
"""Lecteur des voies de l'antenne et de la pré-écoute. Avec GStreamer 1.28, playbin se bloque encore au démarrage
d'un AIFF (36 fois sur 300 en temps réel), playbin3 jamais (python -m tests.gstreamer_measures,
https://github.com/dascritch/machincast/issues/284)."""

PLUGINS: dict[AudioOutput, Plugin] = {
	"alsa": Plugin("alsasink", "device", "gstreamer1.0-alsa"),
	"pulseaudio": Plugin("pulsesink", "device", "gstreamer1.0-pulseaudio"),
	"pipewire": Plugin("pipewiresink", "target-object", "gstreamer1.0-pipewire"),
	"dummy": Plugin("fakesink", None, "libgstreamer1.0-0"),
}


APPLIANCE_TYPES: dict[AudioOutput, tuple[str, ...]] = {
	"pipewire": ("GstPipeWireDevice",),
	"pulseaudio": ("GstPulseDevice",),
	"alsa": ("GstAlsaDevice",),
}
"""Le type GStreamer des périphériques de chaque sortie ; la sortie factice n'en a pas."""
OUTPUT_CLASS = "Audio/Sink"
MONITOR_STARTUP = 5.0
"""Secondes laissées au moniteur de périphériques pour démarrer ses fournisseurs
(https://github.com/dascritch/machincast/issues/289)."""


@dataclass(frozen=True)
class Device:
	"""Un périphérique de sortie du poste (https://github.com/dascritch/machincast/issues/116)."""

	identifier: str
	"""Ce qu'écrivent audio.device et audio.preview : le nom du nœud PipeWire, le nom interne du périphérique
	PulseAudio ou ALSA."""
	name: str
	"""Ce que le poste en montre."""


_monitor: Gst.DeviceMonitor | None = None
"""Le moniteur de périphériques du processus, démarré à la première liste et jamais arrêté
(https://github.com/dascritch/machincast/issues/305)."""


def appliances() -> list[Gst.Device]:
	"""Les périphériques de sortie audio que voit GStreamer, toutes sorties confondues, comme gst-device-monitor-1.0
	Audio/Sink, lus sur le moniteur de périphériques du processus.

	Le moniteur n'est jamais arrêté. Avec GStreamer 1.28.2 et PipeWire 1.6.2, ceux d'Ubuntu 26.04, arrêter un moniteur
	pendant que des sorties apparaissent ou disparaissent (une sortie HDMI à la mise en veille d'un écran, une sortie
	qui change par défaut) tue le processus dans un fil de PipeWire (https://github.com/dascritch/machincast/issues/305,
	python -m tests.device_measures --switch) ; arrêter un moniteur qui démarre encore aussi
	(https://github.com/dascritch/machincast/issues/289, corrigé par GStreamer 1.28.3 :
	https://gitlab.freedesktop.org/gstreamer/gstreamer/-/merge_requests/11554). Un moniteur gardé ouvert suit les
	sorties qui vont et viennent.

	Depuis GStreamer 1.28, start() démarre les fournisseurs dans un fil, qui l'annonce sur le bus du moniteur : la
	première liste l'attend, et le journal dit si elle peut être incomplète. Un moniteur qui ne démarre aucun
	fournisseur est oublié : la liste suivante en démarre un autre."""
	global _monitor
	Gst.init(None)
	if _monitor is None:
		monitor = Gst.DeviceMonitor.new()
		monitor.add_filter(OUTPUT_CLASS, None)
		if not monitor.start():
			return []
		if not _wait_startup(monitor):
			log.warning(
				_(
					"the device monitor did not finish starting within {monitor_startup:g} seconds: the device "
					"list may be incomplete"
				).format(monitor_startup=MONITOR_STARTUP)
			)
		_monitor = monitor
	return list(_monitor.get_devices())


def _wait_startup(monitor: Gst.DeviceMonitor) -> bool:
	"""Vrai quand le moniteur a démarré ses fournisseurs ; avant GStreamer 1.28, sans message de démarrage, start() ne
	rend la main qu'une fois ses fournisseurs démarrés."""
	started = getattr(Gst.MessageType, "DEVICE_MONITOR_STARTED", None)
	if started is None:
		return True
	message = monitor.get_bus().timed_pop_filtered(int(MONITOR_STARTUP * Gst.SECOND), started)
	return message is not None


def appliance_type(appliance: Gst.Device) -> str:
	return str(appliance.__gtype__.name)


def identifier(appliance: Gst.Device) -> str | None:
	"""Le nom du nœud PipeWire, sinon le nom interne du périphérique (PulseAudio, ALSA) ; None s'il n'en a pas."""
	properties = appliance.get_properties()
	if properties is not None:
		name = properties.get_string("node.name")
		if name:
			return str(name)
	try:
		internal = appliance.get_property("internal-name")
	except TypeError:
		return None
	return (str(internal)) or (None)


def devices(output: AudioOutput) -> list[Device]:
	"""Les périphériques de sortie du poste pour cette sortie, dans l'ordre de GStreamer ; aucun pour la sortie
	factice."""
	return _devices(output, appliances())


def _devices(output: AudioOutput, appliance_list: list[Gst.Device]) -> list[Device]:
	types = APPLIANCE_TYPES.get(output, ())
	found_list = []
	for appliance in appliance_list:
		name = identifier(appliance)
		if (appliance_type(appliance) in types) and (name is not None):
			found_list.append(Device(name, appliance.get_display_name()))
	return found_list


PIPEWIRE_PROVIDER = "pipewiredeviceprovider"
_service_provider: tuple[Gst.DeviceProvider, socket.socket] | None = None
"""Le fournisseur de périphériques du PipeWire du service, et sa connexion : démarré à la première liste, jamais
arrêté, comme le moniteur du processus (https://github.com/dascritch/machincast/issues/305)."""


def service_appliances() -> list[Gst.Device] | None:
	"""Les périphériques de sortie du PipeWire du service de diffusion (https://github.com/dascritch/machincast/issues/381),
	où joue l'antenne : un fournisseur PipeWire à lui, joint par sa socket, distinct de celui du moniteur du processus,
	qui suit le PipeWire de la session. None sans PipeWire du service joignable."""
	global _service_provider
	Gst.init(None)
	if _service_provider is None:
		try:
			connection = service.connect_pipewire()
		except OSError as error:
			log.warning(_("PipeWire of the broadcast service unreachable: {error}").format(error=error))
			return None
		if connection is None:
			return None
		factory = Gst.DeviceProviderFactory.find(PIPEWIRE_PROVIDER)
		feature = None
		if factory is not None:
			feature = factory.load()
		if not isinstance(feature, Gst.DeviceProviderFactory):
			connection.close()
			return None
		provider = GObject.new(feature.get_device_provider_type())  # type: ignore[arg-type]
		assert isinstance(provider, Gst.DeviceProvider)
		provider.set_property("fd", connection.fileno())
		if not provider.start():
			connection.close()
			return None
		_service_provider = (provider, connection)
	found_list = []
	for appliance in _service_provider[0].get_devices():
		if appliance.has_classes(OUTPUT_CLASS):
			found_list.append(appliance)
	return found_list


def on_air_devices(output: AudioOutput) -> list[Device]:
	"""Les périphériques où l'antenne peut jouer : sur la sortie PipeWire, ceux du PipeWire du service quand il tourne
	(la carte de l'antenne est cachée aux sessions du poste) ; sinon ceux du poste."""
	if output == "pipewire":
		found = service_appliances()
		if found is not None:
			return _devices(output, found)
	return devices(output)


ICON = "machincast"
"""L'icône que les sorties annoncent au serveur audio : celle de MachinCast, qu'install.sh installe dans le thème
d'icônes du compte (icons/hicolor/512x512/apps/machincast.png). Le réglage du son de Plasma ne montre qu'une icône
du thème."""
ICON_KEYS = ("application.icon-name", "application.icon_name")
"""Le nom de l'icône chez PipeWire, puis chez PulseAudio."""


@dataclass(frozen=True)
class Presentation:
	"""Ce qu'une sortie dit d'elle au serveur audio, PipeWire ou PulseAudio
	(https://github.com/dascritch/machincast/issues/296) : sans elle, elle s'y présente sous le nom de l'interpréteur,
	« Python 3.14 »."""

	program: str
	"""Le nom du programme : client-name, application.name."""
	stream: str
	"""Le nom de son flux : media.name."""


ON_AIR = Presentation("MachinCast lecteur", _("On air"))
PREVIEW = Presentation("MachinCast interface", _("Pre-listen"))
TRIAL = Presentation("MachinCast installation", _("Test sound"))
MONITORING = Presentation("MachinCast interface", _("On-air monitoring"))
"""L'écoute de l'antenne, pour le vumètre de l'interface (https://github.com/dascritch/machincast/issues/343)."""


def identify(presentation: Presentation, binary: str) -> None:
	"""Nomme le processus auprès de GLib : le nom de l'application, et le binaire comme nom du programme
	(https://github.com/dascritch/machincast/issues/343). Un client du serveur audio que MachinCast ne présente pas
	lui-même, comme celui qui liste les périphériques, prend ce nom plutôt que celui de l'interpréteur, « python3.14 »."""
	GLib.set_prgname(binary)
	GLib.set_application_name(presentation.program)


def _has_property(item: Gst.Element, name: str) -> bool:
	return name.replace("-", "_") in dir(item.props)


LOCK = ("node.dont-fallback", "node.linger", "node.dont-move")
"""Les propriétés du flux qui le gardent sur son périphérique (https://github.com/dascritch/machincast/issues/345),
lues par WirePlumber (scripts linking/find-defined-target.lua et prepare-link.lua) : jamais de repli sur le périphérique
par défaut ; attendre le périphérique qui manque, au lieu d'envoyer l'erreur « defined target not found » ; aucun
déplacement par les réglages du son du poste (métadonnée target.object)."""
LOCKABLE_FACTORIES = frozenset({"pipewiresink", "pipewiresrc"})


def lock(item: Gst.Element) -> None:
	"""Verrouille sur son périphérique (target-object) un élément PipeWire, en gardant ses autres propriétés de flux ;
	un élément sans périphérique, ou d'une autre sortie, n'en a pas l'usage."""
	factory = item.get_factory()
	if (factory is None) or (factory.get_name() not in LOCKABLE_FACTORIES):
		return
	if not item.get_property("target-object"):
		return
	properties = item.get_property("stream-properties")
	if properties is None:
		properties = Gst.Structure.new_empty("proprietes")
	else:
		properties = properties.copy()
	for key in LOCK:
		properties.set_value(key, True)
	item.set_property("stream-properties", properties)


def present(output: Gst.Element, presentation: Presentation) -> None:
	"""Le nom du programme, celui du flux et l'icône de MachinCast, pour une sortie ou une source PipeWire ou
	PulseAudio, en gardant ses autres propriétés de flux ; rien pour un élément qui n'en a pas l'usage (ALSA,
	factice)."""
	if not _has_property(output, "client-name"):
		return
	output.set_property("client-name", presentation.program)
	client = Gst.Structure.new_empty("proprietes")
	client.set_value("application.name", presentation.program)
	for key in ICON_KEYS:
		client.set_value(key, ICON)
	if _has_property(output, "client-properties"):
		output.set_property("client-properties", client.copy())
	properties = output.get_property("stream-properties")
	if properties is None:
		properties = Gst.Structure.new_empty("proprietes")
	else:
		properties = properties.copy()
	properties.set_value("application.name", presentation.program)
	for key in ICON_KEYS:
		properties.set_value(key, ICON)
	properties.set_value("media.name", presentation.stream)
	output.set_property("stream-properties", properties)


class UnavailableAudioOutput(Exception):
	"""Le greffon GStreamer de la sortie choisie n'est pas installé."""


def create_output(
	output: AudioOutput,
	device: str | None,
	plugins: dict[AudioOutput, Plugin] = PLUGINS,
	presentation: Presentation | None = None,
) -> Gst.Element:
	"""Crée l'élément GStreamer de la sortie, réglé sur le périphérique s'il est donné, présenté au serveur audio
	(presenter), et, pour PipeWire, verrouillé sur son périphérique (verrouiller)."""
	Gst.init(None)
	plugin = plugins[output]
	item = Gst.ElementFactory.make(plugin.factory, None)
	if item is None:
		raise UnavailableAudioOutput(
			_(
				"audio output “{output}” unavailable: GStreamer element {factory} not found, install the "
				"{package} package"
			).format(output=output, factory=plugin.factory, package=plugin.package)
		)
	if (device is not None) and (plugin.property_ is not None):
		item.set_property(plugin.property_, device)
	if presentation is not None:
		present(item, presentation)
	lock(item)
	return item


def play_test_sound(output: Gst.Element, duration: timedelta) -> bool:
	"""Joue un son de test sur la sortie ; vrai si la lecture va jusqu'au bout sans erreur."""
	Gst.init(None)
	pipeline = Gst.Pipeline.new("son-de-test")
	source = Gst.ElementFactory.make("audiotestsrc", None)
	conversion = Gst.ElementFactory.make("audioconvert", None)
	if (source is None) or (conversion is None):
		raise UnavailableAudioOutput(_("audiotestsrc or audioconvert not found, install gstreamer1.0-plugins-base"))
	# 44 100 échantillons par seconde, 1 024 par tampon.
	source.set_property("num-buffers", max(1, round(duration.total_seconds() * 44100 / 1024)))
	for item in (source, conversion, output):
		pipeline.add(item)
	source.link(conversion)
	conversion.link(output)
	pipeline.set_state(Gst.State.PLAYING)
	bus = pipeline.get_bus()
	assert bus is not None
	message = bus.timed_pop_filtered(
		round((duration.total_seconds() + 5) * Gst.SECOND), Gst.MessageType.EOS | Gst.MessageType.ERROR
	)
	pipeline.set_state(Gst.State.NULL)
	return (message is not None) and (message.type == Gst.MessageType.EOS)
