"""L'alternance d'un événement « méta » (https://github.com/dascritch/machincast/issues/609) : les émissions qui se
partagent son créneau, laquelle joue selon la semaine du mois, ou une semaine sur deux, et les choix faits à la main
pour une date.

Elle est rangée dans la colonne properties de l'événement (https://github.com/dascritch/machincast/issues/607), sous
la clé du plugin :

	{"alternation": {"mode": "monthly", "candidates": [12, 13, 14],
	"rotation": {"1": 12, "2": 13, "3": 14, "4": 13, "5": null}, "choices": {"2026-12-16": 12}}}

- mode : « monthly », par mois, la rotation va de 1 à 5, la n-ième occurrence du jour dans le mois (week) ;
  « fortnightly », par quinzaine, de 1 à 2, une semaine sur deux, comptée depuis la semaine de la première
  occurrence de l'événement (fortnight) ; monthly sans lui ;
- candidates : les événements qu'il fait jouer, hors grille (machincast.shared.grid.Substitution) ;
- rotation : pour chaque rang, celui qui joue ; null, l'événement joue lui-même ;
- choices : pour une date, celui qui joue, à la place de la rotation.

Un identifiant qui n'est pas parmi les candidats est ignoré.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

from machincast.shared.grid import Event, Substitution, wall_hour

KEY = "alternation"
"""La clé du plugin dans properties."""
MONTHLY = "monthly"
FORTNIGHTLY = "fortnightly"
MODES = (MONTHLY, FORTNIGHTLY)
WEEKS = (1, 2, 3, 4, 5)
"""Les rangs d'un jour dans le mois : un mois en a quatre ou cinq."""
RANKS = {MONTHLY: WEEKS, FORTNIGHTLY: (1, 2)}
"""Les rangs de la rotation, selon le rythme."""


@dataclass(frozen=True)
class Alternation:
	candidates: tuple[int, ...] = ()
	rotation: Mapping[int, int | None] = field(default_factory=dict)
	choices: Mapping[date, int] = field(default_factory=dict)
	mode: str = MONTHLY

	def rank(self, day: date, first: date | None) -> int:
		"""Le rang de ce jour dans la rotation : sa semaine du mois, ou de la quinzaine qui part de first, la première
		occurrence de l'événement ; sans elle, par mois."""
		if (self.mode == FORTNIGHTLY) and (first is not None):
			return fortnight(day, first)
		return week(day)

	def playing(self, day: date, first: date | None = None) -> int | None:
		"""L'événement qui joue l'occurrence qui commence ce jour : le choix fait pour la date, sinon la rotation."""
		chosen = self.choices.get(day)
		if chosen not in self.candidates:
			chosen = self.rotation.get(self.rank(day, first))
		if chosen not in self.candidates:
			return None
		return chosen

	def stored(self) -> dict[str, object]:
		"""Ce qui se range sous la clé du plugin : la rotation, seulement pour les rangs de son rythme."""
		rotation: dict[str, int | None] = {}
		for rank in RANKS[self.mode]:
			rotation[str(rank)] = self.rotation.get(rank)
		choices: dict[str, int] = {}
		for day, chosen in sorted(self.choices.items()):
			choices[day.isoformat()] = chosen
		return {"mode": self.mode, "candidates": sorted(self.candidates), "rotation": rotation, "choices": choices}


def week(day: date) -> int:
	"""Le rang de ce jour parmi les mêmes jours de son mois : 1 du 1er au 7, 2 du 8 au 14, et ainsi de suite."""
	return ((day.day - 1) // 7) + 1


def fortnight(day: date, first: date) -> int:
	"""Le rang de ce jour dans sa quinzaine : 1 la semaine de first, 2 la suivante, puis 1 de nouveau, d'un mois à
	l'autre ; les semaines vont de first à six jours après."""
	return (((day - first).days // 7) % 2) + 1


def first_day(event: Event) -> date | None:
	"""Le jour de la première occurrence de l'événement, en heure murale ; None sans début."""
	if event.start is None:
		return None
	return wall_hour(event.start).date()


def _identifier(value: object) -> int | None:
	if (isinstance(value, int)) and (not isinstance(value, bool)):
		return value
	return None


def read(properties: Mapping[str, object]) -> Alternation | None:
	"""L'alternance rangée dans ces propriétés ; None sans elle. Ce qui ne se lit pas est laissé."""
	found = properties.get(KEY)
	if not isinstance(found, Mapping):
		return None
	candidates = []
	given = found.get("candidates")
	if isinstance(given, list):
		for value in given:
			identifier = _identifier(value)
			if (identifier is not None) and (identifier not in candidates):
				candidates.append(identifier)
	rotation: dict[int, int | None] = {}
	given_rotation = found.get("rotation")
	if isinstance(given_rotation, Mapping):
		for rank in WEEKS:
			rotation[rank] = _identifier(given_rotation.get(str(rank)))
	choices: dict[date, int] = {}
	given_choices = found.get("choices")
	if isinstance(given_choices, Mapping):
		for text, value in given_choices.items():
			identifier = _identifier(value)
			day = _day(str(text))
			if (identifier is not None) and (day is not None):
				choices[day] = identifier
	mode = MONTHLY
	if found.get("mode") == FORTNIGHTLY:
		mode = FORTNIGHTLY
	return Alternation(tuple(candidates), rotation, choices, mode)


def _day(text: str) -> date | None:
	try:
		return date.fromisoformat(text)
	except ValueError:
		return None


def _hidden(event: Event) -> frozenset[int]:
	found = read(event.properties)
	if found is None:
		return frozenset()
	return frozenset(found.candidates)


def _playing(event: Event, day: date) -> int | None:
	found = read(event.properties)
	if found is None:
		return None
	return found.playing(day, first_day(event))


def substitution() -> Substitution:
	"""Ce que le plugin répond au point « grid.substitutions » : ses candidats hors grille, et celui qui joue chaque
	occurrence."""
	return Substitution(_hidden, _playing)
