"""Vérification d'un fichier sonore par décodage complet (https://github.com/dascritch/machincast/issues/7).

Le fichier est décodé en entier par GStreamer, sans être joué et donc bien plus vite que le temps
réel. GStreamer est tolérant : un fichier tronqué ou corrompu se décode le plus souvent sans la
moindre erreur, en donnant un son plus court ou parasité. Le décodage examine donc trois signes :

1. une erreur de GStreamer, aucun son décodé ou un décodage qui n'avance plus : fichier illisible ;
2. une rupture de continuité du son décodé (tampon marqué DISCONT après le premier) : le décodeur
   a dû sauter des données, fichier endommagé ;
3. une durée décodée plus courte que la durée annoncée par l'en-tête : fichier tronqué ou trames
   perdues, fichier endommagé.

Limites, propres aux formats : un WAV ou un AIFF n'a ni somme de contrôle ni structure en trames,
des octets altérés y passent inaperçus ; un WAV, un Ogg ou un MP3 sans en-tête de durée tronqué se
décode comme un fichier plus court, sans rien qui le distingue d'un fichier sain.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

DELAI_SANS_PROGRESSION = timedelta(seconds=30)
"""Un décodage qui ne produit plus aucun son pendant ce délai est abandonné (disque bloqué, fichier sur un
partage réseau qui ne répond plus)."""

DELAI_DEMARRAGE = timedelta(seconds=5)
"""Délai accordé au premier son décodé. Au-delà, le décodage est repris depuis le début."""

TENTATIVES = 3
"""Nombre de démarrages tentés. GStreamer se bloque parfois au démarrage d'un pipeline, avant le moindre son
décodé (environ un décodage sur cent, sur des fichiers sains comme défectueux) : un nouveau démarrage suffit.
Trois tentatives laissent aussi à un disque réseau en veille le temps de répondre."""

TOLERANCE_DUREE = timedelta(milliseconds=75)
"""Écart toléré entre la durée annoncée et la durée décodée : les encodeurs MP3 et AAC ajoutent ou retirent
quelques dizaines de millisecondes de remplissage. Une trame FLAC perdue en fait déjà une centaine."""

TOLERANCE_RELATIVE = 0.001
"""Écart toléré en proportion de la durée annoncée, pour les longs fichiers : 3,6 secondes sur une heure."""

PAS_D_ATTENTE = timedelta(milliseconds=250)

PAQUETS_DECODEURS = "gstreamer1.0-plugins-base, gstreamer1.0-plugins-good et gstreamer1.0-plugins-bad"


class EtatFichier(StrEnum):
	"""Verdict de la vérification d'un fichier."""

	SAIN = "sain"
	ENDOMMAGE = "endommagé"
	ILLISIBLE = "illisible"
	INTROUVABLE = "introuvable"


@dataclass(frozen=True)
class Verification:
	etat: EtatFichier
	duree: timedelta | None
	"""Durée effectivement décodée ; None si rien n'a pu être décodé."""
	probleme: str | None = None
	"""Description du problème, commençant par l'état (« endommagé : … ») ; None pour un fichier sain."""

	@classmethod
	def sain(cls, duree: timedelta) -> "Verification":
		return cls(EtatFichier.SAIN, duree)

	@classmethod
	def defectueux(cls, etat: EtatFichier, detail: str, duree: timedelta | None = None) -> "Verification":
		return cls(etat, duree, f"{etat} : {detail}")


class DecodeurIndisponible(Exception):
	"""GStreamer n'a pas de décodeur pour ce format : il manque un paquet, le fichier n'y est pour rien.

	La vérification s'arrête au lieu de déclarer le fichier illisible : sinon, un paquet absent
	désactiverait d'un coup tous les sonores du format concerné.
	"""


@dataclass
class _Suivi:
	"""Ce que la sonde voit passer à l'entrée du puits : les tampons de son décodé."""

	tampons: int = 0
	ruptures: int = 0
	debut: int | None = None
	fin: int = 0


