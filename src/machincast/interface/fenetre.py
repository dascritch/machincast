"""Fenêtre de Machin_interface (https://github.com/dascritch/machincast/issues/26).

Un onglet par écran : l'accueil (écran par défaut, ouvert au lancement), puis une liste par type d'élément, dans
l'ordre de la recherche (spec § 8.2) : événements, séquences, banques, sonores. Ces onglets ne se ferment pas. Une liste
se relit chaque fois que son onglet s'ouvre. Ouvrir une ligne demande l'écran de détail de l'élément (detail_demande).

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
comme la fermeture de la fenêtre) ; « Affichage », pour le calendrier de la grille (machincast.interface.calendrier,
https://github.com/dascritch/machincast/issues/36), dans un onglet qui se ferme, et pour rafraîchir les onglets (F5,
https://github.com/dascritch/machincast/issues/148) ; « Diffusion », qui démarre, arrête ou redémarre le service de
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
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import QLabel, QMainWindow, QTabBar, QWidget

from machincast import service
from machincast.configuration import Audio, Crossfades
from machincast.horloge import Horloge
from machincast.interface import dialogues, indexation, pilotage, preferences, version
from machincast.interface.ajout import ajouter_fichiers
from machincast.interface.calendrier import UNE_HEURE, Calendrier, date_longue
from machincast.interface.ecran_par_defaut import EcranParDefaut
from machincast.interface.etat import EtatLecture
from machincast.interface.fiche import Fiche, Rafraichie
from machincast.interface.fiche_banque import FicheBanque
from machincast.interface.fiche_evenement import FicheEvenement
from machincast.interface.fiche_marque_page import FicheMarquePage
from machincast.interface.fiche_sequence import FicheSequence
from machincast.interface.fiche_sonore import FicheSonore
from machincast.interface.fil_musical import garantir
from machincast.interface.incidents import EcranIncidents
from machincast.interface.indexation import LANCE, TERMINE, TITRES
from machincast.interface.listes import BANQUES, EVENEMENTS, MARQUES_PAGES, SEQUENCES, SONORES, Liste
from machincast.interface.preecoute import FenetrePreecoute
from machincast.interface.ui.fenetre_principale import Ui_FenetrePrincipale
from machincast.interface.verification import Verificateur

journal = logging.getLogger(__name__)

ONGLETS = (
	("Événements", EVENEMENTS),
	("Séquences", SEQUENCES),
	("Banques", BANQUES),
	("Sonores", SONORES),
	("Marques-pages", MARQUES_PAGES),
)
FICHES: dict[str, type[Fiche]] = {
	fiche.genre: fiche for fiche in (FicheEvenement, FicheSequence, FicheBanque, FicheSonore, FicheMarquePage)
}
"""Écrans de détail : les fiches, par genre."""
SUIVI_INDEXATION = 1000
"""Millisecondes entre deux regards sur le processus de l'indexation lancée depuis le menu."""
DOCUMENTATION = "https://github.com/dascritch/machincast/blob/main/doc/utilisation.md"
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
ESSAI_REDEMARRER = "Sans service : l'arrête, puis le relance dans une fenêtre de terminal"
ANTENNE_A_RENSEIGNER = "Périphérique de l'antenne à renseigner"
REGLER_L_ANTENNE = (
	"Machin lecture refuse de diffuser sans lui : le choisir dans Fichier → Préférences…, page Audio, ou le donner"
	" dans audio.peripherique du fichier de configuration."
)
DEJA_EN_MARCHE = "La diffusion d'essai tourne déjà"


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
	) -> None:
		"""commande_indexation : Machin indexation, avec la configuration de l'interface
		(indexation.commande_indexation). configuration : le fichier où « Préférences… » enregistre les réglages,
		crossfades ceux qu'il donne (https://github.com/dascritch/machincast/issues/145) ; sans fichier, les
		préférences ne s'enregistrent pas."""
		super().__init__(parent)
		self.configuration = configuration
		self.audio = audio
		"""Sortie de l'antenne et périphérique de pré-écoute (https://github.com/dascritch/machincast/issues/116)."""
		self.preecoute: FenetrePreecoute | None = None
		"""La fenêtre de pré-écoute, une seule pour toute l'interface, créée à sa première demande."""
		preferences.definir((crossfades) or (Crossfades()))
		self.connexion = connexion
		self.horloge = horloge
		self.ui = Ui_FenetrePrincipale()
		self.ui.setupUi(self)
		self.ui.onglets.setTabsClosable(True)
		self.accueil = EcranParDefaut(connexion, socket_etat, horloge, audio=audio)
		self.accueil.ecoute_demandee.connect(self._ecouter_l_antenne)
		self._ajouter_fixe(self.accueil, "Accueil")
		self.accueil.ouverte.connect(self._ouvrir)
		self.verificateur = Verificateur(connexion, self)
		self.verificateur.termine.connect(self._verification_terminee)
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
		self._apres_l_arret: str | None = None
		"""Sans service, « stop » ou « restart » : ce qu'il reste à faire quand la diffusion d'essai s'est arrêtée."""
		self.sans_service = QLabel(SANS_SERVICE)
		self.sans_service.setToolTip(INSTALLER_LE_SERVICE)
		self.ui.barre_d_etat.addPermanentWidget(self.sans_service)
		self.antenne_a_renseigner = QLabel(ANTENNE_A_RENSEIGNER)
		self.antenne_a_renseigner.setToolTip(REGLER_L_ANTENNE)
		self.ui.barre_d_etat.addPermanentWidget(self.antenne_a_renseigner)
		self._signaler_l_antenne()
		self._garnir_menus()
		self.accueil.client.etat_recu.connect(self._etat_de_la_lecture)
		self._relire_le_service()
		self.listes: list[Liste] = []
		for titre, source in ONGLETS:
			liste = Liste(source, connexion)
			liste.ouverte.connect(self._ouvrir)
			liste.creation_demandee.connect(lambda genre: self._ouvrir_fiche(genre, None))
			liste.ajout_demande.connect(
				lambda liste=liste: self._ajouter_fichiers(liste, dialogues.choisir_fichiers(self))
			)
			liste.fichiers_deposes.connect(lambda chemins, liste=liste: self._ajouter_fichiers(liste, chemins))
			self.listes.append(liste)
			self._ajouter_fixe(liste, titre)
		self.incidents = EcranIncidents(connexion)
		self.incidents.ouverte.connect(self._ouvrir)
		self._ajouter_fixe(self.incidents, "Incidents")
		self.ui.onglets.setCurrentIndex(0)
		self.ui.onglets.currentChanged.connect(self._onglet_ouvert)
		self._garantir_fil_musical()
		self.ui.onglets.tabCloseRequested.connect(self._fermer)

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
		affichage.addAction("Calendrier").triggered.connect(self._ouvrir_calendrier)
		affichage.addAction("Pré-écoute…").triggered.connect(lambda: self._preecouter(None))
		self.menu_diffusion = self.menuBar().addMenu("&Diffusion")
		self.menu_diffusion.aboutToShow.connect(self._relire_le_service)
		self.pilotes: dict[str, QAction] = {}
		for verbe, (entree, _reussite, _echec) in pilotage.VERBES.items():
			action = self.menu_diffusion.addAction(entree)
			action.triggered.connect(lambda _coche=False, verbe=verbe: self._piloter(verbe))
			self.pilotes[verbe] = action
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
		"""La diffusion d'essai arrêtée depuis le menu : l'annoncer, ou la relancer."""
		if (etat.etat != "arret") or (self._apres_l_arret is None):
			return
		verbe, self._apres_l_arret = self._apres_l_arret, None
		if verbe == "stop":
			self.ui.barre_d_etat.showMessage(pilotage.ARRETEE)
			return
		self.ui.barre_d_etat.showMessage(pilotage.lancer_dans_un_terminal(self.configuration, pilotage.RELANCE))

	def _presenter_la_diffusion(self) -> None:
		"""Les entrées du menu « Diffusion » selon l'état du service ; sans lui, le signal d'installation à terminer."""
		self.sans_service.setVisible(not self.service.installe)
		if self.service.installe:
			# active : arrêter ou redémarrer ; en échec : démarrer ou redémarrer ; arrêté : démarrer.
			permis = {
				"start": not self.service.en_marche,
				"stop": self.service.en_marche,
				"restart": self.service.actif != "inactive",
			}
			for verbe, action in self.pilotes.items():
				action.setText(pilotage.VERBES[verbe][0])
				action.setEnabled(permis[verbe])
				action.setToolTip("")
			return
		en_cours = self.accueil.client.pid_du_lecteur() is not None
		infobulles = {"start": SANS_SERVICE_DEMARRER, "stop": SANS_ESSAI, "restart": SANS_ESSAI}
		if en_cours:
			infobulles = {"start": DEJA_EN_MARCHE, "stop": ESSAI_ARRETER, "restart": ESSAI_REDEMARRER}
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
		if texte == pilotage.ARRET_DEMANDE:
			self._apres_l_arret = verbe

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
		self.verificateur.arreter()
		self.accueil.close()
		if self.preecoute is not None:
			self.preecoute.close()
		super().closeEvent(evenement)

	def _ajouter_fixe(self, ecran: QWidget, titre: str) -> None:
		"""Un onglet sans bouton de fermeture."""
		indice = self.ui.onglets.addTab(ecran, titre)
		for cote in (QTabBar.ButtonPosition.LeftSide, QTabBar.ButtonPosition.RightSide):
			self.ui.onglets.tabBar().setTabButton(indice, cote, None)

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
		if isinstance(fiche, FicheSonore):
			fiche.preecoute_demandee.connect(self._preecouter)
		if genre == "événement":
			fiche.supprimee.connect(self._garantir_fil_musical)
			fiche.enregistree.connect(self._garantir_fil_musical)
		self.ui.onglets.addTab(fiche, fiche.titre())
		self.ui.onglets.setCurrentWidget(fiche)

	def _renommer(self, fiche: QWidget, titre: str) -> None:
		self.ui.onglets.setTabText(self.ui.onglets.indexOf(fiche), titre)

	def _preecouter(self, sonore: int | None) -> None:
		"""La fenêtre de pré-écoute, au premier plan : le sonore demandé y remplace le précédent ; sans sonore, elle
		garde le sien."""
		if self.preecoute is None:
			self.preecoute = FenetrePreecoute(self.connexion, self.audio, self.configuration, self)
		if (sonore is not None) or (not self.preecoute.isVisible()):
			self.preecoute.preecouter(sonore)
		self.preecoute.show()
		self.preecoute.raise_()
		self.preecoute.activateWindow()

	def _ecouter_l_antenne(self) -> None:
		"""Clic sur le VU-mètre de l'accueil : l'antenne dans la fenêtre de pré-écoute
		(https://github.com/dascritch/machincast/issues/24)."""
		self._preecouter(None)
		assert self.preecoute is not None
		self.preecoute.ecouter_l_antenne()

	def _ouvrir_calendrier(self) -> None:
		"""Un seul calendrier : celui qui est ouvert revient au premier plan."""
		onglets = self.ui.onglets
		for indice in range(onglets.count()):
			if isinstance(onglets.widget(indice), Calendrier):
				onglets.setCurrentIndex(indice)
				return
		calendrier = Calendrier(self.connexion, self.horloge)
		calendrier.ouverte.connect(self._ouvrir)
		calendrier.creation_demandee.connect(self._creer_evenement)
		onglets.setCurrentIndex(onglets.addTab(calendrier, "Calendrier"))

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
			self.ui.onglets.removeTab(indice)
			fiche.deleteLater()
			return
		assert isinstance(fiche, Fiche), fiche
		if fiche.peut_fermer():
			self._retirer(fiche)

	def _retirer(self, fiche: Fiche) -> None:
		"""Ferme l'onglet de la fiche, sans rien lui demander."""
		self.ui.onglets.removeTab(self.ui.onglets.indexOf(fiche))
		fiche.fermer()
		fiche.deleteLater()

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
		ouvert = self.ui.onglets.widget(indice)
		if isinstance(ouvert, (Liste, EcranIncidents, Calendrier)):
			ouvert.actualiser()

	def _preferences(self) -> None:
		"""Les préférences réglées s'enregistrent dans le fichier de configuration, puis valent pour les fiches
		ouvertes ensuite ; un fichier qui ne s'écrit pas les laisse inchangées, et la barre d'état le dit."""
		assert self.configuration is not None
		audio = self.audio
		montres = preferences.Reglages(preferences.crossfades(), audio.peripherique, audio.preecoute)
		reglages = dialogues.regler_preferences(self, montres, audio.sortie)
		if reglages is None:
			return
		try:
			preferences.ecrire(self.configuration, reglages)
		except OSError as erreur:
			self.statusBar().showMessage(f"Préférences non enregistrées dans {self.configuration} : {erreur}")
			return
		preferences.definir(reglages.crossfades)
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
			f" Machin lecture prendra {texte} à son prochain démarrage."
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
