"""Boucle de diffusion de Machin lecture (https://github.com/dascritch/machincast/issues/88, spec § 5).

Assemble l'ordonnanceur (machincast.lecture.deroule), le moteur audio (machincast.lecture.moteur), la vérification
des fichiers (machincast.lecture.fichiers) et l'enregistrement (machincast.lecture.enregistrement). La diffusion
avance par pas, à l'heure de son horloge ; à chaque pas :

1. les voies finies, ou en erreur, terminent leur passage dans l'airplay ;
2. pendant un sonore, l'ordonnanceur dit s'il faut le couper net (début d'un événement) : toutes les voies
   s'arrêtent, et le sonore de l'événement démarre aussitôt, sans fondu ;
3. quand le sonore atteint le début de son crossfade de fin (enchainement), l'ordonnanceur donne le suivant. Si les
   deux sonores se superposent (chacun son crossfade), le suivant démarre aussitôt avec sa montée ; sinon, le
   sonore en cours joue jusqu'au bout à plein volume, et le suivant attend sa fin ;
4. sans rien sur la sortie, le sonore en attente démarre, ou celui que l'ordonnanceur donne ; sinon, silence.

Avant de jouer un sonore, son fichier est vérifié : introuvable, il est écarté par l'ordonnanceur, et le suivant
est demandé. L'arrêt termine les passages en cours, sans incident, puis consigne l'arrêt.

Streams (https://github.com/dascritch/machincast/issues/16, spec § 4.7) :

- à la fin de son événement, le stream s'éteint pendant son crossfade de fin ; le sonore suivant se superpose s'il a
  un crossfade de début, sinon il attend la fin du fondu ;
- un flux qui s'arrête ou qui ne répond pas, avant la fin de son événement, est tombé : son passage se termine en
  incident « flux tombé », et l'ordonnanceur remplace l'événement (Ordonnanceur.suspendre). Une sonde, voie
  muette, retente la connexion tous les delai_reconnexion ; dès que le flux arrive, le stream monte pendant son
  crossfade de début et les sonores de remplacement s'éteignent pendant ce temps (coupure nette sans crossfade de
  début), et l'incident « reprise du flux » donne la durée de la panne ;
- si l'événement du stream n'est plus actif, la reconnexion est abandonnée.

Playlist immédiate (https://github.com/dascritch/machincast/issues/228) : après le prochain sonore, réservé au début
du sonore en cours, la diffusion prévoit les A_VENIR sonores suivants (a_venir), chacun à l'heure où il serait choisi,
en tenant compte des coupures par les événements qui commencent. Ils sont engagés : à chaque changement de sonore, si
c'est le prochain sonore qui a démarré, que la grille n'a pas changé et que la coupure du sonore en cours est celle
qui était prévue, le premier sonore à venir devient le prochain, et un nouveau est prévu au bout de la liste ; sinon,
sur un imprévu, le prochain sonore et toute la liste sont recalculés. Un sonore à venir qui n'est plus jouable à son
tour est remplacé par la décision de l'ordonnanceur, qui fait recalculer la liste.

Interruption manuelle (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228, interrompre) : demandée par l'interface sur la socket d'état, et
traitée au début du pas suivant. Le sonore en cours s'éteint aussitôt pendant le crossfade de fin par défaut de la
configuration, ou s'arrête net sans lui ; son passage se termine sans incident, et le suivant démarre avec le crossfade
de début par défaut, ou à plein volume : le prochain sonore pour un sonore, le premier sonore prévu après la séquence
pour une séquence (les sonores à venir qui le suivent sont gardés), le fil musical pour un événement
(Ordonnanceur.rendre_au_fil_musical). Le log note l'info « interruption manuelle », avec ce qui est interrompu. Sans
rien à l'antenne, hors d'une séquence pour une séquence, ou dans le fil musical pour un événement, la demande est
ignorée et signalée dans le journal du binaire.

Expiration (https://github.com/dascritch/machincast/issues/18, machincast.lecture.expiration) : chaque passage qui
commence vérifie si son sonore a atteint son maximum de lectures ; tous les sonores sont vérifiés au démarrage, puis
toutes les VERIFICATION_DES_EXPIRATIONS, pour les périodes de diffusion terminées.
"""

import json
import logging
import signal
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import FrameType
from typing import Any

import psycopg
from psycopg.rows import TupleRow

from machincast import __version__
from machincast.configuration import Crossfades, Metadonnees
from machincast.conversion import entier_ou_rien, texte_ou_rien
from machincast.hasard import Hasard
from machincast.horloge import Horloge
from machincast.lecture.analyse import Analyseur, a_analyser
from machincast.lecture.deroule import Choix, Coupure, Decision, EnCours, Ordonnanceur
from machincast.lecture.enregistrement import Passage
from machincast.lecture.etat import PUBLICATION_MINIMALE, RELIRE_LA_GRILLE, SocketEtat, SocketEtatOccupee, est_sain
from machincast.lecture.etat import instant as iso
from machincast.lecture.fichiers import verifier_avant_lecture
from machincast.lecture.fondus import Placement, placer
from machincast.lecture.grille import Occurrence, Priorite
from machincast.lecture.historique import EN_BASE, Historique
from machincast.lecture.moteur import (
	DELAI_DE_DEMARRAGE,
	Moteur,
	VoieLecture,
	enchainement,
	fondu_d_entree,
	superposition,
)
from machincast.lecture.sorties import Sorties, lire_passages, texte_public

journal = logging.getLogger(__name__)

PAUSE = 0.05
AUCUN_CROSSFADE = timedelta(0)
DEBUT_D_EVENEMENT, FIN_D_EVENEMENT = "début d'événement", "fin d'événement"
DEBUT_DE_SEQUENCE, FIN_DE_SEQUENCE = "début de séquence", "fin de séquence"
"""Natures, au niveau info, des débuts et des fins à l'antenne (https://github.com/dascritch/machincast/issues/153)."""
PRIORITES = {
	Priorite.SPECIAL: "spécial",
	Priorite.EMISSION: "émission",
	Priorite.FIL_MUSICAL: "fil musical",
	Priorite.SECOURS: "secours",
}
SANS_DEFAUTS = Crossfades()
"""Une configuration sans crossfades par défaut."""
HORIZON_DES_COUPURES = timedelta(hours=12)
"""Jusqu'où chercher l'événement qui coupera un sonore de durée inconnue, un stream
(https://github.com/dascritch/machincast/issues/169)."""
A_VENIR = 5
"""Sonores prévus après le prochain : la playlist immédiate (https://github.com/dascritch/machincast/issues/228)."""
EMPREINTE_DE_LA_GRILLE = (
	"SELECT md5(concat_ws('|',"
	" (SELECT string_agg(concat_ws(';', e.id, e.priorite, e.debut, e.fin, e.jours_recurrence, e.supprime_le), ','"
	" ORDER BY e.id) FROM evenements e),"
	" (SELECT string_agg(x::text, ',' ORDER BY x.id) FROM evenements_elements x),"
	" (SELECT string_agg(l::text, ',' ORDER BY l.id) FROM sequences_elements l),"
	" (SELECT string_agg(s::text, ',' ORDER BY s.evenement_id, s.jour) FROM evenements_sauts s)))"
)
"""Empreinte de ce qui règle l'antenne dans la grille : les dates, les jours, la priorité et la suppression des
événements, leurs listes, leurs sessions sautées et les listes des séquences. Changée, elle fait recalculer les
sonores à venir ; un nom, un nom public, un masquage ou la date de modification n'y sont pas : les sonores à venir,
déjà tirés, restent ceux qui passeront (https://github.com/dascritch/machincast/issues/266)."""

