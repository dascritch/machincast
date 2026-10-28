"""Fenêtre de Machin_interface (https://github.com/dascritch/machincast/issues/26).

Un onglet par écran : l'accueil (écran par défaut, ouvert au lancement), le calendrier de la grille, onglet fixe
(https://github.com/dascritch/machincast/issues/307), puis une liste par type d'élément, dans
l'ordre de la recherche (spec § 8.2) : événements, séquences, banques, sonores, feeds. Les listes des sonores
et des feeds ne s'ouvrent qu'à la demande, par le menu « Affichage », à leur place parmi les autres, et se
ferment (https://github.com/dascritch/machincast/issues/180) ; les autres onglets fixes ne se ferment pas. Une liste
fermée est gardée : rouverte, elle retrouve son filtre et son tri. Une liste se relit chaque fois que son onglet
s'ouvre. Ouvrir une ligne demande l'écran de détail de l'élément (detail_demande).

L'écran de détail d'un élément est sa fiche, dans un onglet qui se ferme : événement
(machincast.interface.fiche_evenement, https://github.com/dascritch/machincast/issues/32), séquence
(machincast.interface.fiche_sequence, https://github.com/dascritch/machincast/issues/112), banque
(machincast.interface.fiche_banque, https://github.com/dascritch/machincast/issues/31) ou sonore
(machincast.interface.fiche_sonore, https://github.com/dascritch/machincast/issues/28). Une fiche déjà ouverte
revient au premier plan. Un élément cité par une fiche s'ouvre comme une ligne de liste. Une fiche modifiée demande
quoi faire de ses modifications avant de se fermer, avec son onglet ou avec la fenêtre.

Le dernier onglet fixe est l'écran des incidents du log (machincast.interface.incidents,
https://github.com/dascritch/machincast/issues/35), qui se relit aussi à l'ouverture de son onglet.

La barre de menus a cinq menus (https://github.com/dascritch/machincast/issues/117) : « Fichier », pour quitter (Alt+Q,
comme la fermeture de la fenêtre) ; « Affichage », pour ouvrir les listes des sonores et des feeds, dans des onglets
qui se ferment, ramener au premier plan le calendrier de la grille, « Grille horaire » (machincast.interface.calendrier,
https://github.com/dascritch/machincast/issues/36), et pour rafraîchir les onglets (F5,
https://github.com/dascritch/machincast/issues/148) ; « Diffusion », qui lance ou arrête l'écoute de l'antenne (Alt+P,
https://github.com/dascritch/machincast/issues/256), et démarre, arrête ou redémarre le service de
diffusion (machincast.interface.pilotage, https://github.com/dascritch/machincast/issues/25) selon son état, relu à
l'ouverture du menu ; sans le service, la barre d'état dit que l'installation n'est pas définitive, et le menu pilote
une diffusion d'essai ; « Maintenance », qui lance l'indexation rapide ou l'audit complet
(https://github.com/dascritch/machincast/issues/38) dans un processus à part, avec la fenêtre de son journal
(machincast.interface.indexation, https://github.com/dascritch/machincast/issues/120) : fermer l'interface ne l'arrête
pas ; « Aide », pour lire la documentation, signaler un problème et connaître la version (machincast.interface.version).
Une fonction pas encore écrite a son entrée, inactive, dont l'infobulle donne le ticket.

Les fichiers ajoutés depuis la liste des sonores entrent en base (machincast.interface.ajout), puis l'indexeur les
vérifie en tâche de fond (machincast.interface.verification, https://github.com/dascritch/machincast/issues/30) ; la
barre d'état annonce l'un et l'autre.
"""

import dataclasses
import logging
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTabBar, QWidget

from machincast import raccourci, service
from machincast.configuration import (
	PEREMPTION,
	Audio,
	ConfigurationInvalide,
	Crossfades,
	Interface,
	Metadonnees,
	Silences,
	charger,
)
from machincast.horloge import Horloge
from machincast.interface import (
	dialogues,
	groupes,
	icones,
	indexation,
	interruption,
	pilotage,
	preferences,
	suggestions,
	version,
)
from machincast.interface.ajout import ajouter_fichiers
from machincast.interface.application import identifier
from machincast.interface.calendrier import UNE_HEURE, Calendrier, date_longue
from machincast.interface.ecran_par_defaut import EcranParDefaut
from machincast.interface.etat import ARRET, EtatLecture
from machincast.interface.fiche import Fiche, Rafraichie
from machincast.interface.fiche_banque import FicheBanque
from machincast.interface.fiche_evenement import FicheEvenement
from machincast.interface.fiche_feed import FicheFeed
from machincast.interface.fiche_sequence import FicheSequence
from machincast.interface.fiche_sonore import FicheSonore
from machincast.interface.fil_musical import garantir
from machincast.interface.incidents import EcranIncidents
from machincast.interface.indexation import LANCE, TERMINE, TITRES
from machincast.interface.listes import BANQUES, EVENEMENTS, FEEDS, SEQUENCES, SONORES, Liste
from machincast.interface.onglet_airplay import SANS_METADONNEES, EcranAirplay
from machincast.interface.preecoute import FenetrePreecoute
from machincast.interface.recherche import EcranRecherche
from machincast.interface.simulation import EcranSimulation
from machincast.interface.ui.fenetre_principale import Ui_FenetrePrincipale
from machincast.interface.verification import Verificateur, VerificationComplete
from machincast.lecture.etat import demande_d_avance, demande_d_interruption, demande_de_relire_la_grille

journal = logging.getLogger(__name__)

