"""Moteur audio GStreamer avec crossfade (https://github.com/dascritch/machincast/issues/15, spec § 5.1).

Chaque sonore joue dans sa propre voie : un pipeline playbin qui sort sur l'élément de la sortie configurée
(machincast.audio), précédé d'un élément volume. Deux voies se superposent pendant un crossfade ; la sortie
mélange leurs sons (PipeWire et PulseAudio le font toujours ; en ALSA, il faut un périphérique qui le permet,
comme « default » avec dmix).

- Crossfade de début : le sonore monte de 0 à plein volume pendant crossfade_debut.
- Crossfade de fin : le sonore s'éteint pendant ses crossfade_fin dernières secondes, et le sonore suivant démarre
  à ce moment-là (enchainement).
- Les deux sonores ne se superposent que si le sortant a un crossfade de fin et l'entrant un crossfade de début.
  Sinon, le sortant joue jusqu'au bout à plein volume (supprimer_fondu_de_sortie), et l'entrant démarre ensuite,
  à plein volume (fondu_d_entree).
- Coupure nette : toutes les voies s'arrêtent aussitôt (début d'un événement, spec § 4.2).

Le volume suit une enveloppe posée à l'avance sur l'élément volume (GstController), d'après la durée connue du
sonore. Le moteur ne lit l'heure que par la position des voies : il ne décide de rien, l'ordonnanceur
(machincast.lecture.deroule) lui dit quoi jouer et quand couper.
"""

from datetime import timedelta
from pathlib import Path
from typing import Literal

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstController", "1.0")
from gi.repository import Gst, GstController  # type: ignore[attr-defined]  # noqa: E402

from machincast.audio import SortieAudioIndisponible, creer_sortie  # noqa: E402
from machincast.configuration import Audio  # noqa: E402

EtatVoie = Literal["prête", "en cours", "finie", "coupée", "en erreur"]

# GstPlayFlags : audio seulement, sans vidéo ni sous-titres.
LECTURE_AUDIO_SEULE = 0x00000002


def superposition(crossfade_fin_sortant: timedelta, crossfade_debut_entrant: timedelta) -> bool:
	"""Deux sonores ne se superposent que si chacun a son crossfade, de fin pour l'un, de début pour l'autre."""
	return crossfade_fin_sortant > timedelta(0) and crossfade_debut_entrant > timedelta(0)


def enchainement(duree: timedelta, crossfade_fin: timedelta, crossfade_debut_suivant: timedelta) -> timedelta:
	"""Après combien de temps le sonore suivant démarre : avant la fin du crossfade s'ils se superposent."""
	if superposition(crossfade_fin, crossfade_debut_suivant):
		return max(timedelta(0), duree - crossfade_fin)
	return duree


def fondu_d_entree(crossfade_fin_precedent: timedelta, crossfade_debut: timedelta) -> timedelta:
	"""Durée de la montée du sonore entrant : son crossfade de début s'il se superpose au précédent, sinon rien."""
	return crossfade_debut if superposition(crossfade_fin_precedent, crossfade_debut) else timedelta(0)


def enveloppe(
	duree: timedelta | None, crossfade_debut: timedelta, crossfade_fin: timedelta
) -> list[tuple[timedelta, float]]:
	"""Points du volume au fil du sonore, reliés par des droites : montée, plein volume, extinction."""
	points: list[tuple[timedelta, float]] = []
	if crossfade_debut > timedelta(0):
		points += [(timedelta(0), 0.0), (crossfade_debut, 1.0)]
	else:
		points.append((timedelta(0), 1.0))
	if duree is not None and crossfade_fin > timedelta(0):
		points += [(max(duree - crossfade_fin, points[-1][0]), 1.0), (duree, 0.0)]
	return points


def _nanosecondes(duree: timedelta) -> int:
	return round(duree.total_seconds() * Gst.SECOND)