DELAI_RECONNEXION = timedelta(seconds=5)
"""Délai entre deux tentatives de reconnexion d'un stream tombé."""

VERIFICATION_DES_EXPIRATIONS = timedelta(minutes=1)
"""Intervalle entre deux vérifications de tous les sonores (fin de période de diffusion)."""

FLUX_ARRETE = "le flux s'est arrêté avant la fin de son événement"
FLUX_TOMBE = "flux tombé"
REPRISE_DU_FLUX = "reprise du flux"
LECTURE_BLOQUEE = "lecture bloquée"
"""Incident d'un sonore dont le lecteur n'a pas démarré (https://github.com/dascritch/machincast/issues/281)."""
LECTEUR_BLOQUE = (
	f"aucun son {DELAI_DE_DEMARRAGE.total_seconds():g} secondes après son démarrage, le sonore suivant est joué"
).replace(".", ",")
INTERRUPTION_MANUELLE = "interruption manuelle"
IGNOREE = f"{INTERRUPTION_MANUELLE} ignorée"


@dataclass(frozen=True)
class Parametres:
	"""Ce que le moteur audio doit savoir d'un sonore."""

	duree: timedelta | None
	crossfade_debut: timedelta
	crossfade_fin: timedelta
	stream: bool = False
	adresse: str | None = None
	"""Adresse d'un stream : directe, ou celle de son feed."""
	emplacement: str | None = None
	"""Chemin du fichier, ou adresse du stream, comme dans l'airplay
	(https://github.com/dascritch/machincast/issues/23)."""
	secours: int | None = None
	"""Événement de secours d'un stream."""
	artiste: str | None = None
	titre: str | None = None
	decalage: timedelta | None = None
	"""Sonore rogné par la détection de blanc (https://github.com/dascritch/machincast/issues/146) : d'où part la
	lecture du fichier, selon la position de son fade-in (https://github.com/dascritch/machincast/issues/234) ; sa durée
	est alors celle de la partie jouée. None : joué en entier."""
	volume_de_depart: float = 0.0
	"""Volume au début de la lecture, quand le fade-in déborde avant le début du fichier ; 0 sinon."""
	volume_d_arrivee: float = 0.0
	"""Volume à la fin de la lecture, quand le fade-out déborde après la fin du fichier ; 0 sinon."""


@dataclass
class Lecture:
	"""Un sonore sur la sortie : son choix, sa voie et son passage dans l'airplay."""

	choix: Choix
	parametres: Parametres
	voie: VoieLecture
	passage: Passage
	suivant_demande: bool = False
	"""L'ordonnanceur a déjà donné le sonore suivant, au début du crossfade de fin."""
	eteinte: bool = False
	"""La voie s'éteint en fondu et s'arrêtera d'elle-même : la fin du passage est normale."""
	details: dict[str, Any] | None = None
	"""Ce que la socket d'état dit de son contexte, lu une fois (Diffusion._details)."""
	coupure: Coupure | None = None
	"""L'événement qui le coupera net, cherché à sa réservation (https://github.com/dascritch/machincast/issues/169)."""

	@property
	def en_cours(self) -> EnCours:
		debut = self.passage.debut
		fin_prevue = debut + ((self.parametres.duree) or (timedelta(0)))
		return EnCours(self.choix.occurrence, debut, fin_prevue, self.parametres.stream)


@dataclass(frozen=True)
class Reserve:
	"""Prochain sonore, réservé au début du sonore en cours (https://github.com/dascritch/machincast/issues/20)."""

	choix: Choix
	parametres: Parametres
	sain: bool | None
	"""Indicateur « sain » (spec § 4.6) ; None pour un stream."""
	anticipee: bool = False
	"""Réservé pour après une coupure : seulement annoncé, il sera choisi par la décision prise à la coupure, qui
	consigne ce qu'il faut (https://github.com/dascritch/machincast/issues/169)."""


@dataclass(frozen=True)
class Prevu:
	"""Un sonore à venir, après le prochain (https://github.com/dascritch/machincast/issues/228) : engagé, il sera joué
	si rien d'imprévu n'arrive."""

	choix: Choix
	parametres: Parametres
	sain: bool | None
	coupure: Coupure | None
	"""L'événement qui coupe net le sonore précédent, au début duquel celui-ci démarre ; None s'il enchaîne."""
	terminees: frozenset[tuple[int, datetime | None]]
	"""Occurrences terminées par l'ordonnanceur une fois ce sonore choisi (Ordonnanceur.engager)."""
	details: dict[str, Any] = field(default_factory=dict, compare=False)
	"""Ce que la socket d'état dit de son contexte (Diffusion._details), lu une fois."""
	consignes: tuple[dict[str, Any], ...] = field(default=(), compare=False)
	"""Ce que sa décision consignerait, comme un élément sauté : consigné quand il devient le prochain sonore."""


@dataclass
class Sonde:
	"""Reconnexion d'un stream tombé : une voie muette, retentée tous les delai_reconnexion."""

	choix: Choix
	parametres: Parametres
	prochaine_tentative: datetime
	depuis: datetime
	"""Heure de la panne."""
	voie: VoieLecture | None = None


def lire_parametres(
	connexion: psycopg.Connection[TupleRow], choix: Choix, defauts: Crossfades = SANS_DEFAUTS
) -> Parametres:
	"""Ce qu'il faut pour jouer le sonore choisi. Ses crossfades suivent les règles de la banque qui l'a fourni
	(https://github.com/dascritch/machincast/issues/143), puis, s'il n'en a pas de paramétré, les crossfades par défaut
	de la configuration (https://github.com/dascritch/machincast/issues/145). Un fichier qui active la détection de
	blanc, ou fourni par une banque qui l'active, est joué sans ses blancs détectés
	(https://github.com/dascritch/machincast/issues/146, machincast.lecture.fondus.placer)."""
	with connexion.transaction():
		ligne = connexion.execute(
			"SELECT s.duree, s.crossfade_debut, s.crossfade_fin, s.type::text, COALESCE(s.url_stream, m.url),"
			" s.secours_evenement_id, s.artiste, s.titre, COALESCE(s.emplacement, s.url_stream, m.url),"
			" s.detection_blancs OR COALESCE(b.detection_blancs, false), s.debut_detecte, s.fin_detectee,"
			" b.crossfade_debut_regle::text, b.crossfade_debut, b.crossfade_fin_regle::text, b.crossfade_fin"
			" FROM sonores s LEFT JOIN feeds m ON m.id = s.feed_id"
			" LEFT JOIN banques b ON b.id = %s"
			" WHERE s.id = %s",
			(choix.banque, choix.sonore),
		).fetchone()
	if ligne is None:
		return Parametres(None, timedelta(0), timedelta(0))
	duree, debut, fin, type_sonore, adresse, secours, artiste, titre, emplacement, *suite = ligne
	detection, debut_detecte, fin_detectee, regle_debut, debut_banque, regle_fin, fin_banque = suite
	crossfade_debut = crossfade(debut, regle_debut, debut_banque, defauts.debut)
	crossfade_fin = crossfade(fin, regle_fin, fin_banque, defauts.fin)
	# Sans durée connue (un stream), les crossfades restent tels quels.
	placement = Placement(timedelta(0), None, crossfade_debut, 0.0, crossfade_fin, 0.0)
	duree_jouee = None
	if isinstance(duree, timedelta):
		placement = placer(
			duree,
			_intervalle(debut_detecte),
			_intervalle(fin_detectee),
			(detection is True) and (type_sonore == "fichier"),
			crossfade_debut,
			crossfade_fin,
			defauts.entree,
			defauts.sortie,
		)
		duree_jouee = placement.duree
	return Parametres(
		duree_jouee,
		placement.fondu_entree,
		placement.fondu_sortie,
		stream=type_sonore == "stream",
		adresse=texte_ou_rien(adresse),
		secours=entier_ou_rien(secours),
		artiste=texte_ou_rien(artiste),
		titre=texte_ou_rien(titre),
		emplacement=texte_ou_rien(emplacement),
		decalage=placement.decalage,
		volume_de_depart=placement.depart,
		volume_d_arrivee=placement.arrivee,
	)


