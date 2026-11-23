"""L'alternance d'un événement « méta » (https://github.com/dascritch/machincast/issues/609) : les émissions qui se
partagent son créneau, laquelle joue selon la semaine du mois, et les choix faits à la main pour une date.

Elle est rangée dans la colonne properties de l'événement (https://github.com/dascritch/machincast/issues/607), sous
la clé du plugin :

	{"alternation": {"candidates": [12, 13, 14], "rotation": {"1": 12, "2": 13, "3": 14, "4": 13, "5": null},
	"choices": {"2026-12-16": 12}}}

- candidates : les événements qu'il fait jouer, hors grille (machincast.shared.grid.Substitution) ;
- rotation : pour la n-ième occurrence de son jour dans le mois, de 1 à 5, celui qui joue ; null, l'événement joue
  lui-même ;
- choices : pour une date, celui qui joue, à la place de la rotation.

Un identifiant qui n'est pas parmi les candidats est ignoré.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

from machincast.shared.grid import Event, Substitution

KEY = "alternation"
"""La clé du plugin dans properties."""
WEEKS = (1, 2, 3, 4, 5)
"""Les rangs d'un jour dans le mois : un mois en a quatre ou cinq."""


@dataclass(frozen=True)
class Alternation:
	candidates: tuple[int, ...] = ()
	rotation: Mapping[int, int | None] = field(default_factory=dict)
	choices: Mapping[date, int] = field(default_factory=dict)

	def playing(self, day: date) -> int | None:
		"""L'événement qui joue l'occurrence qui commence ce jour : le choix fait pour la date, sinon la rotation."""
		chosen = self.choices.get(day)
		if chosen not in self.candidates:
			chosen = self.rotation.get(week(day))
		if chosen not in self.candidates:
			return None
		return chosen

	def stored(self) -> dict[str, object]:
		"""Ce qui se range sous la clé du plugin."""
		rotation: dict[str, int | None] = {}
		for rank in WEEKS:
			rotation[str(rank)] = self.rotation.get(rank)
		choices: dict[str, int] = {}
		for day, chosen in sorted(self.choices.items()):
			choices[day.isoformat()] = chosen
		return {"candidates": sorted(self.candidates), "rotation": rotation, "choices": choices}


def week(day: date) -> int:
	"""Le rang de ce jour parmi les mêmes jours de son mois : 1 du 1er au 7, 2 du 8 au 14, et ainsi de suite."""
	return ((day.day - 1) // 7) + 1


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
	return Alternation(tuple(candidates), rotation, choices)


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
	return found.playing(day)


def substitution() -> Substitution:
	"""Ce que le plugin répond au point « grid.substitutions » : ses candidats hors grille, et celui qui joue chaque
	occurrence."""
	return Substitution(_hidden, _playing)