class Voie:
	"""Un sonore joué sur la sortie, avec son enveloppe de volume."""

	def __init__(
		self,
		chemin: Path,
		audio: Audio,
		duree: timedelta | None,
		crossfade_debut: timedelta = timedelta(0),
		crossfade_fin: timedelta = timedelta(0),
		temps_reel: bool = True,
	) -> None:
		Gst.init(None)
		self.chemin = chemin
		self.etat: EtatVoie = "prête"
		self.erreur: str | None = None
		self.position_finale: timedelta | None = None
		"""Position atteinte quand la voie a été coupée."""

		lecteur = Gst.ElementFactory.make("playbin", None)
		volume = Gst.ElementFactory.make("volume", None)
		if lecteur is None or volume is None:
			raise SortieAudioIndisponible("playbin ou volume introuvable, installer gstreamer1.0-plugins-base")
		sortie = creer_sortie(audio.sortie, audio.peripherique)
		# Une vraie sortie suit l'horloge ; la sortie factice peut aller au plus vite, pour les tests.
		sortie.set_property("sync", temps_reel)
		fabrique = sortie.get_factory()
		self.fabrique_de_sortie = "" if fabrique is None else fabrique.get_name()

		branche = Gst.Bin.new(None)
		branche.add(volume)
		branche.add(sortie)
		volume.link(sortie)
		entree = volume.get_static_pad("sink")
		assert entree is not None
		branche.add_pad(Gst.GhostPad.new("sink", entree))

		lecteur.set_property("flags", LECTURE_AUDIO_SEULE)
		lecteur.set_property("audio-sink", branche)
		lecteur.set_property("uri", Gst.filename_to_uri(str(chemin.absolute())))

		source = GstController.InterpolationControlSource()
		source.set_property("mode", GstController.InterpolationMode.LINEAR)
		for instant, valeur in enveloppe(duree, crossfade_debut, crossfade_fin):
			source.set(_nanosecondes(instant), valeur)
		volume.add_control_binding(GstController.DirectControlBinding.new_absolute(volume, "volume", source))

		self._lecteur = lecteur
		self._volume = volume
		self._source = source
		self._duree = duree
		self._crossfade_debut = crossfade_debut

	def supprimer_fondu_de_sortie(self) -> None:
		"""Le sonore suivant ne se superpose pas : celui-ci joue jusqu'au bout, à plein volume."""
		self._source.unset_all()
		for instant, valeur in enveloppe(self._duree, self._crossfade_debut, timedelta(0)):
			self._source.set(_nanosecondes(instant), valeur)

	def volume_a(self, instant: timedelta) -> float:
		"""Volume prévu à cet instant du sonore, entre 0 et 1."""
		valeur = self._volume.get_value("volume", _nanosecondes(instant))
		return 1.0 if valeur is None else float(valeur)

	def position(self) -> timedelta:
		trouvee, nanosecondes = self._lecteur.query_position(Gst.Format.TIME)
		return timedelta(microseconds=nanosecondes / 1000) if trouvee else timedelta(0)

	def demarrer(self) -> None:
		self.etat = "en cours"
		if self._lecteur.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
			self.traiter()

	def couper(self) -> None:
		"""Arrêt net, sans fondu."""
		if self.etat == "en cours":
			self.position_finale = self.position()
			self.etat = "coupée"
		self._lecteur.set_state(Gst.State.NULL)

	def traiter(self) -> None:
		"""Lit les messages du pipeline : fin du sonore, ou erreur de lecture."""
		bus = self._lecteur.get_bus()
		while self.etat == "en cours" and bus is not None:
			message = bus.pop_filtered(Gst.MessageType.EOS | Gst.MessageType.ERROR)
			if message is None:
				return
			if message.type == Gst.MessageType.ERROR:
				erreur, _ = message.parse_error()
				self.etat, self.erreur = "en erreur", erreur.message
			else:
				self.etat = "finie"
			self._lecteur.set_state(Gst.State.NULL)

	def fermer(self) -> None:
		self._lecteur.set_state(Gst.State.NULL)


class MoteurAudio:
	"""Joue les sonores sur la sortie de la configuration, une voie par sonore."""

	def __init__(self, audio: Audio, temps_reel: bool = True) -> None:
		self.audio = audio
		self.temps_reel = temps_reel
		self._voies: list[Voie] = []

	def jouer(
		self,
		chemin: Path,
		duree: timedelta | None,
		crossfade_debut: timedelta = timedelta(0),
		crossfade_fin: timedelta = timedelta(0),
	) -> Voie:
		"""Démarre le sonore dans une nouvelle voie, en plus de celles en cours (crossfade)."""
		voie = Voie(chemin, self.audio, duree, crossfade_debut, crossfade_fin, self.temps_reel)
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
