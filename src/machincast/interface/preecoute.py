"""Pré-écoute d'un sonore (https://github.com/dascritch/machincast/issues/116,
https://github.com/dascritch/machincast/issues/29, spec § 8.3).

Une fenêtre indépendante, une seule pour toute l'interface (FenetrePrincipale.preecoute) : la fiche d'un sonore
y envoie son sonore, qui remplace le précédent, à l'arrêt ; le menu « Affichage » l'ouvre sans sonore, pour choisir
sa sortie. Son lecteur est un pipeline playbin3 de GStreamer (machincast.audio.LECTEUR), dont le bus est relevé par
un minuteur de Qt : rien ne bloque l'interface.

- Sortie : le périphérique de pré-écoute de la configuration (audio.preecoute), sur la sortie de l'antenne
  (audio.sortie), jamais le périphérique de l'antenne. Le choix liste les périphériques du poste (peripheriques), celui
  de l'antenne grisé ; un périphérique configuré mais absent reste proposé. Le choix s'enregistre dans le fichier de
  configuration (ecrire_preecoute), qui garde ses commentaires, et arrête la lecture en cours.
- Lecteur : lecture et pause, arrêt, qui ramène au début. La fin du fichier ramène à l'arrêt ; une erreur aussi, et
  elle est signalée.
- Frise d'un fichier (machincast.interface.frise, https://github.com/dascritch/machincast/issues/224) : elle tient
  lieu de barre de position, pendant la lecture ou sa pause, et montre sa forme d'onde, calculée en tâche de fond à
  l'ouverture, ses silences et ses crossfades enregistrés, et la partie jouée à l'antenne. « Début joué » et « Fin
  jouée » y placent la lecture, en la lançant au besoin. Écouté comme à l'antenne, le fichier n'est joué que de sa
  partie jouée, au volume de l'enveloppe de la diffusion, réglé à chaque relève : il commence au début de la partie
  jouée, et s'arrête à sa fin. Un stream n'a ni frise ni barre de position.
- VU-mètre : le niveau RMS de chaque canal, par l'élément level de GStreamer, en décibels.
- Informations : format (codec), débit (celui des tags, sinon la taille du fichier sur sa durée), échantillonnage,
  canaux, et pour un stream, les secondes pré-décodées : le son reçu d'avance, que GStreamer garde en mémoire.

L'écoute de l'antenne (https://github.com/dascritch/machincast/issues/24), par le VU-mètre de l'accueil ou le bouton
« Pré-écoute » de la fenêtre, a pour titre « en cours : » et le texte public du sonore en cours
(https://github.com/dascritch/machincast/issues/223).
"""

import math
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import gi
import psycopg
import tomlkit
from psycopg.rows import TupleRow

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PySide6.QtCore import Qt, QTimer, Signal  # noqa: E402
from PySide6.QtGui import QCloseEvent, QStandardItemModel  # noqa: E402
from PySide6.QtWidgets import QVBoxLayout, QWidget  # noqa: E402

from machincast import audio as sorties_audio  # noqa: E402
from machincast.audio import LECTEUR, PREECOUTE, creer_sortie  # noqa: E402
from machincast.configuration import Audio, Crossfades, SortieAudio  # noqa: E402
from machincast.interface import affichage, etats, liaison, preferences  # noqa: E402
from machincast.interface.frise import FormeDOnde, Frise, Plan, plan_du_sonore  # noqa: E402
from machincast.interface.moniteur import Indisponible, nom_du_port, source_du_moniteur  # noqa: E402
from machincast.interface.ui.preecoute import Ui_FenetrePreecoute  # noqa: E402
from machincast.interface.vumetre import VuMetre  # noqa: E402

