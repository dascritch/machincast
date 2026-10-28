"""Moniteur de la sortie d'antenne (https://github.com/dascritch/machincast/issues/24, spec § 2 et § 8.1).

Les niveaux de l'antenne se lisent sur le port de monitoring du périphérique de l'antenne (audio.peripherique), sans
rien demander à Machin lecture :

- PipeWire : pipewiresrc sur le nœud de l'antenne, qui en capture la sortie (stream.capture.sink) ;
- PulseAudio : pulsesrc sur son « .monitor » ;
- ALSA n'a pas de port de monitoring : le moniteur est indisponible, sans erreur ;
- la sortie factice des tests et des essais : un signal de test en stéréo (SIGNAL_FACTICE).

Le port est capté en stéréo (CANAUX) : sans contrainte, pipewiresrc et pulsesrc se contentent d'un canal, et le
VU-mètre n'en montrerait qu'un.

Le pipeline (port ! audioconvert ! level ! fakesink) ne joue rien ; son bus est relevé par un minuteur de Qt. Le
moniteur donne le VU (RMS) et la crête de chaque canal, et deux voyants : le blanc, après DUREE_DU_BLANC secondes
sous SEUIL_DU_BLANC, et la saturation, dès qu'une crête atteint SEUIL_DE_SATURATION, gardée MAINTIEN_DE_SATURATION
secondes. Un port qui ne s'ouvre pas est réessayé toutes les REESSAI millisecondes. La pré-écoute écoute le même port
(machincast.interface.preecoute).

Un port qui ne donne plus aucun relevé pendant DELAI_DU_GEL secondes, depuis son ouverture ou son dernier relevé,
est gelé (https://github.com/dascritch/machincast/issues/311) : au retour d'une session verrouillée et d'un écran
éteint, un flux PipeWire peut cesser de donner du son, sans erreur ni fin. Le moniteur l'arrête, ce qui efface ses
niveaux : le VU-mètre ne reste pas figé sur les derniers. Il le dit, et le rouvre comme un port qui ne s'ouvre pas.
"""

import time
from collections.abc import Callable

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402
from PySide6.QtCore import QObject, QTimer, Signal  # noqa: E402

from machincast.configuration import Audio  # noqa: E402
from machincast.interface import etats  # noqa: E402

SIGNAL_FACTICE = "audiotestsrc is-live=true wave=sine volume=0.1"
"""Le port de monitoring de la sortie factice : un signal de test, que les scénarios choisissent."""
SEUIL_DU_BLANC = -50.0
DUREE_DU_BLANC = 5.0
SEUIL_DE_SATURATION = -1.0
MAINTIEN_DE_SATURATION = 3.0
RELEVE = 50
"""Millisecondes entre deux relèves du bus."""
REESSAI = 5000
"""Millisecondes avant de rouvrir un port de monitoring qui ne s'est pas ouvert, ou qui s'est fermé."""
INTERVALLE_DES_NIVEAUX = 50 * Gst.MSECOND
DELAI_DU_GEL = 3.0
"""Secondes sans relevé au-delà desquelles le port de monitoring est gelé
(https://github.com/dascritch/machincast/issues/311)."""
GELE = f"Indisponible : le port de monitoring ne donne plus rien depuis {DELAI_DU_GEL:g} secondes."
CANAUX = "audio/x-raw,channels=2"
"""Ce que donne le port de monitoring : les deux canaux de l'antenne."""
SANS_ALSA = "Indisponible avec la sortie ALSA, qui n'a pas de port de monitoring."
SANS_ANTENNE = "Indisponible : périphérique de l'antenne à renseigner."


class Indisponible(Exception):
	"""Le port de monitoring ne peut pas s'ouvrir : le message dit pourquoi."""


def nom_du_port(audio: Audio) -> str:
	"""Ce que le port de monitoring écoute, pour l'infobulle du VU-mètre et la source de la pré-écoute."""
	peripherique = (audio.peripherique) or ("périphérique à renseigner")
	if audio.sortie == "factice":
		return "sortie factice, signal de test"
	if audio.sortie == "pulseaudio":
		return f"PulseAudio, {peripherique}.monitor"
	if audio.sortie == "pipewire":
		return f"PipeWire, {peripherique}"
	return f"ALSA, {peripherique}"


