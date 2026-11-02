"""Interruption manuelle de l'antenne depuis l'interface (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228, spec § 8.11), et clic droit sur le prochain sonore de l'onglet
Antenne (https://github.com/dascritch/machincast/issues/257) : y sauter, ou avancer l'événement suivant
(proposer_au_prochain).

Le menu « Diffusion » propose de sauter au sonore suivant, de sauter après la séquence en cours, ou de couper
l'événement par le fil musical (ENTREES). Chaque entrée suit l'état que Machin lecture publie sur sa socket d'état
(proposer) : elle n'est active que si son élément est à l'antenne, et, pour l'événement, hors du fil musical ; son
infobulle le nomme, ou dit pourquoi elle est inactive. Choisie, elle envoie la demande sur la
socket (ClientEtat.envoyer), aussitôt, sans question : Machin lecture la traite à son pas suivant
(machincast.lecture.diffusion.Diffusion.interrompre). La barre d'état l'annonce (ANNONCES).

Coupures (https://github.com/dascritch/machincast/issues/323) : « ⏭ Couper par le secours », dans le menu « Diffusion »
et au clic droit sur le prochain sonore, inactive sans événement de secours ou sans rien à l'antenne ; avec plusieurs
secours, un sous-menu les nomme (garnir_le_secours). Au clic droit sur un feed, « ⏭ Couper l'événement par ce feed »,
ou, dans le fil musical, « ⏭ Couper le fil musical par ce feed », inactive sans stream actif qui suive le feed
(proposer_le_feed). Le secours, ou le stream du feed, tient l'antenne jusqu'à la fin prévue de l'événement coupé, ou,
sous le fil musical, jusqu'à l'événement suivant (machincast.lecture.deroule.Ordonnanceur.couper_par).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from machincast.interface import affichage
from machincast.interface.calendrier import jour_et_mois
from machincast.interface.etat import EtatLecture, EvenementSuivant
from machincast.interface.intentions import SAUTER, libelle

journal = logging.getLogger(__name__)

ENTREES = {
	"sonore": libelle(SAUTER, "Sauter au sonore suivant"),
	"sequence": libelle(SAUTER, "Sauter après la séquence"),
	"evenement": libelle(SAUTER, "Couper l'événement par le fil musical"),
}
"""Entrée du menu « Diffusion » de chaque élément qui s'interrompt, dans l'ordre du menu."""
ANNONCES = {
	"sonore": "Saut au sonore suivant demandé.",
	"sequence": "Saut après la séquence demandé.",
	"evenement": "Coupure de l'événement par le fil musical demandée.",
}
RIEN_A_L_ANTENNE = "Rien à l'antenne"
AUCUNE_SEQUENCE = "Aucune séquence à l'antenne"
DEJA_LE_FIL_MUSICAL = "Le fil musical est déjà à l'antenne"
SANS_LECTURE = "Interruption impossible : Machin lecture ne répond pas sur sa socket d'état."
SAUTER_A_CE_SONORE = libelle(SAUTER, "Sauter à ce sonore")
AVANCER_L_EVENEMENT_SUIVANT = libelle(SAUTER, "Avancer l'événement suivant")
AUCUN_PROCHAIN_SONORE = "Aucun prochain sonore"
AUCUN_EVENEMENT_SUIVANT = "Aucun événement suivant dans les sept jours"
SANS_DIFFUSION = "Machin lecture ne diffuse pas"
AVANCE_SANS_LECTURE = "Avance impossible : Machin lecture ne répond pas sur sa socket d'état."


@dataclass(frozen=True)
class Proposition:
	active: bool
	infobulle: str
	"""Ce que l'entrée interrompt, ou pourquoi elle est inactive."""


def _nomme(nom: str | None) -> Proposition:
	return Proposition(True, f"« {nom} »")


def proposer(etat: EtatLecture) -> dict[str, Proposition]:
	"""Pour chaque élément, l'entrée de son interruption, selon l'état de Machin lecture."""
	en_cours = etat.en_cours
	# Machin lecture ne publie un sonore en cours qu'en diffusion : ni pendant un blanc, ni à l'arrêt.
	if en_cours is None:
		return {element: Proposition(False, RIEN_A_L_ANTENNE) for element in ENTREES}
	sequence = Proposition(False, AUCUNE_SEQUENCE)
	if en_cours.sequence is not None:
		sequence = _nomme(en_cours.sequence)
	evenement = Proposition(False, RIEN_A_L_ANTENNE)
	if en_cours.evenement is not None:
		evenement = _nomme(en_cours.evenement)
	if en_cours.evenement_priorite == "fil_musical":
		evenement = Proposition(False, DEJA_LE_FIL_MUSICAL)
	return {
		"sonore": _nomme((en_cours.titre) or (en_cours.emplacement)),
		"sequence": sequence,
		"evenement": evenement,
	}


