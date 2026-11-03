"""Scénarios de MachinCast.

Ils se jouent en français, la langue de leurs textes attendus (https://github.com/dascritch/machincast/issues/360) :
la langue est fixée ici, avant tout import de machincast, qui traduit ses constantes en se chargeant. Les programmes que
lancent les scénarios en héritent. Quelques scénarios dédiés vérifient l'anglais et le repli.
"""

import os

os.environ["LANGUAGE"] = "fr"
