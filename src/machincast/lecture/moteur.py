"""Moteur audio GStreamer avec crossfade (https://github.com/dascritch/machincast/issues/15, spec § 5.1).

Chaque sonore joue dans sa propre voie : un pipeline playbin3 (machincast.audio.LECTEUR) qui sort sur l'élément de
la sortie configurée (machincast.audio), précédé d'un élément volume. Deux voies se superposent pendant un crossfade ;
la sortie mélange leurs sons (PipeWire et PulseAudio le font toujours ; en ALSA, il faut un périphérique qui le
permet, comme « default » avec dmix).

- Crossfade de début : le sonore monte de 0 à plein volume pendant crossfade_debut.
- Crossfade de fin : le sonore s'éteint pendant ses crossfade_fin dernières secondes, et le sonore suivant démarre
  à ce moment-là (enchainement).
- Les deux sonores ne se superposent que si le sortant a un crossfade de fin et l'entrant un crossfade de début.
  Sinon, le sortant joue jusqu'au bout à plein volume (supprimer_fondu_de_sortie), et l'entrant démarre ensuite,
  à plein volume (fondu_d_entree).
- Coupure nette : toutes les voies s'arrêtent aussitôt (début d'un événement, spec § 4.2).
- Stream (https://github.com/dascritch/machincast/issues/16) : la voie lit une adresse HTTP, sans durée connue.
  Elle peut démarrer muette, le temps de vérifier que le flux arrive, puis monter (fondu) ; elle s'éteint en fondu
  et s'arrête d'elle-même à la fin du fondu (eteindre). La source ne retente pas seule une connexion perdue : la
  diffusion s'en charge.

Sonore rogné par la détection de silence (https://github.com/dascritch/machincast/issues/146) : la voie commence à
decalage secondes du début du fichier (son début détecté) et s'arrête d'elle-même après duree secondes (à sa fin
détectée), par une recherche (seek) qui borne la lecture du fichier. La position de la voie, l'enveloppe et les fondus
se comptent depuis ce début : le fichier n'est jamais modifié.

Stream gelé (https://github.com/dascritch/machincast/issues/278) : un stream dont la position n'avance plus pendant
DELAI_DE_GARDE est gelé (gelee) ; la diffusion le tient pour tombé, et sa sonde, pour injoignable.

Lecteur bloqué (https://github.com/dascritch/machincast/issues/281) : playbin se bloquait au démarrage d'un AIFF,
sans erreur ni son, avec GStreamer 1.24 comme avec 1.28 (36 fois sur 300 en temps réel). playbin3, qui le remplace,
ne s'est jamais bloqué (https://github.com/dascritch/machincast/issues/284) ; la garde reste, contre tout lecteur
qui ne démarre pas. Une voie qui n'a pas atteint l'état PLAYING
DELAI_DE_GARDE après son démarrage est bloquée (bloquee) : la diffusion la remplace par le sonore suivant.

Le volume suit une enveloppe posée à l'avance sur l'élément volume (GstController), d'après la durée connue du
sonore. Le moteur ne lit l'heure que par la position des voies : il ne décide de rien, l'ordonnanceur
(machincast.lecture.deroule) lui dit quoi jouer et quand couper.
"""

import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Literal, Protocol

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstController", "1.0")
from gi.repository import Gst, GstController  # type: ignore[attr-defined]  # noqa: E402

from machincast.audio import LECTEUR, SortieAudioIndisponible, creer_sortie  # noqa: E402
from machincast.configuration import Audio  # noqa: E402

EtatVoie = Literal["prête", "en cours", "finie", "coupée", "en erreur"]

# GstPlayFlags : audio seulement, sans vidéo ni sous-titres.
LECTURE_AUDIO_SEULE = 0x00000002

DELAI_PRELECTURE = timedelta(seconds=2)
"""Délai accordé à la pré-lecture d'un fichier rogné, avant la recherche de son début détecté : au-delà, la voie joue
le fichier depuis son début."""