def _sonder(suivi: _Suivi) -> Callable[[Gst.Pad, Gst.PadProbeInfo], Gst.PadProbeReturn]:
	def sonde(pad: Gst.Pad, info: Gst.PadProbeInfo) -> Gst.PadProbeReturn:
		tampon = info.get_buffer()
		if tampon is None:
			return Gst.PadProbeReturn.OK
		suivi.tampons += 1
		if suivi.tampons > 1 and tampon.has_flags(Gst.BufferFlags.DISCONT):
			suivi.ruptures += 1
		if tampon.pts != Gst.CLOCK_TIME_NONE:
			if suivi.debut is None:
				suivi.debut = tampon.pts
			duree = tampon.duration if tampon.duration != Gst.CLOCK_TIME_NONE else 0
			suivi.fin = max(suivi.fin, tampon.pts + duree)
		return Gst.PadProbeReturn.OK

	return sonde


def _en_secondes(duree: timedelta) -> str:
	return f"{duree.total_seconds():.3f} s".replace(".", ",")


def _nanosecondes(valeur: int) -> timedelta:
	return timedelta(microseconds=valeur / 1000)


class _Decodage:
	"""Un pipeline filesrc ! decodebin ! audioconvert ! fakesink, aussi rapide que le disque le permet."""

	def __init__(self, chemin: Path) -> None:
		self.pipeline = Gst.Pipeline.new("verification")
		elements = [Gst.ElementFactory.make(nom, None) for nom in ("filesrc", "decodebin", "audioconvert", "fakesink")]
		if any(element is None for element in elements):
			raise DecodeurIndisponible(f"éléments GStreamer de base introuvables : installer {PAQUETS_DECODEURS}")
		source, decodeur, self.conversion, puits = (element for element in elements if element is not None)
		source.set_property("location", str(chemin))
		puits.set_property("sync", False)
		for element in (source, decodeur, self.conversion, puits):
			self.pipeline.add(element)
		source.link(decodeur)
		self.conversion.link(puits)
		decodeur.connect("pad-added", self._relier)
		self.suivi = _Suivi()
		entree = puits.get_static_pad("sink")
		assert entree is not None
		entree.add_probe(Gst.PadProbeType.BUFFER, _sonder(self.suivi))
		bus = self.pipeline.get_bus()
		assert bus is not None
		self.bus = bus
		self.decodeur_absent: str | None = None

	def _relier(self, decodeur: Gst.Element, sortie: Gst.Pad) -> None:
		"""Relie la première sortie audio de decodebin ; les autres flux (pochette, vidéo) sont ignorés."""
		entree = self.conversion.get_static_pad("sink")
		if entree is None or entree.is_linked():
			return
		# decodebin annonce ses sorties avec des capacités fixées ; sans elles, la liaison décide.
		capacites = sortie.get_current_caps()
		structure = capacites.get_structure(0) if capacites is not None and capacites.get_size() > 0 else None
		if structure is None or structure.get_name().startswith("audio/"):
			sortie.link(entree)

	def attendre(
		self, attendus: Gst.MessageType, delai_demarrage: timedelta, delai_sans_progression: timedelta
	) -> Gst.Message | None:
		"""Attend un des messages attendus ou une erreur ; None si le son décodé n'avance plus.

		Tant qu'aucun son n'est décodé, le délai est celui du démarrage ; ensuite, celui de la progression.
		"""
		pas = round(PAS_D_ATTENTE.total_seconds() * Gst.SECOND)
		types = attendus | Gst.MessageType.ERROR | Gst.MessageType.ELEMENT
		immobile = timedelta()
		dernier = self.suivi.tampons
		while True:
			message = self.bus.timed_pop_filtered(pas, types)
			if message is None:
				if self.suivi.tampons == dernier:
					immobile += PAS_D_ATTENTE
					if immobile >= (delai_demarrage if self.suivi.tampons == 0 else delai_sans_progression):
						return None
				else:
					dernier, immobile = self.suivi.tampons, timedelta()
				continue
			if message.type == Gst.MessageType.ELEMENT:
				structure = message.get_structure()
				if structure is not None and structure.get_name() == "missing-plugin":
					detail = structure.get_value("detail")
					self.decodeur_absent = detail.to_string() if isinstance(detail, Gst.Caps) else str(detail)
				continue
			return message

	def erreur(self, message: Gst.Message) -> Verification:
		erreur, _ = message.parse_error()
		if self.decodeur_absent is not None or erreur.matches(Gst.StreamError.quark(), Gst.StreamError.CODEC_NOT_FOUND):
			format_absent = self.decodeur_absent or "ce format"
			raise DecodeurIndisponible(f"aucun décodeur GStreamer pour {format_absent} : installer {PAQUETS_DECODEURS}")
		return Verification.defectueux(EtatFichier.ILLISIBLE, erreur.message)

	def duree_decodee(self) -> timedelta | None:
		if self.suivi.tampons == 0 or self.suivi.debut is None:
			return None
		return _nanosecondes(self.suivi.fin - self.suivi.debut)


