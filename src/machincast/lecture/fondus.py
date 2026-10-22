"""Position des fondus par rapport aux blancs détectés (https://github.com/dascritch/machincast/issues/234, spec § 5.1).

Un sonore joué sans ses blancs détectés (https://github.com/dascritch/machincast/issues/146) ne commence plus
forcément à son début détecté, ni ne s'arrête à sa fin détectée : ses fondus se placent par rapport à eux.

- Le fade-in « commence », « est en cours » ou « se termine » au début détecté : il part du début détecté, de la
  moitié de sa durée avant lui, ou de toute sa durée avant lui. Par défaut, il se termine au début détecté : le son
  arrive à plein volume.
- Le fade-out « commence », « est en cours » ou « se termine » à la fin détectée : il part de la fin détectée, de la
  moitié de sa durée avant elle, ou de toute sa durée avant elle. Par défaut, il commence à la fin détectée : le son va
  à plein volume jusqu'à sa fin, et s'éteint sur le blanc qui suit.

La lecture va du début du fade-in à la fin du fade-out : elle s'étend dans les blancs d'autant que les fondus y
débordent. Un fondu qui sortirait du fichier n'est pas joué hors du fichier : la lecture commence, ou s'arrête, au
bord du fichier, au volume qu'aurait le fondu à cet instant, comme s'il avait déjà commencé. Le fondu qui reste dans
le fichier garde sa pente. Un sonore joué avec ses blancs l'est en entier, ses fondus aux bouts du fichier ; des
blancs qui ne laissent rien du sonore sont ignorés, comme pour le rognage.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

Position = Literal["commence", "en_cours", "termine"]
POSITIONS: tuple[Position, ...] = ("commence", "en_cours", "termine")
"""Les positions d'un fondu, telles qu'elles s'écrivent dans la configuration et en base (position_fondu)."""
LIBELLES: dict[Position, str] = {"commence": "commence", "en_cours": "est en cours", "termine": "se termine"}
"""Ce que dit chaque position, dans « le fade-in se termine au début détecté »."""
ENTREE_PAR_DEFAUT: Position = "termine"
SORTIE_PAR_DEFAUT: Position = "commence"
AVANCE: dict[Position, float] = {"commence": 0.0, "en_cours": 0.5, "termine": 1.0}
"""La part du fondu qui précède le blanc détecté : rien s'il y commence, la moitié s'il y est en cours, tout s'il s'y
termine."""


@dataclass(frozen=True)
class Placement:
	"""La partie du fichier que la diffusion joue, et ses fondus. Les fondus sont ceux qui restent dans le fichier."""

	duree: timedelta
	"""La durée jouée."""
	decalage: timedelta | None
	"""Où la lecture commence dans le fichier ; None : le fichier est joué en entier."""
	fondu_entree: timedelta
	depart: float
	"""Volume au début de la lecture : 0, sauf si le fade-in déborde avant le début du fichier."""
	fondu_sortie: timedelta
	arrivee: float
	"""Volume à la fin de la lecture : 0, sauf si le fade-out déborde après la fin du fichier."""

	@property
	def debut(self) -> timedelta:
		"""Où la lecture commence dans le fichier."""
		return (self.decalage) or (timedelta(0))


def placer(
	duree: timedelta,
	debut_detecte: timedelta | None,
	fin_detectee: timedelta | None,
	sans_blancs: bool,
	crossfade_debut: timedelta,
	crossfade_fin: timedelta,
	entree: Position = ENTREE_PAR_DEFAUT,
	sortie: Position = SORTIE_PAR_DEFAUT,
) -> Placement:
	"""La lecture d'un fichier de cette durée, et ses fondus. sans_blancs : le sonore est joué sans ses blancs
	détectés ; un côté sans blanc détecté (None) a son blanc nul. La fin détectée se compte depuis la fin du fichier."""
	entier = Placement(duree, None, crossfade_debut, 0.0, crossfade_fin, 0.0)
	debut = (debut_detecte) or (timedelta(0))
	fin = duree - ((fin_detectee) or (timedelta(0)))
	if (not sans_blancs) or (fin <= debut):
		return entier
	depart_du_fondu = debut - crossfade_debut * AVANCE[entree]
	lecture = max(timedelta(0), depart_du_fondu)
	fin_du_fondu = fin - crossfade_fin * AVANCE[sortie] + crossfade_fin
	arret = min(duree, fin_du_fondu)
	if (lecture == timedelta(0)) and (arret == duree):
		decalage = None
	else:
		decalage = lecture
	return Placement(
		duree=arret - lecture,
		decalage=decalage,
		fondu_entree=max(timedelta(0), depart_du_fondu + crossfade_debut - lecture),
		depart=_part(lecture - depart_du_fondu, crossfade_debut),
		fondu_sortie=max(timedelta(0), arret - (fin_du_fondu - crossfade_fin)),
		arrivee=_part(fin_du_fondu - arret, crossfade_fin),
	)


def _part(passe: timedelta, fondu: timedelta) -> float:
	"""La part d'un fondu déjà passée hors du fichier, de 0 à 1 : le volume où il en est, à l'entrée comme à la
	sortie, puisque l'un monte et l'autre descend sur la même pente."""
	if fondu <= timedelta(0):
		return 0.0
	return min(1.0, max(0.0, passe / fondu))


def position_ou(valeur: object, defaut: Position) -> Position:
	"""La position lue en base (position_fondu), ou celle des préférences sans position (NULL)."""
	if valeur in POSITIONS:
		return valeur
	return defaut