DELAI_DE_GARDE = timedelta(seconds=10)
"""Le même délai de garde dans tous les cas, celui d'un flux HTTP/1.1 qui ne répond plus (DELAI_CONNEXION_SECONDES) :
une voie qui n'a pas atteint l'état PLAYING au bout de ce délai est bloquée
(https://github.com/dascritch/machincast/issues/281) ; un stream qui ne donne plus de son pendant ce délai est gelé
(https://github.com/dascritch/machincast/issues/278)."""

DELAI_CONNEXION_SECONDES = round(DELAI_DE_GARDE.total_seconds())
"""Délai de connexion et de réponse d'un flux HTTP, au-delà duquel la voie passe en erreur : le délai de garde."""


def superposition(crossfade_fin_sortant: timedelta, crossfade_debut_entrant: timedelta) -> bool:
	"""Deux sonores ne se superposent que si chacun a son crossfade, de fin pour l'un, de début pour l'autre."""
	return (crossfade_fin_sortant > timedelta(0)) and (crossfade_debut_entrant > timedelta(0))


def enchainement(duree: timedelta, crossfade_fin: timedelta, crossfade_debut_suivant: timedelta) -> timedelta:
	"""Après combien de temps le sonore suivant démarre : avant la fin du crossfade s'ils se superposent."""
	if superposition(crossfade_fin, crossfade_debut_suivant):
		return max(timedelta(0), duree - crossfade_fin)
	return duree


def fondu_d_entree(crossfade_fin_precedent: timedelta, crossfade_debut: timedelta) -> timedelta:
	"""Durée de la montée du sonore entrant : son crossfade de début s'il se superpose au précédent, sinon rien."""
	if not superposition(crossfade_fin_precedent, crossfade_debut):
		return timedelta(0)
	return crossfade_debut


def enveloppe(
	duree: timedelta | None,
	crossfade_debut: timedelta,
	crossfade_fin: timedelta,
	depart: float = 0.0,
	arrivee: float = 0.0,
) -> list[tuple[timedelta, float]]:
	"""Points du volume au fil du sonore, reliés par des droites : montée, plein volume, extinction. Un fade-in qui a
	commencé avant le fichier part du volume depart ; un fade-out qui finit après lui s'arrête au volume arrivee
	(https://github.com/dascritch/machincast/issues/234)."""
	points: list[tuple[timedelta, float]] = []
	if crossfade_debut > timedelta(0):
		points += [(timedelta(0), depart), (crossfade_debut, 1.0)]
	else:
		points.append((timedelta(0), 1.0))
	if (duree is not None) and (crossfade_fin > timedelta(0)):
		points += [(max(duree - crossfade_fin, points[-1][0]), 1.0), (duree, arrivee)]
	return points


def _nanosecondes(duree: timedelta) -> int:
	return round(duree.total_seconds() * Gst.SECOND)


