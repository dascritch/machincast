"""Pré-écoute d'un sonore (https://github.com/dascritch/machincast/issues/116,
https://github.com/dascritch/machincast/issues/29, spec § 8.3).

Une fenêtre indépendante, une seule pour toute l'interface (FenetrePrincipale.preecoute) : la fiche d'un sonore
y envoie son sonore, qui remplace le précédent, à l'arrêt ; le menu « Affichage » l'ouvre sans sonore, pour choisir
sa sortie. Son lecteur est un pipeline playbin de GStreamer, dont le bus est relevé par un minuteur de Qt : rien ne
bloque l'interface.

- Sortie : le périphérique de pré-écoute de la configuration (audio.preecoute), sur la sortie de l'antenne
  (audio.sortie), jamais le périphérique de l'antenne. Le choix liste les périphériques du poste (peripheriques), celui
  de l'antenne grisé ; un périphérique configuré mais absent reste proposé. Le choix s'enregistre dans le fichier de
  configuration (ecrire_preecoute), qui garde ses commentaires, et arrête la lecture en cours.
- Lecteur : lecture et pause, arrêt, qui ramène au début, et barre de position, pendant la lecture d'un fichier ou sa
  pause. Un stream n'a pas de position. La fin du fichier ramène à l'arrêt ; une erreur aussi, et elle est signalée.
- VU-mètre : le niveau RMS de chaque canal, par l'élément level de GStreamer, en décibels.
- Informations : format (codec), débit (celui des tags, sinon la taille du fichier sur sa durée), échantillonnage,
  canaux, et pour un stream, les secondes pré-décodées : le son reçu d'avance, que GStreamer garde en mémoire.

L'écoute de l'antenne viendra avec le VU-mètre de la sortie (https://github.com/dascritch/machincast/issues/24).
"""

import math
from dataclasses import dataclass
from pathlib import Path

import gi
import psycopg
import tomlkit
from psycopg.rows import TupleRow

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QCloseEvent, QStandardItemModel  # noqa: E402
from PySide6.QtWidgets import QVBoxLayout, QWidget  # noqa: E402

from machincast import audio as sorties_audio  # noqa: E402
from machincast.audio import creer_sortie  # noqa: E402
from machincast.configuration import Audio, SortieAudio  # noqa: E402
from machincast.interface import affichage  # noqa: E402
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


def ecrire_preecoute(chemin: Path, identifiant: str) -> None:
	"""audio.preecoute dans le fichier de configuration, qui garde ses commentaires et ses autres réglages."""
	document = tomlkit.parse(chemin.read_text(encoding="utf-8"))
	audio = document["audio"]
	assert isinstance(audio, tomlkit.items.Table)
	audio["preecoute"] = identifiant
	chemin.write_text(tomlkit.dumps(document), encoding="utf-8")


def lire_source(connexion: psycopg.Connection[TupleRow], sonore: int) -> Source | None:
	"""Le fichier ou l'adresse du sonore, et ce qui le nomme ; None s'il n'est plus en base."""
	with connexion.transaction():
		ligne = connexion.execute(
			"SELECT s.type::text, s.emplacement, coalesce(s.url_stream, m.url), s.artiste, s.titre,"
			" extract(epoch FROM s.duree)"
			" FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id WHERE s.id = %s",
			(sonore,),
		).fetchone()
	if ligne is None:
		return None
	type_du_sonore, emplacement, url, artiste, titre, duree = ligne
	stream = type_du_sonore == "stream"
	adresse = str((emplacement) or (""))
	if stream:
		adresse = str((url) or (""))
	nom = affichage.nom_du_sonore(artiste, titre, emplacement, url)
	secondes = None
	if duree is not None:
		secondes = float(str(duree))
	return Source(nom, adresse, stream, secondes)


