"""Position des fondus par rapport aux silences détectés (https://github.com/dascritch/machincast/issues/234,
spec § 5.1).

Un sonore joué sans ses silences détectés (https://github.com/dascritch/machincast/issues/146) ne commence plus
forcément à son début détecté, ni ne s'arrête à sa fin détectée : ses fondus se placent par rapport à eux.

- Le fade-in « commence », « est en cours » ou « se termine » au début détecté : il part du début détecté, de la
  moitié de sa durée avant lui, ou de toute sa durée avant lui. Par défaut, il se termine au début détecté : le son
  arrive à plein volume.
- Le fade-out « commence », « est en cours » ou « se termine » à la fin détectée : il part de la fin détectée, de la
  moitié de sa durée avant elle, ou de toute sa durée avant elle. Par défaut, il commence à la fin détectée : le son va
  à plein volume jusqu'à sa fin, et s'éteint sur le silence qui suit.

La lecture va du début du fade-in à la fin du fade-out : elle s'étend dans les silences d'autant que les fondus y
débordent. Un fondu qui sortirait du fichier n'est pas joué hors du fichier : la lecture commence, ou s'arrête, au
bord du fichier, au volume qu'aurait le fondu à cet instant, comme s'il avait déjà commencé. Le fondu qui reste dans
le fichier garde sa pente. Un sonore joué avec ses silences l'est en entier, ses fondus aux bouts du fichier ; des
silences qui ne laissent rien du sonore sont ignorés, comme pour le rognage.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from machincast.i18n import _

Position = Literal["starts", "ongoing", "ends"]
POSITIONS: tuple[Position, ...] = ("starts", "ongoing", "ends")
"""Les positions d'un fondu, telles qu'elles s'écrivent dans la configuration (crossfades.fade_in_position et
position_sortie)."""
LABELS: dict[Position, str] = {"starts": "commence", "ongoing": _("is ongoing"), "ends": _("ends")}
"""Ce que dit chaque position, dans « le fade-in se termine au début détecté »."""
DEFAULT_ENTRY: Position = "ends"
DEFAULT_OUTPUT: Position = "starts"
ADVANCE: dict[Position, float] = {"starts": 0.0, "ongoing": 0.5, "ends": 1.0}
"""La part du fondu qui précède le silence détecté : rien s'il y commence, la moitié s'il y est en cours, tout s'il s'y
termine."""


@dataclass(frozen=True)
class Placement:
	"""La partie du fichier que la diffusion joue, et ses fondus. Les fondus sont ceux qui restent dans le fichier."""

	duration: timedelta
	"""La durée jouée."""
	offset: timedelta | None
	"""Où la lecture commence dans le fichier ; None : le fichier est joué en entier."""
	entry_fade: timedelta
	departure: float
	"""Volume au début de la lecture : 0, sauf si le fade-in déborde avant le début du fichier."""
	output_fade: timedelta
	arrival: float
	"""Volume à la fin de la lecture : 0, sauf si le fade-out déborde après la fin du fichier."""

	@property
	def start(self) -> timedelta:
		"""Où la lecture commence dans le fichier."""
		return (self.offset) or (timedelta(0))


def put(
	duration: timedelta,
	detected_start: timedelta | None,
	detected_end: timedelta | None,
	without_silences: bool,
	start_crossfade: timedelta,
	end_crossfade: timedelta,
	entry: Position = DEFAULT_ENTRY,
	output: Position = DEFAULT_OUTPUT,
) -> Placement:
	"""La lecture d'un fichier de cette durée, et ses fondus. without_silences : le sonore est joué sans ses silences
	détectés ; un côté sans silence détecté (None) a son silence nul. La fin détectée se compte depuis la fin du
	fichier."""
	integer = Placement(duration, None, start_crossfade, 0.0, end_crossfade, 0.0)
	start = (detected_start) or (timedelta(0))
	end = duration - ((detected_end) or (timedelta(0)))
	if (not without_silences) or (end <= start):
		return integer
	fade_departure = start - start_crossfade * ADVANCE[entry]
	playback = max(timedelta(0), fade_departure)
	fade_end = end - end_crossfade * ADVANCE[output] + end_crossfade
	stop = min(duration, fade_end)
	if (playback == timedelta(0)) and (stop == duration):
		offset = None
	else:
		offset = playback
	return Placement(
		duration=stop - playback,
		offset=offset,
		entry_fade=max(timedelta(0), fade_departure + start_crossfade - playback),
		departure=_share(playback - fade_departure, start_crossfade),
		output_fade=max(timedelta(0), stop - (fade_end - end_crossfade)),
		arrival=_share(fade_end - stop, end_crossfade),
	)


def _share(passes: timedelta, fade: timedelta) -> float:
	"""La part d'un fondu déjà passée hors du fichier, de 0 à 1 : le volume où il en est, à l'entrée comme à la
	sortie, puisque l'un monte et l'autre descend sur la même pente."""
	if fade <= timedelta(0):
		return 0.0
	return min(1.0, max(0.0, passes / fade))