class Voie:
	"""Un sonore joué sur la sortie, avec son enveloppe de volume."""

	def __init__(
		self,
		chemin: Path | str,
		audio: Audio,
		duree: timedelta | None,
		crossfade_debut: timedelta = timedelta(0),
		crossfade_fin: timedelta = timedelta(0),
		temps_reel: bool = True,
		muette: bool = False,
		decalage: timedelta | None = None,
		depart: float = 0.0,
		arrivee: float = 0.0,
		horloge: Callable[[], float] = time.monotonic,
	) -> None:
		"""chemin : un fichier, ou l'adresse d'un stream. Muette, la voie joue à volume nul jusqu'à un fondu.

		depart, arrivee : volumes au début et à la fin de la voie, quand ses fondus débordent du fichier
		(https://github.com/dascritch/machincast/issues/234, machincast.lecture.fondus).

		decalage : pour un sonore rogné par la détection de silence, la voie commence à cette position du fichier, et
		s'arrête après duree (https://github.com/dascritch/machincast/issues/146) ; None : le fichier est joué en
		entier."""
		Gst.init(None)
		self.chemin = chemin
		self.etat: EtatVoie = "prête"
		self.erreur: str | None = None
		self.decalage = timedelta(0)
		"""Position du fichier où la voie commence : son début détecté ; 0 pour un sonore joué en entier."""
		self._rognee = (decalage is not None) and (not isinstance(chemin, str))
		"""La voie ne joue qu'une partie du fichier, du début détecté à la fin détectée."""
		if decalage is not None:
			self.decalage = max(decalage, timedelta(0))
		self.position_finale: timedelta | None = None
		"""Position atteinte quand la voie a été coupée, ou quand elle s'est finie."""
		self.arret_prevu: timedelta | None = None
		"""Position où la voie s'arrête d'elle-même, à la fin d'un fondu de sortie (eteindre)."""

		lecteur = Gst.ElementFactory.make(LECTEUR, None)
		volume = Gst.ElementFactory.make("volume", None)
		if (lecteur is None) or (volume is None):
			raise SortieAudioIndisponible(f"{LECTEUR} ou volume introuvable, installer gstreamer1.0-plugins-base")
		sortie = creer_sortie(audio.sortie, audio.peripherique)
		# Une vraie sortie suit l'horloge ; la sortie factice peut aller au plus vite, pour les tests.
		sortie.set_property("sync", temps_reel)
		fabrique = sortie.get_factory()
		self.fabrique_de_sortie: str | None = ""
		if fabrique is not None:
			self.fabrique_de_sortie = fabrique.get_name()

		branche = Gst.Bin.new(None)
		branche.add(volume)
		branche.add(sortie)
		volume.link(sortie)
		entree = volume.get_static_pad("sink")
		assert entree is not None
		branche.add_pad(Gst.GhostPad.new("sink", entree))

		lecteur.set_property("flags", LECTURE_AUDIO_SEULE)
		lecteur.set_property("audio-sink", branche)
		adresse: Path | str | None = chemin
		if not isinstance(chemin, str):
			adresse = Gst.filename_to_uri(str(chemin.absolute()))
		lecteur.set_property("uri", adresse)
		lecteur.connect("source-setup", _regler_source)

		source = GstController.InterpolationControlSource()
		source.set_property("mode", GstController.InterpolationMode.LINEAR)
		points = [(timedelta(0), 0.0)]
		if not muette:
			points = enveloppe(duree, crossfade_debut, crossfade_fin, depart, arrivee)
		volume.add_control_binding(GstController.DirectControlBinding.new_absolute(volume, "volume", source))

		self._lecteur = lecteur
		self._horloge = horloge
		self._demarree_a: float | None = None
		"""Instant du démarrage, à l'horloge de la voie : pour constater un lecteur bloqué."""
		self._a_joue = False
		self._derniere_position = timedelta(0)
		self._avance_le: float | None = None
		"""Instant où la position a avancé pour la dernière fois, à l'horloge de la voie ; son démarrage d'abord."""
		"""La voie a atteint l'état PLAYING : elle n'est plus bloquée au démarrage."""
		self._volume = volume
		self._source = source
		self._duree = duree
		self._crossfade_debut = crossfade_debut
		self._depart = depart
		for instant, valeur in points:
			self._poser(instant, valeur)

	def _poser(self, instant: timedelta, valeur: float) -> None:
		"""Un point de l'enveloppe, à cet instant de la voie : l'élément volume suit la position dans le fichier."""
		self._source.set(_nanosecondes(self.decalage + instant), valeur)

	def supprimer_fondu_de_sortie(self) -> None:
		"""Le sonore suivant ne se superpose pas : celui-ci joue jusqu'au bout, à plein volume."""
		self._source.unset_all()
		for instant, valeur in enveloppe(self._duree, self._crossfade_debut, timedelta(0), self._depart):
			self._poser(instant, valeur)

	def fondu(self, cible: float, duree: timedelta) -> None:
		"""Le volume va de sa valeur actuelle à la cible pendant la durée, à partir de la position actuelle."""
		position = self.position()
		actuel = self.volume_a(position)
		self._source.unset_all()
		if duree > timedelta(0):
			self._poser(position, actuel)
		self._poser(position + duree, cible)

	def eteindre(self, duree: timedelta) -> None:
		"""Fondu de sortie à partir de maintenant ; la voie s'arrête à la fin du fondu, aussitôt sans durée."""
		if duree <= timedelta(0):
			self.arret_prevu = self.position()
			self.traiter()
			return
		self.fondu(0.0, duree)
		self.arret_prevu = self.position() + duree

	def volume_a(self, instant: timedelta) -> float:
		"""Volume prévu à cet instant du sonore, entre 0 et 1."""
		valeur = self._volume.get_value("volume", _nanosecondes(self.decalage + instant))
		if valeur is None:
			return 1.0
		return float(valeur)

	def position(self) -> timedelta:
		"""Position de la voie, depuis son début : pour un sonore rogné, depuis son début détecté."""
		trouvee, nanosecondes = self._lecteur.query_position(Gst.Format.TIME)
		if not trouvee:
			return timedelta(0)
		return max(timedelta(0), timedelta(microseconds=nanosecondes / 1000) - self.decalage)

	def demarrer(self) -> None:
		self.etat = "en cours"
		self._demarree_a = self._horloge()
		self._avance_le = self._demarree_a
		if self._rognee:
			self._borner()
		if self._lecteur.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
			self.traiter()

	def bloquee(self) -> bool:
		"""Le lecteur n'a pas atteint l'état PLAYING DELAI_DE_GARDE après son démarrage, sans erreur ni fin : il
		ne jouera rien (https://github.com/dascritch/machincast/issues/281). Jamais bloquée une fois qu'elle a joué."""
		if (self.etat != "en cours") or (self._demarree_a is None) or (self._a_joue):
			return False
		_resultat, actuel, _attendu = self._lecteur.get_state(0)
		if actuel == Gst.State.PLAYING:
			self._a_joue = True
			return False
		return self._horloge() - self._demarree_a >= DELAI_DE_GARDE.total_seconds()

	def gelee(self) -> bool:
		"""Aucun son depuis DELAI_DE_GARDE : la position n'a pas avancé depuis le démarrage de la voie, ou depuis sa
		dernière avance, sans erreur ni fin (https://github.com/dascritch/machincast/issues/278). C'est ce que fait un
		flux qui ne donne plus rien sans fermer sa connexion, quand le lecteur ne le signale pas : en HTTP/2, libsoup 3
		ne remonte pas l'expiration de son délai. À demander à chaque pas : chaque appel note l'avance de la
		position."""
		if (self.etat != "en cours") or (self._avance_le is None):
			return False
		maintenant = self._horloge()
		position = self.position()
		if position > self._derniere_position:
			self._derniere_position, self._avance_le = position, maintenant
			return False
		return maintenant - self._avance_le >= DELAI_DE_GARDE.total_seconds()

	def _borner(self) -> None:
		"""Pré-lit le fichier, puis borne sa lecture : du début détecté à la fin détectée
		(https://github.com/dascritch/machincast/issues/146). Un fichier qui ne se pré-lit pas est joué en entier ;
		son erreur viendra à la lecture."""
		if self._lecteur.set_state(Gst.State.PAUSED) == Gst.StateChangeReturn.FAILURE:
			return
		resultat, _etat, _attendu = self._lecteur.get_state(_nanosecondes(DELAI_PRELECTURE))
		if resultat == Gst.StateChangeReturn.FAILURE:
			return
		fin_type, fin = Gst.SeekType.NONE, -1
		if self._duree is not None:
			fin_type, fin = Gst.SeekType.SET, _nanosecondes(self.decalage + self._duree)
		self._lecteur.seek(
			1.0,
			Gst.Format.TIME,
			Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
			Gst.SeekType.SET,
			_nanosecondes(self.decalage),
			fin_type,
			fin,
		)
		self._lecteur.get_state(_nanosecondes(DELAI_PRELECTURE))

	def couper(self) -> None:
		"""Arrêt net, sans fondu."""
		if self.etat == "en cours":
			self.position_finale = self.position()
			self.etat = "coupée"
		self._lecteur.set_state(Gst.State.NULL)

	def traiter(self) -> None:
		"""Lit les messages du pipeline : fin du sonore, ou erreur de lecture ; arrête la voie à la fin d'un fondu
		de sortie."""
		if (self.etat == "en cours") and (self.arret_prevu is not None) and (self.position() >= self.arret_prevu):
			self.etat = "finie"
			self._lecteur.set_state(Gst.State.NULL)
			return
		bus = self._lecteur.get_bus()
		while (self.etat == "en cours") and (bus is not None):
			message = bus.pop_filtered(Gst.MessageType.EOS | Gst.MessageType.ERROR)
			if message is None:
				return
			if message.type == Gst.MessageType.ERROR:
				erreur, _ = message.parse_error()
				self.etat, self.erreur = "en erreur", erreur.message
			else:
				self.etat = "finie"
				self.position_finale = self.position()
			self._lecteur.set_state(Gst.State.NULL)

	def fermer(self) -> None:
		self._lecteur.set_state(Gst.State.NULL)


