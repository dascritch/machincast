"""Choix des cartes son de l'antenne et de la pré-écoute (https://github.com/dascritch/machincast/issues/339,
spec § 8.10 et § 8.11).

Le bloc CartesSon sert à la page « Audio » des préférences (machincast.interface.preferences) et à la fenêtre « Pour
bien démarrer » (machincast.interface.suggestions). Il choisit :

- le type de sortie (audio.output) : PipeWire, PulseAudio ou ALSA ; la sortie factice des essais n'est proposée que si
  elle est déjà configurée. Un autre type relit les cartes du poste : l'antenne reste à renseigner, sauf sur la sortie
  factice ; la pré-écoute garde sa carte si elle y est ;
- la carte son de l'antenne (audio.device) et celle de la pré-écoute (audio.preview), chacune parmi les
  périphériques du poste (machincast.audio.peripheriques), la carte configurée en tête, et l'entrée « Sortie factice »
  (configuration.FACTICE). La carte choisie pour l'une est grisée dans l'autre, sortie factice comprise.

Le service de diffusion (machincast.service.EtatDuService), lu par la fenêtre qui ouvre le bloc :

- installé, l'antenne ne prend pas la sortie factice : seule une installation provisoire, sans service, le peut ;
- en marche, le type de sortie, la carte de l'antenne et son bouton « Tester » sont grisés, avec une infobulle qui dit
  d'arrêter la diffusion.

« Tester » joue le son de test (son_de_test) sur la carte de sa ligne : 2 secondes de sinusoïde à 1000 Hz, à -3 dB,
présenté au serveur audio comme « MachinCast interface », flux « Son de test ». Le pipeline change d'état par son
pilote (machincast.interface.etats.Pilote), jamais dans le fil de l'interface, et son bus est relevé par un minuteur
de Qt. Pendant le son, les deux boutons « Tester » sont grisés ; le bloc dit le son en cours, puis s'il a été joué. Un
bloc caché arrête son son de test.
"""

import time
from collections.abc import Callable

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PySide6.QtCore import QTimer, Signal  # noqa: E402
from PySide6.QtGui import QHideEvent, QStandardItemModel  # noqa: E402
from PySide6.QtWidgets import QComboBox, QPushButton, QWidget  # noqa: E402

from machincast import audio as sorties_audio  # noqa: E402
from machincast.audio import Presentation, SortieAudioIndisponible  # noqa: E402
from machincast.configuration import FACTICE, SortieAudio  # noqa: E402
from machincast.interface import etats  # noqa: E402
from machincast.interface.ui.cartes_son import Ui_CartesSon  # noqa: E402
from machincast.service import ABSENT, EtatDuService  # noqa: E402

TYPES: tuple[tuple[SortieAudio, str], ...] = (("pipewire", "PipeWire"), ("pulseaudio", "PulseAudio"), ("alsa", "ALSA"))
"""Les types de sortie proposés."""
TYPE_FACTICE: tuple[SortieAudio, str] = ("factice", "Factice, aucun son")
"""La sortie factice des essais : proposée seulement si elle est déjà configurée."""
SORTIE_FACTICE = "Sortie factice"
A_RENSEIGNER = "(à renseigner)"
"""L'antenne, tant qu'elle n'a pas de carte : Machin player refuse alors de diffuser."""
FACTICE_REFUSEE = (
	"Seulement sans service de diffusion installé : l'antenne d'un poste dédié joue toujours sur une carte son."
)
DIFFUSION_EN_MARCHE = "Arrêter la diffusion pour choisir la carte son de l'antenne."
SANS_CARTE = "Choisir d'abord une carte son."
SANS_SON = "La sortie factice ne joue aucun son."
TESTER = "Jouer 2 secondes de son de test sur cette carte : une sinusoïde à 1000 Hz, à -3 dB"

