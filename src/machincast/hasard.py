"""Hasard injectable (https://github.com/dascritch/machincast/issues/5).

Tout tirage aléatoire passe par un random.Random reçu en paramètre, créé par creer_hasard : avec une
graine, les tirages sont reproductibles (tests, simulation) ; sans graine, ils sont imprévisibles.
"""

import random


def creer_hasard(graine: int | None = None) -> random.Random:
	return random.Random(graine)
