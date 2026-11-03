"""Hasard injectable (https://github.com/dascritch/machincast/issues/5).

Tout tirage aléatoire passe par un random.Random reçu en paramètre, créé par create_randomness : avec une
graine, les tirages sont reproductibles (tests, simulation) ; sans graine, ils sont imprévisibles.
"""

import random

Randomness = random.Random
"""Type d'un générateur de hasard, pour les annotations des modules qui en reçoivent un."""


def create_randomness(seed: int | None = None) -> Randomness:
	return random.Random(seed)