FREQUENCE = 1000
"""Hertz."""
NIVEAU = -3.0
"""Décibels pleine échelle."""
DUREE_DU_SON_DE_TEST = 2.0
"""Secondes ; les scénarios la raccourcissent."""
TAUX = 48000
ECHANTILLONS_PAR_TAMPON = 4800
"""Un dixième de seconde par tampon."""
MARGE = 5.0
"""Secondes au-delà de la durée du son au bout desquelles un son de test qui ne finit pas est abandonné."""
RELEVE = 50
"""Millisecondes entre deux relèves du bus du son de test."""
SON_DE_TEST = Presentation("MachinCast interface", "Son de test")

fabrique_de_sortie: Callable[..., Gst.Element] = sorties_audio.creer_sortie
"""La sortie du son de test ; les scénarios la remplacent par une sortie factice."""


def son_de_test(sortie: SortieAudio, peripherique: str) -> Gst.Pipeline:
	"""Le pipeline du son de test sur la carte ; lève SortieAudioIndisponible si sa sortie ne peut pas être créée."""
	Gst.init(None)
	pipeline = Gst.Pipeline.new("son-de-test")
	source = Gst.ElementFactory.make("audiotestsrc", "source")
	filtre = Gst.ElementFactory.make("capsfilter", None)
	conversion = Gst.ElementFactory.make("audioconvert", None)
	reechantillonnage = Gst.ElementFactory.make("audioresample", None)
	if (source is None) or (filtre is None) or (conversion is None) or (reechantillonnage is None):
		raise SortieAudioIndisponible(
			"audiotestsrc, audioconvert ou audioresample introuvable, installer gstreamer1.0-plugins-base"
		)
	source.set_property("wave", "sine")
	source.set_property("freq", float(FREQUENCE))
	source.set_property("volume", 10 ** (NIVEAU / 20))
	source.set_property("samplesperbuffer", ECHANTILLONS_PAR_TAMPON)
	source.set_property("num-buffers", max(1, round(DUREE_DU_SON_DE_TEST * TAUX / ECHANTILLONS_PAR_TAMPON)))
	filtre.set_property("caps", Gst.Caps.from_string(f"audio/x-raw,rate={TAUX},channels=2"))
	puits = fabrique_de_sortie(sortie, peripherique, presentation=SON_DE_TEST)
	puits.set_name("puits")
	for element in (source, filtre, conversion, reechantillonnage, puits):
		pipeline.add(element)
	source.link(filtre)
	filtre.link(conversion)
	conversion.link(reechantillonnage)
	reechantillonnage.link(puits)
	return pipeline


