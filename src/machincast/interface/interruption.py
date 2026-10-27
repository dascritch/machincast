"""Interruption manuelle de l'antenne depuis l'interface (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228, spec § 8.11), et clic droit sur le prochain sonore de l'accueil
(https://github.com/dascritch/machincast/issues/257) : y sauter, ou avancer l'événement suivant (proposer_au_prochain).

Le menu « Diffusion » propose de sauter au sonore suivant, de sauter après la séquence en cours, ou de couper
l'événement par le fil musical (ENTREES). Chaque entrée suit l'état que Machin lecture publie sur sa socket d'état
(proposer) : elle n'est active que si son élément est à l'antenne, et, pour l'événement, hors du fil musical ; son
infobulle le nomme, ou dit pourquoi elle est inactive. Choisie, elle envoie la demande sur la
socket (ClientEtat.envoyer), aussitôt, sans question : Machin lecture la traite à son pas suivant
(machincast.lecture.diffusion.Diffusion.interrompre). La barre d'état l'annonce (ANNONCES).
"""

from dataclasses import dataclass

from machincast.interface.calendrier import jour_et_mois
from machincast.interface.etat import EtatLecture, EvenementSuivant

ENTREES = {
	"sonore": "Sauter au sonore suivant",
	"sequence": "Sauter après la séquence",
	"evenement": "Couper l'événement par le fil musical",
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
SAUTER_A_CE_SONORE = "Sauter à ce sonore"
AVANCER_L_EVENEMENT_SUIVANT = "Avancer l'événement suivant"
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
	# Machin lecture ne publie un sonore en cours qu'en diffusion : ni en silence, ni à l'arrêt.
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
	"""« Avancer « Journal », prévu le mercredi 21 octobre à 12:00 »."""
	return f"Avancer « {suivant.nom} », prévu le {jour_et_mois(suivant.debut.date())} à {suivant.debut:%H:%M}"


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