def verifier_fichier(
	chemin: Path,
	delai_sans_progression: timedelta = DELAI_SANS_PROGRESSION,
	delai_demarrage: timedelta = DELAI_DEMARRAGE,
) -> Verification:
	"""Décode le fichier en entier et rend son verdict, avec la durée effectivement décodée.

	Un décodage qui ne démarre pas est repris, jusqu'à TENTATIVES fois. Lève DecodeurIndisponible si GStreamer
	n'a pas de décodeur pour ce format.
	"""
	if not chemin.exists():
		return Verification.defectueux(EtatFichier.INTROUVABLE, "aucun fichier à cet emplacement")
	Gst.init(None)
	for _ in range(TENTATIVES):
		resultat = _tentative(chemin, delai_demarrage, delai_sans_progression)
		if resultat is not None:
			return resultat
	return Verification.defectueux(
		EtatFichier.ILLISIBLE,
		f"décodage bloqué au démarrage, aucun son décodé en {TENTATIVES} tentatives de {_en_secondes(delai_demarrage)}",
	)


def _tentative(chemin: Path, delai_demarrage: timedelta, delai_sans_progression: timedelta) -> Verification | None:
	"""Un décodage complet ; None s'il s'est bloqué avant le moindre son décodé, pour qu'il soit repris."""
	decodage = _Decodage(chemin)
	bloque = Verification.defectueux(
		EtatFichier.ILLISIBLE,
		f"décodage bloqué, aucun son décodé pendant {_en_secondes(delai_sans_progression)}",
	)
	try:
		# Pré-lecture : l'en-tête est lu, la durée annoncée devient connue quand le format la donne.
		decodage.pipeline.set_state(Gst.State.PAUSED)
		message = decodage.attendre(Gst.MessageType.ASYNC_DONE, delai_demarrage, delai_sans_progression)
		if message is None:
			return bloque if decodage.suivi.tampons > 0 else None
		if message.type == Gst.MessageType.ERROR:
			return decodage.erreur(message)
		connue, annoncee = decodage.pipeline.query_duration(Gst.Format.TIME)
		duree_annoncee = _nanosecondes(annoncee) if connue and annoncee > 0 else None

		decodage.pipeline.set_state(Gst.State.PLAYING)
		message = decodage.attendre(Gst.MessageType.EOS, delai_demarrage, delai_sans_progression)
		if message is None:
			return bloque if decodage.suivi.tampons > 0 else None
		if message.type == Gst.MessageType.ERROR:
			return decodage.erreur(message)
	finally:
		decodage.pipeline.set_state(Gst.State.NULL)
	duree = decodage.duree_decodee()
	if duree is None or duree <= timedelta():
		return Verification.defectueux(EtatFichier.ILLISIBLE, "aucun son décodé")
	if decodage.suivi.ruptures > 0:
		return Verification.defectueux(
			EtatFichier.ENDOMMAGE,
			f"{decodage.suivi.ruptures} rupture(s) de continuité au décodage, des données ont été perdues",
			duree,
		)
	if duree_annoncee is not None:
		tolerance = max(TOLERANCE_DUREE, duree_annoncee * TOLERANCE_RELATIVE)
		if duree < duree_annoncee - tolerance:
			return Verification.defectueux(
				EtatFichier.ENDOMMAGE,
				f"{_en_secondes(duree)} décodées sur {_en_secondes(duree_annoncee)} annoncées par l'en-tête,"
				" fichier tronqué ou trames perdues",
				duree,
			)
	return Verification.sain(duree)