class CartesSon(QWidget):
	"""Le type de sortie, et les cartes son de l'antenne et de la pré-écoute, chacune avec son bouton « Tester »."""

	change = Signal()
	"""Un autre choix : la fenêtre revoit si elle peut l'enregistrer (valide)."""

	def __init__(
		self,
		sortie: SortieAudio,
		antenne: str | None,
		preecoute: str | None,
		service: EtatDuService = ABSENT,
		parent: QWidget | None = None,
		horloge: Callable[[], float] = time.monotonic,
	) -> None:
		super().__init__(parent)
		self.ui = Ui_CartesSon()
		self.ui.setupUi(self)
		self.service = service
		self.horloge = horloge
		"""L'horloge monotone du poste : un son de test qui ne finit pas est abandonné."""
		self._pipeline: Gst.Pipeline | None = None
		self._pilote: etats.Pilote | None = None
		self._carte = ""
		self._fin = 0.0
		self._releve = QTimer(self)
		self._releve.setInterval(RELEVE)
		self._releve.timeout.connect(self._relever)
		ui = self.ui
		types = list(TYPES)
		if sortie == "factice":
			types.append(TYPE_FACTICE)
		for valeur, texte in types:
			ui.sortie.addItem(texte, valeur)
		ui.sortie.setCurrentIndex(ui.sortie.findData(sortie))
		self._garnir_les_cartes(antenne, preecoute)
		ui.sortie.currentIndexChanged.connect(self._changer_de_type)
		ui.antenne.currentIndexChanged.connect(self._actualiser)
		ui.preecoute.currentIndexChanged.connect(self._actualiser)
		ui.tester_antenne.clicked.connect(lambda: self._tester(ui.antenne))
		ui.tester_preecoute.clicked.connect(lambda: self._tester(ui.preecoute))
		self._dire("")
		self._actualiser()

	# ─── Ce qui est choisi ─────────────────────────────────────

	def sortie_choisie(self) -> SortieAudio:
		sortie: SortieAudio = self.ui.sortie.currentData()
		return sortie

	def antenne_choisie(self) -> str | None:
		donnee = self.ui.antenne.currentData()
		if donnee is None:
			return None
		return str(donnee)

	def preecoute_choisie(self) -> str | None:
		donnee = self.ui.preecoute.currentData()
		if donnee is None:
			return None
		return str(donnee)

	def valide(self) -> bool:
		"""Une pré-écoute, sur une autre carte que l'antenne."""
		preecoute = self.preecoute_choisie()
		return (preecoute is not None) and (preecoute != self.antenne_choisie())

	# ─── Listes ────────────────────────────────────────────────

	def _garnir_les_cartes(self, antenne: str | None, preecoute: str | None) -> None:
		trouves = sorties_audio.peripheriques(self.sortie_choisie())
		for choix in (self.ui.antenne, self.ui.preecoute):
			choix.blockSignals(True)
			choix.clear()
		_garnir(self.ui.antenne, antenne, trouves)
		_garnir(self.ui.preecoute, preecoute, trouves)
		for choix in (self.ui.antenne, self.ui.preecoute):
			choix.blockSignals(False)

	def _changer_de_type(self) -> None:
		"""Les cartes du nouveau type : l'antenne reste à renseigner, sauf sur la sortie factice ; la pré-écoute garde
		la sienne si elle y est, sinon la première autre carte, sinon la sortie factice."""
		antenne = None
		if self.antenne_choisie() == FACTICE:
			antenne = FACTICE
		trouves = [p.identifiant for p in sorties_audio.peripheriques(self.sortie_choisie())]
		preecoute = self.preecoute_choisie()
		if (preecoute != FACTICE) and (preecoute not in trouves):
			preecoute = next((carte for carte in trouves if carte != antenne), FACTICE)
		self._garnir_les_cartes(antenne, preecoute)
		self._actualiser()

	def _actualiser(self) -> None:
		"""Grise ce qui ne peut pas être choisi, et les boutons qui ne peuvent pas servir."""
		ui = self.ui
		antenne, preecoute = self.antenne_choisie(), self.preecoute_choisie()
		_griser(ui.antenne, preecoute, refuser_factice=self.service.installe)
		_griser(ui.preecoute, antenne, refuser_factice=False)
		verrouillee = (self.service.installe) and (self.service.en_marche)
		for element in (ui.sortie, ui.antenne):
			element.setEnabled(not verrouillee)
		ui.sortie.setToolTip("Le serveur audio par lequel passent l'antenne et la pré-écoute")
		ui.antenne.setToolTip("La carte son sur laquelle Machin player diffuse l'antenne")
		if verrouillee:
			for element in (ui.sortie, ui.antenne):
				element.setToolTip(DIFFUSION_EN_MARCHE)
		en_cours = self._pipeline is not None
		_regler_le_bouton(ui.tester_antenne, antenne, en_cours, verrouillee)
		_regler_le_bouton(ui.tester_preecoute, preecoute, en_cours, False)
		self.change.emit()

	# ─── Son de test ───────────────────────────────────────────

	def _tester(self, choix: QComboBox) -> None:
		carte = choix.currentData()
		if (self._pipeline is not None) or (carte is None) or (carte == FACTICE):
			return
		self._carte = choix.currentText()
		try:
			pipeline = son_de_test(self.sortie_choisie(), str(carte))
		except SortieAudioIndisponible as erreur:
			self._dire(f"Son de test impossible sur « {self._carte} » : {erreur}")
			return
		self._pipeline = pipeline
		self._pilote = etats.Pilote(pipeline)
		self._fin = self.horloge() + DUREE_DU_SON_DE_TEST + MARGE
		self._dire(f"Son de test sur « {self._carte} »…")
		self._pilote.vers(Gst.State.PLAYING)
		self._releve.start()
		self._actualiser()

	def _relever(self) -> None:
		pipeline = self._pipeline
		if pipeline is None:
			return
		if (self._pilote is not None) and (self._pilote.a_echoue()):
			self._finir(f"Son de test impossible sur « {self._carte} » : la carte ne s'ouvre pas.")
			return
		bus = pipeline.get_bus()
		assert bus is not None
		while (message := bus.pop()) is not None:
			if message.type == Gst.MessageType.EOS:
				self._finir(f"Son de test joué sur « {self._carte} ».")
				return
			if message.type == Gst.MessageType.ERROR:
				erreur, _detail = message.parse_error()
				self._finir(f"Son de test impossible sur « {self._carte} » : {erreur.message}")
				return
		if self.horloge() > self._fin:
			self._finir(f"Son de test impossible sur « {self._carte} » : la carte ne répond pas.")

	def _finir(self, texte: str) -> None:
		self.arreter()
		self._dire(texte)

	def arreter(self) -> None:
		"""Arrête le son de test en cours, sans l'attendre."""
		self._releve.stop()
		if self._pilote is not None:
			self._pilote.eteindre()
		self._pipeline, self._pilote = None, None
		self._actualiser()

	def hideEvent(self, evenement: QHideEvent) -> None:  # noqa: N802 : nom imposé par Qt
		self.arreter()
		super().hideEvent(evenement)

	def _dire(self, texte: str) -> None:
		self.ui.essai.setText(texte)
		self.ui.essai.setVisible(texte != "")

	def texte(self) -> str:
		"""Ce que le bloc dit du son de test."""
		return str(self.ui.essai.text())