def _intervalle(valeur: object) -> timedelta | None:
	if isinstance(valeur, timedelta):
		return valeur
	return None


@dataclass
class Diffusion:
	"""La diffusion de la grille sur la sortie audio, pas à pas.

	La connexion a endossé le rôle de la lecture (machincast.base.connecter). Les heures de l'airplay et du log
	viennent de l'horloge ; le moment d'enchaîner vient de la position de la voie dans le sonore.
	"""

	connexion: psycopg.Connection[TupleRow]
	moteur: Moteur
	horloge: Horloge
	hasard: Hasard
	delai_reconnexion: timedelta = DELAI_RECONNEXION
	sorties: Sorties | None = None
	"""Modules de sortie : journal, CSV, .pls et HTML (https://github.com/dascritch/machincast/issues/19)."""
	etat: SocketEtat | None = None
	"""Socket d'état pour l'interface (https://github.com/dascritch/machincast/issues/20)."""
	historique: Historique = EN_BASE
	"""Où se lisent et s'écrivent passages et log : la base, ou la mémoire en simulation."""
	publication_minimale: float = PUBLICATION_MINIMALE
	"""Intervalle maximal entre deux publications de l'état, en secondes, pour suivre la progression."""
	metadonnees: Metadonnees | None = None
	"""Masquage et texte public par défaut, pour le texte public de la socket d'état ; à défaut, ceux des sorties."""
	crossfades: Crossfades = SANS_DEFAUTS
	"""Crossfades par défaut des sonores qui n'en ont pas de paramétré (https://github.com/dascritch/machincast/issues/145)."""
	analyseur: Analyseur | None = None
	"""Analyse du prochain sonore qui n'a pas été vérifié en entier
	(https://github.com/dascritch/machincast/issues/181) ; aucune en simulation."""
	ordonnanceur: Ordonnanceur = field(init=False)
	courant: Lecture | None = field(default=None, init=False)
	sortants: list[Lecture] = field(default_factory=list, init=False)
	"""Sonores qui finissent leur crossfade de fin sous le sonore courant."""
	en_attente: Choix | None = field(default=None, init=False)
	"""Sonore suivant, qui attend la fin du sonore courant faute de superposition."""
	sonde: Sonde | None = field(default=None, init=False)
	"""Reconnexion du stream tombé, s'il y en a un."""
	expirations_verifiees: datetime | None = field(default=None, init=False)
	"""Heure de la dernière vérification de tous les sonores."""
	reserve: Reserve | None = field(default=None, init=False)
	"""Prochain sonore, réservé au début du sonore en cours : il sera joué s'il est encore valable."""
	_publication: tuple[str, datetime | None] = field(default=("", None), init=False)
	"""Dernier état publié sur la socket, sans ce qui change à chaque pas, et heure de sa publication."""
	_details_reserve: tuple[Reserve, dict[str, Any]] | None = field(default=None, init=False)
	"""Contexte du sonore réservé, lu une fois pour lui."""
	_a_l_antenne: Choix | None = field(default=None, init=False)
	"""Le dernier passage commencé, pour noter les débuts et les fins d'événements et de séquences."""
	_sequence_a_l_antenne: str = field(default="", init=False)
	"""Le message de la séquence à l'antenne, gardé pour sa fin."""
	a_venir: list[Prevu] = field(default_factory=list, init=False)
	"""Les sonores prévus après le prochain, dans l'ordre (https://github.com/dascritch/machincast/issues/228)."""
	_attendu: Choix | None = field(default=None, init=False)
	"""Le prochain sonore, pris pour être joué : s'il démarre, les sonores à venir avancent d'un cran."""
	_empreinte: str | None = field(default=None, init=False)
	"""Empreinte de la grille quand les sonores à venir ont été prévus (EMPREINTE_DE_LA_GRILLE)."""

	def __post_init__(self) -> None:
		self.ordonnanceur = Ordonnanceur(self.connexion, self.hasard, self.historique)

	def demarrer(self) -> None:
		"""Ouvre la socket d'état, puis consigne le démarrage ; lève SocketEtatOccupee si un autre Machin lecture
		diffuse déjà."""
		instant = self.horloge.maintenant()
		if self.etat is not None:
			try:
				self.etat.ouvrir()
			except SocketEtatOccupee:
				raise
			except OSError as erreur:
				self.historique.consigner(
					self.connexion, "alerte", "socket d'état indisponible", f"{self.etat.chemin} : {erreur}", instant
				)
				self.etat = None
		self.historique.consigner(self.connexion, "info", "démarrage", f"Machin_lecture {__version__}", instant)
		self._verifier_les_expirations(instant)
		self._publier(instant)

	def pas(self) -> None:
		instant = self.horloge.maintenant()
		self._verifier_les_expirations(instant)
		self.moteur.traiter_messages()
		self._terminer_les_voies_arretees(instant)
		self._ecarter_une_lecture_bloquee(instant)
		if self.etat is not None:
			for demande in self.etat.demandes():
				if demande.commande == RELIRE_LA_GRILLE:
					self.relire_la_grille()
				else:
					self.interrompre(demande.element)
		courant = self.courant
		if courant is not None:
			decision = self.ordonnanceur.decider(instant, courant.en_cours)
			if decision.couper:
				reserve = self.reserve
				self._couper(instant)
				self._jouer_la_decision(decision, reserve, instant)
			elif decision.eteindre:
				self._eteindre(courant, (self._prendre_la_reserve(instant)) or (decision.jouer), instant)
			elif (not courant.suivant_demande) and (self._au_crossfade_de_fin(courant)):
				courant.suivant_demande = True
				self._preparer_le_suivant(courant, instant)
		elif not self.sortants:
			# Rien sur la sortie ; tant qu'un stream s'éteint sans superposition, le suivant attend.
			reserve = self.reserve
			choix, self.en_attente = self.en_attente, None
			choix = (choix) or (self._prendre_la_reserve(instant))
			if choix is not None:
				self._jouer(choix, instant)
			else:
				self._jouer_la_decision(self.ordonnanceur.decider(instant, None), reserve, instant)
		self._suivre_la_sonde(instant)
		self._publier(instant)

	def arreter(self) -> None:
		"""Arrête la sortie : les passages en cours se terminent sans incident, puis l'arrêt est consigné."""
		instant = self.horloge.maintenant()
		self.moteur.traiter_messages()
		self._terminer_les_voies_arretees(instant)
		self.moteur.couper()
		for lecture in self._lectures():
			self._terminer(lecture.passage, instant)
		self.courant, self.sortants, self.en_attente, self.sonde, self.reserve = None, [], None, None, None
		self.a_venir = []
		self._noter_l_antenne(None, instant)
		self.historique.consigner(self.connexion, "info", "arrêt", "arrêt demandé", instant)
		self._publier(instant, arret=True)
		if self.etat is not None:
			self.etat.fermer()

	def relire_la_grille(self) -> None:
		"""La grille a pu changer, et le changement doit valoir aussitôt
		(https://github.com/dascritch/machincast/issues/273, https://github.com/dascritch/machincast/issues/266) : si
		ce qui règle l'antenne a changé (EMPREINTE_DE_LA_GRILLE), la coupure du sonore en cours, le prochain sonore et
		les sonores à venir sont recalculés, comme au début d'un sonore ; sinon, rien ne change. Rien à recalculer sans
		sonore à l'antenne, ni quand le suivant est déjà lancé, au crossfade de fin : la grille se relit alors au pas
		suivant, comme toujours."""
		courant = self.courant
		if (courant is None) or (courant.suivant_demande) or (self._empreinte_de_la_grille() == self._empreinte):
			return
		instant = self.horloge.maintenant()
		self._attendu = None
		self._reserver(instant)
		self._publier(instant)

	def interrompre(self, element: str) -> bool:
		"""Interruption manuelle (https://github.com/dascritch/machincast/issues/228) : sauter au sonore suivant
		(« sonore »), sauter après la séquence (« sequence »), ou couper l'événement par le fil musical
		(« evenement ») ; False si elle est ignorée, faute de rien à interrompre."""
		instant = self.horloge.maintenant()
		courant = self.courant
		if courant is None:
			journal.warning(f"{IGNOREE} : rien à l'antenne")
			return False
		choix = courant.choix
		evenement = choix.occurrence.evenement
		if (element == "sequence") and (choix.ligne is None):
			journal.warning(f"{IGNOREE} : aucune séquence à l'antenne")
			return False
		if (element == "evenement") and (evenement.priorite is Priorite.FIL_MUSICAL):
			journal.warning(f"{IGNOREE} : le fil musical est déjà à l'antenne")
			return False
		message = f"du sonore « {self._nom_du_sonore(choix.sonore)} »"
		if element == "sequence":
			message = f"de la séquence {self._sequence_a_l_antenne}"
		if element == "evenement":
			message = f"de l'événement « {evenement.nom} »"
		self.historique.consigner(
			self.connexion,
			"info",
			INTERRUPTION_MANUELLE,
			message,
			instant,
			sonore=choix.sonore,
			evenement=evenement.id,
		)
		if self.sorties is not None:
			self.sorties.annoncer(INTERRUPTION_MANUELLE, message)
		if element != "sonore":
			self.ordonnanceur.abandonner_la_sequence(courant.passage.id)
		suivant = None
		if element == "evenement":
			self.ordonnanceur.rendre_au_fil_musical(instant)
			self.a_venir = []
		else:
			suivant = self._sauter(courant, element == "sequence", instant)
		if suivant is None:
			suivant = self.ordonnanceur.decider(instant, None).jouer
		fondu = (self.crossfades.fin) or (AUCUN_CROSSFADE)
		self._eteindre(courant, suivant, instant, fondu, (self.crossfades.debut) or (AUCUN_CROSSFADE))
		self._publier(instant)
		return True

	def _sauter(self, courant: Lecture, apres_la_sequence: bool, instant: datetime) -> Choix | None:
		"""Le sonore où sauter : le prochain, ou, après la séquence, le premier sonore prévu qui ne la continue pas ;
		les sonores à venir qui le suivent sont gardés. None s'il n'est pas prévu, ou plus jouable : l'ordonnanceur
		décide alors, et la liste sera recalculée."""
		reserve = self.reserve
		if (reserve is None) or (reserve.anticipee):
			return None
		candidats: list[tuple[Choix, Prevu | None]] = [(reserve.choix, None)]
		candidats += [(prevu.choix, prevu) for prevu in self.a_venir]
		precedent = courant.choix
		for rang, (choix, prevu) in enumerate(candidats):
			meme_occurrence = precedent.occurrence.cle == choix.occurrence.cle
			if (apres_la_sequence) and (meme_occurrence) and (_continue_la_sequence(precedent, choix)):
				precedent = choix
				continue
			if not self.ordonnanceur.valider(choix, instant):
				return None
			if prevu is not None:
				self._engager(prevu, instant)
			self.a_venir = self.a_venir[rang:]
			self._attendu = choix
			return choix
		return None

	def _nom_du_sonore(self, sonore: int) -> str:
		with self.connexion.transaction():
			ligne = self.connexion.execute(
				"SELECT COALESCE(titre, emplacement, url_stream) FROM sonores WHERE id = %s", (sonore,)
			).fetchone()
		if (ligne is None) or (ligne[0] is None):
			return str(sonore)
		return str(ligne[0])

	# ─── Étapes ────────────────────────────────────────────

	def _lectures(self) -> list[Lecture]:
		return ([] if self.courant is None else [self.courant]) + self.sortants

	def _terminer_les_voies_arretees(self, instant: datetime) -> None:
		for lecture in self._lectures():
			if lecture.voie.etat not in ("finie", "en erreur"):
				continue
			if (lecture.parametres.stream) and (not lecture.eteinte):
				# Un stream n'a pas de fin : arrêté avant son extinction, il est tombé.
				erreur = f"{lecture.parametres.adresse} : {(lecture.voie.erreur) or (FLUX_ARRETE)}"
				self._terminer(lecture.passage, instant, erreur=erreur, nature=FLUX_TOMBE)
				self._suspendre(lecture, instant)
			else:
				self._terminer(lecture.passage, instant, erreur=lecture.voie.erreur)
		self.sortants = [s for s in self.sortants if s.voie.etat == "en cours"]
		if (self.courant is not None) and (self.courant.voie.etat != "en cours"):
			self.courant = None

	def _ecarter_une_lecture_bloquee(self, instant: datetime) -> None:
		"""Un sonore dont le lecteur n'a pas démarré ne jouera rien : son passage se termine en incident, et le sonore
		suivant prend sa place, comme après un sonore fini (https://github.com/dascritch/machincast/issues/281). Un
		stream a son propre délai de connexion, et sa chute son repli : il n'est pas concerné."""
		courant = self.courant
		if (courant is None) or (courant.parametres.stream) or (not courant.voie.bloquee()):
			return
		courant.voie.couper()
		self._terminer(
			courant.passage,
			instant,
			erreur=f"{courant.parametres.emplacement} : {LECTEUR_BLOQUE}",
			nature=LECTURE_BLOQUEE,
		)
		self.courant = None

	@staticmethod
	def _au_crossfade_de_fin(lecture: Lecture) -> bool:
		duree = lecture.parametres.duree
		return (duree is not None) and (lecture.voie.position() >= duree - lecture.parametres.crossfade_fin)

	def _prendre_la_reserve(self, instant: datetime) -> Choix | None:
		"""Le sonore réservé, s'il est encore valable ; la réserve est vidée dans tous les cas."""
		reserve, self.reserve = self.reserve, None
		if (reserve is not None) and (not reserve.anticipee) and (self.ordonnanceur.valider(reserve.choix, instant)):
			self._attendu = reserve.choix
			return reserve.choix
		return None

	def _jouer_la_decision(self, decision: Decision, reserve: Reserve | None, instant: datetime) -> None:
		"""Joue le sonore de la décision ; à la coupure par un événement, ou quand le sonore coupé a fini plus tôt, le
		sonore réservé pour cet événement est joué à sa place, même tiré au hasard, s'il est encore valable."""
		choix = decision.jouer
		if (
			(choix is not None)
			and (reserve is not None)
			and (reserve.anticipee)
			and (reserve.choix.occurrence.cle == choix.occurrence.cle)
			and (self.ordonnanceur.valider(reserve.choix, instant))
		):
			choix = reserve.choix
			self._attendu = choix
		if choix is not None:
			self._jouer(choix, instant)

	def _reserver(self, instant: datetime) -> None:
		"""Au début du sonore en cours, réserve le prochain sonore, puis prévoit les sonores à venir.

		Si c'est le prochain sonore attendu qui a démarré, que la grille n'a pas changé et que la coupure du sonore en
		cours est celle qui était prévue, le premier sonore à venir devient le prochain
		(https://github.com/dascritch/machincast/issues/228). Sinon, le prochain est choisi : si un événement doit
		couper le sonore en cours, c'est celui que cet événement jouera, anticipé à l'instant de la coupure
		(https://github.com/dascritch/machincast/issues/169) ; et les sonores à venir sont recalculés."""
		courant = self.courant
		attendu, self._attendu = self._attendu, None
		coupure = None
		if courant is not None:
			coupure = self.ordonnanceur.coupure(courant.en_cours, instant, _horizon(courant, instant))
			courant.coupure = coupure
		empreinte = self._empreinte_de_la_grille()
		engage = (
			(courant is not None)
			and (attendu is not None)
			and (attendu is courant.choix)
			and (self.a_venir != [])
			and (empreinte == self._empreinte)
			and (_meme_coupure(self.a_venir[0].coupure, coupure))
		)
		self._empreinte = empreinte
		if engage:
			prevu = self.a_venir.pop(0)
			self._engager(prevu, instant)
			self.reserve = Reserve(prevu.choix, prevu.parametres, prevu.sain, prevu.coupure is not None)
		else:
			self.a_venir = []
			self.reserve = self._choisir_la_reserve(coupure, instant)
		if self.reserve is not None:
			self._analyser(self.reserve, instant)
		self._prolonger(instant)

	def _engager(self, prevu: Prevu, instant: datetime) -> None:
		"""Le sonore prévu devient le prochain : ce que sa décision a terminé l'est pour de bon, et ce qu'elle
		consignerait est consigné, à l'heure où le prochain sonore est réservé."""
		self.ordonnanceur.engager(prevu.terminees)
		for consigne in prevu.consignes:
			self.historique.consigner(self.connexion, instant=instant, **consigne)

	def _choisir_la_reserve(self, coupure: Coupure | None, instant: datetime) -> Reserve | None:
		"""Le prochain sonore, choisi au début du sonore en cours ; pour un stream qui s'éteindra à la fin de son
		événement, choisi pour cette fin, où un autre événement reprendra l'antenne
		(https://github.com/dascritch/machincast/issues/242) ; après une coupure, anticipé à son instant."""
		if coupure is None:
			moment = instant
			courant = self.courant
			if (courant is not None) and (courant.parametres.stream):
				moment = (_fin_de_l_occurrence(courant.choix.occurrence)) or (instant)
			choix = self.ordonnanceur.reserver(max(instant, moment))
		else:
			choix = self.ordonnanceur.anticiper(coupure.instant)
		if choix is None:
			return None
		return Reserve(
			choix,
			lire_parametres(self.connexion, choix, self.crossfades),
			est_sain(self.connexion, choix.sonore),
			coupure is not None,
		)

	def _empreinte_de_la_grille(self) -> str:
		with self.connexion.transaction():
			ligne = self.connexion.execute(EMPREINTE_DE_LA_GRILLE).fetchone()
		return "" if ligne is None else str(ligne[0])

	def _prolonger(self, instant: datetime) -> None:
		"""Prévoit les sonores à venir jusqu'à A_VENIR, au bout de la liste : chacun est choisi à l'heure où le
		précédent appellera son suivant, ou à celle de l'événement qui le coupera. La liste s'arrête sur un silence, ou
		après un sonore dont la fin est inconnue."""
		courant, reserve = self.courant, self.reserve
		if (courant is None) or (reserve is None):
			self.a_venir = []
			return
		debuts = self._debuts()
		chaine = [(reserve.choix, reserve.parametres)] + [(prevu.choix, prevu.parametres) for prevu in self.a_venir]
		if any(debut is None for debut in debuts):
			return
		prevus = [_passage_prevu(choix, debut) for (choix, _), debut in zip(chaine, debuts, strict=True) if debut]
		precedent, parametres = chaine[-1]
		debut = debuts[-1]
		terminees: frozenset[tuple[int, datetime | None]] = frozenset()
		if self.a_venir != []:
			terminees = self.a_venir[-1].terminees
		with self.ordonnanceur.prevision(prevus, terminees) as prevision:
			while (len(self.a_venir) < A_VENIR) and (debut is not None):
				occurrence = precedent.occurrence
				en_cours = EnCours(occurrence, debut, debut + ((parametres.duree) or (timedelta(0))), parametres.stream)
				horizon = _horizon_de(debut, parametres, occurrence, instant)
				coupure = self.ordonnanceur.coupure(en_cours, debut, horizon)
				moment = _instant_du_suivant(debut, parametres, occurrence, coupure)
				if moment is None:
					return
				deja = len(prevision.consignes)
				choix = self.ordonnanceur.reserver(moment)
				if choix is None:
					return
				entrant = lire_parametres(self.connexion, choix, self.crossfades)
				prevu = Prevu(
					choix,
					entrant,
					est_sain(self.connexion, choix.sonore),
					coupure,
					frozenset(self.ordonnanceur.terminees),
					self._details(choix, None),
					tuple(prevision.consignes[deja:]),
				)
				self.a_venir.append(prevu)
				debut = _debut_du_suivant(debut, parametres, occurrence, coupure, entrant)
				if debut is not None:
					prevus.append(_passage_prevu(choix, debut))
				precedent, parametres = choix, entrant

	def _debuts(self) -> list[datetime | None]:
		"""Débuts estimés du prochain sonore et des sonores à venir, enchaînés depuis le sonore en cours ; None à partir
		d'un sonore dont la fin est inconnue."""
		courant, reserve = self.courant, self.reserve
		if (courant is None) or (reserve is None):
			return []
		suite = [(reserve.choix, reserve.parametres)] + [(prevu.choix, prevu.parametres) for prevu in self.a_venir]
		coupures = [courant.coupure] + [prevu.coupure for prevu in self.a_venir]
		debut: datetime | None = courant.passage.debut
		parametres, occurrence = courant.parametres, courant.choix.occurrence
		debuts: list[datetime | None] = []
		for (choix, entrant), coupure in zip(suite, coupures, strict=True):
			if debut is not None:
				debut = _debut_du_suivant(debut, parametres, occurrence, coupure, entrant)
			debuts.append(debut)
			parametres, occurrence = entrant, choix.occurrence
		return debuts

	def _analyser(self, reserve: Reserve, instant: datetime) -> None:
		"""Fait analyser le sonore réservé s'il n'a pas été vérifié en entier, sans attendre l'analyse."""
		analyseur = self.analyseur
		sonore = reserve.choix.sonore
		if (analyseur is None) or (not analyseur.a_demander(sonore, instant)):
			return
		with self.connexion.transaction():
			if not a_analyser(self.connexion, sonore):
				return
		emplacement = reserve.parametres.emplacement
		try:
			analyseur.lancer(sonore, instant)
		except OSError as erreur:
			self.historique.consigner(
				self.connexion, "alerte", "analyse impossible", f"{emplacement} : {erreur}", instant, sonore=sonore
			)
			return
		self.historique.consigner(
			self.connexion,
			"info",
			"analyse du prochain sonore",
			f"{emplacement} : audit complet par Machin indexation, avant sa lecture",
			instant,
			sonore=sonore,
		)

	def _preparer_le_suivant(self, courant: Lecture, instant: datetime) -> None:
		choix = (self._prendre_la_reserve(instant)) or (self.ordonnanceur.decider(instant, None).jouer)
		if choix is None:
			# Rien ensuite : le sonore finit avec son fondu, et le prochain pas sans voie redemande.
			return
		parametres = lire_parametres(self.connexion, choix, self.crossfades)
		if superposition(courant.parametres.crossfade_fin, parametres.crossfade_debut):
			self._jouer(choix, instant, courant.parametres.crossfade_fin)
		else:
			courant.voie.supprimer_fondu_de_sortie()
			self.en_attente = choix

	def _eteindre(
		self,
		courant: Lecture,
		choix: Choix | None,
		instant: datetime,
		fondu: timedelta | None = None,
		montee: timedelta | None = None,
	) -> None:
		"""Fin de l'événement d'un stream : le sonore s'éteint pendant son crossfade de fin, et le sonore choisi
		enchaîne. Pour une interruption manuelle, le sonore s'éteint pendant fondu, aussitôt sans durée, et le sonore
		choisi monte pendant montee : il démarre aussitôt, sauf s'il doit attendre la fin d'un fondu sans montée."""
		if fondu is None:
			fondu = courant.parametres.crossfade_fin
		courant.eteinte = True
		self.reserve = None
		courant.voie.eteindre(fondu)
		self.courant = None
		self.sortants.append(courant)
		self._terminer_les_voies_arretees(instant)
		if choix is None:
			return
		entree = montee
		if entree is None:
			entree = lire_parametres(self.connexion, choix, self.crossfades).crossfade_debut
		if ((montee is not None) and (fondu <= timedelta(0))) or (superposition(fondu, entree)):
			self._jouer(choix, instant, fondu, montee)
		else:
			self.en_attente = choix

	def _suspendre(self, lecture: Lecture, instant: datetime) -> None:
		"""Stream tombé : l'ordonnanceur le remplace, et la sonde le reconnectera."""
		self.ordonnanceur.suspendre(lecture.choix.occurrence, lecture.parametres.secours)
		self.a_venir = []
		self.sonde = Sonde(lecture.choix, lecture.parametres, instant + self.delai_reconnexion, instant)

	def _suivre_la_sonde(self, instant: datetime) -> None:
		sonde = self.sonde
		if sonde is None:
			return
		suspension = self.ordonnanceur.suspension
		if (suspension is None) or (suspension.occurrence.cle != sonde.choix.occurrence.cle):
			if sonde.voie is not None:
				sonde.voie.fermer()
			self.sonde = None
			self.historique.consigner(
				self.connexion,
				"info",
				"reconnexion abandonnée",
				f"{sonde.parametres.adresse} : l'événement du stream n'est plus à l'antenne",
				instant,
				sonore=sonde.choix.sonore,
				evenement=sonde.choix.occurrence.evenement.id,
			)
			return
		if sonde.voie is None:
			if (instant >= sonde.prochaine_tentative) and (sonde.parametres.adresse is not None):
				sonde.voie = self.moteur.jouer(sonde.parametres.adresse, None, muette=True)
			return
		sonde.voie.traiter()
		if sonde.voie.etat != "en cours":
			sonde.voie.fermer()
			sonde.voie = None
			sonde.prochaine_tentative = instant + self.delai_reconnexion
		elif sonde.voie.position() > timedelta(0):
			self._reprendre(sonde, sonde.voie, instant)

	def _reprendre(self, sonde: Sonde, voie: VoieLecture, instant: datetime) -> None:
		"""Le flux est revenu : crossfade immédiat vers le stream, pendant son crossfade de début."""
		fondu = sonde.parametres.crossfade_debut
		voie.fondu(1.0, fondu)
		for lecture in self._lectures():
			if fondu > timedelta(0):
				lecture.eteinte = True
				lecture.voie.eteindre(fondu)
			else:
				lecture.voie.couper()
				self._terminer(lecture.passage, instant)
		self.sortants = [lecture for lecture in self._lectures() if lecture.voie.etat == "en cours"]
		self.en_attente, self.sonde = None, None
		self.ordonnanceur.reprendre()
		choix = sonde.choix
		passage = self._commencer(choix, instant)
		self.courant = Lecture(choix, sonde.parametres, voie, passage)
		self.historique.expirer(self.connexion, instant, choix.sonore)
		self._reserver(instant)
		panne = round((instant - sonde.depuis).total_seconds())
		self.historique.consigner(
			self.connexion,
			"incident",
			REPRISE_DU_FLUX,
			f"{sonde.parametres.adresse} : le flux est revenu après {panne} s de panne",
			instant,
			sonore=choix.sonore,
			evenement=choix.occurrence.evenement.id,
		)

	def _couper(self, instant: datetime) -> None:
		self.moteur.couper()
		for lecture in self._lectures():
			self._terminer(lecture.passage, instant, coupe=True)
		self.courant, self.sortants, self.en_attente, self.reserve = None, [], None, None

	def _jouer(
		self,
		choix: Choix,
		instant: datetime,
		crossfade_fin_precedent: timedelta = timedelta(0),
		montee: timedelta | None = None,
	) -> None:
		"""Démarre le sonore ; un fichier introuvable est écarté, et l'ordonnanceur donne le suivant. montee : la durée
		de la montée, imposée par une interruption manuelle ; sinon, son crossfade de début s'il se superpose au
		précédent."""
		suivant: Choix | None = choix
		chemin: Path | str | None = None
		essayes: set[int] = set()
		# Chaque sonore n'est essayé qu'une fois : la boucle s'arrête même si l'ordonnanceur le redonne.
		while (suivant is not None) and (suivant.sonore not in essayes):
			parametres = lire_parametres(self.connexion, suivant, self.crossfades)
			chemin = parametres.adresse
			if not parametres.stream:
				chemin = verifier_avant_lecture(self.connexion, suivant.sonore, self.historique)
			if chemin is not None:
				break
			essayes.add(suivant.sonore)
			self.ordonnanceur.exclure(suivant.sonore, instant)
			suivant = self.ordonnanceur.decider(instant, None).jouer
		if (suivant is None) or (chemin is None):
			return
		if montee is None:
			montee = fondu_d_entree(crossfade_fin_precedent, parametres.crossfade_debut)
		voie = self.moteur.jouer(
			chemin,
			parametres.duree,
			montee,
			parametres.crossfade_fin,
			decalage=parametres.decalage,
			depart=parametres.volume_de_depart,
			arrivee=parametres.volume_d_arrivee,
		)
		passage = self._commencer(suivant, instant)
		if self.courant is not None:
			self.sortants.append(self.courant)
		self.courant = Lecture(suivant, parametres, voie, passage)
		self.historique.expirer(self.connexion, instant, suivant.sonore)
		self._reserver(instant)

	def _commencer(self, choix: Choix, instant: datetime) -> Passage:
		self._noter_l_antenne(choix, instant)
		ligne = choix.ligne
		passage = self.historique.commencer_passage(
			self.connexion,
			choix.sonore,
			choix.banque,
			choix.occurrence.evenement.id,
			choix.element.id,
			instant,
			None if ligne is None else ligne.sequence,
			None if ligne is None else ligne.id,
		)
		if self.sorties is not None:
			self.sorties.passage_commence(self.connexion, passage)
		return passage

	def _terminer(
		self,
		passage: Passage,
		instant: datetime,
		coupe: bool = False,
		erreur: str | None = None,
		nature: str = "lecture interrompue",
	) -> None:
		self.historique.terminer_passage(self.connexion, passage, instant, coupe=coupe, erreur=erreur, nature=nature)
		if self.sorties is not None:
			self.sorties.passage_termine(self.connexion, passage, instant)

	# ─── Socket d'état (https://github.com/dascritch/machincast/issues/20) ───

	def _publier(self, instant: datetime, arret: bool = False) -> None:
		"""Publie l'état s'il a changé, ou si le dernier date de publication_minimale, pour la progression."""
		if self.etat is None:
			return
		message = self._etat(instant, arret)
		stable = json.dumps({**message, "en_cours": _sans_progression(message["en_cours"])}, default=str)
		precedent, publie_a = self._publication
		ancien = (publie_a is None) or (instant - publie_a >= timedelta(seconds=self.publication_minimale))
		if (arret) or (stable != precedent) or (ancien):
			self.etat.publier({"horodatage": iso(instant), **message})
			self._publication = (stable, instant)

	def _etat(self, instant: datetime, arret: bool) -> dict[str, Any]:
		courant = self.courant
		en_cours = None
		if courant is not None:
			parametres = courant.parametres
			position = courant.voie.position()
			duree = parametres.duree
			if courant.details is None:
				courant.details = self._details(courant.choix, courant.passage)
			en_cours = {
				**_affichage(courant.choix, parametres),
				**courant.details,
				"debut": iso(courant.passage.debut),
				"duree": _secondes(duree),
				"fin_estimee": iso(_fin_estimee(courant)),
				"coupe_par": None,
				"coupe_par_id": None,
				"position": round(position.total_seconds(), 3),
				"progression": _progression(position, duree),
			}
			if courant.coupure is not None:
				evenement = courant.coupure.occurrence.evenement
				en_cours |= {"coupe_par": evenement.nom, "coupe_par_id": evenement.id}
		prochain = None
		a_venir: list[dict[str, Any]] = []
		reserve = self.reserve
		if reserve is not None:
			if (self._details_reserve is None) or (self._details_reserve[0] is not reserve):
				self._details_reserve = (reserve, self._details(reserve.choix, None))
			debuts = self._debuts()
			if debuts == []:
				debuts = [None]
			# La fin de chaque sonore : le début de l'événement qui coupera le suivant, sinon sa durée.
			coupures = [prevu.coupure for prevu in self.a_venir] + [None]
			suite = [(reserve.choix, reserve.parametres, reserve.sain, self._details_reserve[1])]
			suite += [(prevu.choix, prevu.parametres, prevu.sain, prevu.details) for prevu in self.a_venir]
			annonces = [
				_annonce(choix, parametres, sain, details, debut, coupure)
				for (choix, parametres, sain, details), debut, coupure in zip(suite, debuts, coupures, strict=False)
			]
			prochain, a_venir = annonces[0], annonces[1:]
		marche = "arret" if arret else ("diffusion" if (courant is not None) or (self.sortants) else "silence")
		return {"etat": marche, "en_cours": en_cours, "prochain": prochain, "a_venir": a_venir}

	def _noter_l_antenne(self, choix: Choix | None, instant: datetime) -> None:
		"""Avant le passage qui commence, ou à l'arrêt (None) : la fin de la séquence et de l'événement qu'il ne
		continue pas, puis le début des siens, dans le log et le journal du binaire
		(https://github.com/dascritch/machincast/issues/153). Les heures sont celles de l'antenne."""
		precedent, self._a_l_antenne = self._a_l_antenne, choix
		meme_occurrence = (
			(precedent is not None) and (choix is not None) and (precedent.occurrence.cle == choix.occurrence.cle)
		)
		suite = (meme_occurrence) and (_continue_la_sequence(precedent, choix))
		if (precedent is not None) and (precedent.ligne is not None) and (not suite):
			self._noter(FIN_DE_SEQUENCE, self._sequence_a_l_antenne, precedent, instant)
		if (precedent is not None) and (not meme_occurrence):
			self._noter(FIN_D_EVENEMENT, f"« {precedent.occurrence.evenement.nom} »", precedent, instant)
		if choix is None:
			return
		if not meme_occurrence:
			self._noter(DEBUT_D_EVENEMENT, _evenement_a_l_antenne(choix.occurrence), choix, instant)
		if (choix.ligne is not None) and (not suite):
			# Dans sa propre transaction : la connexion n'en laisse jamais une ouverte, qui retiendrait l'airplay.
			with self.connexion.transaction():
				ligne = self.connexion.execute(
					"SELECT nom_interne FROM sequences WHERE id = %s", (choix.ligne.sequence,)
				).fetchone()
			nom = str(choix.ligne.sequence)
			if ligne is not None:
				nom = str(ligne[0])
			self._sequence_a_l_antenne = f"« {nom} », dans « {choix.occurrence.evenement.nom} »"
			self._noter(DEBUT_DE_SEQUENCE, self._sequence_a_l_antenne, choix, instant)

	def _noter(self, nature: str, message: str, choix: Choix, instant: datetime) -> None:
		self.historique.consigner(
			self.connexion, "info", nature, message, instant, evenement=choix.occurrence.evenement.id
		)
		if self.sorties is not None:
			self.sorties.annoncer(nature, message)

	def _details(self, choix: Choix, passage: Passage | None) -> dict[str, Any]:
		"""Le contexte d'un sonore pour la socket d'état (https://github.com/dascritch/machincast/issues/144) :
		l'occurrence de son événement, sa séquence et sa banque ; pour le sonore en cours, le texte que la page
		publique affiche de son passage, masquage appliqué."""
		occurrence = choix.occurrence
		sequence = choix.element.sequence
		with self.connexion.transaction():
			noms = self.connexion.execute(
				"SELECT (SELECT nom_interne FROM sequences WHERE id = %s),"
				" (SELECT nom_interne FROM banques WHERE id = %s)",
				(sequence, choix.banque),
			).fetchone()
		assert noms is not None
		details: dict[str, Any] = {
			"evenement_id": occurrence.evenement.id,
			"evenement_priorite": occurrence.evenement.priorite.value,
			"evenement_debut": iso(occurrence.debut),
			"evenement_fin": iso(occurrence.fin),
			"sequence": noms[0],
			"sequence_id": sequence,
			"banque": noms[1],
			"banque_id": choix.banque,
		}
		if passage is not None:
			lignes = lire_passages(self.connexion, 1, passage.id)
			details["texte_public"] = None
			if lignes != []:
				details["texte_public"] = texte_public(lignes[0], self._metadonnees())
		return details

	def _metadonnees(self) -> Metadonnees:
		if self.metadonnees is not None:
			return self.metadonnees
		if self.sorties is not None:
			return self.sorties.metadonnees
		return Metadonnees(masquer=False, texte_public="")

	def _verifier_les_expirations(self, instant: datetime) -> None:
		derniere = self.expirations_verifiees
		if (derniere is None) or (instant - derniere >= VERIFICATION_DES_EXPIRATIONS):
			self.expirations_verifiees = instant
			self.historique.expirer(self.connexion, instant)