def _regler_source(lecteur: Gst.Element, source: Gst.Element) -> None:
	"""Source HTTP d'un stream : pas de nouvelle tentative de la source elle-même, et un délai de réponse borné."""
	if hasattr(source.props, "retries"):
		source.set_property("retries", 0)
	if hasattr(source.props, "timeout"):
		source.set_property("timeout", DELAI_CONNEXION_SECONDES)


class VoieLecture(Protocol):
	"""Ce que la diffusion attend d'une voie : la voie GStreamer (Voie), ou la voie simulée de la simulation."""

	etat: EtatVoie
	erreur: str | None

	def position(self) -> timedelta: ...

	def bloquee(self) -> bool: ...

	def gelee(self) -> bool: ...

	def traiter(self) -> None: ...

	def couper(self) -> None: ...

	def fermer(self) -> None: ...

	def fondu(self, cible: float, duree: timedelta) -> None: ...

	def eteindre(self, duree: timedelta) -> None: ...

	def supprimer_fondu_de_sortie(self) -> None: ...

	def volume_a(self, instant: timedelta) -> float: ...


class Moteur(Protocol):
	"""Ce que la diffusion attend du moteur : MoteurAudio, ou le moteur simulé de la simulation."""

	def jouer(
		self,
		chemin: Path | str,
		duree: timedelta | None,
		crossfade_debut: timedelta = ...,
		crossfade_fin: timedelta = ...,
		muette: bool = ...,
		decalage: timedelta | None = ...,
		depart: float = ...,
		arrivee: float = ...,
	) -> VoieLecture: ...

	def traiter_messages(self) -> None: ...

	def couper(self) -> None: ...

	def fermer(self) -> None: ...


