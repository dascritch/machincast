"""Sorties audio GStreamer (https://github.com/dascritch/machincast/issues/5).

La sortie choisie dans la configuration (audio.sortie) correspond à un élément GStreamer. La sortie
« factice » ne joue aucun son : elle sert aux tests et aux essais.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from machincast.configuration import SortieAudio  # noqa: E402

journal = logging.getLogger(__name__)


@dataclass(frozen=True)
class Greffon:
	fabrique: str
	"""Nom de la fabrique d'éléments GStreamer."""
	propriete: str | None
	"""Propriété qui désigne le périphérique ; None si la sortie n'en a pas."""
	paquet: str
	"""Paquet Ubuntu qui fournit le greffon."""


LECTEUR = "playbin3"
"""Lecteur des voies de l'antenne et de la pré-écoute. Avec GStreamer 1.28, playbin se bloque encore au démarrage
d'un AIFF (36 fois sur 300 en temps réel), playbin3 jamais (python -m tests.mesures_gstreamer,
https://github.com/dascritch/machincast/issues/284)."""

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
DEMARRAGE_DU_MONITEUR = 5.0
"""Secondes laissées au moniteur de périphériques pour démarrer ses fournisseurs
(https://github.com/dascritch/machincast/issues/289)."""


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
	Audio/Sink : un moniteur de périphériques attend que chaque fournisseur ait donné les siens.

	Depuis GStreamer 1.28, start() démarre les fournisseurs dans un fil, qui l'annonce sur le bus du moniteur. Avec
	GStreamer 1.28.2, celui d'Ubuntu 26.04, get_devices() n'attend pas ce fil : la liste serait incomplète, et stop()
	pendant le démarrage corrompt une liste de GLib, ce qui tue le processus
	(https://github.com/dascritch/machincast/issues/289, corrigé par GStreamer 1.28.3 :
	https://gitlab.freedesktop.org/gstreamer/gstreamer/-/merge_requests/11554). La liste attend donc l'annonce ; sans
	elle, le moniteur n'est pas arrêté : mieux vaut un fil qui finit seul qu'une interface qui tombe."""
	Gst.init(None)
	moniteur = Gst.DeviceMonitor.new()
	moniteur.add_filter(CLASSE_DES_SORTIES, None)
	if not moniteur.start():
		return []
	demarre = _attendre_le_demarrage(moniteur)
	trouves = list(moniteur.get_devices())
	if demarre:
		moniteur.stop()
	else:
		journal.warning(
			f"le moniteur de périphériques n'a pas fini de démarrer en {DEMARRAGE_DU_MONITEUR:g} secondes :"
			" la liste des périphériques peut être incomplète"
		)
	return trouves


def _attendre_le_demarrage(moniteur: Gst.DeviceMonitor) -> bool:
	"""Vrai quand le moniteur a démarré ses fournisseurs ; avant GStreamer 1.28, sans message de démarrage, start() ne
	rend la main qu'une fois ses fournisseurs démarrés."""
	demarre = getattr(Gst.MessageType, "DEVICE_MONITOR_STARTED", None)
	if demarre is None:
		return True
	message = moniteur.get_bus().timed_pop_filtered(int(DEMARRAGE_DU_MONITEUR * Gst.SECOND), demarre)
	return message is not None


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


ICONE = "machincast"
"""L'icône que les sorties annoncent au serveur audio : celle de MachinCast, qu'install.sh installe dans le thème
d'icônes du compte (icons/hicolor/512x512/apps/machincast.png). Le réglage du son de Plasma ne montre qu'une icône
du thème."""
CLES_D_ICONE = ("application.icon-name", "application.icon_name")
"""Le nom de l'icône chez PipeWire, puis chez PulseAudio."""


@dataclass(frozen=True)
class Presentation:
	"""Ce qu'une sortie dit d'elle au serveur audio, PipeWire ou PulseAudio
	(https://github.com/dascritch/machincast/issues/296) : sans elle, elle s'y présente sous le nom de l'interpréteur,
	« Python 3.14 »."""

	programme: str
	"""Le nom du programme : client-name, application.name."""
	flux: str
	"""Le nom de son flux : media.name."""


ANTENNE = Presentation("MachinCast lecteur", "Antenne")
PREECOUTE = Presentation("MachinCast interface", "Pré-écoute")
ESSAI = Presentation("MachinCast installation", "Son de test")


def _a_la_propriete(element: Gst.Element, nom: str) -> bool:
	return nom.replace("-", "_") in dir(element.props)


def presenter(sortie: Gst.Element, presentation: Presentation) -> None:
	"""Le nom du programme, celui du flux et l'icône de MachinCast, pour une sortie PipeWire ou PulseAudio ; rien pour
	une sortie qui n'en a pas l'usage (ALSA, factice)."""
	if not _a_la_propriete(sortie, "client-name"):
		return
	sortie.set_property("client-name", presentation.programme)
	proprietes = Gst.Structure.new_empty("proprietes")
	proprietes.set_value("application.name", presentation.programme)
	for cle in CLES_D_ICONE:
		proprietes.set_value(cle, ICONE)
	if _a_la_propriete(sortie, "client-properties"):
		sortie.set_property("client-properties", proprietes.copy())
	proprietes.set_value("media.name", presentation.flux)
	sortie.set_property("stream-properties", proprietes)


class SortieAudioIndisponible(Exception):
	"""Le greffon GStreamer de la sortie choisie n'est pas installé."""


def creer_sortie(
	sortie: SortieAudio,
	peripherique: str | None,
	greffons: dict[SortieAudio, Greffon] = GREFFONS,
	presentation: Presentation | None = None,
) -> Gst.Element:
	"""Crée l'élément GStreamer de la sortie, réglé sur le périphérique s'il est donné, et présenté au serveur audio
	(presenter)."""
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
	if presentation is not None:
		presenter(element, presentation)
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