def verifier(audio: Audio) -> None:
	"""Lève Indisponible si l'antenne n'a pas de port de monitoring."""
	if audio.sortie == "alsa":
		raise Indisponible(SANS_ALSA)
	if (audio.sortie != "factice") and (audio.peripherique is None):
		raise Indisponible(SANS_ANTENNE)


def source_du_moniteur(audio: Audio) -> Gst.Element:
	"""L'élément qui donne le son de l'antenne ; lève Indisponible s'il n'y en a pas."""
	Gst.init(None)
	verifier(audio)
	if audio.sortie == "factice":
		try:
			return Gst.parse_bin_from_description(f"{SIGNAL_FACTICE} ! capsfilter caps={CANAUX}", True)
		except GLib.Error as erreur:
			raise Indisponible(f"Indisponible : {erreur.message}") from None
	if audio.sortie == "pulseaudio":
		source = _element("pulsesrc")
		source.set_property("device", f"{audio.peripherique}.monitor")
		return _en_stereo(source)
	source = _element("pipewiresrc")
	source.set_property("target-object", audio.peripherique)
	proprietes, _fin = Gst.Structure.from_string("props, stream.capture.sink=(boolean)true")
	source.set_property("stream-properties", proprietes)
	return _en_stereo(source)


def _en_stereo(source: Gst.Element) -> Gst.Element:
	"""La source, suivie d'un filtre qui lui demande les deux canaux de l'antenne."""
	bloc = Gst.Bin.new(None)
	filtre = _element("capsfilter")
	filtre.set_property("caps", Gst.Caps.from_string(CANAUX))
	bloc.add(source)
	bloc.add(filtre)
	source.link(filtre)
	sortie = filtre.get_static_pad("src")
	assert sortie is not None
	bloc.add_pad(Gst.GhostPad.new("src", sortie))
	return bloc


def _element(fabrique: str) -> Gst.Element:
	element = Gst.ElementFactory.make(fabrique, None)
	if element is None:
		raise Indisponible(f"Indisponible : élément GStreamer {fabrique} introuvable.")
	return element


