"""Séquences : suites de sonores et de banques réutilisables dans les événements
(https://github.com/dascritch/machincast/issues/99, spec § 3.1 et § 4.3).

Une séquence se place comme un élément de la liste d'un événement. Elle joue ses éléments dans l'ordre de leur
position ; chaque élément est un sonore ou une banque, jamais une autre séquence. Son déroulé est dans
machincast.lecture.deroule : ce module ne fait que la lire, avec le rôle de la lecture.
"""

from dataclasses import dataclass

import psycopg
from psycopg.rows import TupleRow

from machincast.conversion import entier_ou_rien


@dataclass(frozen=True)
class ElementDeSequence:
	"""Un élément de la liste d'une séquence : un sonore ou une banque."""

	id: int
	sequence: int
	position: int
	sonore: int | None
	banque: int | None


@dataclass(frozen=True)
class Sequence:
	id: int
	nom: str
	elements: list[ElementDeSequence]
	"""Dans l'ordre de leur position."""


def lire_sequence(connexion: psycopg.Connection[TupleRow], identifiant: int) -> Sequence | None:
	ligne = connexion.execute("SELECT nom_interne FROM sequences WHERE id = %s", (identifiant,)).fetchone()
	if ligne is None:
		return None
	lignes = connexion.execute(
		"SELECT id, position, sonore_id, banque_id FROM sequences_elements WHERE sequence_id = %s ORDER BY position",
		(identifiant,),
	).fetchall()
	elements = [
		ElementDeSequence(
			id=int(str(element)),
			sequence=identifiant,
			position=int(str(position)),
			sonore=entier_ou_rien(sonore),
			banque=entier_ou_rien(banque),
		)
		for element, position, sonore, banque in lignes
	]
	return Sequence(identifiant, str(ligne[0]), elements)


def elements_apres(sequence: Sequence, dernier: int | None) -> list[ElementDeSequence]:
	"""Éléments qui restent à jouer après le dernier joué ; tous si dernier est None. Un dernier élément supprimé
	depuis termine la séquence : on ne sait plus où la reprendre."""
	if dernier is None:
		return sequence.elements
	ids = [element.id for element in sequence.elements]
	if dernier not in ids:
		return []
	return sequence.elements[ids.index(dernier) + 1 :]
