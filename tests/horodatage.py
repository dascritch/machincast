"""Horodatage des messages des exécutables (https://github.com/dascritch/machincast/issues/253), dans les scénarios.

Chaque ligne commence par l'heure de son message, en ISO 8601, à la seconde, avec le décalage horaire du poste ; les
scénarios l'écrivent « [horodatage] », puisqu'elle change d'un passage à l'autre.
"""

import re

from machincast.journal import HORODATAGE

LIGNES = re.compile(HORODATAGE.pattern, re.MULTILINE)


def sans_horodatage(texte: str) -> str:
	"""Le texte, l'horodatage de chaque ligne remplacé par « [horodatage] » ; une ligne sans horodatage reste telle
	quelle, et le scénario échoue."""
	return LIGNES.sub("[horodatage] ", texte)