RELEVE = 50
"""Millisecondes entre deux relèves du bus et de l'affichage."""
INTERVALLE_DES_NIVEAUX = 50 * Gst.MSECOND
TAMPON_DES_STREAMS = 5
"""Secondes de son qu'un stream reçoit d'avance : le pré-décodé en est la part remplie."""
ETATS = {"arret": "À l'arrêt", "lecture": "En lecture", "pause": "En pause"}
AUCUN = "Aucun sonore"
CANAUX = {1: "mono", 2: "stéréo"}
DIFFUSION = "(diffusion)"
"""Ce qui suit, grisé dans le choix de sortie, le nom du périphérique de la diffusion."""
LECTURE = ("⏵", "Lecture")
PAUSE = ("⏸", "Pause")
"""Le symbole du bouton, et son infobulle, qui le nomme aussi pour les technologies d'assistance ; l'arrêt est « ⏹ »."""


@dataclass(frozen=True)
class Source:
	"""Ce que la pré-écoute joue."""

	titre: str
	adresse: str
	"""Chemin du fichier, ou adresse du stream."""
	stream: bool
	duree: float | None
	"""Durée en base, en secondes, montrée avant la lecture."""
	antenne: Audio | None = None
	"""L'antenne, écoutée sur son port de monitoring (https://github.com/dascritch/machincast/issues/24) ; None pour
	un sonore."""
	plan: Plan | None = None
	"""Ce que l'antenne fera d'un fichier de durée connue, montré par sa frise
	(https://github.com/dascritch/machincast/issues/224) ; None pour un stream, ou sans durée."""


def ecrire_preecoute(chemin: Path, identifiant: str) -> None:
	"""audio.preecoute dans le fichier de configuration, qui garde ses commentaires et ses autres réglages."""
	document = tomlkit.parse(chemin.read_text(encoding="utf-8"))
	audio = document["audio"]
	assert isinstance(audio, tomlkit.items.Table)
	audio["preecoute"] = identifiant
	chemin.write_text(tomlkit.dumps(document), encoding="utf-8")


def lire_source(
	connexion: psycopg.Connection[TupleRow], sonore: int, defauts: Crossfades | None = None
) -> Source | None:
	"""Le fichier ou l'adresse du sonore, ce qui le nomme, et pour un fichier, le plan de sa frise, ses crossfades non
	paramétrés pris dans defauts ; None s'il n'est plus en base."""
	with connexion.transaction():
		ligne = connexion.execute(
			"SELECT s.type::text, s.emplacement, coalesce(s.url_stream, m.url), s.artiste, s.titre,"
			" extract(epoch FROM s.duree), s.duree, s.debut_detecte, s.fin_detectee, s.detection_silences,"
			" s.crossfade_debut, s.crossfade_fin, s.audite_le IS NOT NULL"
			" FROM sonores s LEFT JOIN feeds m ON m.id = s.feed_id WHERE s.id = %s",
			(sonore,),
		).fetchone()
	if ligne is None:
		return None
	type_du_sonore, emplacement, url, artiste, titre, duree, intervalle, *details = ligne
	stream = type_du_sonore == "stream"
	adresse = str((emplacement) or (""))
	if stream:
		adresse = str((url) or (""))
	nom = affichage.nom_du_sonore(artiste, titre, emplacement, url)
	secondes = None
	if duree is not None:
		secondes = float(str(duree))
	plan = None
	if (not stream) and (isinstance(intervalle, timedelta)):
		debut_detecte, fin_detectee, detection, crossfade_debut, crossfade_fin, audite = details
		plan = plan_du_sonore(
			intervalle,
			_intervalle(debut_detecte),
			_intervalle(fin_detectee),
			bool(detection),
			_intervalle(crossfade_debut),
			_intervalle(crossfade_fin),
			(defauts) or (Crossfades()),
			bool(audite),
		)
	return Source(nom, adresse, stream, secondes, plan=plan)


def _intervalle(valeur: object) -> timedelta | None:
	if isinstance(valeur, timedelta):
		return valeur
	return None


