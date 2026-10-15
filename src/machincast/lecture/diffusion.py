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

Expiration (https://github.com/dascritch/machincast/issues/18, machincast.lecture.expiration) : chaque passage qui
commence vérifie si son sonore a atteint son maximum de lectures ; tous les sonores sont vérifiés au démarrage, puis
toutes les VERIFICATION_DES_EXPIRATIONS, pour les périodes de diffusion terminées.
"""

import signal
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import FrameType

import psycopg
from psycopg.rows import TupleRow

from machincast import __version__
from machincast.hasard import Hasard
from machincast.horloge import Horloge
from machincast.lecture.deroule import Choix, Decision, EnCours, Ordonnanceur
from machincast.lecture.enregistrement import Passage, commencer_passage, consigner, terminer_passage
from machincast.lecture.expiration import expirer
from machincast.lecture.fichiers import verifier_avant_lecture
from machincast.lecture.moteur import MoteurAudio, Voie, fondu_d_entree, superposition

PAUSE = 0.05
"""Pause entre deux pas de la boucle, en secondes : la précision de l'enchaînement et de la coupure."""

DELAI_RECONNEXION = timedelta(seconds=5)
"""Délai entre deux tentatives de reconnexion d'un stream tombé."""

VERIFICATION_DES_EXPIRATIONS = timedelta(minutes=1)
"""Intervalle entre deux vérifications de tous les sonores (fin de période de diffusion)."""

FLUX_ARRETE = "le flux s'est arrêté avant la fin de son événement"
FLUX_TOMBE = "flux tombé"
REPRISE_DU_FLUX = "reprise du flux"


@dataclass(frozen=True)
class Parametres:
	"""Ce que le moteur audio doit savoir d'un sonore."""

	duree: timedelta | None
	crossfade_debut: timedelta
	crossfade_fin: timedelta
	stream: bool = False
	adresse: str | None = None
	"""Adresse d'un stream : directe, ou celle de son marque-page."""
	secours: int | None = None
	"""Événement de secours d'un stream."""


@dataclass
class Lecture:
	"""Un sonore sur la sortie : son choix, sa voie et son passage dans l'airplay."""

	choix: Choix
	parametres: Parametres
	voie: Voie
	passage: Passage
	suivant_demande: bool = False
	"""L'ordonnanceur a déjà donné le sonore suivant, au début du crossfade de fin."""
	eteinte: bool = False
	"""La voie s'éteint en fondu et s'arrêtera d'elle-même : la fin du passage est normale."""

	@property
	def en_cours(self) -> EnCours:
		debut = self.passage.debut
		fin_prevue = debut + (self.parametres.duree or timedelta(0))
		return EnCours(self.choix.occurrence, debut, fin_prevue, self.parametres.stream)


@dataclass
class Sonde:
	"""Reconnexion d'un stream tombé : une voie muette, retentée tous les delai_reconnexion."""

	choix: Choix
	parametres: Parametres
	prochaine_tentative: datetime
	depuis: datetime
	"""Heure de la panne."""
	voie: Voie | None = None


def lire_parametres(connexion: psycopg.Connection[TupleRow], sonore: int) -> Parametres:
	with connexion.transaction():
		ligne = connexion.execute(
			"SELECT s.duree, s.crossfade_debut, s.crossfade_fin, s.type::text, COALESCE(s.url_stream, m.url),"
			" s.secours_evenement_id FROM sonores s LEFT JOIN marques_pages_streams m ON m.id = s.marque_page_id"
			" WHERE s.id = %s",
			(sonore,),
		).fetchone()
	if ligne is None:
		return Parametres(None, timedelta(0), timedelta(0))
	duree, debut, fin, type_sonore, adresse, secours = ligne
	return Parametres(
		duree if isinstance(duree, timedelta) else None,
		debut if isinstance(debut, timedelta) else timedelta(0),
		fin if isinstance(fin, timedelta) else timedelta(0),
		stream=type_sonore == "stream",
		adresse=None if adresse is None else str(adresse),
		secours=None if secours is None else int(str(secours)),
	)


@dataclass
class Diffusion:
	"""La diffusion de la grille sur la sortie audio, pas à pas.

	La connexion a endossé le rôle de la lecture (machincast.base.connecter). Les heures de l'airplay et du log
	viennent de l'horloge ; le moment d'enchaîner vient de la position de la voie dans le sonore.
	"""

	connexion: psycopg.Connection[TupleRow]
	moteur: MoteurAudio
	horloge: Horloge
	hasard: Hasard
	delai_reconnexion: timedelta = DELAI_RECONNEXION
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

	def __post_init__(self) -> None:
		self.ordonnanceur = Ordonnanceur(self.connexion, self.hasard)

	def demarrer(self) -> None:
		instant = self.horloge.maintenant()
		consigner(self.connexion, "info", "démarrage", f"Machin_lecture {__version__}", instant)
		self._verifier_les_expirations(instant)

	def pas(self) -> None:
		instant = self.horloge.maintenant()
		self._verifier_les_expirations(instant)
		self.moteur.traiter_messages()
		self._terminer_les_voies_arretees(instant)
		courant = self.courant
		if courant is not None:
			decision = self.ordonnanceur.decider(instant, courant.en_cours)
			if decision.couper:
				self._couper(instant)
				self._appliquer(decision, instant)
			elif decision.eteindre:
				self._eteindre(courant, decision, instant)
			elif not courant.suivant_demande and self._au_crossfade_de_fin(courant):
				courant.suivant_demande = True
				self._preparer_le_suivant(courant, instant)
		elif not self.sortants:
			# Rien sur la sortie ; tant qu'un stream s'éteint sans superposition, le suivant attend.
			choix, self.en_attente = self.en_attente, None
			if choix is not None:
				self._jouer(choix, instant)
			else:
				self._appliquer(self.ordonnanceur.decider(instant, None), instant)
		self._suivre_la_sonde(instant)

	def arreter(self) -> None:
		"""Arrête la sortie : les passages en cours se terminent sans incident, puis l'arrêt est consigné."""
		instant = self.horloge.maintenant()
		self.moteur.traiter_messages()
		self._terminer_les_voies_arretees(instant)
		self.moteur.couper()
		for lecture in self._lectures():
			terminer_passage(self.connexion, lecture.passage, instant)
		self.courant, self.sortants, self.en_attente, self.sonde = None, [], None, None
		consigner(self.connexion, "info", "arrêt", "arrêt demandé", instant)

	# ─── Étapes ────────────────────────────────────────────

	def _lectures(self) -> list[Lecture]:
		return ([] if self.courant is None else [self.courant]) + self.sortants

	def _terminer_les_voies_arretees(self, instant: datetime) -> None:
		for lecture in self._lectures():
			if lecture.voie.etat not in ("finie", "en erreur"):
				continue
			if lecture.parametres.stream and not lecture.eteinte:
				# Un stream n'a pas de fin : arrêté avant son extinction, il est tombé.
				erreur = f"{lecture.parametres.adresse} : {lecture.voie.erreur or FLUX_ARRETE}"
				terminer_passage(self.connexion, lecture.passage, instant, erreur=erreur, nature=FLUX_TOMBE)
				self._suspendre(lecture, instant)
			else:
				terminer_passage(self.connexion, lecture.passage, instant, erreur=lecture.voie.erreur)
		self.sortants = [s for s in self.sortants if s.voie.etat == "en cours"]
		if self.courant is not None and self.courant.voie.etat != "en cours":
			self.courant = None

	@staticmethod
	def _au_crossfade_de_fin(lecture: Lecture) -> bool:
		duree = lecture.parametres.duree
		return duree is not None and lecture.voie.position() >= duree - lecture.parametres.crossfade_fin

	def _preparer_le_suivant(self, courant: Lecture, instant: datetime) -> None:
		choix = self.ordonnanceur.decider(instant, None).jouer
		if choix is None:
			# Rien ensuite : le sonore finit avec son fondu, et le prochain pas sans voie redemande.
			return
		parametres = lire_parametres(self.connexion, choix.sonore)
		if superposition(courant.parametres.crossfade_fin, parametres.crossfade_debut):
			self._jouer(choix, instant, courant.parametres.crossfade_fin)
		else:
			courant.voie.supprimer_fondu_de_sortie()
			self.en_attente = choix

	def _eteindre(self, courant: Lecture, decision: Decision, instant: datetime) -> None:
		"""Fin de l'événement d'un stream : il s'éteint pendant son crossfade de fin."""
		fondu = courant.parametres.crossfade_fin
		courant.eteinte = True
		courant.voie.eteindre(fondu)
		self.courant = None
		self.sortants.append(courant)
		self._terminer_les_voies_arretees(instant)
		choix = decision.jouer
		if choix is None:
			return
		if superposition(fondu, lire_parametres(self.connexion, choix.sonore).crossfade_debut):
			self._jouer(choix, instant, fondu)
		else:
			self.en_attente = choix

	def _suspendre(self, lecture: Lecture, instant: datetime) -> None:
		"""Stream tombé : l'ordonnanceur le remplace, et la sonde le reconnectera."""
		self.ordonnanceur.suspendre(lecture.choix.occurrence, lecture.parametres.secours)
		self.sonde = Sonde(lecture.choix, lecture.parametres, instant + self.delai_reconnexion, instant)

	def _suivre_la_sonde(self, instant: datetime) -> None:
		sonde = self.sonde
		if sonde is None:
			return
		suspension = self.ordonnanceur.suspension
		if suspension is None or suspension.occurrence.cle != sonde.choix.occurrence.cle:
			if sonde.voie is not None:
				sonde.voie.fermer()
			self.sonde = None
			consigner(
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
			if instant >= sonde.prochaine_tentative and sonde.parametres.adresse is not None:
				sonde.voie = self.moteur.jouer(sonde.parametres.adresse, None, muette=True)
			return
		sonde.voie.traiter()
		if sonde.voie.etat != "en cours":
			sonde.voie.fermer()
			sonde.voie = None
			sonde.prochaine_tentative = instant + self.delai_reconnexion
		elif sonde.voie.position() > timedelta(0):
			self._reprendre(sonde, sonde.voie, instant)

	def _reprendre(self, sonde: Sonde, voie: Voie, instant: datetime) -> None:
		"""Le flux est revenu : crossfade immédiat vers le stream, pendant son crossfade de début."""
		fondu = sonde.parametres.crossfade_debut
		voie.fondu(1.0, fondu)
		for lecture in self._lectures():
			if fondu > timedelta(0):
				lecture.eteinte = True
				lecture.voie.eteindre(fondu)
			else:
				lecture.voie.couper()
				terminer_passage(self.connexion, lecture.passage, instant)
		self.sortants = [lecture for lecture in self._lectures() if lecture.voie.etat == "en cours"]
		self.en_attente, self.sonde = None, None
		self.ordonnanceur.reprendre()
		choix = sonde.choix
		passage = commencer_passage(
			self.connexion, choix.sonore, choix.banque, choix.occurrence.evenement.id, choix.element.id, instant
		)
		self.courant = Lecture(choix, sonde.parametres, voie, passage)
		expirer(self.connexion, instant, choix.sonore)
		panne = round((instant - sonde.depuis).total_seconds())
		consigner(
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
			terminer_passage(self.connexion, lecture.passage, instant, coupe=True)
		self.courant, self.sortants, self.en_attente = None, [], None

	def _appliquer(self, decision: Decision, instant: datetime) -> None:
		if decision.jouer is not None:
			self._jouer(decision.jouer, instant)

	def _jouer(self, choix: Choix, instant: datetime, crossfade_fin_precedent: timedelta = timedelta(0)) -> None:
		"""Démarre le sonore ; un fichier introuvable est écarté, et l'ordonnanceur donne le suivant."""
		suivant: Choix | None = choix
		chemin: Path | str | None = None
		essayes: set[int] = set()
		# Chaque sonore n'est essayé qu'une fois : la boucle s'arrête même si l'ordonnanceur le redonne.
		while suivant is not None and suivant.sonore not in essayes:
			parametres = lire_parametres(self.connexion, suivant.sonore)
			chemin = parametres.adresse if parametres.stream else verifier_avant_lecture(self.connexion, suivant.sonore)
			if chemin is not None:
				break
			essayes.add(suivant.sonore)
			self.ordonnanceur.exclure(suivant.sonore, instant)
			suivant = self.ordonnanceur.decider(instant, None).jouer
		if suivant is None or chemin is None:
			return
		voie = self.moteur.jouer(
			chemin,
			parametres.duree,
			fondu_d_entree(crossfade_fin_precedent, parametres.crossfade_debut),
			parametres.crossfade_fin,
		)
		passage = commencer_passage(
			self.connexion,
			suivant.sonore,
			suivant.banque,
			suivant.occurrence.evenement.id,
			suivant.element.id,
			instant,
		)
		if self.courant is not None:
			self.sortants.append(self.courant)
		self.courant = Lecture(suivant, parametres, voie, passage)
		expirer(self.connexion, instant, suivant.sonore)

	def _verifier_les_expirations(self, instant: datetime) -> None:
		derniere = self.expirations_verifiees
		if derniere is None or instant - derniere >= VERIFICATION_DES_EXPIRATIONS:
			self.expirations_verifiees = instant
			expirer(self.connexion, instant)


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

	Sur une erreur (base de données perdue, par exemple), la sortie est coupée et l'erreur remonte.
	"""
	diffusion.demarrer()
	try:
		while not arret.is_set():
			diffusion.pas()
			arret.wait(pause)
	except BaseException:
		diffusion.moteur.couper()
		raise
	diffusion.arreter()
