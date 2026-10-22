"""Test d'un flux à la demande, depuis la fiche d'un stream (https://github.com/dascritch/machincast/issues/28,
spec § 4.6).

GStreamer se connecte à l'adresse et décode le flux, sans rien jouer. Le flux répond dès qu'une seconde de son est
décodée ; il ne répond pas si GStreamer signale une erreur (adresse injoignable, réponse en erreur), ou si cette seconde
de son n'arrive pas dans le délai. Qui répond dit aussi le type du flux et son débit, lus dans les tags que GStreamer
trouve en le décodant (https://github.com/dascritch/machincast/issues/223) : le codec, puis le débit nominal, sinon le
débit mesuré. Le test terminé, la connexion au flux est fermée. Le test ne bloque pas l'interface :
le bus de GStreamer est relevé par un minuteur de Qt.
"""

from datetime import timedelta

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PySide6.QtCore import QObject, QTimer, Signal  # noqa: E402

DELAI = timedelta(seconds=10)
"""Au-delà, sans son, le flux ne répond pas."""
SON_ATTENDU = timedelta(seconds=1)
"""Son décodé qui prouve que le flux répond."""
RELEVE = timedelta(milliseconds=100)
"""Intervalle de relève du bus de GStreamer."""


def _millisecondes(duree: timedelta) -> int:
	return int(duree.total_seconds() * 1000)


def resultat_de_l_essai(repond: bool, detail: str) -> str:
	"""« Le flux répond : du son arrive. », ou « Le flux ne répond pas : … », pour la fiche qui a lancé l'essai."""
	verdict = "Le flux ne répond pas"
	if repond:
		verdict = "Le flux répond"
	return f"{verdict} : {detail}"


def decrire(type_du_flux: str | None, debit: int | None) -> str:
	"""« en MPEG-1 Layer 3 (MP3) à 128 kbit/s », ce qu'on en sait."""
	type_lu = "de type inconnu"
	if type_du_flux is not None:
		type_lu = f"en {type_du_flux}"
	debit_lu = "à débit inconnu"
	if debit is not None:
		debit_lu = f"à {round(debit / 1000)} kbit/s"
	return f"{type_lu} {debit_lu}"


class EssaiDeFlux(QObject):
	termine = Signal(bool, str)
	"""Fin du test : le flux répond-il, et sinon pourquoi."""

	def __init__(self, parent: QObject | None = None) -> None:
		super().__init__(parent)
		Gst.init(None)
		self._pipeline: Gst.Pipeline | None = None
		self._son = 0
		"""Son décodé, en nanosecondes."""
		self._type: str | None = None
		self._debit: int | None = None
		"""En bits par seconde : le débit nominal du flux, sinon le dernier mesuré."""
		self._releve = QTimer(self)
		self._releve.setInterval(_millisecondes(RELEVE))
		self._releve.timeout.connect(self._relever)
		self._limite = QTimer(self)
		self._limite.setSingleShot(True)
		self._limite.timeout.connect(self._expirer)

	def en_cours(self) -> bool:
		return self._pipeline is not None

	def lancer(self, adresse: str) -> None:
		"""Un seul test à la fois : la fiche n'en relance pas un tant que le précédent n'est pas terminé."""
		if not Gst.uri_is_valid(adresse):
			self.termine.emit(False, f"« {adresse} » n'est pas une adresse.")
			return
		pipeline = Gst.parse_launch(
			"uridecodebin name=source ! audioconvert ! fakesink name=sortie sync=false signal-handoffs=true"
		)
		assert isinstance(pipeline, Gst.Pipeline)
		source, sortie = pipeline.get_by_name("source"), pipeline.get_by_name("sortie")
		assert (source is not None) and (sortie is not None)
		source.set_property("uri", adresse)
		sortie.connect("handoff", self._recu)
		self._son = 0
		self._type, self._debit = None, None
		self._pipeline = pipeline
		pipeline.set_state(Gst.State.PLAYING)
		self._releve.start()
		self._limite.start(_millisecondes(DELAI))

	def arreter(self) -> None:
		self._releve.stop()
		self._limite.stop()
		if self._pipeline is not None:
			self._pipeline.set_state(Gst.State.NULL)
			self._pipeline = None

	def _recu(self, _sortie: Gst.Element, tampon: Gst.Buffer, _pad: Gst.Pad) -> None:
		"""Appelé dans un fil de GStreamer : il ne fait que compter."""
		self._son += tampon.duration

	def _relever(self) -> None:
		assert self._pipeline is not None
		bus = self._pipeline.get_bus()
		# pop_filtered jette les messages d'autres types : les tags et les erreurs se lisent ensemble.
		while (message := bus.pop_filtered(Gst.MessageType.TAG | Gst.MessageType.ERROR)) is not None:
			if message.type == Gst.MessageType.TAG:
				self._lire_les_tags(message.parse_tag())
				continue
			erreur, _detail = message.parse_error()
			self._finir(False, f"{erreur.message.rstrip('.')}.")
			return
		if self._son >= SON_ATTENDU.total_seconds() * Gst.SECOND:
			self._finir(True, f"du son arrive, {decrire(self._type, self._debit)}.")

	def _lire_les_tags(self, tags: Gst.TagList) -> None:
		trouve, codec = tags.get_string(Gst.TAG_AUDIO_CODEC)
		if trouve:
			self._type = codec
		trouve, nominal = tags.get_uint(Gst.TAG_NOMINAL_BITRATE)
		if (trouve) and (nominal > 0):
			self._debit = nominal
			return
		trouve, mesure = tags.get_uint(Gst.TAG_BITRATE)
		if (trouve) and (mesure > 0) and (self._debit is None):
			self._debit = mesure

	def _expirer(self) -> None:
		self._finir(False, f"le son n'arrive pas en {int(DELAI.total_seconds())} s.")

	def _finir(self, repond: bool, detail: str) -> None:
		self.arreter()
		self.termine.emit(repond, detail)
