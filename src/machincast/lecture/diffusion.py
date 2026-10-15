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
"""

import signal
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import FrameType

import psycopg
from psycopg.rows import TupleRow

from machincast import __version__
from machincast.hasard import Hasard
from machincast.horloge import Horloge
from machincast.lecture.deroule import Choix, Decision, EnCours, Ordonnanceur
from machincast.lecture.enregistrement import Passage, commencer_passage, consigner, terminer_passage
from machincast.lecture.fichiers import verifier_avant_lecture
from machincast.lecture.moteur import MoteurAudio, Voie, fondu_d_entree, superposition

PAUSE = 0.05
"""Pause entre deux pas de la boucle, en secondes : la précision de l'enchaînement et de la coupure."""


@dataclass(frozen=True)
class Parametres:
	"""Ce que le moteur audio doit savoir d'un sonore."""

	duree: timedelta | None
	crossfade_debut: timedelta
	crossfade_fin: timedelta


@dataclass
class Lecture:
	"""Un sonore sur la sortie : son choix, sa voie et son passage dans l'airplay."""

	choix: Choix
	parametres: Parametres
	voie: Voie
	passage: Passage
	suivant_demande: bool = False
	"""L'ordonnanceur a déjà donné le sonore suivant, au début du crossfade de fin."""

	@property
	def en_cours(self) -> EnCours:
		debut = self.passage.debut
		return EnCours(self.choix.occurrence, debut, debut + (self.parametres.duree or timedelta(0)))


def lire_parametres(connexion: psycopg.Connection[TupleRow], sonore: int) -> Parametres:
	with connexion.transaction():
		ligne = connexion.execute(
			"SELECT duree, crossfade_debut, crossfade_fin FROM sonores WHERE id = %s", (sonore,)
		).fetchone()
	if ligne is None:
		return Parametres(None, timedelta(0), timedelta(0))
	duree, debut, fin = ligne
	return Parametres(
		duree if isinstance(duree, timedelta) else None,
		debut if isinstance(debut, timedelta) else timedelta(0),
		fin if isinstance(fin, timedelta) else timedelta(0),
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
	ordonnanceur: Ordonnanceur = field(init=False)
	courant: Lecture | None = field(default=None, init=False)
	sortants: list[Lecture] = field(default_factory=list, init=False)
	"""Sonores qui finissent leur crossfade de fin sous le sonore courant."""
	en_attente: Choix | None = field(default=None, init=False)
	"""Sonore suivant, qui attend la fin du sonore courant faute de superposition."""

	def __post_init__(self) -> None:
		self.ordonnanceur = Ordonnanceur(self.connexion, self.hasard)

	def demarrer(self) -> None:
		consigner(self.connexion, "info", "démarrage", f"Machin_lecture {__version__}", self.horloge.maintenant())

	def pas(self) -> None:
		instant = self.horloge.maintenant()
		self.moteur.traiter_messages()
		self._terminer_les_voies_arretees(instant)
		courant = self.courant
		if courant is not None:
			decision = self.ordonnanceur.decider(instant, courant.en_cours)
			if decision.couper:
				self._couper(instant)
				self._appliquer(decision, instant)
			elif not courant.suivant_demande and self._au_crossfade_de_fin(courant):
				courant.suivant_demande = True
				self._preparer_le_suivant(courant, instant)
			return
		choix, self.en_attente = self.en_attente, None
		if choix is not None:
			self._jouer(choix, instant)
		else:
			self._appliquer(self.ordonnanceur.decider(instant, None), instant)

	def arreter(self) -> None:
		"""Arrête la sortie : les passages en cours se terminent sans incident, puis l'arrêt est consigné."""
		instant = self.horloge.maintenant()
		self.moteur.traiter_messages()
		self._terminer_les_voies_arretees(instant)
		self.moteur.couper()
		for lecture in self._lectures():
			terminer_passage(self.connexion, lecture.passage, instant)
		self.courant, self.sortants, self.en_attente = None, [], None
		consigner(self.connexion, "info", "arrêt", "arrêt demandé", instant)

	# ─── Étapes ────────────────────────────────────────────

	def _lectures(self) -> list[Lecture]:
		return ([] if self.courant is None else [self.courant]) + self.sortants

	def _terminer_les_voies_arretees(self, instant: datetime) -> None:
		for lecture in self._lectures():
			if lecture.voie.etat in ("finie", "en erreur"):
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
		chemin = None
		essayes: set[int] = set()
		# Chaque sonore n'est essayé qu'une fois : la boucle s'arrête même si l'ordonnanceur le redonne.
		while suivant is not None and suivant.sonore not in essayes:
			chemin = verifier_avant_lecture(self.connexion, suivant.sonore)
			if chemin is not None:
				break
			essayes.add(suivant.sonore)
			self.ordonnanceur.exclure(suivant.sonore, instant)
			suivant = self.ordonnanceur.decider(instant, None).jouer
		if suivant is None or chemin is None:
			return
		parametres = lire_parametres(self.connexion, suivant.sonore)
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