class Lecteur:
	"""Le pipeline de la pré-écoute : un seul sonore à la fois, sur le périphérique de pré-écoute."""

	def __init__(self, sortie: SortieAudio, peripherique: str) -> None:
		Gst.init(None)
		self.sortie = sortie
		self.peripherique = peripherique
		self.source: Source | None = None
		self._pipeline: Gst.Element | None = None
		self._pilote: etats.Pilote | None = None
		"""Les changements d'état du pipeline, hors du fil de l'interface (https://github.com/dascritch/machincast/issues/259)."""
		self._niveau: Gst.Element | None = None
		self._liens: list[liaison.Paire] = []
		"""Les liens de PipeWire qui copient l'antenne sur la pré-écoute, tant qu'elle joue."""
		self.etat = "arret"
		self.niveaux: list[float] = []
		"""Niveau RMS de chaque canal, en décibels ; vide à l'arrêt."""
		self.erreur: str | None = None
		self.codec: str | None = None
		self.debit: int | None = None
		"""Débit annoncé par les tags, en bits par seconde."""
		self.frequence: int | None = None
		self.canaux: int | None = None
		self.comme_a_l_antenne = False
		"""Ne jouer que la partie jouée à l'antenne, au volume de ses fondus
		(https://github.com/dascritch/machincast/issues/224)."""
		self.volume = 1.0
		"""Volume de la lecture, de 0 à 1 : plein, sauf écouté comme à l'antenne."""
		self.derniere_position: float | None = None
		"""La dernière position relevée pendant la lecture, gardée après l'arrêt."""

	def charger(self, source: Source | None) -> None:
		self.arreter()
		self.derniere_position = None
		self.source = source
		self.erreur = None
		self.codec, self.debit, self.frequence, self.canaux = None, None, None, None

	def changer_de_sortie(self, peripherique: str) -> None:
		self.arreter()
		self.peripherique = peripherique

	def actif(self) -> bool:
		return self._pipeline is not None

	def lire(self) -> None:
		if self.source is None:
			return
		if (not self.source.stream) and (not Path(self.source.adresse).is_file()):
			self.erreur = f"fichier introuvable, {self.source.adresse}"
			return
		depuis_le_debut = self._pipeline is None
		if self._pipeline is None:
			self.erreur = None
			try:
				self._pipeline = self._construire(self.source)
			except Indisponible as erreur:
				self.erreur = str(erreur)
				return
			self._pilote = etats.Pilote(self._pipeline)
		plan = self._plan_a_l_antenne()
		if plan is not None:
			self._regler_le_volume(plan.volume(plan.repere_de_debut()))
		assert self._pilote is not None
		self._pilote.vers(Gst.State.PLAYING)
		self.etat = "lecture"
		if (plan is not None) and (depuis_le_debut):
			self.placer_a(plan.repere_de_debut())
		antenne = self._antenne_par_pipewire(self.source.antenne)
		if (antenne is not None) and (not self._liens):
			try:
				self._liens = liaison.paires(antenne, self.peripherique)
				liaison.relier(self._liens)
			except liaison.LiaisonImpossible as erreur:
				self.arreter()
				self.erreur = str(erreur)

	def mettre_en_pause(self) -> None:
		if self._pilote is not None:
			self._pilote.vers(Gst.State.PAUSED)
			self.etat = "pause"
		self._delier()

	def arreter(self) -> None:
		self._delier()
		if self._pilote is not None:
			self._pilote.eteindre()
		self._pipeline, self._pilote, self._niveau = None, None, None
		self.etat = "arret"
		self.niveaux = []

	def _delier(self) -> None:
		liaison.delier(self._liens)
		self._liens = []

	def _antenne_par_pipewire(self, antenne: Audio | None) -> str | None:
		"""Le périphérique de l'antenne, quand elle s'écoute par un lien de PipeWire : sur la sortie pipewire, qui est
		aussi celle de la pré-écoute."""
		if (antenne is None) or (antenne.sortie != "pipewire"):
			return None
		return antenne.peripherique

	def placer_a(self, position: float) -> None:
		"""Va à cette position du fichier, en secondes ; écouté comme à l'antenne, dans sa partie jouée."""
		duree = self.duree()
		if (self._pipeline is None) or (duree is None):
			return
		plan = self._plan_a_l_antenne()
		if plan is not None:
			de, a = plan.partie()
			position = max(de, min(a, position))
		instant = round(max(0.0, min(duree, position)) * Gst.SECOND)
		# Un déplacement demandé pendant un changement d'état (une pause qui s'installe) serait perdu : il attend sa
		# fin, une demi-seconde au plus, après que son pilote l'a demandé, une demi-seconde au plus.
		if self._pilote is not None:
			self._pilote.attendre(0.5)
		self._pipeline.get_state(Gst.SECOND // 2)
		self._pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE, instant)

	def position(self) -> float | None:
		if self._pipeline is None:
			return None
		trouvee, position = self._pipeline.query_position(Gst.Format.TIME)
		if not trouvee:
			return None
		return position / Gst.SECOND

	def duree(self) -> float | None:
		"""Durée du fichier selon GStreamer, sinon celle de la base ; aucune pour un stream."""
		if (self.source is None) or (self.source.stream):
			return None
		if self._pipeline is not None:
			trouvee, duree = self._pipeline.query_duration(Gst.Format.TIME)
			if (trouvee) and (duree > 0):
				return duree / Gst.SECOND
		return self.source.duree

	def predecode(self) -> float | None:
		"""Secondes de son reçues d'avance par un stream, d'après le remplissage de son tampon ; None pour un fichier,
		ou si GStreamer ne le dit pas."""
		if (self._pipeline is None) or (self.source is None) or (not self.source.stream):
			return None
		requete = Gst.Query.new_buffering(Gst.Format.TIME)
		if not self._pipeline.query(requete):
			return None
		_occupe, pourcentage = requete.parse_buffering_percent()
		return pourcentage / 100 * TAMPON_DES_STREAMS

	def debit_en_kbits(self) -> str | None:
		"""« 320 kbit/s » des tags, sinon « ≈ 705 kbit/s » d'après la taille du fichier sur sa durée."""
		if self.debit is not None:
			return f"{round(self.debit / 1000)} kbit/s"
		duree = self.duree()
		if (self.source is None) or (self.source.stream) or (not duree):
			return None
		try:
			taille = Path(self.source.adresse).stat().st_size
		except OSError:
			return None
		return f"≈ {round(taille * 8 / duree / 1000)} kbit/s"

	def relever(self) -> None:
		"""Les messages de GStreamer : niveaux, tags, fin et erreurs."""
		pipeline = self._pipeline
		if pipeline is None:
			return
		bus = pipeline.get_bus()
		assert bus is not None
		while (message := bus.pop()) is not None:
			if message.type == Gst.MessageType.EOS:
				self.arreter()
				return
			if message.type == Gst.MessageType.ERROR:
				erreur, _detail = message.parse_error()
				self.arreter()
				self.erreur = str(erreur.message)
				return
			if message.type == Gst.MessageType.TAG:
				self._lire_les_tags(message.parse_tag())
			if (message.type == Gst.MessageType.ELEMENT) and (message.src == self._niveau):
				self._lire_les_niveaux(message.get_structure())
		self._lire_le_format()
		self._suivre_la_partie_jouee()

	def _plan_a_l_antenne(self) -> Plan | None:
		"""Le plan du fichier, s'il est écouté comme à l'antenne ; None sinon."""
		if (not self.comme_a_l_antenne) or (self.source is None) or (self.source.antenne is not None):
			return None
		return self.source.plan

	def _regler_le_volume(self, volume: float) -> None:
		self.volume = volume
		if (self._pipeline is not None) and (self.source is not None) and (self.source.antenne is None):
			self._pipeline.set_property("volume", volume)

	def _suivre_la_partie_jouee(self) -> None:
		"""Note la position ; écouté comme à l'antenne, règle le volume de l'enveloppe, et s'arrête à la fin de la
		partie jouée. Sinon, le volume est plein."""
		position = self.position()
		if (self.etat == "lecture") and (position is not None):
			self.derniere_position = position
		plan = self._plan_a_l_antenne()
		if plan is None:
			if self.volume != 1.0:
				self._regler_le_volume(1.0)
			return
		if (position is None) or (self.etat != "lecture"):
			return
		_de, a = plan.partie()
		if (a < plan.duree) and (position >= a):
			self.arreter()
			return
		self._regler_le_volume(plan.volume(position))

	def _construire(self, source: Source) -> Gst.Element:
		if source.antenne is not None:
			return self._construire_l_ecoute(source.antenne)
		lecteur = Gst.ElementFactory.make(LECTEUR, None)
		niveau = Gst.ElementFactory.make("level", None)
		assert (lecteur is not None) and (niveau is not None), "installer gstreamer1.0-plugins-base et -good"
		niveau.set_property("interval", INTERVALLE_DES_NIVEAUX)
		niveau.set_property("post-messages", True)
		sortie = creer_sortie(self.sortie, self.peripherique, presentation=PREECOUTE)
		if self.sortie == "factice":
			# La sortie factice joue au rythme du temps réel, comme un vrai périphérique.
			sortie.set_property("sync", True)
		lecteur.set_property("audio-filter", niveau)
		lecteur.set_property("audio-sink", sortie)
		adresse = source.adresse
		if source.stream:
			lecteur.set_property("buffer-duration", TAMPON_DES_STREAMS * Gst.SECOND)
		else:
			adresse = str(Gst.filename_to_uri(adresse))
		lecteur.set_property("uri", adresse)
		self._niveau = niveau
		return lecteur

	def _construire_l_ecoute(self, antenne: Audio) -> Gst.Element:
		"""Le port de monitoring de l'antenne, joué sur la sortie de pré-écoute. Sous PipeWire, le son passe par un
		lien (machincast.interface.liaison) : le pipeline ne fait que mesurer, pour le VU-mètre."""
		pipeline = Gst.Pipeline.new("ecoute-antenne")
		sortie = Gst.ElementFactory.make("fakesink", None)
		assert sortie is not None
		sortie.set_property("sync", False)
		if self._antenne_par_pipewire(antenne) is None:
			sortie = creer_sortie(self.sortie, self.peripherique, presentation=PREECOUTE)
		crees = [
			source_du_moniteur(antenne),
			Gst.ElementFactory.make("audioconvert", None),
			Gst.ElementFactory.make("audioresample", None),
			Gst.ElementFactory.make("level", None),
			sortie,
		]
		# ElementFactory.make rend None pour un élément introuvable : pygobject-stubs le type ainsi depuis sa
		# version 2.19, et mypy refuse alors de l'ajouter au pipeline sans l'avoir écarté.
		elements = [element for element in crees if element is not None]
		assert len(elements) == len(crees), "installer gstreamer1.0-plugins-base et -good"
		niveau = elements[3]
		niveau.set_property("interval", INTERVALLE_DES_NIVEAUX)
		niveau.set_property("post-messages", True)
		for element in elements:
			pipeline.add(element)
		for avant, apres in zip(elements, elements[1:], strict=False):
			avant.link(apres)
		self._niveau = niveau
		return pipeline

	def _lire_les_tags(self, tags: Gst.TagList) -> None:
		trouve, codec = tags.get_string(Gst.TAG_AUDIO_CODEC)
		if trouve:
			self.codec = codec
		for nom in (Gst.TAG_BITRATE, Gst.TAG_NOMINAL_BITRATE):
			trouve, debit = tags.get_uint(nom)
			if (trouve) and (debit > 0):
				self.debit = int(debit)
				return

	def _lire_les_niveaux(self, structure: Gst.Structure | None) -> None:
		if (structure is None) or (structure.get_name() != "level"):
			return
		valeurs = structure.get_value("rms")
		if valeurs is not None:
			self.niveaux = [float(valeur) for valeur in valeurs]

	def _lire_le_format(self) -> None:
		if (self._niveau is None) or ((self.frequence is not None) and (self.canaux is not None)):
			return
		entree = self._niveau.get_static_pad("sink")
		caps = None
		if entree is not None:
			caps = entree.get_current_caps()
		if (caps is None) or (caps.get_size() == 0):
			return
		structure = caps.get_structure(0)
		trouvee, frequence = structure.get_int("rate")
		if trouvee:
			self.frequence = frequence
		trouves, canaux = structure.get_int("channels")
		if trouves:
			self.canaux = canaux