@dataclass(frozen=True)
class EntreeDuProchain:
	"""Une entrée du clic droit sur le prochain sonore (https://github.com/dascritch/machincast/issues/257)."""

	texte: str
	proposition: Proposition


def avance(suivant: EvenementSuivant) -> str:
	"""« ⏭ Avancer « Journal », prévu le mercredi 21 octobre à 12:00 »."""
	return f"{SAUTER} Avancer « {suivant.nom} », prévu le {jour_et_mois(suivant.debut.date())} à {suivant.debut:%H:%M}"


def annonce_d_avance(nom: str) -> str:
	return f"Avance de l'événement « {nom} » demandée."


def _jusqu_a(suivant: EvenementSuivant) -> str:
	if suivant.fin is None:
		return "Il commence aussitôt, au-dessus de la grille, jusqu'à la fin de sa liste"
	fin = f"{suivant.fin:%H:%M}"
	if suivant.fin.date() != suivant.debut.date():
		fin = f"{jour_et_mois(suivant.fin.date())}, {fin}"
	return f"Il commence aussitôt, au-dessus de la grille, jusqu'à sa fin, à {fin}"


def proposer_au_prochain(etat: EtatLecture) -> dict[str, EntreeDuProchain]:
	"""Sauter au prochain sonore (« sonore »), et avancer l'événement suivant (« avancer »), selon l'état de Machin
	lecture : il faut un sonore à l'antenne et un prochain sonore pour y sauter ; un événement suivant annoncé pour
	l'avancer. À l'arrêt, rien ne se demande."""
	if etat.etat == "arret":
		return {
			"sonore": EntreeDuProchain(SAUTER_A_CE_SONORE, Proposition(False, SANS_DIFFUSION)),
			"avancer": EntreeDuProchain(AVANCER_L_EVENEMENT_SUIVANT, Proposition(False, SANS_DIFFUSION)),
		}
	sonore = EntreeDuProchain(SAUTER_A_CE_SONORE, Proposition(False, AUCUN_PROCHAIN_SONORE))
	if (etat.en_cours is not None) and (etat.prochain is not None):
		prochain = (etat.prochain.titre) or (etat.prochain.emplacement)
		en_cours = (etat.en_cours.titre) or (etat.en_cours.emplacement)
		infobulle = f"« {prochain} », aussitôt : « {en_cours} » s'arrête"
		sonore = EntreeDuProchain(SAUTER_A_CE_SONORE, Proposition(True, infobulle))
	avancer = EntreeDuProchain(AVANCER_L_EVENEMENT_SUIVANT, Proposition(False, AUCUN_EVENEMENT_SUIVANT))
	suivant = etat.evenement_suivant
	if suivant is not None:
		avancer = EntreeDuProchain(avance(suivant), Proposition(True, _jusqu_a(suivant)))
	return {"sonore": sonore, "avancer": avancer}


# ─── Coupures par le secours et par un feed (https://github.com/dascritch/machincast/issues/323) ───

COUPER_PAR_LE_SECOURS = libelle(SAUTER, "Couper par le secours")
"""L'entrée du menu « Diffusion » et du clic droit sur le prochain sonore ; avec plusieurs secours, son sous-menu."""
AUCUN_SECOURS = "Aucun événement de secours"
JUSQU_A_LA_FIN = (
	"Le secours joue jusqu'à la fin prévue de l'événement coupé ; sous le fil musical, jusqu'à l'événement suivant"
)
COUPER_L_EVENEMENT_PAR_CE_FEED = libelle(SAUTER, "Couper l'événement par ce feed")
COUPER_LE_FIL_MUSICAL_PAR_CE_FEED = libelle(SAUTER, "Couper le fil musical par ce feed")
AUCUN_STREAM = "Aucun stream actif ne suit ce feed"
FEED_JUSQU_A_LA_FIN = (
	"Le stream du feed passe jusqu'à la fin prévue de l'événement coupé ; sous le fil musical, jusqu'à l'événement"
	" suivant. S'il tombe, le fil musical prend le relais"
)
COUPURE_SANS_LECTURE = "Coupure impossible : Machin lecture ne répond pas sur sa socket d'état."


@dataclass(frozen=True)
class Secours:
	"""Un événement de secours, que l'interface propose pour couper l'antenne."""

	identifiant: int
	nom: str


def lire_les_secours(connexion: psycopg.Connection[TupleRow]) -> list[Secours]:
	"""Les événements de secours en base, non supprimés, par nom ; aucun si la base est injoignable."""
	try:
		with connexion.transaction():
			lignes = connexion.execute(
				"SELECT id, nom_interne FROM evenements WHERE priorite = 'secours' AND supprime_le IS NULL"
				" ORDER BY nom_interne, id"
			).fetchall()
	except psycopg.Error as erreur:
		journal.error(f"événements de secours illisibles : {erreur}")
		return []
	return [Secours(int(str(identifiant)), str(nom)) for identifiant, nom in lignes]