def _garnir(choix: QComboBox, actuel: str | None, trouves: list[sorties_audio.Peripherique]) -> None:
	"""La carte configurée d'abord, « (introuvable) » si elle n'est pas sur le poste, « (à renseigner) » s'il n'y en a
	pas ; puis les autres cartes du poste ; puis la sortie factice, si elle n'est pas déjà en tête."""
	if actuel is None:
		choix.addItem(A_RENSEIGNER, None)
	elif actuel == FACTICE:
		choix.addItem(SORTIE_FACTICE, FACTICE)
	else:
		nom = next((p.nom for p in trouves if p.identifiant == actuel), f"{actuel} (introuvable)")
		choix.addItem(nom, actuel)
	for peripherique in trouves:
		if peripherique.identifiant != actuel:
			choix.addItem(peripherique.nom, peripherique.identifiant)
	if actuel != FACTICE:
		choix.addItem(SORTIE_FACTICE, FACTICE)
	choix.setCurrentIndex(0)


def _griser(choix: QComboBox, exclu: object, refuser_factice: bool) -> None:
	"""La carte de l'autre choix est grisée ; la sortie factice aussi, si elle est refusée."""
	modele = choix.model()
	assert isinstance(modele, QStandardItemModel)
	for indice in range(choix.count()):
		donnee = choix.itemData(indice)
		ligne = modele.item(indice)
		refusee = (donnee == FACTICE) and (refuser_factice)
		ligne.setEnabled((donnee != exclu) and (not refusee))
		infobulle = ""
		if refusee:
			infobulle = FACTICE_REFUSEE
		ligne.setToolTip(infobulle)


def _regler_le_bouton(bouton: QPushButton, carte: str | None, en_cours: bool, verrouille: bool) -> None:
	infobulle = TESTER
	if verrouille:
		infobulle = DIFFUSION_EN_MARCHE
	elif carte is None:
		infobulle = SANS_CARTE
	elif carte == FACTICE:
		infobulle = SANS_SON
	bouton.setToolTip(infobulle)
	bouton.setEnabled((infobulle == TESTER) and (not en_cours))
