"""Hasard injectable (https://github.com/dascritch/machincast/issues/5).

Tout tirage aléatoire passe par un random.Random reçu en paramètre, créé par creer_hasard : avec une
graine, les tirages sont reproductibles (tests, simulation) ; sans graine, ils sont imprévisibles.
"""

import random

Hasard = random.Random
"""Type d'un générateur de hasard, pour les annotations des modules qui en reçoivent un."""


def creer_hasard(graine: int | None = None) -> Hasard:
	return random.Random(graine)