ONGLETS = (
	("Événements", EVENEMENTS),
	("Séquences", SEQUENCES),
	("Banques", BANQUES),
	("Sonores", SONORES),
	("Feeds", FEEDS),
)
A_LA_DEMANDE = frozenset({"Sonores", "Feeds"})
"""Les listes qui ne s'ouvrent pas au lancement, mais par le menu « Affichage », et qui se ferment
(https://github.com/dascritch/machincast/issues/180)."""
FICHES: dict[str, type[Fiche]] = {
	fiche.genre: fiche for fiche in (FicheEvenement, FicheSequence, FicheBanque, FicheSonore, FicheFeed)
}
"""Écrans de détail : les fiches, par genre."""
SUIVI_INDEXATION = 1000
"""Millisecondes entre deux regards sur le processus de l'indexation lancée depuis le menu."""
DOCUMENTATION = "https://github.com/dascritch/machincast/blob/main/doc/utilisateur/README.md"
"""Le guide de l'antenne, pour l'équipe qui se sert de l'interface (https://github.com/dascritch/machincast/issues/128)."""
"""Le guide d'utilisation, qu'ouvre « Documentation »."""
TICKETS = "https://github.com/dascritch/machincast/issues"
"""Les tickets de MachinCast, qu'ouvre « Signaler un problème… » ; comme dans pyproject.toml."""
SANS_SERVICE = "Installation non définitive : diffusion sans service"
"""Ce que montre la barre d'état tant que le service n'est pas installé (https://github.com/dascritch/machincast/issues/25)."""
INSTALLER_LE_SERVICE = (
	"La diffusion ne démarre pas avec le poste, et ne redémarre pas seule après un plantage. Sur un ordinateur dédié à "
	"l'antenne, installer le service : ./install.sh --service (INSTALL.md, Service de diffusion)."
)
SANS_SERVICE_DEMARRER = "Sans service : Machin lecture dans une fenêtre de terminal"
SANS_ESSAI = "Aucune diffusion d'essai en cours"
ESSAI_ARRETER = "Sans service : arrête le Machin lecture lancé à la main, comme Ctrl-C"
ANTENNE_A_RENSEIGNER = "Périphérique de l'antenne à renseigner"
REGLER_L_ANTENNE = (
	"Machin lecture refuse de diffuser sans lui : le choisir dans Fichier → Préférences…, page Audio, ou le donner"
	" dans audio.peripherique du fichier de configuration."
)
DEJA_EN_MARCHE = "La diffusion d'essai tourne déjà"
ECOUTE = {
	False: ("Pré-écoute de l'antenne", "Écouter l'antenne sur la sortie de pré-écoute, aussitôt"),
	True: ("Arrêter la pré-écoute de l'antenne", "Arrêter l'écoute de l'antenne sur la sortie de pré-écoute"),
}
"""L'entrée d'écoute de l'antenne du menu « Diffusion », et son infobulle, selon que l'antenne s'écoute
(https://github.com/dascritch/machincast/issues/256)."""

RACCOURCIS_DES_ONGLETS = 12
"""Les onglets qui ont un raccourci, Maj+F1 à Maj+F12 (https://github.com/dascritch/machincast/issues/192)."""
AJOUT_A_DES_BANQUES = "Les sonores choisis s'ajoutent à la fin de chaque banque."
"""Remarque du choix des banques où ajouter des sonores (https://github.com/dascritch/machincast/issues/114)."""
RETRAIT_DE_BANQUES = "Seules les banques où figure l'un des sonores choisis sont proposées."
"""Remarque du choix des banques d'où retirer des sonores."""


def genre_de_l_ecran(ecran: QWidget) -> str:
	"""Le genre que montre un onglet, pour son icône (https://github.com/dascritch/machincast/issues/215) ; rien pour
	l'accueil, les incidents et la recherche."""
	if isinstance(ecran, Liste):
		return ecran.source.genre
	if isinstance(ecran, Fiche):
		return ecran.genre
	if isinstance(ecran, Calendrier):
		return "grille"
	if isinstance(ecran, EcranSimulation):
		return "simulation"
	if isinstance(ecran, EcranAirplay):
		return "airplay"
	return ""


