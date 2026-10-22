"""Interruption manuelle de l'antenne depuis l'interface (https://github.com/dascritch/machincast/issues/104,
https://github.com/dascritch/machincast/issues/228, spec § 8.11).

Le menu « Diffusion » propose de sauter au sonore suivant, de sauter après la séquence en cours, ou de couper
l'événement par le fil musical (ENTREES). Chaque entrée suit l'état que Machin lecture publie sur sa socket d'état
(proposer) : elle n'est active que si son élément est à l'antenne, et, pour l'événement, hors du fil musical ; son
infobulle le nomme, ou dit pourquoi elle est inactive. Choisie, elle envoie la demande sur la
socket (ClientEtat.envoyer), aussitôt, sans question : Machin lecture la traite à son pas suivant
(machincast.lecture.diffusion.Diffusion.interrompre). La barre d'état l'annonce (ANNONCES).
"""

from dataclasses import dataclass

from machincast.interface.etat import EtatLecture

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