def _affichage(choix: Choix, parametres: Parametres) -> dict[str, Any]:
	return {
		"sonore": choix.sonore,
		"type": "stream" if parametres.stream else "fichier",
		"artiste": parametres.artiste,
		"titre": parametres.titre,
		"emplacement": parametres.emplacement,
		"evenement": choix.occurrence.evenement.nom,
	}


def _annonce(
	choix: Choix,
	parametres: Parametres,
	sain: bool | None,
	details: dict[str, Any],
	debut: datetime | None,
	coupure: Coupure | None,
) -> dict[str, Any]:
	"""Ce que la socket d'état dit du prochain sonore, ou d'un sonore à venir."""
	duree = parametres.duree
	fin = None
	if (debut is not None) and (duree is not None):
		fin = debut + duree
	if coupure is not None:
		fin = coupure.instant
	return {
		**_affichage(choix, parametres),
		**details,
		"debut_estime": iso(debut),
		"duree": _secondes(duree),
		"fin_estimee": iso(fin),
		"sain": sain,
	}


def _passage_prevu(choix: Choix, debut: datetime) -> Passage:
	ligne = choix.ligne
	return Passage(
		uuid.uuid4(),
		choix.sonore,
		choix.banque,
		choix.occurrence.evenement.id,
		choix.element.id,
		debut,
		None if ligne is None else ligne.sequence,
		None if ligne is None else ligne.id,
	)