class MoteurAudio:
	"""Joue les sonores sur la sortie de la configuration, une voie par sonore."""

	def __init__(self, audio: Audio, temps_reel: bool = True, horloge: Callable[[], float] = time.monotonic) -> None:
		self.audio = audio
		self.temps_reel = temps_reel
		self.horloge = horloge
		"""L'horloge des voies, qui constate un lecteur bloqué ; les scénarios la remplacent."""
		self._voies: list[Voie] = []

	def jouer(
		self,
		chemin: Path | str,
		duree: timedelta | None,
		crossfade_debut: timedelta = timedelta(0),
		crossfade_fin: timedelta = timedelta(0),
		muette: bool = False,
		decalage: timedelta | None = None,
		depart: float = 0.0,
		arrivee: float = 0.0,
	) -> Voie:
		"""Démarre le sonore dans une nouvelle voie, en plus de celles en cours (crossfade) ; un sonore rogné commence à
		decalage secondes du début de son fichier (https://github.com/dascritch/machincast/issues/146)."""
		voie = Voie(
			chemin,
			self.audio,
			duree,
			crossfade_debut,
			crossfade_fin,
			self.temps_reel,
			muette,
			decalage,
			depart,
			arrivee,
			self.horloge,
		)
		voie.demarrer()
		self._voies.append(voie)
		return voie

	def traiter_messages(self) -> None:
		for voie in self._voies:
			voie.traiter()
		self._voies = [voie for voie in self._voies if voie.etat == "en cours"]

	def voies_en_cours(self) -> list[Voie]:
		return [voie for voie in self._voies if voie.etat == "en cours"]

	def couper(self) -> None:
		"""Coupure nette de toutes les voies en cours."""
		for voie in self._voies:
			voie.couper()
		self._voies = []

	def fermer(self) -> None:
		for voie in self._voies:
			voie.fermer()
		self._voies = []