class Lecteur:
	"""Le pipeline de la pré-écoute : un seul sonore à la fois, sur le périphérique de pré-écoute."""

	def __init__(self, sortie: SortieAudio, peripherique: str) -> None:
		Gst.init(None)
		self.sortie = sortie
		self.peripherique = peripherique
		self.source: Source | None = None
		self._pipeline: Gst.Element | None = None
		self._niveau: Gst.Element | None = None
		self.etat = "arret"
		self.niveaux: list[float] = []
		"""Niveau RMS de chaque canal, en décibels ; vide à l'arrêt."""
		self.erreur: str | None = None
		self.codec: str | None = None
		self.debit: int | None = None
		"""Débit annoncé par les tags, en bits par seconde."""
		self.frequence: int | None = None
		self.canaux: int | None = None

	def charger(self, source: Source | None) -> None:
		self.arreter()
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
		if self._pipeline is None:
			self.erreur = None
			try:
				self._pipeline = self._construire(self.source)
			except Indisponible as erreur:
				self.erreur = str(erreur)
				return
		self._pipeline.set_state(Gst.State.PLAYING)
		self.etat = "lecture"

	def mettre_en_pause(self) -> None:
		if self._pipeline is not None:
			self._pipeline.set_state(Gst.State.PAUSED)
			self.etat = "pause"

	def arreter(self) -> None:
		if self._pipeline is not None:
			self._pipeline.set_state(Gst.State.NULL)
		self._pipeline, self._niveau = None, None
		self.etat = "arret"
		self.niveaux = []

	def placer(self, fraction: float) -> None:
		"""Va à cette fraction du fichier, de 0 à 1."""
		duree = self.duree()
		if (self._pipeline is None) or (duree is None):
			return
		instant = round(max(0.0, min(1.0, fraction)) * duree * Gst.SECOND)
		# Un déplacement demandé pendant un changement d'état (une pause qui s'installe) serait perdu : il attend sa
		# fin, une demi-seconde au plus.
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

	def _construire(self, source: Source) -> Gst.Element:
		if source.antenne is not None:
			return self._construire_l_ecoute(source.antenne)
		lecteur = Gst.ElementFactory.make("playbin", None)
		niveau = Gst.ElementFactory.make("level", None)
		assert (lecteur is not None) and (niveau is not None), "installer gstreamer1.0-plugins-base et -good"
		niveau.set_property("interval", INTERVALLE_DES_NIVEAUX)
		niveau.set_property("post-messages", True)
		sortie = creer_sortie(self.sortie, self.peripherique)
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
		"""Le port de monitoring de l'antenne, joué sur la sortie de pré-écoute."""
		pipeline = Gst.Pipeline.new("ecoute-antenne")
		elements = [
			source_du_moniteur(antenne),
			Gst.ElementFactory.make("audioconvert", None),
			Gst.ElementFactory.make("audioresample", None),
			Gst.ElementFactory.make("level", None),
			creer_sortie(self.sortie, self.peripherique),
		]
		assert all(element is not None for element in elements), "installer gstreamer1.0-plugins-base et -good"
		niveau = elements[3]
		assert niveau is not None
		niveau.set_property("interval", INTERVALLE_DES_NIVEAUX)
		niveau.set_property("post-messages", True)
		for element in elements:
			pipeline.add(element)
		for avant, apres in zip(elements, elements[1:], strict=False):
			assert (avant is not None) and (apres is not None)
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


class FenetrePreecoute(QWidget):
	"""La fenêtre de pré-écoute : indépendante, elle ne se ferme pas avec la fiche qui l'a ouverte."""

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
		self.lecteur = Lecteur(audio.sortie, audio.preecoute)
		self._garnir_les_sorties()
		self.ui.sortie.currentIndexChanged.connect(self._changer_de_sortie)
		self.ui.lecture.clicked.connect(self._lire_ou_mettre_en_pause)
		self.ui.arret.clicked.connect(self._arreter)
		self.ui.position.sliderReleased.connect(self._placer)
		self._releve = QTimer(self)
		self._releve.setInterval(RELEVE)
		self._releve.timeout.connect(self._rafraichir)
		self._releve.start()
		self.preecouter(None)

	def preecouter(self, sonore: int | None) -> None:
		"""Le sonore à pré-écouter, à l'arrêt, à la place du précédent ; None : aucun."""
		source = None
		if sonore is not None:
			source = lire_source(self.connexion, sonore)
		self.lecteur.charger(source)
		self.setWindowTitle("Pré-écoute")
		self.ui.source.setText(affichage.VIDE)
		if source is not None:
			self.setWindowTitle(f"Pré-écoute : {source.titre}")
			self.ui.source.setText(source.adresse)
		self.ui.message.clear()
		self._rafraichir()

	def ecouter_l_antenne(self) -> None:
		"""L'antenne, sur son port de monitoring, à la place du sonore précédent, à l'arrêt."""
		nom = nom_du_port(self.audio)
		self.lecteur.charger(Source("Antenne", f"Antenne : {nom}", True, None, self.audio))
		self.setWindowTitle("Pré-écoute : Antenne")
		self.ui.source.setText(f"Antenne : {nom}")
		self.ui.message.clear()
		self._rafraichir()

	def closeEvent(self, evenement: QCloseEvent) -> None:
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

	def _placer(self) -> None:
		barre = self.ui.position
		self.lecteur.placer(barre.value() / barre.maximum())

	def _rafraichir(self) -> None:
		lecteur = self.lecteur
		lecteur.relever()
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
		ui.position.setEnabled((lecteur.actif()) and (duree is not None))
		ui.temps.setText(self._temps(duree))
		if (duree) and (not ui.position.isSliderDown()):
			ui.position.setValue(round(((lecteur.position()) or (0.0)) / duree * ui.position.maximum()))
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