def _meme_coupure(prevue: Coupure | None, coupure: Coupure | None) -> bool:
	if (prevue is None) or (coupure is None):
		return (prevue is None) and (coupure is None)
	return (prevue.instant == coupure.instant) and (prevue.occurrence.cle == coupure.occurrence.cle)


def _fin_de_l_occurrence(occurrence: Occurrence) -> datetime | None:
	if occurrence.fin is None:
		return None
	return occurrence.fin.astimezone()


def _instant_du_suivant(
	debut: datetime, parametres: Parametres, occurrence: Occurrence, coupure: Coupure | None
) -> datetime | None:
	"""Quand le sonore qui commence à debut appellera son suivant : à la coupure, au début de son crossfade de fin, ou,
	pour un stream, à la fin de son événement ; None si on ne le sait pas."""
	if coupure is not None:
		return coupure.instant
	if parametres.duree is not None:
		return debut + max(timedelta(0), parametres.duree - parametres.crossfade_fin)
	if not parametres.stream:
		return None
	return _fin_de_l_occurrence(occurrence)


def _debut_du_suivant(
	debut: datetime, parametres: Parametres, occurrence: Occurrence, coupure: Coupure | None, entrant: Parametres
) -> datetime | None:
	"""Quand démarrera le sonore entrant, après celui qui commence à debut : à la coupure, qui est nette ; au début du
	crossfade de fin s'ils se superposent, sinon à la fin ; pour un stream, à la fin de son événement, où il s'éteint.
	None si on ne le sait pas."""
	if coupure is not None:
		return coupure.instant
	if parametres.duree is not None:
		return debut + enchainement(parametres.duree, parametres.crossfade_fin, entrant.crossfade_debut)
	fin = None
	if parametres.stream:
		fin = _fin_de_l_occurrence(occurrence)
	if (fin is None) or (superposition(parametres.crossfade_fin, entrant.crossfade_debut)):
		return fin
	return fin + parametres.crossfade_fin