def proposer_le_secours(etat: EtatLecture, secours: list[Secours]) -> Proposition:
	"""Couper par le secours : il faut un événement de secours, et un sonore à l'antenne."""
	if secours == []:
		return Proposition(False, AUCUN_SECOURS)
	if etat.en_cours is None:
		return Proposition(False, RIEN_A_L_ANTENNE)
	if len(secours) == 1:
		return Proposition(True, f"« {secours[0].nom} », {JUSQU_A_LA_FIN.removeprefix('Le secours ')}")
	return Proposition(True, JUSQU_A_LA_FIN)


def garnir_le_secours(
	action: QAction, etat: EtatLecture, secours: list[Secours], demander: Callable[[Secours], None]
) -> None:
	"""L'entrée « ⏭ Couper par le secours » : avec un seul secours, elle porte ce secours (data), et coupe par lui une
	fois reliée à demander_le_secours ; avec plusieurs, son sous-menu les nomme, chacun coupant par lui."""
	proposition = proposer_le_secours(etat, secours)
	action.setText(COUPER_PAR_LE_SECOURS)
	action.setEnabled(proposition.active)
	action.setToolTip(proposition.infobulle)
	ancien = action.menu()
	# Sans sous-menu : PySide6 ne déclare pas None, que Qt accepte pour retirer le menu de l'action.
	action.setMenu(None)  # type: ignore[arg-type]
	if isinstance(ancien, QMenu):
		ancien.deleteLater()
	action.setData(None)
	if len(secours) == 1:
		action.setData(secours[0])
	elif len(secours) > 1:
		sous_menu = QMenu(COUPER_PAR_LE_SECOURS)
		sous_menu.setToolTipsVisible(True)
		for un in secours:
			entree = sous_menu.addAction(f"« {un.nom} »")
			entree.setToolTip(JUSQU_A_LA_FIN)
			entree.triggered.connect(lambda _coche=False, un=un: demander(un))
		action.setMenu(sous_menu)


def demander_le_secours(action: QAction, demander: Callable[[Secours], None]) -> None:
	"""L'entrée choisie coupe par le secours qu'elle porte ; avec un sous-menu, ce sont ses entrées qui coupent."""
	secours = action.data()
	if isinstance(secours, Secours):
		demander(secours)


def annonce_du_secours(nom: str) -> str:
	return f"Coupure par le secours « {nom} » demandée."


def proposer_le_feed(etat: EtatLecture, stream_actif: bool) -> EntreeDuProchain:
	"""Couper par un feed, au clic droit sur sa ligne : l'événement à l'antenne, ou le fil musical. Il faut un sonore à
	l'antenne, et un stream actif qui suive le feed."""
	en_cours = etat.en_cours
	texte = COUPER_L_EVENEMENT_PAR_CE_FEED
	if (en_cours is not None) and (en_cours.evenement_priorite == "fil_musical"):
		texte = COUPER_LE_FIL_MUSICAL_PAR_CE_FEED
	if en_cours is None:
		return EntreeDuProchain(texte, Proposition(False, RIEN_A_L_ANTENNE))
	if not stream_actif:
		return EntreeDuProchain(texte, Proposition(False, AUCUN_STREAM))
	return EntreeDuProchain(texte, Proposition(True, FEED_JUSQU_A_LA_FIN))


def annonce_du_feed(nom: str) -> str:
	return f"Coupure par le feed « {nom} » demandée."


def stream_du_feed(connexion: psycopg.Connection[TupleRow], feed: int) -> tuple[int | None, bool]:
	"""Le stream qui suit le feed, un actif d'abord, le plus ancien ; et s'il est actif. Aucun si la base est
	injoignable."""
	try:
		with connexion.transaction():
			ligne = connexion.execute(
				"SELECT id, etat = 'actif' FROM sonores WHERE feed_id = %s AND type = 'stream' AND supprime_le IS NULL"
				" ORDER BY etat = 'actif' DESC, id LIMIT 1",
				(feed,),
			).fetchone()
	except psycopg.Error as erreur:
		journal.error(f"stream du feed {feed} illisible : {erreur}")
		return None, False
	if ligne is None:
		return None, False
	return int(str(ligne[0])), ligne[1] is True


def garnir_le_feed(
	menu: QMenu,
	etat: EtatLecture,
	connexion: psycopg.Connection[TupleRow],
	feed: int,
	nom: str,
	preecouter: Callable[[int], None],
	couper: Callable[[int, str], None],
) -> None:
	"""Le clic droit sur un feed : « Pré-écoute… » de son stream, puis la coupure de l'antenne par lui."""
	stream, actif = stream_du_feed(connexion, feed)
	if stream is not None:
		affichage.proposer_la_preecoute(menu, stream, preecouter)
	entree = proposer_le_feed(etat, actif)
	action = menu.addAction(entree.texte)
	action.setEnabled(entree.proposition.active)
	action.setToolTip(entree.proposition.infobulle)
	action.triggered.connect(lambda _coche=False: couper(feed, nom))
	menu.setToolTipsVisible(True)