EN_COURS = "en cours : "
"""Début du titre de l'écoute de l'antenne, suivi du texte public du sonore en cours."""


class FenetrePreecoute(QWidget):
	"""La fenêtre de pré-écoute : indépendante, elle ne se ferme pas avec la fiche qui l'a ouverte."""

	ecoute_changee = Signal(bool)
	"""L'écoute de l'antenne commence (vrai) ou cesse (faux) : lecture lancée, arrêtée, fenêtre fermée ou autre
	sonore (https://github.com/dascritch/machincast/issues/256)."""

	def __init__(
		self,
		connexion: psycopg.Connection[TupleRow],
		audio: Audio,
		configuration: Path | None = None,
		parent: QWidget | None = None,
	) -> None:
		super().__init__(parent, Qt.WindowType.Window)
		self.connexion = connexion
		self.audio = audio
		self.configuration = configuration
		self.ui = Ui_FenetrePreecoute()
		self.ui.setupUi(self)
		self.vumetre = VuMetre(self.ui.place_vumetre)
		self.ui.place_vumetre.setMinimumHeight(48)
		self.ui.place_vumetre.setMaximumHeight(56)
		disposition = QVBoxLayout(self.ui.place_vumetre)
		disposition.setContentsMargins(0, 0, 0, 0)
		disposition.addWidget(self.vumetre)
		self.frise = Frise(self.ui.place_frise)
		disposition_de_la_frise = QVBoxLayout(self.ui.place_frise)
		disposition_de_la_frise.setContentsMargins(0, 0, 0, 0)
		disposition_de_la_frise.addWidget(self.frise)
		self.forme: FormeDOnde | None = None
		"""La forme d'onde du fichier, calculée en tâche de fond (https://github.com/dascritch/machincast/issues/224)."""
		self.lecteur = Lecteur(audio.sortie, audio.preecoute)
		self._garnir_les_sorties()
		self.ui.sortie.currentIndexChanged.connect(self._changer_de_sortie)
		self.ui.lecture.clicked.connect(self._lire_ou_mettre_en_pause)
		self.ui.arret.clicked.connect(self._arreter)
		self.frise.placee.connect(self._placer)
		self.ui.debut_joue.clicked.connect(lambda: self._aller_au_repere(debut=True))
		self.ui.fin_jouee.clicked.connect(lambda: self._aller_au_repere(debut=False))
		self.ui.comme_a_l_antenne.toggled.connect(self._ecouter_comme_a_l_antenne)
		self._releve = QTimer(self)
		self._releve.setInterval(RELEVE)
		self._releve.timeout.connect(self._rafraichir)
		self._releve.start()
		self.a_l_antenne = False
		"""La fenêtre écoute l'antenne : son titre suit le texte public du sonore en cours."""
		self._ecoute_annoncee = False
		self.preecouter(None)

	def ecoute_l_antenne(self) -> bool:
		"""L'antenne est chargée, et sa lecture lancée, ou en pause."""
		return (self.a_l_antenne) and (self.lecteur.actif())

	def arreter(self) -> None:
		"""Arrête la lecture, comme le bouton « ⏹ »."""
		self._arreter()

	def preecouter(self, sonore: int | None) -> None:
		"""Le sonore à pré-écouter, à l'arrêt, à la place du précédent ; None : aucun."""
		self.a_l_antenne = False
		source = None
		if sonore is not None:
			source = lire_source(self.connexion, sonore, preferences.crossfades())
		self.lecteur.charger(source)
		self._montrer_la_frise(source)
		self.setWindowTitle("Pré-écoute")
		self.ui.source.setText(affichage.VIDE)
		if source is not None:
			self.setWindowTitle(f"Pré-écoute : {source.titre}")
			self.ui.source.setText(source.adresse)
		self.ui.message.clear()
		self._rafraichir()

	def ecouter_l_antenne(self, texte_public: str | None, lancer: bool = False) -> None:
		"""L'antenne, sur son port de monitoring, à la place du sonore précédent : à l'arrêt, ou lancée aussitôt. Le
		titre de la fenêtre est « en cours : » et le texte public du sonore en cours
		(https://github.com/dascritch/machincast/issues/223)."""
		nom = nom_du_port(self.audio)
		source = Source("Antenne", f"Antenne : {nom}", True, None, self.audio)
		self.lecteur.charger(source)
		self._montrer_la_frise(source)
		self.a_l_antenne = True
		self.suivre_l_antenne(texte_public)
		self.ui.source.setText(f"Antenne : {nom}")
		self.ui.message.clear()
		if lancer:
			self._lire_ou_mettre_en_pause()
		self._rafraichir()

	def suivre_l_antenne(self, texte_public: str | None) -> None:
		"""Le texte public du sonore en cours a changé : le titre le suit, tant que la fenêtre écoute l'antenne."""
		if self.a_l_antenne:
			self.setWindowTitle(f"{EN_COURS}{(texte_public) or (affichage.VIDE)}")

	def _montrer_la_frise(self, source: Source | None) -> None:
		"""La frise d'un fichier, et le calcul de sa forme d'onde, lancé en tâche de fond ; rien pour un stream."""
		self._arreter_la_forme()
		fichier = (source is not None) and (not source.stream)
		self.ui.zone_frise.setVisible(fichier)
		plan = None
		duree = None
		if (source is not None) and (fichier):
			plan, duree = source.plan, source.duree
			self.forme = FormeDOnde(Path(source.adresse), duree)
			self.forme.demarrer()
		self.frise.montrer(plan, duree)
		self.frise.montrer_la_forme(self.forme)
		resume = ""
		if plan is not None:
			resume = plan.resume()
		self.ui.plage.setText(resume)
		for commande in (self.ui.debut_joue, self.ui.fin_jouee, self.ui.comme_a_l_antenne):
			commande.setEnabled(plan is not None)

	def _arreter_la_forme(self) -> None:
		if self.forme is not None:
			self.forme.arreter()
		self.forme = None

	def closeEvent(self, evenement: QCloseEvent) -> None:
		self._arreter_la_forme()
		self.lecteur.arreter()
		self._rafraichir()
		super().closeEvent(evenement)

	def _garnir_les_sorties(self) -> None:
		"""Le périphérique configuré d'abord, puis les autres du poste, dans leur ordre. Celui de la diffusion y est,
		grisé : il ne peut pas être choisi."""
		choix = self.ui.sortie
		trouves = sorties_audio.peripheriques(self.audio.sortie)
		configure = next((p for p in trouves if p.identifiant == self.audio.preecoute), None)
		nom = f"{self.audio.preecoute} (introuvable)"
		if configure is not None:
			nom = configure.nom
		choix.addItem(nom, self.audio.preecoute)
		modele = choix.model()
		assert isinstance(modele, QStandardItemModel)
		for peripherique in trouves:
			if peripherique.identifiant == self.audio.preecoute:
				continue
			if peripherique.identifiant != self.audio.peripherique:
				choix.addItem(peripherique.nom, peripherique.identifiant)
				continue
			choix.addItem(f"{peripherique.nom} {DIFFUSION}", peripherique.identifiant)
			ligne = modele.item(choix.count() - 1)
			ligne.setEnabled(False)
			ligne.setToolTip("Le périphérique de la diffusion ne peut pas servir à la pré-écoute.")

	def _changer_de_sortie(self) -> None:
		identifiant = str(self.ui.sortie.currentData())
		if identifiant == self.audio.peripherique:
			# Jamais la sortie de la diffusion, même choisie autrement qu'à la souris : retour à la précédente.
			self.ui.sortie.setCurrentIndex(self.ui.sortie.findData(self.lecteur.peripherique))
			self.ui.message.setText("Le périphérique de la diffusion ne peut pas servir à la pré-écoute.")
			return
		self.lecteur.changer_de_sortie(identifiant)
		texte = "Sortie de pré-écoute changée pour cette session."
		if self.configuration is not None:
			try:
				ecrire_preecoute(self.configuration, identifiant)
			except OSError as erreur:
				texte = f"Sortie de pré-écoute non enregistrée dans {self.configuration} : {erreur}"
			else:
				texte = f"Sortie de pré-écoute enregistrée dans {self.configuration}."
		self.ui.message.setText(texte)
		self._rafraichir()

	def _lire_ou_mettre_en_pause(self) -> None:
		if self.lecteur.etat == "lecture":
			self.lecteur.mettre_en_pause()
		else:
			self.ui.message.clear()
			self.lecteur.lire()
		self._rafraichir()

	def _arreter(self) -> None:
		self.lecteur.arreter()
		self._rafraichir()

	def _placer(self, position: float) -> None:
		self.lecteur.placer_a(position)
		self._rafraichir()

	def _aller_au_repere(self, debut: bool) -> None:
		"""« Début joué » ou « Fin jouée » : la lecture y va, lancée au besoin."""
		source = self.lecteur.source
		if (source is None) or (source.plan is None):
			return
		repere = source.plan.repere_de_fin()
		if debut:
			repere = source.plan.repere_de_debut()
		if self.lecteur.etat != "lecture":
			self.ui.message.clear()
			self.lecteur.lire()
		self.lecteur.placer_a(repere)
		self._rafraichir()

	def _ecouter_comme_a_l_antenne(self, coche: bool) -> None:
		self.lecteur.comme_a_l_antenne = coche
		self._rafraichir()

	def _rafraichir(self) -> None:
		lecteur = self.lecteur
		lecteur.relever()
		if self.ecoute_l_antenne() != self._ecoute_annoncee:
			self._ecoute_annoncee = self.ecoute_l_antenne()
			self.ecoute_changee.emit(self._ecoute_annoncee)
		ui = self.ui
		source = lecteur.source
		if lecteur.erreur is not None:
			ui.message.setText(f"Lecture impossible : {lecteur.erreur}")
		ui.etat.setText(ETATS[lecteur.etat])
		if source is None:
			ui.etat.setText(AUCUN)
		ui.lecture.setEnabled(source is not None)
		bouton = LECTURE
		if lecteur.etat == "lecture":
			bouton = PAUSE
		ui.lecture.setText(bouton[0])
		ui.lecture.setToolTip(bouton[1])
		ui.lecture.setAccessibleName(bouton[1])
		ui.arret.setEnabled(lecteur.actif())
		duree = lecteur.duree()
		self.frise.setEnabled((lecteur.actif()) and (duree is not None))
		ui.temps.setText(self._temps(duree))
		tete = None
		if lecteur.actif():
			tete = lecteur.position()
		self.frise.placer_la_tete(tete)
		if (self.forme is not None) and (self.forme.relever()):
			self.frise.update()
		self.vumetre.montrer(lecteur.niveaux)
		ui.format.setText((lecteur.codec) or (affichage.VIDE))
		ui.debit.setText((lecteur.debit_en_kbits()) or (affichage.VIDE))
		ui.echantillonnage.setText(affichage.VIDE)
		if lecteur.frequence is not None:
			ui.echantillonnage.setText(f"{lecteur.frequence:,} Hz".replace(",", " "))
		ui.canaux.setText(affichage.VIDE)
		if lecteur.canaux is not None:
			ui.canaux.setText(CANAUX.get(lecteur.canaux, f"{lecteur.canaux} canaux"))
		ui.predecode.setText(affichage.VIDE)
		predecode = lecteur.predecode()
		if predecode is not None:
			ui.predecode.setText(f"{predecode:.1f} s".replace(".", ","))

	def _temps(self, duree: float | None) -> str:
		"""« 0:12 / 3:34 » pour un fichier ; la position seule pour un stream en lecture ; « — » sinon."""
		lecteur = self.lecteur
		position = lecteur.position()
		if (lecteur.source is None) or ((duree is None) and (position is None)):
			return affichage.VIDE
		if duree is None:
			return affichage.duree(position)
		# Une durée se compte à la seconde entamée : un fichier de 0,998 seconde dure « 0:01 ».
		return f"{affichage.duree((position) or (0))} / {affichage.duree(math.ceil(duree))}"