def _continue_la_sequence(precedent: Choix | None, choix: Choix | None) -> bool:
	"""Le passage suit-il le précédent dans la même séquence, un élément plus loin ?"""
	if (precedent is None) or (choix is None) or (precedent.ligne is None) or (choix.ligne is None):
		return False
	return (precedent.element.id == choix.element.id) and (choix.ligne.position > precedent.ligne.position)


def _heure(instant: datetime) -> str:
	"""« 20:00 », ou « 19:59:51 » quand les secondes comptent."""
	if instant.second == 0:
		return f"{instant:%H:%M}"
	return f"{instant:%H:%M:%S}"


def _evenement_a_l_antenne(occurrence: Occurrence) -> str:
	"""« « Journal », émission, de 20:00 à 20:30 » ; « depuis 19:00 » sans fin, « permanent » pour un fil musical."""
	debut, fin = occurrence.debut, occurrence.fin
	heures = "permanent"
	if (debut is not None) and (fin is None):
		heures = f"depuis {_heure(debut)}"
	if (debut is not None) and (fin is not None):
		heures = f"de {_heure(debut)} à {_heure(fin)}"
	return f"« {occurrence.evenement.nom} », {PRIORITES[occurrence.evenement.priorite]}, {heures}"


def crossfade(du_sonore: object, regle: object, de_la_banque: object, defaut: timedelta | None = None) -> timedelta:
	"""Le crossfade retenu, d'un côté : celui que la banque impose ; sinon celui du sonore, s'il est paramétré
	(0 seconde en est un) ; sinon celui que la banque applique à défaut ; sinon celui de la configuration ; sinon
	aucun. Sans banque, la règle est None (https://github.com/dascritch/machincast/issues/145)."""
	banque = AUCUN_CROSSFADE
	if isinstance(de_la_banque, timedelta):
		banque = de_la_banque
	if regle == "impose":
		return banque
	if isinstance(du_sonore, timedelta):
		return du_sonore
	if regle == "a_defaut":
		return banque
	return (defaut) or (AUCUN_CROSSFADE)