class Moniteur(QObject):
	"""Les niveaux de l'antenne, relevés tant qu'il tourne."""

	change = Signal()
	"""Nouveaux niveaux, voyants, ou disponibilité."""

	def __init__(
		self, audio: Audio | None, parent: QObject | None = None, horloge: Callable[[], float] = time.monotonic
	) -> None:
		super().__init__(parent)
		self.audio = audio
		self.horloge = horloge
		self._pipeline: Gst.Pipeline | None = None
		self._pilote: etats.Pilote | None = None
		"""Les changements d'état du port, hors du fil de l'interface (https://github.com/dascritch/machincast/issues/259)."""
		self._niveau: Gst.Element | None = None
		self.niveaux: list[float] = []
		self.cretes: list[float] = []
		self.indisponible: str | None = None
		self.blanc = False
		self.saturation = False
		self._son_depuis: float | None = None
		"""Dernier instant où un canal dépassait le seuil du blanc."""
		self._saturation_depuis: float | None = None
		self._releve_le: float | None = None
		"""Instant de l'ouverture du port, puis de son dernier relevé : pour constater un port gelé."""
		self._releve = QTimer(self)
		self._releve.setInterval(RELEVE)
		self._releve.timeout.connect(self._relever)
		self._reessai = QTimer(self)
		self._reessai.setSingleShot(True)
		self._reessai.timeout.connect(self.demarrer)

	def actif(self) -> bool:
		return self._pipeline is not None

	def reessai_prevu(self) -> bool:
		"""Un port indisponible sera rouvert ; jamais avec ALSA ni sans périphérique d'antenne."""
		return self._reessai.isActive()

	def demarrer(self) -> None:
		"""Ouvre le port de monitoring ; indisponible, il le dit, et réessaie si l'antenne a bien un port."""
		self.arreter()
		if self.audio is None:
			self.indisponible = "Indisponible : sortie de l'antenne inconnue."
			self.change.emit()
			return
		try:
			source = source_du_moniteur(self.audio)
		except Indisponible as erreur:
			self._indisponible(str(erreur))
			return
		pipeline = Gst.Pipeline.new("moniteur-antenne")
		conversion = Gst.ElementFactory.make("audioconvert", None)
		niveau = Gst.ElementFactory.make("level", None)
		puits = Gst.ElementFactory.make("fakesink", None)
		assert (conversion is not None) and (niveau is not None) and (puits is not None)
		niveau.set_property("interval", INTERVALLE_DES_NIVEAUX)
		niveau.set_property("post-messages", True)
		puits.set_property("sync", False)
		for element in (source, conversion, niveau, puits):
			pipeline.add(element)
		source.link(conversion)
		conversion.link(niveau)
		niveau.link(puits)
		self._pipeline, self._niveau = pipeline, niveau
		self._pilote = etats.Pilote(pipeline)
		self.indisponible = None
		self._son_depuis = self._releve_le = self.horloge()
		# Ouvrir le port peut attendre le serveur audio : son pilote l'ouvre, et la relève dit s'il ne s'ouvre pas.
		self._pilote.vers(Gst.State.PLAYING)
		self._releve.start()
		self.change.emit()

	def arreter(self) -> None:
		self._releve.stop()
		self._reessai.stop()
		if self._pilote is not None:
			self._pilote.eteindre()
		self._pipeline, self._pilote, self._niveau = None, None, None
		self.niveaux, self.cretes = [], []
		self.blanc, self.saturation = False, False

	def _indisponible(self, message: str) -> None:
		self.arreter()
		self.indisponible = message
		if (self.audio is not None) and (message not in (SANS_ALSA, SANS_ANTENNE)):
			self._reessai.start(REESSAI)
		self.change.emit()

	def _relever(self) -> None:
		pipeline = self._pipeline
		if pipeline is None:
			return
		if (self._pilote is not None) and (self._pilote.a_echoue()):
			self._indisponible("Indisponible : le port de monitoring ne s'ouvre pas.")
			return
		bus = pipeline.get_bus()
		assert bus is not None
		while (message := bus.pop()) is not None:
			if message.type in (Gst.MessageType.ERROR, Gst.MessageType.EOS):
				texte = "le port de monitoring s'est fermé."
				if message.type == Gst.MessageType.ERROR:
					erreur, _detail = message.parse_error()
					texte = str(erreur.message)
				self._indisponible(f"Indisponible : {texte}")
				return
			structure = message.get_structure()
			if (message.src == self._niveau) and (structure is not None) and (structure.get_name() == "level"):
				self._releve_le = self.horloge()
				self.noter(list((structure.get_value("rms")) or ([])), list((structure.get_value("peak")) or ([])))
		if (self._releve_le is not None) and (self.horloge() - self._releve_le >= DELAI_DU_GEL):
			self._indisponible(GELE)
			return
		self.change.emit()

	def noter(self, niveaux: list[float], cretes: list[float]) -> None:
		"""Un relevé de level : le VU (RMS) et la crête de chaque canal, en décibels ; met à jour les voyants."""
		maintenant = self.horloge()
		self.niveaux, self.cretes = [float(n) for n in niveaux], [float(c) for c in cretes]
		if any(niveau > SEUIL_DU_BLANC for niveau in self.niveaux):
			self._son_depuis = maintenant
		self.blanc = (self._son_depuis is not None) and (maintenant - self._son_depuis >= DUREE_DU_BLANC)
		if any(crete >= SEUIL_DE_SATURATION for crete in self.cretes):
			self._saturation_depuis = maintenant
		self.saturation = (self._saturation_depuis is not None) and (
			maintenant - self._saturation_depuis < MAINTIEN_DE_SATURATION
		)
