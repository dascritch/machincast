"""Sorties audio GStreamer (https://github.com/dascritch/machincast/issues/5).

La sortie choisie dans la configuration (audio.sortie) correspond à un élément GStreamer. La sortie
« factice » ne joue aucun son : elle sert aux tests et aux essais.
"""

from dataclasses import dataclass
from datetime import timedelta

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast.configuration import SortieAudio  # noqa: E402


@dataclass(frozen=True)
class Greffon:
	fabrique: str
	"""Nom de la fabrique d'éléments GStreamer."""
	propriete: str | None
	"""Propriété qui désigne le périphérique ; None si la sortie n'en a pas."""
	paquet: str
	"""Paquet Ubuntu qui fournit le greffon."""


GREFFONS: dict[SortieAudio, Greffon] = {
	"alsa": Greffon("alsasink", "device", "gstreamer1.0-alsa"),
	"pulseaudio": Greffon("pulsesink", "device", "gstreamer1.0-pulseaudio"),
	"pipewire": Greffon("pipewiresink", "target-object", "gstreamer1.0-pipewire"),
	"factice": Greffon("fakesink", None, "libgstreamer1.0-0"),
}


TYPES_D_APPAREILS: dict[SortieAudio, tuple[str, ...]] = {
	"pipewire": ("GstPipeWireDevice",),
	"pulseaudio": ("GstPulseDevice",),
	"alsa": ("GstAlsaDevice",),
}
"""Le type GStreamer des périphériques de chaque sortie ; la sortie factice n'en a pas."""
CLASSE_DES_SORTIES = "Audio/Sink"


@dataclass(frozen=True)
class Peripherique:
	"""Un périphérique de sortie du poste (https://github.com/dascritch/machincast/issues/116)."""

	identifiant: str
	"""Ce qu'écrivent audio.peripherique et audio.preecoute : le nom du nœud PipeWire, le nom interne du périphérique
	PulseAudio ou ALSA."""
	nom: str
	"""Ce que le poste en montre."""


def appareils() -> list[Gst.Device]:
	"""Les périphériques de sortie audio que voit GStreamer, toutes sorties confondues, comme gst-device-monitor-1.0
	Audio/Sink : un moniteur de périphériques attend que chaque fournisseur ait donné les siens."""
	Gst.init(None)
	moniteur = Gst.DeviceMonitor.new()
	moniteur.add_filter(CLASSE_DES_SORTIES, None)
	if not moniteur.start():
		return []
	try:
		return list(moniteur.get_devices())
	finally:
		moniteur.stop()


def type_d_appareil(appareil: Gst.Device) -> str:
	return str(appareil.__gtype__.name)


def identifiant(appareil: Gst.Device) -> str | None:
	"""Le nom du nœud PipeWire, sinon le nom interne du périphérique (PulseAudio, ALSA) ; None s'il n'en a pas."""
	proprietes = appareil.get_properties()
	if proprietes is not None:
		nom = proprietes.get_string("node.name")
		if nom:
			return str(nom)
	try:
		interne = appareil.get_property("internal-name")
	except TypeError:
		return None
	return (str(interne)) or (None)


def peripheriques(sortie: SortieAudio) -> list[Peripherique]:
	"""Les périphériques de sortie du poste pour cette sortie, dans l'ordre de GStreamer ; aucun pour la sortie
	factice."""
	types = TYPES_D_APPAREILS.get(sortie, ())
	trouves = []
	for appareil in appareils():
		nom = identifiant(appareil)
		if (type_d_appareil(appareil) in types) and (nom is not None):
			trouves.append(Peripherique(nom, appareil.get_display_name()))
	return trouves


class SortieAudioIndisponible(Exception):
	"""Le greffon GStreamer de la sortie choisie n'est pas installé."""


def creer_sortie(
	sortie: SortieAudio, peripherique: str | None, greffons: dict[SortieAudio, Greffon] = GREFFONS
) -> Gst.Element:
	"""Crée l'élément GStreamer de la sortie, réglé sur le périphérique s'il est donné."""
	Gst.init(None)
	greffon = greffons[sortie]
	element = Gst.ElementFactory.make(greffon.fabrique, None)
	if element is None:
		raise SortieAudioIndisponible(
			f"sortie audio « {sortie} » indisponible : élément GStreamer {greffon.fabrique} introuvable, "
			f"installer le paquet {greffon.paquet}"
		)
	if (peripherique is not None) and (greffon.propriete is not None):
		element.set_property(greffon.propriete, peripherique)
	return element


def jouer_son_de_test(sortie: Gst.Element, duree: timedelta) -> bool:
	"""Joue un son de test sur la sortie ; vrai si la lecture va jusqu'au bout sans erreur."""
	Gst.init(None)
	pipeline = Gst.Pipeline.new("son-de-test")
	source = Gst.ElementFactory.make("audiotestsrc", None)
	conversion = Gst.ElementFactory.make("audioconvert", None)
	if (source is None) or (conversion is None):
		raise SortieAudioIndisponible("audiotestsrc ou audioconvert introuvable, installer gstreamer1.0-plugins-base")
	# 44 100 échantillons par seconde, 1 024 par tampon.
	source.set_property("num-buffers", max(1, round(duree.total_seconds() * 44100 / 1024)))
	for element in (source, conversion, sortie):
		pipeline.add(element)
	source.link(conversion)
	conversion.link(sortie)
	pipeline.set_state(Gst.State.PLAYING)
	bus = pipeline.get_bus()
	assert bus is not None
	message = bus.timed_pop_filtered(
		round((duree.total_seconds() + 5) * Gst.SECOND), Gst.MessageType.EOS | Gst.MessageType.ERROR
	)
	pipeline.set_state(Gst.State.NULL)
	return (message is not None) and (message.type == Gst.MessageType.EOS)