def _horizon(lecture: Lecture, instant: datetime) -> datetime:
	"""Jusqu'où un événement qui commence coupe le sonore : jusqu'à ce que le suivant soit demandé, au début de son
	crossfade de fin ; pour un stream, jusqu'à la fin de son occurrence, où il s'éteint, ou HORIZON_DES_COUPURES."""
	return _horizon_de(lecture.passage.debut, lecture.parametres, lecture.choix.occurrence, instant)


def _horizon_de(debut: datetime, parametres: Parametres, occurrence: Occurrence, instant: datetime) -> datetime:
	duree = parametres.duree
	if duree is not None:
		return debut + duree - parametres.crossfade_fin
	horizon = max(instant, debut) + HORIZON_DES_COUPURES
	fin = _fin_de_l_occurrence(occurrence)
	if fin is not None:
		horizon = min(horizon, fin)
	return horizon


def _fin_estimee(lecture: Lecture) -> datetime | None:
	"""L'instant de la coupure annoncée, sinon la fin du sonore ; pour un stream, la fin de son événement, où il
	s'éteint (https://github.com/dascritch/machincast/issues/242), None sans elle."""
	if lecture.coupure is not None:
		return lecture.coupure.instant
	if lecture.parametres.duree is None:
		if not lecture.parametres.stream:
			return None
		return _fin_de_l_occurrence(lecture.choix.occurrence)
	return lecture.passage.debut + lecture.parametres.duree


