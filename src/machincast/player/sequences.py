"""Séquences : suites de sonores et de banques réutilisables dans les événements
(https://github.com/dascritch/machincast/issues/99, spec § 3.1 et § 4.3).

Une séquence se place comme un élément de la liste d'un événement. Elle joue ses éléments dans l'ordre de leur
position ; chaque élément est un sonore ou une banque, jamais une autre séquence. Son déroulé est dans
machincast.player.rundown : ce module ne fait que la lire, avec le rôle de la lecture.
"""

from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import integer_or_none
from machincast.player import queries


@dataclass(frozen=True)
class SequenceItem:
	"""Un élément de la liste d'une séquence : un sonore ou une banque."""

	id: int
	sequence: int
	position: int
	sound: int | None
	bank: int | None


@dataclass(frozen=True)
class Sequence:
	id: int
	name: str
	items: list[SequenceItem]
	"""Dans l'ordre de leur position."""


def read_sequence(connection: psycopg.Connection[TupleRow], identifier: int) -> Sequence | None:
	"""La séquence et ses éléments, dans leur ordre ; None si elle n'est pas en base."""
	line = queries.sequence_name(connection, identifier)
	if line is None:
		return None
	lines = queries.sequence_items(connection, identifier)
	items = []
	for item, position, sound, bank in lines:
		items.append(
			SequenceItem(
				id=int(str(item)),
				sequence=identifier,
				position=int(str(position)),
				sound=integer_or_none(sound),
				bank=integer_or_none(bank),
			)
		)
	return Sequence(identifier, str(line[0]), items)


def sequence_of_item(connection: psycopg.Connection[TupleRow], item: int) -> int | None:
	"""La séquence de cet élément de séquence ; None s'il n'est plus en base."""
	line = queries.sequence_of_item(connection, item)
	if line is None:
		return None
	return int(str(line[0]))


def items_after(sequence: Sequence, last: int | None) -> list[SequenceItem]:
	"""Éléments qui restent à jouer après le dernier joué ; tous si dernier est None. Un dernier élément supprimé
	depuis termine la séquence : on ne sait plus où la reprendre."""
	if last is None:
		return sequence.items
	ids = []
	for item in sequence.items:
		ids.append(item.id)
	if last not in ids:
		return []
	return sequence.items[ids.index(last) + 1 :]