class FenetrePrincipale(QMainWindow):
	detail_demande = Signal(str, int)
	"""Écran de détail demandé : genre et identifiant de l'élément."""

	def __init__(
		self,
		connexion: psycopg.Connection[TupleRow],
		socket_etat: Path,
		horloge: Horloge,
		parent: QWidget | None = None,
		commande_indexation: list[str] | None = None,
		configuration: Path | None = None,
		crossfades: Crossfades | None = None,
		*,
		audio: Audio,
		silences: Silences | None = None,
		interface: Interface | None = None,
		peremption: int = PEREMPTION,
	) -> None:
		"""commande_indexation : Machin indexation, avec la configuration de l'interface
		(indexation.commande_indexation). configuration : le fichier où « Préférences… » enregistre les réglages,
		crossfades ceux qu'il donne (https://github.com/dascritch/machincast/issues/145) ; sans fichier, les
		préférences ne s'enregistrent pas. silences : la détection de silence qu'il donne
		(https://github.com/dascritch/machincast/issues/146). interface : ses réglages de l'interface, le voyant
		« Saturation » de l'accueil (https://github.com/dascritch/machincast/issues/191)."""
		super().__init__(parent)
		self.configuration = configuration
		self.audio = audio
		"""Sortie de l'antenne et périphérique de pré-écoute (https://github.com/dascritch/machincast/issues/116)."""
		self.preecoute: FenetrePreecoute | None = None
		"""La fenêtre de pré-écoute, une seule pour toute l'interface, créée à sa première demande."""
		preferences.definir((crossfades) or (Crossfades()))
		preferences.definir_peremption(peremption)
		self.seuil_silences = ((silences) or (Silences())).seuil
		self.saturation = ((interface) or (Interface())).saturation
		"""Le voyant « Saturation » de l'accueil est affiché (https://github.com/dascritch/machincast/issues/191)."""
		self.suggestions = ((interface) or (Interface())).suggestions
		self.icone = ((interface) or (Interface())).icone
		"""L'icône choisie pour l'application ; None : celle de MachinCast
		(https://github.com/dascritch/machincast/issues/111)."""
		"""Au lancement, proposer ce qui manque pour démarrer (https://github.com/dascritch/machincast/issues/119)."""
		"""Seuil de silence du fichier de configuration, que montrent les préférences."""
		self.connexion = connexion
		self.horloge = horloge
		self.ui = Ui_FenetrePrincipale()
		self.ui.setupUi(self)
		self.ui.onglets.setTabsClosable(True)
		self.accueil = EcranParDefaut(connexion, socket_etat, horloge, audio=audio)
		self.accueil.montrer_la_saturation(self.saturation)
		self.accueil.ecoute_demandee.connect(self._ecouter_l_antenne)
		self._ajouter_fixe(self.accueil, "Accueil")
		# La grille d'antenne, onglet fixe juste après l'accueil (https://github.com/dascritch/machincast/issues/307).
		self.calendrier = Calendrier(connexion, horloge)
		self.calendrier.ouverte.connect(self._ouvrir)
		self.calendrier.creation_demandee.connect(self._creer_evenement)
		self.calendrier.annonce.connect(self.ui.barre_d_etat.showMessage)
		self.calendrier.grille_modifiee.connect(self._grille_modifiee)
		self._ajouter_fixe(self.calendrier, "Calendrier")
		self.accueil.ouverte.connect(self._ouvrir)
		self.accueil.preecoute_demandee.connect(self._preecouter)
		# Le clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257).
		self.accueil.saut_demande.connect(lambda: self._interrompre("sonore"))
		self.accueil.avance_demandee.connect(self._avancer)
		self.verificateur = Verificateur(connexion, self)
		self.verificateur.termine.connect(self._verification_terminee)
		self.verification_complete = VerificationComplete(connexion, self)
		"""L'audit complet d'un sonore, demandé depuis sa fiche (https://github.com/dascritch/machincast/issues/190)."""
		self.verification_complete.terminee.connect(self._verification_complete_terminee)
		if commande_indexation is None:
			commande_indexation = indexation.commande_indexation(None)
		self.commande_indexation = commande_indexation
		self.indexation_lancee: int | None = None
		"""Numéro du processus de l'indexation lancée depuis le menu, tant qu'il tourne."""
		self._suivi_indexation = QTimer(self)
		self._suivi_indexation.setInterval(SUIVI_INDEXATION)
		self._suivi_indexation.timeout.connect(self._suivre_indexation)
		self._mode_lance = False
		"""Audit complet ou indexation rapide, pour l'indexation lancée."""
		self.pilotage = pilotage.Pilotage(self)
		self.pilotage.termine.connect(self._pilotage_termine)
		self.service = service.ABSENT
		"""L'état du service de diffusion, relu au lancement, à l'ouverture du menu et après chaque commande."""
		self._arret_demande = False
		"""Sans service : l'arrêt de la diffusion d'essai, demandé depuis le menu, est à annoncer quand il a lieu."""
		self.sans_service = QLabel(SANS_SERVICE)
		self.sans_service.setToolTip(INSTALLER_LE_SERVICE)
		self.ui.barre_d_etat.addPermanentWidget(self.sans_service)
		self.antenne_a_renseigner = QLabel(ANTENNE_A_RENSEIGNER)
		self.antenne_a_renseigner.setToolTip(REGLER_L_ANTENNE)
		self.ui.barre_d_etat.addPermanentWidget(self.antenne_a_renseigner)
		self._signaler_l_antenne()
		self._garnir_menus()
		self.accueil.client.etat_recu.connect(self._etat_de_la_lecture)
		self.accueil.client.etat_recu.connect(self._suivre_le_texte_public)
		self._texte_public: str | None = None
		"""Le texte public du sonore en cours, titre de l'écoute de l'antenne."""
		self.accueil.client.etat_recu.connect(self._proposer_les_interruptions)
		self._proposer_les_interruptions(ARRET)
		self._relire_le_service()
		self._juste_lue: Fiche | None = None
		"""La fiche qui vient de s'ouvrir, et de se lire : son passage au premier plan ne la relit pas."""
		self.listes: list[Liste] = []
		self._titres: dict[QWidget, str] = {}
		"""Le titre de l'onglet de chaque liste, ouverte ou non."""
		for titre, source in ONGLETS:
			liste = Liste(source, connexion)
			liste.ouverte.connect(self._ouvrir)
			liste.creation_demandee.connect(lambda genre: self._ouvrir_fiche(genre, None))
			liste.duplication_demandee.connect(self._dupliquer)
			liste.preecoute_demandee.connect(self._preecouter)
			liste.action_demandee.connect(lambda cle, elements, liste=liste: self._agir(liste, cle, elements))
			liste.ajout_demande.connect(
				lambda liste=liste: self._ajouter_fichiers(liste, dialogues.choisir_fichiers(self))
			)
			liste.fichiers_deposes.connect(lambda chemins, liste=liste: self._ajouter_fichiers(liste, chemins))
			self.listes.append(liste)
			self._titres[liste] = titre
			if titre not in A_LA_DEMANDE:
				self._ajouter_fixe(liste, titre)
				continue
			# Sans onglet jusqu'à ce qu'on la demande, elle appartient à la fenêtre, cachée : elle ne lui survit pas
			# (https://github.com/dascritch/machincast/issues/262).
			liste.setParent(self)
			liste.hide()
		self.incidents = EcranIncidents(connexion)
		self.incidents.ouverte.connect(self._ouvrir)
		self._ajouter_fixe(self.incidents, "Incidents")
		self.ui.onglets.setCurrentIndex(0)
		self.ui.onglets.currentChanged.connect(self._onglet_ouvert)
		self.ui.onglets.tabCloseRequested.connect(self._fermer)
		self._creer_les_raccourcis()
		if not identifier(self._application(), self.icone):
			self.statusBar().showMessage(
				f"Icône {self.icone} illisible ou introuvable : icône de MachinCast à la place."
			)

	@staticmethod
	def _application() -> QApplication:
		application = QApplication.instance()
		assert isinstance(application, QApplication)
		return application

	def _changer_d_icone(self, icone: Path | None) -> str:
		"""L'icône choisie, pour les fenêtres et les raccourcis déjà installés ; ce qu'en dit la barre d'état."""
		self.icone = icone
		identifier(self._application(), icone)
		try:
			lieux = raccourci.reecrire(icone)
		except OSError as erreur:
			return f" Raccourcis non mis à jour : {erreur}."
		if not lieux:
			return ""
		return f" Icône mise à jour {' et '.join(lieux)}."

	def _garnir_menus(self) -> None:
		"""Fichier, Affichage, Diffusion, Maintenance, Aide ; une fonction à venir a son entrée, inactive, avec son
		ticket."""
		fichier = self.menuBar().addMenu("&Fichier")
		# La page « Interface » : https://github.com/dascritch/machincast/issues/145 ; l'icône viendra avec
		# https://github.com/dascritch/machincast/issues/111.
		reglages = fichier.addAction("Préférences…")
		reglages.triggered.connect(self._preferences)
		if self.configuration is None:
			reglages.setEnabled(False)
			reglages.setToolTip("Sans fichier de configuration, les préférences ne s'enregistrent pas")
		fichier.addSeparator()
		quitter = fichier.addAction("Quitter")
		quitter.setShortcut(QKeySequence("Alt+Q"))
		quitter.triggered.connect(self.close)
		affichage = self.menuBar().addMenu("A&ffichage")
		rafraichir = affichage.addAction("Rafraîchir les onglets")
		rafraichir.setShortcut(QKeySequence("F5"))
		rafraichir.triggered.connect(self.rafraichir)
		rechercher = affichage.addAction("Rechercher…")
		rechercher.setShortcut(QKeySequence("Ctrl+F"))
		rechercher.triggered.connect(self._ouvrir_recherche)
		for titre, source in ONGLETS:
			if titre not in A_LA_DEMANDE:
				continue
			ouvrir = affichage.addAction(icones.icone_de(source.genre), f"Ouvrir l'onglet {titre}")
			ouvrir.triggered.connect(lambda _coche=False, titre=titre: self.ouvrir_liste(titre))
		grille = affichage.addAction(icones.icone("grille"), "Ouvrir l'onglet Grille horaire")
		grille.triggered.connect(self._ouvrir_calendrier)
		simulation = affichage.addAction(icones.icone("simulation"), "Ouvrir l'onglet Simulation")
		simulation.triggered.connect(self._ouvrir_simulation)
		airplay = affichage.addAction(icones.icone("airplay"), "Ouvrir l'onglet Airplay")
		airplay.triggered.connect(self._ouvrir_airplay)
		preecoute = affichage.addAction(icones.icone("pré-écoute"), "Pré-écoute…")
		preecoute.triggered.connect(lambda: self._preecouter(None))
		self.menu_diffusion = self.menuBar().addMenu("&Diffusion")
		self.menu_diffusion.aboutToShow.connect(self._relire_le_service)
		# L'écoute de l'antenne, lancée aussitôt, en tête du menu (https://github.com/dascritch/machincast/issues/245) ;
		# pendant l'écoute, elle l'arrête, et Alt+P fait l'un ou l'autre (https://github.com/dascritch/machincast/issues/256).
		self.ecouter = self.menu_diffusion.addAction(icones.icone("pré-écoute"), "")
		self.ecouter.setShortcut(QKeySequence("Alt+P"))
		self.ecouter.triggered.connect(self._basculer_l_ecoute)
		self._montrer_l_ecoute(False)
		self.menu_diffusion.addSeparator()
		self.pilotes: dict[str, QAction] = {}
		for verbe, (entree, _reussite, _echec) in pilotage.VERBES.items():
			action = self.menu_diffusion.addAction(entree)
			action.triggered.connect(lambda _coche=False, verbe=verbe: self._piloter(verbe))
			self.pilotes[verbe] = action
		self.menu_diffusion.addSeparator()
		# https://github.com/dascritch/machincast/issues/104
		self.interruptions: dict[str, QAction] = {}
		for element, entree in interruption.ENTREES.items():
			action = self.menu_diffusion.addAction(entree)
			action.triggered.connect(lambda _coche=False, element=element: self._interrompre(element))
			self.interruptions[element] = action
		maintenance = self.menuBar().addMenu("&Maintenance")
		_a_venir(
			maintenance.addAction("Moniteur de la sortie…"), "ticket 85"
		)  # https://github.com/dascritch/machincast/issues/85
		maintenance.addSeparator()
		self.indexations: list[QAction] = []
		for audit_complet in (False, True):
			action = maintenance.addAction(TITRES[audit_complet])
			action.triggered.connect(lambda _coche=False, audit=audit_complet: self._indexer(audit))
			self.indexations.append(action)
		maintenance.addSeparator()
		# Grisée, comme l'indexation, pendant une indexation lancée d'ici : ses migrations attendraient la base
		# (https://github.com/dascritch/machincast/issues/127).
		base = maintenance.addAction(pilotage.MAINTENANCE)
		base.triggered.connect(self._maintenir_la_base)
		self.indexations.append(base)
		aide = self.menuBar().addMenu("&Aide")
		aide.addAction("Documentation").triggered.connect(lambda: dialogues.ouvrir_page(DOCUMENTATION))
		aide.addAction("Signaler un problème…").triggered.connect(lambda: dialogues.ouvrir_page(TICKETS))
		aide.addAction("Version").triggered.connect(lambda: dialogues.montrer_version(self, version.texte()))
		for menu in (fichier, affichage, self.menu_diffusion, maintenance, aide):
			menu.setToolTipsVisible(True)

	def _relire_le_service(self) -> None:
		self.service = service.lire_l_etat()
		self._presenter_la_diffusion()

	def _etat_de_la_lecture(self, etat: EtatLecture) -> None:
		"""La diffusion d'essai arrêtée depuis le menu : l'annoncer."""
		if (etat.etat != "arret") or (not self._arret_demande):
			return
		self._arret_demande = False
		self.ui.barre_d_etat.showMessage(pilotage.ARRETEE)

	def _proposer_les_interruptions(self, etat: EtatLecture) -> None:
		"""Les interruptions du menu « Diffusion » suivent ce qui est à l'antenne."""
		for element, proposition in interruption.proposer(etat).items():
			action = self.interruptions[element]
			action.setEnabled(proposition.active)
			action.setToolTip(proposition.infobulle)

	def _grille_modifiee(self) -> None:
		"""Une session sautée ou rétablie (https://github.com/dascritch/machincast/issues/273), une fiche enregistrée,
		supprimée ou restaurée (https://github.com/dascritch/machincast/issues/266) valent aussitôt à l'antenne :
		Machin lecture relit la grille, s'il diffuse ; sinon, il la lira à son démarrage."""
		self.accueil.client.envoyer(demande_de_relire_la_grille())

	def _interrompre(self, element: str) -> None:
		"""Demande à Machin lecture d'interrompre l'élément, sans question : l'antenne n'attend pas."""
		annonce = interruption.SANS_LECTURE
		if self.accueil.client.envoyer(demande_d_interruption(element)):
			annonce = interruption.ANNONCES[element]
		self.ui.barre_d_etat.showMessage(annonce)

	def _avancer(self, evenement: int, nom: str) -> None:
		"""Demande à Machin lecture d'avancer l'événement suivant qu'il a annoncé, sans question
		(https://github.com/dascritch/machincast/issues/257)."""
		annonce = interruption.AVANCE_SANS_LECTURE
		if self.accueil.client.envoyer(demande_d_avance(evenement)):
			annonce = interruption.annonce_d_avance(nom)
		self.ui.barre_d_etat.showMessage(annonce)

	def _presenter_la_diffusion(self) -> None:
		"""Les entrées du menu « Diffusion » selon l'état du service ; sans lui, le signal d'installation à terminer."""
		self.sans_service.setVisible(not self.service.installe)
		if self.service.installe:
			# En marche : arrêter ; arrêté ou en échec : démarrer.
			permis = {"start": not self.service.en_marche, "stop": self.service.en_marche}
			for verbe, action in self.pilotes.items():
				action.setText(pilotage.VERBES[verbe][0])
				action.setEnabled(permis[verbe])
				action.setToolTip("")
			return
		en_cours = self.accueil.client.pid_du_lecteur() is not None
		infobulles = {"start": SANS_SERVICE_DEMARRER, "stop": SANS_ESSAI}
		if en_cours:
			infobulles = {"start": DEJA_EN_MARCHE, "stop": ESSAI_ARRETER}
		for verbe, action in self.pilotes.items():
			action.setText(pilotage.ESSAI[verbe])
			action.setEnabled((verbe == "start") != en_cours)
			action.setToolTip(infobulles[verbe])

	def _piloter(self, verbe: str) -> None:
		if self.service.installe:
			self.pilotage.piloter(verbe)
			return
		if verbe == "start":
			self.ui.barre_d_etat.showMessage(pilotage.lancer_dans_un_terminal(self.configuration))
			return
		pid = self.accueil.client.pid_du_lecteur()
		if pid is None:
			# Le menu relu à son ouverture n'active l'entrée qu'avec une diffusion d'essai : elle vient de s'arrêter.
			return
		texte = pilotage.arreter_le_lecteur(pid)
		self.ui.barre_d_etat.showMessage(texte)
		self._arret_demande = texte == pilotage.ARRET_DEMANDE

	def _pilotage_termine(self, texte: str) -> None:
		self.ui.barre_d_etat.showMessage(texte)
		self._relire_le_service()

	def rafraichir(self) -> None:
		"""Relit l'onglet ouvert, l'airplay de l'accueil et les fiches ; une liste se relit déjà à son ouverture."""
		self._onglet_ouvert(self.ui.onglets.currentIndex())
		self.accueil.actualiser_airplay()
		laissees: list[str] = []
		effacees: list[str] = []
		for fiche in self.fiches():
			titre = fiche.titre()
			resultat = fiche.rafraichir()
			if resultat is Rafraichie.LAISSEE:
				laissees.append(titre)
			if resultat is Rafraichie.EFFACEE:
				effacees.append(titre)
				self._retirer(fiche)
		texte = "Onglets rafraîchis."
		if laissees != []:
			texte = f"{texte} Fiches laissées telles quelles : {_titres(laissees)}."
		if effacees != []:
			texte = f"{texte} Fiches fermées, leur élément n'est plus en base : {_titres(effacees)}."
		self.ui.barre_d_etat.showMessage(texte)

	def fiches(self) -> list[Fiche]:
		onglets = self.ui.onglets
		return [fiche for indice in range(onglets.count()) if isinstance(fiche := onglets.widget(indice), Fiche)]

	def closeEvent(self, evenement: QCloseEvent) -> None:
		for fiche in self.fiches():
			if not fiche.peut_fermer():
				evenement.ignore()
				return
		for fiche in self.fiches():
			fiche.fermer()
		onglets = self.ui.onglets
		for indice in range(onglets.count()):
			simulation = onglets.widget(indice)
			if isinstance(simulation, EcranSimulation):
				simulation.fermer()
		self.verificateur.arreter()
		self.verification_complete.arreter()
		self.accueil.close()
		if self.preecoute is not None:
			self.preecoute.close()
		super().closeEvent(evenement)

	def _ajouter_fixe(self, ecran: QWidget, titre: str) -> None:
		"""Un onglet sans bouton de fermeture."""
		indice = self._ajouter_onglet(ecran, titre)
		for cote in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
			self.ui.onglets.tabBar().setTabButton(indice, cote, None)

	def _ajouter_onglet(self, ecran: QWidget, titre: str) -> int:
		"""Tout onglet s'ajoute par ici, et se retire par _retirer_onglet : les raccourcis suivent."""
		indice = self.ui.onglets.addTab(ecran, icones.icone_de(genre_de_l_ecran(ecran)), titre)
		self._numeroter_les_onglets()
		return indice

	def _retirer_onglet(self, indice: int) -> None:
		self.ui.onglets.removeTab(indice)
		self._numeroter_les_onglets()

	def _creer_les_raccourcis(self) -> None:
		"""Maj+F1 à Maj+F12 : les 12 premiers onglets, selon leur rang
		(https://github.com/dascritch/machincast/issues/192)."""
		for rang in range(RACCOURCIS_DES_ONGLETS):
			raccourci = QShortcut(QKeySequence(f"Shift+F{rang + 1}"), self)
			raccourci.activated.connect(lambda rang=rang: self._aller_a_l_onglet(rang))

	def _aller_a_l_onglet(self, rang: int) -> None:
		"""Un rang sans onglet ne change rien : Qt ignore l'indice."""
		self.ui.onglets.setCurrentIndex(rang)

	def _numeroter_les_onglets(self) -> None:
		"""L'infobulle de chaque onglet donne son raccourci ; au-delà des 12 premiers, il n'en a pas."""
		onglets = self.ui.onglets
		for indice in range(onglets.count()):
			texte = ""
			if indice < RACCOURCIS_DES_ONGLETS:
				texte = f"Maj+F{indice + 1}"
			onglets.setTabToolTip(indice, texte)

	def _ouvrir_fiche(self, genre: str, identifiant: int | None) -> None:
		"""Ouvre la fiche d'un élément, ou ramène au premier plan celle déjà ouverte ; None pour un nouvel élément."""
		for ouverte in self.fiches():
			if (identifiant is not None) and (ouverte.genre == genre) and (ouverte.identifiant == identifiant):
				self.ui.onglets.setCurrentWidget(ouverte)
				return
		fiche = FICHES[genre](self.connexion, identifiant, self.horloge)
		fiche.titre_change.connect(lambda titre: self._renommer(fiche, titre))
		fiche.ouverture_demandee.connect(self._ouvrir)
		fiche.supprimee.connect(lambda: self._retirer(fiche))
		fiche.duplication_demandee.connect(self._dupliquer)
		fiche.preecoute_demandee.connect(self._preecouter)
		if isinstance(fiche, FicheSonore):
			fiche.verification_demandee.connect(lambda sonore, fiche=fiche: self._verifier_completement(fiche, sonore))
		if genre == "événement":
			fiche.supprimee.connect(self._garantir_fil_musical)
			fiche.enregistree.connect(self._garantir_fil_musical)
		if isinstance(fiche, FicheEvenement):
			# Une session rétablie depuis la fiche (https://github.com/dascritch/machincast/issues/295), comme depuis le
			# calendrier : la barre d'état l'annonce, et Machin lecture relit la grille.
			fiche.session_retablie.connect(self.ui.barre_d_etat.showMessage)
			fiche.session_retablie.connect(self._grille_modifiee)
		# Une fiche enregistrée, supprimée ou restaurée vaut aussitôt à l'antenne
		# (https://github.com/dascritch/machincast/issues/266) : Machin lecture relit la grille, et ne recalcule que si
		# ce qui règle l'antenne a changé. Un sonore ou une banque supprimé quitte les listes des événements.
		fiche.enregistree.connect(self._grille_modifiee)
		fiche.supprimee.connect(self._grille_modifiee)
		self._ajouter_onglet(fiche, fiche.titre())
		# Elle vient de se lire : passer au premier plan ne la relit pas (https://github.com/dascritch/machincast/issues/305).
		self._juste_lue = fiche
		self.ui.onglets.setCurrentWidget(fiche)
		self._juste_lue = None

	def _dupliquer(self, genre: str, identifiant: int) -> None:
		"""Une nouvelle fiche, copie de l'élément (https://github.com/dascritch/machincast/issues/130) : rien n'est
		enregistré avant « Enregistrer »."""
		self._ouvrir_fiche(genre, None)
		fiche = self.ui.onglets.currentWidget()
		assert isinstance(fiche, Fiche)
		fiche.copier(identifiant)

	def _verifier_completement(self, fiche: FicheSonore, sonore: int) -> None:
		"""L'audit complet du sonore, au seuil de silence de la configuration ; sa fiche attend."""
		fiche.attendre_la_verification()
		self.verification_complete.lancer(sonore, self.seuil_silences)

	def _verification_complete_terminee(self, sonore: int, texte: str) -> None:
		"""La barre d'état le dit ; la fiche du sonore, encore ouverte, propose de se rafraîchir."""
		self.ui.barre_d_etat.showMessage(texte)
		for fiche in self.fiches():
			if (isinstance(fiche, FicheSonore)) and (fiche.identifiant == sonore):
				fiche.verification_terminee(texte)

	def _renommer(self, fiche: QWidget, titre: str) -> None:
		self.ui.onglets.setTabText(self.ui.onglets.indexOf(fiche), titre)

	def _preecouter(self, sonore: int | None) -> None:
		"""La fenêtre de pré-écoute, au premier plan : le sonore demandé y remplace le précédent ; sans sonore, elle
		garde le sien."""
		if self.preecoute is None:
			self.preecoute = FenetrePreecoute(self.connexion, self.audio, self.configuration, self)
			self.preecoute.ecoute_changee.connect(self._montrer_l_ecoute)
		if (sonore is not None) or (not self.preecoute.isVisible()):
			self.preecoute.preecouter(sonore)
		self.preecoute.show()
		self.preecoute.raise_()
		self.preecoute.activateWindow()

	def _basculer_l_ecoute(self) -> None:
		"""L'entrée d'écoute de l'antenne, ou Alt+P : l'arrête pendant l'écoute, la lance sinon."""
		if (self.preecoute is not None) and (self.preecoute.ecoute_l_antenne()):
			self.preecoute.arreter()
			return
		self._ecouter_l_antenne(lancer=True)

	def _montrer_l_ecoute(self, en_cours: bool) -> None:
		texte, infobulle = ECOUTE[en_cours]
		self.ecouter.setText(texte)
		self.ecouter.setToolTip(infobulle)

	def _ecouter_l_antenne(self, lancer: bool = False) -> None:
		"""Clic sur le VU-mètre de l'accueil : l'antenne dans la fenêtre de pré-écoute
		(https://github.com/dascritch/machincast/issues/24) ; par le bouton « Pré-écoute » de la fenêtre, lancée
		aussitôt (https://github.com/dascritch/machincast/issues/223)."""
		self._preecouter(None)
		assert self.preecoute is not None
		self.preecoute.ecouter_l_antenne(self._texte_public, lancer)

	def _suivre_le_texte_public(self, etat: EtatLecture) -> None:
		self._texte_public = None
		if etat.en_cours is not None:
			self._texte_public = etat.en_cours.texte_public
		if self.preecoute is not None:
			self.preecoute.suivre_l_antenne(self._texte_public)

	def _ouvrir_calendrier(self) -> None:
		"""Le calendrier, onglet fixe, revient au premier plan (https://github.com/dascritch/machincast/issues/307)."""
		self.ui.onglets.setCurrentWidget(self.calendrier)

	def _ouvrir_recherche(self) -> None:
		"""Un seul onglet de recherche (https://github.com/dascritch/machincast/issues/27) : celui qui est ouvert
		revient au premier plan ; le curseur va dans son champ."""
		onglets = self.ui.onglets
		ouvertes = [onglets.widget(indice) for indice in range(onglets.count())]
		recherche = next((ecran for ecran in ouvertes if isinstance(ecran, EcranRecherche)), None)
		if recherche is None:
			recherche = EcranRecherche(self.connexion)
			recherche.ouverte.connect(self._ouvrir)
			self._ajouter_onglet(recherche, "Recherche")
		onglets.setCurrentWidget(recherche)
		recherche.focaliser()

	def ouvrir_liste(self, titre: str) -> None:
		"""Ouvre une liste à la demande à sa place, après les listes qui la précèdent et avant les incidents, ou la
		ramène au premier plan (https://github.com/dascritch/machincast/issues/180)."""
		onglets = self.ui.onglets
		(liste,) = (liste for liste in self.listes if self._titres[liste] == titre)
		indice = onglets.indexOf(liste)
		if indice < 0:
			ordre: list[QWidget] = [self.accueil, self.calendrier, *self.listes]
			rang = ordre.index(liste)
			place = sum(1 for ecran in ordre[:rang] if onglets.indexOf(ecran) >= 0)
			indice = onglets.insertTab(place, liste, icones.icone_de(genre_de_l_ecran(liste)), titre)
			self._numeroter_les_onglets()
		onglets.setCurrentIndex(indice)

	def _ouvrir_simulation(self) -> None:
		"""Un seul onglet de simulation (https://github.com/dascritch/machincast/issues/37) : celui qui est ouvert
		revient au premier plan, avec son résultat."""
		onglets = self.ui.onglets
		ouverts = [onglets.widget(indice) for indice in range(onglets.count())]
		simulation = next((ecran for ecran in ouverts if isinstance(ecran, EcranSimulation)), None)
		if simulation is None:
			simulation = EcranSimulation(self.horloge, self.configuration)
			self._ajouter_onglet(simulation, "Simulation")
		onglets.setCurrentWidget(simulation)

	def _ouvrir_airplay(self) -> None:
		"""Un seul onglet Airplay (https://github.com/dascritch/machincast/issues/244) : celui qui est ouvert revient au
		premier plan. Il se relit quand l'accueil voit un nouveau sonore."""
		onglets = self.ui.onglets
		ouverts = [onglets.widget(indice) for indice in range(onglets.count())]
		airplay = next((ecran for ecran in ouverts if isinstance(ecran, EcranAirplay)), None)
		if airplay is None:
			airplay = EcranAirplay(self.connexion, self.horloge, self._metadonnees())
			airplay.ouverte.connect(self._ouvrir)
			airplay.preecoute_demandee.connect(self._preecouter)
			airplay.annonce.connect(self.ui.barre_d_etat.showMessage)
			self.accueil.airplay_relu.connect(airplay.actualiser)
			self._ajouter_onglet(airplay, "Airplay")
		onglets.setCurrentWidget(airplay)

	def _metadonnees(self) -> Metadonnees:
		"""Le masquage et le texte public de la configuration, pour le texte public des exports de l'airplay."""
		if self.configuration is None:
			return SANS_METADONNEES
		try:
			return charger(self.configuration).metadonnees
		except (ConfigurationInvalide, OSError) as erreur:
			journal.warning(f"configuration illisible, exports sans masquage : {erreur}")
			return SANS_METADONNEES

	def _creer_evenement(self, debut: datetime) -> None:
		"""Un nouvel événement, à l'heure cliquée dans le calendrier, s'ouvre dans sa fiche si on le confirme."""
		fin = debut + UNE_HEURE
		texte = f"Créer un événement le {date_longue(debut.date())} de {debut:%H:%M} à {fin:%H:%M} ?"
		if not dialogues.confirmer_creation(self, texte):
			return
		self._ouvrir_fiche("événement", None)
		fiche = self.ui.onglets.currentWidget()
		assert isinstance(fiche, FicheEvenement)
		fiche.prevoir(debut, fin)

	def _fermer(self, indice: int) -> None:
		fiche = self.ui.onglets.widget(indice)
		if isinstance(fiche, Calendrier):
			# Onglet fixe (https://github.com/dascritch/machincast/issues/307) : il ne se ferme pas.
			return
		if isinstance(fiche, (EcranRecherche, EcranSimulation, EcranAirplay)):
			if isinstance(fiche, EcranAirplay):
				self.accueil.airplay_relu.disconnect(fiche.actualiser)
			if isinstance(fiche, EcranSimulation):
				fiche.fermer()
			self._retirer_onglet(indice)
			fiche.deleteLater()
			return
		if isinstance(fiche, Liste):
			# Une liste à la demande est gardée : rouverte, elle retrouve son filtre et son tri.
			self._retirer_onglet(indice)
			return
		assert isinstance(fiche, Fiche), fiche
		if fiche.peut_fermer():
			self._retirer(fiche)

	def _retirer(self, fiche: Fiche) -> None:
		"""Ferme l'onglet de la fiche, sans rien lui demander."""
		self._retirer_onglet(self.ui.onglets.indexOf(fiche))
		fiche.fermer()
		fiche.deleteLater()

	def _agir(self, liste: Liste, cle: str, elements: list[int]) -> None:
		"""Une action sur la sélection d'une liste (https://github.com/dascritch/machincast/issues/114) : le choix des
		banques s'il en faut, la confirmation, puis l'action en une transaction ; la liste se relit et la barre d'état
		annonce ce qui a changé. Un choix abandonné, ou une confirmation refusée, ne change rien."""
		action = groupes.action(liste.source.genre, cle)
		banques: list[int] = []
		try:
			if action.choix == "toutes":
				banques = dialogues.choisir_banques(self, self.connexion, AJOUT_A_DES_BANQUES)
			elif action.choix == "leurs":
				with self.connexion.transaction():
					parmi = groupes.banques_des_sonores(self.connexion, elements)
				banques = dialogues.choisir_banques(self, self.connexion, RETRAIT_DE_BANQUES, parmi)
			if (action.choix != "") and (banques == []):
				return
			with self.connexion.transaction():
				noms = groupes.noms_des_banques(self.connexion, banques)
			if not dialogues.confirmer_action(self, action.titre, action.question(len(elements), noms), action.bouton):
				return
			with self.connexion.transaction():
				annonce = action.executer(self.connexion, elements, banques)
		except psycopg.Error as erreur:
			journal.error(f"{action.titre} : impossible : {erreur}")
			self.ui.barre_d_etat.showMessage(f"{action.titre} : impossible : {erreur}")
			return
		self.ui.barre_d_etat.showMessage(annonce)
		liste.actualiser()

	def _ajouter_fichiers(self, liste: Liste, chemins: list[Path]) -> None:
		"""Les fichiers entrent en base à l'état aperçu, puis l'indexeur les vérifie, en tâche de fond."""
		if chemins == []:
			return
		try:
			ajout = ajouter_fichiers(self.connexion, chemins)
		except psycopg.Error as erreur:
			journal.error(f"ajout de fichiers impossible : {erreur}")
			self.ui.barre_d_etat.showMessage(f"Ajout impossible : {erreur}")
			return
		self.ui.barre_d_etat.showMessage(ajout.texte())
		liste.actualiser()
		self.verificateur.verifier(ajout.ajoutes)

	def proposer_au_lancement(self) -> None:
		"""Une fois la fenêtre montrée : la fenêtre des suggestions, s'il manque de quoi démarrer
		(https://github.com/dascritch/machincast/issues/119) ; sans les suggestions, le fil musical garanti, comme avant
		(spec § 8.10)."""
		if not self.suggestions:
			self._garantir_fil_musical()
			return
		try:
			manques = suggestions.manquants(self.connexion, self.audio)
		except psycopg.Error as erreur:
			journal.error(f"suggestions impossibles : {erreur}")
			return
		if manques.vide():
			return
		reponse = dialogues.suggerer(self, manques)
		if self.configuration is not None:
			try:
				suggestions.enregistrer(self.configuration, reponse.antenne, reponse.ne_plus_proposer)
			except OSError as erreur:
				self.statusBar().showMessage(f"Réglages non enregistrés dans {self.configuration} : {erreur}")
				return
		if reponse.ne_plus_proposer:
			self.suggestions = False
		if not reponse.creer:
			return
		try:
			texte = suggestions.creer(self.connexion, reponse)
		except psycopg.Error as erreur:
			self.statusBar().showMessage(f"Création impossible : {erreur}")
			return
		if texte is not None:
			self.statusBar().showMessage(texte)
		if (reponse.antenne is not None) and (self.configuration is not None):
			self.audio = dataclasses.replace(self.audio, peripherique=reponse.antenne)
			self._signaler_l_antenne()
			self.accueil.changer_d_antenne(self.audio)
			self.statusBar().showMessage(
				f"Périphérique de l'antenne : {reponse.antenne} ; Machin lecture le prendra à son prochain démarrage."
			)

	def _garantir_fil_musical(self) -> None:
		"""Sans fil musical en base, en crée un, permanent et vide, et le dit (spec § 8.10)."""
		try:
			cree = garantir(self.connexion)
		except psycopg.Error as erreur:
			journal.error(f"vérification du fil musical impossible : {erreur}")
			return
		if cree is None:
			return
		texte = (
			f"Aucun fil musical : « {cree} » est créé, permanent et sans élément ; sa liste se remplit dans sa fiche."
		)
		journal.warning(texte)
		self.ui.barre_d_etat.showMessage(texte)

	def _maintenir_la_base(self) -> None:
		"""Machin maintenance-db dans un terminal, une fois confirmée, avec l'emplacement de sa sauvegarde, au choix
		(https://github.com/dascritch/machincast/issues/127)."""
		sauvegardes = dialogues.confirmer_maintenance(self, pilotage.sauvegardes_de_la_maintenance(self.configuration))
		if sauvegardes is None:
			self.statusBar().showMessage(pilotage.MAINTENANCE_ABANDONNEE)
			return
		self.statusBar().showMessage(pilotage.lancer_la_maintenance(self.configuration, sauvegardes))

	def _indexer(self, audit_complet: bool) -> None:
		"""Lance Machin indexation dans son propre processus, avec sa fenêtre ; le menu ne la propose plus tant qu'il
		tourne."""
		commande = [*self.commande_indexation, "--fenetre"]
		if audit_complet:
			commande.append("--audit-complet")
		self._mode_lance = audit_complet
		self.indexation_lancee = indexation.lancer_detachee(commande)
		if self.indexation_lancee is None:
			journal.error(f"indexation impossible à lancer : {' '.join(commande)}")
			self.ui.barre_d_etat.showMessage("Indexation impossible : Machin indexation n'a pas pu être lancé.")
			return
		for action in self.indexations:
			action.setEnabled(False)
		titre = TITRES[audit_complet]
		self.ui.barre_d_etat.showMessage(f"{titre} {LANCE[audit_complet]}, dans sa propre fenêtre.")
		self._suivi_indexation.start()

	def _suivre_indexation(self) -> None:
		assert self.indexation_lancee is not None
		if indexation.processus_actif(self.indexation_lancee):
			return
		self._suivi_indexation.stop()
		self.indexation_lancee = None
		for action in self.indexations:
			action.setEnabled(True)
		titre = TITRES[self._mode_lance]
		self.ui.barre_d_etat.showMessage(
			f"{titre} {TERMINE[self._mode_lance]} ; « Rafraîchir les onglets » (F5) montre ses changements."
		)

	def _verification_terminee(self, texte: str) -> None:
		self.ui.barre_d_etat.showMessage(texte)
		ouvert = self.ui.onglets.currentWidget()
		if isinstance(ouvert, Liste):
			ouvert.actualiser()

	def _onglet_ouvert(self, indice: int) -> None:
		"""L'onglet qui passe au premier plan se relit, s'il n'est pas en cours d'édition
		(https://github.com/dascritch/machincast/issues/241) : une liste, les incidents, le calendrier, la recherche,
		l'airplay, l'airplay de l'accueil, et une fiche qui n'est pas modifiée, sans rien demander. Une fiche modifiée
		reste telle quelle ; celle d'un élément effacé de la base se ferme."""
		ouvert = self.ui.onglets.widget(indice)
		if isinstance(ouvert, (Liste, EcranIncidents, Calendrier, EcranRecherche, EcranAirplay)):
			ouvert.actualiser()
		if ouvert is self.accueil:
			self.accueil.actualiser_airplay()
		if (not isinstance(ouvert, Fiche)) or (ouvert.modifiee) or (ouvert is self._juste_lue):
			return
		titre = ouvert.titre()
		if ouvert.rafraichir() is Rafraichie.EFFACEE:
			self._retirer(ouvert)
			self.ui.barre_d_etat.showMessage(f"Fiche fermée, son élément n'est plus en base : « {titre} ».")

	def _preferences(self) -> None:
		"""Les préférences réglées s'enregistrent dans le fichier de configuration, puis valent pour les fiches
		ouvertes ensuite ; un fichier qui ne s'écrit pas les laisse inchangées, et la barre d'état le dit."""
		assert self.configuration is not None
		audio = self.audio
		montres = preferences.Reglages(
			preferences.crossfades(),
			audio.peripherique,
			audio.preecoute,
			self.seuil_silences,
			self.saturation,
			self.suggestions,
			self.icone,
			preferences.peremption(),
		)
		reglages = dialogues.regler_preferences(self, montres, audio.sortie)
		if reglages is None:
			return
		try:
			preferences.ecrire(self.configuration, reglages)
		except OSError as erreur:
			self.statusBar().showMessage(f"Préférences non enregistrées dans {self.configuration} : {erreur}")
			return
		preferences.definir(reglages.crossfades)
		preferences.definir_peremption(reglages.peremption)
		self.seuil_silences = reglages.seuil_silences
		self.saturation = reglages.saturation
		self.suggestions = reglages.suggestions
		self.accueil.montrer_la_saturation(self.saturation)
		icone = ""
		if reglages.icone != self.icone:
			icone = self._changer_d_icone(reglages.icone)
		texte = "les crossfades par défaut"
		if reglages.antenne != audio.peripherique:
			texte = "les crossfades par défaut et le périphérique de l'antenne"
		self.audio = dataclasses.replace(audio, peripherique=reglages.antenne, preecoute=reglages.preecoute)
		if self.preecoute is not None:
			# La pré-écoute repart des nouveaux périphériques à sa prochaine ouverture.
			self.preecoute.close()
			self.preecoute.deleteLater()
			self.preecoute = None
		self._signaler_l_antenne()
		self.accueil.changer_d_antenne(self.audio)
		self.statusBar().showMessage(
			f"Préférences enregistrées dans {self.configuration} ;"
			f" Machin lecture prendra {texte} à son prochain démarrage.{icone}"
		)

	def _signaler_l_antenne(self) -> None:
		"""Sans périphérique d'antenne, sur une vraie sortie, Machin lecture refuse de diffuser : la barre d'état le
		dit."""
		self.antenne_a_renseigner.setVisible((self.audio.sortie != "factice") and (self.audio.peripherique is None))

	def _ouvrir(self, genre: str, identifiant: int, _nom: str) -> None:
		self.detail_demande.emit(genre, identifiant)
		self._ouvrir_fiche(genre, identifiant)


def _a_venir(action: QAction, tickets: str) -> None:
	"""Une infobulle ne porte pas de lien : elle nomme le ticket par son numéro, sans « # »."""
	action.setEnabled(False)
	action.setToolTip(f"À venir : {tickets} sur GitHub")


def _titres(titres: list[str]) -> str:
	return ", ".join(f"« {titre} »" for titre in titres)