def _secondes(duree: timedelta | None) -> float | None:
	if duree is None:
		return None
	return round(duree.total_seconds(), 3)


def _progression(position: timedelta, duree: timedelta | None) -> float | None:
	"""Part jouée du sonore, de 0 à 1, au millième ; None sans durée connue."""
	if not duree:
		return None
	return round(min(1.0, position / duree), 3)


def _sans_progression(en_cours: object) -> object:
	if not isinstance(en_cours, dict):
		return en_cours
	return {cle: valeur for cle, valeur in en_cours.items() if cle not in ("position", "progression")}


def installer_arret() -> threading.Event:
	"""SIGTERM (arrêt du service) et SIGINT (Ctrl-C) demandent l'arrêt de la diffusion, sans l'interrompre en
	plein pas : la boucle le voit à la fin du pas, et arrête proprement."""
	arret = threading.Event()

	def demander(numero: int, cadre: FrameType | None) -> None:
		arret.set()

	signal.signal(signal.SIGTERM, demander)
	signal.signal(signal.SIGINT, demander)
	return arret


def diffuser(diffusion: Diffusion, arret: threading.Event, pause: float = PAUSE) -> None:
	"""Fait tourner la diffusion jusqu'à la demande d'arrêt, puis l'arrête proprement.

	Sur une erreur (base de données perdue, par exemple), la sortie est coupée, la socket d'état fermée et effacée,
	pour que l'interface voie aussitôt l'arrêt (https://github.com/dascritch/machincast/issues/187), et l'erreur
	remonte.
	"""
	diffusion.demarrer()
	try:
		while not arret.is_set():
			diffusion.pas()
			arret.wait(pause)
	except BaseException:
		diffusion.moteur.couper()
		if diffusion.etat is not None:
			diffusion.etat.fermer()
		raise
	diffusion.arreter()
